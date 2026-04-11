"""Unit tests for :class:`IncruitChannel` — no network I/O.

Covers:
    - Import smoke (class metadata sanity).
    - :meth:`IncruitChannel.check` with a mocked ``requests.get``.
    - :meth:`IncruitChannel.list_jobs` on:
        * empty HTML → ``[]``
        * primary-selector HTML fixture → >= 1 record
        * anchor-fallback HTML fixture → >= 1 record
        * keyword filter → excludes non-matching postings
        * duplicate URLs across pages are deduped
    - :meth:`IncruitChannel.get_detail` on:
        * 200 + valid HTML → :class:`JobRecord`
        * None response → ``None``
        * empty URL → ``None``

All HTTP calls are monkey-patched; no sockets are opened.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.incruit import (
    DEFAULT_PAGES,
    LIST_URL,
    MAX_PAGES,
    IncruitChannel,
)

# ---------------------------------------------------------------------------
# HTML fixtures — inlined so the tests have zero external deps
# ---------------------------------------------------------------------------

# Uses the primary-path selector ``a[href*='jobdb_info/jobpost.asp']`` nested
# inside a card container so the org/location helpers have something to chew
# on. Two postings with distinct URLs.
LIST_PRIMARY_HTML = """
<html>
  <head><title>인쿠르트 검색결과</title></head>
  <body>
    <div class="jobListDefault">
      <ul class="c_row">
        <li>
          <div class="l_job">
            <a class="accent" href="/jobdb_info/jobpost.asp?job=A111">
              블록체인 리서치 신입/경력 채용
            </a>
            <a class="company" href="/company/123">서울핀테크</a>
            <span class="area">서울 강남구 | 정규직 | ~2026.05.10</span>
          </div>
        </li>
        <li>
          <div class="l_job">
            <a class="c_tit" href="/jobdb_info/jobpost.asp?job=A222">
              디지털자산 개발 인턴 모집
            </a>
            <a class="company" href="/company/456">부산디지털</a>
            <span class="area">부산 해운대구 | 인턴 | 마감 2026-04-30</span>
          </div>
        </li>
      </ul>
    </div>
  </body>
</html>
"""

# Uses only plain ``<a>`` tags so primary selectors return nothing — forces
# the anchor-fallback code path. Intentionally includes a nav anchor that
# should be filtered (no career keyword).
LIST_FALLBACK_HTML = """
<html>
  <body>
    <header>
      <a href="/">홈</a>
    </header>
    <section>
      <ul>
        <li>
          <a href="https://job.incruit.com/jobdb_info/jobpost.asp?job=F001">
            핀테크 데이터 분석 경력 채용 공고
          </a>
          <span>경기 성남시 | 접수: 2026.05.15</span>
        </li>
        <li>
          <a href="https://job.incruit.com/jobdb_info/jobpost.asp?job=F002">
            금융 리서치 신입 모집
          </a>
          <span>서울 중구</span>
        </li>
      </ul>
    </section>
  </body>
</html>
"""

# Degenerate case — no anchors, no postings.
LIST_EMPTY_HTML = "<html><body><p>검색 결과가 없습니다.</p></body></html>"

DETAIL_HTML = """
<html>
  <head><title>인쿠르트 상세</title></head>
  <body>
    <h1 class="jobTit">블록체인 리서치 신입 정규직</h1>
    <div class="company">서울핀테크</div>
    <div class="jobDesc">
      근무지: 서울 강남구. 지원 마감 2026.05.10. 주요 업무는 블록체인 리서치.
    </div>
  </body>
</html>
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    resp.status_code = status
    return resp


def _bypass_retry(channel: IncruitChannel) -> None:
    """Replace ``_retry`` with a direct call — skips rate limiting in tests."""
    channel._retry = lambda fn, *args, **kw: fn(*args, **kw)  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


def test_incruit_import_smoke() -> None:
    """Class metadata matches the channel contract."""
    assert IncruitChannel.name == "incruit"
    assert IncruitChannel.tier == 1
    assert IncruitChannel.backend == "requests"
    assert IncruitChannel.default_legitimacy_tier == "T1"
    assert IncruitChannel.default_rate_per_minute == 10


def test_incruit_instantiates_with_defaults() -> None:
    channel = IncruitChannel()
    assert channel.list_url == LIST_URL
    assert channel.logger.name.endswith("incruit")


def test_incruit_normalise_pages_bounds() -> None:
    normalise = IncruitChannel._normalise_pages
    assert normalise(None) == DEFAULT_PAGES
    assert normalise("not-a-number") == DEFAULT_PAGES
    assert normalise(0) == 1
    assert normalise(1) == 1
    assert normalise(MAX_PAGES + 10) == MAX_PAGES
    assert normalise("5") == 5


def test_incruit_build_list_url_includes_category_and_page() -> None:
    channel = IncruitChannel()
    url = channel._build_list_url(page=3, category="100")
    assert "page=3" in url
    assert "cd=100" in url
    assert url.startswith(LIST_URL)


def test_incruit_build_list_url_without_category() -> None:
    channel = IncruitChannel()
    url = channel._build_list_url(page=1, category=None)
    assert "page=1" in url
    assert "cd=" not in url


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_incruit_check_true_when_list_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = IncruitChannel()
    monkeypatch.setattr(
        "career_ops_kr.channels.incruit.requests.get",
        lambda *a, **kw: _make_response("ok", status=200),
    )
    assert channel.check() is True


def test_incruit_check_false_when_all_urls_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = IncruitChannel()

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        import requests as _req

        raise _req.RequestException("boom")

    monkeypatch.setattr(
        "career_ops_kr.channels.incruit.requests.get",
        _raise,
    )
    assert channel.check() is False


def test_incruit_check_false_when_status_is_500(monkeypatch: pytest.MonkeyPatch) -> None:
    channel = IncruitChannel()
    monkeypatch.setattr(
        "career_ops_kr.channels.incruit.requests.get",
        lambda *a, **kw: _make_response("err", status=500),
    )
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_incruit_list_jobs_empty_html_returns_empty_list() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response("", status=200)  # type: ignore[method-assign]
    assert channel.list_jobs({"pages": 1}) == []


def test_incruit_list_jobs_none_response_returns_empty_list() -> None:
    channel = IncruitChannel()
    # Force _retry to return None (simulates all retries exhausted).
    channel._retry = lambda fn, *a, **kw: None  # type: ignore[method-assign]
    assert channel.list_jobs({"pages": 1}) == []


def test_incruit_list_jobs_primary_selectors_yields_records() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response(LIST_PRIMARY_HTML, status=200)  # type: ignore[method-assign]

    jobs = channel.list_jobs({"pages": 1})
    assert len(jobs) >= 2
    assert all(isinstance(job, JobRecord) for job in jobs)
    assert all(job.source_channel == "incruit" for job in jobs)
    assert all(job.source_tier == 1 for job in jobs)
    assert all(job.legitimacy_tier == "T1" for job in jobs)

    titles = " ".join(job.title for job in jobs)
    assert "블록체인" in titles or "디지털자산" in titles

    # 인턴 archetype 태그 검증
    intern_jobs = [job for job in jobs if job.archetype == "INTERN"]
    assert len(intern_jobs) >= 1

    # 지역 추출 검증 — 서울/부산 중 최소 하나는 나와야 함
    locations = {job.location for job in jobs if job.location}
    assert locations & {"서울", "부산"}


def test_incruit_list_jobs_anchor_fallback_path() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response(LIST_FALLBACK_HTML, status=200)  # type: ignore[method-assign]

    jobs = channel.list_jobs({"pages": 1})
    assert len(jobs) >= 2
    titles = [job.title for job in jobs]
    assert any("핀테크" in t or "금융" in t for t in titles)


def test_incruit_list_jobs_keyword_filter_excludes_non_matching() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response(LIST_PRIMARY_HTML, status=200)  # type: ignore[method-assign]

    jobs = channel.list_jobs({"pages": 1, "keyword": "블록체인"})
    assert len(jobs) >= 1
    for job in jobs:
        blob = f"{job.title} {job.description}"
        assert "블록체인" in blob


def test_incruit_list_jobs_dedupes_across_pages() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    call_count = {"n": 0}

    def _fetch(url: str) -> MagicMock:
        call_count["n"] += 1
        return _make_response(LIST_PRIMARY_HTML, status=200)

    channel._fetch = _fetch  # type: ignore[method-assign]

    jobs = channel.list_jobs({"pages": 3})
    # 같은 fixture 를 3페이지 모두 반환 → 첫 페이지 이후 모두 중복, 조기
    # 종료 로직에 의해 page 2 까지만 fetch.
    assert call_count["n"] >= 2
    unique_urls = {str(job.source_url) for job in jobs}
    assert len(jobs) == len(unique_urls)


def test_incruit_list_jobs_handles_fetch_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)

    responses = iter(
        [
            _make_response("", status=500),
            _make_response(LIST_PRIMARY_HTML, status=200),
        ]
    )
    channel._fetch = lambda url: next(responses)  # type: ignore[method-assign]

    jobs = channel.list_jobs({"pages": 2})
    # 첫 페이지는 500 → skip, 두 번째 페이지에서 실제 데이터 확보
    assert len(jobs) >= 1


def test_incruit_list_jobs_accepts_query_none() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response(LIST_EMPTY_HTML, status=200)  # type: ignore[method-assign]
    assert channel.list_jobs(None) == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_incruit_get_detail_returns_record() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response(DETAIL_HTML, status=200)  # type: ignore[method-assign]

    url = "https://job.incruit.com/jobdb_info/jobpost.asp?job=A111"
    record = channel.get_detail(url)
    assert record is not None
    assert record.source_channel == "incruit"
    assert "블록체인" in record.title
    assert record.location == "서울"
    assert record.raw_html is not None


def test_incruit_get_detail_none_on_failed_fetch() -> None:
    channel = IncruitChannel()
    channel._retry = lambda fn, *a, **kw: None  # type: ignore[method-assign]
    assert channel.get_detail("https://example/x") is None


def test_incruit_get_detail_none_on_non_200() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response("err", status=404)  # type: ignore[method-assign]
    assert channel.get_detail("https://job.incruit.com/x") is None


def test_incruit_get_detail_none_on_empty_url() -> None:
    channel = IncruitChannel()
    assert channel.get_detail("") is None


def test_incruit_get_detail_none_on_empty_body() -> None:
    channel = IncruitChannel()
    _bypass_retry(channel)
    channel._fetch = lambda url: _make_response("", status=200)  # type: ignore[method-assign]
    assert channel.get_detail("https://job.incruit.com/x") is None
