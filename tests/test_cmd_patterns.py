"""Tests for career_ops_kr.patterns.analyzer and patterns CLI command."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_analyze_empty_db():
    """빈 DB → total_analyzed=0, patterns 필드 존재."""
    from career_ops_kr.patterns.analyzer import analyze

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = analyze(days=30)

    assert result["total_analyzed"] == 0
    assert "patterns" in result
    assert isinstance(result["patterns"], list)
    assert len(result["patterns"]) > 0


def test_analyze_returns_required_keys():
    """analyze() 반환 dict에 필수 키 모두 존재."""
    from career_ops_kr.patterns.analyzer import analyze

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = analyze(days=30)

    required_keys = [
        "days", "period", "total_analyzed", "by_status", "by_grade",
        "by_archetype", "rejection_rate", "avg_days_to_deadline", "top_orgs", "patterns",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"


def test_tool_run_patterns_basic():
    """days=7 파라미터, 'days' 키 존재."""
    from career_ops_kr.patterns.analyzer import analyze

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = analyze(days=7)

    assert result["days"] == 7
    assert "days" in result


def test_analyze_with_jobs():
    """실제 job 데이터 → 통계 계산 확인."""
    from career_ops_kr.patterns.analyzer import analyze
    from datetime import datetime

    fake_jobs = [
        {
            "id": f"id{i:016d}",
            "org": f"기관{i % 3}",
            "status": ["inbox", "applying", "rejected"][i % 3],
            "fit_grade": ["A", "B", "C"][i % 3],
            "archetype": ["BLOCKCHAIN_INTERN", "FINTECH", "RESEARCH"][i % 3],
            "deadline": "2026-06-30",
            "scanned_at": datetime.now().isoformat(),
        }
        for i in range(9)
    ]

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=fake_jobs):
        result = analyze(days=30)

    assert result["total_analyzed"] == 9
    assert result["by_status"]["inbox"] == 3
    assert result["by_status"]["applying"] == 3
    assert result["by_status"]["rejected"] == 3


def test_analyze_rejection_rate():
    """거절율 계산 검증."""
    from career_ops_kr.patterns.analyzer import analyze
    from datetime import datetime

    fake_jobs = [
        {"id": "a", "org": "A", "status": "applying", "scanned_at": datetime.now().isoformat()},
        {"id": "b", "org": "B", "status": "applying", "scanned_at": datetime.now().isoformat()},
        {"id": "c", "org": "C", "status": "rejected", "scanned_at": datetime.now().isoformat()},
        {"id": "d", "org": "D", "status": "rejected", "scanned_at": datetime.now().isoformat()},
    ]

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=fake_jobs):
        result = analyze(days=30)

    # rejected 2 / applied 2 = 1.0
    assert result["rejection_rate"] == 1.0


def test_patterns_cmd_empty_db(runner):
    """CLI: 빈 DB → exit_code=0."""
    from career_ops_kr.commands.patterns_cmd import patterns_cmd

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = runner.invoke(patterns_cmd, [])
    assert result.exit_code == 0


def test_patterns_cmd_json_output(runner):
    """CLI: --json → JSON 출력."""
    import json
    from career_ops_kr.commands.patterns_cmd import patterns_cmd

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = runner.invoke(patterns_cmd, ["--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "days" in data


def test_patterns_cmd_days_option(runner):
    """CLI: --days N → 출력에 반영."""
    from career_ops_kr.commands.patterns_cmd import patterns_cmd

    with patch("career_ops_kr.patterns.analyzer._load_jobs", return_value=[]):
        result = runner.invoke(patterns_cmd, ["--days", "7"])
    assert result.exit_code == 0


def test_patterns_package_importable():
    """career_ops_kr.patterns 패키지 임포트 가능."""
    import career_ops_kr.patterns as p

    assert hasattr(p, "analyze")
