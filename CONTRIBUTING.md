# Contributing to career-ops-kr

## 환영 / Welcome

career-ops-kr에 기여하려고 와주셔서 감사합니다. 이 프로젝트는 Luxon AI 창업자 이찬희가
한국 구직 시장(특히 금융/핀테크/블록체인)용으로 만든 AI 구직 자동화 에이전트이며,
`CLAUDE.md`가 강제하는 **User/System 레이어 분리 구조** 덕분에 금융 밖의 도메인으로도
확장 가능합니다.

Thanks for considering a contribution. career-ops-kr is a Korean-first AI job-hunt
automation agent originally built by 이찬희 (Luxon AI) for finance/fintech/blockchain,
but the User/System layer separation enforced by `CLAUDE.md` makes it multi-domain.

---

## 개발 환경 세팅 / Development Setup

```bash
# 1. 클론
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr

# 2. 의존성 설치 (uv 권장)
uv sync --extra dev
uv sync --extra scrapling   # optional: adaptive scraper layer

# 3. Playwright 브라우저 설치
uv run playwright install chromium

# 4. 테스트 실행
uv run pytest -q

# 5. CLI 확인
uv run career-ops --help
```

Python 3.11+, Windows / Ubuntu 양쪽에서 CI 가 돌아갑니다.

---

## 작업 원칙 / Working Principles

이 프로젝트에는 **절대 원칙 (invariants)** 이 있습니다. PR 을 올리기 전 반드시 숙지하세요.

### 1. UTF-8 인코딩 필수
- 모든 파일 I/O 에 `encoding='utf-8'` 을 명시.
- Windows↔WSL↔VPS 간 cp949 가정 금지. `pathlib.Path` 사용.
- VPS/WSL 스크립트는 `PYTHONIOENCODING=utf-8` 설정.

### 2. 실데이터 원칙 (No Mock Data)
- 목업, 가짜 데이터, LLM 할루시네이션 금지.
- 크롤링 실패 시 "실패"로 명시 저장. 추정 데이터로 대체 금지.
- 테스트도 가능하면 실제 HTML 캡처로 회귀 데이터셋 구성.

### 3. User / System 레이어 분리 엄수 (`CLAUDE.md` 참조)
- **User 레이어** (개인 커스터마이징 전용 — 시스템 업데이트로 건드리지 말 것):
  - `cv.md`, `config/profile.yml`, `config/portals.yml`, `config/qualifier_rules.yml`,
    `config/scoring_weights.yml`, `modes/_profile.md`, `data/*`
- **System 레이어** (엔진 — 자동 업데이트 가능):
  - `career_ops_kr/**/*.py`, `modes/_shared.md`, `modes/*.md` (`_profile.md` 제외),
    `templates/*`, `scripts/*.py`, `presets/*.yml`
- PR 이 User 레이어를 건드리면 반드시 설명과 함께.

### 4. HITL 5 Gates 준수
| Gate | 차단 조건 |
|------|-----------|
| G1 | 온보딩 (유저 파일 미존재) |
| G2 | Archetype 변경 (`_profile.md` 수정) |
| G3 | Tracker 병합 |
| G4 | 5건 이상 배치 평가 |
| G5 | **자동 제출 영구 금지** (apply 모드는 "준비 완료"까지만) |

자동 제출 로직을 추가하는 PR 은 **merge 되지 않습니다**.

---

## 새 프리셋 추가 / Adding a Preset

새 도메인 프리셋(예: `legal`, `healthcare`, `game`)을 제안하려면:

1. [docs/adding-a-preset.md](docs/adding-a-preset.md) 를 읽기
2. `presets/<domain>.yml` 작성 (finance.yml 이 참고 모범)
3. 해당 도메인의 주요 포털 3~5개 목록화
4. archetype 4~6개 정의
5. `career-ops init --preset <domain> --dry-run` 로 검증
6. PR 에 **실 데이터 기반 예시** 1건 첨부

---

## 새 채널 추가 / Adding a Channel

새 포털(채널) 지원을 추가하려면:

1. `career_ops_kr/channels/base.py` 의 **Channel Protocol** 구현
2. 가능한 경우 순서: RSS/API → requests+bs4 → scrapling → playwright
3. **실제 HTML 캡처** (`tests/fixtures/<channel>/`) 로 선택자 튜닝
4. Tier 등급 지정 (T1 공식 / T2 정부 / T3 Aggregator / T4 뉴스 / T5 미확인)
5. 회귀 테스트 추가 (실 공고 1건 이상)

---

## 테스트 / Testing

```bash
uv run pytest -q                    # 전체
uv run pytest -q tests/test_cli.py  # 특정 파일
uv run pytest -q -m "not slow"      # 빠른 것만
uv run pytest -q -m "not playwright"  # 브라우저 없이
```

- 모든 PR 은 회귀 테스트 통과 필수.
- 새 기능은 테스트 포함 필수 (80% 커버리지 목표).
- 실 HTML fixture 를 쓰는 게 Mock 보다 강하게 권장됩니다.

---

## PR 가이드라인 / Pull Request Guidelines

### 브랜치 이름
- `feat/<scope>` — 새 기능
- `fix/<scope>` — 버그 수정
- `refactor/<scope>` — 리팩토링
- `docs/<scope>` — 문서
- `preset/<domain>` — 새 프리셋
- `channel/<portal>` — 새 채널

### 커밋 메시지 (Conventional Commits)
```
<type>: <description>

<optional body>
```
타입: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### 리뷰 체크리스트
- [ ] UTF-8 인코딩 준수
- [ ] User/System 레이어 분리 준수
- [ ] 실데이터 원칙 (no mock)
- [ ] 테스트 추가/업데이트
- [ ] `ruff check .` 통과
- [ ] `mypy career_ops_kr` 통과
- [ ] 문서 업데이트 (해당 시)
- [ ] HITL 게이트 변경 없음 (또는 명시적 논의)

---

## Code of Conduct

이 프로젝트는 Contributor Covenant 2.1 을 따릅니다. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 참조.
