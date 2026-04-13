> Inherits from [_shared.md](_shared.md)

# Mode: score

단일 공고 하나를 입력 받아 **원본 Career-Ops `oferta.md` 등가** 의 구조화 리포트를 생성한다. URL 또는 `JobRecord` 하나에 대해: 아키타입 분류 → 자격 판정 → 적합도 점수 → 정당성 검증 → 마크다운 리포트 출력.

## Purpose

- 사용자가 링크 하나 던지면 "지원할 만한가, 허위는 아닌가, 왜 맞는가/아닌가" 를 1분 안에 답한다.
- 평가 결과는 `inbox` → `eligible` / `rejected_self` 전환의 근거가 된다.
- 이 모드는 **읽기 전용** — 상태 전환은 `tracker` 모드가 담당한다.

## Inputs

- 아래 중 하나:
  - URL (str): 공고 원본 페이지
  - `JobRecord`: 이미 정규화된 레코드
- 선택 인자:
  - `--profile <path>` 기본 `data/profile.yml`
  - `--no-fetch` URL 입력이어도 재-fetch 하지 않고 SQLite에서 조회

## Process

1. **입력 정규화**
   - URL → `scan` 모드의 fetcher로 HTML 받기 → `JobNormalizer.from_html(url, html)` 로 `JobRecord` 생성.
   - SQLite에 이미 존재하면 기존 레코드 재사용 (`--no-fetch` 시 필수).
2. **아키타입 분류** — `ArchetypeClassifier.classify(record)` → 다음 중 하나:
   - `financial_digital` / `fintech_growth` / `blockchain_web3` / `pubfin_policy` / `general_it` / `unknown`
3. **자격 판정** — `filter` 모드 호출 (`QualifierEngine.evaluate`).
4. **적합도 점수** — `FitScorer.score(record, profile, archetype)`:
   - 차원: 기술매칭 / 조직매력 / 성장성 / 급여/복지 / 지리 / 리스크
   - 각 0~5, 가중합 → 0~100 정규화 → `S/A/B/C/D` Grade
5. **정당성 검증** — `LegitimacyVerifier.verify(record)`:
   - 사업자등록번호 조회(가능 시), 도메인 WHOIS, 채용 공고 재게시 이력, 의심 키워드("수수료", "투자") 탐지.
   - 결과: `LEGIT` / `SUSPICIOUS` / `UNKNOWN`
6. **리포트 생성** — 아래 Output format 그대로 마크다운 출력.

## Output format

```markdown
# <회사명> — <직무명>

**URL:** <원본 URL>
**Legitimacy:** LEGIT | SUSPICIOUS | UNKNOWN — <근거 1줄>
**Archetype:** financial_digital | fintech_growth | ...
**Fit Grade:** A (83/100)
**Eligibility:** PASS | CONDITIONAL | FAIL — <핵심 이유 1줄>
**Deadline:** 2026-04-30 (18일 남음) | 상시채용 | 불명

## 요약
<2~4줄 핵심 요약>

## 적합도 점수 상세
| 차원 | 점수 | 근거 |
|---|---|---|
| 기술매칭 | 4/5 | Python, MCP 경험 매칭 |
| ... | ... | ... |

## 자격 판정 상세
- [PASS] 학적: ...
- [CONDITIONAL] 병역: ...

## 리스크/주의
- <리스크 1>
- <리스크 2>

## 권장 액션
- [ ] 지원 / [ ] 보류 / [ ] 기각
- 근거: <1~2줄>
```

## HITL

- 없음. 이 모드는 순수 평가/리포트 생성.
- 상태 전환은 사용자가 결정 후 `tracker` 모드로 실행.

## Failure handling

- URL fetch 실패 → 리포트의 Legitimacy=`UNKNOWN`, 본문 섹션을 "본문 획득 실패" 로 명시. **본문을 상상/합성하지 말 것.**
- 아키타입 분류 불확실 → `unknown` 으로 표시하고 이유 기재.
- LegitimacyVerifier 외부 API 실패 → `UNKNOWN` 으로 degrade, 스택트레이스 숨기고 한 줄 경고만.
- FitScorer 가중치 합 0 → Grade `D` + 경고 표시.
- 한국어 문서 인코딩 문제 → utf-8 강제 후 재시도. 여전히 실패 시 raw bytes preview 기재.
