"""Qualifier engine — rule-based eligibility judgment for Korean jobs.

Exports:
    QualifierEngine: main evaluator
    Verdict: enum (PASS / CONDITIONAL / FAIL)
    QualifierResult: pydantic model with verdict + reasons
"""

from __future__ import annotations

from career_ops_kr.qualifier.engine import (
    QualifierEngine,
    QualifierResult,
    Verdict,
)

__all__ = ["QualifierEngine", "QualifierResult", "Verdict"]
