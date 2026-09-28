"""Optional live RAGAS evaluation using modern single-turn metrics."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass

from app.config import Settings


EMPTY_SCORES: dict[str, float | None] = {
    "correctness_score": None,
    "relevance_score": None,
    "groundedness_score": None,
}


@dataclass(frozen=True)
class EvaluationOutcome:
    scores: dict[str, float | None]
    error: str | None = None


class RagasEvaluator:
    """Run real evaluator calls; failures produce nulls, never invented scores."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.ragas_evaluator_model and self.settings.llm_base_url)

    async def _evaluate_async(
        self, question: str, answer: str, reference_answer: str | None, contexts: list[str]
    ) -> dict[str, float | None]:
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import SingleTurnSample
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import Faithfulness, FactualCorrectness, ResponseRelevancy

        chat = ChatOpenAI(
            model=self.settings.ragas_evaluator_model,
            api_key=self.settings.llm_api_key or "ollama",
            base_url=self.settings.llm_base_url,
            temperature=0,
        )
        evaluator_llm = LangchainLLMWrapper(chat)
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            reference=reference_answer,
            retrieved_contexts=contexts,
        )
        metric_map: dict[str, object] = {
            "correctness_score": FactualCorrectness(llm=evaluator_llm),
            "groundedness_score": Faithfulness(llm=evaluator_llm),
        }
        if self.settings.ragas_embedding_model:
            embeddings = OpenAIEmbeddings(
                model=self.settings.ragas_embedding_model,
                api_key=self.settings.llm_api_key or "ollama",
                base_url=self.settings.llm_base_url,
            )
            metric_map["relevance_score"] = ResponseRelevancy(
                llm=evaluator_llm,
                embeddings=LangchainEmbeddingsWrapper(embeddings),
            )
        scores = dict(EMPTY_SCORES)
        for name, metric in metric_map.items():
            method = getattr(metric, "single_turn_ascore", None) or getattr(metric, "single_turn_score")
            value = method(sample)
            if inspect.isawaitable(value):
                value = await value
            scores[name] = max(0.0, min(1.0, float(value)))
        return scores

    def evaluate_response(
        self, question: str, answer: str, reference_answer: str | None, retrieved_contexts: list[str]
    ) -> EvaluationOutcome:
        if not self.configured:
            return EvaluationOutcome(dict(EMPTY_SCORES), "RAGAS evaluator model is not configured")
        try:
            scores = asyncio.run(
                self._evaluate_async(question, answer, reference_answer, retrieved_contexts)
            )
            return EvaluationOutcome(scores)
        except Exception as exc:  # third-party/provider failures must not abort the suite
            return EvaluationOutcome(dict(EMPTY_SCORES), f"RAGAS evaluation unavailable: {type(exc).__name__}")


def evaluate_response(
    question: str,
    answer: str,
    reference_answer: str | None,
    retrieved_contexts: list[str],
    settings: Settings | None = None,
) -> dict[str, float | None]:
    """Convenience interface requested by the project specification."""

    outcome = RagasEvaluator(settings or Settings.from_env()).evaluate_response(
        question, answer, reference_answer, retrieved_contexts
    )
    return outcome.scores

