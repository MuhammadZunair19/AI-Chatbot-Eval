from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.llm_client import LLMResult


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cases() -> list[dict[str, Any]]:
    with (ROOT / "data" / "test_cases.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def case_by_id(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {case["test_id"]: case for case in cases}


@pytest.fixture
def perfect_metrics() -> dict[str, float]:
    return {"correctness_score": 1.0, "relevance_score": 1.0, "groundedness_score": 1.0}


class StubLLM:
    def __init__(self, answer: str = "A grounded mocked answer.") -> None:
        self.answer = answer
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResult:
        self.calls += 1
        return LLMResult(self.answer, "stub-model")

