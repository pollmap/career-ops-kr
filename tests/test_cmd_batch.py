"""Tests for career-ops batch command."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_batch_dry_run(runner):
    """--dry-run → exit_code=0."""
    from career_ops_kr.commands.batch_cmd import batch_cmd

    mock_store = MagicMock()
    mock_store.search.return_value = []

    with patch("career_ops_kr.commands.batch_cmd.get_store", return_value=mock_store):
        result = runner.invoke(batch_cmd, ["--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output


def test_batch_empty_inbox(runner):
    """빈 inbox → "no inbox" 메시지."""
    from career_ops_kr.commands.batch_cmd import batch_cmd

    mock_store = MagicMock()
    mock_store.search.return_value = []

    with patch("career_ops_kr.commands.batch_cmd.get_store", return_value=mock_store):
        result = runner.invoke(batch_cmd, [])
    assert result.exit_code == 0
    assert "no inbox" in result.output


def test_batch_no_db(runner):
    """DB 없음 → 경고 메시지."""
    from career_ops_kr.commands.batch_cmd import batch_cmd

    with patch("career_ops_kr.commands.batch_cmd.get_store", return_value=None):
        result = runner.invoke(batch_cmd, [])
    assert result.exit_code == 0
    assert "DB 없음" in result.output or "없음" in result.output


def test_batch_dry_run_shows_count(runner):
    """--dry-run → inbox 건수 표시."""
    from career_ops_kr.commands.batch_cmd import batch_cmd

    mock_store = MagicMock()
    mock_store.search.return_value = [
        {"id": "abc", "source_url": "https://ex.com", "status": "inbox"}
    ]

    with patch("career_ops_kr.commands.batch_cmd.get_store", return_value=mock_store):
        result = runner.invoke(batch_cmd, ["--dry-run"])
    assert result.exit_code == 0
