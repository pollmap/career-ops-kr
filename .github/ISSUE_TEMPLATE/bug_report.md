---
name: Bug Report / 버그 리포트
about: 버그를 발견했을 때 사용 / Report a bug to help us improve
title: "[BUG] "
labels: bug
assignees: ''
---

## 버그 설명 / Describe the bug

무엇이 잘못됐는지 명확하고 간결하게 설명해주세요.
A clear and concise description of what the bug is.

## 재현 절차 / Steps to reproduce

1. `career-ops <mode> ...` 실행
2. ...
3. 에러 발생

## 예상 동작 / Expected behavior

어떻게 동작해야 하는지.

## 실제 동작 / Actual behavior

실제로 어떤 일이 일어났는지. 가능하면 에러 메시지/스택 트레이스 전체 포함.

```
<에러 로그 붙여넣기>
```

## 환경 / Environment

- OS: [Windows 11 / Ubuntu 24.04 / macOS 14 등]
- Python 버전: [예: 3.12.2]
- career-ops-kr 버전: [예: 0.2.0]
- 사용 중인 preset: [finance / dev / design / ...]
- 설치 방식: [uv sync / pip install / source]

## 채널/모드 컨텍스트 / Channel & Mode

- 어떤 채널에서 발생? (예: linkareer, jobalio, wanted)
- 어떤 모드에서 발생? (예: scan, filter, pipeline, apply)

## 추가 정보 / Additional context

- 실 HTML 캡처 있으면 첨부
- 환경 변수나 config 변경사항
- 스크린샷

## 체크리스트 / Checklist

- [ ] UTF-8 인코딩 관련 이슈가 아닌지 확인 (`PYTHONIOENCODING=utf-8`)
- [ ] User/System 레이어 파일 중 어느 쪽의 문제인지 확인
- [ ] 최신 main 브랜치에서도 재현되는지 확인
- [ ] 중복 이슈가 아닌지 검색 완료
