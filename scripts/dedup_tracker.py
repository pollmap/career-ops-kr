"""Detect duplicate entries across data/applications.md and data/tracker-additions/*.tsv.

Composite key: (source_url, title+org+deadline). Uses fuzzywuzzy for near-duplicates
(threshold 85). Dry-run by default; pass --apply to actually deduplicate (future work,
currently read-only).

Usage:
    python scripts/dedup_tracker.py
    python scripts/dedup_tracker.py --threshold 90
    python scripts/dedup_tracker.py --apply    # would rewrite (NOT yet implemented)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

try:
    from fuzzywuzzy import fuzz
except ImportError:  # pragma: no cover
    fuzz = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATIONS_MD = PROJECT_ROOT / "data" / "applications.md"
ADDITIONS_DIR = PROJECT_ROOT / "data" / "tracker-additions"


def parse_markdown_table(path: Path) -> list[dict[str, str]]:
    """Parse a simple pipe-delimited markdown table. Returns list of row dicts."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    # lines[1] is the separator row (---|---|...)
    rows: list[dict[str, str]] = []
    for ln in lines[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def parse_tsv(path: Path) -> list[dict[str, str]]:
    """Parse a TSV file with header row."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for ln in lines[1:]:
        cells = ln.split("\t")
        if len(cells) != len(header):
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def load_all_rows() -> list[tuple[str, dict[str, str]]]:
    """Load rows from applications.md + all tracker-additions/*.tsv. Returns (source, row)."""
    rows: list[tuple[str, dict[str, str]]] = []
    for row in parse_markdown_table(APPLICATIONS_MD):
        rows.append(("applications.md", row))
    if ADDITIONS_DIR.exists():
        for tsv in sorted(ADDITIONS_DIR.glob("*.tsv")):
            for row in parse_tsv(tsv):
                rows.append((tsv.name, row))
    return rows


def composite_key(row: dict[str, str]) -> str:
    """Build normalized composite key for exact-match dedup."""
    url = (row.get("source_url") or row.get("url") or "").strip().lower()
    title = (row.get("title") or row.get("position") or "").strip().lower()
    org = (row.get("org") or row.get("company") or "").strip().lower()
    deadline = (row.get("deadline") or "").strip().lower()
    return f"{url}||{title}||{org}||{deadline}"


def fuzzy_duplicate(a: dict[str, str], b: dict[str, str], threshold: int) -> bool:
    """Return True if rows are near-duplicates above threshold."""
    if fuzz is None:
        return False
    combo_a = " ".join(str(a.get(k, "")) for k in ("title", "org", "company", "position"))
    combo_b = " ".join(str(b.get(k, "")) for k in ("title", "org", "company", "position"))
    if not combo_a.strip() or not combo_b.strip():
        return False
    return fuzz.token_set_ratio(combo_a, combo_b) >= threshold


def find_duplicates(
    entries: list[tuple[str, dict[str, str]]],
    threshold: int,
) -> tuple[list[list[int]], list[list[int]]]:
    """Return (exact_groups, fuzzy_groups) — lists of index groups."""
    exact: dict[str, list[int]] = {}
    for idx, (_src, row) in enumerate(entries):
        key = composite_key(row)
        exact.setdefault(key, []).append(idx)
    exact_groups = [idxs for idxs in exact.values() if len(idxs) > 1]

    fuzzy_groups: list[list[int]] = []
    visited: set[int] = set()
    for i, (_, row_i) in enumerate(entries):
        if i in visited:
            continue
        group = [i]
        for j in range(i + 1, len(entries)):
            if j in visited:
                continue
            if fuzzy_duplicate(row_i, entries[j][1], threshold):
                group.append(j)
                visited.add(j)
        if len(group) > 1:
            visited.update(group)
            fuzzy_groups.append(group)
    return exact_groups, fuzzy_groups


def report(
    entries: Iterable[tuple[str, dict[str, str]]], groups: list[list[int]], label: str
) -> None:
    entries_list = list(entries)
    print(f"\n=== {label} ===")
    if not groups:
        print("  (none)")
        return
    for gi, group in enumerate(groups, 1):
        print(f"  Group {gi} ({len(group)} rows):")
        for idx in group:
            src, row = entries_list[idx]
            title = row.get("title") or row.get("position") or "?"
            org = row.get("org") or row.get("company") or "?"
            print(f"    - [{src}] {org} / {title}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect duplicates across tracker sources.")
    parser.add_argument("--threshold", type=int, default=85, help="fuzzy match threshold (0-100)")
    parser.add_argument(
        "--apply", action="store_true", help="apply deduplication (not implemented yet)"
    )
    args = parser.parse_args(argv)

    if args.apply:
        print("[dedup] --apply is not yet implemented. Running dry-run only.", file=sys.stderr)

    entries = load_all_rows()
    print(f"Loaded {len(entries)} rows total")
    if not entries:
        return 0

    exact_groups, fuzzy_groups = find_duplicates(entries, args.threshold)
    report(entries, exact_groups, "Exact duplicates (composite key)")
    report(entries, fuzzy_groups, f"Fuzzy duplicates (ratio >= {args.threshold})")

    total_dupes = sum(len(g) - 1 for g in exact_groups + fuzzy_groups)
    print(f"\nSummary: {total_dupes} duplicate row(s) detected")
    return 0 if total_dupes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
