# Generalization — career-ops-kr가 범용 프레임워크인 이유

> career-ops-kr은 겉보기엔 찬희 한 명의 한국 금융 구직 도구처럼 보인다. 그러나 내부 구조는 **하나의 엔진 + 갈아 끼우는 프리셋**이라는 모듈형 디자인으로, 7개 이상 도메인에 그대로 배포할 수 있다. 이 문서는 그 원리를 설명한다.
>
> 관련: [presets.md](presets.md) · [adding-a-preset.md](adding-a-preset.md) · 프로젝트 루트 `CLAUDE.md`, `README.md`

---

## 1. 핵심 아이디어 — User / System 레이어 분리

career-ops-kr의 가장 중요한 **invariant**는 `CLAUDE.md` §2 "데이터 계약"에 정의되어 있다.

> 시스템 업데이트 시 **유저 파일은 절대 수정하지 않는다.**

이는 원본 `santifer/career-ops`에서 차용한 원칙을 한국형 리팩토링에서 더 엄격하게 강제한 것이다.

### 레이어 구분표

| 파일 / 디렉토리 | 레이어 | 의미 |
|----------------|--------|------|
| `cv.md` | 🔶 User | 개인 이력서 markdown |
| `config/profile.yml` | 🔶 User | 타겟 산업/아키타입 선택 |
| `config/portals.yml` | 🔶 User | 구독 포털 목록 |
| `config/qualifier_rules.yml` | 🔶 User | 자격 판정 규칙 |
| `config/scoring_weights.yml` | 🔶 User | A~F 가중치 |
| `config/archetypes.yml` | 🔶 User | 아키타입 정의 (v0.2에서 외부화) |
| `modes/_profile.md` | 🔶 User | 개인 narrative/협상 스크립트 |
| `data/**` | 🔶 User | SQLite/applications.md |
| `modes/_shared.md` | 🔷 System | 전 모드 공통 컨텍스트 |
| `modes/_profile.template.md` | 🔷 System | User `_profile.md` 템플릿 |
| `modes/*.md` (나머지) | 🔷 System | 개별 모드 (scan/filter/score/...) |
| `templates/**` | 🔷 System | 예시 YAML/HTML |
| `scripts/**` | 🔷 System | dedup/merge/verify 스크립트 |
| `career_ops_kr/**/*.py` | 🔷 System | Python 코어 (엔진) |
| `presets/**` | 🔷 System | 프리셋 카탈로그 |

### 이 분리가 주는 힘

`git pull` → `pip install -U .`로 엔진을 업데이트해도 `config/`, `cv.md`, `modes/_profile.md`, `data/`는 **절대 덮여쓰이지 않는다**. 덕분에:

1. **같은 엔진**으로 찬희(`finance`), 개발자 팀원(`dev`), 디자이너(`design`)가 각자의 User 파일만 유지하면 된다
2. 업데이트가 두렵지 않다 → 오픈소스 배포가 안전해진다
3. **프리셋 교체**도 같은 원리 — `--preset dev`는 User 레이어를 한 번에 덮어쓰는 것이 아니라, `config/`에 새 YAML 세트를 심는 일회성 초기화다

---

## 2. 하나의 엔진이 7개 도메인을 커버하는 이유

엔진(`career_ops_kr/`)은 **도메인-무관하게** 설계되어 있다. 구체적으로:

### (a) Channel 레이어 — 포털 수집의 추상화

`career_ops_kr/channels/` 는 Panniantong/Agent-Reach 패턴을 차용한 플러거블 크롤러 집합이다:

- `base.py` — 공통 인터페이스 (`fetch` → `parse` → `yield Job`)
- 각 포털별 서브클래스 (linkareer, wanted, etc.)
- **Scrapling**(저수준 엔진)이 실제 HTTP/Playwright 호출을 담당

**핵심**: 채널은 "금융 포털만" 다루는 게 아니다. 어떤 한국 포털이든 같은 인터페이스로 붙일 수 있다. `dev` 프리셋은 원티드/점핏을, `public` 프리셋은 잡알리오/나라일터를 `portals.yml`에 나열하기만 하면 된다.

### (b) Archetype 외부화

Sprint 1까지는 archetype이 Python 코드(`career_ops_kr/archetype/`)에 있었지만, v0.2 로드맵에서 **`config/archetypes.yml`로 외부화**된다. 이렇게 되면 프리셋 YAML이 `archetypes:` 키를 통해 완전히 도메인-specific 아키타입을 선언할 수 있다.

```yaml
# 금융 프리셋
archetypes:
  - id: blockchain
    label_ko: 블록체인
    keywords: [블록체인, DeFi, 크립토, Web3]

# 디자인 프리셋
archetypes:
  - id: product_design
    label_ko: 프로덕트 디자이너
    keywords: [프로덕트 디자인, Figma, UX, 서비스 기획]
```

엔진은 `config/archetypes.yml`의 레이블과 키워드만 알면 되며, 의미(금융인가 디자인인가)는 몰라도 된다.

### (c) Qualifier / Scorer — 규칙 기반, 도메인 중립

- `qualifier_rules.yml`의 negative/positive/numeric 패턴은 한국어 정규식이지 "금융" 지식이 아니다
- `scoring_weights.yml`의 A~F 가중치는 domain 독립 메트릭 (fit_job, legitimacy, deadline_urgency, ...)
- 한국 시장 특화(휴학생/재학생/NCS 등)는 **한국 전체 공통**이지 금융만의 것이 아님

### (d) Scrapling + Agent-Reach 레이어링

```
Scrapling (저수준)     →  HTTP/Playwright, anti-bot, stealth
 career_ops_kr.channels →  한국 포털별 파서 + 로그인 상태 관리
 Agent-Reach 패턴       →  채널 등록/디스패치 고수준 API
 modes/*.md             →  Claude Code 모드 (scan/filter/score/...)
 CLI (career-ops)       →  사용자 인터페이스
```

이 스택의 어느 층도 "금융"에 하드코딩되지 않았다.

---

## 3. 프리셋이 교체하는 것 vs 교체하지 않는 것

### 프리셋이 바꾸는 것 (User 레이어 5파일)

- `config/profile.yml` — 타겟 산업·archetype 선택
- `config/portals.yml` — 구독 포털
- `config/qualifier_rules.yml` — 자격 판정 규칙
- `config/scoring_weights.yml` — A~F 가중치
- `modes/_profile.md` — 개인 narrative 템플릿

### 프리셋이 건드리지 않는 것

- `career_ops_kr/**/*.py` — 엔진 코드
- `modes/_shared.md` — 공통 컨텍스트 (7개 도메인 모두 적용)
- `scripts/` — dedup/verify/merge
- `cv.md` — **개인 이력서는 사용자가 직접 관리**
- `data/` — 과거 공고·applications.md

> 이것이 `career-ops init --preset`가 "초기화"지 "재설치"가 아닌 이유다.

---

## 4. 배포 모델

이 레이어 분리 덕분에 **세 가지 배포 시나리오**가 모두 작동한다.

### 개인 사용 (찬희)

```
~/career-ops-kr/
├── config/*.yml          ← finance 프리셋으로 초기화
├── cv.md                 ← 찬희 이력서
├── data/jobs.db          ← 찬희 SQLite
└── career_ops_kr/**      ← 엔진 (git pull로 업데이트)
```

`git pull`로 엔진 업데이트 → User 파일 보존 → 재시작.

### 팀 내부 배포 (Luxon 팀원)

팀원 A (디자이너):
```bash
git clone https://github.com/luxon-ai/career-ops-kr
cd career-ops-kr
career-ops init --preset design
```

팀원 B (백엔드 개발자):
```bash
git clone https://github.com/luxon-ai/career-ops-kr
cd career-ops-kr
career-ops init --preset dev
```

동일 레포, 동일 엔진, 다른 User 레이어. 서로의 `config/`/`cv.md`는 각자 git stash/personal branch로 관리.

### 오픈소스 커뮤니티

- 엔진은 MIT 라이선스로 공개
- 기여자는 `presets/<domain>.yml` PR → 새 도메인 추가 ([adding-a-preset.md](adding-a-preset.md))
- User 파일은 각자 local에 유지, 저장소에 올리지 않음 (`.gitignore`로 `cv.md`, `config/profile.yml`, `data/` 제외)

---

## 5. 한계와 제약

이 범용화는 만능이 아니다. 명시적으로 드러내자.

### 한국어 고유 특화

- `qualifier_rules.yml`의 정규식은 **한국어 기반** ("휴학생 가능", "석사 이상 필수" 등)
- 포털은 전부 한국 사이트
- `modes/` 문서들도 한국어 narrative
- 영어권/일본/중국 시장에 그대로는 못 가져감

### 글로벌 확장 시 고려사항

- 정규식 패턴을 locale별로 분리 (`qualifier_rules/kr.yml`, `qualifier_rules/en.yml`)
- `modes/kr/`, `modes/en/`, `modes/ja/` 식의 locale 디렉토리 (v0.2 로드맵에 이미 포함)
- HITL 메시지 i18n
- 포털 Tier 체계는 나라마다 재정의 필요 (미국이라면 LinkedIn=T3, Glassdoor=T3 등)

### HITL G5는 영구 불변

프리셋이 뭐든 `CLAUDE.md` §4 HITL G5 "지원 제출" 게이트는 **영구 수동**이다. 시스템은 "준비 완료"까지만. 어떤 도메인이든 자동 제출은 금지.

### 범용성 vs 특화

찬희의 금융 프리셋은 5년 이상 데이터 축적과 커스터마이징이 녹아 있다. 새 프리셋이 같은 수준의 정밀도에 도달하려면 그 도메인 전문가의 손이 필요하다. 프레임워크는 **뼈대**만 제공한다.

---

## 6. 미래 방향

### v0.2 (Phase 2)

- `config/archetypes.yml` 완전 외부화
- `modes/kr/` 로컬라이제이션 디렉토리
- `presets/<domain>.yml` 공식 스키마 검증 (pydantic)
- `career-ops init --preset <id> --dry-run` 플래그

### v1.0 (Phase 3)

- `modes/en/`, `modes/ja/` 등 locale 병행 지원
- 74개 포털 커버 (현재 9개)
- 공개 오픈소스 배포 → 커뮤니티 프리셋 마켓플레이스
- 프리셋 버전 관리 + 자동 업데이트 알림

### 꿈

하나의 `career-ops` CLI로 전 세계 구직자가 자기 도메인에 맞는 프리셋을 `--preset <domain>`으로 바로 설치하고, User 레이어만 유지하면서 엔진 업데이트를 받을 수 있게 된다. 그 때가 되면 이 문서는 **왜 이 프레임워크가 일반화 가능했는가**를 기록한 최초의 증거가 된다.

---

## 참고

- 프로젝트 루트 `CLAUDE.md` §2 (User/System 계약), §4 (HITL 5게이트)
- `README.md` "도메인 지원 / Generalization" 섹션
- [presets.md](presets.md) — 7종 프리셋 카탈로그
- [adding-a-preset.md](adding-a-preset.md) — 새 프리셋 작성 가이드
- 원본 철학: [santifer/career-ops](https://github.com/santifer/career-ops)
- Channel 패턴 원본: [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach)
