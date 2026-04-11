"""Merge data/tracker-additions/*.tsv into data/applications.md.

STRICT RULES (Career-Ops invariants):
  1. NEVER edit existing rows in applications.md. Only append new rows.
  2. Dedup against existing rows before appending.
  3. Require HITL confirmation for each batch before writing.
  4. Dry-run is the default. Pass --apply to actually write.
  5. UTF-8 only. Use pathlib.

Usage:
    python scripts/merge_tracker.py                # dry-run, print plan
    python scripts/merge_tracker.py --apply        # interactive apply
    python scripts/merge_tracker.py --apply --yes  # non-interactive apply
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Support both direct script execution (`python scripts/merge_tracker.py`,
# where `scripts/` is on sys.path) and module import
# (`python -m scripts.merge_tracker` or `import scripts.merge_tracker`).
try:
    from dedup_tracker import (  # type: ignore[import-not-found]
        ADDITIONS_DIR,
        APPLICATIONS_MD,
        composite_key,
        parse_markdown_table,
        parse_tsv,
    )
except ImportError:  # pragma: no cover - alternate import path
    from scripts.dedup_tracker import (
        ADDITIONS_DIR,
        APPLICATIONS_MD,
        composite_key,
        parse_markdown_table,
        parse_tsv,
    )


def load_existing_keys() -> set[str]:
    """Return set of composite keys present in applications.md."""
    return {composite_key(row) for row in parse_markdown_table(APPLICATIONS_MD)}


def collect_additions() -> list[tuple[Path, list[dict[str, str]]]]:
    """Return list of (tsv_path, rows) for each file in tracker-additions/."""
    if not ADDITIONS_DIR.exists():
        return []
    out: list[tuple[Path, list[dict[str, str]]]] = []
    for tsv in sorted(ADDITIONS_DIR.glob("*.tsv")):
        out.append((tsv, parse_tsv(tsv)))
    return out


def filter_new_rows(
    batches: list[tuple[Path, list[dict[str, str]]]],
    existing_keys: set[str],
) -> list[tuple[Path, list[dict[str, str]]]]:
    """Drop rows whose composite key already exists. Preserve ordering."""
    seen = set(existing_keys)
    filtered: list[tuple[Path, list[dict[str, str]]]] = []
    for path, rows in batches:
        new_rows: list[dict[str, str]] = []
        for row in rows:
            key = composite_key(row)
            if key in seen:
                continue
            seen.add(key)
            new_rows.append(row)
        if new_rows:
            filtered.append((path, new_rows))
    return filtered


def render_markdown_rows(rows: list[dict[str, str]], header: list[str]) -> str:
    """Render rows as markdown table body lines (no header)."""
    lines = []
    for row in rows:
        cells = [str(row.get(col, "")).replace("|", "\\|").strip() for col in header]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def detect_header() -> list[str]:
    """Read header columns from existing applications.md."""
    if not APPLICATIONS_MD.exists():
        # Sensible default. Users can edit.
        return ["date", "org", "title", "source_url", "deadline", "status", "notes"]
    text = APPLICATIONS_MD.read_text(encoding="utf-8")
    for ln in text.splitlines():
        if ln.strip().startswith("|"):
            return [c.strip() for c in ln.strip("|").split("|")]
    return ["date", "org", "title", "source_url", "deadline", "status", "notes"]


def append_rows(rows: list[dict[str, str]], header: list[str]) -> None:
    """Append rendered rows to applications.md. Creates file+header if missing."""
    body = render_markdown_rows(rows, header)
    if not APPLICATIONS_MD.exists():
        APPLICATIONS_MD.parent.mkdir(parents=True, exist_ok=True)
        sep = "| " + " | ".join("---" for _ in header) + " |"
        head = "| " + " | ".join(header) + " |"
        content = f"{head}\n{sep}\n{body}\n"
        APPLICATIONS_MD.write_text(content, encoding="utf-8")
        return
    existing = APPLICATIONS_MD.read_text(encoding="utf-8")
    if not existing.endswith("\n"):
        existing += "\n"
    APPLICATIONS_MD.write_text(existing + body + "\n", encoding="utf-8")


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Merge tracker-additions into applications.md.")
    parser.add_argument("--apply", action="store_true", help="actually write (default: dry-run)")
    parser.add_argument("--yes", action="store_true", help="skip confirmations (requires --apply)")
    args = parser.parse_args(argv)

    batches = collect_additions()
    if not batches:
        print("No tracker-additions/*.tsv found. Nothing to merge.")
        return 0

    existing_keys = load_existing_keys()
    filtered = filter_new_rows(batches, existing_keys)

    if not filtered:
        print("All candidate rows already exist in applications.md. No merge needed.")
        return 0

    header = detect_header()
    total_new = sum(len(rows) for _, rows in filtered)
    print(f"Plan: append {total_new} new row(s) from {len(filtered)} file(s)")
    print(f"Target: {APPLICATIONS_MD}")
    for path, rows in filtered:
        print(f"  - {path.name}: {len(rows)} new row(s)")
        for row in rows[:3]:
            preview = row.get("title") or row.get("position") or "?"
            org = row.get("org") or row.get("company") or "?"
            print(f"      * {org} / {preview}")
        if len(rows) > 3:
            print(f"      ... +{len(rows) - 3} more")

    if not args.apply:
        print("\n[dry-run] Pass --apply to actually write.")
        return 0

    for path, rows in filtered:
        if not confirm(f"Append {len(rows)} row(s) from {path.name}?", args.yes):
            print(f"  [skipped] {path.name}")
            continue
        append_rows(rows, header)
        print(f"  [appended] {path.name}: {len(rows)} row(s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
