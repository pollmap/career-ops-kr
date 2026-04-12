"""Shared helpers for career-ops-kr CLI commands.

Defines console, path constants, and reusable helper functions so that
command modules never need to import from cli.py (avoids circular imports).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)

console = Console()

PROJECT_ROOT = Path.cwd()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
MODES_DIR = PROJECT_ROOT / "modes"


def print_standard_report(
    evaluation: dict[str, Any],
    con: Console | None = None,
) -> None:
    """CLAUDE.md 표준 6줄 리포트 패널 출력.

    Args:
        evaluation: tool_score_job() 반환 dict.
        con: 출력 콘솔. None이면 모듈 레벨 console 사용.
    """
    _con = con or console
    url = evaluation.get("url", "")
    legitimacy = evaluation.get("legitimacy") or "T5 미확인"
    archetype = evaluation.get("archetype") or "(미판정)"
    grade = evaluation.get("grade") or "(미평가)"
    total = evaluation.get("total_score")
    fit_grade_line = f"{grade}" + (f" ({total})" if total is not None else "")
    eligibility = evaluation.get("qualifier_verdict") or "(미판정)"
    deadline = evaluation.get("deadline") or "(미상)"
    org = evaluation.get("org") or ""
    title = evaluation.get("title") or ""
    reasons = evaluation.get("reasons") or []

    lines = [
        f"**URL:** {url}",
        f"**Legitimacy:** {legitimacy}",
        f"**Archetype:** {archetype}",
        f"**Fit Grade:** {fit_grade_line}",
        f"**Eligibility:** {eligibility}",
        f"**Deadline:** {deadline}",
    ]
    if org or title:
        lines.append(f"**Org / Title:** {org} / {title}")
    if reasons:
        lines.append("")
        lines.append("**Reasons:**")
        for r in reasons:
            lines.append(f"- {r}")

    _con.print(
        Panel.fit(
            "\n".join(lines),
            title="evaluation report",
            border_style="green",
        )
    )


def get_ai_client_or_fallback(
    api_key: str | None = None,
    con: Console | None = None,
) -> tuple[Any | None, str | None]:
    """OpenRouter 클라이언트 반환. 없으면 (None, None) + 경고.

    Returns:
        (client, model_id) 또는 API 키 미설정 시 (None, None).
    """
    _con = con or console
    try:
        from career_ops_kr.ai.client import DEFAULT_MODEL, get_client

        return get_client(api_key), DEFAULT_MODEL
    except (ImportError, ValueError) as exc:
        _con.print(f"[yellow]AI 비활성화[/yellow]: {exc}")
        return None, None


def load_profile() -> dict[str, Any]:
    """config/profile.yml 로드. 없거나 오류 시 빈 dict 반환."""
    try:
        import yaml

        p = CONFIG_DIR / "profile.yml"
        if p.exists():
            return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        logger.debug("load_profile failed: %s", exc)
    return {}


def get_store() -> Any | None:
    """SQLiteStore 인스턴스 반환. 실패하면 None."""
    try:
        from career_ops_kr.storage.sqlite_store import SQLiteStore

        return SQLiteStore(DATA_DIR / "jobs.db")
    except Exception as exc:
        logger.debug("get_store failed: %s", exc)
        return None


def grade_ge(grade: str, min_grade: str) -> bool:
    """grade >= min_grade 여부 (A > B > C > D > F 순서).

    Args:
        grade: 비교할 등급 문자열.
        min_grade: 최소 등급 문자열.

    Returns:
        grade가 min_grade 이상이면 True.
    """
    order = ["A", "B", "C", "D", "F"]
    try:
        return order.index(grade.upper()) <= order.index(min_grade.upper())
    except ValueError:
        return False
