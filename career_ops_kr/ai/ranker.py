"""전략적 지원 우선순위 랭커 — deadline urgency + fit score + archetype → Top N.

네트워크 없이 순수 계산만 수행합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from career_ops_kr.channels.base import JobRecord

# 찬희 우선순위 archetype 보너스
_ARCHETYPE_BONUS: dict[str, int] = {
    "KDA_COHORT": 20,          # 키움 KDA — 최우선
    "BLOCKCHAIN_INTERN": 18,   # 신한 블록체인 — 최우선
    "INTERN": 10,
    "DATA": 8,
    "ENGINEER": 6,
    "RESEARCH": 6,
    "EXPERIENCE_TYPE": 5,
    "PROJECT_TYPE": 4,
    "ENTRY": 3,
    "GENERAL": 0,
}

# legitimacy_tier 보너스
_LEGITIMACY_BONUS: dict[str, int] = {
    "T1": 5,
    "T2": 3,
    "T3": 1,
    "T4": 0,
    "T5": 0,
}


@dataclass
class RankedJob:
    """랭킹 결과 단위."""

    job: JobRecord
    fit_score: int         # AI 채점 0~100
    fit_reason: str        # AI 이유
    urgency_bonus: int     # 마감 임박 보너스
    archetype_bonus: int   # archetype 보너스
    legitimacy_bonus: int  # legitimacy_tier 보너스
    total_score: int       # fit_score + urgency + archetype + legitimacy (최대 100 클램프)
    summary: str = field(default="")  # AI 요약 (표시용)

    @property
    def days_left(self) -> int | None:
        """오늘 기준 마감까지 남은 일수. deadline 없으면 None."""
        if self.job.deadline is None:
            return None
        today = date.today()
        return (self.job.deadline - today).days


def _urgency_bonus(deadline: date | None, today: date) -> int:
    """마감일 기준 긴급도 보너스를 계산합니다."""
    if deadline is None:
        return 0
    days_left = (deadline - today).days
    if days_left < 0:
        return -20   # 이미 마감
    if days_left <= 2:
        return 25    # D-2 이내: 지금 당장
    if days_left <= 5:
        return 20    # D-5 이내: 이번 주
    if days_left <= 10:
        return 15    # D-10 이내: 다음 주
    if days_left <= 14:
        return 10    # D-14 이내: 이번 달
    return 0


def rank_jobs(
    jobs: list[JobRecord],
    fit_scores: list[tuple[int, str]],
    summaries: list[str] | None = None,
    today: date | None = None,
    top_n: int = 5,
) -> list[RankedJob]:
    """공고 목록을 종합 점수 기준으로 내림차순 정렬합니다.

    Args:
        jobs: 공고 레코드 리스트.
        fit_scores: scorer.score_jobs_batch() 결과 — (score, reason) 리스트.
            jobs와 동일한 순서여야 합니다.
        summaries: summarizer 결과 — 표시용. None이면 빈 문자열.
        today: 기준 날짜 (테스트 주입용). None이면 date.today().
        top_n: 반환할 상위 N개.

    Returns:
        점수 내림차순 RankedJob 리스트 (최대 top_n개).
    """
    _today = today or date.today()
    _summaries = summaries or [""] * len(jobs)

    ranked: list[RankedJob] = []
    for job, (fit, reason), summary in zip(jobs, fit_scores, _summaries, strict=False):
        urgency = _urgency_bonus(job.deadline, _today)
        arch_bonus = _ARCHETYPE_BONUS.get(job.archetype or "", 0)
        leg_bonus = _LEGITIMACY_BONUS.get(job.legitimacy_tier or "T5", 0)
        total = max(0, min(100, fit + urgency + arch_bonus + leg_bonus))

        ranked.append(
            RankedJob(
                job=job,
                fit_score=fit,
                fit_reason=reason,
                urgency_bonus=urgency,
                archetype_bonus=arch_bonus,
                legitimacy_bonus=leg_bonus,
                total_score=total,
                summary=summary,
            )
        )

    ranked.sort(key=lambda r: r.total_score, reverse=True)
    return ranked[:top_n]
