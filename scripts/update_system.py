"""System-layer update / rollback CLI.

Usage
-----
    python scripts/update_system.py check
    python scripts/update_system.py apply
    python scripts/update_system.py rollback [--latest]

Layer contract (from project CLAUDE.md §2)
------------------------------------------
* **SYSTEM layer** (auto-updatable):
    - ``career_ops_kr/**/*.py``
    - ``scripts/*.py``
    - ``modes/*.md`` **except** ``modes/_profile.md``
    - ``templates/*``
* **USER layer** (NEVER touched by this tool):
    - ``cv.md``
    - ``config/*.yml``
    - ``modes/_profile.md``
    - ``data/*``

Before apply we snapshot the entire SYSTEM layer to
``.backups/sys_<timestamp>/`` using ``shutil.copytree``. The ``rollback``
subcommand restores the most recent snapshot after explicit confirmation.

Git integration is optional: ``check`` prefers ``git fetch`` + ``git log``
if the project is a repo, otherwise reports "no git, manual update mode".
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import click  # type: ignore
except ImportError:  # pragma: no cover
    click = None  # type: ignore

logger = logging.getLogger("update_system")
logging.basicConfig(level=logging.INFO, format="%(message)s")


ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / ".backups"


# ---------------------------------------------------------------------------
# Layer allowlists
# ---------------------------------------------------------------------------

# Explicit allowlist — only paths matching these globs may be touched.
SYSTEM_GLOBS: tuple[str, ...] = (
    "career_ops_kr/**/*.py",
    "scripts/*.py",
    "templates/*.yml",
    "templates/*.html",
    "templates/*.md",
    "modes/*.md",
)

# Hard denylist — never touched, even if caught by a glob above.
USER_LAYER_DENY: frozenset[str] = frozenset(
    {
        "cv.md",
        "config/profile.yml",
        "config/portals.yml",
        "config/qualifier_rules.yml",
        "config/scoring_weights.yml",
        "modes/_profile.md",
    }
)

USER_LAYER_DENY_PREFIXES: tuple[str, ...] = (
    "data/",
    "config/",
    "reports/",
    "output/",
    ".backups/",
    ".auth/",
)


def _is_system_path(rel: Path) -> bool:
    """Return ``True`` if ``rel`` is in the SYSTEM allowlist and not denied."""
    rel_str = rel.as_posix()
    if rel_str in USER_LAYER_DENY:
        return False
    for prefix in USER_LAYER_DENY_PREFIXES:
        if rel_str.startswith(prefix):
            return False
    return any(rel.match(glob) for glob in SYSTEM_GLOBS)


def _iter_system_files(root: Path) -> list[Path]:
    """Enumerate SYSTEM-layer files under ``root`` (relative paths)."""
    out: list[Path] = []
    for glob in SYSTEM_GLOBS:
        for abs_path in root.glob(glob):
            if not abs_path.is_file():
                continue
            rel = abs_path.relative_to(root)
            if _is_system_path(rel):
                out.append(rel)
    return sorted(set(out))


# ---------------------------------------------------------------------------
# Git helpers (best-effort)
# ---------------------------------------------------------------------------


def _git(*args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except FileNotFoundError:
        return 127, "git not installed"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def _is_git_repo() -> bool:
    code, _ = _git("rev-parse", "--is-inside-work-tree")
    return code == 0


# ---------------------------------------------------------------------------
# Backup / restore
# ---------------------------------------------------------------------------


def _make_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"sys_{stamp}"
    target.mkdir(parents=True, exist_ok=False)
    files = _iter_system_files(ROOT)
    for rel in files:
        src = ROOT / rel
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    logger.info("backup: %d files → %s", len(files), target)
    return target


def _list_backups() -> list[Path]:
    if not BACKUP_DIR.exists():
        return []
    return sorted(
        (p for p in BACKUP_DIR.iterdir() if p.is_dir() and p.name.startswith("sys_")),
        reverse=True,
    )


def _restore_backup(backup: Path) -> int:
    """Restore all files from ``backup`` into SYSTEM paths. Returns count."""
    count = 0
    for src in backup.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(backup)
        if not _is_system_path(rel):
            logger.warning("restore: skipping non-SYSTEM path %s", rel)
            continue
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Diff pretty-printing
# ---------------------------------------------------------------------------


def _print_delta(files: list[Path]) -> None:
    logger.info("SYSTEM-layer files that would be updated (%d):", len(files))
    for rel in files[:50]:
        logger.info("  %s", rel.as_posix())
    if len(files) > 50:
        logger.info("  ... and %d more", len(files) - 50)


def _confirm(prompt: str) -> bool:
    if click is not None:
        return bool(click.confirm(prompt, default=False))
    resp = input(f"{prompt} [y/N]: ").strip().lower()
    return resp in {"y", "yes"}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_check() -> int:
    logger.info("career-ops-kr update check")
    files = _iter_system_files(ROOT)
    logger.info("SYSTEM layer: %d files tracked", len(files))
    if _is_git_repo():
        code, out = _git("fetch", "--dry-run")
        logger.info("git fetch --dry-run: %s", "ok" if code == 0 else out[:200])
        code, out = _git("status", "-sb")
        logger.info("git status:\n%s", out or "(clean)")
        code, out = _git("log", "..@{u}", "--oneline")
        if code == 0 and out:
            logger.info("Remote is ahead:\n%s", out)
        else:
            logger.info("Remote is in sync or unreachable")
    else:
        logger.info("no git repo detected — manual update only")
    return 0


def cmd_apply() -> int:
    logger.info("career-ops-kr update apply")
    files = _iter_system_files(ROOT)
    _print_delta(files)
    if not _confirm("Proceed with backup + update?"):
        logger.info("aborted by user")
        return 1
    backup = _make_backup()
    logger.info("backup stored at %s", backup)
    if _is_git_repo():
        code, out = _git("pull", "--ff-only")
        if code != 0:
            logger.error("git pull failed:\n%s", out)
            logger.error("rollback available: python scripts/update_system.py rollback")
            return 2
        logger.info("git pull:\n%s", out)
    else:
        logger.warning(
            "no git repo — nothing pulled. This tool only backs up; "
            "manual file replacement is up to the operator."
        )
    logger.info("update complete")
    return 0


def cmd_rollback(latest: bool = False) -> int:
    backups = _list_backups()
    if not backups:
        logger.error("no backups found in %s", BACKUP_DIR)
        return 1
    if latest:
        target = backups[0]
    else:
        logger.info("Available backups:")
        for i, b in enumerate(backups):
            logger.info("  [%d] %s", i, b.name)
        try:
            idx = int(input("Select index: ").strip() or "0")
        except ValueError:
            logger.error("invalid selection")
            return 1
        if idx < 0 or idx >= len(backups):
            logger.error("out of range")
            return 1
        target = backups[idx]
    logger.info("will restore from %s", target)
    if not _confirm("Restore SYSTEM layer from this backup?"):
        logger.info("aborted")
        return 1
    count = _restore_backup(target)
    logger.info("restored %d files", count)
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="update_system")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="report what would change")
    sub.add_parser("apply", help="backup + pull")
    rb = sub.add_parser("rollback", help="restore latest/chosen backup")
    rb.add_argument("--latest", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "check":
        return cmd_check()
    if args.cmd == "apply":
        return cmd_apply()
    if args.cmd == "rollback":
        return cmd_rollback(latest=bool(args.latest))
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
