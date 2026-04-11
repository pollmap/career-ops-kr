"""Standalone rollback tool — restore SYSTEM layer from a backup snapshot.

This is a thin, user-facing wrapper around the restore logic in
:mod:`scripts.update_system`. Kept separate so 찬희 can roll back without
reading the larger update tool first.

Usage
-----
    python scripts/rollback.py              # interactive picker
    python scripts/rollback.py --latest     # restore newest snapshot
    python scripts/rollback.py --list       # list available snapshots

USER-layer files (``cv.md``, ``config/*.yml``, ``modes/_profile.md``,
``data/*``) are **never** touched — see ``_is_system_path`` in
``update_system``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Re-use the allowlist + restore helpers to guarantee identical semantics.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_system import (  # type: ignore
    BACKUP_DIR,
    _confirm,
    _list_backups,
    _restore_backup,
)

logger = logging.getLogger("rollback")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def _print_listing(backups: list[Path]) -> None:
    if not backups:
        logger.info("no backups found in %s", BACKUP_DIR)
        return
    logger.info("Backups under %s:", BACKUP_DIR)
    for i, b in enumerate(backups):
        file_count = sum(1 for _ in b.rglob("*") if _.is_file())
        logger.info("  [%d] %s (%d files)", i, b.name, file_count)


def _pick_backup(backups: list[Path], latest: bool) -> Path | None:
    if latest:
        return backups[0]
    _print_listing(backups)
    try:
        raw = input("Select index (blank = latest, q = quit): ").strip()
    except EOFError:
        return None
    if raw.lower() in {"q", "quit", "exit"}:
        return None
    if raw == "":
        return backups[0]
    try:
        idx = int(raw)
    except ValueError:
        logger.error("invalid index")
        return None
    if idx < 0 or idx >= len(backups):
        logger.error("out of range")
        return None
    return backups[idx]


def _diff_preview(backup: Path) -> None:
    logger.info("Files to be restored from %s:", backup.name)
    files = sorted(p.relative_to(backup).as_posix() for p in backup.rglob("*") if p.is_file())
    for path in files[:30]:
        logger.info("  %s", path)
    if len(files) > 30:
        logger.info("  ... and %d more", len(files) - 30)
    logger.info("total: %d files", len(files))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rollback")
    parser.add_argument("--latest", action="store_true", help="restore newest backup")
    parser.add_argument("--list", action="store_true", help="list backups and exit")
    args = parser.parse_args(argv)

    backups = _list_backups()
    if args.list:
        _print_listing(backups)
        return 0
    if not backups:
        logger.error("no backups available — run update_system.py apply first")
        return 1

    target = _pick_backup(backups, latest=bool(args.latest))
    if target is None:
        logger.info("aborted")
        return 1

    _diff_preview(target)
    if not _confirm("Restore SYSTEM layer from this backup? USER files will NOT be touched."):
        logger.info("aborted by user")
        return 1

    count = _restore_backup(target)
    logger.info("restored %d SYSTEM-layer files from %s", count, target.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
