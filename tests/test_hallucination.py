from __future__ import annotations

import pytest

from evaluation.rules import appropriately_handles_missing_information
from evaluation.scorer import score_case


@pytest.mark.hallucination
@pytest.mark.parametrize("test_id", [f"HALLUCINATION-{index:03}" for index in range(1, 6)])
def test_hallucination_cases_require_uncertainty(test_id, case_by_id, perfect_metrics) -> None:
    case = case_by_id[test_id]
    decision = score_case(case, {"answer": case["reference_answer"], "source_ids": []}, perfect_metrics)
    assert decision.status == "PASS", decision.failure_reason


def test_uncertainty_detection_is_semantic_phrase_based() -> None:
    assert appropriately_handles_missing_information("That detail is not provided in the available context.")
    assert not appropriately_handles_missing_information("The CEO is John Smith.")

