"""OpenRouter API 클라이언트 팩토리.

OpenRouter는 OpenAI 라이브러리와 100% 호환됩니다.
base_url만 바꾸면 동일한 코드로 100+ 모델을 교체 사용할 수 있습니다.

환경변수:
    OPENROUTER_API_KEY  — 필수. sk-or-... 형식.
    OPENROUTER_MODEL    — 선택. 기본값: DEFAULT_MODEL.

무료 모델 예시:
    google/gemini-2.0-flash-exp:free
    meta-llama/llama-3.1-8b-instruct:free

유료 저렴 모델 예시:
    google/gemini-flash-1.5          — $0.075/1M input
    deepseek/deepseek-chat           — $0.14/1M input
    anthropic/claude-haiku-4-5       — $0.25/1M input
"""

from __future__ import annotations

import os

try:
    from openai import OpenAI
except ImportError as exc:
    raise ImportError(
        "openai 패키지가 필요합니다: uv add openai  또는  pip install openai"
    ) from exc

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_APP_SITE = "https://github.com/pollmap/career-ops-kr"
_APP_TITLE = "career-ops-kr"

# 완전 무료 기본 모델 — 프로덕션 품질은 아니지만 career-ops 사용량에 충분
DEFAULT_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "google/gemini-2.0-flash-exp:free",
)


def get_client(api_key: str | None = None) -> OpenAI:
    """OpenRouter API 클라이언트를 반환합니다.

    Args:
        api_key: API 키. None이면 OPENROUTER_API_KEY 환경변수에서 읽습니다.

    Raises:
        ValueError: API 키가 없을 때.
    """
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "OPENROUTER_API_KEY 환경변수를 설정해주세요.\n"
            "  발급: https://openrouter.ai/keys\n"
            "  설정: set OPENROUTER_API_KEY=sk-or-..."
        )
    return OpenAI(
        api_key=key,
        base_url=_OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": _APP_SITE,
            "X-Title": _APP_TITLE,
        },
    )
