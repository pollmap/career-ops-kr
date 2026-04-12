"""Shinhan Investment & Securities recruitment channel.

Source: https://recruit.shinhansec.com/

Backend: ``requests`` + BeautifulSoup. Reachable without login; the listing
page is publicly accessible. The crawler walks every anchor on the landing
page, filters by Korean career keywords (블록체인/디지털자산/IT/핀테크/...),
and elevates 블록체인/디지털자산 keywords to the dedicated
``BLOCKCHAIN_INTERN`` archetype so downstream scorer can prioritise them.

Failure semantics
-----------------
- Network failure / non-200 → returns ``[]`` (list_jobs) or ``None`` (get_detail).
- HTML present but parsing yields zero records → returns ``[]`` with an info log.
- We **never** fabricate jobs — the project-wide invariant from CLAUDE.md.

Tier
----
신한투자증권 is a top-tier 증권사 (T1 legitimacy) but Korean 증권사 official
career sites historically rank as ``tier=3`` per the project portal-tier
system (1=정부, 2=공공, 3=대형 민간 등). Legitimacy stays ``T1`` because the
URL is the company-owned recruit subdomain.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LISTING_URL = "https://recruit.shinhansec.com/"
ORG = "신한투자증권"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    "career-ops-kr/0.2.0"
)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
}

KEYWORDS: tuple[str, ...] = (
    "블록체인",
    "디지털자산",
    "디지털",
    "IT",
    "핀테크",
    "크립토",
    "토큰",
    "STO",
    "개발",
    "데이터",
    "AI",
    "리서치",
)

BLOCKCHAIN_MARKERS: tuple[str, ...] = (
    "블록체인",
    "디지털자산",
    "STO",
    "크립토",
    "토큰",
)


class ShinhanSecChannel(BaseChannel):
    """신한투자증권 채용 공고 수집기 (requests backend)."""

    name = "shinhan_sec"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, listing_url: str = LISTING_URL) -> None:
        super().__init__()
        self.listing_url = listing_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe — GET the landing URL."""
        try:
            resp = requests.get(
                self.listing_url,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("shinhan_sec check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Fetch the landing page and parse keyword-matched anchors."""
        resp = self._retry(
            requests.get,
            self.listing_url,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        if resp is None:
            self.logger.warning("shinhan_sec: listing fetch failed — returning []")
            return []
        status = getattr(resp, "status_code", None)
        if status != 200:
            self.logger.warning(
                "shinhan_sec: listing returned status=%s — returning []",
                status,
            )
            return []
        # Force UTF-8 — Korean recruit pages routinely mis-declare encoding.
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        html = getattr(resp, "text", "") or ""

        try:
            jobs = self._parse_listing_html(html)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("shinhan_sec: parse error: %s", exc)
            return []

        if not jobs:
            self.logger.info(
                "shinhan_sec: no matching postings (kw=%s)",
                KEYWORDS,
            )
        return jobs

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch + parse a single detail page. Returns None on failure."""
        resp = self._retry(
            requests.get,
            url,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        if resp is None:
            return None
        status = getattr(resp, "status_code", None)
        if status != 200:
            self.logger.warning(
                "shinhan_sec: get_detail %s returned status=%s",
                url,
                status,
            )
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        html = getattr(resp, "text", "") or ""
        try:
            return self._parse_detail_html(html, url)
        except Exception as exc:
            self.logger.warning("shinhan_sec: parse detail failed %s: %s", url, exc)
            return None

    # -- Parsing ------------------------------------------------------------

    def _parse_listing_html(self, html: str) -> list[JobRecord]:
        """Walk every anchor, keep keyword matches, return JobRecord list."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[JobRecord] = []
        seen_urls: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            try:
                text = (anchor.get_text(" ", strip=True) or "").strip()
                if not text or len(text) < 4 or len(text) > 300:
                    continue
                if not any(kw in text for kw in KEYWORDS):
                    continue
                href_raw = anchor.get("href") or ""
                href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
                if not href or href.startswith("#") or href.lower().startswith("javascript"):
                    continue
                url = urljoin(self.listing_url, href)
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = text[:200]
                container = anchor.find_parent(["li", "tr", "div", "article", "section"])
                body_text = container.get_text(" ", strip=True) if container else text
                deadline = deadline_parser(body_text) or deadline_parser(title)
                archetype = self._infer_archetype(title)

                record = JobRecord(
                    id=self._make_id(url, title),
                    source_url=url,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org=ORG,
                    title=title,
                    archetype=archetype,
                    deadline=deadline,
                    location="서울",
                    description=body_text[:2000],
                    raw_html=None,
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
                jobs.append(record)
            except Exception as exc:
                self.logger.warning("shinhan_sec: skip bad anchor: %s", exc)
                continue
        return jobs

    def _parse_detail_html(self, html: str, url: str) -> JobRecord:
        """Parse a single detail page into a JobRecord."""
        soup = BeautifulSoup(html, "html.parser")
        title = (
            soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]
        ) or "신한투자증권 채용"
        title = title[:200]
        body = soup.get_text(" ", strip=True)[:5000]
        archetype = self._infer_archetype(title)

        return JobRecord(
            id=self._make_id(url, title),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org=ORG,
            title=title,
            archetype=archetype,
            deadline=deadline_parser(body) or deadline_parser(title),
            location="서울",
            description=body,
            raw_html=html[:50_000],
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- Tiny extractors ----------------------------------------------------

    @staticmethod
    def _infer_archetype(title: str) -> str | None:
        """Infer a coarse archetype from the title.

        Blockchain / digital-asset markers take priority — they map to the
        project-wide ``BLOCKCHAIN_INTERN`` archetype which the qualifier
        scores highest. Otherwise fall back to the standard
        INTERN/ENTRY/EXPERIENCED bucket.
        """
        if not title:
            return None
        if any(marker in title for marker in BLOCKCHAIN_MARKERS):
            return "BLOCKCHAIN_INTERN"
        if "인턴" in title or "intern" in title.lower():
            return "INTERN"
        if "신입" in title:
            return "ENTRY"
        if "경력" in title:
            return "EXPERIENCED"
        return None
