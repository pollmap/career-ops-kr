"""Job normalizer — raw dict → validated :class:`JobRecord`.

Responsibilities:
    - HTML stripping + whitespace collapse
    - Korean date parsing via :func:`deadline_parser`
    - Stable id generation via SHA256(url+title)[:16]
    - Eligibility keyword extraction (재학생/졸업자/학력무관 etc.)
    - In-memory dedup across a batch

No network I/O. Pure transformation.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser

logger = logging.getLogger(__name__)


_WHITESPACE_RE = re.compile(r"[ \t\u00a0\u3000]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")

_ELIGIBILITY_KEYWORDS: tuple[str, ...] = (
    "졸업자",
    "졸업예정자",
    "재학생",
    "휴학생",
    "학력무관",
    "전공무관",
    "인턴",
    "신입",
    "경력",
    "청년",
    "만39세",
    "고졸",
    "대졸",
    "석사",
    "박사",
    "보훈",
    "장애인",
    "병역특례",
)


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

        job_id = self._make_id(url, title)
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
        """Return eligibility keywords found in ``text`` (dedup, order-preserved)."""
        if not text:
            return []
        found: list[str] = []
        seen: set[str] = set()
        for kw in _ELIGIBILITY_KEYWORDS:
            if kw in text and kw not in seen:
                found.append(kw)
                seen.add(kw)
        return found

    def reset_dedup(self) -> None:
        """Clear in-memory dedup cache between batches."""
        self._seen_ids.clear()

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _make_id(url: str, title: str) -> str:
        return hashlib.sha256(f"{url}||{title}".encode()).hexdigest()[:16]

    @staticmethod
    def _strip_html(text: str) -> str:
        if not text:
            return ""
        # BeautifulSoup gracefully handles plain text too.
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
