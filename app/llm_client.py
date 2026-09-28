"""OpenAI-compatible chat-completions client, including local Ollama."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


class LLMClientError(RuntimeError):
    """A safe provider error that never embeds response bodies or credentials."""


@dataclass(frozen=True)
class LLMResult:
    answer: str
    model: str | None = None


class LLMProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResult: ...


class OpenAICompatibleClient:
    """Minimal client for OpenAI, compatible gateways, and Ollama's `/v1` API."""

    def __init__(self, api_key: str, model: str, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResult:
        if not self.model or not self.base_url:
            raise LLMClientError("LLM provider is not configured")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            answer = data["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise KeyError("empty content")
            return LLMResult(answer=answer.strip(), model=data.get("model", self.model))
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise LLMClientError("LLM provider is unavailable or timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMClientError(f"LLM provider returned HTTP {exc.response.status_code}") from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMClientError("LLM provider returned an invalid response") from exc

