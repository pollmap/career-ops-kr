"""지원 이력 패턴 분석 — SQLiteStore 기반, AI 없음.

거절 패턴, 지원 상태 분포, archetype별 성공률 등을 deterministic으로 계산한다.
실데이터 원칙: 목업 데이터 생성 없음. DB가 비어있으면 total_analyzed=0 반환.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path.cwd() / "data"


def analyze(days: int = 30) -> dict[str, Any]:
    """지원 이력 패턴 분석.

    Args:
        days: 분석 기간 (오늘 기준 days일 이내 데이터).

    Returns:
        {
          days: int,
          period: str (YYYY-MM-DD ~ YYYY-MM-DD),
          total_analyzed: int,
          by_status: dict[str, int],
          by_grade: dict[str, int],
          by_archetype: dict[str, int],
          rejection_rate: float (0.0~1.0),
          avg_days_to_deadline: float | None,
          top_orgs: list[str],
          patterns: list[str],
        }
    """
    today = date.today()
    start = today - timedelta(days=days)
    period = f"{start} ~ {today}"

    all_jobs = _load_jobs()

    # days 이내 필터
    recent = _filter_recent(all_jobs, start)
    total = len(recent)

    if total == 0:
        return {
            "days": days,
            "period": period,
            "total_analyzed": 0,
            "by_status": {},
            "by_grade": {},
            "by_archetype": {},
            "rejection_rate": 0.0,
            "avg_days_to_deadline": None,
            "top_orgs": [],
            "patterns": ["데이터 없음: career-ops scan 먼저 실행하세요."],
        }

    by_status = dict(Counter(j.get("status") or "inbox" for j in recent))
    by_grade = dict(Counter(j.get("fit_grade") or "?" for j in recent if j.get("fit_grade")))
    by_archetype = dict(Counter(j.get("archetype") or "?" for j in recent if j.get("archetype")))

    rejected_count = by_status.get("rejected", 0)
    applied_count = by_status.get("applying", 0) + by_status.get("applied", 0)
    rejection_rate = rejected_count / applied_count if applied_count > 0 else 0.0

    avg_days = _calc_avg_days_to_deadline(recent, today)

    top_orgs = _top_orgs(recent, n=5)

    patterns = _generate_pattern_insights(
        total, by_status, by_grade, by_archetype, rejection_rate, avg_days
    )

    return {
        "days": days,
        "period": period,
        "total_analyzed": total,
        "by_status": by_status,
        "by_grade": by_grade,
        "by_archetype": by_archetype,
        "rejection_rate": round(rejection_rate, 3),
        "avg_days_to_deadline": round(avg_days, 1) if avg_days is not None else None,
        "top_orgs": top_orgs,
        "patterns": patterns,
    }


def _load_jobs() -> list[dict[str, Any]]:
    """SQLiteStore에서 전체 공고 로드."""
    try:
        from career_ops_kr.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(_DATA_DIR / "jobs.db")
        return list(store.search(keyword=""))
    except Exception as exc:
        logger.debug("_load_jobs failed: %s", exc)
        return []


def _filter_recent(jobs: list[dict[str, Any]], start: date) -> list[dict[str, Any]]:
    """scanned_at 기준 start 이후 데이터만 필터."""
    result = []
    for j in jobs:
        scanned = j.get("scanned_at")
        if scanned is None:
            result.append(j)
            continue
        try:
            if isinstance(scanned, str):
                scanned_date = datetime.fromisoformat(scanned).date()
            elif isinstance(scanned, datetime):
                scanned_date = scanned.date()
            elif isinstance(scanned, date):
                scanned_date = scanned
            else:
                result.append(j)
                continue
            if scanned_date >= start:
                result.append(j)
        except (ValueError, TypeError):
            result.append(j)
    return result


def _calc_avg_days_to_deadline(
    jobs: list[dict[str, Any]], today: date
) -> float | None:
    """평균 마감까지 남은 일수 계산."""
    diffs = []
    for j in jobs:
        deadline = j.get("deadline")
        if not deadline:
            continue
        try:
            if isinstance(deadline, str):
                dl = date.fromisoformat(str(deadline))
            elif isinstance(deadline, date):
                dl = deadline
            else:
                continue
            diffs.append((dl - today).days)
        except (ValueError, TypeError):
            continue
    return sum(diffs) / len(diffs) if diffs else None


def _top_orgs(jobs: list[dict[str, Any]], n: int = 5) -> list[str]:
    """가장 많이 등장한 기관 top-N."""
    orgs = [j.get("org") or "" for j in jobs if j.get("org")]
    counter = Counter(orgs)
    return [org for org, _ in counter.most_common(n)]


def _generate_pattern_insights(
    total: int,
    by_status: dict[str, int],
    by_grade: dict[str, int],
    by_archetype: dict[str, int],
    rejection_rate: float,
    avg_days: float | None,
) -> list[str]:
    """Deterministic 패턴 인사이트 문장 생성."""
    insights = []

    if total > 0:
        insights.append(f"분석 기간 내 총 {total}건의 공고가 수집되었습니다.")

    inbox = by_status.get("inbox", 0)
    if inbox > 10:
        insights.append(f"inbox 대기 중인 공고가 {inbox}건입니다. pipeline 실행을 권장합니다.")

    a_count = by_grade.get("A", 0)
    b_count = by_grade.get("B", 0)
    if a_count + b_count > 0:
        insights.append(f"A/B 등급 공고 {a_count + b_count}건 — 적극적인 지원을 고려하세요.")

    if rejection_rate > 0.5:
        insights.append(
            f"거절율 {rejection_rate:.0%}. "
            "자격 요건 필터(QualifierEngine) 활용을 늘리세요."
        )

    if avg_days is not None and avg_days < 3:
        insights.append("마감 임박 공고가 많습니다. notify --days 3 으로 알림 설정을 권장합니다.")

    top_arch = max(by_archetype, key=by_archetype.get, default=None)  # type: ignore[arg-type]
    if top_arch:
        insights.append(f"가장 많은 archetype: {top_arch} ({by_archetype[top_arch]}건)")

    if not insights:
        insights.append("분석 패턴을 도출하기에 데이터가 부족합니다.")

    return insights
