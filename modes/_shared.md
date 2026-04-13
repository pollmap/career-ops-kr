# _shared.md — 모든 모드 공통 컨텍스트

> 이 파일은 career-ops-kr의 모든 모드(`scan`, `filter`, `score`, `pipeline`, `tracker`, `patterns`, `auto-pipeline`)가
> 호출 시 반드시 상속하는 공통 프롬프트 컨텍스트다.
>
> 🔷 **System 레이어** — 자동 업데이트 가능. 유저 커스터마이징은 `_profile.md`로.

---

## 1. 사용자 요약 (사용자)

**상세 프로필은 `config/profile.yml` + `modes/_profile.md` 참조.**

- 24세, 충북대 경영학부 4학기 수료 후 휴학
- 학점 2.9, 비전공 (경영학), 내일배움카드 발급 가능
- CUFA 가치투자학회 회장, Luxon AI 창업자
- MCP 서버 64개 운영, 에이전틱코딩 실력, Python+SQL 실전
- 생활권: 안산/서울/청주 (대중교통 통근 가능)
- 타겟: 한국 금융사 디지털 부문 > 핀테크/블록체인 > 공공금융

---

## 2. 74개 검증 프로그램 데이터셋

- **위치**: `tests/fixtures/programs_verified_20260411.json`
- **출처**: 2026.04.11 수동 검증 (사용자_검증완료_지원가능_프로그램_최종.md)
- **분류**:
  - 🟢 확정 지원 가능 (7개): 키움 KDA, 미래내일 일경험 등
  - 🟡 패턴 확인 (22개): 신한투자 블록체인부, 디지털 하나로 등
  - 🔴 수시 채용 (7개): 두나무, 빗썸, 토스 등
  - ❌ 자격 미달 (8개): KB IT's Your Life, 신한DS, 우리FISA 등
  - + 추가 확장 (30개): 공공기관 체험형, 핀테크 스타트업 등
- **용도**: `qualifier` / `archetype` / `scorer` 회귀 테스트 기준

---

## 3. Archetype 6분류 (한국 금융/디지털)

| Code | 명 | 키워드 | 예시 공고 |
|------|---|--------|----------|
| `BLOCKCHAIN` | 블록체인 | 블록체인, 디지털자산, STO, 토큰증권, DID, 스마트컨트랙트 | 신한투자 블록체인부, Lambda256 |
| `DIGITAL_ASSET` | 디지털자산 운영 | 크립토, 거래소, 수탁, 마이닝 | 두나무, 빗썸, 코빗 |
| `FINANCIAL_IT` | 금융 IT | FinTech 인프라, 코어뱅킹, 결제시스템, API 게이트웨이 | KB증권 디지털, 신한DS |
| `RESEARCH` | 리서치/분석 | 기업분석, 퀀트, 이코노미스트, 투자전략 | 한국투자증권 리서치, KDI |
| `FINTECH_PRODUCT` | 핀테크 프로덕트 | 마이데이터, P2P, 간편결제, 인슈어테크 | 토스, 카카오페이, 뱅크샐러드 |
| `PUBLIC_FINANCE` | 공공금융 | 한국은행, 신보/기보, 거래소, 예탁결제원 | 한국은행 체험형, 주금공 |

분류 로직: `career_ops_kr/archetype/classifier.py`
→ 규칙 기반 키워드 매칭 1차, 애매하면 LLM 2차 호출.

---

## 4. 지원 상태 canonical 정의

**`templates/states.yml` 참조**. 모든 트래커 행은 아래 상태 중 하나여야 한다:

```
inbox          → 새로 스캔, 아직 분류 안 됨
eligible       → 자격 통과 (Vault 1-eligible/)
watchlist      → 수시/패턴 모니터링 중 (Vault 2-watchlist/)
rejected_self  → 사용자 자격 미달 (Vault 3-rejected/)
rejected_site  → 공고가 사라짐 / 취소됨
preparing      → 지원 준비 중 (자소서 작성 등)
applied        → 지원 완료 (Vault 4-applied/)
interview      → 면접 진행
offer          → 합격
declined       → 사양
accepted       → 최종 수락
```

레거시 상태값은 `scripts/normalize_statuses.py`로 변환.

---

## 5. HITL 원칙 요약

- **G1 온보딩**: 유저 파일 미존재 시 대화형 인터뷰 블로킹
- **G2 Archetype 변경**: `_profile.md` 수정 시 diff 승인 필수
- **G3 Tracker 병합**: dedup 결과 리뷰 후 승인
- **G4 배치 평가**: 5건 이상 병렬 시 샘플 1건 먼저
- **G5 지원 제출**: 영구 수동 (자동 제출 금지)

---

## 6. 출력 포맷 (모든 리포트 공통)

```markdown
# [공고 제목]

**URL:** {source_url}
**Legitimacy:** {T1~T5}
**Archetype:** {6분류 중 1}
**Fit Grade:** {A~F} ({점수}/100)
**Eligibility:** {✅|△|❌}
**Deadline:** {YYYY-MM-DD} (D-{N})
**Source Tier:** {1~6}

## 요약
[공고 핵심 3~5문장]

## 자격 판정 근거
- [규칙 매칭 결과]
- [충족 요건]
- [미달 요건 (있다면)]

## 적합도 세부
| 차원 | 점수 | 근거 |
| ... |

## 권장 액션
- [ ] [다음 할 일]
```

---

## 7. 실데이터 원칙 (전역 CLAUDE.md 상속)

- 크롤링 실패 → "실패"로 명시 저장, 빈 필드 금지
- 추정 데이터 금지 — "아마도", "예상" 언어 사용 금지
- 출처(`source_url`) 모든 공고에 필수
- 자격 판정 근거를 공고 원문에서 직접 인용

---

## 8. 환경 주의 (Windows)

- 파일 I/O: 반드시 `encoding='utf-8'`
- 경로: `pathlib.Path` 사용, `os.path.join` 금지
- 개행: LF 유지 (`.gitattributes`로 강제)
- Playwright 브라우저: `playwright install chromium` 후 `.cache/ms-playwright/` 에 저장됨
