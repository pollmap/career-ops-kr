---
name: career-ops-kr
description: 한국 금융/핀테크/블록체인 채용 공고를 수집·판정·점수화·추적하는 개인 커리어 파이프라인. 찬희 프로파일 기반 단일 URL 평가와 전체 포털 스캔 배치 트리아지 지원. HITL 5 게이트로 자동화와 안전성을 동시에 확보.
version: 0.1.0
---

# career-ops-kr

Fork of `santifer/career-ops` — 한국 채용 시장에 맞춘 개인 커리어 운영 시스템. 찬희(24세, 충북대 경영 3-1, Luxon AI / CUFA 회장)의 금융/핀테크/블록체인/공공금융 직무 타겟팅에 최적화.

## When to use

다음 트리거가 감지되면 이 스킬을 사용한다:

- "공고 평가", "이 공고 어때", "잡공고 분석"
- "포털 스캔", "새 공고 있나", "사람인/잡코리아/원티드 훑어봐"
- "내가 지원 가능해?", "자격 되는지 봐줘"
- "기각 사유 분석", "왜 자꾸 떨어지지"
- "지원 기록", "트래커 업데이트"

한국 채용 공고 평가 맥락이 아니면 이 스킬은 활성화하지 않는다.

## Mode dispatcher

| 명령 / 트리거 | 모드 파일 | 역할 |
|---|---|---|
| `/auto-pipeline <URL>` | [modes/auto-pipeline.md](../../../modes/auto-pipeline.md) | **최상위 진입점** — 단일 URL 평가 |
| `/auto-pipeline scan-all` | [modes/auto-pipeline.md](../../../modes/auto-pipeline.md) | **최상위 진입점** — 전 포털 스캔+트리아지 |
| `scan` / "포털 스캔" | [modes/scan.md](../../../modes/scan.md) | 포털 → inbox 적재 |
| `filter` / "자격 판정" | [modes/filter.md](../../../modes/filter.md) | 한국 고유 자격 조건 판정 |
| `score` / "공고 점수" | [modes/score.md](../../../modes/score.md) | 단일 공고 종합 리포트 |
| `pipeline` / "배치 평가" | [modes/pipeline.md](../../../modes/pipeline.md) | inbox → eligible/rejected_self |
| `tracker` / "상태 전환" | [modes/tracker.md](../../../modes/tracker.md) | SQLite+Vault 상태 갱신 |
| `patterns` / "기각 패턴 분석" | [modes/patterns.md](../../../modes/patterns.md) | 탈락 클러스터링 리포트 |

**기본 답변**: 특별한 이유가 없으면 `auto-pipeline` 을 호출하라. 하위 모드는 디버깅/고급 사용자용.

## User layer vs System layer

- **System layer** (이 스킬 / 모드 / 코드) — 찬희가 건드리지 않는 영역. 규칙, 스키마, 파이프라인 구조.
- **User layer** — 찬희가 편집하는 영역:
  - `data/profile.yml` — 개인 프로파일
  - `config/portals.yml` — 포털 enable/disable
  - `templates/states.yml` — 상태 전이 매트릭스
  - `data/applications.md` — **append-only** 지원 이력 (기존 행 수정 금지)

이 경계를 흐리지 말 것. 스킬이 user layer 를 자의적으로 수정해서는 안 된다 (특히 `applications.md` 기존 행).

## 실데이터 원칙

- 외부 데이터 획득 실패 시 **빈 결과 반환**. 가짜 공고/판정/점수 금지.
- 외부 API 오류는 `UNKNOWN` 으로 degrade.
- LLM 요약/추정이 필요한 지점은 명시적으로 "AI 추정" 태그.

## HITL 5 게이트 요약

| ID | 단계 | 차단 여부 |
|---|---|---|
| G1 | Onboarding 체크 | YES (블로킹) |
| G2 | Archetype 확정 | 확인 필요 |
| G3 | merge_tracker (applied+) | YES (명시적 승인) |
| G4 | Batch ≥ 5 | 샘플 먼저 확인 |
| G5 | 실제 제출 | YES (체크리스트 후 명시 승인) |

자세한 로직은 [modes/auto-pipeline.md](../../../modes/auto-pipeline.md) 참고.

## Path references

- Project root: `~/career-ops-kr/`
- Modes: `modes/*.md`
- Python package: `career_ops_kr/`
- Integrity scripts: `scripts/*.py`
- User profile: `data/profile.yml`
- Vault sync root: `Vault/` (외부 Obsidian Vault 미러)

## Integrity scripts

- `scripts/dedup_tracker.py` — 지원 이력 중복 탐지 (dry-run default)
- `scripts/merge_tracker.py` — tracker-additions → applications.md 병합
- `scripts/normalize_statuses.py` — 레거시 상태값 → 표준 enum
- `scripts/verify_pipeline.py` — 파이프라인 헬스체크

## Version

- v0.1.0 (2026-04-11) — 초기 골격 (7 modes + 4 integrity scripts)
