"""Health check for the career-ops-kr pipeline.

Checks:
    1. All files in data/*.md have valid frontmatter (if frontmatter block present).
    2. SQLite schema matches expected table/column set.
    3. No orphan Vault notes (present in Vault, not in SQLite).
    4. No orphan SQLite rows (present in DB, no Vault note).
    5. All portals in config/portals.yml reachable (HTTP HEAD / GET).
    6. .auth/*.json session files not older than 30 days.

Output: markdown report to stdout, exit code:
    0  all PASS
    1  WARN (non-critical issues)
    2  FAIL (critical issues)

Usage:
    python scripts/verify_pipeline.py
    python scripts/verify_pipeline.py --skip-network
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
VAULT_DIR = PROJECT_ROOT / "Vault"
CONFIG_DIR = PROJECT_ROOT / "config"
AUTH_DIR = PROJECT_ROOT / ".auth"
DB_PATH = PROJECT_ROOT / "data" / "career_ops.db"

EXPECTED_TABLES = {"jobs", "job_history", "scan_log"}
EXPECTED_JOBS_COLUMNS = {
    "id",
    "source",
    "external_id",
    "source_url",
    "title",
    "org",
    "deadline",
    "status",
    "created_at",
    "updated_at",
    "last_reason",
}


@dataclass
class CheckResult:
    name: str
    level: str  # PASS | WARN | FAIL
    detail: str = ""
    items: list[str] = field(default_factory=list)


def check_frontmatter() -> CheckResult:
    r = CheckResult(name="1. Markdown frontmatter", level="PASS")
    if not DATA_DIR.exists():
        r.level = "WARN"
        r.detail = "data/ directory missing"
        return r
    bad: list[str] = []
    for md in DATA_DIR.rglob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad.append(f"{md.name}: not utf-8")
            continue
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end == -1:
                bad.append(f"{md.name}: unterminated frontmatter")
    if bad:
        r.level = "WARN"
        r.detail = f"{len(bad)} file(s) with frontmatter issues"
        r.items = bad
    else:
        r.detail = "all markdown files OK"
    return r


def check_sqlite_schema() -> CheckResult:
    r = CheckResult(name="2. SQLite schema", level="PASS")
    if not DB_PATH.exists():
        r.level = "WARN"
        r.detail = f"{DB_PATH.name} not found (pipeline not initialized)"
        return r
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
            missing_tables = EXPECTED_TABLES - tables
            if missing_tables:
                r.level = "FAIL"
                r.detail = f"missing tables: {sorted(missing_tables)}"
                return r
            if "jobs" in tables:
                cur.execute("PRAGMA table_info(jobs)")
                cols = {row[1] for row in cur.fetchall()}
                missing_cols = EXPECTED_JOBS_COLUMNS - cols
                if missing_cols:
                    r.level = "FAIL"
                    r.detail = f"jobs table missing columns: {sorted(missing_cols)}"
                    return r
            r.detail = f"tables={sorted(tables)}"
    except sqlite3.DatabaseError as exc:
        r.level = "FAIL"
        r.detail = f"sqlite error: {exc}"
    return r


def _list_vault_notes() -> set[str]:
    if not VAULT_DIR.exists():
        return set()
    return {p.stem for p in VAULT_DIR.rglob("*.md")}


def _list_db_stems() -> set[str]:
    if not DB_PATH.exists():
        return set()
    out: set[str] = set()
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'")
            if not cur.fetchone():
                return set()
            cur.execute("SELECT source, external_id FROM jobs")
            for source, ext in cur.fetchall():
                out.add(f"{source}__{ext}")
    except sqlite3.DatabaseError:
        return set()
    return out


def check_orphan_vault() -> CheckResult:
    r = CheckResult(name="3. Orphan Vault notes", level="PASS")
    vault = _list_vault_notes()
    db = _list_db_stems()
    if not vault and not db:
        r.level = "WARN"
        r.detail = "no Vault notes and no DB rows"
        return r
    orphans = sorted(vault - db)
    if orphans:
        r.level = "WARN"
        r.detail = f"{len(orphans)} vault note(s) without DB row"
        r.items = orphans[:20]
    else:
        r.detail = "no orphan Vault notes"
    return r


def check_orphan_db() -> CheckResult:
    r = CheckResult(name="4. Orphan DB rows", level="PASS")
    vault = _list_vault_notes()
    db = _list_db_stems()
    orphans = sorted(db - vault)
    if orphans:
        r.level = "WARN"
        r.detail = f"{len(orphans)} DB row(s) without Vault note"
        r.items = orphans[:20]
    else:
        r.detail = "no orphan DB rows"
    return r


def _parse_portals_yml(path: Path) -> list[tuple[str, str]]:
    """Return list of (name, url) from portals.yml. Stdlib-only parser."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    portals: list[tuple[str, str]] = []
    current_name = None
    current_url = None
    current_enabled = True
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0 and stripped.endswith(":"):
            if current_name and current_url and current_enabled:
                portals.append((current_name, current_url))
            current_name = stripped[:-1]
            current_url = None
            current_enabled = True
        elif indent > 0 and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key == "url":
                current_url = value
            elif key == "enabled":
                current_enabled = value.lower() == "true"
    if current_name and current_url and current_enabled:
        portals.append((current_name, current_url))
    return portals


def check_portals(skip_network: bool) -> CheckResult:
    r = CheckResult(name="5. Portal reachability", level="PASS")
    portals_yml = CONFIG_DIR / "portals.yml"
    portals = _parse_portals_yml(portals_yml)
    if not portals:
        r.level = "WARN"
        r.detail = "no enabled portals in config/portals.yml"
        return r
    if skip_network:
        r.detail = f"{len(portals)} portal(s) (network skipped)"
        return r
    failed: list[str] = []
    for name, url in portals:
        try:
            req = urllib.request.Request(
                url, method="HEAD", headers={"User-Agent": "career-ops-kr/0.1"}
            )
            urllib.request.urlopen(req, timeout=10)
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            failed.append(f"{name} ({url}): {exc}")
        time.sleep(0.5)
    if failed:
        r.level = "WARN"
        r.detail = f"{len(failed)}/{len(portals)} portal(s) unreachable"
        r.items = failed
    else:
        r.detail = f"all {len(portals)} portal(s) reachable"
    return r


def check_auth_sessions() -> CheckResult:
    r = CheckResult(name="6. Auth session age", level="PASS")
    if not AUTH_DIR.exists():
        r.level = "WARN"
        r.detail = ".auth/ directory missing (no sessions yet)"
        return r
    files = list(AUTH_DIR.glob("*.json"))
    if not files:
        r.level = "WARN"
        r.detail = "no session files in .auth/"
        return r
    now = datetime.now()
    old: list[str] = []
    for path in files:
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        if now - mtime > timedelta(days=30):
            old.append(f"{path.name}: {(now - mtime).days}d old")
        # Also sanity check it's valid JSON
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            old.append(f"{path.name}: invalid JSON")
    if old:
        r.level = "WARN"
        r.detail = f"{len(old)}/{len(files)} session file(s) stale or invalid"
        r.items = old
    else:
        r.detail = f"all {len(files)} session file(s) fresh"
    return r


def emit_markdown(results: list[CheckResult]) -> str:
    lines = ["# career-ops-kr pipeline verify"]
    lines.append(f"\n_run: {datetime.now().isoformat(timespec='seconds')}_\n")
    lines.append("| # | Check | Level | Detail |")
    lines.append("|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r.name[0]} | {r.name[3:] if len(r.name) > 3 else r.name} | {r.level} | {r.detail} |"
        )
    for r in results:
        if r.items:
            lines.append(f"\n## {r.name}")
            for it in r.items:
                lines.append(f"- {it}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify career-ops-kr pipeline health.")
    parser.add_argument("--skip-network", action="store_true", help="skip portal HTTP checks")
    args = parser.parse_args(argv)

    results = [
        check_frontmatter(),
        check_sqlite_schema(),
        check_orphan_vault(),
        check_orphan_db(),
        check_portals(args.skip_network),
        check_auth_sessions(),
    ]
    print(emit_markdown(results))

    if any(r.level == "FAIL" for r in results):
        return 2
    if any(r.level == "WARN" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
