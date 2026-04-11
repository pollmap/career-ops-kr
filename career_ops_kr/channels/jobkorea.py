"""JobKorea channel — 잡코리아 (www.jobkorea.co.kr).

Backend: ``requests`` + BeautifulSoup.

Notes:
    - 잡코리아는 대형 상업 채용 포털(T1 신뢰도). 대부분의 리스트 페이지는
      인증 없이 접근 가능하며 ``/recruit/joblist`` 가 메인 진입점.
    - **전수 수집 원칙**: 필터링/랭킹은 downstream scorer 에서 처리한다.
      이 채널은 가능한 많은 공고를 수집한다 — ``pages`` 파라미터로 전부
      페이지네이션한다 (기본 3, 최대 20).
    - **절대 가짜 데이터 금지**: fetch 실패 시 빈 리스트 + 로그 warning.
    - 셀렉터는 defensive: primary (``.list-default .title a``) → fallback
      (``a[href*='/Recruit/GI_Read']``) → 일반 anchor + 키워드 스캔. 잡코리아
      의 DOM 이 재설계될 때마다 적어도 fallback 으로는 공고를 건져낸다.

Layout references (2026-04 기준):
    - 리스트: ``https://www.jobkorea.co.kr/recruit/joblist``
    - 검색:   ``https://www.jobkorea.co.kr/Search/?stext=<query>&tabType=recruit``
    - 상세:   ``https://www.jobkorea.co.kr/Recruit/GI_Read/<GI_NO>``
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

BASE_URL = "https://www.jobkorea.co.kr/"
LIST_URL = "https://www.jobkorea.co.kr/recruit/joblist"
SEARCH_URL_TMPL = "https://www.jobkorea.co.kr/Search/?stext={query}&tabType=recruit&Page_No={page}"
LIST_PAGINATED_TMPL = (
    "https://www.jobkorea.co.kr/recruit/joblist?menucode=local&localorder=1&Page_No={page}"
)
DETAIL_PREFIX = "/Recruit/GI_Read/"

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

# 전수 수집 원칙 — 페이지 상한은 abuse 방지용 safety net 일 뿐 기본 필터 아님.
MAX_PAGES_HARD_CAP = 20
DEFAULT_PAGES = 3

# Primary CSS selectors — 잡코리아가 쓰는 known layout (2026-04 기준).
# 하나라도 매치되면 primary path 로 간주, 실패하면 fallback 으로 내려간다.
PRIMARY_SELECTORS: tuple[str, ...] = (
    "div.list-default tr.devloopArea td.tplTit a.link",
    "div.list-default .post-list-info .title a",
    "article.list-post .title a",
    "div.recruit-info a.title",
    "tbody tr td.tplTit a",
)

FALLBACK_ANCHOR_SELECTOR = "a[href*='/Recruit/GI_Read']"


class JobKoreaChannel(BaseChannel):
    """잡코리아 리스트/검색/상세 크롤러.

    전수 수집 — query 없이 호출하면 메인 리스트의 첫 N 페이지를 전부
    가져온다. 필터링은 downstream qualifier/scorer 가 담당한다.
    """

    name = "jobkorea"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 10
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        base_url: str = BASE_URL,
        list_url: str = LIST_URL,
    ) -> None:
        super().__init__()
        self.base_url = base_url
        self.list_url = list_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe — HEAD the base URL."""
        try:
            resp = requests.get(
                self.base_url,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("jobkorea check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return postings — paginated across all requested pages.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword``: str — full-text search term (uses /Search/?stext=).
                ``pages``: int — number of pages to crawl (default 3, max 20).
                ``category``: str — URL hint appended to list URL (optional).

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch error.
        """
        query = query or {}
        keyword = (query.get("keyword") or "").strip()
        pages = min(int(query.get("pages") or DEFAULT_PAGES), MAX_PAGES_HARD_CAP)
        category = (query.get("category") or "").strip()

        all_jobs: list[JobRecord] = []
        seen_ids: set[str] = set()

        for page_no in range(1, pages + 1):
            page_url = self._build_list_url(page_no=page_no, keyword=keyword, category=category)
            html = self._fetch_html(page_url)
            if html is None:
                self.logger.warning("jobkorea: page %d fetch failed — skipping", page_no)
                continue

            page_jobs = self._parse_list_html(html, base_url=page_url)
            new_count = 0
            for job in page_jobs:
                if job.id in seen_ids:
                    continue
                seen_ids.add(job.id)
                all_jobs.append(job)
                new_count += 1
            self.logger.info(
                "jobkorea: page %d parsed %d jobs (%d new)",
                page_no,
                len(page_jobs),
                new_count,
            )
            # 새 공고가 0개면 더 이상 페이지가 없다고 가정하고 조기 종료.
            if new_count == 0 and page_no > 1:
                self.logger.info("jobkorea: no new jobs on page %d — stopping pagination", page_no)
                break

        self.logger.info("jobkorea: total %d unique jobs collected", len(all_jobs))
        return all_jobs

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
            self.logger.warning("jobkorea get_detail parse failed %s: %s", url, exc)
            return None

    # -- URL builders -------------------------------------------------------

    def _build_list_url(self, *, page_no: int, keyword: str, category: str) -> str:
        """Build the paginated list URL respecting keyword/category filters."""
        if keyword:
            return SEARCH_URL_TMPL.format(query=quote(keyword), page=page_no)
        if category:
            sep = "&" if "?" in category else "?"
            return f"{self.list_url}{sep}{category.lstrip('&?')}&Page_No={page_no}"
        return LIST_PAGINATED_TMPL.format(page=page_no)

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
            self.logger.warning("jobkorea: %s returned %s", url, status)
            return None
        # Explicit UTF-8 — jobkorea serves mixed encoding headers; force utf-8.
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Parse a listing page into :class:`JobRecord`\\ s.

        Primary strategy: walk ``PRIMARY_SELECTORS`` until one yields cards.
        Fallback: any anchor matching ``FALLBACK_ANCHOR_SELECTOR``.
        Last resort: generic anchor scan keyed on career keywords.
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
            org = self._extract_org(container) or "잡코리아 기업"
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
                self.logger.warning("jobkorea: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)
        return jobs

    def _records_from_generic_scan(self, soup: BeautifulSoup, *, base_url: str) -> list[JobRecord]:
        """Final fallback — scan every anchor and keep those matching career keywords."""
        career_keywords = (
            "채용",
            "모집",
            "공고",
            "신입",
            "인턴",
            "경력",
            "recruit",
            "career",
        )
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 6 or len(text) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue
            blob = (text + " " + href).lower()
            if not any(kw.lower() in blob for kw in career_keywords):
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
                        org=self._extract_org(container) or "잡코리아 기업",
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
                self.logger.warning("jobkorea: bad generic card %r: %s", text, exc)
                continue
        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse the detail (GI_Read) page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Title candidates (order matters — first match wins)
        title = ""
        for selector in (
            "div.tit-area h3.hd_3",
            "div.recruit-info h3",
            "h1.header-top-title",
            "h1",
            "h2.tit",
        ):
            node = soup.select_one(selector)
            if node:
                title = node.get_text(" ", strip=True)
                if title:
                    break
        if not title:
            title = (
                soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]
            ) or "잡코리아 공고"
        title = title[:200]

        # Body text — whole page fallback
        body_text = soup.get_text(" ", strip=True)[:5000]

        # Organization
        org = ""
        for selector in (
            "div.company-label a",
            "span.coName",
            "a.name",
            "div.co-name",
        ):
            node = soup.select_one(selector)
            if node:
                org = node.get_text(" ", strip=True)
                if org:
                    break
        if not org:
            org = "잡코리아 기업"

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title,
                archetype=self._infer_archetype(title),
                deadline=deadline_parser(body_text) or deadline_parser(title),
                description=body_text,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("jobkorea: bad detail record %r: %s", title, exc)
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
        """Infer a coarse archetype from the title for downstream routing."""
        if not title:
            return None
        if "인턴" in title or "intern" in title.lower():
            return "INTERN"
        if "신입" in title:
            return "ENTRY"
        if "경력" in title:
            return "EXPERIENCED"
        return None
