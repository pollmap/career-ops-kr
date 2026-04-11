"""Discord webhook pusher for career-ops-kr.

Rate-limited (max 5 msg / 60s). Log-only when webhook URL is not configured.
Never fabricates URLs. Uses httpx.
"""

from __future__ import annotations

import contextlib
import logging
import os
import time
from collections import deque
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_SEC = 60.0

GRADE_COLORS: dict[str, int] = {
    "A": 0x2ECC71,  # green
    "B": 0x3498DB,  # blue
    "C": 0xF1C40F,  # yellow
    "D": 0xE67E22,  # orange
    "F": 0xE74C3C,  # red
}


class DiscordNotifier:
    """Discord webhook client.

    If `webhook_url` is None and `DISCORD_WEBHOOK_URL` env var is empty,
    operates in log-only mode. NEVER fabricates a URL.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url: str | None = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL") or None
        self._send_times: deque[float] = deque()
        self._client = httpx.Client(timeout=10.0)

        if not self.webhook_url:
            logger.info(
                "DiscordNotifier: webhook not configured. "
                "Set env DISCORD_WEBHOOK_URL or config/profile.yml > discord.webhook_url. "
                "Running in log-only mode."
            )

    # ------------------------------------------------------------------ rate
    def _rate_check(self) -> bool:
        now = time.monotonic()
        cutoff = now - RATE_LIMIT_WINDOW_SEC
        while self._send_times and self._send_times[0] < cutoff:
            self._send_times.popleft()
        if len(self._send_times) >= RATE_LIMIT_MAX:
            logger.warning("DiscordNotifier rate limit hit (5/60s), dropping message")
            return False
        self._send_times.append(now)
        return True

    # ------------------------------------------------------------------ send
    def _send(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.info("DiscordNotifier log-only: %s", payload.get("content") or payload)
            return False
        if not self._rate_check():
            return False
        try:
            resp = self._client.post(self.webhook_url, json=payload)
            if resp.status_code >= 400:
                logger.warning("Discord webhook non-2xx: %s %s", resp.status_code, resp.text[:200])
                return False
            return True
        except httpx.HTTPError as exc:
            logger.warning("Discord webhook failed: %s", exc)
            return False

    # ------------------------------------------------------------------ public
    def test_connection(self) -> bool:
        if not self.webhook_url:
            return False
        return self._send({"content": "career-ops-kr test ping"})

    def notify_new_jobs(self, jobs: list[dict[str, Any]], grade_filter: str = "A") -> bool:
        filtered = [j for j in jobs if str(j.get("fit_grade", "")).upper() >= grade_filter.upper()]
        if not filtered:
            logger.info("notify_new_jobs: no jobs above %s", grade_filter)
            return False

        fields = []
        for job in filtered[:10]:
            org = job.get("org", "?")
            title = job.get("title", "?")
            grade = job.get("fit_grade", "?")
            deadline = job.get("deadline", "?")
            fields.append(
                {
                    "name": f"[{grade}] {org}",
                    "value": f"{title}\n마감: {deadline}\n{job.get('url', '')}",
                    "inline": False,
                }
            )

        embed = {
            "title": f"career-ops-kr — {grade_filter}급 신규 공고 {len(filtered)}건",
            "color": GRADE_COLORS.get(grade_filter.upper(), 0x95A5A6),
            "fields": fields,
        }
        return self._send({"embeds": [embed]})

    def notify_deadline(self, job: dict[str, Any], days_left: int) -> bool:
        content = (
            f"D-{days_left} [{job.get('org', '?')}] {job.get('title', '?')}\n{job.get('url', '')}"
        )
        return self._send({"content": content})

    def notify_batch_summary(self, scan_results: dict[str, Any]) -> bool:
        lines = ["career-ops-kr 일일 스캔 리포트"]
        for site, stats in scan_results.items():
            lines.append(f"- {site}: {stats}")
        return self._send({"content": "\n".join(lines)})

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._client.close()
