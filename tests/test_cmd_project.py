"""Tests for career-ops project command."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


_FAKE_EVALUATION = {
    "url": "https://ex.com/job/1",
    "org": "두나무",
    "title": "블록체인 리서치 인턴",
    "archetype": "BLOCKCHAIN_INTERN",
    "grade": "A",
    "total_score": 88,
    "qualifier_verdict": "PASS",
    "legitimacy": "T1",
    "deadline": "2026-12-31",
    "reasons": [],
}


def test_project_no_ai(runner):
    """--no-ai → 스프린트 테이블 출력."""
    from career_ops_kr.commands.project_cmd import project_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.project_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(project_cmd, ["https://ex.com/job/1", "--no-ai"])
    assert result.exit_code == 0
    # 스프린트 테이블 또는 "week" 관련 내용 포함
    assert "스프린트" in result.output or "주차" in result.output or "week" in result.output.lower()


def test_project_weeks_option(runner):
    """--weeks N → N주 플랜 생성."""
    from career_ops_kr.commands.project_cmd import project_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.project_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(project_cmd, ["https://ex.com/job/1", "--no-ai", "--weeks", "2"])
    assert result.exit_code == 0


def test_project_api_key_missing(runner):
    """API 키 없음 → fallback으로 exit_code=0."""
    from career_ops_kr.commands.project_cmd import project_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.project_cmd.load_profile", return_value={}),
        patch(
            "career_ops_kr.commands.project_cmd.get_ai_client_or_fallback",
            return_value=(None, None),
        ),
    ):
        result = runner.invoke(project_cmd, ["https://ex.com/job/1"])
    assert result.exit_code == 0


def test_project_save_file(runner, tmp_path):
    """--save PATH → 파일 저장."""
    from career_ops_kr.commands.project_cmd import project_cmd

    out_file = tmp_path / "project.md"
    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.project_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(
            project_cmd, ["https://ex.com/job/1", "--no-ai", "--save", str(out_file)]
        )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "스프린트" in content or "주차" in content


def test_project_score_fail(runner):
    """채점 실패 → exit_code != 0."""
    from career_ops_kr.commands.project_cmd import project_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value={"error": "not found"}):
        result = runner.invoke(project_cmd, ["https://ex.com/fail"])
    assert result.exit_code != 0
