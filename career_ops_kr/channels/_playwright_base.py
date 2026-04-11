"""Playwright-backed channel base.

Provides :class:`PlaywrightChannel`, an async-capable extension of
:class:`BaseChannel` for channels that require a full browser engine
(JavaScript-rendered pages, login-gated portals).

Invariants
----------
* Browser is lazily created and closed after ``MAX_FETCHES_BEFORE_RECYCLE``
  fetches to keep memory usage bounded.
* ``storage_state`` is persisted to ``.auth/<name>.json`` (relative to the
  repo root) so Kakao/Naver/OAuth sessions can be reused across runs.
* On any Playwright failure :meth:`fetch_html` returns ``None`` — channels
  must NEVER fabricate results from a missing page.
* If Playwright is not installed, a clear :class:`PlaywrightNotInstalled`
  error is raised with installation instructions.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from pathlib import Path
from typing import Any

from career_ops_kr.channels.base import BaseChannel, ChannelError, JobRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PlaywrightNotInstalled(ChannelError):
    """Raised when the ``playwright`` package or its browsers are missing."""


class LoginRequiredError(ChannelError):
    """Raised when a channel requires user-interactive login.

    The caller (CLI) should catch this and guide 찬희 through the manual
    login flow: ``career-ops login <channel>``.
    """

    def __init__(self, channel: str, login_url: str) -> None:
        self.channel = channel
        self.login_url = login_url
        super().__init__(
            f"[{channel}] Login session missing/expired. "
            f"Run `career-ops login {channel}` to authenticate at {login_url}."
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


_USER_AGENTS: tuple[str, ...] = (
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
)

MAX_FETCHES_BEFORE_RECYCLE = 100
DEFAULT_RATE_PER_MINUTE = 10
DEFAULT_NAV_TIMEOUT_MS = 30_000


def _repo_root() -> Path:
    """Resolve repository root from this file's location."""
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# PlaywrightChannel
# ---------------------------------------------------------------------------


class PlaywrightChannel(BaseChannel):
    """Base class for channels that need a headless browser.

    Concrete subclasses set class attributes ``name``, ``tier``, ``backend``
    (= ``"playwright"``) and implement :meth:`list_jobs` / :meth:`get_detail`
    using :meth:`fetch_html` as their network primitive.
    """

    backend: str = "playwright"

    def __init__(
        self,
        name: str | None = None,
        tier: int | None = None,
        login_url: str | None = None,
        storage_state_path: Path | None = None,
        rate_per_minute: int | None = None,
        headless: bool = True,
        requires_login: bool = False,
    ) -> None:
        if name is not None:
            self.name = name
        if tier is not None:
            self.tier = tier
        super().__init__(rate_per_minute=rate_per_minute or DEFAULT_RATE_PER_MINUTE)
        self.login_url = login_url
        self.headless = headless
        self.requires_login = requires_login
        self._storage_state_path: Path = (
            storage_state_path
            if storage_state_path is not None
            else _repo_root() / ".auth" / f"{self.name}.json"
        )
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None
        self._fetch_count: int = 0
        self._last_rate_ts: float = 0.0

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def storage_state_path(self) -> Path:
        return self._storage_state_path

    def _ensure_auth_dir(self) -> None:
        self._storage_state_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Rate limiting (async-friendly)
    # ------------------------------------------------------------------

    async def _rate_limit(self) -> None:
        min_interval = 60.0 / float(self._rate.per_minute)
        now = time.monotonic()
        delta = now - self._last_rate_ts
        if delta < min_interval:
            await asyncio.sleep(min_interval - delta)
        self._last_rate_ts = time.monotonic()

    # ------------------------------------------------------------------
    # Playwright lifecycle
    # ------------------------------------------------------------------

    async def _get_playwright(self) -> Any:
        if self._playwright is not None:
            return self._playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover — environment specific
            raise PlaywrightNotInstalled(
                "playwright is not installed. Install with:\n"
                "    pip install playwright\n"
                "    python -m playwright install chromium"
            ) from exc
        self._playwright = await async_playwright().start()
        return self._playwright

    async def _get_browser(self) -> Any:
        if self._browser is not None:
            return self._browser
        pw = await self._get_playwright()
        try:
            self._browser = await pw.chromium.launch(headless=self.headless)
        except Exception as exc:
            raise PlaywrightNotInstalled(
                f"Failed to launch Chromium: {exc}. Try: python -m playwright install chromium"
            ) from exc
        return self._browser

    async def _get_context(self) -> Any:
        if self._context is not None:
            return self._context
        browser = await self._get_browser()
        ua = random.choice(_USER_AGENTS)
        kwargs: dict[str, Any] = {
            "user_agent": ua,
            "locale": "ko-KR",
            "timezone_id": "Asia/Seoul",
            "viewport": {"width": 1366, "height": 900},
        }
        if self._storage_state_path.exists():
            kwargs["storage_state"] = str(self._storage_state_path)
            self.logger.debug(
                "%s: loaded storage_state from %s", self.name, self._storage_state_path
            )
        self._context = await browser.new_context(**kwargs)
        self._context.set_default_navigation_timeout(DEFAULT_NAV_TIMEOUT_MS)
        return self._context

    async def _save_storage_state(self, context: Any | None = None) -> None:
        ctx = context or self._context
        if ctx is None:
            return
        self._ensure_auth_dir()
        try:
            await ctx.storage_state(path=str(self._storage_state_path))
            self.logger.info("%s: saved storage_state to %s", self.name, self._storage_state_path)
        except Exception as exc:
            self.logger.warning("%s: storage_state save failed: %s", self.name, exc)

    async def _ensure_logged_in(self, page: Any) -> bool:
        """Override per site. Default: accept whatever state exists.

        Subclasses should navigate to a "my page" style URL and check for a
        login indicator; return False to trigger :class:`LoginRequiredError`.
        """
        return True

    async def close(self) -> None:
        try:
            if self._context is not None:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser is not None:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright is not None:
                await self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._browser = None
        self._playwright = None
        self._fetch_count = 0

    async def _recycle_if_needed(self) -> None:
        if self._fetch_count >= MAX_FETCHES_BEFORE_RECYCLE:
            self.logger.info("%s: recycling browser after %d fetches", self.name, self._fetch_count)
            await self.close()

    # ------------------------------------------------------------------
    # fetch_html
    # ------------------------------------------------------------------

    async def fetch_html(self, url: str, wait_selector: str | None = None) -> str | None:
        """Fetch and return the rendered HTML of ``url``.

        Returns ``None`` on any failure — callers must handle None and NEVER
        fabricate results.
        """
        await self._recycle_if_needed()
        await self._rate_limit()
        page: Any = None
        try:
            context = await self._get_context()
            page = await context.new_page()
            response = await page.goto(url, wait_until="domcontentloaded")
            if response is None:
                self.logger.warning("%s: no response from %s", self.name, url)
                return None
            if response.status >= 400:
                self.logger.warning("%s: HTTP %d for %s", self.name, response.status, url)
                return None
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10_000)
                except Exception as exc:
                    self.logger.debug(
                        "%s: wait_selector %r timed out on %s: %s",
                        self.name,
                        wait_selector,
                        url,
                        exc,
                    )
            html = await page.content()
            self._fetch_count += 1
            return html
        except PlaywrightNotInstalled:
            raise
        except Exception as exc:
            self.logger.warning("%s: fetch_html(%s) failed: %s", self.name, url, exc)
            return None
        finally:
            if page is not None:
                with contextlib.suppress(Exception):
                    await page.close()

    # ------------------------------------------------------------------
    # Sync shims for BaseChannel abstract API
    # ------------------------------------------------------------------

    def check(self) -> bool:
        try:
            return asyncio.run(self._async_check())
        except Exception as exc:
            self.logger.warning("%s: check failed: %s", self.name, exc)
            return False

    async def _async_check(self) -> bool:
        target = self.login_url or "https://example.com"
        html = await self.fetch_html(target)
        await self.close()
        return html is not None

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        try:
            return asyncio.run(self._async_list_jobs(query))
        except LoginRequiredError:
            raise
        except Exception as exc:
            self.logger.error("%s: list_jobs failed: %s", self.name, exc)
            return []

    async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        raise NotImplementedError

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            return asyncio.run(self._async_get_detail(url))
        except Exception as exc:
            self.logger.warning("%s: get_detail(%s) failed: %s", self.name, url, exc)
            return None

    async def _async_get_detail(self, url: str) -> JobRecord | None:
        raise NotImplementedError
