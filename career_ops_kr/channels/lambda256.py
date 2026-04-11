"""Lambda256 recruitment channel — 두나무의 블록체인 인프라 자회사.

Source: https://lambda256.io/careers

Tier: 4 (blockchain infra). Legitimacy: T1 (official corporate career
page). Lambda256 is a Dunamu subsidiary that operates the Luniverse
blockchain-as-a-service platform. Most postings are for 블록체인
프로토콜 엔지니어, 스마트컨트랙트 개발자, and 디지털자산 제품 매니저 —
exceptionally high archetype fit for 찬희.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
careers page is a Webflow-hosted static site with anchor-based job
cards. The generic anchor scan should work once the CSS selectors are
verified; until then, zero matches raises :class:`NotTunedYetError`
(caught → empty list). If Lambda256 retires their standalone site and
consolidates into Dunamu's careers portal, point this channel at
``https://careers.dunamu.com/?team=lambda256`` instead.

Tuning hint
-----------
Run::

    career-ops channels tune lambda256

to capture live HTML. Known upstream quirks:

    * Webflow emits ``.w-dyn-item`` for CMS-driven lists — the job-card
      wrapper is usually under that class
    * 상세 페이지는 ``/careers/<slug>`` 형태의 개별 URL
    * 마감일이 명시되지 않는 경우가 많음 → ``deadline=None`` 이 정상
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://lambda256.io/careers"
ORG = "Lambda256"
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
