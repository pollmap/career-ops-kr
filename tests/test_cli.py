"""CLI smoke tests using click.testing.CliRunner."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from career_ops_kr.cli import cli


@pytest.fixture
def runner(tmp_path: Path) -> CliRunner:
    # Ensure CLI uses an isolated cwd so tests don't touch real data/
    os.chdir(tmp_path)
    return CliRunner()


def test_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "career-ops-kr" in result.output or "Commands" in result.output


def test_init_missing_files(runner: CliRunner, tmp_path: Path) -> None:
    # No user input → declines interview
    result = runner.invoke(cli, ["init"], input="n\n")
    assert result.exit_code == 0
    assert "missing" in result.output or "onboarding" in result.output.lower()


def test_list_empty(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "no jobs found" in result.output.lower() or "jobs" in result.output.lower()


def test_verify_clean(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["verify"])
    assert result.exit_code == 0
    assert "clean" in result.output.lower() or "verify" in result.output.lower()


def test_scan_dry(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["scan", "--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output.lower() or "scan" in result.output.lower()


def test_score_invalid_url(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["score", "invalid://bogus"])
    assert result.exit_code != 0
    assert "invalid" in result.output.lower()


def test_pipeline_small_no_gate(runner: CliRunner) -> None:
    # limit < 5 → no G4 gate
    result = runner.invoke(cli, ["pipeline", "--limit", "2"])
    assert result.exit_code == 0


def test_calendar_empty_jobs(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "out" / "deadlines.ics"
    result = runner.invoke(cli, ["calendar", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    content = out.read_bytes()
    assert b"BEGIN:VCALENDAR" in content
