from __future__ import annotations

import csv
import json

from evaluation.report_generator import calculate_summary, write_reports


def test_report_generator_writes_parseable_files(tmp_path) -> None:
    record = {
        "test_id": "X", "category": "normal", "prompt": "q", "expected_behavior": "a",
        "reference_answer": "a", "actual_response": "a", "correctness_score": 1.0,
        "relevance_score": 1.0, "groundedness_score": 1.0, "latency_ms": 5,
        "expected_source_ids": ["KB001"], "retrieved_source_ids": ["KB001"],
        "retrieval_scores": [0.9], "rule_checks": {"sources_ok": True},
        "pass_fail": "PASS", "failure_reason": "", "timestamp": "2026-01-01T00:00:00Z",
    }
    csv_path, json_path = write_reports([record], tmp_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["pass_fail"] == "PASS"
    with csv_path.open(encoding="utf-8") as handle:
        assert list(csv.DictReader(handle))[0]["test_id"] == "X"
    assert calculate_summary([record])["pass_rate"] == 100.0

