"""Jobalio channel — 공공기관 채용정보 (job.alio.go.kr).

Backend: ``rss`` (primary) with ``requests`` fallback.

Notes:
    - The RSS URL at construction time is a best-effort; if upstream changes
      its feed path we log a warning and return an empty list rather than
      fabricating records.
    - Records are marked ``legitimacy_tier="T1"`` because ALIO is an
      official public-agency recruitment portal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import feedparser
import requests

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

RSS_URL = "https://job.alio.go.kr/rss/recruit.xml"
LANDING_URL = "https://job.alio.go.kr/recruit.do"
USER_AGENT = "career-ops-kr/0.1 (+https://github.com/pollmap/career-ops-kr)"


class JobalioChannel(BaseChannel):
    """공공기관 채용정보 (ALIO) RSS/HTML scraper."""

    name = "jobalio"
    tier = 1
    backend = "rss"
    default_rate_per_minute = 12
    default_legitimacy_tier = "T1"

    def __init__(self, rss_url: str = RSS_URL) -> None:
        super().__init__()
        self.rss_url = rss_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        try:
            resp = requests.get(
                self.rss_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.warning("jobalio check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return jobs from RSS.

        Args:
            query: Optional filter dict. Recognised keys:
                ``type``: if ``"intern"``, keep only postings containing
                ``인턴`` in title/description.
        """
        query = query or {}
        parsed = self._retry(self._fetch_rss)
        if parsed is None:
            return []

        if not getattr(parsed, "entries", None):
            self.logger.warning(
                "jobalio RSS returned no entries (url=%s). Structure may have changed.",
                self.rss_url,
            )
            return []

        results: list[JobRecord] = []
        now = datetime.now()
        for entry in parsed.entries:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            summary = (getattr(entry, "summary", "") or "").strip()
            org = (getattr(entry, "author", "") or "").strip() or "공공기관"

            if not title or not link:
                continue

            posted_at = None
            if getattr(entry, "published_parsed", None):
                try:
                    posted_at = datetime(*entry.published_parsed[:6]).date()
                except (TypeError, ValueError):
                    posted_at = None

            deadline = deadline_parser(summary) or deadline_parser(title)

            if query.get("type") == "intern":
                blob = f"{title} {summary}"
                if "인턴" not in blob:
                    continue

            try:
                record = JobRecord(
                    id=self._make_id(link, title),
                    source_url=link,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org=org,
                    title=title,
                    archetype="INTERN" if "인턴" in title else None,
                    deadline=deadline,
                    posted_at=posted_at,
                    description=summary,
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("jobalio: bad entry %r: %s", title, exc)
                continue
            results.append(record)
        return results

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            resp = self._retry(
                requests.get,
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
        except Exception as exc:
            self.logger.warning("jobalio get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        body = resp.text
        title = url.rsplit("/", 1)[-1]
        return JobRecord(
            id=self._make_id(url, title),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="공공기관",
            title=title,
            description=body[:4000],
            raw_html=body,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals ----------------------------------------------------------

    def _fetch_rss(self) -> Any:
        self.logger.info("jobalio: fetching RSS %s", self.rss_url)
        return feedparser.parse(
            self.rss_url,
            request_headers={"User-Agent": USER_AGENT},
        )
