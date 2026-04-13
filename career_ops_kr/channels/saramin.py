"""Saramin (사람인) channel — 한국 최대 민간 채용 포털 (www.saramin.co.kr).

Backend: ``requests`` + BeautifulSoup.

사람인은 한국 최대 민간 채용 포털(100만+ 공고)로 **전수 수집**이 핵심.
Listing 엔드포인트는 공개 페이지네이션(``recruitPage=N``)을 지원하므로
인증 없이 페이지별로 공고를 순회할 수 있다.

전수 수집 철학:
    - 단일 페이지만 긁으면 한 번에 ~40개 카드만 잡힌다. 찬희의 요구는
      "추리지 말고 가능한 모든 공고" — 따라서 ``pages`` 파라미터로 N개
      페이지를 **순차 요청**한다 (기본 5, 최대 20 하드 캡).
    - 페이지 간에는 :meth:`BaseChannel._retry` 에 내장된 rate limiter 가
      ``default_rate_per_minute = 8`` 로 자동 간격을 확보한다 — 별도
      ``time.sleep`` 호출은 rate limiter 가 이미 관리하므로 생략.
    - 페이지 요청이 실패하면 해당 페이지만 건너뛰고 ``fetch_errors`` 에
      기록. 나머지 페이지는 계속 순회해 "전수" 정책을 유지한다.

Saramin은 DOM 구조가 주기적으로 바뀌므로 모든 selector 는 다중 fallback
을 둔다:
    1. ``.item_recruit`` (사람인 표준 카드, 가장 신뢰)
    2. ``div.list_item`` / ``div.list_body``
    3. 일반 anchor 스캔 (``href`` 에 ``rec_idx`` 포함)

실패 시에는 빈 리스트를 반환하고 절대 목업 데이터를 만들지 않는다
(career-ops-kr 실데이터 원칙).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser
from career_ops_kr.sector import infer_sector as _infer_sector

BASE_URL = "https://www.saramin.co.kr/"
LIST_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
LANDING_URL = "https://www.saramin.co.kr/zf_user/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 career-ops-kr/0.2"
)

# 기본/최대 페이지 수 (전수 수집 지향)
DEFAULT_PAGES = 3
MAX_PAGES = 20

# 키워드 미지정 시 사용하는 금융 업종 기본 검색어
DEFAULT_FINANCE_KEYWORDS: tuple[str, ...] = (
    "은행",
    "증권사",
    "보험",
    "자산운용",
    "카드사",
    "캐피탈",
    "저축은행",
    "핀테크",
    "블록체인",
    "디지털자산",
)

# 사람인 직무 카테고리 코드 — 쿼리 단계에서 노이즈 차단
# - 2: 경영·사무·총무·법무 (기획/재무 관련)
# - 3: IT·개발 (핀테크·금융IT)
# 두 카테고리로 제한하면 카지노/화장품/건설 공고는 쿼리에서 제외됨.
DEFAULT_JOB_CATEGORY = "2,3"

# 응답 타임아웃
REQUEST_TIMEOUT = 20
CHECK_TIMEOUT = 10

# Title 길이 cap
MAX_TITLE = 200
MAX_DESCRIPTION = 5000


class SaraminChannel(BaseChannel):
    """사람인 전수 수집 크롤러.

    list_jobs 의 ``query`` dict 는 다음 키를 인식한다:
        * ``keyword`` (str): 검색어. 미지정 시 포털 기본 전체 공고.
        * ``pages`` (int): 수집할 페이지 수. 기본 5, 최대 20.
        * ``category`` (str): 사람인 직무 카테고리 ID
          (``cat_mcls`` 파라미터로 매핑). 예: ``"3"`` = IT·개발.
        * ``location`` (str): 지역 ID (``loc_cd`` 로 매핑).

    ``rate_per_minute`` 는 ``BaseChannel._retry`` 가 소비하는 rate limiter
    에 묶여 있으므로 페이지 간 별도 sleep 은 필요 없다. 8 req/min 은
    사람인 같은 대형 포털에 무례하지 않은 보수적 값이다.
    """

    name = "saramin"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 8
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
        # Session 재사용으로 TCP handshake 절감 (동일 호스트 다수 요청)
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
        self._fetch_errors: list[str] = []

    # -- public API ---------------------------------------------------------

    def check(self) -> bool:
        """랜딩 페이지 reachability 확인."""
        for url in (self.landing_url, BASE_URL):
            try:
                resp = self._session.get(url, timeout=CHECK_TIMEOUT)
            except requests.RequestException as exc:
                self.logger.debug("saramin check %s: %s", url, exc)
                continue
            if resp.status_code == 200:
                return True
        return False

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """N 페이지 순회 수집. 전수 수집 지향.

        Args:
            query: Optional filter dict — ``keyword``/``pages``/``category``/
                ``location`` 키를 인식. 기타 키는 무시.

        Returns:
            수집된 ``JobRecord`` 리스트. URL 기준 중복 제거. 실패 시 ``[]``.
        """
        query = query or {}
        self._fetch_errors = []

        pages = self._resolve_pages(query.get("pages"))
        keyword = str(query.get("keyword") or "").strip()
        # category 미지정 시 금융/IT 기본 카테고리 (쿼리 레벨 필터)
        category = str(query.get("category") or DEFAULT_JOB_CATEGORY).strip()
        location = str(query.get("location") or "").strip()
        # 도메인 필터 기본 ON — 카테고리로 1차 필터링해도 노이즈 남을 수 있음.
        # archetype 매칭되면 sector 무관하게 통과 (BLOCKCHAIN/FINTECH 공고 보호).
        strict = bool(query.get("strict", True))

        _archetype_clf = None
        if strict:
            try:
                from career_ops_kr.archetype.classifier import ArchetypeClassifier
                _archetype_clf = ArchetypeClassifier()
            except Exception:
                _archetype_clf = None

        # 키워드 없으면 금융 업종 기본 검색어 순회
        search_keywords = (keyword,) if keyword else DEFAULT_FINANCE_KEYWORDS

        all_jobs: list[JobRecord] = []
        seen_urls: set[str] = set()

        for kw in search_keywords:
            for page_num in range(1, pages + 1):
                url = self._build_list_url(
                    page=page_num,
                    keyword=kw,
                    category=category,
                    location=location,
                )
                self.logger.info("saramin: [%s] fetching page %d/%d", kw, page_num, pages)

                html = self._fetch_page(url)
                if html is None:
                    self._fetch_errors.append(f"kw={kw} page={page_num}: fetch failed")
                    continue

                try:
                    page_jobs = self._parse_list(html, base_url=url)
                except Exception as exc:
                    self.logger.warning("saramin: parse page %d failed: %s", page_num, exc)
                    self._fetch_errors.append(f"kw={kw} page={page_num}: parse failed: {exc}")
                    continue

                new_count = 0
                skipped_offdomain = 0
                for rec in page_jobs:
                    key = str(rec.source_url)
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                    if strict:
                        sector = _infer_sector(rec.source_channel, rec.org, rec.title)
                        if sector == "기타":
                            # archetype이 매칭되면 도메인 내 — 통과
                            # (예: BLOCKCHAIN 공고는 org/title에 금융 키워드 없어도 유지)
                            keep = False
                            if _archetype_clf is not None:
                                from career_ops_kr.archetype.classifier import Archetype
                                _text = " ".join([
                                    rec.title or "", rec.org or "", rec.description or "",
                                ])
                                _arch, _ = _archetype_clf.classify(_text)
                                keep = _arch is not Archetype.UNKNOWN
                            if not keep:
                                skipped_offdomain += 1
                                continue
                    all_jobs.append(rec)
                    new_count += 1
                if strict and skipped_offdomain:
                    self.logger.info(
                        "saramin: [%s] page %d skipped %d off-domain records",
                        kw, page_num, skipped_offdomain,
                    )

                self.logger.info(
                    "saramin: [%s] page %d yielded %d new records (total=%d)",
                    kw, page_num, new_count, len(all_jobs),
                )

                # 더 이상 새 공고가 없으면 early stop
                if page_num > 1 and new_count == 0:
                    self.logger.info(
                        "saramin: [%s] page %d returned 0 new records — early stop", kw,
                    page_num,
                )
                break

        if not all_jobs:
            self.logger.warning(
                "saramin: no jobs extracted from %d page(s) — errors=%s",
                pages,
                self._fetch_errors,
            )
        return all_jobs

    def get_detail(self, url: str) -> JobRecord | None:
        """단일 공고 상세 페이지 파싱.

        상세 페이지에서 title / company / description / deadline 을 추출.
        실패 시 ``None`` 반환 (절대 raise 하지 않음).
        """
        if not url:
            return None
        html = self._fetch_page(url)
        if html is None:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("saramin get_detail parse failed: %s", exc)
            return None

        title = self._extract_detail_title(soup, fallback_url=url)
        company = self._extract_detail_company(soup)
        body = soup.get_text(" ", strip=True)
        deadline = deadline_parser(body)
        location = self._extract_detail_location(soup)

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=company or "사람인",
                title=title[:MAX_TITLE],
                deadline=deadline,
                location=location,
                description=body[:MAX_DESCRIPTION],
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("saramin: detail record build failed: %s", exc)
            return None

    # -- pagination + URL building -----------------------------------------

    @staticmethod
    def _resolve_pages(raw: Any) -> int:
        """Clamp ``pages`` 파라미터: 1 <= pages <= MAX_PAGES, 기본 DEFAULT_PAGES."""
        if raw is None:
            return DEFAULT_PAGES
        try:
            val = int(raw)
        except (TypeError, ValueError):
            return DEFAULT_PAGES
        if val < 1:
            return 1
        if val > MAX_PAGES:
            return MAX_PAGES
        return val

    def _build_list_url(
        self,
        *,
        page: int,
        keyword: str = "",
        category: str = "",
        location: str = "",
    ) -> str:
        """사람인 검색 URL 조립. 페이지네이션은 ``recruitPage``."""
        params: dict[str, str] = {
            "searchType": "search",
            "recruitPage": str(page),
            "recruitPageCount": "40",  # 페이지당 공고 수
            "recruitSort": "reg_dt",  # 최신순
        }
        if keyword:
            params["searchword"] = keyword
        if category:
            params["cat_mcls"] = category
        if location:
            params["loc_cd"] = location
        return f"{self.list_url}?{urlencode(params, encoding='utf-8')}"

    # -- fetch --------------------------------------------------------------

    def _fetch_page(self, url: str) -> str | None:
        """``_retry`` wrapper around session.get. Returns HTML text or None."""

        def _do_fetch() -> requests.Response:
            return self._session.get(url, timeout=REQUEST_TIMEOUT)

        try:
            resp = self._retry(_do_fetch)
        except Exception as exc:
            self.logger.warning("saramin fetch %s: %s", url, exc)
            return None
        if resp is None:
            return None
        if resp.status_code != 200:
            self.logger.warning("saramin fetch %s: HTTP %s", url, resp.status_code)
            return None
        # 사람인은 기본 UTF-8 이지만 가끔 EUC-KR 헤더를 반환 — 명시적으로 고정.
        if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
            resp.encoding = "utf-8"
        return resp.text

    # -- list parsing -------------------------------------------------------

    def _parse_list(self, html: str, *, base_url: str) -> list[JobRecord]:
        """Primary selector ``.item_recruit`` + fallback anchor 스캔."""
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # Primary: 사람인 표준 카드
        cards = soup.select(".item_recruit")
        if not cards:
            # Fallback 1: 다른 리스트 컨테이너 변형
            cards = soup.select("div.list_item, div.list_body, .recruit_info")
        if cards:
            results = self._parse_card_list(cards, base_url=base_url)
            if results:
                return results
            self.logger.info("saramin: %d cards seen but 0 records built", len(cards))

        # Fallback 2: 어떤 구조든 rec_idx anchor 로 복원
        self.logger.info("saramin: primary selectors empty — anchor fallback")
        return self._parse_anchor_fallback(soup, base_url=base_url)

    def _parse_card_list(self, cards: list[Tag], *, base_url: str) -> list[JobRecord]:
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for card in cards:
            title_anchor = self._find_title_anchor(card)
            if title_anchor is None:
                continue
            title = (title_anchor.get_text(" ", strip=True) or "").strip()
            href_raw = title_anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not title or not href or href.startswith("#"):
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            company = self._extract_card_company(card)
            location = self._extract_card_location(card)
            salary_hint = self._extract_card_salary(card)
            deadline_text = self._extract_card_deadline(card)
            body_text = card.get_text(" ", strip=True)
            deadline = deadline_parser(deadline_text) or deadline_parser(body_text)

            description_parts = [p for p in (salary_hint, deadline_text, body_text) if p]
            description = " | ".join(description_parts)[:MAX_DESCRIPTION]

            try:
                results.append(
                    JobRecord(
                        id=self._make_id(url, title),
                        source_url=url,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=company or "사람인 기업",
                        title=title[:MAX_TITLE],
                        deadline=deadline,
                        location=location,
                        description=description,
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("saramin: skip invalid card %r: %s", title, exc)
                continue
        return results

    def _parse_anchor_fallback(
        self,
        soup: BeautifulSoup,
        *,
        base_url: str,
    ) -> list[JobRecord]:
        """마지막 방어선: ``rec_idx`` 파라미터를 포함한 anchor 전수 스캔."""
        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or "rec_idx" not in href:
                continue
            if href.startswith("#") or href.lower().startswith("javascript"):
                continue

            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 4:
                continue

            url = urljoin(base_url, href)
            if url in seen:
                continue
            seen.add(url)

            container = anchor.find_parent(["li", "tr", "div", "article", "section"])
            body = container.get_text(" ", strip=True) if container else text
            deadline = deadline_parser(body) or deadline_parser(text)

            try:
                results.append(
                    JobRecord(
                        id=self._make_id(url, text),
                        source_url=url,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org="사람인 기업",
                        title=text[:MAX_TITLE],
                        deadline=deadline,
                        description=body[:MAX_DESCRIPTION],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("saramin: anchor-fallback skip %r: %s", text, exc)
                continue
        return results

    # -- card field extractors (all defensive, all string-only return) -----

    @staticmethod
    def _find_title_anchor(card: Tag) -> Tag | None:
        """Title anchor 후보를 여러 selector 로 탐색."""
        candidates = (
            ".job_tit a",
            "h2.job_tit a",
            ".area_job .job_tit a",
            "a[href*='rec_idx']",
        )
        for sel in candidates:
            found = card.select_one(sel)
            if isinstance(found, Tag):
                return found
        # 최후의 수단: 카드 안의 아무 rec_idx 링크
        for anchor in card.find_all("a"):
            href = anchor.get("href") or ""
            if isinstance(href, str) and "rec_idx" in href:
                return anchor
        return None

    @staticmethod
    def _extract_card_company(card: Tag) -> str | None:
        for sel in (".corp_name a", ".area_corp .corp_name", ".corp_name"):
            found = card.select_one(sel)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None

    @staticmethod
    def _extract_card_location(card: Tag) -> str | None:
        for sel in (".job_condition span:nth-of-type(1)", ".work_place", ".job_condition"):
            found = card.select_one(sel)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None

    @staticmethod
    def _extract_card_salary(card: Tag) -> str | None:
        for sel in (".job_sector", ".salary", ".area_job .job_sector"):
            found = card.select_one(sel)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text[:200]
        return None

    @staticmethod
    def _extract_card_deadline(card: Tag) -> str:
        for sel in (".job_date .date", ".date", ".deadlines", ".job_day"):
            found = card.select_one(sel)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text
        return ""

    # -- detail field extractors -------------------------------------------

    @staticmethod
    def _extract_detail_title(soup: BeautifulSoup, *, fallback_url: str) -> str:
        for sel in (
            "h1.tit_job",
            ".wrap_tit_job h1",
            ".tit_job",
            "meta[property='og:title']",
            "title",
        ):
            found = soup.select_one(sel)
            if found is None:
                continue
            if sel.startswith("meta"):
                content = found.get("content") if isinstance(found, Tag) else None
                if isinstance(content, str) and content.strip():
                    return content.strip()
            else:
                text = found.get_text(" ", strip=True)
                if text:
                    return text
        return fallback_url.rsplit("/", 1)[-1] or "사람인 공고"

    @staticmethod
    def _extract_detail_company(soup: BeautifulSoup) -> str | None:
        for sel in (
            ".company_name a",
            ".company_name",
            ".wrap_tit_company .name",
            "meta[property='og:site_name']",
        ):
            found = soup.select_one(sel)
            if found is None:
                continue
            if sel.startswith("meta"):
                content = found.get("content") if isinstance(found, Tag) else None
                if isinstance(content, str) and content.strip():
                    return content.strip()[:100]
            else:
                text = found.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None

    @staticmethod
    def _extract_detail_location(soup: BeautifulSoup) -> str | None:
        for sel in (".work_place", ".location", ".info_work .work_place"):
            found = soup.select_one(sel)
            if found:
                text = found.get_text(" ", strip=True)
                if text:
                    return text[:100]
        return None
