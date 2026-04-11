> Inherits from [_shared.md](_shared.md)

# Mode: pdf

공고별로 ATS(Applicant Tracking System) 통과율을 최우선으로 하는 맞춤형 이력서 PDF를 생성한다. `cv.md` 기반에 공고 키워드를 주입하고 `templates/cv-template.html`로 렌더링 → Playwright로 A4 1페이지 PDF 출력.

## Purpose

- 공고 하나당 공고 맞춤 CV PDF 1부 생성.
- **ATS 통과율 우선** — 예쁜 디자인보다 키워드 매칭과 파싱 친화성이 먼저.
- 결과물은 `output/<org>_<title>_<YYYYMMDD>.pdf`.
- **제출은 하지 않는다** — 찬희가 수동으로 업로드 (G5 영구 수동).

## Inputs

- `target_job`: `JobRecord` (id, org, title, source_url, raw_description, archetype)
- `cv_markdown_path`: 기본 `cv.md` (찬희 베이스 이력서)
- 선택 인자:
  - `--top-k <n>` : 공고에서 뽑을 키워드 수 (기본 20)
  - `--output-dir <path>` : 출력 디렉토리 (기본 `output/`)
  - `--no-rerank` : 섹션 재정렬 비활성화 (원본 순서 유지)

## Process

1. **공고 파싱** — `target_job.raw_description`에서 상위 `top_k`(기본 20)개 키워드 추출.
   - 명사구/기술스택/자격요건 위주 (TF-IDF + 한국어 stopword 제거).
   - `archetype` 기반 필수 키워드 보강 (예: `BLOCKCHAIN` → DID/스마트컨트랙트/Solidity).
2. **베이스 CV 로드** — `pathlib.Path(cv_markdown_path).read_text(encoding='utf-8')`.
   - 마크다운을 섹션(Summary / Core Skills / Experience / Education / Certifications / Projects / Languages)으로 파싱.
3. **Rerank (기본 활성)** — 각 섹션의 항목을 공고 키워드 밀도 내림차순으로 재정렬.
   - Experience 불릿 중 키워드 매칭 0건인 항목은 뒷순위로.
   - 삭제하지 말 것 — 순서만 바꾼다 (찬희 이력 손실 금지).
4. **키워드 매칭 점수 계산** — (공고 키워드 ∩ CV 키워드) / 공고 키워드 수. %로 출력.
5. **Jinja2 렌더링** — `templates/cv-template.html`에 context 주입:
   - `name`, `contact`, `summary`, `skills`, `experiences`, `education`, `certifications`, `projects`, `languages`
   - 모든 값은 CV에서 파싱한 실데이터. **빈 필드 날조 금지.**
6. **Playwright PDF 생성**:
   - `playwright.sync_api` → `chromium.launch()` → `page.set_content(html)` → `page.pdf(format='A4', print_background=False, margin=...)`
   - 파일명: `{org_slug}_{title_slug}_{YYYYMMDD}.pdf` (한글 → 영숫자 slug).
   - 저장 경로: `pathlib.Path(output_dir) / filename`, 인코딩 이슈 방지 위해 영문 slug.
7. **검증** — 생성된 PDF 크기 > 10KB, 페이지 수 ≤ 1 확인. 초과 시 경고.

## Output

- PDF 경로 (절대경로)
- 키워드 매칭 점수 (예: `14/20 = 70%`)
- 매칭된 키워드 리스트
- 누락된 공고 키워드 리스트 (찬희가 수동 보강 참고용)

## HITL

- **G5 인접**: 이 모드는 PDF 생성까지만 수행. 제출/업로드는 절대 자동화하지 않는다.
- 키워드 매칭 < 50% 이면 경고 출력 + "이 공고는 베이스 CV와 적합도가 낮습니다. Archetype 확인 권장."

## ATS 규칙 (엄수)

- ❌ 이미지/로고/아이콘 일절 금지 (ATS 파서가 인식 못함)
- ❌ 복잡한 CSS 레이아웃, 2단 컬럼, 테이블 레이아웃 금지
- ❌ 헤더/푸터 내 연락처 (본문에 배치)
- ❌ 폰트 embed 복잡화 — 시스템 폰트 기반 단순 serif
- ✅ 단일 컬럼, 표준 섹션 헤더(`Summary`, `Experience` 등)
- ✅ 11pt 기준, A4 1페이지 (초과 금지)
- ✅ 키워드를 공고 원문과 동일한 표기로 유지 (예: "Python" vs "파이썬" — 공고 따라감)
- ✅ 날짜 포맷 `YYYY.MM ~ YYYY.MM` 통일

## Failure handling

- Playwright 미설치 → 명확한 에러: `playwright install chromium` 실행 후 재시도 안내.
- `cv.md` 미존재 → G1 온보딩 게이트 발동 (`_shared.md` 참조).
- `target_job.raw_description` 공란 → 키워드 추출 불가 → "공고 원문 재크롤링 필요" 에러, PDF 생성 중단.
- Jinja2 렌더 실패 → 템플릿 placeholder 누락 위치를 구체적으로 보고. **가짜 값 주입 금지.**
- 1페이지 초과 → 섹션 trim 없이 경고만 출력 (찬희가 수동으로 cv.md 다이어트).

## 실데이터 원칙

- CV에 없는 경력/자격/프로젝트를 공고 맞추려고 **절대 날조하지 않는다**.
- 공고 키워드가 CV에 없으면 "누락" 리스트에만 올리고 본문 삽입 금지.
- 번역(한↔영) 요청 없으면 원문 언어 유지.
