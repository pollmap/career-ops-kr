"""IBK투자증권 (IBK Securities) recruitment channel.

Source: https://www.ibks.com/recruit/
Tier: 3 (securities). Legitimacy: T1 (official corporate career page).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://www.ibks.com/recruit/"
ORG = "IBK투자증권"
LOCATION = "서울"

IbkSecChannel = make_stub_channel_class(
    class_name="IbkSecChannel",
    channel_name="ibk_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "IbkSecChannel"]
