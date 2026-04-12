"""AI 적합도 채점 — profile.yml + 공고 요약 → 0~100 fit score + 이유 1줄.

LLM에게 JSON 응답을 요청하고, 파싱 실패 시 (0, "parse error")를 반환합니다.
실데이터 절대 원칙: 파싱 실패를 추정값으로 대체하지 않습니다.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable

from career_ops_kr.channels.base import JobRecord

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "/no_think\n"
    "당신은 채용 적합도를 평가하는 전문가입니다. "
    "반드시 유효한 JSON 객체 하나만 출력하세요. "
    "마크다운 코드블록, 설명, 추가 텍스트 없이 JSON만 출력하세요. "
    "생각 과정을 출력하지 마세요. JSON만 출력하세요. "
    '형식: {"score": <0~100 정수>, "reason": "<한국어 이유 1줄>"}'
)

_JSON_PATTERN = re.compile(r'\{[^{}]*"score"\s*:\s*\d+[^{}]*\}', re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """LLM 응답에서 JSON 객체를 추출합니다. 잘린 JSON도 복구 시도."""
    if not text:
        return None
    # 직접 파싱 시도
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # 정규식으로 JSON 블록 추출 시도
    match = _JSON_PATTERN.search(text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # 잘린 JSON 복구: score는 있지만 reason이 잘린 경우
    score_match = re.search(r'"score"\s*:\s*(\d+)', text)
    if score_match:
        score_val = int(score_match.group(1))
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)', text)
        reason_val = reason_match.group(1) if reason_match else ""
        return {"score": score_val, "reason": reason_val}
    return None


def _build_user_prompt(job: JobRecord, profile: dict, summary: str) -> str:
    profile_parts = []
    if profile.get("name"):
        name = profile["name"]
        if isinstance(name, dict):
            profile_parts.append(f"이름: {name.get('ko', '')}")
        else:
            profile_parts.append(f"이름: {name}")
    if profile.get("university"):
        uni = profile["university"]
        if isinstance(uni, dict):
            profile_parts.append(f"대학: {uni.get('name', '')}")
    if profile.get("major"):
        major = profile["major"]
        if isinstance(major, dict):
            profile_parts.append(f"전공: {major.get('field', '')} {major.get('track', '')}")
    if profile.get("target_industries"):
        industries = profile["target_industries"]
        profile_parts.append(f"목표 산업: {', '.join(str(i) for i in industries[:5])}")
    if profile.get("strengths"):
        strengths = profile["strengths"]
        profile_parts.append(f"강점: {', '.join(str(s) for s in strengths[:4])}")
    if profile.get("status"):
        profile_parts.append(f"상태: {profile['status']}")
    if profile.get("certifications"):
        certs = profile["certifications"]
        cert_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in certs[:3]]
        profile_parts.append(f"자격증: {', '.join(cert_names)}")

    profile_str = "\n".join(profile_parts) if profile_parts else "(프로필 정보 없음)"

    return (
        f"[지원자 프로필]\n{profile_str}\n\n"
        f"[채용 공고]\n"
        f"제목: {job.title}\n"
        f"기관: {job.org}\n"
        f"분류: {job.archetype or '미분류'}\n"
        f"마감: {job.deadline or '미정'}\n"
        f"요약: {summary or '(요약 없음)'}\n\n"
        "위 프로필과 공고의 적합도를 0~100으로 평가해주세요.\n"
        '{"score": <점수>, "reason": "<이유 1줄>"} 형식 JSON만 출력.'
    )


def score_job(
    job: JobRecord,
    profile: dict,
    summary: str,
    client: object,
    model: str,
) -> tuple[int, str]:
    """공고 1개의 적합도를 채점합니다.

    Args:
        job: 채점할 공고 레코드.
        profile: config/profile.yml 내용 (dict).
        summary: summarizer.summarize_job() 결과.
        client: ``openai.OpenAI`` 인스턴스.
        model: 모델 ID.

    Returns:
        (score: 0~100, reason: 이유 문자열).
        LLM 실패 시 (0, "error: <메시지>").
    """
    user_prompt = _build_user_prompt(job, profile, summary)
    try:
        # Some models (qwen3, deepseek) use thinking mode — disable it for JSON tasks
        extra_kwargs: dict = {}
        model_lower = model.lower()
        if "qwen3" in model_lower or "deepseek" in model_lower:
            extra_kwargs["extra_body"] = {"enable_thinking": False}

        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.1,
            **extra_kwargs,
        )
        choice = response.choices[0]
        raw = (choice.message.content or "").strip()

        # Fallback: some thinking models put content in reasoning_content
        if not raw and hasattr(choice.message, "reasoning_content"):
            raw = (choice.message.reasoning_content or "").strip()

        parsed = _extract_json(raw)
        if parsed is None:
            logger.warning("score_job JSON parse failed for %s: %r", job.id, raw[:200])
            return 0, f"parse error: {raw[:100]}"

        score = int(parsed.get("score", 0))
        score = max(0, min(100, score))  # clamp 0~100
        reason = str(parsed.get("reason", ""))
        return score, reason

    except Exception as exc:
        logger.warning("score_job failed for %s: %s", job.id, exc)
        return 0, f"error: {exc}"


def score_jobs_batch(
    jobs: list[JobRecord],
    summaries: list[str],
    profile: dict,
    client: object,
    model: str,
    *,
    request_delay: float = 0.3,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[tuple[int, str]]:
    """여러 공고를 순차적으로 채점합니다.

    Args:
        jobs: 채점할 공고 리스트.
        summaries: jobs와 동일한 순서의 요약 문자열 리스트.
        profile: config/profile.yml 내용.
        client: ``openai.OpenAI`` 인스턴스.
        model: 모델 ID.
        request_delay: API 호출 간 대기 시간(초). 무료 tier rate limit 방어용.
        on_progress: (done, total) 콜백. 각 공고 처리 후 호출됨.

    Returns:
        jobs와 동일한 순서의 (score, reason) 리스트.
    """
    total = len(jobs)
    results: list[tuple[int, str]] = []
    for i, (job, summary) in enumerate(zip(jobs, summaries, strict=False)):
        results.append(score_job(job, profile, summary, client, model))
        if on_progress is not None:
            on_progress(i + 1, total)
        if request_delay > 0 and i < total - 1:
            time.sleep(request_delay)
    return results
