"""Textual screens for the career-ops-kr TUI."""

from __future__ import annotations

from career_ops_kr.tui.screens.calendar import CalendarScreen
from career_ops_kr.tui.screens.dashboard import DashboardScreen
from career_ops_kr.tui.screens.job_detail import JobDetailScreen
from career_ops_kr.tui.screens.jobs_list import JobsListScreen
from career_ops_kr.tui.screens.patterns import PatternsScreen

__all__ = [
    "CalendarScreen",
    "DashboardScreen",
    "JobDetailScreen",
    "JobsListScreen",
    "PatternsScreen",
]
