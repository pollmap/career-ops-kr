"""Unit tests for MiraeNaeilChannel.

All tests run **offline** — every network call is monkeypatched.
The fixtures here mirror the real ``work.go.kr/experi/`` DOM shapes
(as inferred 2026-04) and exercise:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` — empty HTML returns ``[]``
    * ``list_jobs()`` — sample HTML yields >= 3 :class:`JobRecord`
    * ``list_jobs()`` — LANDING empty → ALT URL fallback path
    * ``list_jobs()`` — archetype inference (인턴형/프로젝트형/체험형)
    * ``list_jobs()`` — org / legitimacy tier propagation
    * ``list_jobs()`` — fetch failure returns empty
    * ``get_detail()`` — None URL returns None
    * ``get_detail()`` — sample HTML yields a record
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.mirae_naeil import (
    ALT_LIST_URL,
    DEFAULT_HEADERS,
    LANDING_URL,
    ORG,
    MiraeNaeilChannel,
)

# ---------------------------------------------------------------------------
# Fixtures — fake HTTP responses
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for :class:`requests.Response`."""

    def __init__(
        self,
        text: str = "",
        status_code: int = 200,
        encoding: str | None = "utf-8",
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = encoding


# A stripped-down version of a plausible work.go.kr/experi/ landing page.
# At least one PRIMARY_SELECTORS entry (``div.list-card a``) matches so the
# primary-path branch in ``_parse_list_html`` activates.
SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>미래내일 일경험 | 워크넷</title></head>
<body>
  <div class="list-card">
    <a href="/experi/detail/1001">삼성SDS 미래내일 일경험 인턴형 모집 (마감 2026.05.30)</a>
    <a href="/experi/detail/1002">KB금융 체험형 청년 일경험 프로그램</a>
    <a href="/experi/detail/1003">핀테크 스타트업 프로젝트형 일경험</a>
    <a href="/experi/detail/1004">일반 정규직 채용 공고</a>
  </div>
</body></html>
"""


# Realistic-ish detail-page HTML — uses the ``h1.title`` selector that the
# parser walks first.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>삼성SDS 미래내일 일경험 인턴형 모집 | 워크넷</title></head>
<body>
  <div class="recruit-detail">
    <h1>삼성SDS 미래내일 일경험 인턴형 모집</h1>
    <p>운영기관: 미래내일 일경험</p>
    <p>지원마감: 2026-05-30</p>
    <p>직무: 클라우드 / 데이터 / 보안</p>
    <p>대상: 만 34세 이하 미취업 청년</p>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> MiraeNaeilChannel:
    """Fresh MiraeNaeilChannel instance per test."""
    return MiraeNaeilChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import mirae_naeil

    assert hasattr(mirae_naeil, "MiraeNaeilChannel")
    assert hasattr(mirae_naeil, "LANDING_URL")
    assert hasattr(mirae_naeil, "ALT_LIST_URL")
    assert hasattr(mirae_naeil, "DEFAULT_HEADERS")
    assert hasattr(mirae_naeil, "ORG")
    assert mirae_naeil.MiraeNaeilChannel.name == "mirae_naeil"
    assert mirae_naeil.MiraeNaeilChannel.tier == 2
    assert mirae_naeil.MiraeNaeilChannel.default_legitimacy_tier == "T1"
    assert LANDING_URL.startswith("https://www.work.go.kr/experi")
    assert ALT_LIST_URL.startswith("https://www.work.go.kr/experi")
    assert "User-Agent" in DEFAULT_HEADERS
    assert ORG == "미래내일 일경험"


def test_class_satisfies_channel_protocol(channel: MiraeNaeilChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "mirae_naeil"
    assert channel.tier == 2
    assert channel.backend == "requests"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_connection_error(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML fixture yields >= 3 valid JobRecords (TYPE_KEYWORDS match)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    # 3 cards mention 인턴형/체험형/프로젝트형 (TYPE_KEYWORDS); the 4th
    # ("일반 정규직 채용 공고") is correctly excluded by the keyword filter.
    assert len(jobs) >= 3
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "mirae_naeil"
        assert job.source_tier == 2
        assert job.legitimacy_tier == "T1"
        assert job.title
        assert str(job.source_url).startswith("https://www.work.go.kr/experi/")


def test_list_jobs_excludes_non_type_anchor(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generic '정규직 채용 공고' anchor must NOT become a JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    titles = [j.title for j in jobs]
    # 정규직 anchor 는 TYPE_KEYWORDS 미매치 → 제외
    assert not any("정규직" in t for t in titles)


def test_list_jobs_falls_back_to_alt_url(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LANDING returns empty HTML → channel must retry against ALT_LIST_URL."""
    call_log: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_log.append(url)
        if url == LANDING_URL:
            return _FakeResponse(text="<html><body></body></html>", status_code=200)
        # ALT URL serves the real fixture
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    # Both URLs hit exactly once (in order).
    assert call_log == [LANDING_URL, ALT_LIST_URL]
    # ALT path actually delivered records.
    assert len(jobs) >= 3


def test_list_jobs_intern_type_archetype(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``인턴형`` titles should map to archetype == 'INTERN_TYPE'."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    intern_type = [j for j in jobs if j.archetype == "INTERN_TYPE"]
    assert len(intern_type) >= 1
    assert any("인턴형" in j.title for j in intern_type)


def test_list_jobs_project_type_archetype(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``프로젝트형`` titles should map to archetype == 'PROJECT_TYPE'."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    project_type = [j for j in jobs if j.archetype == "PROJECT_TYPE"]
    assert len(project_type) >= 1
    assert any("프로젝트형" in j.title for j in project_type)


def test_list_jobs_experience_type_archetype(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``체험형`` titles should map to archetype == 'EXPERIENCE_TYPE'."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    experience_type = [j for j in jobs if j.archetype == "EXPERIENCE_TYPE"]
    assert len(experience_type) >= 1
    assert any("체험형" in j.title for j in experience_type)


def test_list_jobs_org_is_mirae_naeil(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every record's org must be the constant ``ORG`` (미래내일 일경험)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs, "expected non-empty job list"
    assert all(j.org == ORG for j in jobs)


def test_list_jobs_legitimacy_t1(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """미래내일 is a 정부 공식 program — every record gets T1."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs
    assert all(j.legitimacy_tier == "T1" for j in jobs)


def test_list_jobs_fetch_failure_returns_empty(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 responses must yield an empty result — NEVER fabricated data."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error page", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_fetch_failure_returns_none(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    result = channel.get_detail("https://www.work.go.kr/experi/detail/99999")
    assert result is None


def test_get_detail_parses_sample_html(
    channel: MiraeNaeilChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML fixture yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mirae_naeil.requests.get", fake_get)
    url = "https://www.work.go.kr/experi/detail/1001"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "삼성SDS" in record.title
    assert record.org == ORG
    assert record.source_channel == "mirae_naeil"
    assert record.source_tier == 2
    assert record.legitimacy_tier == "T1"
    assert record.archetype == "INTERN_TYPE"
    assert record.raw_html is not None and len(record.raw_html) > 0
    # Deadline ``2026-05-30`` should be parsed from the body.
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5
    assert record.deadline.day == 30
