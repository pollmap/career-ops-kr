"""Linkareer (링커리어) channel — intern & activity listings.

Source: https://linkareer.com/

Backend: ``requests`` + JSON (``__NEXT_DATA__``) / BeautifulSoup HTML fallback.

Notes:
    - 링커리어는 Next.js SSR 기반. ``<script id="__NEXT_DATA__">`` 태그에
      페이지 데이터가 JSON 으로 내장되어 있어 CSS 셀렉터보다 안정적으로
      파싱할 수 있다.
    - **3단계 수집 전략**:
        1. ``__NEXT_DATA__`` JSON 파싱 (가장 안정적)
        2. CSS 셀렉터 (카드/리스트 레이아웃)
        3. href 패턴 generic anchor scan
    - **금융 키워드 검색**: ``?query=<kw>`` 파라미터로 금융 관련 공고를
      직접 서버에서 필터링해 수집. 각 키워드 1~2 페이지.
    - 수집 후 타이틀 재필터링 없음 — downstream scorer 가 처리.
    - 실패 시 빈 리스트 반환. 절대 가짜 데이터 금지.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://linkareer.com/"
ACTIVITY_SEARCH_TMPL = "https://linkareer.com/list/activity?query={kw}&page={page}"
INTERN_SEARCH_TMPL = "https://linkareer.com/list/intern?query={kw}&page={page}"
ACTIVITY_DEFAULT_URL = "https://linkareer.com/list/activity"
INTERN_DEFAULT_URL = "https://linkareer.com/list/intern"
MAX_PAGES = 2

FINANCIAL_QUERIES: tuple[str, ...] = (
    "금융",
    "은행",
    "증권",
    "보험",
    "핀테크",
    "자산운용",
    "카드",
    "캐피탈",
    "저축은행",
    "디지털자산",
    "블록체인",
    "투자",
)

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
    "Referer": "https://linkareer.com/",
}

# CSS selectors — Next.js 기반 링커리어 (2026-04 기준).
PRIMARY_SELECTORS: tuple[str, ...] = (
    ".ActivityCard a",
    ".activity-card a",
    ".recruit-card a",
    ".list-item a",
    "article.card a",
    "div.card-wrap a",
    "[class*='Card'] a",
    "[class*='card'] a",
    "[class*='List'] a",
    "[class*='Item'] a",
)

FALLBACK_ANCHOR_SELECTOR = "a[href*='/intern/'], a[href*='/activity/'], a[href*='/recruit/']"

GENERIC_HREF_PATTERNS: tuple[str, ...] = (
    "/intern/",
    "/activity/",
    "/recruit/",
    "/competition/",
)


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------


class LinkareerChannel(BaseChannel):
    """링커리어 인턴/대외활동/채용 공고 수집기 (requests + Next.js JSON).

    전략:
        1. 금융 키워드별 검색 URL 에서 ``__NEXT_DATA__`` JSON 파싱.
        2. JSON 실패 시 CSS 셀렉터 fallback.
        3. CSS 실패 시 href 패턴 generic anchor scan.
    """

    name = "linkareer"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 10
    default_legitimacy_tier = "T1"

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe -- GET the base URL."""
        try:
            resp = requests.get(BASE_URL, headers=DEFAULT_HEADERS, timeout=10)
        except requests.RequestException as exc:
            self.logger.debug("linkareer check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """금융 키워드 검색 → 인턴/대외활동 페이지를 수집해 반환.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword``: str -- single keyword override.

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch error.
        """
        q = query or {}
        keyword_override = (q.get("keyword") or "").strip()
        search_keywords = (keyword_override,) if keyword_override else FINANCIAL_QUERIES

        all_jobs: list[JobRecord] = []
        seen_ids: set[str] = set()

        for kw in search_keywords:
            for tmpl in (ACTIVITY_SEARCH_TMPL, INTERN_SEARCH_TMPL):
                for page in range(1, MAX_PAGES + 1):
                    url = tmpl.format(kw=quote(kw), page=page)
                    html = self._fetch_html(url)
                    if html is None:
                        break
                    page_jobs = self._parse_list_html(html, base_url=url)
                    new_count = 0
                    for job in page_jobs:
                        if job.id not in seen_ids:
                            seen_ids.add(job.id)
                            all_jobs.append(job)
                            new_count += 1
                    self.logger.info(
                        "linkareer: kw=%r %s p%d → %d parsed / %d new",
                        kw, "activity" if "activity" in url else "intern",
                        page, len(page_jobs), new_count,
                    )
                    # 새 공고 없으면 다음 페이지 건너뜀
                    if new_count == 0 and page >= 2:
                        break

        # 키워드 없이 기본 페이지도 fallback 으로 수집
        if not keyword_override:
            for listing_url in (ACTIVITY_DEFAULT_URL, INTERN_DEFAULT_URL):
                html = self._fetch_html(listing_url)
                if html is None:
                    continue
                for job in self._parse_list_html(html, base_url=listing_url):
                    if job.id not in seen_ids:
                        seen_ids.add(job.id)
                        all_jobs.append(job)

        self.logger.info("linkareer: total %d unique jobs collected", len(all_jobs))
        return all_jobs

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch + parse a single detail page."""
        html = self._fetch_html(url)
        if html is None:
            return None
        try:
            return self._parse_detail_html(html, url=url)
        except Exception as exc:
            self.logger.warning("linkareer get_detail parse failed %s: %s", url, exc)
            return None

    # -- Fetch --------------------------------------------------------------

    def _fetch_html(self, url: str) -> str | None:
        resp = self._retry(requests.get, url, headers=DEFAULT_HEADERS, timeout=15)
        if resp is None:
            return None
        status = getattr(resp, "status_code", None)
        if status != 200:
            self.logger.warning("linkareer: %s returned %s", url, status)
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """3-tier: __NEXT_DATA__ JSON → CSS selectors → generic anchor scan."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # 1) __NEXT_DATA__ JSON (Next.js SSR)
        jobs = self._parse_next_data(soup, base_url=base_url)
        if jobs:
            return jobs

        # 2) Primary CSS selectors
        for selector in PRIMARY_SELECTORS:
            anchors = soup.select(selector)
            if anchors:
                jobs = self._records_from_anchors(anchors, base_url=base_url)
                if jobs:
                    self.logger.info("linkareer: CSS selector %r got %d jobs", selector, len(jobs))
                    return jobs

        # 3) Fallback href pattern
        fallback_anchors = soup.select(FALLBACK_ANCHOR_SELECTOR)
        if fallback_anchors:
            jobs = self._records_from_anchors(fallback_anchors, base_url=base_url)
            if jobs:
                return jobs

        # 4) Last resort generic scan
        return self._records_from_generic_scan(soup, base_url=base_url)

    def _parse_next_data(self, soup: BeautifulSoup, *, base_url: str) -> list[JobRecord]:
        """Extract jobs from Next.js __NEXT_DATA__ JSON blob."""
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script is None or not script.string:
            return []
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.debug("linkareer: __NEXT_DATA__ parse failed: %s", exc)
            return []

        page_props = data.get("props", {}).get("pageProps", {})
        jobs: list[JobRecord] = []
        now = datetime.now()

        # 다양한 데이터 키를 시도 (API 응답 구조가 바뀔 수 있음)
        for candidates_key in (
            "activities", "internships", "recruits", "jobs",
            "activityList", "internList", "recruitList", "jobList",
            "data", "list", "items",
        ):
            items = page_props.get(candidates_key)
            if isinstance(items, list) and items:
                for item in items:
                    record = self._next_item_to_record(item, base_url=base_url, now=now)
                    if record:
                        jobs.append(record)
                if jobs:
                    self.logger.info(
                        "linkareer: __NEXT_DATA__[%r] → %d jobs", candidates_key, len(jobs)
                    )
                    return jobs

        # Nested search (e.g. data.activities.list)
        nested = page_props.get("data") or {}
        if isinstance(nested, dict):
            for sub_key in ("activities", "internships", "recruits", "jobs", "list", "items"):
                items = nested.get(sub_key)
                if isinstance(items, list) and items:
                    for item in items:
                        record = self._next_item_to_record(item, base_url=base_url, now=now)
                        if record:
                            jobs.append(record)
                    if jobs:
                        self.logger.info(
                            "linkareer: __NEXT_DATA__[data][%r] → %d jobs", sub_key, len(jobs)
                        )
                        return jobs

        return []

    def _next_item_to_record(
        self, item: Any, *, base_url: str, now: datetime
    ) -> JobRecord | None:
        """Convert a single __NEXT_DATA__ activity/intern item to JobRecord."""
        if not isinstance(item, dict):
            return None

        # Title — 다양한 키 후보
        title = ""
        for k in ("title", "name", "activityTitle", "jobTitle", "subject"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                title = v.strip()
                break
        if not title:
            return None

        # URL
        url = ""
        item_id = item.get("id") or item.get("activityId") or item.get("jobId") or ""
        url_path = item.get("url") or item.get("path") or item.get("href") or ""
        if url_path:
            url = urljoin("https://linkareer.com", url_path)
        elif item_id:
            # 인턴이면 /intern/, 대외활동이면 /activity/
            if "intern" in base_url:
                url = f"https://linkareer.com/intern/{item_id}"
            else:
                url = f"https://linkareer.com/activity/{item_id}"
        if not url:
            return None

        # Org
        org = ""
        for k in ("organizer", "company", "organization", "host", "orgName", "companyName"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                org = v.strip()
                break
            if isinstance(v, dict):
                org = (v.get("name") or v.get("title") or "").strip()
                if org:
                    break
        if not org:
            org = "링커리어"

        # Deadline
        deadline_str = ""
        for k in ("deadline", "endDate", "dueDate", "closingDate", "applyEndDate"):
            v = item.get(k)
            if isinstance(v, str) and v.strip():
                deadline_str = v.strip()
                break
        deadline = deadline_parser(deadline_str) if deadline_str else None

        # Archetype
        archetype = self._infer_archetype(title, url)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title[:200],
                archetype=archetype,
                deadline=deadline,
                description=title[:2000],
                legitimacy_tier=self.default_legitimacy_tier,
                scanned_at=now,
            )
        except Exception as exc:
            self.logger.warning("linkareer: bad __NEXT_DATA__ item %r: %s", title, exc)
            return None

    def _records_from_anchors(self, anchors: list[Tag], *, base_url: str) -> list[JobRecord]:
        """Convert <a> tags to JobRecords. No keyword filter — already on search page."""
        jobs: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            title = (anchor.get_text(" ", strip=True) or "").strip()
            if not title or len(title) < 5 or len(title) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue
            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["li", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else title

            org = self._extract_org(container, title)
            deadline = deadline_parser(body_text) or deadline_parser(title)

            try:
                record = JobRecord(
                    id=self._make_id(url, title),
                    source_url=url,
                    source_channel=self.name,
                    source_tier=self.tier,
                    org=org[:100],
                    title=title[:200],
                    archetype=self._infer_archetype(title, url),
                    deadline=deadline,
                    description=body_text[:2000],
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("linkareer: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)
        return jobs

    def _records_from_generic_scan(self, soup: BeautifulSoup, *, base_url: str) -> list[JobRecord]:
        """Final fallback — scan every anchor for linkareer path patterns."""
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 5 or len(text) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            href_lower = href.lower()
            if not any(pat in href_lower for pat in GENERIC_HREF_PATTERNS):
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["li", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else text

            try:
                results.append(
                    JobRecord(
                        id=self._make_id(url, text),
                        source_url=url,
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=self._extract_org(container, text)[:100],
                        title=text[:200],
                        archetype=self._infer_archetype(text, url),
                        deadline=deadline_parser(body_text),
                        description=body_text[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("linkareer: bad generic card %r: %s", text, exc)
                continue
        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Try __NEXT_DATA__ first
        script = soup.find("script", {"id": "__NEXT_DATA__"})
        if script and script.string:
            try:
                data = json.loads(script.string)
                page_props = data.get("props", {}).get("pageProps", {})
                activity = (
                    page_props.get("activity")
                    or page_props.get("intern")
                    or page_props.get("recruit")
                    or page_props.get("job")
                    or page_props.get("data")
                    or {}
                )
                if isinstance(activity, dict) and activity:
                    now = datetime.now()
                    record = self._next_item_to_record(activity, base_url=url, now=now)
                    if record:
                        return record
            except Exception:
                pass

        # HTML fallback
        title = ""
        for selector in (
            "h1.title", "h1.header-title", "h2.title",
            "div.detail-header h1", "h1", "h2",
        ):
            node = soup.select_one(selector)
            if node:
                title = node.get_text(" ", strip=True)
                if title:
                    break
        if not title:
            title = (soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1]) or "링커리어 공고"
        title = title[:200]

        body_text = soup.get_text(" ", strip=True)[:5000]
        org = ""
        for selector in (".company-name", ".org-name", ".company a", "span.company"):
            node = soup.select_one(selector)
            if node:
                org = node.get_text(" ", strip=True)
                if org:
                    break
        if not org:
            org = "링커리어 게시물"

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title,
                archetype=self._infer_archetype(title, url),
                deadline=deadline_parser(body_text) or deadline_parser(title),
                description=body_text,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("linkareer: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny extractors ----------------------------------------------------

    @staticmethod
    def _extract_org(container: Tag | None, title: str) -> str:
        if container is not None:
            for selector in (".company-name", ".org-name", ".name", "span.company"):
                node = container.select_one(selector)
                if node:
                    text = node.get_text(" ", strip=True)
                    if text:
                        return text[:100]
        for sep in ("|", "\u00b7", "\u318d", "-"):
            if sep in title:
                hint = title.split(sep, 1)[0].strip()
                if hint and len(hint) >= 2:
                    return hint[:100]
        return "링커리어 게시물"

    @staticmethod
    def _infer_archetype(title: str, url: str = "") -> str | None:
        title_lower = title.lower() if title else ""
        url_lower = url.lower() if url else ""
        if "인턴" in title_lower or "intern" in title_lower or "/intern/" in url_lower:
            return "INTERN"
        if "대외활동" in title_lower or "activity" in title_lower or "/activity/" in url_lower:
            return "ACTIVITY"
        if "공모전" in title_lower or "competition" in title_lower or "/competition/" in url_lower:
            return "COMPETITION"
        return None
