"""Legitimacy verifier.

Classifies every job-posting URL into one of five trust tiers.  The tier
feeds both the scoring pipeline (via :meth:`score_penalty`) and the
output markdown's ``Legitimacy`` line.

Design
------
* First pass is a **pure regex domain match** — zero network, deterministic.
* :meth:`verify` optionally issues a Playwright fetch to confirm the URL is
  live.  If the fetch fails we keep the regex tier but mark ``reachable=False``
  so downstream code can warn instead of fabricating a "verified" label.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier enum
# ---------------------------------------------------------------------------


class Tier(str, Enum):
    T1_OFFICIAL = "T1"  # Official employer career site (recruit.*.com, or.kr careers)
    T2_GOVERNMENT = "T2"  # Government / public institution portal (.go.kr, jobkorea-gov, etc.)
    T3_AGGREGATOR = "T3"  # Trusted aggregator (linkareer, wanted, jobkorea, saramin)
    T4_NEWS = "T4"  # News / blog mentions
    T5_UNKNOWN = "T5"  # Unclassified / suspicious


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------


# Order matters — more specific rules first.
_T1_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^recruit\.[a-z0-9\-]+\.(?:com|co\.kr)$"),
    re.compile(r"^careers?\.[a-z0-9\-]+\.(?:com|co\.kr)$"),
    re.compile(r"^jobs?\.[a-z0-9\-]+\.(?:com|co\.kr)$"),
    re.compile(r"^hiring\.[a-z0-9\-]+\.(?:com|co\.kr)$"),
    re.compile(r"^people\.[a-z0-9\-]+\.(?:com|co\.kr)$"),
)

_T1_OFFICIAL_KR_ORGS: frozenset[str] = frozenset(
    {
        "recruit.shinhansec.com",
        "recruit.samsung.com",
        "careers.kakao.com",
        "careers.coupang.com",
        "careers.toss.im",
        "career.hanwhalife.com",
        "nhhiring.nonghyup.com",
    }
)


_T2_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.go\.kr$"),
    re.compile(r"\.or\.kr$"),
    re.compile(r"^work\.go\.kr$"),
    re.compile(r"^www\.work24\.go\.kr$"),
    re.compile(r"^www\.nhis\.or\.kr$"),
    re.compile(r"^license\.kofia\.or\.kr$"),
    re.compile(r"^job\.alio\.go\.kr$"),
)

_T3_AGGREGATORS: frozenset[str] = frozenset(
    {
        "linkareer.com",
        "www.linkareer.com",
        "wanted.co.kr",
        "www.wanted.co.kr",
        "jobkorea.co.kr",
        "www.jobkorea.co.kr",
        "saramin.co.kr",
        "www.saramin.co.kr",
        "programmers.co.kr",
        "www.programmers.co.kr",
        "rocketpunch.com",
        "www.rocketpunch.com",
    }
)

_T4_NEWS_DOMAINS: frozenset[str] = frozenset(
    {
        "news.naver.com",
        "n.news.naver.com",
        "www.hankyung.com",
        "www.mk.co.kr",
        "www.edaily.co.kr",
        "www.yna.co.kr",
        "www.chosun.com",
        "www.donga.com",
        "biz.chosun.com",
        "news.mt.co.kr",
        "brunch.co.kr",
        "medium.com",
    }
)


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------


class LegitimacyVerifier:
    """Classify URLs into :class:`Tier`."""

    _PENALTIES: dict[Tier, float] = {
        Tier.T1_OFFICIAL: 0.0,
        Tier.T2_GOVERNMENT: 0.0,
        Tier.T3_AGGREGATOR: -5.0,
        Tier.T4_NEWS: -10.0,
        Tier.T5_UNKNOWN: -15.0,
    }

    def classify_url(self, url: str) -> Tier:
        """Synchronous, offline classification based on domain patterns."""
        if not url:
            return Tier.T5_UNKNOWN
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception as exc:
            logger.debug("classify_url: parse error for %r: %s", url, exc)
            return Tier.T5_UNKNOWN
        if not host:
            return Tier.T5_UNKNOWN

        if host in _T1_OFFICIAL_KR_ORGS:
            return Tier.T1_OFFICIAL
        if any(pat.match(host) for pat in _T1_PATTERNS):
            return Tier.T1_OFFICIAL
        if host in _T3_AGGREGATORS:
            return Tier.T3_AGGREGATOR
        if any(pat.search(host) for pat in _T2_PATTERNS):
            return Tier.T2_GOVERNMENT
        if host in _T4_NEWS_DOMAINS:
            return Tier.T4_NEWS
        return Tier.T5_UNKNOWN

    async def verify(self, url: str) -> tuple[Tier, bool]:
        """Classify + confirm URL is live via Playwright.

        Returns ``(tier, reachable)``.  ``reachable`` is ``False`` if Playwright
        is unavailable or the fetch fails.  The tier is ALWAYS the offline
        classification — we never upgrade/downgrade based on HTTP status.
        """
        tier = self.classify_url(url)
        try:
            from career_ops_kr.channels._playwright_base import (
                PlaywrightChannel,
                PlaywrightNotInstalled,
            )

            class _Probe(PlaywrightChannel):
                name = "legitimacy_probe"
                tier = 6

                async def _async_list_jobs(self, query: dict[str, Any] | None = None) -> list[Any]:
                    return []

                async def _async_get_detail(self, url: str) -> None:
                    return None

            probe = _Probe()
            try:
                html = await probe.fetch_html(url)
                reachable = html is not None and len(html) > 0
            except PlaywrightNotInstalled:
                logger.warning("verify: playwright missing — reachable=False")
                reachable = False
            finally:
                await probe.close()
        except Exception as exc:
            logger.warning("verify: probe failed for %s: %s", url, exc)
            reachable = False
        return tier, reachable

    def score_penalty(self, tier: Tier) -> float:
        """Return a score adjustment for ``tier``.

        T1/T2 = 0.  T3 = -5.  T4 = -10.  T5 = -15.  The scorer applies this
        on top of the base grade to penalize low-trust sources.
        """
        return self._PENALTIES.get(tier, -15.0)
