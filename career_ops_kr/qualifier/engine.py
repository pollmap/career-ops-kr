"""Rule-based eligibility qualifier for Korean finance/fintech/blockchain jobs.

Decision order:
    1. Hard negatives (졸업자, 졸업예정자, 정보통신 전공 필수, CS 전공 필수)
       → FAIL
    2. Hard positives (학력무관, 전공무관, 재학생/휴학생 가능, 내일배움카드)
       → PASS
    3. Numeric rules (학기수, 학점 cutoff, 나이 범위)
       → FAIL / CONDITIONAL
    4. Contextual fallback → CONDITIONAL (inconclusive)

All file I/O uses encoding='utf-8'. Falls back to hardcoded defaults if
config files are missing so engine is usable during tests.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


class Verdict(str, Enum):
    """Eligibility verdict."""

    PASS = "PASS"
    CONDITIONAL = "CONDITIONAL"
    FAIL = "FAIL"


class QualifierResult(BaseModel):
    """Result of a single job evaluation."""

    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    blocking_rules: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Hardcoded default rules (used if YAML files are missing).
# ---------------------------------------------------------------------------

DEFAULT_NEGATIVE_PATTERNS: list[tuple[str, str]] = [
    # (regex, reason)
    (r"졸업\s*예정자?", "졸업예정자 요건 (사용자는 휴학 중 2학년 수료)"),
    (r"(?<!미)졸업자", "졸업자 요건 (사용자는 미졸업)"),
    (r"4\s*년제\s*대학\s*졸업", "4년제 대학 졸업 요건"),
    (r"학사\s*학위\s*(소지|보유|필수)", "학사 학위 소지자 요건"),
    (r"정보\s*통신\s*(관련)?\s*학과", "정보통신 관련학과 전공 요건"),
    (r"컴퓨터\s*공학\s*(전공|필수)", "컴퓨터공학 전공 필수"),
    (r"전산\s*(전공|관련)", "전산 전공 요건"),
    (r"CS\s*(전공|major)", "CS 전공 요건"),
    (r"이공\s*계열?\s*(전공|필수)", "이공계 전공 필수"),
    (r"경력\s*\d+\s*년\s*이상", "경력직 요건"),
    (r"(석사|박사)\s*(이상|학위)", "대학원 학위 요건"),
    (r"학점\s*[34]\.\d+\s*이상", "학점 3.x 이상 요건"),
    (r"해외\s*출장\s*가능자?\s*필수", "해외 출장 필수"),
    (r"기술\s*보유자\s*한정", "특정 기술 보유자 한정"),
]

DEFAULT_POSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"학력\s*무관", "학력 무관"),
    (r"전공\s*무관", "전공 무관"),
    (r"(재학생|휴학생).{0,10}(가능|지원|환영)", "재학생/휴학생 지원 가능"),
    (r"재학\s*중.{0,10}(가능|지원|환영)", "재학 중 지원 가능"),
    (r"내일\s*배움\s*카드", "내일배움카드 활용 가능"),
    (r"체험형\s*인턴", "체험형 인턴 (일반적으로 학점/전공 무관)"),
    (r"미래\s*내일\s*일\s*경험", "미래내일 일경험 사업 (청년 인턴)"),
    (r"국민\s*내일\s*배움", "국민내일배움 제도"),
    (r"청년\s*인턴", "청년 인턴"),
    (r"대학생\s*서포터즈", "대학생 서포터즈"),
    (r"부트\s*캠프", "부트캠프"),
    (r"KDT\b", "KDT 과정"),
    (r"K-디지털\s*트레이닝", "K-디지털 트레이닝"),
    (r"정기\s*시험", "자격시험 (지원 제약 없음)"),
    (r"자격\s*시험", "자격시험 (지원 제약 없음)"),
    (r"정기\s*모집", "정기 모집 (연령 제한 외 제약 적음)"),
]

DEFAULT_CONDITIONAL_HINTS: list[tuple[str, str]] = [
    (r"수시\s*채용", "수시 채용 (경력 중심일 가능성)"),
    (r"경력\s*우대", "경력 우대 (필수 아님)"),
    (r"우대\s*사항", "우대 사항 존재"),
    (r"코딩\s*테스트", "코딩 테스트 존재 (통과 여부에 따라 결정)"),
    (r"서류\s*전형", "서류 전형 중심"),
]


class QualifierEngine:
    """Rule-based eligibility engine for Korean job postings."""

    def __init__(
        self,
        rules_path: Path | None = None,
        profile_path: Path | None = None,
    ) -> None:
        self.rules_path = rules_path
        self.profile_path = profile_path
        self._negative: list[tuple[re.Pattern[str], str]] = []
        self._positive: list[tuple[re.Pattern[str], str]] = []
        self._conditional: list[tuple[re.Pattern[str], str]] = []
        self._profile: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load(self) -> None:
        """Load rules from YAML or fallback to hardcoded defaults."""
        neg = DEFAULT_NEGATIVE_PATTERNS
        pos = DEFAULT_POSITIVE_PATTERNS
        cond = DEFAULT_CONDITIONAL_HINTS

        if self.rules_path and self.rules_path.exists() and yaml is not None:
            try:
                data = yaml.safe_load(self.rules_path.read_text(encoding="utf-8")) or {}
                neg = [(r["pattern"], r.get("reason", "")) for r in data.get("negative", [])] or neg
                pos = [(r["pattern"], r.get("reason", "")) for r in data.get("positive", [])] or pos
                cond = [
                    (r["pattern"], r.get("reason", "")) for r in data.get("conditional", [])
                ] or cond
            except (OSError, ValueError, KeyError):
                pass  # fall back to defaults silently

        self._negative = [(re.compile(p, re.IGNORECASE | re.UNICODE), reason) for p, reason in neg]
        self._positive = [(re.compile(p, re.IGNORECASE | re.UNICODE), reason) for p, reason in pos]
        self._conditional = [
            (re.compile(p, re.IGNORECASE | re.UNICODE), reason) for p, reason in cond
        ]

        if self.profile_path and self.profile_path.exists() and yaml is not None:
            try:
                self._profile = yaml.safe_load(self.profile_path.read_text(encoding="utf-8")) or {}
            except (OSError, ValueError):
                self._profile = {}

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, job_text: str) -> QualifierResult:
        """Evaluate a single job description text.

        Args:
            job_text: raw description / title / notes concatenated.

        Returns:
            QualifierResult with verdict + reasons.
        """
        if not job_text or not job_text.strip():
            return QualifierResult(
                verdict=Verdict.CONDITIONAL,
                reasons=["빈 입력"],
                blocking_rules=[],
                confidence=0.3,
            )

        text = job_text.strip()

        # 1. Hard negatives → FAIL
        blocking: list[str] = []
        for rx, reason in self._negative:
            if rx.search(text):
                blocking.append(reason)
        if blocking:
            return QualifierResult(
                verdict=Verdict.FAIL,
                reasons=blocking,
                blocking_rules=blocking,
                confidence=0.9,
            )

        # 2. Numeric rules — check FAIL conditions BEFORE positives,
        # because numeric hard fails (e.g. 만 22세 이하) dominate
        # positive markers like "청년 인턴".
        numeric_verdict = self._check_numeric(text)
        if numeric_verdict is not None and numeric_verdict.verdict == Verdict.FAIL:
            return numeric_verdict

        # 3. Hard positives → PASS
        matched_positive: list[str] = []
        for rx, reason in self._positive:
            if rx.search(text):
                matched_positive.append(reason)
        if matched_positive:
            return QualifierResult(
                verdict=Verdict.PASS,
                reasons=matched_positive,
                blocking_rules=[],
                confidence=0.9,
            )

        # 3b. Numeric PASS (if any) only after positives didn't fire.
        if numeric_verdict is not None:
            return numeric_verdict

        # 4. Contextual hints → CONDITIONAL
        hints: list[str] = []
        for rx, reason in self._conditional:
            if rx.search(text):
                hints.append(reason)
        if hints:
            return QualifierResult(
                verdict=Verdict.CONDITIONAL,
                reasons=hints,
                blocking_rules=[],
                confidence=0.6,
            )

        # Default fallback: CONDITIONAL (inconclusive)
        return QualifierResult(
            verdict=Verdict.CONDITIONAL,
            reasons=["명시적 요건 없음 — 실물 공고 확인 필요"],
            blocking_rules=[],
            confidence=0.4,
        )

    def _check_numeric(self, text: str) -> QualifierResult | None:
        """Numeric thresholds: semester count, GPA cutoff, age range."""
        # 학기 수 (사용자 = 4학기 수료). 6학기 이상 요구 → FAIL
        m = re.search(r"(\d)\s*학기\s*이상", text)
        if m:
            required = int(m.group(1))
            if required >= 6:
                return QualifierResult(
                    verdict=Verdict.FAIL,
                    reasons=[f"{required}학기 이상 요건 (사용자 4학기 수료)"],
                    blocking_rules=[f"semester>={required}"],
                    confidence=0.9,
                )
            if required <= 4:
                return QualifierResult(
                    verdict=Verdict.PASS,
                    reasons=[f"{required}학기 이상 — 사용자 4학기 수료 충족"],
                    blocking_rules=[],
                    confidence=0.85,
                )

        # 학점 cutoff
        m = re.search(r"학점\s*(\d\.\d+)\s*이상", text)
        if m:
            cutoff = float(m.group(1))
            gpa = float(((self._profile.get("gpa") or {}).get("value")) or 2.9)
            if gpa + 0.001 < cutoff:
                return QualifierResult(
                    verdict=Verdict.FAIL,
                    reasons=[f"학점 {cutoff} 이상 요건 (사용자 {gpa})"],
                    blocking_rules=[f"gpa>={cutoff}"],
                    confidence=0.95,
                )

        # 나이 범위 (만 19 ~ 34세 등)
        m = re.search(r"만\s*(\d{2})\s*세\s*이하", text)
        if m:
            age_limit = int(m.group(1))
            age = int(((self._profile.get("birth") or {}).get("age")) or 24)
            if age > age_limit:
                return QualifierResult(
                    verdict=Verdict.FAIL,
                    reasons=[f"만 {age_limit}세 이하 (사용자 {age}세)"],
                    blocking_rules=[f"age<={age_limit}"],
                    confidence=0.95,
                )

        return None

    def batch_evaluate(self, jobs: list[dict[str, Any]]) -> list[QualifierResult]:
        """Evaluate a batch of jobs.

        Each dict should contain ``text`` or ``name`` + ``notes`` / ``description``.
        """
        results: list[QualifierResult] = []
        for job in jobs:
            text = job.get("text") or " ".join(
                str(job.get(k, "")) for k in ("name", "description", "notes")
            )
            results.append(self.evaluate(text))
        return results
