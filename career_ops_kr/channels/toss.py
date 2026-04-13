"""Toss (토스) recruitment channel — 비바리퍼블리카 그룹 통합.

Source: https://toss.im/career/

Tier: 4 (fintech). Legitimacy: T1 (official corporate career page).

The 토스 careers portal is the unified entry point for every 비바리퍼블리카
subsidiary. A single posting page typically advertises one of the following
entities, which the tuning pass should surface as a ``company`` tag and
the downstream archetype classifier should disambiguate:

    * 비바리퍼블리카 (Toss Core — 결제/플랫폼/인프라)
    * 토스뱅크 (banking license)
    * 토스증권 (securities brokerage)
    * 토스페이먼츠 (PG / 가맹점 결제)
    * 토스인슈어런스 (insurance)
    * 토스플레이스 (offline POS)
    * 토스씨엑스 (CX operations)

user's highest-interest entities are 토스증권 and 토스뱅크 — the
channel should prefer those when a filter is available.

Status
------
**Stub** — selectors have not yet been tuned against live HTML. Toss
uses a Next.js SSR site with structured ``__NEXT_DATA__`` JSON embedded
in every page. A tuned channel should parse that JSON directly rather
than HTML. Scrapling's ``stealth`` mode handles the Cloudflare challenge
during list traversal; the generic anchor scan returns best-effort
matches until tuning lands.

Tuning hint
-----------
Run::

    career-ops channels tune toss

to capture a live sample. Targets:

    1. ``<script id="__NEXT_DATA__">`` JSON — contains the full posting list
    2. ``company`` field inside each posting for subsidiary disambiguation
    3. ``dueDate`` field for :func:`deadline_parser` input
"""

from __future__ import annotations

from career_ops_kr.channels._stub_helpers import make_stub_channel_class

LISTING_URL = "https://toss.im/career/jobs"
ORG = "토스 (비바리퍼블리카 그룹)"
LOCATION = "서울"

TossChannel = make_stub_channel_class(
    class_name="TossChannel",
    channel_name="toss",
    channel_tier=4,
    listing_url=LISTING_URL,
    org=ORG,
    location=LOCATION,
    legitimacy_tier="T1",
    fetcher_mode="stealth",
)

__all__ = ["LISTING_URL", "ORG", "TossChannel"]
