"""Parser package — raw→JobRecord normalizer + helpers."""

from __future__ import annotations

from career_ops_kr.parser.job_normalizer import JobNormalizer
from career_ops_kr.parser.utils import (
    clean_html,
    extract_eligibility_keywords,
    generate_job_id,
    parse_korean_date,
)

__all__ = [
    "JobNormalizer",
    "clean_html",
    "extract_eligibility_keywords",
    "generate_job_id",
    "parse_korean_date",
]
