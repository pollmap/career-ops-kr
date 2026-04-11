"""Job detail screen — full context for one job + status actions."""

from __future__ import annotations

import json
import webbrowser
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Markdown, Static

from career_ops_kr.storage.sqlite_store import SQLiteStore

GRADE_BADGES = {
    "A": "[b white on green] A [/]",
    "B": "[b white on blue] B [/]",
    "C": "[b black on yellow] C [/]",
    "D": "[b white on orange3] D [/]",
    "F": "[b white on red] F [/]",
}


class JobDetailScreen(Screen[None]):  # type: ignore[misc]
    """Detailed Markdown view for a single job + status mutations."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "뒤로"),
        Binding("a", "mark_applied", "지원"),
        Binding("w", "mark_watching", "워치"),
        Binding("x", "mark_rejected", "거절"),
        Binding("o", "open_url", "URL 열기"),
        Binding("b", "app.pop_screen", "뒤로", show=False),
    ]

    def __init__(self, job_id: str) -> None:
        super().__init__()
        self._job_id = job_id
        self._job: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="detail-root"):
            yield Static("로딩 중…", id="detail-header", classes="detail-header")
            yield Markdown("", id="detail-body")
            with Horizontal(id="detail-actions"):
                yield Static(
                    "[b]액션:[/b] "
                    "[cyan]a[/cyan] 지원  "
                    "[cyan]w[/cyan] 워치  "
                    "[cyan]x[/cyan] 거절  "
                    "[cyan]o[/cyan] URL  "
                    "[cyan]esc[/cyan] 뒤로",
                    classes="detail-actions-hint",
                )
        yield Footer()

    def on_mount(self) -> None:
        self._load()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _store(self) -> SQLiteStore | None:
        store = getattr(self.app, "store", None)
        return store if isinstance(store, SQLiteStore) else None

    def _load(self) -> None:
        store = self._store()
        if store is None:
            return
        try:
            with store._connect() as conn:
                row = conn.execute("SELECT * FROM jobs WHERE id = ?", (self._job_id,)).fetchone()
        except Exception as exc:
            self.notify(f"DB 조회 실패: {exc}", severity="error")
            return
        if row is None:
            self.query_one("#detail-header", Static).update(
                f"[red]job not found[/red]: {self._job_id}"
            )
            self.query_one("#detail-body", Markdown).update("")
            return
        self._job = dict(row)
        self._render()

    def _render(self) -> None:
        job = self._job or {}
        grade = str(job.get("fit_grade") or "-")
        badge = GRADE_BADGES.get(grade, f"[b] {grade} [/b]")
        org = str(job.get("org") or "?")
        title = str(job.get("title") or "?")
        deadline = str(job.get("deadline") or "미정")
        status = str(job.get("status") or "inbox")
        tier = int(job.get("source_tier", 5))
        legit = str(job.get("legitimacy_tier") or "T5")
        archetype = str(job.get("archetype") or "미분류")
        score = job.get("fit_score")
        score_txt = f"{float(score):.1f}" if score is not None else "-"
        eligible = str(job.get("eligible") or "-")

        header_txt = (
            f"{badge}  [b]{org}[/b]  —  {title}\n"
            f"[dim]archetype[/dim] {archetype}   "
            f"[dim]status[/dim] {status}   "
            f"[dim]deadline[/dim] {deadline}   "
            f"[dim]tier[/dim] T{tier}/{legit}   "
            f"[dim]score[/dim] {score_txt}   "
            f"[dim]eligible[/dim] {eligible}"
        )
        self.query_one("#detail-header", Static).update(header_txt)

        description = str(job.get("description") or "(설명 없음)")
        url = str(job.get("source_url") or "")
        scanned = str(job.get("scanned_at") or "-")
        channel = str(job.get("source_channel") or "-")
        errors_json = str(job.get("fetch_errors") or "[]")
        try:
            errors = json.loads(errors_json)
        except json.JSONDecodeError:
            errors = [errors_json]

        md_lines: list[str] = []
        md_lines.append(f"## 설명\n\n{description}\n")
        md_lines.append("## 메타데이터\n")
        md_lines.append(f"- **Source URL:** {url}")
        md_lines.append(f"- **Channel:** {channel}")
        md_lines.append(f"- **Scanned at:** {scanned}")
        md_lines.append(f"- **Legitimacy tier:** {legit}")
        if errors:
            md_lines.append("\n## Fetch errors\n")
            for err in errors:
                md_lines.append(f"- `{err}`")
        self.query_one("#detail-body", Markdown).update("\n".join(md_lines))

    # ------------------------------------------------------------------
    # Actions — status mutations
    # ------------------------------------------------------------------

    def _set_status(self, status: str) -> None:
        store = self._store()
        if store is None or self._job is None:
            return
        ok = store.set_status(self._job_id, status)
        if ok:
            self._job["status"] = status
            self._render()
            self.notify(f"status → {status}", severity="information", timeout=3.0)
        else:
            self.notify("상태 업데이트 실패", severity="error")

    def action_mark_applied(self) -> None:
        self._set_status("applied")

    def action_mark_watching(self) -> None:
        self._set_status("watching")

    def action_mark_rejected(self) -> None:
        self._set_status("rejected")

    def action_open_url(self) -> None:
        if not self._job:
            return
        url = str(self._job.get("source_url") or "")
        if not url:
            self.notify("URL 없음", severity="warning")
            return
        try:
            webbrowser.open(url)
            self.notify(f"브라우저에서 열림: {url[:60]}", timeout=3.0)
        except Exception as exc:
            self.notify(f"URL 열기 실패: {exc}", severity="error")
