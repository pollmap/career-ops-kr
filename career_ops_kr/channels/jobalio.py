"""Jobalio channel — 공공기관 채용정보 (job.alio.go.kr).

Backend: ``rss`` primary + ``html`` fallback via anchor scraping.

Notes:
    - ALIO 공식 RSS(recruit.xml) 가 구조 변경되면 feedparser 가 빈 entries
      를 반환한다. 이 경우 ``_list_from_html`` fallback 으로 랜딩 페이지의
      anchor 들을 직접 스캔하여 포스팅 후보를 추출한다.
    - 모든 경로가 실패하면 빈 리스트를 반환한다 (실데이터 원칙 — 목업 금지).
    - 기본 Tier 는 1 (ALIO 는 공공 채용 공식 포털).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

RSS_URL = "https://job.alio.go.kr/rss/recruit.xml"
LANDING_URL = "https://job.alio.go.kr/recruit.do"
ALT_LIST_URL = "https://job.alio.go.kr/recruitList.do"
OCCASIONAL_URL = "https://job.alio.go.kr/occasional/researchList.do"
OCCASIONAL_ALT_URL = "https://job.alio.go.kr/mobile/occasional/researchList.do"
USER_AGENT = "Mozilla/5.0 (career-ops-kr/0.2.0; +https://github.com/pollmap/career-ops-kr)"

_CAREER_KEYWORDS: tuple[str, ...] = (
    "채용",
    "모집",
    "공고",
    "인턴",
    "신입",
    "경력",
    "recruit",
    "career",
)


class JobalioChannel(BaseChannel):
    """공공기관 채용정보 (ALIO) RSS/HTML scraper with HTML fallback."""

    name = "jobalio"
    tier = 1
    backend = "rss+html"
    default_rate_per_minute = 12
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        rss_url: str = RSS_URL,
        landing_url: str = LANDING_URL,
    ) -> None:
        super().__init__()
        self.rss_url = rss_url
        self.landing_url = landing_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        for url in (self.rss_url, self.landing_url):
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return True
            except requests.RequestException as exc:
                self.logger.debug("jobalio check %s: %s", url, exc)
                continue
        return False

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return jobs — RSS first, HTML fallback on empty/failure.

        Also fetches 수시공고 (occasional) postings from OCCASIONAL_URL and
        merges them with regular postings, deduplicating by record ``id``.

        Args:
            query: Optional filter dict. Recognised keys:
                ``type``: if ``"intern"``, keep only postings containing
                ``인턴`` in title/description.
        """
        query = query or {}

        # --- regular 정기공고 (RSS → HTML fallback) ---
        rss_jobs = self._list_from_rss(query)
        if rss_jobs:
            self.logger.info("jobalio: %d jobs from RSS", len(rss_jobs))
            regular_jobs: list[JobRecord] = rss_jobs
        else:
            self.logger.info("jobalio: RSS empty — falling back to HTML landing")
            html_jobs = self._list_from_html(query)
            self.logger.info("jobalio: %d jobs from HTML fallback", len(html_jobs))
            regular_jobs = html_jobs

        # --- 수시공고 (occasional) ---
        occasional_jobs = self._list_from_occasional(query)
        self.logger.info("jobalio: %d jobs from occasional", len(occasional_jobs))

        # --- combine + dedup by id ---
        seen_ids: set[str] = set()
        combined: list[JobRecord] = []
        for job in regular_jobs + occasional_jobs:
            if job.id not in seen_ids:
                seen_ids.add(job.id)
                combined.append(job)

        return combined

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            resp = self._retry(
                requests.get,
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
        except Exception as exc:
            self.logger.warning("jobalio get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        body = resp.text
        soup = BeautifulSoup(body, "html.parser")
        title = (soup.title.get_text(strip=True) if soup.title else url.rsplit("/", 1)[-1])[
            :200
        ] or "ALIO 공고"
        plain = soup.get_text(" ", strip=True)
        return JobRecord(
            id=self._make_id(url, title),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="공공기관",
            title=title,
            description=plain[:4000],
            raw_html=body,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals: RSS path ------------------------------------------------

    def _list_from_rss(self, query: dict[str, Any]) -> list[JobRecord]:
        parsed = self._retry(self._fetch_rss)
        if parsed is None:
            return []
        entries = getattr(parsed, "entries", None) or []
        if not entries:
            bozo = getattr(parsed, "bozo", None)
            status = getattr(parsed, "status", None)
            # Downgraded to INFO: ALIO RSS is known to return 0 entries or a
            # 404 periodically; the HTML fallback path in ``list_jobs`` will
            # compensate. Only the final dispatcher (RSS→HTML→empty) warrants
            # a WARNING and that's handled by the public ``list_jobs`` logs.
            self.logger.info(
                "jobalio RSS empty (url=%s, status=%s, bozo=%s) — using HTML fallback",
                self.rss_url,
                status,
                bozo,
            )
            return []

        results: list[JobRecord] = []
        now = datetime.now()
        for entry in entries:
            title = (getattr(entry, "title", "") or "").strip()
            link = (getattr(entry, "link", "") or "").strip()
            summary = (getattr(entry, "summary", "") or "").strip()
            org = (getattr(entry, "author", "") or "").strip() or "공공기관"
            if not title or not link:
                continue
            if query.get("type") == "intern":
                blob = f"{title} {summary}"
                if "인턴" not in blob:
                    continue

            posted_at = None
            if getattr(entry, "published_parsed", None):
                try:
                    posted_at = datetime(*entry.published_parsed[:6]).date()
                except (TypeError, ValueError):
                    posted_at = None
            deadline = deadline_parser(summary) or deadline_parser(title)

            try:
                results.append(
                    JobRecord(
                        id=self._make_id(link, title),
                        source_url=link,  # type: ignore[arg-type]
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=org,
                        title=title,
                        archetype="INTERN" if "인턴" in title else None,
                        deadline=deadline,
                        posted_at=posted_at,
                        description=summary,
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("jobalio: bad RSS entry %r: %s", title, exc)
                continue
        return results

    def _fetch_rss(self) -> Any:
        self.logger.info("jobalio: fetching RSS %s", self.rss_url)
        return feedparser.parse(
            self.rss_url,
            request_headers={"User-Agent": USER_AGENT},
        )

    # -- internals: occasional (수시공고) ------------------------------------

    def _list_from_occasional(self, query: dict[str, Any]) -> list[JobRecord]:
        """Fetch 수시공고 from OCCASIONAL_URL with OCCASIONAL_ALT_URL fallback.

        Uses the same 3-tier anchor fallback pattern as ``_list_from_html``.
        Records are marked with ``archetype="OCCASIONAL"``.
        """
        for url in (OCCASIONAL_URL, OCCASIONAL_ALT_URL):
            try:
                resp = self._retry(
                    requests.get,
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=15,
                )
            except Exception as exc:
                self.logger.warning("jobalio occasional fetch %s failed: %s", url, exc)
                continue
            if resp is None or resp.status_code != 200:
                self.logger.warning(
                    "jobalio occasional %s returned %s",
                    url,
                    getattr(resp, "status_code", "n/a"),
                )
                continue
            jobs = self._parse_occasional_html(resp.text, base_url=url, query=query)
            if jobs:
                return jobs
        return []

    def _parse_occasional_html(
        self,
        html: str,
        *,
        base_url: str,
        query: dict[str, Any],
    ) -> list[JobRecord]:
        """Parse HTML from the occasional listing page into JobRecords.

        Anchor selection is attempted in priority order:
        1. ``table.tbl_list td a`` / ``ul.list_board li a`` (primary)
        2. ``a[href*='/occasional/']`` / ``a[href*='/researchDetail']`` (fallback)
        3. Generic ``_CAREER_KEYWORDS`` scan (generic)

        All resulting records carry ``archetype="OCCASIONAL"``.
        """
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        seen: set[str] = set()
        results: list[JobRecord] = []
        now = datetime.now()

        # Tier 1 — structured selectors
        primary_anchors = soup.select("table.tbl_list td a, ul.list_board li a")

        # Tier 2 — URL-pattern fallback
        if not primary_anchors:
            primary_anchors = soup.select("a[href*='/occasional/'], a[href*='/researchDetail']")

        # Tier 3 — generic keyword scan (all anchors)
        candidate_anchors = primary_anchors if primary_anchors else soup.find_all("a")

        for anchor in candidate_anchors:
            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 6 or len(text) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            # Tier 3 only: require career keywords
            if not primary_anchors:
                blob_lower = (text + " " + href).lower()
                if not any(kw.lower() in blob_lower for kw in _CAREER_KEYWORDS):
                    continue

            if query.get("type") == "intern" and "인턴" not in text:
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
                        org="공공기관",
                        title=text[:200],
                        archetype="OCCASIONAL",
                        deadline=deadline,
                        description=body[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("jobalio: bad occasional card %r: %s", text, exc)
                continue

            if len(results) >= 50:
                break
        return results

    # -- internals: HTML fallback -------------------------------------------

    def _list_from_html(self, query: dict[str, Any]) -> list[JobRecord]:
        for url in (self.landing_url, ALT_LIST_URL):
            try:
                resp = self._retry(
                    requests.get,
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=15,
                )
            except Exception as exc:
                self.logger.warning("jobalio HTML fetch %s failed: %s", url, exc)
                continue
            if resp is None or resp.status_code != 200:
                self.logger.warning(
                    "jobalio HTML %s returned %s",
                    url,
                    getattr(resp, "status_code", "n/a"),
                )
                continue
            jobs = self._parse_html(resp.text, base_url=url, query=query)
            if jobs:
                return jobs
        return []

    def _parse_html(
        self,
        html: str,
        *,
        base_url: str,
        query: dict[str, Any],
    ) -> list[JobRecord]:
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        seen: set[str] = set()
        results: list[JobRecord] = []
        now = datetime.now()

        for anchor in soup.find_all("a"):
            text = (anchor.get_text(" ", strip=True) or "").strip()
            if not text or len(text) < 6 or len(text) > 300:
                continue
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                continue

            blob_lower = (text + " " + href).lower()
            if not any(kw.lower() in blob_lower for kw in _CAREER_KEYWORDS):
                continue
            if query.get("type") == "intern" and "인턴" not in text:
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
                        org="공공기관",
                        title=text[:200],
                        archetype="INTERN" if "인턴" in text else None,
                        deadline=deadline,
                        description=body[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("jobalio: bad HTML card %r: %s", text, exc)
                continue

            if len(results) >= 50:
                break
        return results
