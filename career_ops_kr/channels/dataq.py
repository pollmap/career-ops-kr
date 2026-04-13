"""Dataq channel — 한국데이터산업진흥원 (dataq.or.kr).

Backend: ``requests``. Extracts ADsP / SQLD / DAP exam schedules from the
public notice area and models them as :class:`JobRecord` with
``archetype="CERTIFICATION"``. Returns [] on any failure.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from career_ops_kr.channels.base import BaseChannel, JobRecord, deadline_parser

LANDING_URL = "https://www.dataq.or.kr/www/main.do"
NOTICE_URL = "https://www.dataq.or.kr/www/board/view.do"
from career_ops_kr._constants import DEFAULT_USER_AGENT as USER_AGENT  # noqa: E402


class DataqChannel(BaseChannel):
    """한국데이터산업진흥원 자격검정 일정 scraper."""

    name = "dataq"
    tier = 2
    backend = "requests"
    default_rate_per_minute = 6
    default_legitimacy_tier = "T1"

    def __init__(self, landing_url: str = LANDING_URL) -> None:
        super().__init__()
        self.landing_url = landing_url

    # -- API ----------------------------------------------------------------

    def check(self) -> bool:
        try:
            resp = requests.get(
                self.landing_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
            )
        except requests.RequestException as exc:
            self.logger.warning("dataq check failed: %s", exc)
            return False
        return resp.status_code == 200

    def list_jobs(self, query: dict[str, Any] | None = None) -> list[JobRecord]:
        resp = self._retry(self._get_landing)
        if resp is None or resp.status_code != 200:
            self.logger.warning(
                "dataq: landing fetch failed (status=%s)",
                getattr(resp, "status_code", "n/a"),
            )
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        results: list[JobRecord] = []
        now = datetime.now()
        exam_pat = re.compile(
            r"(ADsP|SQLD|SQLP|DAP|DAsP|빅데이터분석기사)[^\n]{0,80}(접수|시험|발표)[^\n]{0,60}",
        )
        for m in exam_pat.finditer(text):
            title = m.group(0).strip()
            deadline = deadline_parser(title)
            try:
                record = JobRecord(
                    id=self._make_id(self.landing_url, title),
                    source_url=self.landing_url,  # type: ignore[arg-type]
                    source_channel=self.name,
                    source_tier=self.tier,
                    org="한국데이터산업진흥원",
                    title=title[:200],
                    archetype="CERTIFICATION",
                    deadline=deadline,
                    description=title,
                    legitimacy_tier=self.default_legitimacy_tier,
                    scanned_at=now,
                )
            except Exception as exc:
                self.logger.warning("dataq: skip match: %s", exc)
                continue
            results.append(record)

        if not results:
            self.logger.info("dataq: no exam schedule patterns matched.")
        return results

    def get_detail(self, url: str) -> JobRecord | None:
        try:
            resp = self._retry(
                requests.get,
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
            )
        except Exception as exc:
            self.logger.warning("dataq get_detail failed: %s", exc)
            return None
        if resp is None or resp.status_code != 200:
            return None
        return JobRecord(
            id=self._make_id(url, url),
            source_url=url,  # type: ignore[arg-type]
            source_channel=self.name,
            source_tier=self.tier,
            org="한국데이터산업진흥원",
            title=url.rsplit("/", 1)[-1] or "데이터자격검정",
            archetype="CERTIFICATION",
            description=resp.text[:4000],
            raw_html=resp.text,
            legitimacy_tier=self.default_legitimacy_tier,
        )

    # -- internals ----------------------------------------------------------

    def _get_landing(self) -> requests.Response:
        self.logger.info("dataq: GET %s", self.landing_url)
        return requests.get(
            self.landing_url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
