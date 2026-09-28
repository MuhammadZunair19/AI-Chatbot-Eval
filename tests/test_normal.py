from __future__ import annotations

import pytest

from evaluation.scorer import score_case


@pytest.mark.normal
@pytest.mark.parametrize("test_id", [f"NORMAL-{index:03}" for index in range(1, 11)])
def test_normal_case_contract(test_id, case_by_id, perfect_metrics) -> None:
    case = case_by_id[test_id]
    result = {"answer": case["reference_answer"], "source_ids": case["expected_source_ids"], "latency_ms": 10}
    decision = score_case(case, result, perfect_metrics)
    assert decision.status == "PASS", decision.failure_reason

