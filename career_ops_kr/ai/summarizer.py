"""공고 요약 — JobRecord → 1~3문장 한국어 요약.

네트워크 오류나 모델 에러 발생 시 빈 문자열을 반환합니다.
실패를 숨기지 않고 caller에서 fetch_errors 처리를 유도합니다.
"""

from __future__ import annotations

import logging

from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 채용 공고를 간결하게 요약하는 어시스턴트입니다. "
    "반드시 한국어로, 1~3문장으로만 답하세요. "
    "부연 설명, 인사말, 추가 질문 없이 요약문만 출력하세요."
)

_MAX_DESC_CHARS = 2000  # 설명 텍스트 최대 길이 (토큰 절약)


def _build_prompt(job: JobRecord) -> str:
    parts = [f"제목: {job.title}", f"기관: {job.org}"]
    if job.archetype:
        parts.append(f"분류: {job.archetype}")
    if job.deadline:
        parts.append(f"마감: {job.deadline}")
    if job.location:
        parts.append(f"위치: {job.location}")
    if job.description:
        truncated = job.description[:_MAX_DESC_CHARS]
        parts.append(f"공고 내용:\n{truncated}")
    return "\n".join(parts)


def summarize_job(
    job: JobRecord,
    client: object,
    model: str,
) -> str:
    """JobRecord를 1~3문장으로 요약합니다.

    Args:
        job: 요약할 공고 레코드.
        client: ``openai.OpenAI`` 인스턴스 (OpenRouter base_url 설정).
        model: 사용할 모델 ID (예: "google/gemini-2.0-flash-exp:free").

    Returns:
        한국어 요약 문자열. 실패 시 빈 문자열.
    """
    prompt = _build_prompt(job)
    try:
        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"다음 채용 공고를 요약해주세요:\n\n{prompt}"},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("summarize_job failed for %s: %s", job.id, exc)
        return ""


def summarize_jobs_batch(
    jobs: list[JobRecord],
    client: object,
    model: str,
) -> list[str]:
    """여러 공고를 순차적으로 요약합니다.

    Returns:
        jobs와 동일한 순서의 요약 문자열 리스트.
        실패한 항목은 빈 문자열.
    """
    return [summarize_job(job, client, model) for job in jobs]
