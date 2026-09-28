from __future__ import annotations

import pytest

from evaluation.scorer import score_case


@pytest.mark.performance
@pytest.mark.parametrize("test_id", ["PERF-001", "PERF-002"])
def test_performance_threshold(test_id, case_by_id) -> None:
    case = case_by_id[test_id]
    result = {
        "answer": case["reference_answer"], "source_ids": case["expected_source_ids"],
        "latency_ms": case["max_latency_ms"],
    }
    assert score_case(case, result).status == "PASS"


def test_latency_over_limit_fails(case_by_id) -> None:
    case = case_by_id["PERF-001"]
    result = {"answer": "answer", "source_ids": ["KB001"], "latency_ms": 5001}
    decision = score_case(case, result)
    assert decision.status == "FAIL"
    assert "exceeded" in decision.failure_reason

