"""미래내일 일경험 channel — work.go.kr/experi/.

Backend: ``requests`` + BeautifulSoup.

Notes:
    - 미래내일 일경험은 정부(고용노동부) 운영 청년 일경험 프로그램으로
      ``인턴형`` / ``프로젝트형`` / ``체험형`` 3종이 상시 모집된다.
    - 별도 채널 ``yw_work24``\\ 는 ``yw.work24.go.kr`` 만 프로브하며 auth-gated 라
      0건 상태이므로, 본 채널은 ``www.work.go.kr/experi/index.do`` 와 ALT
      리스트 URL 두 곳을 직접 스캔한다.
    - work.go.kr 는 정부 포털이라 DOM 이 robust 하지 않을 수 있다. 3-tier
      fallback (primary selectors → anchor href filter → generic keyword
      scan) + LANDING → ALT URL 재시도로 방어한다.
    - **절대 가짜 데이터 금지**: 모든 경로가 빈 결과를 돌려주면 빈 리스트 +
      info log 만 남긴다.
    - work.go.kr 는 JSESSIONID 쿠키 의존성이 있을 수 있어 ``requests.Session``
      을 쓰지 않고 단순 ``requests.get`` 만 사용한다 (테스트 monkeypatch 용이).

Layout references (2026-04 기준):
    - 랜딩:  ``https://www.work.go.kr/experi/index.do``
    - 리스트: ``https://www.work.go.kr/experi/experRecruit/list.do``
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://www.work.go.kr/experi/index.do"
ALT_LIST_URL = "https://www.work.go.kr/experi/experRecruit/list.do"
ORG = "미래내일 일경험"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    "career-ops-kr/0.2.0"
)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
}

# 미래내일 일경험 트랙 구분 키워드 — anchor 텍스트에 하나라도 포함되면
# 미래내일 후보로 간주한다.
TYPE_KEYWORDS: tuple[str, ...] = (
    "인턴형",
    "프로젝트형",
    "체험형",
    "일경험",
    "미래내일",
)

# Generic scan fallback 에 쓰이는 일반 채용 키워드. TYPE_KEYWORDS 와 OR 결합한다.
GENERAL_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "인턴",
    "experi",
    "recruit",
)

# Primary CSS selectors — work.go.kr/experi 에서 관찰된 known layouts.
# 하나라도 매치되면 primary path 로 간주, 실패하면 fallback 으로 내려간다.
PRIMARY_SELECTORS: tuple[str, ...] = (
    "div.list-card a",
    "ul.board-list li a",
    "div.recruit-list a",
    "table.board-table tbody tr a",
    "a[href*='experi']",
)

FALLBACK_ANCHOR_SELECTOR = "a[href*='experi']"


class MiraeNaeilChannel(BaseChannel):
    """미래내일 일경험 (work.go.kr/experi) HTML scraper.

    Two URLs are tried in order — ``LANDING_URL`` first, then ``ALT_LIST_URL``
    if the landing page yields zero candidates. Within each page a 3-tier
    parsing strategy is used (primary selectors → anchor href filter →
    generic keyword scan).
    """

    name = "mirae_naeil"
    tier = 2
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        landing_url: str = LANDING_URL,
        alt_list_url: str = ALT_LIST_URL,
    ) -> None:
        super().__init__()
        self.landing_url = landing_url
        self.alt_list_url = alt_list_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe — GET the landing URL."""
        try:
            resp = requests.get(
                self.landing_url,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("mirae_naeil check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return 미래내일 일경험 postings.

        Strategy:
            1. Fetch ``self.landing_url`` and try to parse cards.
            2. If empty, fetch ``self.alt_list_url`` and parse again.
            3. If both empty, return ``[]`` plus an info log.

        Args:
            query: Currently unused — kept for API parity with other channels.

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch / parse error
            (실데이터 원칙 — 가짜 데이터 절대 생성 금지).
        """
        # Defensive: keep ``query`` reachable for future filters; nothing to
        # consume right now.
        del query

        for url in (self.landing_url, self.alt_list_url):
            html = self._fetch_html(url)
            if html is None:
                continue
            jobs = self._parse_list_html(html, base_url=url)
            self.logger.info(
                "mirae_naeil: %s parsed %d jobs",
                url,
                len(jobs),
            )
            if jobs:
                return jobs

        self.logger.info(
            "mirae_naeil: no candidates from LANDING or ALT — returning []",
        )
        return []

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch + parse a single detail page.

        Returns ``None`` on any failure — never raises to caller.
        """
        html = self._fetch_html(url)
        if html is None:
            return None
        try:
            return self._parse_detail_html(html, url=url)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("mirae_naeil get_detail parse failed %s: %s", url, exc)
            return None

    # -- Fetch helpers ------------------------------------------------------

    def _fetch_html(self, url: str) -> str | None:
        """Fetch ``url`` with retry + rate limiting. Returns text or None.

        Forces ``utf-8`` because work.go.kr serves mixed encoding headers.
        """
        resp = self._retry(
            requests.get,
            url,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        if resp is None:
            return None
        status = getattr(resp, "status_code", None)
        if status != 200:
            self.logger.warning("mirae_naeil: %s returned %s", url, status)
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Parse a listing page into :class:`JobRecord`\\ s.

        Primary strategy: walk ``PRIMARY_SELECTORS`` until one yields cards.
        Fallback: any anchor matching ``FALLBACK_ANCHOR_SELECTOR``.
        Last resort: generic anchor scan keyed on TYPE + GENERAL keywords.
        """
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # 1) Primary path — known layouts
        for selector in PRIMARY_SELECTORS:
            anchors = soup.select(selector)
            if anchors:
                jobs = self._records_from_anchors(anchors, base_url=base_url)
                if jobs:
                    return jobs

        # 2) Fallback — anchor href contains "experi"
        fallback_anchors = soup.select(FALLBACK_ANCHOR_SELECTOR)
        if fallback_anchors:
            jobs = self._records_from_anchors(fallback_anchors, base_url=base_url)
            if jobs:
                return jobs

        # 3) Last resort — generic anchor scan with TYPE + GENERAL keywords
        return self._records_from_generic_scan(soup, base_url=base_url)

    def _records_from_anchors(
        self,
        anchors: list[Tag],
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Convert a list of ``<a>`` tags into JobRecords.

        Anchors are kept only if their text matches at least one of
        ``TYPE_KEYWORDS`` (this is what distinguishes 미래내일 일경험 cards
        from generic site navigation links that also live under ``experi/``).
        """
        jobs: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            title = (anchor.get_text(" ", strip=True) or "").strip()
            if not title or len(title) < 4 or len(title) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            # Must match at least one TYPE keyword in title or href.
            blob_lower = (title + " " + href).lower()
            if not any(kw.lower() in blob_lower for kw in TYPE_KEYWORDS):
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["tr", "li", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else title
            deadline = deadline_parser(body_text) or deadline_parser(title)

            try:
                record = JobRecord(
                    id=self._make_id(url, title),
                    source_url=url,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org=ORG,
                    title=title[:200],
                    archetype=self._infer_archetype(title),
                    deadline=deadline,
                    description=body_text[:2000],
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("mirae_naeil: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)
        return jobs

    def _records_from_generic_scan(
        self,
        soup: BeautifulSoup,
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Final fallback — scan every anchor and keep keyword-matching ones.

        Match rule: ``TYPE_KEYWORDS`` AND (``GENERAL_KEYWORDS`` OR href hint).
        Falls back to TYPE-only match if nothing pairs.
        """
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 4 or len(text) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            blob_lower = (text + " " + href).lower()
            type_match = any(kw.lower() in blob_lower for kw in TYPE_KEYWORDS)
            general_match = any(kw.lower() in blob_lower for kw in GENERAL_KEYWORDS)
            # 두 가지 모두 매치돼야 미래내일 후보로 인정 — 일반 채용 anchor 와의
            # 충돌을 막는다.
            if not (type_match and general_match):
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["tr", "li", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else text
            try:
                results.append(
                    JobRecord(
                        id=self._make_id(url, text),
                        source_url=url,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=ORG,
                        title=text[:200],
                        archetype=self._infer_archetype(text),
                        deadline=deadline_parser(body_text),
                        description=body_text[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("mirae_naeil: bad generic card %r: %s", text, exc)
                continue
        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Title candidates (order matters — first match wins)
        title = ""
        for selector in (
            "div.recruit-detail h1",
            "div.detail-header h2",
            "h1.title",
            "h1",
            "h2.title",
            ".title",
        ):
            node = soup.select_one(selector)
            if node:
                title = node.get_text(" ", strip=True)
                if title:
                    break
        if not title:
            title = (
                soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]
            ) or "미래내일 일경험"
        title = title[:200]

        body_text = soup.get_text(" ", strip=True)[:5000]

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=ORG,
                title=title,
                archetype=self._infer_archetype(title),
                deadline=deadline_parser(body_text) or deadline_parser(title),
                description=body_text,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("mirae_naeil: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny helpers -------------------------------------------------------

    @staticmethod
    def _infer_archetype(title: str) -> str | None:
        """Infer 미래내일 일경험 archetype from a title.

        Order matters — more specific tags win first so that ``인턴형``
        is not swallowed by the generic ``인턴`` rule.
        """
        if not title:
            return None
        if "인턴형" in title:
            return "INTERN_TYPE"
        if "프로젝트형" in title:
            return "PROJECT_TYPE"
        if "체험형" in title:
            return "EXPERIENCE_TYPE"
        if "인턴" in title or "intern" in title.lower():
            return "INTERN"
        return None
