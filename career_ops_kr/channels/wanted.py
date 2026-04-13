"""Wanted (원티드) channel — fintech / blockchain / crypto positions.

Source: https://www.wanted.co.kr/

Backend: ``requests`` + JSON API (primary) / BeautifulSoup HTML (fallback).

Notes:
    - 원티드는 내부 JSON API ``/api/v4/jobs`` 를 제공한다. 키워드 검색 결과를
      JSON 으로 가져올 수 있어 HTML 스크래핑보다 안정적이다.
    - **2가지 전략 (API 우선)**:
        1. API 경로: ``/api/v4/jobs?query=<kw>&limit=20`` → JSON 파싱 → JobRecord
        2. HTML fallback: ``/search?query=<kw>&tab=position`` → anchor scan
    - API 가 200 이 아니거나 JSON 파싱 실패 시 HTML fallback 으로 내려간다.
    - On any failure return ``[]``. Never fabricate listings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "https://www.wanted.co.kr/"

API_SEARCH_TMPL = (
    "https://www.wanted.co.kr/api/v4/jobs"
    "?query={query}&country=kr&job_sort=job.latest_order"
    "&years=-1&limit=20&offset={offset}"
)

SEARCH_PAGE_TMPL = "https://www.wanted.co.kr/search?query={query}&tab=position"

SEARCH_QUERIES: tuple[str, ...] = (
    # 금융 업종
    "은행",
    "증권",
    "보험",
    "자산운용",
    "카드사",
    "캐피탈",
    "저축은행",
    # 기타 금융/IT
    "핀테크",
    "디지털자산",
    "데이터",
    "AI",
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
    "Accept": "application/json, text/html, */*;q=0.8",
}


# ---------------------------------------------------------------------------
# Channel
# ---------------------------------------------------------------------------


class WantedChannel(BaseChannel):
    """원티드 포지션 수집기 (requests backend, API-first).

    전략:
        1. SEARCH_QUERIES 각 키워드에 대해 ``/api/v4/jobs`` JSON API 를 호출.
        2. API 실패(비200 또는 JSON 파싱 오류) 시 HTML fallback (anchor scan).
        3. 중복 제거는 ``seen_ids`` set 으로 처리.
    """

    name = "wanted"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 10
    default_legitimacy_tier = "T1"

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        """Reachability probe -- HEAD the base URL."""
        try:
            resp = requests.get(
                BASE_URL,
                headers=DEFAULT_HEADERS,
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.debug("wanted check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        """Return postings from all SEARCH_QUERIES, deduped.

        Args:
            query: Optional filter dict. Recognised keys:
                ``keyword``: str -- single keyword override.

        Returns:
            list of :class:`JobRecord`. Empty list on any fetch error.
        """
        query = query or {}
        keyword_override = (query.get("keyword") or "").strip()
        keywords = (keyword_override,) if keyword_override else SEARCH_QUERIES

        all_jobs: list[JobRecord] = []
        seen_ids: set[str] = set()

        for search_term in keywords:
            api_jobs = self._fetch_via_api(search_term)
            if api_jobs:
                for job in api_jobs:
                    if job.id not in seen_ids:
                        seen_ids.add(job.id)
                        all_jobs.append(job)
            else:
                # API failed -> HTML fallback
                html_jobs = self._fetch_via_html(search_term)
                for job in html_jobs:
                    if job.id not in seen_ids:
                        seen_ids.add(job.id)
                        all_jobs.append(job)

        self.logger.info("wanted: total %d unique jobs collected", len(all_jobs))
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
            self.logger.warning("wanted get_detail parse failed %s: %s", url, exc)
            return None

    # -- API path -----------------------------------------------------------

    def _fetch_via_api(self, keyword: str) -> list[JobRecord]:
        """Fetch job listings via the JSON API for *keyword*.

        Returns a list of JobRecords, or empty list on any failure.
        """
        url = API_SEARCH_TMPL.format(query=quote(keyword), offset=0)
        resp = self._retry(
            requests.get,
            url,
            headers=DEFAULT_HEADERS,
            timeout=15,
        )
        if resp is None or getattr(resp, "status_code", None) != 200:
            return []

        try:
            data = resp.json()
        except (ValueError, AttributeError):
            return []

        jobs: list[JobRecord] = []
        now = datetime.now()

        for item in data.get("data", []):
            position = (item.get("position") or "").strip()
            if not position:
                continue

            company_obj = item.get("company") or {}
            company_name = (company_obj.get("name") or "원티드 기업").strip()
            job_id = item.get("id", "")
            detail_url = f"https://www.wanted.co.kr/wd/{job_id}"
            due_time = (item.get("due_time") or "").strip()

            try:
                jobs.append(
                    JobRecord(
                        id=self._make_id(detail_url, position),
                        source_url=detail_url,
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=company_name[:100],
                        title=position[:200],
                        archetype=self._infer_archetype(position),
                        deadline=deadline_parser(due_time) if due_time else None,
                        description=position[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("wanted: skip invalid API item %r: %s", position, exc)
                continue

        self.logger.info("wanted: API returned %d jobs for %r", len(jobs), keyword)
        return jobs

    # -- HTML fallback path -------------------------------------------------

    def _fetch_via_html(self, keyword: str) -> list[JobRecord]:
        """Fallback: fetch the search page HTML and parse anchors.

        Returns a list of JobRecords, or empty list on any failure.
        """
        url = SEARCH_PAGE_TMPL.format(query=quote(keyword))
        html = self._fetch_html(url)
        if html is None:
            return []
        return self._parse_listing_html(html)

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
            self.logger.warning("wanted: %s returned %s", url, status)
            return None
        if getattr(resp, "encoding", None):
            resp.encoding = "utf-8"
        return getattr(resp, "text", None)

    def _parse_listing_html(self, html: str) -> list[JobRecord]:
        """Parse a search-result page into JobRecords via anchor scan.

        Looks for ``<a>`` tags whose href contains ``/wd/`` (원티드 detail
        path). Extracts title and org from surrounding container.
        """
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[JobRecord] = []
        seen: set[str] = set()
        now = datetime.now()

        for anchor in soup.find_all("a"):
            href_raw = anchor.get("href") or ""
            href = href_raw if isinstance(href_raw, str) else " ".join(href_raw)
            if "/wd/" not in href:
                continue
            url = urljoin(BASE_URL, href.split("?", 1)[0])
            if url in seen:
                continue
            text = anchor.get_text(" ", strip=True)
            if not text or len(text) < 4:
                continue
            seen.add(url)

            container = anchor.find_parent(["li", "article", "div"])
            body = container.get_text(" ", strip=True) if container else text

            title = text[:200]
            org = "원티드 기업"
            if container:
                span = container.find("span")
                if span:
                    org = (span.get_text(strip=True) or org)[:100]

            try:
                jobs.append(
                    JobRecord(
                        id=self._make_id(url, title),
                        source_url=url,
                        source_channel=self.name,
                        source_tier=self.tier,
                        org=org,
                        title=title,
                        archetype=self._infer_archetype(title),
                        deadline=deadline_parser(body),
                        description=body[:2000],
                        legitimacy_tier=self.default_legitimacy_tier,
                        scanned_at=now,
                    )
                )
            except Exception as exc:
                self.logger.warning("wanted: skip invalid HTML card %r: %s", title, exc)
                continue

        return jobs

    # -- Detail parsing -----------------------------------------------------

    def _parse_detail_html(self, html: str, *, url: str) -> JobRecord | None:
        """Parse a detail (``/wd/<id>``) page into a single JobRecord."""
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.get_text(strip=True) if soup.title else url)[:200]
        body_text = soup.get_text(" ", strip=True)[:5000]

        try:
            return JobRecord(
                id=self._make_id(url, title),
                source_url=url,
                source_channel=self.name,
                source_tier=self.tier,
                org="원티드 기업",
                title=title,
                archetype=self._infer_archetype(title),
                deadline=deadline_parser(body_text) or deadline_parser(title),
                description=body_text,
                raw_html=html[:50_000],
                legitimacy_tier=self.default_legitimacy_tier,
            )
        except Exception as exc:
            self.logger.warning("wanted: bad detail record %r: %s", title, exc)
            return None

    # -- Tiny extractors ----------------------------------------------------

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
