> Inherits from [_shared.md](_shared.md)

# Mode: pipeline

`inbox` 상태의 공고를 배치로 평가하여 `eligible` / `rejected_self` 로 전환한다. 내부적으로 각 아이템마다 `score` 모드를 호출하고, 결과 verdict에 따라 `tracker` 모드로 상태를 넘긴다.

## Purpose

- `scan` 이 쌓아둔 inbox 더미를 일괄 처리.
- 목표: "오늘 inbox 30건 → 아침 한 번 실행 → 지원 후보 8건, 기각 22건" 수준의 빠른 트리아지.
- **쓰기 대상**: SQLiteStore 상태 + Vault 노트 위치. 원본 공고 수정 금지.

## Inputs

- 없음 (기본: 모든 inbox).
- 선택 인자:
  - `--limit <n>` : 최대 처리 개수 (기본 50, 상한 200)
  - `--portal <name>` : 특정 포털 inbox 만
  - `--since <days>` : N일 이내 inbox 만
  - `--dry-run` : 상태 전환 없이 결과 표만 출력

## Process

1. `SQLiteStore.list_by_status('inbox', filters=...)` 로 대상 집합 로드.
2. 개수 계산. 비어있으면 "처리할 inbox 없음" 출력 후 즉시 종료.
3. **G4 배치 게이트** — `count >= 5` 이면:
   - 처음 2건만 먼저 `score` 실행 → 결과를 사용자에게 보여주고 "계속 진행하시겠습니까? [y/N]" 확인.
   - 거부 시 처리한 2건만 결과 반영 후 종료.
4. 각 아이템에 대해 순차 처리 (병렬은 rate limit 고려해 금지):
   - `score` 모드 호출 → verdict, legitimacy, fit_grade, reasons 수집
   - verdict 에 따른 신규 상태 결정:
     - `FAIL` → `rejected_self`
     - `SUSPICIOUS` → `rejected_self` (사기 의심)
     - `PASS` + Grade S/A/B → `eligible`
     - `PASS` + Grade C/D → `rejected_self` (적합도 낮음)
     - `CONDITIONAL` → `eligible` (수동 확인 태그 부여)
   - `tracker` 모드 호출 → 상태 전환 + Vault 노트 이동 + SQLite 업데이트
5. 처리 중 각 아이템 사이에 **최소 1.5초 sleep** (포털 rate limit 보호).
6. 결과 요약을 `data/pipeline_log.jsonl` 에 append.

## Outputs

- 실시간 진행 표시 (`n/total | state → new_state | grade`).
- 최종 요약 표:
  - `신규 eligible: N (grade 분포 S:a A:b B:c)`
  - `신규 rejected_self: M (사유 상위 3: ...)`
  - `오류: K`
- `data/pipeline_log.jsonl` 한 줄 append.

## HITL

- **G4** — 배치 크기 5건 이상 시 샘플 2건 먼저 보여주고 계속할지 확인.
- 다른 게이트는 score/tracker 에 위임.

## Rate limit note

- 아이템 간 1.5초 sleep 필수.
- 동일 포털 연속 시 1건당 sleep 을 3초로 늘리는 `QualifierRateLimiter` 적용.
- 429/403 응답 감지 시 exponential backoff (2^n, max 120s) + 진행률 저장 후 재개 가능하게.

## Failure handling

- score 호출 예외 → 해당 아이템은 상태 변경 없이 `error_count++`, 로그 기록 후 다음으로 진행. **가짜 verdict 생성 금지.**
- tracker 호출 예외 → SQLite 롤백, Vault 이동 역전(복구), 에러 보고.
- `--dry-run` 플래그면 상태 전환을 실제로 수행하지 않음 (결과 표만 출력).
- 세션 중단 시에도 이미 전환된 레코드는 유지 (멱등성). 재실행 시 남은 inbox 부터 계속.
