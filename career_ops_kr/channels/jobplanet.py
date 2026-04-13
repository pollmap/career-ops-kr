"""JobPlanet (잡플래닛) recruitment channel.

Source: https://www.jobplanet.co.kr/

JobPlanet is a major Korean careers portal best known for its
employee-review + salary database. On top of that dataset it runs a
publicly-browsable job board at ``/job_postings/search_results`` — the
listings themselves are readable without login, though the richer data
(salary ranges, full reviews) is auth-gated.

Tier: 1 (major portal + T1 review legitimacy when present).
Backend: ``requests`` + BeautifulSoup — the listing HTML is SSR-friendly
and does not require a headless browser. If the parse comes back empty
the channel returns ``[]`` (실데이터 원칙 — 목업 절대 금지).

찬희's scan contract: "전수 수집 — 추리지 말고 가능한 모든 공고".
No keyword whitelist is applied at the channel layer. Downstream
``qualifier`` / ``scorer`` modules are responsible for filtering.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

BASE_URL = "https://www.jobplanet.co.kr/"
SEARCH_URL = "https://www.jobplanet.co.kr/job_postings/search_results"
from career_ops_kr._constants import DEFAULT_USER_AGENT as _APP_UA  # noqa: E402

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    f"({_APP_UA})"
)

# 상세 공고 URL 패턴 후보 — 잡플래닛은 버전에 따라 경로가 바뀜
DETAIL_PATH_MARKERS: tuple[str, ...] = (
    "/job_postings/",
    "/job_posting/",
    "/job/",
    "/jobs/",
    "/company/",
    "/companies/",
)

# 리뷰/연봉 데이터는 auth 게이트지만 평점 숫자는 공개 카드에 노출되는
# 경우가 많다. 평점 토큰을 감지해 description 에 포함한다.
RATING_MARKERS: tuple[str, ...] = (
    "평점",
    "리뷰",
    "만족도",
    "stars",
    "rating",
)

# 방어적 파싱용 selector 세트 — card-level 만 사용한다. wrapper (div.posting_list,
# div.section_group) 는 single-node 로 매칭되어 전체 HTML을 하나의 카드로 합쳐
# 버리기 때문에 여기 포함하면 안 된다. fallback 경로가 generic anchor scan 을
# 담당하므로 primary 는 개별 posting 요소에 집중한다.
PRIMARY_CARD_SELECTORS: tuple[str, ...] = (
    "article.posting",
    "article.job_posting",
    "li.recruit-item",
    "li.posting_item",
    "div.recruit_card",
    "div.job_posting_card",
    "div.posting-card",
)

MAX_CARDS_PER_PAGE = 200
MAX_PAGES_DEFAULT = 5
REQUEST_TIMEOUT = 15


class JobPlanetChannel(BaseChannel):
    """잡플래닛 공개 공고 리스팅 수집기 (requests backend)."""

    name = "jobplanet"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 8
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        search_url: str = SEARCH_URL,
        base_url: str = BASE_URL,
    ) -> None:
        super().__init__()
        self.search_url = search_url
        self.base_url = base_url

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def check(self) -> bool:
        """Probe the public listing page. True on HTTP 200."""
        try:
            resp = requests.get(
                self.search_url,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            self.logger.debug("jobplanet check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return postings — paginated anchor scan of the public search page.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword``: free-text search term passed to ?query=.
                ``industry``: industry filter passed to ?industry=.
                ``pages``: number of pages to fetch (default 5).
        """
        query = query or {}
        keyword = str(query.get("keyword") or "").strip()
        industry = str(query.get("industry") or "").strip()
        try:
            pages = max(1, int(query.get("pages") or MAX_PAGES_DEFAULT))
        except (TypeError, ValueError):
            pages = MAX_PAGES_DEFAULT

        jobs: list[JobRecord] = []
        seen: set[str] = set()

        for page in range(1, pages + 1):
            url = self._build_search_url(
                keyword=keyword,
                industry=industry,
                page=page,
            )
            html = self._fetch_html(url)
            if not html:
                self.logger.info("jobplanet: page %d fetch failed — stopping", page)
                break

            cards = self._parse_cards(html, base_url=url)
            if not cards:
                # 빈 페이지 = 끝 도달. 루프 종료.
                self.logger.info(
                    "jobplanet: page %d returned 0 cards — stopping pagination",
                    page,
                )
                break

            new_count = 0
            for rec in cards:
                key = str(rec.source_url)
                if key in seen:
                    continue
                seen.add(key)
                jobs.append(rec)
                new_count += 1

            self.logger.info(
                "jobplanet: page %d → %d cards (%d new)",
                page,
                len(cards),
                new_count,
            )
            # 새로 추가된 공고가 0개면 페이지네이션이 더 이상 의미 없음.
            if new_count == 0:
                break

        self.logger.info("jobplanet: total %d postings collected", len(jobs))
        return jobs

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch and parse a single posting page. None on any failure."""
        html = self._fetch_html(url)
        if not html:
            return None
        try:
            return self._parse_detail(html, url)
        except Exception as exc:
            self.logger.warning("jobplanet: detail parse failed %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # internals — networking
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.6",
            "Referer": self.base_url,
        }

    def _fetch_html(self, url: str) -> str | None:
        try:
            resp = self._retry(
                requests.get,
                url,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT,
            )
        except Exception as exc:
            self.logger.warning("jobplanet: fetch %s failed: %s", url, exc)
            return None
        if resp is None:
            return None
        if getattr(resp, "status_code", None) != 200:
            self.logger.warning(
                "jobplanet: %s returned HTTP %s",
                url,
                getattr(resp, "status_code", "n/a"),
            )
            return None
        text = getattr(resp, "text", "") or ""
        return text or None

    def _build_search_url(
        self,
        *,
        keyword: str,
        industry: str,
        page: int,
    ) -> str:
        params: dict[str, Any] = {"page": page}
        if keyword:
            params["query"] = keyword
        if industry:
            params["industry"] = industry
        return f"{self.search_url}?{urlencode(params, doseq=True)}"

    # ------------------------------------------------------------------
    # internals — parsing
    # ------------------------------------------------------------------

    def _parse_cards(self, html: str, *, base_url: str) -> list[JobRecord]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")

        # 1) Primary card selectors 시도
        primary_cards: list[Any] = []
        for selector in PRIMARY_CARD_SELECTORS:
            found = soup.select(selector)
            if found:
                primary_cards = found
                self.logger.debug(
                    "jobplanet: primary selector %r matched %d cards",
                    selector,
                    len(found),
                )
                break

        results: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        if primary_cards:
            for card in primary_cards:
                rec = self._card_to_record(card, base_url=base_url, seen=seen, now=now)
                if rec is not None:
                    results.append(rec)
                if len(results) >= MAX_CARDS_PER_PAGE:
                    break
            if results:
                return results

        # 2) Fallback — generic anchor scan (selectors 가 바뀌었을 때 방어)
        for anchor in soup.find_all("a"):
            if len(results) >= MAX_CARDS_PER_PAGE:
                break
            rec = self._anchor_to_record(
                anchor,
                base_url=base_url,
                seen=seen,
                now=now,
            )
            if rec is not None:
                results.append(rec)
        return results

    def _card_to_record(
        self,
        card: Any,
        *,
        base_url: str,
        seen: set[str],
        now: datetime,
    ) -> JobRecord | None:
        anchor = card.find("a", href=True)
        if anchor is None:
            return None
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            return None
        if not any(marker in href for marker in DETAIL_PATH_MARKERS):
            return None

        url = urljoin(base_url, href.split("#", 1)[0])
        if url in seen:
            return None
        seen.add(url)

        title_node = (
            card.select_one(".posting_title")
            or card.select_one(".job_posting__title")
            or card.select_one("h2")
            or card.select_one("h3")
            or anchor
        )
        title = (title_node.get_text(" ", strip=True) or "").strip()
        if not title:
            return None

        org_node = (
            card.select_one(".company_name")
            or card.select_one(".posting_company")
            or card.select_one(".company")
        )
        org = (
            org_node.get_text(" ", strip=True) if org_node else ""
        ).strip() or "잡플래닛 등록기업"

        location_node = (
            card.select_one(".location")
            or card.select_one(".posting_location")
            or card.select_one(".region")
        )
        location = (
            location_node.get_text(" ", strip=True) if location_node else ""
        ).strip() or None

        body = card.get_text(" ", strip=True)
        deadline = deadline_parser(body) or deadline_parser(title)

        description_parts: list[str] = [body[:1800]]
        rating = self._extract_rating(card)
        if rating:
            description_parts.append(f"[잡플래닛 평점] {rating}")

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title[:200],
                archetype="INTERN" if "인턴" in title else None,
                deadline=deadline,
                location=location,
                description=" ".join(p for p in description_parts if p)[:2000],
                legitimacy_tier=self.default_legitimacy_tier,
                scanned_at=now,
            )
        except Exception as exc:
            self.logger.warning("jobplanet: bad card %r: %s", title, exc)
            return None

    def _anchor_to_record(
        self,
        anchor: Any,
        *,
        base_url: str,
        seen: set[str],
        now: datetime,
    ) -> JobRecord | None:
        href_raw = anchor.get("href") or ""
        href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            return None
        if not any(marker in href for marker in DETAIL_PATH_MARKERS):
            return None

        text = (anchor.get_text(" ", strip=True) or "").strip()
        if not text or len(text) < 4 or len(text) > 300:
            return None

        url = urljoin(base_url, href.split("#", 1)[0])
        if url in seen:
            return None
        seen.add(url)

        container = anchor.find_parent(["li", "article", "div", "section"])
        body = container.get_text(" ", strip=True) if container else text

        org_hint = "잡플래닛 등록기업"
        for sep in ("|", "·", "ㆍ", "-"):
            if sep in text:
                candidate = text.split(sep, 1)[0].strip()
                if candidate:
                    org_hint = candidate
                    break
        if container is not None:
            org_node = (
                container.select_one(".company_name")
                or container.select_one(".posting_company")
                or container.select_one(".company")
            )
            if org_node is not None:
                label = (org_node.get_text(" ", strip=True) or "").strip()
                if label:
                    org_hint = label

        description_parts: list[str] = [body[:1800]]
        if container is not None:
            rating = self._extract_rating(container)
            if rating:
                description_parts.append(f"[잡플래닛 평점] {rating}")

        deadline = deadline_parser(body) or deadline_parser(text)

        try:
            return JobRecord(
                id=self._make_id(url, text),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org_hint[:100],
                title=text[:200],
                archetype="INTERN" if "인턴" in text else None,
                deadline=deadline,
                description=" ".join(p for p in description_parts if p)[:2000],
                legitimacy_tier=self.default_legitimacy_tier,
                scanned_at=now,
            )
        except Exception as exc:
            self.logger.warning("jobplanet: bad anchor %r: %s", text, exc)
            return None

    def _parse_detail(self, html: str, url: str) -> JobRecord:
        soup = BeautifulSoup(html, "html.parser")
        title_node = (
            soup.select_one(".posting_title")
            or soup.select_one(".job_posting__title")
            or soup.select_one("h1")
            or soup.title
        )
        title = (title_node.get_text(" ", strip=True) if title_node else url.rsplit("/", 1)[-1])[
            :200
        ] or "잡플래닛 공고"

        org_node = (
            soup.select_one(".company_name")
            or soup.select_one(".posting_company")
            or soup.select_one(".company")
        )
        org = (
            org_node.get_text(" ", strip=True) if org_node else ""
        ).strip() or "잡플래닛 등록기업"

        location_node = (
            soup.select_one(".location")
            or soup.select_one(".posting_location")
            or soup.select_one(".region")
        )
        location = (
            location_node.get_text(" ", strip=True) if location_node else ""
        ).strip() or None

        plain = soup.get_text(" ", strip=True)
        rating = self._extract_rating(soup)
        description = plain[:4800]
        if rating:
            description = f"{description} [잡플래닛 평점] {rating}"

        return JobRecord(
            id=self._make_id(url, title),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org=org[:100],
            title=title,
            archetype="INTERN" if "인턴" in title else None,
            deadline=deadline_parser(plain),
            location=location,
            description=description[:5000],
            raw_html=html[:50_000],
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # ------------------------------------------------------------------
    # internals — rating extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_rating(node: Any) -> str | None:
        """Look for a rating label/value pair inside ``node``.

        Returns a human-readable string like ``"3.8/5.0"`` or ``"평점 4.1"``
        when any rating marker is present, else ``None``.
        """
        if node is None:
            return None
        try:
            text = node.get_text(" ", strip=True)
        except Exception:
            return None
        if not text:
            return None
        lowered = text.lower()
        if not any(marker in lowered or marker in text for marker in RATING_MARKERS):
            return None

        # 평점 숫자 추출 시도 (ex. "3.8/5.0", "4.1")
        import re

        match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*5(?:\.0)?", text)
        if match:
            return f"{match.group(1)}/5.0"
        match = re.search(r"평점[^0-9]{0,4}(\d+(?:\.\d+)?)", text)
        if match:
            return f"평점 {match.group(1)}"
        match = re.search(r"(\d+\.\d+)\s*점", text)
        if match:
            return f"{match.group(1)}점"
        return None


__all__ = ["BASE_URL", "SEARCH_URL", "JobPlanetChannel"]
