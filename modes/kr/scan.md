> Inherits from [../_shared.md](../_shared.md) and [_shared.md](_shared.md)

# modes/kr/scan.md — 한국 금융권 특화 스캔 오버레이

> 디폴트 `modes/scan.md`의 9개 포털 스캔 로직 위에 한국 금융권 전용 키워드 부스트/분류를 얹는다.
> 목적: 동일한 공고라도 한국 금융권 맥락이면 우선 순위를 올려 inbox 상단에 노출.

## Purpose

- 링커리어/잡알리오/원티드/자소설닷컴/잡코리아/사람인/캐치/슈퍼루키/잡플래닛에서 수집된 raw JD 중,
  한국 금융권에 해당하는 공고를 식별하고 1차 부스트 점수(`boost_kr`)를 부여한다.
- 민간 vs 공공, 체험형 vs 채용형 인턴, 리테일 vs 본점 부서 구분을 메타데이터에 추가한다.

## 한국 금융 키워드 부스트

공고 제목/본문에 아래 토큰이 1개 이상 등장하면 `boost_kr += weight`:

| 카테고리 | 키워드 | weight |
|---|---|---|
| **5대 금융지주** | KB국민, 신한, 하나, 우리, NH농협 | +15 |
| **대형 증권** | 미래에셋, 한국투자증권, NH투자, 삼성증권, KB증권, 신한투자, 키움, 대신, 유안타 | +12 |
| **중형 증권** | 교보, 하이투자, 이베스트, IBK투자, SK증권, DB금융투자, 현대차, 유진 | +8 |
| **자산운용** | 미래에셋운용, 삼성운용, KB운용, 한화운용, 한투운용, 신한운용, 이지스 | +10 |
| **보험** | 삼성생명, 한화생명, 교보생명, 삼성화재, DB손보, 현대해상, 메리츠 | +7 |
| **카드** | 신한카드, 삼성카드, 현대카드, KB국민카드, 하나카드, 비씨, 롯데카드 | +6 |
| **캐피탈** | KB캐피탈, 현대캐피탈, 하나캐피탈, BNK캐피탈, 우리금융캐피탈 | +5 |
| **저축은행** | SBI저축, 웰컴저축, OK저축, 페퍼저축, 애큐온 | +4 |
| **핀테크 유니콘** | 토스, 카카오페이, 카카오뱅크, 케이뱅크, 뱅크샐러드, 핀다 | +14 |
| **크립토/블록체인** | 두나무, 빗썸, 코빗, 코인원, 고팍스, Lambda256, 해시드 | +16 |
| **공공금융** | 한국은행, 금융감독원, 금융위원회, 예탁결제원, 한국거래소, 신보, 기보, 주금공, 예보, 캠코 | +9 |
| **신탁/자문** | 한국투자신탁, 에셋플러스, VIP, 라이프운용 | +6 |

## 민간 vs 공공 분류

공고가 아래 패턴에 해당하면 `sector = public`:
- 회사명이 "한국+X" 형태 (한국은행/한국거래소/한국예탁결제원/한국주택금융공사)
- "X공사" / "X재단" / "X원" 접미사 (예금보험공사, 기술보증기금, 금융연구원)
- "금감원" / "금융위" / "예보" / "캠코" 약칭
- 채용 유형에 "체험형", "청년인턴", "NCS" 언급

그 외는 `sector = private`. 혼합 (민관합작, 예: 핀테크지원센터)는 `sector = public_private_hybrid`.

## 체험형 vs 채용형 인턴 분류

공고 본문에서 아래 신호 매칭:

| 신호 | 분류 |
|---|---|
| "채용연계형", "전환형", "정규직 전환 검토", "우수자 정규직 전환" | `internship_type = hiring_track` |
| "체험형", "청년 체험형", "단기 현장실습", "직무체험", "전환 불가" | `internship_type = experience_only` |
| "수습사원", "수습기간 N개월 후 본채용" | `internship_type = probationary` (=정규직) |
| "계약직 1년", "계약직 2년", "기간제 근로자" | `internship_type = fixed_term` |
| 인턴십 언급 없음 + "신입공채" / "정규직 채용" | `internship_type = direct_hire` |

- `experience_only`는 스코어 -10 감점 (kr/score.md에서 처리).
- `hiring_track`은 +10 가점.

## Process

1. 디폴트 `modes/scan.md` 파이프라인 전량 실행 → `raw_jobs: list[JobRecord]`.
2. 각 JobRecord에 대해:
   - `detect_kr_boost(title + body)` → `boost_kr` 계산
   - `detect_sector(company_name)` → `sector`
   - `detect_internship_type(body)` → `internship_type`
3. 결과를 JobRecord에 메타 필드로 머지 (기존 필드 수정 금지).
4. `inbox/` 저장 시 한국 부스트 내림차순 정렬.

## Outputs

- `data/inbox/*.md` 각 파일 frontmatter에 추가:
  ```yaml
  boost_kr: 14
  sector: private
  internship_type: hiring_track
  kr_keywords_matched: ["신한투자", "블록체인부"]
  ```
- 콘솔 요약: "KR 부스트 상위 10건" 테이블 (회사/부서/타입/점수)

## 주의

- 회사명은 `normalize_company_name()` 으로 공백/영문 약칭 정규화 후 매칭 (예: "KB국민은행" = "국민은행" = "KB Kookmin Bank").
- 민간 자회사 (예: 신한DS = 신한금융그룹 IT 자회사)는 모회사 가중치의 80% 적용.
