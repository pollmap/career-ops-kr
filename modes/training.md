> Inherits from [_shared.md](_shared.md)

# Mode: training

찬희가 최근 떨어진(rejected_self / CONDITIONAL) 공고와 현재 자격증 진도를 엮어, **부족한 역량 영역을 찾아 1개월 학습 플랜**을 만든다.

## Purpose

- 왜 떨어졌는지(patterns 모드) → 무엇을 배워야 뚫리는지(training 모드)로 연결.
- `fit_score` 10차원에서 반복적으로 낮게 나오는 차원을 선정하고, 그 차원을 직접 끌어올리는 자격증/강의/프로젝트를 추천한다.
- 찬희의 자격증 5개(ADsP/SQLD/한국사/금투사/투운사) 일정과 충돌하지 않는 학습 슬롯을 제시한다.
- 이 모드는 **읽기 전용**. 실제 학습 등록/결제는 찬희가 수동으로 한다.

## Inputs

- `--days <n>` : 최근 N일 실패/조건부 레코드 (기본 30)
- `--top <k>` : 추천 리소스 개수 상한 (기본 5)
- `--budget <won>` : 유료 리소스 월 예산 한도 (기본 50000 — 무료 우선)
- 자동 로드:
  - `config/profile.yml > certifications` — 현재 자격증 진도
  - `data/scoring_history.jsonl` — 최근 점수 분포
  - `data/legitimacy_queue.jsonl` — 미검토 큐 (제외)

## Process

1. **부족 차원 식별**
   - 최근 FAIL + CONDITIONAL 레코드의 `ScoreBreakdown.dimension_scores` 로드.
   - 차원별 평균이 60 미만이고 최소 5건 이상 관측된 항목을 "약한 차원" 으로 선정.
   - 상위 3개 약한 차원을 학습 플랜의 핵심 타겟으로 삼는다.
2. **자격증 진도 체크**
   - `profile.yml` 의 자격증 5개 상태(`not_started`/`studying`/`scheduled`/`passed`) 확인.
   - 진행 중이지만 진도율 < 50% 이면 "자격증 우선" 플래그.
3. **학습 리소스 매핑 (규칙 기반 — 실데이터 원칙 엄수)**
   - `templates/training_catalog.yml` 에서 차원별 큐레이션 로드.
   - 카탈로그에 **실존하는 리소스만** 허용: 인프런(무료 코스/공식), 유튜브(채널명+링크), 공식 문서(Python/SQLAlchemy/CCXT 등), KOSTA/KISA 공공 교육.
   - 카탈로그에 없는 리소스는 추천 금지. "카탈로그에 없음 → 수동 조사 필요" 로 표기.
4. **1개월 슬롯 생성**
   - 주당 10~15시간 기본 (휴학 중 가정).
   - 자격시험 주간(±3일)에는 학습 슬롯을 30% 감축.
   - Week 1~4 각각에 학습 목표 + 체크리스트 배치.
5. **출력** — markdown 학습 플랜을 `reports/training_<date>.md` 및 stdout.

## Output format

```markdown
# 학습 플랜 — 2026-04-11 기준 (최근 30일 분석)

## 약한 차원 Top 3
| 차원 | 평균 | 관측 | 주 원인 |
|---|---|---|---|
| portfolio_usefulness | 48 | 12 | Python 실무 키워드 부족 |
| brand | 52 | 18 | 대형사 지원 이력 없음 |
| growth | 55 | 9 | 채용연계 코스 미수료 |

## 자격증 진도
- [ ] ADsP 49 — 2026-05-17 (studying, 40%)
- [ ] SQLD 61 — 2026-05-31 (scheduled)
- [x] 한국사 78 — passed
- [ ] 금투사 24 — not_started
- [ ] 투운사 46 — not_started

## 4주 학습 플랜
### Week 1 (04-11 ~ 04-17)
- [ ] [무료] 인프런 — <강의명> (링크)
- [ ] [무료] 유튜브 — <채널명> SQL 실전 (5h)
- 목표: portfolio_usefulness 차원 +15

### Week 2 ...

## 월 예산 사용
- 무료: 18h
- 유료: 2h (₩39,000 / 한도 ₩50,000)
```

## HITL

- 없음. 읽기 전용 리포트.
- 실제 학습 등록은 찬희가 수동.

## Failure handling

- 최근 30일 FAIL/CONDITIONAL 레코드 < 5건 → "표본 부족" 경고 + 부분 리포트만. 가짜 분석 금지.
- `training_catalog.yml` 파일 없음 → "카탈로그 미설치" 에러 + 빈 플랜 생성 중단.
- `profile.yml > certifications` 필드 없음 → 자격증 섹션 생략, 차원 분석만 출력.
- 차원 분석에서 5건 미만 차원은 "데이터 부족" 표기. 평균값 추정 금지.

## 실데이터 원칙

- 존재하지 않는 강의/책/채널 절대 추천 금지. `training_catalog.yml` 에 등록된 것만 사용.
- "아마 이 강의가 좋을 것" 류 추측 언어 금지.
- 링크는 HTTP 200 확인된 것만 (카탈로그 등록 시 검증 완료 전제).
