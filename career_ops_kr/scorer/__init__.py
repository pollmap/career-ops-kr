"""Fit scorer — A~F grading for Korean job postings (10-dimensional).

Exports:
    FitScorer: main scorer
    FitGrade: enum (A / B / C / D / F)
    ScoreBreakdown: pydantic result with per-dimension scores
"""

from __future__ import annotations

from career_ops_kr.scorer.fit_score import FitGrade, FitScorer, ScoreBreakdown

__all__ = ["FitGrade", "FitScorer", "ScoreBreakdown"]
