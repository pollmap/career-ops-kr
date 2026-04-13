"""Targeted tests for MCP tool wrappers."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from career_ops_kr import mcp_server


def test_query_by_archetype_filters_only_by_archetype(monkeypatch) -> None:
    """The MCP wrapper should not force a text keyword match."""

    class FakeStore:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def search(self, keyword: str, archetype: str | None = None):
            assert keyword == ""
            assert archetype == "GENERAL"
            return [{"id": "job-1", "archetype": archetype}]

    def fake_safe_import(dotted: str, attr: str | None = None):
        if dotted == "career_ops_kr.storage.sqlite_store" and attr == "SQLiteStore":
            return FakeStore
        raise AssertionError(f"unexpected import request: {dotted}.{attr}")

    monkeypatch.setattr(mcp_server, "_safe_import", fake_safe_import)

    result = mcp_server.tool_query_by_archetype("GENERAL")

    assert result == [{"id": "job-1", "archetype": "GENERAL"}]


def test_score_job_serializes_grade_as_plain_letter(monkeypatch) -> None:
    """MCP output should use grade values that downstream storage can filter."""

    class FakeVerdict(Enum):
        CONDITIONAL = "CONDITIONAL"

    class FakeGrade(Enum):
        C = "C"

    class FakeRecord:
        org = "테스트 회사"
        title = "테스트 공고"
        archetype = "GENERAL"
        legitimacy_tier = "T1"
        deadline = None
        description = "테스트 설명"
        location = "서울"
        source_url = "https://example.com/job"

    class FakeChannel:
        def get_detail(self, url: str):
            return FakeRecord()

    class FakeQualifierResult:
        verdict = FakeVerdict.CONDITIONAL

    class FakeQualifierEngine:
        def __init__(self, path: Path) -> None:
            self.path = path

        def evaluate(self, text: str):
            return FakeQualifierResult()

    class FakeScoreBreakdown:
        grade = FakeGrade.C
        total = 55.0
        reasons = ["role_fit=40 (UNKNOWN)"]

    class FakeFitScorer:
        def __init__(self, weights_path: Path, profile_path: Path) -> None:
            self.weights_path = weights_path
            self.profile_path = profile_path

        def score(self, job, qualifier_result, archetype):
            return FakeScoreBreakdown()

    class FakeChannelsModule:
        CHANNEL_REGISTRY = {"fake": FakeChannel}

    def fake_safe_import(dotted: str, attr: str | None = None):
        if dotted == "career_ops_kr.channels":
            return FakeChannelsModule
        if dotted == "career_ops_kr.qualifier.engine" and attr == "QualifierEngine":
            return FakeQualifierEngine
        if dotted == "career_ops_kr.scorer.fit_score" and attr == "FitScorer":
            return FakeFitScorer
        raise AssertionError(f"unexpected import request: {dotted}.{attr}")

    monkeypatch.setattr(mcp_server, "_safe_import", fake_safe_import)

    result = mcp_server.tool_score_job("https://example.com/job")

    assert result["grade"] == "C"


def test_list_eligible_uses_minimum_grade_threshold(monkeypatch) -> None:
    """MCP list_eligible should honor its documented minimum-grade semantics."""

    class FakeStore:
        def __init__(self, db_path: Path) -> None:
            self.db_path = db_path

        def list_at_or_above_grade(self, grade: str):
            assert grade == "C"
            return [{"id": "job-b", "fit_grade": "B"}, {"id": "job-c", "fit_grade": "C"}]

        def list_by_grade(self, grade: str):
            raise AssertionError("exact-grade lookup should not be used")

    def fake_safe_import(dotted: str, attr: str | None = None):
        if dotted == "career_ops_kr.storage.sqlite_store" and attr == "SQLiteStore":
            return FakeStore
        raise AssertionError(f"unexpected import request: {dotted}.{attr}")

    monkeypatch.setattr(mcp_server, "_safe_import", fake_safe_import)

    result = mcp_server.tool_list_eligible("C")

    assert result == [
        {"id": "job-b", "fit_grade": "B"},
        {"id": "job-c", "fit_grade": "C"},
    ]
