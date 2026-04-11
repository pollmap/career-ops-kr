"""Jobs list screen — searchable, filterable DataTable of jobs."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Select, Static
from textual.widgets.data_table import RowKey

from career_ops_kr.storage.sqlite_store import SQLiteStore

GRADE_CHOICES: tuple[tuple[str, str], ...] = (
    ("All", ""),
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("F", "F"),
)

STATUS_CHOICES: tuple[tuple[str, str], ...] = (
    ("All", ""),
    ("inbox", "inbox"),
    ("eligible", "eligible"),
    ("applied", "applied"),
    ("rejected", "rejected"),
    ("watching", "watching"),
)

ARCHETYPE_CHOICES: tuple[tuple[str, str], ...] = (
    ("All", ""),
    ("블록체인", "블록체인"),
    ("디지털자산", "디지털자산"),
    ("금융IT", "금융IT"),
    ("리서치", "리서치"),
    ("핀테크", "핀테크"),
    ("공공", "공공"),
)

GRADE_COLORS = {
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}


class JobsListScreen(Screen[None]):  # type: ignore[misc]
    """Scrollable DataTable of jobs with filter + search bar."""

    BINDINGS = [
        Binding("enter", "open_detail", "상세"),
        Binding("/", "focus_search", "검색"),
        Binding("escape", "clear_search", "검색 지우기", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[dict[str, Any]] = []
        self._row_ids: dict[RowKey, str] = {}
        self._filter_grade: str = ""
        self._filter_status: str = ""
        self._filter_archetype: str = ""
        self._search: str = ""

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="jobs-root"):
            with Horizontal(id="jobs-filters"):
                yield Input(placeholder="검색 (org/title/description)", id="jobs-search")
                yield Select(GRADE_CHOICES, id="jobs-grade", value="", prompt="grade")
                yield Select(STATUS_CHOICES, id="jobs-status", value="", prompt="status")
                yield Select(ARCHETYPE_CHOICES, id="jobs-archetype", value="", prompt="archetype")
            table = DataTable(id="jobs-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("grade", "arch", "org", "title", "deadline", "status", "tier")
            yield table
            yield Static("", id="jobs-count", classes="jobs-footer")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()

    # ------------------------------------------------------------------
    # Data pipeline
    # ------------------------------------------------------------------

    def _store(self) -> SQLiteStore | None:
        store = getattr(self.app, "store", None)
        return store if isinstance(store, SQLiteStore) else None

    def refresh_data(self) -> None:
        store = self._store()
        if store is None:
            return
        try:
            rows = self._query(store)
        except Exception as exc:
            self.notify(f"DB 조회 실패: {exc}", severity="error")
            return
        self._rows = rows
        self._repopulate()

    def _query(self, store: SQLiteStore) -> list[dict[str, Any]]:
        if self._search:
            rows = store.search(
                self._search,
                archetype=self._filter_archetype or None,
            )
        else:
            with store._connect() as conn:
                where: list[str] = []
                params: list[Any] = []
                if self._filter_archetype:
                    where.append("archetype = ?")
                    params.append(self._filter_archetype)
                if self._filter_grade:
                    where.append("fit_grade = ?")
                    params.append(self._filter_grade)
                if self._filter_status:
                    where.append("status = ?")
                    params.append(self._filter_status)
                sql = "SELECT * FROM jobs"
                if where:
                    sql += " WHERE " + " AND ".join(where)
                sql += (
                    " ORDER BY "
                    "CASE fit_grade WHEN 'A' THEN 0 WHEN 'B' THEN 1 WHEN 'C' THEN 2 "
                    "WHEN 'D' THEN 3 WHEN 'F' THEN 4 ELSE 5 END ASC, "
                    "deadline ASC LIMIT 500"
                )
                rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
        # Post-filter for grade/status when we went through .search()
        if self._search:
            if self._filter_grade:
                rows = [r for r in rows if r.get("fit_grade") == self._filter_grade]
            if self._filter_status:
                rows = [r for r in rows if r.get("status") == self._filter_status]
        return rows

    def _repopulate(self) -> None:
        table = self.query_one("#jobs-table", DataTable)
        table.clear()
        self._row_ids.clear()
        for job in self._rows:
            grade = str(job.get("fit_grade") or "-")
            color = GRADE_COLORS.get(grade, "white")
            row_key = table.add_row(
                f"[{color}]{grade}[/{color}]",
                str(job.get("archetype") or "-")[:8],
                str(job.get("org") or "")[:18],
                str(job.get("title") or "")[:40],
                str(job.get("deadline") or "")[:10],
                str(job.get("status") or "inbox"),
                f"T{int(job.get('source_tier', 5))}",
            )
            self._row_ids[row_key] = str(job.get("id", ""))
        counter = self.query_one("#jobs-count", Static)
        counter.update(f"[dim]총 {len(self._rows)}건 (필터 적용 후)[/dim]")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "jobs-search":
            self._search = event.value.strip()
            self.refresh_data()

    def on_select_changed(self, event: Select.Changed) -> None:
        value = "" if event.value is Select.BLANK else str(event.value)
        if event.select.id == "jobs-grade":
            self._filter_grade = value
        elif event.select.id == "jobs-status":
            self._filter_status = value
        elif event.select.id == "jobs-archetype":
            self._filter_archetype = value
        self.refresh_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        job_id = self._row_ids.get(event.row_key)
        if job_id:
            open_detail = getattr(self.app, "open_job_detail", None)
            if callable(open_detail):
                open_detail(job_id)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_open_detail(self) -> None:
        table = self.query_one("#jobs-table", DataTable)
        if table.row_count == 0:
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        job_id = self._row_ids.get(row_key)
        if job_id and hasattr(self.app, "open_job_detail"):
            self.app.open_job_detail(job_id)

    def action_focus_search(self) -> None:
        self.query_one("#jobs-search", Input).focus()

    def action_clear_search(self) -> None:
        inp = self.query_one("#jobs-search", Input)
        inp.value = ""
        self._search = ""
        self.refresh_data()
