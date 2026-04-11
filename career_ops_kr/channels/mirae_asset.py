"""Mirae Asset Securities (미래에셋증권) recruitment channel.

Source: https://securities.miraeasset.com/

Tier: 3 (Korean securities firm, public listing). Legitimacy: T1 (official
corporate career page). No login required to browse active postings, but
the listing surface is a React SPA so Scrapling's dynamic fetcher mode is
the preferred backend.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
:func:`~career_ops_kr.channels._stub_helpers.parse_generic_cards` best-effort
anchor scan is used; when it finds zero cards it raises
:class:`NotTunedYetError` which ``list_jobs`` catches and converts to an
empty list. We never fabricate records — the 실데이터 invariant is absolute.

Tuning hint
-----------
Run::

    career-ops channels tune mirae_asset

to capture a live HTML sample under ``data/tuning/mirae_asset/`` and
regenerate channel-specific selectors. Known upstream path candidates:

    /recruit/
    /careers/
    /about/careers/

If the parent group's (미래에셋금융그룹) unified recruiting portal migrates,
update :data:`LISTING_URL` accordingly.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://securities.miraeasset.com/recruit/"
ORG = "미래에셋증권"
LOCATION = "서울"

MiraeAssetChannel = make_stub_channel_class(
    class_name="MiraeAssetChannel",
    channel_name="mirae_asset",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="dynamic",
)

__all__ = ["LISTING_URL", "ORG", "MiraeAssetChannel"]
