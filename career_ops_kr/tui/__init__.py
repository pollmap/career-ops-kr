"""Textual TUI dashboard for career-ops-kr.

Optional dependency: ``textual``. Import is guarded so the package
stays importable (and the CLI keeps working) even when textual is
not installed.  Install with::

    pip install 'career-ops-kr[tui]'
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["TEXTUAL_AVAILABLE", "CareerOpsApp", "run_tui"]

CareerOpsApp: Any = None
TEXTUAL_AVAILABLE: bool = False


def run_tui(db_path: Path | None = None) -> None:
    """Launch the TUI dashboard (raises if textual not installed)."""
    if not TEXTUAL_AVAILABLE:
        raise ImportError(
            "textual 패키지가 필요합니다. 설치: pip install 'career-ops-kr[tui]'"
        )
    from career_ops_kr.tui.app import run_tui as _real_run_tui

    _real_run_tui(db_path)


try:
    from career_ops_kr.tui.app import CareerOpsApp as _CareerOpsApp

    CareerOpsApp = _CareerOpsApp
    TEXTUAL_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on optional dep
    pass
