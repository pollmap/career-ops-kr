"""iCalendar (.ics) export for job deadlines and certification exams.

Uses `icalendar` library. All events are Asia/Seoul by default.
Handles missing deadlines gracefully (skip + log).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from icalendar import Alarm, Calendar, Event

logger = logging.getLogger(__name__)

# 찬희 자격증 시험 일정 (2026)
CERT_SCHEDULE: list[dict[str, Any]] = [
    {"name": "ADsP", "date": date(2026, 5, 17), "category": "데이터"},
    {"name": "한국사능력검정", "date": date(2026, 5, 23), "category": "기본자격"},
    {"name": "SQLD", "date": date(2026, 5, 31), "category": "데이터"},
    {"name": "금융투자분석사", "date": date(2026, 7, 12), "category": "금융자격"},
    {"name": "투자자산운용사", "date": date(2026, 8, 23), "category": "금융자격"},
]


def _uid(prefix: str, seed: str) -> str:
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{h}@career-ops-kr.luxon.ai"


def _parse_deadline(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


class CalendarExporter:
    """Generate .ics files for jobs and certifications."""

    def __init__(self, timezone: str = "Asia/Seoul") -> None:
        self.timezone = timezone

    # --------------------------------------------------------------- helpers
    def _new_calendar(self, name: str) -> Calendar:
        cal = Calendar()  # type: ignore[no-untyped-call]
        cal.add("prodid", "-//career-ops-kr//Luxon AI//KR")
        cal.add("version", "2.0")
        cal.add("x-wr-calname", name)
        cal.add("x-wr-timezone", self.timezone)
        return cal

    def _write(self, cal: Calendar, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ics_bytes = cal.to_ical()
        output_path.write_bytes(ics_bytes)
        return output_path

    # --------------------------------------------------------------- jobs
    def from_jobs(self, jobs: list[dict[str, Any]], output_path: Path) -> Path:
        cal = self._new_calendar("career-ops-kr 마감일")
        added = 0
        skipped = 0
        for job in jobs:
            deadline = _parse_deadline(job.get("deadline"))
            if deadline is None:
                skipped += 1
                logger.info("skip job without deadline: %s", job.get("id") or job.get("title"))
                continue

            event = Event()  # type: ignore[no-untyped-call]
            org = job.get("org", "?")
            title = job.get("title", "?")
            archetype = job.get("archetype", "")
            grade = job.get("fit_grade", "")
            url = job.get("url", "")

            event.add("summary", f"[{org}] {title} - 마감")
            event.add("dtstart", deadline)
            event.add("dtend", deadline + timedelta(days=1))
            event.add("dtstamp", datetime.utcnow())
            event.add(
                "description",
                f"URL: {url}\nArchetype: {archetype}\nFit Grade: {grade}",
            )
            if archetype:
                event.add("categories", [archetype])
            seed = str(job.get("id") or f"{org}-{title}-{deadline.isoformat()}")
            event.add("uid", _uid("job", seed))

            # 24h alarm for all
            alarm_24h = Alarm()  # type: ignore[no-untyped-call]
            alarm_24h.add("action", "DISPLAY")
            alarm_24h.add("description", f"D-1 {org} {title}")
            alarm_24h.add("trigger", timedelta(hours=-24))
            event.add_component(alarm_24h)

            # Additional 7-day alarm for grade A
            if str(grade).upper() == "A":
                alarm_7d = Alarm()  # type: ignore[no-untyped-call]
                alarm_7d.add("action", "DISPLAY")
                alarm_7d.add("description", f"D-7 {org} {title}")
                alarm_7d.add("trigger", timedelta(days=-7))
                event.add_component(alarm_7d)

            cal.add_component(event)
            added += 1

        logger.info("CalendarExporter.from_jobs added=%d skipped=%d", added, skipped)
        return self._write(cal, output_path)

    # --------------------------------------------------------------- certs
    def from_certifications(
        self,
        exams: list[dict[str, Any]] | None,
        output_path: Path,
    ) -> Path:
        cal = self._new_calendar("career-ops-kr 자격증 일정")
        schedule = exams if exams else CERT_SCHEDULE

        for item in schedule:
            exam_date = item.get("date")
            if not isinstance(exam_date, date):
                exam_date = _parse_deadline(exam_date)
            if exam_date is None:
                logger.info("skip cert without date: %s", item.get("name"))
                continue

            event = Event()  # type: ignore[no-untyped-call]
            name = item.get("name", "시험")
            category = item.get("category", "자격증")
            event.add("summary", f"[자격증] {name}")
            event.add("dtstart", exam_date)
            event.add("dtend", exam_date + timedelta(days=1))
            event.add("dtstamp", datetime.utcnow())
            event.add("description", f"{category} - {name}")
            event.add("categories", [category])
            event.add("uid", _uid("cert", f"{name}-{exam_date.isoformat()}"))

            alarm = Alarm()  # type: ignore[no-untyped-call]
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"D-7 {name}")
            alarm.add("trigger", timedelta(days=-7))
            event.add_component(alarm)

            cal.add_component(event)

        return self._write(cal, output_path)
