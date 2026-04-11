# CLAUDE.md — career-ops-kr 에이전트 지침

> 이 파일은 Claude Code가 career-ops-kr 리포에서 작업할 때 반드시 따르는 규칙을 정의한다.
> 루트 `~/.claude/CLAUDE.md` 전역 원칙(실데이터/MCP우선/인코딩 UTF-8 등)을 모두 상속한다.

---

## 1. 프로젝트 정체성

- **이름**: career-ops-kr
- **목적**: 찬희(Luxon AI)의 한국 금융/디지털/블록체인 구직 파이프라인 자동화
- **철학**: santifer/career-ops의 "mode 분리 + HITL + 프로필 중심"을 한국화
- **실운영 환경**: Windows 11 로컬 (`C:\Users\lch68\Desktop\career-ops-kr\`)
- **Phase 2 이식 대상**: Luxon VPS (HERMES/NEXUS, Nexus MCP 서버 편입)

---

## 2. 데이터 계약 (CRITICAL INVARIANT)

career-ops-kr는 **User 레이어 / System 레이어**를 엄격히 분리한다.
시스템 업데이트 시 **유저 파일은 절대 수정하지 않는다.**

### 🔶 User 레이어 (찬희 커스터마이징 전용)
- `cv.md` — 찬희 이력서 markdown
- `config/profile.yml` — 개인 프로필 (휴학/비전공/학점/타겟 산업)
- `config/portals.yml` — 포털 구독 목록
- `config/qualifier_rules.yml` — 자격 판정 규칙 (한국 특화)
- `config/scoring_weights.yml` — A~F 가중치
- `modes/_profile.md` — 개인 narrative / archetype / 협상 스크립트
- `data/*` — SQLite, applications.md, tracker-additions

### 🔷 System 레이어 (엔진 — 자동 업데이트 가능)
- `modes/_shared.md` — 모든 모드 공통 컨텍스트
- `modes/_profile.template.md` — `_profile.md`의 템플릿
- `modes/*.md` (개별 모드들, `_profile.md` 제외)
- `templates/*.yml`, `templates/*.html`
- `scripts/*.py` — dedup/merge/normalize/verify
- `career_ops_kr/**/*.py` — Python 코어

### 규칙
1. 찬희가 "archetype 추가해줘" 요청 → `modes/_profile.md` 또는 `config/profile.yml`만 편집
2. "스코어 가중치 바꿔줘" → `config/scoring_weights.yml`만 편집
3. "링커리어 크롤러 고쳐줘" → `career_ops_kr/channels/linkareer.py` (시스템 레이어)
4. User 레이어 파일을 수정할 땐 반드시 `git diff` 보여주고 찬희 확인 (HITL G2)
5. System 레이어 파일 수정은 확인 없이 진행 가능하되 커밋 메시지에 명시

---

## 3. 온보딩 6단계 (첫 실행 시 필수)

`career-ops` CLI가 최초 호출되면 아래 순서로 확인. 누락된 게 있으면 G1 게이트 발동.

1. `cv.md` 존재 확인 → 없으면 대화형 인터뷰로 생성
2. `config/profile.yml` 존재 확인 → 없으면 `templates/profile.example.yml` 복사 + 필드 채우기
3. `modes/_profile.md` 존재 확인 → 없으면 `_profile.template.md` 무음 복사
4. `config/portals.yml` 존재 확인 → 없으면 9개 MVP 포털 템플릿 복사
5. `data/applications.md` 초기화 (빈 테이블 + `states.yml` 참조)
6. 컨텍스트 학습 — 찬희의 강점(superpowers), deal-breaker, 성과, proof points 수집 → `_profile.md`

완료 후: 매일 09:00 `scan` 자동 실행 제안 (Windows 작업 스케줄러).

---

## 4. HITL 5게이트

| 게이트 | 차단 조건 | 해제 방법 |
|--------|-----------|-----------|
| **G1. 온보딩** | 유저 파일 미존재 | CLI 대화형 인터뷰 → 파일 생성 |
| **G2. Archetype 변경** | `modes/_profile.md` 수정 요청 | diff 보여주고 찬희 "적용/취소" |
| **G3. Tracker 병합** | `tracker-additions/*.tsv` → `applications.md` 병합 | dedup 결과 리뷰 후 "merge 승인" |
| **G4. 배치 평가** | `pipeline` 모드 5건 이상 | 샘플 1건 먼저 보여주고 "계속" |
| **G5. 지원 제출** | `apply` 모드 (Phase 2) | **영구 수동** — 시스템은 "준비 완료"까지만 |

구현: `click.confirm()` 블로킹 또는 Discord ✅/❌ 이모지 대기.

---

## 5. 전역 원칙 상속 (루트 CLAUDE.md)

다음 원칙을 career-ops-kr에서도 엄수한다:

- **실데이터 절대 원칙**: 목업/가짜/할루시네이션 금지. 크롤링 실패 시 "실패"로 명시 저장. 추정 데이터 생성 금지.
- **MCP 우선**: Nexus MCP 398도구에 있는 건 재사용. 특히 `vault_*` / `discord_*` 툴군.
- **인코딩**: 모든 파일 I/O `encoding='utf-8'` 명시. `pathlib.Path` 사용. Windows↔WSL↔VPS 간 cp949 가정 금지.
- **범위 엄수**: 찬희가 지정한 범위 밖 확장 금지. 모르면 물어보기.
- **병렬 서브에이전트**: 복잡한 코드 변경은 구현 → 검증 → 테스트 3에이전트 게이트 통과 후 적용.

---

## 6. 출력 포맷 규약

모든 평가 리포트는 아래 필드를 반드시 포함한다 (Career-Ops 차용):

```markdown
**URL:** https://...
**Legitimacy:** T1 공식 | T2 정부포털 | T3 Aggregator | T4 뉴스 | T5 미확인
**Archetype:** 블록체인 | 디지털자산 | 금융IT | 리서치 | 핀테크 | 공공
**Fit Grade:** A (92) | B (85) | C (78) | D (65) | F (42)
**Eligibility:** ✅ 통과 | △ 조건부 | ❌ 자격 미달
**Deadline:** 2026-04-17 (D-6)
```

---

## 7. 금지 사항

- ❌ 공고 자동 제출 (HITL G5 영구)
- ❌ 유저 레이어 파일을 시스템 업데이트 경로로 수정
- ❌ 크롤링 실패를 "추정 데이터"로 대체
- ❌ 1000줄 이상 단일 파일 (분할 필수)
- ❌ `utf-8` 명시 없는 파일 I/O
- ❌ 하드코딩된 찬희 개인정보 (모두 `config/profile.yml` 참조)

---

## 8. 버전 정책

- **MVP (v0.1)**: 7개 모드 + 9개 포털 + HITL G1~G3 + Integrity 4 스크립트
- **Phase 2 (v0.2)**: +6개 모드 + MCP 서버화 + `modes/kr/` 로컬라이제이션
- **Phase 3 (v1.0)**: +3개 모드 + TUI 대시보드 + 74개 포털 + 공개 오픈소스

플랜 원본: `~/.claude/plans/melodic-moseying-cupcake.md`
