"""Dunamu (두나무 / 업비트 운영사) recruitment channel.

Source: https://careers.dunamu.com/

Tier: 4 (crypto / blockchain infra — top priority for 찬희's archetype
match). Legitimacy: T1 (official corporate career page). Dunamu operates
Upbit (the largest Korean crypto exchange) and Lambda256 (see
:mod:`career_ops_kr.channels.lambda256`); its careers site lists
postings across the entire group including Upbit, Dunamu Research,
Dunamu Art Labs, and 부동산 투자 plaform 스테이션3.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. The
``careers.dunamu.com`` site is a Next.js static-exported SPA backed by
a JSON build manifest at ``/_next/data/<build-id>/index.json``. A
properly tuned channel should prefer that manifest over HTML scraping.
Until tuning lands, Scrapling's ``stealth`` fetcher mode handles
Cloudflare and the generic anchor scan returns best-effort matches.

Tuning hint
-----------
Run::

    career-ops channels tune dunamu

to capture live HTML + XHR traces. Priority order:

    1. JSON manifest — stable, no scraping needed
    2. ``data-testid="job-card"`` elements if the manifest is gone
    3. Fallback to the generic scan (current behaviour)

Each posting's detail page has a structured right-sidebar with
``팀``, ``근무지``, ``마감일``, ``지원 자격`` fields — the detail
parser should extract these into typed :class:`JobRecord` fields.
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://careers.dunamu.com/"
ORG = "두나무 (Dunamu)"
LOCATION = "서울"

DunamuChannel = make_stub_channel_class(
    class_name="DunamuChannel",
    channel_name="dunamu",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="stealth",
)

__all__ = ["LISTING_URL", "ORG", "DunamuChannel"]
