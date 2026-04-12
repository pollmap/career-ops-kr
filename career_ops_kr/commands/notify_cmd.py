"""career-ops notify — Discord 알림 발송.

webhook URL 우선순위: --webhook > profile.yml discord.webhook_url > DISCORD_WEBHOOK_URL 환경변수.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import click

from career_ops_kr.commands._shared import console, get_store, load_profile


def _resolve_webhook(webhook_opt: str | None, profile: dict) -> str | None:
    """webhook URL 결정 (CLI옵션 > profile.yml > 환경변수)."""
    if webhook_opt:
        return webhook_opt
    profile_webhook = (profile.get("discord") or {}).get("webhook_url")
    if profile_webhook:
        return profile_webhook
    return os.environ.get("DISCORD_WEBHOOK_URL") or None


@click.command("notify")
@click.option("--test", "ping_test", is_flag=True, help="ping 테스트만")
@click.option(
    "--grade",
    type=str,
    default="A",
    show_default=True,
    help="알림할 최소 등급",
)
@click.option("--days", type=int, default=7, show_default=True, help="마감 D-N 이내 알림")
@click.option("--webhook", type=str, default=None, help="Discord webhook URL")
@click.option("--summary", "send_summary", is_flag=True, help="배치 요약 전송")
def notify_cmd(
    ping_test: bool,
    grade: str,
    days: int,
    webhook: str | None,
    send_summary: bool,
) -> None:
    """Discord webhook으로 공고 알림/마감 알림/배치 요약 전송."""
    profile = load_profile()
    _webhook = _resolve_webhook(webhook, profile)

    try:
        from career_ops_kr.notifier.discord_push import DiscordNotifier

        notifier = DiscordNotifier(webhook_url=_webhook)
    except Exception as exc:
        console.print(f"[red]DiscordNotifier 초기화 실패[/red]: {exc}")
        return

    if not _webhook:
        console.print(
            "[yellow]webhook 미설정[/yellow] — log-only 모드로 실행합니다.\n"
            "  설정: --webhook URL  또는  DISCORD_WEBHOOK_URL 환경변수"
        )

    if ping_test:
        ok = notifier.test_connection()
        status = "[green]OK[/green]" if ok else "[yellow]log-only (webhook 없음)[/yellow]"
        console.print(f"Discord ping {status}")
        return

    store = get_store()
    if store is None:
        console.print("[yellow]DB 없음[/yellow] — career-ops scan 먼저 실행하세요.")
        return

    if send_summary:
        try:
            stats = store.get_stats()
            notifier.notify_batch_summary(stats)
            console.print("[green]배치 요약 전송 완료[/green]")
        except Exception as exc:
            console.print(f"[red]요약 전송 실패[/red]: {exc}")
        return

    # 등급별 신규 공고 알림
    try:
        jobs = store.list_by_grade(grade)
        if jobs:
            notifier.notify_new_jobs(jobs, grade_filter=grade)
            console.print(f"[green]{grade}+ 공고 알림 전송[/green]: {len(jobs)}건")
        else:
            console.print(f"[dim]{grade}+ 공고 없음[/dim]")
    except Exception as exc:
        console.print(f"[red]공고 알림 실패[/red]: {exc}")

    # 마감 임박 알림
    try:
        upcoming = store.list_upcoming_deadlines(days)
        today = date.today()
        for job in upcoming:
            deadline_str = job.get("deadline") or ""
            try:
                deadline_date = date.fromisoformat(str(deadline_str))
                days_left = (deadline_date - today).days
            except (ValueError, TypeError):
                days_left = days
            notifier.notify_deadline(job, days_left)
        if upcoming:
            console.print(f"[green]마감 임박 알림 전송[/green]: {len(upcoming)}건 (D-{days} 이내)")
    except Exception as exc:
        console.print(f"[red]마감 알림 실패[/red]: {exc}")
