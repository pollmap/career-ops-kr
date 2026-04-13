"""Incruit channel — 인쿠르트 (job.incruit.com).

Backend: ``requests`` + BS4. Incruit 는 대표적인 국내 상업 채용 포털로,
상시 3만+ 건의 일반 공고를 운영한다. 본 채널은 **전수 수집 원칙**에
따라 리스트 페이지를 페이지네이션으로 크롤해 가능한 모든 공고를
긁어온다. 필터링/랭킹은 downstream scorer 가 담당.

URL 구조:
    - 리스트:   ``https://job.incruit.com/jobdb_list/searchjob.asp``
      * ``?cd=<category>`` 카테고리 코드 (선택)
      * ``&page=<n>``      페이지 번호 (1-indexed)
    - 상세:     ``https://job.incruit.com/jobdb_info/jobpost.asp?job=<id>``

Defensive selector strategy:
    1. primary  — ``div.jobListDefault`` / ``ul.c_row`` / ``.l_job`` /
                  ``.c_tit`` 등 흔히 쓰이는 리스트 wrapper 탐색
    2. fallback — career keyword 를 포함한 ``<a href>`` 를 전수 스캔
                  (jobalio.py HTML fallback 과 동일한 방어적 패턴)

실패 시 빈 리스트를 반환한다 (실데이터 원칙 — 목업/추정 금지).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOMAIN = "https://www.incruit.com/"
LIST_URL = "https://job.incruit.com/jobdb_list/searchjob.asp"
DETAIL_PREFIX = "https://job.incruit.com/jobdb_info/jobpost.asp"

from career_ops_kr._constants import DEFAULT_USER_AGENT as _APP_UA  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    f"{_APP_UA}"
)

DEFAULT_PAGES = 3
MAX_PAGES = 50

# 리스트 페이지에서 공고 링크를 잡아낼 때 쓰는 셀렉터 — primary path 실패
# 시 anchor fallback 으로 넘어간다. 인쿠르트는 CSS 클래스를 자주
# 바꾸므로 후보를 넉넉히 둔다.
_LIST_SELECTORS: tuple[str, ...] = (
    "div.jobListDefault a[href*='jobpost.asp']",
    "ul.c_row a[href*='jobpost.asp']",
    "div.l_job a[href*='jobpost.asp']",
    "td.tit a[href*='jobpost.asp']",
    "a.accent[href*='jobpost.asp']",
    "a.c_tit[href*='jobpost.asp']",
    "a[href*='jobdb_info/jobpost.asp']",
)

# 공고로 보이는 anchor 를 식별하기 위한 키워드 (anchor fallback 용).
_CAREER_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "신입",
    "경력",
    "인턴",
    "개발",
    "데이터",
    "금융",
    "리서치",
    "분석",
    "기획",
    "마케팅",
    "디자인",
    "운영",
    "영업",
    "엔지니어",
    "engineer",
    "developer",
    "recruit",
    "career",
)

# 리스트 카드 내부에서 기업명을 찾아낼 때 쓰는 셀렉터 후보.
_ORG_LIST_SELECTORS: tuple[str, ...] = (
    "a.company",
    "a.cn",
    "span.company",
    "span.cn",
    "div.company",
    "td.cn",
    ".cName",
    ".compName",
)

# 상세 페이지 제목 / 기업명 탐색 셀렉터.
_DETAIL_TITLE_SELECTORS: tuple[str, ...] = (
    "h1.jobTit",
    "h1.c_tit",
    "div.jobTit",
    "h2.tit",
    "h1",
    "title",
)
_DETAIL_ORG_SELECTORS: tuple[str, ...] = (
    "a.company",
    "div.company",
    "span.company",
    "div.cName",
    "a.cName",
    "h2.company",
)

# 한국 17개 시/도 — location 추출에 쓰이는 간단 키워드 매칭.
_KR_REGIONS: tuple[str, ...] = (
    "서울",
    "경기",
    "인천",
    "부산",
    "대구",
    "광주",
    "대전",
    "울산",
    "세종",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
)


# ---------------------------------------------------------------------------
# Channel implementation
# ---------------------------------------------------------------------------


class IncruitChannel(BaseChannel):
    """인쿠르트(Incruit) 메이저 채용 포털 스크레이퍼.

    전수 수집 원칙: 리스트 페이지 ``N`` 페이지 (``query['pages']``) 를
    순차 크롤해 가능한 모든 공고를 긁어온다. 제한/필터링은 downstream
    scorer 가 처리하며, 본 채널은 **최대한 많이** 모으는 것이 목표다.
    """

    name = "incruit"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 10
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        list_url: str = LIST_URL,
        domain: str = DOMAIN,
    ) -> None:
        super().__init__()
        self.list_url = list_url
        self.domain = domain

    # -- public API ---------------------------------------------------------

    def check(self) -> bool:
        """Upstream reachability probe — 리스트/도메인 둘 중 하나라도 200 이면 OK."""
        for url in (self.list_url, self.domain):
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
            except requests.RequestException as exc:
                self.logger.debug("incruit check %s: %s", url, exc)
                continue
            if resp.status_code == 200:
                return True
        return False

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """리스트 페이지를 ``pages`` 만큼 크롤해 모든 공고를 반환.

        Args:
            query: Optional filter dict. Recognised keys:
                - ``keyword``: 제목/본문에 해당 문자열이 포함된 공고만.
                - ``pages``:   크롤할 페이지 수 (기본 :data:`DEFAULT_PAGES`,
                               상한 :data:`MAX_PAGES`).
                - ``category``: ``cd`` 쿼리파라미터로 붙일 카테고리 코드.
        """
        q = query or {}
        pages = self._normalise_pages(q.get("pages"))
        category = q.get("category")
        keyword = (q.get("keyword") or "").strip() or None

        aggregated: list[JobRecord] = []
        seen_urls: set[str] = set()

        for page_idx in range(1, pages + 1):
            page_url = self._build_list_url(page=page_idx, category=category)
            resp = self._retry(self._fetch, page_url)
            if resp is None or resp.status_code != 200:
                self.logger.warning(
                    "incruit: page %d fetch failed (status=%s)",
                    page_idx,
                    getattr(resp, "status_code", "n/a"),
                )
                continue
            page_jobs = self._parse_list_html(
                resp.text,
                base_url=page_url,
                keyword=keyword,
            )
            new_count = 0
            for job in page_jobs:
                url_str = str(job.source_url)
                if url_str in seen_urls:
                    continue
                seen_urls.add(url_str)
                aggregated.append(job)
                new_count += 1
            self.logger.info(
                "incruit: page %d — %d parsed, %d new (total=%d)",
                page_idx,
                len(page_jobs),
                new_count,
                len(aggregated),
            )
            # 연속으로 새 공고가 0건이면 조기 종료 (중복 루프 방지).
            if new_count == 0 and page_idx >= 2:
                self.logger.info(
                    "incruit: page %d returned no new jobs — stopping pagination",
                    page_idx,
                )
                break

        return aggregated

    def get_detail(self, url: str) -> JobRecord | None:
        """상세 페이지 파싱 — 제목/본문/마감일/요건 추출."""
        if not url:
            return None
        resp = self._retry(self._fetch, url)
        if resp is None or resp.status_code != 200:
            self.logger.warning(
                "incruit get_detail failed: status=%s url=%s",
                getattr(resp, "status_code", "n/a"),
                url,
            )
            return None
        return self._parse_detail_html(resp.text, url=url)

    # -- internals: fetching ------------------------------------------------

    def _fetch(self, url: str) -> requests.Response:
        self.logger.info("incruit: GET %s", url)
        return requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5",
            },
            timeout=15,
        )

    def _build_list_url(self, *, page: int, category: str | None) -> str:
        params: list[str] = []
        if category:
            params.append(f"cd={category}")
        params.append(f"page={page}")
        query = "&".join(params)
        sep = "&" if "?" in self.list_url else "?"
        return f"{self.list_url}{sep}{query}"

    @staticmethod
    def _normalise_pages(raw: Any) -> int:
        if raw is None:
            return DEFAULT_PAGES
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_PAGES
        if value < 1:
            return 1
        if value > MAX_PAGES:
            return MAX_PAGES
        return value

    # -- internals: parsing -------------------------------------------------

    def _parse_list_html(
        self,
        html: str,
        *,
        base_url: str,
        keyword: str | None,
    ) -> list[JobRecord]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # Primary path — try channel-specific selectors first.
        anchors = self._collect_primary_anchors(soup)
        if not anchors:
            self.logger.info("incruit: primary selectors empty — falling back to anchor scan")
            anchors = self._collect_fallback_anchors(soup)

        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in anchors:
            record = self._anchor_to_record(
                anchor,
                base_url=base_url,
                keyword=keyword,
                seen=seen,
                now=now,
            )
            if record is not None:
                results.append(record)
        return results

    def _collect_primary_anchors(self, soup: BeautifulSoup) -> list[Tag]:
        anchors: list[Tag] = []
        seen_ids: set[int] = set()
        for selector in _LIST_SELECTORS:
            try:
                found = soup.select(selector)
            except Exception as exc:  # pragma: no cover - bs4 selector edge
                self.logger.debug("incruit: selector %r raised %s", selector, exc)
                continue
            for tag in found:
                if not isinstance(tag, Tag):
                    continue
                key = id(tag)
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                anchors.append(tag)
        return anchors

    def _collect_fallback_anchors(self, soup: BeautifulSoup) -> list[Tag]:
        anchors: list[Tag] = []
        for tag in soup.find_all("a"):
            if not isinstance(tag, Tag):
                continue
            href_raw = tag.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue
            text = (tag.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 4 or len(text) > 300:
                continue
            blob = f"{text} {href}".lower()
            if not any(kw.lower() in blob for kw in _CAREER_KEYWORDS):
                continue
            anchors.append(tag)
        return anchors

    def _anchor_to_record(
        self,
        anchor: Tag,
        *,
        base_url: str,
        keyword: str | None,
        seen: set[str],
        now: datetime,
    ) -> JobRecord | None:
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            return None

        url = urljoin(base_url, href)
        # 외부 도메인 anchor 는 제외 — 인쿠르트 내부 링크만 수집.
        host = urlparse(url).netloc.lower()
        if host and "incruit.com" not in host:
            return None
        if url in seen:
            return None

        title = (anchor.get_text(" ", strip=True) or "").strip()
        if not title:
            return None
        if len(title) < 4 or len(title) > 300:
            return None

        container = anchor.find_parent(["li", "tr", "div", "article", "section"])
        body_text = container.get_text(" ", strip=True) if isinstance(container, Tag) else title

        if keyword and keyword not in title and keyword not in body_text:
            return None

        org = self._extract_org(container, fallback="인쿠르트 게시기업")
        location = self._extract_location(body_text)
        deadline = deadline_parser(body_text) or deadline_parser(title)

        try:
            record = JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org,
                title=title[:200],
                archetype="INTERN" if "인턴" in title else None,
                deadline=deadline,
                location=location,
                description=body_text[:4000],
                legitimacy_tier=self.default_legitimacy_tier,
                scanned_at=now,
            )
        except Exception as exc:
            self.logger.warning("incruit: bad list row %r: %s", title, exc)
            return None

        seen.add(url)
        return record

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        if not html:
            return None
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("incruit: detail parse error: %s", exc)
            return None

        title = self._extract_detail_title(soup, fallback=url)
        plain = soup.get_text(" ", strip=True)
        org = self._extract_detail_org(soup, fallback="인쿠르트 게시기업")
        location = self._extract_location(plain)
        deadline = deadline_parser(plain)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org,
                title=title[:200],
                archetype="INTERN" if "인턴" in title else None,
                deadline=deadline,
                location=location,
                description=plain[:4000],
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("incruit: bad detail record: %s", exc)
            return None

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _first_text(scope: Tag | BeautifulSoup | None, selectors: tuple[str, ...]) -> str | None:
        """Return the first non-empty text found by any of ``selectors``."""
        if scope is None:
            return None
        for selector in selectors:
            try:
                node = scope.select_one(selector)
            except Exception:
                continue
            if isinstance(node, Tag):
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return None

    @classmethod
    def _extract_org(cls, container: Tag | None, *, fallback: str) -> str:
        text = cls._first_text(container, _ORG_LIST_SELECTORS)
        return text[:120] if text else fallback

    @classmethod
    def _extract_detail_title(cls, soup: BeautifulSoup, *, fallback: str) -> str:
        text = cls._first_text(soup, _DETAIL_TITLE_SELECTORS)
        if text:
            return text[:200]
        return fallback.rsplit("/", 1)[-1] or "인쿠르트 공고"

    @classmethod
    def _extract_detail_org(cls, soup: BeautifulSoup, *, fallback: str) -> str:
        text = cls._first_text(soup, _DETAIL_ORG_SELECTORS)
        return text[:120] if text else fallback

    @staticmethod
    def _extract_location(text: str) -> str | None:
        if not text:
            return None
        return next((r for r in _KR_REGIONS if r in text), None)
