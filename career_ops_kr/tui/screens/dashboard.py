"""Home dashboard screen — overview widgets read from SQLiteStore.

Layout (3x2 grid):
    +------------------+------------------+------------------+
    |  총 공고/분류    |  등급 분포       |  최근 스캔 로그  |
    +------------------+------------------+------------------+
    |  임박 마감 (D-7) |  아키타입 분포   |  퀵 액션 힌트    |
    +------------------+------------------+------------------+

The screen auto-refreshes every 60 seconds via
``textual.timer.Timer`` (``set_interval``) and also refreshes on
``action_refresh`` when the user hits ``r``.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from career_ops_kr.storage.sqlite_store import SQLiteStore

REFRESH_INTERVAL_SEC = 60.0
DEADLINE_WINDOW_DAYS = 7


GRADE_COLORS = {
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}

ARCHETYPES = (
    "블록체인",
    "디지털자산",
    "금융IT",
    "리서치",
    "핀테크",
    "공공",
)


def _sparkline(counts: list[int], width: int = 20) -> str:
    if not counts or max(counts) == 0:
        return "·" * width
    blocks = "▁▂▃▄▅▆▇█"
    peak = max(counts)
    return "".join(blocks[min(len(blocks) - 1, int(c / peak * (len(blocks) - 1)))] for c in counts)


def _days_until(deadline: str | None) -> int | None:
    if not deadline:
        return None
    try:
        d = date.fromisoformat(deadline[:10])
    except ValueError:
        return None
    return (d - date.today()).days


class DashboardScreen(Screen[None]):  # type: ignore[misc]
    """Overview home screen for career-ops-kr TUI."""

    BINDINGS: list[Any] = []  # app-level bindings handle navigation

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="dash-grid"):
            yield Static("로딩 중…", id="cell-totals", classes="dash-cell")
            yield Static("로딩 중…", id="cell-grades", classes="dash-cell")
            yield Static("로딩 중…", id="cell-scans", classes="dash-cell")
            yield Static("로딩 중…", id="cell-deadlines", classes="dash-cell")
            yield Static("로딩 중…", id="cell-archetype", classes="dash-cell")
            yield Static(
                "[b]퀵 액션[/b]\n\n"
                "[cyan]s[/cyan] 스캔 안내\n"
                "[cyan]j[/cyan] 공고 목록\n"
                "[cyan]c[/cyan] 마감 캘린더\n"
                "[cyan]r[/cyan] 새로고침\n"
                "[cyan]?[/cyan] 도움말",
                id="cell-actions",
                classes="dash-cell",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_data()
        self.set_interval(REFRESH_INTERVAL_SEC, self.refresh_data, pause=False)

    # ------------------------------------------------------------------
    # Data loading — direct synchronous SQLite calls. The store is
    # local-file SQLite and queries are indexed + tiny (<1000 rows) so
    # blocking the event loop is acceptable. Switching to a worker is
    # trivial later.
    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        store = self._store()
        if store is None:
            return
        try:
            stats = store.get_stats()
            upcoming = store.list_upcoming_deadlines(days=DEADLINE_WINDOW_DAYS)
            archetype_counts = self._archetype_counts(store)
        except Exception as exc:
            self.notify(f"DB 조회 실패: {exc}", severity="error", timeout=5.0)
            return

        self._render_totals(stats)
        self._render_grades(stats)
        self._render_scans(stats)
        self._render_deadlines(upcoming)
        self._render_archetype(archetype_counts, stats)

    def _store(self) -> SQLiteStore | None:
        store = getattr(self.app, "store", None)
        return store if isinstance(store, SQLiteStore) else None

    def _archetype_counts(self, store: SQLiteStore) -> Counter[str]:
        """Pull archetype distribution via a dedicated lightweight query."""
        with store._connect() as conn:
            rows = conn.execute(
                "SELECT archetype, COUNT(*) AS n FROM jobs GROUP BY archetype"
            ).fetchall()
        return Counter({(r["archetype"] or "미분류"): int(r["n"]) for r in rows})

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_totals(self, stats: dict[str, Any]) -> None:
        by_status = stats.get("by_status", {}) or {}
        total = int(stats.get("total", 0))
        inbox = int(by_status.get("inbox", 0))
        eligible = int(by_status.get("eligible", 0))
        applied = int(by_status.get("applied", 0))
        rejected = int(by_status.get("rejected", 0))
        body = (
            "[b]총 공고[/b]\n"
            f"[b cyan]{total:>4d}[/b cyan] 건\n\n"
            f"  inbox    {inbox:>4d}\n"
            f"  eligible {eligible:>4d}\n"
            f"  applied  {applied:>4d}\n"
            f"  rejected {rejected:>4d}\n"
        )
        self.query_one("#cell-totals", Static).update(body)

    def _render_grades(self, stats: dict[str, Any]) -> None:
        by_grade = stats.get("by_grade", {}) or {}
        lines = ["[b]등급 분포[/b]", ""]
        for grade in ("A", "B", "C", "D", "F"):
            count = int(by_grade.get(grade, 0))
            color = GRADE_COLORS.get(grade, "white")
            bar = "█" * min(count, 20) if count else "·"
            lines.append(f"[{color}]{grade}[/{color}] {bar} {count}")
        ungraded = int(by_grade.get("ungraded", 0))
        if ungraded:
            lines.append(f"[dim]ungraded {ungraded}[/dim]")
        self.query_one("#cell-grades", Static).update("\n".join(lines))

    def _render_scans(self, stats: dict[str, Any]) -> None:
        scans = stats.get("recent_scans") or []
        lines = ["[b]최근 스캔 로그[/b]", ""]
        if not scans:
            lines.append("[dim](아직 스캔 기록 없음)[/dim]")
            lines.append("[dim]career-ops scan --all 실행[/dim]")
        else:
            for scan in scans[:5]:
                ts = str(scan.get("timestamp", ""))[:16].replace("T", " ")
                channel = str(scan.get("channel", "?"))[:14]
                count = int(scan.get("count", 0))
                lines.append(f"{ts}  {channel:<14} {count:>4d}")
            counts = [int(s.get("count", 0)) for s in scans[:10]]
            lines.append("")
            lines.append("[dim]spark: " + _sparkline(list(reversed(counts))) + "[/dim]")
        self.query_one("#cell-scans", Static).update("\n".join(lines))

    def _render_deadlines(self, upcoming: list[dict[str, Any]]) -> None:
        lines = [f"[b]임박 마감 (D-{DEADLINE_WINDOW_DAYS})[/b]", ""]
        if not upcoming:
            lines.append("[dim](임박 마감 없음)[/dim]")
        else:
            for job in upcoming[:5]:
                days = _days_until(job.get("deadline"))
                d_tag = f"D-{days}" if days is not None and days >= 0 else "D?"
                org = str(job.get("org", "?"))[:10]
                title = str(job.get("title", "?"))[:22]
                grade = str(job.get("fit_grade") or "-")
                color = GRADE_COLORS.get(grade, "white")
                lines.append(f"[{color}]{grade}[/{color}] {d_tag:<5} {org:<10} {title}")
        self.query_one("#cell-deadlines", Static).update("\n".join(lines))

    def _render_archetype(self, counts: Counter[str], stats: dict[str, Any]) -> None:
        total = int(stats.get("total", 0)) or 1
        lines = ["[b]아키타입 분포[/b]", ""]
        for arch in ARCHETYPES:
            n = counts.get(arch, 0)
            pct = n / total * 100
            bar = "▇" * int(pct / 5) if pct else "·"
            lines.append(f"{arch:<7} {bar} {n:>3d} ({pct:4.1f}%)")
        leftover = sum(counts.values()) - sum(counts.get(a, 0) for a in ARCHETYPES)
        if leftover > 0:
            lines.append(f"[dim]기타 {leftover}[/dim]")
        self.query_one("#cell-archetype", Static).update("\n".join(lines))
