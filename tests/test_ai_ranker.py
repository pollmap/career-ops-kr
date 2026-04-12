"""Tests for career_ops_kr.ai.ranker — pure computation, zero network."""
from __future__ import annotations

from datetime import date

from career_ops_kr.channels.base import JobRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_job(
    job_id: str = "abcd1234efgh5678",
    url: str = "https://example.com/jobs/1",
    title: str = "테스트 공고",
    archetype: str | None = "INTERN",
    deadline: date | None = None,
    legitimacy_tier: str = "T1",
) -> JobRecord:
    return JobRecord(
        id=job_id,
        source_url=url,
        source_channel="test",
        source_tier=1,
        org="테스트 기관",
        title=title,
        archetype=archetype,
        deadline=deadline,
        legitimacy_tier=legitimacy_tier,
    )


_TODAY = date(2026, 4, 12)


# ---------------------------------------------------------------------------
# rank_jobs tests
# ---------------------------------------------------------------------------


def test_rank_jobs_returns_top_n():
    """top_n=3이면 최대 3개 반환."""
    from career_ops_kr.ai.ranker import rank_jobs

    jobs = [_make_job(job_id=f"id{i:016d}", url=f"https://ex.com/{i}") for i in range(10)]
    scores = [(50, "이유") for _ in jobs]
    result = rank_jobs(jobs, scores, today=_TODAY, top_n=3)
    assert len(result) <= 3


def test_rank_jobs_sorted_descending():
    """결과가 total_score 내림차순."""
    from career_ops_kr.ai.ranker import rank_jobs

    jobs = [
        _make_job(job_id="id0000000000000a", url="https://ex.com/a"),
        _make_job(job_id="id0000000000000b", url="https://ex.com/b"),
        _make_job(job_id="id0000000000000c", url="https://ex.com/c"),
    ]
    scores = [(30, "낮음"), (80, "높음"), (55, "중간")]
    result = rank_jobs(jobs, scores, today=_TODAY, top_n=3)
    totals = [r.total_score for r in result]
    assert totals == sorted(totals, reverse=True)


def test_rank_jobs_kda_archetype_bonus():
    """KDA_COHORT archetype이 INTERN보다 높은 보너스."""
    from career_ops_kr.ai.ranker import rank_jobs

    kda = _make_job(
        job_id="kda00000000000001", url="https://ex.com/kda", archetype="KDA_COHORT"
    )
    intern = _make_job(
        job_id="int00000000000001", url="https://ex.com/intern", archetype="INTERN"
    )
    scores = [(50, ""), (50, "")]
    result = rank_jobs([kda, intern], scores, today=_TODAY, top_n=2)
    kda_result = next(r for r in result if r.job.archetype == "KDA_COHORT")
    intern_result = next(r for r in result if r.job.archetype == "INTERN")
    assert kda_result.archetype_bonus > intern_result.archetype_bonus


def test_rank_jobs_urgency_d2():
    """마감 D-2 → 높은 urgency."""
    from career_ops_kr.ai.ranker import rank_jobs

    urgent = _make_job(
        job_id="urg00000000000001",
        url="https://ex.com/urgent",
        deadline=date(2026, 4, 14),  # D-2
    )
    far = _make_job(
        job_id="far00000000000001",
        url="https://ex.com/far",
        deadline=date(2026, 5, 12),  # D+30
    )
    scores = [(50, ""), (50, "")]
    result = rank_jobs([urgent, far], scores, today=_TODAY, top_n=2)
    urgent_r = next(r for r in result if r.job.id == "urg00000000000001")
    far_r = next(r for r in result if r.job.id == "far00000000000001")
    assert urgent_r.urgency_bonus > far_r.urgency_bonus


def test_rank_jobs_expired_penalty():
    """마감 지난 공고 → 음수 urgency."""
    from career_ops_kr.ai.ranker import rank_jobs

    expired = _make_job(
        job_id="exp00000000000001",
        url="https://ex.com/expired",
        deadline=date(2026, 4, 1),  # 11일 전 마감
    )
    scores = [(70, "")]
    result = rank_jobs([expired], scores, today=_TODAY, top_n=1)
    assert result[0].urgency_bonus < 0


def test_rank_jobs_no_deadline():
    """deadline 없어도 에러 없음."""
    from career_ops_kr.ai.ranker import rank_jobs

    job = _make_job(deadline=None)
    result = rank_jobs([job], [(60, "이유")], today=_TODAY, top_n=1)
    assert len(result) == 1
    assert result[0].days_left is None


def test_rank_jobs_total_clamped_0_to_100():
    """total_score 항상 0~100 범위."""
    from career_ops_kr.ai.ranker import rank_jobs

    # fit=100 + archetype=20 + urgency=25 → clamp to 100
    kda = _make_job(
        job_id="clamp000000000001",
        url="https://ex.com/clamp",
        archetype="KDA_COHORT",
        deadline=date(2026, 4, 13),  # D-1
    )
    result = rank_jobs([kda], [(100, "최고")], today=_TODAY, top_n=1)
    assert result[0].total_score <= 100

    # fit=0 + expired → clamp to 0
    expired = _make_job(
        job_id="clamp000000000002",
        url="https://ex.com/clamp2",
        deadline=date(2026, 4, 1),
    )
    result2 = rank_jobs([expired], [(0, "최저")], today=_TODAY, top_n=1)
    assert result2[0].total_score >= 0


def test_rank_jobs_empty_input():
    """빈 리스트 입력 → 빈 리스트 반환."""
    from career_ops_kr.ai.ranker import rank_jobs

    result = rank_jobs([], [], today=_TODAY, top_n=5)
    assert result == []


def test_rank_jobs_fewer_than_top_n():
    """공고 수 < top_n → 있는 것만 반환."""
    from career_ops_kr.ai.ranker import rank_jobs

    jobs = [_make_job(job_id=f"id{i:016d}", url=f"https://ex.com/{i}") for i in range(2)]
    scores = [(50, ""), (60, "")]
    result = rank_jobs(jobs, scores, today=_TODAY, top_n=5)
    assert len(result) == 2


def test_ranked_job_days_left_positive():
    """days_left 계산이 정확하다."""
    from career_ops_kr.ai.ranker import rank_jobs

    job = _make_job(deadline=date(2026, 4, 17))
    result = rank_jobs([job], [(50, "")], today=_TODAY, top_n=1)
    assert result[0].days_left == 5  # 4/12 → 4/17 = 5일


def test_rank_jobs_blockchain_intern_high_bonus():
    """BLOCKCHAIN_INTERN archetype이 GENERAL보다 높은 보너스."""
    from career_ops_kr.ai.ranker import rank_jobs

    bc = _make_job(
        job_id="bc000000000000001", url="https://ex.com/bc", archetype="BLOCKCHAIN_INTERN"
    )
    gen = _make_job(
        job_id="gen00000000000001", url="https://ex.com/gen", archetype="GENERAL"
    )
    scores = [(50, ""), (50, "")]
    result = rank_jobs([bc, gen], scores, today=_TODAY, top_n=2)
    bc_r = next(r for r in result if r.job.archetype == "BLOCKCHAIN_INTERN")
    gen_r = next(r for r in result if r.job.archetype == "GENERAL")
    assert bc_r.archetype_bonus > gen_r.archetype_bonus


def test_rank_jobs_summary_attached():
    """요약 문자열이 RankedJob에 붙는다."""
    from career_ops_kr.ai.ranker import rank_jobs

    job = _make_job()
    result = rank_jobs([job], [(70, "이유")], summaries=["AI 요약 텍스트"], today=_TODAY)
    assert result[0].summary == "AI 요약 텍스트"
