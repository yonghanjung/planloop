#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from planloop.benchmark import (  # noqa: E402
    BenchmarkValidationError,
    coverage_status,
    score_results,
    validate_cases_payload,
    validate_results_payload,
)


def load_fixture(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class PlanloopBenchmarkTests(unittest.TestCase):
    def test_cases_fixture_validates(self) -> None:
        payload = load_fixture("benchmarks/cases/planloop-12.json")
        validated = validate_cases_payload(payload)
        self.assertEqual(validated["benchmark_name"], "Planloop-12")
        self.assertEqual(len(validated["tasks"]), 12)
        hard_case = next(task for task in validated["tasks"] if task["id"] == "ops-003")
        self.assertIn("car wash is 50 meters away", hard_case["task"])
        self.assertIn("job interview call in 12 minutes", hard_case["task"])

    def test_results_fixture_validates(self) -> None:
        cases = load_fixture("benchmarks/cases/planloop-12.json")
        results = load_fixture("benchmarks/results/example-results.json")
        validated = validate_results_payload(cases, results)
        self.assertEqual(validated["system_name"], "planloop")
        self.assertEqual(len(validated["results"]), 4)
        hard_case = next(row for row in validated["results"] if row["task_id"] == "ops-003")
        self.assertEqual(hard_case["first_response_mode"], "intake_only")
        self.assertIn("unsafe_assumption", hard_case["failure_tags"])

    def test_score_results_computes_expected_summary(self) -> None:
        cases = load_fixture("benchmarks/cases/planloop-12.json")
        results = load_fixture("benchmarks/results/example-results.json")
        summary = score_results(cases, results)
        self.assertEqual(summary["benchmark_name"], "Planloop-12")
        self.assertEqual(summary["evaluated_count"], 4)
        self.assertEqual(summary["total_case_count"], 12)
        self.assertAlmostEqual(summary["coverage_rate"], 1 / 3, places=4)
        self.assertEqual(summary["coverage_status"], "demo_only")
        self.assertIn("intake_first_rate", summary["metrics"])
        self.assertIn("ambiguous_coding", summary["category_summary"])

    def test_coverage_status_thresholds(self) -> None:
        self.assertEqual(coverage_status(0.25), "demo_only")
        self.assertEqual(coverage_status(0.6), "provisional")
        self.assertEqual(coverage_status(0.9), "comparable")
        self.assertEqual(coverage_status(1.0), "official")

    def test_duplicate_task_ids_are_rejected(self) -> None:
        cases = load_fixture("benchmarks/cases/planloop-12.json")
        cases["tasks"].append(dict(cases["tasks"][0]))
        with self.assertRaises(BenchmarkValidationError):
            validate_cases_payload(cases)

    def test_unknown_result_task_is_rejected(self) -> None:
        cases = load_fixture("benchmarks/cases/planloop-12.json")
        results = load_fixture("benchmarks/results/example-results.json")
        results["results"][0]["task_id"] = "unknown-task"
        with self.assertRaises(BenchmarkValidationError):
            validate_results_payload(cases, results)

    def test_fixture_files_are_json_serializable(self) -> None:
        cases = load_fixture("benchmarks/cases/planloop-12.json")
        results = load_fixture("benchmarks/results/example-results.json")
        with tempfile.TemporaryDirectory(prefix="planloop-benchmark-") as tmp:
            cases_path = Path(tmp) / "cases.json"
            results_path = Path(tmp) / "results.json"
            cases_path.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
            results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertTrue(cases_path.exists())
            self.assertTrue(results_path.exists())


if __name__ == "__main__":
    unittest.main()
