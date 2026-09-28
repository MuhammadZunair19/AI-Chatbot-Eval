"""Live RAGAS evaluation through an OpenAI-compatible Ollama endpoint."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from ragas.embeddings.base import embedding_factory
from ragas.llms import llm_factory
from ragas.metrics.collections import AnswerRelevancy, Faithfulness, FactualCorrectness

from app.config import Settings


EMPTY_SCORES: dict[str, float | None] = {
    "correctness_score": None,
    "relevance_score": None,
    "groundedness_score": None,
}


@dataclass(frozen=True)
class EvaluationOutcome:
    """Semantic scores and a safe diagnostic when any score is unavailable."""

    scores: dict[str, float | None]
    error: str | None = None


class RagasEvaluator:
    """Calculate real RAGAS metrics without inventing fallback values."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(self.settings.ragas_evaluator_model and self.settings.llm_base_url)

    def _build_metrics(self) -> dict[str, Any]:
        """Create modern RAGAS collection metrics backed by Ollama/OpenAI."""

        evaluator_model = self.settings.ragas_evaluator_model
        if not evaluator_model:
            raise ValueError("RAGAS evaluator model is not configured")
        llm_client = AsyncOpenAI(
            api_key=self.settings.llm_api_key or "ollama",
            base_url=self.settings.llm_base_url,
            timeout=self.settings.request_timeout_seconds,
            max_retries=1,
        )
        evaluator_llm = llm_factory(
            evaluator_model,
            provider="openai",
            client=llm_client,
        )
        metrics: dict[str, Any] = {
            "correctness_score": FactualCorrectness(llm=evaluator_llm),
            "groundedness_score": Faithfulness(llm=evaluator_llm),
        }
        if self.settings.ragas_embedding_model:
            evaluator_embeddings = embedding_factory(
                "openai",
                model=self.settings.ragas_embedding_model,
                client=llm_client,
                interface="modern",
            )
            metrics["relevance_score"] = AnswerRelevancy(
                llm=evaluator_llm,
                embeddings=evaluator_embeddings,
            )
        return metrics

    @staticmethod
    def _normalise_score(value: Any) -> float | None:
        """Return a finite score clamped to the report's 0–1 range."""

        number = float(value)
        if not math.isfinite(number):
            return None
        return round(max(0.0, min(1.0, number)), 6)

    def evaluate_response(
        self,
        question: str,
        answer: str,
        reference_answer: str | None,
        retrieved_contexts: list[str],
    ) -> EvaluationOutcome:
        """Run correctness, relevance, and groundedness independently."""

        if not self.configured:
            return EvaluationOutcome(dict(EMPTY_SCORES), "RAGAS evaluator model is not configured")

        try:
            metrics = self._build_metrics()
        except Exception as exc:
            return EvaluationOutcome(
                dict(EMPTY_SCORES),
                f"RAGAS metric setup unavailable: {type(exc).__name__}",
            )

        scores = dict(EMPTY_SCORES)
        errors: list[str] = []
        metric_inputs: dict[str, dict[str, Any]] = {
            "correctness_score": {
                "response": answer,
                "reference": reference_answer,
            },
            "relevance_score": {
                "user_input": question,
                "response": answer,
            },
            "groundedness_score": {
                "user_input": question,
                "response": answer,
                "retrieved_contexts": retrieved_contexts,
            },
        }

        for score_name, inputs in metric_inputs.items():
            metric = metrics.get(score_name)
            if metric is None:
                if score_name == "relevance_score":
                    errors.append("relevance unavailable: embedding model is not configured")
                continue
            if score_name == "correctness_score" and reference_answer is None:
                errors.append("correctness unavailable: reference answer is missing")
                continue
            try:
                result = metric.score(**inputs)
                scores[score_name] = self._normalise_score(result.value)
                if scores[score_name] is None:
                    errors.append(f"{score_name} returned a non-finite value")
            except Exception as exc:  # provider/metric errors must not abort the suite
                label = score_name.removesuffix("_score")
                errors.append(f"{label} unavailable: {type(exc).__name__}")

        return EvaluationOutcome(scores, "; ".join(errors) or None)


def evaluate_response(
    question: str,
    answer: str,
    reference_answer: str | None,
    retrieved_contexts: list[str],
    settings: Settings | None = None,
) -> dict[str, float | None]:
    """Evaluate one chatbot response and return report-ready score fields."""

    outcome = RagasEvaluator(settings or Settings.from_env()).evaluate_response(
        question, answer, reference_answer, retrieved_contexts
    )
    return outcome.scores

