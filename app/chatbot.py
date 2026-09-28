"""RAG orchestration for AcmeCloud Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.llm_client import LLMProvider
from app.prompts import SYSTEM_PROMPT, build_user_prompt
from app.rag import TfidfRetriever


@dataclass(frozen=True)
class ChatResult:
    answer: str
    retrieved_contexts: list[str]
    source_ids: list[str]
    retrieval_scores: list[float]
    latency_ms: int
    model: str | None = None


class ChatbotService:
    def __init__(self, retriever: TfidfRetriever, llm: LLMProvider, top_k: int = 3, min_score: float = 0.10) -> None:
        self.retriever = retriever
        self.llm = llm
        self.top_k = top_k
        self.min_score = min_score

    def answer(self, question: str) -> ChatResult:
        started = perf_counter()
        documents = self.retriever.retrieve(question, self.top_k, self.min_score)
        contexts = [f"{item.title}: {item.content}" for item in documents]
        result = self.llm.complete(SYSTEM_PROMPT, build_user_prompt(question, contexts))
        latency_ms = round((perf_counter() - started) * 1000)
        return ChatResult(
            answer=result.answer,
            retrieved_contexts=contexts,
            source_ids=[item.id for item in documents],
            retrieval_scores=[item.similarity_score for item in documents],
            latency_ms=latency_ms,
            model=result.model,
        )

