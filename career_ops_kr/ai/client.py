"""LLM 클라이언트 팩토리 — 3-backend 자동감지.

우선순위 (자동):
    1. FastFlowLM NPU (localhost:52625) — 빠름, 조용, 배터리 절약
    2. Ollama CPU (localhost:11434) — 품질, 무료, 로컬
    3. OpenRouter 클라우드 — API 키 필요, fallback

환경변수:
    LLM_BACKEND         — 강제 선택: "fastflowlm" / "ollama" / "openrouter"
    FASTFLOWLM_HOST     — FastFlowLM 호스트 (기본: http://localhost:52625)
    FASTFLOWLM_MODEL    — FastFlowLM 모델 (기본: qwen3.5:4b)
    OLLAMA_HOST          — Ollama 호스트 (기본: http://localhost:11434)
    OLLAMA_MODEL         — Ollama 모델 (기본: qwen3:14b)
    OPENROUTER_API_KEY   — OpenRouter API 키
    OPENROUTER_MODEL     — OpenRouter 모델 (기본: google/gemini-2.0-flash-exp:free)

동시 실행 가능:
    FastFlowLM(:52625, NPU) + Ollama(:11434, CPU) + llama.cpp(:8080, iGPU)
    → 서로 다른 칩, 충돌 없음
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

_APP_SITE = "https://github.com/pollmap/career-ops-kr"
_APP_TITLE = "career-ops-kr"

# Backend configs
_FASTFLOWLM_HOST = os.environ.get("FASTFLOWLM_HOST", "http://localhost:52625")
_FASTFLOWLM_MODEL = os.environ.get("FASTFLOWLM_MODEL", "qwen3.5:4b")

_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:26b")

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")


def _check_server(host: str) -> bool:
    """Check if an OpenAI-compatible server is running."""
    try:
        import urllib.request
        # Try /v1/models endpoint (OpenAI compatible)
        url = f"{host}/v1/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        pass
    try:
        # Fallback: try /api/tags (Ollama native)
        import urllib.request
        url = f"{host}/api/tags"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _ollama_available() -> bool:
    return _check_server(_OLLAMA_HOST)


def _fastflowlm_available() -> bool:
    return _check_server(_FASTFLOWLM_HOST)


# Resolve backend at import time
_forced_backend: str = os.environ.get("LLM_BACKEND", "").lower()

if _forced_backend == "fastflowlm":
    DEFAULT_MODEL = _FASTFLOWLM_MODEL
    _ACTIVE_BACKEND = "fastflowlm"
elif _forced_backend == "ollama":
    DEFAULT_MODEL = _OLLAMA_MODEL
    _ACTIVE_BACKEND = "ollama"
elif _forced_backend == "openrouter":
    DEFAULT_MODEL = _OPENROUTER_MODEL
    _ACTIVE_BACKEND = "openrouter"
elif _fastflowlm_available():
    DEFAULT_MODEL = _FASTFLOWLM_MODEL
    _ACTIVE_BACKEND = "fastflowlm"
    logger.info("FastFlowLM NPU detected at %s — model: %s", _FASTFLOWLM_HOST, _FASTFLOWLM_MODEL)
elif _ollama_available():
    DEFAULT_MODEL = _OLLAMA_MODEL
    _ACTIVE_BACKEND = "ollama"
    logger.info("Ollama detected at %s — model: %s", _OLLAMA_HOST, _OLLAMA_MODEL)
else:
    DEFAULT_MODEL = _OPENROUTER_MODEL
    _ACTIVE_BACKEND = "openrouter"

# Backwards compat
_USE_OLLAMA = _ACTIVE_BACKEND == "ollama"


def get_backend_info() -> dict[str, str]:
    """현재 활성 백엔드 정보 반환."""
    return {
        "backend": _ACTIVE_BACKEND,
        "model": DEFAULT_MODEL,
        "host": {
            "fastflowlm": _FASTFLOWLM_HOST,
            "ollama": _OLLAMA_HOST,
            "openrouter": _OPENROUTER_BASE_URL,
        }.get(_ACTIVE_BACKEND, "unknown"),
    }


def get_client(api_key: str | None = None, backend: str | None = None) -> OpenAI:
    """LLM 클라이언트 반환. 3-backend 자동감지.

    Args:
        api_key: OpenRouter API 키 (OpenRouter 백엔드만 필요)
        backend: 강제 백엔드 선택 ("fastflowlm"/"ollama"/"openrouter")

    Returns:
        OpenAI-compatible client.
    """
    active = backend or _ACTIVE_BACKEND

    if active == "fastflowlm":
        return OpenAI(
            api_key="fastflowlm",
            base_url=f"{_FASTFLOWLM_HOST}/v1",
        )

    if active == "ollama":
        return OpenAI(
            api_key="ollama",
            base_url=f"{_OLLAMA_HOST}/v1",
        )

    # OpenRouter
    key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ValueError(
            "LLM 백엔드를 찾을 수 없습니다.\n"
            "  옵션 1: FastFlowLM 실행 (flm serve)\n"
            "  옵션 2: Ollama 실행 (ollama serve)\n"
            "  옵션 3: set OPENROUTER_API_KEY=sk-or-..."
        )
    return OpenAI(
        api_key=key,
        base_url=_OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": _APP_SITE,
            "X-Title": _APP_TITLE,
        },
    )


def get_model(backend: str | None = None) -> str:
    """현재 백엔드의 기본 모델 ID 반환."""
    active = backend or _ACTIVE_BACKEND
    return {
        "fastflowlm": _FASTFLOWLM_MODEL,
        "ollama": _OLLAMA_MODEL,
        "openrouter": _OPENROUTER_MODEL,
    }.get(active, DEFAULT_MODEL)
