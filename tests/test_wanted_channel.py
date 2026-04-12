"""Unit tests for WantedChannel.

All tests run **offline** -- every network call is monkeypatched.
The fixtures simulate the Wanted JSON API (primary) and HTML fallback
paths, exercising:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` -- API path with JSON data
    * ``list_jobs()`` -- API failure -> HTML fallback
    * ``list_jobs()`` -- empty responses -> ``[]``
    * ``list_jobs()`` -- dedup across SEARCH_QUERIES
    * ``list_jobs()`` -- keyword override
    * ``get_detail()`` -- success and failure
    * archetype inference (인턴/신입/경력)
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.wanted import (
    BASE_URL,
    DEFAULT_HEADERS,
    SEARCH_QUERIES,
    WantedChannel,
)

# ---------------------------------------------------------------------------
# Fixtures -- fake HTTP responses
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for :class:`requests.Response` with JSON support."""

    def __init__(
        self,
        text: str = "",
        status_code: int = 200,
        encoding: str | None = "utf-8",
        json_data: Any = None,
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = encoding
        self._json_data = json_data

    def json(self) -> Any:
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON data")


# Simulated API JSON response -- mirrors /api/v4/jobs structure.
SAMPLE_API_JSON = {
    "data": [
        {
            "id": 100001,
            "position": "블록체인 플랫폼 엔지니어 신입",
            "company": {"name": "두나무"},
            "due_time": "2026-05-31",
        },
        {
            "id": 100002,
            "position": "디지털자산 리서치 인턴",
            "company": {"name": "빗썸코리아"},
            "due_time": "2026-06-15",
        },
        {
            "id": 100003,
            "position": "핀테크 백엔드 경력 개발자",
            "company": {"name": "토스"},
            "due_time": "",
        },
    ]
}

# Simulated second keyword API response (has overlap: id 100001 again + new).
SAMPLE_API_JSON_2 = {
    "data": [
        {
            "id": 100001,
            "position": "블록체인 플랫폼 엔지니어 신입",
            "company": {"name": "두나무"},
            "due_time": "2026-05-31",
        },
        {
            "id": 100004,
            "position": "AI 데이터 분석가",
            "company": {"name": "카카오페이"},
            "due_time": "2026-07-01",
        },
    ]
}

# HTML fallback -- anchor scan targets /wd/ links.
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>원티드 검색결과</title></head>
<body>
  <div class="search-results">
    <li>
      <a href="/wd/200001">
        크립토 트레이딩 시스템 개발 신입
      </a>
      <span>업비트</span>
    </li>
    <li>
      <a href="/wd/200002">
        블록체인 보안 엔지니어 경력
      </a>
      <span>체인파트너스</span>
    </li>
  </div>
</body></html>
"""

# Detail page HTML.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>블록체인 엔지니어 인턴 | 원티드</title></head>
<body>
  <div class="job-detail">
    <h1>블록체인 엔지니어 인턴</h1>
    <p>두나무에서 블록체인 엔지니어 인턴을 모집합니다.</p>
    <p>마감일: 2026-06-30</p>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> WantedChannel:
    """Fresh WantedChannel instance per test."""
    return WantedChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import wanted

    assert hasattr(wanted, "WantedChannel")
    assert hasattr(wanted, "BASE_URL")
    assert hasattr(wanted, "DEFAULT_HEADERS")
    assert wanted.WantedChannel.name == "wanted"
    assert wanted.WantedChannel.tier == 1
    assert wanted.WantedChannel.backend == "requests"
    assert wanted.WantedChannel.default_legitimacy_tier == "T1"
    assert BASE_URL.startswith("https://www.wanted.co.kr")
    assert "User-Agent" in DEFAULT_HEADERS


def test_class_satisfies_channel_protocol(channel: WantedChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "wanted"
    assert channel.tier == 1
    assert channel.backend == "requests"
    assert channel.default_rate_per_minute == 10


def test_search_queries_present() -> None:
    """SEARCH_QUERIES must include the expected fintech/crypto keywords."""
    assert len(SEARCH_QUERIES) >= 4
    assert "핀테크" in SEARCH_QUERIES
    assert "블록체인" in SEARCH_QUERIES


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(channel: WantedChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_error(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests as req_mod

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise req_mod.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs() -- API path
# ---------------------------------------------------------------------------


def test_list_jobs_api_success(channel: WantedChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """API path yields JobRecords from JSON data."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 3
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "wanted"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert job.title


def test_list_jobs_api_extracts_company(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Company name from API JSON should be captured in org field."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    orgs = {j.org for j in jobs}
    assert "두나무" in orgs
    assert "빗썸코리아" in orgs
    assert "토스" in orgs


def test_list_jobs_api_builds_detail_url(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Detail URL should follow ``/wd/<id>`` pattern."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    for job in jobs:
        assert "/wd/" in str(job.source_url)


def test_list_jobs_api_parses_deadline(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """due_time from API should be parsed into deadline."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    with_deadline = [j for j in jobs if j.deadline is not None]
    assert len(with_deadline) >= 1
    # "2026-05-31" should be parsed
    dates = [(j.deadline.year, j.deadline.month) for j in with_deadline]
    assert (2026, 5) in dates or (2026, 6) in dates


# ---------------------------------------------------------------------------
# list_jobs() -- API fail -> HTML fallback
# ---------------------------------------------------------------------------


def test_list_jobs_api_fail_falls_back_to_html(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When API returns non-200, the HTML fallback should kick in."""
    call_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_urls.append(url)
        if "/api/v4/" in url:
            return _FakeResponse(text="", status_code=500)
        # HTML fallback
        return _FakeResponse(text=SAMPLE_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs(query={"keyword": "크립토"})
    # Should have attempted API first, then fallen back to HTML
    assert any("/api/v4/" in u for u in call_urls)
    assert any("/search?" in u for u in call_urls)
    # HTML fallback should produce results
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "wanted"


# ---------------------------------------------------------------------------
# list_jobs() -- empty / error
# ---------------------------------------------------------------------------


def test_list_jobs_empty_api_response(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty ``data`` array in API response yields empty list."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data={"data": []}, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_total_failure_returns_empty(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both API and HTML fail -> empty list, never fabricated data."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs(query={"keyword": "핀테크"})
    assert jobs == []


# ---------------------------------------------------------------------------
# list_jobs() -- dedup
# ---------------------------------------------------------------------------


def test_list_jobs_dedupes_across_queries(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duplicate job IDs across different SEARCH_QUERIES should be deduped."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        # All queries return the same 3 items
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    # Only 3 unique jobs despite 6 queries
    assert len(jobs) == 3
    ids = {j.id for j in jobs}
    assert len(ids) == 3


def test_list_jobs_dedupes_mixed_queries(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Overlapping results from different queries should be deduped."""
    call_count = {"n": 0}

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_count["n"] += 1
        # Alternate between two result sets with overlap
        if call_count["n"] % 2 == 1:
            return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)
        return _FakeResponse(json_data=SAMPLE_API_JSON_2, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    # 100001 appears in both sets, should appear only once
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "Duplicate IDs found!"


# ---------------------------------------------------------------------------
# list_jobs() -- keyword override
# ---------------------------------------------------------------------------


def test_list_jobs_keyword_override(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``keyword`` kwarg should use only that keyword, not all SEARCH_QUERIES."""
    captured_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        captured_urls.append(url)
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    channel.list_jobs(query={"keyword": "DeFi"})
    # Only 1 API call (for "DeFi"), not 6 (for all SEARCH_QUERIES)
    api_calls = [u for u in captured_urls if "/api/v4/" in u]
    assert len(api_calls) == 1
    assert "DeFi" in api_calls[0]


# ---------------------------------------------------------------------------
# Archetype inference
# ---------------------------------------------------------------------------


def test_archetype_intern(channel: WantedChannel) -> None:
    assert channel._infer_archetype("블록체인 개발 인턴") == "INTERN"
    assert channel._infer_archetype("Summer Intern Program") == "INTERN"


def test_archetype_entry(channel: WantedChannel) -> None:
    assert channel._infer_archetype("핀테크 플랫폼 신입 개발자") == "ENTRY"


def test_archetype_experienced(channel: WantedChannel) -> None:
    assert channel._infer_archetype("시니어 백엔드 경력 개발자") == "EXPERIENCED"


def test_archetype_none(channel: WantedChannel) -> None:
    assert channel._infer_archetype("블록체인 개발자") is None
    assert channel._infer_archetype("") is None


def test_list_jobs_api_infers_archetypes(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """API results with 신입/인턴/경력 in title should have archetype set."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(json_data=SAMPLE_API_JSON, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs()
    archetypes = {j.archetype for j in jobs if j.archetype}
    assert archetypes == {"ENTRY", "INTERN", "EXPERIENCED"}


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_success(channel: WantedChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Detail page HTML yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    record = channel.get_detail("https://www.wanted.co.kr/wd/100001")
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "블록체인" in record.title or "블록체인" in record.description
    assert record.source_channel == "wanted"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0


def test_get_detail_failure_returns_none(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    result = channel.get_detail("https://www.wanted.co.kr/wd/999999")
    assert result is None


def test_get_detail_parses_deadline(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Detail page with date in body should parse deadline."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    record = channel.get_detail("https://www.wanted.co.kr/wd/100001")
    assert record is not None
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 6
    assert record.deadline.day == 30


# ---------------------------------------------------------------------------
# HTML fallback path (directly)
# ---------------------------------------------------------------------------


def test_html_fallback_parses_anchors(
    channel: WantedChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HTML fallback extracts /wd/ links and company names."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "/api/v4/" in url:
            return _FakeResponse(text="", status_code=500)
        return _FakeResponse(text=SAMPLE_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs(query={"keyword": "크립토"})
    assert len(jobs) >= 1
    for job in jobs:
        assert "/wd/" in str(job.source_url)
        assert job.source_channel == "wanted"


def test_html_fallback_empty_page(channel: WantedChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty HTML page yields empty list."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "/api/v4/" in url:
            return _FakeResponse(text="", status_code=500)
        return _FakeResponse(text="<html><body></body></html>", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.wanted.requests.get", fake_get)
    jobs = channel.list_jobs(query={"keyword": "핀테크"})
    assert jobs == []
