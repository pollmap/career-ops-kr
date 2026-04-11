> Inherits from [../_shared.md](../_shared.md) and [_shared.md](_shared.md)

# modes/kr/auto-pipeline.md — 한국 모드 오케스트레이션

> 디폴트 `modes/auto-pipeline.md` 위에 한국어 JD 자동 감지·라우팅 계층을 얹는다.
> 목적: 한국어 공고는 `kr/*` 모드로, 영문 공고는 디폴트 모드로 자동 분기.

## Purpose

- 한국어 JD 자동 감지 (Hangul character ratio heuristic).
- 감지 결과에 따라 `scan/filter/score` 를 kr 버전으로 라우팅.
- 교차검증을 위해 디폴트 score 도 병렬 실행 → 차이 ±25 초과 시 HITL.
- HITL 5게이트(G1~G5)는 변경 없이 상속.

## Hangul 감지 휴리스틱

```python
def is_korean_jd(text: str) -> bool:
    """한글 문자 비율 기반 한국어 JD 판정.

    - 유니코드 블록 U+AC00~U+D7A3 (완성형 한글음절) 카운트.
    - 전체 문자(공백·숫자·특수문자 제외) 대비 한글 비율 > 30% 이면 KR.
    - 예외: 30% 미만이어도 회사명이 modes/kr/scan.md 화이트리스트에 있으면 KR.
    """
    if not text:
        return False
    meaningful = [c for c in text if c.isalnum() or '\uAC00' <= c <= '\uD7A3']
    if not meaningful:
        return False
    hangul_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3')
    ratio = hangul_count / len(meaningful)
    return ratio > 0.30
```

- **30% 하드컷 이유**: 한국 금융 JD 는 전문용어(영문 약칭 IB/WM/S&T) 비율이 높아 순 한글 비율이 낮을 수 있음.
  반대로 영문 JD 에 한글이 5% 미만이면 디폴트 유지.
- **오버라이드**: 회사명이 `modes/kr/scan.md` 부스트 리스트에 있으면 한글 비율 무관 KR 라우팅.
- **혼합 JD**: 한글 5~30% 구간은 `CONDITIONAL_KR` → 디폴트 + kr 양쪽 실행 후 finalizer 가 합의.

## 실행 시퀀스 (KR 라우팅 시)

```
[1] raw JD text
      │
      ├─ is_korean_jd() ──── False ──→ 디폴트 modes/*.md 파이프라인
      │                                  (변경 없음)
      │
      └─ True ──→ KR pipeline:
            │
            ├─ (1) modes/kr/scan.md    → boost_kr, sector, internship_type
            │
            ├─ (2) modes/kr/filter.md  → verdict + bonus_kr + cert_bonus
            │                            + COMPLIANCE_WARN 플래그
            │
            ├─ (3) modes/kr/score.md   → final_score (KR 보정)
            │         ║
            │         ╠══ 병렬: modes/score.md → default_score (cross-check)
            │         ║
            │         └─ Δ > 25 → verify_flag = True (HITL)
            │
            └─ (4) modes/tracker.md    → data/tracker-additions/*.tsv
                                          (kr 플래그 컬럼 추가)
```

## Fallback (영문 JD)

```
text = fetch_jd(url)
if not is_korean_jd(text):
    # 디폴트 경로 그대로
    result = run_default_pipeline(text)
else:
    result = run_kr_pipeline(text)
```

- **혼합 공고 (한영 병기)**: 한국 회사가 영문 JD 만 올린 케이스(외국계 GS/영국계 HSBC 서울지점 등)는
  회사명 화이트리스트 매칭으로 KR 라우팅 강제.
- **공공기관 NCS 공고**: 한국어 100% → 당연히 KR 라우팅. 단, NCS 평가 기준은 별도 처리
  (학점 영향 적음, `modes/kr/filter.md` 긍정 패턴 +3).

## HITL 게이트 (변경 없음)

`../_shared.md` 의 G1~G5 그대로 상속:

| 게이트 | 조건 | KR 차이점 |
|---|---|---|
| **G1. 온보딩** | 유저 파일 미존재 | `config/profile.yml` 에 한국 자격증 필드 필수 체크 |
| **G2. Archetype 변경** | `_profile.md` 수정 | 변경 없음 |
| **G3. Tracker 병합** | TSV merge | kr 공고는 `source=kr` 컬럼으로 구분 |
| **G4. 배치 평가** | 5건+ 병렬 | 첫 샘플은 kr/default 양쪽 결과 비교 보여주기 |
| **G5. 지원 제출** | apply | 영구 수동 |

## Verify Flag 처리

`kr/score.md` 에서 `verify_flag = True` 일 때:

1. 해당 공고를 `data/verify_queue/*.md` 로 이동.
2. Discord Nexus 채널에 알림: "default 72 vs kr 100 차이 28점, 확인 요망."
3. 찬희 확인 전까지 `status = verify_pending`.
4. 확인 후 최종 점수는 찬희 판단 (kr 우선이 기본, but 오버라이드 가능).

## 실데이터 원칙 (재확인)

- 한글 감지 실패 → "감지 실패" 로그 기록, 디폴트 파이프라인으로 fallback.
- JD 본문이 비어있으면 (크롤링 실패) → `status = crawl_failed`, 스코어링 스킵.
- 공고 삭제(404) → `status = rejected_site`, verify_queue 에서 제외.

## Outputs

```yaml
# data/inbox/신한투자_블록체인부_20260411.md
---
routed_via: kr
hangul_ratio: 0.72
boost_kr: 27
sector: private
internship_type: hiring_track
default_score: 72
kr_score: 93
verify_flag: false
compliance_warnings: []
status: eligible
---
```
