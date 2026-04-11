---
name: Preset Proposal / 새 도메인 프리셋 제안
about: 새 도메인(예: legal, healthcare, game)용 프리셋 제안
title: "[PRESET] <domain_id>"
labels: preset
assignees: ''
---

## 도메인 / Domain

- `preset_id`: [예: `legal`, `healthcare`, `game`, `bio`, `media`]
- 한국어 도메인명: [예: 법률/리걸테크]
- 영문 도메인명: [예: Legal / LegalTech]

## 타겟 사용자 / Target users

어떤 사람이 이 프리셋을 쓸까요? (예: 법무법인 인턴 지원자, 대학 리서치 조교 등)

## 주요 포털 / Key portals

이 도메인의 주요 구직 포털/공고 소스를 3~5개 나열:

1. **포털명** — URL, Tier 등급 (T1~T5), 접근 방식(RSS/API/requests/playwright)
2. ...
3. ...

## Archetype 후보

이 도메인의 직무 유형 4~6개:

| Archetype | 설명 | 대표 직무 |
|-----------|------|-----------|
| 예: `legal_tech` | 리걸테크 엔지니어 | 백엔드, ML |
| ... | ... | ... |

## 자격 판정 규칙 / Qualifier rules

한국 시장 특화 조건(휴학생 가능? 비전공자? 경력 몇년?):

- 예: 휴학생 지원 가능 여부가 중요
- 예: 학부 졸업 필수 여부
- 예: 특정 자격증 선호

## 점수 가중치 / Scoring weights

A~F 등급 매길 때 무엇을 중시할지:

- 역할 fit: ___
- 도메인 경험: ___
- 위치/원격: ___
- 회사 규모/평판: ___

## 실 예시 공고 (필수)

실제로 이 프리셋으로 평가할 공고 1건 이상 링크:

1. URL: ...
   - 원하는 등급: A/B/C/...
   - 이유:

## 체크리스트

- [ ] `presets/finance.yml` 구조를 참고해 초안 작성 완료
- [ ] 포털 접근 방법 확인 (접근성/로그인 벽/API 여부)
- [ ] 실 공고로 수동 테스트 완료
- [ ] `docs/adding-a-preset.md` 를 읽음
