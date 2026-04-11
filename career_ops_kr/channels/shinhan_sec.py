"""Shinhan Investment & Securities recruitment channel.

Source: https://recruit.shinhansec.com/

Tier: 1 (공식 채용 사이트). Legitimacy: T1.
No login required; the listing page is publicly accessible. Filters for
블록체인/디지털자산/핀테크/IT keywords before returning :class:`JobRecord`.
If the page structure cannot be parsed we return ``[]`` with a fetch_errors
note — we NEVER fabricate jobs.

Backend selection
-----------------
Prefers :class:`ScraplingChannel` (fast :class:`scrapling.fetchers.Fetcher`)
when ``scrapling`` is importable; otherwise falls back to
:class:`PlaywrightChannel`. The two implementations expose identical
public methods so downstream code is agnostic.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser

logger = logging.getLogger(__name__)


LISTING_URL = "https://recruit.shinhansec.com/"
ORG = "신한투자증권"
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
)


# ---------------------------------------------------------------------------
# Shared parsing helpers (used by both backends)
# ---------------------------------------------------------------------------


def _parse_listing_html(html: str, make_id: Any) -> list[JobRecord]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[JobRecord] = []
    seen_urls: set[str] = set()

    for anchor in soup.find_all("a"):
        text = (anchor.get_text(" ", strip=True) or "").strip()
        if not text or len(text) < 4:
            continue
        if not any(kw in text for kw in KEYWORDS):
            continue
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.startswith("javascript"):
            continue
        url = urljoin(LISTING_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = text[:200]
        container = anchor.find_parent(["li", "tr", "div", "article"])
        body_text = container.get_text(" ", strip=True) if container else text
        deadline = deadline_parser(body_text)

        jobs.append(
            JobRecord(
                id=make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel="shinhan_sec",
                source_tier=1,
                org=ORG,
                title=title,
                archetype=None,
                deadline=deadline,
                location="서울",
                description=body_text[:2000],
                raw_html=None,
                legitimacy_tier="T1",
            )
        )
    return jobs


def _parse_detail_html(html: str, url: str, make_id: Any) -> JobRecord:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else url)[:200]
    body = soup.get_text(" ", strip=True)
    return JobRecord(
        id=make_id(url, title),
        source_url=url,  # type: ignore[arg-type]
        source_channel="shinhan_sec",
        source_tier=1,
        org=ORG,
        title=title,
        archetype=None,
        deadline=deadline_parser(body),
        description=body[:5000],
        raw_html=html[:50_000],
        legitimacy_tier="T1",
    )


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


try:
    from career_ops_kr.channels._scrapling_base import (
        SCRAPLING_AVAILABLE,
        ScraplingChannel,
    )
except ImportError:  # pragma: no cover — defensive
    SCRAPLING_AVAILABLE = False


if SCRAPLING_AVAILABLE:

    class ShinhanSecChannel(ScraplingChannel):
        """신한투자증권 채용 공고 수집기 (Scrapling backend)."""

        name = "shinhan_sec"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="shinhan_sec",
                tier=1,
                login_url=None,
                fetcher_mode="fast",
                **kwargs,
            )

        def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            try:
                result = self.fetch_page(LISTING_URL)
            except Exception as exc:
                self.logger.error("shinhan_sec: fetch_page raised: %s", exc)
                return []
            if result is None:
                self.logger.warning("shinhan_sec: listing fetch failed — returning []")
                return []
            try:
                jobs = _parse_listing_html(result["html"], self._make_id)
            except Exception as exc:
                self.logger.error("shinhan_sec: parse error: %s", exc)
                return []
            if not jobs:
                self.logger.info("shinhan_sec: no matching postings (kw=%s)", KEYWORDS)
            return jobs

        def get_detail(self, url: str) -> JobRecord | None:
            try:
                result = self.fetch_page(url)
            except Exception as exc:
                self.logger.warning("shinhan_sec: get_detail(%s) failed: %s", url, exc)
                return None
            if result is None:
                return None
            try:
                return _parse_detail_html(result["html"], url, self._make_id)
            except Exception as exc:
                self.logger.warning("shinhan_sec: parse detail failed %s: %s", url, exc)
                return None

else:
    from career_ops_kr.channels._playwright_base import PlaywrightChannel

    class ShinhanSecChannel(PlaywrightChannel):  # type: ignore[no-redef]
        """신한투자증권 채용 공고 수집기 (Playwright fallback)."""

        name = "shinhan_sec"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="shinhan_sec",
                tier=1,
                login_url=LISTING_URL,
                requires_login=False,
                **kwargs,
            )

        async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            html = await self.fetch_html(LISTING_URL, wait_selector="body")
            if html is None:
                self.logger.warning("shinhan_sec: listing fetch failed — returning []")
                return []
            try:
                jobs = _parse_listing_html(html, self._make_id)
            except Exception as exc:
                self.logger.error("shinhan_sec: parse error: %s", exc)
                return []
            finally:
                await self.close()
            if not jobs:
                self.logger.info("shinhan_sec: no matching postings (kw=%s)", KEYWORDS)
            return jobs

        async def _async_get_detail(self, url: str) -> JobRecord | None:
            html = await self.fetch_html(url)
            await self.close()
            if html is None:
                return None
            return _parse_detail_html(html, url, self._make_id)
