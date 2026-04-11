"""Unit tests for JobKoreaChannel.

All tests run **offline** — every network call is monkeypatched.
The fixtures here mirror the real 잡코리아 list / detail DOM shapes
(as observed 2026-04) and exercise:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` — empty HTML returns ``[]``
    * ``list_jobs()`` — sample HTML yields >= 1 :class:`JobRecord`
    * ``list_jobs()`` — pagination respects ``pages`` kwarg
    * ``get_detail()`` — None URL returns None
    * ``get_detail()`` — sample HTML yields a record
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.jobkorea import (
    DEFAULT_HEADERS,
    LIST_URL,
    JobKoreaChannel,
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


# A stripped-down version of a real 잡코리아 joblist page. The key primary
# selector (``div.list-default tr.devloopArea td.tplTit a.link``) is present
# so the primary-path branch in ``_parse_list_html`` activates.
SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>잡코리아 채용정보</title></head>
<body>
  <div class="list-default">
    <table><tbody>
      <tr class="devloopArea">
        <td class="tplCo"><a class="name" href="/Corp/Recruit/Index/C000001">토스뱅크</a></td>
        <td class="tplTit">
          <a class="link" href="/Recruit/GI_Read/40000001">
            토스뱅크 디지털자산 리서치 신입 채용
          </a>
        </td>
        <td class="tplLocation"><span class="loc">서울 강남구</span></td>
        <td class="tplDeadline">~2026.05.17</td>
      </tr>
      <tr class="devloopArea">
        <td class="tplCo"><a class="name" href="/Corp/Recruit/Index/C000002">두나무</a></td>
        <td class="tplTit">
          <a class="link" href="/Recruit/GI_Read/40000002">
            두나무 블록체인 엔지니어 경력 모집
          </a>
        </td>
        <td class="tplLocation"><span class="loc">서울 성동구</span></td>
        <td class="tplDeadline">~2026.06.01</td>
      </tr>
      <tr class="devloopArea">
        <td class="tplCo"><a class="name" href="/Corp/Recruit/Index/C000003">카카오뱅크</a></td>
        <td class="tplTit">
          <a class="link" href="/Recruit/GI_Read/40000003">
            카카오뱅크 금융IT 인턴 공고
          </a>
        </td>
        <td class="tplLocation"><span class="loc">경기 성남시</span></td>
        <td class="tplDeadline">~2026.04.30</td>
      </tr>
    </tbody></table>
  </div>
</body></html>
"""


# Realistic-ish detail-page HTML with known selectors.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>토스뱅크 디지털자산 리서치 채용 | 잡코리아</title></head>
<body>
  <div class="company-label"><a href="/Corp/Recruit/Index/C000001">토스뱅크</a></div>
  <div class="tit-area"><h3 class="hd_3">토스뱅크 디지털자산 리서치 신입 채용</h3></div>
  <div class="recruit-info">
    <p>업무: 디지털자산 관련 리서치, 스테이블코인/STO 분석</p>
    <p>자격: 4년제 재학 또는 휴학생, 금융/경영/컴공 전공 우대</p>
    <p>지원 마감: 2026-05-17</p>
    <p>근무지: 서울 강남구 테헤란로</p>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> JobKoreaChannel:
    """Fresh JobKoreaChannel instance per test."""
    return JobKoreaChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import jobkorea

    assert hasattr(jobkorea, "JobKoreaChannel")
    assert hasattr(jobkorea, "LIST_URL")
    assert hasattr(jobkorea, "DEFAULT_HEADERS")
    assert jobkorea.JobKoreaChannel.name == "jobkorea"
    assert jobkorea.JobKoreaChannel.tier == 1
    assert jobkorea.JobKoreaChannel.default_legitimacy_tier == "T1"
    assert LIST_URL.startswith("https://www.jobkorea.co.kr")
    assert "User-Agent" in DEFAULT_HEADERS


def test_class_satisfies_channel_protocol(channel: JobKoreaChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "jobkorea"
    assert channel.tier == 1
    assert channel.backend == "requests"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_error(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 1})
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML fixture yields at least one valid JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 1})
    assert len(jobs) >= 1
    # All entries are JobRecords with the expected provenance.
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "jobkorea"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert job.title
        # URL absolutized against base
        assert str(job.source_url).startswith("https://www.jobkorea.co.kr/Recruit/GI_Read/")


def test_list_jobs_dedupes_across_pages(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Page N always returns the same HTML — dedup must kick in."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 5})
    # 3 unique cards across 5 duplicate pages.
    assert len(jobs) == 3
    # And every id is unique.
    ids = {j.id for j in jobs}
    assert len(ids) == 3


def test_list_jobs_extracts_deadlines(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one record should have a parsed deadline."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 1})
    assert any(j.deadline is not None for j in jobs), (
        "expected at least one deadline parsed from sample HTML"
    )


def test_list_jobs_infers_archetype(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Titles containing 인턴/신입/경력 should populate archetype."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 1})
    archetypes = {j.archetype for j in jobs if j.archetype}
    # sample has 신입/경력/인턴 exactly once each
    assert archetypes == {"ENTRY", "EXPERIENCED", "INTERN"}


def test_list_jobs_fetch_failure_returns_empty(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 responses must yield an empty result — NEVER fabricated data."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error page", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    jobs = channel.list_jobs(query={"pages": 1})
    assert jobs == []


def test_list_jobs_respects_keyword_query(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``keyword`` kwarg should route requests through the /Search/ endpoint."""
    captured_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        captured_urls.append(url)
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    channel.list_jobs(query={"keyword": "블록체인", "pages": 1})
    assert captured_urls, "expected at least one fetch"
    assert "/Search/" in captured_urls[0]
    assert "stext=" in captured_urls[0]


def test_list_jobs_pages_cap(channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """``pages`` larger than MAX_PAGES_HARD_CAP should be clamped."""
    from career_ops_kr.channels.jobkorea import MAX_PAGES_HARD_CAP

    call_count = {"n": 0}

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_count["n"] += 1
        # Return empty list HTML so pagination stops early (dedup + no new).
        return _FakeResponse(text="<html><body></body></html>", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    channel.list_jobs(query={"pages": 999})
    # Early-termination + cap: at most MAX_PAGES_HARD_CAP fetches, but in
    # practice the loop stops on page 2 (no new jobs after page 1 empty).
    assert call_count["n"] <= MAX_PAGES_HARD_CAP


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_fetch_failure_returns_none(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    result = channel.get_detail("https://www.jobkorea.co.kr/Recruit/GI_Read/99999999")
    assert result is None


def test_get_detail_parses_sample_html(
    channel: JobKoreaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML fixture yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobkorea.requests.get", fake_get)
    url = "https://www.jobkorea.co.kr/Recruit/GI_Read/40000001"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "토스뱅크" in record.org or "토스뱅크" in record.title
    assert "디지털자산" in record.description
    assert record.source_channel == "jobkorea"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0
    # Deadline "2026-05-17" should be parsed.
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5
    assert record.deadline.day == 17
