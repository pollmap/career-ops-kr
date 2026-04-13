"""Tests for the Saramin (사람인) channel.

Covers:
    * import + registration smoke
    * ``check()`` success/failure via monkeypatched session
    * ``list_jobs()`` empty-HTML → ``[]``
    * ``list_jobs()`` fixture HTML → >= 1 record
    * **페이지네이션**: ``pages=N`` 파라미터가 정확히 ``N`` 번의 session.get
      호출로 반영되는지 counter 로 검증 (전수 수집 철학의 핵심).
    * ``get_detail()`` None handling 및 성공 경로
"""

from __future__ import annotations

from typing import Any

import pytest
import requests

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.saramin import (
    DEFAULT_PAGES,
    MAX_PAGES,
    SaraminChannel,
)

# ---------------------------------------------------------------------------
# Fake response infrastructure
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for ``requests.Response`` used in tests."""

    def __init__(
        self,
        text: str = "",
        status_code: int = 200,
        encoding: str | None = "utf-8",
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = encoding


def _install_fake_session_get(
    monkeypatch: pytest.MonkeyPatch,
    channel: SaraminChannel,
    *,
    response_factory: Any,
) -> list[str]:
    """Replace ``channel._session.get`` with a counter-recording fake.

    Returns the shared ``calls`` list so tests can assert on request count.
    ``response_factory`` may be a single ``_FakeResponse`` or a callable
    ``(url, call_index) -> _FakeResponse``.
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
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_LIST_HTML = """
<html><body>
  <div class="list_recruit">
    <div class="item_recruit">
      <div class="area_corp">
        <strong class="corp_name"><a href="/company?id=1">테스트기업A</a></strong>
      </div>
      <div class="area_job">
        <h2 class="job_tit"><a href="/zf_user/jobs/view?rec_idx=100001">백엔드 개발자 (신입)</a></h2>
        <div class="job_condition">
          <span>서울 강남구</span><span>신입</span><span>정규직</span>
        </div>
        <div class="job_sector">
          <a>Python</a><a>Django</a><a>PostgreSQL</a>
        </div>
      </div>
      <div class="job_date"><span class="date">~ 2026-05-31</span></div>
    </div>
    <div class="item_recruit">
      <div class="area_corp">
        <strong class="corp_name"><a href="/company?id=2">핀테크스타트업B</a></strong>
      </div>
      <div class="area_job">
        <h2 class="job_tit"><a href="/zf_user/jobs/view?rec_idx=100002">디지털자산 리서치 인턴</a></h2>
        <div class="job_condition">
          <span>서울 여의도</span><span>인턴</span>
        </div>
        <div class="job_sector"><a>블록체인</a><a>리서치</a></div>
      </div>
      <div class="job_date"><span class="date">~ 04/20(토)</span></div>
    </div>
  </div>
</body></html>
"""

SAMPLE_DETAIL_HTML = """
<html><head>
  <title>사람인 - 백엔드 개발자 (신입) | 테스트기업A 채용공고</title>
  <meta property="og:title" content="백엔드 개발자 (신입)">
  <meta property="og:site_name" content="테스트기업A">
</head><body>
  <div class="wrap_tit_job"><h1 class="tit_job">백엔드 개발자 (신입)</h1></div>
  <div class="company_name"><a>테스트기업A</a></div>
  <div class="work_place">서울 강남구 테헤란로</div>
  <div class="job_content">
    자격 요건: Python 3.11, Django 4+, PostgreSQL.
    우대사항: AWS, 블록체인 경험.
    마감일: 2026-05-31
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> SaraminChannel:
    return SaraminChannel()


# ---------------------------------------------------------------------------
# 1. Import + class-level invariants
# ---------------------------------------------------------------------------


def test_saramin_class_metadata() -> None:
    """Class attributes match the spec (T1, tier 1, requests backend, rate 8)."""
    assert SaraminChannel.name == "saramin"
    assert SaraminChannel.tier == 1
    assert SaraminChannel.backend == "requests"
    assert SaraminChannel.default_rate_per_minute == 8
    assert SaraminChannel.default_legitimacy_tier == "T1"


def test_saramin_constructor_defaults(channel: SaraminChannel) -> None:
    """Constructor wires up session + URLs."""
    assert channel.list_url.endswith("/zf_user/search/recruit")
    assert channel.landing_url.startswith("https://www.saramin.co.kr/")
    assert isinstance(channel._session, requests.Session)
    assert "career-ops-kr" in channel._session.headers["User-Agent"]


# ---------------------------------------------------------------------------
# 2. check()
# ---------------------------------------------------------------------------


def test_check_success(monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel) -> None:
    _install_fake_session_get(
        monkeypatch, channel, response_factory=_FakeResponse(text="ok", status_code=200)
    )
    assert channel.check() is True


def test_check_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    def _raise(_url: str, _idx: int) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    _install_fake_session_get(monkeypatch, channel, response_factory=_raise)
    assert channel.check() is False


def test_check_non_200_returns_false(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch, channel, response_factory=_FakeResponse(text="", status_code=500)
    )
    assert channel.check() is False


# ---------------------------------------------------------------------------
# 3. list_jobs() — empty HTML path
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text="<html><body></body></html>", status_code=200),
    )
    result = channel.list_jobs({"pages": 1, "strict": False})
    assert result == []


def test_list_jobs_http_error_returns_empty(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text="", status_code=503),
    )
    # _retry will retry 4x per page before giving up → we only care about final result
    result = channel.list_jobs({"pages": 1, "strict": False})
    assert result == []


# ---------------------------------------------------------------------------
# 4. list_jobs() — fixture HTML path
# ---------------------------------------------------------------------------


def test_list_jobs_fixture_yields_records(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text=SAMPLE_LIST_HTML, status_code=200),
    )
    # Use pages=1 so dedup early-stop does not discard subsequent identical pages.
    jobs = channel.list_jobs({"pages": 1, "keyword": "블록체인", "strict": False})

    assert len(jobs) >= 1, "fixture HTML should yield at least one record"
    titles = [j.title for j in jobs]
    assert any("백엔드 개발자" in t for t in titles)
    assert any("디지털자산" in t for t in titles)

    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "saramin"
        assert job.source_tier == 1
        assert job.legitimacy_tier == "T1"
        assert "saramin.co.kr" in str(job.source_url)
        assert job.title  # non-empty


def test_list_jobs_extracts_company_and_location(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text=SAMPLE_LIST_HTML, status_code=200),
    )
    jobs = channel.list_jobs({"pages": 1, "strict": False})
    backend_job = next((j for j in jobs if "백엔드" in j.title), None)
    assert backend_job is not None
    assert backend_job.org == "테스트기업A"
    assert backend_job.location is not None and "서울" in backend_job.location


# ---------------------------------------------------------------------------
# 5. Pagination — the critical test for 전수 수집
# ---------------------------------------------------------------------------


def test_pagination_pages_param_triggers_n_requests(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    """``pages=N`` 은 정확히 N 번의 session.get 호출을 유발해야 한다.

    각 페이지마다 *다른* rec_idx 를 반환해야 early-stop dedup 로직이
    발동하지 않음 — 이렇게 해야 "모든 페이지가 실제로 요청되었다"를
    입증할 수 있다.
    """

    def _factory(url: str, idx: int) -> _FakeResponse:
        html = f"""
        <html><body>
          <div class="item_recruit">
            <div class="area_corp">
              <strong class="corp_name"><a>테스트기업P{idx}</a></strong>
            </div>
            <div class="area_job">
              <h2 class="job_tit"><a href="/zf_user/jobs/view?rec_idx=900{idx:03d}">공고 페이지 {idx + 1}</a></h2>
              <div class="job_condition"><span>서울</span></div>
            </div>
            <div class="job_date"><span class="date">~ 2026-06-30</span></div>
          </div>
        </body></html>
        """
        return _FakeResponse(text=html, status_code=200)

    calls = _install_fake_session_get(monkeypatch, channel, response_factory=_factory)

    jobs = channel.list_jobs({"pages": 4, "keyword": "개발", "strict": False})

    assert len(calls) == 4, f"expected 4 page requests, got {len(calls)}: {calls}"
    # ``recruitPage=<n>`` 가 각 URL 에 실제로 박혀 있어야 한다.
    for n in (1, 2, 3, 4):
        assert any(f"recruitPage={n}" in url for url in calls), (
            f"recruitPage={n} missing from calls: {calls}"
        )
    # 4 페이지 각각 서로 다른 rec_idx → dedup 이 작동해도 4건 유지
    assert len(jobs) == 4
    assert len({str(j.source_url) for j in jobs}) == 4


def test_pagination_default_pages_constant_is_five() -> None:
    """기본값 = 5 (전수 수집 지향)."""
    assert DEFAULT_PAGES == 5


def test_pagination_pages_clamped_to_max(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    """pages=999 는 MAX_PAGES 로 clamp 되어야 한다."""
    assert MAX_PAGES == 20
    assert SaraminChannel._resolve_pages(999) == MAX_PAGES
    assert SaraminChannel._resolve_pages(0) == 1
    assert SaraminChannel._resolve_pages(-5) == 1
    assert SaraminChannel._resolve_pages(None) == DEFAULT_PAGES
    assert SaraminChannel._resolve_pages("bad") == DEFAULT_PAGES
    assert SaraminChannel._resolve_pages(7) == 7


def test_pagination_early_stop_on_zero_new_records(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    """같은 공고만 반복되면 early-stop 이 발동해야 한다."""
    # 매번 같은 rec_idx 반환 → 첫 페이지만 새 공고, 나머지는 중복
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text=SAMPLE_LIST_HTML, status_code=200),
    )
    jobs = channel.list_jobs({"pages": 5, "strict": False})
    assert len(jobs) == 2  # SAMPLE_LIST_HTML 에는 정확히 2개 카드


def test_pagination_per_page_failure_does_not_break_others(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    """페이지 2가 실패해도 1, 3, 4는 살아남아야 한다 (전수 정책)."""

    def _factory(url: str, idx: int) -> _FakeResponse:
        # idx 는 _retry 재시도 때문에 불안정할 수 있어 recruitPage 를 직접 본다
        if "recruitPage=2" in url:
            return _FakeResponse(text="", status_code=500)
        html = f"""
        <html><body>
          <div class="item_recruit">
            <h2 class="job_tit"><a href="/zf_user/jobs/view?rec_idx=P{idx}">공고{idx}</a></h2>
            <div class="job_condition"><span>서울</span></div>
          </div>
        </body></html>
        """
        return _FakeResponse(text=html, status_code=200)

    _install_fake_session_get(monkeypatch, channel, response_factory=_factory)
    jobs = channel.list_jobs({"pages": 4, "strict": False})
    # 페이지 2만 실패, 나머지 3페이지에서 최소 각 1건씩은 수집
    assert len(jobs) >= 3


# ---------------------------------------------------------------------------
# 6. URL building
# ---------------------------------------------------------------------------


def test_build_list_url_includes_keyword_and_page(channel: SaraminChannel) -> None:
    url = channel._build_list_url(page=3, keyword="블록체인")
    assert "recruitPage=3" in url
    # URL-encoded 블록체인
    assert "searchword=" in url
    assert "searchType=search" in url


def test_build_list_url_includes_category_and_location(
    channel: SaraminChannel,
) -> None:
    url = channel._build_list_url(page=1, category="3", location="101000")
    assert "cat_mcls=3" in url
    assert "loc_cd=101000" in url


# ---------------------------------------------------------------------------
# 7. get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_none_url_returns_none(channel: SaraminChannel) -> None:
    assert channel.get_detail("") is None


def test_get_detail_fetch_failure_returns_none(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    def _raise(_url: str, _idx: int) -> _FakeResponse:
        raise requests.Timeout("slow")

    _install_fake_session_get(monkeypatch, channel, response_factory=_raise)
    result = channel.get_detail("https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=999")
    assert result is None


def test_get_detail_success_extracts_fields(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200),
    )
    url = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=100001"
    detail = channel.get_detail(url)
    assert detail is not None
    assert isinstance(detail, JobRecord)
    assert "백엔드 개발자" in detail.title
    assert detail.org and "테스트기업A" in detail.org
    assert detail.source_channel == "saramin"
    assert detail.source_tier == 1
    assert detail.raw_html is not None
    assert detail.description  # body text captured
    assert detail.legitimacy_tier == "T1"


def test_get_detail_http_error_returns_none(
    monkeypatch: pytest.MonkeyPatch, channel: SaraminChannel
) -> None:
    _install_fake_session_get(
        monkeypatch,
        channel,
        response_factory=_FakeResponse(text="", status_code=404),
    )
    assert channel.get_detail("https://www.saramin.co.kr/zf_user/jobs/view?rec_idx=x") is None
