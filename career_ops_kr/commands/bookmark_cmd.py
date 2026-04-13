"""`career-ops bookmark` — 공고 북마크/스크랩 관리.

Usage::

    career-ops bookmark add <job_id>        # 스크랩
    career-ops bookmark remove <job_id>     # 스크랩 해제
    career-ops bookmark list                # 스크랩된 공고 목록
"""

from __future__ import annotations

import click
from rich.table import Table

from career_ops_kr.commands._shared import console, get_store
from career_ops_kr.sector import infer_sector


@click.group("bookmark", help="공고 북마크 관리 (add/remove/list)")
def bookmark_cmd() -> None:
    """Bookmark group."""


@bookmark_cmd.command("add")
@click.argument("job_id")
def bookmark_add(job_id: str) -> None:
    """공고를 스크랩."""
    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음[/yellow]")
        return
    if store.set_bookmark(job_id, True):
        console.print(f"[green]✓[/green] 스크랩됨: {job_id}")
    else:
        console.print(f"[red]✗[/red] job_id 일치 없음: {job_id}")


@bookmark_cmd.command("remove")
@click.argument("job_id")
def bookmark_remove(job_id: str) -> None:
    """공고 스크랩 해제."""
    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음[/yellow]")
        return
    if store.set_bookmark(job_id, False):
        console.print(f"[green]✓[/green] 스크랩 해제: {job_id}")
    else:
        console.print(f"[red]✗[/red] job_id 일치 없음: {job_id}")


@bookmark_cmd.command("list")
def bookmark_list() -> None:
    """스크랩된 공고 목록."""
    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음[/yellow]")
        return
    jobs = store.list_bookmarked()
    if not jobs:
        console.print("[yellow]스크랩된 공고 없음[/yellow]")
        return
    table = Table(title=f"북마크 ({len(jobs)})")
    for col in ("id", "sector", "org", "title", "grade", "match", "deadline"):
        table.add_column(col)
    for j in jobs:
        fs = j.get("fit_score")
        match_str = f"{int(fs)}%" if fs is not None and fs != "" else "-"
        table.add_row(
            str(j.get("id") or "")[:12],
            infer_sector(j.get("source_channel"), j.get("org"), j.get("title")),
            str(j.get("org") or ""),
            str(j.get("title") or "")[:50],
            str(j.get("fit_grade") or ""),
            match_str,
            str(j.get("deadline") or ""),
        )
    console.print(table)
