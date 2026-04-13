"""Lambda256 / Nodit recruitment channel — 두나무의 블록체인 인프라 자회사.

Source: https://www.nodit.io/careers

Tier: 4 (blockchain infra). Legitimacy: T1 (official corporate career
page). Lambda256(루니버스)는 2024년 Nodit으로 리브랜딩.
Most postings are for 블록체인 프로토콜 엔지니어, 스마트컨트랙트 개발자,
디지털자산 제품 매니저 — 찬희 archetype fit 최상위.

2026-04 URL 변경: lambda256.io → nodit.io (리브랜딩).
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://www.nodit.io/careers"
ORG = "Nodit (Lambda256)"
LOCATION = "서울"

Lambda256Channel = make_stub_channel_class(
    class_name="Lambda256Channel",
    channel_name="lambda256",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="dynamic",
)

__all__ = ["LISTING_URL", "ORG", "Lambda256Channel"]
