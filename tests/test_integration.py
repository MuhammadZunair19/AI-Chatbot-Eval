from __future__ import annotations

import os

import pytest

from app.config import Settings
from app.llm_client import OpenAICompatibleClient


@pytest.mark.integration
def test_live_openai_compatible_provider() -> None:
    if os.getenv("RUN_LIVE_LLM_TESTS") != "1":
        pytest.skip("set RUN_LIVE_LLM_TESTS=1 to call the configured Ollama/OpenAI-compatible provider")
    settings = Settings.from_env()
    result = OpenAICompatibleClient(
        settings.llm_api_key, settings.llm_model, settings.llm_base_url, settings.request_timeout_seconds
    ).complete("Reply using exactly one word.", "Say ready")
    assert result.answer.strip()

