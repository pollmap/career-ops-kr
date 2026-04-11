"""One-shot audit for the verified programs fixture.

Checks the following:
    1. Schema - required fields present and non-empty.
    2. Duplicate ids + duplicate (org,name) pairs.
    3. Deadline sanity - no past dates (wrt a configurable cutoff).
    4. URL format - http/https, no whitespace.
    5. Archetype / tier / eligibility / grade distributions.
    6. Deadline range sanity.

Usage:
    uv run python scripts/audit_dataset.py [--cutoff YYYY-MM-DD] [--fixture PATH]

Prints a markdown-style report to stdout. Exit code:
    0  all clean
    1  WARN (quality issues, non-critical)
    2  FAIL (critical schema violations)
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

# Force stdout to UTF-8 on Windows so em-dashes etc. don't crash cp949 consoles.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "programs_verified_20260411.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "org",
    "tier",
    "backend",
    "source_url",
    "deadline",
    "status",
    "eligibility_expected",
    "archetype_expected",
    "fit_grade_expected",
)


def audit(fixture: Path, cutoff: date) -> int:
    text = fixture.read_text(encoding="utf-8")
    data = json.loads(text)
    programs = data["programs"]

    print("# Fixture audit")
    print(f"_file: {fixture.relative_to(REPO_ROOT)}_")
    print(f"_cutoff: {cutoff.isoformat()}_")
    print(f"_total: {len(programs)}_\n")

    fail = 0
    warn = 0

    # 1. Required fields
    missing: list[tuple[str, str]] = []
    for program in programs:
        for field_name in REQUIRED_FIELDS:
            if field_name not in program or program.get(field_name) in (None, ""):
                missing.append((program.get("id", "?"), field_name))
    if missing:
        fail += 1
        print(f"## 1. Required fields — FAIL ({len(missing)} missing)")
        for identifier, field_name in missing[:20]:
            print(f"- `{identifier}` missing `{field_name}`")
    else:
        print("## 1. Required fields — PASS")

    # 2. Duplicates
    ids = [p["id"] for p in programs]
    dup_ids = [i for i, count in Counter(ids).items() if count > 1]
    titles = [(p["org"], p["name"]) for p in programs]
    dup_titles = [t for t, count in Counter(titles).items() if count > 1]
    if dup_ids:
        fail += 1
        print(f"\n## 2a. Duplicate ids — FAIL ({dup_ids})")
    else:
        print("\n## 2a. Duplicate ids — PASS")
    if dup_titles:
        warn += 1
        print(f"## 2b. Duplicate (org, name) — WARN ({dup_titles})")
    else:
        print("## 2b. Duplicate (org, name) — PASS")

    # 3. Deadline sanity
    past: list[tuple[str, str]] = []
    invalid: list[tuple[str, str]] = []
    for program in programs:
        raw = program.get("deadline", "")
        try:
            parsed = date.fromisoformat(raw)
        except ValueError as exc:
            invalid.append((program["id"], f"{raw!r} — {exc}"))
            continue
        if parsed < cutoff:
            past.append((program["id"], raw))
    if invalid:
        fail += 1
        print(f"\n## 3a. Deadline parse — FAIL ({len(invalid)})")
        for identifier, detail in invalid[:10]:
            print(f"- `{identifier}`: {detail}")
    else:
        print("\n## 3a. Deadline parse — PASS")
    if past:
        warn += 1
        print(f"## 3b. Stale deadlines — WARN ({len(past)} < {cutoff.isoformat()})")
        for identifier, detail in past:
            print(f"- `{identifier}`: {detail}")
    else:
        print(f"## 3b. Stale deadlines — PASS (none < {cutoff.isoformat()})")

    # 4. URL format
    bad_urls: list[tuple[str, str]] = []
    for program in programs:
        url = program.get("source_url", "")
        if not isinstance(url, str):
            bad_urls.append((program["id"], repr(url)))
            continue
        if not (url.startswith("http://") or url.startswith("https://")) or " " in url:
            bad_urls.append((program["id"], url))
    if bad_urls:
        warn += 1
        print(f"\n## 4. URL format — WARN ({len(bad_urls)})")
        for identifier, detail in bad_urls[:10]:
            print(f"- `{identifier}`: {detail}")
    else:
        print("\n## 4. URL format — PASS")

    # 5. Distributions
    print("\n## 5. Distributions")
    arch = Counter(p.get("archetype_expected", "?") for p in programs)
    print(f"- archetype: {dict(arch)}")
    tier = Counter(p.get("tier", "?") for p in programs)
    print(f"- tier: {dict(tier)}")
    elig = Counter(p.get("eligibility_expected", "?") for p in programs)
    print(f"- eligibility: {dict(elig)}")
    grade = Counter(p.get("fit_grade_expected", "?") for p in programs)
    print(f"- fit_grade: {dict(grade)}")

    unknown_arch = [
        p["id"] for p in programs if p.get("archetype_expected") in (None, "", "UNKNOWN")
    ]
    if unknown_arch:
        warn += 1
        print(f"- UNKNOWN archetype — WARN ({len(unknown_arch)}): {unknown_arch[:10]}")

    # 6. Deadline range
    deadlines = sorted(p["deadline"] for p in programs if isinstance(p.get("deadline"), str))
    if deadlines:
        print(f"\n## 6. Deadline range: {deadlines[0]} -> {deadlines[-1]}")

    # Summary
    print("\n---")
    if fail:
        print(f"**Summary: FAIL ({fail} critical, {warn} warnings)**")
        return 2
    if warn:
        print(f"**Summary: WARN ({warn} warnings, 0 critical)**")
        return 1
    print("**Summary: PASS (clean)**")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="path to programs fixture json",
    )
    parser.add_argument(
        "--cutoff",
        type=date.fromisoformat,
        default=date(2026, 4, 12),
        help="date cutoff for stale deadline check (YYYY-MM-DD)",
    )
    args = parser.parse_args(argv)
    return audit(args.fixture, args.cutoff)


if __name__ == "__main__":
    sys.exit(main())
