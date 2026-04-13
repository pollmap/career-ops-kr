> Inherits from [_shared.md](_shared.md)

# Mode: project

공고 요구사항을 1~2주짜리 개인 프로젝트로 역설계한다. 사용자 현재 스킬과의 gap을 채우는 포트폴리오 확장용 스프린트 제안.

## Purpose

- 공고 JD → "이걸 증명할 수 있는 작은 프로젝트" 역설계.
- 결과물은 사용자가 GitHub/블로그에 올릴 수 있는 구체적 스프린트.
- 이력서/자소서 bullet까지 자동 생성.
- Luxon AI 포트폴리오 확장 + 공고 적합도 보강 동시 달성.

## Inputs

- `target_job`: `JobRecord` (org, title, raw_description, archetype)
- `modes/_profile.md` / `config/profile.yml` — 사용자 현재 스킬/보유 자산
- 선택 인자:
  - `--duration 1w|2w` : 스프린트 기간 (기본 1w)
  - `--publish github|blog|both` : 공개 채널 (기본 both)

## Process

1. **JD 요구사항 추출** — 공고 원문에서:
   - 필수 기술 스택 (예: Python, SQL, React, Solidity)
   - 필수 도메인 지식 (예: 블록체인 표준, 코어뱅킹 아키텍처)
   - 우대 사항 (2차 gap)
   - 직무 일상 업무 (proxy task)
2. **사용자 현재 자산 매핑** (`_profile.md` / `config/profile.yml`):
   - 보유 스킬: Python, SQL, MCP 64서버, 에이전틱코딩, Luxon AI, CUFA 회장
   - 보유 프로젝트: career-ops-kr, Nexus MCP, quant-fund, CUFA 보고서 등
   - **실제 있는 것만 사용.** 없는 것 채우지 않는다.
3. **Gap 분석** — JD 요구사항 ∩ 현재 자산 → 부족 영역 도출.
   - 예: 공고가 `Solidity` 요구, 사용자 보유 X → gap.
   - 예: 공고가 `Python+FastAPI`, 사용자 Python 있음 → gap 작음.
4. **스프린트 제안** — gap을 채울 1~2주 프로젝트 1~3개:
   - **목표**: 공고 요구사항 핵심을 직접 시연
   - **범위**: 1~2주 1인 개발 규모 (over-scope 금지)
   - **산출물**: GitHub repo + README + 데모 / 블로그 포스트
   - **증명 포인트**: 이 프로젝트가 공고의 어떤 요건을 증명하는지
   - **재사용성**: Luxon AI / 기존 프로젝트와 연결 가능한가?
5. **타임라인** — 일자별 세부 (예: Day 1-2 리서치, Day 3-5 코어, Day 6-7 문서/배포).
6. **공개 전략**:
   - GitHub: repo 이름, README 구조, 라이선스 제안
   - 블로그: 포스트 제목 1~2개, 커버 이미지 필요 여부
   - Vault 노트 연결 (필요시)
7. **이력서/자소서 bullet 자동 생성** — STAR 구조:
   - "{프로젝트명}을 1주간 개발하여 {JD 요구 기술}을 실증. {구체 수치/결과}를 달성."
   - 사용자가 이력서 Experience 섹션에 바로 추가 가능한 형태.

## Output

```markdown
# 공고 기반 포트폴리오 스프린트: {org} — {title}

## 공고 요구 핵심 (JD 추출)
- 필수: ...
- 우대: ...

## 사용자 현재 자산 매핑
| JD 요구 | 보유 여부 | 근거 |
|---|---|---|
| Python | ✅ | career-ops-kr |
| Solidity | ❌ | — |

## Gap 분석
- 큰 gap: Solidity, Hardhat
- 작은 gap: 해당 도메인 용어

## 제안 스프린트 #1: {이름}
**목표**: ...
**기간**: 1주
**산출물**: GitHub repo + 블로그 포스트
**증명 포인트**: JD의 "블록체인 개발 경험" 직접 시연

### 타임라인
- Day 1-2: 리서치 (ERC-20, Hardhat 환경)
- Day 3-5: 컨트랙트 작성 + 테스트
- Day 6-7: 배포 + README + 블로그

### 이력서 bullet (STAR)
- "Solidity 기반 ERC-20 토큰 컨트랙트를 1주간 직접 구현. Hardhat 테스트 커버리지 85% 달성, Sepolia 테스트넷 배포."

## 제안 스프린트 #2: ...
## 공개 전략
## 사용자 수동 체크
- [ ] 스프린트 #1 승인 여부
- [ ] 착수 시점 결정
```

## HITL

- 별도 게이트 없음 (제안만 생성, 실행은 사용자 결정).
- 단, **over-scoped 프로젝트 경고** — 1인 1~2주로 불가능한 규모면 축소 권장.

## Failure handling

- JD에서 기술 스택 추출 실패 → "공고 원문 부실, 재크롤링 필요" 경고.
- 사용자 자산 정보 부족 → `_profile.md` 보강 요청.
- Gap이 너무 크면 (예: 전혀 새로운 언어 5개) "1~2주 내 불가. 공고 재고 권장" 안내.

## 실데이터 원칙

- 사용자가 실제로 보유하지 않은 스킬을 "보유"로 표시 금지.
- 제안 프로젝트의 결과 수치(커버리지, 성능)는 사용자가 실제로 달성 가능한 범위로만 제안.
- 이력서 bullet에 미리 "완료" 형태로 쓸 땐 `{미착수}` 플래그 명시.
