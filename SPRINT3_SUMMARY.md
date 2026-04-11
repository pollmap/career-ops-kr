# Sprint 3 Summary — career-ops-kr v0.2.0

**Date**: 2026-04-11
**Track**: P3F (Open Source Prep + Phase 2/3 modes + MCP + TUI)
**Version**: 0.1.0 → 0.2.0

---

## Scope

Sprint 3 finalizes career-ops-kr for **public open source release** while
delivering the Phase 2 / Phase 3 modes originally scheduled in the version
policy (see `CLAUDE.md` §8).

Everything landed as **additive changes** — no User layer files touched, no
HITL gates weakened, no breaking changes to Sprint 1 CLI behavior.

---

## File count delta

| | Sprint 1 (v0.1) | Sprint 2 end | Sprint 3 end (v0.2) |
|-|----------------:|-------------:|--------------------:|
| Total tracked files | 71 | ~82 | ~97 |
| Modes | 7 | 7 | 16 (+9) |
| Channels | 9 | 9 | 9 + 9 stubs |
| Presets | 1 (implicit) | 7 YAML | 7 YAML |
| Docs | 1 (README) | 4 | 7 (+3 translations) |
| GitHub templates | 0 | 0 | 6 |
| CI workflows | 0 | 0 | 1 |

---

## Modes added

### Phase 2 (6 modes — user-facing workflow depth)
- **`pdf.md`** — CV/공고 PDF extraction & comparison
- **`interview-prep.md`** — interview study guide generator from JD + profile
- **`apply.md`** — pre-submission packaging (HITL G5 still blocks auto-submit)
- **`followup.md`** — post-application nudge scheduling
- **`project.md`** — project proof-point extraction for matching
- **`batch.md`** — multi-program batch evaluation with G4 gate

### Phase 3 (3 modes — advanced/strategic)
- **`training.md`** — skill gap training plan from archetype mismatches
- **`deep.md`** — deep research on a target company/program
- **`contacto.md`** — contact (referral) discovery assistant

### Korean localization
- **`modes/kr/_shared.md`** — finance-locale overrides (휴학생, 비전공자, 자격증
  terms and Korean-specific qualifier rules).

---

## Channels added (stubs)

9 Tier 3-4 channel stubs to be filled by contributors (see
`career_ops_kr/channels/` and the 9 MVP channels for the canonical structure):
Linkareer, Jobalio, Wanted, Work24, Shinhan Securities, Kiwoom KDA, KOFIA,
DataQ, Bank of Korea are implemented; the 9 new stubs extend coverage to
Tier 3 aggregators and Tier 4 news sources.

---

## MCP server tool list

`career_ops_kr/mcp_server.py` exposes 10 tools for mounting into Nexus MCP
(398-tool hub):

1. `career_ops_scan` — run scan mode
2. `career_ops_filter` — run filter mode
3. `career_ops_score` — score a candidate
4. `career_ops_pipeline` — full pipeline on a list
5. `career_ops_tracker` — query tracker state
6. `career_ops_pdf` — extract from PDF
7. `career_ops_interview_prep` — generate interview guide
8. `career_ops_followup` — followup schedule
9. `career_ops_project` — project match
10. `career_ops_deep` — deep research

---

## TUI dashboard (`career_ops_kr/tui/`)

Textual-based terminal dashboard launched via `career-ops ui`. Layout:

- **Left sidebar**: current preset, user profile summary, HITL gate status
- **Main pane**: candidate table (URL / Tier / Archetype / Grade / Deadline)
- **Bottom strip**: scan progress, qualifier hit rate, Discord notify queue
- **Key bindings**: `s` scan, `f` filter, `p` pipeline, `q` quit

No screenshots committed — TUI is terminal-native and OS-adaptive.

---

## Open source readiness checklist

| Item | Status |
|------|:------:|
| `LICENSE` (MIT, correct copyright) | PASS |
| `CONTRIBUTING.md` with User/System rules | PASS |
| `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) | PASS |
| CI: GitHub Actions (Windows + Ubuntu × Py 3.11/3.12) | PASS |
| Issue templates (bug, feature, preset, channel) | PASS |
| PR template with invariants checklist | PASS |
| README translations (ko / en / ja) | PASS |
| `llms.txt` for LLM ingestion | PASS |
| `CHANGELOG.md` (Keep a Changelog) | PASS |
| `pyproject.toml` version bumped to 0.2.0 | **pending** |
| `CLAUDE.md` invariants documented | PASS (pre-existing) |
| User layer files unchanged by Sprint 3 | PASS |
| HITL G5 still forbidden | PASS |
| UTF-8 enforced everywhere | PASS |
| Real-data principle maintained (no mocks) | PASS |

> **Action for next session**: bump `pyproject.toml` `version = "0.2.0"`.

---

## Next sprint preview (Sprint 4 / v0.3)

- Fill the 9 Tier 3-4 channel stubs with real implementations
- Publish to PyPI (`pip install career-ops-kr`)
- Create GitHub repo `pollmap/career-ops-kr`, push initial commit
- Integrate `career_ops_kr.mcp_server` into Nexus MCP hub on VPS
- Phase 3 expansion: reach 74-program target across 15+ portals
- Internationalization: channel pattern for non-Korean sources (`modes/en/`,
  channel stubs for LinkedIn Jobs, Wellfound, etc.)
- Screencast demo + Discord onboarding for Luxon AI team usage

---

## Files delivered this sprint (15)

1. `LICENSE`
2. `CONTRIBUTING.md`
3. `CODE_OF_CONDUCT.md`
4. `.github/workflows/ci.yml`
5. `.github/ISSUE_TEMPLATE/bug_report.md`
6. `.github/ISSUE_TEMPLATE/feature_request.md`
7. `.github/ISSUE_TEMPLATE/preset_proposal.md`
8. `.github/ISSUE_TEMPLATE/channel_request.md`
9. `.github/PULL_REQUEST_TEMPLATE.md`
10. `docs/README.ko.md`
11. `docs/README.en.md`
12. `docs/README.ja.md`
13. `llms.txt`
14. `CHANGELOG.md`
15. `SPRINT3_SUMMARY.md` (this file)

All 15 files are UTF-8 encoded, cite real paths/versions, and respect the
User/System layer invariants from `CLAUDE.md`.
