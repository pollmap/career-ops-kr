"""Tests for the KakaoPay (카카오페이) channel.

Covers:
    * Import smoke + class-level metadata
    * ``check()`` — 200 OK / 4xx / exception
    * ``list_jobs()`` — empty HTML, fixture with 2+ links, dedup, LIST_URL→LANDING_URL
      fallback, archetype inference, fetch failure
    * ``get_detail()`` — success, 404, parse failure
"""

from __future__ import annotations

from typing import Any

import pytest

from career_ops_kr.channels.base import JobRecord
from career_ops_kr.channels.kakao_pay import (
    FINTECH_KEYWORDS,
    LANDING_URL,
    LIST_URL,
    ORG,
    KakaoPayChannel,
    _infer_archetype,
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
        encoding: str = "utf-8",
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.encoding = encoding


# ---------------------------------------------------------------------------
# Fixture HTML
# ---------------------------------------------------------------------------

SAMPLE_LIST_HTML = """
<html><body>
  <ul class="jobs-list">
    <li>
      <a href="/careers/jobs/001">백엔드 개발자 (경력)</a>
    </li>
    <li>
      <a href="/careers/jobs/002">데이터 분석 인턴</a>
    </li>
    <li>
      <a href="/careers/jobs/003">핀테크 리서치 매니저</a>
    </li>
  </ul>
</body></html>
"""

SAMPLE_LIST_HTML_HREF_PATTERN = """
<html><body>
  <a href="/careers/jobs/101">결제 컴플라이언스 담당자</a>
  <a href="/careers/jobs/102">AI 모델 개발자</a>
</body></html>
"""

SAMPLE_DETAIL_HTML = """
<html><head>
  <title>백엔드 개발자 (경력) | 카카오페이 채용</title>
</head><body>
  <h1>백엔드 개발자 (경력)</h1>
  <div class="job-description">
    자격 요건: Java/Kotlin, Spring Boot.
    우대사항: 결제 도메인 경험.
    마감: 2026-05-31
  </div>
</body></html>
"""

SAMPLE_DETAIL_WITH_DEADLINE = """
<html><body>
  <h1>블록체인 리서치 인턴</h1>
  <div class="job-description">채용 마감 2026-06-30</div>
</body></html>
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def channel() -> KakaoPayChannel:
    return KakaoPayChannel()


# ---------------------------------------------------------------------------
# 1. Import smoke + class-level metadata
# ---------------------------------------------------------------------------


def test_import_smoke() -> None:
    """KakaoPayChannel을 임포트할 수 있어야 한다."""
    assert KakaoPayChannel is not None


def test_class_metadata() -> None:
    """클래스 속성이 스펙과 일치해야 한다."""
    assert KakaoPayChannel.name == "kakao_pay"
    assert KakaoPayChannel.tier == 3
    assert KakaoPayChannel.backend == "requests"
    assert KakaoPayChannel.default_rate_per_minute == 6
    assert KakaoPayChannel.default_legitimacy_tier == "T1"


# ---------------------------------------------------------------------------
# 2. check()
# ---------------------------------------------------------------------------


def test_check_200_returns_true(monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel) -> None:
    """200 응답이면 check()는 True여야 한다."""

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text="ok", status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    monkeypatch.setattr(channel._session, "get", _fake_get)
    assert channel.check() is True


def test_check_4xx_returns_false(monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel) -> None:
    """4xx 응답이면 check()는 False여야 한다."""

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=403)

    monkeypatch.setattr(channel._session, "get", _fake_get)
    assert channel.check() is False


def test_check_exception_returns_false(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """네트워크 예외 발생 시 check()는 False여야 한다."""
    import requests as req_module

    def _raise(url: str, **_kwargs: Any) -> _FakeResponse:
        raise req_module.ConnectionError("network down")

    monkeypatch.setattr(channel._session, "get", _raise)
    assert channel.check() is False


# ---------------------------------------------------------------------------
# 3. list_jobs()
# ---------------------------------------------------------------------------


def test_list_jobs_empty_html_returns_empty(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """빈 HTML이면 list_jobs()는 []를 반환해야 한다."""
    fake_resp = _FakeResponse(text="<html><body></body></html>", status_code=200)

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return fake_resp

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    result = channel.list_jobs()
    assert result == []


def test_list_jobs_fixture_yields_records(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """픽스처 HTML에서 2개 이상 JobRecord를 반환해야 한다."""

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    jobs = channel.list_jobs()

    assert len(jobs) >= 2
    for job in jobs:
        assert isinstance(job, JobRecord)
        assert job.source_channel == "kakao_pay"
        assert job.source_tier == 3
        assert job.legitimacy_tier == "T1"
        assert job.org == ORG
        assert job.title


def test_list_jobs_dedup_same_id(monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel) -> None:
    """같은 URL의 공고는 중복 제거되어야 한다."""
    # HTML with identical hrefs
    dup_html = """
    <html><body>
      <ul class="jobs-list">
        <li><a href="/careers/jobs/999">데이터 엔지니어</a></li>
        <li><a href="/careers/jobs/999">데이터 엔지니어</a></li>
      </ul>
    </body></html>
    """

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text=dup_html, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    jobs = channel.list_jobs()
    assert len(jobs) == 1


def test_list_jobs_list_url_tried_first(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """LIST_URL이 먼저 호출되어야 한다."""
    called_urls: list[str] = []

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        called_urls.append(url)
        return _FakeResponse(text=SAMPLE_LIST_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    channel.list_jobs()

    assert called_urls, "requests.get should be called"
    assert called_urls[0] == LIST_URL


def test_list_jobs_landing_url_fallback_when_list_empty(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """LIST_URL이 빈 결과면 LANDING_URL로 재시도해야 한다."""
    call_log: list[str] = []

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        call_log.append(url)
        if url == LIST_URL:
            return _FakeResponse(text="<html><body></body></html>", status_code=200)
        # LANDING_URL returns real content
        return _FakeResponse(text=SAMPLE_LIST_HTML_HREF_PATTERN, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    jobs = channel.list_jobs()

    assert LIST_URL in call_log
    assert LANDING_URL in call_log
    assert len(jobs) >= 1


def test_list_jobs_archetype_intern(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """인턴 포함 제목은 archetype=INTERN이어야 한다."""
    intern_html = """
    <html><body>
      <ul class="jobs-list">
        <li><a href="/careers/jobs/i01">데이터 분석 인턴</a></li>
      </ul>
    </body></html>
    """

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text=intern_html, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    jobs = channel.list_jobs()
    assert any(j.archetype == "INTERN" for j in jobs)


def test_list_jobs_archetype_data(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """데이터 포함 제목은 archetype=DATA이어야 한다 (인턴 아닐 때)."""
    data_html = """
    <html><body>
      <ul class="jobs-list">
        <li><a href="/careers/jobs/d01">데이터 엔지니어 (경력)</a></li>
      </ul>
    </body></html>
    """

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text=data_html, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    jobs = channel.list_jobs()
    assert any(j.archetype == "DATA" for j in jobs)


def test_list_jobs_fetch_failure_returns_empty(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """네트워크 완전 실패 시 list_jobs()는 []를 반환해야 한다."""
    import requests as req_module

    def _raise(url: str, **_kwargs: Any) -> _FakeResponse:
        raise req_module.ConnectionError("offline")

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _raise)
    result = channel.list_jobs()
    assert result == []


# ---------------------------------------------------------------------------
# 4. get_detail()
# ---------------------------------------------------------------------------


def test_get_detail_success(monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel) -> None:
    """픽스처 HTML로 get_detail()이 올바른 JobRecord를 반환해야 한다."""

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text=SAMPLE_DETAIL_HTML, status_code=200)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    url = "https://kakaopay.com/careers/jobs/001"
    detail = channel.get_detail(url)

    assert detail is not None
    assert isinstance(detail, JobRecord)
    assert "백엔드 개발자" in detail.title
    assert detail.org == ORG
    assert detail.source_channel == "kakao_pay"
    assert detail.source_tier == 3
    assert detail.legitimacy_tier == "T1"
    assert detail.raw_html is not None
    assert detail.description


def test_get_detail_404_returns_none(
    monkeypatch: pytest.MonkeyPatch, channel: KakaoPayChannel
) -> None:
    """404 응답이면 get_detail()은 None을 반환해야 한다."""

    def _fake_get(url: str, **_kwargs: Any) -> _FakeResponse:
        return _FakeResponse(text="", status_code=404)

    monkeypatch.setattr("career_ops_kr.channels.kakao_pay.requests.get", _fake_get)
    result = channel.get_detail("https://kakaopay.com/careers/jobs/notfound")
    assert result is None


def test_get_detail_empty_url_returns_none(channel: KakaoPayChannel) -> None:
    """빈 URL이면 get_detail()은 None을 반환해야 한다 (네트워크 없이)."""
    assert channel.get_detail("") is None


# ---------------------------------------------------------------------------
# 5. _infer_archetype (unit tests for the pure helper)
# ---------------------------------------------------------------------------


def test_infer_archetype_intern() -> None:
    assert _infer_archetype("블록체인 리서치 인턴") == "INTERN"
    assert _infer_archetype("Data Intern 2026") == "INTERN"


def test_infer_archetype_data() -> None:
    assert _infer_archetype("데이터 엔지니어 (경력)") == "DATA"
    assert _infer_archetype("Data Scientist") == "DATA"


def test_infer_archetype_engineer() -> None:
    assert _infer_archetype("백엔드 개발자") == "ENGINEER"
    assert _infer_archetype("Frontend Engineer") == "ENGINEER"


def test_infer_archetype_research() -> None:
    assert _infer_archetype("핀테크 리서치 매니저") == "RESEARCH"
    assert _infer_archetype("금융 분석가") == "RESEARCH"


def test_infer_archetype_general() -> None:
    assert _infer_archetype("마케터 (브랜드)") == "GENERAL"
    assert _infer_archetype("법무 담당") == "GENERAL"


# ---------------------------------------------------------------------------
# 6. Module-level constants
# ---------------------------------------------------------------------------


def test_fintech_keywords_non_empty() -> None:
    """FINTECH_KEYWORDS는 비어있지 않아야 한다."""
    assert len(FINTECH_KEYWORDS) > 0
    assert "결제" in FINTECH_KEYWORDS
    assert "데이터" in FINTECH_KEYWORDS
