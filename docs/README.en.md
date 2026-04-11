# career-ops-kr (English)

> A Korean-first AI job-hunt automation agent — a Korean port of the
> `santifer/career-ops` philosophy for the finance/fintech/blockchain market,
> with multi-domain support via presets.
>
> A Luxon AI project · Claude Code native · Python-only stack · v0.2.0

> **Note on language**: This project is Korean-first. Most internal text
> (mode prompts, reports, CLI messages) is in Korean. This README translates
> the Korean version for international readers — the codebase itself is
> generalization-ready (see the 7 preset domains) and can be adopted outside
> Korea with new channel implementations.

---

## Why it exists — founder context

This tool was built by **이찬희 (pollmap / Luxon AI founder)** for his own job hunt:
a 3rd-year undergrad on leave from Chungbuk National University, juggling 5 certifications,
preparing for H2 internship applications in Korean finance.

The problem:

- Major Korean sites (`dataq.or.kr`, `license.kofia.or.kr`, Linkareer...) use
  **dynamic loading + login walls** — a standalone LLM cannot scrape them.
- Every program has different eligibility rules ("is a student-on-leave allowed?",
  "is a non-major allowed?", "do they require a graduation-expected student?").
  Eligibility checking becomes repetitive drudgery.
- Manually polling 74 target programs across 9 portals every week is unrealistic.
- Job hunting has to be run as a **pipeline** to survive.

Built for one person's real need, battle-tested, then open-sourced.

---

## Key features

- **16 Claude Code modes (v0.2)**
  - **Phase 1 (MVP)**: `scan` · `filter` · `score` · `pipeline` · `tracker` · `patterns` · `auto-pipeline`
  - **Phase 2**: `pdf` · `interview-prep` · `apply` · `followup` · `project` · `batch`
  - **Phase 3**: `training` · `deep` · `contacto`
  - **Korean localization**: `modes/kr/*`
- **9 + 9 channels** (MVP 9 + Sprint 3 stubs 9)
  - MVP: Linkareer, Jobalio, Work24 Youth, Shinhan Securities, Kiwoom KDA, KOFIA,
    DataQ, Bank of Korea, Wanted
- **Pluggable channel architecture** — RSS/API/requests → Scrapling → Playwright priority
- **Scrapling integration layer** (Sprint 2) — adaptive scraping
- **7 domain presets**: `finance` · `dev` · `design` · `marketing` · `research` · `public` · `edu`
- **User / System layer separation** — user customization files are preserved across system updates
- **HITL 5 gates** — auto-submission permanently forbidden; human confirmation on every critical decision
- **Obsidian Vault + SQLite dual storage**
- **Discord push notifications** via the HERMES bot to `#luxon-jobs`
- **MCP server wrapper** — exposes 10 tools so Nexus MCP can mount career-ops-kr
- **Textual TUI dashboard** — pipeline visualization in the terminal
- **LLM second-pass scorer** — resolves ambiguity in the D~B middle grades

---

## Domain support / Generalization

career-ops-kr was originally built for **Korean finance**, but the User/System
layer separation enforced by `CLAUDE.md` lets you keep the engine (`career_ops_kr/`)
unchanged and swap only the preset to cover other domains.

| preset_id | Domain | Representative portals | Main archetypes |
|-----------|--------|------------------------|-----------------|
| `finance` | Finance/Fintech/Blockchain (default) | Linkareer, Jobalio, DataQ, BOK, KOFIA | blockchain, fin-IT, research, fintech |
| `dev` | Software Engineering | Wanted, Programmers, Jumpit, JobKorea, Rocketpunch | backend, frontend, devops, ML |
| `design` | UX/UI / Product | Wanted, Designerss, Notefolio | UX, UI, product, visual |
| `marketing` | Digital marketing / Growth | Wanted, Superookie, Saramin | performance, content, brand, growth |
| `research` | Research / Data analysis | BOK, KDI, DataQ, KOSSDA | economics, policy, data science |
| `public` | Public sector / Government / Youth | Jobalio, Narailteo, Work24 | public agency, ministry |
| `edu` | Education / Edtech / Research assistant | School boards, Eduwill, Wanted | research asst, tutor, edtech |

---

## Installation

```bash
# Windows 11 / Ubuntu 24.04 / macOS
git clone https://github.com/pollmap/career-ops-kr.git
cd career-ops-kr
uv sync
uv run playwright install chromium
uv run career-ops --help
```

---

## Usage

```bash
# List presets
career-ops init --list-presets

# Initialize with a domain preset
career-ops init --preset dev
career-ops init --preset research
career-ops init --preset finance  # default

# Daily pipeline (MVP flow)
career-ops scan
career-ops filter
career-ops pipeline

# Phase 2 modes
career-ops interview-prep
career-ops pdf
career-ops followup

# MCP server (for Nexus MCP mounting)
python -m career_ops_kr.mcp_server

# TUI dashboard
career-ops ui
```

---

## Distribution model

- **Personal use**: original author's Windows 11 local install (finance preset)
- **Team**: Luxon AI members git clone and run `--preset <their domain>`
- **Open source**: community contributes `presets/*.yml` and channel impls via PR

---

## References

- [santifer/career-ops](https://github.com/santifer/career-ops) — original philosophy
- [Panniantong/Agent-Reach](https://github.com/Panniantong/Agent-Reach) — channel pattern
- `CLAUDE.md` — agent working rules (User/System separation, HITL gates)
- `CONTRIBUTING.md` — contribution guide
- `CHANGELOG.md` — version history

## License

MIT © 2026 이찬희 (Luxon AI)
