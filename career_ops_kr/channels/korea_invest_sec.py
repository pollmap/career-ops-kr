"""한국투자증권 (Korea Investment & Securities) recruitment channel.

Source: https://recruit.truefriend.com/
Tier: 3 (securities). Legitimacy: T1 (official corporate career page).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://recruit.truefriend.com/"
ORG = "한국투자증권"
LOCATION = "서울"

KoreaInvestSecChannel = make_stub_channel_class(
    class_name="KoreaInvestSecChannel",
    channel_name="korea_invest_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "KoreaInvestSecChannel"]
