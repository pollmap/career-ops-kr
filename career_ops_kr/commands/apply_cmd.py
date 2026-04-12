"""career-ops apply — 지원 준비 체크리스트 + G5 영구 수동 안내.

⚠️ G5 영구 수동: 제출은 반드시 직접 하세요.
자동 제출 없음. webbrowser.open() 없음. 폼 자동입력 없음.
"""

from __future__ import annotations

import sys
from typing import Any

import click
from rich.panel import Panel
from rich.prompt import Confirm

from career_ops_kr.commands._shared import console, get_store, print_standard_report

_AUTO_CHECKLIST = [
    "공고 URL 유효성 확인",
    "마감일 확인 (D-day 계산)",
    "기관명/직무명 정확히 확인",
    "자격 요건 필터 (QualifierEngine)",
    "적합도 등급 확인 (FitScorer)",
    "지원 자격 충족 여부 검토",
    "중복 지원 여부 확인 (DB 조회)",
    "채용공고 원본 URL 저장",
    "관련 archetpye 분류 확인",
    "tracker DB 상태 확인",
]

_MANUAL_CHECKLIST = [
    "이력서 최신 버전 확인 ← 수동 필요",
    "자기소개서 맞춤 작성 ← 수동 필요",
    "포트폴리오 파일 준비 ← 수동 필요",
    "추천서/참고인 연락 여부 확인 ← 수동 필요",
    "지원 사이트 회원가입/로그인 확인 ← 수동 필요",
    "지원서 폼 항목 미리 확인 ← 수동 필요",
    "파일 업로드 용량 제한 확인 ← 수동 필요",
    "최종 제출 전 오탈자 검토 ← 수동 필요",
    "제출 완료 확인 메일 확인 ← 수동 필요",
    "제출 후 tracker 상태 수동 업데이트 ← 수동 필요",
]


@click.command("apply")
@click.argument("url")
def apply_cmd(url: str) -> None:
    """공고 URL → 지원 준비 체크리스트 출력 (G5 영구 수동).

    ⚠️ 제출은 반드시 직접 하세요 — 시스템은 '준비 완료'까지만 지원합니다.
    """
    evaluation = _score_url(url)
    if evaluation is None:
        sys.exit(1)

    print_standard_report(evaluation, console)

    # FAIL verdict → 경고
    verdict = evaluation.get("qualifier_verdict") or ""
    if "FAIL" in verdict.upper():
        console.print(
            Panel.fit(
                "[bold red]❌ 자격 요건 FAIL[/bold red]\n"
                "QualifierEngine이 자격 미달로 판정했습니다.\n"
                "계속 진행하려면 아래 확인 후 수동으로 판단하세요.",
                border_style="red",
            )
        )
        if not Confirm.ask("FAIL 판정에도 계속 진행?", default=False):
            console.print("[yellow]aborted[/yellow]")
            return

    # 체크리스트 출력
    _print_checklist(evaluation)

    # G5 강조
    console.print(
        Panel.fit(
            "[bold red]★ G5 영구 수동: 제출은 반드시 직접 하세요.[/bold red]\n"
            "시스템은 체크리스트 준비까지만 지원합니다.\n"
            "지원 폼 자동 입력/제출은 절대 없습니다.",
            border_style="red",
            title="G5 PERMANENT MANUAL",
        )
    )

    # tracker 등록
    if Confirm.ask("tracker에 'applying' 상태로 등록?", default=True):
        _update_tracker(evaluation)


def _score_url(url: str) -> dict[str, Any] | None:
    """tool_score_job() 호출."""
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


def _print_checklist(evaluation: dict[str, Any]) -> None:
    """지원 준비 체크리스트 패널 출력."""
    org = evaluation.get("org") or ""
    title = evaluation.get("title") or ""

    auto_lines = ["[bold]자동 확인 항목:[/bold]"]
    for i, item in enumerate(_AUTO_CHECKLIST, 1):
        auto_lines.append(f"  [{i:02d}] ✅ {item}")

    manual_lines = ["\n[bold]수동 확인 항목:[/bold]"]
    for i, item in enumerate(_MANUAL_CHECKLIST, 1):
        manual_lines.append(f"  [{i:02d}] ☐ {item}")

    console.print(
        Panel.fit(
            "\n".join(auto_lines + manual_lines),
            title=f"지원 체크리스트 — {org} / {title}",
            border_style="cyan",
        )
    )


def _update_tracker(evaluation: dict[str, Any]) -> None:
    """SQLiteStore에 applying 상태 등록."""
    try:
        from career_ops_kr.channels.base import JobRecord

        store = get_store()
        if store is None:
            console.print("[yellow]DB 없음 — tracker 업데이트 불가[/yellow]")
            return

        url = evaluation.get("url") or ""
        jobs = store.search(keyword="")
        job_id = None
        for j in jobs:
            if j.get("source_url") == url or str(j.get("source_url", "")) == url:
                job_id = j.get("id")
                break

        if job_id:
            store.set_status(job_id, "applying")
            console.print(f"[green]tracker 등록 완료[/green]: {job_id[:12]}... → applying")
        else:
            console.print("[yellow]DB에서 해당 공고를 찾지 못했습니다.[/yellow]")
            console.print("[dim]먼저 career-ops scan으로 수집 후 시도하세요.[/dim]")
    except Exception as exc:
        console.print(f"[red]tracker 업데이트 실패[/red]: {exc}")
