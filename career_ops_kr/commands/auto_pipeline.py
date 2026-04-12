"""career-ops auto-pipeline — 전체 채널 수집 + AI 채점 자동 파이프라인.

CHANNEL_REGISTRY를 직접 순회해서 JobRecord 목록을 수집한다.
(tool_scan_jobs()는 count만 반환하므로 URL 목록 추출 불가)
G4 게이트: 5건 이상이면 샘플 1건 확인 후 진행.
"""

from __future__ import annotations

import sys

import click
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm

from career_ops_kr.commands._shared import (
    CONFIG_DIR,
    DATA_DIR,
    console,
    get_store,
    grade_ge,
    load_profile,
    print_standard_report,
)

_PROGRESS_COLS = (
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    MofNCompleteColumn(),
    TimeElapsedColumn(),
)


@click.command("auto-pipeline")
@click.option("--tier", type=int, default=None, help="채널 Tier 필터 (1~6)")
@click.option("--site", type=str, default=None, help="특정 사이트만 (예: linkareer)")
@click.option("--limit", type=int, default=50, show_default=True, help="최대 채점 건수")
@click.option(
    "--grade",
    "min_grade",
    type=str,
    default="B",
    show_default=True,
    help="저장 최소 등급 (A/B/C/D/F)",
)
@click.option("--notify", is_flag=True, help="Discord 알림 전송")
@click.option("--dry-run", "dry_run", is_flag=True, help="설정 검증만, 네트워크 없음")
def auto_pipeline_cmd(
    tier: int | None,
    site: str | None,
    limit: int,
    min_grade: str,
    notify: bool,
    dry_run: bool,
) -> None:
    """전체 채널 자동 수집 + 채점 → SQLiteStore 저장 (G4 게이트 포함)."""
    if dry_run:
        console.print("[cyan]dry-run[/cyan] 모드: 설정 검증만 수행")
        console.print(
            f"  tier={tier}  site={site}  limit={limit}  "
            f"min_grade={min_grade}  notify={notify}"
        )
        console.print(f"  CONFIG_DIR: {CONFIG_DIR}")
        console.print(f"  DATA_DIR: {DATA_DIR}")
        return

    # 채널 순회 → JobRecord 수집
    try:
        from career_ops_kr.channels import CHANNEL_REGISTRY
    except Exception as exc:
        console.print(f"[red]channels import 실패[/red]: {exc}")
        sys.exit(1)

    console.print("[cyan]채널 순회 중...[/cyan]")
    all_jobs = []
    for name, cls in CHANNEL_REGISTRY.items():
        if site and name != site:
            continue
        if tier is not None and getattr(cls, "tier", None) != tier:
            continue
        try:
            jobs = cls().list_jobs() or []
            all_jobs.extend(jobs)
            console.print(f"  [dim]{name}[/dim]: {len(jobs)}건")
        except Exception as exc:
            console.print(f"  [yellow]{name}[/yellow] 실패: {exc}")

    console.print(f"[green]수집 완료[/green] 총 {len(all_jobs)}건")

    if not all_jobs:
        console.print("[yellow]수집된 공고 없음[/yellow]")
        return

    # G4 게이트 — 5건 이상
    if len(all_jobs) >= 5:
        console.print(f"[yellow]G4 게이트[/yellow]: {len(all_jobs)}건 채점 예정")
        if not Confirm.ask("샘플 1건 확인 후 계속 진행?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return

        _run_sample(str(all_jobs[0].source_url))

        if not Confirm.ask("계속 진행?", default=True):
            console.print("[yellow]aborted[/yellow]")
            return

    target = min(limit, len(all_jobs))
    store = get_store()
    saved = 0

    try:
        from career_ops_kr import mcp_server as mcp
    except Exception as exc:
        console.print(f"[red]mcp_server import 실패[/red]: {exc}")
        sys.exit(1)

    with Progress(*_PROGRESS_COLS, console=console, transient=True) as prog:
        task = prog.add_task("[cyan]채점[/cyan]", total=target)
        for job in all_jobs[:target]:
            url = str(job.source_url)
            try:
                result = mcp.tool_score_job(url=url)
                if isinstance(result, dict) and "error" not in result:
                    if grade_ge(result.get("grade") or "", min_grade) and store is not None:
                        try:
                            store.upsert(job, fit=result)
                            saved += 1
                        except Exception:
                            pass
            except Exception:
                pass
            prog.advance(task)

    console.print(
        f"[green]완료[/green] 채점 {target}건 → {min_grade}+ 등급 저장 {saved}건"
    )

    if notify and store is not None:
        _send_notification(store, load_profile())


def _run_sample(url: str) -> None:
    """샘플 1건 채점 후 표준 리포트 출력."""
    try:
        from career_ops_kr import mcp_server as mcp

        result = mcp.tool_score_job(url=url)
        if isinstance(result, dict) and "error" not in result:
            print_standard_report(result, console)
    except Exception as exc:
        console.print(f"[yellow]샘플 채점 실패[/yellow]: {exc}")


def _send_notification(store: object, profile: dict) -> None:
    """Discord 배치 요약 알림 전송."""
    try:
        from career_ops_kr.notifier.discord_push import DiscordNotifier

        webhook = (profile.get("discord") or {}).get("webhook_url")
        notifier = DiscordNotifier(webhook_url=webhook)
        stats = store.get_stats()  # type: ignore[union-attr]
        notifier.notify_batch_summary(stats)
        console.print("[green]Discord 알림 전송 완료[/green]")
    except Exception as exc:
        console.print(f"[yellow]Discord 알림 실패[/yellow]: {exc}")
