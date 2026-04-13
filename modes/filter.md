> Inherits from [_shared.md](_shared.md)

# Mode: filter

한국 채용 시장 고유의 자격 조건(학적/전공/학기/졸업연도/병역)을 판정한다. 사용자의 프로파일(`data/profile.yml`)을 기준으로 PASS / CONDITIONAL / FAIL 를 산출.

## Purpose

- 공고 본문(또는 `JobRecord`)에서 한국 특유의 자격 문구를 추출해 기계적 판정.
- **사용자 특수조건**: 24세 / 충북대 경영 3-1 / 휴학 가능 / 병역미필 / 공모전·학회 경력(CUFA, Luxon AI) / 서류 vs 수시 구분.
- 이 모드는 "맞는 공고를 통과시키는 것"이 아니라 "명백히 부적격인 공고를 거르는 것" 이 목적. 애매하면 **CONDITIONAL** 로 반환.

## Inputs

- `job`: `JobRecord` 또는 원문 텍스트(str) 또는 URL.
  - URL인 경우 `scan` 모드의 fetch 헬퍼 재사용.
- `profile_path` (기본 `data/profile.yml`)

## Process

1. 입력이 URL/텍스트면 `JobNormalizer.from_text(...)` 로 `JobRecord` 변환.
2. `QualifierEngine.load(profile_path)` 로 프로파일 로드.
3. `QualifierEngine.evaluate(record)` 호출 → 내부적으로 다음 체크 실행:
   - **학적**: "재학생 불가" / "졸업자 한정" / "졸업예정자" 패턴
   - **전공**: 경영/경제/통계/전산 포함 여부 (사용자=경영)
   - **학기**: 최소 학기수 (3-1 이상 PASS)
   - **졸업연도**: "25년 2월 이전 졸업자" 등
   - **병역**: "병역필 필수" → 사용자 미필 → FAIL
   - **언어**: TOEIC/OPIc 점수 요구
   - **경력**: "경력 N년 이상" → 신입 사용자 → FAIL
4. 각 체크는 `(status, reason, matched_text)` 튜플 반환. 종합 verdict:
   - 하나라도 `FAIL` → **FAIL**
   - `CONDITIONAL` 포함 & `FAIL` 없음 → **CONDITIONAL**
   - 전부 `PASS` → **PASS**

## Outputs

```
Verdict: CONDITIONAL
Reasons:
  - [PASS] 학적: 재학생 허용 ("휴학생 지원 가능")
  - [CONDITIONAL] 병역: 병역 관련 언급 없음 (수동 확인 필요)
  - [PASS] 전공: 경영학 포함
  - [FAIL 없음]
```

- 반환값은 dict: `{verdict, reasons: [{check, status, reason, matched_text}], confidence}`

## Korean patterns note

- 정규식/키워드 패턴은 `career_ops_kr/qualifier/patterns.py` 에 관리.
- 예: `r"병역.{0,5}(필수|완료|필)"`, `r"(재학생|휴학생)\s*(불가|제외)"`
- 한국어 fuzzy 매칭은 `fuzzywuzzy.token_set_ratio` 사용 (임계값 80).

## HITL

- 없음. 완전 자동 판정.
- CONDITIONAL 결과는 `score` / `pipeline` 모드가 수동 확인을 요구할 수 있음.

## Failure handling

- 프로파일 파일 없음 → `onboarding` 실행 안내 후 중단 (가짜 프로파일 금지).
- 본문이 너무 짧음(<50자) → `CONDITIONAL` + reason="본문 불충분".
- 패턴 엔진 예외 → 해당 체크만 `CONDITIONAL(엔진 오류)` 로 표시, 다른 체크는 계속.
- **절대 판정을 가공·낙관화하지 말 것.** 확신 없으면 CONDITIONAL.
