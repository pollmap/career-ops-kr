"""Tests for institutions CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_institutions_missing_config(runner, tmp_path):
    """config 없으면 에러 메시지."""
    from career_ops_kr.cli import cli

    with patch("career_ops_kr.cli.PROJECT_ROOT", tmp_path):
        result = runner.invoke(cli, ["institutions"])
    assert result.exit_code != 0 or "없음" in result.output


def test_institutions_dry_run_import():
    """institutions_cmd imports cleanly."""
    from career_ops_kr.cli import institutions_cmd
    assert institutions_cmd is not None


def test_fuzzy_match_exact():
    """Exact substring match works."""
    # Import the function from cli module scope — it's a closure inside institutions_cmd
    # so we test the logic directly
    from fuzzywuzzy import fuzz
    assert fuzz.partial_ratio("메리츠증권", "메리츠증권") == 100
    assert fuzz.partial_ratio("메리츠증권", "메리츠증권 주식회사") >= 60
    assert fuzz.partial_ratio("토스", "토스뱅크") >= 60


def test_fuzzy_match_rejects_noise():
    """Unrelated orgs rejected by fuzzy matching."""
    from fuzzywuzzy import fuzz
    # "저축은행중앙회" should NOT match "OO보험설계사"
    assert fuzz.partial_ratio("저축은행중앙회", "보험설계사 모집") < 60
    # But should match "저축은행"
    assert fuzz.partial_ratio("저축은행중앙회", "SBI저축은행") >= 60
