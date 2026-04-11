> Inherits from [_shared.md](_shared.md)

# Mode: scan

한국 채용 포털을 순회하며 신규 공고를 수집하고 `SQLiteStore` + `Vault 0-inbox`에 업서트한다.

## Purpose

- `config/portals.yml` 에 `enabled: true` 로 등록된 포털만 대상으로 **list_jobs** 호출 → 정규화 → 저장.
- 결과물은 "평가 이전 상태"인 `inbox` 상태로만 적재한다. 평가/점수/자격판정은 별도 모드(`filter`, `score`, `pipeline`) 담당.
- 한 번의 scan 실행이 실패해도 다른 포털에 전파되지 않도록 포털 단위 격리.

## Inputs

- 없음 (기본). 선택 인자:
  - `--portal <name>` : 특정 포털만 스캔
  - `--since <days>` : N일 이내 공고만 upsert (기본 7)
  - `--limit <n>` : 포털당 최대 수집 개수 (기본 50)

## Process

1. **G1 Onboarding 확인** — `data/profile.yml` 이 없거나 `completed: false` 면 즉시 중단하고 `onboarding` 실행 안내만 출력. scan 수행 금지.
2. `config/portals.yml` 로드 → `enabled: true` 항목만 선별.
3. 각 포털에 대해 병렬(최대 3 concurrent) 로:
   - `career_ops_kr.channels.<portal>.Channel.list_jobs(since=...)` 호출
   - 반환값을 `JobNormalizer.normalize(raw)` 로 `JobRecord` 변환
   - 포털 단위 try/except 로 래핑. 실패 시 해당 포털만 스킵하고 `scan_log` 에 error 기록.
4. 모든 정규화 레코드에 대해:
   - `SQLiteStore.upsert(record, status='inbox')` (이미 존재 시 last_seen_at만 갱신)
   - 신규 레코드만 `VaultSync.write_inbox_note(record)` 로 `Vault/0-inbox/` 에 마크다운 노트 생성
5. 실행 요약을 `data/scan_log.jsonl` 에 append (utf-8, 한 줄 JSON).

## Outputs

- 콘솔 표 (포털별):
  - `포털 | 조회 | 신규 | 중복 | 오류 | 경과(s)`
- 종합 수치: `전체 신규 N건 / 오류 M건 / 총 경과 X초`
- `data/scan_log.jsonl` 한 줄 추가.

## HITL

- **G1 (onboarding check)** 만 적용. 그 외 게이트 없음 (수집은 자동 승인).

## Failure handling (실데이터 원칙)

- 포털 응답이 비었거나 파싱 실패 → 해당 포털 결과는 **빈 리스트** 로 처리. **절대 가짜 공고를 생성하지 말 것.**
- 네트워크/인증 실패 → error 로그만 남기고 다음 포털로 진행.
- `.auth/*.json` 만료/없음 → 해당 포털 스킵 + 사용자에게 재로그인 안내 메시지.
- SQLite 트랜잭션 실패 → rollback 후 해당 레코드만 스킵, 나머지는 계속.
- 모든 포털이 실패한 경우라도 허위 데이터 합성 금지. 종료 코드 1 과 함께 원인 로그 출력.

## 참고

- 실제 채널 구현은 `career_ops_kr/channels/<portal>.py` 참조.
- `JobRecord` 스키마는 `career_ops_kr/store/models.py` 참조.
- Vault 경로: `Vault/0-inbox/<source>__<external_id>.md`
