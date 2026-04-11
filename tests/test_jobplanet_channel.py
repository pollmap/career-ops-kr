"""Tests for :mod:`career_ops_kr.channels.jobplanet`.

All network I/O is mocked — these tests must pass offline.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.jobplanet import (
    BASE_URL,
    SEARCH_URL,
    JobPlanetChannel,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SEARCH_HTML_WITH_CARDS = """
<!DOCTYPE html>
<html lang="ko">
<head><title>잡플래닛 채용</title></head>
<body>
  <div class="posting_list">
    <article class="posting">
      <a href="/job_postings/1001">
        <h2 class="posting_title">블록체인 리서치 어시스턴트 (인턴)</h2>
      </a>
      <div class="company_name">디지털자산거래소</div>
      <div class="location">서울 강남구</div>
      <p>접수 마감: 2026.04.17</p>
      <span class="rating">평점 4.2 / 5.0</span>
    </article>
    <article class="posting">
      <a href="/job_postings/1002">
        <h3 class="job_posting__title">핀테크 프로덕트 매니저</h3>
      </a>
      <div class="posting_company">토스페이먼츠</div>
      <div class="posting_location">서울 역삼동</div>
      <p>지원 마감일 2026-05-01</p>
      <span>리뷰 평점 3.9점</span>
    </article>
    <article class="posting">
      <a href="/company/42/jobs/7">
        <h2 class="posting_title">데이터 엔지니어 신입</h2>
      </a>
      <div class="company">에프앤가이드</div>
    </article>
  </div>
</body>
</html>
"""


_SEARCH_HTML_ANCHOR_ONLY = """
<!DOCTYPE html>
<html>
<body>
  <ul class="custom-list">
    <li>
      <a href="/job_postings/2050">AI 엔지니어 | 카카오페이</a>
      <span>마감 2026.06.10</span>
    </li>
    <li>
      <a href="/job_postings/2051">금융데이터 인턴 · 한국거래소</a>
      <span>서울 여의도</span>
    </li>
    <li>
      <a href="/careers/about">About us</a>
    </li>
    <li>
      <a href="javascript:void(0)">Disabled</a>
    </li>
  </ul>
</body>
</html>
"""


_SEARCH_HTML_EMPTY = """
<!DOCTYPE html>
<html><body><div class="posting_list"></div></body></html>
"""


_DETAIL_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head><title>잡플래닛 공고 상세</title></head>
<body>
  <h1 class="posting_title">블록체인 리서치 어시스턴트 (인턴)</h1>
  <div class="company_name">디지털자산거래소</div>
  <div class="location">서울 강남구 테헤란로</div>
  <section class="posting_body">
    <p>지원 자격: 경영/경제/컴퓨터공학 3학년 이상</p>
    <p>접수 마감: 2026.04.17</p>
  </section>
  <div class="reviews">
    <span>평점 4.2 / 5.0</span>
  </div>
</body>
</html>
"""


def _mk_response(text: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.text = text
    return resp


# ---------------------------------------------------------------------------
# Smoke / metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_import_smoke() -> None:
    assert JobPlanetChannel.name == "jobplanet"
    assert JobPlanetChannel.tier == 1
    assert JobPlanetChannel.backend == "requests"
    assert JobPlanetChannel.default_legitimacy_tier == "T1"
    assert BASE_URL.startswith("https://www.jobplanet.co.kr")
    assert "/job_postings/search_results" in SEARCH_URL


@pytest.mark.unit
def test_instantiation_sets_logger_and_rate_limiter() -> None:
    ch = JobPlanetChannel()
    assert ch.name == "jobplanet"
    assert ch.logger is not None
    assert ch._rate.per_minute == JobPlanetChannel.default_rate_per_minute


# ---------------------------------------------------------------------------
# check()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_success() -> None:
    ch = JobPlanetChannel()
    with patch(
        "career_ops_kr.channels.jobplanet.requests.get",
        return_value=_mk_response("<html><body>ok</body></html>", status=200),
    ) as mock_get:
        assert ch.check() is True
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == SEARCH_URL or kwargs.get("url") == SEARCH_URL
    assert "User-Agent" in kwargs["headers"]


@pytest.mark.unit
def test_check_non_200_returns_false() -> None:
    ch = JobPlanetChannel()
    with patch(
        "career_ops_kr.channels.jobplanet.requests.get",
        return_value=_mk_response("", status=503),
    ):
        assert ch.check() is False


@pytest.mark.unit
def test_check_request_exception_returns_false() -> None:
    import requests as _requests

    ch = JobPlanetChannel()
    with patch(
        "career_ops_kr.channels.jobplanet.requests.get",
        side_effect=_requests.ConnectionError("boom"),
    ):
        assert ch.check() is False


# ---------------------------------------------------------------------------
# list_jobs()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_jobs_empty_html_returns_empty() -> None:
    ch = JobPlanetChannel()
    with patch.object(
        ch,
        "_fetch_html",
        return_value=_SEARCH_HTML_EMPTY,
    ) as mock_fetch:
        result = ch.list_jobs({"pages": 2})
    assert result == []
    # 첫 페이지가 비었으면 추가 페이지 요청을 중단해야 함.
    assert mock_fetch.call_count == 1


@pytest.mark.unit
def test_list_jobs_parses_primary_cards() -> None:
    ch = JobPlanetChannel()

    def fetch(url: str) -> str | None:
        if "page=1" in url:
            return _SEARCH_HTML_WITH_CARDS
        return _SEARCH_HTML_EMPTY

    with patch.object(ch, "_fetch_html", side_effect=fetch):
        jobs = ch.list_jobs({"pages": 3, "keyword": "블록체인"})

    assert len(jobs) == 3
    assert all(isinstance(j, JobRecord) for j in jobs)
    titles = [j.title for j in jobs]
    assert any("블록체인 리서치" in t for t in titles)
    assert any("핀테크 프로덕트 매니저" in t for t in titles)

    intern_card = next(j for j in jobs if "인턴" in j.title)
    assert intern_card.archetype == "INTERN"
    assert intern_card.source_channel == "jobplanet"
    assert intern_card.source_tier == 1
    assert intern_card.legitimacy_tier == "T1"
    assert intern_card.org == "디지털자산거래소"
    assert intern_card.location == "서울 강남구"
    # 평점 추출 → description 에 포함
    assert "평점" in intern_card.description


@pytest.mark.unit
def test_list_jobs_anchor_fallback() -> None:
    ch = JobPlanetChannel()

    def fetch(url: str) -> str | None:
        if "page=1" in url:
            return _SEARCH_HTML_ANCHOR_ONLY
        return _SEARCH_HTML_EMPTY

    with patch.object(ch, "_fetch_html", side_effect=fetch):
        jobs = ch.list_jobs({"pages": 2})

    assert len(jobs) >= 2
    urls = [str(j.source_url) for j in jobs]
    assert any("/job_postings/2050" in u for u in urls)
    assert any("/job_postings/2051" in u for u in urls)
    # 자바스크립트/About 링크는 걸러져야 함.
    assert not any("/careers/about" in u for u in urls)
    assert not any("javascript" in u for u in urls)


@pytest.mark.unit
def test_list_jobs_deduplicates_across_pages() -> None:
    ch = JobPlanetChannel()
    # 두 페이지 다 같은 HTML → dedupe 시 3개만 남아야 한다
    with patch.object(ch, "_fetch_html", return_value=_SEARCH_HTML_WITH_CARDS):
        jobs = ch.list_jobs({"pages": 2})
    assert len(jobs) == 3


@pytest.mark.unit
def test_list_jobs_fetch_failure_returns_empty() -> None:
    ch = JobPlanetChannel()
    with patch.object(ch, "_fetch_html", return_value=None):
        jobs = ch.list_jobs({"pages": 5})
    assert jobs == []


@pytest.mark.unit
def test_list_jobs_invalid_pages_uses_default() -> None:
    ch = JobPlanetChannel()
    with patch.object(
        ch,
        "_fetch_html",
        return_value=_SEARCH_HTML_EMPTY,
    ) as mock_fetch:
        ch.list_jobs({"pages": "bad"})
    # 기본값으로라도 최소 1회는 호출되어야 함.
    assert mock_fetch.call_count >= 1


@pytest.mark.unit
def test_list_jobs_no_query_uses_defaults() -> None:
    ch = JobPlanetChannel()
    with patch.object(ch, "_fetch_html", return_value=_SEARCH_HTML_EMPTY):
        assert ch.list_jobs() == []
        assert ch.list_jobs(None) == []


# ---------------------------------------------------------------------------
# get_detail()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_detail_happy_path() -> None:
    ch = JobPlanetChannel()
    url = "https://www.jobplanet.co.kr/job_postings/1001"
    with patch.object(ch, "_fetch_html", return_value=_DETAIL_HTML):
        rec = ch.get_detail(url)
    assert rec is not None
    assert rec.title.startswith("블록체인 리서치 어시스턴트")
    assert rec.org == "디지털자산거래소"
    assert rec.source_channel == "jobplanet"
    assert rec.source_tier == 1
    assert rec.legitimacy_tier == "T1"
    assert rec.archetype == "INTERN"
    assert rec.raw_html is not None
    assert "평점" in rec.description
    assert rec.location == "서울 강남구 테헤란로"


@pytest.mark.unit
def test_get_detail_none_when_fetch_fails() -> None:
    ch = JobPlanetChannel()
    with patch.object(ch, "_fetch_html", return_value=None):
        assert ch.get_detail("https://www.jobplanet.co.kr/job_postings/999") is None


@pytest.mark.unit
def test_get_detail_none_when_parse_raises() -> None:
    ch = JobPlanetChannel()
    with (
        patch.object(ch, "_fetch_html", return_value="<html>ok</html>"),
        patch.object(ch, "_parse_detail", side_effect=ValueError("bad html")),
    ):
        assert ch.get_detail("https://www.jobplanet.co.kr/job_postings/999") is None


# ---------------------------------------------------------------------------
# URL building
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_search_url_encodes_korean_keyword() -> None:
    ch = JobPlanetChannel()
    url = ch._build_search_url(keyword="블록체인", industry="", page=2)
    assert url.startswith(SEARCH_URL + "?")
    assert "page=2" in url
    # 한글은 %EB%... 형태로 인코딩되어야 함 (한글 원문 그대로 들어가지 않음)
    assert "블록체인" not in url
    assert "query=" in url


@pytest.mark.unit
def test_build_search_url_with_industry() -> None:
    ch = JobPlanetChannel()
    url = ch._build_search_url(keyword="", industry="fintech", page=1)
    assert "industry=fintech" in url
    assert "page=1" in url


# ---------------------------------------------------------------------------
# rating extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "text,expected_contains",
    [
        ("평점 4.2 / 5.0", "/5.0"),
        ("리뷰 평점 3.9점", "3.9"),
        ("만족도 4.5/5", "/5"),
        ("company name only", None),
    ],
)
def test_extract_rating_variants(text: str, expected_contains: str | None) -> None:
    from bs4 import BeautifulSoup

    node = BeautifulSoup(f"<div>{text}</div>", "html.parser").find("div")
    result = JobPlanetChannel._extract_rating(node)
    if expected_contains is None:
        assert result is None
    else:
        assert result is not None
        assert expected_contains in result


@pytest.mark.unit
def test_extract_rating_none_for_none_node() -> None:
    assert JobPlanetChannel._extract_rating(None) is None
