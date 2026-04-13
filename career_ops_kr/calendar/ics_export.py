"""iCalendar (.ics) export for job deadlines and certification exams.

Uses `icalendar` library. All events are Asia/Seoul by default.
Handles missing deadlines gracefully (skip + log).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from icalendar import Alarm, Calendar, Event

logger = logging.getLogger(__name__)

# 자격증 시험 일정 — `config/certifications.yml`에서 로드 (사용자별 커스터마이징)
# 파일이 없으면 빈 리스트 → 자격증 이벤트 없음 (공고 마감일만 ICS에 포함)
def _load_cert_schedule() -> list[dict[str, Any]]:
    try:
        import yaml
        from career_ops_kr.commands._shared import PROJECT_ROOT
        p = PROJECT_ROOT / "config" / "certifications.yml"
        if not p.exists():
            return []
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        items = data.get("certifications") if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        out: list[dict[str, Any]] = []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            raw_date = entry.get("date")
            if not name or not raw_date:
                continue
            if isinstance(raw_date, str):
                try:
                    dt = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
            elif isinstance(raw_date, date):
                dt = raw_date
            else:
                continue
            out.append({
                "name": name,
                "date": dt,
                "category": entry.get("category", "자격증"),
            })
        return out
    except Exception:
        return []


CERT_SCHEDULE: list[dict[str, Any]] = _load_cert_schedule()


def _uid(prefix: str, seed: str) -> str:
    from career_ops_kr._constants import ICS_UID_DOMAIN
    h = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{h}@{ICS_UID_DOMAIN}"


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
            event.add("dtstamp", datetime.now(UTC))
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
            event.add("dtstamp", datetime.now(UTC))
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
