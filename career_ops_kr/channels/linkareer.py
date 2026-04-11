"""Linkareer (링커리어) channel — intern & activity listings.

Source: https://linkareer.com/

Login required via Kakao/Naver/Google OAuth. On the Playwright path the
first run raises :class:`LoginRequiredError`; 찬희 runs
``career-ops login linkareer`` which persists ``storage_state`` to
``.auth/linkareer.json``.

On the Scrapling path, :class:`scrapling.fetchers.StealthySession` can
persist cookies similarly — we store them under
``.auth/linkareer_scrapling.json`` so the two backends never step on
each other's state.

On parse/fetch failure we return ``[]`` — we NEVER fabricate listings.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_ops_kr.channels.base import JobRecord, deadline_parser

logger = logging.getLogger(__name__)


BASE_URL = "https://linkareer.com/"
INTERN_URL = "https://linkareer.com/list/intern"
ACTIVITY_URL = "https://linkareer.com/list/activity"
LOGIN_URL = "https://linkareer.com/login"

KEYWORDS: tuple[str, ...] = (
    "금융",
    "핀테크",
    "블록체인",
    "디지털자산",
    "증권",
    "자산운용",
    "은행",
    "투자",
    "크립토",
    "IT",
    "데이터",
)

LOGIN_MARKERS: tuple[str, ...] = (
    "로그인",
    "login",
    "signIn",
    "카카오로 시작",
    "네이버로 시작",
)


# ---------------------------------------------------------------------------
# Shared parsing + login detection
# ---------------------------------------------------------------------------


def _is_login_gated(html: str) -> bool:
    lower = html.lower()
    login_hit = any(marker.lower() in lower for marker in LOGIN_MARKERS)
    has_cards = "/intern/" in lower or "/activity/" in lower
    return login_hit and not has_cards


def _parse_cards(html: str, listing_url: str, make_id: Any) -> list[JobRecord]:
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[JobRecord] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a"):
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href:
            continue
        if "/intern/" not in href and "/activity/" not in href:
            continue
        url = urljoin(BASE_URL, href)
        if url in seen:
            continue
        text = anchor.get_text(" ", strip=True)
        if not text or len(text) < 5:
            continue
        if not any(kw in text for kw in KEYWORDS):
            continue
        seen.add(url)

        container = anchor.find_parent(["li", "article", "div"])
        body = container.get_text(" ", strip=True) if container else text

        org_hint = ""
        for sep in ("|", "·", "ㆍ", "-"):
            if sep in text:
                org_hint = text.split(sep, 1)[0].strip()
                break
        org = org_hint or "링커리어 게시물"

        jobs.append(
            JobRecord(
                id=make_id(url, text),
                source_url=url,  # type: ignore[arg-type]
                source_channel="linkareer",
                source_tier=1,
                org=org[:100],
                title=text[:200],
                archetype="INTERN" if "/intern/" in url else "ACTIVITY",
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
        source_channel="linkareer",
        source_tier=1,
        org="링커리어",
        title=title,
        archetype="INTERN" if "/intern/" in url else "ACTIVITY",
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
except ImportError:  # pragma: no cover
    SCRAPLING_AVAILABLE = False

# LoginRequiredError is always imported from the playwright base because it
# is part of the public channel-error contract regardless of backend.
from career_ops_kr.channels._playwright_base import LoginRequiredError  # noqa: E402

if SCRAPLING_AVAILABLE:

    class LinkareerChannel(ScraplingChannel):
        """링커리어 인턴/대외활동 리스팅 수집기 (Scrapling backend)."""

        name = "linkareer"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="linkareer",
                tier=1,
                login_url=LOGIN_URL,
                fetcher_mode="stealth",
                **kwargs,
            )

        def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            jobs: list[JobRecord] = []
            for listing_url in (INTERN_URL, ACTIVITY_URL):
                result = self.fetch_page(listing_url)
                if result is None:
                    self.logger.warning("linkareer: fetch failed for %s", listing_url)
                    continue
                html = result["html"]
                if _is_login_gated(html):
                    raise LoginRequiredError(self.name, LOGIN_URL)
                jobs.extend(_parse_cards(html, listing_url, self._make_id))
            return jobs

        def get_detail(self, url: str) -> JobRecord | None:
            result = self.fetch_page(url)
            if result is None:
                return None
            try:
                return _parse_detail(result["html"], url, self._make_id)
            except Exception as exc:
                self.logger.warning("linkareer: detail parse failed %s: %s", url, exc)
                return None

else:
    from career_ops_kr.channels._playwright_base import PlaywrightChannel

    class LinkareerChannel(PlaywrightChannel):  # type: ignore[no-redef]
        """링커리어 인턴/대외활동 리스팅 수집기 (Playwright fallback)."""

        name = "linkareer"
        tier = 1
        default_legitimacy_tier = "T1"

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(
                name="linkareer",
                tier=1,
                login_url=LOGIN_URL,
                requires_login=True,
                **kwargs,
            )

        async def _ensure_logged_in(self, page: Any) -> bool:
            try:
                url = (page.url or "").lower()
                if "login" in url or "signin" in url:
                    return False
                html = await page.content()
            except Exception as exc:
                self.logger.debug("linkareer: login probe failed: %s", exc)
                return False
            return not _is_login_gated(html)

        async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
            jobs: list[JobRecord] = []
            try:
                for listing in (INTERN_URL, ACTIVITY_URL):
                    html = await self.fetch_html(listing, wait_selector="body")
                    if html is None:
                        self.logger.warning("linkareer: fetch failed for %s", listing)
                        continue
                    if _is_login_gated(html):
                        raise LoginRequiredError(self.name, LOGIN_URL)
                    jobs.extend(_parse_cards(html, listing, self._make_id))
            finally:
                await self.close()
            return jobs

        async def _async_get_detail(self, url: str) -> JobRecord | None:
            html = await self.fetch_html(url)
            await self.close()
            if html is None:
                return None
            return _parse_detail(html, url, self._make_id)
