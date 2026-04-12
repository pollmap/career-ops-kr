"""코인원 (Coinone) recruitment channel.

Source: https://coinone.career/
Tier: 4 (crypto). Legitimacy: T1 (official corporate career page).
Coinone is a major Korean cryptocurrency exchange.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://coinone.co.kr/careers"
ORG = "코인원 (Coinone)"
LOCATION = "서울"

CoinoneChannel = make_stub_channel_class(
    class_name="CoinoneChannel",
    channel_name="coinone",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "CoinoneChannel"]
