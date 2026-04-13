"""Bithumb (빗썸) recruitment channel.

Source: https://bithumbcorp.com/careers/

Tier: 4 (crypto / blockchain infra). Legitimacy: T1 (official corporate
career page). 빗썸코리아 operates the 빗썸 exchange — the second-largest
domestic crypto exchange by volume. Recent hiring focuses on 블록체인
인프라, 보안, 리서치, and 디지털자산 프로덕트 개발자 roles.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
careers page is historically a Wordpress-backed static site with
postings served as individual anchor links to ``bithumbcorp.com/jobs/<slug>``.
The generic anchor scan should therefore work reasonably well, but
zero matches raises :class:`NotTunedYetError` which is converted to
an empty list. No records are fabricated.

Tuning hint
-----------
Run::

    career-ops channels tune bithumb

to capture live HTML. Priority items:

    * Identify the category filter (``?category=tech`` vs ``?category=product``)
    * Capture the posting-title class (likely ``.job-title`` or ``.career__title``)
    * Extract the deadline — Bithumb often leaves it open-ended (``채용 시 마감``)
      which :func:`deadline_parser` correctly returns ``None`` for
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://www.bithumb.com/react/recruit/main"
ORG = "빗썸 (Bithumb)"
LOCATION = "서울"

BithumbChannel = make_stub_channel_class(
    class_name="BithumbChannel",
    channel_name="bithumb",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="stealth",
)

__all__ = ["LISTING_URL", "ORG", "BithumbChannel"]
