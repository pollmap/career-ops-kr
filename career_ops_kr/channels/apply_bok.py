"""BOK Apply channel — 한국은행 채용 (apply.bok.or.kr).

Backend: ``requests``. Parses publicly visible recruit listings on the
landing page. Marked as ``legitimacy_tier="T1"`` (central bank, highest
trust). Returns empty list on any failure — never fabricates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://apply.bok.or.kr/"
USER_AGENT = "career-ops-kr/0.1 (+https://github.com/pollmap/career-ops-kr)"


class ApplyBokChannel(BaseChannel):
    """한국은행 채용 portal scraper."""

    name = "apply_bok"
    tier = 1
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
            self.logger.warning("apply_bok check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        resp = self._retry(self._get_landing)
        if resp is None or resp.status_code != 200:
            self.logger.warning(
                "apply_bok: landing fetch failed (status=%s)",
                getattr(resp, "status_code", "n/a"),
            )
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        # Primary selectors — table rows / notice list / recruit items.
        rows = soup.select(
            "table tr, .notice-list li, .recruit-item, ul.list li, .board-list tr, .boardList tr"
        )
        results: list[JobRecord] = []
        now = datetime.now()
        seen_hrefs: set[str] = set()

        def _emit(title: str, href: str) -> None:
            if not title or len(title) < 4 or len(title) > 300:
                return
            href_full = str(href).strip()
            # Drop non-navigational hrefs that would fail pydantic HttpUrl.
            if (
                not href_full
                or href_full.startswith("#")
                or href_full.lower().startswith("javascript")
            ):
                return
            if href_full.startswith("/"):
                href_full = self.landing_url.rstrip("/") + href_full
            if "://" not in href_full:
                return
            if href_full in seen_hrefs:
                return
            seen_hrefs.add(href_full)
            deadline = deadline_parser(title)
            try:
                results.append(
                    JobRecord(
                        id=self._make_id(href_full, title[:120]),
                        source_url=href_full,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org="한국은행",
                        title=title[:200],
                        deadline=deadline,
                        description=title,
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("apply_bok: skip row: %s", exc)

        for row in rows:
            title = row.get_text(" ", strip=True)
            link_tag = row.find("a") if hasattr(row, "find") else None
            href = (link_tag.get("href") if link_tag else None) or self.landing_url
            _emit(title, str(href))

        # Fallback: career-keyword anchors anywhere in the page (defensive
        # path used when the primary selectors do not match the live DOM).
        if not results:
            self.logger.info("apply_bok: primary selectors empty, trying anchor fallback")
            for anchor in soup.find_all("a"):
                text = (anchor.get_text(" ", strip=True) or "").strip()
                href_raw = anchor.get("href") or ""
                if not text or not href_raw:
                    continue
                if not any(kw in text for kw in ("채용", "공고", "모집", "인턴", "신입")):
                    continue
                _emit(text, str(href_raw))
                if len(results) >= 30:
                    break

        if not results:
            self.logger.info("apply_bok: no listings parsed from landing.")
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
            self.logger.warning("apply_bok get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="한국은행",
            title=url.rsplit("/", 1)[-1] or "한국은행 채용",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals ----------------------------------------------------------

    def _get_landing(self) -> requests.Response:
        self.logger.info("apply_bok: GET %s", self.landing_url)
        return requests.get(
            self.landing_url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
