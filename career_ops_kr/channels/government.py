"""Config-driven government channel — 여러 정부기관을 하나의 채널로 통합.

기존 10개 개별 파일(nis.py, police.py, mnd.py 등)을 대체.
config/government_portals.yml에서 URL/org/키워드 로드.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

USER_AGENT = "career-ops-kr/0.2 (+https://github.com/pollmap/career-ops-kr)"

_DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "government_portals.yml"

# Fallback config when YAML doesn't exist
_BUILTIN_PORTALS: list[dict[str, Any]] = [
    {"name": "nis", "org": "국가정보원", "url": "https://career.nis.go.kr:4017/", "tier": 1, "legitimacy": "T1"},
    {"name": "police", "org": "경찰청", "url": "https://gosi.police.go.kr/", "tier": 1, "legitimacy": "T1"},
    {"name": "mnd", "org": "국방부", "url": "https://www.mnd.go.kr/mbshome/mbs/mnd/subview.jsp?id=mnd_010701000000", "tier": 1, "legitimacy": "T1"},
    {"name": "mofa", "org": "외교부", "url": "https://www.mofa.go.kr/www/brd/m_4080/list.do", "tier": 1, "legitimacy": "T1"},
    {"name": "customs", "org": "관세청", "url": "https://www.customs.go.kr/kcs/ad/brd/list.do?mi=2871&bbsId=BBSMSTR_000000000028", "tier": 1, "legitimacy": "T1"},
    {"name": "fsc", "org": "금융위원회", "url": "https://www.fsc.go.kr/no010201", "tier": 1, "legitimacy": "T1"},
    {"name": "fss", "org": "금융감독원", "url": "https://www.fss.or.kr/fss/main/sub1Contents.do?menuNo=200600", "tier": 1, "legitimacy": "T1"},
    {"name": "dapa", "org": "방위사업청", "url": "https://www.dapa.go.kr/dapa/na/ntt/selectNttList.do?bbsId=326&menuId=678", "tier": 1, "legitimacy": "T1"},
    {"name": "kisa", "org": "한국인터넷진흥원", "url": "https://www.kisa.or.kr/401", "tier": 2, "legitimacy": "T2"},
    {"name": "gojobs", "org": "나라일터", "url": "https://gojobs.go.kr/apmAllList.do", "tier": 1, "legitimacy": "T1"},
]

_KEYWORDS = ("채용", "공고", "모집", "인턴", "신입", "경력", "지원", "recruit", "career")


def _load_portals(config_path: Path | None = None) -> list[dict[str, Any]]:
    """Load government portals from YAML or fallback to builtins."""
    path = config_path or _DEFAULT_CONFIG
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data.get("portals", _BUILTIN_PORTALS)
        except Exception:
            pass
    return _BUILTIN_PORTALS


class GovernmentChannel(BaseChannel):
    """Config-driven multi-government-agency channel."""

    name = "government"
    tier = 1
    backend = "requests"
    default_rate_per_minute = 20
    default_legitimacy_tier = "T1"

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__()
        self._portals = _load_portals(config_path)

    def check(self) -> bool:
        return len(self._portals) > 0

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        all_jobs: list[JobRecord] = []
        for portal in self._portals:
            try:
                jobs = self._scrape_portal(portal)
                all_jobs.extend(jobs)
                if jobs:
                    self.logger.info("government/%s: %d jobs", portal["name"], len(jobs))
            except Exception as exc:
                self.logger.warning("government/%s failed: %s", portal.get("name", "?"), exc)
        return all_jobs

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            resp = self._retry(
                requests.get, url,
                headers={"User-Agent": USER_AGENT}, timeout=15,
            )
        except Exception:
            return None
        if resp is None or resp.status_code != 200:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,
            source_channel=self.name,
            source_tier=self.tier,
            org="(정부기관)",
            title="정부 채용",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    def _scrape_portal(self, portal: dict[str, Any]) -> list[JobRecord]:
        """Scrape a single government portal."""
        url = portal["url"]
        org = portal["org"]
        tier_val = portal.get("tier", 1)
        legitimacy = portal.get("legitimacy", "T1")
        base = url.split("/", 3)[:3]
        base_url = "/".join(base) if len(base) >= 3 else url

        resp = self._retry(
            requests.get, url,
            headers={"User-Agent": USER_AGENT}, timeout=15,
        )
        if resp is None or resp.status_code != 200:
            self.logger.warning("government/%s: HTTP %s", portal["name"], getattr(resp, "status_code", "?"))
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[JobRecord] = []
        now = datetime.now()
        seen: set[str] = set()

        # Strategy 1: table/list rows
        for row in soup.select(
            "table tr, .board-list tr, .boardList tr, ul.list li, "
            ".bbs_list tr, .notice-list li, .recruit-item"
        ):
            title = row.get_text(" ", strip=True)
            if not title or len(title) < 4 or len(title) > 300:
                continue
            link = row.find("a") if hasattr(row, "find") else None
            href = str(link.get("href", "")) if link else ""
            if not href or href.startswith("#") or href.lower().startswith("javascript"):
                href = url
            if href.startswith("/"):
                href = base_url + href
            if "://" not in href or href in seen:
                continue
            seen.add(href)
            try:
                results.append(JobRecord(
                    id=self._make_id(href, title[:120]),
                    source_url=href, source_channel=f"gov_{portal['name']}",
                    source_tier=tier_val, org=org, title=title[:200],
                    deadline=deadline_parser(title), description=title,
                    legitimacy_tier=legitimacy, scanned_at=now,
                ))
            except Exception:
                continue

        # Strategy 2: keyword anchor fallback
        if not results:
            for anchor in soup.find_all("a"):
                text = (anchor.get_text(" ", strip=True) or "").strip()
                href = anchor.get("href") or ""
                if not text or len(text) < 4 or not href:
                    continue
                if href.startswith("#") or href.lower().startswith("javascript"):
                    continue
                if not any(kw in text for kw in _KEYWORDS):
                    continue
                if href.startswith("/"):
                    href = base_url + href
                if "://" not in href or href in seen:
                    continue
                seen.add(href)
                try:
                    results.append(JobRecord(
                        id=self._make_id(href, text[:120]),
                        source_url=href, source_channel=f"gov_{portal['name']}",
                        source_tier=tier_val, org=org, title=text[:200],
                        deadline=deadline_parser(text), description=text,
                        legitimacy_tier=legitimacy, scanned_at=now,
                    ))
                except Exception:
                    continue
                if len(results) >= 30:
                    break

        return results
