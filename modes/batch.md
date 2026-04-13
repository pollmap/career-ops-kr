> Inherits from [_shared.md](_shared.md)

# Mode: batch

`pipeline` 모드의 병렬 버전. asyncio + semaphore(3)로 10~30건 inbox를 동시 평가한다. Nexus MCP 부하와 포털 rate limit을 고려한 제한된 병렬성.

## Purpose

- 대량 inbox 빠른 트리아지 (예: 주 1회 30건 밀어내기).
- `pipeline`은 순차, `batch`는 병렬 — 공고 수가 많을 때 사용.
- 핵심 제약: 동시 실행 최대 3 (Nexus MCP + 포털 부담).
- 상태 전환은 개별 아이템 단위로 isolated — 1건 실패가 다른 건에 영향 없음.

## Inputs

- 없음 (기본: 모든 inbox)
- 선택 인자:
  - `--limit <n>` : 최대 처리 개수 (기본 30, 상한 100)
  - `--portal <name>` : 특정 포털 inbox 필터
  - `--since <days>` : N일 이내 inbox
  - `--concurrency <n>` : 동시 실행 수 (기본 3, 최대 5)
  - `--dry-run` : 상태 전환 없이 결과만 출력

## Process

1. **대상 수집** — `SQLiteStore.list_by_status('inbox', filters=...)` → `list[JobRecord]`.
2. **G4 배치 게이트** — `count >= 5` 이면:
   - **샘플 1건 먼저** 순차 실행 (병렬 X) → 결과를 사용자에게 보여줌.
   - "계속 진행? [y/N]" 블로킹 확인.
   - 거부 시 샘플 1건 결과만 반영 후 종료.
   - 승인 시에만 나머지 병렬 배치 시작.
3. **asyncio 병렬 실행**:
   ```python
   import asyncio
   from pathlib import Path

   sem = asyncio.Semaphore(concurrency)  # 기본 3
   async def process_one(job: JobRecord) -> dict:
       async with sem:
           try:
               archetype = await classify(job)
               verdict = await qualify(job, archetype)
               score = await fit_score(job, archetype)
               await vault_upsert(job, verdict, score)
               return {"ok": True, "job_id": job.id, "verdict": verdict, "grade": score.grade}
           except Exception as e:
               return {"ok": False, "job_id": job.id, "error": str(e)}
   results = await asyncio.gather(*(process_one(j) for j in jobs))
   ```
4. **진행률 표시** — `rich.progress.Progress`로 실시간 bar:
   - `total=len(jobs)`, `completed=해결된 건수`
   - 각 건 완료 시마다 `progress.update(..., advance=1)`
   - 컬럼: `{done}/{total} | OK:{n} FAIL:{m} | elapsed`
5. **상태 전환** — `pipeline` 모드와 동일 매핑:
   - `FAIL` / `SUSPICIOUS` → `rejected_self`
   - `PASS` + Grade S/A/B → `eligible`
   - `PASS` + Grade C/D → `rejected_self`
   - `CONDITIONAL` → `eligible` + 수동 확인 태그
6. **결과 집계 리포트**:
   - 신규 `eligible`: N (grade 분포)
   - 신규 `rejected_self`: M (사유 상위 3)
   - 오류: K (사유 상위 3)
   - 총 소요 시간, 평균 건당 시간
7. **로그** — `data/batch_log.jsonl`에 실행 레코드 append (run_id, started_at, ended_at, counts).

## Rate limit note

- **동시 실행 3 기본** — Nexus MCP 398도구 공유 부하 고려.
- 동일 포털 연속 요청은 QualifierRateLimiter가 자동 제어 (1건당 최소 1.5초).
- 429/403 감지 시 해당 아이템만 exponential backoff (2^n, max 120s), 다른 아이템은 계속 진행.
- 전체 실패율 > 30% 감지 시 자동 중단 + 체크포인트 저장.

## HITL

- **G4 샘플 우선**: 5건 이상 배치 시 반드시 샘플 1건 순차 실행 후 사용자 승인을 받는다. 승인 없이 병렬 시작 금지.
- 배치 중 G2/G3/G5는 해당 모드(score/tracker)에 위임.

## Failure handling

- **Per-job isolation**: 1건 실패 → 해당 `job_id` status는 변경하지 않고 `error_count++`. 로그 기록 후 다른 건은 계속 진행.
- 가짜 verdict 생성 금지 — 실패 건은 `inbox` 상태 그대로 유지.
- Task 전체 캔슬 시 (Ctrl+C) 완료된 건은 유지, 진행 중 건은 롤백 (멱등성).
- 재실행 시 inbox 잔여분부터 이어서 처리 (이미 전환된 건 스킵).
- `--dry-run` 이면 상태 전환 안 함, 결과 표만 출력.

## Output

```
[batch] 대상 30건, 동시성 3

[G4 샘플 체크]
샘플 1건: "XYZ 블록체인 인턴" → PASS / Grade A
계속 진행하시겠습니까? [y/N]: y

[진행] ████████████████ 30/30 | OK:28 FAIL:2 | 3m 24s

=== 결과 요약 ===
신규 eligible: 12 (S:1 A:4 B:7)
신규 rejected_self: 16 (사유: 학점 미달 8, 전공 불일치 5, 적합도 낮음 3)
오류: 2 (사유: 크롤링 실패 2)
총 소요: 3m 24s (평균 6.8s/건)
```

## 실데이터 원칙

- 실패한 아이템을 추정 값으로 채우지 않는다. 에러는 에러로 기록.
- `data/batch_log.jsonl`은 실제 실행 결과만 기록.
