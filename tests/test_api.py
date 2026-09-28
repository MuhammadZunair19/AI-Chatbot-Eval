from __future__ import annotations

from fastapi.testclient import TestClient

from app.chatbot import ChatResult
from app.llm_client import LLMClientError
from app.main import app, get_chatbot


class SuccessfulChatbot:
    def answer(self, question: str) -> ChatResult:
        return ChatResult(
            answer="AcmeCloud offers a 14-day free trial.",
            retrieved_contexts=["Free Trial: AcmeCloud offers a 14-day free trial."],
            source_ids=["KB001"], retrieval_scores=[0.91], latency_ms=12, model="mock-model",
        )


class FailingChatbot:
    def answer(self, question: str) -> ChatResult:
        raise LLMClientError("LLM provider is unavailable or timed out")


def test_health() -> None:
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_chat_schema_with_mocked_llm() -> None:
    app.dependency_overrides[get_chatbot] = lambda: SuccessfulChatbot()
    try:
        response = TestClient(app).post("/chat", json={"question": "How long is the free trial?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["source_ids"] == ["KB001"]
    assert response.json()["model"] == "mock-model"


def test_empty_and_whitespace_chat_inputs_are_422() -> None:
    client = TestClient(app)
    assert client.post("/chat", json={"question": ""}).status_code == 422
    assert client.post("/chat", json={"question": "   "}).status_code == 422


def test_provider_failure_is_sanitized_503() -> None:
    app.dependency_overrides[get_chatbot] = lambda: FailingChatbot()
    try:
        response = TestClient(app).post("/chat", json={"question": "trial?"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["detail"] == "LLM provider is unavailable or timed out"

