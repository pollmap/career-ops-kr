# Release Checklist — career-ops-kr v0.2.0

**Target release:** 2026-04-11
**Prepared by:** V6 (version bump + git init track)

This checklist captures the manual steps 찬희 still needs to execute
after the orchestrator commits the v0.2.0 tree.

## Pre-flight (automated — done by orchestrator)

- [x] `pyproject.toml` version bumped to `0.2.0`
- [x] `career_ops_kr/__init__.py` `__version__` bumped to `0.2.0`
- [x] `CHANGELOG.md` 0.2.0 entry dated 2026-04-11
- [x] `RELEASE_NOTES.md` drafted
- [x] `.gitattributes` with LF normalization
- [x] `git init` local repo
- [x] `git config user.name` / `user.email` set

## Publishing

- [ ] Create remote on GitHub: `pollmap/career-ops-kr` (public, MIT)
- [ ] Add remote: `git remote add origin git@github.com:pollmap/career-ops-kr.git`
- [ ] First push: `git push -u origin main`
- [ ] Create annotated tag: `git tag -a v0.2.0 -m "career-ops-kr v0.2.0"`
- [ ] Push tags: `git push origin v0.2.0`
- [ ] Create GitHub release from tag v0.2.0 using `RELEASE_NOTES.md` body

## Runtime Setup

- [ ] `uv sync` — install locked dependencies
- [ ] `uv run playwright install chromium` — browser binaries
- [ ] `uv pip install 'career-ops-kr[scrapling,tui]'` — optional extras
- [ ] `uv run career-ops --version` prints `0.2.0`

## First Real Run

- [ ] `uv run career-ops scan --tier 1` — scan Tier 1 official portals
- [ ] Review `data/scan_*.json` for real results (no mock data)
- [ ] `uv run career-ops pipeline --limit 1` — HITL single-candidate test
- [ ] Verify `data/applications.md` updated correctly

## Integrations

- [ ] Set `DISCORD_WEBHOOK_JOBS` in environment or `.auth/`
- [ ] Send test notification via HERMES bot to `#luxon-jobs`
- [ ] Register `career_ops_kr/mcp_server.py` into Nexus MCP catalog
- [ ] Verify MCP health: 10 tools visible in Nexus
- [ ] Confirm `vault_*` tool integration (if enabled)

## Sprint 4 Planning

- [ ] Schedule Sprint 4 kickoff
- [ ] Capture learnings from first live scan into `docs/sprint4/`
- [ ] Prioritize: MCP production flag vs TUI polish vs channel expansion
- [ ] Draft Sprint 4 PRD and add to `~/.claude/plans/`

## Notes

- HITL G5 (auto-submit) remains **permanently forbidden** — do not add
  any automation that submits applications without 찬희 approval.
- User layer files (`cv.md`, `config/*.yml`, `modes/_profile.md`, `data/*`)
  must never be overwritten by system upgrades.
