# 프리셋 카탈로그 — career-ops-kr

> career-ops-kr v0.1 공식 프리셋 7종. 모두 동일한 엔진(`career_ops_kr/`)을 공유하며, 차이는 `config/*.yml` + `modes/_profile.md` 뿐이다. 새 프리셋 작성 가이드는 [adding-a-preset.md](adding-a-preset.md), 범용화 원리는 [generalization.md](generalization.md) 참조.

---

## 목록

| preset_id | 레이블 | 기본 archetype 수 | 포털 수 |
|-----------|--------|-------------------|---------|
| [`finance`](#finance--금융핀테크블록체인) | 금융/핀테크/블록체인 | 6 | 9 |
| [`dev`](#dev--소프트웨어-엔지니어) | 소프트웨어 엔지니어 | 6 | 7 |
| [`design`](#design--uxui-디자인) | UX/UI·프로덕트 디자인 | 5 | 6 |
| [`marketing`](#marketing--디지털-마케팅그로스) | 디지털 마케팅·그로스 | 5 | 5 |
| [`research`](#research--리서치데이터-분석) | 리서치·데이터 분석 | 5 | 6 |
| [`public`](#public--공공정부청년정책) | 공공/정부/청년정책 | 4 | 5 |
| [`edu`](#edu--교육에듀테크) | 교육·에듀테크 | 5 | 5 |

사용법: `career-ops init --preset <preset_id>` (기존 config 덮어쓰기는 `--force` 추가).

---

## `finance` — 금융/핀테크/블록체인

찬희 기본 프리셋 (Sprint 1 MVP). 한국 금융권 인턴/프로그램 특화.

- **용도**: 증권·자산운용·은행·핀테크·블록체인·DeFi 구직/프로그램 지원
- **타겟 직무**: IB·리서치·퀀트·리스크·디지털자산·DevOps(금융IT)·Compliance
- **주요 포털**: 링커리어 · 잡알리오 · dataq.or.kr · 한국은행 · license.kofia.or.kr · 신한투자증권 · 키움 KDA · 청년일경험포털 · 원티드
- **기본 archetype**: 블록체인 / 디지털자산 / 금융IT / 리서치 / 핀테크 / 공공
- **권장 자격증**: 투자자산운용사 · CFA L1 · ADSP · 증권투자권유자문인력 · 빅데이터분석기사
- **추천 대상**: 금융권 공채/인턴 파이프라인을 정기 운영해야 하는 학부생·휴학생·졸업예정자

예시 `config/profile.yml`:

```yaml
name: 홍길동
target_industries:
  - 금융
  - 핀테크
  - 블록체인
archetypes_enabled: [blockchain, digital_asset, fintech, finance_it, research, public]
```

사용법: `career-ops init --preset finance` (플래그 없이 그냥 `init`을 써도 동일).

---

## `dev` — 소프트웨어 엔지니어

한국 개발자 취업/이직 파이프라인.

- **용도**: 백엔드·프론트·모바일·데브옵스·ML 엔지니어 포지션 수집
- **타겟 직무**: Backend · Frontend · Full-stack · iOS/Android · DevOps/SRE · ML/AI Engineer
- **주요 포털**: 원티드 · 프로그래머스 잡 · 점핏 · 잡코리아 · 로켓펀치 · 사람인 · 링커리어
- **기본 archetype**: backend / frontend / fullstack / mobile / devops / ml_engineer
- **권장 자격증**: 정보처리기사 · AWS SAA · AWS DevOps · 빅데이터분석기사 · SQLD
- **추천 대상**: 네카라쿠배·중견 IT·스타트업 포지션을 동시에 폴링하려는 개발자

예시 `config/profile.yml`:

```yaml
name: 김개발
target_industries:
  - 소프트웨어
  - IT 서비스
  - 스타트업
archetypes_enabled: [backend, frontend, fullstack, mobile, devops, ml_engineer]
preferred_stack: [python, typescript, kotlin, aws, kubernetes]
```

사용법: `career-ops init --preset dev`

---

## `design` — UX/UI 디자인

- **용도**: 프로덕트 디자인·UX 리서치·비주얼 디자인 포지션
- **타겟 직무**: Product Designer · UX Designer · UX Writer · Visual/Brand Designer · UX Researcher
- **주요 포털**: 원티드 · 디자이너스닷컴 · 노트폴리오 · 프로그래머스 잡 · 로켓펀치 · 잡코리아
- **기본 archetype**: product_design / ux / ux_research / visual_brand / motion
- **권장 자격증**: GTQ · 컬러리스트기사 · 웹디자인기능사 (선택)
- **추천 대상**: 포트폴리오 기반 디자이너 — 공고 발견 + 마감일 추적을 자동화하고 싶은 경우

예시 `config/profile.yml`:

```yaml
name: 박디자인
target_industries:
  - 소프트웨어
  - 이커머스
  - 게임
archetypes_enabled: [product_design, ux, ux_research, visual_brand, motion]
portfolio_url: https://www.notion.so/portfolio
```

사용법: `career-ops init --preset design`

---

## `marketing` — 디지털 마케팅/그로스

- **용도**: 퍼포먼스 마케팅·콘텐츠 마케팅·그로스 해킹·브랜드 매니저
- **타겟 직무**: Performance Marketer · Content Marketer · Growth Hacker · Brand Manager · CRM
- **주요 포털**: 원티드 · 슈퍼루키 · 사람인 · 잡코리아 · 링커리어
- **기본 archetype**: performance / content / growth / brand / crm
- **권장 자격증**: 구글 애널리틱스 자격 · 메타 블루프린트 · Google Ads 인증
- **추천 대상**: 퍼포먼스·콘텐츠·브랜드 포지션을 동시에 서칭하는 마케터 — D2C/커머스/SaaS 모두 커버

예시 `config/profile.yml`:

```yaml
name: 최마케팅
target_industries:
  - 이커머스
  - D2C
  - SaaS
archetypes_enabled: [performance, content, growth, brand, crm]
preferred_tools: [ga4, meta_ads, google_ads, amplitude]
```

사용법: `career-ops init --preset marketing`

---

## `research` — 리서치/데이터 분석

한국 정책·경제·데이터 리서치 커리어 빌딩용.

- **용도**: 경제 리서치·정책 연구·데이터 분석·계량 리서치 포지션
- **타겟 직무**: Economic Research · Policy Analyst · Data Analyst · Data Scientist · 연구조교
- **주요 포털**: 한국은행 · KDI · 잡알리오 · dataq.or.kr · KOSSDA · 원티드
- **기본 archetype**: economic_research / policy / data_analyst / data_scientist / quant_research
- **권장 자격증**: 빅데이터분석기사 · ADsP · SQLD · 사회조사분석사
- **추천 대상**: 학·석사 과정 중 연구 경력을 쌓고 싶은 사회과학·경제·통계 전공자

예시 `config/profile.yml`:

```yaml
name: 윤리서치
target_industries:
  - 공공
  - 연구기관
  - 핀테크
archetypes_enabled: [economic_research, policy, data_analyst, data_scientist, quant_research]
academic_level: undergraduate
```

사용법: `career-ops init --preset research`

---

## `public` — 공공/정부/청년정책

- **용도**: 공공기관·정부부처·공기업 채용/청년 프로그램
- **타겟 직무**: 공공기관 정규직 · 청년인턴 · 공기업 체험형 · 정부부처 계약직
- **주요 포털**: 잡알리오 · 나라일터 · 청년일경험포털 · 공공기관경영정보공개시스템 · 워크넷
- **기본 archetype**: public_institution / ministry / soe / youth_experience
- **권장 자격증**: NCS 기반 직업기초능력 · 한국사능력검정 · 컴활 1급 · 토익
- **추천 대상**: 공공기관 공채 + 청년인턴 + 공기업 체험형을 한 대시보드에서 추적하고 싶은 경우

예시 `config/profile.yml`:

```yaml
name: 정공공
target_industries:
  - 공공
  - 정부
  - 공기업
archetypes_enabled: [public_institution, ministry, soe, youth_experience]
ncs_track: business_admin
```

사용법: `career-ops init --preset public`

---

## `edu` — 교육/에듀테크

- **용도**: 학교·학원·에듀테크 SaaS·연구조교·튜터·커리큘럼 디자이너
- **타겟 직무**: 연구조교 · 튜터 · 강사 · 에듀테크 PM · 커리큘럼 디자이너
- **주요 포털**: 학교 홈페이지 공고 · 에듀윌 · 원티드 · 링커리어 · 잡코리아
- **기본 archetype**: research_assistant / tutor / instructor / edtech_pm / curriculum
- **권장 자격증**: 정교사 2급 · 한국어교원 2급 · 평생교육사 · 교원자격증
- **추천 대상**: 교육 관련 파트타임/풀타임을 병렬 서칭하는 대학생·현직 교사·에듀테크 종사자

예시 `config/profile.yml`:

```yaml
name: 한에듀
target_industries:
  - 교육
  - 에듀테크
  - 출판
archetypes_enabled: [research_assistant, tutor, instructor, edtech_pm, curriculum]
teaching_level: [middle_school, high_school]
```

사용법: `career-ops init --preset edu`

---

## 다음 단계

- 새 도메인을 만들고 싶다면 → [adding-a-preset.md](adding-a-preset.md)
- 왜 하나의 엔진으로 7개 도메인이 돌아가는지 → [generalization.md](generalization.md)
- 루트 철학·5게이트 HITL → 프로젝트 루트의 `CLAUDE.md`
