> Inherits from [_shared.md](_shared.md)

# Mode: auto-pipeline

career-ops-kr 의 **최상위 단일 진입점**. 한 번의 명령으로 URL 평가 또는 전 포털 스캔+트리아지를 완료한다. 모든 HITL 게이트는 이 모드가 중앙에서 관리한다.

## Purpose

- 사용자가 기억해야 할 명령은 이것 하나.
- 두 가지 모드:
  1. `auto-pipeline <URL>` — 단일 공고 평가 → 리포트 + 상태 전환 제안
  2. `auto-pipeline scan-all` — 모든 포털 스캔 → 배치 트리아지 → 요약

## Trigger examples

```bash
# 단일 URL
/auto-pipeline https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345678

# 전체 스캔+트리아지
/auto-pipeline scan-all

# 스캔+트리아지 + 특정 포털만
/auto-pipeline scan-all --portal saramin --limit 30
```

## Process

1. **G1 — Onboarding check** (게이트 1)
   - `data/profile.yml` 존재 & `completed: true` 여부 검증.
   - 미완료면 즉시 `onboarding` 실행 안내 + 진행 중단. 프로파일 없이는 어떤 평가도 수행하지 않음.
2. **라우팅**
   - 인자가 URL 이면 → 단일 경로로 분기 (3번).
   - 인자가 `scan-all` 이면 → 배치 경로로 분기 (4번).
   - 그 외 → 사용법 안내 후 종료.
3. **단일 URL 경로**
   - `score` 모드 호출 → 마크다운 리포트 출력.
   - **G2 — Archetype confirm** (게이트 2): 아키타입 = `unknown` 이거나 confidence < 0.6 이면 사용자에게 "이 공고 archetype 을 X 로 분류. 맞나요? [y/N]" 질의.
   - 사용자가 verdict 를 받고 "지원 후보로 저장?" 물음 → Yes 시 `tracker` 로 `eligible` 전환.
4. **scan-all 경로**
   - `scan` 모드 호출 → 포털별 신규 N건 수집.
   - `scan` 완료 표 출력 후, 곧바로 `pipeline` 모드 호출 (inbox 배치 처리).
   - **G4 — Batch size gate** (게이트 4): `pipeline` 내부에서 5건 이상이면 샘플 2건 먼저 보여주고 확인.
5. **상태 전환 & 알림**
   - `tracker` 모드가 상태/Vault 동기화 수행.
   - **G3 — Merge tracker gate** (게이트 3): `applied` 이상 전환이 제안되면 사용자 확인 필수 (tracker 내부).
6. **제출 단계**
   - **G5 — Submit gate** (게이트 5): 사용자가 실제 지원서 제출 버튼/명령을 요청하면, 제출 전 최종 체크리스트(마감일/자기소개서/첨부/프로파일 스냅샷)를 보여주고 명시적 "제출" 답변이 있어야만 진행. 자동 제출 금지.

## HITL gate map

| ID | 시점 | 트리거 조건 | 차단? |
|---|---|---|---|
| **G1** | 모드 진입 직후 | 프로파일 없음/미완료 | YES — 즉시 중단 |
| **G2** | 단일 URL score 후 | archetype unknown 또는 conf < 0.6 | 사용자 확인 필요 |
| **G3** | tracker 호출 시 | new_status ∈ {applied, interview, offer} | YES — 명시적 승인 |
| **G4** | pipeline 호출 시 | inbox 대상 ≥ 5건 | 샘플 2건 먼저, 계속할지 확인 |
| **G5** | 외부 제출 요청 시 | submit 액션 | YES — 체크리스트 후 명시적 "제출" |

## Failure handling

- 어떤 하위 모드 예외든 상위 요약에 기록하되 **진행 상태는 보존** (부분 성공 허용).
- `scan` 단계에서 전 포털 실패 시 → `pipeline` 단계 건너뛰기 + 오류 리포트만 출력.
- 사용자가 도중에 거부하면 해당 단계에서 즉시 종료. 이후 재실행 시 이어서 수행 가능하게 상태는 멱등.
- **절대 금지**: 데이터 합성, 상태 자동 전진 (gate 우회), 사용자 대신 "제출" 결정.
- 외부 API 오류 → 해당 결과는 `UNKNOWN` 으로 표시. 낙관화 금지.

## Exit criteria

- 단일 URL 경로: `score` 리포트 출력 + (선택) eligible 전환 완료 → 종료.
- scan-all 경로: `scan` 요약 + `pipeline` 요약 두 개 표 출력 + `data/scan_log.jsonl`, `data/pipeline_log.jsonl` 에 append 완료 → 종료.
- 오류 발생 시 적절한 non-zero exit code 와 함께 종료 (0: 정상, 1: 부분 성공, 2: 실패).

## 참고

- 이 모드는 "지휘자" 일 뿐 — 실제 로직은 `scan` / `filter` / `score` / `pipeline` / `tracker` / `patterns` 에 분산. 중복 구현 금지.
- 게이트 재정의가 필요하면 이 파일을 수정하고 하위 모드의 게이트 설명도 일치시킬 것.
