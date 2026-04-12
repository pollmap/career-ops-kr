"""career-ops batch — DB inbox 비동기 배치 채점.

Windows asyncio 호환: run_in_executor(None, tool_score_job, url) 패턴.
G4 게이트: 5건 이상이면 Confirm 후 진행.
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm

from career_ops_kr.commands._shared import console, get_store

_PROGRESS_COLS = (
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
)


@click.command("batch")
@click.option("--limit", type=int, default=50, show_default=True, help="최대 처리 건수")
@click.option(
    "--concurrency",
    type=int,
    default=3,
    show_default=True,
    help="동시 채점 수 (ThreadPoolExecutor 기반)",
)
@click.option("--status", type=str, default="inbox", show_default=True, help="처리할 status 필터")
@click.option("--dry-run", "dry_run", is_flag=True, help="DB 조회만, 실제 채점 없음")
def batch_cmd(
    limit: int,
    concurrency: int,
    status: str,
    dry_run: bool,
) -> None:
    """DB inbox 공고를 비동기 배치 채점하여 grade/status 업데이트."""
    if dry_run:
        console.print("[cyan]dry-run[/cyan] 모드: DB 조회만 수행")
        store = get_store()
        if store is None:
            console.print("[yellow]DB 없음[/yellow]")
            return
        inbox = _get_inbox(store, status, limit)
        console.print(f"  inbox {status} 건수: {len(inbox)}")
        return

    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음 — career-ops scan 먼저 실행하세요.[/yellow]")
        return

    inbox = _get_inbox(store, status, limit)
    if not inbox:
        console.print(f"[yellow]no inbox items[/yellow] (status={status})")
        return

    if len(inbox) >= 5:
        console.print(f"[yellow]G4 게이트[/yellow]: {len(inbox)}건 일괄 채점 예정")
        if not Confirm.ask("계속 진행?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return

    asyncio.run(_batch_main(inbox[:limit], concurrency, store))


def _get_inbox(store: object, status: str, limit: int) -> list[dict]:
    """DB에서 status 필터 inbox 목록 반환."""
    try:
        all_jobs = store.search(keyword="")  # type: ignore[union-attr]
        return [j for j in all_jobs if (j.get("status") or "inbox") == status][:limit]
    except Exception as exc:
        console.print(f"[red]DB 조회 실패[/red]: {exc}")
        return []


async def _batch_main(
    inbox: list[dict],
    concurrency: int,
    store: object,
) -> None:
    """비동기 배치 채점 메인 루프."""
    try:
        from career_ops_kr import mcp_server as mcp
    except Exception as exc:
        console.print(f"[red]mcp_server import 실패[/red]: {exc}")
        sys.exit(1)

    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_event_loop()
    total = len(inbox)
    done_count = 0

    with Progress(*_PROGRESS_COLS, console=console, transient=True) as prog:
        task = prog.add_task("[cyan]배치 채점[/cyan]", total=total)

        async def _score_one(job: dict) -> dict | None:
            nonlocal done_count
            url = job.get("source_url") or ""
            if not url:
                done_count += 1
                prog.update(task, completed=done_count)
                return None
            try:
                async with sem:
                    result = await loop.run_in_executor(
                        None, mcp.tool_score_job, url
                    )
                    return result if isinstance(result, dict) else None
            except Exception:
                return None
            finally:
                done_count += 1
                prog.update(task, completed=done_count)

        tasks = [asyncio.create_task(_score_one(j)) for j in inbox]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    saved = 0
    for job, result in zip(inbox, results):
        if result is None or "error" in result:
            continue
        try:
            job_id = job.get("id") or ""
            grade = result.get("grade") or ""
            if job_id and grade:
                store.set_status(job_id, "graded")  # type: ignore[union-attr]
                saved += 1
        except Exception:
            pass

    console.print(f"[green]배치 완료[/green] {total}건 처리 → {saved}건 grade 업데이트")
