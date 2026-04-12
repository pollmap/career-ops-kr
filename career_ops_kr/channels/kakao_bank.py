"""KakaoBank (카카오뱅크) recruitment channel.

Source: https://www.kakaobank.com/careers

Tier: 3 (company direct — fintech/bank). Legitimacy: T1 (official
corporate career page).

카카오뱅크는 국내 1위 인터넷전문은행(2017년 출범, 2021년 코스피 상장).
금융 데이터/AI/리스크/플랫폼 직군 중심으로 채용하며 인턴 프로그램도 운영.
공식 채용 페이지에서 직접 공고를 수집한다.

Backend: ``requests`` + BeautifulSoup.

Selector strategy (3-tier fallback):
    1. ``div.career-list a``, ``ul.recruit-list li a``,
       ``div[class*='career'] a``, ``div[class*='job'] a``
    2. ``a[href*='/careers/jobs/']``, ``a[href*='/careers/detail/']``
    3. Generic anchor-text scan matching FINTECH_KEYWORDS tokens

fetch strategy (list_jobs):
    - Fetch LIST_URL first
    - If 0 records extracted, fall back to LANDING_URL
    - Optional keyword filtering (FINTECH_KEYWORDS)
    - Dedup by record id
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://www.kakaobank.com/careers"
LIST_URL = "https://www.kakaobank.com/careers/jobs"
ORG = "카카오뱅크"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 career-ops-kr/0.2"
)

FINTECH_KEYWORDS: tuple[str, ...] = (
    "금융",
    "데이터",
    "AI",
    "디지털",
    "핀테크",
    "리스크",
    "인턴",
    "신입",
    "분석",
    "기획",
)

# Generic anchor-text tokens used in tier-3 fallback
_GENERIC_TOKENS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "인턴",
    "개발",
    "데이터",
    "analyst",
    "engineer",
)

# Primary CSS selectors (tier-1 fallback list)
_PRIMARY_SELECTORS: tuple[str, ...] = (
    "div.career-list a",
    "ul.recruit-list li a",
    "div[class*='career'] a",
    "div[class*='job'] a",
)

# Tier-2 href-pattern selectors
_HREF_SELECTORS = "a[href*='/careers/jobs/'], a[href*='/careers/detail/']"

REQUEST_TIMEOUT = 20
CHECK_TIMEOUT = 10
MAX_TITLE = 200
MAX_DESCRIPTION = 5_000


class KakaoBankChannel(BaseChannel):
    """카카오뱅크 공식 채용 페이지 크롤러.

    list_jobs ``query`` dict 키:
        * ``keyword`` (str): 키워드 필터. FINTECH_KEYWORDS 와 매칭하여
          미포함 공고를 제거한다. 미지정 시 전체 수집.

    실패 시 빈 리스트/None 반환. 절대 목업 데이터 생성 금지.
    """

    name = "kakao_bank"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        list_url: str = LIST_URL,
        landing_url: str = LANDING_URL,
        rate_per_minute: int | None = None,
    ) -> None:
        super().__init__(rate_per_minute=rate_per_minute)
        self.list_url = list_url
        self.landing_url = landing_url
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;"
                    "q=0.9,image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
            }
        )

    # -- public API -----------------------------------------------------------

    def check(self) -> bool:
        """랜딩 페이지 reachability 확인."""
        for url in (self.landing_url, self.list_url):
            try:
                resp = self._session.get(url, timeout=CHECK_TIMEOUT)
            except requests.RequestException as exc:
                self.logger.debug("kakao_bank check %s: %s", url, exc)
                continue
            if resp.status_code == 200:
                return True
        return False

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """LIST_URL 우선 수집, 공고 0건이면 LANDING_URL 폴백.

        Args:
            query: Optional dict. ``keyword`` 키 존재 시 FINTECH_KEYWORDS
                필터 적용.

        Returns:
            중복 제거된 ``JobRecord`` 리스트. 실패 시 ``[]``.
        """
        query = query or {}
        keyword = str(query.get("keyword") or "").strip().lower()

        # Step 1: fetch LIST_URL
        jobs = self._fetch_and_parse(self.list_url)

        # Step 2: fallback to LANDING_URL if nothing found
        if not jobs:
            self.logger.info("kakao_bank: LIST_URL empty — falling back to LANDING_URL")
            jobs = self._fetch_and_parse(self.landing_url)

        if not jobs:
            self.logger.warning("kakao_bank: no jobs extracted from either URL")
            return []

        # Step 3: keyword filter (optional)
        if keyword:
            jobs = self._apply_keyword_filter(jobs, keyword)

        # Step 4: dedup by id
        return self._dedup(jobs)

    def get_detail(self, url: str) -> JobRecord | None:
        """단일 공고 상세 페이지 파싱.

        Returns:
            ``JobRecord`` or ``None`` on any failure.
        """
        if not url:
            return None
        html = self._fetch_page(url)
        if html is None:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("kakao_bank get_detail parse failed: %s", exc)
            return None

        title = self._extract_detail_title(soup, fallback_url=url)
        description = self._extract_detail_description(soup)
        body = soup.get_text(" ", strip=True)
        deadline = deadline_parser(self._extract_deadline_text(soup)) or deadline_parser(body)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=ORG,
                title=title[:MAX_TITLE],
                deadline=deadline,
                description=description[:MAX_DESCRIPTION],
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("kakao_bank: detail record build failed: %s", exc)
            return None

    # -- internal fetch + parse -----------------------------------------------

    def _fetch_and_parse(self, url: str) -> list[JobRecord]:
        """Fetch ``url`` and parse job links. Returns ``[]`` on any error."""
        html = self._fetch_page(url)
        if html is None:
            return []
        try:
            return self._parse_list(html, base_url=url)
        except Exception as exc:
            self.logger.warning("kakao_bank: parse failed for %s: %s", url, exc)
            return []

    def _fetch_page(self, url: str) -> str | None:
        """``_retry`` wrapper. Returns HTML text or ``None``."""

        def _do_fetch() -> requests.Response:
            return self._session.get(url, timeout=REQUEST_TIMEOUT)

        try:
            resp = self._retry(_do_fetch)
        except Exception as exc:
            self.logger.warning("kakao_bank fetch %s: %s", url, exc)
            return None
        if resp is None:
            return None
        if resp.status_code != 200:
            self.logger.warning("kakao_bank fetch %s: HTTP %s", url, resp.status_code)
            return None
        if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
            resp.encoding = "utf-8"
        return resp.text

    # -- list parsing ---------------------------------------------------------

    def _parse_list(self, html: str, *, base_url: str) -> list[JobRecord]:
        """3-tier selector fallback → list of JobRecord."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # Tier 1: primary CSS selectors
        anchors = self._collect_anchors_primary(soup)
        if not anchors:
            # Tier 2: href-pattern selectors
            anchors = list(soup.select(_HREF_SELECTORS))
        if not anchors:
            # Tier 3: generic anchor-text scan
            anchors = self._collect_anchors_generic(soup)

        return self._build_records(anchors, base_url=base_url)

    def _collect_anchors_primary(self, soup: BeautifulSoup) -> list[Tag]:
        for selector in _PRIMARY_SELECTORS:
            found = soup.select(selector)
            if found:
                return [t for t in found if isinstance(t, Tag)]
        return []

    def _collect_anchors_generic(self, soup: BeautifulSoup) -> list[Tag]:
        """Anchor-text matching _GENERIC_TOKENS."""
        results: list[Tag] = []
        for anchor in soup.find_all("a"):
            if not isinstance(anchor, Tag):
                continue
            text = anchor.get_text(" ", strip=True).lower()
            if any(tok in text for tok in _GENERIC_TOKENS):
                href = anchor.get("href") or ""
                if isinstance(href, str) and href and not href.startswith("#"):
                    results.append(anchor)
        return results

    def _build_records(
        self,
        anchors: list[Tag],
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Turn anchor tags into JobRecords; skip invalid entries."""
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#"):
                continue

            url = urljoin(base_url, href)
            title = (anchor.get_text(" ", strip=True) or "").strip()
            if not title:
                # Try parent container for text
                parent = anchor.find_parent(["li", "div", "article"])
                if parent:
                    title = (parent.get_text(" ", strip=True) or "").strip()
            if not title:
                continue

            rec_id = self._make_id(url, title)
            if rec_id in seen:
                continue
            seen.add(rec_id)

            container = anchor.find_parent(["li", "div", "article", "section"])
            body = container.get_text(" ", strip=True) if container else title
            deadline = deadline_parser(body)
            archetype = _infer_archetype(title)

            try:
                results.append(
                    JobRecord(
                        id=rec_id,
                        source_url=url,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=ORG,
                        title=title[:MAX_TITLE],
                        archetype=archetype,
                        deadline=deadline,
                        description=body[:MAX_DESCRIPTION],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("kakao_bank: skip invalid anchor %r: %s", title, exc)
        return results

    # -- filtering + dedup ----------------------------------------------------

    @staticmethod
    def _apply_keyword_filter(
        jobs: list[JobRecord],
        keyword: str,
    ) -> list[JobRecord]:
        """Keep records whose title/description matches FINTECH_KEYWORDS."""
        kw_lower = keyword.lower()
        filtered = []
        for job in jobs:
            combined = (job.title + " " + job.description).lower()
            if kw_lower in combined or any(tok in combined for tok in FINTECH_KEYWORDS):
                filtered.append(job)
        return filtered

    @staticmethod
    def _dedup(jobs: list[JobRecord]) -> list[JobRecord]:
        """Dedup by record id, preserving first occurrence."""
        seen: set[str] = set()
        out: list[JobRecord] = []
        for job in jobs:
            if job.id not in seen:
                seen.add(job.id)
                out.append(job)
        return out

    # -- detail field extractors ----------------------------------------------

    @staticmethod
    def _extract_detail_title(soup: BeautifulSoup, *, fallback_url: str) -> str:
        for sel in (
            "h1",
            "h2",
            "div.job-title",
            "div[class*='title']",
        ):
            found = soup.select_one(sel)
            if found and isinstance(found, Tag):
                text = found.get_text(" ", strip=True)
                if text:
                    return text
        # Final fallback: <title> tag
        title_tag = soup.find("title")
        if title_tag:
            text = title_tag.get_text(" ", strip=True)
            if text:
                return text
        return fallback_url.rsplit("/", 1)[-1] or "카카오뱅크 공고"

    @staticmethod
    def _extract_detail_description(soup: BeautifulSoup) -> str:
        for sel in ("div[class*='content']", "div[class*='description']"):
            found = soup.select_one(sel)
            if found and isinstance(found, Tag):
                text = found.get_text(" ", strip=True)
                if len(text) >= 100:
                    return text
        # Generic: first <div> with 100+ chars
        for div in soup.find_all("div"):
            if not isinstance(div, Tag):
                continue
            text = div.get_text(" ", strip=True)
            if len(text) >= 100:
                return text
        return soup.get_text(" ", strip=True)

    @staticmethod
    def _extract_deadline_text(soup: BeautifulSoup) -> str:
        """Extract text likely to contain a deadline."""
        deadline_keywords = ("마감", "접수", "~")
        for tag in soup.find_all(["span", "p", "div", "td", "li"]):
            if not isinstance(tag, Tag):
                continue
            text = tag.get_text(" ", strip=True)
            if any(kw in text for kw in deadline_keywords):
                return text
        return ""


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _infer_archetype(title: str) -> str:
    """Infer archetype from job title text.

    Rules (in priority order):
        인턴/intern → INTERN
        데이터/data/분석 → DATA
        개발/engineer/dev → ENGINEER
        리스크/컴플라이언스/준법 → RISK_COMPLIANCE
        else → GENERAL
    """
    t = title.lower()
    if "인턴" in t or "intern" in t:
        return "INTERN"
    if "데이터" in t or "data" in t or "분석" in t:
        return "DATA"
    if "개발" in t or "engineer" in t or "dev" in t:
        return "ENGINEER"
    if "리스크" in t or "컴플라이언스" in t or "준법" in t:
        return "RISK_COMPLIANCE"
    return "GENERAL"


__all__ = [
    "FINTECH_KEYWORDS",
    "LANDING_URL",
    "LIST_URL",
    "ORG",
    "KakaoBankChannel",
    "_infer_archetype",
]
