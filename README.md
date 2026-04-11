# career-ops-kr

[![CI](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml/badge.svg)](https://github.com/pollmap/career-ops-kr/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> 한국형 AI 구직 자동화 에이전트 — `santifer/career-ops`의 철학을 한국 금융/핀테크/블록체인 시장에 맞춰 포팅.
>
> Luxon AI 프로젝트 · Claude Code 기반 · Python 단일 스택

## 왜 만드는가

- `dataq.or.kr`, `license.kofia.or.kr`, 링커리어 등 주요 한국 사이트가 **동적 로딩 + 로그인 벽**이라 LLM 단독으로 수집 불가
- 프로그램마다 "휴학생 가능 / 비전공 가능 / 졸업예정자 요건" 조건이 제각각 → 자격 판정이 반복 노동
- 74개 타겟 프로그램 × 9개 포털을 주 단위로 수동 폴링하는 건 비현실적
- **자격증 5개 + KDA 프로그램 + 하반기 인턴 준비를 병행하는 상황에서 구직을 파이프라인으로 운영해야 한다**

## 핵심 특징

- **7개 Claude Code 모드** (MVP): `scan` · `filter` · `score` · `pipeline` · `tracker` · `patterns` · `auto-pipeline`
- **9개 한국 포털 커버** (MVP): 링커리어 · 잡알리오 · 청년일경험포털 · 신한투자증권 · 키움 KDA · 금투협 · dataq · 한국은행 · 원티드
- **Pluggable Channel 아키텍처** — RSS/API/requests 우선, Playwright는 4개 어려운 포털에만
- **User / System 데이터 레이어 분리** — 시스템 업데이트 시 유저 커스터마이징 보존
- **HITL 5게이트** — 자동 제출 영구 금지, 모든 중요 결정에 찬희 확인 필수
- **Obsidian Vault + SQLite 이중 저장** — Vault가 단일 진실원, SQLite는 인덱스
- **Discord 푸시 알림** — HERMES 봇 경유 `#luxon-jobs` 채널

## 도메인 지원 / Generalization

career-ops-kr은 원래 찬희의 **한국 금융 도메인**용으로 만들어졌지만, `CLAUDE.md`가 강제하는 **User / System 레이어 분리 구조** 덕분에 금융 밖의 도메인으로도 그대로 배포할 수 있다. 한 엔진(`career_ops_kr/`)에 **도메인 프리셋**만 갈아 끼우면 된다.

### 지원 도메인 (v0.1)

| preset_id | 도메인 | 대표 포털 / 데이터 소스 | 주요 archetype |
|-----------|--------|------------------------|----------------|
| `finance` | 금융/핀테크/블록체인 (기본값) | 링커리어·잡알리오·dataq·한국은행·금투협 | 블록체인·금융IT·리서치·핀테크 |
| `dev` | 소프트웨어 엔지니어 | 원티드·프로그래머스·점핏·잡코리아·로켓펀치 | 백엔드·프론트엔드·데브옵스·ML엔지니어 |
| `design` | UX/UI·프로덕트 디자인 | 원티드·디자이너스·노트폴리오·프로그래머스 | UX·UI·프로덕트·비주얼 |
| `marketing` | 디지털 마케팅·그로스 | 원티드·슈퍼루키·사람인 | 퍼포먼스·콘텐츠·브랜드·그로스 |
| `research` | 리서치·데이터 분석 | 한국은행·KDI·잡알리오·dataq·KOSSDA | 경제리서치·정책·데이터사이언스 |
| `public` | 공공/정부/청년정책 | 잡알리오·나라일터·청년일경험·공공기관경영정보 | 공공기관·정부부처·공기업 |
| `edu` | 교육·에듀테크·연구조교 | 학교 공고·에듀윌·원티드·링커리어 | 연구조교·튜터·에듀테크·커리큘럼 |

> 7개 프리셋은 모두 동일한 엔진(`career_ops_kr/`)을 공유하며, 차이는 `config/*.yml` + `modes/_profile.md` 뿐이다.

### 사용법

```bash
# 프리셋 목록 확인
career-ops init --list-presets

# 도메인 선택해 초기화
career-ops init --preset dev       # 소프트웨어 엔지니어
career-ops init --preset research  # 리서치/데이터
career-ops init --preset finance   # 금융 (기본 — 플래그 없이 `init`만 써도 같음)

# 기존 config 덮어쓰기
career-ops init --preset design --force

# 플래그 없이 기존 인터랙티브 플로우 (하위 호환)
career-ops init
```

> `--preset` 플래그 없는 `career-ops init`은 Sprint 1 MVP와 **완전히 동일하게 동작**한다. 기존 사용자는 아무것도 바꿀 필요가 없다.

### 새 도메인 추가

새 도메인(예: `legal`, `healthcare`, `game`)을 만들고 싶다면 [docs/adding-a-preset.md](docs/adding-a-preset.md) 를 참조. 본질적으로 `presets/<domain>.yml` 하나만 작성하면 된다.

### 배포 모델

- **본인 사용**: 찬희 로컬 (`C:\Users\lch68\Desktop\career-ops-kr\`) — 금융 프리셋
- **팀 내부 배포**: Luxon AI 팀원/수강생에게 git clone 후 `--preset <자기 도메인>`
- **오픈소스 커뮤니티**: `presets/*.yml` PR 기반 기여 → Tier 1~6 포털 큐레이션 공유

자세한 원리는 [docs/generalization.md](docs/generalization.md), 프리셋 카탈로그는 [docs/presets.md](docs/presets.md) 참조.

## 레퍼런스

- [santifer/career-ops](https://github.com/santifer/career-ops) — 원본 (740+ 공고 평가 실전 검증)
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — Channel 아키텍처 패턴
- 플랜 원본: `~/.claude/plans/melodic-moseying-cupcake.md`

## 상태

- ✅ **W1 d1** (2026-04-11): 부트스트랩 완료 — 디렉토리, pyproject, CLAUDE.md, _shared.md
- ⏭ **W1 d2~d7**: User 레이어, 쉬운 채널, parser, qualifier, archetype, scorer, storage
- ⏭ **W2 d1~d7**: Playwright 채널, 모드, integrity, notifier, CLI

## 설치 (준비 중)

```bash
# Windows
cd C:\Users\lch68\Desktop\career-ops-kr
uv sync
uv run playwright install chromium
uv run career-ops --help
```

## 라이선스

MIT © 이찬희 (Luxon AI, 2026)
