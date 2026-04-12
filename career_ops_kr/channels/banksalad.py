"""뱅크샐러드 (Banksalad) recruitment channel.

Source: https://career.banksalad.com/
Tier: 4 (fintech). Legitimacy: T1 (official corporate career page).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://career.banksalad.com/"
ORG = "뱅크샐러드 (Banksalad)"
LOCATION = "서울"

BanksaladChannel = make_stub_channel_class(
    class_name="BanksaladChannel",
    channel_name="banksalad",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "BanksaladChannel"]
