"""AI subpackage — OpenRouter 기반 공고 요약·채점·랭킹.

사용하려면 OPENROUTER_API_KEY 환경변수를 설정해야 합니다.
기본 모델: google/gemini-2.0-flash-exp:free (무료)

Example::

    import os
    os.environ["OPENROUTER_API_KEY"] = "sk-or-..."

    from career_ops_kr.ai.client import get_client, DEFAULT_MODEL
    from career_ops_kr.ai.summarizer import summarize_job
    from career_ops_kr.ai.scorer import score_job
    from career_ops_kr.ai.ranker import rank_jobs
"""

from career_ops_kr.ai.client import DEFAULT_MODEL, get_client
from career_ops_kr.ai.ranker import rank_jobs
from career_ops_kr.ai.scorer import score_job
from career_ops_kr.ai.summarizer import summarize_job

__all__ = [
    "DEFAULT_MODEL",
    "get_client",
    "rank_jobs",
    "score_job",
    "summarize_job",
]
