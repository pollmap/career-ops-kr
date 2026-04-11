# 새 프리셋 추가 가이드 — career-ops-kr

> career-ops-kr v0.1은 `finance / dev / design / marketing / research / public / edu` 7종 프리셋을 기본 제공한다. 이 문서는 **여덟 번째 프리셋**을 직접 작성해 팀/커뮤니티와 공유하는 방법을 설명한다.
>
> 관련 문서: [presets.md](presets.md) · [generalization.md](generalization.md) · 프로젝트 루트 `CLAUDE.md`

---

## 0. 작성 전 체크리스트

- [ ] 이 도메인이 기존 7종으로 커버되지 않는지 확인 (`dev`와 섞이는 `game` 등은 중복일 수 있음)
- [ ] 해당 도메인 한국 포털/API 5개 이상 실제로 사용해봤는지
- [ ] 타겟 직무를 3~6개 archetype으로 분해할 수 있는지
- [ ] **실데이터 원칙**: 존재하지 않는 포털, 허구의 자격증, 검증 안 된 URL 금지

---

## 1. 파일 위치 & 네이밍

```
presets/
  <domain>.yml    # 예: presets/legal.yml, presets/healthcare.yml
```

- 파일명은 `snake_case` + 단일 단어 선호 (`legal`, `game`, `healthcare`)
- `preset_id`는 파일명 stem과 동일해야 함
- 인코딩: **UTF-8 필수** (BOM 없음)

---

## 2. 프리셋 파일 구조 (top-level keys)

모든 프리셋은 아래 키를 포함해야 한다. `PresetLoader`가 스키마 검증을 수행한다.

```yaml
preset_id: legal               # 파일명과 동일
label_ko: 법무/리걸테크        # 한글 레이블
label_en: Legal/Legaltech      # 영문 레이블 (optional)
description: |
  변호사·로클럭·리걸테크 SaaS·컴플라이언스 포지션을 정기적으로
  수집·평가하기 위한 프리셋.

version: "0.1.0"
maintainer: "Your Name <email@example.com>"

profile_template:                # → config/profile.yml
  name: ""
  target_industries:
    - 법률
    - 리걸테크
    - 컴플라이언스
  archetypes_enabled: [lawyer, law_clerk, legaltech_pm, compliance]

archetypes:                      # → config/archetypes.yml 병합
  - id: lawyer
    label_ko: 변호사
    keywords: [변호사, 송무, 자문, 법률자문]
  - id: law_clerk
    label_ko: 로클럭/재판연구원
    keywords: [로클럭, 재판연구원, 연구원]
  - id: legaltech_pm
    label_ko: 리걸테크 PM
    keywords: [리걸테크, 법률 SaaS, 문서 자동화]
  - id: compliance
    label_ko: 컴플라이언스
    keywords: [컴플라이언스, CP, AML, KYC]

portals:                         # → config/portals.yml
  - name: 대법원 법률구조공단
    url: https://example.or.kr
    tier: 1
    kind: official
  - name: 로앤잡
    url: https://example.com
    tier: 2
    kind: aggregator
  # Tier 1~6 가이드는 아래 3장 참조

qualifier_rules:                 # → config/qualifier_rules.yml
  negative:
    - pattern: "(경력|3년 이상|시니어)"
      reason: "신입 불가"
  positive:
    - pattern: "(신입|주니어|인턴)"
      reason: "신입 허용"
  numeric:
    - field: min_years
      operator: "<="
      value: 0

scoring_weights:                 # → config/scoring_weights.yml
  fit_job: 0.35
  fit_stack: 0.25
  legitimacy: 0.15
  deadline_urgency: 0.15
  location: 0.10

profile_md_template: |           # → modes/_profile.md
  # Profile — <사용자>

  ## 강점
  - (채워주세요)

  ## Deal-breakers
  - (채워주세요)

  ## Archetype 선호 순위
  1. lawyer
  2. legaltech_pm
  3. compliance
  4. law_clerk
```

> `PresetLoader.apply_to()`는 이 YAML을 읽어 `config/profile.yml`, `config/portals.yml`, `config/qualifier_rules.yml`, `config/scoring_weights.yml`, `modes/_profile.md` 5개 파일을 생성한다.

---

## 3. 포털 Tier 선정 가이드

Sprint 1 MVP의 `config/portals.yml`에서 차용한 6단계 체계.

| Tier | 의미 | 예시 |
|------|------|------|
| **T1** | 공식 채용 (회사/기관 직영) | 신한투자증권 · 대법원 · 한국은행 |
| **T2** | 정부/공공 포털 | 잡알리오 · 워크넷 · 나라일터 |
| **T3** | Aggregator (대형 구직사이트) | 원티드 · 잡코리아 · 사람인 |
| **T4** | 뉴스·커뮤니티 기반 (검증 약함) | 클리앙/루리웹 채용글 |
| **T5** | 미확인/소형 포털 | 블로그 채용 공고 |
| **T6** | 개인 추천·인맥 채널 | 슬랙·디스코드 DM |

**선정 기준**: 프리셋당 최소 5개, 가능하면 T1~T3 위주로 60% 이상.

---

## 4. qualifier_rules 작성 팁

한국 시장 특화 규칙. Sprint 1 `config/qualifier_rules.yml` 패턴을 따른다.

### negative (자격 박탈)

```yaml
negative:
  - pattern: "(경력 [3-9]년|시니어 이상)"
    reason: "신입 불가"
  - pattern: "석사 (이상|필수)"
    reason: "학력 미달"
```

### positive (자격 부합)

```yaml
positive:
  - pattern: "(신입|주니어|인턴|체험형)"
    reason: "진입 가능"
  - pattern: "(휴학생|재학생) 가능"
    reason: "재학생 허용"
```

### numeric (수치 비교)

```yaml
numeric:
  - field: min_years      # job 데이터 구조의 필드명
    operator: "<="
    value: 0              # 경력 0년 이하만 통과
  - field: gpa_required
    operator: ">="
    value: 3.0
```

> 정규식은 Python `re` 기준. 한글 특수문자 escape 주의.

---

## 5. scoring_weights 설계 팁

합은 1.0 가까이. Sprint 1은 A~F 그레이드 기본 가중치를 사용.

```yaml
fit_job: 0.30            # archetype 매칭 강도
fit_stack: 0.20          # 스택/자격증 매칭
legitimacy: 0.15         # 포털 Tier 신뢰도
deadline_urgency: 0.20   # 마감 임박도 (D-day)
location: 0.10           # 통근 가능성
benefits: 0.05           # 복지/연봉 매칭
```

- 도메인별로 우선순위가 다름 (예: `public`은 `legitimacy` 가중치↑, `dev`는 `fit_stack`↑)
- 찬희 금융 프리셋은 `deadline_urgency` 가중치를 높게 잡는다 (74개 프로그램 × 마감 분산)

---

## 6. archetype 정의 원칙

1. **3~6개가 적정**: 2개는 너무 좁고, 7개 이상이면 사용자가 선택을 못함
2. **한국어 레이블 필수** (`label_ko`)
3. **keywords**: 5~15개, 공고 제목/본문에서 자주 등장하는 한국어 + 영문
4. **MECE 원칙**: 서로 배타적이면서 전체 도메인 커버

예시 (`dev` 프리셋 archetype):

```yaml
archetypes:
  - id: backend
    label_ko: 백엔드 엔지니어
    keywords: [백엔드, server, API, Spring, Django, FastAPI, Node]
  - id: frontend
    label_ko: 프론트엔드 엔지니어
    keywords: [프론트엔드, React, Vue, Next, TypeScript, UI]
  # ...
```

---

## 7. profile_template / profile_md_template

- **profile_template** → `config/profile.yml`에 그대로 쓰기 (사용자가 채우는 placeholder)
- **profile_md_template** → `modes/_profile.md`에 복사 (narrative/강점/deal-breaker/협상 스크립트 템플릿)

Sprint 1의 `modes/_profile.template.md`를 참조해 동일 구조 유지.

---

## 8. 검증

프리셋 파일 작성 후 다음 단계로 검증한다.

```bash
# 1. 문법 확인 (YAML 파싱)
python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('presets/legal.yml').read_text(encoding='utf-8'))"

# 2. 프리셋 목록에 뜨는지 확인
career-ops init --list-presets

# 3. 임시 디렉토리에 실제 적용 테스트
career-ops init --preset legal --force
ls config/ modes/_profile.md

# 4. scan 연동 smoke test
career-ops scan --dry-run --all
```

> **TODO**: `career-ops init --preset <id> --dry-run` 플래그는 v0.2에서 추가 예정. 현재 v0.1에서는 별도 작업 디렉토리에서 `--force`로 테스트.

---

## 9. 커뮤니티 기여 워크플로

1. 포크 → `presets/<domain>.yml` 작성
2. `docs/presets.md`에 `### <preset_id> — <label_ko>` 섹션 추가
3. 실데이터 검증: 최소 1회 full pipeline 실행 결과 스크린샷 첨부
4. PR 제목: `feat: add preset <domain>`
5. 리뷰어가 확인할 것:
   - [ ] 포털 URL 실존 (404 없음)
   - [ ] 자격증/학위 요건 현실적
   - [ ] 기존 프리셋과 중복되지 않음
   - [ ] YAML 스키마 검증 통과
   - [ ] `presets.md` 섹션 추가 & cross-link 정상

---

## 10. 실데이터 검증 체크리스트 (CRITICAL)

루트 `CLAUDE.md` **실데이터 절대 원칙**을 준수할 것:

- [ ] 포털 URL: 브라우저로 직접 접속해 채용 공고 1건 이상 확인
- [ ] 자격증: 해당 국가 공식 발급기관 이름/링크 확인
- [ ] archetype keywords: 최근 3개월 공고에서 실제로 등장한 단어만 사용
- [ ] 할루시네이션 금지: "아마 있을 것 같은" 포털 추가 금지

---

## 다음 단계

- 프리셋 카탈로그: [presets.md](presets.md)
- 범용화 원리: [generalization.md](generalization.md)
- HITL 게이트 & User/System 레이어 규칙: 프로젝트 루트의 `CLAUDE.md`
