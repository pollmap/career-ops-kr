# career-ops-kr (한국어 전체판)

> 한국형 AI 구직 자동화 에이전트 — `santifer/career-ops` 의 철학을 한국 금융/핀테크/블록체인
> 시장에 맞춰 포팅. User/System 레이어 분리 덕분에 금융 밖 도메인으로도 확장 가능.
>
> Luxon AI 프로젝트 · Claude Code 기반 · Python 단일 스택 · v0.2.0

---

## 왜 만들었나 — 창업자의 맥락

이 도구는 **Luxon AI 창업자 이찬희**가 본인의 실제 구직 필요로 만든 도구입니다.
충북대 경영학과 3학년 1학기, 휴학생, 자격증 5개 병행, 하반기 인턴 준비 중이라는 상황에서:

- `dataq.or.kr`, `license.kofia.or.kr`, 링커리어 등 주요 한국 사이트가 **동적 로딩 + 로그인 벽**이라 LLM 단독으로는 수집 불가
- 프로그램마다 "휴학생 가능 / 비전공 가능 / 졸업예정자 요건" 조건이 제각각 → 자격 판정이 반복 노동
- 74개 타겟 프로그램 × 9개 포털을 주 단위로 수동 폴링하는 건 비현실적
- 구직을 **파이프라인으로 운영**해야 생존 가능하다는 판단

본인이 쓰려고 만들었고, 실전에서 검증된 후 오픈소스로 공개합니다.

---

## 핵심 특징

- **16개 Claude Code 모드 (v0.2)**
  - **Phase 1 (MVP)**: `scan` · `filter` · `score` · `pipeline` · `tracker` · `patterns` · `auto-pipeline`
  - **Phase 2**: `pdf` · `interview-prep` · `apply` · `followup` · `project` · `batch`
  - **Phase 3**: `training` · `deep` · `contacto`
  - **한국 로컬라이제이션**: `modes/kr/*`
- **9 + 9 채널** (MVP 9 + Sprint 3 에 스텁 9 추가)
  - MVP: 링커리어 · 잡알리오 · 청년일경험포털 · 신한투자증권 · 키움 KDA · 금투협 · dataq · 한국은행 · 원티드
- **Pluggable Channel 아키텍처** — RSS/API/requests → Scrapling → Playwright 우선순위
- **Scrapling 통합 레이어** (Sprint 2) — adaptive scraping
- **7개 도메인 프리셋**: finance · dev · design · marketing · research · public · edu
- **User / System 데이터 레이어 분리** — 시스템 업데이트 시 유저 파일 보존
- **HITL 5게이트** — 자동 제출 영구 금지, 중요 결정마다 확인 필수
- **Obsidian Vault + SQLite 이중 저장**
- **Discord 푸시 알림** — HERMES 봇 경유 `#luxon-jobs`
- **MCP 서버 래퍼** — 10 도구를 Nexus MCP 에 편입 가능
- **Textual TUI 대시보드** — 터미널에서 파이프라인 시각화
- **LLM 2차 스코어러** — D~B 중간 등급의 모호함 해소

---

## 도메인 지원 / Generalization

career-ops-kr 은 원래 찬희의 **한국 금융 도메인**용이지만, `CLAUDE.md` 가 강제하는
**User / System 레이어 분리** 덕분에 엔진(`career_ops_kr/`) 을 그대로 두고 프리셋만 바꿔
금융 밖 도메인에 쓸 수 있습니다.

| preset_id | 도메인 | 대표 포털 | 주요 archetype |
|-----------|--------|-----------|----------------|
| `finance` | 금융/핀테크/블록체인 (기본값) | 링커리어·잡알리오·dataq·한국은행·금투협 | 블록체인·금융IT·리서치·핀테크 |
| `dev` | 소프트웨어 엔지니어 | 원티드·프로그래머스·점핏·잡코리아·로켓펀치 | 백엔드·프론트엔드·데브옵스·ML |
| `design` | UX/UI·프로덕트 | 원티드·디자이너스·노트폴리오 | UX·UI·프로덕트·비주얼 |
| `marketing` | 디지털 마케팅·그로스 | 원티드·슈퍼루키·사람인 | 퍼포먼스·콘텐츠·브랜드·그로스 |
| `research` | 리서치·데이터 분석 | 한국은행·KDI·dataq·KOSSDA | 경제·정책·데이터사이언스 |
| `public` | 공공/정부/청년정책 | 잡알리오·나라일터·청년일경험 | 공공기관·정부·공기업 |
| `edu` | 교육·에듀테크·연구조교 | 학교 공고·에듀윌·원티드 | 연구조교·튜터·에듀테크 |

---

## 설치 / Installation

```bash
# Windows 11
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
uv sync
uv run playwright install chromium
uv run career-ops --help
```

---

## 사용법 / Usage

```bash
# 프리셋 목록 확인
career-ops init --list-presets

# 도메인 선택해 초기화
career-ops init --preset dev
career-ops init --preset research
career-ops init --preset finance  # 기본값 (플래그 생략 시 동일)

# 하루 스캔 (MVP 흐름)
career-ops scan
career-ops filter
career-ops pipeline

# Phase 2
career-ops interview-prep
career-ops pdf
career-ops followup

# MCP 서버 (Nexus 편입용)
python -m career_ops_kr.mcp_server

# TUI 대시보드
career-ops ui
```

---

## 배포 모델

- **본인 사용**: 찬희 로컬 (Windows 11) — 금융 프리셋
- **팀 내부**: Luxon AI 팀원이 git clone 후 `--preset <자기 도메인>`
- **오픈소스**: `presets/*.yml` PR 기반 기여

---

## 참고

- [generalization.md](generalization.md) — 도메인 일반화 원리
- [presets.md](presets.md) — 프리셋 카탈로그
- [adding-a-preset.md](adding-a-preset.md) — 새 프리셋 만드는 법
- `../CLAUDE.md` — 에이전트 작업 규칙 (User/System 분리, HITL 게이트)
- `../CONTRIBUTING.md` — 기여 가이드
- `../CHANGELOG.md` — 변경 이력

## 레퍼런스

- [santifer/career-ops](https://github.com/santifer/career-ops) — 원본 철학
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — Channel 패턴

## 라이선스

MIT © 2026 이찬희 (Luxon AI)
