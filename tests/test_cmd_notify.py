"""Tests for career-ops notify command."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_notify_test_no_webhook(runner):
    """webhook 없이 --test → log-only 모드."""
    from career_ops_kr.commands.notify_cmd import notify_cmd

    with (
        patch("career_ops_kr.commands.notify_cmd.load_profile", return_value={}),
        patch.dict("os.environ", {}, clear=False),
    ):
        # DISCORD_WEBHOOK_URL 환경변수 제거
        import os
        old = os.environ.pop("DISCORD_WEBHOOK_URL", None)
        try:
            result = runner.invoke(notify_cmd, ["--test"])
        finally:
            if old is not None:
                os.environ["DISCORD_WEBHOOK_URL"] = old

    assert result.exit_code == 0
    assert "ping" in result.output.lower() or "log-only" in result.output.lower()


def test_notify_webhook_param(runner):
    """--webhook 파라미터로 DiscordNotifier 초기화."""
    from career_ops_kr.commands.notify_cmd import notify_cmd

    mock_notifier = MagicMock()
    mock_notifier.test_connection.return_value = True

    with (
        patch("career_ops_kr.commands.notify_cmd.load_profile", return_value={}),
        patch(
            "career_ops_kr.notifier.discord_push.DiscordNotifier",
            return_value=mock_notifier,
        ),
    ):
        result = runner.invoke(notify_cmd, ["--test", "--webhook", "https://discord.com/test"])

    assert result.exit_code == 0
    assert "OK" in result.output or "ping" in result.output.lower()


def test_notify_no_db(runner):
    """DB 없음 → 경고 메시지 (--test 없이)."""
    from career_ops_kr.commands.notify_cmd import notify_cmd

    with (
        patch("career_ops_kr.commands.notify_cmd.load_profile", return_value={}),
        patch("career_ops_kr.commands.notify_cmd.get_store", return_value=None),
    ):
        result = runner.invoke(notify_cmd, [])
    assert result.exit_code == 0
    assert "없음" in result.output or "DB" in result.output


def test_notify_summary_flag(runner):
    """--summary → notify_batch_summary 호출."""
    from career_ops_kr.commands.notify_cmd import notify_cmd

    mock_store = MagicMock()
    mock_store.get_stats.return_value = {"total": 10}
    mock_notifier = MagicMock()

    with (
        patch("career_ops_kr.commands.notify_cmd.load_profile", return_value={}),
        patch("career_ops_kr.commands.notify_cmd.get_store", return_value=mock_store),
        patch(
            "career_ops_kr.notifier.discord_push.DiscordNotifier",
            return_value=mock_notifier,
        ),
    ):
        result = runner.invoke(notify_cmd, ["--summary"])

    assert result.exit_code == 0
    mock_notifier.notify_batch_summary.assert_called_once()
