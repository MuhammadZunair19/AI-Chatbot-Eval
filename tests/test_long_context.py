from __future__ import annotations

import pytest

from app.rag import TfidfRetriever
from evaluation.scorer import score_case
from tests.conftest import ROOT


@pytest.mark.long_context
@pytest.mark.parametrize("test_id", ["LONG-001", "LONG-002"])
def test_long_context_requires_every_source(test_id, case_by_id, perfect_metrics) -> None:
    case = case_by_id[test_id]
    result = {"answer": case["reference_answer"], "source_ids": case["expected_source_ids"]}
    assert score_case(case, result, perfect_metrics).status == "PASS"


@pytest.mark.long_context
@pytest.mark.parametrize("test_id", ["LONG-001", "LONG-002"])
def test_retriever_finds_all_long_context_sources(test_id, case_by_id) -> None:
    case = case_by_id[test_id]
    retriever = TfidfRetriever.from_json(ROOT / "data" / "knowledge_base.json")
    retrieved = {item.id for item in retriever.retrieve(case["prompt"], top_k=3, min_score=0)}
    assert set(case["expected_source_ids"]).issubset(retrieved)

