"""NH Investment & Securities (NH투자증권) recruitment channel.

Source: https://recruit.nhqv.com/

Tier: 3 (Korean securities firm, public listing). Legitimacy: T1 (official
corporate career page). NH투자증권 is part of the NH농협금융지주 group
(the largest domestic agricultural-banking group) but runs its own
``nhqv.com`` recruiting portal distinct from the group-wide site.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
recruiting portal historically used a JSP-rendered listing with a
``/recruit/list.do`` endpoint, but recent audits suggest a migration to
a React SPA. Scrapling's ``dynamic`` mode is used to execute the
JavaScript required to populate the listing, then the generic anchor
scan extracts postings. On zero matches :class:`NotTunedYetError` is
raised and converted to an empty list.

Tuning hint
-----------
Run::

    career-ops channels tune nh_sec

to capture live HTML. Check for:

    * XHR to ``/api/recruit/notices`` or similar — preferable to HTML
    * ``data-notice-id`` attributes on card rows
    * 마감일 rendered as ``~ YYYY.MM.DD`` inside a ``.deadline`` span
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://nhqv.recruiter.co.kr/career/home"
ORG = "NH투자증권"
LOCATION = "서울"

NhSecChannel = make_stub_channel_class(
    class_name="NhSecChannel",
    channel_name="nh_sec",
    channel_tier=3,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="dynamic",
)

__all__ = ["LISTING_URL", "ORG", "NhSecChannel"]
