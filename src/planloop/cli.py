#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import (
    DEFAULT_RUN_ROOT,
    CriticReport,
    DiscoveryPacket,
    LoopConfig,
    ModeratorReview,
    ModeratedPrdLoop,
    PRD,
    PlanPacket,
    ValidationError,
    build_guided_intake_artifacts,
    guided_intake_questions,
    resolve_workspace_strategy_input,
    validate_output_path,
)


def _read_task(args: argparse.Namespace) -> str:
    if args.task_text:
        return str(args.task_text).strip()
    if args.task_file:
        return Path(args.task_file).expanduser().read_text(encoding="utf-8").strip()
    raise RuntimeError("either --task-text or --task-file is required")


def _read_json_file(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _read_or_prompt_task(args: argparse.Namespace) -> str:
    if args.task_text or args.task_file:
        return _read_task(args)
    try:
        print("Task to plan: ", end="", file=sys.stderr)
        value = input().strip()
    except EOFError as exc:
        raise RuntimeError("either --task-text or --task-file is required when stdin is not interactive") from exc
    if not value:
        raise RuntimeError("task_text must not be empty")
    return value


def _prompt_non_empty(prompt: str) -> str:
    while True:
        try:
            print(prompt, end="", file=sys.stderr)
            value = input().strip()
        except EOFError as exc:
            raise RuntimeError("interactive input ended before the run command finished") from exc
        if value:
            return value
        print("Please enter a value.", file=sys.stderr)


def _prompt_guided_answer(question: dict[str, object], *, preset: str = "") -> str:
    if preset.strip():
        return preset.strip()
    print("", file=sys.stderr)
    print(f"{question['title']}", file=sys.stderr)
    print(str(question["question"]), file=sys.stderr)
    for option in question["options"]:
        print(f"  {option['key']}. {option['summary']} Example: {option['example']}", file=sys.stderr)
    print("  Or just tell me in your own words.", file=sys.stderr)
    return _prompt_non_empty("Choose A/B/C or type your answer: ")


def _prompt_workspace_strategy(*, preset: str = "") -> str:
    while True:
        raw = _prompt_guided_answer(guided_intake_questions()[-1], preset=preset)
        try:
            return resolve_workspace_strategy_input(raw)
        except ValidationError as exc:
            preset = ""
            print(f"Please use A/B/C or say branch, worktree, or in place. ({exc})", file=sys.stderr)


def _prompt_output_path(*, preset: str = "") -> str:
    while True:
        raw = preset.strip() or _prompt_non_empty(
            "\nFinal plan output path (absolute path, example: /tmp/my-plan.md): "
        )
        try:
            return validate_output_path(raw)
        except ValidationError as exc:
            preset = ""
            print(f"Please enter an absolute path. ({exc})", file=sys.stderr)


def _ensure_existing_output_parent(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.parent.exists():
        raise ValidationError(f"output path parent directory must already exist: {path.parent}")
    return str(path)


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if payload.get("result_type") == "auto_finish":
            next_payload = payload["next_handoff"]
            print("# Planloop")
            print("")
            print(f"Run dir: {payload['run_dir']}")
            print(f"Task: {payload['task_text']}")
            if payload["state"]["phase"] == "succeeded":
                print("Status: Auto-finish complete. Final plan written.")
            else:
                print("Status: Auto-finish paused before completion.")
            print(f"Generated artifacts: {', '.join(payload.get('generated_artifacts', [])) or 'None'}")
            print(f"Current stage: {next_payload.get('stage_label')}")
            print(f"Final plan path: {payload.get('final_plan_path')}")
            paused_reason = payload.get("paused_reason") or ""
            if paused_reason:
                print(f"Paused reason: {paused_reason}")
            blockers = next_payload.get("blocking_conditions") or []
            if blockers:
                print("")
                print("Blocking conditions:")
                for item in blockers:
                    print(f"- {item}")
            print("")
            print("Next move:")
            print(next_payload.get("product_prompt", "No further action required."))
            if payload["state"]["phase"] != "succeeded":
                print("")
                print("Detailed prompt:")
                print(next_payload.get("prompt", ""))
            return
        if payload.get("result_type") == "interactive_run":
            next_payload = payload["next_handoff"]
            print("# Planloop")
            print("")
            print(f"Run dir: {payload['run_dir']}")
            print(f"Task: {payload['task_text']}")
            if payload.get("auto_finish"):
                if payload["state"]["phase"] == "succeeded":
                    print("Status: Intake complete. Auto-finish completed the planning loop.")
                else:
                    print("Status: Intake complete. Auto-finish paused before completion.")
            else:
                print("Status: Intake complete. PRD created.")
            print(f"Workspace strategy: {payload['prd']['workspace_strategy']}")
            print(f"Artifact output path: {payload['prd']['artifact_output_path']}")
            warnings = payload.get("warnings") or []
            if warnings:
                print("Warnings:")
                for item in warnings:
                    print(f"- {item}")
            print("")
            print(f"Next stage: {next_payload.get('stage_label')} - {next_payload.get('title')}")
            if next_payload.get("required_record"):
                print(f"Next artifact: {next_payload.get('required_record')}")
                print(
                    f"Suggested file: {payload['state']['artifact_paths'].get(next_payload.get('required_record') or '', 'N/A')}"
                )
            generated = payload.get("generated_artifacts") or []
            if generated:
                print(f"Generated artifacts: {', '.join(generated)}")
            if payload["state"]["phase"] == "succeeded":
                print(f"Final plan path: {payload.get('final_plan_path')}")
                return
            print("")
            print("Next move:")
            print(next_payload.get("product_prompt") or next_payload.get("prompt", ""))
            print("")
            print("Detailed prompt:")
            print(next_payload.get("prompt", ""))
            return
        if isinstance(payload, dict) and {"title", "prompt", "phase"}.issubset(payload):
            print(f"# {payload['title']}")
            print("")
            if payload.get("stage_label"):
                print(f"Stage: {payload['stage_label']}")
            print(f"Actor: {payload.get('actor_label') or 'None'}")
            print(f"Phase: {payload.get('phase')}")
            print(f"Iteration: {payload.get('iteration')}/{payload.get('max_iterations')}")
            print(f"Required record: {payload.get('required_record') or 'None'}")
            command = payload.get("record_command_template")
            if command:
                print(f"Record command: {command}")
            missing_fields = payload.get("missing_fields") or []
            print("Missing fields:")
            if missing_fields:
                for item in missing_fields:
                    print(f"- {item}")
            else:
                print("- None")
            blockers = payload.get("blocking_conditions") or []
            print("Blocking conditions:")
            if blockers:
                for item in blockers:
                    print(f"- {item}")
            else:
                print("- None")
            print("")
            print("Prompt:")
            print(payload.get("prompt", ""))
            return
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_init(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.create(
        task_text=_read_task(args),
        run_root=Path(args.run_root).expanduser(),
        config=LoopConfig(max_iterations=args.max_iterations),
    )
    return {
        "run_dir": str(loop.run_dir),
        "state": loop.state.to_dict(),
        "completion": loop.completion_summary(),
    }


def cmd_status(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    return {
        "run_dir": str(loop.run_dir),
        "state": loop.state.to_dict(),
        "completion": loop.completion_summary(),
    }


def cmd_record(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    payload = _read_json_file(args.input_file)
    if args.kind == "discovery":
        loop.record_discovery_packet(DiscoveryPacket.from_dict(payload))
    elif args.kind == "prd":
        loop.record_prd(PRD.from_dict(payload))
    elif args.kind == "plan":
        loop.record_plan_packet(PlanPacket.from_dict(payload))
    elif args.kind == "critique":
        loop.record_critic_report(CriticReport.from_dict(payload))
    elif args.kind == "moderator":
        loop.record_moderator_review(ModeratorReview.from_dict(payload))
    else:
        raise RuntimeError(f"unsupported record kind: {args.kind}")
    return {
        "run_dir": str(loop.run_dir),
        "state": loop.state.to_dict(),
        "completion": loop.completion_summary(),
    }


def cmd_report(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    final_path = loop.state.artifact_output_path
    exists = False
    if final_path and final_path != "Path pending user answer":
        exists = Path(final_path).expanduser().exists()
    return {
        "run_dir": str(loop.run_dir),
        "state": loop.state.to_dict(),
        "completion": loop.completion_summary(),
        "final_plan_path": final_path,
        "final_plan_exists": exists,
    }


def cmd_verify(args: argparse.Namespace) -> tuple[dict, int]:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    payload = {
        "run_dir": str(loop.run_dir),
        **loop.verify_completion(),
    }
    return payload, 0 if payload["ok"] else 2


def cmd_next(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    return loop.next_handoff()


def cmd_auto_finish(args: argparse.Namespace) -> dict:
    loop = ModeratedPrdLoop.load(Path(args.run_dir))
    payload = loop.auto_finish()
    return {
        "result_type": "auto_finish",
        "run_dir": str(loop.run_dir),
        "task_text": loop.state.task_text,
        **payload,
    }


def cmd_run(args: argparse.Namespace) -> dict:
    task_text = _read_or_prompt_task(args)
    loop = ModeratedPrdLoop.create(
        task_text=task_text,
        run_root=Path(args.run_root).expanduser(),
        config=LoopConfig(max_iterations=args.max_iterations),
    )
    print("Plan is mandatory. I just need four quick preferences.", file=sys.stderr)
    questions = guided_intake_questions()
    success_answer = _prompt_guided_answer(questions[0], preset=args.success)
    failure_answer = _prompt_guided_answer(questions[1], preset=args.failure)
    safety_answer = _prompt_guided_answer(questions[2], preset=args.safety)
    workspace_strategy = _prompt_workspace_strategy(preset=args.workspace_strategy)
    output_path = _prompt_output_path(preset=args.output_path)
    if args.auto_finish:
        output_path = _ensure_existing_output_parent(output_path)
    discovery, prd, intake_summary = build_guided_intake_artifacts(
        task_text=task_text,
        success_answer=success_answer,
        failure_answer=failure_answer,
        safety_answer=safety_answer,
        workspace_answer=workspace_strategy,
        artifact_output_path=output_path,
        iteration_budget=args.max_iterations,
    )
    loop.record_discovery_packet(discovery)
    loop.record_prd(prd)
    next_payload = loop.next_handoff()
    warnings: list[str] = []
    parent_dir = Path(prd.artifact_output_path).expanduser().parent
    if not parent_dir.exists():
        warnings.append(f"output path parent directory does not exist yet: {parent_dir}")
    auto_payload: dict[str, object] = {}
    if args.auto_finish:
        auto_payload = loop.auto_finish()
        next_payload = auto_payload["next_handoff"]  # type: ignore[index]
    return {
        "result_type": "interactive_run",
        "run_dir": str(loop.run_dir),
        "task_text": task_text,
        "intake_summary": intake_summary,
        "discovery_packet": discovery.to_dict(),
        "prd": prd.to_dict(),
        "next_handoff": next_payload,
        "state": auto_payload.get("state", loop.state.to_dict()),
        "completion": auto_payload.get("completion", loop.completion_summary()),
        "warnings": warnings,
        "auto_finish": bool(args.auto_finish),
        "generated_artifacts": auto_payload.get("generated_artifacts", []),
        "final_plan_path": auto_payload.get("final_plan_path", prd.artifact_output_path),
        "final_plan_exists": auto_payload.get("final_plan_exists", False),
        "paused_reason": auto_payload.get("paused_reason", ""),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="planloop")
    sub = ap.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--task-text", default="")
    p_init.add_argument("--task-file", default="")
    p_init.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    p_init.add_argument("--max-iterations", type=int, default=5)
    p_init.add_argument("--json", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status")
    p_status.add_argument("--run-dir", required=True)
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_record = sub.add_parser("record")
    p_record.add_argument("--run-dir", required=True)
    p_record.add_argument("--kind", required=True, choices=["discovery", "prd", "plan", "critique", "moderator"])
    p_record.add_argument("--input-file", required=True)
    p_record.add_argument("--json", action="store_true")
    p_record.set_defaults(func=cmd_record)

    p_report = sub.add_parser("report")
    p_report.add_argument("--run-dir", required=True)
    p_report.add_argument("--json", action="store_true")
    p_report.set_defaults(func=cmd_report)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--run-dir", required=True)
    p_verify.add_argument("--json", action="store_true")
    p_verify.set_defaults(func=cmd_verify)

    p_next = sub.add_parser("next")
    p_next.add_argument("--run-dir", required=True)
    p_next.add_argument("--json", action="store_true")
    p_next.set_defaults(func=cmd_next)

    p_handoff = sub.add_parser("handoff")
    p_handoff.add_argument("--run-dir", required=True)
    p_handoff.add_argument("--json", action="store_true")
    p_handoff.set_defaults(func=cmd_next)

    p_auto_finish = sub.add_parser("auto-finish")
    p_auto_finish.add_argument("--run-dir", required=True)
    p_auto_finish.add_argument("--json", action="store_true")
    p_auto_finish.set_defaults(func=cmd_auto_finish)

    p_run = sub.add_parser("run")
    p_run.add_argument("--task-text", default="")
    p_run.add_argument("--task-file", default="")
    p_run.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    p_run.add_argument("--max-iterations", type=int, default=5)
    p_run.add_argument("--outcome", default="", help=argparse.SUPPRESS)
    p_run.add_argument("--success", default="")
    p_run.add_argument("--failure", default="")
    p_run.add_argument("--safety", default="")
    p_run.add_argument("--workspace-strategy", default="")
    p_run.add_argument("--output-path", default="")
    p_run.add_argument("--auto-finish", action="store_true")
    p_run.add_argument("--json", action="store_true")
    p_run.set_defaults(func=cmd_run)
    return ap


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    as_json = bool(getattr(args, "json", False))
    try:
        result = args.func(args)
    except (ValidationError, RuntimeError, FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        error_payload = {"ok": False, "error": str(exc)}
        if as_json:
            _emit(error_payload, True)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    exit_code = 0
    payload = result
    if isinstance(result, tuple):
        payload, exit_code = result
    _emit(payload, as_json)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
