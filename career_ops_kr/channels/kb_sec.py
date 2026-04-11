"""KB Securities (KB증권) recruitment channel.

Source: https://recruit.kbsec.com/

Tier: 3 (Korean securities firm, public listing). Legitimacy: T1 (official
corporate career page). KB금융지주 runs a separate group-wide recruiting
site (``careers.kbfg.com``) — this channel targets the securities-only
portal because its postings are tagged by division and are easier to
filter for 디지털/IT/리서치 archetypes.

Status
------
**Stub** — selectors have not yet been tuned against live HTML.
``list_jobs`` runs the generic anchor scan, and raises
:class:`NotTunedYetError` internally (caught + logged) when the
recruitment portal returns a hash-routed SPA that the anchor scan cannot
parse. ``[]`` is returned in that case; no records are fabricated.

Tuning hint
-----------
Run::

    career-ops channels tune kb_sec

to capture live HTML. Likely JSON endpoint candidates to probe during
tuning (XHR inspection on the live site):

    /api/v1/recruit/list
    /recruit/api/notices

If a plain JSON endpoint exists, the tuning CLI should prefer it over
HTML scraping and the stub can be replaced with a direct API channel.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://recruit.kbsec.com/"
ORG = "KB증권"
LOCATION = "서울"

KbSecChannel = make_stub_channel_class(
    class_name="KbSecChannel",
    channel_name="kb_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="dynamic",
)

__all__ = ["LISTING_URL", "ORG", "KbSecChannel"]
