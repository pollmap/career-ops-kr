# career-ops-kr v0.2.0 — Release Notes

**Release date:** 2026-04-11
**Codename:** Sprint 2 + Sprint 3 + Sprint 4 — Generalization, Phase 2/3 modes, Parser unification, Open Source

For the full changelog, see [CHANGELOG.md](CHANGELOG.md).

---

## Highlights

- **17 modes total** (7 MVP + 6 Phase 2 + 3 Phase 3 + `kr/` localized overrides)
  covering the full job-hunt lifecycle from `scan` to `followup` and `contacto`.
- **18 channels** — 9 MVP production (Linkareer, Jobalio, Work24 Youth,
  Shinhan Securities, Kiwoom KDA, KOFIA, DataQ, Bank of Korea, Wanted) +
  9 Tier 3-4 scaffolds (Mirae Asset, KB Securities, Hana Securities, NH,
  Samsung Securities, Dunamu, Bithumb, Toss, Lambda256).
- **7 domain presets** — `career-ops init --preset finance` onboards a new
  user in one command, no interactive interview required.
- **210-term Korean finance glossary** (`modes/kr/glossary.md`) for LLM
  2nd-pass scoring and domain disambiguation.
- **120 tests passing, 0 failures** across parser, channels, qualifier,
  archetype, scorer, CLI, TUI, MCP wrapper, and integration layers.
- **HITL 5 gates enforced** — onboarding, archetype change, tracker merge,
  batch evaluation, application submission (G5 permanently manual).
- **Scrapling integration** — adaptive HTML parsing with automatic fallback
  to Playwright on failure.
- **MCP server wrapper** — 10 Career Ops tools (`scan`, `filter`, `score`,
  `pipeline`, `tracker`, `pdf`, `interview-prep`, `followup`, `project`,
  `deep`) mountable into the Nexus MCP fabric via `career_ops_kr/mcp_server.py`.
- **Textual TUI dashboard** — pipeline status, candidate cards, qualifier
  hits, and a deadline calendar, all in the terminal.
- **Open source ready** — MIT license, contributor docs, CI matrix, issue
  and PR templates, multi-language READMEs.

## Sprint 4 Hardening (in-progress, included in v0.2.0 cut)

- **Parser unification** — `career_ops_kr/parser/` consolidated around
  `job_normalizer` with a shared `utils.py` for Korean date / deadline
  normalization; `tests/test_parser.py` rewired against the unified API.
- **CLI wiring fixes** — `career_ops_kr/cli.py` now correctly binds the
  `grade_cuts` signature to `scorer`, eliminating the Sprint 3 drift.
- **Channel Protocol cleanup** — `career_ops_kr/channels/base.py` tightened
  around the Scrapling-first path.
- **TUI `__init__` / `calendar/ics_export.py` / parser polish** — small
  quality fixes surfaced during the Sprint 4 audit.
- **Public repo preparation** — `.gitignore` now explicitly excludes
  User-layer files (`cv.md`, `config/profile.yml`, `modes/_profile.md`)
  so the public fork ships only System-layer engine + templates.

## New Modes (9 total)

| Phase | Mode | Purpose |
|-------|------|---------|
| 2 | `pdf` | Parse PDF announcements into candidate records |
| 2 | `interview-prep` | Company research + question bank |
| 2 | `apply` | Pre-fill application materials (HITL-only, never auto-submits) |
| 2 | `followup` | Draft follow-up emails after interview or application |
| 2 | `project` | Portfolio project-fit analysis |
| 2 | `batch` | Batch-run pipeline across many candidates |
| 3 | `training` | Training program / bootcamp discovery |
| 3 | `deep` | Deep-research mode using Exa + firecrawl MCPs |
| 3 | `contacto` | Contact / hiring-manager mapping |

Modes live under `career_ops_kr/modes/` and are bound via the click CLI in
`career_ops_kr/cli.py`.

## New Channels

Nine Tier 3-4 channel stubs were added under `career_ops_kr/channels/` so
contributors can extend portal coverage without touching the Channel
Protocol. The MVP production channels remain:
Linkareer, Jobalio, Work24 Youth, Shinhan Securities, Kiwoom KDA, KOFIA,
DataQ, Bank of Korea, Wanted.

## Scrapling Integration

- `career_ops_kr/channels/_scrapling_base.py` — shared base providing
  adaptive element selection with Playwright fallback.
- `career_ops_kr/channels/_slash_scrape_proxy.py` — bridge into the
  `/scrape` slash command so agents can reuse scraping sessions.
- Optional install: `pip install 'career-ops-kr[scrapling]'`.

## Preset System (7 domains)

Presets live in `presets/*.yml` and are consumed by `career-ops init --preset <id>`:

- `presets/finance.yml` — 찬희's original archetype set
- `presets/dev.yml` — software engineering
- `presets/design.yml` — UI/UX + product design
- `presets/marketing.yml` — marketing / growth / content
- `presets/research.yml` — research / academia
- `presets/public.yml` — public sector / civil service
- `presets/edu.yml` — education / tutoring

Archetype definitions are now externalized in `config/archetypes.yml`.
See `docs/generalization.md`, `docs/presets.md`, and
`docs/adding-a-preset.md` for authoring guidance.

## Breaking Changes

**None.** v0.2.0 is additive. All Sprint 1 CLI commands, config files,
and User-layer files are preserved unchanged.

## Upgrade Path

```bash
# 1. Pull latest
git pull origin main

# 2. Update dependencies
uv sync

# 3. (Optional) Install Scrapling / TUI extras
uv pip install 'career-ops-kr[scrapling,tui]'

# 4. Run the idempotent update script (preserves User layer)
uv run python scripts/update-system.py

# 5. Verify
uv run career-ops --version   # should print 0.2.0
```

To rollback: `uv run python scripts/rollback.py`.

## Known Issues

- Phase 3 `deep` mode requires external MCP servers (firecrawl, exa) that
  are not bundled — configure via `.mcp.json`.
- MCP server wrapper (`career_ops_kr/mcp_server.py`) is functional but has
  not yet been registered into production Nexus.
- TUI dashboard depends on Textual >= 0.80 (optional extra).
- `ics_export.py` still uses `datetime.utcnow()` in one path (Python 3.12
  deprecation warning); fix queued for v0.2.1.
- Tier 3-4 channel stubs (9 portals) require real-HTML selector tuning
  before producing live data.

## Next Sprint Preview

- Register `career_ops_kr/mcp_server.py` into Nexus MCP production.
- Enable real Discord webhook flow on successful `scan` runs.
- First live end-to-end run across the 9 production channels.
- Sprint 4 planning docs land in `docs/sprint4/`.
