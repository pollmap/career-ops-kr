"""LLM 클라이언트 팩토리 — Ollama(로컬) 우선, OpenRouter fallback.

우선순위:
    1. Ollama (localhost:11434) — 무료, 로컬, 개인정보 안전
    2. OpenRouter — 클라우드, API 키 필요

환경변수:
    OLLAMA_HOST         — Ollama 호스트 (기본: http://localhost:11434)
    OLLAMA_MODEL        — Ollama 모델 (기본: qwen2.5-coder:7b)
    OPENROUTER_API_KEY  — OpenRouter API 키. Ollama 없을 때 사용.
    OPENROUTER_MODEL    — OpenRouter 모델 (기본: google/gemini-2.0-flash-exp:free)
    LLM_BACKEND         — 강제 선택: "ollama" 또는 "openrouter"
"""

from __future__ import annotations

import logging
import os

try:
    from openai import OpenAI
except ImportError as exc:
    raise ImportError(
        "openai 패키지가 필요합니다: uv add openai  또는  pip install openai"
    ) from exc

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_APP_SITE = "https://github.com/pollmap/career-ops-kr"
_APP_TITLE = "career-ops-kr"

# Ollama defaults
_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

# OpenRouter defaults
_OPENROUTER_MODEL = os.environ.get(
    "OPENROUTER_MODEL",
    "google/gemini-2.0-flash-exp:free",
)


def _ollama_available() -> bool:
    """Check if Ollama is running and has models."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{_OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


# Resolve default model + backend at import time
_backend: str = os.environ.get("LLM_BACKEND", "").lower()
if _backend == "ollama":
    DEFAULT_MODEL = _OLLAMA_MODEL
    _USE_OLLAMA = True
elif _backend == "openrouter":
    DEFAULT_MODEL = _OPENROUTER_MODEL
    _USE_OLLAMA = False
elif _ollama_available():
    DEFAULT_MODEL = _OLLAMA_MODEL
    _USE_OLLAMA = True
    logger.info("Ollama detected at %s — using local LLM (%s)", _OLLAMA_HOST, _OLLAMA_MODEL)
else:
    DEFAULT_MODEL = _OPENROUTER_MODEL
    _USE_OLLAMA = False


def get_client(api_key: str | None = None) -> OpenAI:
    """LLM 클라이언트 반환. Ollama 우선, OpenRouter fallback.

    Returns:
        OpenAI-compatible client (Ollama 또는 OpenRouter).
    """
    if _USE_OLLAMA:
        return OpenAI(
            api_key="ollama",  # Ollama doesn't need a real key
            base_url=f"{_OLLAMA_HOST}/v1",
        )

    # OpenRouter fallback
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "LLM 백엔드를 찾을 수 없습니다.\n"
            "  옵션 1: Ollama 실행 (ollama serve)\n"
            "  옵션 2: set OPENROUTER_API_KEY=sk-or-..."
        )
    return OpenAI(
        api_key=key,
        base_url=_OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": _APP_SITE,
            "X-Title": _APP_TITLE,
        },
    )
