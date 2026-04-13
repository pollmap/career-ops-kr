"""Kiwoom KDA channel — recruit.kiwoom.com (키움증권 공식 채용 페이지).

Backend: ``requests`` + BeautifulSoup. Single landing-page scan
(no pagination — recruit.kiwoom.com surfaces all open postings on the
root page).

Notes:
    - 키움증권 공식 채용(recruit.kiwoom.com)은 일반 공고와 KDA(키움 디지털
      아카데미) 기수 모집을 동시에 게시한다. 이 채널은 둘 다 수집하되,
      KDA 키워드(KDA / 디지털 아카데미 / 기수 / 아카데미 / 수료 / 교육생 / Digital Academy)
      가 매치되면 ``archetype="KDA_COHORT"`` 로 우선 마킹한다.
    - **별도 채널 분리 이유**: 기존 ``kiwoomda.py`` 는 정적 사이트(kiwoomda.com)
      를 본다. ``portals.yml`` 의 ``kiwoom_kda`` 키는 recruit.kiwoom.com 을
      가리켜서 네이밍 불일치 상태였다. 이 파일은 portals.yml 키와 일치시킨
      별도 채널이며 기존 ``kiwoomda.py`` 는 그대로 유지된다.
    - **절대 가짜 데이터 금지**: fetch 실패 시 빈 리스트 + 로그 warning.
    - 셀렉터는 defensive: primary (키움 known layout) → fallback
      (``a[href*='/detail']``) → 일반 anchor + 키워드 스캔 (3-tier).

Layout references (2026-04 기준):
    - 랜딩:   ``https://recruit.kiwoom.com/``
    - 상세:   ``https://recruit.kiwoom.com/detail/<id>`` (추정)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

BASE_URL = "https://www.kiwoom.com/h/help/social/VHelpSocialView"
LIST_URL = "https://www.kiwoom.com/h/help/social/VHelpSocialView"
ORG = "키움증권"

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

KDA_KEYWORDS: tuple[str, ...] = (
    "KDA",
    "디지털 아카데미",
    "Digital Academy",
    "기수",
    "아카데미",
    "수료",
    "교육생",
)

GENERAL_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "신입",
    "인턴",
    "경력",
    "recruit",
)

# Primary CSS selectors — 키움 recruit 페이지의 known layouts (2026-04 기준).
# 하나라도 매치되면 primary path 로 간주, 실패하면 fallback 으로 내려간다.
PRIMARY_SELECTORS: tuple[str, ...] = (
    "div.recruit-list a",
    "ul.list-recruit li a",
    "div.board-list a",
    "table.recruitTable tbody tr a",
    "a[href*='/recruit']",
)

FALLBACK_ANCHOR_SELECTOR = "a[href*='/detail']"


class KiwoomKdaChannel(BaseChannel):
    """키움증권 recruit.kiwoom.com 크롤러 (KDA 우선 마킹).

    일반 채용 공고 + KDA 기수 모집을 동시에 수집한다. KDA 키워드와
    매치되는 공고는 archetype 을 ``KDA_COHORT`` 로 마킹해 downstream
    qualifier/scorer 에서 우선순위를 줄 수 있게 한다.
    """

    name = "kiwoom_kda"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, base_url: str = BASE_URL, list_url: str = LIST_URL) -> None:
        super().__init__()
        self.base_url = base_url
        self.list_url = list_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe — GET the base URL."""
        try:
            resp = requests.get(
                self.base_url,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("kiwoom_kda check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return postings — single landing-page scan (no pagination).

        Args:
            query: Currently unused (kept for Channel protocol compat).

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch error.
        """
        del query  # explicit no-op for protocol compatibility
        html = self._fetch_html(self.list_url)
        if html is None:
            self.logger.warning("kiwoom_kda: list fetch failed — returning empty list")
            return []

        jobs = self._parse_list_html(html, base_url=self.list_url)
        self.logger.info("kiwoom_kda: parsed %d jobs from %s", len(jobs), self.list_url)
        return jobs

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
            self.logger.warning("kiwoom_kda get_detail parse failed %s: %s", url, exc)
            return None

    # -- Fetch helpers ------------------------------------------------------

    def _fetch_html(self, url: str) -> str | None:
        """Fetch ``url`` with retry + rate limiting. Returns text or None."""
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
            self.logger.warning("kiwoom_kda: %s returned %s", url, status)
            return None
        # Explicit UTF-8 — 키움 페이지는 일관성을 보장하지 않으므로 강제.
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Parse a listing page into :class:`JobRecord`\\ s.

        Primary strategy: walk ``PRIMARY_SELECTORS`` until one yields cards.
        Fallback: any anchor matching ``FALLBACK_ANCHOR_SELECTOR``.
        Last resort: generic anchor scan keyed on ``GENERAL_KEYWORDS``.
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

        # 2) Fallback — anchor href matches the detail path
        fallback_anchors = soup.select(FALLBACK_ANCHOR_SELECTOR)
        if fallback_anchors:
            jobs = self._records_from_anchors(fallback_anchors, base_url=base_url)
            if jobs:
                return jobs

        # 3) Last resort — generic anchor scan with career keywords
        return self._records_from_generic_scan(soup, base_url=base_url)

    def _records_from_anchors(self, anchors: list[Tag], *, base_url: str) -> list[JobRecord]:
        """Convert a list of ``<a>`` tags into JobRecords."""
        jobs: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            title = (anchor.get_text(" ", strip=True) or "").strip()
            if not title or len(title) < 3 or len(title) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue
            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["tr", "li", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else title
            org = self._extract_org(container) or ORG
            location = self._extract_location(container)
            deadline = deadline_parser(body_text) or deadline_parser(title)

            try:
                record = JobRecord(
                    id=self._make_id(url, title),
                    source_url=url,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org=org[:100],
                    title=title[:200],
                    archetype=self._infer_archetype(title),
                    deadline=deadline,
                    location=location,
                    description=body_text[:2000],
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("kiwoom_kda: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)
        return jobs

    def _records_from_generic_scan(self, soup: BeautifulSoup, *, base_url: str) -> list[JobRecord]:
        """Final fallback — scan every anchor and keep career-keyword matches."""
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
            blob = (text + " " + href).lower()
            # KDA 키워드도 generic scan 단계에서 함께 체크해서 놓치지 않게.
            keyword_hit = any(kw.lower() in blob for kw in GENERAL_KEYWORDS) or any(
                kw.lower() in blob for kw in KDA_KEYWORDS
            )
            if not keyword_hit:
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
                        org=self._extract_org(container) or ORG,
                        title=text[:200],
                        archetype=self._infer_archetype(text),
                        deadline=deadline_parser(body_text),
                        location=self._extract_location(container),
                        description=body_text[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("kiwoom_kda: bad generic card %r: %s", text, exc)
                continue
        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Title candidates (order matters — first match wins)
        title = ""
        for selector in (
            "h1.recruit-title",
            "div.recruit-title",
            ".recruit-title",
            "h1",
            "h2.tit",
            "h2",
        ):
            node = soup.select_one(selector)
            if node:
                title = node.get_text(" ", strip=True)
                if title:
                    break
        if not title:
            title = (
                soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]
            ) or "키움증권 채용"
        title = title[:200]

        # Body text — whole page fallback
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
            self.logger.warning("kiwoom_kda: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny extractors ----------------------------------------------------

    @staticmethod
    def _extract_org(container: Tag | None) -> str | None:
        """Best-effort organization extractor from a card container."""
        if container is None:
            return None
        for selector in (
            ".coName",
            ".name",
            ".company a",
            ".company-name",
            "span.corp",
        ):
            node = container.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None

    @staticmethod
    def _extract_location(container: Tag | None) -> str | None:
        """Best-effort location extractor from a card container."""
        if container is None:
            return None
        for selector in (
            ".loc",
            ".location",
            ".region",
            "span.loc",
        ):
            node = container.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None

    @staticmethod
    def _infer_archetype(title: str) -> str | None:
        """Infer a coarse archetype from the title for downstream routing.

        KDA 키워드를 우선 매칭한 뒤 일반 인턴/신입/경력 분류로 fallthrough.
        """
        if not title:
            return None
        # KDA 우선 매칭 — KDA / 디지털 아카데미 / 기수 / 아카데미 / 수료 / 교육생 / Digital Academy
        for kw in KDA_KEYWORDS:
            if kw in title or kw.lower() in title.lower():
                return "KDA_COHORT"
        if "인턴" in title or "intern" in title.lower():
            return "INTERN"
        if "신입" in title:
            return "ENTRY"
        if "경력" in title:
            return "EXPERIENCED"
        return None
