"""career-ops filter — 공고 텍스트 자격 판정 (PASS/CONDITIONAL/FAIL).

텍스트 소스 우선순위: --url > --file > positional TEXT.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.panel import Panel

from career_ops_kr.commands._shared import CONFIG_DIR, console


@click.command("filter")
@click.argument("text", required=False, default=None)
@click.option("--url", "url_", type=str, default=None, help="공고 URL로 직접 판정")
@click.option(
    "--file",
    "file_path",
    type=click.Path(),
    default=None,
    help="판정할 텍스트 파일 경로",
)
@click.option("--json", "output_json", is_flag=True, help="결과 JSON 출력")
@click.option("--confidence", is_flag=True, help="신뢰도 점수 표시")
def filter_cmd(
    text: str | None,
    url_: str | None,
    file_path: str | None,
    output_json: bool,
    confidence: bool,
) -> None:
    """공고 텍스트/URL/파일 → 자격 판정 패널 출력."""
    job_text = _resolve_text(text, url_, file_path)

    # QualifierEngine 실행
    try:
        from career_ops_kr.qualifier.engine import QualifierEngine

        qe = QualifierEngine(
            rules_path=CONFIG_DIR / "qualifier_rules.yml",
            profile_path=CONFIG_DIR / "profile.yml",
        )
        result = qe.evaluate(job_text)
    except Exception as exc:
        console.print(f"[red]qualifier 실행 실패[/red]: {exc}")
        sys.exit(1)

    verdict_str = result.verdict.value
    emoji_map = {"PASS": "✅", "CONDITIONAL": "△", "FAIL": "❌"}
    color_map = {"PASS": "green", "CONDITIONAL": "yellow", "FAIL": "red"}
    emoji = emoji_map.get(verdict_str, "?")
    border = color_map.get(verdict_str, "dim")

    if output_json:
        out: dict = {
            "verdict": verdict_str,
            "reasons": result.reasons,
            "blocking_rules": result.blocking_rules,
        }
        if confidence:
            out["confidence"] = result.confidence
        click.echo(json.dumps(out, ensure_ascii=False, indent=2))
        return

    lines = [f"{emoji} **{verdict_str}**"]
    if result.reasons:
        lines.append("\n**이유:**")
        for r in result.reasons:
            lines.append(f"- {r}")
    if result.blocking_rules:
        lines.append("\n**차단 규칙:**")
        for b in result.blocking_rules:
            lines.append(f"- ❌ {b}")
    if confidence:
        lines.append(f"\n신뢰도: {result.confidence:.0%}")

    console.print(
        Panel.fit(
            "\n".join(lines),
            title="자격 판정 결과",
            border_style=border,
        )
    )


def _resolve_text(
    text: str | None,
    url_: str | None,
    file_path: str | None,
) -> str:
    """텍스트 소스 결정 (url > file > positional text)."""
    if url_:
        return _fetch_url_text(url_)
    if file_path:
        try:
            return Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            console.print(f"[red]파일 읽기 실패[/red]: {exc}")
            sys.exit(1)
    if text:
        return text
    console.print("[red]텍스트, --url, 또는 --file을 지정해주세요.[/red]")
    sys.exit(1)


def _fetch_url_text(url: str) -> str:
    """URL → 텍스트. 등록 채널 먼저, fallback으로 requests."""
    try:
        from career_ops_kr.channels import CHANNEL_REGISTRY

        for _name, cls in CHANNEL_REGISTRY.items():
            try:
                detail = cls().get_detail(url)
                if detail is not None:
                    return (detail.description or "") + " " + detail.title
            except Exception:
                continue
    except Exception:
        pass

    try:
        import requests  # type: ignore[import-untyped]

        resp = requests.get(url, timeout=10)
        return resp.text
    except Exception as exc:
        console.print(f"[red]URL 조회 실패[/red]: {exc}")
        sys.exit(1)
