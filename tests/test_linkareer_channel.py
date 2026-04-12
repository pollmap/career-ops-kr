"""Unit tests for LinkareerChannel.

All tests run **offline** -- every network call is monkeypatched.
The fixtures mirror real 링커리어 list / detail DOM shapes and exercise:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` -- empty HTML returns ``[]``
    * ``list_jobs()`` -- sample HTML yields valid JobRecords
    * ``list_jobs()`` -- dedup across intern + activity pages
    * ``list_jobs()`` -- KEYWORDS filtering
    * ``list_jobs()`` -- archetype inference from URL path
    * ``list_jobs()`` -- fallback selector path
    * ``list_jobs()`` -- generic scan path
    * ``get_detail()`` -- None on fetch failure
    * ``get_detail()`` -- sample HTML yields a record
    * ``_infer_archetype()`` -- various inputs
    * ``_extract_org()`` -- separator-based extraction
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.linkareer import (
    BASE_URL,
    DEFAULT_HEADERS,
    LinkareerChannel,
)

# ---------------------------------------------------------------------------
# Fixtures -- fake HTTP responses
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


# Sample list HTML with 2 intern cards + 1 activity card using primary selectors.
SAMPLE_LIST_INTERN_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>링커리어 인턴</title></head>
<body>
  <div class="recruit-card">
    <a href="/intern/12345">
      토스뱅크 디지털자산 리서치 인턴
    </a>
    <span class="company-name">토스뱅크</span>
    <span>마감: 2026.05.17</span>
  </div>
  <div class="recruit-card">
    <a href="/intern/12346">
      두나무 블록체인 데이터 분석 인턴
    </a>
    <span class="company-name">두나무</span>
    <span>마감: 2026.06.01</span>
  </div>
</body></html>
"""

SAMPLE_LIST_ACTIVITY_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>링커리어 대외활동</title></head>
<body>
  <div class="activity-card">
    <a href="/activity/67890">
      KB금융그룹 핀테크 대외활동 모집
    </a>
    <span class="company-name">KB금융그룹</span>
    <span>마감: 2026.04.30</span>
  </div>
</body></html>
"""

# Fallback HTML -- no primary selectors, but href contains /intern/
SAMPLE_FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>링커리어</title></head>
<body>
  <div>
    <a href="/intern/99001">NH투자증권 금융 인턴십 모집</a>
  </div>
  <div>
    <a href="/activity/99002">신한은행 투자 대외활동 서포터즈</a>
  </div>
</body></html>
"""

# Generic scan HTML -- no known selectors, no /intern/ or /activity/ in href,
# but has /list/ path + KEYWORDS in text.
SAMPLE_GENERIC_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>링커리어</title></head>
<body>
  <div>
    <a href="/list/special-program/55555">미래에셋증권 데이터 분석 프로그램</a>
  </div>
</body></html>
"""

# Detail page HTML.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>토스뱅크 디지털자산 리서치 인턴 | 링커리어</title></head>
<body>
  <div class="company-name">토스뱅크</div>
  <h1 class="title">토스뱅크 디지털자산 리서치 인턴</h1>
  <div class="detail-body">
    <p>업무: 디지털자산 관련 리서치, 스테이블코인/STO 분석</p>
    <p>자격: 4년제 재학 또는 휴학생, 금융/경영/컴공 전공 우대</p>
    <p>지원 마감: 2026-05-17</p>
    <p>근무지: 서울 강남구 테헤란로</p>
  </div>
</body></html>
"""

# HTML with no KEYWORDS matches -- should yield 0 jobs.
SAMPLE_NO_KEYWORDS_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>링커리어</title></head>
<body>
  <div class="recruit-card">
    <a href="/intern/77777">CJ제일제당 식품 마케팅 인턴</a>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> LinkareerChannel:
    """Fresh LinkareerChannel instance per test."""
    return LinkareerChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import linkareer

    assert hasattr(linkareer, "LinkareerChannel")
    assert hasattr(linkareer, "BASE_URL")
    assert hasattr(linkareer, "INTERN_URL")
    assert hasattr(linkareer, "ACTIVITY_URL")
    assert hasattr(linkareer, "DEFAULT_HEADERS")
    assert hasattr(linkareer, "KEYWORDS")
    assert linkareer.LinkareerChannel.name == "linkareer"
    assert linkareer.LinkareerChannel.tier == 1
    assert linkareer.LinkareerChannel.default_legitimacy_tier == "T1"
    assert BASE_URL.startswith("https://linkareer.com")
    assert "User-Agent" in DEFAULT_HEADERS


def test_class_satisfies_channel_protocol(channel: LinkareerChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "linkareer"
    assert channel.tier == 1
    assert channel.backend == "requests"


def test_class_attributes() -> None:
    """Verify class-level attributes match spec."""
    assert LinkareerChannel.name == "linkareer"
    assert LinkareerChannel.tier == 1
    assert LinkareerChannel.backend == "requests"
    assert LinkareerChannel.default_rate_per_minute == 10
    assert LinkareerChannel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_error(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML fixture yields valid JobRecords from both pages."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "intern" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_ACTIVITY_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "linkareer"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert job.title


def test_list_jobs_fetches_both_urls(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both INTERN_URL and ACTIVITY_URL should be fetched."""
    captured_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        captured_urls.append(url)
        if "intern" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_ACTIVITY_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    channel.list_jobs()
    assert any("intern" in u for u in captured_urls)
    assert any("activity" in u for u in captured_urls)


def test_list_jobs_dedup_by_id(channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same HTML on both pages -- dedup must prevent duplicates."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate IDs found"


def test_list_jobs_keywords_filter(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cards without KEYWORDS should be filtered out."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_NO_KEYWORDS_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_archetype_from_url(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Archetype should be inferred from URL path (/intern/ -> INTERN)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "intern" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_ACTIVITY_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    archetypes = {j.archetype for j in jobs if j.archetype}
    assert "INTERN" in archetypes
    assert "ACTIVITY" in archetypes


def test_list_jobs_extracts_deadlines(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one record should have a parsed deadline."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "intern" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_ACTIVITY_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert any(j.deadline is not None for j in jobs), (
        "expected at least one deadline parsed from sample HTML"
    )


def test_list_jobs_fetch_failure_returns_empty(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 responses must yield an empty result."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error page", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_fallback_selector(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback selector path: no primary selectors, href matches /intern/."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_FALLBACK_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    for job in jobs:
        assert job.source_channel == "linkareer"


def test_list_jobs_generic_scan(channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic scan: no primary/fallback selectors, KEYWORDS + /list/ path."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_GENERIC_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    assert any("데이터" in j.title for j in jobs)


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_fetch_failure_returns_none(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    result = channel.get_detail("https://linkareer.com/intern/12345")
    assert result is None


def test_get_detail_parses_sample_html(
    channel: LinkareerChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML fixture yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.linkareer.requests.get", fake_get)
    url = "https://linkareer.com/intern/12345"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "토스뱅크" in record.org or "토스뱅크" in record.title
    assert "디지털자산" in record.description
    assert record.source_channel == "linkareer"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5
    assert record.deadline.day == 17


# ---------------------------------------------------------------------------
# _infer_archetype()
# ---------------------------------------------------------------------------


def test_infer_archetype_intern() -> None:
    assert LinkareerChannel._infer_archetype("토스 인턴 모집", "") == "INTERN"
    assert LinkareerChannel._infer_archetype("Intern program", "") == "INTERN"
    assert LinkareerChannel._infer_archetype("무관", "/intern/123") == "INTERN"


def test_infer_archetype_activity() -> None:
    assert LinkareerChannel._infer_archetype("대외활동 모집", "") == "ACTIVITY"
    assert LinkareerChannel._infer_archetype("무관", "/activity/456") == "ACTIVITY"


def test_infer_archetype_competition() -> None:
    assert LinkareerChannel._infer_archetype("금융 공모전 안내", "") == "COMPETITION"
    assert LinkareerChannel._infer_archetype("무관", "/competition/789") == "COMPETITION"


def test_infer_archetype_none() -> None:
    assert LinkareerChannel._infer_archetype("일반 채용 공고", "/jobs/100") is None


# ---------------------------------------------------------------------------
# _extract_org()
# ---------------------------------------------------------------------------


def test_extract_org_from_separator() -> None:
    org = LinkareerChannel._extract_org(None, "토스뱅크 | 디지털자산 인턴")
    assert org == "토스뱅크"


def test_extract_org_fallback() -> None:
    org = LinkareerChannel._extract_org(None, "인턴 프로그램 안내")
    assert org == "링커리어 게시물"
