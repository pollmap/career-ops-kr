"""Mjob channel — 중소벤처기업부/중소기업진흥공단(KOSME) SME job portal (mjob.mainbiz.or.kr).

Backend: ``requests`` + BeautifulSoup.

Notes:
    - mjob.mainbiz.or.kr 는 중소기업진흥공단(KOSME)이 운영하는 중소기업 특화
      채용 포털이다.
    - 3-tier fallback (primary selectors → anchor href filter → generic keyword
      scan) + LIST_URL → ALT_LIST_URL → LANDING_URL 순서로 방어한다.
    - **절대 가짜 데이터 금지**: 모든 경로가 빈 결과를 반환하면 빈 리스트 +
      info log 만 남긴다.
    - requests.Session 없이 단순 ``requests.get`` 을 사용한다 (테스트 monkeypatch
      용이).

Layout references (2026-04 기준):
    - 랜딩:  ``https://mjob.mainbiz.or.kr/``
    - 리스트: ``https://mjob.mainbiz.or.kr/recruit/list.do``
    - ALT:   ``https://mjob.mainbiz.or.kr/work/list.do``
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://mjob.mainbiz.or.kr/"
LIST_URL = "https://mjob.mainbiz.or.kr/recruit/list.do"
ALT_LIST_URL = "https://mjob.mainbiz.or.kr/work/list.do"
ORG = "중소기업진흥공단 일자리"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 "
    "career-ops-kr/0.2"
)

DEFAULT_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
}

# Generic career keywords used for the last-resort anchor scan.
_CAREER_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "인턴",
    "신입",
    "채용공고",
    "경력",
)

# Primary CSS selectors tried in order — known mjob.mainbiz.or.kr layouts.
_PRIMARY_SELECTORS: tuple[str, ...] = (
    "table.list tbody tr td a",
    "div.board-list ul li a",
    "div.list-wrap ul li a",
    "div.recruit-list a",
    "table.board-table tbody tr td a",
)

# Href-based fallback selectors for anchor scanning.
_HREF_FALLBACK_SELECTORS: tuple[str, ...] = (
    "a[href*='/recruit/']",
    "a[href*='/work/']",
)


class MjobChannel(BaseChannel):
    """중소기업진흥공단(KOSME) mjob.mainbiz.or.kr HTML scraper.

    Three URLs are tried in order:
        1. ``LIST_URL`` (primary list page)
        2. ``ALT_LIST_URL`` (alternate list page)
        3. ``LANDING_URL`` (generic anchor scan fallback)

    Within each page a 3-tier parsing strategy is applied:
        1. Primary CSS selectors (known DOM layouts)
        2. Anchor href containing ``/recruit/`` or ``/work/``
        3. Generic anchor scan keyed on career keywords
    """

    name = "mjob"
    tier = 2
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        list_url: str = LIST_URL,
        alt_list_url: str = ALT_LIST_URL,
        landing_url: str = LANDING_URL,
    ) -> None:
        super().__init__()
        self.list_url = list_url
        self.alt_list_url = alt_list_url
        self.landing_url = landing_url

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
            self.logger.debug("mjob check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return KOSME mjob postings.

        Strategy:
            1. Fetch ``self.list_url`` and parse.
            2. If empty, fetch ``self.alt_list_url`` and parse.
            3. If still empty, fetch ``self.landing_url`` and do generic scan.
            4. Dedup by ``id``.

        Args:
            query: Currently unused — kept for API parity with other channels.

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch / parse error.
        """
        del query  # reserved for future filter support

        seen_ids: set[str] = set()
        results: list[JobRecord] = []

        for url in (self.list_url, self.alt_list_url, self.landing_url):
            html = self._fetch_html(url)
            if html is None:
                continue
            jobs = self._parse_list_html(html, base_url=url)
            self.logger.info("mjob: %s parsed %d jobs", url, len(jobs))
            if not jobs:
                continue
            # Dedup by id — later URLs may produce overlapping records.
            for job in jobs:
                if job.id not in seen_ids:
                    seen_ids.add(job.id)
                    results.append(job)
            # Stop after the first URL that yields results.
            break

        if not results:
            self.logger.info("mjob: no candidates from any URL — returning []")
        return results

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch + parse a single detail page.

        Returns ``None`` on any failure — never raises to caller.
        """
        html = self._fetch_html(url)
        if html is None:
            return None
        try:
            return self._parse_detail_html(html, url=url)
        except Exception as exc:
            self.logger.warning("mjob get_detail parse failed %s: %s", url, exc)
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
            self.logger.warning("mjob: %s returned %s", url, status)
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Parse a listing page into :class:`JobRecord`s.

        3-tier strategy:
            1. Primary selectors (known DOM shapes)
            2. Href-based fallback (anchor href contains /recruit/ or /work/)
            3. Generic keyword anchor scan
        """
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # 1) Primary path — known layouts
        for selector in _PRIMARY_SELECTORS:
            anchors = soup.select(selector)
            if anchors:
                jobs = self._records_from_anchors(anchors, base_url=base_url)
                if jobs:
                    return jobs

        # 2) Fallback — anchor href contains /recruit/ or /work/
        for selector in _HREF_FALLBACK_SELECTORS:
            fallback_anchors = soup.select(selector)
            if fallback_anchors:
                jobs = self._records_from_anchors(fallback_anchors, base_url=base_url)
                if jobs:
                    return jobs

        # 3) Last resort — generic career keyword anchor scan
        return self._records_from_generic_scan(soup, base_url=base_url)

    def _records_from_anchors(
        self,
        anchors: list[Tag],
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Convert a list of ``<a>`` tags into JobRecords.

        Anchors are kept if their combined text + href matches at least one
        career keyword. Navigation links and very short labels are skipped.
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

            blob_lower = (title + " " + href).lower()
            if not any(kw.lower() in blob_lower for kw in _CAREER_KEYWORDS):
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
                self.logger.warning("mjob: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)

            if len(jobs) >= 50:
                break

        return jobs

    def _records_from_generic_scan(
        self,
        soup: BeautifulSoup,
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Final fallback — scan every anchor and keep keyword-matching ones."""
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
            if not any(kw.lower() in blob_lower for kw in _CAREER_KEYWORDS):
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
                        deadline=deadline_parser(body_text) or deadline_parser(text),
                        description=body_text[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("mjob: bad generic card %r: %s", text, exc)
                continue

            if len(results) >= 50:
                break

        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Title candidates — first match wins
        title = ""
        for selector in (
            "h1",
            "h2",
            "td.title",
            "div.view-title",
            ".title",
        ):
            node = soup.select_one(selector)
            if node:
                candidate = node.get_text(" ", strip=True)
                if candidate:
                    title = candidate
                    break
        if not title:
            title = (
                soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]
            ) or "KOSME 채용공고"
        title = title[:200]

        body_text = soup.get_text(" ", strip=True)[:5000]

        # Org extraction: td.org or prefix before first space/공백 in title
        org = ORG
        org_node = soup.select_one("td.org")
        if org_node:
            candidate = org_node.get_text(" ", strip=True)
            if candidate:
                org = candidate[:100]

        # Deadline from text containing 마감 or 접수기간
        deadline = None
        for line in body_text.split():
            if "마감" in line or "접수기간" in line:
                deadline = deadline_parser(line)
                if deadline:
                    break
        if deadline is None:
            deadline = deadline_parser(body_text) or deadline_parser(title)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org,
                title=title,
                archetype=self._infer_archetype(title),
                deadline=deadline,
                description=body_text,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("mjob: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny helpers -------------------------------------------------------

    @staticmethod
    def _infer_archetype(title: str) -> str | None:
        """Infer job archetype from a posting title.

        Order matters — more specific tags win first.
        """
        if not title:
            return None
        if "체험형" in title:
            return "EXPERIENCE_TYPE"
        if "인턴" in title or "intern" in title.lower():
            return "INTERN"
        if "신입" in title:
            return "ENTRY"
        return "GENERAL"
