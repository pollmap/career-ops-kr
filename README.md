# career-ops-kr

[![CI](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml/badge.svg)](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Channels](https://img.shields.io/badge/channels-212-green.svg)](#채널-카탈로그)
[![Institutions](https://img.shields.io/badge/institutions-201-orange.svg)](#기관-DB)
[![Tests](https://img.shields.io/badge/tests-609%20collected-blue.svg)](#개발--테스트)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **한국형 구직 자동화 파이프라인** — 212채널 엔트리 + 201기관 DB + AI 채점.
> 금융·핀테크·블록체인·공공기관·안보기관 도메인 특화. 30 CLI 커맨드. 완전 오픈소스.

**누구나 사용 가능합니다.** `config/profile.yml` 하나만 바꾸면 자신의 도메인에 맞게 바로 사용할 수 있도록 설계되었습니다.

---

## 무엇인가

```
링커리어/사람인/원티드/증권사채용/공공기관...
         ↓ 자동 스캔 (매일 or 수동)
  JobRecord (포털별 다른 형식 → 단일 스키마로 정규화)
         ↓ SQLite DB 저장
  엑셀 출력 / CLI 조회 / AI 채점 / Discord 알림
```

**한 줄 요약**: 한국 금융·IT·공공기관 취업 공고를 자동으로 수집하고, 본인 프로필에 맞게 채점해서 엑셀/DB로 정리해주는 Python 도구.

---

## 30초 빠른 시작

```bash
# 1. 설치
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
pip install uv && uv sync

# 2. 내 프로필 설정 (선택 — 기본값으로도 동작)
cp templates/profile.example.yml config/profile.yml
# 편집: 이름/관심직종/지역/경력 등

# 3. 스캔 실행 (링커리어 우선 권장 — 도메인 일치율 높음)
uv run career-ops scan --site linkareer    # ⭐ 링커리어 (추천)
uv run career-ops scan --site saramin      # 사람인 (금융 도메인 자동 필터 ON)
uv run career-ops scan --all              # 전체 212채널 레지스트리 스캔

# 4. 결과 확인
uv run career-ops list                    # 터미널 테이블
uv run career-ops export                  # 엑셀 파일로 출력

# 5. 웹 대시보드 (Streamlit)
uv run career-ops web                     # 브라우저에서 localhost:8501 오픈
```

> **Windows 사용자**: 한글 출력을 위해 `$env:PYTHONIOENCODING="utf-8"` 먼저 실행하거나, `uv run` 대신 `PYTHONIOENCODING=utf-8 python -m career_ops_kr.cli` 사용.

---

## 파이프라인 구조

```
┌──────────────────────────────────────────────────────────────────┐
│                    career-ops-kr 파이프라인                      │
│                                                                  │
│  ┌──────────┐   fetch    ┌──────────────┐  score  ┌──────────┐  │
│  │ 212개 채널│ ─────────> │  JobRecord   │ ──────> │ A~F 등급 │  │
│  │ (포털/직채)│           │  (정규화)    │         │ +자격판정│  │
│  └──────────┘           └──────────────┘         └──────────┘  │
│        ↑                       ↓                       ↓        │
│  config/portals.yml      SQLite 저장소             CLI/Excel    │
│  (채널 on/off)           data/jobs.db            Discord 알림   │
└──────────────────────────────────────────────────────────────────┘
```

---

## CLI 명령어 전체 목록

```bash
# 시스템 상태
career-ops status              # LLM/DB/채널/자격증 D-day 한눈에

# 수집
career-ops scan --all                    # 전체 채널 레지스트리 스캔
career-ops scan --site linkareer         # 특정 채널만
career-ops scan --tier 1                 # Tier 1 채널만
career-ops history                       # 과거 마감 공고 수집 (패턴 분석)
career-ops institutions                  # 201개 금융기관 aggregator 검색

# 조회
career-ops list                          # 공고 테이블 출력
career-ops list --grade A                # A등급만
career-ops list --open-only              # 마감 안 된 것만
career-ops export                        # Excel 파일로 출력
career-ops export --open-only -o jobs.xlsx

# AI 채점
career-ops score <URL>                   # 단일 공고 상세 채점
career-ops batch                         # inbox 전체 배치 채점 + fit_grade 저장
career-ops ai-rank                       # AI 적합도 랭킹
career-ops auto-pipeline --ai-score      # scan → 채점 → 저장 원스텝

# 지원 도구
career-ops filter <URL>                  # 자격 판정 (지원 가능 여부)
career-ops apply <URL>                   # 지원 체크리스트
career-ops interview-prep <URL>          # STAR 면접 질문 자동 생성
career-ops followup <URL>                # 후속 이메일 초안
career-ops project <URL>                 # 포트폴리오 스프린트 플랜

# 기타
career-ops ncs                           # NCS 10영역 대시보드
career-ops calendar                      # 마감일 .ics 캘린더 파일
career-ops notify                        # Discord 알림 전송
career-ops vault-sync                    # SQLite → Obsidian 동기화
career-ops web                           # Streamlit 웹 대시보드 (localhost:8501)
career-ops web --port 8502               # 포트 변경
career-ops web --no-browser              # 브라우저 자동 오픈 없이 서버만 실행
career-ops ui                            # TUI 대시보드 (Textual)
career-ops init                          # 첫 실행 온보딩
```

---

## 채널 카탈로그 (36개 대표 예시)

현재 `CHANNEL_REGISTRY`는 `212`개 엔트리이며, 아래 표는 핵심 대표 채널만 발췌한 목록입니다.

### Tier 1 — 대형 포털 (범용, 8채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `linkareer` | linkareer.com | 대학생 인턴/대외활동/공모전 특화. 금융 12개 키워드 자동 검색 |
| `saramin` | saramin.co.kr | 금융 키워드 자동 검색. 페이지네이션 3~20p |
| `wanted` | wanted.co.kr | 핀테크/IT. JSON API-first 수집 |
| `jobkorea` | jobkorea.co.kr | 국내 1위 민간 채용 포털 |
| `incruit` | incruit.com | 대기업·중견 공채 |
| `jobplanet` | jobplanet.co.kr | 기업 리뷰 + 채용 정보 |
| `jasoseol` | jasoseol.com | 자소서 문항 + 공고 |
| `catch` | catch.co.kr | 대학생 채용 포털 |

### Tier 2 — 공공/정부 포털 (7채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `jobalio` | job.alio.go.kr | 공공기관 채용 공식 포털. RSS + HTML fallback |
| `apply_bok` | apply.bok.or.kr | 한국은행 직접 채용 |
| `yw_work24` | yw.work24.go.kr | 청년일경험 포털 |
| `kiwoomda` | kiwoomda.com | 키움증권 데이터분석 |
| `dataq` | dataq.or.kr | 데이터 전문 자격·채용 |
| `mirae_naeil` | work.go.kr/experi | 미래내일 일경험 |
| `mjob` | mjob.mainbiz.or.kr | 중소기업진흥공단 |

### Tier 3 — 금융/증권 직채용 (12채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `kiwoom_kda` | recruit.kiwoom.com | KDA 기수 — `KDA_COHORT` archetype |
| `shinhan_sec` | recruit.shinhansec.com | 블록체인부 특화 — `BLOCKCHAIN_INTERN` archetype |
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

### Tier 4 — 크립토/핀테크 (7채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `dunamu` | careers.dunamu.com | 두나무/업비트 |
| `bithumb` | bithumbcorp.com/careers | 빗썸코리아 |
| `toss` | toss.im/career/jobs | 토스그룹 통합 |
| `lambda256` | lambda256.io/careers | 두나무 자회사 — Luniverse 블록체인 |
| `banksalad` | career.banksalad.com | 뱅크샐러드 |
| `finda` | finda.co.kr/careers | 핀다 — 대출 비교 핀테크 |
| `coinone` | coinone.co.kr/careers | 코인원 |

### Tier 5 — 안보/국방/공공기관 (2채널)

| key | 사이트 | 특징 |
|-----|--------|------|
| `institutions_securities` | 각 증권사 직채용 | 201개 금융기관 aggregator |
| `institutions_public` | 공공기관 직채용 | 정부/공기업 직채용 |

---

## 아키텍처

```
career_ops_kr/
├── channels/
│   ├── base.py              # BaseChannel ABC + JobRecord pydantic 모델
│   ├── _stub_helpers.py     # 팩토리 기반 stub 채널 생성
│   ├── __init__.py          # CHANNEL_REGISTRY (212개 엔트리 등록)
│   ├── linkareer.py         # Next.js __NEXT_DATA__ JSON + CSS 와일드카드
│   ├── saramin.py           # 금융 키워드 반복 + 페이지네이션
│   ├── wanted.py            # JSON API-first + HTML fallback
│   ├── shinhan_sec.py       # BLOCKCHAIN_INTERN archetype 특화
│   ├── kiwoom_kda.py        # KDA_COHORT archetype 특화
│   └── ... (대표 채널 예시, 전체 212개)
├── cli.py                   # Click CLI (27개 커맨드)
└── pipeline.py              # 채널 오케스트레이션

config/                      # 사용자 설정 (본인 것으로 교체)
├── profile.yml              # 이름/관심직종/학력/우대조건
├── portals.yml              # 채널 on/off + 키워드 필터
└── scoring_weights.yml      # A~F 채점 가중치

data/
└── jobs.db                  # SQLite — 수집된 공고 저장소

tests/                       # 449개 unit test (네트워크 0)
```

### BaseChannel 인터페이스

모든 채널은 아래 3개 메서드를 구현합니다:

```python
class BaseChannel(ABC):
    name: str       # 채널 고유 키 (예: "linkareer")
    tier: int       # 1~5 (낮을수록 우선순위 높음)
    backend: str    # "requests" | "rss+html" | "api"

    def check(self) -> bool:
        """포털 접근 가능 여부 확인"""

    def list_jobs(self, query=None) -> list[JobRecord]:
        """공고 목록 수집. 실패 시 [] 반환. 절대 가짜 데이터 금지."""

    def get_detail(self, url: str) -> JobRecord | None:
        """단일 공고 상세 정보 수집"""
```

### JobRecord 스키마

```python
class JobRecord(BaseModel):
    id: str                    # 16자 SHA-256 stable ID (중복 제거 키)
    source_url: str            # 원본 공고 URL
    source_channel: str        # 수집 채널 (예: "linkareer")
    source_tier: int           # 채널 Tier (1~5)
    org: str                   # 기업/기관명
    title: str                 # 공고 제목
    archetype: str | None      # INTERN / ENTRY / EXPERIENCED / KDA_COHORT / BLOCKCHAIN_INTERN
    deadline: datetime | None  # 마감일 (자동 파싱)
    legitimacy_tier: str       # T1(공식) ~ T5(미확인)
    description: str           # 공고 본문
    location: str | None       # 근무 지역
    fit_grade: str | None      # A~F 채점 결과
    status: str                # inbox / applied / passed / rejected
    scanned_at: datetime       # 수집 시각
```

### 3-tier Selector Fallback

포털의 HTML 구조가 바뀌어도 수집이 끊기지 않도록 3단계 fallback 전략을 사용합니다:

```
1. PRIMARY      → 포털 특화 CSS selector (안정적, 빠름)
       ↓ 0개 반환 시
2. HREF 패턴   → a[href*='/recruit/'] 등 URL 패턴 매칭
       ↓ 0개 반환 시
3. GENERIC      → "채용"/"모집"/"공고" 포함 anchor 전수 스캔
```

링커리어처럼 Next.js SPA인 경우:
```
1. __NEXT_DATA__ JSON 파싱 (가장 안정적)
       ↓ 실패 시
2. [class*='Card'], [class*='List'] 와일드카드 CSS
       ↓ 실패 시
3. href 패턴 + generic scan
```

---

## 다른 사람도 사용 가능한가?

**네, 완전히 가능합니다.** User Layer와 System Layer가 엄격히 분리되어 있습니다.

```
System Layer (엔진 — 건드릴 필요 없음)
├── career_ops_kr/channels/*.py   # 212개 채널/기관 엔트리 스크레이퍼
├── career_ops_kr/cli.py          # CLI 커맨드
└── career_ops_kr/pipeline.py     # 오케스트레이션

User Layer (본인 것으로 교체)
├── cv.md                         # 이력서 (마크다운)
├── config/profile.yml            # 이름/학력/관심직종/우대조건
├── config/portals.yml            # 어떤 채널을 켤지
└── config/scoring_weights.yml    # 채점 가중치 (금융 도메인 가중치 등)
```

**사용 시나리오 예시**:

| 사용자 | profile.yml 수정 | 달라지는 점 |
|--------|-----------------|-------------|
| 금융권 취준생 | 금융/핀테크 키워드 강화 | 증권사·은행 공고 A등급 우선 |
| IT 개발자 | 백엔드/프론트 키워드 | 원티드/링커리어 개발 공고 집중 |
| 공공기관 지망 | 공기업/공공 키워드 | jobalio/yw_work24 채널 우선 |

---

## 사용자 설정 방법

### config/profile.yml

```yaml
name: "홍길동"
university: "서울대학교"
major: "경영학과"
grade: "3학년"
gpa: 3.8

target_domains:
  - "금융"
  - "핀테크"
  - "블록체인"

preferred_archetypes:
  - "INTERN"
  - "ENTRY"

location_preference: "서울"

certifications:
  - name: "CFA Level 1"
    status: "studying"
  - name: "SQLD"
    status: "planned"
```

### config/portals.yml

```yaml
portals:
  - name: "링커리어"
    key: "linkareer"
    enabled: true       # false → scan 시 제외
    priority: 1

  - name: "사람인"
    key: "saramin"
    enabled: true
    priority: 2
    filters:
      keyword_include:  # 이 키워드 포함 공고만 저장
        - "금융"
        - "핀테크"
      keyword_exclude:  # 이 키워드 포함 공고 제외
        - "영업직"
```

---

## 설치 방법

### 방법 1: uv (권장)

```bash
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
pip install uv
uv sync
```

### 방법 2: pip

```bash
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
pip install -e ".[dev]"
```

### Windows 주의사항

```powershell
# PowerShell에서 실행
$env:PYTHONIOENCODING="utf-8"
uv run career-ops status

# 또는 한 번에
$env:PYTHONIOENCODING="utf-8"; uv run career-ops scan --all
```

---

## 일반적인 워크플로우

```
매일 09:00 (자동 — scripts/auto_scan.ps1 → Windows 작업 스케줄러)
      │
      ▼
career-ops scan --all        # 전체 채널 레지스트리 스캔 → 신규 공고 수집
      │
      ▼
career-ops batch              # inbox 공고 배치 채점 + SQLite 저장
      │
      ▼
career-ops web                # Streamlit 대시보드 오픈 (localhost:8501)
  ├─ 섹터 퀵필터: 🏦금융 | 🏛️공공 | 🛡️안보 | 💳핀테크
  ├─ 등급 필터: A/B/C/D/F
  ├─ 자격충족만 필터 (기본값 ON)
  └─ 적합도순/마감순/최신순 정렬
      │
      ▼
career-ops filter <URL>       # 지원 자격 판정
career-ops interview-prep <URL>  # 면접 준비
      │
      ▼
수동 지원 (자동 제출 없음 — 영구 수동 원칙)
```

### Windows 자동 스케줄러 설정

```powershell
# scripts/auto_scan.ps1 실행 (매일 09:00 자동 스캔)
scripts\setup_scheduler.ps1

# 수동 실행 (테스트)
scripts\auto_scan.ps1
```

---

## 개발 / 테스트

```bash
# 전체 테스트 자산 확인 (609 collected)
uv run pytest --collect-only -q

# 핵심 회귀 테스트
uv run pytest tests/test_ai_ranker.py tests/test_mcp_server.py tests/test_cmd_batch.py -q

# 전체 테스트 실행
uv run pytest -q

# 특정 채널 테스트
uv run pytest tests/test_linkareer_channel.py -v
uv run pytest tests/test_kiwoom_kda_channel.py -v

# 린터
uv run ruff check .
uv run ruff format --check .
```

### 새 채널 추가하기

```
1. career_ops_kr/channels/my_portal.py    # BaseChannel 상속, list_jobs() 구현
2. tests/test_my_portal_channel.py        # _FakeResponse + monkeypatch 패턴
3. career_ops_kr/channels/__init__.py     # CHANNEL_REGISTRY에 등록
4. config/portals.yml                    # 포털 항목 추가
```

기존 구현체 `saramin.py`, `linkareer.py`, `kiwoom_kda.py`를 템플릿으로 사용하세요.

---

## 현재 상태 (2026-04-13)

| 항목 | 현황 |
|------|------|
| 버전 | **v1.0.0** |
| 채널 | **212개 엔트리** (`CHANNEL_REGISTRY`) |
| 기관 DB | **201개** 금융기관 |
| CLI 커맨드 | **28개** (`career-ops web` 추가) |
| Backend | requests 전용 (Playwright 의존 0) |
| Tests | **609 collected** |
| CI | GitHub Actions ubuntu/windows x py3.11/3.12 |
| 공개 | [pollmap/career-ops-kr](https://github.com/pollmap/career-ops-kr) (MIT) |
| 대시보드 | Streamlit 화이트 테마 + 섹터 퀵필터 (금융/공공/안보/핀테크) |

### 주요 채널 수집 성능

| 채널 | 수집량 | 방식 |
|------|--------|------|
| 링커리어 | ~156건/회 | Next.js CSS 와일드카드 + 금융12키워드 |
| 사람인 | ~320건/회 | 금융 8키워드 × 3페이지 |
| 원티드 | ~100건/회 | JSON API (안정적) |
| 잡코리아 | ~60건/회 | HTML 파싱 |

---

## 레퍼런스

- [santifer/career-ops](https://github.com/santifer/career-ops) — 원본 설계 철학 참고
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — 채널 아키텍처 패턴

## 라이선스

MIT — see [LICENSE](LICENSE).
