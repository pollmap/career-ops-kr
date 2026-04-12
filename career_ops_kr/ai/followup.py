"""AI 후속 이메일 초안 생성.

LLM 실패 시 deterministic 템플릿으로 대체.
실데이터 원칙: 이메일 실제 발송은 절대 없음 (G5 원칙).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 한국 취업 지원 전문가입니다. "
    "지원자 정보와 공고를 바탕으로 후속 이메일 초안을 작성하세요. "
    "150~300자 분량의 한국어 이메일 본문만 출력하세요. (제목/수신자 제외)"
)

_TONE_MAP = {
    "professional": "정중하고 전문적인",
    "friendly": "친근하고 밝은",
    "concise": "간결하고 명확한",
}

_STAGE_CONTEXT = {
    "applied": "서류 지원 후 관심 표현 및 추가 어필",
    "interviewed": "면접 후 감사 인사 및 입사 의지 표현",
    "rejected": "불합격 통보 후 피드백 요청 및 재도전 의지 표현",
}


def generate_followup_email(
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    stage: str,
    tone: str,
    client: object,
    model: str,
) -> str:
    """LLM으로 후속 이메일 초안 생성.

    Args:
        evaluation: tool_score_job() 반환 dict.
        profile: config/profile.yml 내용.
        stage: "applied" / "interviewed" / "rejected".
        tone: "professional" / "friendly" / "concise".
        client: openai.OpenAI 인스턴스.
        model: 모델 ID.

    Returns:
        이메일 본문 문자열. LLM 실패 시 템플릿 반환.
    """
    org = evaluation.get("org") or "담당자"
    title = evaluation.get("title") or "해당 직무"
    name = _get_name(profile)
    tone_desc = _TONE_MAP.get(tone, "정중하고 전문적인")
    stage_context = _STAGE_CONTEXT.get(stage, stage)

    user_prompt = (
        f"[지원자] {name}\n"
        f"[공고] {org} — {title}\n"
        f"[단계] {stage_context}\n"
        f"[톤] {tone_desc}\n\n"
        f"위 정보로 후속 이메일 본문을 작성해주세요."
    )

    try:
        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400,
            temperature=0.4,
        )
        result = response.choices[0].message.content.strip()
        if result:
            return result
    except Exception as exc:
        logger.warning("generate_followup_email LLM failed: %s", exc)

    return _followup_template(evaluation, profile, stage, tone)


def _followup_template(
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    stage: str,
    tone: str,
) -> str:
    """Deterministic 후속 이메일 템플릿 (AI 없음).

    ⚠️ 수동 작성 필요: 구체적 내용은 직접 보완하세요.
    """
    org = evaluation.get("org") or "귀사"
    title = evaluation.get("title") or "해당 직무"
    name = _get_name(profile)

    if stage == "applied":
        body = (
            f"안녕하세요, {org} 채용 담당자님.\n\n"
            f"{title} 직무에 지원한 {name}입니다.\n"
            f"귀사의 [구체적 강점 입력]에 깊이 공감하여 지원하게 되었습니다.\n"
            f"[본인의 관련 경험/역량 1-2줄 입력] ⚠️ 수동 작성 필요\n\n"
            f"검토해 주셔서 감사합니다.\n\n{name} 드림"
        )
    elif stage == "interviewed":
        body = (
            f"안녕하세요, {org} 채용 담당자님.\n\n"
            f"오늘 {title} 면접 기회를 주셔서 진심으로 감사드립니다.\n"
            f"면접을 통해 [인상 깊었던 점 입력] ⚠️ 수동 작성 필요\n"
            f"꼭 함께하고 싶다는 마음이 더욱 강해졌습니다.\n\n{name} 드림"
        )
    else:  # rejected
        body = (
            f"안녕하세요, {org} 채용 담당자님.\n\n"
            f"이번 {title} 채용에 관심 가져주셔서 감사합니다.\n"
            f"혹시 가능하시다면 보완해야 할 부분에 대한 피드백을 주실 수 있을까요?\n"
            f"다음 기회를 위해 꼭 참고하겠습니다. ⚠️ 수동 작성 필요\n\n{name} 드림"
        )
    return body


def _get_name(profile: dict[str, Any]) -> str:
    """profile에서 이름 추출."""
    name = profile.get("name")
    if isinstance(name, dict):
        return name.get("ko", "지원자")
    return str(name) if name else "지원자"
