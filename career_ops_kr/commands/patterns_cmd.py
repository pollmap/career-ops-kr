"""career-ops patterns — 지원 이력 패턴 분석 리포트.

SQLiteStore 기반, AI 없음. patterns/ 서브패키지가 존재하면 MCP tool_run_patterns도 활성화.
"""

from __future__ import annotations

import json

import click
from rich.table import Table

from career_ops_kr.commands._shared import console


@click.command("patterns")
@click.option("--days", type=int, default=30, show_default=True, help="분석 기간 (일)")
@click.option("--json", "output_json", is_flag=True, help="JSON 출력")
def patterns_cmd(days: int, output_json: bool) -> None:
    """지원 이력 패턴 분석 — 거절율/등급 분포/archetype 통계."""
    try:
        from career_ops_kr.patterns.analyzer import analyze

        result = analyze(days=days)
    except Exception as exc:
        console.print(f"[red]패턴 분석 실패[/red]: {exc}")
        return

    if output_json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return

    _print_report(result)


def _print_report(result: dict) -> None:
    """패턴 분석 결과 리포트 출력."""
    console.print(
        f"\n[bold cyan]패턴 분석[/bold cyan] "
        f"기간: {result.get('period', '')} "
        f"({result.get('days', 30)}일 / {result.get('total_analyzed', 0)}건)\n"
    )

    total = result.get("total_analyzed", 0)
    if total == 0:
        console.print("[yellow]분석 데이터 없음[/yellow] — career-ops scan 먼저 실행하세요.")
        return

    # 상태별 분포
    by_status = result.get("by_status") or {}
    if by_status:
        table = Table(title="상태별 분포")
        table.add_column("status", style="cyan")
        table.add_column("건수", justify="right")
        for k, v in sorted(by_status.items(), key=lambda x: -x[1]):
            table.add_row(k, str(v))
        console.print(table)

    # 등급별 분포
    by_grade = result.get("by_grade") or {}
    if by_grade:
        table2 = Table(title="Fit 등급 분포")
        table2.add_column("grade", style="yellow")
        table2.add_column("건수", justify="right")
        for k, v in sorted(by_grade.items()):
            table2.add_row(k, str(v))
        console.print(table2)

    # Archetype 분포
    by_arch = result.get("by_archetype") or {}
    if by_arch:
        table3 = Table(title="Archetype 분포")
        table3.add_column("archetype", style="green")
        table3.add_column("건수", justify="right")
        for k, v in sorted(by_arch.items(), key=lambda x: -x[1])[:8]:
            table3.add_row(k, str(v))
        console.print(table3)

    # 주요 통계
    rejection_rate = result.get("rejection_rate", 0.0)
    avg_days = result.get("avg_days_to_deadline")
    top_orgs = result.get("top_orgs") or []

    console.print(f"\n거절율: [red]{rejection_rate:.0%}[/red]")
    if avg_days is not None:
        console.print(f"평균 마감까지 남은 일: [yellow]{avg_days:.1f}일[/yellow]")
    if top_orgs:
        console.print(f"자주 등장한 기관: {', '.join(top_orgs)}")

    # 패턴 인사이트
    patterns = result.get("patterns") or []
    if patterns:
        console.print("\n[bold]패턴 인사이트:[/bold]")
        for p in patterns:
            console.print(f"  💡 {p}")
