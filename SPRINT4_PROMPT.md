# Sprint 4 시작 프롬프트 — career-ops-kr v0.2.0 → v0.3.0

다음 세션 시작 시 이 파일의 내용을 Claude Code에 붙여넣으면 컨텍스트 로드 + 즉시 실행 가능.

---

## 프롬프트 (복붙용)

```
career-ops-kr Sprint 4를 시작한다. 배포 + 실전 검증 + 인프라 통합 + 품질 마감.

프로젝트 상태:
- 위치: <YOUR_PROJECT_ROOT>/career-ops-kr/
- 버전: v0.2.0 (git commit c8c8905, master branch, working tree clean)
- 파일: 142개, ~17,000줄
- 테스트: pytest 120 passed / 13 skipped / 0 failed
- Lint: ruff 0 errors
- Deps: uv sync --extra dev 완료 (scrapling/playwright/pdfplumber/pydantic 설치됨)
- Playwright 브라우저: 미설치

레퍼런스:
- 메모리: project_career_ops_kr_sprint4.md 에 상세 컨텍스트 저장돼 있음
- 프로젝트 원본 플랜: ~/.claude/plans/melodic-moseying-cupcake.md
- CLAUDE.md: 프로젝트 루트에 데이터 계약, HITL 5 gates, 실데이터 원칙 명시

Sprint 4 할 일 8개 (우선순위 순):

1. GitHub 공개 리포 생성: gh repo create pollmap/career-ops-kr --public --source=. --push
2. v0.2.0 태그 + 릴리스: git tag → push → GitHub Release 에 RELEASE_NOTES.md 내용 게시
3. Playwright 브라우저 설치: uv run playwright install chromium
4. 첫 실제 스캔: uv run career-ops scan --tier 1 (잡알리오/yw.work24/apply.bok 3개)
   → 실패하는 채널은 실 HTML 캡처 후 selector 튜닝
5. Tier 3-4 selector 튜닝: 9개 스텁 채널(미래에셋/KB/하나/NH/삼성/두나무/빗썸/토스/Lambda256)
   → 각 사이트 실 HTML 캡처 → Scrapling adaptive selector 학습 → 실 데이터 통과
6. Discord 웹훅 연결: config/profile.yml > discord.webhook_url 설정 + 테스트 메시지
7. Nexus MCP 서버 등록: ssh luxon VPS 접속 → /opt/nexus-finance-mcp/config/ 에 career-ops-kr 추가 → PM2 재기동 → 398 → 408 도구
8. 품질 마감:
   - LLM 2차 scorer 실전 호출 비용 프로파일링
   - 55 → 100 프로그램 데이터셋 확장
   - GitHub Actions CI 첫 green
   - uv.lock 커밋 여부 결정
   - tests/test_parser.py 스킵 해제 (parser.parse_korean_date 등 구현)
   - ics_export.py:93 datetime.utcnow() deprecation 제거

제약:
- UTF-8 전역, pathlib.Path 사용
- 실데이터 원칙 절대 (목업 금지)
- User/System 레이어 분리 엄수
- HITL 5 gates 준수
- 병렬 서브에이전트 극한 활용

시작 검증 커맨드:
cd "<YOUR_PROJECT_ROOT>/career-ops-kr"
git log --oneline
uv run pytest -q
uv run ruff check .

3개 전부 그린이면 Sprint 4 즉시 착수.

첫 번째 질문: "어떤 작업부터 시작할까? 1~8 순서대로? 아니면 병렬 가능한 것 묶어서?"
```

---

## 사용법

1. 다음 Claude Code 세션 시작
2. 위 프롬프트 블록 복사 (```로 감싼 부분)
3. 붙여넣기
4. 엔터
5. Sprint 4 즉시 진행
