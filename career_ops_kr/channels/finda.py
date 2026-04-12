"""핀다 (Finda) recruitment channel.

Source: https://finda.career/
Tier: 4 (fintech). Legitimacy: T1 (official corporate career page).
Finda is a leading Korean financial comparison platform (대출 비교).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://finda.co.kr/careers"
ORG = "핀다 (Finda)"
LOCATION = "서울"

FindaChannel = make_stub_channel_class(
    class_name="FindaChannel",
    channel_name="finda",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
)

__all__ = ["LISTING_URL", "ORG", "FindaChannel"]
