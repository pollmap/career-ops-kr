"""Unit tests for JobalioChannel.

All tests run **offline** -- every network call is monkeypatched.
The fixtures exercise:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` -- RSS path success
    * ``list_jobs()`` -- RSS empty → HTML fallback
    * ``list_jobs()`` -- combined regular + occasional
    * ``list_jobs()`` -- occasional URL fallback (OCCASIONAL_ALT_URL)
    * ``list_jobs()`` -- dedup across regular and occasional sources
    * ``list_jobs()`` -- occasional records carry archetype="OCCASIONAL"
    * ``list_jobs()`` -- total failure returns []
    * ``get_detail()`` -- success and failure
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.jobalio import (
    OCCASIONAL_ALT_URL,
    OCCASIONAL_URL,
    RSS_URL,
    JobalioChannel,
)

# ---------------------------------------------------------------------------
# Helpers -- fake HTTP responses
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


# ---------------------------------------------------------------------------
# HTML Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RSS_ENTRIES = [
    {
        "title": "공공기관 경영직 신규채용 공고",
        "link": "https://job.alio.go.kr/recruitView.do?seq=1001",
        "summary": "마감일: 2026.05.31 한국전력공사에서 경영직을 모집합니다.",
        "author": "한국전력공사",
        "published_parsed": (2026, 4, 10, 9, 0, 0, 0, 0, 0),
    },
    {
        "title": "정보기술직 인턴 채용공고",
        "link": "https://job.alio.go.kr/recruitView.do?seq=1002",
        "summary": "마감일: 2026.06.15 KDB산업은행 IT 인턴 모집",
        "author": "KDB산업은행",
        "published_parsed": (2026, 4, 11, 9, 0, 0, 0, 0, 0),
    },
]


class _FakeRSSEntry:
    """Simulate a feedparser entry."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.title = data.get("title", "")
        self.link = data.get("link", "")
        self.summary = data.get("summary", "")
        self.author = data.get("author", "")
        self.published_parsed = data.get("published_parsed")


class _FakeParsed:
    """Simulate feedparser result with entries."""

    def __init__(self, entries: list[dict[str, Any]], status: int = 200) -> None:
        self.entries = [_FakeRSSEntry(e) for e in entries]
        self.status = status
        self.bozo = False


# Regular HTML with career keyword links
SAMPLE_LANDING_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>ALIO 채용정보</title></head>
<body>
  <table class="tbl_list">
    <tr>
      <td><a href="/recruitView.do?seq=2001">한국수자원공사 신규 채용공고</a></td>
    </tr>
    <tr>
      <td><a href="/recruitView.do?seq=2002">한국도로공사 인턴 모집공고</a></td>
    </tr>
  </table>
</body></html>
"""

# Occasional HTML with career-related links using primary tbl_list selector
SAMPLE_OCCASIONAL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>ALIO 수시공고</title></head>
<body>
  <table class="tbl_list">
    <tr>
      <td><a href="/occasional/researchDetail.do?seq=3001">국책연구원 전문연구원 수시채용</a></td>
    </tr>
  </table>
</body></html>
"""

# Occasional HTML using the fallback href-pattern selector
SAMPLE_OCCASIONAL_FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>ALIO 수시공고 모바일</title></head>
<body>
  <div>
    <a href="/occasional/researchDetail.do?seq=4001">경제연구원 수시채용 공고</a>
  </div>
</body></html>
"""

# HTML where the anchor URL is the same as one from the regular landing page
SAMPLE_OCCASIONAL_DUPLICATE_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>ALIO 수시공고</title></head>
<body>
  <table class="tbl_list">
    <tr>
      <td><a href="/recruitView.do?seq=2001">한국수자원공사 신규 채용공고</a></td>
    </tr>
  </table>
</body></html>
"""

SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>한국전력공사 경영직 채용 | ALIO</title></head>
<body>
  <div class="job-detail">
    <h1>한국전력공사 경영직 신규채용</h1>
    <p>지원 마감: 2026-05-31</p>
    <p>한국전력공사에서 경영직군 신규직원을 모집합니다.</p>
  </div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def channel() -> JobalioChannel:
    """Fresh JobalioChannel instance per test."""
    return JobalioChannel()


def _make_fake_rss(entries: list[dict[str, Any]]) -> _FakeParsed:
    return _FakeParsed(entries)


def _make_empty_rss() -> _FakeParsed:
    return _FakeParsed([])


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes expected class + constants."""
    from career_ops_kr.channels import jobalio

    assert hasattr(jobalio, "JobalioChannel")
    assert hasattr(jobalio, "RSS_URL")
    assert hasattr(jobalio, "LANDING_URL")
    assert hasattr(jobalio, "ALT_LIST_URL")
    assert hasattr(jobalio, "OCCASIONAL_URL")
    assert hasattr(jobalio, "OCCASIONAL_ALT_URL")
    assert jobalio.JobalioChannel.name == "jobalio"
    assert jobalio.JobalioChannel.tier == 1
    assert jobalio.JobalioChannel.backend == "rss+html"
    assert jobalio.JobalioChannel.default_legitimacy_tier == "T1"
    assert RSS_URL.startswith("https://job.alio.go.kr")
    assert OCCASIONAL_URL == "https://job.alio.go.kr/occasional/researchList.do"
    assert OCCASIONAL_ALT_URL == "https://job.alio.go.kr/mobile/occasional/researchList.do"


def test_class_satisfies_channel_protocol(channel: JobalioChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "jobalio"
    assert channel.tier == 1
    assert channel.backend == "rss+html"
    assert channel.default_rate_per_minute == 12


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_error(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests as req_mod

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise req_mod.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs() -- RSS path
# ---------------------------------------------------------------------------


def test_list_jobs_rss_success(channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """RSS entries yield valid JobRecords."""
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_fake_rss(SAMPLE_RSS_ENTRIES),
    )
    # Occasional must return nothing so we can isolate RSS path result count
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.requests.get",
        lambda url, **_: _FakeResponse(text="", status_code=404),
    )

    jobs = channel.list_jobs()
    assert len(jobs) >= 2
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "jobalio"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert job.title


def test_list_jobs_rss_empty_falls_back_to_html(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty RSS triggers HTML fallback path."""
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.requests.get",
        lambda url, **_: _FakeResponse(
            text=SAMPLE_LANDING_HTML if "recruit.do" in url else "",
            status_code=200 if "recruit.do" in url else 404,
        ),
    )

    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    urls = [str(j.source_url) for j in jobs]
    assert any("recruitView" in u for u in urls)


# ---------------------------------------------------------------------------
# list_jobs() -- occasional path
# ---------------------------------------------------------------------------


def test_list_jobs_includes_occasional(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Occasional postings from OCCASIONAL_URL appear in combined results."""
    # Empty RSS → no regular jobs via RSS
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if OCCASIONAL_URL in url or "occasional/researchList" in url:
            return _FakeResponse(text=SAMPLE_OCCASIONAL_HTML, status_code=200)
        # Regular HTML also returns something so we have both
        if "recruit.do" in url:
            return _FakeResponse(text=SAMPLE_LANDING_HTML, status_code=200)
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)

    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    # At least one record should come from occasional page (researchDetail URL)
    occasional_records = [j for j in jobs if "researchDetail" in str(j.source_url)]
    assert len(occasional_records) >= 1


def test_list_jobs_occasional_fallback(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When OCCASIONAL_URL returns 4xx, OCCASIONAL_ALT_URL is tried."""
    # Empty RSS so we can track all HTTP calls
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )

    called_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        called_urls.append(url)
        if OCCASIONAL_ALT_URL in url or "mobile/occasional" in url:
            return _FakeResponse(text=SAMPLE_OCCASIONAL_FALLBACK_HTML, status_code=200)
        if OCCASIONAL_URL in url and "mobile" not in url:
            return _FakeResponse(text="", status_code=404)
        # Regular HTML
        if "recruit.do" in url:
            return _FakeResponse(text=SAMPLE_LANDING_HTML, status_code=200)
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)

    jobs = channel.list_jobs()

    # Both primary and alt occasional URLs should have been attempted
    assert any(OCCASIONAL_URL in u for u in called_urls)
    assert any(OCCASIONAL_ALT_URL in u for u in called_urls)

    # Alt URL returned data, so occasional records should appear
    occasional_records = [j for j in jobs if "researchDetail" in str(j.source_url)]
    assert len(occasional_records) >= 1


def test_list_jobs_dedup_cross_source(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same URL appearing in both regular HTML and occasional → only 1 record."""
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if OCCASIONAL_URL in url or "occasional/researchList" in url:
            # Returns the same anchor URL as SAMPLE_LANDING_HTML (/recruitView.do?seq=2001)
            return _FakeResponse(text=SAMPLE_OCCASIONAL_DUPLICATE_HTML, status_code=200)
        if "recruit.do" in url:
            return _FakeResponse(text=SAMPLE_LANDING_HTML, status_code=200)
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)

    jobs = channel.list_jobs()

    # All IDs must be unique
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "Duplicate job IDs found after cross-source dedup"

    # The duplicate URL (seq=2001) must appear exactly once
    matching = [j for j in jobs if "seq=2001" in str(j.source_url)]
    assert len(matching) == 1


def test_occasional_archetype(channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Records sourced from the occasional URL carry archetype='OCCASIONAL'."""
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if OCCASIONAL_URL in url or "occasional/researchList" in url:
            return _FakeResponse(text=SAMPLE_OCCASIONAL_HTML, status_code=200)
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)

    jobs = channel.list_jobs()

    occasional_records = [j for j in jobs if "researchDetail" in str(j.source_url)]
    assert len(occasional_records) >= 1
    for job in occasional_records:
        assert job.archetype == "OCCASIONAL", (
            f"Expected archetype='OCCASIONAL', got {job.archetype!r} for {job.source_url}"
        )


# ---------------------------------------------------------------------------
# list_jobs() -- total failure
# ---------------------------------------------------------------------------


def test_list_jobs_total_failure_returns_empty(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All paths fail → empty list, no fabricated data."""
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.feedparser.parse",
        lambda *_a, **_kw: _make_empty_rss(),
    )
    monkeypatch.setattr(
        "career_ops_kr.channels.jobalio.requests.get",
        lambda url, **_: _FakeResponse(text="error", status_code=500),
    )

    jobs = channel.list_jobs()
    assert jobs == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_success(channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Detail page HTML yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)
    record = channel.get_detail("https://job.alio.go.kr/recruitView.do?seq=9001")
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "전력공사" in record.title or "전력공사" in record.description
    assert record.source_channel == "jobalio"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0


def test_get_detail_failure_returns_none(
    channel: JobalioChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 response from get_detail returns None."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.jobalio.requests.get", fake_get)
    result = channel.get_detail("https://job.alio.go.kr/recruitView.do?seq=99999")
    assert result is None
