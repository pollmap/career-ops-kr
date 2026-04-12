"""Unit tests for KiwoomKdaChannel.

All tests run **offline** — every network call is monkeypatched.
The fixtures here mirror the real recruit.kiwoom.com list / detail DOM
shapes (as inferred 2026-04) and exercise:

    * module + class import smoke
    * ``check()`` success and failure paths
    * ``list_jobs()`` — empty HTML returns ``[]``
    * ``list_jobs()`` — sample HTML yields >= 3 :class:`JobRecord`
    * ``list_jobs()`` — KDA keyword titles get archetype="KDA_COHORT"
    * ``list_jobs()`` — 인턴 titles get archetype="INTERN"
    * ``list_jobs()`` — deadline parsing
    * ``list_jobs()`` — org defaults to 키움증권
    * ``list_jobs()`` — legitimacy_tier == "T1"
    * ``list_jobs()`` — fetch failure returns []
    * ``get_detail()`` — None on fetch failure
    * ``get_detail()`` — sample HTML yields a record
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.kiwoom_kda import (
    BASE_URL,
    DEFAULT_HEADERS,
    LIST_URL,
    ORG,
    KiwoomKdaChannel,
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


# A stripped-down version of recruit.kiwoom.com landing page. The primary
# selector ``div.recruit-list a`` is present so the primary-path branch in
# ``_parse_list_html`` activates.
SAMPLE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>키움증권 채용</title></head>
<body>
  <div class="recruit-list">
    <a href="/detail/kda-12th">
      키움 디지털 아카데미 KDA 12기 모집 안내 (마감 2026.04.17)
    </a>
    <a href="/detail/fe-intern">
      프론트엔드 엔지니어 신입 인턴 채용 공고 ~2026.05.01
    </a>
    <a href="/detail/branch-sales">
      지점 영업직 경력 모집 (서울) 마감 2026.06.10
    </a>
  </div>
</body></html>
"""


# Realistic-ish detail-page HTML with known selectors.
SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>KDA 12기 모집 | 키움증권</title></head>
<body>
  <h1 class="recruit-title">키움 디지털 아카데미 KDA 12기 모집 안내</h1>
  <div class="recruit-info">
    <p>대상: 4년제 재학 또는 휴학생, 비전공 환영</p>
    <p>지원 마감: 2026-04-17</p>
    <p>교육 기간: 2026년 5월 ~ 2026년 10월 (6개월)</p>
    <p>장소: 서울 영등포구 키움증권 본사</p>
  </div>
</body></html>
"""


@pytest.fixture
def channel() -> KiwoomKdaChannel:
    """Fresh KiwoomKdaChannel instance per test."""
    return KiwoomKdaChannel()


# ---------------------------------------------------------------------------
# Smoke + contract
# ---------------------------------------------------------------------------


def test_module_importable() -> None:
    """Module loads and exposes the expected class + constants."""
    from career_ops_kr.channels import kiwoom_kda

    assert hasattr(kiwoom_kda, "KiwoomKdaChannel")
    assert hasattr(kiwoom_kda, "BASE_URL")
    assert hasattr(kiwoom_kda, "LIST_URL")
    assert hasattr(kiwoom_kda, "DEFAULT_HEADERS")
    assert hasattr(kiwoom_kda, "ORG")
    assert kiwoom_kda.KiwoomKdaChannel.name == "kiwoom_kda"
    assert kiwoom_kda.KiwoomKdaChannel.tier == 3
    assert kiwoom_kda.KiwoomKdaChannel.default_legitimacy_tier == "T1"
    assert BASE_URL.startswith("https://recruit.kiwoom.com")
    assert LIST_URL.startswith("https://recruit.kiwoom.com")
    assert "User-Agent" in DEFAULT_HEADERS
    assert ORG == "키움증권"


def test_class_satisfies_channel_protocol(channel: KiwoomKdaChannel) -> None:
    """Instance implements the structural Channel contract."""
    assert hasattr(channel, "check")
    assert hasattr(channel, "list_jobs")
    assert hasattr(channel, "get_detail")
    assert channel.name == "kiwoom_kda"
    assert channel.tier == 3
    assert channel.backend == "requests"


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    assert channel.check() is True


def test_check_returns_false_on_connection_error(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import requests

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        raise requests.ConnectionError("boom")

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    assert channel.check() is False


def test_check_returns_false_on_non_200(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="nope", status_code=503)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty_list(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


def test_list_jobs_parses_sample_html(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample HTML fixture yields at least 3 valid JobRecords."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) >= 3
    # All entries are JobRecords with the expected provenance.
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "kiwoom_kda"
        assert job.source_tier == 3
        assert job.legitimacy_tier == "T1"
        assert job.title
        # URL absolutized against base
        assert str(job.source_url).startswith("https://recruit.kiwoom.com/")


def test_list_jobs_kda_priority_archetype(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KDA 키워드가 있는 anchor 는 archetype == 'KDA_COHORT' 로 마킹된다."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    kda_jobs = [j for j in jobs if j.archetype == "KDA_COHORT"]
    assert len(kda_jobs) >= 1, "expected at least one KDA_COHORT entry from sample HTML"
    # KDA 12기 anchor 는 반드시 KDA_COHORT 여야 함 (인턴/신입 키워드보다 우선).
    kda_titles = [j.title for j in kda_jobs]
    assert any("KDA" in t or "디지털 아카데미" in t for t in kda_titles)


def test_list_jobs_intern_archetype(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KDA 키워드 없이 인턴 키워드만 있는 anchor 는 INTERN 으로 마킹된다."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    intern_jobs = [j for j in jobs if j.archetype == "INTERN"]
    # 프론트엔드 엔지니어 신입 인턴 anchor 는 INTERN 이어야 함.
    assert len(intern_jobs) >= 1, "expected at least one INTERN entry"
    # 그리고 그 entry 의 title 에는 KDA 키워드가 없어야 함 (KDA 우선 매칭 검증).
    for j in intern_jobs:
        assert "KDA" not in j.title and "디지털 아카데미" not in j.title


def test_list_jobs_extracts_deadlines(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """KDA 12기 마감일(2026-04-17)이 파싱돼야 한다."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    # 어떤 job 이든 deadline 이 파싱된 게 1건 이상 있어야 한다.
    assert any(j.deadline is not None for j in jobs), (
        "expected at least one deadline parsed from sample HTML"
    )
    # KDA 12기 anchor 의 deadline 은 정확히 2026-04-17 이어야 한다.
    kda_jobs = [j for j in jobs if j.archetype == "KDA_COHORT"]
    assert kda_jobs, "no KDA_COHORT job to check deadline on"
    kda_deadlines = [j.deadline for j in kda_jobs if j.deadline is not None]
    assert kda_deadlines, "KDA_COHORT job has no parsed deadline"
    assert any(d.year == 2026 and d.month == 4 and d.day == 17 for d in kda_deadlines), (
        f"expected 2026-04-17 in KDA deadlines, got {kda_deadlines}"
    )


def test_list_jobs_org_is_kiwoom(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 record 의 org 는 키움증권 (또는 container 추출값) 이다."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs, "expected at least one job"
    # SAMPLE HTML 에는 .coName 등 별도 셀렉터가 없으므로 모두 fallback ORG 여야 한다.
    for j in jobs:
        assert j.org == ORG == "키움증권"


def test_list_jobs_legitimacy_t1(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 record 는 T1(공식) legitimacy 로 마킹된다."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs
    for j in jobs:
        assert j.legitimacy_tier == "T1"


def test_list_jobs_fetch_failure_returns_empty(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-200 응답 → 빈 리스트. 절대 가짜 데이터 생성 금지."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="error page", status_code=500)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    jobs = channel.list_jobs()
    assert jobs == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_fetch_failure_returns_none(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    result = channel.get_detail("https://recruit.kiwoom.com/detail/missing")
    assert result is None


def test_get_detail_parses_sample_html(
    channel: KiwoomKdaChannel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample detail HTML fixture yields a populated JobRecord."""

    def fake_get(url: str, **_: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kiwoom_kda.requests.get", fake_get)
    url = "https://recruit.kiwoom.com/detail/kda-12th"
    record = channel.get_detail(url)
    assert record is not None
    assert isinstance(record, JobRecord)
    assert "KDA" in record.title or "디지털 아카데미" in record.title
    assert record.source_channel == "kiwoom_kda"
    assert record.source_tier == 3
    assert record.legitimacy_tier == "T1"
    assert record.org == ORG
    assert record.archetype == "KDA_COHORT"
    assert record.raw_html is not None and len(record.raw_html) > 0
    # Deadline "2026-04-17" should be parsed.
    assert record.deadline is not None
    assert record.deadline.year == 2026
    assert record.deadline.month == 4
    assert record.deadline.day == 17
