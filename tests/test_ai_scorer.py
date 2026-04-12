"""Tests for career_ops_kr.ai.scorer — zero network, monkeypatched client."""
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
        "org": "신한투자증권",
        "title": "블록체인부 체험형 인턴",
        "archetype": "BLOCKCHAIN_INTERN",
        "deadline": date(2026, 4, 17),
        "description": "블록체인, STO, 디지털 자산 관련 업무",
        "legitimacy_tier": "T1",
    }
    defaults.update(kwargs)
    return JobRecord(**defaults)


_SAMPLE_PROFILE = {
    "name": {"ko": "이찬희"},
    "university": {"name": "충북대학교"},
    "major": {"field": "경영학", "track": "재무"},
    "target_industries": ["금융", "핀테크", "블록체인"],
    "strengths": ["Python", "데이터 분석", "금융 이해"],
    "status": "휴학",
}


def _make_client(json_content: str, raise_exc: Exception | None = None):
    class _Msg:
        content = json_content

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        def create(self, **_kwargs):
            if raise_exc:
                raise raise_exc
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    return _Client()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_score_job_valid_json():
    """유효한 JSON 응답 → (score, reason) 반환."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": 85, "reason": "블록체인 전공 우대"}')
    score, reason = score_job(_make_job(), _SAMPLE_PROFILE, "요약", client, "test")
    assert score == 85
    assert "블록체인" in reason


def test_score_job_clamp_over_100():
    """score > 100 → 100으로 클램프."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": 150, "reason": "과도한 점수"}')
    score, _ = score_job(_make_job(), _SAMPLE_PROFILE, "", client, "test")
    assert score == 100


def test_score_job_clamp_below_0():
    """score < 0 → 0으로 클램프."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": -10, "reason": "음수 점수"}')
    score, _ = score_job(_make_job(), _SAMPLE_PROFILE, "", client, "test")
    assert score == 0


def test_score_job_parse_failure_returns_zero():
    """JSON 파싱 실패 → (0, error 문자열)."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client("이건 JSON이 아닙니다")
    score, reason = score_job(_make_job(), _SAMPLE_PROFILE, "", client, "test")
    assert score == 0
    assert "parse error" in reason or "error" in reason


def test_score_job_network_error():
    """LLM 예외 → (0, error 문자열) 반환."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client("", raise_exc=RuntimeError("timeout"))
    score, reason = score_job(_make_job(), _SAMPLE_PROFILE, "", client, "test")
    assert score == 0
    assert "error" in reason


def test_score_job_markdown_wrapped_json():
    """마크다운 코드블록으로 감싼 JSON도 파싱."""
    from career_ops_kr.ai.scorer import score_job

    raw = '```json\n{"score": 72, "reason": "마크다운 감쌈"}\n```'
    client = _make_client(raw)
    score, _reason = score_job(_make_job(), _SAMPLE_PROFILE, "", client, "test")
    assert score == 72


def test_score_job_empty_profile():
    """profile dict 비어있어도 에러 없음."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": 50, "reason": "빈 프로필"}')
    score, _reason = score_job(_make_job(), {}, "", client, "test")
    assert score == 50


def test_score_job_no_archetype():
    """archetype=None 공고도 처리."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": 40, "reason": "미분류"}')
    score, _ = score_job(_make_job(archetype=None), _SAMPLE_PROFILE, "", client, "test")
    assert score == 40


def test_score_jobs_batch_length():
    """배치 채점 결과 길이 = 입력 길이."""
    from career_ops_kr.ai.scorer import score_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(4)]
    summaries = ["요약"] * 4
    client = _make_client('{"score": 60, "reason": "배치"}')
    results = score_jobs_batch(jobs, summaries, _SAMPLE_PROFILE, client, "test")
    assert len(results) == 4


def test_score_jobs_batch_all_tuples():
    """배치 결과 모두 (int, str) 튜플."""
    from career_ops_kr.ai.scorer import score_jobs_batch

    jobs = [_make_job(id=f"id{i:016d}", source_url=f"https://ex.com/{i}") for i in range(2)]
    summaries = ["", ""]
    client = _make_client('{"score": 75, "reason": "테스트"}')
    results = score_jobs_batch(jobs, summaries, {}, client, "test")
    for score, reason in results:
        assert isinstance(score, int)
        assert isinstance(reason, str)


def test_score_job_reason_extracted():
    """reason 필드가 정확히 추출된다."""
    from career_ops_kr.ai.scorer import score_job

    client = _make_client('{"score": 80, "reason": "정확한 이유"}')
    _, reason = score_job(_make_job(), {}, "", client, "test")
    assert reason == "정확한 이유"
