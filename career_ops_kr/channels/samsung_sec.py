"""Samsung Securities (삼성증권) recruitment channel.

Source: https://www.samsungpop.com/

Tier: 3 (Korean securities firm, public listing). Legitimacy: T1 (official
corporate career page). Samsung 그룹 runs a unified careers portal at
``samsungcareers.com`` but individual 삼성증권 (Samsung POP) postings are
often routed through their own subdomain first. This stub targets the
securities-specific recruit path under the primary ``samsungpop.com``
domain; the tuning pass should decide whether the group-level portal is
a better source.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
site is protected by Akamai bot mitigation, so Scrapling's
``stealth`` fetcher mode (camoufox) is the preferred backend when
available. The generic anchor scan is used as a fallback; on zero
matches :class:`NotTunedYetError` is raised → empty list.

Tuning hint
-----------
Run::

    career-ops channels tune samsung_sec

to capture live HTML. Compare two sources:

    1. ``https://www.samsungpop.com/ui.do?menuId=...`` (direct portal)
    2. ``https://www.samsungcareers.com/hr/`` with ``company=증권`` filter

Prefer whichever exposes structured data (JSON or HTML tables with
``data-*`` attributes). Stealth mode is recommended because Samsung's
Akamai WAF has historically blocked plain httpx clients.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://recruit.samsungsec.com/"
ORG = "삼성증권"
LOCATION = "서울"

SamsungSecChannel = make_stub_channel_class(
    class_name="SamsungSecChannel",
    channel_name="samsung_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="stealth",
)

__all__ = ["LISTING_URL", "ORG", "SamsungSecChannel"]
