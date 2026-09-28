from __future__ import annotations

import pytest

from evaluation.scorer import score_case


@pytest.mark.edge
@pytest.mark.parametrize("test_id", ["EDGE-001", "EDGE-002"])
def test_invalid_edge_cases_expect_422(test_id, case_by_id) -> None:
    decision = score_case(case_by_id[test_id], {}, http_status=422)
    assert decision.status == "PASS"


@pytest.mark.edge
@pytest.mark.parametrize("test_id", ["EDGE-003", "EDGE-004", "EDGE-005"])
def test_understandable_edge_cases_use_normal_quality_gates(test_id, case_by_id, perfect_metrics) -> None:
    case = case_by_id[test_id]
    result = {"answer": case["reference_answer"], "source_ids": case["expected_source_ids"]}
    assert score_case(case, result, perfect_metrics).status == "PASS"

