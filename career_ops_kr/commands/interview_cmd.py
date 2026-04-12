"""career-ops interview-prep — STAR 면접 질문 생성.

--no-ai 플래그 시 LLM 없이 archetype 기본 템플릿 사용.
output/ 디렉토리에 마크다운 파일 저장.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Any

import click
from rich.panel import Panel

from career_ops_kr.commands._shared import (
    console,
    get_ai_client_or_fallback,
    load_profile,
    print_standard_report,
)

_STAR_COLORS = {"S": "green", "T": "yellow", "A": "cyan", "R": "blue"}


@click.command("interview-prep")
@click.argument("url")
@click.option("--questions", type=int, default=5, show_default=True, help="생성할 질문 수")
@click.option("--model", type=str, default=None, help="LLM 모델 ID 오버라이드")
@click.option("--api-key", "api_key", type=str, default=None, help="OpenRouter API 키")
@click.option("--no-ai", "no_ai", is_flag=True, help="AI 없이 기본 템플릿 사용")
@click.option("--save", "save_path", type=str, default=None, help="저장 경로 (default: output/)")
def interview_prep_cmd(
    url: str,
    questions: int,
    model: str | None,
    api_key: str | None,
    no_ai: bool,
    save_path: str | None,
) -> None:
    """공고 URL → STAR 면접 질문 생성 + 파일 저장."""
    evaluation = _score_url(url)
    if evaluation is None:
        sys.exit(1)

    print_standard_report(evaluation, console)
    profile = load_profile()

    if no_ai:
        from career_ops_kr.ai.interview import _fallback_star_template

        q_list = _fallback_star_template(evaluation, questions)
    else:
        client, _model = get_ai_client_or_fallback(api_key, console)
        model = model or _model
        if client is None or model is None:
            from career_ops_kr.ai.interview import _fallback_star_template

            q_list = _fallback_star_template(evaluation, questions)
        else:
            from career_ops_kr.ai.interview import generate_interview_questions

            q_list = generate_interview_questions(evaluation, profile, client, model, questions)

    _print_questions(q_list, evaluation)
    _save_questions(q_list, evaluation, save_path)


def _score_url(url: str) -> dict[str, Any] | None:
    """tool_score_job() 호출. 실패하면 None."""
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


def _print_questions(q_list: list[dict], evaluation: dict[str, Any]) -> None:
    """STAR 패널 출력."""
    org = evaluation.get("org") or ""
    for i, q in enumerate(q_list, 1):
        question = q.get("question", "")
        star = q.get("star_guide") or {}
        lines = [f"[bold]{question}[/bold]\n"]
        for key, label in [("S", "S (상황)"), ("T", "T (과제)"), ("A", "A (행동)"), ("R", "R (결과)")]:
            val = star.get(key, "")
            color = _STAR_COLORS.get(key, "white")
            lines.append(f"[{color}]{label}[/{color}]: {val}")

        console.print(
            Panel.fit(
                "\n".join(lines),
                title=f"Q{i}/{len(q_list)} — {org}",
                border_style="cyan",
            )
        )


def _save_questions(
    q_list: list[dict],
    evaluation: dict[str, Any],
    save_path: str | None,
) -> None:
    """마크다운 파일로 저장."""
    org = (evaluation.get("org") or "unknown").replace("/", "_").replace(" ", "_")
    today = date.today().strftime("%Y%m%d")
    filename = f"interview_{org}_{today}.md"

    if save_path:
        out_path = Path(save_path)
    else:
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / filename

    lines = [f"# 면접 준비 — {evaluation.get('org', '')} {evaluation.get('title', '')}\n"]
    for i, q in enumerate(q_list, 1):
        lines.append(f"## Q{i}. {q.get('question', '')}\n")
        star = q.get("star_guide") or {}
        for key, label in [("S", "상황"), ("T", "과제"), ("A", "행동"), ("R", "결과")]:
            lines.append(f"**{key} ({label})**: {star.get(key, '')}\n")
        lines.append("")

    try:
        out_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]저장[/green]: {out_path}")
    except Exception as exc:
        console.print(f"[yellow]파일 저장 실패[/yellow]: {exc}")
