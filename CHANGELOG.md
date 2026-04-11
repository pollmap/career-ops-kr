# Changelog

All notable changes to `career-ops-kr` are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-11

### Added

#### Sprint 2 — Generalization + Scraping upgrade
- Scrapling integration layer (`career_ops_kr/channels/_scrapling_base.py`) for
  adaptive scraping with fallback to Playwright.
- Slash-scrape proxy (`_slash_scrape_proxy.py`) bridging Scrapling sessions.
- Archetype YAML externalization (`config/archetypes.yml`) — archetypes now
  defined as data, not code.
- 7 domain presets under `presets/*.yml`: `finance`, `dev`, `design`,
  `marketing`, `research`, `public`, `edu`.
- `career-ops init --preset <id>` CLI flag (backwards compatible: plain `init`
  still runs the Sprint 1 interactive flow).
- `--list-presets` flag to enumerate available domains.
- `docs/generalization.md`, `docs/presets.md`, `docs/adding-a-preset.md`.

#### Sprint 3 — Phase 2 + Phase 3 modes, MCP, TUI, Open Source prep
- **Phase 2 modes** (6): `pdf`, `interview-prep`, `apply`, `followup`,
  `project`, `batch`.
- **Phase 3 modes** (3): `training`, `deep`, `contacto`.
- **Korean localization**: `modes/kr/_shared.md` — finance-locale overrides.
- **LLM 2nd-pass scorer**: ambiguous D~B range now refined with an LLM call
  when automated scoring confidence is low.
- **Legitimacy review queue**: T4 (news) / T5 (unknown) sources held for manual
  review instead of auto-ingested.
- **Update & rollback scripts**: `scripts/update-system.py`,
  `scripts/rollback.py` — preserve User layer across upgrades.
- **MCP server wrapper** (`career_ops_kr/mcp_server.py`): exposes 10 tools
  (scan, filter, score, pipeline, tracker, pdf, interview-prep, followup,
  project, deep) for mounting into Nexus MCP.
- **9 Tier 3-4 channel stubs**: placeholder classes so contributors can
  implement new portals without touching the base architecture.
- **Textual TUI dashboard** (`career_ops_kr/tui/`): terminal UI showing
  pipeline status, candidate cards, qualifier hits, deadline calendar.
- **Open source preparation**:
  - `LICENSE` (MIT)
  - `CONTRIBUTING.md` with User/System layer rules
  - `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
  - `.github/workflows/ci.yml` (Windows + Ubuntu × Python 3.11/3.12)
  - `.github/ISSUE_TEMPLATE/` (bug, feature, preset, channel)
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - Multi-language READMEs: `docs/README.ko.md`, `README.en.md`, `README.ja.md`
  - `llms.txt` for LLM-friendly context
  - `CHANGELOG.md` (this file)
  - `SPRINT3_SUMMARY.md`

### Changed
- Version bumped from `0.1.0` to `0.2.0` in `pyproject.toml`.
- `career_ops_kr/channels/base.py` Channel Protocol documented with Scrapling path.
- README.md updated with v0.2 feature list.

### Notes
- User layer files (`cv.md`, `config/*.yml`, `modes/_profile.md`, `data/*`)
  untouched by Sprint 2 and Sprint 3. Safe to upgrade.
- HITL G5 (auto-submit) remains permanently forbidden.

## [0.1.0] - 2026-04-11

### Added
- Sprint 1 MVP: 71 files.
- **7 modes**: `scan`, `filter`, `score`, `pipeline`, `tracker`, `patterns`,
  `auto-pipeline`.
- **9 Korean portals**: Linkareer, Jobalio, Work24 Youth, Shinhan Securities,
  Kiwoom KDA, KOFIA, DataQ, Bank of Korea (apply_bok), Wanted.
- `qualifier` (Korean-specific rule engine), `archetype` classifier,
  `scorer` (A~F grading), `storage` (SQLite + Obsidian Vault dual).
- CLI: `career-ops` (click-based).
- Discord notifier (HERMES bot → `#luxon-jobs`).
- ICS calendar export for deadlines.
- `CLAUDE.md` with User/System layer separation and HITL 5 gates.
- Real 55-program regression test dataset (100% accuracy).
