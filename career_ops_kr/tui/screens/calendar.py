"""Upcoming deadlines calendar screen — D-30 timeline view."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from career_ops_kr.storage.sqlite_store import SQLiteStore

DEADLINE_WINDOW_DAYS = 30

GRADE_COLORS = {
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}


def _days_until(deadline: str | None) -> int | None:
    if not deadline:
        return None
    try:
        d = date.fromisoformat(deadline[:10])
    except ValueError:
        return None
    return (d - date.today()).days


class CalendarScreen(Screen[None]):
    """Simple deadline list grouped by D-bucket."""

    BINDINGS = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="calendar-root"):
            yield Static(
                f"[b]마감 일정 (향후 {DEADLINE_WINDOW_DAYS}일)[/b]",
                classes="calendar-title",
            )
            table = DataTable(id="calendar-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("D-", "마감일", "등급", "org", "title", "archetype")
            yield table
            yield Static("", id="calendar-summary", classes="calendar-summary")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _store(self) -> SQLiteStore | None:
        store = getattr(self.app, "store", None)
        return store if isinstance(store, SQLiteStore) else None

    def refresh_data(self) -> None:
        store = self._store()
        if store is None:
            return
        try:
            rows = store.list_upcoming_deadlines(days=DEADLINE_WINDOW_DAYS)
        except Exception as exc:
            self.notify(f"DB 조회 실패: {exc}", severity="error")
            return
        self._populate(rows)

    def _populate(self, rows: list[dict[str, Any]]) -> None:
        table = self.query_one("#calendar-table", DataTable)
        table.clear()
        buckets: dict[str, int] = defaultdict(int)
        for job in rows:
            days = _days_until(job.get("deadline"))
            if days is None:
                continue
            d_tag = f"D-{days}"
            if days <= 1:
                buckets["🔥 긴급 (D-1)"] += 1
            elif days <= 3:
                buckets["⚠️ 임박 (D-3)"] += 1
            elif days <= 7:
                buckets["📌 이번 주 (D-7)"] += 1
            else:
                buckets["🗓  향후 (D-30)"] += 1

            grade = str(job.get("fit_grade") or "-")
            color = GRADE_COLORS.get(grade, "white")
            table.add_row(
                d_tag,
                str(job.get("deadline") or "")[:10],
                f"[{color}]{grade}[/{color}]",
                str(job.get("org") or "")[:18],
                str(job.get("title") or "")[:40],
                str(job.get("archetype") or "-")[:10],
            )
        summary_lines = [f"[dim]총 {len(rows)}건 · 마감 임박 순[/dim]"]
        for label in (
            "🔥 긴급 (D-1)",
            "⚠️ 임박 (D-3)",
            "📌 이번 주 (D-7)",
            "🗓  향후 (D-30)",
        ):
            if buckets.get(label):
                summary_lines.append(f"{label}: {buckets[label]}")
        self.query_one("#calendar-summary", Static).update("  ·  ".join(summary_lines))
