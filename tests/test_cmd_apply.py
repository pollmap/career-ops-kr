"""Tests for career-ops apply command."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


_PASS_EVALUATION = {
    "url": "https://ex.com/job/1",
    "org": "테스트 기관",
    "title": "블록체인 인턴",
    "archetype": "BLOCKCHAIN_INTERN",
    "grade": "A",
    "total_score": 85,
    "qualifier_verdict": "PASS",
    "legitimacy": "T1",
    "deadline": "2026-12-31",
    "reasons": [],
}

_FAIL_EVALUATION = dict(_PASS_EVALUATION, qualifier_verdict="FAIL", grade="F")


def test_apply_checklist_output(runner):
    """체크리스트 및 G5 강조 포함 여부."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value=_PASS_EVALUATION):
        result = runner.invoke(apply_cmd, ["https://ex.com/job/1"], input="n\n")
    assert result.exit_code == 0
    assert "G5" in result.output
    assert "체크리스트" in result.output or "checklist" in result.output.lower()


def test_apply_fail_verdict_warning(runner):
    """FAIL verdict → 경고 출력."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAIL_EVALUATION):
        result = runner.invoke(apply_cmd, ["https://ex.com/job/1"], input="n\n")
    assert result.exit_code == 0
    assert "FAIL" in result.output


def test_apply_fail_verdict_abort(runner):
    """FAIL verdict + 'n' 입력 → aborted."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value=_FAIL_EVALUATION):
        result = runner.invoke(apply_cmd, ["https://ex.com/job/1"], input="n\n")
    assert "aborted" in result.output


def test_apply_tracker_register(runner):
    """'y' 입력 → tracker 등록 시도."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    mock_store = MagicMock()
    mock_store.search.return_value = []

    with (
        patch("career_ops_kr.mcp_server.tool_score_job", return_value=_PASS_EVALUATION),
        patch("career_ops_kr.commands.apply_cmd.get_store", return_value=mock_store),
    ):
        result = runner.invoke(apply_cmd, ["https://ex.com/job/1"], input="y\n")
    assert result.exit_code == 0


def test_apply_score_fail(runner):
    """채점 실패 → exit_code != 0."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value={"error": "not found"}):
        result = runner.invoke(apply_cmd, ["https://ex.com/fail"])
    assert result.exit_code != 0


def test_apply_g5_permanent_manual_message(runner):
    """G5 영구 수동 메시지 포함 확인."""
    from career_ops_kr.commands.apply_cmd import apply_cmd

    with patch("career_ops_kr.mcp_server.tool_score_job", return_value=_PASS_EVALUATION):
        result = runner.invoke(apply_cmd, ["https://ex.com/job/1"], input="n\n")
    assert "PERMANENT MANUAL" in result.output or "영구 수동" in result.output
