"""Patterns analysis screen — rejection/application statistics."""

from __future__ import annotations

from collections import Counter
from typing import Any

from textual.app import ComposeResult
from textual.containers import Grid, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from career_ops_kr.storage.sqlite_store import SQLiteStore

GRADE_COLORS = {
    "A": "green",
    "B": "cyan",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}

STATUS_LABELS = {
    "inbox": "📥 inbox",
    "applying": "📝 applying",
    "graded": "✅ graded",
    "rejected": "❌ rejected",
    "archived": "📦 archived",
}


def _bar(count: int, total: int, width: int = 20) -> str:
    """Simple horizontal bar for distribution display."""
    if total <= 0:
        return "·" * width
    filled = int(count / total * width)
    return "▇" * filled + "·" * (width - filled)


class PatternsScreen(Screen[None]):  # type: ignore[misc]
    """Application pattern analysis dashboard.

    Layout (2x2 grid):
        +----------------------------+----------------------------+
        |  상태별 분포 + 거절율       |  등급별 분포 + 바 차트       |
        +----------------------------+----------------------------+
        |  아키타입 Top-5 테이블      |  상위 기관 + 인사이트        |
        +----------------------------+----------------------------+
    """

    BINDINGS: list[Any] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Grid(id="patterns-grid"):
            yield Static("로딩 중…", id="pat-status", classes="pat-cell")
            yield Static("로딩 중…", id="pat-grades", classes="pat-cell")
            yield Static("로딩 중…", id="pat-archetype", classes="pat-cell")
            yield Static("로딩 중…", id="pat-insights", classes="pat-cell")
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
            stats = store.get_stats()
            all_jobs = store.search(keyword="")
        except Exception as exc:
            self.notify(f"DB 조회 실패: {exc}", severity="error")
            return

        self._render_status(stats, all_jobs)
        self._render_grades(stats)
        self._render_archetype(all_jobs)
        self._render_insights(stats, all_jobs)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_status(self, stats: dict[str, Any], jobs: list[dict]) -> None:
        by_status = stats.get("by_status", {}) or {}
        total = int(stats.get("total", 0)) or 1

        applied = int(by_status.get("applying", 0))
        rejected = int(by_status.get("rejected", 0))
        denom = applied + rejected
        rejection_rate = (rejected / denom * 100) if denom > 0 else 0.0

        lines = ["[b]상태별 분포[/b]", ""]
        for status_key in ("inbox", "applying", "graded", "rejected", "archived"):
            count = int(by_status.get(status_key, 0))
            label = STATUS_LABELS.get(status_key, status_key)
            bar = _bar(count, total, 15)
            lines.append(f"{label:<16} {bar} {count:>4d} ({count / total * 100:4.1f}%)")

        lines.append("")
        rate_color = "red" if rejection_rate > 50 else "yellow" if rejection_rate > 30 else "green"
        lines.append(f"[b]거절율[/b]: [{rate_color}]{rejection_rate:.1f}%[/{rate_color}]")
        lines.append(f"[dim](applied {applied} + rejected {rejected} = {denom}건 기준)[/dim]")

        self.query_one("#pat-status", Static).update("\n".join(lines))

    def _render_grades(self, stats: dict[str, Any]) -> None:
        by_grade = stats.get("by_grade", {}) or {}
        total = int(stats.get("total", 0)) or 1

        lines = ["[b]등급별 분포[/b]", ""]
        for grade in ("A", "B", "C", "D", "F"):
            count = int(by_grade.get(grade, 0))
            color = GRADE_COLORS.get(grade, "white")
            bar = _bar(count, total, 15)
            lines.append(f"[{color}]{grade}[/{color}] {bar} {count:>4d} ({count / total * 100:4.1f}%)")

        ungraded = int(by_grade.get("ungraded", 0))
        if ungraded:
            bar = _bar(ungraded, total, 15)
            lines.append(f"[dim]?[/dim] {bar} {ungraded:>4d} ({ungraded / total * 100:4.1f}%)")

        # A+B 비율
        ab = int(by_grade.get("A", 0)) + int(by_grade.get("B", 0))
        ab_pct = ab / total * 100
        ab_color = "green" if ab_pct > 30 else "yellow" if ab_pct > 15 else "red"
        lines.append("")
        lines.append(f"[b]A+B 비율[/b]: [{ab_color}]{ab_pct:.1f}%[/{ab_color}] ({ab}건)")

        self.query_one("#pat-grades", Static).update("\n".join(lines))

    def _render_archetype(self, jobs: list[dict]) -> None:
        counter: Counter[str] = Counter()
        for job in jobs:
            arch = job.get("archetype") or "미분류"
            counter[arch] += 1

        total = len(jobs) or 1
        top = counter.most_common(8)

        lines = ["[b]아키타입 분포 (Top 8)[/b]", ""]
        for arch, count in top:
            pct = count / total * 100
            bar = _bar(count, total, 15)
            display = arch[:12] if len(arch) > 12 else arch
            lines.append(f"{display:<12} {bar} {count:>4d} ({pct:4.1f}%)")

        self.query_one("#pat-archetype", Static).update("\n".join(lines))

    def _render_insights(self, stats: dict[str, Any], jobs: list[dict]) -> None:
        total = int(stats.get("total", 0))
        by_status = stats.get("by_status", {}) or {}
        by_grade = stats.get("by_grade", {}) or {}

        # 상위 기관
        org_counter: Counter[str] = Counter()
        for job in jobs:
            org = job.get("org") or "미상"
            org_counter[org] += 1
        top_orgs = org_counter.most_common(5)

        lines = ["[b]상위 채용 기관 (Top 5)[/b]", ""]
        for org, count in top_orgs:
            lines.append(f"  {org[:18]:<18} {count:>3d}건")

        # 인사이트 생성
        lines.append("")
        lines.append("[b]인사이트[/b]")
        lines.append("")

        # 1. inbox 비율
        inbox = int(by_status.get("inbox", 0))
        if total > 0 and inbox / total > 0.7:
            lines.append("[yellow]  ! inbox 비율 70%+ — 채점/지원 속도를 올려야 합니다[/yellow]")

        # 2. A등급 부족
        a_count = int(by_grade.get("A", 0))
        if total > 10 and a_count == 0:
            lines.append("[red]  ! A등급 공고 0건 — 타겟 채널/키워드 재검토 필요[/red]")
        elif total > 0 and a_count / total < 0.05:
            lines.append("[yellow]  ! A등급 비율 5% 미만 — 프로필 최적화 검토[/yellow]")

        # 3. 거절율
        applied = int(by_status.get("applying", 0))
        rejected = int(by_status.get("rejected", 0))
        denom = applied + rejected
        if denom >= 3 and rejected / denom > 0.5:
            lines.append("[red]  ! 거절율 50%+ — 서류 전략 재검토 권장[/red]")

        # 4. 총평
        if total == 0:
            lines.append("[dim]  데이터 없음 — career-ops scan --all 먼저 실행[/dim]")
        elif total < 10:
            lines.append(f"[dim]  총 {total}건 — 표본 부족, 더 스캔 필요[/dim]")
        else:
            lines.append(f"[dim]  총 {total}건 분석 완료[/dim]")

        self.query_one("#pat-insights", Static).update("\n".join(lines))
