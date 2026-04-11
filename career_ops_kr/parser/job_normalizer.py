"""Job normalizer — raw dict → validated :class:`JobRecord`.

Responsibilities:
    - HTML stripping + whitespace collapse (BeautifulSoup for large bodies)
    - Korean date parsing via :func:`parser.utils.parse_korean_date`
    - Stable id generation via :func:`parser.utils.generate_job_id`
    - Eligibility keyword extraction via
      :func:`parser.utils.extract_eligibility_keywords`
    - In-memory dedup across a batch

No network I/O. Pure transformation.

All shared logic (date parsing, id hashing, eligibility lists) now lives
in :mod:`career_ops_kr.parser.utils` as the project-wide single source of
truth. This module focuses on the *orchestration* — assembling a validated
:class:`JobRecord` from a raw channel dict and handling the heavyweight
HTML-to-text conversion that is out of scope for ``parser.utils.clean_html``.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser
from career_ops_kr.parser.utils import (
    extract_eligibility_keywords as _extract_eligibility_keywords,
)
from career_ops_kr.parser.utils import (
    generate_job_id,
)

logger = logging.getLogger(__name__)


_WHITESPACE_RE = re.compile(r"[ \t\u00a0\u3000]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")


class JobNormalizer:
    """Normalize raw channel output into :class:`JobRecord`."""

    def __init__(self) -> None:
        self._seen_ids: set[str] = set()

    # -- public API ---------------------------------------------------------

    def normalize(self, raw: dict[str, Any]) -> JobRecord:
        """Convert raw dict → :class:`JobRecord`.

        Required keys in ``raw``:
            ``source_url``, ``source_channel``, ``source_tier``, ``org``,
            ``title``.

        Optional:
            ``description``, ``raw_html``, ``deadline``, ``posted_at``,
            ``location``, ``archetype``, ``legitimacy_tier``.
        """
        url = str(raw.get("source_url") or "").strip()
        title = self._clean_text(str(raw.get("title") or ""))
        if not url or not title:
            raise ValueError("JobNormalizer: source_url and title are required")

        description = self._strip_html(str(raw.get("description") or ""))
        deadline = raw.get("deadline")
        if isinstance(deadline, str):
            deadline = deadline_parser(deadline)
        posted_at = raw.get("posted_at")
        if isinstance(posted_at, str):
            posted_at = deadline_parser(posted_at)

        job_id = generate_job_id(url, title)
        if job_id in self._seen_ids:
            logger.debug("JobNormalizer: duplicate id %s (%s)", job_id, title)
        self._seen_ids.add(job_id)

        record = JobRecord(
            id=job_id,
            source_url=url,  # type: ignore[arg-type]
            source_channel=str(raw.get("source_channel") or "unknown"),
            source_tier=int(raw.get("source_tier") or 6),
            org=self._clean_text(str(raw.get("org") or "")),
            title=title,
            archetype=raw.get("archetype"),
            deadline=deadline,
            posted_at=posted_at,
            location=raw.get("location"),
            description=description,
            raw_html=raw.get("raw_html"),
            legitimacy_tier=str(raw.get("legitimacy_tier") or "T5"),
            scanned_at=raw.get("scanned_at") or datetime.now(),
            fetch_errors=list(raw.get("fetch_errors") or []),
        )
        return record

    def extract_eligibility_keywords(self, text: str) -> list[str]:
        """Return eligibility keywords found in ``text``.

        Thin instance-method wrapper over
        :func:`parser.utils.extract_eligibility_keywords` — kept for
        backwards compatibility with callers that already hold a
        ``JobNormalizer`` instance. New code should call the free function
        directly.
        """
        return _extract_eligibility_keywords(text)

    def reset_dedup(self) -> None:
        """Clear in-memory dedup cache between batches."""
        self._seen_ids.clear()

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _strip_html(text: str) -> str:
        """Heavy-duty HTML → plain text using BeautifulSoup.

        Distinct from :func:`parser.utils.clean_html` (regex-based, fast) —
        use this one for raw_html document bodies where nested structure
        and malformed markup are common.
        """
        if not text:
            return ""
        try:
            soup = BeautifulSoup(text, "html.parser")
            plain = soup.get_text("\n", strip=True)
        except Exception as exc:
            logger.debug("html strip failed: %s", exc)
            plain = text
        plain = plain.replace("\r\n", "\n").replace("\r", "\n")
        plain = _WHITESPACE_RE.sub(" ", plain)
        plain = _MULTINEWLINE_RE.sub("\n\n", plain)
        return plain.strip()

    @classmethod
    def _clean_text(cls, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = _WHITESPACE_RE.sub(" ", text)
        return text.strip()
