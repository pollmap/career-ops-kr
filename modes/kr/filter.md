> Inherits from [../_shared.md](../_shared.md) and [_shared.md](_shared.md)

# modes/kr/filter.md — 한국 특화 자격 필터

> 디폴트 `modes/filter.md` 의 학적/전공/학기/병역 체크 위에, 한국 고유의 모순 패턴·차별 패턴·
> 자격증 화이트리스트 보너스·한국 학점 스케일 변환을 추가한다.

## Purpose

- 한국 채용 공고에서 **명백히 부적격**인 공고는 FAIL, **법규 위반 의심** 공고는 `COMPLIANCE_WARN`,
  애매한 공고는 CONDITIONAL 로 분류.
- 찬희 프로파일(`config/profile.yml`) 기준 한국식 학점 4.5 스케일 변환을 적용한다.

## 확장 부정 패턴 (Negative Extended)

공고 원문에 아래 패턴이 등장하면 즉시 FAIL:

| 패턴 | 이유 |
|---|---|
| `신입\s*.{0,5}경력\s*[3-9]년\s*이상` | 모순: 신입인데 경력 3년 이상 요구 (실질 경력직) |
| `병역특례` / `산업기능요원` / `전문연구요원` | 찬희 해당 없음 |
| `운전면허\s*1종.*필수` | 외근직 신호 (내근 희망과 충돌) |
| `자차\s*소유` | 외근직 신호 |
| `지방\s*근무` 단독 (수도권 전혀 없음) | 찬희 거주권 밖 |

## 법규 위반/차별 패턴 → COMPLIANCE_WARN

아래 패턴은 **한국 고용정책 기본법 및 남녀고용평등법, 채용절차법 위반 소지**가 있어 경고 플래그와 함께 기록한다.
찬희가 지원할지는 HITL로 결정하되 로그에 영구 기록한다:

| 패턴 정규식 | 위반 근거 |
|---|---|
| `남성\s*(만|지원|우대)` / `여성\s*(만|지원|우대)` | 남녀고용평등법 제7조 (모집·채용 성차별 금지) |
| `군필자\s*(만|우대|한정)` | 국가인권위 권고 사항 (병역 차별) |
| `[2-3]\d\s*세\s*이하` / `만\s*\d{2}\s*세\s*(이하|까지)` | 고용상 연령차별금지법 제4조의4 |
| `서울\s*거주자\s*(만|한정)` / `수도권\s*거주자\s*우대` | 채용절차법 거주지 차별 (시정 권고 대상) |
| `지방캠퍼스\s*제외` / `수도권\s*대학\s*이상` | 학력 차별 (고용정책기본법 제7조) |
| `미혼\s*(우대|자)` / `기혼\s*제외` | 남녀고용평등법 혼인 차별 |
| `용모\s*단정` / `키\s*\d{3}\s*cm` | 외모 차별 (정당한 직무 요건 없으면 위반) |

**COMPLIANCE_WARN은 FAIL과 별도 상태**: 찬희가 리스크 감수하고 지원할 수 있지만, 회사의 컴플라이언스 신호로 기록.

## 긍정 패턴 (Positive)

공고 본문에 아래가 있으면 `bonus_kr += weight`:

| 패턴 | weight | 의미 |
|---|---|---|
| `학력\s*무관` | +5 | 학점/학교 차별 없음 |
| `전공\s*무관` | +4 | 비전공 찬희 강점 |
| `거주지\s*불문` / `전국\s*지원\s*가능` | +3 | 지역 제약 없음 |
| `재학생\s*지원\s*가능` / `휴학생\s*환영` | +8 | 찬희 강점 |
| `자격증\s*우대` | +2 | 실적 기반 평가 여지 |
| `블라인드\s*채용` | +5 | 학점/학교 숨김 |
| `NCS\s*기반` | +3 | 공공기관 표준 평가 (학점 영향 적음) |

## 수치 cutoff 판정 (한국 4.5 스케일)

찬희 학점: **2.9 / 4.5** (혹은 `config/profile.yml` 값).

```
공고에서 요구 학점 파싱 규칙:
- "학점 3.0 이상" → 3.0/4.5 → 찬희 FAIL
- "학점 평균 3.5 이상" → 3.5/4.5 → 찬희 FAIL
- "학점 4.0/4.5 이상" → 4.0 → 찬희 FAIL
- "백분위 70점 이상" → ≈ 3.15/4.5 → 찬희 FAIL
- "학점 무관" → PASS
- 언급 없음 → CONDITIONAL (수동 확인)
```

찬희의 학점(2.9)보다 높은 cutoff가 명시되면 **FAIL**. 언급 없으면 통과시키고 리스크로 표기.

## 토익/언어 cutoff

```
"토익 700점 이상" → 찬희 점수 비교 (profile.yml 에 토익 저장 필요)
"TOEIC Speaking Lv6+" → 별도 필드
"OPIc IM2 이상" → 별도 필드
"영어 가능자 우대" → +3 bonus만, FAIL 아님
"영어 능통자 필수" → CONDITIONAL (수동 확인)
```

## 학기/나이

- "4학기 이상 수료" → 찬희 4학기 수료 (2.5 완료) → PASS
- "3학년 이상" → 찬희 3학년 휴학 → PASS
- "만 29세 이하" → 찬희 24세 → PASS (단 COMPLIANCE_WARN 플래그)
- "졸업예정자 한정" → 찬희 휴학 → CONDITIONAL (복학 시점 체크)

## 자격증 화이트리스트 보너스

`modes/kr/_shared.md` 의 자격증 매핑을 참조.
공고 우대사항에 아래 자격증이 언급되면 찬희가 보유한 것과 교집합 계산:

- 보유(찬희): `config/profile.yml` → `certifications` 필드
- 요구: 공고 우대사항 파싱
- 교집합 × 자격증별 가중치(1~10) = `cert_bonus` → kr/score.md 로 전달

## Process

1. 디폴트 `modes/filter.md` QualifierEngine 전량 실행 → `default_verdict`.
2. kr 확장 체크 병렬 실행:
   - `check_negative_extended()` → FAIL 후보
   - `check_compliance_violations()` → COMPLIANCE_WARN 플래그
   - `check_positive_kr()` → `bonus_kr` 누적
   - `check_grade_cutoff()` → 4.5 스케일 비교
   - `check_certification_overlap()` → `cert_bonus`
3. 종합 verdict:
   - default FAIL 또는 kr FAIL → **FAIL**
   - COMPLIANCE_WARN 있으면 status 별도 표기, verdict 는 default 기반
   - 전부 PASS/CONDITIONAL → default verdict 유지 + bonus/cert_bonus 부여

## Outputs

```
Verdict: PASS
Compliance: ⚠️ COMPLIANCE_WARN (남녀고용평등법 제7조 위반 소지 — "남성 우대" 문구)
Bonus KR: +12 (학력무관 +5, 재학생 환영 +8 - compliance penalty -1)
Cert Bonus: +6 (SQLD 매칭)
Reasons:
  - [PASS-KR] 학력무관 명시
  - [COMPLIANCE_WARN] "남성 우대" — 남녀고용평등법 7조
  - [CERT] SQLD 요구 일치 (+6)
```
