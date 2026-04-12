"""Tests for career-ops interview-prep command."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


_FAKE_EVALUATION = {
    "url": "https://ex.com/job/1",
    "org": "테스트 기관",
    "title": "블록체인 인턴",
    "archetype": "BLOCKCHAIN_INTERN",
    "grade": "A",
    "total_score": 85,
    "qualifier_verdict": "PASS",
    "legitimacy": "T1",
    "deadline": "2026-12-31",
    "reasons": ["블록체인 우대"],
}


def test_interview_no_ai_fallback(runner):
    """--no-ai → fallback 템플릿, 'S (상황)' 포함."""
    from career_ops_kr.commands.interview_cmd import interview_prep_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.interview_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(interview_prep_cmd, ["https://ex.com/job/1", "--no-ai"])
    assert result.exit_code == 0
    assert "S (상황)" in result.output


def test_interview_api_key_missing(runner):
    """API 키 없음 → graceful degrade (exit_code=0, fallback 사용)."""
    from career_ops_kr.commands.interview_cmd import interview_prep_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.interview_cmd.load_profile", return_value={}),
        patch(
            "career_ops_kr.commands.interview_cmd.get_ai_client_or_fallback",
            return_value=(None, None),
        ),
    ):
        result = runner.invoke(interview_prep_cmd, ["https://ex.com/job/1"])
    assert result.exit_code == 0
    # fallback 템플릿으로 STAR 가이드 출력
    assert "Q1" in result.output or "상황" in result.output


def test_interview_score_fail(runner):
    """채점 실패 → exit_code != 0."""
    from career_ops_kr.commands.interview_cmd import interview_prep_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value={"error": "not found"}):
        result = runner.invoke(interview_prep_cmd, ["https://ex.com/fail"])
    assert result.exit_code != 0


def test_interview_questions_count(runner):
    """--questions N → N개 질문 생성."""
    from career_ops_kr.commands.interview_cmd import interview_prep_cmd

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.interview_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(interview_prep_cmd, ["https://ex.com/job/1", "--no-ai", "--questions", "3"])
    assert result.exit_code == 0
    # Q1, Q2, Q3 모두 출력
    assert "Q1" in result.output
    assert "Q3" in result.output


def test_interview_save_file(runner, tmp_path):
    """--save PATH → 마크다운 파일 저장."""
    from career_ops_kr.commands.interview_cmd import interview_prep_cmd

    out_file = tmp_path / "interview.md"
    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAKE_EVALUATION),
        patch("career_ops_kr.commands.interview_cmd.load_profile", return_value={}),
    ):
        result = runner.invoke(
            interview_prep_cmd,
            ["https://ex.com/job/1", "--no-ai", "--save", str(out_file)],
        )
    assert result.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "면접" in content or "Q1" in content
