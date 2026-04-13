"""대신증권 (Daishin Securities) recruitment channel.

Source: https://www.daishin.com/recruit/
Tier: 3 (securities). Legitimacy: T1 (official corporate career page).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://www.daishin.com/g.ds?m=4027&p=3979&v=2983"
ORG = "대신증권"
LOCATION = "서울"

DaishinSecChannel = make_stub_channel_class(
    class_name="DaishinSecChannel",
    channel_name="daishin_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "DaishinSecChannel"]
