"""10-dimensional A~F fit scorer for user's Korean job pipeline.

Dimensions (weights sum to 100):

    role_fit              20 — archetype match with 사용자 preferences
    eligibility_match     20 — Qualifier verdict (FAIL → auto-F)
    compensation          10 — 월급/장려금/지원금 금액
    location              10 — 서울/안산/청주 우선, 수도권 2순위
    growth                10 — 교육연계 + 정규직 전환 + 브릿지
    brand                 10 — 대형 금융사/공공기관 브랜드 가치
    portfolio_usefulness  10 — Python/SQL/MCP/블록체인/AI 키워드
    schedule_conflict      5 — 자격시험 일정과 충돌 여부
    deadline_urgency       3 — D-7 이내 가산점
    hitl_discretion        2 — 기본 0, 사용자 수동 부여

Grade cutoffs (inclusive lower bound):
    A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, F < 60.

File I/O uses encoding='utf-8'. Missing YAML → hardcoded defaults.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from career_ops_kr.archetype import Archetype
from career_ops_kr.parser.utils import coerce_to_date
from career_ops_kr.qualifier import QualifierResult, Verdict

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class FitGrade(str, Enum):
    """A~F letter grade."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class ScoreBreakdown(BaseModel):
    """Per-dimension + total score result."""

    dimension_scores: dict[str, float] = Field(default_factory=dict)
    total: float = 0.0
    grade: FitGrade = FitGrade.F
    reasons: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "role_fit": 20,
    "eligibility_match": 20,
    "compensation": 10,
    "location": 10,
    "growth": 10,
    "brand": 10,
    "portfolio_usefulness": 10,
    "schedule_conflict": 5,
    "deadline_urgency": 3,
    "hitl_discretion": 2,
}

# Matches config/scoring_weights.yml defaults. Until this commit the YAML
# grade_cuts was dead config — fit_score hardcoded 90/80/70/60. FitScorer
# now reads YAML grade_cuts and overrides these defaults at load time.
DEFAULT_GRADE_CUTS: dict[str, float] = {
    "A": 85.0,
    "B": 70.0,
    "C": 55.0,
    "D": 40.0,
    "F": 0.0,
}

# 사용자 preference tiers for archetype fit.
ARCHETYPE_PREFERENCE: dict[Archetype, float] = {
    Archetype.BLOCKCHAIN: 100.0,
    Archetype.DIGITAL_ASSET: 90.0,
    Archetype.FINANCIAL_IT: 90.0,
    Archetype.PUBLIC_FINANCE: 85.0,
    Archetype.RESEARCH: 80.0,
    Archetype.FINTECH_PRODUCT: 80.0,
    Archetype.CERTIFICATION: 70.0,
    Archetype.UNKNOWN: 40.0,
}

# 자격시험 일정 (충돌 감지).
DEFAULT_EXAM_DATES: list[date] = [
    date(2026, 5, 17),  # ADsP 49
    date(2026, 5, 23),  # 한국사 78
    date(2026, 5, 31),  # SQLD 61
    date(2026, 7, 12),  # 금투사 24
    date(2026, 8, 23),  # 투운사 46
]

# Location tiers.
LOCATION_TIER: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"서울|안산|청주", re.IGNORECASE), 100.0),
    (re.compile(r"시흥|과천|성남|수원|인천|경기", re.IGNORECASE), 80.0),
    (re.compile(r"부산|대구|대전|광주|울산", re.IGNORECASE), 50.0),
]

# Brand keywords (high-signal company names).
BRAND_KEYWORDS: list[tuple[re.Pattern[str], float]] = [
    (
        re.compile(
            r"한국은행|금융감독원|금감원|금융위|한국거래소|"
            r"예탁결제원|신용보증기금|기술보증기금|주택금융공사|"
            r"예금보험공사|자산관리공사|캠코|신한|KB|국민|하나|우리|"
            r"삼성|미래에셋|NH|한국투자|키움|카카오|토스|업비트",
            re.IGNORECASE,
        ),
        100.0,
    ),
    (
        re.compile(
            r"빗썸|코인원|두나무|Lambda256|Hashed|뱅크샐러드|"
            r"핀다|8percent|페이히어",
            re.IGNORECASE,
        ),
        80.0,
    ),
]

PORTFOLIO_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"Python",
        r"파이썬",
        r"SQL",
        r"데이터 분석",
        r"데이터분석",
        r"MCP",
        r"LLM",
        r"AI",
        r"머신러닝",
        r"블록체인",
        r"Web3",
        r"스마트컨트랙트",
        r"퀀트",
        r"Quant",
        r"리서치",
        r"백테스트",
    )
]

GROWTH_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"정규직 전환",
        r"채용 연계",
        r"채용연계",
        r"교육 연계",
        r"KDA",
        r"디지털 하나로",
        r"부트캠프",
        r"하나금융융합기술원",
        r"brick",
        r"코스",
    )
]


class FitScorer:
    """10-dimensional A~F scorer."""

    def __init__(
        self,
        weights_path: Path | None = None,
        profile_path: Path | None = None,
    ) -> None:
        self.weights_path = weights_path
        self.profile_path = profile_path
        self.weights: dict[str, float] = dict(DEFAULT_WEIGHTS)
        self.grade_cuts: dict[str, float] = dict(DEFAULT_GRADE_CUTS)
        self.exam_dates: list[date] = list(DEFAULT_EXAM_DATES)
        self.profile: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self.weights_path and self.weights_path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(self.weights_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict) and data.get("weights"):
                    for k, v in data["weights"].items():
                        if k in self.weights:
                            self.weights[k] = float(v)
                if isinstance(data, dict) and data.get("exam_dates"):
                    parsed = [coerce_to_date(x) for x in data["exam_dates"]]
                    self.exam_dates = [d for d in parsed if d is not None]
                if isinstance(data, dict) and data.get("grade_cuts"):
                    for k, v in data["grade_cuts"].items():
                        try:
                            self.grade_cuts[str(k)] = float(v)
                        except (TypeError, ValueError):
                            continue
            except (OSError, ValueError, KeyError):
                pass
        if self.profile_path and self.profile_path.exists() and yaml is not None:
            try:
                self.profile = yaml.safe_load(self.profile_path.read_text(encoding="utf-8")) or {}
            except (OSError, ValueError):
                self.profile = {}

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def score(
        self,
        job: dict[str, Any],
        qualifier_result: QualifierResult,
        archetype: Archetype,
        today: date | None = None,
    ) -> ScoreBreakdown:
        """Score a single job.

        Args:
            job: dict-like with keys name, description, notes, location,
                 compensation, deadline, source_url.
            qualifier_result: result from QualifierEngine.
            archetype: predicted archetype.
            today: optional date override for tests.
        """
        today = today or date.today()
        text = self._job_text(job)
        reasons: list[str] = []

        # 2. eligibility — FAIL dominates (auto-F).
        if qualifier_result.verdict == Verdict.FAIL:
            breakdown = dict.fromkeys(self.weights, 0.0)
            breakdown["eligibility_match"] = 0.0
            return ScoreBreakdown(
                dimension_scores=breakdown,
                total=0.0,
                grade=FitGrade.F,
                reasons=[
                    "Eligibility FAIL → 자동 F",
                    *qualifier_result.reasons[:3],
                ],
            )

        scores: dict[str, float] = {}

        # 1. role_fit
        role = ARCHETYPE_PREFERENCE.get(archetype, 40.0)
        scores["role_fit"] = role
        reasons.append(f"role_fit={role:.0f} ({archetype.value})")

        # 2. eligibility_match (PASS -> 100, CONDITIONAL -> 60)
        elig = 100.0 if qualifier_result.verdict == Verdict.PASS else 60.0
        scores["eligibility_match"] = elig
        reasons.append(f"eligibility={elig:.0f} ({qualifier_result.verdict.value})")

        # 3. compensation
        scores["compensation"] = self._score_compensation(job, text)

        # 4. location
        scores["location"] = self._score_location(job, text)

        # 5. growth
        scores["growth"] = self._score_growth(text)

        # 6. brand
        scores["brand"] = self._score_brand(job, text)

        # 7. portfolio usefulness
        scores["portfolio_usefulness"] = self._score_portfolio(text)

        # 8. schedule conflict
        scores["schedule_conflict"] = self._score_schedule(job, today)

        # 9. deadline urgency
        scores["deadline_urgency"] = self._score_urgency(job, today)

        # 10. HITL discretion — default 0; caller may inject later.
        scores["hitl_discretion"] = float(job.get("hitl_bonus", 0.0))

        # Weighted total.
        total = 0.0
        for dim, raw in scores.items():
            w = self.weights.get(dim, 0.0)
            total += (raw * w) / 100.0

        grade = self._grade(total)
        return ScoreBreakdown(
            dimension_scores=scores,
            total=round(total, 2),
            grade=grade,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Dimension helpers
    # ------------------------------------------------------------------
    def _job_text(self, job: dict[str, Any]) -> str:
        parts = [str(job.get(k, "")) for k in ("name", "org", "description", "notes", "location")]
        return " ".join(parts)

    def _score_compensation(self, job: dict[str, Any], text: str) -> float:
        comp_raw = job.get("compensation")
        if isinstance(comp_raw, (int, float)):
            amount = float(comp_raw)
        else:
            m = re.search(r"월\s*(\d{2,4})\s*만", text)
            amount = float(m.group(1)) if m else 0.0
        if amount >= 280:
            return 100.0
        if amount >= 220:
            return 85.0
        if amount >= 180:
            return 70.0
        if amount >= 100:
            return 50.0
        if amount > 0:
            return 30.0
        return 50.0  # unknown — neutral

    def _score_location(self, job: dict[str, Any], text: str) -> float:
        loc = str(job.get("location", ""))
        blob = f"{loc} {text}"
        for rx, pts in LOCATION_TIER:
            if rx.search(blob):
                return pts
        if re.search(r"재택|원격|remote", blob, re.IGNORECASE):
            return 90.0
        return 60.0

    def _score_growth(self, text: str) -> float:
        hits = sum(1 for rx in GROWTH_KEYWORDS if rx.search(text))
        if hits >= 3:
            return 100.0
        if hits == 2:
            return 80.0
        if hits == 1:
            return 60.0
        return 40.0

    def _score_brand(self, job: dict[str, Any], text: str) -> float:
        blob = f"{job.get('org', '')} {text}"
        for rx, pts in BRAND_KEYWORDS:
            if rx.search(blob):
                return pts
        return 50.0

    def _score_portfolio(self, text: str) -> float:
        hits = sum(1 for rx in PORTFOLIO_KEYWORDS if rx.search(text))
        if hits >= 4:
            return 100.0
        if hits == 3:
            return 85.0
        if hits == 2:
            return 70.0
        if hits == 1:
            return 55.0
        return 40.0

    def _score_schedule(self, job: dict[str, Any], today: date) -> float:
        deadline = coerce_to_date(job.get("deadline"))
        if deadline is None:
            return 80.0
        for exam in self.exam_dates:
            if abs((exam - deadline).days) <= 3:
                return 40.0  # conflict
        return 90.0

    def _score_urgency(self, job: dict[str, Any], today: date) -> float:
        deadline = coerce_to_date(job.get("deadline"))
        if deadline is None:
            return 50.0
        delta = (deadline - today).days
        if delta < 0:
            return 0.0
        if delta <= 3:
            return 100.0
        if delta <= 7:
            return 90.0
        if delta <= 14:
            return 75.0
        if delta <= 30:
            return 60.0
        return 50.0

    def _grade(self, total: float) -> FitGrade:
        cuts = self.grade_cuts
        if total >= cuts.get("A", 85.0):
            return FitGrade.A
        if total >= cuts.get("B", 70.0):
            return FitGrade.B
        if total >= cuts.get("C", 55.0):
            return FitGrade.C
        if total >= cuts.get("D", 40.0):
            return FitGrade.D
        # YAML may define an "E" cut but FitGrade enum only has A~F — fold
        # E into F so the single-source-of-truth YAML stays authoritative
        # without enum churn.
        return FitGrade.F
