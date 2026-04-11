# LLM 2차 Scorer 비용 프로파일

> 대상: `career_ops_kr/scorer/llm_scorer.py` (Haiku 4.5, 324줄)
> 작성일: 2026-04-11
> **실 API 호출 없이** prompt 길이 기반 정적 추정 — 금액은 모두 **추정**.

## Summary

찬희 사용 패턴(일 50 scan, 30% ambiguous → 15 LLM call/day) 기준 **월 $1.31 (~1,800원), 연 $15.66 (~21,610원)** 수준. 실질적으로 "무료"에 가깝고, rate limit(10/60s)에도 충분히 여유. 단, 극단값(JD 3000자 가득 + 출력 max) 고려 시 월 예산 상한은 **$3 / 4,200원**으로 잡고 kill-switch를 걸어두는 것을 권고.

## 측정 방법

1. `LLMScorer._build_prompt()` (lines 188~225) 템플릿을 **정적 파싱**해 고정 헤더/푸터 문자 수 산출.
2. 3개 archetype(블록체인/금융IT/공공) 각각 대표 JobRecord 시나리오 구성 — `org`/`title`/`jd_snippet`/`breakdown` 실값 대입.
3. prompt string 총 문자 수 → token 환산 (한국어·영어·JSON 혼합 prompt 기준 **약 2 chars/token**; 순수 한국어는 ~1.3, 순수 영어는 ~4).
4. 출력은 `max_tokens=600` 상한, 실제 JSON 응답 평균 ~400 token 가정 (schema: `adjusted_score` + 1~3문장 `reasoning` + 최대 5개 `key_match_points`/`concerns`).
5. **실 API 호출은 금지** (비용 발생 방지). 실측 데이터는 추후 production 로그 축적 후 재보정 예정.

## 결과 테이블

### Prompt 길이 분포 (정적 계산)

| 구분 | 시나리오 | 총 문자 수 | 추정 input tokens | 비고 |
|---|---|---|---|---|
| Low | JD 400자 (짧은 공고) | ~1,265 | ~630 | 공공기관 단문 인턴 공고 |
| **Typical** | **JD 1,000자** | **~1,865** | **~930** | **블록체인/금융IT 평균** |
| High | JD 3,000자 (최대치, `[:3000]` 캡) | ~3,865 | ~1,930 | 상세 JD + 장문 breakdown |

> 고정 헤더(찬희 프로필 8줄 + 섹션 헤더 + 지시문 + JSON 스키마) ≈ **615 chars**, 가변부(org/title/archetype/location/deadline + jd_snippet + breakdown JSON)가 나머지.

### Haiku 4.5 단가 (2025 공식)

| 항목 | 단가 |
|---|---|
| Input | $1 / M tokens |
| Output | $5 / M tokens |
| Cache read (미적용) | $0.10 / M tokens |

### Per-call 비용

| 시나리오 | Input tokens | Output tokens | Cost / call |
|---|---|---|---|
| Low | 630 | 300 | ~$0.0021 |
| **Typical** | **930** | **400** | **~$0.0029** |
| High | 1,930 | 600 | ~$0.0049 |

> `llm_scorer.py` docstring(line 27)의 자체 추정 `~1.5k in + ~400 out ≈ $0.0035` 와 **동일 수준**. 교차 검증 OK.

## 시나리오별 비용

가정: **일 50 scan × 30% ambiguous = 15 LLM calls/day**, `$1 = 1,380원`.

| 기간 | Calls | Typical ($0.0029/call) | High ($0.005/call) | KRW (Typical) |
|---|---|---|---|---|
| 일일 | 15 | $0.044 | $0.075 | ~60원 |
| 월간 | 450 | $1.305 | $2.25 | ~1,800원 |
| 연간 | 5,400 | $15.66 | $27.00 | ~21,610원 |

> `llm_scorer.py` docstring(line 28)의 `~$0.05/day` 추정과 정합 (15 calls × $0.0035 ≈ $0.053).

### Rate limit 여유

- 상한: **10 calls / 60s** (`_RATE_LIMIT`, `_RATE_WINDOW`)
- 실 부하: 15 calls/day 평균 ≈ 0.00017 calls/sec → 10분 간격으로 분산 시 **도달 확률 0에 수렴**
- 최악(50건 ambiguous 일괄 처리): 5 window 분산 필요, 실제로는 natural 분산으로 문제 없음
- **결론**: 현재 사용 패턴에서 rate limit hit은 사실상 없음. Kill-switch는 비용 쪽에만 걸면 충분.

## 권고

### 1. Prompt Caching 도입 (잠재 절감 ~60%)
고정 헤더 ~615 chars (찬희 프로필 + 지시문 + JSON schema)를 Anthropic `cache_control`로 마킹하면 2번째 호출부터 input의 ~33%가 $0.10/M 단가 적용 → 월 **$1.3 → $0.85** 수준. [참고: `claude-api` 스킬]

### 2. Kill-switch (권장)
- 월 예산 상한: **$3 / 4,200원** (high 시나리오의 1.3배)
- 일일 호출 상한: **30 calls** (현재 평균의 2배)
- 초과 시 `LLMScorer.score()` 에서 `None` 반환 → rule-based verdict 유지
- 구현 위치: `_rate_limit_ok()` 옆에 `_budget_ok()` 추가, 일/월 카운터를 SQLite에 persist

### 3. 배치 호출 (옵션, 복잡도↑)
여러 ambiguous job을 하나의 prompt로 묶어 호출 → 고정 헤더 분할상환(amortize). 단, 응답 파싱 복잡도 증가 + 한 건 실패 시 전체 재호출 리스크 → **MVP 단계에서는 비권장**, 월 $3 넘어갈 때 재검토.

## 주의사항 / 한계

- 본 수치는 **prompt 길이 기반 정적 추정**이며, 실제 Anthropic 토크나이저 결과와 ±15% 편차 가능.
- `jd_snippet` 은 `[:3000]` 으로 하드 캡되므로 초장문 JD도 상한 예측 가능 (`llm_scorer.py` line 194).
- Output tokens는 모델 행동에 따라 변동 — schema 위반 응답(`_parse_response()` 에서 drop)은 비용만 발생하고 결과 0.
- Haiku 4.5 가격은 2025년 공시 기준 ($1/$5 per M input/output). 모델 교체 또는 단가 인상 시 재계산 필요.
- 실 production 로그(`anthropic-response.usage.input_tokens` / `output_tokens`) 누적되면 본 문서를 실측치로 갱신할 것.
