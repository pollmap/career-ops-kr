"""Tests for ai/client.py — Ollama/OpenRouter auto-detection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_client_import():
    """ai.client imports cleanly."""
    from career_ops_kr.ai.client import get_client, DEFAULT_MODEL
    assert DEFAULT_MODEL is not None
    assert isinstance(DEFAULT_MODEL, str)


def test_ollama_detection_returns_true_when_running():
    """_ollama_available() returns True when server responds 200."""
    from career_ops_kr.ai.client import _ollama_available

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert _ollama_available() is True


def test_ollama_detection_returns_false_on_error():
    """_ollama_available() returns False when server is down."""
    from career_ops_kr.ai.client import _ollama_available

    with patch("urllib.request.urlopen", side_effect=Exception("refused")):
        assert _ollama_available() is False


def test_get_client_ollama_path():
    """get_client() returns Ollama client when _USE_OLLAMA is True."""
    import career_ops_kr.ai.client as mod

    original = mod._USE_OLLAMA
    try:
        mod._USE_OLLAMA = True
        client = mod.get_client()
        assert "11434" in str(client.base_url)
    finally:
        mod._USE_OLLAMA = original


def test_get_client_openrouter_path():
    """get_client() returns OpenRouter client with API key."""
    import career_ops_kr.ai.client as mod

    original = mod._USE_OLLAMA
    try:
        mod._USE_OLLAMA = False
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-or-test123"}):
            client = mod.get_client()
            assert "openrouter" in str(client.base_url)
    finally:
        mod._USE_OLLAMA = original


def test_get_client_raises_without_backend():
    """get_client() raises ValueError when no backend available."""
    import career_ops_kr.ai.client as mod

    original = mod._USE_OLLAMA
    try:
        mod._USE_OLLAMA = False
        with patch.dict("os.environ", {}, clear=True):
            # Remove OPENROUTER_API_KEY
            import os
            key = os.environ.pop("OPENROUTER_API_KEY", None)
            try:
                with pytest.raises(ValueError, match="LLM 백엔드"):
                    mod.get_client()
            finally:
                if key:
                    os.environ["OPENROUTER_API_KEY"] = key
    finally:
        mod._USE_OLLAMA = original
