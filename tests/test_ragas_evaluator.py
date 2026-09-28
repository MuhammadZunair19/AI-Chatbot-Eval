from __future__ import annotations

from types import SimpleNamespace

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


class FakeMetric:
    def __init__(self, value: float | None = None, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.calls: list[dict] = []

    def score(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(value=self.value)


def test_all_three_ragas_metrics_map_to_report_scores(monkeypatch) -> None:
    evaluator = RagasEvaluator(
        Settings(ragas_evaluator_model="mistral", ragas_embedding_model="nomic-embed-text")
    )
    metrics = {
        "correctness_score": FakeMetric(0.91),
        "relevance_score": FakeMetric(0.82),
        "groundedness_score": FakeMetric(0.97),
    }
    monkeypatch.setattr(evaluator, "_build_metrics", lambda: metrics)

    outcome = evaluator.evaluate_response(
        "How long is the trial?",
        "The trial lasts 14 days.",
        "AcmeCloud offers a 14-day trial.",
        ["AcmeCloud offers a 14-day free trial."],
    )

    assert outcome.scores == {
        "correctness_score": 0.91,
        "relevance_score": 0.82,
        "groundedness_score": 0.97,
    }
    assert outcome.error is None
    assert metrics["correctness_score"].calls[0] == {
        "response": "The trial lasts 14 days.",
        "reference": "AcmeCloud offers a 14-day trial.",
    }
    assert metrics["relevance_score"].calls[0]["user_input"] == "How long is the trial?"
    assert metrics["groundedness_score"].calls[0]["retrieved_contexts"] == [
        "AcmeCloud offers a 14-day free trial."
    ]


def test_metric_failure_preserves_other_real_scores(monkeypatch) -> None:
    evaluator = RagasEvaluator(Settings(ragas_evaluator_model="mistral"))
    monkeypatch.setattr(
        evaluator,
        "_build_metrics",
        lambda: {
            "correctness_score": FakeMetric(1.4),
            "relevance_score": FakeMetric(error=RuntimeError("provider failed")),
            "groundedness_score": FakeMetric(0.75),
        },
    )

    outcome = evaluator.evaluate_response("question", "answer", "reference", ["context"])

    assert outcome.scores == {
        "correctness_score": 1.0,
        "relevance_score": None,
        "groundedness_score": 0.75,
    }
    assert outcome.error == "relevance unavailable: RuntimeError"


def test_ollama_factory_constructs_all_collection_metrics() -> None:
    evaluator = RagasEvaluator(
        Settings(
            ragas_evaluator_model="mistral",
            ragas_embedding_model="nomic-embed-text",
            request_timeout_seconds=1,
        )
    )

    metrics = evaluator._build_metrics()

    assert set(metrics) == {"correctness_score", "relevance_score", "groundedness_score"}
    assert metrics["correctness_score"].__class__.__name__ == "FactualCorrectness"
    assert metrics["relevance_score"].__class__.__name__ == "AnswerRelevancy"
    assert metrics["groundedness_score"].__class__.__name__ == "Faithfulness"
    assert metrics["relevance_score"].embeddings.is_async is True
