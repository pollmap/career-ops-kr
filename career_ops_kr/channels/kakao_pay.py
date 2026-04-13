"""KakaoPay (카카오페이) recruitment channel.

Source: https://kakaopay.com/careers

Tier: 3 (company direct — fintech). Legitimacy: T1 (official corporate
career page). 카카오페이는 국내 최대 핀테크 기업 중 하나로 결제·금융·
데이터·블록체인 영역 직채용 사이트를 운영한다.

Backend
-------
``requests`` + BeautifulSoup. 카카오페이 커리어 페이지는 현대적 SPA
구조이므로 1차 HTML에서 링크가 없을 때를 대비해 3단계 fallback 선택자를
제공한다.

Fallback 선택자 (3단계):
    1. ``div.job-card a``, ``ul.jobs-list li a``, ``div[class*='job'] a``,
       ``article a[href*='/careers/jobs/']``
    2. ``a[href*='/careers/jobs/']`` 또는 ``a[href*='/jobs/']``
    3. Generic — anchor text가 채용/모집/공고/인턴/개발/데이터/finance/
       engineer 포함

실패 시 빈 리스트를 반환하고 절대 목업 데이터를 만들지 않는다
(career-ops-kr 실데이터 원칙).
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://kakaopay.career.greetinghr.com/"
LIST_URL = "https://kakaopay.career.greetinghr.com/"
ORG = "카카오페이"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 career-ops-kr/0.2"
)

FINTECH_KEYWORDS = (
    "핀테크",
    "결제",
    "페이",
    "금융",
    "데이터",
    "AI",
    "블록체인",
    "디지털",
    "리스크",
    "컴플라이언스",
)

# Archetype inference keywords (lowercase for matching)
_INTERN_KEYS = ("인턴", "intern")
_DATA_KEYS = ("데이터", "data")
_ENGINEER_KEYS = ("개발", "engineer", "dev")
_RESEARCH_KEYS = ("리서치", "research", "분석")

# Generic anchor text patterns for tier-3 fallback
_GENERIC_ANCHOR_PATTERNS = re.compile(
    r"채용|모집|공고|인턴|개발|데이터|finance|engineer",
    re.IGNORECASE,
)

# Request timeouts
REQUEST_TIMEOUT = 20
CHECK_TIMEOUT = 10

# Field length caps
MAX_TITLE = 200
MAX_DESCRIPTION = 5_000


class KakaoPayChannel(BaseChannel):
    """카카오페이 직채용 크롤러.

    ``list_jobs`` 의 ``query`` dict 는 다음 키를 인식한다:
        * ``keyword`` (str): 키워드 필터 — ``FINTECH_KEYWORDS`` 포함 여부
          기준. 미지정 시 필터 없음.

    Listing 전략:
        1. ``LIST_URL`` 먼저 요청
        2. 빈 결과면 ``LANDING_URL`` 로 재시도
        3. query에 keyword가 있으면 ``FINTECH_KEYWORDS`` 로 필터링
    """

    name = "kakao_pay"
    tier = 3
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, rate_per_minute: int | None = None) -> None:
        super().__init__(rate_per_minute=rate_per_minute)
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
            }
        )

    # -- public API -----------------------------------------------------------

    def check(self) -> bool:
        """랜딩 페이지 reachability 확인."""
        try:
            resp = self._session.get(LANDING_URL, timeout=CHECK_TIMEOUT)
            return resp.status_code == 200
        except requests.RequestException as exc:
            self.logger.debug("kakao_pay check failed: %s", exc)
            return False

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """카카오페이 채용 목록 수집.

        Args:
            query: Optional filter dict — ``keyword`` 키 인식.

        Returns:
            수집된 ``JobRecord`` 리스트. URL 기준 중복 제거. 실패 시 ``[]``.
        """
        query = query or {}
        keyword = str(query.get("keyword") or "").strip()

        # Step 1: try LIST_URL
        records = self._fetch_and_parse(LIST_URL)

        # Step 2: fallback to LANDING_URL if empty
        if not records:
            self.logger.info("kakao_pay: LIST_URL empty — trying LANDING_URL")
            records = self._fetch_and_parse(LANDING_URL)

        if not records:
            return []

        # Step 3: keyword filter (fintech keywords)
        if keyword:
            filtered = [r for r in records if self._matches_fintech(r.title)]
            records = filtered if filtered else records

        # Dedup by id
        seen: set[str] = set()
        deduped: list[JobRecord] = []
        for rec in records:
            if rec.id in seen:
                continue
            seen.add(rec.id)
            deduped.append(rec)

        return deduped

    def get_detail(self, url: str) -> JobRecord | None:
        """단일 공고 상세 페이지 파싱.

        Args:
            url: 카카오페이 채용공고 URL.

        Returns:
            ``JobRecord`` 또는 실패 시 ``None``.
        """
        if not url:
            return None

        html = self._fetch_page(url)
        if html is None:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("kakao_pay: get_detail parse failed: %s", exc)
            return None

        title = self._extract_detail_title(soup, fallback_url=url)
        description = self._extract_detail_description(soup)
        deadline_text = self._extract_detail_deadline(soup)
        deadline = deadline_parser(deadline_text) if deadline_text else None
        archetype = _infer_archetype(title)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=ORG,
                title=title[:MAX_TITLE],
                archetype=archetype,
                deadline=deadline,
                description=description[:MAX_DESCRIPTION],
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("kakao_pay: detail record build failed: %s", exc)
            return None

    # -- fetch ----------------------------------------------------------------

    def _fetch_page(self, url: str) -> str | None:
        """``requests.get`` with retry + rate limiting. Returns HTML or None."""
        try:
            resp = self._retry(
                requests.get,
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
        except Exception as exc:
            self.logger.warning("kakao_pay: fetch %s: %s", url, exc)
            return None

        if resp is None:
            return None
        if resp.status_code != 200:
            self.logger.warning("kakao_pay: fetch %s: HTTP %s", url, resp.status_code)
            return None
        if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
            resp.encoding = "utf-8"
        return resp.text

    def _fetch_and_parse(self, url: str) -> list[JobRecord]:
        """Fetch a listing URL and parse job records from it."""
        html = self._fetch_page(url)
        if not html:
            return []
        try:
            return self._parse_list(html, base_url=url)
        except Exception as exc:
            self.logger.warning("kakao_pay: parse failed for %s: %s", url, exc)
            return []

    # -- list parsing ---------------------------------------------------------

    def _parse_list(self, html: str, *, base_url: str) -> list[JobRecord]:
        """3단계 fallback 선택자로 채용공고 링크를 수집한다."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        anchors = self._collect_anchors(soup)
        if not anchors:
            return []
        return self._build_records_from_anchors(anchors, soup, base_url=base_url)

    def _collect_anchors(self, soup: BeautifulSoup) -> list[Tag]:
        """3단계 fallback 선택자 전략으로 채용 anchor를 수집한다."""
        # Tier 1: specific job-card selectors
        candidates: list[Tag] = []
        for sel in (
            "div.job-card a",
            "ul.jobs-list li a",
            "div[class*='job'] a",
            "article a[href*='/careers/jobs/']",
        ):
            found = soup.select(sel)
            candidates.extend(t for t in found if isinstance(t, Tag))
        if candidates:
            return _dedup_anchors(candidates)

        # Tier 2: href pattern matching
        for pattern in ("/careers/jobs/", "/jobs/"):
            found = soup.find_all("a", href=lambda h, p=pattern: isinstance(h, str) and p in h)
            if found:
                return _dedup_anchors([t for t in found if isinstance(t, Tag)])

        # Tier 3: generic anchor text matching
        generic: list[Tag] = []
        for anchor in soup.find_all("a"):
            if not isinstance(anchor, Tag):
                continue
            text = anchor.get_text(" ", strip=True)
            if _GENERIC_ANCHOR_PATTERNS.search(text):
                generic.append(anchor)
        return _dedup_anchors(generic)

    def _build_records_from_anchors(
        self,
        anchors: list[Tag],
        soup: BeautifulSoup,
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """Anchor 태그 목록에서 JobRecord 리스트를 만든다."""
        results: list[JobRecord] = []
        seen_urls: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            title = (anchor.get_text(" ", strip=True) or "").strip()
            if not title or len(title) < 2:
                # Try aria-label or title attribute
                title = str(anchor.get("aria-label") or anchor.get("title") or "").strip()
            if not title:
                continue

            url = urljoin(base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            container = anchor.find_parent(["li", "tr", "div", "article", "section"])
            body_text = container.get_text(" ", strip=True) if container else title
            deadline = deadline_parser(body_text)
            archetype = _infer_archetype(title)

            try:
                results.append(
                    JobRecord(
                        id=self._make_id(url, title),
                        source_url=url,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=ORG,
                        title=title[:MAX_TITLE],
                        archetype=archetype,
                        deadline=deadline,
                        description=body_text[:MAX_DESCRIPTION],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("kakao_pay: skip invalid anchor %r: %s", title, exc)
                continue

        return results

    # -- detail field extractors ----------------------------------------------

    @staticmethod
    def _extract_detail_title(soup: BeautifulSoup, *, fallback_url: str) -> str:
        for sel in (
            "h1",
            "h2",
            "div.job-title",
            "div[class*='title']",
            "title",
        ):
            found = soup.select_one(sel)
            if found is None:
                continue
            text = found.get_text(" ", strip=True)
            if text:
                return text
        return fallback_url.rsplit("/", 1)[-1] or "카카오페이 공고"

    @staticmethod
    def _extract_detail_description(soup: BeautifulSoup) -> str:
        for sel in (
            "div.job-description",
            "div[class*='description']",
            "div[class*='content']",
        ):
            found = soup.select_one(sel)
            if found is None:
                continue
            text = found.get_text(" ", strip=True)
            if text:
                return text
        return soup.get_text(" ", strip=True)

    @staticmethod
    def _extract_detail_deadline(soup: BeautifulSoup) -> str:
        # Search all text nodes for deadline patterns
        deadline_re = re.compile(
            r"마감|deadline|~\s*\d{4}[-./]\d{1,2}[-./]\d{1,2}",
            re.IGNORECASE,
        )
        for elem in soup.find_all(string=deadline_re):
            text = elem.strip()
            if text:
                return text
        return ""

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _matches_fintech(title: str) -> bool:
        """제목이 FINTECH_KEYWORDS 중 하나를 포함하면 True."""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in FINTECH_KEYWORDS)


# -- module-level helpers -----------------------------------------------------


def _infer_archetype(title: str) -> str:
    """제목 키워드로 archetype을 추론한다.

    Returns:
        "INTERN" | "DATA" | "ENGINEER" | "RESEARCH" | "GENERAL"
    """
    t = title.lower()
    if any(k in t for k in _INTERN_KEYS):
        return "INTERN"
    if any(k in t for k in _DATA_KEYS):
        return "DATA"
    if any(k in t for k in _ENGINEER_KEYS):
        return "ENGINEER"
    if any(k in t for k in _RESEARCH_KEYS):
        return "RESEARCH"
    return "GENERAL"


def _dedup_anchors(anchors: list[Tag]) -> list[Tag]:
    """href 기준으로 anchor 중복을 제거한다 (순서 유지)."""
    seen: set[str] = set()
    result: list[Tag] = []
    for anchor in anchors:
        href = anchor.get("href") or ""
        if isinstance(href, list):
            href = " ".join(href)
        if href and href not in seen:
            seen.add(href)
            result.append(anchor)
    return result


__all__ = [
    "FINTECH_KEYWORDS",
    "LANDING_URL",
    "LIST_URL",
    "ORG",
    "KakaoPayChannel",
]
