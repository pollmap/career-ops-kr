"""Normalize legacy status values in data/applications.md to canonical enum.

Canonical enum (per templates/states.yml):
    inbox, eligible, rejected_self, applied, interview, offer,
    rejected_site, withdrawn

Legacy mappings (Korean + common variations):
    지원완료 / 지원함 / 제출 / submitted          -> applied
    서류합격 / 서류통과 / 1차합격                 -> interview
    면접 / 인터뷰 / 2차                          -> interview
    최종합격 / 합격 / 오퍼                        -> offer
    불합격 / 탈락 / 서류탈락 / 최종탈락            -> rejected_site
    자진철회 / 철회 / 지원취소                     -> withdrawn
    보류 / 홀드 / hold                           -> eligible
    관심 / 후보 / 관심공고                        -> eligible

Dry-run default. --apply to rewrite applications.md (backup created).

Usage:
    python scripts/normalize_statuses.py
    python scripts/normalize_statuses.py --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APPLICATIONS_MD = PROJECT_ROOT / "data" / "applications.md"

CANONICAL = {
    "inbox",
    "eligible",
    "rejected_self",
    "applied",
    "interview",
    "offer",
    "rejected_site",
    "withdrawn",
}

LEGACY_MAP: dict[str, str] = {
    # applied
    "지원완료": "applied",
    "지원함": "applied",
    "제출": "applied",
    "submitted": "applied",
    "submit": "applied",
    # interview
    "서류합격": "interview",
    "서류통과": "interview",
    "1차합격": "interview",
    "면접": "interview",
    "인터뷰": "interview",
    "2차": "interview",
    "interviewing": "interview",
    # offer
    "최종합격": "offer",
    "합격": "offer",
    "오퍼": "offer",
    "accepted": "offer",
    # rejected_site
    "불합격": "rejected_site",
    "탈락": "rejected_site",
    "서류탈락": "rejected_site",
    "최종탈락": "rejected_site",
    "rejected": "rejected_site",
    # withdrawn
    "자진철회": "withdrawn",
    "철회": "withdrawn",
    "지원취소": "withdrawn",
    # eligible
    "보류": "eligible",
    "홀드": "eligible",
    "hold": "eligible",
    "관심": "eligible",
    "후보": "eligible",
    "관심공고": "eligible",
    # rejected_self
    "자체기각": "rejected_self",
    "내가기각": "rejected_self",
}


def parse_table(text: str) -> tuple[list[str], list[list[str]], list[str]]:
    """Extract header, rows, and non-table lines from a markdown file.

    Returns (header, rows, trailing_or_prefix_lines). Trailing lines are kept
    separately so we can re-emit the file without losing context.
    """
    lines = text.splitlines()
    prefix: list[str] = []
    header: list[str] = []
    rows: list[list[str]] = []
    in_table = False
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not header:
                header = cells
                in_table = True
                continue
            if set(stripped.replace("|", "").replace("-", "").strip()) == set():
                # separator row (---|---|...) — skip
                continue
            if in_table:
                rows.append(cells)
        else:
            if not in_table:
                prefix.append(ln)
            # lines after table are discarded to keep scope small
    return header, rows, prefix


def find_status_col(header: list[str]) -> int:
    for i, col in enumerate(header):
        if col.strip().lower() in {"status", "상태"}:
            return i
    return -1


def normalize_value(raw: str) -> tuple[str, bool]:
    """Return (canonical, changed)."""
    v = raw.strip()
    if not v:
        return v, False
    if v in CANONICAL:
        return v, False
    lower = v.lower()
    if lower in CANONICAL:
        return lower, lower != v
    for legacy, canon in LEGACY_MAP.items():
        if legacy.lower() == lower:
            return canon, True
    # Unknown — leave as-is with a marker
    return v, False


def render(header: list[str], rows: list[list[str]], prefix: list[str]) -> str:
    out: list[str] = list(prefix)
    out.append("| " + " | ".join(header) + " |")
    out.append("| " + " | ".join("---" for _ in header) + " |")
    for row in rows:
        safe = [(c or "").replace("|", "\\|") for c in row]
        out.append("| " + " | ".join(safe) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize legacy status values.")
    parser.add_argument("--apply", action="store_true", help="write normalized file (with backup)")
    args = parser.parse_args(argv)

    if not APPLICATIONS_MD.exists():
        print(f"[skip] {APPLICATIONS_MD} not found.")
        return 0

    text = APPLICATIONS_MD.read_text(encoding="utf-8")
    header, rows, prefix = parse_table(text)
    if not header:
        print("[skip] No table found in applications.md.")
        return 0

    status_col = find_status_col(header)
    if status_col == -1:
        print("[skip] No 'status' column detected.")
        return 0

    diffs: list[tuple[int, str, str]] = []
    unknown: list[tuple[int, str]] = []
    new_rows: list[list[str]] = []
    for idx, row in enumerate(rows):
        if status_col >= len(row):
            new_rows.append(row)
            continue
        old = row[status_col]
        new, changed = normalize_value(old)
        if changed:
            diffs.append((idx, old, new))
        elif old and old not in CANONICAL:
            unknown.append((idx, old))
        updated = list(row)
        updated[status_col] = new
        new_rows.append(updated)

    print(f"Parsed {len(rows)} row(s). Changes: {len(diffs)}. Unknown values: {len(unknown)}.")
    for idx, old, new in diffs[:50]:
        print(f"  row {idx + 1}: '{old}' -> '{new}'")
    if len(diffs) > 50:
        print(f"  ... +{len(diffs) - 50} more")
    if unknown:
        print("\nUnknown values (left as-is — add to LEGACY_MAP if desired):")
        for idx, old in unknown[:20]:
            print(f"  row {idx + 1}: '{old}'")

    if not args.apply:
        print("\n[dry-run] Pass --apply to write.")
        return 0

    if not diffs:
        print("\nNo changes to write.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = APPLICATIONS_MD.with_suffix(f".md.bak.{stamp}")
    shutil.copy2(APPLICATIONS_MD, backup)
    rendered = render(header, new_rows, prefix)
    APPLICATIONS_MD.write_text(rendered, encoding="utf-8")
    print(f"\nWrote {APPLICATIONS_MD}. Backup: {backup.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
