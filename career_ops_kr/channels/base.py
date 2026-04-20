"""Channel base module.

Defines the :class:`JobRecord` pydantic v2 model, the :class:`Channel`
Protocol, and :class:`BaseChannel` abstract helper that concrete channel
implementations subclass.

Invariants:
    - All network I/O goes through :meth:`BaseChannel._fetch` which applies
      exponential backoff (max 120s) and rate limiting.
    - On failure, list_jobs/get_detail return an empty list / None. Never
      fabricate records. Failures are appended to ``JobRecord.fetch_errors``
      where possible and logged via ``logging``.
    - All file I/O elsewhere in the package uses ``encoding='utf-8'`` and
      :class:`pathlib.Path`.
    - Date parsing + ID generation delegate to
      :mod:`career_ops_kr.parser.utils` (project-wide single source of truth).
      This module keeps thin wrappers for backwards-compat with the 14+
      channels that already import ``deadline_parser`` and call
      ``BaseChannel._make_id``.
"""

from __future__ import annotations

import logging
import random
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl

logger = logging.getLogger(__name__)


def can_fetch(url: str, user_agent: str = "*") -> bool:
    """Return True if the given URL is allowed for the user agent by robots.txt.

    Returns True on any error (unreachable robots.txt, DNS failure, etc.) so
    callers get a permissive default; they should still respect site ToS.

    Channels SHOULD gate their fetch logic on this helper when polling
    third-party sites that publish robots.txt.
    """
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
        rp.read()
        return rp.can_fetch(user_agent, url)
    except Exception:  # noqa: BLE001 — permissive fallback by design
        return True


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ChannelError(Exception):
    """Raised for unrecoverable channel errors.

    Channels should prefer returning empty results + logging, and only raise
    ``ChannelError`` on programmer errors (e.g. misconfiguration).
    """


# ---------------------------------------------------------------------------
# JobRecord
# ---------------------------------------------------------------------------


class JobRecord(BaseModel):
    """Canonical job-posting record shared across the pipeline.

    Attributes:
        id: 16-char SHA-256 prefix from ``generate_job_id`` — stable dedup key.
        source_url: Canonical URL of the posting.
        source_channel: Channel name (e.g. ``"jobalio"``).
        source_tier: 1..6 per portal tier system (1 = highest trust).
        org: Hiring organization.
        title: Job title.
        archetype: Filled by classifier (e.g. ``"INTERN"``). May be None.
        deadline: Application deadline if known.
        posted_at: Posted date if known.
        location: Free-text location.
        description: Full body text (plain, HTML-stripped).
        raw_html: Raw HTML kept for re-parsing if available.
        legitimacy_tier: ``T1`` (official) .. ``T5`` (unknown).
        scanned_at: UTC-naive datetime when scraped.
        fetch_errors: List of non-fatal error messages for debugging.
    """

    id: str
    source_url: HttpUrl
    source_channel: str
    source_tier: int = Field(ge=1, le=6)
    org: str
    title: str
    archetype: str | None = None
    deadline: date | None = None
    posted_at: date | None = None
    location: str | None = None
    description: str = ""
    raw_html: str | None = None
    legitimacy_tier: str = "T5"
    scanned_at: datetime = Field(default_factory=datetime.now)
    fetch_errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Korean date parser — thin wrapper over parser.utils.parse_korean_date
# ---------------------------------------------------------------------------


def deadline_parser(text: str) -> date | None:
    """Parse common Korean date formats into :class:`datetime.date`.

    Thin wrapper — the real implementation lives in
    :func:`career_ops_kr.parser.utils.parse_korean_date`. This wrapper
    exists so 14+ channels that import ``deadline_parser`` from
    ``career_ops_kr.channels.base`` keep working without edits.

    Supported forms:
        - ``2026.04.17`` / ``2026-04-17`` / ``2026/04/17``
        - ``2026년 4월 17일``
        - ``4/17(금)`` / ``4.17(금)``
        - ``4월 17일``
        - ``26.04.17`` (2-digit year auto-expanded to 20xx)
    """
    # Lazy import to avoid a parser ↔ channels circular dependency at module
    # load time. Python caches the module after the first call so the cost
    # is effectively zero from the second invocation onwards.
    from career_ops_kr.parser.utils import parse_korean_date

    return parse_korean_date(text)


# ---------------------------------------------------------------------------
# Channel Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Channel(Protocol):
    """Structural protocol every channel implementation must satisfy."""

    name: str
    tier: int
    backend: str

    def check(self) -> bool:
        """Return True if the upstream is reachable."""

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return a list of job postings. Empty list on failure."""

    def get_detail(self, url: str) -> JobRecord | None:
        """Return full detail for a single posting. None on failure."""


# ---------------------------------------------------------------------------
# BaseChannel — shared helpers
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Simple token-bucket style rate limiter (requests per minute)."""

    def __init__(self, per_minute: int = 10) -> None:
        self.per_minute = max(1, per_minute)
        self._window: list[float] = []

    def acquire(self) -> None:
        now = time.monotonic()
        cutoff = now - 60.0
        self._window = [t for t in self._window if t > cutoff]
        if len(self._window) >= self.per_minute:
            sleep_for = 60.0 - (now - self._window[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._window.append(time.monotonic())


class BaseChannel(ABC):
    """Abstract base with retry, rate limiting, and helper utilities.

    Concrete channels set ``name``, ``tier``, ``backend`` class attributes
    and implement :meth:`check`, :meth:`list_jobs`, :meth:`get_detail`.
    """

    name: str = "base"
    tier: int = 6
    backend: str = "requests"
    default_rate_per_minute: int = 10
    default_legitimacy_tier: str = "T5"

    def __init__(self, rate_per_minute: int | None = None) -> None:
        self._rate = _RateLimiter(rate_per_minute or self.default_rate_per_minute)
        self.logger = logging.getLogger(f"career_ops_kr.channels.{self.name}")

    # -- id helper ----------------------------------------------------------

    @staticmethod
    def _make_id(url: str, title: str) -> str:
        """Stable 16-char id — delegates to ``parser.utils.generate_job_id``.

        Kept as a static method so the 14+ channels that already call
        ``self._make_id(url, title)`` keep working without edits. The wrapper
        passes ``org=""`` so the resulting hash is **byte-identical** to the
        pre-refactor implementation (``sha256("url||title")[:16]``).
        """
        from career_ops_kr.parser.utils import generate_job_id

        return generate_job_id(url, title)

    # -- retry + rate limit -------------------------------------------------

    def _retry(
        self,
        fn: Any,
        *args: Any,
        max_attempts: int = 4,
        **kwargs: Any,
    ) -> Any:
        """Exponential backoff retry wrapper. Max 120s sleep per attempt."""
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                self._rate.acquire()
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                wait = min(120.0, (2**attempt) + random.random())
                self.logger.warning(
                    "%s attempt %d/%d failed: %s; sleeping %.1fs",
                    self.name,
                    attempt + 1,
                    max_attempts,
                    exc,
                    wait,
                )
                time.sleep(wait)
        if last_exc is not None:
            self.logger.error("%s: all %d attempts failed", self.name, max_attempts)
        return None

    # -- abstract API -------------------------------------------------------

    @abstractmethod
    def check(self) -> bool:
        """Upstream reachability probe."""

    @abstractmethod
    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return postings. MUST return ``[]`` on any failure."""

    @abstractmethod
    def get_detail(self, url: str) -> JobRecord | None:
        """Return posting detail. MUST return ``None`` on failure."""
