"""Scrapling-backed channel base.

Provides :class:`ScraplingChannel`, a synchronous extension of
:class:`BaseChannel` for channels that can use the Scrapling fetcher stack
(https://github.com/D4Vinci/Scrapling) as a primary scraping layer.

Why Scrapling first, Playwright as fallback:
    * Scrapling offers three fetchers: ``Fetcher`` (httpx-like, static),
      ``StealthyFetcher`` (camoufox — Cloudflare bypass), and
      ``DynamicFetcher`` (Chromium full automation). All share a single
      ``Response`` object with CSS/XPath + ``adaptive=True`` auto-relocation.
    * Playwright stays available via :mod:`_playwright_base` — if Scrapling
      is missing we simply never import this module and the channel uses
      the Playwright path.

Graceful degradation contract
-----------------------------
* ``SCRAPLING_AVAILABLE`` is a boolean resolved at import time via
  :func:`importlib.util.find_spec`. Importing this module MUST NOT crash
  when scrapling is missing; subclasses should branch on the flag.
* :class:`ScraplingNotInstalled` is raised by :meth:`ScraplingChannel.check`
  when the flag is False, carrying install instructions.
* On any fetch failure, :meth:`fetch_page` returns ``None``. We NEVER
  fabricate a page.
* File I/O (session state) uses ``encoding='utf-8'`` and :class:`pathlib.Path`.
"""

from __future__ import annotations

import importlib.util
import logging
import socket
from pathlib import Path
from typing import Any, Literal

from career_ops_kr.channels.base import BaseChannel, ChannelError, JobRecord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Availability probe
# ---------------------------------------------------------------------------


def _detect_scrapling() -> bool:
    """Return True iff the ``scrapling`` package is importable.

    We use :func:`importlib.util.find_spec` to avoid eagerly loading a
    heavy package whose import-time side effects (playwright/camoufox
    bootstrapping) we don't want to pay when the caller only wants the
    Playwright path.
    """
    try:
        return importlib.util.find_spec("scrapling") is not None
    except (ImportError, ValueError) as exc:
        logger.debug("scrapling find_spec raised %s", exc)
        return False


SCRAPLING_AVAILABLE: bool = _detect_scrapling()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ScraplingNotInstalled(ChannelError):
    """Raised when the ``scrapling`` package is unavailable.

    Carries a human-friendly install hint so the CLI can tell 찬희 exactly
    what to run. Channels that extend :class:`ScraplingChannel` catch this
    and fall back to the Playwright path.
    """

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or (
                "scrapling is not installed. Install with:\n"
                "    pip install 'career-ops-kr[scrapling]'\n"
                "    # or: pip install scrapling\n"
                "Scrapling optionally needs camoufox/chromium for Stealthy/Dynamic:\n"
                "    python -m camoufox fetch\n"
                "    python -m playwright install chromium"
            )
        )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


FetcherMode = Literal["auto", "fast", "stealth", "dynamic"]
DEFAULT_RATE_PER_MINUTE = 10
DEFAULT_TIMEOUT_SEC = 30


def _repo_root() -> Path:
    """Repository root — same anchoring rule as :mod:`_playwright_base`."""
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# ScraplingChannel
# ---------------------------------------------------------------------------


class ScraplingChannel(BaseChannel):
    """Base class for channels that prefer Scrapling as their network layer.

    Concrete subclasses set ``name``, ``tier``, ``default_legitimacy_tier``
    and implement :meth:`list_jobs` / :meth:`get_detail` using
    :meth:`fetch_page` (single URL) or :meth:`fetch_with_session` (bulk).

    Constructor
    -----------
    * ``name`` / ``tier`` override class attributes.
    * ``login_url`` — if set and fetcher_mode="auto", bumps mode to ``stealth``.
    * ``fetcher_mode``:
        - ``"auto"`` — picks ``stealth`` for login_url/anti-bot sites,
          ``fast`` otherwise, ``dynamic`` opt-in.
        - ``"fast"`` — :class:`scrapling.fetchers.Fetcher`.
        - ``"stealth"`` — :class:`scrapling.fetchers.StealthyFetcher`.
        - ``"dynamic"`` — :class:`scrapling.fetchers.DynamicFetcher` (Chromium).
    """

    backend: str = "scrapling"

    def __init__(
        self,
        name: str | None = None,
        tier: int | None = None,
        login_url: str | None = None,
        fetcher_mode: FetcherMode = "auto",
        storage_state_path: Path | None = None,
        rate_per_minute: int | None = None,
        timeout: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        if name is not None:
            self.name = name
        if tier is not None:
            self.tier = tier
        super().__init__(rate_per_minute=rate_per_minute or DEFAULT_RATE_PER_MINUTE)
        self.login_url = login_url
        self.fetcher_mode: FetcherMode = fetcher_mode
        self.timeout = timeout
        self._storage_state_path: Path = (
            storage_state_path
            if storage_state_path is not None
            else _repo_root() / ".auth" / f"{self.name}_scrapling.json"
        )
        self._fetch_count: int = 0

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def storage_state_path(self) -> Path:
        return self._storage_state_path

    def _ensure_auth_dir(self) -> None:
        self._storage_state_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Fetcher factory
    # ------------------------------------------------------------------

    def _resolved_mode(self) -> FetcherMode:
        """Pick an effective fetcher mode when ``auto`` is configured."""
        if self.fetcher_mode != "auto":
            return self.fetcher_mode
        # Heuristic: login-gated / anti-bot → stealth. Everything else → fast.
        if self.login_url:
            return "stealth"
        return "fast"

    def _make_fetcher(self, mode: FetcherMode) -> Any:
        """Return the configured Scrapling fetcher class for ``mode``.

        Raises :class:`ScraplingNotInstalled` if scrapling is unavailable.
        """
        if not SCRAPLING_AVAILABLE:
            raise ScraplingNotInstalled()
        try:
            from scrapling.fetchers import (
                DynamicFetcher,
                Fetcher,
                StealthyFetcher,
            )
        except ImportError as exc:
            raise ScraplingNotInstalled(f"scrapling import failed: {exc}") from exc

        if mode == "dynamic":
            return DynamicFetcher
        if mode == "stealth":
            return StealthyFetcher
        # Fall-through: "fast" (and defensive default for "auto")
        return Fetcher

    def _session_factory(self, mode: FetcherMode) -> Any:
        """Return a Scrapling ``*Session`` class matching ``mode``.

        Sessions reuse cookies across multiple ``fetch`` calls — useful for
        bulk list-page + detail-page pipelines.
        """
        if not SCRAPLING_AVAILABLE:
            raise ScraplingNotInstalled()
        try:
            from scrapling.fetchers import (
                DynamicSession,
                FetcherSession,
                StealthySession,
            )
        except ImportError as exc:
            raise ScraplingNotInstalled(f"scrapling import failed: {exc}") from exc

        if mode == "dynamic":
            return DynamicSession
        if mode == "stealth":
            return StealthySession
        return FetcherSession

    # ------------------------------------------------------------------
    # Public fetch API
    # ------------------------------------------------------------------

    def check(self) -> bool:
        """Return True iff Scrapling is installed AND network looks reachable.

        Raises :class:`ScraplingNotInstalled` if Scrapling is missing so the
        caller can fall back to Playwright. A bare return-False would hide
        the install problem from the fallback selector.
        """
        if not SCRAPLING_AVAILABLE:
            raise ScraplingNotInstalled()
        try:
            # Lightweight DNS probe — doesn't hit the target site.
            socket.gethostbyname("example.com")
            return True
        except OSError as exc:
            self.logger.warning("%s: scrapling network probe failed: %s", self.name, exc)
            return False

    def fetch_page(self, url: str) -> dict[str, Any] | None:
        """Fetch ``url`` and return a plain-dict view of the response.

        Returns ``None`` on any failure. Dict shape::

            {
                "text": str,            # .text or rendered body
                "html": str,            # .body/.html content
                "status": int,          # HTTP status (0 if unknown)
                "url": str,             # final URL after redirects
                "page": scrapling page  # raw Scrapling Response (for CSS)
            }
        """
        if not SCRAPLING_AVAILABLE:
            self.logger.debug("%s: scrapling unavailable", self.name)
            return None
        mode = self._resolved_mode()
        fetcher_cls = self._make_fetcher(mode)

        def _do_fetch() -> Any:
            # Prefer ``fetch`` for dynamic/stealth; ``get`` for fast.
            if mode == "fast" and hasattr(fetcher_cls, "get"):
                return fetcher_cls.get(url, timeout=self.timeout)
            if hasattr(fetcher_cls, "fetch"):
                return fetcher_cls.fetch(url)
            # Defensive fallback — older/newer APIs
            return fetcher_cls.get(url)

        try:
            page = self._retry(_do_fetch)
        except ScraplingNotInstalled:
            raise
        except Exception as exc:
            self.logger.warning("%s: scrapling fetch(%s) failed: %s", self.name, url, exc)
            return None

        if page is None:
            return None

        try:
            status = int(getattr(page, "status", 0) or 0)
        except (TypeError, ValueError):
            status = 0
        if status and status >= 400:
            self.logger.warning("%s: HTTP %d for %s", self.name, status, url)
            return None

        html = ""
        text = ""
        try:
            html = str(getattr(page, "body", None) or getattr(page, "html", "") or "")
        except Exception:
            html = ""
        try:
            text = str(getattr(page, "text", None) or html)
        except Exception:
            text = html

        self._fetch_count += 1
        return {
            "text": text,
            "html": html,
            "status": status,
            "url": str(getattr(page, "url", None) or url),
            "page": page,
        }

    def fetch_with_session(self, urls: list[str]) -> list[dict[str, Any]]:
        """Bulk fetch ``urls`` reusing a single Scrapling session.

        Missed/failed URLs are skipped — they do NOT appear in the returned
        list. The returned list is therefore possibly shorter than ``urls``.
        """
        if not SCRAPLING_AVAILABLE:
            return []
        if not urls:
            return []
        mode = self._resolved_mode()
        session_cls = self._session_factory(mode)

        results: list[dict[str, Any]] = []
        try:
            with session_cls() as session:
                for url in urls:
                    try:
                        self._rate.acquire()
                        if mode == "fast" and hasattr(session, "get"):
                            page = session.get(url, timeout=self.timeout)
                        else:
                            page = session.fetch(url)
                    except Exception as exc:
                        self.logger.warning("%s: session fetch(%s) failed: %s", self.name, url, exc)
                        continue
                    if page is None:
                        continue
                    try:
                        status = int(getattr(page, "status", 0) or 0)
                    except (TypeError, ValueError):
                        status = 0
                    if status and status >= 400:
                        continue
                    html = str(getattr(page, "body", None) or getattr(page, "html", "") or "")
                    text = str(getattr(page, "text", None) or html)
                    results.append(
                        {
                            "text": text,
                            "html": html,
                            "status": status,
                            "url": str(getattr(page, "url", None) or url),
                            "page": page,
                        }
                    )
                    self._fetch_count += 1
        except ScraplingNotInstalled:
            raise
        except Exception as exc:
            self.logger.warning("%s: session failed: %s", self.name, exc)
        return results

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _select_text(self, page: Any, selector: str, adaptive: bool = True) -> str | None:
        """CSS-select a single node's text from a Scrapling ``page``.

        Falls back to ``adaptive=False`` if the kwarg is rejected and then
        to plain ``.css(selector)`` as a last resort. Returns ``None`` on
        miss.
        """
        if page is None:
            return None
        try:
            try:
                hit = page.css(f"{selector}::text", adaptive=adaptive)
            except TypeError:
                hit = page.css(f"{selector}::text")
            value = hit.get() if hasattr(hit, "get") else hit
            if value is None:
                return None
            return str(value).strip() or None
        except Exception as exc:
            self.logger.debug("%s: select_text(%r) failed: %s", self.name, selector, exc)
            return None

    def _select_all(self, page: Any, selector: str, adaptive: bool = True) -> list[Any]:
        """CSS-select all matches. Returns ``[]`` on error."""
        if page is None:
            return []
        try:
            try:
                hit = page.css(selector, adaptive=adaptive)
            except TypeError:
                hit = page.css(selector)
            if hasattr(hit, "getall"):
                values = hit.getall()
                return list(values) if values else []
            if isinstance(hit, list):
                return hit
            return [hit] if hit is not None else []
        except Exception as exc:
            self.logger.debug("%s: select_all(%r) failed: %s", self.name, selector, exc)
            return []

    # ------------------------------------------------------------------
    # Abstract API — concrete channels override
    # ------------------------------------------------------------------

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        raise NotImplementedError

    def get_detail(self, url: str) -> JobRecord | None:
        raise NotImplementedError
