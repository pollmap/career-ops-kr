"""career-ops project — 포트폴리오 스프린트 플랜 생성.

--no-ai 플래그 시 archetype별 기본 플랜 사용.
output/ 디렉토리에 마크다운 파일 저장.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import click
from rich.table import Table

from career_ops_kr.commands._shared import (
    console,
    get_ai_client_or_fallback,
    load_profile,
    print_standard_report,
)


@click.command("project")
@click.argument("url")
@click.option("--weeks", type=int, default=4, show_default=True, help="스프린트 주차 수")
@click.option("--no-ai", "no_ai", is_flag=True, help="AI 없이 기본 플랜 사용")
@click.option("--save", "save_path", type=str, default=None, help="저장 경로 (default: output/)")
@click.option("--model", type=str, default=None, help="LLM 모델 ID 오버라이드")
@click.option("--api-key", "api_key", type=str, default=None, help="OpenRouter API 키")
def project_cmd(
    url: str,
    weeks: int,
    no_ai: bool,
    save_path: str | None,
    model: str | None,
    api_key: str | None,
) -> None:
    """공고 URL → 포트폴리오 스프린트 플랜 생성."""
    evaluation = _score_url(url)
    if evaluation is None:
        sys.exit(1)

    print_standard_report(evaluation, console)
    profile = load_profile()

    if no_ai:
        from career_ops_kr.ai.project import _get_fallback

        archetype = evaluation.get("archetype") or "DEFAULT"
        plan = _get_fallback(archetype, weeks)
    else:
        client, _model = get_ai_client_or_fallback(api_key, console)
        model = model or _model
        if client is None or model is None:
            from career_ops_kr.ai.project import _get_fallback

            archetype = evaluation.get("archetype") or "DEFAULT"
            plan = _get_fallback(archetype, weeks)
        else:
            from career_ops_kr.ai.project import generate_sprint_plan

            plan = generate_sprint_plan(evaluation, profile, weeks, client, model)

    _print_plan(plan, evaluation)
    _save_plan(plan, evaluation, save_path)


def _score_url(url: str) -> dict[str, Any] | None:
    try:
        from career_ops_kr import mcp_server as mcp

        result = mcp.tool_score_job(url=url)
        if isinstance(result, dict) and "error" in result:
            console.print(f"[red]채점 실패[/red]: {result.get('error')}")
            return None
        return result
    except Exception as exc:
        console.print(f"[red]채점 실패[/red]: {exc}")
        return None


def _print_plan(plan: list[dict[str, Any]], evaluation: dict[str, Any]) -> None:
    """스프린트 테이블 출력."""
    org = evaluation.get("org") or ""
    title = evaluation.get("title") or ""

    table = Table(title=f"포트폴리오 스프린트 — {org} / {title}")
    table.add_column("주차", style="cyan", width=6)
    table.add_column("테마", style="bold")
    table.add_column("할 일")
    table.add_column("산출물", style="green")

    for sprint in plan:
        week = str(sprint.get("week", ""))
        theme = str(sprint.get("theme", ""))
        tasks = sprint.get("tasks") or []
        tasks_str = "\n".join(f"• {t}" for t in tasks)
        deliverable = str(sprint.get("deliverable", ""))
        table.add_row(week, theme, tasks_str, deliverable)

    console.print(table)


def _save_plan(
    plan: list[dict[str, Any]],
    evaluation: dict[str, Any],
    save_path: str | None,
) -> None:
    """마크다운 파일로 저장."""
    org = (evaluation.get("org") or "unknown").replace("/", "_").replace(" ", "_")
    today = date.today().strftime("%Y%m%d")
    filename = f"portfolio_{org}_{today}.md"

    if save_path:
        out_path = Path(save_path)
    else:
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / filename

    lines = [
        f"# 포트폴리오 스프린트 플랜 — {evaluation.get('org', '')}",
        f"\n**공고**: {evaluation.get('title', '')} — {evaluation.get('url', '')}",
        f"**생성일**: {today}\n",
        "---\n",
    ]
    for sprint in plan:
        lines.append(f"## {sprint.get('week', '')}주차: {sprint.get('theme', '')}\n")
        for t in sprint.get("tasks") or []:
            lines.append(f"- {t}")
        lines.append(f"\n**산출물**: {sprint.get('deliverable', '')}\n")

    try:
        out_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]저장[/green]: {out_path}")
    except Exception as exc:
        console.print(f"[yellow]파일 저장 실패[/yellow]: {exc}")
