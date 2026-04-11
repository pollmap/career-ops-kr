# Pull Request

## 요약 / Summary

이 PR 이 무엇을 하는지 1~3줄로 요약.

## 변경 유형 / Type of change

- [ ] `feat`: 새 기능
- [ ] `fix`: 버그 수정
- [ ] `refactor`: 리팩토링 (동작 변경 없음)
- [ ] `docs`: 문서
- [ ] `test`: 테스트 추가/수정
- [ ] `chore`: 빌드/설정/의존성
- [ ] `perf`: 성능 개선
- [ ] `ci`: CI/CD

## 영향받는 컴포넌트 / Affected components

- [ ] 채널 (`career_ops_kr/channels/`)
- [ ] 모드 (`modes/`)
- [ ] Qualifier / Scorer / Archetype
- [ ] Storage (SQLite / Vault)
- [ ] CLI (`career_ops_kr/cli.py`)
- [ ] MCP 서버 (`career_ops_kr/mcp_server.py`)
- [ ] TUI 대시보드 (`career_ops_kr/tui/`)
- [ ] 프리셋 (`presets/*.yml`)
- [ ] 문서

## 체크리스트 / Checklist

반드시 확인해야 하는 원칙들:

- [ ] **UTF-8 인코딩**: 모든 파일 I/O 에 `encoding='utf-8'` 명시
- [ ] **실데이터 원칙**: Mock/fake/할루시네이션 데이터 없음
- [ ] **User/System 분리**: User 레이어 (cv.md, config/*, modes/_profile.md, data/*) 미건드림
  - User 레이어 수정이 필요하면 이유 명시: ___
- [ ] **HITL 게이트 유지**: 특히 G5 (자동 제출 금지) 변경 없음
- [ ] **테스트 추가/업데이트**: 새 기능에 테스트 포함
- [ ] **회귀 테스트 통과**: `uv run pytest -q`
- [ ] **Lint 통과**: `uv run ruff check .`
- [ ] **문서 업데이트**: 사용자 영향 있으면 README / docs 갱신
- [ ] **CHANGELOG**: 사용자 영향 있으면 Unreleased 섹션에 추가

## 테스트 계획 / Test plan

어떻게 테스트했는지, 어떻게 테스트할 수 있는지:

```bash
# 예: 이 PR 검증 절차
uv run pytest tests/test_new_feature.py
uv run career-ops <mode> --dry-run
```

## 스크린샷 / 실행 결과 / Output

해당되면 출력, 로그, 스크린샷 첨부.

## 관련 이슈 / Related issues

Closes #___ , Refs #___
