"""SQLite-backed job index for career-ops-kr.

Uses the ``sqlite3`` stdlib (no extra deps) with UTF-8 text mode.  Tables
are created idempotently on first use so the same database file can be
shared across runs / backed up / synced to Vault.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)


_SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        source_url TEXT NOT NULL UNIQUE,
        source_channel TEXT NOT NULL,
        source_tier INTEGER NOT NULL,
        org TEXT NOT NULL,
        title TEXT NOT NULL,
        archetype TEXT,
        deadline TEXT,
        posted_at TEXT,
        location TEXT,
        description TEXT,
        legitimacy_tier TEXT DEFAULT 'T5',
        scanned_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'inbox',
        fit_grade TEXT,
        fit_score REAL,
        eligible TEXT,
        fetch_errors TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        channel TEXT NOT NULL,
        count INTEGER NOT NULL,
        errors TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_fit_grade ON jobs(fit_grade)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_channel ON jobs(source_channel)",
)


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    return value.isoformat()


class SQLiteStore:
    """Thin repository around a SQLite file."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        default = repo_root / "data" / "jobs.db"
        self.db_path: Path = Path(db_path) if db_path else default
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            for stmt in _SCHEMA:
                conn.execute(stmt)
            conn.commit()

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(self, job: JobRecord, fit: Any | None = None) -> bool:
        """Insert or replace ``job``.

        ``fit`` is expected to have attributes ``grade: str`` and
        ``score: float`` and ``eligible: bool``; a plain dict with the same
        keys also works.  Returns ``True`` if the row was new.
        """
        fit_grade = None
        fit_score = None
        eligible_str = None
        if fit is not None:
            fit_grade = _getattr_or_key(fit, "grade")
            fit_score = _getattr_or_key(fit, "score")
            eligible_val = _getattr_or_key(fit, "eligible")
            if eligible_val is not None:
                eligible_str = "true" if bool(eligible_val) else "false"

        errors_json = json.dumps(job.fetch_errors or [], ensure_ascii=False)

        with self._connect() as conn:
            cur = conn.execute(
                "SELECT 1 FROM jobs WHERE id = ? OR source_url = ?",
                (job.id, str(job.source_url)),
            )
            is_new = cur.fetchone() is None
            conn.execute(
                """
                INSERT INTO jobs (
                    id, source_url, source_channel, source_tier, org, title,
                    archetype, deadline, posted_at, location, description,
                    legitimacy_tier, scanned_at, status, fit_grade, fit_score,
                    eligible, fetch_errors
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,
                    COALESCE((SELECT status FROM jobs WHERE id = ?), 'inbox'),
                    ?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    source_url=excluded.source_url,
                    source_channel=excluded.source_channel,
                    source_tier=excluded.source_tier,
                    org=excluded.org,
                    title=excluded.title,
                    archetype=excluded.archetype,
                    deadline=excluded.deadline,
                    posted_at=excluded.posted_at,
                    location=excluded.location,
                    description=excluded.description,
                    legitimacy_tier=excluded.legitimacy_tier,
                    scanned_at=excluded.scanned_at,
                    fit_grade=COALESCE(excluded.fit_grade, jobs.fit_grade),
                    fit_score=COALESCE(excluded.fit_score, jobs.fit_score),
                    eligible=COALESCE(excluded.eligible, jobs.eligible),
                    fetch_errors=excluded.fetch_errors
                """,
                (
                    job.id,
                    str(job.source_url),
                    job.source_channel,
                    int(job.source_tier),
                    job.org,
                    job.title,
                    job.archetype,
                    _iso(job.deadline),
                    _iso(job.posted_at),
                    job.location,
                    job.description,
                    job.legitimacy_tier,
                    _iso(job.scanned_at),
                    job.id,
                    fit_grade,
                    fit_score,
                    eligible_str,
                    errors_json,
                ),
            )
            conn.commit()
        return is_new

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_by_grade(self, grade: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE fit_grade = ? ORDER BY fit_score DESC",
                (grade,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_upcoming_deadlines(self, days: int = 7) -> list[dict[str, Any]]:
        today = date.today().isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM jobs
                WHERE deadline IS NOT NULL
                  AND deadline >= ?
                  AND julianday(deadline) - julianday(?) <= ?
                ORDER BY deadline ASC
                """,
                (today, today, int(days)),
            ).fetchall()
        return [dict(r) for r in rows]

    def search(self, keyword: str, archetype: str | None = None) -> list[dict[str, Any]]:
        like = f"%{keyword}%"
        sql = "SELECT * FROM jobs WHERE (title LIKE ? OR description LIKE ? OR org LIKE ?)"
        params: list[Any] = [like, like, like]
        if archetype:
            sql += " AND archetype = ?"
            params.append(archetype)
        sql += " ORDER BY scanned_at DESC LIMIT 200"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            by_status = {
                r["status"]: r["n"]
                for r in conn.execute("SELECT status, COUNT(*) AS n FROM jobs GROUP BY status")
            }
            by_grade = {
                r["fit_grade"] or "ungraded": r["n"]
                for r in conn.execute(
                    "SELECT fit_grade, COUNT(*) AS n FROM jobs GROUP BY fit_grade"
                )
            }
            recent_scans = [
                dict(r) for r in conn.execute("SELECT * FROM scan_log ORDER BY id DESC LIMIT 10")
            ]
        return {
            "total": total,
            "by_status": by_status,
            "by_grade": by_grade,
            "recent_scans": recent_scans,
        }

    # ------------------------------------------------------------------
    # Scan logging
    # ------------------------------------------------------------------

    def log_scan(self, channel: str, count: int, errors: Iterable[str] | None = None) -> None:
        err_json = json.dumps(list(errors or []), ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO scan_log (timestamp, channel, count, errors) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), channel, int(count), err_json),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Status updates
    # ------------------------------------------------------------------

    def set_status(self, job_id: str, status: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
            conn.commit()
            return cur.rowcount > 0


def _getattr_or_key(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)
