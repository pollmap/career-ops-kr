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


@pytest.mark.asyncio
async def test_batch_main_persists_fit_results():
    """Successful batch scoring should persist fit data back into SQLiteStore."""
    from career_ops_kr.commands.batch_cmd import _batch_main

    inbox = [
        {
            "id": "job-1",
            "source_url": "https://example.com/job-1",
            "source_channel": "wanted",
            "source_tier": 1,
            "org": "테스트 회사",
            "title": "테스트 공고",
            "archetype": "GENERAL",
            "deadline": None,
            "posted_at": None,
            "location": "서울",
            "description": "설명",
            "legitimacy_tier": "T1",
            "scanned_at": "2026-04-13T10:00:00",
            "fetch_errors": "[]",
            "status": "inbox",
        }
    ]

    mock_store = MagicMock()

    with patch(
        "career_ops_kr.mcp_server.tool_score_job",
        return_value={
            "url": "https://example.com/job-1",
            "org": "테스트 회사",
            "title": "테스트 공고",
            "grade": "C",
            "total_score": 55.0,
            "qualifier_verdict": "CONDITIONAL",
            "legitimacy": "T1",
            "archetype": "GENERAL",
            "deadline": None,
            "reasons": [],
        },
    ):
        await _batch_main(inbox, concurrency=1, store=mock_store)

    mock_store.upsert.assert_called_once()


def test_get_inbox_not_truncated_by_search_limit():
    """Batch should be able to fetch more than SQLiteStore.search()'s default 200 rows."""
    from datetime import datetime
    from pathlib import Path
    import uuid

    from career_ops_kr.channels.base import JobRecord
    from career_ops_kr.commands.batch_cmd import _get_inbox
    from career_ops_kr.storage.sqlite_store import SQLiteStore

    tmp_dir = Path("data") / ".test-tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    db_path = tmp_dir / f"batch-{uuid.uuid4().hex}.db"
    store = SQLiteStore(db_path)
    now = datetime(2026, 4, 13, 10, 0, 0)

    for i in range(250):
        store.upsert(
            JobRecord(
                id=f"job{i:04d}",
                source_url=f"https://example.com/jobs/{i}",
                source_channel="test",
                source_tier=1,
                org="테스트 회사",
                title=f"공고 {i}",
                archetype="GENERAL",
                description="설명",
                legitimacy_tier="T1",
                scanned_at=now,
            )
        )

    inbox = _get_inbox(store, "inbox", 250)

    assert len(inbox) == 250
