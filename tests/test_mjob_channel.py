"""Unit tests for MjobChannel.

All tests run **offline** — every network call is monkeypatched.
The fixtures here mirror plausible mjob.mainbiz.or.kr DOM shapes and exercise:

    * module + class import smoke
    * ``check()`` success, 4xx failure, and exception paths
    * ``list_jobs()`` — empty HTML returns ``[]``
    * ``list_jobs()`` — sample HTML with table rows yields valid JobRecords
    * ``list_jobs()`` — ALT_LIST_URL fallback triggers when primary is empty
    * ``list_jobs()`` — LANDING_URL generic scan fallback
    * ``list_jobs()`` — dedup by id prevents duplicates
    * ``list_jobs()`` — fetch failure returns ``[]``
    * ``list_jobs()`` — archetype inference (인턴/체험형/신입)
    * ``get_detail()`` — success yields a populated JobRecord
    * ``get_detail()`` — 404 returns None
    * ``get_detail()`` — parse exception returns None
    * ``_infer_archetype()`` — various title inputs
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.mjob import (
    ALT_LIST_URL,
    LANDING_URL,
    LIST_URL,
    ORG,
    MjobChannel,
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


# Primary list page — table.list tbody tr td a selector matches.
SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>KOSME 채용공고 목록</title></head>
<body>
  <table class="list">
    <tbody>
      <tr>
        <td><a href="/recruit/view.do?no=1001">중소기업진흥공단 신입 채용공고</a></td>
        <td>마감: 2026.05.30</td>
      </tr>
      <tr>
        <td><a href="/recruit/view.do?no=1002">KOSME 인턴 모집공고</a></td>
        <td>마감: 2026.06.15</td>
      </tr>
      <tr>
        <td><a href="/recruit/view.do?no=1003">중소기업 체험형 인턴 채용</a></td>
        <td>마감: 2026.07.01</td>
      </tr>
    </tbody>
  </table>
</body></html>
"""

# ALT list page — div.board-list ul li a selector matches.
SAMPLE_ALT_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>KOSME 일자리 목록</title></head>
<body>
  <div class="board-list">
    <ul>
      <li><a href="/work/view.do?no=2001">중소기업 채용 지원 프로그램</a></li>
      <li><a href="/work/view.do?no=2002">스타트업 신입 공채 공고</a></li>
    </ul>
  </div>
</body></html>
"""

# Landing generic scan — no primary selectors, /recruit/ href in anchors.
SAMPLE_LANDING_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>KOSME 일자리 포털</title></head>
<body>
  <div>
    <a href="/recruit/view.do?no=3001">중소벤처기업부 경력 채용 공고</a>
    <a href="/home">홈으로</a>
  </div>
</body></html>
"""

# Detail page HTML.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>중소기업진흥공단 신입 채용공고 | KOSME</title></head>
<body>
  <h1>중소기업진흥공단 신입 채용공고</h1>
  <table>
    <tr><td class="org">중소기업진흥공단</td><td>부서: 경영기획팀</td></tr>
    <tr><td>접수기간: 2026.05.01 ~ 2026.05.30</td></tr>
    <tr><td>지원 자격: 신입 / 대졸 이상</td></tr>
  </table>
</body></html>
"""


@pytest.fixture
def channel() -> MjobChannel:
    """Fresh MjobChannel instance per test."""
    return MjobChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import mjob

    assert hasattr(mjob, "MjobChannel")
    assert hasattr(mjob, "LIST_URL")
    assert hasattr(mjob, "ALT_LIST_URL")
    assert hasattr(mjob, "LANDING_URL")
    assert hasattr(mjob, "ORG")
    assert mjob.MjobChannel.name == "mjob"
    assert mjob.MjobChannel.tier == 2
    assert mjob.MjobChannel.default_legitimacy_tier == "T1"
    assert LIST_URL.startswith("https://mjob.mainbiz.or.kr")
    assert ALT_LIST_URL.startswith("https://mjob.mainbiz.or.kr")
    assert LANDING_URL.startswith("https://mjob.mainbiz.or.kr")
    assert ORG == "중소기업진흥공단 일자리"


def test_class_satisfies_channel_protocol(channel: MjobChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "mjob"
    assert channel.tier == 2
    assert channel.backend == "requests"
    assert channel.default_rate_per_minute == 6
    assert channel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_4xx(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="not found", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_exception(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_table_rows(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Primary list page with table.list rows yields valid JobRecords."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 3
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "mjob"
        assert job.source_tier == 2
        assert job.legitimacy_tier == "T1"
        assert job.org == ORG
        assert job.title
        assert str(job.source_url).startswith("https://mjob.mainbiz.or.kr")


def test_list_jobs_alt_list_url_fallback(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Primary LIST_URL returns empty HTML → channel retries against ALT_LIST_URL."""
    call_log: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_log.append(url)
        if url == LIST_URL:
            return _FakeResponse(text="<html><body></body></html>", status_code=200)
        if url == ALT_LIST_URL:
            return _FakeResponse(text=SAMPLE_ALT_LIST_HTML, status_code=200)
        return _FakeResponse(text="<html><body></body></html>", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert LIST_URL in call_log
    assert ALT_LIST_URL in call_log
    assert len(jobs) >= 1


def test_list_jobs_landing_generic_scan_fallback(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both list URLs empty → channel uses LANDING_URL generic scan."""
    call_log: list[str] = []

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        call_log.append(url)
        if url == LANDING_URL:
            return _FakeResponse(text=SAMPLE_LANDING_HTML, status_code=200)
        return _FakeResponse(text="<html><body></body></html>", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert LANDING_URL in call_log
    assert len(jobs) >= 1


def test_list_jobs_dedup_same_id(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same HTML on all URLs — dedup must prevent duplicates."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    ids = [j.id for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate IDs found after dedup"


def test_list_jobs_fetch_failure_returns_empty(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 responses on all URLs must yield an empty list — no fabrication."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="server error", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_intern_archetype(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """``인턴`` titles should map to archetype == 'INTERN'."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    intern_jobs = [j for j in jobs if j.archetype == "INTERN"]
    assert len(intern_jobs) >= 1
    assert any("인턴" in j.title for j in intern_jobs)


def test_list_jobs_experience_type_archetype(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``체험형`` titles should map to archetype == 'EXPERIENCE_TYPE'."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    exp_jobs = [j for j in jobs if j.archetype == "EXPERIENCE_TYPE"]
    assert len(exp_jobs) >= 1
    assert any("체험형" in j.title for j in exp_jobs)


def test_list_jobs_id_is_16_chars(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Every JobRecord id must be exactly 16 characters (SHA-256 prefix)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs
    for job in jobs:
        assert len(job.id) == 16, f"expected 16-char id, got {len(job.id)!r}"


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_parses_sample_html(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    url = "https://mjob.mainbiz.or.kr/recruit/view.do?no=1001"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "신입" in record.title or "중소기업진흥공단" in record.title
    assert record.source_channel == "mjob"
    assert record.source_tier == 2
    assert record.legitimacy_tier == "T1"
    assert record.raw_html is not None and len(record.raw_html) > 0
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 5


def test_get_detail_404_returns_none(channel: MjobChannel, monkeypatch: pytest.MonkeyPatch) -> None:
    """404 response must return None — never fabricate a record."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)
    result = channel.get_detail("https://mjob.mainbiz.or.kr/recruit/view.do?no=99999")
    assert result is None


def test_get_detail_parse_failure_returns_none(
    channel: MjobChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If internal parsing raises, get_detail must return None (not propagate)."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="<not-valid-html<><<<<", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.mjob.requests.get", fake_get)

    # BeautifulSoup is lenient with broken HTML — patch _parse_detail_html directly
    # to simulate a genuine parse error.
    def _raise(*_args: Any, **_kwargs: Any) -> None:
        raise ValueError("intentional parse error")

    monkeypatch.setattr(channel, "_parse_detail_html", _raise)
    result = channel.get_detail("https://mjob.mainbiz.or.kr/recruit/view.do?no=1")
    assert result is None


# ---------------------------------------------------------------------------
# _infer_archetype()
# ---------------------------------------------------------------------------


def test_infer_archetype_intern() -> None:
    assert MjobChannel._infer_archetype("KOSME 인턴 모집") == "INTERN"
    assert MjobChannel._infer_archetype("intern program") == "INTERN"


def test_infer_archetype_experience_type() -> None:
    assert MjobChannel._infer_archetype("중소기업 체험형 인턴 채용") == "EXPERIENCE_TYPE"


def test_infer_archetype_entry() -> None:
    assert MjobChannel._infer_archetype("중소기업 신입 공채") == "ENTRY"


def test_infer_archetype_general() -> None:
    assert MjobChannel._infer_archetype("경력직 채용공고") == "GENERAL"


def test_infer_archetype_empty() -> None:
    assert MjobChannel._infer_archetype("") is None
