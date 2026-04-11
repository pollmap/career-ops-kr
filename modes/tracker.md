> Inherits from [_shared.md](_shared.md)

# Mode: tracker

`JobRecord` 의 상태를 한 단계 전환한다. 전환은 `templates/states.yml` 에 정의된 다이어그램에 따라서만 허용된다. 전환 시 SQLite + Vault 노트 위치 + 인덱스 세 곳을 원자적으로 갱신한다.

## Purpose

- 다른 모드(`pipeline`, `score`, 수동)가 "이 공고 상태 바꿔" 요청할 때 단일 창구.
- Career-Ops 원본의 "applications.md 기존 행 수정 금지" 원칙을 보존하면서, 신규 상태 전환만 허용.

## Inputs

- `record_id` (SQLite row id) 또는 `external_key` (source_url or source__external_id)
- `new_status`: `inbox` / `eligible` / `rejected_self` / `applied` / `interview` / `offer` / `rejected_site` / `withdrawn`
- `reason` (선택): 한 줄 전환 사유
- `meta` (선택): dict — 예: `{"deadline": "...", "next_action": "..."}`

## Process

1. SQLite에서 대상 레코드 로드. 없으면 에러 종료.
2. 현재 상태 확인 후 `templates/states.yml` 의 `transitions` 매트릭스로 허용 여부 검증.
3. **G3 (merge_tracker) 게이트** — 요청 상태가 `applied` 이상(= 영구 기록성)이면:
   - 사용자에게 "이 전환은 실제 지원 이력에 기록됩니다. 진행? [y/N]" 확인 필수.
   - 거부 시 즉시 중단.
4. SQLite 트랜잭션 시작:
   - `UPDATE jobs SET status=?, updated_at=?, last_reason=? WHERE id=?`
   - `INSERT INTO job_history(...)` — 전환 이력 append-only
5. Vault 노트 이동:
   - 현재 경로 계산: `Vault/<folder_for(old_status)>/<filename>.md`
   - 목표 경로: `Vault/<folder_for(new_status)>/<filename>.md`
   - `shutil.move(...)` (encoding 무관 바이너리 이동)
   - 노트 frontmatter `status` 필드 업데이트
6. `Vault/index.md` 재생성 (`VaultSync.write_index()`).
7. 예외 발생 시 1~6 모두 롤백 (SQLite savepoint + 파일 이동 역전).

## Allowed transitions

| From \\ To | inbox | eligible | rejected_self | applied | interview | offer | rejected_site | withdrawn |
|---|---|---|---|---|---|---|---|---|
| inbox | - | OK | OK | - | - | - | - | - |
| eligible | - | - | OK | OK | - | - | - | OK |
| rejected_self | OK | OK | - | - | - | - | - | - |
| applied | - | - | - | - | OK | - | OK | OK |
| interview | - | - | - | - | - | OK | OK | OK |
| offer | - | - | - | - | - | - | - | OK |
| rejected_site | - | - | - | - | - | - | - | - |
| withdrawn | - | - | - | - | - | - | - | - |

실제 enum/매트릭스는 `templates/states.yml` 이 단일 진실원천(SSOT).

## HITL

- **G3** — `applied` 이상 전환 시 확인 프롬프트.
- 그 외 전환은 자동 허용 (inbox↔eligible↔rejected_self 는 자유로움).

## Failure handling

- 허용되지 않은 전환 → 에러 + 현재 전이표 노출. 아무것도 변경하지 않음.
- 레코드 없음 → 에러. **가짜 레코드 생성 금지.**
- 파일 이동 중 실패 → SQLite rollback, 원래 경로로 파일 복원.
- `states.yml` 로드 실패 → 전환 거부. 전환 로직을 하드코딩된 fallback 으로 우회하지 말 것.
- 동시성: SQLite에 `BEGIN IMMEDIATE` 사용으로 동시 쓰기 충돌 방지.
