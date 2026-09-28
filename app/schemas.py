"""Pydantic request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=False)

    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def question_must_have_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty or whitespace-only")
        return value.strip()


class ChatResponse(BaseModel):
    answer: str
    retrieved_contexts: list[str]
    source_ids: list[str]
    retrieval_scores: list[float]
    latency_ms: int
    model: str | None = None


class HealthResponse(BaseModel):
    status: str

