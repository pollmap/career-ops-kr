"""Tests for career_ops_kr.ai.summarizer — zero network, monkeypatched client."""
from __future__ import annotations

from datetime import date

from career_ops_kr.channels.base import JobRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(**kwargs) -> JobRecord:
    defaults: dict = {
        "id": "abcd1234efgh5678",
        "source_url": "https://example.com/jobs/1",
        "source_channel": "test",
        "source_tier": 1,
        "org": "테스트 기관",
        "title": "블록체인 체험형 인턴",
        "archetype": "BLOCKCHAIN_INTERN",
        "deadline": date(2026, 4, 17),
        "description": "Python, 블록체인 기술 활용 인턴십 모집",
        "legitimacy_tier": "T1",
    }
    defaults.update(kwargs)
    return JobRecord(**defaults)


class _FakeChoice:
    class _Msg:
        content = "블록체인부 체험형 인턴 공고, 마감 4/17, Python 우대."

    message = _Msg()


class _FakeResponse:
    choices = [_FakeChoice()]


class _FakeClient:
    """네트워크 없는 가짜 OpenAI 클라이언트."""

    def __init__(self, response: _FakeResponse | None = None, raise_exc: Exception | None = None):
        self._response = response or _FakeResponse()
        self._raise = raise_exc
        self.chat = _FakeChatNamespace(self)


class _FakeChatNamespace:
    def __init__(self, parent: _FakeClient):
        self._parent = parent
        self.completions = _FakeCompletionsNamespace(parent)


class _FakeCompletionsNamespace:
    def __init__(self, parent: _FakeClient):
        self._parent = parent

    def create(self, **_kwargs):
        if self._parent._raise:
            raise self._parent._raise
        return self._parent._response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_summarize_job_returns_string():
    """정상 응답 → 요약 문자열 반환."""
    from career_ops_kr.ai.summarizer import summarize_job

    job = _make_job()
    client = _FakeClient()
    result = summarize_job(job, client, "test-model")
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_job_content():
    """LLM 응답 텍스트가 그대로 반환된다."""
    from career_ops_kr.ai.summarizer import summarize_job

    job = _make_job()
    client = _FakeClient()
    result = summarize_job(job, client, "test-model")
    assert "블록체인" in result or "인턴" in result  # fixture text 포함


def test_summarize_job_on_error_returns_empty():
    """LLM 예외 → 빈 문자열 반환 (전파 없음)."""
    from career_ops_kr.ai.summarizer import summarize_job

    job = _make_job()
    client = _FakeClient(raise_exc=RuntimeError("network error"))
    result = summarize_job(job, client, "test-model")
    assert result == ""


def test_summarize_job_strips_whitespace():
    """LLM 응답 앞뒤 공백 제거."""
    from career_ops_kr.ai.summarizer import summarize_job

    class _Whitespace:
        class _Msg:
            content = "  요약 문장.  "
        message = _Msg()

    class _WResp:
        choices = [_Whitespace()]

    job = _make_job()
    client = _FakeClient(response=_WResp())
    result = summarize_job(job, client, "test-model")
    assert result == "요약 문장."


def test_summarize_job_no_deadline():
    """deadline=None 공고도 정상 처리."""
    from career_ops_kr.ai.summarizer import summarize_job

    job = _make_job(deadline=None)
    client = _FakeClient()
    result = summarize_job(job, client, "test-model")
    assert isinstance(result, str)


def test_summarize_job_no_description():
    """description 없는 공고도 정상 처리."""
    from career_ops_kr.ai.summarizer import summarize_job

    job = _make_job(description="")
    client = _FakeClient()
    result = summarize_job(job, client, "test-model")
    assert isinstance(result, str)


def test_summarize_jobs_batch_length():
    """배치 요약 결과 길이 = 입력 리스트 길이."""
    from career_ops_kr.ai.summarizer import summarize_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(3)]
    client = _FakeClient()
    results = summarize_jobs_batch(jobs, client, "test-model", request_delay=0)
    assert len(results) == 3


def test_summarize_jobs_batch_all_strings():
    """배치 요약 결과 모두 문자열."""
    from career_ops_kr.ai.summarizer import summarize_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(2)]
    client = _FakeClient()
    results = summarize_jobs_batch(jobs, client, "test-model", request_delay=0)
    assert all(isinstance(r, str) for r in results)


def test_summarize_jobs_batch_partial_failure():
    """배치 중 일부 실패해도 나머지 결과 반환."""
    from career_ops_kr.ai.summarizer import summarize_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(3)]

    call_count = 0

    class _IntermittentClient:
        def __init__(self):
            self.chat = _FakeChatNamespace(self)
            self._raise = None

        def _try_create(self, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("intermittent")
            return _FakeResponse()

    class _FakeChatNamespace2:
        def __init__(self, parent):
            self._parent = parent
            self.completions = _FakeCompletions2(parent)

    class _FakeCompletions2:
        def __init__(self, parent):
            self._parent = parent

        def create(self, **kwargs):
            return self._parent._try_create(**kwargs)

    client = _IntermittentClient()
    client.chat = _FakeChatNamespace2(client)
    results = summarize_jobs_batch(jobs, client, "test-model", request_delay=0)
    assert len(results) == 3
    assert results[1] == ""  # 실패한 것만 빈 문자열


def test_summarize_jobs_batch_on_progress_called():
    """on_progress 콜백이 각 공고 처리 후 호출된다."""
    from career_ops_kr.ai.summarizer import summarize_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(3)]
    client = _FakeClient()
    calls: list[tuple[int, int]] = []
    summarize_jobs_batch(jobs, client, "test-model", request_delay=0, on_progress=lambda d, t: calls.append((d, t)))
    assert calls == [(1, 3), (2, 3), (3, 3)]
