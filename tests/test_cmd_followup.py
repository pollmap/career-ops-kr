"""Tests for career-ops followup command."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


_FAKE_EVALUATION = {
    "url": "https://ex.com/job/1",
    "org": "신한투자증권",
    "title": "블록체인 인턴",
    "archetype": "BLOCKCHAIN_INTERN",
    "grade": "A",
    "total_score": 85,
    "qualifier_verdict": "PASS",
    "legitimacy": "T1",
    "deadline": "2026-12-31",
    "reasons": [],
}


def test_followup_no_ai(runner):
    """--no-ai → org명이 출력에 포함."""
    from career_ops_kr.commands.followup_cmd import followup_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.followup_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(followup_cmd, ["https://ex.com/job/1", "--no-ai"])
    assert result.exit_code == 0
    assert "신한투자증권" in result.output


def test_followup_stages(runner):
    """모든 stage에서 정상 동작."""
    from career_ops_kr.commands.followup_cmd import followup_cmd

    for stage in ["applied", "interviewed", "rejected"]:
        with (
            patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
            patch("career_ops_kr.commands.followup_cmd.load_profile", return_value={}),
        ):
            result = runner.invoke(followup_cmd, ["https://ex.com/job/1", "--no-ai", "--stage", stage])
        assert result.exit_code == 0, f"stage={stage} failed: {result.output}"


def test_followup_api_key_missing(runner):
    """API 키 없음 → fallback으로 exit_code=0."""
    from career_ops_kr.commands.followup_cmd import followup_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.followup_cmd.load_profile", return_value={}),
        patch(
            "career_ops_kr.commands.followup_cmd.get_ai_client_or_fallback",
            return_value=(None, None),
        ),
    ):
        result = runner.invoke(followup_cmd, ["https://ex.com/job/1"])
    assert result.exit_code == 0


def test_followup_save_file(runner, tmp_path):
    """--save PATH → 파일 저장."""
    from career_ops_kr.commands.followup_cmd import followup_cmd

    out_file = tmp_path / "followup.md"
    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.followup_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(
            followup_cmd, ["https://ex.com/job/1", "--no-ai", "--save", str(out_file)]
        )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "신한투자증권" in content or "이메일" in content


def test_followup_score_fail(runner):
    """채점 실패 → exit_code != 0."""
    from career_ops_kr.commands.followup_cmd import followup_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value={"error": "not found"}):
        result = runner.invoke(followup_cmd, ["https://ex.com/fail"])
    assert result.exit_code != 0
