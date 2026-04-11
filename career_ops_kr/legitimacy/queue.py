"""Legitimacy review queue — manual inspection bucket for T4/T5 jobs.

Jobs tagged ``T4_NEWS`` or ``T5_UNKNOWN`` by :class:`LegitimacyVerifier`
have low auto-classification confidence. Instead of silently dropping
them or trusting the tier, we enqueue them here so 찬희 can batch-review
on a schedule.

Storage
-------
* ``data/legitimacy_queue.jsonl`` — pending items (one JSON object per
  line, UTF-8, append-only).
* ``data/legitimacy_resolved.jsonl`` — resolved items, appended when
  :meth:`ReviewQueue.resolve` is called.

Records are immutable once written; resolving just migrates a copy to
the resolved log with the new tier and notes attached. This makes the
queue tolerant to crash/interrupt — partial writes are recoverable by
truncating the last line.

No network, no external deps beyond stdlib + pydantic.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.legitimacy.verifier import Tier

logger = logging.getLogger(__name__)


DEFAULT_QUEUE_PATH = Path("data/legitimacy_queue.jsonl")
DEFAULT_RESOLVED_PATH = Path("data/legitimacy_resolved.jsonl")


# ---------------------------------------------------------------------------
# Record shape
# ---------------------------------------------------------------------------


class QueueRecord(BaseModel):
    """One row in the legitimacy review queue."""

    job_id: str
    source_url: str
    org: str
    title: str
    tier: str  # Tier enum value (T1..T5)
    reason: str
    enqueued_at: str  # ISO-8601
    resolved: bool = False
    resolved_at: str | None = None
    resolved_tier: str | None = None
    notes: str | None = None

    # Optional breadcrumbs for the reviewer.
    source_channel: str | None = None
    source_tier: int | None = Field(default=None, ge=1, le=6)


# ---------------------------------------------------------------------------
# ReviewQueue
# ---------------------------------------------------------------------------


class ReviewQueue:
    """Append-only JSONL queue for manual legitimacy review."""

    def __init__(
        self,
        queue_path: Path = DEFAULT_QUEUE_PATH,
        resolved_path: Path = DEFAULT_RESOLVED_PATH,
    ) -> None:
        self.queue_path = Path(queue_path)
        self.resolved_path = Path(resolved_path)
        self._ensure_parent(self.queue_path)
        self._ensure_parent(self.resolved_path)

    # ------------------------------------------------------------------
    # Enqueue / dequeue / list
    # ------------------------------------------------------------------
    def enqueue(
        self,
        job: JobRecord,
        tier: Tier,
        reason: str,
    ) -> QueueRecord:
        """Append a new review item for ``job``.

        Returns the stored :class:`QueueRecord`. Duplicate ``job_id`` is
        allowed (e.g. re-classified later) — dedup is the reviewer's job.
        """
        record = QueueRecord(
            job_id=job.id,
            source_url=str(job.source_url),
            org=job.org,
            title=job.title,
            tier=tier.value,
            reason=reason,
            enqueued_at=datetime.now().isoformat(timespec="seconds"),
            source_channel=job.source_channel,
            source_tier=job.source_tier,
        )
        self._append(self.queue_path, record)
        logger.info("ReviewQueue.enqueue: %s %s (%s)", job.id, tier.value, reason)
        return record

    def dequeue_next(self) -> dict[str, Any] | None:
        """Return the oldest still-pending item (FIFO) without removing it.

        The queue is append-only; items disappear from the pending view
        only after :meth:`resolve`. This method is a convenience for the
        reviewer CLI to grab "the next one to look at".
        """
        items = self.list_pending()
        if not items:
            return None
        return items[0]

    def list_pending(self) -> list[dict[str, Any]]:
        """Return every record with ``resolved=False``, oldest first."""
        resolved_ids = self._resolved_ids()
        pending: list[dict[str, Any]] = []
        for row in self._iter_rows(self.queue_path):
            if row.get("resolved"):
                continue
            if row.get("job_id") in resolved_ids:
                continue
            pending.append(row)
        return pending

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------
    def resolve(
        self,
        job_id: str,
        new_tier: Tier,
        notes: str,
    ) -> QueueRecord | None:
        """Mark ``job_id`` as reviewed with a new tier.

        The original queue file is never rewritten — instead, a copy of
        the most recent matching record is appended to the resolved log
        with ``resolved=True`` and the reviewer's notes attached.
        """
        original = self._find_latest(self.queue_path, job_id)
        if original is None:
            logger.warning("ReviewQueue.resolve: job_id %r not found", job_id)
            return None
        updated = original.model_copy(
            update={
                "resolved": True,
                "resolved_at": datetime.now().isoformat(timespec="seconds"),
                "resolved_tier": new_tier.value,
                "notes": notes,
            }
        )
        self._append(self.resolved_path, updated)
        logger.info("ReviewQueue.resolve: %s → %s", job_id, new_tier.value)
        return updated

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        """Return a summary dict: total pending + per-tier counts."""
        by_tier: dict[str, int] = {}
        pending = self.list_pending()
        for row in pending:
            tier = row.get("tier", "T5")
            by_tier[tier] = by_tier.get(tier, 0) + 1
        return {
            "pending_total": len(pending),
            "pending_by_tier": by_tier,
            "resolved_total": sum(1 for _ in self._iter_rows(self.resolved_path)),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_parent(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _append(path: Path, record: QueueRecord) -> None:
        line = json.dumps(record.model_dump(), ensure_ascii=False, separators=(",", ":"))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    @staticmethod
    def _iter_rows(path: Path):  # type: ignore[no-untyped-def]
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "ReviewQueue: skipping bad line %d in %s: %s",
                        idx,
                        path,
                        exc,
                    )

    def _resolved_ids(self) -> set[str]:
        return {
            row.get("job_id") for row in self._iter_rows(self.resolved_path) if row.get("job_id")
        }

    def _find_latest(self, path: Path, job_id: str) -> QueueRecord | None:
        latest: QueueRecord | None = None
        for row in self._iter_rows(path):
            if row.get("job_id") != job_id:
                continue
            try:
                latest = QueueRecord.model_validate(row)
            except Exception as exc:
                logger.debug("ReviewQueue: bad record skipped: %s", exc)
        return latest
