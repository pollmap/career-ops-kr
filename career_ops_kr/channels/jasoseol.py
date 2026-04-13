"""Jasoseol (자소설닷컴) channel — 신입/인턴 전문 채용 포털.

Source: https://jasoseol.com/ (listing: https://jasoseol.com/recruit)

자소설닷컴은 대학생·신입·인턴 특화 채용 포털로, 자소서 샘플 + 기업 지원
마감일 + 채용 공고가 통합된 공개 리스팅을 제공한다. 사용자 프로파일
(24세 재학생 휴학, 신입 타겟)과 정확히 일치하므로 Tier 1 공식 채널로
분류한다.

Backend: ``requests`` + BeautifulSoup. 자소설은 서버사이드 렌더링된 HTML
리스트를 노출하기 때문에 Playwright 없이 정적 파싱이 가능하다. 동적
섹션(리액트 하이드레이션)이 있는 경우에도 ``__NEXT_DATA__`` 인라인
JSON payload가 남아 있어 fallback 파서가 이를 활용한다.

Query parameters (``list_jobs``):
    keyword:  제목/회사명 필터링 (대소문자 무시, 한글 substring 매치)
    pages:    크롤할 페이지 수 (기본 1, 최대 10) — ``/recruit?page=N``
    category: ``"신입"`` / ``"인턴"`` / ``"경력"`` 중 하나로 제한

특징:
    * 마감일이 prominently 표시됨 (``D-N`` 형태 + 절대일자)
    * 지원자 수 / 경쟁률 데이터가 카드에 포함 → description 에 보존
    * 조회수(views) 및 북마크 수치도 있으면 함께 저장

실패 시 항상 빈 리스트 / None 반환. 실데이터 원칙 — 목업/추정 금지.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://jasoseol.com/"
LIST_URL = "https://jasoseol.com/recruit"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 "
    "career-ops-kr/0.2.0"
)
DEFAULT_TIMEOUT = 15

# Supported category filters — Korean keyword → token that must appear in
# the card body for the card to be kept.
_CATEGORY_TOKENS: dict[str, tuple[str, ...]] = {
    "신입": ("신입",),
    "인턴": ("인턴", "체험형", "intern"),
    "경력": ("경력", "정규직", "career"),
}

# Positive career-keyword allowlist applied to every anchor before we even
# consider it a candidate posting. Jasoseol has a lot of nav/footer anchors.
_CARD_HINTS: tuple[str, ...] = (
    "recruit",
    "jobs",
    "posting",
    "채용",
    "공고",
    "모집",
    "/company/",
)

# Negative substring list — if any of these appear in the anchor text the
# card is skipped (nav, auth, marketing).
_CARD_NEGATIVES: tuple[str, ...] = (
    "로그인",
    "회원가입",
    "개인정보",
    "이용약관",
    "고객센터",
    "자소서",
    "자소설",
    "프리미엄",
    "이벤트",
)

# Regex patterns — compiled once and reused.
_DDAY_RE = re.compile(r"D-(\d{1,3})")
_DEND_RE = re.compile(r"(?:마감|상시|오늘마감|today)", re.IGNORECASE)
_APPLICANT_RE = re.compile(r"지원자\s*([0-9,]+)")
_COMPETITION_RE = re.compile(r"경쟁률\s*([0-9.,:]+)")
_VIEWS_RE = re.compile(r"조회\s*([0-9,]+)")


# ---------------------------------------------------------------------------
# Parsed card DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ParsedCard:
    """Intermediate DTO between HTML parse and ``JobRecord`` materialization."""

    url: str
    title: str
    org: str
    location: str | None
    deadline: date | None
    dday: int | None
    applicants: str | None
    competition: str | None
    views: str | None
    body_text: str


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------


class JasoseolChannel(BaseChannel):
    """자소설닷컴 (jasoseol.com) listing scraper — 신입/인턴 특화 T1 채널."""

    name = "jasoseol"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 10
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        base_url: str = BASE_URL,
        list_url: str = LIST_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        super().__init__()
        self.base_url = base_url
        self.list_url = list_url
        self.timeout = timeout

    # ------------------------------------------------------------------ API

    def check(self) -> bool:
        """Return True if the Jasoseol listing URL is reachable."""
        try:
            resp = requests.get(
                self.list_url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            self.logger.debug("jasoseol check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Crawl ``/recruit`` (plus optional extra pages) and emit records.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword`` (str): case-insensitive title/org filter.
                ``pages`` (int): pagination depth, 1..10 (default 1).
                ``category`` (str): ``"신입"`` / ``"인턴"`` / ``"경력"``.
                ``sort`` (str): ``"deadline"`` → sort by D-N ascending.
        """
        query = query or {}
        keyword = (query.get("keyword") or "").strip().lower() or None
        category = query.get("category")
        sort = (query.get("sort") or "").strip().lower()
        try:
            pages = max(1, min(10, int(query.get("pages") or 1)))
        except (TypeError, ValueError):
            pages = 1

        urls = [self.list_url] + [f"{self.list_url}?page={n}" for n in range(2, pages + 1)]

        seen_ids: set[str] = set()
        records: list[JobRecord] = []

        for url in urls:
            html = self._fetch_html(url)
            if not html:
                continue
            cards = self._parse_listing(html, base_url=url)
            if not cards:
                self.logger.info("jasoseol: no cards on %s", url)
                continue
            for card in cards:
                if not self._passes_filters(card, keyword=keyword, category=category):
                    continue
                record = self._card_to_record(card)
                if record is None or record.id in seen_ids:
                    continue
                seen_ids.add(record.id)
                records.append(record)

        if sort == "deadline":
            records = self._sort_by_deadline(records)

        self.logger.info("jasoseol: %d records collected", len(records))
        return records

    def get_detail(self, url: str) -> JobRecord | None:
        """Fetch a single posting and build a ``JobRecord``."""
        if not url:
            return None
        html = self._fetch_html(url)
        if not html:
            return None
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("jasoseol: detail parse failed %s: %s", url, exc)
            return None

        title_tag = soup.title
        title = (title_tag.get_text(strip=True) if title_tag else url).strip()[
            :200
        ] or "자소설 공고"
        body_text = soup.get_text(" ", strip=True)

        # Try to pick the company name out of an h1/h2 near the top.
        org = self._guess_org(soup) or "자소설 게시물"
        deadline = self._extract_deadline(body_text)
        applicants = _APPLICANT_RE.search(body_text)
        competition = _COMPETITION_RE.search(body_text)

        desc_parts: list[str] = [body_text[:4500]]
        if applicants:
            desc_parts.append(f"[지원자 {applicants.group(1)}]")
        if competition:
            desc_parts.append(f"[경쟁률 {competition.group(1)}]")
        description = " ".join(desc_parts)[:5000]

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=org[:100],
                title=title,
                archetype=self._infer_archetype(title),
                deadline=deadline,
                description=description,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("jasoseol: build detail record failed %s: %s", url, exc)
            return None

    # ----------------------------------------------------------------- HTTP

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _fetch_html(self, url: str) -> str | None:
        try:
            resp = self._retry(
                requests.get,
                url,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except Exception as exc:
            self.logger.warning("jasoseol: fetch %s raised %s", url, exc)
            return None
        if resp is None:
            self.logger.warning("jasoseol: fetch %s returned None", url)
            return None
        if getattr(resp, "status_code", 0) != 200:
            self.logger.warning(
                "jasoseol: fetch %s returned status=%s",
                url,
                getattr(resp, "status_code", "n/a"),
            )
            return None
        text = getattr(resp, "text", "") or ""
        if not text.strip():
            return None
        return text

    # ----------------------------------------------------------------- PARSE

    def _parse_listing(self, html: str, *, base_url: str) -> list[_ParsedCard]:
        """Extract candidate postings from a ``/recruit`` listing page."""
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            self.logger.warning("jasoseol: BS4 parse failed: %s", exc)
            return []

        cards = self._parse_from_anchors(soup, base_url=base_url)
        if cards:
            return cards

        # Fallback: scrape Next.js hydration payload (``__NEXT_DATA__``).
        next_data = soup.find("script", id="__NEXT_DATA__")
        if isinstance(next_data, Tag) and next_data.string:
            return self._parse_from_next_data(next_data.string, base_url=base_url)

        return []

    def _parse_from_anchors(self, soup: BeautifulSoup, *, base_url: str) -> list[_ParsedCard]:
        results: list[_ParsedCard] = []
        seen_urls: set[str] = set()

        for anchor in soup.find_all("a"):
            if not isinstance(anchor, Tag):
                continue

            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 4 or len(text) > 300:
                continue

            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            # Positive/negative filters.
            low = (text + " " + href).lower()
            if any(neg in text for neg in _CARD_NEGATIVES):
                continue
            if not any(hint in low for hint in _CARD_HINTS):
                continue

            url = urljoin(base_url, href)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            container = anchor.find_parent(["li", "tr", "article", "div", "section"])
            body_text = container.get_text(" ", strip=True) if container else text

            title, org = self._split_title_org(text)
            location = self._extract_location(body_text)
            dday, deadline = self._extract_dday_and_deadline(body_text)
            applicants = self._first_group(_APPLICANT_RE, body_text)
            competition = self._first_group(_COMPETITION_RE, body_text)
            views = self._first_group(_VIEWS_RE, body_text)

            results.append(
                _ParsedCard(
                    url=url,
                    title=title[:200] or text[:200],
                    org=org[:100] or "자소설 게시물",
                    location=location,
                    deadline=deadline,
                    dday=dday,
                    applicants=applicants,
                    competition=competition,
                    views=views,
                    body_text=body_text[:3000],
                )
            )

        return results

    def _parse_from_next_data(self, raw_json: str, *, base_url: str) -> list[_ParsedCard]:
        """Fallback: walk ``__NEXT_DATA__`` JSON tree for job-like dicts."""
        try:
            payload = json.loads(raw_json)
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.warning("jasoseol: __NEXT_DATA__ JSON parse failed: %s", exc)
            return []

        results: list[_ParsedCard] = []
        seen: set[str] = set()

        def walk(obj: Any) -> None:
            if isinstance(obj, dict):
                card = self._card_from_dict(obj, base_url=base_url)
                if card is not None and card.url not in seen:
                    seen.add(card.url)
                    results.append(card)
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        try:
            walk(payload)
        except RecursionError:  # pragma: no cover - defensive
            self.logger.warning("jasoseol: __NEXT_DATA__ too deep — partial results")

        return results

    def _card_from_dict(self, obj: dict[str, Any], *, base_url: str) -> _ParsedCard | None:
        """Build a ``_ParsedCard`` from a dict if it looks like a posting."""
        title = obj.get("title") or obj.get("recruit_title") or obj.get("name")
        if not isinstance(title, str) or len(title.strip()) < 4:
            return None

        slug_keys = ("slug", "recruit_slug", "path", "url", "permalink")
        slug: str | None = None
        for key in slug_keys:
            value = obj.get(key)
            if isinstance(value, str) and value:
                slug = value
                break
        if slug is None:
            rid = obj.get("id") or obj.get("recruit_id")
            if rid is None:
                return None
            slug = f"/recruit/{rid}"

        url = urljoin(
            base_url, slug if slug.startswith("http") or slug.startswith("/") else f"/{slug}"
        )

        org_raw = obj.get("company_name") or obj.get("company") or obj.get("org") or ""
        if isinstance(org_raw, dict):
            org_raw = org_raw.get("name") or org_raw.get("title") or ""
        org = (org_raw or "자소설 게시물").strip()[:100]

        location_raw = obj.get("location") or obj.get("region") or obj.get("address")
        location = location_raw.strip() if isinstance(location_raw, str) else None

        deadline_raw = obj.get("end_date") or obj.get("deadline") or obj.get("close_at")
        deadline = deadline_parser(deadline_raw) if isinstance(deadline_raw, str) else None
        if deadline is None and isinstance(deadline_raw, str):
            deadline = self._extract_deadline(deadline_raw)

        dday_raw = obj.get("d_day") or obj.get("dday")
        dday: int | None = None
        if isinstance(dday_raw, int):
            dday = dday_raw
        elif isinstance(dday_raw, str):
            match = _DDAY_RE.search(dday_raw)
            if match is not None:
                try:
                    dday = int(match.group(1))
                except ValueError:
                    dday = None

        body_bits: list[str] = [title]
        if org:
            body_bits.append(org)
        if location:
            body_bits.append(location)
        if isinstance(deadline_raw, str):
            body_bits.append(deadline_raw)
        body_text = " | ".join(body_bits)[:3000]

        return _ParsedCard(
            url=url,
            title=title.strip()[:200],
            org=org,
            location=location,
            deadline=deadline,
            dday=dday,
            applicants=None,
            competition=None,
            views=None,
            body_text=body_text,
        )

    # ------------------------------------------------------------- FILTERS

    def _passes_filters(
        self,
        card: _ParsedCard,
        *,
        keyword: str | None,
        category: str | None,
    ) -> bool:
        if keyword:
            blob = f"{card.title} {card.org} {card.body_text}".lower()
            if keyword not in blob:
                return False
        if category:
            tokens = _CATEGORY_TOKENS.get(category)
            if tokens:
                blob = f"{card.title} {card.body_text}"
                if not any(tok in blob for tok in tokens):
                    return False
        return True

    # --------------------------------------------------------- UTILITIES

    @staticmethod
    def _first_group(pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        return match.group(1) if match else None

    @staticmethod
    def _split_title_org(text: str) -> tuple[str, str]:
        """Split ``"회사 | 제목"`` or ``"회사 - 제목"`` into (title, org)."""
        for sep in ("|", "·", "ㆍ", " - ", " — "):
            if sep in text:
                head, tail = text.split(sep, 1)
                head, tail = head.strip(), tail.strip()
                if head and tail:
                    return tail, head
        return text.strip(), ""

    def _extract_dday_and_deadline(self, body_text: str) -> tuple[int | None, date | None]:
        """Extract both a D-N offset and an absolute deadline if present."""
        deadline = self._extract_deadline(body_text)
        dday: int | None = None

        match = _DDAY_RE.search(body_text)
        if match is not None:
            try:
                dday = int(match.group(1))
            except ValueError:
                dday = None

        if deadline is None and dday is not None:
            deadline = date.today() + timedelta(days=dday)

        # "상시/마감" markers — no numeric deadline, leave None.
        return dday, deadline

    @staticmethod
    def _extract_deadline(body_text: str) -> date | None:
        """Run ``deadline_parser`` over the card body, tolerating None."""
        return deadline_parser(body_text) if body_text else None

    @staticmethod
    def _extract_location(body_text: str) -> str | None:
        """Pull a coarse location hint out of the card body."""
        if not body_text:
            return None
        for keyword in ("서울", "경기", "인천", "부산", "대전", "대구", "광주", "세종"):
            if keyword in body_text:
                # Capture the token plus an optional district.
                idx = body_text.find(keyword)
                snippet = body_text[idx : idx + 15]
                return snippet.split(" ", 1)[0][:40]
        return None

    @staticmethod
    def _guess_org(soup: BeautifulSoup) -> str | None:
        for selector in ("h1", "h2", "[class*='company']", "[class*='org']"):
            tag = soup.select_one(selector)
            if tag is not None:
                text = tag.get_text(" ", strip=True)
                if text and 1 < len(text) < 80:
                    return text
        return None

    @staticmethod
    def _infer_archetype(text: str) -> str | None:
        low = (text or "").lower()
        if "인턴" in text or "intern" in low:
            return "INTERN"
        if "신입" in text:
            return "NEW_GRAD"
        if "경력" in text:
            return "EXPERIENCED"
        return None

    def _card_to_record(self, card: _ParsedCard) -> JobRecord | None:
        stats: list[str] = []
        if card.dday is not None:
            stats.append(f"[D-{card.dday}]")
        if card.applicants:
            stats.append(f"[지원자 {card.applicants}]")
        if card.competition:
            stats.append(f"[경쟁률 {card.competition}]")
        if card.views:
            stats.append(f"[조회 {card.views}]")
        description = " ".join([*stats, card.body_text])[:5000]

        try:
            return JobRecord(
                id=self._make_id(card.url, card.title),
                source_url=card.url,  # type: ignore[arg-type]
                source_channel=self.name,
                source_tier=self.tier,
                org=card.org,
                title=card.title,
                archetype=self._infer_archetype(card.title),
                deadline=card.deadline,
                posted_at=None,
                location=card.location,
                description=description,
                legitimacy_tier=self.default_legitimacy_tier,
                scanned_at=datetime.now(),
            )
        except Exception as exc:
            self.logger.warning("jasoseol: record build failed for %r: %s", card.title, exc)
            return None

    @staticmethod
    def _sort_by_deadline(records: list[JobRecord]) -> list[JobRecord]:
        """Sort by ``deadline`` ascending; records without a deadline go last."""
        today = date.today()

        def key(rec: JobRecord) -> tuple[int, int]:
            if rec.deadline is None:
                return (1, 10_000)
            return (0, max(0, (rec.deadline - today).days))

        return sorted(records, key=key)
