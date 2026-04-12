# career-ops-kr

[![CI](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml/badge.svg)](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Channels](https://img.shields.io/badge/channels-36-green.svg)](#채널-카탈로그)
[![Institutions](https://img.shields.io/badge/institutions-201-orange.svg)](#기관-DB)
[![Tests](https://img.shields.io/badge/tests-588%2B%20passed-brightgreen.svg)](#개발--테스트)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **한국형 구직 자동화 파이��라인** — 36채널 + 201기관 DB + Gemma4 AI 채점.
> 금융·핀테크·블록체인·공공기관·안보기관 도메인 특화. 26 CLI + MCP 10도구 + 로컬 LLM(Ollama). 완전 오픈소스.

```bash
career-ops status                # 전체 상태 대시보드 + 자격증 D-day
career-ops scan --all            # 36채널 병��� 스캔
career-ops institutions          # 201기관 aggregator 검색
career-ops auto-pipeline --ai-score  # scan → Gemma4 AI 채점 → SQLite
career-ops list --grade A        # A등급 공고만 조회
career-ops history               # 과거 마감 공고 수집 (패턴 분석)
career-ops ncs                   # NCS 10영역 대시��드
career-ops vault-sync            # Obsidian Vault 동기화
```

---

## 무엇을 하는가

```
┌──────────────────────────────────────────────────────────────────┐
│                    career-ops-kr 파이프라인                      │
│                                                                  │
│  ┌──────────┐   fetch   ┌──────────────┐  score  ┌───────────┐  │
│  │ 27개 포털 │ ────────▶ │  JobRecord   │ ──────▶ │ A~F 등급  │  │
│  │  (채널)  │           │  (정규화)    │         │ + 자격판정 │  │
│  └──────────┘           └──────────────┘         └───────────┘  │
│        ↑                       ↓                       ↓        │
│  portals.yml             SQLite 저장소             CLI 출력      │
│  (키워드필터)             data/jobs.db            Discord 알림   │
└──────────────────────────────────────────────────────────────────┘
```

**핵심 기능**:
- **34개 포털 병렬 스캔** — 대학생 특화·공공기관·증권사·핀테크·크립토
- **JobRecord 표준 스키마** — 포털마다 다른 공고 형식을 단일 pydantic 모델로 정규화
- **archetype 분류** — `BLOCKCHAIN_INTERN` / `KDA_COHORT` / `DATA` / `ENGINEER` 등 도메인 태그
- **Legitimacy Tier** — T1(공식)/T2(정부)/T3(aggregator) 신뢰도 레이어
- **3-tier selector fallback** — PRIMARY CSS → HREF 패턴 → 키워드 스캔 (DOM 변경에 강인)
- **Zero mock data** — 수집 실패 시 빈 리스트 반환, 추정 데이터 생성 절대 금지

---

## 채널 카탈로그 (34개)

### Tier 1 — General Major (대형 민간 포털, 8채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `linkareer` | linkareer.com | 대학생 특화 — 인턴/대외활동/공모전 |
| `catch` | catch.co.kr | 대학생 채용 포털 — INTERN/ACTIVITY archetype |
| `wanted` | wanted.co.kr | 핀테크/IT — API-first 수집 |
| `jobkorea` | jobkorea.co.kr | 국내 1위 민간 채용 |
| `incruit` | incruit.com | 대기업·중견 공채 |
| `jobplanet` | jobplanet.co.kr | 기업 리뷰 + 채용 |
| `jasoseol` | jasoseol.com | 자소서 문항 + 공고 |
| `saramin` | saramin.co.kr | 전수 수집 — 페이지네이션 5~20p |

### Tier 2 — Public Agency (공공/정부 포털, 7채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `jobalio` | job.alio.go.kr | 공공기관 공식 — RSS + HTML fallback |
| `apply_bok` | apply.bok.or.kr | 한국은행 직접 채용 |
| `yw_work24` | yw.work24.go.kr | 청년일경험 포털 |
| `kiwoomda` | kiwoomda.com | 키움 DA |
| `dataq` | dataq.or.kr | 데이터 전문 자격/채용 |
| `mirae_naeil` | work.go.kr/experi | 미래내일 일경험 — ALT URL fallback |
| `mjob` | mjob.mainbiz.or.kr | 중소기업진흥공단 일자리 |

### Tier 3 — Target-Specific & Securities (12채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `kiwoom_kda` | recruit.kiwoom.com | **KDA 기수 우선** — `KDA_COHORT` archetype |
| `shinhan_sec` | recruit.shinhansec.com | **블록체인부 특화** — `BLOCKCHAIN_INTERN` archetype |
| `kakao_pay` | kakaopay.com/careers | 카카오페이 직채용 |
| `kakao_bank` | kakaobank.com/careers | 카카오뱅크 직채용 |
| `mirae_asset` | careers.miraeasset.com | 미래에셋증권 |
| `kb_sec` | recruit.kbsec.com | KB증권 |
| `hana_sec` | careers.hanasec.co.kr | 하나증권 |
| `nh_sec` | recruit.nhqv.com | NH투자증권 |
| `samsung_sec` | recruit.samsungsecurities.com | 삼성증권 |
| `korea_invest_sec` | recruit.truefriend.com | 한국투자증권 |
| `ibk_sec` | ibks.com/recruit | IBK투자증권 |
| `daishin_sec` | daishin.com/recruit | 대신증권 |

### Tier 4 — Crypto/Fintech (7채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `dunamu` | careers.dunamu.com | 두나무/업비트 |
| `bithumb` | bithumbcorp.com/careers | 빗썸코리아 |
| `toss` | toss.im/career/jobs | 토스그룹 통합 |
| `lambda256` | lambda256.io/careers | 두나무 자회사 — Luniverse 블록체인 |
| `banksalad` | career.banksalad.com | 뱅크샐러드 — 금융 비교 플랫폼 |
| `finda` | finda.co.kr/careers | 핀다 — 대출 비교 핀테크 |
| `coinone` | coinone.co.kr/careers | 코인원 — 크립토 거래소 |

---

## 아키텍처

```
career_ops_kr/
├── channels/
│   ├── base.py              ← BaseChannel ABC + JobRecord pydantic 모델
│   ├── _stub_helpers.py     ← 9개 stub 채널용 팩토리
│   ├── __init__.py          ← CHANNEL_REGISTRY (27채널 등록)
│   ├── saramin.py           ← 완전 구현 예시 (페이지네이션 + 3-tier)
│   ├── shinhan_sec.py       ← BLOCKCHAIN_INTERN archetype 특화
│   ├── kiwoom_kda.py        ← KDA_COHORT archetype 특화
│   └── ... (27개 채널 파일)
├── parser/
│   └── utils.py             ← 마감일 파싱 SSOT (deadline_parser)
├── pipeline.py              ← 채널 오케스트레이션
└── cli.py                   ← Click CLI

config/                      ← USER LAYER (사용자 커스터마이징)
├── portals.yml              ← 포털 구독 목록 + 키워드 필터
├── profile.yml              ← 사용자 프로필
└── scoring_weights.yml      ← A~F 채점 가중치

tests/                       ← 434개 unit test (네트워크 0)
```

### BaseChannel 인터페이스

```python
class BaseChannel(ABC):
    name: str       # 채널 고유 키 (portals.yml key와 일치)
    tier: int       # 1~5 (낮을수록 우선순위 높음)
    backend: str    # "requests" | "rss+html" | "api"

    def check(self) -> bool: ...                         # 포털 접근 가능 여부
    def list_jobs(self, query=None) -> list[JobRecord]: ...
    def get_detail(self, url: str) -> JobRecord | None: ...
```

### JobRecord 스키마

```python
class JobRecord(BaseModel):
    id: str                    # 16자 SHA-256 stable ID (dedup 키)
    source_url: str            # 원본 공고 URL
    org: str                   # 기업/기관명
    title: str                 # 공고 제목
    archetype: str             # INTERN / KDA_COHORT / BLOCKCHAIN_INTERN / DATA ...
    deadline: datetime | None  # 마감일
    legitimacy_tier: str       # T1~T5
    fetch_errors: list[str]    # 수집 오류 로그
```

### 3-tier Selector Fallback

```
1. PRIMARY     → 포털 특화 CSS selector (div.item_recruit a 등)
       ↓ 0개 반환 시
2. HREF 패턴  → a[href*='/recruit/'] 등 URL 패턴
       ↓ 0개 반환 시
3. GENERIC     → "채용"/"모집"/"공고" 포함 anchor 전수 스캔
```

---

## 설치 및 사용법

### 설치

```bash
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
uv sync
```

### 기본 사용

```bash
# 전체 채널 스캔 (Windows에서 한글 출력)
PYTHONIOENCODING=utf-8 uv run career-ops scan

# 특정 채널만
uv run career-ops scan --site kiwoom_kda
uv run career-ops scan --site shinhan_sec
uv run career-ops scan --site kakao_pay

# 공고 목록 (등급 필터)
uv run career-ops list --min-grade B

# 프로필 기반 채점
uv run career-ops score

# 원스텝 파이프라인
uv run career-ops pipeline
```

### 워크플로우

```
매일 09:00 (Windows 작업 스케줄러)
      │
      ▼
career-ops scan      ← 27채널 순차 스크래핑
      │
      ▼
JobRecord 정규화     ← 포털마다 다른 포맷 → 단일 스키마
      │
      ▼
career-ops score     ← profile.yml + scoring_weights.yml → A~F
      │
      ▼
career-ops list      ← 상위 등급 공고 출력 / Discord 알림
      │
      ▼
수동 지원            ← HITL G5 영구 수동 (자동 제출 없음)
```

### config/portals.yml 커스터마이징

```yaml
portals:
  - name: "링커리어"
    key: "linkareer"
    enabled: true          # false → scan 제외
    filters:
      include:             # 이 키워드 포함 공고만 수집
        - "금융"
        - "핀테크"
      exclude:             # 이 키워드 포함 공고 제외
        - "영업"
```

---

## 개발 / 테스트

```bash
# 전체 테스트 (434개, 네트워크 0)
uv run pytest -q

# 특정 채널 테스트
uv run pytest tests/test_kiwoom_kda_channel.py -v

# 린터 / 포맷 확인
uv run ruff check .
uv run ruff format --check .
```

### 새 채널 추가

```
1. career_ops_kr/channels/my_portal.py   ← BaseChannel 상속
2. tests/test_my_portal_channel.py       ← _FakeResponse + monkeypatch 패턴
3. career_ops_kr/channels/__init__.py    ← CHANNEL_REGISTRY 등록
4. config/portals.yml                   ← 포털 항목 추가
```

기존 구현이 잘 된 채널(`saramin.py`, `kiwoom_kda.py`, `kakao_pay.py`)을 템플릿으로 사용.

---

## 현재 상태 (2026-04-12)

| 항목 | 현황 |
|------|------|
| 버전 | **v0.2.0** |
| 채널 | **34개** (T1~T4) |
| CLI 커맨드 | **19개** (scan/score/filter/batch/notify/apply/interview-prep/followup/project/patterns/vault-sync ...) |
| MCP 도구 | **10개** (FastMCP + stdio JSON-RPC 이중 지원) |
| TUI | **5개 화면** (dashboard/jobs/calendar/patterns/help) |
| Backend | requests 전용 (Scrapling/Playwright 의존 0개) |
| Tests | **562 passed** / 0 failed |
| CI | GitHub Actions ubuntu/windows × py3.11/3.12 |
| 공개 | [pollmap/career-ops-kr](https://github.com/pollmap/career-ops-kr) (MIT) |

### v0.2 신규 기능

- **9개 CLI 커맨드**: filter / auto-pipeline / batch / notify / apply / interview-prep / followup / project / patterns
- **6개 채널 추가**: 한국투자증권 / IBK투자증권 / 대신증권 / 뱅크샐러드 / 핀다 / 코인원
- **TUI 패턴 화면**: 상태/등급/아키타입 분포 + 거절율 + 인사이트
- **VaultSync CLI**: `career-ops vault-sync` — SQLite → Obsidian 마크다운 동기화
- **병렬 스캔**: `career-ops scan --concurrency 4` — ThreadPoolExecutor 기반
- **AI 지원 도구**: STAR 면접 질문 / 후속 이메일 / 포트폴리오 스프린트 (LLM + fallback)
- **14섹션 기술 문서**: `docs/ARCHITECTURE.md`

### 다음 작업

- [ ] Tier 3-4 selector 튜닝 (#5)
- [ ] 포털 34개 → 74개 확장
- [ ] Windows 작업 스케줄러 자동 등록
- [ ] VPS Nexus MCP 등록 (#7)

---

## 레퍼런스

- [santifer/career-ops](https://github.com/santifer/career-ops) — 원본 설계 참고
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — Channel 아키텍처 패턴

## 라이선스

MIT — see [LICENSE](LICENSE).
