# career-ops-kr 완전 기술 문서

> **버전**: v0.2.0 · **작성**: 2026-04-12 · **대상**: 찬희 (Luxon AI)
>
> 이 문서는 career-ops-kr 레포지토리 전체 — 파일 하나, 함수 하나, 데이터 흐름 하나도 빠짐없이 —
> 수석 아키텍트 관점에서 해부한 기술 레퍼런스다.

---

## 목차

0. [30초 요약](#0-30초-요약)
1. [프로젝트 정체성 & 가치](#1-프로젝트-정체성--가치)
2. [전체 아키텍처 조감도](#2-전체-아키텍처-조감도)
3. [디렉터리 & 파일 구조 전체 해부](#3-디렉터리--파일-구조-전체-해부)
4. [기술 스택 & 의존성 지도](#4-기술-스택--의존성-지도)
5. [데이터 계층 완전 해부](#5-데이터-계층-완전-해부)
6. [핵심 워크플로우 & 시퀀스 다이어그램](#6-핵심-워크플로우--시퀀스-다이어그램)
7. [모듈별 세부 엔지니어링](#7-모듈별-세부-엔지니어링)
8. [API / 인터페이스 명세](#8-api--인터페이스-명세)
9. [설정 & 환경변수 완전 가이드](#9-설정--환경변수-완전-가이드)
10. [현황 & 완성도 진단](#10-현황--완성도-진단)
11. [사용 방법 — 완전 초보자용 가이드](#11-사용-방법--완전-초보자용-가이드)
12. [타인에게 소개하는 방법](#12-타인에게-소개하는-방법)
13. [확장 & 기여 가이드](#13-확장--기여-가이드)
14. [로드맵 제안](#14-로드맵-제안)

---

## 0. 30초 요약

**career-ops-kr**는 충북대 경영학 3학년 재학생(찬희)이 한국 금융·블록체인·핀테크 인턴 공고를
자동으로 **수집 → 자격 판정 → 10차원 채점 → SQLite 저장 → Discord 알림 → AI 지원 보조**
까지 처리하는 구직 자동화 파이프라인이다.

```
[212개 한국 채용 채널/기관 엔트리]
      ↓  CHANNEL_REGISTRY
[QualifierEngine]  ← 학력/전공 자격 필터 (PASS/CONDITIONAL/FAIL)
      ↓
[FitScorer]        ← 10차원 가중합 → A~F 학점
      ↓
[SQLiteStore]      ← WAL 모드 SQLite, 상태 추적
      ↓
[CLI 27개 커맨드]  ← click + rich (터미널)
[MCP 10개 도구]   ← Nexus MCP 에이전트 인터페이스
[TUI 대시보드]    ← textual 기반 시각화
[Discord Notifier] ← 마감 알림 / 요약 리포트
```

한 줄 설치 후 `career-ops scan --all` 한 번이면 전체 파이프라인이 돌아간다.

---

## 1. 프로젝트 정체성 & 가치

### 1.1 왜 만들었나

찬희는 2026년 상반기에 **블록체인 인턴 → 금융 IT 인턴 → 핀테크 인턴** 순서로 취업 트랙을
밟고 있다. 문제는:

- 한국 채용 채널/기관 엔트리가 **212개** 이상 분산돼 있어 매일 수동 탐색이 불가능
- 공고마다 "졸업예정자 지원 불가", "이공계 전공 필수" 같은 **자격 요건 함정**이 숨어 있음
- 적합도를 직관으로만 판단 → 지원 우선순위가 불명확
- 마감일 관리 실패 → 기회 손실

이 문제를 해결하기 위해 career-ops-kr를 설계했다.

### 1.2 핵심 철학 세 가지

| 철학 | 의미 | 구현 포인트 |
|------|------|-------------|
| **실데이터 절대 원칙** | 목업/추정/할루시네이션 금지 | 크롤링 실패 → `fetch_errors` 저장, 추정값 생성 금지 |
| **HITL 5게이트** | 제출은 반드시 찬희가 직접 | G5 = 영구 수동, `webbrowser.open()` 절대 금지 |
| **User/System 계층 분리** | 개인정보/설정 파일 수정 금지 | `config/` = User 레이어, `career_ops_kr/**` = System 레이어 |

### 1.3 santifer/career-ops와의 차이

원본 프로젝트(santifer/career-ops)를 **한국 특화**로 이식한 파생 프로젝트다.

| 항목 | 원본 career-ops | career-ops-kr |
|------|-----------------|---------------|
| 채용 포털 | 해외 범용 | 한국 212개 채널/기관 엔트리 특화 |
| 자격 판정 | 영어 키워드 | 한국어 정규식 ("학력무관", "재학생 지원 가능") |
| 채점 archetype | 직군 중립 | 찬희 맞춤 8개 (BLOCKCHAIN, DIGITAL_ASSET, RESEARCH 등) |
| 언어 | 영어 | 한국어 (CLI 출력, 모드 파일) |
| MCP 통합 | 없음 | 10개 도구 (Nexus MCP 에이전트 연동) |
| AI 지원 | 없음 | interview-prep / followup / project 커맨드 |

---

## 2. 전체 아키텍처 조감도

### 2.1 레이어 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                        인터페이스 레이어                          │
│                                                                   │
│  CLI (click)      TUI (textual)     MCP Server (stdio/FastMCP)   │
│  27개 커맨드       4개 화면          10개 도구                     │
│  career-ops *     career-ops ui     python -m career_ops_kr.mcp  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        커맨드 레이어                              │
│                                                                   │
│  commands/_shared.py     commands/filter_cmd.py                  │
│  commands/auto_pipeline  commands/batch_cmd.py                   │
│  commands/notify_cmd     commands/apply_cmd.py                   │
│  commands/interview_cmd  commands/followup_cmd.py                │
│  commands/project_cmd    commands/patterns_cmd.py                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                        엔진 레이어                                │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Qualifier   │  │  FitScorer   │  │  ArchetypeClassifier │   │
│  │  Engine      │  │  10차원 채점  │  │  8개 아키타입 분류   │   │
│  │  PASS/COND/  │  │  A~F 학점    │  │  키워드+가중치       │   │
│  │  FAIL        │  │              │  │                      │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  AI Ranker   │  │  AI Clients  │  │  Notifier            │   │
│  │  (ai/ranker) │  │  (ai/client) │  │  (Discord webhook)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Patterns    │  │  PresetLoader│  │  CalendarExporter    │   │
│  │  Analyzer    │  │  YAML→config │  │  ICS 출력            │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    채널 레이어 (212개 엔트리)                     │
│                                                                   │
│  BaseChannel (ABC + retry/rate-limit)                            │
│  ├── linkareer / saramin / jobkorea / wanted / incruit           │
│  ├── rocketpunch / jumpit / rallit / programmers                 │
│  ├── jobalio / jobalio_susis / catch_intern                      │
│  ├── kakao_pay / kakao_bank / toss / dunamu                      │
│  ├── hana_bank / shinhan_bank / kb / woori / nh                 │
│  ├── kdb / ibk / kfb                                             │
│  └── kotra / kised / kipf / kibo                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                       데이터 레이어                               │
│                                                                   │
│  SQLiteStore (data/jobs.db)    VaultSync (Obsidian 미러링)        │
│  ├── jobs 테이블                ├── upsert_note()                 │
│  ├── scan_log 테이블            ├── move_note()                   │
│  └── 4개 인덱스 (WAL 모드)      └── write_index()                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름 (정상 경로)

```
URL 또는 채널 목록
    │
    ▼
[BaseChannel.list_jobs()] ─────────────────────────────► fetch_errors 저장
    │ JobRecord
    ▼
[ArchetypeClassifier.classify(title+description)]
    │ archetype: BLOCKCHAIN | FINTECH | ...
    ▼
[QualifierEngine.evaluate(job_text)]
    │ QualifierResult: verdict + reasons + confidence
    │
    ├── Verdict.FAIL ──► FitGrade.F 자동, 이후 처리 중단
    │
    ▼
[FitScorer.score(job, qresult, archetype)]
    │ ScoreBreakdown: {dimension_scores, total, grade, reasons}
    │
    ▼
[SQLiteStore.upsert(job, fit)]
    │ jobs 테이블에 INSERT OR UPDATE
    │
    ▼
[CLI 출력 / Discord 알림 / TUI 표시 / MCP 응답]
```

---

## 3. 디렉터리 & 파일 구조 전체 해부

```
career-ops-kr/
│
├── career_ops_kr/                  ← Python 패키지 루트
│   │
│   ├── __init__.py                 ← 빈 (네임스페이스만)
│   ├── cli.py                      ← Click CLI 진입점 (800+ 줄)
│   │                                  _register_commands() + 기존 score/scan/etc
│   ├── mcp_server.py               ← MCP 서버 (10개 도구 + stdio/FastMCP 이중 지원)
│   │
│   ├── commands/                   ← Sprint 6~9 신규 커맨드 서브패키지
│   │   ├── __init__.py
│   │   ├── _shared.py              ← console, CONFIG_DIR, DATA_DIR, 공유 헬퍼
│   │   ├── filter_cmd.py           ← career-ops filter
│   │   ├── auto_pipeline.py        ← career-ops auto-pipeline
│   │   ├── batch_cmd.py            ← career-ops batch (asyncio + Windows 호환)
│   │   ├── notify_cmd.py           ← career-ops notify
│   │   ├── apply_cmd.py            ← career-ops apply (G5 영구 수동)
│   │   ├── interview_cmd.py        ← career-ops interview-prep
│   │   ├── followup_cmd.py         ← career-ops followup
│   │   ├── project_cmd.py          ← career-ops project
│   │   └── patterns_cmd.py         ← career-ops patterns
│   │
│   ├── channels/                   ← 채용 포털 채널 레이어
│   │   ├── __init__.py             ← CHANNEL_REGISTRY dict 노출
│   │   ├── base.py                 ← JobRecord, BaseChannel, Channel 프로토콜
│   │   ├── linkareer.py
│   │   ├── saramin.py
│   │   ├── jobkorea.py
│   │   ├── wanted.py
│   │   ├── incruit.py
│   │   ├── rocketpunch.py
│   │   ├── jumpit.py
│   │   ├── rallit.py
│   │   ├── programmers.py
│   │   ├── jobalio.py
│   │   ├── jobalio_susis.py
│   │   ├── catch_intern.py
│   │   ├── kakao_pay.py
│   │   ├── kakao_bank.py
│   │   ├── toss.py
│   │   ├── dunamu.py
│   │   ├── hana_bank.py
│   │   ├── shinhan_bank.py
│   │   ├── kb.py
│   │   ├── woori.py
│   │   ├── nh.py
│   │   ├── kdb.py
│   │   ├── ibk.py
│   │   ├── kfb.py
│   │   ├── kotra.py
│   │   ├── kised.py
│   │   ├── kipf.py
│   │   └── kibo.py
│   │
│   ├── qualifier/                  ← 자격 판정 엔진
│   │   ├── __init__.py             ← QualifierResult, Verdict 노출
│   │   └── engine.py               ← QualifierEngine (4단계 결정 트리)
│   │
│   ├── scorer/                     ← 적합도 채점 엔진
│   │   ├── __init__.py
│   │   └── fit_score.py            ← FitScorer (10차원 가중합, A~F 학점)
│   │
│   ├── archetype/                  ← 직군 분류기
│   │   ├── __init__.py             ← Archetype enum 노출
│   │   └── classifier.py           ← ArchetypeClassifier
│   │
│   ├── parser/                     ← 파싱 유틸리티
│   │   ├── __init__.py
│   │   └── utils.py                ← parse_korean_date, coerce_to_date,
│   │                                   clean_html, generate_job_id,
│   │                                   extract_eligibility_keywords
│   │
│   ├── storage/                    ← 영속성 레이어
│   │   ├── __init__.py
│   │   ├── sqlite_store.py         ← SQLiteStore (WAL, idempotent 스키마)
│   │   └── vault_sync.py           ← VaultSync (Obsidian Vault 미러링)
│   │
│   ├── notifier/                   ← 알림 레이어
│   │   ├── __init__.py
│   │   └── discord_push.py         ← DiscordNotifier (webhook 기반)
│   │
│   ├── calendar/                   ← ICS 캘린더 내보내기
│   │   ├── __init__.py
│   │   └── ics_export.py           ← CalendarExporter
│   │
│   ├── ai/                         ← AI 지원 모듈
│   │   ├── __init__.py
│   │   ├── client.py               ← OpenRouter 클라이언트 (OpenAI 호환)
│   │   ├── ranker.py               ← RankedJob + rank_jobs() (네트워크 없음)
│   │   ├── scorer.py               ← AI 채점 (LLM 기반, 선택적)
│   │   ├── summarizer.py           ← AI 요약 생성
│   │   ├── interview.py            ← STAR 면접 질문 생성 (fallback 포함)
│   │   ├── followup.py             ← 후속 이메일 초안 (fallback 포함)
│   │   └── project.py              ← 포트폴리오 스프린트 제안 (fallback 포함)
│   │
│   ├── patterns/                   ← 패턴 분석 (MCP tool_run_patterns 자동 활성화)
│   │   ├── __init__.py             ← analyze() 노출
│   │   └── analyzer.py             ← analyze(days) → 통계 dict
│   │
│   ├── presets/                    ← 프리셋 번들 로더
│   │   ├── __init__.py
│   │   └── loader.py               ← PresetLoader, Preset pydantic 모델
│   │
│   └── tui/                        ← Textual TUI 대시보드
│       ├── __init__.py
│       ├── app.py                  ← CareerOpsApp, HelpScreen, MissingDbScreen
│       ├── screens.py              ← DashboardScreen, JobsListScreen,
│       │                              JobDetailScreen, CalendarScreen
│       └── styles.tcss             ← Textual CSS
│
├── config/                         ← [User 레이어] 찬희 개인화 설정
│   ├── profile.yml                 ← 개인 프로필 (학점, 나이, 타겟 산업 등)
│   ├── qualifier_rules.yml         ← 자격 판정 규칙 (negative/positive 패턴)
│   ├── scoring_weights.yml         ← 채점 가중치 + grade_cuts
│   ├── archetypes.yml              ← 8개 아키타입 정의
│   └── portals.yml                 ← 포털 구독 목록
│
├── data/                           ← [User 레이어] 런타임 데이터
│   ├── jobs.db                     ← SQLite DB (자동 생성)
│   └── applications.md             ← 지원 현황 마크다운 테이블
│
├── modes/                          ← [User/System 혼합] Claude 모드 파일
│   ├── _shared.md                  ← 모든 모드 공통 컨텍스트 (System)
│   ├── _profile.md                 ← 찬희 개인 내러티브 (User, 수정 금지)
│   ├── _profile.template.md        ← _profile.md 템플릿 (System)
│   ├── score.md                    ← score 모드 프롬프트
│   ├── scan.md                     ← scan 모드 프롬프트
│   └── ...                         ← 기타 모드 파일
│
├── presets/                        ← 도메인 프리셋 번들
│   └── finance_kr.yml              ← 한국 금융 특화 프리셋
│
├── templates/                      ← 초기화 템플릿
│   ├── profile.example.yml
│   └── portals.example.yml
│
├── tests/                          ← pytest 테스트 스위트
│   ├── conftest.py
│   ├── test_channels_*.py          ← 채널별 테스트
│   ├── test_qualifier_engine.py
│   ├── test_fit_scorer.py
│   ├── test_archetype_classifier.py
│   ├── test_sqlite_store.py
│   ├── test_mcp_server.py
│   ├── test_cmd_filter.py          ← Sprint 6~9 신규 테스트 9개
│   ├── test_cmd_auto_pipeline.py
│   ├── test_cmd_batch.py
│   ├── test_cmd_notify.py
│   ├── test_cmd_apply.py
│   ├── test_cmd_interview.py
│   ├── test_cmd_followup.py
│   ├── test_cmd_project.py
│   └── test_cmd_patterns.py
│
├── scripts/                        ← 유지보수 스크립트
│   ├── dedup.py
│   ├── merge.py
│   ├── normalize.py
│   └── verify.py
│
├── docs/                           ← 문서
│   ├── ARCHITECTURE.md             ← 이 파일
│   ├── README.ko.md
│   ├── README.en.md
│   ├── README.ja.md
│   ├── presets.md
│   ├── adding-a-preset.md
│   ├── generalization.md
│   └── llm_cost_profile.md
│
├── output/                         ← [자동 생성] AI 커맨드 출력물
│   ├── interview_<org>_<date>.md
│   ├── followup_<org>_<stage>_<date>.md
│   └── portfolio_<org>_<date>.md
│
├── cv.md                           ← [User 레이어] 찬희 이력서
├── pyproject.toml                  ← uv 패키지 설정 (Python 3.11+)
├── CLAUDE.md                       ← Claude Code 에이전트 지침
└── .python-version                 ← 3.11 고정
```

---

## 4. 기술 스택 & 의존성 지도

### 4.1 런타임 의존성

```
pyproject.toml [project.dependencies]
│
├── 웹 스크래핑
│   ├── playwright ≥1.40        ← JS 렌더링 채널 (catch_intern 등)
│   ├── requests ≥2.31          ← 단순 HTTP GET 채널
│   └── beautifulsoup4 ≥4.12   ← HTML 파싱
│
├── CLI / TUI
│   ├── click ≥8.1              ← CLI 커맨드 시스템
│   ├── rich ≥13.7              ← 컬러 출력, Panel, Table, Progress
│   └── textual ≥0.47           ← [선택적] TUI 대시보드
│
├── 데이터 모델
│   └── pydantic ≥2.0           ← JobRecord, ScoreBreakdown, QualifierResult 등
│
├── AI / LLM
│   └── openai ≥1.10            ← OpenRouter 호환 (base_url 변경)
│
├── ICS 캘린더
│   └── ics ≥0.7                ← .ics 파일 생성
│
├── 설정 파일
│   └── pyyaml ≥6.0             ← config/*.yml 파싱
│
└── stdlib 활용
    ├── sqlite3                  ← DB (의존성 없음)
    ├── asyncio                  ← batch 비동기 처리
    ├── pathlib                  ← 모든 파일 경로
    ├── re                       ← 정규식 (qualifier, scorer)
    └── json                     ← MCP 프로토콜 직렬화
```

### 4.2 개발 의존성

```
[project.optional-dependencies.dev]
├── pytest, pytest-cov, pytest-asyncio  ← 테스트
├── ruff                                ← 린터
└── mypy                                ← 타입 체커
```

### 4.3 외부 서비스

| 서비스 | 용도 | 필수 여부 |
|--------|------|-----------|
| OpenRouter API | AI 커맨드 (interview/followup/project) | 선택 (fallback 있음) |
| Discord Webhook | notify 커맨드 알림 | 선택 (log-only 모드 가능) |
| 각 채용 포털 | 크롤링 대상 | 필수 (스캔 시) |

### 4.4 의존성 격리 원칙

- 모든 `import`는 try/except로 감싸고 `None` 반환 → **부분 실패 시에도 서버 기동**
- `_safe_import(dotted, attr)` 패턴이 `mcp_server.py` 전체에 적용됨
- `textual`은 `tui/__init__.py`에서만 임포트 → TUI 미설치 시 나머지 CLI 영향 없음

---

## 5. 데이터 계층 완전 해부

### 5.1 JobRecord (핵심 DTO)

**파일**: `career_ops_kr/channels/base.py:54`

```python
class JobRecord(BaseModel):
    id: str              # SHA-256[:16] — 안정적 중복 제거 키
    source_url: HttpUrl  # pydantic v2 URL 검증
    source_channel: str  # "linkareer", "saramin" 등
    source_tier: int     # 1(공식) ~ 6(미확인), ge=1, le=6
    org: str             # 채용 기관
    title: str           # 공고 제목
    archetype: str|None  # 분류 결과 (ArchetypeClassifier 출력)
    deadline: date|None  # 마감일
    posted_at: date|None
    location: str|None
    description: str     # HTML 제거된 본문
    raw_html: str|None   # 재파싱용 원본 HTML
    legitimacy_tier: str # "T1"~"T5" (기본값 "T5")
    scanned_at: datetime # 스캔 시각 (UTC naive)
    fetch_errors: list[str]  # 비치명적 오류 목록
```

### 5.2 SQLite 스키마

**파일**: `career_ops_kr/storage/sqlite_store.py:23`

```sql
-- 메인 공고 테이블
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source_url TEXT NOT NULL UNIQUE,     -- UNIQUE → 중복 URL 자동 차단
    source_channel TEXT NOT NULL,
    source_tier INTEGER NOT NULL,
    org TEXT NOT NULL,
    title TEXT NOT NULL,
    archetype TEXT,
    deadline TEXT,                       -- ISO-8601 "YYYY-MM-DD"
    posted_at TEXT,
    location TEXT,
    description TEXT,
    legitimacy_tier TEXT DEFAULT 'T5',
    scanned_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'inbox', -- inbox|applying|graded|rejected|archived
    fit_grade TEXT,                       -- A|B|C|D|F
    fit_score REAL,
    eligible TEXT,                        -- "true"|"false"
    fetch_errors TEXT                     -- JSON array
);

-- 스캔 이력 로그
CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    channel TEXT NOT NULL,
    count INTEGER NOT NULL,
    errors TEXT                           -- JSON array
);

-- 성능 인덱스 4개
CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_fit_grade ON jobs(fit_grade);
CREATE INDEX IF NOT EXISTS idx_jobs_deadline  ON jobs(deadline);
CREATE INDEX IF NOT EXISTS idx_jobs_channel   ON jobs(source_channel);
```

**PRAGMA 설정**:
- `PRAGMA foreign_keys = ON` — 외래키 강제
- `PRAGMA journal_mode = WAL` — Write-Ahead Logging, 읽기/쓰기 동시성 향상

**Upsert 전략**: `INSERT ... ON CONFLICT(id) DO UPDATE SET`  
- `status`는 기존 값 보존 (`COALESCE`)
- `fit_grade`, `fit_score`, `eligible`도 기존 값 보존 (NULL 덮어쓰기 방지)
- 재스캔 시 메타데이터 갱신, 사용자 입력 유지

### 5.3 SQLiteStore API

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `upsert` | `(job: JobRecord, fit: Any) → bool` | 삽입 또는 갱신, True=신규 |
| `list_by_grade` | `(grade: str) → list[dict]` | 학점 필터, score 내림차순 |
| `list_upcoming_deadlines` | `(days: int = 7) → list[dict]` | N일 이내 마감 목록 |
| `search` | `(keyword: str, archetype: str) → list[dict]` | 제목/설명/기관 LIKE, 최대 200건 |
| `get_stats` | `() → dict` | total, by_status, by_grade, recent_scans |
| `log_scan` | `(channel: str, count: int, errors) → None` | scan_log 기록 |
| `set_status` | `(job_id: str, status: str) → bool` | 상태 변경, True=변경됨 |

### 5.4 User/System 계층 분리

```
config/profile.yml         ← 찬희 수동 관리 (GPA, 나이, 타겟 산업)
config/qualifier_rules.yml ← 찬희 수동 관리 (자격 판정 규칙)
config/scoring_weights.yml ← 찬희 수동 관리 (채점 가중치)
config/archetypes.yml      ← 찬희 수동 관리 (아키타입 정의)
─────────────────────────────────────────────────────────────
career_ops_kr/**/*.py      ← 시스템 자동 업데이트 가능
modes/_shared.md           ← 시스템 자동 업데이트 가능
templates/*.yml            ← 시스템 자동 업데이트 가능
```

**핵심 규칙**: 엔진 업데이트 시 `config/`는 절대 변경하지 않는다. 프리셋 `apply_to(overwrite=False)` 기본값도 같은 이유.

---

## 6. 핵심 워크플로우 & 시퀀스 다이어그램

### 6.1 score 워크플로우 (가장 핵심)

```
사용자: career-ops score https://linkareer.com/job/12345
         │
         ▼
cli.py: score_cmd()
         │
         ├─[1]─► tool_score_job(url)
         │           │
         │           ├─ CHANNEL_REGISTRY 순회
         │           │      └─ cls().get_detail(url) → JobRecord
         │           │
         │           ├─ QualifierEngine.evaluate(description)
         │           │      └─ QualifierResult {verdict, reasons, confidence}
         │           │
         │           └─ FitScorer.score(job, qresult, archetype)
         │                  └─ ScoreBreakdown {total, grade, dimension_scores}
         │
         └─[2]─► print_standard_report(evaluation, console)
                    │
                    └─ Panel 출력:
                       URL / Legitimacy / Archetype / Fit Grade / Eligibility / Deadline
```

### 6.2 scan 워크플로우

```
career-ops scan [--all] [--tier N] [--site NAME]
         │
         ▼
cli.py: scan_cmd()
         │
         ├─ G4 게이트: 5건 이상 → Confirm.ask()
         │
         ├─ CHANNEL_REGISTRY 순회 (필터 적용)
         │      └─ channel.list_jobs() → list[JobRecord]
         │
         ├─ ArchetypeClassifier.classify() per job
         │
         ├─ QualifierEngine.evaluate() per job
         │
         ├─ FitScorer.score() per job
         │
         └─ SQLiteStore.upsert(job, fit) per job
                └─ scan_log 기록
```

### 6.3 auto-pipeline 워크플로우

```
career-ops auto-pipeline [--grade A] [--notify] [--dry-run]
         │
         ▼
auto_pipeline.py
         │
         ├─[dry-run]─► 설정 검증만, 네트워크 없음
         │
         ├─ CHANNEL_REGISTRY 직접 순회 (tool_scan_jobs는 count만 반환 → 직접 접근 필요)
         │      └─ cls().list_jobs() → source_url 목록 수집
         │
         ├─ G4 게이트: 5건 이상 → Confirm.ask("계속 진행?")
         │
         ├─ 샘플 1건 tool_score_job() → print_standard_report()
         │      └─ Confirm.ask("전체 진행?")
         │
         ├─ Progress bar: tool_score_job(url) per job (--limit 건)
         │      └─ grade_ge(result.grade, min_grade) → SQLiteStore.upsert()
         │
         └─ [--notify] → DiscordNotifier.notify_batch_summary()
```

### 6.4 batch 워크플로우 (비동기)

```
career-ops batch [--limit 50] [--concurrency 3] [--status inbox]
         │
         ▼
batch_cmd.py
         │
         ├─ SQLite direct query → status 필터 → inbox 목록 (limit 그대로 유지)
         │
         ├─ G4 게이트: 5건 이상
         │
         └─ asyncio.run(_batch_main(inbox, concurrency, store))
                │
                ├─ asyncio.Semaphore(concurrency)     ← 동시 채점 수 제한
                ├─ loop.run_in_executor(None, tool_score_job, url)  ← Windows 호환
                └─ gather() → 결과 수집 → store.upsert(fit=...) + store.set_status("graded")
```

### 6.5 interview-prep 워크플로우

```
career-ops interview-prep URL [--no-ai] [--questions 5] [--save PATH]
         │
         ▼
interview_cmd.py
         │
         ├─[1]─► tool_score_job(url) → evaluation dict
         │
         ├─[2]─► load_profile() → profile dict
         │
         ├─[3]─► get_ai_client_or_fallback()
         │           ├─[AI 있음]─► generate_interview_questions(evaluation, profile, client, model, n)
         │           │                  └─ LLM → [{"question": str, "star_guide": {"S","T","A","R": str}}]
         │           └─[AI 없음 / --no-ai]─► _fallback_star_template(evaluation, n)
         │                                    └─ archetype별 기본 5개 질문 (deterministic)
         │
         └─[4]─► STAR 패널 출력 (S=green, T=yellow, A=cyan, R=blue)
                  [--save] → output/interview_<org>_<date>.md
```

---

## 7. 모듈별 세부 엔지니어링

### 7.1 QualifierEngine

**파일**: `career_ops_kr/qualifier/engine.py`

4단계 결정 트리 (순서 엄수):

```
Step 1: 하드 네거티브 (regex 14개)
        "졸업예정자", "이공계 전공 필수", "경력 N년 이상"
        → 매치 시 즉시 FAIL (confidence=0.9)

Step 2: 수치 FAIL 체크 (numeric_verdict)
        - 6학기 이상 → FAIL (찬희 4학기 수료)
        - 학점 X.X 이상 + 찬희 GPA 2.9 → FAIL
        - 만 N세 이하 + 찬희 24세 → FAIL
        ※ Step 3 이전에 수치 FAIL 체크 → "청년 인턴" 포지티브보다 선행

Step 3: 하드 포지티브 (regex 15개)
        "학력 무관", "재학생 지원 가능", "내일배움카드"
        → 매치 시 즉시 PASS (confidence=0.9)

Step 4a: 수치 PASS (4학기 이하 요건 충족)
         → PASS 반환

Step 4b: 컨텍스트 힌트 (regex 5개)
         "수시 채용", "경력 우대", "코딩 테스트"
         → CONDITIONAL (confidence=0.6)

Default: CONDITIONAL (confidence=0.4, "명시적 요건 없음")
```

**YAML 커스터마이징**: `config/qualifier_rules.yml`  
`negative`, `positive`, `conditional` 배열 → 런타임 로드. 없으면 하드코딩 defaults 사용.

### 7.2 FitScorer

**파일**: `career_ops_kr/scorer/fit_score.py`

10차원 가중합 채점 엔진:

| 차원 | 가중치 | 로직 |
|------|--------|------|
| `role_fit` | 20 | ARCHETYPE_PREFERENCE dict lookup (BLOCKCHAIN=100, UNKNOWN=40) |
| `eligibility_match` | 20 | PASS=100, CONDITIONAL=60, FAIL→전체 F 자동 |
| `compensation` | 10 | 월 280만+→100, 220만+→85, 180만+→70, 100만+→50, 미확인→50 |
| `location` | 10 | 서울/안산/청주→100, 수도권→80, 지방 광역시→50, 재택/원격→90 |
| `growth` | 10 | 정규직전환/교육연계 키워드 수: 3+→100, 2→80, 1→60, 0→40 |
| `brand` | 10 | 한국은행/금감원/4대 은행→100, 빗썸/두나무/Hashed→80, 기타→50 |
| `portfolio_usefulness` | 10 | Python/SQL/LLM/블록체인 등 15개 키워드 매칭 수 |
| `schedule_conflict` | 5 | ADsP/한국사/SQLD/금투사/투운사 시험 ±3일 충돌→40, 안전→90 |
| `deadline_urgency` | 3 | D-3이내→100, D-7→90, D-14→75, D-30→60, 기타→50 |
| `hitl_discretion` | 2 | 기본 0, job["hitl_bonus"]로 찬희 직접 부여 |

**Grade Cutoff** (config/scoring_weights.yml 참조):
- A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, F < 40

**FAIL 자동 처리**: `qualifier_result.verdict == FAIL` → 전 차원 0점, `FitGrade.F` 즉시 반환.

### 7.3 ArchetypeClassifier

**파일**: `career_ops_kr/archetype/classifier.py`

8개 아키타입:

| Archetype | 설명 | 핵심 키워드 예시 |
|-----------|------|------------------|
| BLOCKCHAIN | 블록체인/Web3 | "블록체인", "Web3", "DeFi", "NFT", "스마트컨트랙트" |
| DIGITAL_ASSET | 디지털자산/거래소 | "가상자산", "코인", "업비트", "빗썸" |
| CERTIFICATION | 자격증/시험 | "ADsP", "CFA", "SQLD", "한국사" |
| PUBLIC_FINANCE | 공공/공기업 금융 | "한국거래소", "예탁결제원", "공공기관" |
| RESEARCH | 리서치/퀀트 | "리서치", "퀀트", "백테스트", "데이터분석" |
| FINTECH_PRODUCT | 핀테크 | "토스", "카카오페이", "카카오뱅크", "핀테크" |
| FINANCIAL_IT | 금융 IT | "금융IT", "코어뱅킹", "레거시", "Java" |
| UNKNOWN | 미분류 | (기타) |

동점 시 `_break_tie()`: 특수 키워드(KDA_COHORT, BLOCKCHAIN_INTERN 등) 우선.

### 7.4 BaseChannel

**파일**: `career_ops_kr/channels/base.py`

```
BaseChannel(ABC)
├── _RateLimiter                ← token-bucket 방식, 분당 N회 제한
├── _retry(fn, max_attempts=4)  ← 지수 백오프 (2^n + random), max 120s
├── _make_id(url, title)        ← SHA-256[:16], parser.utils.generate_job_id 위임
├── check() → bool              ← [abstract] 업스트림 도달 가능 여부
├── list_jobs() → list[JobRecord]  ← [abstract] 공고 목록
└── get_detail(url) → JobRecord|None  ← [abstract] 상세 정보
```

**실패 정책**: 4회 재시도 후에도 실패 → `None` / `[]` 반환. 절대 `raise`하지 않음.  
**fetch_errors**: 비치명적 오류는 `JobRecord.fetch_errors`에 append.

### 7.5 MCP Server

**파일**: `career_ops_kr/mcp_server.py`

10개 MCP 도구:

| MCP 도구명 | 내부 함수 | 설명 |
|-----------|-----------|------|
| `career_ops_scan_jobs` | `tool_scan_jobs(tier, site)` | 채널 스캔, count summary |
| `career_ops_score_job` | `tool_score_job(url)` | URL → 완전 평가 dict |
| `career_ops_list_eligible` | `tool_list_eligible(grade)` | 최소 grade 이상 목록 (`C`면 `A/B/C`) |
| `career_ops_get_deadline_calendar` | `tool_get_deadline_calendar(days)` | N일 이내 마감 |
| `career_ops_query_by_archetype` | `tool_query_by_archetype(archetype)` | 아키타입 필터 |
| `career_ops_generate_cover_letter_draft` | `tool_generate_cover_letter_draft(url, tone)` | 커버레터 초안 |
| `career_ops_run_patterns` | `tool_run_patterns(days)` | 패턴 분석 |
| `career_ops_verify_pipeline` | `tool_verify_pipeline()` | 파이프라인 헬스체크 |
| `career_ops_apply_preset` | `tool_apply_preset(preset_id)` | 프리셋 적용 |
| `career_ops_get_stats` | `tool_get_stats()` | DB 통계 |

2026-04-13 live verification snapshot:

- `career_ops_get_stats()` → `total=446`, `graded=446`
- `career_ops_list_eligible("C")` → `353` (`A/B/C` 포함)
- `career_ops_list_eligible("D")` → `398`
- `career_ops_query_by_archetype("GENERAL")` → `24`
- `career_ops_scan_jobs(site="saramin")` → `320`

**트랜스포트 이중화**:
1. FastMCP (`pip install mcp`) → 우선 시도
2. 최소 stdio JSON-RPC (폴백) → 의존성 없이 MCP 2024-11-05 프로토콜 지원

**등록 방법** (VPS `~/.mcp.json`):
```json
{
  "mcpServers": {
    "career-ops-kr": {
      "command": "python",
      "args": ["-m", "career_ops_kr.mcp_server"],
      "cwd": "/root/career-ops-kr"
    }
  }
}
```

### 7.6 ai/ranker.py

**파일**: `career_ops_kr/ai/ranker.py`

네트워크 없이 순수 계산 기반 랭킹:

```python
@dataclass
class RankedJob:
    job: JobRecord
    fit_score: int           # AI 채점 0~100
    fit_reason: str
    urgency_bonus: int       # D-2이내=+25, D-5=+20, D-10=+15
    archetype_bonus: int     # KDA_COHORT=+20, BLOCKCHAIN_INTERN=+18
    legitimacy_bonus: int    # T1=+5, T2=+3
    total_score: int         # min(100, fit + urgency + archetype + legitimacy)
    summary: str             # AI 요약 (표시용)
```

`rank_jobs(jobs, fit_scores, summaries, today, top_n=5)` → `list[RankedJob]` 내림차순.

### 7.7 commands/_shared.py

**파일**: `career_ops_kr/commands/_shared.py`

CLI 커맨드 간 공유 헬퍼:

```python
console = Console()                    # rich Console 싱글톤
PROJECT_ROOT = Path.cwd()             # 프로세스 시작 시 CWD
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
MODES_DIR = PROJECT_ROOT / "modes"

def print_standard_report(evaluation: dict, con: Console) -> None:
    """CLAUDE.md 표준 6줄 Panel 출력 (URL/Legitimacy/Archetype/Grade/Eligibility/Deadline)."""

def get_ai_client_or_fallback(api_key: str|None, con: Console) -> tuple[Any|None, str|None]:
    """OpenRouter 클라이언트 반환, 실패 시 (None, None) + 경고."""

def load_profile() -> dict:
    """config/profile.yml 로드, 없으면 {}."""

def get_store() -> SQLiteStore|None:
    """data/jobs.db SQLiteStore 반환, 없으면 None."""

def grade_ge(grade: str, min_grade: str) -> bool:
    """grade >= min_grade 비교 (A > B > C > D > F)."""
```

**circular import 방지**: `cli.py`에서 임포트하지 않음. `Path.cwd()`는 프로세스 시작 시 한 번만 실행되므로 `mcp_server.py`의 `PROJECT_ROOT`와 동일한 경로 보장.

### 7.8 patterns/analyzer.py

**파일**: `career_ops_kr/patterns/analyzer.py`

```python
def analyze(days: int = 30) -> dict:
    """Returns:
        {
          "days": int,
          "period": {"from": str, "to": str},
          "total_analyzed": int,
          "by_status": {"inbox": n, "applying": n, ...},
          "by_grade": {"A": n, "B": n, ...},
          "by_archetype": {"BLOCKCHAIN": n, ...},
          "rejection_rate": float,   # rejected / (applying + rejected)
          "avg_days_to_deadline": float,
          "top_orgs": [{"org": str, "count": n}, ...],
          "patterns": [str, ...]     # deterministic 인사이트 문장
        }
    """
```

**MCP 자동 활성화**: `mcp_server.py`의 `_safe_import("career_ops_kr.patterns")`가 이 패키지를 찾으면 `tool_run_patterns`가 실제 분석을 실행. 패키지 없으면 `{"status": "not_implemented"}` 반환.

---

## 8. API / 인터페이스 명세

### 8.1 CLI 전체 커맨드 목록

```
career-ops --help

Commands:
  score          단일 URL 채점 + 표준 리포트 출력
  scan           포털 스캔 + SQLite 저장
  list           저장된 공고 목록 조회
  rank           Top-N 공고 AI 랭킹
  ai-rank        AI 채점 + 진행 표시 랭킹
  init           온보딩 (G1 게이트)
  status         tracker 상태 확인
  export         ICS 캘린더 내보내기
  ui             Textual TUI 대시보드 실행
  filter         단일 텍스트/URL 자격 판정
  auto-pipeline  전체 스캔→채점→저장 파이프라인
  batch          DB inbox 비동기 배치 채점
  notify         Discord 알림 (--test / --summary)
  apply          지원 체크리스트 + G5 수동 강조
  interview-prep STAR 면접 질문 생성
  followup       후속 이메일 초안 생성
  project        포트폴리오 스프린트 계획
  patterns       지원 패턴 분석 리포트
```

### 8.2 주요 커맨드 시그니처

```bash
# 채점
career-ops score URL [--save PATH] [--json]

# 스캔
career-ops scan [--all] [--tier INT] [--site TEXT] [--limit INT] [--dry-run]

# 랭킹
career-ops rank [--top INT] [--grade TEXT]
career-ops ai-rank [--top INT] [--grade TEXT] [--max-jobs INT] [--model TEXT]

# 필터
career-ops filter TEXT [--url URL] [--file PATH] [--json] [--confidence]

# 파이프라인
career-ops auto-pipeline [--tier INT] [--site TEXT] [--limit INT] [--grade TEXT] [--notify] [--dry-run]

# 배치
career-ops batch [--limit INT] [--concurrency INT] [--status TEXT] [--dry-run]

# 알림
career-ops notify [--test] [--grade TEXT] [--days INT] [--webhook URL] [--summary]

# 지원
career-ops apply URL

# AI 지원 도구
career-ops interview-prep URL [--questions INT] [--model TEXT] [--api-key TEXT] [--no-ai] [--save PATH]
career-ops followup URL [--stage applied|interviewed|rejected] [--tone TEXT] [--no-ai] [--save PATH]
career-ops project URL [--weeks INT] [--no-ai] [--save PATH]

# 패턴
career-ops patterns [--days INT] [--json]

# 초기화
career-ops init [--preset TEXT]
```

### 8.3 tool_score_job 반환 스키마

모든 CLI AI 커맨드와 MCP 도구가 공유하는 표준 평가 dict:

```json
{
  "url": "https://linkareer.com/job/12345",
  "channel": "linkareer",
  "org": "두나무",
  "title": "블록체인 리서치 인턴",
  "archetype": "BLOCKCHAIN_INTERN",
  "legitimacy": "T1",
  "deadline": "2026-06-30",
  "qualifier_verdict": "PASS",
  "grade": "A",
  "total_score": 88.5,
  "reasons": [
    "role_fit=100 (BLOCKCHAIN)",
    "eligibility=100 (PASS)",
    "학력 무관",
    "재학생 지원 가능"
  ]
}
```

오류 시: `{"error": "메시지", "hint": "pip install -e ."}`

### 8.4 analyze() 반환 스키마

```json
{
  "days": 30,
  "period": {"from": "2026-03-13", "to": "2026-04-12"},
  "total_analyzed": 42,
  "by_status": {"inbox": 15, "applying": 20, "rejected": 7},
  "by_grade": {"A": 3, "B": 8, "C": 12, "ungraded": 19},
  "by_archetype": {"BLOCKCHAIN": 10, "FINTECH": 8, "RESEARCH": 6},
  "rejection_rate": 0.35,
  "avg_days_to_deadline": 12.4,
  "top_orgs": [{"org": "두나무", "count": 4}, {"org": "토스", "count": 3}],
  "patterns": [
    "블록체인 공고가 가장 많습니다 (10건)",
    "지원율 47.6% — 목표치보다 낮습니다",
    "거절율 35.0% — 서류 경쟁 전략 재검토 권장"
  ]
}
```

---

## 9. 설정 & 환경변수 완전 가이드

### 9.1 config/profile.yml (핵심 User 파일)

```yaml
# 찬희 개인 프로필 — 모든 엔진이 이 파일 참조
name: 이찬희
age: 24
gpa:
  value: 2.9
  scale: 4.5
birth:
  age: 24              # QualifierEngine 나이 체크에 사용
education:
  status: enrolled     # enrolled | leave | graduated
  semester: 4          # 수료 학기 (QualifierEngine 학기수 체크)
  major: business_admin

target_industries:
  - blockchain
  - fintech
  - financial_it
  - research

preferred_locations:
  - 서울
  - 안산
  - 청주

strengths:
  - Python
  - 데이터분석
  - 금융이해
  - 블록체인 기초

# FitScorer school_type 차원에서 참조
school:
  name: 충북대학교
  tier: regional_public

# DiscordNotifier webhook
discord:
  webhook_url: ""      # --webhook 없을 때 fallback

# AI 클라이언트
ai:
  api_key: ""          # OPENROUTER_API_KEY 환경변수 우선
  model: "google/gemini-2.0-flash-exp:free"
```

### 9.2 config/scoring_weights.yml

```yaml
grade_cuts:
  A: 85     # 이상 → A
  B: 70     # 이상 → B
  C: 55     # 이상 → C
  D: 40     # 이상 → D
  E: 25     # (enum에 E 없음 → F로 fold)
  F: 0

weights:
  role_fit: 20
  eligibility_match: 20
  compensation: 10
  location: 10
  growth: 10
  brand: 10
  portfolio_usefulness: 10
  schedule_conflict: 5
  deadline_urgency: 3
  hitl_discretion: 2    # 합계: 100

exam_dates:             # schedule_conflict 충돌 체크용
  - 2026-05-17    # ADsP 49
  - 2026-05-23    # 한국사 78
  - 2026-05-31    # SQLD 61
  - 2026-07-12    # 금투사 24
  - 2026-08-23    # 투운사 46
```

### 9.3 환경변수

| 환경변수 | 용도 | 기본값 |
|----------|------|--------|
| `OPENROUTER_API_KEY` | AI 커맨드 LLM 호출 | (없으면 fallback 템플릿) |
| `DISCORD_WEBHOOK_URL` | notify 커맨드 webhook | (없으면 log-only 모드) |
| `CAREER_OPS_DB_PATH` | 커스텀 DB 경로 | `data/jobs.db` |
| `PYTHONIOENCODING` | Windows 출력 인코딩 | 실행 시 `utf-8` 권장 |

### 9.4 presets/finance_kr.yml

도메인 특화 프리셋 번들. `career-ops init --preset finance_kr` 실행 시 `config/*.yml` 파일 자동 생성.

```yaml
preset_id: finance_kr
label_ko: 한국 금융 특화
label_en: Korean Finance
description: 블록체인/디지털자산/핀테크/금융IT/리서치 특화

qualifier_rules:
  negative_patterns: [...]
  positive_patterns: [...]
  numeric_rules:
    min_semester_completed: 2
    max_gpa_required: 3.5

scoring_weights:
  dimensions:
    role_fit: 0.20
    eligibility_match: 0.20
    # ...합계 1.00

portals:
  - {name: linkareer, url: ..., backend: requests, tier: 3}
  # ...27개 포털

archetypes:
  BLOCKCHAIN: {label: "블록체인/Web3 인턴"}
  # ...8개

profile_template:
  target_industries: [blockchain, fintech, ...]
  default_strengths: [Python, 데이터분석, ...]
  suggested_certifications: [ADsP, SQLD, ...]
```

---

## 10. 현황 & 완성도 진단

### 10.1 Phase 별 완성도

| Phase | 기능 | 완성도 | 비고 |
|-------|------|--------|------|
| MVP (v0.1) | 채널 27개 + Qualifier + FitScorer + SQLite + scan/score/list CLI | ✅ 100% | 449 green tests (Sprint 5) |
| Phase 2 (v0.2) | filter/auto-pipeline/batch/notify/apply/interview-prep/followup/project/patterns | ✅ 100% | Sprint 6~9 완료 |
| Phase 2 보조 | MCP 10도구 + TUI 대시보드 + AI ranker + PresetLoader | ✅ 100% | |
| Phase 3 (v1.0) | TUI 패턴 화면 + 74개 포털 + 오픈소스 배포 | 🔧 부분 | TUI 패턴 화면 stub |

### 10.2 테스트 커버리지

```
tests/ 총 테스트: 609 collected (2026-04-13 기준)
─────────────────────────────────────────────────────────
채널 테스트:         test_channels_*.py (채널당 ~5개)
엔진 테스트:         test_qualifier_engine.py, test_fit_scorer.py
분류기 테스트:       test_archetype_classifier.py
DB 테스트:          test_sqlite_store.py
MCP 테스트:         test_mcp_server.py
커맨드 테스트:      test_cmd_*.py (9개 파일 × ~7개 = 63개)
```

**빠른 실행**:
```bash
uv run pytest -q --tb=short          # 전체
uv run pytest tests/test_cmd_*.py -v # 신규 커맨드만
```

### 10.3 알려진 제한사항

| 항목 | 현황 | 영향 |
|------|------|------|
| TUI 패턴 화면 | `"v0.3 예정"` 알림만 | 낮음 (CLI `patterns` 커맨드로 대체 가능) |
| `ai/scorer.py`, `ai/summarizer.py` | 존재하나 `ai-rank` 커맨드에서만 사용 | 낮음 |
| `VaultSync` | 구현 완료, CLI 노출 없음 | 낮음 |
| `CalendarExporter` | `career-ops export`로 노출, ICS 생성 | 없음 |
| Windows asyncio event loop | `ProactorEventLoop` 경고 가능 | `run_in_executor` 패턴으로 완화 |

### 10.4 ruff 린트 상태

```bash
uv run ruff check career_ops_kr/
# 목표: 0 errors, warnings 최소화
```

---

## 11. 사용 방법 — 완전 초보자용 가이드

### 11.1 설치

```bash
# 1. 클론
git clone https://github.com/pollmap/career-ops-kr
cd career-ops-kr

# 2. uv 설치 (없으면)
pip install uv

# 3. 의존성 설치
uv sync

# 4. playwright 브라우저 설치 (JS 채널용)
uv run playwright install chromium

# 5. 동작 확인
PYTHONIOENCODING=utf-8 uv run career-ops --help
```

### 11.2 첫 실행 순서 (온보딩)

```bash
# Step 1: 프리셋 초기화 (config/*.yml 자동 생성)
uv run career-ops init --preset finance_kr

# Step 2: profile.yml 직접 편집 (학점, 나이 등 개인 정보 입력)
notepad config/profile.yml

# Step 3: 파이프라인 헬스체크
uv run career-ops verify  # MCP tool_verify_pipeline 호출

# Step 4: 첫 스캔 (dry-run으로 먼저)
PYTHONIOENCODING=utf-8 uv run career-ops scan --dry-run --limit 5

# Step 5: 실제 스캔
PYTHONIOENCODING=utf-8 uv run career-ops scan --all --limit 50
```

### 11.3 일상적 사용 흐름

```bash
# 매일 아침: 새 공고 스캔
PYTHONIOENCODING=utf-8 uv run career-ops scan --all

# 특정 URL 빠르게 채점
PYTHONIOENCODING=utf-8 uv run career-ops score https://linkareer.com/job/12345

# A등급 공고 목록
PYTHONIOENCODING=utf-8 uv run career-ops list --grade A

# 지원 준비 (체크리스트 + G5 강조)
PYTHONIOENCODING=utf-8 uv run career-ops apply https://linkareer.com/job/12345

# 면접 준비 (AI 없이)
PYTHONIOENCODING=utf-8 uv run career-ops interview-prep https://... --no-ai --save output/prep.md

# 패턴 분석 (30일)
PYTHONIOENCODING=utf-8 uv run career-ops patterns

# TUI 대시보드 실행
PYTHONIOENCODING=utf-8 uv run career-ops ui
```

### 11.4 Discord 알림 설정

```bash
# .env 또는 직접 설정
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

# 연결 테스트
uv run career-ops notify --test

# A등급 공고 + 7일 이내 마감 알림
uv run career-ops notify --grade A --days 7

# 일일 요약 알림
uv run career-ops notify --summary
```

### 11.5 MCP 에이전트에서 사용 (Nexus/HERMES)

```python
# HERMES/NEXUS 에이전트에서 career-ops-kr 도구 호출 예시
result = mcp.call("career_ops_score_job", {"url": "https://..."})
# → {"grade": "A", "total_score": 88, "archetype": "BLOCKCHAIN_INTERN", ...}

stats = mcp.call("career_ops_get_stats", {})
# → {"total": 156, "by_status": {...}, "by_grade": {...}}
```

---

## 12. 타인에게 소개하는 방법

### 12.1 엘리베이터 피치 (30초)

> "한국 채용 채널 212개 엔트리를 자동으로 수집해서, 학력/전공 자격 필터로 걸러내고,
> 10개 차원으로 A~F 학점을 매겨서 SQLite에 저장하는 구직 자동화 파이프라인입니다.
> Discord 알림, MCP 에이전트 연동, AI 면접 준비까지 되어 있고,
> 사용자 설정 파일은 시스템이 절대 건드리지 않는 HITL 철학으로 설계했습니다."

### 12.2 기술 면접관에게 (아키텍처 설명)

이 프로젝트에서 기술적으로 흥미로운 결정 4가지:

1. **User/System 계층 분리**: `config/`는 사용자 전용, `career_ops_kr/**`는 시스템 전용.
   프리셋 업데이트가 사용자 데이터를 절대 덮어쓰지 않도록 `apply_to(overwrite=False)` 기본값 설계.

2. **MCP 이중 트랜스포트**: FastMCP가 없어도 stdlib만으로 MCP 2024-11-05 프로토콜 구현.
   `_safe_import` 패턴으로 broken subpackage가 서버 기동을 막지 않음.

3. **QualifierEngine 결정 트리 순서**: 하드 네거티브 → 수치 FAIL → 하드 포지티브 순서가
   "청년 인턴(포지티브)"이 "만 22세 이하(수치 FAIL)"보다 먼저 평가되는 버그를 방지.

4. **Windows asyncio 호환**: `batch_cmd`에서 `loop.run_in_executor(None, tool_score_job, url)` 패턴으로
   동기 함수를 async 컨텍스트에서 안전하게 실행. `ProactorEventLoop` 이슈 우회.

### 12.3 같은 상황의 취업 준비생에게

- 이 코드를 **포크**하면 본인 학교/학점/선호 산업으로 바꾸는 데 `config/profile.yml` 하나만 편집하면 됨
- 채널 추가는 `BaseChannel`을 상속하고 `CHANNEL_REGISTRY`에 등록하면 끝
- AI 기능은 선택적 — OpenRouter 키 없어도 전체 파이프라인 동작

---

## 13. 확장 & 기여 가이드

### 13.1 새 채널 추가

```python
# career_ops_kr/channels/mynewportal.py
from career_ops_kr.channels.base import BaseChannel, JobRecord

class MyNewPortal(BaseChannel):
    name = "mynewportal"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 5

    def check(self) -> bool:
        import requests
        try:
            r = requests.get("https://mynewportal.co.kr", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_jobs(self, query=None) -> list[JobRecord]:
        # 크롤링 로직
        jobs = []
        # ... _retry(fn) 감싸기 권장
        return jobs

    def get_detail(self, url: str) -> JobRecord | None:
        # 상세 크롤링
        return None
```

```python
# career_ops_kr/channels/__init__.py에 등록
from career_ops_kr.channels.mynewportal import MyNewPortal
CHANNEL_REGISTRY["mynewportal"] = MyNewPortal
```

### 13.2 새 아키타입 추가

1. `career_ops_kr/archetype/classifier.py`의 `Archetype` enum에 추가
2. `config/archetypes.yml`에 키워드 + 가중치 추가
3. `scorer/fit_score.py`의 `ARCHETYPE_PREFERENCE`에 점수 추가
4. `ai/interview.py`의 `_ARCHETYPE_BASE_QUESTIONS`에 기본 질문 추가
5. `ai/project.py`의 `_ARCHETYPE_SPRINT_DEFAULTS`에 스프린트 계획 추가

### 13.3 새 MCP 도구 추가

```python
# mcp_server.py의 TOOL_SPECS에 추가
{
    "name": "career_ops_my_new_tool",
    "description": "...",
    "inputSchema": {
        "type": "object",
        "properties": {"param": {"type": "string"}},
        "required": ["param"],
    },
    "fn": lambda args: my_new_function(args["param"]),
},
```

### 13.4 AI 모듈 개선

`ai/interview.py`, `ai/followup.py`, `ai/project.py` 모두 동일한 패턴:
- `generate_*()` → LLM 호출 시도
- `_fallback_*()` → 실패 시 archetype 기반 deterministic 템플릿
- 항상 `exit_code=0` 보장

LLM 프롬프트 품질 개선은 `generate_*()` 내부 `system_prompt` / `user_prompt` 문자열만 수정하면 됨.

### 13.5 기여 시 체크리스트

- [ ] `encoding='utf-8'` 모든 파일 I/O에 명시
- [ ] 새 파일 800줄 이하
- [ ] 실데이터 원칙 — 추정값 생성 금지
- [ ] `uv run pytest -q` 통과
- [ ] `uv run ruff check career_ops_kr/` 통과
- [ ] User 레이어 파일 (`config/`, `data/`, `modes/_profile.md`) 미변경

---

## 14. 로드맵 제안

### Phase 3 (v1.0) — 오픈소스 준비

| 우선순위 | 항목 | 예상 작업량 |
|---------|------|-------------|
| P0 | TUI 패턴 분석 화면 구현 (현재 stub) | ~200줄 |
| P0 | 포털 27개 → 74개 확장 | 채널당 ~80줄 |
| P1 | `VaultSync`를 CLI 커맨드로 노출 (`career-ops vault-sync`) | ~50줄 |
| P1 | Windows 작업 스케줄러 자동 등록 (`career-ops schedule --daily`) | ~100줄 |
| P2 | `ai-rank` 결과 → Discord 일일 리포트 자동화 | ~80줄 |
| P2 | `.env` 파일 지원 (python-dotenv) | ~10줄 |

### Phase 4 — Luxon 통합

| 항목 | 설명 |
|------|------|
| HERMES 에이전트 연동 | MCP로 `career_ops_score_job` 자동 호출 → 일일 브리핑 |
| NEXUS Vault 미러링 | `VaultSync.write_index()` → Obsidian 연동 |
| KIS 백테스터 | `archetype=RESEARCH` 공고 → 실제 퀀트 프로젝트 제안 매핑 |
| 스마트폰 알림 | Discord → 모바일 푸시 (기존 NEXUS 채널 재사용) |

### 성능 최적화 후보

| 항목 | 현황 | 개선안 |
|------|------|--------|
| 채널 스캔 속도 | 순차 처리 | `asyncio.gather` + `run_in_executor` 병렬화 |
| SQLite 성능 | 단건 upsert | `executemany` 배치 삽입 |
| 패턴 분석 | 매번 전체 조회 | `scanned_at` 인덱스 추가 |

---

> 이 문서는 `career_ops_kr` v0.2.0 기준이다. 새 버전에서 변경된 내용은 이 파일을 직접 업데이트하거나
> `docs/ARCHITECTURE.md` PR을 통해 기여하면 된다.
