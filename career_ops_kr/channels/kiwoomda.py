"""Kiwoom Digital Academy channel — kiwoomda.com.

Backend: ``requests``. Static single-page site. We only keep a fallback
JobRecord when the real landing page responds 200 AND actually contains
the site's brand string — otherwise return []. Never fabricate.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://kiwoomda.com/"
USER_AGENT = "career-ops-kr/0.1 (+https://github.com/pollmap/career-ops-kr)"
BRAND_MARKER = "키움 디지털 아카데미"


class KiwoomdaChannel(BaseChannel):
    """키움 디지털 아카데미 static-site scraper."""

    name = "kiwoomda"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, landing_url: str = LANDING_URL) -> None:
        super().__init__()
        self.landing_url = landing_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        try:
            resp = requests.get(
                self.landing_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.warning("kiwoomda check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        resp = self._retry(self._get_landing)
        if resp is None or resp.status_code != 200:
            self.logger.warning(
                "kiwoomda: landing fetch failed (status=%s)",
                getattr(resp, "status_code", "n/a"),
            )
            return []
        body = resp.text
        if BRAND_MARKER not in body:
            self.logger.info(
                "kiwoomda: brand marker %r not found — returning [] (no fabrication).",
                BRAND_MARKER,
            )
            return []

        soup = BeautifulSoup(body, "html.parser")
        results: list[JobRecord] = []
        now = datetime.now()

        # Try to find obvious apply/deadline blocks.
        for block in soup.find_all(["section", "div", "article"]):
            text = block.get_text(" ", strip=True)
            if not text or ("모집" not in text and "지원" not in text):
                continue
            match = re.search(r"([^.\n]{5,80}(모집|지원|마감)[^.\n]{0,40})", text)
            if not match:
                continue
            title = match.group(1).strip()
            deadline = deadline_parser(text)
            try:
                record = JobRecord(
                    id=self._make_id(self.landing_url, title),
                    source_url=self.landing_url,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org="키움 디지털 아카데미",
                    title=title[:200],
                    deadline=deadline,
                    description=text[:1500],
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("kiwoomda: skip block: %s", exc)
                continue
            results.append(record)
            if len(results) >= 5:  # single-page, bound the output
                break
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
            self.logger.warning("kiwoomda get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        if BRAND_MARKER not in resp.text:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="키움 디지털 아카데미",
            title="키움 디지털 아카데미 모집",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals ----------------------------------------------------------

    def _get_landing(self) -> requests.Response:
        self.logger.info("kiwoomda: GET %s", self.landing_url)
        return requests.get(
            self.landing_url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
