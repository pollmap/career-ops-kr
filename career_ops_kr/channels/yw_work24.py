"""Youth-Work24 channel — 청년일경험포털 (yw.work24.go.kr).

Backend: ``requests``.

The real portal is auth-gated and JS-heavy. This implementation performs a
minimal public probe and returns any publicly visible listings that can be
parsed without session cookies. On failure it returns an empty list plus a
populated ``fetch_errors`` field where applicable — it never fabricates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord

LANDING_URL = "https://yw.work24.go.kr/"
from career_ops_kr._constants import DEFAULT_USER_AGENT as USER_AGENT  # noqa: E402


class YwWork24Channel(BaseChannel):
    """청년일경험포털 probe channel."""

    name = "yw_work24"
    tier = 2
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T2"

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
            self.logger.warning("yw_work24 check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        resp = self._retry(self._get_landing)
        if resp is None:
            self.logger.warning("yw_work24: landing fetch returned None")
            return []
        self.logger.info("yw_work24: HTTP %s", resp.status_code)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        # Defensive: the portal may render everything via JS. In that case
        # the listing containers will simply not exist.
        cards = soup.select("a[href*='recruit'], li.list-item, .recruit-card")
        results: list[JobRecord] = []
        now = datetime.now()
        for card in cards:
            title = card.get_text(strip=True)
            href = card.get("href") if hasattr(card, "get") else None
            if not title or not href:
                continue
            if str(href).startswith("/"):
                href = self.landing_url.rstrip("/") + str(href)
            try:
                record = JobRecord(
                    id=self._make_id(str(href), title),
                    source_url=str(href),  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org="청년일경험포털",
                    title=title[:200],
                    description=title,
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("yw_work24: skip invalid card: %s", exc)
                continue
            results.append(record)

        if not results:
            self.logger.info(
                "yw_work24: no publicly visible listings parsed (likely JS-gated).",
            )
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
            self.logger.warning("yw_work24 get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="청년일경험포털",
            title=url.rsplit("/", 1)[-1] or "청년일경험",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals ----------------------------------------------------------

    def _get_landing(self) -> requests.Response:
        self.logger.info("yw_work24: GET %s", self.landing_url)
        return requests.get(
            self.landing_url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
