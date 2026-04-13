"""Batch-score inbox jobs and persist fit results back into SQLite."""

from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.commands._shared import console, get_store

_PROGRESS_COLS = (
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
)


@click.command("batch")
@click.option("--limit", type=int, default=50, show_default=True, help="Maximum jobs to process")
@click.option(
    "--concurrency",
    type=int,
    default=3,
    show_default=True,
    help="Concurrent score requests",
)
@click.option("--status", type=str, default="inbox", show_default=True, help="Status filter")
@click.option("--dry-run", "dry_run", is_flag=True, help="Only inspect DB rows without scoring")
def batch_cmd(
    limit: int,
    concurrency: int,
    status: str,
    dry_run: bool,
) -> None:
    """Score existing DB rows and persist fit-grade data."""
    if dry_run:
        console.print("[cyan]dry-run[/cyan] mode: DB query only")
        store = get_store()
        if store is None:
            console.print("[yellow]DB not found[/yellow]")
            return
        inbox = _get_inbox(store, status, limit)
        console.print(f"  inbox {status} count: {len(inbox)}")
        return

    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음 — run career-ops scan first[/yellow]")
        return

    inbox = _get_inbox(store, status, limit)
    if not inbox:
        console.print(f"[yellow]no inbox items[/yellow] (status={status})")
        return

    if len(inbox) >= 5:
        console.print(f"[yellow]G4 batch gate[/yellow]: about to score {len(inbox)} jobs")
        if not Confirm.ask("Continue?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return

    asyncio.run(_batch_main(inbox[:limit], concurrency, store))


def _get_inbox(store: object, status: str, limit: int) -> list[dict]:
    """Return DB rows filtered by status."""
    try:
        if hasattr(store, "_connect"):
            with store._connect() as conn:  # type: ignore[attr-defined]
                rows = conn.execute(
                    """
                    SELECT * FROM jobs
                    WHERE status = ?
                    ORDER BY scanned_at DESC
                    LIMIT ?
                    """,
                    (status, int(limit)),
                ).fetchall()
            return [dict(row) for row in rows]
        all_jobs = store.search(keyword="")  # type: ignore[union-attr]
        return [j for j in all_jobs if (j.get("status") or "inbox") == status][:limit]
    except Exception as exc:
        console.print(f"[red]DB query failed[/red]: {exc}")
        return []


async def _batch_main(
    inbox: list[dict],
    concurrency: int,
    store: object,
) -> None:
    """Run rule-based scoring for existing DB rows."""
    try:
        from career_ops_kr import mcp_server as mcp
    except Exception as exc:
        console.print(f"[red]mcp_server import failed[/red]: {exc}")
        sys.exit(1)

    sem = asyncio.Semaphore(concurrency)
    loop = asyncio.get_event_loop()
    total = len(inbox)
    done_count = 0

    with Progress(*_PROGRESS_COLS, console=console, transient=True) as prog:
        task = prog.add_task("[cyan]batch scoring[/cyan]", total=total)

        async def _score_one(job: dict) -> dict | None:
            nonlocal done_count
            url = job.get("source_url") or ""
            if not url:
                done_count += 1
                prog.update(task, completed=done_count)
                return None
            try:
                async with sem:
                    result = await loop.run_in_executor(None, mcp.tool_score_job, url)
                    return result if isinstance(result, dict) else None
            except Exception:
                return None
            finally:
                done_count += 1
                prog.update(task, completed=done_count)

        tasks = [asyncio.create_task(_score_one(job)) for job in inbox]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    saved = 0
    for job, result in zip(inbox, results):
        if result is None or "error" in result:
            continue
        try:
            job_id = job.get("id") or ""
            grade = result.get("grade") or ""
            if not job_id or not grade:
                continue

            record = _row_to_job_record(job)
            store.upsert(  # type: ignore[union-attr]
                record,
                fit={
                    "grade": grade,
                    "score": result.get("total_score"),
                    "eligible": grade != "F",
                },
            )
            store.set_status(job_id, "graded")  # type: ignore[union-attr]
            saved += 1
        except Exception:
            continue

    console.print(f"[green]batch complete[/green] processed {total} jobs → saved {saved} grades")


def _row_to_job_record(row: dict) -> JobRecord:
    """Rehydrate a SQLite row into a JobRecord."""
    fetch_errors = row.get("fetch_errors")
    if isinstance(fetch_errors, str):
        try:
            parsed = json.loads(fetch_errors)
            fetch_errors = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            fetch_errors = []
    elif not isinstance(fetch_errors, list):
        fetch_errors = []

    return JobRecord.model_validate(
        {
            "id": row.get("id"),
            "source_url": row.get("source_url"),
            "source_channel": row.get("source_channel"),
            "source_tier": row.get("source_tier"),
            "org": row.get("org"),
            "title": row.get("title"),
            "archetype": row.get("archetype"),
            "deadline": row.get("deadline"),
            "posted_at": row.get("posted_at"),
            "location": row.get("location"),
            "description": row.get("description") or "",
            "legitimacy_tier": row.get("legitimacy_tier") or "T5",
            "scanned_at": row.get("scanned_at"),
            "fetch_errors": fetch_errors,
        }
    )
