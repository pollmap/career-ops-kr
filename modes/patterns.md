> Inherits from [_shared.md](_shared.md)

# Mode: patterns

기각/탈락 레코드를 분석해 공통 disqualifier 패턴을 추출하고, 사용자의 타겟팅/프로파일 개선안을 제안한다.

## Purpose

- "왜 자꾸 떨어지는지" 를 데이터로 답하기 위한 모드.
- `rejected_self`, `rejected_site`, `FAIL verdict` 분포를 클러스터링해서 상위 3 disqualifier 를 노출.
- 결과물은 읽기 전용 마크다운 리포트. 이 모드가 상태나 프로파일을 직접 수정하지는 않는다.

## Inputs

- `--days <n>` : 최근 N일 (기본 30)
- `--source <name>` : 특정 포털 한정 (선택)
- `--status <list>` : 분석 대상 상태 (기본 `rejected_self,rejected_site`)
- `--min-samples <n>` : 패턴 추출 최소 표본 수 (기본 10)

## Process

1. SQLiteStore에서 `status ∈ 지정목록` & `updated_at >= today - days` 레코드 로드.
2. 표본 수가 `--min-samples` 미만이면 "표본 부족" 경고 + 부분 리포트만 출력 후 종료.
3. 각 레코드에서 `last_reason` + `qualifier_reasons` 수집.
4. 클러스터링:
   - 1차: rule-based (키워드 매핑 — 병역/경력/전공/자격증/지역/마감일 등)
   - 2차: `fuzzywuzzy.token_set_ratio` 기반 근접 병합 (임계 80)
5. 클러스터별 집계: 빈도, 대표 문구 3개, 관련 회사 샘플 5개, 평균 Fit Grade.
6. 상위 3 클러스터를 "핵심 disqualifier" 로 강조.
7. 프로파일 개선 제안 생성 (규칙 기반):
   - 예: "병역 FAIL이 35% → 병역미필 조항 필터 사전 적용 권장"
   - 예: "특정 지역 불합격 비중 > 40% → 지역 선호도 프로파일 업데이트"
8. 마크다운 리포트 출력 (stdout + `reports/patterns_<date>.md`).

## Output (markdown report)

```markdown
# Rejection patterns — 최근 30일 (표본 42건)

## 상위 disqualifier
| 순위 | 클러스터 | 빈도 | 대표 문구 | 평균 Grade |
|---|---|---|---|---|
| 1 | 병역 필수 | 14 (33%) | "병역필 필수" 외 2 | C |
| 2 | 경력 N년+ | 9 (21%) | "3년 이상 경력" 외 2 | C |
| 3 | 특정 자격증 | 5 (12%) | "CFA/FRM 우대" 외 1 | B |

## 관찰 요약
- ...

## 프로파일 개선 제안
1. [HIGH] 병역 미해당 필터 사전 적용 — `qualifier/patterns.py` 업데이트
2. [MID] 신입/인턴 키워드 가중치 상향
3. [LOW] ...
```

## HITL

- 없음. 읽기 전용 분석.
- 제안을 실제 적용하는 것은 사용자가 별도 PR/수동 작업으로 처리.

## Limitation note

- 표본 < 10 이면 통계적 유의성 없음 — 리포트 상단에 "참고용" 배너 표시.
- 최소 2주 이상 운영 데이터 누적 후 사용 권장.
- 클러스터링은 결정적(deterministic) 이어야 함. **LLM 기반 요약 금지** — 동일 입력 → 동일 출력.

## Failure handling

- DB 접근 실패 → 에러 종료. 가짜 통계 생성 금지.
- 표본이 전혀 없으면 "분석할 기각 레코드가 없음. 먼저 pipeline 을 돌려보세요" 안내.
- 클러스터링 예외 → 해당 클러스터만 "unclassified" 로 분류하고 계속 진행.
