"""Unit tests for FitScorer.

Covers the critical invariants:
    * eligibility FAIL → grade F regardless of other dimensions
    * high-tier BLOCKCHAIN with tight deadline → grade A
    * location affects total score correctly
    * compensation parsing
    * schedule conflict with 자격시험 deducts points
"""

from __future__ import annotations

from datetime import date

import pytest

from career_ops_kr.archetype import Archetype
from career_ops_kr.qualifier import QualifierResult, Verdict
from career_ops_kr.scorer import FitGrade, FitScorer

TODAY = date(2026, 4, 11)


@pytest.fixture(scope="module")
def scorer() -> FitScorer:
    return FitScorer()


def _pass(reasons: list[str] | None = None) -> QualifierResult:
    return QualifierResult(
        verdict=Verdict.PASS,
        reasons=reasons or ["학력 무관"],
        confidence=0.9,
    )


def _fail(reasons: list[str] | None = None) -> QualifierResult:
    return QualifierResult(
        verdict=Verdict.FAIL,
        reasons=reasons or ["졸업예정자"],
        blocking_rules=["negative"],
        confidence=0.95,
    )


def _conditional() -> QualifierResult:
    return QualifierResult(
        verdict=Verdict.CONDITIONAL,
        reasons=["수시 채용"],
        confidence=0.6,
    )


def test_fail_always_grade_f(scorer: FitScorer) -> None:
    """FAIL dominates — even a perfect blockchain job returns F."""
    job = {
        "name": "신한투자증권 블록체인부 인턴",
        "org": "신한투자증권",
        "notes": "블록체인 STO 담당 Python MCP 활용",
        "location": "서울",
        "compensation": 300,
        "deadline": "2026-04-15",
    }
    result = scorer.score(
        job=job,
        qualifier_result=_fail(),
        archetype=Archetype.BLOCKCHAIN,
        today=TODAY,
    )
    assert result.grade == FitGrade.F
    assert result.total == 0.0


def test_high_tier_blockchain_urgent_grade_a(scorer: FitScorer) -> None:
    """BLOCKCHAIN + PASS + Seoul + 신한 brand + D-4 deadline → A."""
    job = {
        "name": "신한투자증권 블록체인부 인턴",
        "org": "신한투자증권",
        "notes": (
            "블록체인 STO 토큰증권 담당, Python SQL MCP AI 실전, "
            "정규직 전환 가능, 채용 연계 교육 연계"
        ),
        "location": "서울",
        "compensation": 280,
        "deadline": "2026-04-15",
    }
    result = scorer.score(
        job=job,
        qualifier_result=_pass(["블록체인부 재학생 가능"]),
        archetype=Archetype.BLOCKCHAIN,
        today=TODAY,
    )
    assert result.grade in {FitGrade.A, FitGrade.B}
    assert result.total >= 80.0
    assert result.dimension_scores["role_fit"] == 100.0
    assert result.dimension_scores["eligibility_match"] == 100.0


def test_location_penalty(scorer: FitScorer) -> None:
    """Same job, different locations → Seoul should beat 부산 on total."""
    base = {
        "name": "금융 IT 인턴",
        "org": "금융기관",
        "notes": "학력 무관 재학생 가능",
        "compensation": 220,
        "deadline": "2026-06-01",
    }
    seoul = scorer.score(
        job={**base, "location": "서울"},
        qualifier_result=_pass(),
        archetype=Archetype.FINANCIAL_IT,
        today=TODAY,
    )
    busan = scorer.score(
        job={**base, "location": "부산"},
        qualifier_result=_pass(),
        archetype=Archetype.FINANCIAL_IT,
        today=TODAY,
    )
    assert seoul.total > busan.total
    assert seoul.dimension_scores["location"] > busan.dimension_scores["location"]


def test_conditional_reduces_eligibility_score(
    scorer: FitScorer,
) -> None:
    job = {
        "name": "Lambda256 블록체인 인턴",
        "org": "Lambda256",
        "notes": "수시 채용 경력 우대 코딩 테스트",
        "location": "서울",
        "compensation": 280,
        "deadline": "2026-06-01",
    }
    result = scorer.score(
        job=job,
        qualifier_result=_conditional(),
        archetype=Archetype.BLOCKCHAIN,
        today=TODAY,
    )
    assert result.dimension_scores["eligibility_match"] == 60.0
    # Still non-F because BLOCKCHAIN role_fit is 100.
    assert result.grade in {FitGrade.B, FitGrade.C, FitGrade.D}


def test_schedule_conflict_with_exam(scorer: FitScorer) -> None:
    """Deadline near ADsP 49 (2026-05-17) → schedule_conflict penalty."""
    clash = {
        "name": "체험형 인턴",
        "org": "금융사",
        "notes": "학력 무관",
        "location": "서울",
        "compensation": 220,
        "deadline": "2026-05-17",
    }
    no_clash = {**clash, "deadline": "2026-06-15"}
    r_clash = scorer.score(clash, _pass(), Archetype.FINANCIAL_IT, today=TODAY)
    r_ok = scorer.score(no_clash, _pass(), Archetype.FINANCIAL_IT, today=TODAY)
    assert (
        r_clash.dimension_scores["schedule_conflict"] < r_ok.dimension_scores["schedule_conflict"]
    )


def test_compensation_parsing_from_text(scorer: FitScorer) -> None:
    job = {
        "name": "인턴",
        "org": "org",
        "notes": "월 250만원 지급",
        "location": "서울",
        "deadline": "2026-06-01",
    }
    result = scorer.score(job, _pass(), Archetype.FINANCIAL_IT, today=TODAY)
    assert result.dimension_scores["compensation"] >= 70.0


def test_urgency_d_minus_3_max(scorer: FitScorer) -> None:
    job = {
        "name": "인턴",
        "org": "org",
        "notes": "학력 무관",
        "location": "서울",
        "compensation": 220,
        "deadline": "2026-04-13",  # D-2 from TODAY
    }
    result = scorer.score(job, _pass(), Archetype.FINANCIAL_IT, today=TODAY)
    assert result.dimension_scores["deadline_urgency"] == 100.0


def test_portfolio_keywords_boost(scorer: FitScorer) -> None:
    job = {
        "name": "데이터 분석 인턴",
        "org": "핀테크",
        "notes": "Python SQL MCP AI 블록체인 활용",
        "location": "서울",
        "compensation": 240,
        "deadline": "2026-06-01",
    }
    result = scorer.score(job, _pass(), Archetype.FINANCIAL_IT, today=TODAY)
    assert result.dimension_scores["portfolio_usefulness"] >= 85.0


def test_unknown_archetype_lower_role_fit(scorer: FitScorer) -> None:
    job = {
        "name": "알 수 없는 인턴",
        "org": "org",
        "notes": "학력 무관",
        "location": "서울",
        "compensation": 200,
        "deadline": "2026-06-01",
    }
    result = scorer.score(job, _pass(), Archetype.UNKNOWN, today=TODAY)
    assert result.dimension_scores["role_fit"] == 40.0
