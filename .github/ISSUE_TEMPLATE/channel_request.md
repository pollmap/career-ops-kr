---
name: Channel Request / 새 포털 채널 요청
about: 새 채용 포털 지원 요청
title: "[CHANNEL] <portal_name>"
labels: channel
assignees: ''
---

## 포털 / Portal

- **이름**: [예: 로켓펀치, 프로그래머스, 점핏, 사람인]
- **URL**: https://...
- **언어**: 한국어 / 영어 / 양쪽

## Tier 등급 제안 / Legitimacy Tier

- [ ] T1 공식 (회사 공식 채용 페이지)
- [ ] T2 정부포털 (공공기관/정부)
- [ ] T3 Aggregator (잡코리아, 사람인 등 집계)
- [ ] T4 뉴스/커뮤니티
- [ ] T5 미확인/SNS

## 접근 방법 / Access method

어떤 방식으로 크롤링 가능한지 조사 결과:

- [ ] RSS 피드 있음 — URL: ___
- [ ] 공개 API 있음 — 엔드포인트: ___
- [ ] 일반 HTTP(requests + bs4) 가능
- [ ] 동적 로딩 — Scrapling / Playwright 필요
- [ ] 로그인 필수 (HITL 주의)
- [ ] robots.txt 확인 완료

## 도메인 커버리지 / Domain coverage

이 포털이 어떤 도메인 프리셋에 해당되는지:

- [ ] finance
- [ ] dev
- [ ] design
- [ ] marketing
- [ ] research
- [ ] public
- [ ] edu
- [ ] other: ___

## 샘플 공고 / Sample listings

실제 공고 URL 2~3건:

1. ...
2. ...
3. ...

## 추가 정보

- 갱신 주기 (매일/주간/이벤트)
- 예상 공고 수
- 알려진 차단/rate-limit 이슈
