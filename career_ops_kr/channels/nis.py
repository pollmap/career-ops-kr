"""NIS channel — 국가정보원 채용 (nis.go.kr).

Backend: ``requests``. Scrapes career listings from NIS public site.
Legitimacy: T1 (government agency).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://career.nis.go.kr:4017/"
from career_ops_kr._constants import DEFAULT_USER_AGENT as USER_AGENT  # noqa: E402


class NisChannel(BaseChannel):
    """국가정보원 채용 scraper."""

    name = "nis"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, landing_url: str = LANDING_URL) -> None:
        super().__init__()
        self.landing_url = landing_url

    def check(self) -> bool:
        try:
            resp = requests.get(
                self.landing_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
                verify=True,
            )
        except requests.RequestException:
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        resp = self._retry(self._get_landing)
        if resp is None or resp.status_code != 200:
            self.logger.warning("nis: landing fetch failed (status=%s)", getattr(resp, "status_code", "n/a"))
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select("table tr, .board-list tr, .boardList tr, ul.list li, .recruit-item, .notice-list li")
        results: list[JobRecord] = []
        now = datetime.now()
        seen: set[str] = set()

        def _emit(title: str, href: str) -> None:
            if not title or len(title) < 4 or len(title) > 300:
                return
            href_full = href.strip()
            if not href_full or href_full.startswith("#") or href_full.lower().startswith("javascript"):
                return
            if href_full.startswith("/"):
                href_full = "https://www.nis.go.kr" + href_full
            if "://" not in href_full:
                return
            if href_full in seen:
                return
            seen.add(href_full)
            try:
                results.append(JobRecord(
                    id=self._make_id(href_full, title[:120]),
                    source_url=href_full,
                    source_channel=self.name,
                    source_tier=self.tier,
                    org="국가정보원",
                    title=title[:200],
                    deadline=deadline_parser(title),
                    description=title,
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                ))
            except Exception as exc:
                self.logger.warning("nis: skip row: %s", exc)

        for row in rows:
            title = row.get_text(" ", strip=True)
            link = row.find("a") if hasattr(row, "find") else None
            href = (link.get("href") if link else None) or self.landing_url
            _emit(title, str(href))

        if not results:
            self.logger.info("nis: primary selectors empty, trying anchor fallback")
            for anchor in soup.find_all("a"):
                text = (anchor.get_text(" ", strip=True) or "").strip()
                href_raw = anchor.get("href") or ""
                if not text or not href_raw:
                    continue
                if any(kw in text for kw in ("채용", "공고", "모집", "인턴", "신입", "경력", "지원")):
                    _emit(text, str(href_raw))
                    if len(results) >= 30:
                        break

        return results

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            resp = self._retry(requests.get, url, headers={"User-Agent": USER_AGENT}, timeout=15)
        except Exception:
            return None
        if resp is None or resp.status_code != 200:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,
            source_channel=self.name,
            source_tier=self.tier,
            org="국가정보원",
            title="국가정보원 채용",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    def _get_landing(self) -> requests.Response:
        return requests.get(self.landing_url, headers={"User-Agent": USER_AGENT}, timeout=15, verify=True)
