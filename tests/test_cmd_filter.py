"""Tests for career-ops filter command — QualifierEngine wrapper."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture()
def runner():
    return CliRunner()


def test_filter_direct_text_pass(runner):
    """학력 무관 텍스트 → PASS 판정."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, ["학력 무관 전공 무관 재학생 가능 인턴"])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_filter_fail_verdict(runner):
    """졸업자/전공필수 → FAIL 판정."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, ["졸업자 대상, 컴퓨터공학 전공 필수, 경력 2년 이상"])
    assert result.exit_code == 0
    assert "FAIL" in result.output


def test_filter_json_output(runner):
    """--json 플래그 → JSON 출력."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, ["학력 무관", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "verdict" in data
    assert "reasons" in data


def test_filter_file_input(runner, tmp_path):
    """--file 플래그 → 파일 내용 판정."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    job_file = tmp_path / "job.txt"
    job_file.write_text("학력 무관 전공 무관 체험형 인턴", encoding="utf-8")

    result = runner.invoke(filter_cmd, ["--file", str(job_file)])
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_filter_no_args(runner):
    """인수 없이 호출 → exit code != 0."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, [])
    assert result.exit_code != 0


def test_filter_confidence_flag(runner):
    """--confidence 플래그 → 신뢰도 포함 출력."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, ["학력 무관", "--confidence"])
    assert result.exit_code == 0


def test_filter_json_confidence(runner):
    """--json --confidence → confidence 필드 존재."""
    from career_ops_kr.commands.filter_cmd import filter_cmd

    result = runner.invoke(filter_cmd, ["학력 무관", "--json", "--confidence"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "confidence" in data
