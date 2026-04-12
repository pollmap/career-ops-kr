"""Textual application root for career-ops-kr dashboard.

This module is only importable when the optional ``textual`` extra is
installed. ``career_ops_kr.tui.__init__`` guards the import so missing
textual does not break the rest of the package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from career_ops_kr.storage.sqlite_store import SQLiteStore
from career_ops_kr.tui.screens import (
    CalendarScreen,
    DashboardScreen,
    JobDetailScreen,
    JobsListScreen,
    PatternsScreen,
)

DEFAULT_DB_PATH = Path("data") / "jobs.db"


class HelpScreen(Screen[None]):  # type: ignore[misc]
    """Modal-ish help overlay listing keybindings."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "닫기", show=True),
        Binding("q", "app.pop_screen", "닫기", show=False),
        Binding("?", "app.pop_screen", "닫기", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="help-body"):
            yield Static("[b]career-ops-kr 키 바인딩[/b]\n", classes="help-title")
            yield Static(
                "[cyan]d[/cyan]  대시보드 (홈)\n"
                "[cyan]j[/cyan]  공고 목록\n"
                "[cyan]c[/cyan]  마감 캘린더\n"
                "[cyan]p[/cyan]  패턴 분석\n"
                "[cyan]r[/cyan]  현재 화면 새로고침\n"
                "[cyan]s[/cyan]  스캔 안내 (CLI 명령 표시)\n"
                "[cyan]?[/cyan]  도움말 열기/닫기\n"
                "[cyan]q[/cyan]  종료\n\n"
                "[dim]공고 목록에서 Enter → 상세 화면[/dim]\n"
                "[dim]상세 화면에서 a(지원) / w(워치) / x(거절)[/dim]",
                classes="help-body",
            )
        yield Footer()


class MissingDbScreen(Screen[None]):  # type: ignore[misc]
    """Shown at startup when the SQLite database file does not exist."""

    BINDINGS = [
        Binding("q", "app.quit", "종료", show=True),
    ]

    def __init__(self, db_path: Path) -> None:
        super().__init__()
        self._db_path = db_path

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="missing-db"):
            yield Static("[b red]jobs.db 가 존재하지 않습니다[/b red]\n")
            yield Static(
                f"경로: [yellow]{self._db_path}[/yellow]\n\n"
                "먼저 아래 명령으로 온보딩 + 첫 스캔을 수행하세요:\n\n"
                "  [cyan]career-ops init[/cyan]\n"
                "  [cyan]career-ops scan --all[/cyan]\n\n"
                "[dim]q 를 눌러 종료.[/dim]"
            )
        yield Footer()


class CareerOpsApp(App[None]):  # type: ignore[misc]
    """Textual app root — dashboard shell for career-ops-kr."""

    CSS_PATH = "styles.tcss"
    TITLE = "career-ops-kr dashboard v0.2"
    SUB_TITLE = "찬희 — 구직 파이프라인"

    BINDINGS = [
        Binding("q", "quit", "종료"),
        Binding("r", "refresh", "새로고침"),
        Binding("s", "scan_hint", "스캔"),
        Binding("d", "goto_dashboard", "대시보드"),
        Binding("j", "goto_jobs", "공고 목록"),
        Binding("c", "goto_calendar", "캘린더"),
        Binding("p", "goto_patterns", "패턴"),
        Binding("question_mark", "help", "도움말"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "jobs": JobsListScreen,
        "calendar": CalendarScreen,
        "patterns": PatternsScreen,
        "help": HelpScreen,
    }

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.db_path: Path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.store: SQLiteStore | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        if not self.db_path.exists():
            self.push_screen(MissingDbScreen(self.db_path))
            return
        # SQLiteStore will create parent dir + idempotent schema
        self.store = SQLiteStore(self.db_path)
        self.push_screen(DashboardScreen())

    # ------------------------------------------------------------------
    # Helpers consumed by screens
    # ------------------------------------------------------------------

    def require_store(self) -> SQLiteStore:
        if self.store is None:
            raise RuntimeError("SQLiteStore not initialized — jobs.db missing?")
        return self.store

    def open_job_detail(self, job_id: str) -> None:
        """Push a JobDetailScreen for the given job id."""
        self.push_screen(JobDetailScreen(job_id))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        screen = self.screen
        refresh = getattr(screen, "refresh_data", None)
        if callable(refresh):
            refresh()
        else:
            self.notify("현재 화면은 새로고침할 데이터가 없습니다.", severity="information")

    def action_scan_hint(self) -> None:
        self.notify(
            "터미널에서 실행: career-ops scan --all",
            title="스캔",
            severity="information",
            timeout=5.0,
        )

    def action_goto_dashboard(self) -> None:
        self._switch_to("dashboard", DashboardScreen)

    def action_goto_jobs(self) -> None:
        self._switch_to("jobs", JobsListScreen)

    def action_goto_calendar(self) -> None:
        self._switch_to("calendar", CalendarScreen)

    def action_goto_patterns(self) -> None:
        self._switch_to("patterns", PatternsScreen)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _switch_to(self, name: str, screen_cls: type[Screen[Any]]) -> None:
        if self.store is None:
            # Still waiting on missing-db screen.
            return
        # Always create a fresh instance so DB-backed widgets reload.
        self.push_screen(screen_cls())


def run_tui(db_path: Path | None = None) -> None:
    """Entry point used by ``career-ops ui`` CLI command."""
    app = CareerOpsApp(db_path=db_path)
    app.run()
