"""FastAPI entry point."""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException

from app.chatbot import ChatbotService
from app.config import get_settings
from app.llm_client import LLMClientError, OpenAICompatibleClient
from app.rag import TfidfRetriever
from app.schemas import ChatRequest, ChatResponse, HealthResponse


logger = logging.getLogger(__name__)
app = FastAPI(title="AI Chatbot QA Framework", version="1.0.0")


def build_chatbot() -> ChatbotService:
    settings = get_settings()
    retriever = TfidfRetriever.from_json(settings.knowledge_base_path)
    llm = OpenAICompatibleClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    return ChatbotService(retriever, llm, settings.top_k, settings.retrieval_min_score)


def get_chatbot() -> ChatbotService:
    return build_chatbot()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, chatbot: ChatbotService = Depends(get_chatbot)) -> ChatResponse:
    try:
        result = chatbot.answer(payload.question)
    except LLMClientError as exc:
        logger.warning("LLM request failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatResponse(**result.__dict__)

