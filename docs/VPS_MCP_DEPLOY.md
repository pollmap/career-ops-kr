# career-ops-kr VPS/MCP 배포 가이드

## 구조 이해

```
현재 (로컬 전용)                    목표 (VPS MCP 배포 후)
─────────────────────           ──────────────────────────────
로컬 Windows                    Claude Code / HERMES / NEXUS
  └─ career-ops CLI               └─ MCP 도구 호출
       └─ jobs.db (SQLite)               ↓
                                 VPS (career-ops MCP 서버)
                                   └─ career_ops_scan_jobs()
                                   └─ career_ops_score_job()
                                   └─ career_ops_list_eligible()
                                   └─ ... (총 10개 도구)
```

## 옵션 A: 로컬 Claude Code에서 직접 사용 (추천, 즉시 가능)

`~/.mcp.json` 또는 Claude Desktop config에 추가:

```json
{
  "mcpServers": {
    "career-ops-kr": {
      "command": "python",
      "args": ["-m", "career_ops_kr.mcp_server"],
      "cwd": "C:\\Users\\lch68\\Desktop\\05_개발·도구\\career-ops-kr",
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

등록 후 Claude Code에서:
```
career_ops_scan_jobs(site="linkareer")
career_ops_list_eligible(grade="A")
career_ops_score_job(url="https://linkareer.com/activity/12345")
career_ops_get_stats()
```

## 옵션 B: VPS (NEXUS) 배포

### 1. VPS에 코드 배포

```bash
# VPS에서
ssh root@62.171.141.206
cd /root
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
pip install uv && uv sync
```

### 2. config 설정

```bash
# VPS에서 profile.yml 복사
cp templates/profile.example.yml config/profile.yml
# 필요시 편집
```

### 3. nexus-finance-mcp에 등록

VPS의 `/opt/nexus-finance-mcp/mcp.json` (또는 `mcporter.json`)에 추가:

```json
{
  "mcpServers": {
    "career-ops-kr": {
      "command": "python",
      "args": ["-m", "career_ops_kr.mcp_server"],
      "cwd": "/root/career-ops-kr",
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

MCP 서비스 재시작 후 25초 대기.

### 4. NEXUS/HERMES에서 사용 가능한 도구 10개

| 도구명 | 기능 |
|--------|------|
| `career_ops_scan_jobs` | 채널 스캔 실행 (tier/site 필터) |
| `career_ops_score_job` | URL → A~F 채점 |
| `career_ops_list_eligible` | 최소 grade 이상 공고 조회 (`C`면 `A/B/C`) |
| `career_ops_get_deadline_calendar` | N일 이내 마감 공고 |
| `career_ops_query_by_archetype` | archetype별 조회 |
| `career_ops_generate_cover_letter_draft` | 지원서 초안 생성 |
| `career_ops_run_patterns` | 지원 패턴 분석 |
| `career_ops_verify_pipeline` | 파이프라인 헬스체크 |
| `career_ops_apply_preset` | 프리셋 적용 |
| `career_ops_get_stats` | DB 통계 |

### 4.1 2026-04-13 live verification snapshot

- `career_ops_get_stats()` → `total=446`, `by_status={graded: 446}`, `by_grade={B: 5, C: 348, D: 45, F: 48}`
- `career_ops_list_eligible("B")` → `5`
- `career_ops_list_eligible("C")` → `353`
- `career_ops_list_eligible("D")` → `398`
- `career_ops_query_by_archetype("GENERAL")` → `24`
- `career_ops_get_deadline_calendar(days=30)` → `24`
- `career_ops_run_patterns(days=30)` → `total_analyzed=200`
- `career_ops_verify_pipeline()` → `ok=true`, `7/7 checks`
- `career_ops_score_job(sample_url)` → plain grade string (`"B"`), not enum repr
- `career_ops_scan_jobs(site="saramin")` → `320`

추가로 반영된 동작 수정:

- `career_ops_query_by_archetype`는 이제 텍스트 검색을 섞지 않고 archetype 필터만 적용
- `career_ops_score_job`는 `FitGrade.C` 대신 `C`처럼 저장 가능한 grade 값을 반환
- `career-ops batch`는 `fit_grade`, `fit_score`, `eligible`를 SQLite에 실제 저장
- `career-ops batch --limit N`은 더 이상 `search()`의 200건 제한에 잘리지 않음

### 주의사항

- VPS의 DB(`jobs.db`)는 로컬과 별개로 관리됨
- 로컬 스캔 결과를 VPS와 공유하려면 rsync 또는 SQLite 파일 동기화 필요
- VPS에서 직접 스캔하면 VPS IP 기준으로 수집 (rate limit 공유 없음)

## 옵션 C: HTTP API 서버 (FastAPI 래핑)

향후 Phase 3 계획. `mcp_server.py`의 함수를 FastAPI 엔드포인트로 래핑.

```python
# 예시 (미구현)
from fastapi import FastAPI
from career_ops_kr.mcp_server import tool_scan_jobs, tool_list_eligible

app = FastAPI()

@app.post("/scan")
def scan(site: str = None, tier: int = None):
    return tool_scan_jobs(tier=tier, site=site)

@app.get("/jobs")
def jobs(grade: str = "A"):
    return tool_list_eligible(grade=grade)
```

## 즉시 할 수 있는 것 (옵션 A)

1. `~/.mcp.json` 편집해서 career-ops-kr 등록
2. Claude Code 재시작
3. "career_ops_scan_jobs 써서 링커리어 스캔해줘" 하면 Claude가 직접 실행
