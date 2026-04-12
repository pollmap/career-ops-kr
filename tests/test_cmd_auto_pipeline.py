"""Tests for career-ops auto-pipeline command."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_auto_pipeline_dry_run(runner):
    """--dry-run → exit_code=0, 네트워크 없음."""
    from career_ops_kr.commands.auto_pipeline import auto_pipeline_cmd

    result = runner.invoke(auto_pipeline_cmd, ["--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output


def test_auto_pipeline_dry_run_shows_config(runner):
    """--dry-run → 설정값 출력 확인."""
    from career_ops_kr.commands.auto_pipeline import auto_pipeline_cmd

    result = runner.invoke(auto_pipeline_cmd, ["--dry-run", "--limit", "10", "--grade", "A"])
    assert result.exit_code == 0
    assert "10" in result.output
    assert "A" in result.output


def test_auto_pipeline_no_channels(runner):
    """채널 0건 → '수집된 공고 없음' 출력."""
    from career_ops_kr.commands.auto_pipeline import auto_pipeline_cmd

    with patch("career_ops_kr.channels.CHANNEL_REGISTRY", {}):
        result = runner.invoke(auto_pipeline_cmd, ["--source", "channels"])
    assert result.exit_code == 0
    assert "없음" in result.output or "완료" in result.output


def test_auto_pipeline_g4_abort(runner):
    """G4 게이트에서 'n' 입력 → aborted."""
    from career_ops_kr.commands.auto_pipeline import auto_pipeline_cmd
    from career_ops_kr.channels.base import JobRecord
    from datetime import date

    fake_jobs = [
        JobRecord(
            id=f"id{i:016d}",
            source_url=f"https://ex.com/{i}",
            source_channel="test",
            source_tier=1,
            org="테스트",
            title=f"인턴 {i}",
            archetype="TEST",
            deadline=date(2026, 12, 31),
            description="",
            legitimacy_tier="T1",
        )
        for i in range(6)
    ]

    mock_cls = MagicMock()
    mock_cls.return_value.list_jobs.return_value = fake_jobs
    mock_cls.tier = 1

    with patch("career_ops_kr.channels.CHANNEL_REGISTRY", {"test": mock_cls}):
        result = runner.invoke(auto_pipeline_cmd, [], input="n\n")
    assert "aborted" in result.output


def test_auto_pipeline_g4_runs(runner):
    """G4 게이트 통과 + 채점 실행."""
    from career_ops_kr.commands.auto_pipeline import auto_pipeline_cmd
    from career_ops_kr.channels.base import JobRecord
    from datetime import date

    fake_jobs = [
        JobRecord(
            id=f"id{i:016d}",
            source_url=f"https://ex.com/{i}",
            source_channel="test",
            source_tier=1,
            org="테스트",
            title=f"인턴 {i}",
            archetype="TEST",
            deadline=date(2026, 12, 31),
            description="",
            legitimacy_tier="T1",
        )
        for i in range(6)
    ]

    mock_cls = MagicMock()
    mock_cls.return_value.list_jobs.return_value = fake_jobs
    mock_cls.tier = 1

    mock_score = MagicMock(return_value={
        "url": "https://ex.com/0",
        "org": "테스트",
        "title": "인턴 0",
        "grade": "A",
        "total_score": 90,
        "qualifier_verdict": "PASS",
        "legitimacy": "T1",
        "archetype": "TEST",
        "deadline": "2026-12-31",
        "reasons": [],
    })

    with (
        patch("career_ops_kr.channels.CHANNEL_REGISTRY", {"test": mock_cls}),
        patch("career_ops_kr.mcp_server.tool_score_job", mock_score),
        patch("career_ops_kr.commands.auto_pipeline.get_store", return_value=None),
    ):
        result = runner.invoke(auto_pipeline_cmd, ["--limit", "3"], input="y\ny\n")
    assert result.exit_code == 0
    assert "완료" in result.output
