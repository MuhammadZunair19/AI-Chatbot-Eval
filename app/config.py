"""Environment-backed application configuration."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseModel):
    """Validated runtime settings with Ollama-friendly defaults."""

    llm_api_key: str = "ollama"
    llm_model: str = "llama3.2:3b"
    llm_base_url: str = "http://localhost:11434/v1"
    ragas_evaluator_model: str | None = None
    ragas_embedding_model: str | None = None
    top_k: int = Field(default=3, ge=1, le=15)
    retrieval_min_score: float = Field(default=0.10, ge=0, le=1)
    latency_threshold_ms: int = Field(default=5000, gt=0)
    request_timeout_seconds: float = Field(default=60.0, gt=0)
    knowledge_base_path: Path = PROJECT_ROOT / "data" / "knowledge_base.json"

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables without logging secrets."""

        return cls(
            llm_api_key=os.getenv("LLM_API_KEY", "ollama"),
            llm_model=os.getenv("LLM_MODEL", "llama3.2:3b"),
            llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            ragas_evaluator_model=os.getenv("RAGAS_EVALUATOR_MODEL") or None,
            ragas_embedding_model=os.getenv("RAGAS_EMBEDDING_MODEL") or None,
            top_k=int(os.getenv("TOP_K", "3")),
            retrieval_min_score=float(os.getenv("RETRIEVAL_MIN_SCORE", "0.10")),
            latency_threshold_ms=int(os.getenv("LATENCY_THRESHOLD_MS", "5000")),
            request_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        )

    @property
    def live_llm_configured(self) -> bool:
        """Return whether the configured provider has enough information to run."""

        is_local = "localhost" in self.llm_base_url or "127.0.0.1" in self.llm_base_url
        return bool(self.llm_model and self.llm_base_url and (self.llm_api_key or is_local))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()

