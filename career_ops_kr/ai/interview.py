"""AI 면접 질문 생성 — STAR 가이드 포함.

LLM 응답 실패 시 archetype별 fallback 템플릿으로 대체.
실데이터 원칙: fallback은 "수동 작성 필요" 명시.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 한국 채용 면접 전문가입니다. "
    "지원자 프로필과 공고를 분석하여 STAR 구조의 면접 질문을 생성하세요. "
    "반드시 JSON 배열만 출력하세요. "
    "형식: [{\"question\": \"질문 내용\", "
    "\"star_guide\": {\"S\": \"상황 예시\", \"T\": \"과제 예시\", "
    "\"A\": \"행동 예시\", \"R\": \"결과 예시\"}}]"
)

_ARCHETYPE_BASE_QUESTIONS: dict[str, list[str]] = {
    "BLOCKCHAIN_INTERN": ["블록체인 기술에 관심 갖게 된 계기", "DeFi/NFT/STO 관련 경험"],
    "FINTECH": ["핀테크 서비스를 사용하며 개선점을 발견한 경험", "데이터 분석 프로젝트"],
    "RESEARCH": ["재무제표를 분석한 경험", "투자 아이디어 도출 과정"],
    "SECURITIES": ["금융 시장에 대한 관심", "리스크와 수익 균형 사고"],
    "PUBLIC": ["공공기관 지원 동기", "팀 협업 경험"],
}

_DEFAULT_QUESTIONS = [
    "이 직무에 지원한 동기",
    "본인의 가장 큰 강점",
    "가장 도전적이었던 경험",
    "실패를 극복한 경험",
    "5년 후 비전",
]


def generate_interview_questions(
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    client: object,
    model: str,
    n: int = 5,
) -> list[dict[str, Any]]:
    """LLM으로 STAR 면접 질문 생성.

    Args:
        evaluation: tool_score_job() 반환 dict.
        profile: config/profile.yml 내용.
        client: openai.OpenAI 인스턴스.
        model: 모델 ID.
        n: 생성할 질문 수.

    Returns:
        [{"question": str, "star_guide": {"S", "T", "A", "R"}}] 리스트.
        LLM 실패 시 fallback 템플릿.
    """
    archetype = evaluation.get("archetype") or "UNKNOWN"
    org = evaluation.get("org") or "해당 기관"
    title = evaluation.get("title") or "해당 직무"

    profile_parts = _build_profile_summary(profile)
    user_prompt = (
        f"[지원자]\n{profile_parts}\n\n"
        f"[공고]\n기관: {org}\n직무: {title}\n분류: {archetype}\n\n"
        f"위 정보를 바탕으로 STAR 구조 면접 질문 {n}개를 JSON 배열로 생성하세요."
    )

    try:
        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1000,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        parsed = _parse_questions(raw, n)
        if parsed:
            return parsed
    except Exception as exc:
        logger.warning("generate_interview_questions LLM failed: %s", exc)

    return _fallback_star_template(evaluation, n)


def _parse_questions(raw: str, n: int) -> list[dict[str, Any]] | None:
    """LLM 응답에서 JSON 배열 추출."""
    # 마크다운 코드블록 제거
    text = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            return data[:n]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _fallback_star_template(
    evaluation: dict[str, Any],
    n: int,
) -> list[dict[str, Any]]:
    """Archetype별 기본 STAR 질문 템플릿 (AI 없음).

    ⚠️ 수동 작성 필요: 구체적 내용은 직접 보완하세요.
    """
    archetype = (evaluation.get("archetype") or "DEFAULT").upper()
    base = _ARCHETYPE_BASE_QUESTIONS.get(archetype, [])
    questions = list(base) + _DEFAULT_QUESTIONS
    questions = questions[:n]

    result = []
    for q in questions:
        result.append(
            {
                "question": q + "에 대해 구체적인 경험을 말씀해주세요.",
                "star_guide": {
                    "S": "(상황) 어떤 맥락이었는지 설명하세요. ⚠️ 수동 작성 필요",
                    "T": "(과제) 당시 달성해야 할 목표나 과제는 무엇이었나요? ⚠️ 수동 작성 필요",
                    "A": "(행동) 구체적으로 어떤 행동을 취했나요? ⚠️ 수동 작성 필요",
                    "R": "(결과) 그 결과는 어떠했나요? 수치/성과로 표현하세요. ⚠️ 수동 작성 필요",
                },
            }
        )
    return result


def _build_profile_summary(profile: dict[str, Any]) -> str:
    """profile dict → 요약 문자열."""
    parts = []
    if profile.get("name"):
        name = profile["name"]
        parts.append(f"이름: {name.get('ko', name) if isinstance(name, dict) else name}")
    if profile.get("university"):
        uni = profile["university"]
        parts.append(f"대학: {uni.get('name', uni) if isinstance(uni, dict) else uni}")
    if profile.get("major"):
        major = profile["major"]
        if isinstance(major, dict):
            parts.append(f"전공: {major.get('field', '')} {major.get('track', '')}")
    if profile.get("strengths"):
        parts.append(f"강점: {', '.join(str(s) for s in profile['strengths'][:4])}")
    return "\n".join(parts) if parts else "(프로필 없음)"
