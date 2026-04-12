"""Unit tests for ShinhanSecChannel.

All tests run **offline** — every network call is monkeypatched. The
fixtures mirror the real https://recruit.shinhansec.com/ DOM shape (as
observed 2026-04) and exercise:

    * module + class import smoke
    * Channel-protocol contract (name / tier / backend)
    * ``check()`` success and failure paths
    * ``list_jobs()`` — empty HTML, sample HTML, keyword filtering,
      blockchain archetype elevation, deadline parsing, org/legitimacy
      invariants, fetch failures
    * ``get_detail()`` — fetch failure + sample HTML success
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.shinhan_sec import (
    DEFAULT_HEADERS,
    KEYWORDS,
    LISTING_URL,
    ShinhanSecChannel,
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


# A stripped-down version of the real Shinhan Securities recruit landing
# page. Three anchors:
#   * /detail/1 — 블록체인부 체험형 인턴 (must elevate to BLOCKCHAIN_INTERN)
#   * /detail/2 — 디지털자산 리서치 인턴 (also BLOCKCHAIN_INTERN)
#   * /detail/3 — 지점 영업직 (must be filtered out — no KEYWORD match)
SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>신한투자증권 채용</title></head>
<body>
  <section class="recruit-list">
    <ul>
      <li class="recruit-item">
        <a href="/detail/1">신한투자증권 블록체인부 체험형 인턴 모집</a>
        <span class="period">접수기간: 2026.04.20 ~ 2026.05.17</span>
      </li>
      <li class="recruit-item">
        <a href="/detail/2">신한투자증권 디지털자산 리서치 인턴 채용</a>
        <span class="period">접수기간: 2026.05.10 ~ 2026.06.01</span>
      </li>
      <li class="recruit-item">
        <a href="/detail/3">지점 영업직 경력 모집</a>
        <span class="period">접수기간: 상시</span>
      </li>
    </ul>
  </section>
</body></html>
"""


# Realistic-ish detail-page HTML for the 블록체인부 체험형 인턴 listing.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>신한투자증권 블록체인부 체험형 인턴 모집 | 신한투자증권</title>
</head>
<body>
  <main class="recruit-detail">
    <h1>신한투자증권 블록체인부 체험형 인턴 모집</h1>
    <div class="info">
      <p>업무: 블록체인 / 디지털자산(STO) 리서치 및 사업 기획 보조</p>
      <p>자격: 4년제 재학 또는 휴학생, 금융/IT 전공 우대</p>
      <p>접수 마감: 2026-05-17</p>
      <p>근무지: 서울 영등포구 여의도</p>
    </div>
  </main>
</body></html>
"""


@pytest.fixture
def channel() -> ShinhanSecChannel:
    """Fresh ShinhanSecChannel instance per test."""
    return ShinhanSecChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import shinhan_sec

    assert hasattr(shinhan_sec, "ShinhanSecChannel")
    assert hasattr(shinhan_sec, "LISTING_URL")
    assert hasattr(shinhan_sec, "KEYWORDS")
    assert hasattr(shinhan_sec, "DEFAULT_HEADERS")
    assert hasattr(shinhan_sec, "BLOCKCHAIN_MARKERS")
    assert LISTING_URL.startswith("https://recruit.shinhansec.com")
    assert "User-Agent" in DEFAULT_HEADERS
    assert "블록체인" in KEYWORDS
    assert "디지털자산" in KEYWORDS


def test_class_satisfies_channel_protocol(channel: ShinhanSecChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "shinhan_sec"
    assert channel.tier == 3
    assert channel.backend == "requests"
    assert channel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_connection_error(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML yields >= 2 records (3rd anchor filtered out)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 2
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "shinhan_sec"
        assert job.source_tier == 3
        assert job.legitimacy_tier == "T1"
        assert job.title
        assert str(job.source_url).startswith("https://recruit.shinhansec.com")


def test_list_jobs_filters_out_non_keyword_anchors(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 영업직 anchor must NOT be present (no KEYWORD match)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    titles = [j.title for j in jobs]
    assert all("영업직" not in t for t in titles), (
        "영업직 anchor should have been filtered by KEYWORDS"
    )


def test_list_jobs_assigns_blockchain_archetype(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """블록체인 / 디지털자산 titles must elevate to BLOCKCHAIN_INTERN."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    blockchain_jobs = [j for j in jobs if j.archetype == "BLOCKCHAIN_INTERN"]
    assert len(blockchain_jobs) >= 2, (
        "expected both 블록체인 + 디지털자산 anchors to elevate to BLOCKCHAIN_INTERN"
    )


def test_list_jobs_extracts_deadlines(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At least one record should have a parsed deadline."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert any(j.deadline is not None for j in jobs), (
        "expected at least one deadline parsed from sample HTML"
    )


def test_list_jobs_org_is_shinhan(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All records must be tagged with the 신한투자증권 org."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs, "fixture should yield at least one job"
    assert all(j.org == "신한투자증권" for j in jobs)


def test_list_jobs_legitimacy_tier_t1(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All records must carry legitimacy_tier=T1 (official career site)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs
    assert all(j.legitimacy_tier == "T1" for j in jobs)


def test_list_jobs_fetch_failure_returns_empty(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 responses must yield an empty result — never fabricated."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error page", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_fetch_failure_returns_none(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    result = channel.get_detail("https://recruit.shinhansec.com/detail/99999")
    assert result is None


def test_get_detail_parses_sample_html(
    channel: ShinhanSecChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.shinhan_sec.requests.get", fake_get)
    url = "https://recruit.shinhansec.com/detail/1"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert record.org == "신한투자증권"
    assert "블록체인" in record.title or "블록체인" in record.description
    assert record.source_channel == "shinhan_sec"
    assert record.source_tier == 3
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0
    # Deadline "2026-05-17" should be parsed.
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5
    assert record.deadline.day == 17
    # Blockchain archetype must be elevated.
    assert record.archetype == "BLOCKCHAIN_INTERN"
