from __future__ import annotations

from app.config import Settings


def test_ollama_defaults_are_valid(monkeypatch) -> None:
    for name in ("LLM_API_KEY", "LLM_MODEL", "LLM_BASE_URL", "TOP_K"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.llm_base_url == "http://localhost:11434/v1"
    assert settings.llm_model
    assert settings.top_k == 3


def test_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MODEL", "qwen2.5:3b")
    monkeypatch.setenv("TOP_K", "5")
    settings = Settings.from_env()
    assert settings.llm_model == "qwen2.5:3b"
    assert settings.top_k == 5

