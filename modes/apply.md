> Inherits from [_shared.md](_shared.md)

# Mode: apply

지원 제출 **준비**를 돕는 모드. 체크리스트 검증과 제출 폼 URL 전달까지만 수행하고, **실제 제출은 사용자가 직접 수동으로** 한다.

## Purpose

- 공고 제출 직전 마지막 검증 + 체크리스트.
- 첨부 파일 누락, 공고 원문 변경(마감일/조건), 자소서 분량 등 사전 점검.
- 상태 전환 `preparing → applied`는 사용자가 "제출 완료" 확인 후에만.

## 🛑 HITL G5 — 영구 수동 제출

- **이 모드는 절대 자동 제출하지 않는다.** 영구 원칙.
- Playwright/Selenium으로 폼 자동 입력/submit 금지.
- 자동 제출 요청이 들어와도 거절하고 G5 원칙 안내.
- 시스템의 역할은 **"준비 완료"까지만**. 제출 버튼은 사용자가 누른다.

## Inputs

- `target_job`: `JobRecord` (id, org, title, source_url, deadline, status)
- `prepared_cv_path`: `pdf` 모드로 생성된 PDF 경로
- 선택 인자:
  - `--cover-letter <path>` : 자소서 파일 경로 (있다면)
  - `--additional <paths>` : 추가 첨부 파일 목록

## Pre-check

- `target_job.status == 'preparing'` 이어야 함. 아니면 경고.
- `prepared_cv_path` 파일 존재 + 크기 > 10KB 확인.

## Process

### 1. 제출 전 체크리스트 20개 검증

시스템이 자동 체크 가능한 항목 + 사용자 수동 확인 항목을 구분:

**자동 체크 (시스템)**
1. CV PDF 파일 존재 및 크기 > 10KB
2. CV PDF 1페이지 이내
3. 공고 마감일 미도과 (D-day > 0)
4. 공고 URL 200 응답 (아직 살아있는가)
5. 공고 원문 해시 변경 여부 (마감/자격 변경 감지)
6. Vault 노트 `4-applied/`로 이동 준비됨
7. SQLite `status` 전환 경로 확인 (`preparing → applied`)
8. 첨부 파일 경로 모두 존재 확인
9. 파일명 특수문자/공백 체크 (포털 업로드 호환)
10. 사용자 개인정보(이메일/전화) CV에 최신 값 포함

**수동 체크 (사용자)**
11. 자소서 분량 글자 수 (공고 요구 대비)
12. 첨부 추가 서류 (자격증 사본 등) 포함 여부
13. 포털 계정 로그인 가능 상태
14. 공고 질문 답변 항목 모두 작성
15. 연봉 / 근무 조건 희망 입력란 확인
16. 추천인 정보 (필요 시)
17. 개인정보 동의 체크
18. 제출 전 최종 오탈자 검토
19. 이력서/자소서 파일명 규칙 (회사 요구 시)
20. 제출 버튼 누르기 전 한 번 더 공고 원문 확인

### 2. 첨부 파일 목록 생성

- 메인 CV PDF 경로
- 자소서 경로 (있다면)
- 추가 첨부 리스트
- 각 파일 크기, 확장자, 최종 수정일 표시

### 3. 공고 원문 재확인 (변경 감지)

- `source_url` 재크롤링 → 원본 해시와 비교.
- 마감일/자격요건 변경 시 **경고 후 중단**: "공고가 변경되었습니다. 재평가 필요."
- 크롤링 실패 시 "수동 확인 필요"로 명시. 날조 금지.

### 4. 제출 폼 URL 전달

- `source_url` 또는 파생 apply URL을 사용자에게 출력.
- Windows: `os.startfile(url)` 또는 단순 URL 출력 (`webbrowser.open` 은 선택).
- **자동 클릭/입력 금지.**

### 5. 상태 전환 대기

- 사용자가 수동 제출 후 CLI에 `career-ops apply --confirm <job_id>` 또는 이모지 ✅로 확인.
- 확인 전까지 `status`는 `preparing` 유지.
- 확인 후: `tracker` 모드 호출 → `preparing → applied` 전환 + Vault 이동 + SQLite 업데이트.

## Output

```markdown
# 지원 준비: {org} — {title}

**공고 URL:** ...
**마감:** D-{n}
**준비된 CV:** {path}

## 자동 체크 결과 (10/10)
- [x] CV PDF 존재 (152KB)
- [x] 1페이지 이내
- [ ] 공고 원문 변경 감지 → ⚠️ 마감일 연장됨
...

## 수동 체크리스트 (사용자)
- [ ] 자소서 글자 수 확인
- [ ] ...

## 첨부 파일 목록
1. {cv_path} (152KB, PDF)
2. {cover_letter} (45KB, DOCX)

## 제출 URL
{apply_url}

## 다음 액션
1. 위 URL 열기
2. 체크리스트 수동 항목 확인
3. 직접 제출 후 `career-ops apply --confirm {job_id}` 실행
```

## Failure handling

- CV PDF 미존재 → `pdf` 모드 선행 실행 안내.
- 공고 URL 404 → 상태 `rejected_site`로 전환 제안 + 제출 중단.
- 마감 도과 → 중단 + `rejected_site` 전환 제안.
- 원문 해시 변경 → 중단 + 재평가 요청 (score 모드 재실행).

## 실데이터 원칙

- 제출 여부를 가정하지 않는다. 사용자 명시적 confirm 없이는 절대 `applied` 상태로 바꾸지 않는다.
- 체크리스트 결과를 임의로 PASS 처리 금지.
