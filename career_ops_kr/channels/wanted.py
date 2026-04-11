"""Wanted (원티드) channel — fintech / blockchain / crypto positions.

Source: https://www.wanted.co.kr/

Login is optional for basic listing but recommended. We use the public
search endpoint and handle infinite scroll:
    * Scrapling ``DynamicFetcher`` path: real scrolling (full JS).
    * Scrapling ``StealthyFetcher`` path (default): single-shot page load —
      we scrape the initial ~20 cards only.
    * Playwright fallback: scroll N times manually.

On any failure return ``[]``. On login expiry raise
:class:`LoginRequiredError`. Never fabricate listings.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser

logger = logging.getLogger(__name__)


BASE_URL = "https://www.wanted.co.kr/"
LOGIN_URL = "https://www.wanted.co.kr/auth/signin"

SEARCH_QUERIES: tuple[str, ...] = ("핀테크", "블록체인", "크립토", "디지털자산")
SCROLL_ROUNDS = 6
SCROLL_PAUSE_SEC = 1.2


def _search_url(keyword: str) -> str:
    return f"https://www.wanted.co.kr/search?query={quote(keyword)}&tab=position"


# ---------------------------------------------------------------------------
# Shared parsing
# ---------------------------------------------------------------------------


def _parse_cards(html: str, make_id: Any) -> list[JobRecord]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[JobRecord] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a"):
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if "/wd/" not in href:
            continue
        url = urljoin(BASE_URL, href.split("?", 1)[0])
        if url in seen:
            continue
        text = anchor.get_text(" ", strip=True)
        if not text or len(text) < 4:
            continue
        seen.add(url)

        container = anchor.find_parent(["li", "article", "div"])
        body = container.get_text(" ", strip=True) if container else text

        title = text[:200]
        org = "원티드 기업"
        if container:
            span = container.find("span")
            if span:
                org = (span.get_text(strip=True) or org)[:100]

        jobs.append(
            JobRecord(
                id=make_id(url, title),
                source_url=url,
                source_channel="wanted",
                source_tier=1,
                org=org,
                title=title,
                archetype=None,
                deadline=deadline_parser(body),
                description=body[:2000],
                legitimacy_tier="T1",
            )
        )
    return jobs


def _parse_detail(html: str, url: str, make_id: Any) -> JobRecord:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else url)[:200]
    body = soup.get_text(" ", strip=True)
    return JobRecord(
        id=make_id(url, title),
        source_url=url,  # type: ignore[arg-type]
        source_channel="wanted",
        source_tier=1,
        org="원티드 기업",
        title=title,
        archetype=None,
        deadline=deadline_parser(body),
        description=body[:5000],
        raw_html=html[:50_000],
        legitimacy_tier="T1",
    )


def _detect_login_redirect(final_url: str) -> bool:
    lower = (final_url or "").lower()
    return "signin" in lower or "login" in lower


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


try:
    from career_ops_kr.channels._scrapling_base import (
        SCRAPLING_AVAILABLE,
        ScraplingChannel,
    )
except ImportError:  # pragma: no cover
    SCRAPLING_AVAILABLE = False

from career_ops_kr.channels._playwright_base import LoginRequiredError  # noqa: E402

if SCRAPLING_AVAILABLE:

    class WantedChannel(ScraplingChannel):
        """원티드 포지션 수집기 (Scrapling backend)."""

        name = "wanted"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="wanted",
                tier=1,
                login_url=LOGIN_URL,
                fetcher_mode="stealth",
                **kwargs,
            )

        def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            keywords = SEARCH_QUERIES
            if query and query.get("keyword"):
                keywords = (str(query["keyword"]),)

            jobs: list[JobRecord] = []
            seen: set[str] = set()
            for kw in keywords:
                result = self.fetch_page(_search_url(kw))
                if result is None:
                    self.logger.warning("wanted: fetch failed for keyword %r", kw)
                    continue
                if _detect_login_redirect(result.get("url", "")):
                    raise LoginRequiredError(self.name, LOGIN_URL)
                try:
                    cards = _parse_cards(result["html"], self._make_id)
                except Exception as exc:
                    self.logger.warning("wanted: parse failed for keyword %r: %s", kw, exc)
                    continue
                for rec in cards:
                    key = str(rec.source_url)
                    if key in seen:
                        continue
                    seen.add(key)
                    jobs.append(rec)
            return jobs

        def get_detail(self, url: str) -> JobRecord | None:
            result = self.fetch_page(url)
            if result is None:
                return None
            try:
                return _parse_detail(result["html"], url, self._make_id)
            except Exception as exc:
                self.logger.warning("wanted: detail parse failed %s: %s", url, exc)
                return None

else:
    from career_ops_kr.channels._playwright_base import PlaywrightChannel

    class WantedChannel(PlaywrightChannel):  # type: ignore[no-redef]
        """원티드 포지션 수집기 (Playwright fallback)."""

        name = "wanted"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="wanted",
                tier=1,
                login_url=LOGIN_URL,
                requires_login=True,
                **kwargs,
            )

        async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            keywords = SEARCH_QUERIES
            if query and query.get("keyword"):
                keywords = (str(query["keyword"]),)

            jobs: list[JobRecord] = []
            seen: set[str] = set()

            try:
                for kw in keywords:
                    cards = await self._scroll_and_collect(_search_url(kw))
                    for rec in cards:
                        key = str(rec.source_url)
                        if key in seen:
                            continue
                        seen.add(key)
                        jobs.append(rec)
            finally:
                await self.close()
            return jobs

        async def _scroll_and_collect(self, url: str) -> list[JobRecord]:
            context = await self._get_context()
            page = await context.new_page()
            results: list[JobRecord] = []
            try:
                response = await page.goto(url, wait_until="domcontentloaded")
                if response is None or response.status >= 400:
                    self.logger.warning(
                        "wanted: bad response for %s (status=%s)",
                        url,
                        getattr(response, "status", None),
                    )
                    return results

                current = (page.url or "").lower()
                if _detect_login_redirect(current):
                    raise LoginRequiredError(self.name, LOGIN_URL)

                for _ in range(SCROLL_ROUNDS):
                    try:
                        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                    except Exception as exc:
                        self.logger.debug("wanted: scroll eval failed: %s", exc)
                        break
                    await asyncio.sleep(SCROLL_PAUSE_SEC)

                html = await page.content()
                self._fetch_count += 1
                results = _parse_cards(html, self._make_id)
            except LoginRequiredError:
                raise
            except Exception as exc:
                self.logger.warning("wanted: scroll_and_collect failed for %s: %s", url, exc)
            finally:
                with contextlib.suppress(Exception):
                    await page.close()
            return results

        async def _async_get_detail(self, url: str) -> JobRecord | None:
            html = await self.fetch_html(url)
            await self.close()
            if html is None:
                return None
            return _parse_detail(html, url, self._make_id)
