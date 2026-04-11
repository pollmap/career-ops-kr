"""Tests for :class:`career_ops_kr.channels.jasoseol.JasoseolChannel`.

Covers:
    * Import smoke — class attributes, registry contract.
    * ``check()`` — mocked ``requests.get`` returning 200 / 500 / exception.
    * ``list_jobs()`` — empty HTML, fixture HTML with at least one card,
      Next.js ``__NEXT_DATA__`` fallback, filter rules (keyword/category),
      deadline sort.
    * ``get_detail()`` — ``None`` handling for empty url / fetch failure.

No real network — every HTTP call is intercepted via pytest-mock.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest

from career_ops_kr.channels.base import BaseChannel, JobRecord
from career_ops_kr.channels.jasoseol import JasoseolChannel

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------


FIXTURE_LIST_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head><title>자소설 | 채용공고</title></head>
<body>
  <nav>
    <a href="/login">로그인</a>
    <a href="/join">회원가입</a>
  </nav>
  <main>
    <ul class="recruit-list">
      <li>
        <a href="/recruit/12345">
          토스 | 블록체인 엔지니어 신입 모집
        </a>
        <div class="meta">서울 강남 · D-7 · 지원자 1,245 · 경쟁률 12.5:1 · 조회 9,821</div>
      </li>
      <li>
        <a href="/recruit/22222">
          카카오뱅크 | 금융IT 개발자 인턴 (체험형)
        </a>
        <div class="meta">경기 판교 · 2026-05-20 마감 · 지원자 842 · 조회 5,104</div>
      </li>
      <li>
        <a href="/recruit/33333">
          두나무 | 디지털자산 리서치 경력 채용
        </a>
        <div class="meta">서울 여의도 · 상시채용 · 지원자 203</div>
      </li>
      <li>
        <!-- Non-posting link that should be filtered out by negatives. -->
        <a href="/privacy">개인정보 처리방침</a>
      </li>
    </ul>
  </main>
</body>
</html>
"""


FIXTURE_NEXT_DATA_HTML = """
<!DOCTYPE html>
<html><head><title>자소설</title></head><body>
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "recruits": [
        {
          "id": 77777,
          "title": "신한투자증권 블록체인부 체험형 인턴",
          "company_name": "신한투자증권",
          "location": "서울 여의도",
          "end_date": "2026-05-15",
          "d_day": "D-30"
        },
        {
          "id": 88888,
          "title": "KB국민은행 핀테크 신입 공채",
          "company": {"name": "KB국민은행"},
          "region": "서울",
          "deadline": "2026-04-25"
        }
      ]
    }
  }
}
</script>
</body></html>
"""


EMPTY_HTML = "<html><body><p>조회 결과 없음</p></body></html>"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal ``requests.Response``-compatible stub."""

    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


# ---------------------------------------------------------------------------
# Smoke — class attributes / registry contract
# ---------------------------------------------------------------------------


def test_class_attributes() -> None:
    assert JasoseolChannel.name == "jasoseol"
    assert JasoseolChannel.tier == 1
    assert JasoseolChannel.backend == "requests"
    assert JasoseolChannel.default_legitimacy_tier == "T1"
    assert issubclass(JasoseolChannel, BaseChannel)


def test_instantiation_defaults() -> None:
    channel = JasoseolChannel()
    assert channel.name == "jasoseol"
    assert channel.tier == 1
    assert channel.base_url.startswith("https://jasoseol.com")
    assert channel.list_url.endswith("/recruit")


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


def test_check_returns_true_on_200(mocker: Any) -> None:
    mocker.patch(
        "career_ops_kr.channels.jasoseol.requests.get",
        return_value=_FakeResponse(status_code=200, text="ok"),
    )
    assert JasoseolChannel().check() is True


def test_check_returns_false_on_500(mocker: Any) -> None:
    mocker.patch(
        "career_ops_kr.channels.jasoseol.requests.get",
        return_value=_FakeResponse(status_code=500, text=""),
    )
    assert JasoseolChannel().check() is False


def test_check_returns_false_on_exception(mocker: Any) -> None:
    import requests

    mocker.patch(
        "career_ops_kr.channels.jasoseol.requests.get",
        side_effect=requests.ConnectionError("network down"),
    )
    assert JasoseolChannel().check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


def _patch_fetch(mocker: Any, html: str | None) -> None:
    """Short-circuit ``_fetch_html`` so tests don't exercise the real retry."""
    mocker.patch.object(
        JasoseolChannel,
        "_fetch_html",
        return_value=html,
    )


def test_list_jobs_empty_html_returns_empty(mocker: Any) -> None:
    _patch_fetch(mocker, EMPTY_HTML)
    results = JasoseolChannel().list_jobs()
    assert results == []


def test_list_jobs_none_fetch_returns_empty(mocker: Any) -> None:
    _patch_fetch(mocker, None)
    results = JasoseolChannel().list_jobs()
    assert results == []


def test_list_jobs_parses_anchor_fixture(mocker: Any) -> None:
    _patch_fetch(mocker, FIXTURE_LIST_HTML)
    records = JasoseolChannel().list_jobs()

    assert len(records) >= 1, (
        f"expected at least one record from anchor fixture, got {len(records)}"
    )

    # Every record is a valid JobRecord with canonical fields filled in.
    for rec in records:
        assert isinstance(rec, JobRecord)
        assert rec.source_channel == "jasoseol"
        assert rec.source_tier == 1
        assert rec.legitimacy_tier == "T1"
        assert rec.id and len(rec.id) == 16
        assert "jasoseol.com" in str(rec.source_url)
        assert rec.title

    # The D-7 card must surface with a future deadline computed from today.
    dday_titles = [r for r in records if "블록체인" in r.title and r.deadline is not None]
    assert dday_titles, "D-7 블록체인 card should have a deadline"
    tomorrow_plus_six = date.today() + timedelta(days=7)
    assert any(r.deadline == tomorrow_plus_six for r in dday_titles), (
        "D-7 should resolve to today+7"
    )

    # Category + competition metadata should land in description.
    blockchain = next((r for r in records if "블록체인" in r.title), None)
    assert blockchain is not None
    assert "D-7" in blockchain.description
    assert "지원자 1,245" in blockchain.description


def test_list_jobs_next_data_fallback(mocker: Any) -> None:
    _patch_fetch(mocker, FIXTURE_NEXT_DATA_HTML)
    records = JasoseolChannel().list_jobs()

    assert len(records) >= 2
    titles = [r.title for r in records]
    assert any("신한투자증권" in t or "체험형 인턴" in t for t in titles)

    # End_date from the next-data payload should parse into a real date.
    dated = [r for r in records if r.deadline is not None]
    assert dated, "end_date field should yield at least one real deadline"
    assert any(r.deadline == date(2026, 5, 15) for r in dated)


def test_list_jobs_keyword_filter(mocker: Any) -> None:
    _patch_fetch(mocker, FIXTURE_LIST_HTML)
    records = JasoseolChannel().list_jobs({"keyword": "카카오"})
    # All surviving records must mention the keyword somewhere.
    assert records, "keyword filter should not drop every card"
    for rec in records:
        blob = f"{rec.title} {rec.org} {rec.description}".lower()
        assert "카카오" in blob


def test_list_jobs_category_intern_filter(mocker: Any) -> None:
    _patch_fetch(mocker, FIXTURE_LIST_HTML)
    records = JasoseolChannel().list_jobs({"category": "인턴"})
    assert records
    for rec in records:
        blob = f"{rec.title} {rec.description}"
        assert any(tok in blob for tok in ("인턴", "체험형", "intern"))


def test_list_jobs_pages_query_clamped(mocker: Any) -> None:
    calls: list[str] = []

    def fake_fetch(self: Any, url: str) -> str:
        calls.append(url)
        return FIXTURE_LIST_HTML

    mocker.patch.object(JasoseolChannel, "_fetch_html", fake_fetch)

    records = JasoseolChannel().list_jobs({"pages": 3})
    assert len(calls) == 3
    # Dedup should be strict — identical HTML three times → same ids → single set.
    ids = {r.id for r in records}
    assert len(ids) == len(records)


def test_list_jobs_deadline_sort(mocker: Any) -> None:
    _patch_fetch(mocker, FIXTURE_LIST_HTML)
    records = JasoseolChannel().list_jobs({"sort": "deadline"})

    dated = [r for r in records if r.deadline is not None]
    # Ascending — first dated record should have the smallest (soonest) deadline.
    if len(dated) >= 2:
        assert dated[0].deadline <= dated[1].deadline


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_none_url_returns_none() -> None:
    channel = JasoseolChannel()
    assert channel.get_detail("") is None


def test_get_detail_fetch_failure_returns_none(mocker: Any) -> None:
    mocker.patch.object(JasoseolChannel, "_fetch_html", return_value=None)
    channel = JasoseolChannel()
    assert channel.get_detail("https://jasoseol.com/recruit/99999") is None


def test_get_detail_parses_fixture(mocker: Any) -> None:
    detail_html = """
    <html>
      <head><title>토스 | 블록체인 엔지니어 신입 모집</title></head>
      <body>
        <h1>토스</h1>
        <main>
          <p>지원 자격: 4년제 재학/휴학생</p>
          <p>마감: 2026-05-30</p>
          <p>지원자 1,245</p>
          <p>경쟁률 12.5:1</p>
        </main>
      </body>
    </html>
    """
    mocker.patch.object(JasoseolChannel, "_fetch_html", return_value=detail_html)

    channel = JasoseolChannel()
    record = channel.get_detail("https://jasoseol.com/recruit/12345")

    assert record is not None
    assert record.source_channel == "jasoseol"
    assert record.source_tier == 1
    assert record.legitimacy_tier == "T1"
    assert "블록체인" in record.title
    assert record.deadline == date(2026, 5, 30)
    assert "지원자 1,245" in record.description
    assert record.raw_html is not None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def test_split_title_org_pipe() -> None:
    title, org = JasoseolChannel._split_title_org("토스 | 블록체인 엔지니어")
    assert title == "블록체인 엔지니어"
    assert org == "토스"


def test_split_title_org_no_separator() -> None:
    title, org = JasoseolChannel._split_title_org("단일 제목")
    assert title == "단일 제목"
    assert org == ""


def test_infer_archetype_variants() -> None:
    assert JasoseolChannel._infer_archetype("체험형 인턴 모집") == "INTERN"
    assert JasoseolChannel._infer_archetype("신입 공채") == "NEW_GRAD"
    assert JasoseolChannel._infer_archetype("경력직 채용") == "EXPERIENCED"
    assert JasoseolChannel._infer_archetype("기타") is None


def test_extract_location_detects_korean_region() -> None:
    assert JasoseolChannel._extract_location("서울 강남구 역삼동") is not None
    assert JasoseolChannel._extract_location("대전 유성구") is not None
    assert JasoseolChannel._extract_location("") is None


@pytest.mark.parametrize(
    "pages_input,expected_calls",
    [
        (1, 1),
        (2, 2),
        (0, 1),
        ("bad", 1),
        (99, 10),  # clamped to 10
    ],
)
def test_list_jobs_pages_clamping(mocker: Any, pages_input: Any, expected_calls: int) -> None:
    calls: list[str] = []

    def fake_fetch(self: Any, url: str) -> str:
        calls.append(url)
        return EMPTY_HTML

    mocker.patch.object(JasoseolChannel, "_fetch_html", fake_fetch)
    JasoseolChannel().list_jobs({"pages": pages_input})
    assert len(calls) == expected_calls
