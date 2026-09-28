from __future__ import annotations

import pytest

from app.rag import TfidfRetriever, load_knowledge_base
from tests.conftest import ROOT


@pytest.fixture(scope="module")
def retriever() -> TfidfRetriever:
    return TfidfRetriever.from_json(ROOT / "data" / "knowledge_base.json")


def test_knowledge_base_loads_exactly_fifteen_documents() -> None:
    documents = load_knowledge_base(ROOT / "data" / "knowledge_base.json")
    assert len(documents) == 15
    assert len({document["id"] for document in documents}) == 15


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("free trial duration", "KB001"),
        ("Business upload size", "KB006"),
        ("API rate limit", "KB012"),
        ("delete workspace owner", "KB014"),
        ("export data", "KB009"),
    ],
)
def test_expected_source_is_ranked_first(retriever: TfidfRetriever, query: str, expected: str) -> None:
    results = retriever.retrieve(query, top_k=3, min_score=0)
    assert results[0].id == expected
    assert 0 <= results[0].similarity_score <= 1


def test_empty_query_returns_no_documents(retriever: TfidfRetriever) -> None:
    assert retriever.retrieve("   ") == []

