from __future__ import annotations

from app.config import Settings
from evaluation.ragas_evaluator import RagasEvaluator


def test_unconfigured_ragas_returns_null_scores_without_fabrication() -> None:
    settings = Settings(ragas_evaluator_model=None)
    outcome = RagasEvaluator(settings).evaluate_response("question", "answer", "reference", ["context"])
    assert outcome.scores == {
        "correctness_score": None,
        "relevance_score": None,
        "groundedness_score": None,
    }
    assert outcome.error
