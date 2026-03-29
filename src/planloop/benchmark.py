#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any


ALLOWED_CATEGORIES = {"ambiguous_coding", "integration_setup", "operational_workflow"}
ALLOWED_FIRST_RESPONSE_MODES = {"intake_only", "mixed", "plan_first"}
ALLOWED_FAILURE_TAGS = {
    "scope_drift",
    "overengineering",
    "weak_verification",
    "unsafe_assumption",
    "not_intake_first",
    "other",
}


class BenchmarkValidationError(RuntimeError):
    pass


def coverage_status(rate: float) -> str:
    if rate < 0.5:
        return "demo_only"
    if rate < 0.8:
        return "provisional"
    if rate < 1.0:
        return "comparable"
    return "official"


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _require_mapping(value: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BenchmarkValidationError(f"{name} must be an object")
    return value


def _require_list(value: Any, *, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise BenchmarkValidationError(f"{name} must be a list")
    return value


def _require_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkValidationError(f"{name} must be a non-empty string")
    return value.strip()


def _require_bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise BenchmarkValidationError(f"{name} must be a boolean")
    return value


def _require_int(value: Any, *, name: str) -> int:
    if not isinstance(value, int):
        raise BenchmarkValidationError(f"{name} must be an integer")
    return value


def validate_cases_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = _require_mapping(payload, name="cases")
    benchmark_name = _require_string(data.get("benchmark_name"), name="benchmark_name")
    version = _require_string(data.get("version"), name="version")
    tasks = _require_list(data.get("tasks"), name="tasks")
    if not tasks:
        raise BenchmarkValidationError("tasks must not be empty")

    seen_ids: set[str] = set()
    validated_tasks: list[dict[str, Any]] = []
    for idx, item in enumerate(tasks):
        task = _require_mapping(item, name=f"tasks[{idx}]")
        task_id = _require_string(task.get("id"), name=f"tasks[{idx}].id")
        if task_id in seen_ids:
            raise BenchmarkValidationError(f"duplicate task id: {task_id}")
        seen_ids.add(task_id)
        category = _require_string(task.get("category"), name=f"tasks[{idx}].category")
        if category not in ALLOWED_CATEGORIES:
            raise BenchmarkValidationError(f"unsupported category for {task_id}: {category}")
        task_text = _require_string(task.get("task"), name=f"tasks[{idx}].task")
        evaluation_focus = _require_list(task.get("evaluation_focus"), name=f"tasks[{idx}].evaluation_focus")
        if not evaluation_focus:
            raise BenchmarkValidationError(f"evaluation_focus must not be empty for {task_id}")
        validated_tasks.append(
            {
                "id": task_id,
                "category": category,
                "task": task_text,
                "evaluation_focus": [_require_string(x, name=f"{task_id}.evaluation_focus item") for x in evaluation_focus],
            }
        )

    return {
        "benchmark_name": benchmark_name,
        "version": version,
        "description": str(data.get("description", "")).strip(),
        "tasks": validated_tasks,
    }


def validate_results_payload(cases_payload: dict[str, Any], results_payload: dict[str, Any]) -> dict[str, Any]:
    cases = validate_cases_payload(cases_payload)
    data = _require_mapping(results_payload, name="results")
    benchmark_name = _require_string(data.get("benchmark_name"), name="benchmark_name")
    if benchmark_name != cases["benchmark_name"]:
        raise BenchmarkValidationError(
            f"results benchmark_name {benchmark_name!r} does not match cases {cases['benchmark_name']!r}"
        )
    version = _require_string(data.get("version"), name="version")
    system_name = _require_string(data.get("system_name"), name="system_name")
    run_label = _require_string(data.get("run_label"), name="run_label")
    results = _require_list(data.get("results"), name="results")

    known_task_ids = {task["id"] for task in cases["tasks"]}
    seen_ids: set[str] = set()
    validated_results: list[dict[str, Any]] = []
    for idx, item in enumerate(results):
        result = _require_mapping(item, name=f"results[{idx}]")
        task_id = _require_string(result.get("task_id"), name=f"results[{idx}].task_id")
        if task_id not in known_task_ids:
            raise BenchmarkValidationError(f"unknown task_id in results: {task_id}")
        if task_id in seen_ids:
            raise BenchmarkValidationError(f"duplicate result for task_id: {task_id}")
        seen_ids.add(task_id)

        first_response_mode = _require_string(
            result.get("first_response_mode"), name=f"results[{idx}].first_response_mode"
        )
        if first_response_mode not in ALLOWED_FIRST_RESPONSE_MODES:
            raise BenchmarkValidationError(f"unsupported first_response_mode for {task_id}: {first_response_mode}")

        failure_tags = _require_list(result.get("failure_tags", []), name=f"results[{idx}].failure_tags")
        validated_tags = []
        for tag in failure_tags:
            tag_value = _require_string(tag, name=f"{task_id}.failure_tags item")
            if tag_value not in ALLOWED_FAILURE_TAGS:
                raise BenchmarkValidationError(f"unsupported failure tag for {task_id}: {tag_value}")
            validated_tags.append(tag_value)

        total_tokens_raw = result.get("total_tokens")
        total_tokens = None
        if total_tokens_raw is not None:
            total_tokens = _require_int(total_tokens_raw, name=f"results[{idx}].total_tokens")
            if total_tokens < 0:
                raise BenchmarkValidationError(f"total_tokens must be non-negative for {task_id}")

        user_turns = _require_int(
            result.get("user_turns_to_approved_plan"), name=f"results[{idx}].user_turns_to_approved_plan"
        )
        if user_turns < 1:
            raise BenchmarkValidationError(f"user_turns_to_approved_plan must be >= 1 for {task_id}")

        validated_results.append(
            {
                "task_id": task_id,
                "first_response_mode": first_response_mode,
                "bundled_intake": _require_bool(result.get("bundled_intake"), name=f"{task_id}.bundled_intake"),
                "asked_outcome": _require_bool(result.get("asked_outcome"), name=f"{task_id}.asked_outcome"),
                "used_why_this_matters": _require_bool(
                    result.get("used_why_this_matters"), name=f"{task_id}.used_why_this_matters"
                ),
                "user_turns_to_approved_plan": user_turns,
                "approved_without_rewrite": _require_bool(
                    result.get("approved_without_rewrite"), name=f"{task_id}.approved_without_rewrite"
                ),
                "downstream_execution_ready": _require_bool(
                    result.get("downstream_execution_ready"), name=f"{task_id}.downstream_execution_ready"
                ),
                "total_tokens": total_tokens,
                "failure_tags": validated_tags,
            }
        )

    return {
        "benchmark_name": benchmark_name,
        "version": version,
        "system_name": system_name,
        "run_label": run_label,
        "cases": cases,
        "results": validated_results,
    }


def _rate(results: list[dict[str, Any]], predicate) -> float:
    if not results:
        return 0.0
    return sum(1 for row in results if predicate(row)) / len(results)


def _tag_rate(results: list[dict[str, Any]], tag: str) -> float:
    return _rate(results, lambda row: tag in row["failure_tags"])


def score_results(cases_payload: dict[str, Any], results_payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_results_payload(cases_payload, results_payload)
    cases = validated["cases"]["tasks"]
    results = validated["results"]
    total_case_count = len(cases)
    evaluated_count = len(results)
    coverage_rate = evaluated_count / total_case_count

    intake_first_rate = _rate(results, lambda row: row["first_response_mode"] == "intake_only")
    bundled_intake_rate = _rate(results, lambda row: row["bundled_intake"])
    no_outcome_question_rate = _rate(results, lambda row: not row["asked_outcome"])
    no_why_this_matters_rate = _rate(results, lambda row: not row["used_why_this_matters"])
    approval_without_rewrite_rate = _rate(results, lambda row: row["approved_without_rewrite"])
    downstream_execution_ready_rate = _rate(results, lambda row: row["downstream_execution_ready"])
    scope_drift_rate = _tag_rate(results, "scope_drift")
    overengineering_rate = _tag_rate(results, "overengineering")
    weak_verification_rate = _tag_rate(results, "weak_verification")
    unsafe_assumption_rate = _tag_rate(results, "unsafe_assumption")

    median_user_turns = 0
    if results:
        median_user_turns = int(statistics.median(row["user_turns_to_approved_plan"] for row in results))
    mean_total_tokens = None
    token_values = [row["total_tokens"] for row in results if row["total_tokens"] is not None]
    if token_values:
        mean_total_tokens = sum(token_values) / len(token_values)

    scope_control_score = 1.0 - max(scope_drift_rate, overengineering_rate)
    verification_score = 1.0 - weak_verification_rate

    weighted_score = (
        0.20 * intake_first_rate
        + 0.10 * bundled_intake_rate
        + 0.05 * no_outcome_question_rate
        + 0.05 * no_why_this_matters_rate
        + 0.20 * approval_without_rewrite_rate
        + 0.20 * downstream_execution_ready_rate
        + 0.10 * scope_control_score
        + 0.10 * verification_score
    )

    category_map = {task["id"]: task["category"] for task in cases}
    category_summary: dict[str, dict[str, Any]] = {}
    for category in sorted(ALLOWED_CATEGORIES):
        rows = [row for row in results if category_map.get(row["task_id"]) == category]
        category_summary[category] = {
            "evaluated_count": len(rows),
            "intake_first_rate": round(_rate(rows, lambda row: row["first_response_mode"] == "intake_only"), 4),
            "approval_without_rewrite_rate": round(_rate(rows, lambda row: row["approved_without_rewrite"]), 4),
            "downstream_execution_ready_rate": round(_rate(rows, lambda row: row["downstream_execution_ready"]), 4),
        }

    return {
        "benchmark_name": validated["benchmark_name"],
        "version": validated["version"],
        "system_name": validated["system_name"],
        "run_label": validated["run_label"],
        "coverage_rate": round(coverage_rate, 4),
        "coverage_status": coverage_status(coverage_rate),
        "evaluated_count": evaluated_count,
        "total_case_count": total_case_count,
        "metrics": {
            "intake_first_rate": round(intake_first_rate, 4),
            "bundled_intake_rate": round(bundled_intake_rate, 4),
            "no_outcome_question_rate": round(no_outcome_question_rate, 4),
            "no_why_this_matters_rate": round(no_why_this_matters_rate, 4),
            "approval_without_rewrite_rate": round(approval_without_rewrite_rate, 4),
            "downstream_execution_ready_rate": round(downstream_execution_ready_rate, 4),
            "scope_drift_rate": round(scope_drift_rate, 4),
            "overengineering_rate": round(overengineering_rate, 4),
            "weak_verification_rate": round(weak_verification_rate, 4),
            "unsafe_assumption_rate": round(unsafe_assumption_rate, 4),
            "median_user_turns_to_approved_plan": median_user_turns,
            "mean_total_tokens": None if mean_total_tokens is None else round(mean_total_tokens, 2),
        },
        "composite_score_0_to_100": round(weighted_score * 100, 2),
        "category_summary": category_summary,
    }


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"Benchmark: {payload['benchmark_name']} v{payload['version']}")
    if "system_name" in payload:
        print(f"System: {payload['system_name']} ({payload['run_label']})")
    print(f"Coverage: {payload['evaluated_count']}/{payload['total_case_count']} ({payload['coverage_rate']:.2%})")
    if "coverage_status" in payload:
        print(f"Coverage status: {payload['coverage_status']}")
    if "composite_score_0_to_100" in payload:
        print(f"Composite score: {payload['composite_score_0_to_100']:.2f}/100")
        print("")
        print("Metrics:")
        for key, value in payload["metrics"].items():
            print(f"- {key}: {value}")
        print("")
        print("Category summary:")
        for category, row in payload["category_summary"].items():
            print(f"- {category}: {row}")


def cmd_validate_cases(args: argparse.Namespace) -> dict[str, Any]:
    cases = validate_cases_payload(_load_json(args.cases))
    return {
        "benchmark_name": cases["benchmark_name"],
        "version": cases["version"],
        "coverage_status": "official",
        "evaluated_count": len(cases["tasks"]),
        "total_case_count": len(cases["tasks"]),
        "coverage_rate": 1.0,
    }


def cmd_validate_results(args: argparse.Namespace) -> dict[str, Any]:
    payload = validate_results_payload(_load_json(args.cases), _load_json(args.results))
    return {
        "benchmark_name": payload["benchmark_name"],
        "version": payload["version"],
        "system_name": payload["system_name"],
        "run_label": payload["run_label"],
        "evaluated_count": len(payload["results"]),
        "total_case_count": len(payload["cases"]["tasks"]),
        "coverage_rate": round(len(payload["results"]) / len(payload["cases"]["tasks"]), 4),
        "coverage_status": coverage_status(len(payload["results"]) / len(payload["cases"]["tasks"])),
    }


def cmd_score(args: argparse.Namespace) -> dict[str, Any]:
    return score_results(_load_json(args.cases), _load_json(args.results))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="planloop-benchmark")
    sub = ap.add_subparsers(dest="command", required=True)

    p_cases = sub.add_parser("validate-cases")
    p_cases.add_argument("--cases", required=True)
    p_cases.add_argument("--json", action="store_true")
    p_cases.set_defaults(func=cmd_validate_cases)

    p_results = sub.add_parser("validate-results")
    p_results.add_argument("--cases", required=True)
    p_results.add_argument("--results", required=True)
    p_results.add_argument("--json", action="store_true")
    p_results.set_defaults(func=cmd_validate_results)

    p_score = sub.add_parser("score")
    p_score.add_argument("--cases", required=True)
    p_score.add_argument("--results", required=True)
    p_score.add_argument("--json", action="store_true")
    p_score.set_defaults(func=cmd_score)
    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.func(args)
    except (BenchmarkValidationError, FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    _emit(payload, bool(getattr(args, "json", False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
