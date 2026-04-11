#!/usr/bin/env bash
# sync_to_oss.sh — sync local private working copy → public fork.
#
# Usage:
#   scripts/sync_to_oss.sh                       # default src/dst
#   SRC=/path/to/private DST=/path/to/oss ./sync_to_oss.sh
#
# Behavior:
#   1. tar copy SRC → DST with sensitive files excluded (cv.md,
#      config/profile.yml, modes/_profile.md, data/, reports/, caches)
#   2. ``git add -A`` in DST and show cached diff stat
#   3. commit with message derived from the latest SRC commit
#   4. ``git push origin main``
#
# Safety:
#   - SRC and DST must both be existing directories.
#   - DST must be a git repo tracked to ``origin`` (the public fork).
#   - Never touches SRC's git history — SRC is the authoritative working
#     copy; DST is only the publishable mirror.
#
# Idempotency:
#   Running the script with no SRC changes produces a no-op commit attempt
#   (``nothing to commit`` + exit 0), so it's safe to re-run.

set -euo pipefail

SRC="${SRC:-$HOME/Desktop/career-ops-kr}"
DST="${DST:-$HOME/Desktop/career-ops-kr-oss}"

if [ ! -d "$SRC" ]; then
  echo "ERROR: SRC directory missing: $SRC" >&2
  exit 2
fi
if [ ! -d "$DST" ]; then
  echo "ERROR: DST directory missing: $DST" >&2
  echo "       Expected public fork working copy at $DST" >&2
  exit 2
fi
if [ ! -d "$DST/.git" ]; then
  echo "ERROR: DST is not a git repo: $DST" >&2
  exit 2
fi

echo "=== [1] tar copy $SRC -> $DST (sensitive files excluded) ==="
cd "$SRC"
tar \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./.mypy_cache' \
  --exclude='./.ruff_cache' \
  --exclude='./.pytest_cache' \
  --exclude='./data' \
  --exclude='./reports' \
  --exclude='./output' \
  --exclude='./.auth' \
  --exclude='./cv.md' \
  --exclude='./config/profile.yml' \
  --exclude='./modes/_profile.md' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='*.db-journal' \
  -cf - . | (cd "$DST" && tar -xf -)

echo ""
echo "=== [2] sensitive file verification (must all be 'excluded') ==="
for f in cv.md config/profile.yml modes/_profile.md; do
  if [ -f "$DST/$f" ]; then
    echo "  FAIL: $f was NOT excluded — aborting sync" >&2
    exit 3
  else
    echo "  OK   $f excluded"
  fi
done

echo ""
echo "=== [3] git diff in public fork ==="
cd "$DST"
git add -A
if git -c core.pager='' diff --cached --quiet; then
  echo "  no changes — nothing to sync"
  exit 0
fi
git -c core.pager='' diff --cached --stat | head -40

echo ""
echo "=== [4] commit + push ==="
LOCAL_MSG=$(git -C "$SRC" log -1 --pretty='%s' 2>/dev/null || echo "local updates")
git commit -m "sync: $LOCAL_MSG" 2>&1 | tail -5
git push origin main 2>&1 | tail -3
echo ""
echo "=== sync complete ==="
