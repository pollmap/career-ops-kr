"""Experimental Claude Code ``/scrape`` slash-command proxy.

This is an **opt-in** alternative scraping backend that shells out to the
local ``claude`` CLI and invokes the ``/scrape`` slash command (see
``~/.claude/commands/scrape.md``). Unlike :mod:`_scrapling_base`, this
module is NOT a :class:`BaseChannel` subclass — it's a utility that
individual channels can elect to use when the env var
``CAREER_OPS_USE_SLASH_SCRAPE=1`` is set.

Why this exists
---------------
찬희's local Claude Code installation already has a ``/scrape`` command
wired up to Scrapling (see the skills list). For environments where
installing ``scrapling`` directly is painful, this proxy lets us reuse
the already-working command by piping a single URL at a time.

Assumptions
-----------
* ``claude`` CLI is on PATH.
* The user has the ``/scrape`` command registered globally or in the
  current project.
* The command accepts a URL and prints the fetched text/HTML on stdout.

Safety
------
* All ``subprocess`` calls use ``shell=False`` (list args) on Windows.
* ``encoding='utf-8'`` is passed explicitly — we never rely on cp949.
* Default 60s timeout; caller can override.
* On ANY failure we return ``None`` and log stderr. We NEVER fabricate.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Final

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Availability probe
# ---------------------------------------------------------------------------


_ENV_FLAG: Final[str] = "CAREER_OPS_USE_SLASH_SCRAPE"
_DEFAULT_TIMEOUT: Final[int] = 60
_MAX_OUTPUT_BYTES: Final[int] = 2_000_000  # 2 MB guardrail


def _claude_cli_available() -> bool:
    """Return True if the ``claude`` executable is on PATH."""
    try:
        return shutil.which("claude") is not None
    except Exception as exc:
        logger.debug("which(claude) raised %s", exc)
        return False


def _detect() -> bool:
    """Heuristic: ``claude`` CLI present AND user opted-in via env var.

    We intentionally require the env var — we do NOT auto-enable this
    path even if the CLI exists, because invoking a slash command per
    URL is expensive and has side effects (telemetry, quota).
    """
    if os.environ.get(_ENV_FLAG, "").strip() not in {"1", "true", "yes", "on"}:
        return False
    return _claude_cli_available()


SLASH_SCRAPE_AVAILABLE: bool = _detect()


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------


class SlashScrapeProxy:
    """Wrapper around ``claude -p '/scrape <url>'``.

    This is NOT a channel — it's a building block channels can call when
    ``SLASH_SCRAPE_AVAILABLE`` is True and they explicitly want to use the
    slash-command path (e.g. their Scrapling + Playwright paths both
    failed).
    """

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.logger = logging.getLogger("career_ops_kr.channels.slash_scrape")

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    @staticmethod
    def is_available() -> bool:
        """Re-probe availability at call time (env var can be flipped)."""
        return _detect()

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> str | None:
        """Invoke ``claude -p '/scrape <url>'`` and return stdout, or ``None``.

        The returned string is whatever the ``/scrape`` command printed,
        typically clean text or JSON. We do not parse it — the caller is
        responsible for interpretation.
        """
        if not self.is_available():
            self.logger.debug(
                "slash-scrape not available (env=%s cli=%s)",
                os.environ.get(_ENV_FLAG, ""),
                _claude_cli_available(),
            )
            return None

        if not url or not isinstance(url, str):
            self.logger.warning("slash-scrape: invalid url %r", url)
            return None

        # URL scheme 방어 — http/https만 허용 (file://, javascript:, data: 차단)
        from urllib.parse import urlparse
        try:
            _scheme = urlparse(url).scheme.lower()
        except Exception:
            _scheme = ""
        if _scheme not in ("http", "https"):
            self.logger.warning("slash-scrape: disallowed URL scheme %r (url=%s)", _scheme, url)
            return None

        prompt = f"/scrape {url}"
        cmd = ["claude", "-p", prompt]

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                shell=False,
                check=False,
            )
        except FileNotFoundError as exc:
            self.logger.warning("slash-scrape: claude CLI missing: %s", exc)
            return None
        except subprocess.TimeoutExpired as exc:
            self.logger.warning(
                "slash-scrape: timeout after %ds fetching %s: %s",
                self.timeout,
                url,
                exc,
            )
            return None
        except Exception as exc:
            self.logger.warning("slash-scrape: subprocess raised: %s", exc)
            return None

        if completed.returncode != 0:
            self.logger.warning(
                "slash-scrape: non-zero exit %d for %s: %s",
                completed.returncode,
                url,
                (completed.stderr or "").strip()[:500],
            )
            return None

        stdout = completed.stdout or ""
        if not stdout.strip():
            self.logger.debug("slash-scrape: empty stdout for %s", url)
            return None
        if len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES:
            self.logger.warning(
                "slash-scrape: output exceeded %d bytes for %s, truncating",
                _MAX_OUTPUT_BYTES,
                url,
            )
            stdout = stdout[: _MAX_OUTPUT_BYTES // 2]
        return stdout
