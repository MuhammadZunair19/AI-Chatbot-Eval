"""CSV/JSON report output and dynamic summary calculation."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


REPORT_COLUMNS = [
    "test_id", "category", "prompt", "expected_behavior", "reference_answer",
    "actual_response", "correctness_score", "relevance_score", "groundedness_score",
    "latency_ms", "expected_source_ids", "retrieved_source_ids", "retrieval_scores",
    "rule_checks", "pass_fail", "failure_reason", "timestamp",
]


def write_reports(records: list[dict[str, Any]], report_dir: str | Path) -> tuple[Path, Path]:
    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path = directory / "evaluation_report.csv"
    json_path = directory / "evaluation_report.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for record in records:
            row = dict(record)
            for field in ("expected_source_ids", "retrieved_source_ids", "retrieval_scores", "rule_checks"):
                row[field] = json.dumps(row.get(field), ensure_ascii=False)
            writer.writerow({key: row.get(key) for key in REPORT_COLUMNS})
    return csv_path, json_path


def calculate_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"PASS": 0, "FAIL": 0, "SKIPPED": 0}
    categories: dict[str, dict[str, int]] = defaultdict(lambda: dict(counts))
    for record in records:
        status = record["pass_fail"]
        counts[status] += 1
        categories[record["category"]][status] += 1

    def average(field: str) -> float | None:
        values = [float(item[field]) for item in records if item.get(field) is not None]
        return round(mean(values), 3) if values else None

    decided = counts["PASS"] + counts["FAIL"]
    return {
        "total": len(records), **{key.lower(): value for key, value in counts.items()},
        "pass_rate": round(counts["PASS"] / decided * 100, 1) if decided else 0.0,
        "categories": dict(categories),
        "average_correctness": average("correctness_score"),
        "average_relevance": average("relevance_score"),
        "average_groundedness": average("groundedness_score"),
        "average_latency_ms": average("latency_ms"),
    }

