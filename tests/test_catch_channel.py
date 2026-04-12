"""Unit tests for CatchChannel.

All tests run **offline** -- every network call is monkeypatched.
The fixtures mirror real 캐치 list / detail DOM shapes and exercise:

    * module + class import smoke
    * ``check()`` success, 4xx failure, and exception paths
    * ``list_jobs()`` -- empty HTML returns ``[]``
    * ``list_jobs()`` -- sample HTML yields valid JobRecords
    * ``list_jobs()`` -- dedup across recruit + intern pages
    * ``list_jobs()`` -- INTERN_URL is also fetched
    * ``list_jobs()`` -- keyword filter via query dict
    * ``list_jobs()`` -- archetype inference
    * ``get_detail()`` -- sample HTML yields a record
    * ``get_detail()`` -- 404 returns None
    * ``get_detail()`` -- minimal HTML (parse-graceful) returns a record or None
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.catch import (
    INTERN_URL,
    LANDING_URL,
    RECRUIT_URL,
    CatchChannel,
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


# Sample list HTML using primary selector "ul.list_item li a".
SAMPLE_LIST_RECRUIT_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치 채용공고</title></head>
<body>
  <ul class="list_item">
    <li>
      <a href="/NCS/RecruitView?RecruitNo=11111">
        삼성SDS 신입공채 IT 개발 채용
      </a>
      <span class="co_name">삼성SDS</span>
      <span>마감: 2026.05.20</span>
    </li>
    <li>
      <a href="/NCS/RecruitView?RecruitNo=22222">
        카카오뱅크 경력 개발자 모집 공고
      </a>
      <span class="co_name">카카오뱅크</span>
      <span>마감: 2026.06.10</span>
    </li>
  </ul>
</body></html>
"""

# Sample intern list HTML using primary selector.
SAMPLE_LIST_INTERN_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치 인턴</title></head>
<body>
  <ul class="list_item">
    <li>
      <a href="/NCS/RecruitInternView?RecruitNo=33333">
        현대자동차 인턴 모집 공고
      </a>
      <span class="co_name">현대자동차</span>
      <span>마감: 2026.05.31</span>
    </li>
  </ul>
</body></html>
"""

# Fallback HTML -- no primary selectors, but href contains /NCS/.
SAMPLE_FALLBACK_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치</title></head>
<body>
  <div>
    <a href="/NCS/RecruitView?RecruitNo=44444">LG전자 신입 채용 공고</a>
  </div>
  <div>
    <a href="/NCS/RecruitInternView?RecruitNo=55555">SK하이닉스 인턴 모집</a>
  </div>
</body></html>
"""

# Generic scan HTML -- no known selectors, no /NCS/ in href,
# but contains generic recruitment keywords in text.
SAMPLE_GENERIC_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치</title></head>
<body>
  <div>
    <a href="/jobs/special/99999">포스코 신입 채용 모집 안내</a>
  </div>
</body></html>
"""

# Detail page HTML.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>삼성SDS 신입공채 IT 개발 채용 | 캐치</title></head>
<body>
  <div class="tit_area">
    <h1 class="tit">삼성SDS 신입공채 IT 개발 채용</h1>
  </div>
  <span class="co_name">삼성SDS</span>
  <div class="content_area">
    <p>업무: IT 개발, 클라우드 인프라 구축, 솔루션 개발</p>
    <p>자격: 4년제 대학 졸업(예정)자, IT/컴공 전공 우대</p>
    <p>마감: 2026-05-20</p>
    <p>근무지: 서울 잠실</p>
  </div>
</body></html>
"""

# HTML with COMPETITION keyword in URL path.
SAMPLE_COMPETITION_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치 공모전</title></head>
<body>
  <ul class="list_item">
    <li>
      <a href="/competition/RecruitView?RecruitNo=66666">
        KB금융 공모전 신청 안내
      </a>
    </li>
  </ul>
</body></html>
"""

# HTML with no matching keywords -- should yield 0 jobs via generic scan.
SAMPLE_NO_MATCH_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>캐치</title></head>
<body>
  <div>
    <a href="/misc/page123">날씨 예보 서비스 소개 페이지입니다</a>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> CatchChannel:
    """Fresh CatchChannel instance per test."""
    return CatchChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import catch

    assert hasattr(catch, "CatchChannel")
    assert hasattr(catch, "LANDING_URL")
    assert hasattr(catch, "RECRUIT_URL")
    assert hasattr(catch, "INTERN_URL")
    assert hasattr(catch, "DEFAULT_HEADERS")
    assert catch.CatchChannel.name == "catch"
    assert catch.CatchChannel.tier == 1
    assert catch.CatchChannel.default_legitimacy_tier == "T1"
    assert LANDING_URL.startswith("https://www.catch.co.kr")
    assert RECRUIT_URL.startswith("https://www.catch.co.kr")
    assert INTERN_URL.startswith("https://www.catch.co.kr")


def test_class_attributes() -> None:
    """Verify class-level attributes match spec."""
    assert CatchChannel.name == "catch"
    assert CatchChannel.tier == 1
    assert CatchChannel.backend == "requests"
    assert CatchChannel.default_rate_per_minute == 8
    assert CatchChannel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_4xx(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="not found", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_exception(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests as req

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise req.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML fixture yields valid JobRecords from both pages."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "InternList" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_RECRUIT_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "catch"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert job.title


def test_list_jobs_intern_url_also_fetched(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INTERN_URL must be fetched in addition to RECRUIT_URL."""
    captured_urls: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        captured_urls.append(url)
        if "InternList" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_RECRUIT_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    channel.list_jobs()
    assert any(RECRUIT_URL in u or "RecruitListingAll" in u for u in captured_urls)
    assert any(INTERN_URL in u or "InternList" in u for u in captured_urls)


def test_list_jobs_dedup_on_same_id(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same HTML on both pages -- dedup must prevent duplicate IDs."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_RECRUIT_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate IDs found"


def test_list_jobs_keyword_filter_via_query(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """query dict keyword filter keeps only matching records."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "InternList" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_RECRUIT_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs(query={"keyword": "카카오뱅크"})
    assert all("카카오뱅크" in j.title or "카카오뱅크" in j.description for j in jobs)


def test_list_jobs_archetype_inference(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Archetype should be inferred: 인턴 → INTERN, default → GENERAL."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        if "InternList" in url:
            return _FakeResponse(text=SAMPLE_LIST_INTERN_HTML, status_code=200)
        return _FakeResponse(text=SAMPLE_LIST_RECRUIT_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    archetypes = {j.archetype for j in jobs if j.archetype}
    # Intern HTML has "인턴" in title → INTERN expected
    assert "INTERN" in archetypes


def test_list_jobs_fallback_selector(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fallback selector: no primary matches, but href contains /NCS/."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_FALLBACK_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    for job in jobs:
        assert job.source_channel == "catch"


def test_list_jobs_generic_scan(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generic scan: no primary/fallback selectors, matches GENERIC_KEYWORDS in text."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_GENERIC_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 1
    assert any("채용" in j.title or "모집" in j.title for j in jobs)


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_parses_sample_html(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML fixture yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    url = "https://www.catch.co.kr/NCS/RecruitView?RecruitNo=11111"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "삼성SDS" in record.org or "삼성SDS" in record.title
    assert "IT" in record.description or "IT" in record.title
    assert record.source_channel == "catch"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5
    assert record.deadline.day == 20


def test_get_detail_returns_none_on_404(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    result = channel.get_detail("https://www.catch.co.kr/NCS/RecruitView?RecruitNo=99999")
    assert result is None


def test_get_detail_minimal_html_graceful(
    channel: CatchChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Minimal HTML with no structured elements still yields a record or None gracefully."""
    minimal_html = "<html><head><title>캐치 공고 페이지</title></head><body></body></html>"

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=minimal_html, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.catch.requests.get", fake_get)
    result = channel.get_detail("https://www.catch.co.kr/NCS/RecruitView?RecruitNo=12345")
    # Must not raise — either a record or None is acceptable
    assert result is None or isinstance(result, JobRecord)


# ---------------------------------------------------------------------------
# _infer_archetype()
# ---------------------------------------------------------------------------


def test_infer_archetype_intern() -> None:
    assert CatchChannel._infer_archetype("현대차 인턴 모집", "") == "INTERN"
    assert CatchChannel._infer_archetype("Intern Program", "") == "INTERN"
    assert CatchChannel._infer_archetype("무관", "/NCS/RecruitInternList") == "INTERN"


def test_infer_archetype_activity() -> None:
    assert CatchChannel._infer_archetype("대외활동 모집", "") == "ACTIVITY"
    assert CatchChannel._infer_archetype("무관", "/activity/123") == "ACTIVITY"


def test_infer_archetype_competition() -> None:
    assert CatchChannel._infer_archetype("금융 공모전 안내", "") == "COMPETITION"
    assert CatchChannel._infer_archetype("무관", "/competition/789") == "COMPETITION"


def test_infer_archetype_general() -> None:
    assert CatchChannel._infer_archetype("일반 채용 공고", "/NCS/RecruitView?RecruitNo=100") == "GENERAL"
