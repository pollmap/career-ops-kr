"""AI 포트폴리오 스프린트 플랜 생성.

LLM 실패 시 archetype별 기본 스프린트 플랜으로 대체.
실데이터 원칙: fallback은 "수동 작성 필요" 명시.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 취업 포트폴리오 코치입니다. "
    "지원자 프로필과 공고를 분석하여 주차별 스프린트 플랜을 생성하세요. "
    "반드시 JSON 배열만 출력하세요. "
    "형식: [{\"week\": 1, \"theme\": \"주제\", "
    "\"tasks\": [\"할 일1\", \"할 일2\"], \"deliverable\": \"산출물\"}]"
)

# Archetype별 기본 스프린트 플랜 (AI 없음)
_ARCHETYPE_SPRINT_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "BLOCKCHAIN_INTERN": [
        {"week": 1, "theme": "Web3 기초", "tasks": ["Ethereum 백서 정독", "MetaMask 설치", "Hardhat 환경 구성"], "deliverable": "개발 환경 세팅 완료"},
        {"week": 2, "theme": "스마트 컨트랙트", "tasks": ["Solidity 기초 문법", "ERC-20 토큰 구현", "테스트넷 배포"], "deliverable": "ERC-20 토큰 스마트 컨트랙트"},
        {"week": 3, "theme": "DeFi 분석", "tasks": ["Uniswap V3 코드 분석", "AMM 원리 정리", "유동성 풀 시뮬레이션"], "deliverable": "DeFi 분석 보고서"},
        {"week": 4, "theme": "STO/RWA 리서치", "tasks": ["국내 STO 규제 조사", "토큰증권 사례 분석", "발표 자료 제작"], "deliverable": "STO 리서치 발표자료"},
    ],
    "FINTECH": [
        {"week": 1, "theme": "핀테크 생태계 이해", "tasks": ["주요 핀테크 서비스 UX 분석", "오픈뱅킹 API 조사", "경쟁사 비교"], "deliverable": "핀테크 생태계 맵"},
        {"week": 2, "theme": "데이터 분석 프로젝트", "tasks": ["공공 금융 데이터 수집", "EDA 분석", "시각화"], "deliverable": "데이터 분석 Jupyter 노트북"},
        {"week": 3, "theme": "API 개발 실습", "tasks": ["REST API 설계", "결제 모의 구현", "API 문서 작성"], "deliverable": "간단한 결제 API"},
        {"week": 4, "theme": "포트폴리오 정리", "tasks": ["GitHub README 작성", "발표 자료 제작", "코드 리뷰"], "deliverable": "GitHub 포트폴리오"},
    ],
    "RESEARCH": [
        {"week": 1, "theme": "재무제표 분석 기초", "tasks": ["DART 전자공시 수집", "연결 재무제표 분석", "주요 지표 계산"], "deliverable": "재무분석 엑셀 시트"},
        {"week": 2, "theme": "퀀트 모델 구현", "tasks": ["Python 팩터 모델 구현", "백테스트 환경 구성", "성과 측정"], "deliverable": "팩터 백테스트 코드"},
        {"week": 3, "theme": "리서치 리포트 작성", "tasks": ["종목 분석 보고서 초안", "밸류에이션 모델", "투자 의견 수립"], "deliverable": "리서치 보고서 초안"},
        {"week": 4, "theme": "발표 준비", "tasks": ["보고서 최종 편집", "발표 연습", "Q&A 예상 문답 준비"], "deliverable": "최종 리서치 보고서"},
    ],
    "SECURITIES": [
        {"week": 1, "theme": "증권 시장 이해", "tasks": ["주요 지수 분석", "섹터별 동향 조사", "KIS API 실습"], "deliverable": "시장 분석 요약"},
        {"week": 2, "theme": "파생상품 학습", "tasks": ["선물/옵션 기초", "헷징 전략 이해", "KOSPI200 옵션 분석"], "deliverable": "파생상품 학습 노트"},
        {"week": 3, "theme": "투자 포트폴리오", "tasks": ["자산 배분 전략 수립", "백테스트 실행", "리스크 분석"], "deliverable": "투자 전략 보고서"},
        {"week": 4, "theme": "면접 준비", "tasks": ["시사 경제 정리", "예상 면접 문답 작성", "포트폴리오 발표 연습"], "deliverable": "면접 준비 자료"},
    ],
}

# 기본 플랜 (archetype 미매칭)
_DEFAULT_SPRINT: list[dict[str, Any]] = [
    {"week": 1, "theme": "직무 이해", "tasks": ["직무 기술서 분석 ⚠️ 수동 작성 필요", "관련 자료 수집", "역량 갭 분석"], "deliverable": "직무 분석 노트"},
    {"week": 2, "theme": "핵심 역량 개발", "tasks": ["관련 강의/도서 학습 ⚠️ 수동 작성 필요", "실습 프로젝트", "결과물 정리"], "deliverable": "학습 결과물"},
    {"week": 3, "theme": "프로젝트 실전", "tasks": ["포트폴리오 프로젝트 시작 ⚠️ 수동 작성 필요", "코드/문서 작성", "동료 리뷰"], "deliverable": "프로젝트 초안"},
    {"week": 4, "theme": "마무리 & 발표", "tasks": ["최종 완성", "GitHub 공개", "발표 자료 제작 ⚠️ 수동 작성 필요"], "deliverable": "최종 포트폴리오"},
]


def generate_sprint_plan(
    evaluation: dict[str, Any],
    profile: dict[str, Any],
    weeks: int,
    client: object,
    model: str,
) -> list[dict[str, Any]]:
    """LLM으로 포트폴리오 스프린트 플랜 생성.

    Args:
        evaluation: tool_score_job() 반환 dict.
        profile: config/profile.yml 내용.
        weeks: 플랜 주차 수.
        client: openai.OpenAI 인스턴스.
        model: 모델 ID.

    Returns:
        [{"week", "theme", "tasks", "deliverable"}] 리스트.
        LLM 실패 시 archetype 기본 플랜 반환.
    """
    archetype = evaluation.get("archetype") or "UNKNOWN"
    org = evaluation.get("org") or "해당 기관"
    title = evaluation.get("title") or "해당 직무"
    strengths = profile.get("strengths") or []
    strengths_str = ", ".join(str(s) for s in strengths[:4])

    user_prompt = (
        f"[지원자 강점] {strengths_str or '(미입력)'}\n"
        f"[공고] {org} — {title} (분류: {archetype})\n"
        f"[플랜 기간] {weeks}주\n\n"
        f"위 공고에 합격하기 위한 {weeks}주 포트폴리오 스프린트 플랜을 JSON 배열로 생성하세요."
    )

    try:
        response = client.chat.completions.create(  # type: ignore[union-attr]
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        parsed = _parse_sprint(raw, weeks)
        if parsed:
            return parsed
    except Exception as exc:
        logger.warning("generate_sprint_plan LLM failed: %s", exc)

    return _get_fallback(archetype, weeks)


def _parse_sprint(raw: str, weeks: int) -> list[dict[str, Any]] | None:
    """LLM 응답에서 JSON 배열 추출."""
    text = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            return data[:weeks]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _get_fallback(archetype: str, weeks: int) -> list[dict[str, Any]]:
    """Archetype별 기본 스프린트 플랜 반환."""
    archetype_upper = archetype.upper() if archetype else "DEFAULT"
    base = _ARCHETYPE_SPRINT_DEFAULTS.get(archetype_upper, _DEFAULT_SPRINT)
    plan = list(base[:weeks])
    # 주차가 부족하면 기본 플랜으로 채우기
    for w in range(len(plan) + 1, weeks + 1):
        plan.append(
            {
                "week": w,
                "theme": f"{w}주차 활동 ⚠️ 수동 작성 필요",
                "tasks": ["학습/실습", "결과물 작성", "정리"],
                "deliverable": f"{w}주차 산출물 ⚠️ 수동 작성 필요",
            }
        )
    return plan
