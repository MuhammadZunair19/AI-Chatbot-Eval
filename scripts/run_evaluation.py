"""Run the 30-case live evaluation and write CSV/JSON reports."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.chatbot import ChatbotService  # noqa: E402
from app.config import Settings  # noqa: E402
from app.llm_client import LLMClientError, OpenAICompatibleClient  # noqa: E402
from app.rag import TfidfRetriever  # noqa: E402
from app.schemas import ChatRequest  # noqa: E402
from evaluation.ragas_evaluator import EMPTY_SCORES, RagasEvaluator  # noqa: E402
from evaluation.report_generator import calculate_summary, write_reports  # noqa: E402
from evaluation.scorer import score_case  # noqa: E402


def load_cases() -> list[dict[str, Any]]:
    with (PROJECT_ROOT / "data" / "test_cases.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _base_record(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "test_id": case["test_id"], "category": case["category"], "prompt": case["prompt"],
        "expected_behavior": case["expected_behavior"], "reference_answer": case.get("reference_answer"),
        "actual_response": "", **EMPTY_SCORES, "latency_ms": None,
        "expected_source_ids": case.get("expected_source_ids", []), "retrieved_source_ids": [],
        "retrieval_scores": [], "rule_checks": {}, "pass_fail": "SKIPPED",
        "failure_reason": "", "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def provider_available(settings: Settings) -> tuple[bool, str | None]:
    """Fail fast for a missing local Ollama server instead of timing out per case."""

    is_local = "localhost" in settings.llm_base_url or "127.0.0.1" in settings.llm_base_url
    if not settings.live_llm_configured:
        return False, "Live LLM is not configured."
    if not is_local:
        return True, None
    try:
        response = httpx.get(f"{settings.llm_base_url}/models", timeout=3.0)
        response.raise_for_status()
        return True, None
    except httpx.HTTPError:
        return False, "Local Ollama endpoint is unavailable; start Ollama and pull the configured model."


def run() -> list[dict[str, Any]]:
    settings = Settings.from_env()
    cases = load_cases()
    retriever = TfidfRetriever.from_json(settings.knowledge_base_path)
    client = OpenAICompatibleClient(
        settings.llm_api_key, settings.llm_model, settings.llm_base_url, settings.request_timeout_seconds
    )
    chatbot = ChatbotService(retriever, client, settings.top_k, settings.retrieval_min_score)
    evaluator = RagasEvaluator(settings)
    provider_ready, provider_error = provider_available(settings)
    if not provider_ready:
        print(provider_error)
    records: list[dict[str, Any]] = []

    for case in cases:
        record = _base_record(case)
        expected_status = case.get("expected_http_status", 200)
        if expected_status != 200:
            try:
                ChatRequest(question=case["prompt"])
                http_status = 200
            except ValidationError:
                http_status = 422
            decision = score_case(case, {}, http_status=http_status)
            record.update(rule_checks=decision.rule_checks, pass_fail=decision.status, failure_reason=decision.failure_reason)
            records.append(record)
            continue

        if not provider_ready:
            record["failure_reason"] = provider_error or "Live generation unavailable."
            records.append(record)
            continue

        try:
            ChatRequest(question=case["prompt"])
            response = chatbot.answer(case["prompt"])
        except (LLMClientError, ValidationError) as exc:
            record["failure_reason"] = f"Live generation unavailable: {type(exc).__name__}."
            records.append(record)
            continue

        result = {
            "answer": response.answer,
            "source_ids": response.source_ids,
            "retrieved_contexts": response.retrieved_contexts,
            "retrieval_scores": response.retrieval_scores,
            "latency_ms": response.latency_ms,
        }
        record.update(
            actual_response=response.answer,
            latency_ms=response.latency_ms,
            retrieved_source_ids=response.source_ids,
            retrieval_scores=response.retrieval_scores,
        )
        semantic_required = any(case.get(key) is not None for key in (
            "minimum_correctness", "minimum_relevance", "minimum_groundedness"
        ))
        if semantic_required:
            outcome = evaluator.evaluate_response(
                case["prompt"], response.answer, case.get("reference_answer"), response.retrieved_contexts
            )
            record.update(outcome.scores)
        else:
            outcome = None
        if semantic_required and any(
            outcome is not None
            and outcome.scores.get(name) is None
            and case.get(threshold) is not None
            for name, threshold in (
                ("correctness_score", "minimum_correctness"),
                ("relevance_score", "minimum_relevance"),
                ("groundedness_score", "minimum_groundedness"),
            )
        ):
            record["failure_reason"] = (
                outcome.error if outcome is not None else None
            ) or "Required semantic score unavailable."
            records.append(record)
            continue
        decision = score_case(case, result, outcome.scores if outcome is not None else EMPTY_SCORES)
        record.update(rule_checks=decision.rule_checks, pass_fail=decision.status, failure_reason=decision.failure_reason)
        records.append(record)
    return records


def print_summary(records: list[dict[str, Any]], csv_path: Path, json_path: Path) -> None:
    summary = calculate_summary(records)
    print("=" * 49)
    print("AI CHATBOT QA EVALUATION")
    print("=" * 49)
    print(f"Total Tests: {summary['total']:>13}")
    print(f"Passed:      {summary['pass']:>13}")
    print(f"Failed:      {summary['fail']:>13}")
    print(f"Skipped:     {summary['skipped']:>13}")
    print(f"Pass Rate:   {summary['pass_rate']:>12.1f}%")
    print("\nCATEGORY RESULTS")
    for category, values in summary["categories"].items():
        decided = values["PASS"] + values["FAIL"]
        print(f"{category:20} {values['PASS']} / {decided} ({values['SKIPPED']} skipped)")
    print("\nAVERAGES")
    for label, key in (
        ("Correctness", "average_correctness"), ("Relevance", "average_relevance"),
        ("Groundedness", "average_groundedness"), ("Latency ms", "average_latency_ms"),
    ):
        print(f"{label:20} {summary[key] if summary[key] is not None else 'n/a'}")
    print(f"\nReports written to:\n{csv_path}\n{json_path}\n" + "=" * 49)


if __name__ == "__main__":
    evaluation_records = run()
    csv_report, json_report = write_reports(evaluation_records, PROJECT_ROOT / "reports")
    print_summary(evaluation_records, csv_report, json_report)

