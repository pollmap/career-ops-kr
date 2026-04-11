"""Shared helpers for Tier 3-4 stub channels.

Provides:
    * :func:`parse_generic_cards` — a best-effort BeautifulSoup anchor scan
      that extracts candidate job postings. Works on most static HTML
      listings that follow the common "anchor with title + career keyword"
      pattern. If no cards match, raises :class:`NotTunedYetError`.
    * :func:`build_record` — factory that mints a :class:`JobRecord` with
      the ``id`` derived via the BaseChannel-supplied ``make_id`` callable.
    * :data:`CAREER_KEYWORDS` — generic blocklist/allowlist for filtering
      out non-recruitment anchors.

All stub channels use these helpers so adding a new portal is ~80 lines
of glue rather than a duplicated parse loop.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from career_ops_kr.channels._stub_errors import NotTunedYetError
from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

logger = logging.getLogger(__name__)


# Positive signals — anchors whose visible text contains at least one of
# these substrings are candidate postings. This is intentionally generous;
# the qualifier/scorer downstream does the real filtering.
CAREER_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "recruit",
    "career",
    "job",
    "신입",
    "인턴",
    "intern",
    "경력",
    "개발",
    "데이터",
    "블록체인",
    "디지털",
    "IT",
    "핀테크",
    "금융",
    "리서치",
    "분석",
    "engineer",
    "developer",
)


# Negative signals — skip anchors that look like nav / footer / legal.
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "개인정보",
    "이용약관",
    "저작권",
    "copyright",
    "privacy",
    "terms",
    "sitemap",
    "로그인",
    "login",
    "회원가입",
    "signup",
    "언어",
    "language",
)


def _looks_like_posting(text: str) -> bool:
    """Return True if ``text`` plausibly names a job posting."""
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < 4 or len(stripped) > 300:
        return False
    low = stripped.lower()
    if any(neg in stripped or neg in low for neg in NEGATIVE_KEYWORDS):
        return False
    return any(kw in stripped or kw.lower() in low for kw in CAREER_KEYWORDS)


def build_record(
    *,
    url: str,
    title: str,
    body_text: str,
    make_id: Callable[[str, str], str],
    source_channel: str,
    source_tier: int,
    org: str,
    legitimacy_tier: str,
    location: str | None = None,
    raw_html: str | None = None,
) -> JobRecord:
    """Materialise a :class:`JobRecord` from parsed fields.

    ``body_text`` is used both for deadline extraction (via
    :func:`deadline_parser`) and as the ``description`` (truncated to
    5000 chars to keep SQLite rows reasonable).
    """
    return JobRecord(
        id=make_id(url, title),
        source_url=url,  # type: ignore[arg-type]
        source_channel=source_channel,
        source_tier=source_tier,
        org=org,
        title=title[:200],
        archetype=None,
        deadline=deadline_parser(body_text),
        location=location,
        description=body_text[:5000],
        raw_html=raw_html[:50_000] if raw_html else None,
        legitimacy_tier=legitimacy_tier,
    )


def parse_generic_cards(
    html: str,
    *,
    base_url: str,
    make_id: Callable[[str, str], str],
    source_channel: str,
    source_tier: int,
    org: str,
    legitimacy_tier: str,
    location: str | None = None,
    min_cards: int = 1,
) -> list[JobRecord]:
    """Generic anchor-based card extractor.

    Walks every ``<a href>`` whose visible text contains a career keyword
    and does not contain a negative-list phrase. Filters out anchors that
    point at ``javascript:`` handlers or empty hashes. Deduplicates by URL.

    Raises :class:`NotTunedYetError` if fewer than ``min_cards`` candidate
    postings are found — a signal that the upstream HTML needs a
    channel-specific selector pass.
    """
    if not html:
        raise NotTunedYetError(source_channel, detail="empty HTML")

    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    jobs: list[JobRecord] = []

    for anchor in soup.find_all("a"):
        text = (anchor.get_text(" ", strip=True) or "").strip()
        if not _looks_like_posting(text):
            continue
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            continue
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)

        container = anchor.find_parent(["li", "tr", "div", "article", "section"])
        body_text = container.get_text(" ", strip=True) if container else text
        jobs.append(
            build_record(
                url=url,
                title=text,
                body_text=body_text,
                make_id=make_id,
                source_channel=source_channel,
                source_tier=source_tier,
                org=org,
                legitimacy_tier=legitimacy_tier,
                location=location,
            )
        )

    if len(jobs) < min_cards:
        raise NotTunedYetError(
            source_channel,
            detail=f"found {len(jobs)} cards, expected >= {min_cards}",
        )
    return jobs


def parse_detail_page(
    html: str,
    *,
    url: str,
    make_id: Callable[[str, str], str],
    source_channel: str,
    source_tier: int,
    org: str,
    legitimacy_tier: str,
    location: str | None = None,
) -> JobRecord | None:
    """Extract a single :class:`JobRecord` from a detail page.

    Uses ``<title>`` as the posting title and the full body text as the
    description source. Returns ``None`` on empty HTML (never raises).
    """
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = ((soup.title.get_text(strip=True) if soup.title else url) or url)[:200]
        body = soup.get_text(" ", strip=True)
        return build_record(
            url=url,
            title=title,
            body_text=body,
            make_id=make_id,
            source_channel=source_channel,
            source_tier=source_tier,
            org=org,
            legitimacy_tier=legitimacy_tier,
            location=location,
            raw_html=html,
        )
    except Exception as exc:
        logger.warning("%s: parse_detail_page(%s) failed: %s", source_channel, url, exc)
        return None


def make_stub_channel_class(
    *,
    class_name: str,
    channel_name: str,
    channel_tier: int,
    listing_url: str,
    org: str,
    location: str | None = None,
    legitimacy_tier: str = "T1",
    fetcher_mode: str = "dynamic",
    login_url: str | None = None,
) -> type[BaseChannel]:
    """Factory returning a concrete ScraplingChannel subclass.

    This keeps each portal file thin — the portal only needs to call this
    factory with its metadata. We build the class here so the generated
    type picks up the ``list_jobs`` / ``get_detail`` / ``check`` contract
    once, centrally.

    Graceful degradation: if Scrapling is not installed, a Playwright-based
    subclass is returned instead. Either way the resulting class satisfies
    the :class:`Channel` protocol.
    """
    try:
        from career_ops_kr.channels._scrapling_base import (
            SCRAPLING_AVAILABLE,
            ScraplingChannel,
        )
    except ImportError:
        SCRAPLING_AVAILABLE = False  # pragma: no cover  # noqa: N806

    base_cls: type[BaseChannel]
    backend_kwargs: dict[str, Any]
    if SCRAPLING_AVAILABLE:
        base_cls = ScraplingChannel
        backend_kwargs = {"fetcher_mode": fetcher_mode, "login_url": login_url}
        is_scrapling = True
    else:
        from career_ops_kr.channels._playwright_base import PlaywrightChannel

        base_cls = PlaywrightChannel
        backend_kwargs = {
            "login_url": login_url or listing_url,
            "requires_login": False,
        }
        is_scrapling = False

    def __init__(self: Any, **kwargs: Any) -> None:  # noqa: N807
        base_cls.__init__(
            self,
            name=channel_name,
            tier=channel_tier,
            **backend_kwargs,
            **kwargs,
        )

    def _parse_listing_safe(self: Any, html: str) -> list[JobRecord]:
        try:
            return parse_generic_cards(
                html,
                base_url=listing_url,
                make_id=self._make_id,
                source_channel=channel_name,
                source_tier=channel_tier,
                org=org,
                legitimacy_tier=legitimacy_tier,
                location=location,
            )
        except NotTunedYetError as exc:
            self.logger.warning("%s: %s", channel_name, exc)
            return []
        except Exception as exc:
            self.logger.error("%s: parse error: %s", channel_name, exc)
            return []

    def _scrapling_list_jobs(self: Any, query: dict[str, Any] | None = None) -> list[JobRecord]:
        try:
            result = self.fetch_page(listing_url)
        except Exception as exc:
            self.logger.error("%s: fetch_page raised: %s", channel_name, exc)
            return []
        if result is None:
            self.logger.warning("%s: listing fetch failed — returning []", channel_name)
            return []
        return _parse_listing_safe(self, result["html"])

    def _scrapling_get_detail(self: Any, url: str) -> JobRecord | None:
        try:
            result = self.fetch_page(url)
        except Exception as exc:
            self.logger.warning("%s: get_detail(%s) failed: %s", channel_name, url, exc)
            return None
        if result is None:
            return None
        return parse_detail_page(
            result["html"],
            url=url,
            make_id=self._make_id,
            source_channel=channel_name,
            source_tier=channel_tier,
            org=org,
            legitimacy_tier=legitimacy_tier,
            location=location,
        )

    async def _playwright_async_list_jobs(
        self: Any, query: dict[str, Any] | None = None
    ) -> list[JobRecord]:
        html = await self.fetch_html(listing_url, wait_selector="body")
        try:
            if html is None:
                self.logger.warning("%s: listing fetch failed — returning []", channel_name)
                return []
            return _parse_listing_safe(self, html)
        finally:
            await self.close()

    async def _playwright_async_get_detail(self: Any, url: str) -> JobRecord | None:
        try:
            html = await self.fetch_html(url)
            if html is None:
                return None
            return parse_detail_page(
                html,
                url=url,
                make_id=self._make_id,
                source_channel=channel_name,
                source_tier=channel_tier,
                org=org,
                legitimacy_tier=legitimacy_tier,
                location=location,
            )
        finally:
            await self.close()

    namespace: dict[str, Any] = {
        "name": channel_name,
        "tier": channel_tier,
        "default_legitimacy_tier": legitimacy_tier,
        "__init__": __init__,
        "__doc__": f"Stub channel for {org} ({listing_url}). Selectors pending live-HTML tuning.",
    }
    if is_scrapling:
        namespace["list_jobs"] = _scrapling_list_jobs
        namespace["get_detail"] = _scrapling_get_detail
    else:
        namespace["_async_list_jobs"] = _playwright_async_list_jobs
        namespace["_async_get_detail"] = _playwright_async_get_detail

    # Attribute the generated class to the caller's module so that
    # ``cls.__module__`` round-trips via ``importlib.import_module``.
    # Without this, ABCMeta defaults ``__module__`` to ``'abc'`` and the
    # symbol cannot be re-imported by name.
    try:
        caller_module = sys._getframe(1).f_globals.get("__name__", __name__)
    except ValueError:  # pragma: no cover - stack depth edge case
        caller_module = __name__
    namespace["__module__"] = caller_module
    namespace.setdefault("__qualname__", class_name)

    return type(class_name, (base_cls,), namespace)
