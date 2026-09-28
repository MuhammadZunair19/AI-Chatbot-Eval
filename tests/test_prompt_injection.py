from __future__ import annotations

import pytest

from evaluation.rules import contains_forbidden_pattern, exposes_secret
from evaluation.scorer import score_case


@pytest.mark.injection
@pytest.mark.parametrize("test_id", ["INJECTION-001", "INJECTION-002", "INJECTION-003"])
def test_safe_injection_responses_pass(test_id, case_by_id, perfect_metrics) -> None:
    case = case_by_id[test_id]
    result = {"answer": case["reference_answer"], "source_ids": case["expected_source_ids"]}
    decision = score_case(case, result, perfect_metrics)
    assert decision.status == "PASS", decision.failure_reason


def test_forbidden_and_secret_patterns_are_detected() -> None:
    assert contains_forbidden_pattern("Business costs $1 PER MONTH", ["$1 per month"])
    assert exposes_secret("OPENAI_API_KEY=do-not-print-secrets")

