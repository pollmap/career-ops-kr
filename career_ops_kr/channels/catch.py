"""캐치(Catch) channel — 대학생 취업/인턴 공고 수집기.

Source: https://www.catch.co.kr/

Backend: ``requests`` + BeautifulSoup.

Notes:
    - 캐치는 대학생/신입 대상 채용포털(T1 신뢰도). 공개 리스트 페이지
      ``/NCS/RecruitListingAll`` 과 ``/NCS/RecruitInternList`` 는
      로그인 없이 접근 가능.
    - **전수 수집 원칙**: 필터링은 downstream scorer 에서 처리한다.
      이 채널은 가능한 많은 공고를 수집한다.
    - **절대 가짜 데이터 금지**: fetch 실패 시 빈 리스트 + 로그 warning.
    - 셀렉터는 defensive: primary → fallback (NCS 경로) → generic (KEYWORDS 기반).

Layout references (2026-04 기준):
    - 채용 리스트: ``https://www.catch.co.kr/NCS/RecruitListingAll``
    - 인턴 리스트: ``https://www.catch.co.kr/NCS/RecruitInternList``
    - 상세: ``https://www.catch.co.kr/NCS/RecruitView?RecruitNo=<id>`` 등
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://www.catch.co.kr/"
RECRUIT_URL = "https://www.catch.co.kr/NCS/RecruitCategory"
INTERN_URL = "https://www.catch.co.kr/NCS/RecruitCategory?recruitType=2"
ORG = "캐치"

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

# Primary CSS selectors — known 캐치 list layouts (2026-04 기준).
PRIMARY_SELECTORS: tuple[str, ...] = (
    "ul.list_item li a",
    "div.list_wrap a.list_item_link",
)

# Fallback: href pattern containing /NCS/ path.
FALLBACK_ANCHOR_SELECTOR = "a[href*='/NCS/']"

# Generic keyword scan terms (title text matching).
GENERIC_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "인턴",
    "신입",
    "경력",
)


class CatchChannel(BaseChannel):
    """캐치 채용/인턴 리스팅 수집기 (requests backend).

    공개 페이지 2개(채용 전체 + 인턴)를 순차 fetch → 합산 후 dedup.
    """

    name = "catch"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 8
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        landing_url: str = LANDING_URL,
        recruit_url: str = RECRUIT_URL,
        intern_url: str = INTERN_URL,
    ) -> None:
        super().__init__()
        self.landing_url = landing_url
        self.recruit_url = recruit_url
        self.intern_url = intern_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe -- GET the landing URL."""
        try:
            resp = requests.get(
                self.landing_url,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("catch check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Fetch recruit + intern list pages, parse, dedup, return.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword``: str -- post-fetch keyword filter on title/description.

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch error.
        """
        all_jobs: list[JobRecord] = []
        seen_ids: set[str] = set()

        for listing_url in (self.recruit_url, self.intern_url):
            html = self._fetch_html(listing_url)
            if html is None:
                self.logger.warning("catch: fetch failed for %s -- skipping", listing_url)
                continue

            page_jobs = self._parse_list_html(html, base_url=listing_url)
            new_count = 0
            for job in page_jobs:
                if job.id in seen_ids:
                    continue
                seen_ids.add(job.id)
                all_jobs.append(job)
                new_count += 1
            self.logger.info(
                "catch: %s parsed %d jobs (%d new)",
                listing_url,
                len(page_jobs),
                new_count,
            )

        # Optional post-fetch keyword filter.
        if query and (kw := query.get("keyword")):
            kw_lower = kw.lower()
            all_jobs = [
                j
                for j in all_jobs
                if kw_lower in j.title.lower() or kw_lower in j.description.lower()
            ]

        self.logger.info("catch: total %d unique jobs collected", len(all_jobs))
        return all_jobs

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch + parse a single detail page.

        Returns ``None`` on any failure -- never raises to caller.
        """
        html = self._fetch_html(url)
        if html is None:
            return None
        try:
            return self._parse_detail_html(html, url=url)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.warning("catch get_detail parse failed %s: %s", url, exc)
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
            self.logger.warning("catch: %s returned %s", url, status)
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    # -- Parsing ------------------------------------------------------------

    def _parse_list_html(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Parse a listing page into :class:`JobRecord` s.

        3-tier selector strategy:
            1) Primary: known list CSS selectors.
            2) Fallback: anchors whose href contains /NCS/.
            3) Generic: GENERIC_KEYWORDS-based anchor scan.
        """
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # 1) Primary path -- known list layouts
        for selector in PRIMARY_SELECTORS:
            anchors = soup.select(selector)
            if anchors:
                jobs = self._records_from_anchors(anchors, base_url=base_url)
                if jobs:
                    return jobs

        # 2) Fallback -- anchor href matches NCS path
        fallback_anchors = soup.select(FALLBACK_ANCHOR_SELECTOR)
        if fallback_anchors:
            jobs = self._records_from_anchors(fallback_anchors, base_url=base_url)
            if jobs:
                return jobs

        # 3) Last resort -- generic anchor scan with GENERIC_KEYWORDS
        return self._records_from_generic_scan(soup, base_url=base_url)

    def _records_from_anchors(self, anchors: list[Tag], *, base_url: str) -> list[JobRecord]:
        """Convert a list of ``<a>`` tags into JobRecords."""
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
                    source_url=url,  # type: ignore[arg-type]
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
                self.logger.warning("catch: skip invalid card %r: %s", title, exc)
                continue
            jobs.append(record)
        return jobs

    def _records_from_generic_scan(self, soup: BeautifulSoup, *, base_url: str) -> list[JobRecord]:
        """Final fallback -- scan every anchor and keep GENERIC_KEYWORDS matches."""
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

            blob = (text + " " + href).lower()
            if not any(kw in blob for kw in GENERIC_KEYWORDS):
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
                        source_url=url,  # type: ignore[arg-type]
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
                self.logger.warning("catch: bad generic card %r: %s", text, exc)
                continue
        return results

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")

        # Title candidates
        title = ""
        for selector in (
            "h1.tit",
            "h2.tit",
            "div.tit_area h1",
            "h1",
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
            ) or "캐치 공고"
        title = title[:200]

        # Description from div.content_area or first long <p>
        description = ""
        content_node = soup.select_one("div.content_area")
        if content_node:
            description = content_node.get_text(" ", strip=True)
        if not description:
            for p in soup.find_all("p"):
                p_text = p.get_text(" ", strip=True)
                if len(p_text) >= 30:
                    description = p_text
                    break
        if not description:
            description = soup.get_text(" ", strip=True)[:5000]

        # Deadline from element containing "마감"
        deadline = None
        for node in soup.find_all(string=lambda t: t and "마감" in t):
            parent = node.parent
            if parent:
                deadline = deadline_parser(parent.get_text(" ", strip=True))
                if deadline:
                    break
        if not deadline:
            deadline = deadline_parser(description) or deadline_parser(title)

        # Organization
        org = self._extract_org(soup.body, title)  # type: ignore[arg-type]

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title,
                archetype=self._infer_archetype(title, url),
                deadline=deadline,
                description=description[:5000],
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("catch: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny extractors ----------------------------------------------------

    @staticmethod
    def _extract_org(container: Tag | None, title: str) -> str:
        """Best-effort organization extractor from a container or title."""
        if container is not None:
            for selector in (
                ".company-name",
                ".org-name",
                ".co_name",
                "span.company",
                ".name",
            ):
                node = container.select_one(selector)
                if node:
                    text = node.get_text(" ", strip=True)
                    if text:
                        return text[:100]

        # Fallback: split title by common separators
        for sep in ("|", "\u00b7", "\u318d", "-"):
            if sep in title:
                hint = title.split(sep, 1)[0].strip()
                if hint and len(hint) >= 2:
                    return hint[:100]
        return ORG

    @staticmethod
    def _infer_archetype(title: str, url: str = "") -> str | None:
        """Infer archetype from title keywords or URL path."""
        title_lower = title.lower() if title else ""
        url_lower = url.lower() if url else ""

        if "인턴" in title_lower or "intern" in title_lower or "intern" in url_lower:
            return "INTERN"
        if "대외활동" in title_lower or "activity" in title_lower or "activity" in url_lower:
            return "ACTIVITY"
        if "공모전" in title_lower or "competition" in title_lower or "competition" in url_lower:
            return "COMPETITION"
        return "GENERAL"
