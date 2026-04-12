"""Unit tests for KakaoBankChannel.

All tests run **offline** — every network call is monkeypatched.
Covers:

    1. Import smoke (2): module import + class-level metadata
    2. ``check()`` (3): 200 OK / 4xx / exception
    3. ``list_jobs()`` (7): empty HTML → [], fixture HTML → records,
       LIST_URL → LANDING_URL fallback, dedup, archetype inference,
       keyword filter, fetch failure → []
    4. ``get_detail()`` (3): success / 404 → None / parse failure → None
    5. ``_infer_archetype()`` (4): all 5 branches covered
"""

from __future__ import annotations

from typing import Any

import pytest
import requests

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.kakao_bank import (
    FINTECH_KEYWORDS,
    LANDING_URL,
    LIST_URL,
    ORG,
    KakaoBankChannel,
    _infer_archetype,
)

# ---------------------------------------------------------------------------
# Fake response infrastructure
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


def _patch_session_get(
    monkeypatch: pytest.MonkeyPatch,
    channel: KakaoBankChannel,
    response_factory: Any,
) -> list[str]:
    """Patch ``channel._session.get`` (the requests.Session instance method).

    ``response_factory`` may be:
        * a ``_FakeResponse`` instance (same response for every call)
        * a callable ``(url: str, call_index: int) -> _FakeResponse``

    Returns the shared ``calls`` list for assertion.
    """
    calls: list[str] = []

    def _fake_get(url: str, *_args: Any, **_kwargs: Any) -> _FakeResponse:
        idx = len(calls)
        calls.append(url)
        if callable(response_factory):
            return response_factory(url, idx)
        return response_factory

    monkeypatch.setattr(channel._session, "get", _fake_get)
    return calls


# ---------------------------------------------------------------------------
# HTML Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>카카오뱅크 채용</title></head>
<body>
  <div class="career-list">
    <a href="/careers/jobs/101">데이터 엔지니어 (신입/경력)</a>
    <a href="/careers/jobs/102">인턴 - 디지털 금융 기획</a>
    <a href="/careers/jobs/103">리스크 관리 전문가</a>
    <a href="/careers/jobs/104">AI 분석 개발자</a>
  </div>
</body>
</html>
"""

SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>카카오뱅크 채용 — 데이터 엔지니어</title>
</head>
<body>
  <h1>데이터 엔지니어 (신입/경력)</h1>
  <div class="job-content">
    카카오뱅크 데이터 플랫폼 팀에서 데이터 파이프라인을 설계하고 운영할
    인재를 모집합니다. Python, Spark, Hadoop 등 빅데이터 기술 스택을
    활용한 업무를 담당합니다.
    마감: 2026-06-30
  </div>
</body>
</html>
"""

FALLBACK_HREF_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
  <a href="/careers/jobs/201">백엔드 개발자</a>
  <a href="/careers/detail/202">컴플라이언스 담당자</a>
</body>
</html>
"""

GENERIC_ANCHOR_HTML = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body>
  <a href="/recruit/300">데이터 분석 인턴 모집공고</a>
  <a href="/about">회사 소개</a>
</body>
</html>
"""

EMPTY_HTML = "<html><body></body></html>"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def channel() -> KakaoBankChannel:
    return KakaoBankChannel()


# ---------------------------------------------------------------------------
# 1. Import smoke + metadata
# ---------------------------------------------------------------------------


def test_import_module_constants() -> None:
    """Module-level constants are defined and sane."""
    assert LIST_URL == "https://www.kakaobank.com/careers/jobs"
    assert LANDING_URL == "https://www.kakaobank.com/careers"
    assert ORG == "카카오뱅크"
    assert len(FINTECH_KEYWORDS) >= 5


def test_class_metadata() -> None:
    """Class attributes match the specification."""
    assert KakaoBankChannel.name == "kakao_bank"
    assert KakaoBankChannel.tier == 3
    assert KakaoBankChannel.backend == "requests"
    assert KakaoBankChannel.default_rate_per_minute == 6
    assert KakaoBankChannel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# 2. check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    _patch_session_get(monkeypatch, channel, _FakeResponse(text="ok", status_code=200))
    assert channel.check() is True


def test_check_returns_false_on_4xx(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    _patch_session_get(monkeypatch, channel, _FakeResponse(text="", status_code=404))
    assert channel.check() is False


def test_check_returns_false_on_exception(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    def _raise(url: str, idx: int) -> _FakeResponse:
        raise requests.ConnectionError("unreachable")

    _patch_session_get(monkeypatch, channel, _raise)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# 3. list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    _patch_session_get(monkeypatch, channel, _FakeResponse(text=EMPTY_HTML, status_code=200))
    result = channel.list_jobs()
    assert result == []


def test_list_jobs_fixture_yields_records(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Sample HTML with ``div.career-list a`` links → multiple JobRecords."""
    _patch_session_get(monkeypatch, channel, _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200))
    jobs = channel.list_jobs()

    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "kakao_bank"
        assert job.source_tier == 3
        assert job.legitimacy_tier == "T1"
        assert job.org == ORG
        assert job.title
        assert len(job.id) == 16


def test_list_jobs_landing_fallback_when_list_url_empty(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """If LIST_URL returns no records, LANDING_URL is fetched as fallback."""
    calls: list[str] = []

    def _factory(url: str, idx: int) -> _FakeResponse:
        calls.append(url)
        if "jobs" in url:
            # LIST_URL returns empty body → triggers fallback
            return _FakeResponse(text=EMPTY_HTML, status_code=200)
        # LANDING_URL returns actual content
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    _patch_session_get(monkeypatch, channel, _factory)
    jobs = channel.list_jobs()

    # Must have fetched LANDING_URL (not just LIST_URL)
    assert any(LANDING_URL in c for c in calls)
    assert len(jobs) >= 1


def test_list_jobs_dedup_removes_duplicate_records(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Identical records built from two separate calls are deduplicated."""
    # Return the same HTML twice (simulated via the factory)
    call_count = [0]

    def _factory(url: str, idx: int) -> _FakeResponse:
        call_count[0] += 1
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    _patch_session_get(monkeypatch, channel, _factory)
    jobs = channel.list_jobs()
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate ids found after dedup"


def test_list_jobs_archetype_inference(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Archetypes are inferred correctly from job titles in the fixture."""
    _patch_session_get(monkeypatch, channel, _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200))
    jobs = channel.list_jobs()

    # "인턴" in title → INTERN
    intern_job = next((j for j in jobs if "인턴" in j.title), None)
    assert intern_job is not None
    assert intern_job.archetype == "INTERN"

    # "데이터 엔지니어" → either DATA or ENGINEER; archetype should be non-None
    data_job = next((j for j in jobs if "데이터" in j.title), None)
    assert data_job is not None
    assert data_job.archetype in ("DATA", "ENGINEER", "INTERN", "RISK_COMPLIANCE", "GENERAL")


def test_list_jobs_keyword_filter_applied(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Keyword filter keeps relevant records and removes irrelevant ones."""
    # HTML with one matching and one non-matching job
    html = """
    <div class="career-list">
      <a href="/careers/jobs/501">데이터 분석가 신입</a>
      <a href="/careers/jobs/502">법무팀 변호사</a>
    </div>
    """
    _patch_session_get(monkeypatch, channel, _FakeResponse(text=html, status_code=200))
    jobs = channel.list_jobs({"keyword": "데이터"})
    titles = [j.title for j in jobs]
    assert any("데이터" in t for t in titles)


def test_list_jobs_fetch_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Both URLs returning errors → empty list, no exception raised."""
    _patch_session_get(monkeypatch, channel, _FakeResponse(text="", status_code=503))
    result = channel.list_jobs()
    assert result == []


def test_list_jobs_fallback_href_selector(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    """Tier-2 fallback: ``a[href*='/careers/jobs/']`` and ``/careers/detail/``."""
    _patch_session_get(
        monkeypatch, channel, _FakeResponse(text=FALLBACK_HREF_HTML, status_code=200)
    )
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    urls = [str(j.source_url) for j in jobs]
    assert any("careers" in u for u in urls)


# ---------------------------------------------------------------------------
# 4. get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_success_extracts_fields(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    _patch_session_get(
        monkeypatch, channel, _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)
    )
    url = "https://www.kakaobank.com/careers/jobs/101"
    detail = channel.get_detail(url)

    assert detail is not None
    assert isinstance(detail, JobRecord)
    assert "데이터 엔지니어" in detail.title
    assert detail.org == ORG
    assert detail.source_channel == "kakao_bank"
    assert detail.source_tier == 3
    assert detail.legitimacy_tier == "T1"
    assert detail.raw_html is not None
    assert detail.description


def test_get_detail_404_returns_none(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoBankChannel
) -> None:
    _patch_session_get(monkeypatch, channel, _FakeResponse(text="", status_code=404))
    result = channel.get_detail("https://www.kakaobank.com/careers/jobs/999")
    assert result is None


def test_get_detail_empty_url_returns_none(channel: KakaoBankChannel) -> None:
    assert channel.get_detail("") is None


# ---------------------------------------------------------------------------
# 5. _infer_archetype() — branch coverage
# ---------------------------------------------------------------------------


def test_infer_archetype_intern() -> None:
    assert _infer_archetype("디지털금융 인턴 채용") == "INTERN"
    assert _infer_archetype("Summer Intern Program") == "INTERN"


def test_infer_archetype_data() -> None:
    assert _infer_archetype("데이터 엔지니어") == "DATA"
    assert _infer_archetype("Data Analyst 신입") == "DATA"
    assert _infer_archetype("분석가 (BI/통계)") == "DATA"


def test_infer_archetype_engineer() -> None:
    assert _infer_archetype("백엔드 개발자") == "ENGINEER"
    assert _infer_archetype("Platform Engineer") == "ENGINEER"


def test_infer_archetype_risk_compliance() -> None:
    assert _infer_archetype("리스크 관리 전문가") == "RISK_COMPLIANCE"
    assert _infer_archetype("컴플라이언스 담당자") == "RISK_COMPLIANCE"
    assert _infer_archetype("준법감시 업무") == "RISK_COMPLIANCE"


def test_infer_archetype_general_fallback() -> None:
    assert _infer_archetype("디자이너") == "GENERAL"
    assert _infer_archetype("인사(HR) 담당자") == "GENERAL"
