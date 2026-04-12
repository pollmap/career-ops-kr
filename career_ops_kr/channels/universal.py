"""Universal channel — config/institutions.yml 기반 전체 기관 크롤링.

194+ 금융기관/공공기관의 채용 페이지를 하나의 채널에서 일괄 크롤링.
requests 실패 시 Scrapling auto-fallback.

Design:
    - institutions.yml에 기관명+URL+적합도+섹터 저장
    - list_jobs()에서 URL이 있는 기관만 크롤링
    - grade 필터링으로 S/A등급만 우선 스캔 가능
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

logger = logging.getLogger(__name__)

USER_AGENT = "career-ops-kr/0.2 (+https://github.com/pollmap/career-ops-kr)"
CONFIG_PATH = Path.cwd() / "config" / "institutions.yml"


def _load_institutions(path: Path | None = None) -> list[dict[str, Any]]:
    """Load institutions from YAML config."""
    target = path or CONFIG_PATH
    if not target.exists():
        logger.warning("institutions.yml not found at %s", target)
        return []
    try:
        import yaml
        with open(target, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("institutions", [])
    except Exception as exc:
        logger.error("Failed to load institutions.yml: %s", exc)
        return []


def _fetch_career_page(url: str) -> str | None:
    """Fetch career page HTML. Returns None on failure."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass

    # Scrapling fallback
    try:
        from career_ops_kr.channels._scrapling_base import SCRAPLING_AVAILABLE, ScraplingChannel
        if SCRAPLING_AVAILABLE:
            sc = ScraplingChannel(name="universal_fallback")
            page_data = sc.fetch_page(url)
            if page_data and page_data.get("html"):
                return page_data["html"]
    except Exception:
        pass

    return None


def _extract_jobs_from_html(
    html: str,
    org: str,
    career_url: str,
    tier: int,
    legitimacy: str,
) -> list[JobRecord]:
    """Parse HTML for job-related anchors and return JobRecords."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[JobRecord] = []
    now = datetime.now()
    seen: set[str] = set()

    # Determine base URL for relative hrefs
    parts = career_url.split("/", 3)
    base = "/".join(parts[:3]) if len(parts) >= 3 else career_url

    # Strategy 1: table rows / list items (board patterns)
    for row in soup.select(
        "table tr, .board-list tr, .boardList tr, ul.list li, "
        ".recruit-item, .notice-list li, .bbs_list tr, .job-list li, "
        ".list-body .item, .recruit-list li, .board_list tr"
    ):
        title = row.get_text(" ", strip=True)
        if not title or len(title) < 4 or len(title) > 300:
            continue
        link = row.find("a") if hasattr(row, "find") else None
        href = str(link.get("href", "")) if link else ""
        if not href or href.startswith("#") or href.lower().startswith("javascript"):
            href = career_url
        if href.startswith("/"):
            href = base + href
        if "://" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        try:
            results.append(JobRecord(
                id=BaseChannel._make_id(href, title[:120]),
                source_url=href,
                source_channel="universal",
                source_tier=tier,
                org=org,
                title=title[:200],
                deadline=deadline_parser(title),
                description=title,
                legitimacy_tier=legitimacy,
                scanned_at=now,
            ))
        except Exception:
            continue

    # Strategy 2: keyword anchor fallback
    if not results:
        keywords = ("채용", "공고", "모집", "인턴", "신입", "경력", "지원", "recruit", "career", "hiring")
        for anchor in soup.find_all("a"):
            text = (anchor.get_text(" ", strip=True) or "").strip()
            href = anchor.get("href") or ""
            if not text or len(text) < 4 or not href:
                continue
            if href.startswith("#") or href.lower().startswith("javascript"):
                continue
            if not any(kw in text.lower() for kw in keywords):
                continue
            if href.startswith("/"):
                href = base + href
            if "://" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)
            try:
                results.append(JobRecord(
                    id=BaseChannel._make_id(href, text[:120]),
                    source_url=href,
                    source_channel="universal",
                    source_tier=tier,
                    org=org,
                    title=text[:200],
                    deadline=deadline_parser(text),
                    description=text,
                    legitimacy_tier=legitimacy,
                    scanned_at=now,
                ))
            except Exception:
                continue
            if len(results) >= 30:
                break

    return results


class UniversalChannel(BaseChannel):
    """institutions.yml 기반 전체 기관 크롤러.

    Attributes:
        grade_filter: S/A/B/C/D 중 스캔할 등급 (None=전체)
        max_concurrency: 동시 크롤링 수
    """

    name = "universal"
    tier = 1
    backend = "requests+scrapling"
    default_rate_per_minute = 30
    default_legitimacy_tier = "T1"

    def __init__(
        self,
        grade_filter: str | None = None,
        max_concurrency: int = 6,
        config_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.grade_filter = grade_filter
        self.max_concurrency = max_concurrency
        self._config_path = config_path
        self._institutions: list[dict[str, Any]] = []

    def _load(self) -> list[dict[str, Any]]:
        if not self._institutions:
            self._institutions = _load_institutions(self._config_path)
        return self._institutions

    def _filtered(self) -> list[dict[str, Any]]:
        """Return institutions filtered by grade and having a career_url."""
        insts = self._load()
        filtered = [i for i in insts if i.get("career_url")]
        if self.grade_filter:
            grades = set(self.grade_filter.upper().split(","))
            filtered = [i for i in filtered if i.get("grade", "").upper() in grades]
        return filtered

    def check(self) -> bool:
        return len(self._filtered()) > 0

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        targets = self._filtered()
        if not targets:
            self.logger.info("universal: no institutions with career_url (grade=%s)", self.grade_filter)
            return []

        all_jobs: list[JobRecord] = []

        def _scan_institution(inst: dict[str, Any]) -> list[JobRecord]:
            url = inst["career_url"]
            org = inst["name"]
            grade = inst.get("grade", "C")
            tier_val = 1 if grade in ("S", "A") else 2 if grade == "B" else 3
            legit = "T1" if "공제" in inst.get("sector", "") or "정책" in inst.get("sector", "") else "T3"

            html = _fetch_career_page(url)
            if not html:
                self.logger.debug("universal: %s fetch failed", org)
                return []

            return _extract_jobs_from_html(html, org, url, tier_val, legit)

        with ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            futures = {pool.submit(_scan_institution, inst): inst["name"] for inst in targets}
            for future in as_completed(futures):
                org_name = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    if jobs:
                        self.logger.info("universal: %s → %d jobs", org_name, len(jobs))
                except Exception as exc:
                    self.logger.warning("universal: %s error: %s", org_name, exc)

        return all_jobs

    def get_detail(self, url: str) -> JobRecord | None:
        html = _fetch_career_page(url)
        if not html:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,
            source_channel=self.name,
            source_tier=self.tier,
            org="(universal)",
            title="채용 상세",
            description=html[:4000],
            raw_html=html,
            legitimacy_tier=self.default_legitimacy_tier,
        )
