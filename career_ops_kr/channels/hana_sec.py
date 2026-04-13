"""Hana Securities (하나증권) recruitment channel.

Source: https://careers.hanafn.com/

Tier: 3 (Korean securities firm, public listing). Legitimacy: T1 (official
corporate career page).

**Important**: 하나증권 does not run an independent recruiting site —
postings are published through the unified 하나금융그룹 (Hana Financial
Group) portal at ``careers.hanafn.com``. Listings span all subsidiaries
(하나은행, 하나증권, 하나카드, 하나캐피탈, 하나생명). This channel filters
by the 계열사 tag ``하나증권`` when selectors are tuned; until then it
returns every posting matched by the generic scan and leaves
disambiguation to the downstream archetype classifier.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
generic anchor scan is used as a fallback and raises
:class:`NotTunedYetError` on zero matches (caught → empty list).

Tuning hint
-----------
Run::

    career-ops channels tune hana_sec

to capture live HTML. Priority during tuning:

    1. Find the 계열사 filter selector so the channel can post
       ``?company=하나증권`` or equivalent.
    2. Identify the posting-row element (likely a card component).
    3. Extract the deadline field — Hana's format typically uses
       ``YYYY.MM.DD ~ YYYY.MM.DD``.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://www.hanaw.com/main/recruit/listRecruit.cmd"
ORG = "하나증권"
LOCATION = "서울"

HanaSecChannel = make_stub_channel_class(
    class_name="HanaSecChannel",
    channel_name="hana_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="dynamic",
)

__all__ = ["LISTING_URL", "ORG", "HanaSecChannel"]
