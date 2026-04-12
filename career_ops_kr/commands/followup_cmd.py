"""career-ops followup — 후속 이메일 초안 생성.

--no-ai 플래그 시 deterministic 템플릿 사용.
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


@click.command("followup")
@click.argument("url")
@click.option(
    "--stage",
    type=click.Choice(["applied", "interviewed", "rejected"]),
    default="applied",
    show_default=True,
    help="지원 단계",
)
@click.option(
    "--tone",
    type=click.Choice(["professional", "friendly", "concise"]),
    default="professional",
    show_default=True,
    help="이메일 톤",
)
@click.option("--no-ai", "no_ai", is_flag=True, help="AI 없이 기본 템플릿 사용")
@click.option("--save", "save_path", type=str, default=None, help="저장 경로 (default: output/)")
@click.option("--model", type=str, default=None, help="LLM 모델 ID 오버라이드")
@click.option("--api-key", "api_key", type=str, default=None, help="OpenRouter API 키")
def followup_cmd(
    url: str,
    stage: str,
    tone: str,
    no_ai: bool,
    save_path: str | None,
    model: str | None,
    api_key: str | None,
) -> None:
    """공고 URL + 단계 → 후속 이메일 초안 생성."""
    evaluation = _score_url(url)
    if evaluation is None:
        sys.exit(1)

    print_standard_report(evaluation, console)
    profile = load_profile()

    if no_ai:
        from career_ops_kr.ai.followup import _followup_template

        email_body = _followup_template(evaluation, profile, stage, tone)
    else:
        client, _model = get_ai_client_or_fallback(api_key, console)
        model = model or _model
        if client is None or model is None:
            from career_ops_kr.ai.followup import _followup_template

            email_body = _followup_template(evaluation, profile, stage, tone)
        else:
            from career_ops_kr.ai.followup import generate_followup_email

            email_body = generate_followup_email(evaluation, profile, stage, tone, client, model)

    _print_email(email_body, evaluation, stage)
    _save_email(email_body, evaluation, stage, save_path)


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


def _print_email(email_body: str, evaluation: dict[str, Any], stage: str) -> None:
    """이메일 초안 패널 출력."""
    org = evaluation.get("org") or ""
    console.print(
        Panel.fit(
            email_body,
            title=f"후속 이메일 초안 — {org} [{stage}]",
            border_style="cyan",
        )
    )
    console.print(
        "[dim]⚠️ 이 초안을 직접 검토·수정 후 발송하세요. 자동 발송 없음.[/dim]"
    )


def _save_email(
    email_body: str,
    evaluation: dict[str, Any],
    stage: str,
    save_path: str | None,
) -> None:
    """마크다운 파일로 저장."""
    org = (evaluation.get("org") or "unknown").replace("/", "_").replace(" ", "_")
    today = date.today().strftime("%Y%m%d")
    filename = f"followup_{org}_{stage}_{today}.md"

    if save_path:
        out_path = Path(save_path)
    else:
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / filename

    content = (
        f"# 후속 이메일 — {evaluation.get('org', '')} [{stage}]\n\n"
        f"**생성일**: {today}\n"
        f"**공고**: {evaluation.get('title', '')} — {evaluation.get('url', '')}\n\n"
        f"---\n\n{email_body}\n"
    )

    try:
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[green]저장[/green]: {out_path}")
    except Exception as exc:
        console.print(f"[yellow]파일 저장 실패[/yellow]: {exc}")
