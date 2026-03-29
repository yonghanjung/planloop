#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_ROOT = ROOT / ".planloop" / "runs"
VALID_PHASES = {"intake", "planning", "critique", "moderator_review", "prd_revision", "succeeded", "exhausted"}
VALID_TERMINAL_PHASES = {"succeeded", "exhausted"}
VALID_WORKSPACE_STRATEGIES = {"in_place", "branch", "worktree"}
VALID_CRITIC_DECISIONS = {"approve", "revise"}
VALID_MODERATOR_DECISIONS = {"approve", "reject"}
ARTIFACT_FILENAMES = {
    "task": "task.md",
    "discovery_packet": "discovery_packet.json",
    "prd": "prd.json",
    "plan_packet": "plan_packet.json",
    "critic_report": "critic_report.json",
    "moderator_review": "moderator_review.json",
    "run_state": "run_state.json",
}
ARTIFACT_REQUIRED_FIELDS = {
    "discovery_packet": [
        "stated_request",
        "interpreted_goal",
        "desired_end_state",
        "success_signals",
        "failure_signals",
        "approval_and_safety_boundaries",
        "workspace_strategy",
        "artifact_output_path",
        "iteration_budget",
        "moderator_confidence",
    ],
    "prd": [
        "user_intent",
        "success_criteria",
        "failure_conditions",
        "safety_constraints",
        "workspace_strategy",
        "artifact_output_path",
        "iteration_budget",
        "acceptance_bar_for_planner_approval",
        "moderator_rejection_log",
    ],
    "plan_packet": [
        "goal_mapping",
        "minimal_strategy",
        "implementation_shape",
        "tdd_qa",
        "risk_controls",
        "workspace_strategy",
        "artifact_output_path",
        "critique_responses",
        "open_assumptions",
        "why_this_is_minimal",
    ],
    "critic_report": [
        "decision",
        "iteration_count",
        "major_failures",
        "missing_evidence",
        "complexity_concerns",
        "safety_concerns",
        "testing_gaps",
        "questions_the_planner_must_answer",
    ],
    "moderator_review": [
        "decision",
        "iteration_count",
        "prd_compliance",
        "user_value_alignment",
        "safety_review",
        "reasons",
        "required_prd_updates",
        "residual_unknowns",
    ],
}
PHASE_STAGE_LABELS = {
    "intake": "Clarify",
    "planning": "Draft Plan",
    "critique": "Stress-Test Plan",
    "moderator_review": "Approve Plan",
    "prd_revision": "Revise Requirements",
    "succeeded": "Complete",
    "exhausted": "Budget Exhausted",
}
GUIDED_INTAKE_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "success",
        "title": "Success",
        "question": "What kind of plan should count as good enough?",
        "options": [
            {"key": "A", "summary": "A reviewable plan is enough.", "example": "The plan is clear enough that I can approve it quickly."},
            {"key": "B", "summary": "Include tests, checks, or commands.", "example": "The plan names concrete validation steps."},
            {
                "key": "C",
                "summary": "Include a recommendation plus verification.",
                "example": "The plan recommends one path and explains how to verify it.",
            },
        ],
    },
    {
        "id": "failure",
        "title": "Failure",
        "question": "What should definitely not happen?",
        "options": [
            {"key": "A", "summary": "Overengineering.", "example": "Too many files, abstractions, or extra work."},
            {"key": "B", "summary": "Weak verification.", "example": "No tests, checks, or clear proof."},
            {"key": "C", "summary": "Scope drift.", "example": "It changes unrelated systems or adds extras."},
        ],
    },
    {
        "id": "safety",
        "title": "Safety and approvals",
        "question": "How cautious should the workflow be?",
        "options": [
            {"key": "A", "summary": "Planning only, no changes.", "example": "Analyze and plan, but do not edit anything."},
            {
                "key": "B",
                "summary": "Local changes are okay, but no external side effects.",
                "example": "Edit local files, but do not send, deploy, or touch third-party systems.",
            },
            {
                "key": "C",
                "summary": "Normal local workflow is okay, but pause at risky steps.",
                "example": "Work locally, but ask before anything irreversible or unclear.",
            },
        ],
    },
    {
        "id": "workspace",
        "title": "Workspace and output",
        "question": "Where should the work happen, and where should the final plan be saved?",
        "options": [
            {"key": "A", "summary": "Work in place.", "example": "Use the current working tree directly."},
            {"key": "B", "summary": "Use a branch.", "example": "Keep changes isolated on a named branch."},
            {"key": "C", "summary": "Use a worktree.", "example": "Use a separate working directory."},
        ],
    },
]


class ValidationError(RuntimeError):
    pass


def _now_local() -> datetime:
    return datetime.now().astimezone()


def _now_iso() -> str:
    return _now_local().isoformat(timespec="seconds")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _quote_join(items: list[str]) -> str:
    if not items:
        return "None."
    return "\n".join(f"- {item}" for item in items)


def _dedupe_strings(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = item.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(value)
    return out


def _split_user_list(raw: str) -> list[str]:
    items: list[str] = []
    for line in raw.replace("\r", "\n").split("\n"):
        for part in line.split(";"):
            value = part.strip(" -*\t")
            if value:
                items.append(value)
    return _dedupe_strings(items)


def stage_label_for_phase(phase: str) -> str:
    return PHASE_STAGE_LABELS.get(phase, phase.replace("_", " ").title())


def guided_intake_questions() -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for question in GUIDED_INTAKE_QUESTIONS:
        questions.append(
            {
                "id": question["id"],
                "title": question["title"],
                "question": question["question"],
                "options": [dict(option) for option in question["options"]],
            }
        )
    return questions


def render_guided_intake_prompt(task_text: str) -> str:
    lines = [
        "You are the intake host for a moderated planning workflow.",
        "Talk to the user in simple English.",
        "The outcome is implicit: produce a plan.",
        "Ask at most 4 short questions.",
        "For each question, give 3 easy options with examples, then say: \"Or just tell me in your own words.\"",
        "",
        f"User task: {task_text}",
        "",
        "Ask these questions:",
    ]
    for idx, question in enumerate(guided_intake_questions(), start=1):
        lines.append(f"{idx}. {question['title']}: {question['question']}")
        for option in question["options"]:
            lines.append(f"   - {option['key']}. {option['summary']} Example: {option['example']}")
        lines.append("   Or just tell me in your own words.")
    lines.extend(
        [
            "",
            "Also ask for the absolute artifact output path.",
            "",
            "After the answers, write discovery_packet.json with the required fields.",
        ]
    )
    return "\n".join(lines)


def resolve_workspace_strategy_input(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValidationError("workspace strategy answer must not be empty")
    upper = value.upper()
    if upper == "A":
        return "in_place"
    if upper == "B":
        return "branch"
    if upper == "C":
        return "worktree"
    lower = value.lower().replace("-", "_")
    if "worktree" in lower:
        return "worktree"
    if "branch" in lower:
        return "branch"
    if "in place" in lower or "in_place" in lower or "inplace" in lower:
        return "in_place"
    return normalize_workspace_strategy(value)


def _resolve_success(raw: str, artifact_output_path: str) -> dict[str, Any]:
    value = raw.strip()
    upper = value.upper()
    if upper == "A":
        return {
            "signals": ["The user can review the plan and approve it quickly."],
            "acceptance": "Keep the plan concise and easy to review.",
            "custom": False,
        }
    if upper == "B":
        return {
            "signals": ["The plan includes explicit tests, checks, or commands that verify it."],
            "acceptance": "Include explicit tests, checks, or commands.",
            "custom": False,
        }
    if upper == "C":
        return {
            "signals": ["The plan includes a clear recommendation and explicit verification steps."],
            "acceptance": "Include a recommendation and explicit verification steps.",
            "custom": False,
        }
    signals = _split_user_list(value)
    if not signals:
        raise ValidationError("success answer must not be empty")
    return {
        "signals": signals,
        "acceptance": f"Make this success condition directly checkable: {signals[0]}",
        "custom": True,
    }


def _resolve_failure(raw: str) -> dict[str, Any]:
    value = raw.strip()
    upper = value.upper()
    if upper == "A":
        return {"signals": ["The plan becomes overengineered or unnecessarily complex."], "custom": False}
    if upper == "B":
        return {"signals": ["The plan has weak verification or unclear proof."], "custom": False}
    if upper == "C":
        return {"signals": ["The plan drifts into unrelated scope."], "custom": False}
    signals = _split_user_list(value)
    if not signals:
        raise ValidationError("failure answer must not be empty")
    return {"signals": signals, "custom": True}


def _resolve_safety(raw: str) -> dict[str, Any]:
    value = raw.strip()
    upper = value.upper()
    if upper == "A":
        return {"signals": ["Planning only. Do not make changes."], "custom": False}
    if upper == "B":
        return {"signals": ["Local changes are okay, but do not cause external side effects."], "custom": False}
    if upper == "C":
        return {"signals": ["Normal local workflow is okay, but pause at risky steps."], "custom": False}
    signals = _split_user_list(value)
    if not signals:
        raise ValidationError("safety answer must not be empty")
    return {"signals": signals, "custom": True}


def build_guided_intake_artifacts(
    *,
    task_text: str,
    success_answer: str,
    failure_answer: str,
    safety_answer: str,
    workspace_answer: str,
    artifact_output_path: str,
    iteration_budget: int = 5,
) -> tuple[DiscoveryPacket, PRD, dict[str, Any]]:
    if not task_text.strip():
        raise ValidationError("task_text must not be empty")
    workspace_strategy = resolve_workspace_strategy_input(workspace_answer)
    validated_output_path = validate_output_path(artifact_output_path)
    success = _resolve_success(success_answer, validated_output_path)
    failure = _resolve_failure(failure_answer)
    safety = _resolve_safety(safety_answer)
    moderator_confidence = "medium" if any((success["custom"], failure["custom"], safety["custom"])) else "high"
    task_text_clean = task_text.strip()
    interpreted_goal = f"Produce an approved plan for: {task_text_clean}"
    desired_end_state = "A plan document exists and is ready for review."
    if not success["custom"] and success_answer.strip().upper() == "B":
        desired_end_state = "A plan document exists with explicit tests, checks, or commands."
    if not success["custom"] and success_answer.strip().upper() == "C":
        desired_end_state = "A plan document exists with a recommendation and explicit verification steps."
    boundaries = _dedupe_strings(
        safety["signals"]
        + [f"Use workspace strategy: {workspace_strategy}.", f"Write the final plan artifact to: {validated_output_path}."]
    )
    discovery = DiscoveryPacket(
        stated_request=task_text_clean,
        interpreted_goal=interpreted_goal,
        desired_end_state=desired_end_state,
        success_signals=_dedupe_strings(success["signals"]),
        failure_signals=_dedupe_strings(failure["signals"]),
        approval_and_safety_boundaries=boundaries,
        workspace_strategy=workspace_strategy,
        artifact_output_path=validated_output_path,
        iteration_budget=iteration_budget,
        moderator_confidence=moderator_confidence,
    )
    prd = PRD(
        user_intent=interpreted_goal,
        success_criteria=_dedupe_strings(
            discovery.success_signals + [f"Write the final plan document to {validated_output_path}."]
        ),
        failure_conditions=list(discovery.failure_signals),
        safety_constraints=_dedupe_strings(
            safety["signals"]
            + [f"Use workspace strategy: {workspace_strategy}.", f"Keep artifact output path fixed at {validated_output_path}."]
        ),
        workspace_strategy=workspace_strategy,
        artifact_output_path=validated_output_path,
        iteration_budget=iteration_budget,
        acceptance_bar_for_planner_approval=_dedupe_strings(
            [
                "Produce a plan document only. Do not treat this workflow as implementation by default.",
                success["acceptance"],
                "Use the minimal credible path only.",
                "Stay aligned to the chosen workspace strategy and output path.",
                "Address approval gates explicitly.",
            ]
        ),
        moderator_rejection_log=[],
    )
    intake_summary = {
        "success_answer": success_answer.strip(),
        "failure_answer": failure_answer.strip(),
        "safety_answer": safety_answer.strip(),
        "workspace_strategy": workspace_strategy,
        "artifact_output_path": validated_output_path,
        "moderator_confidence": moderator_confidence,
        "stage_label": stage_label_for_phase("planning"),
    }
    return discovery, prd, intake_summary


def _looks_like_validation_step(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("check", "test", "verify", "validation", "command", "confirm"))


def _has_explicit_stop_language(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("pause", "stop", "approval", "review", "before"))


def synthesize_plan_packet(
    *,
    task_text: str,
    prd: "PRD",
    critic: "CriticReport | None" = None,
) -> "PlanPacket":
    revision_items: list[str] = []
    if critic is not None and critic.decision == "revise":
        revision_items.extend(critic.major_failures)
        revision_items.extend(critic.missing_evidence)
        revision_items.extend(critic.complexity_concerns)
        revision_items.extend(critic.safety_concerns)
        revision_items.extend(critic.testing_gaps)
        revision_items.extend(critic.questions_the_planner_must_answer)
    validation_steps: list[str] = []
    for item in prd.success_criteria:
        if _looks_like_validation_step(item):
            validation_steps.append(f"Verify: {item}")
    validation_steps.append(f"Confirm the final plan document is written to {prd.artifact_output_path}.")
    validation_steps.append("Check that every proposed step maps back to the stated user intent and acceptance bar.")
    implementation_shape = [
        f"Restate the task and boundaries for: {task_text}",
        "List the minimum prerequisite checks before any change or external action.",
        "Outline the smallest implementation sequence that satisfies the PRD.",
        "Document the explicit validation and approval-stop steps before completion.",
    ]
    if revision_items:
        implementation_shape.append("Tighten the revised sections called out by the prior critique.")
    risk_controls = _dedupe_strings(
        list(prd.safety_constraints)
        + [
            f"Keep the work inside the `{prd.workspace_strategy}` strategy.",
            "Do not widen scope beyond the current PRD.",
            "Stop at approval gates before any risky or external action.",
        ]
    )
    critique_responses = [f"Addressed: {item}" for item in revision_items]
    return PlanPacket(
        goal_mapping=[
            f"Deliver the requested outcome with the smallest credible plan: {prd.user_intent}",
            f"Preserve the workspace strategy `{prd.workspace_strategy}` and fixed output path `{prd.artifact_output_path}`.",
            "Keep validation explicit and lightweight enough for quick review.",
        ],
        minimal_strategy=(
            "Start with the smallest prerequisite check, then outline only the task-specific implementation steps, "
            "then run the explicit validation checks, and stop at the approval gates. Avoid unrelated refactors, "
            "extra abstractions, or speculative automation."
        ),
        implementation_shape=implementation_shape,
        tdd_qa=_dedupe_strings(validation_steps),
        risk_controls=risk_controls,
        workspace_strategy=prd.workspace_strategy,
        artifact_output_path=prd.artifact_output_path,
        critique_responses=critique_responses,
        open_assumptions=[],
        why_this_is_minimal=(
            "It keeps only prerequisites, the minimum implementation sequence, explicit validation, and explicit "
            "stop points. It does not add broader automation, unrelated edits, or speculative scope."
        ),
    )


def synthesize_critic_report(*, prd: "PRD", plan: "PlanPacket", iteration_count: int) -> "CriticReport":
    major_failures: list[str] = []
    missing_evidence: list[str] = []
    complexity_concerns: list[str] = []
    safety_concerns: list[str] = []
    testing_gaps: list[str] = []
    questions: list[str] = []
    if not plan.goal_mapping:
        major_failures.append("The plan does not map the implementation back to the user intent.")
    if not any(_looks_like_validation_step(item) for item in plan.tdd_qa):
        testing_gaps.append("The plan does not name a concrete validation or verification step.")
        questions.append("What exact check proves the plan worked?")
    if prd.artifact_output_path not in "\n".join(plan.tdd_qa):
        missing_evidence.append("The plan does not explicitly confirm the final output path.")
    if not any(_has_explicit_stop_language(item) for item in plan.risk_controls):
        safety_concerns.append("The plan does not clearly stop at an approval gate before risky actions.")
    if len(plan.implementation_shape) > 6:
        complexity_concerns.append("The implementation shape is wider than the minimal path.")
    if len(plan.minimal_strategy.split()) > 70:
        complexity_concerns.append("The minimal strategy explanation is longer than needed.")
    decision = "approve"
    if any((major_failures, missing_evidence, complexity_concerns, safety_concerns, testing_gaps, questions)):
        decision = "revise"
    return CriticReport(
        decision=decision,
        iteration_count=iteration_count,
        major_failures=major_failures,
        missing_evidence=missing_evidence,
        complexity_concerns=complexity_concerns,
        safety_concerns=safety_concerns,
        testing_gaps=testing_gaps,
        questions_the_planner_must_answer=questions,
    )


def synthesize_moderator_review(
    *,
    prd: "PRD",
    plan: "PlanPacket",
    critic: "CriticReport",
    iteration_count: int,
) -> "ModeratorReview":
    blockers = []
    if plan.workspace_strategy != prd.workspace_strategy:
        blockers.append("Plan workspace strategy drifted from the PRD.")
    if plan.artifact_output_path != prd.artifact_output_path:
        blockers.append("Plan output path drifted from the PRD.")
    if critic.decision != "approve":
        blockers.append("Critic did not approve the current plan yet.")
    if blockers:
        return ModeratorReview(
            decision="reject",
            iteration_count=iteration_count,
            prd_compliance=["The plan is not yet fully aligned to the current PRD."],
            user_value_alignment=["The current draft still needs tightening before approval."],
            safety_review=["Approval is withheld until the unresolved blockers are fixed."],
            reasons=blockers,
            required_prd_updates=blockers,
            residual_unknowns=[],
        )
    return ModeratorReview(
        decision="approve",
        iteration_count=iteration_count,
        prd_compliance=[
            "The plan stays inside the current PRD boundaries.",
            f"The plan preserves the `{prd.workspace_strategy}` workspace strategy and fixed output path.",
        ],
        user_value_alignment=[
            "The plan remains short, reviewable, and explicit about validation.",
            "The plan optimizes for the minimal credible path instead of a broad implementation.",
        ],
        safety_review=[
            "The plan keeps approval-stop language before risky or external actions.",
            "No new destructive or hidden side effects are introduced by the auto-generated draft.",
        ],
        reasons=[
            "The critic approved the current plan.",
            "The plan stays aligned to the current PRD, workspace strategy, and artifact output path.",
        ],
        required_prd_updates=[],
        residual_unknowns=[],
    )


def synthesize_revised_prd(*, prd: "PRD", review: "ModeratorReview") -> "PRD":
    updates = _dedupe_strings(review.required_prd_updates)
    return PRD(
        user_intent=prd.user_intent,
        success_criteria=list(prd.success_criteria),
        failure_conditions=list(prd.failure_conditions),
        safety_constraints=list(prd.safety_constraints),
        workspace_strategy=prd.workspace_strategy,
        artifact_output_path=prd.artifact_output_path,
        iteration_budget=prd.iteration_budget,
        acceptance_bar_for_planner_approval=_dedupe_strings(
            list(prd.acceptance_bar_for_planner_approval) + updates
        ),
        moderator_rejection_log=_dedupe_strings(list(prd.moderator_rejection_log) + review.reasons),
    )


def _require_mapping(payload: Any, *, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationError(f"{name} must be a mapping")
    return payload


def _require_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"`{key}` must be a non-empty string")
    return value.strip()


def _require_int(payload: dict[str, Any], key: str, *, minimum: int = 1) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < minimum:
        raise ValidationError(f"`{key}` must be an integer >= {minimum}")
    return value


def _require_string_list(payload: Any, *, name: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(payload, list):
        raise ValidationError(f"`{name}` must be a list")
    out: list[str] = []
    for item in payload:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"`{name}` items must be non-empty strings")
        out.append(item.strip())
    if not allow_empty and not out:
        raise ValidationError(f"`{name}` must not be empty")
    return out


def normalize_workspace_strategy(raw: str) -> str:
    value = raw.strip().lower().replace("-", "_").replace(" ", "_")
    if value in {"inplace", "in_place"}:
        return "in_place"
    if value not in VALID_WORKSPACE_STRATEGIES:
        allowed = ", ".join(sorted(VALID_WORKSPACE_STRATEGIES))
        raise ValidationError(f"unsupported workspace strategy `{raw}`; expected one of: {allowed}")
    return value


def is_pending_path(raw: str) -> bool:
    value = raw.strip().lower()
    return value.startswith("path pending") or value in {"pending", "pending_user_answer", "pending user answer"}


def validate_output_path(raw: str) -> str:
    value = raw.strip()
    if not value:
        raise ValidationError("artifact_output_path must be a non-empty string")
    if is_pending_path(value):
        return "Path pending user answer"
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValidationError("artifact_output_path must be an absolute path or `Path pending user answer`")
    return str(path)


@dataclass(frozen=True)
class LoopConfig:
    max_iterations: int = 5

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LoopConfig":
        data = dict(payload)
        return cls(max_iterations=int(data.get("max_iterations", 5)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryPacket:
    stated_request: str
    interpreted_goal: str
    desired_end_state: str
    success_signals: list[str]
    failure_signals: list[str]
    approval_and_safety_boundaries: list[str]
    workspace_strategy: str
    artifact_output_path: str
    iteration_budget: int
    moderator_confidence: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DiscoveryPacket":
        data = _require_mapping(payload, name="DiscoveryPacket")
        return cls(
            stated_request=_require_string(data, "stated_request"),
            interpreted_goal=_require_string(data, "interpreted_goal"),
            desired_end_state=_require_string(data, "desired_end_state"),
            success_signals=_require_string_list(data.get("success_signals"), name="success_signals"),
            failure_signals=_require_string_list(data.get("failure_signals"), name="failure_signals"),
            approval_and_safety_boundaries=_require_string_list(
                data.get("approval_and_safety_boundaries"),
                name="approval_and_safety_boundaries",
            ),
            workspace_strategy=normalize_workspace_strategy(_require_string(data, "workspace_strategy")),
            artifact_output_path=validate_output_path(_require_string(data, "artifact_output_path")),
            iteration_budget=_require_int(data, "iteration_budget"),
            moderator_confidence=_require_string(data, "moderator_confidence"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PRD:
    user_intent: str
    success_criteria: list[str]
    failure_conditions: list[str]
    safety_constraints: list[str]
    workspace_strategy: str
    artifact_output_path: str
    iteration_budget: int
    acceptance_bar_for_planner_approval: list[str]
    moderator_rejection_log: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PRD":
        data = _require_mapping(payload, name="PRD")
        return cls(
            user_intent=_require_string(data, "user_intent"),
            success_criteria=_require_string_list(data.get("success_criteria"), name="success_criteria"),
            failure_conditions=_require_string_list(data.get("failure_conditions"), name="failure_conditions"),
            safety_constraints=_require_string_list(data.get("safety_constraints"), name="safety_constraints"),
            workspace_strategy=normalize_workspace_strategy(_require_string(data, "workspace_strategy")),
            artifact_output_path=validate_output_path(_require_string(data, "artifact_output_path")),
            iteration_budget=_require_int(data, "iteration_budget"),
            acceptance_bar_for_planner_approval=_require_string_list(
                data.get("acceptance_bar_for_planner_approval"),
                name="acceptance_bar_for_planner_approval",
            ),
            moderator_rejection_log=_require_string_list(
                data.get("moderator_rejection_log", []),
                name="moderator_rejection_log",
                allow_empty=True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanPacket:
    goal_mapping: list[str]
    minimal_strategy: str
    implementation_shape: list[str]
    tdd_qa: list[str]
    risk_controls: list[str]
    workspace_strategy: str
    artifact_output_path: str
    critique_responses: list[str]
    open_assumptions: list[str]
    why_this_is_minimal: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanPacket":
        data = _require_mapping(payload, name="PlanPacket")
        return cls(
            goal_mapping=_require_string_list(data.get("goal_mapping"), name="goal_mapping"),
            minimal_strategy=_require_string(data, "minimal_strategy"),
            implementation_shape=_require_string_list(data.get("implementation_shape"), name="implementation_shape"),
            tdd_qa=_require_string_list(data.get("tdd_qa"), name="tdd_qa"),
            risk_controls=_require_string_list(data.get("risk_controls"), name="risk_controls"),
            workspace_strategy=normalize_workspace_strategy(_require_string(data, "workspace_strategy")),
            artifact_output_path=validate_output_path(_require_string(data, "artifact_output_path")),
            critique_responses=_require_string_list(
                data.get("critique_responses", []),
                name="critique_responses",
                allow_empty=True,
            ),
            open_assumptions=_require_string_list(
                data.get("open_assumptions", []),
                name="open_assumptions",
                allow_empty=True,
            ),
            why_this_is_minimal=_require_string(data, "why_this_is_minimal"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CriticReport:
    decision: str
    iteration_count: int
    major_failures: list[str]
    missing_evidence: list[str]
    complexity_concerns: list[str]
    safety_concerns: list[str]
    testing_gaps: list[str]
    questions_the_planner_must_answer: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CriticReport":
        data = _require_mapping(payload, name="CriticReport")
        decision = _require_string(data, "decision")
        if decision not in VALID_CRITIC_DECISIONS:
            raise ValidationError(f"unsupported critic decision: {decision}")
        report = cls(
            decision=decision,
            iteration_count=_require_int(data, "iteration_count"),
            major_failures=_require_string_list(data.get("major_failures", []), name="major_failures", allow_empty=True),
            missing_evidence=_require_string_list(data.get("missing_evidence", []), name="missing_evidence", allow_empty=True),
            complexity_concerns=_require_string_list(
                data.get("complexity_concerns", []),
                name="complexity_concerns",
                allow_empty=True,
            ),
            safety_concerns=_require_string_list(
                data.get("safety_concerns", []),
                name="safety_concerns",
                allow_empty=True,
            ),
            testing_gaps=_require_string_list(data.get("testing_gaps", []), name="testing_gaps", allow_empty=True),
            questions_the_planner_must_answer=_require_string_list(
                data.get("questions_the_planner_must_answer", []),
                name="questions_the_planner_must_answer",
                allow_empty=True,
            ),
        )
        if report.decision == "revise" and not any(
            (
                report.major_failures,
                report.missing_evidence,
                report.complexity_concerns,
                report.safety_concerns,
                report.testing_gaps,
                report.questions_the_planner_must_answer,
            )
        ):
            raise ValidationError("revise critic report must contain at least one issue")
        return report

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModeratorReview:
    decision: str
    iteration_count: int
    prd_compliance: list[str]
    user_value_alignment: list[str]
    safety_review: list[str]
    reasons: list[str]
    required_prd_updates: list[str]
    residual_unknowns: list[str]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModeratorReview":
        data = _require_mapping(payload, name="ModeratorReview")
        decision = _require_string(data, "decision")
        if decision not in VALID_MODERATOR_DECISIONS:
            raise ValidationError(f"unsupported moderator decision: {decision}")
        review = cls(
            decision=decision,
            iteration_count=_require_int(data, "iteration_count"),
            prd_compliance=_require_string_list(data.get("prd_compliance"), name="prd_compliance"),
            user_value_alignment=_require_string_list(data.get("user_value_alignment"), name="user_value_alignment"),
            safety_review=_require_string_list(data.get("safety_review"), name="safety_review"),
            reasons=_require_string_list(data.get("reasons"), name="reasons"),
            required_prd_updates=_require_string_list(
                data.get("required_prd_updates", []),
                name="required_prd_updates",
                allow_empty=True,
            ),
            residual_unknowns=_require_string_list(
                data.get("residual_unknowns", []),
                name="residual_unknowns",
                allow_empty=True,
            ),
        )
        if review.decision == "reject" and not review.required_prd_updates:
            raise ValidationError("reject moderator review must include required_prd_updates")
        return review

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunState:
    run_id: str
    task_text: str
    phase: str
    status: str
    iteration: int
    max_iterations: int
    created_at: str
    updated_at: str
    artifact_paths: dict[str, str]
    workspace_strategy: str
    artifact_output_path: str
    terminal_reason: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunState":
        data = _require_mapping(payload, name="RunState")
        phase = _require_string(data, "phase")
        if phase not in VALID_PHASES:
            raise ValidationError(f"unsupported phase: {phase}")
        return cls(
            run_id=_require_string(data, "run_id"),
            task_text=_require_string(data, "task_text"),
            phase=phase,
            status=_require_string(data, "status"),
            iteration=_require_int(data, "iteration"),
            max_iterations=_require_int(data, "max_iterations"),
            created_at=_require_string(data, "created_at"),
            updated_at=_require_string(data, "updated_at"),
            artifact_paths=_require_mapping(data.get("artifact_paths"), name="artifact_paths"),
            workspace_strategy=_require_string(data, "workspace_strategy"),
            artifact_output_path=_require_string(data, "artifact_output_path"),
            terminal_reason=str(data.get("terminal_reason", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModeratedPrdLoop:
    def __init__(self, run_dir: Path, state: RunState, config: LoopConfig):
        self.run_dir = run_dir
        self.state = state
        self.config = config

    @classmethod
    def create(
        cls,
        *,
        task_text: str,
        run_root: Path = DEFAULT_RUN_ROOT,
        config: LoopConfig | None = None,
    ) -> "ModeratedPrdLoop":
        if not task_text.strip():
            raise ValidationError("task_text must not be empty")
        config = config or LoopConfig()
        timestamp = _now_local().strftime("%Y%m%d-%H%M%S")
        run_dir = Path(run_root).expanduser() / f"{timestamp}-{uuid.uuid4().hex[:8]}"
        _ensure_dir(run_dir)
        artifact_paths = {
            key: str(run_dir / filename)
            for key, filename in ARTIFACT_FILENAMES.items()
        }
        state = RunState(
            run_id=run_dir.name,
            task_text=task_text.strip(),
            phase="intake",
            status="running",
            iteration=1,
            max_iterations=config.max_iterations,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            artifact_paths=artifact_paths,
            workspace_strategy="in_place",
            artifact_output_path="Path pending user answer",
        )
        loop = cls(run_dir, state, config)
        _write_text(Path(artifact_paths["task"]), task_text.strip() + "\n")
        loop._persist_state()
        return loop

    @classmethod
    def load(cls, run_dir: Path) -> "ModeratedPrdLoop":
        base = Path(run_dir).expanduser()
        state = RunState.from_dict(_read_json(base / ARTIFACT_FILENAMES["run_state"]))
        return cls(base, state, LoopConfig(max_iterations=state.max_iterations))

    def _artifact_path(self, kind: str) -> Path:
        return Path(self.state.artifact_paths[kind])

    def _artifact_exists(self, kind: str) -> bool:
        return self._artifact_path(kind).exists()

    def _read_artifact(self, kind: str) -> dict[str, Any]:
        path = self._artifact_path(kind)
        if not path.exists():
            raise ValidationError(f"artifact `{kind}` is missing")
        return _read_json(path)

    def _read_artifact_if_present(self, kind: str) -> dict[str, Any] | None:
        path = self._artifact_path(kind)
        if not path.exists():
            return None
        return _read_json(path)

    def _persist_state(self) -> None:
        self.state.updated_at = _now_iso()
        _write_json(self._artifact_path("run_state"), self.state.to_dict())

    def _set_phase(self, phase: str, *, status: str = "running", terminal_reason: str = "") -> None:
        self.state.phase = phase
        self.state.status = status
        self.state.terminal_reason = terminal_reason

    def _bump_iteration_or_exhaust(self, reason: str) -> bool:
        if self.state.iteration >= self.state.max_iterations:
            self._set_phase("exhausted", status="exhausted", terminal_reason=reason)
            self._persist_state()
            return False
        self.state.iteration += 1
        return True

    def _moderator_approval_blockers(self, output_path: str) -> list[str]:
        blockers: list[str] = []
        if is_pending_path(output_path):
            blockers.append("artifact_output_path is still pending user answer")
            return blockers
        final_path = Path(output_path).expanduser()
        if not final_path.parent.exists():
            blockers.append("artifact_output_path parent directory does not exist yet")
        return blockers

    def next_required_record(self) -> str | None:
        if self.state.phase == "intake":
            return "discovery_packet" if not self._artifact_exists("discovery_packet") else "prd"
        if self.state.phase == "planning":
            return "plan_packet"
        if self.state.phase == "critique":
            return "critic_report"
        if self.state.phase == "moderator_review":
            return "moderator_review"
        if self.state.phase == "prd_revision":
            return "prd"
        return None

    def completion_summary(self) -> dict[str, Any]:
        full_loop_completed = self.state.phase == "succeeded"
        return {
            "discipline_state": "complete" if full_loop_completed else "incomplete",
            "full_loop_completed": full_loop_completed,
            "success_claim_allowed": full_loop_completed,
            "next_required_record": self.next_required_record(),
            "phase": self.state.phase,
            "iteration": self.state.iteration,
            "max_iterations": self.state.max_iterations,
            "artifact_output_path": self.state.artifact_output_path,
        }

    def auto_finish(self) -> dict[str, Any]:
        generated: list[str] = []
        paused_reason = ""
        while True:
            if self.state.phase == "intake":
                if not self._artifact_exists("discovery_packet"):
                    raise ValidationError("cannot auto-finish before discovery_packet exists")
                if not self._artifact_exists("prd"):
                    discovery = DiscoveryPacket.from_dict(self._read_artifact("discovery_packet"))
                    prd = PRD(
                        user_intent=discovery.interpreted_goal,
                        success_criteria=_dedupe_strings(
                            list(discovery.success_signals)
                            + [f"Write the final plan document to {discovery.artifact_output_path}."]
                        ),
                        failure_conditions=list(discovery.failure_signals),
                        safety_constraints=_dedupe_strings(
                            list(discovery.approval_and_safety_boundaries)
                            + [f"Keep artifact output path fixed at {discovery.artifact_output_path}."]
                        ),
                        workspace_strategy=discovery.workspace_strategy,
                        artifact_output_path=discovery.artifact_output_path,
                        iteration_budget=discovery.iteration_budget,
                        acceptance_bar_for_planner_approval=[
                            "Keep the final output reviewable and minimal.",
                            "Make validation explicit and locally checkable.",
                            "Address approval gates explicitly.",
                        ],
                        moderator_rejection_log=[],
                    )
                    self.record_prd(prd)
                    generated.append("prd")
                    continue
            if self.state.phase == "planning":
                prd = PRD.from_dict(self._read_artifact("prd"))
                critic = None
                if self._artifact_exists("critic_report"):
                    critic = CriticReport.from_dict(self._read_artifact("critic_report"))
                plan = synthesize_plan_packet(task_text=self.state.task_text, prd=prd, critic=critic)
                self.record_plan_packet(plan)
                generated.append("plan_packet")
                continue
            if self.state.phase == "critique":
                prd = PRD.from_dict(self._read_artifact("prd"))
                plan = PlanPacket.from_dict(self._read_artifact("plan_packet"))
                critic = synthesize_critic_report(prd=prd, plan=plan, iteration_count=self.state.iteration)
                self.record_critic_report(critic)
                generated.append("critic_report")
                continue
            if self.state.phase == "moderator_review":
                prd = PRD.from_dict(self._read_artifact("prd"))
                blockers = self._moderator_approval_blockers(prd.artifact_output_path)
                if blockers:
                    paused_reason = "; ".join(blockers)
                    break
                plan = PlanPacket.from_dict(self._read_artifact("plan_packet"))
                critic = CriticReport.from_dict(self._read_artifact("critic_report"))
                review = synthesize_moderator_review(
                    prd=prd,
                    plan=plan,
                    critic=critic,
                    iteration_count=self.state.iteration,
                )
                self.record_moderator_review(review)
                generated.append("moderator_review")
                continue
            if self.state.phase == "prd_revision":
                prd = PRD.from_dict(self._read_artifact("prd"))
                review = ModeratorReview.from_dict(self._read_artifact("moderator_review"))
                revised = synthesize_revised_prd(prd=prd, review=review)
                self.record_prd(revised)
                generated.append("prd")
                continue
            break
        return {
            "generated_artifacts": generated,
            "paused_reason": paused_reason,
            "state": self.state.to_dict(),
            "completion": self.completion_summary(),
            "next_handoff": self.next_handoff(),
            "final_plan_path": self.state.artifact_output_path,
            "final_plan_exists": (
                False
                if is_pending_path(self.state.artifact_output_path)
                else Path(self.state.artifact_output_path).expanduser().exists()
            ),
        }

    def next_handoff(self) -> dict[str, Any]:
        required_record = self.next_required_record()
        discovery_payload = self._read_artifact_if_present("discovery_packet")
        prd_payload = self._read_artifact_if_present("prd")
        plan_payload = self._read_artifact_if_present("plan_packet")
        critic_payload = self._read_artifact_if_present("critic_report")
        review_payload = self._read_artifact_if_present("moderator_review")

        discovery = DiscoveryPacket.from_dict(discovery_payload) if discovery_payload else None
        prd = PRD.from_dict(prd_payload) if prd_payload else None
        plan = PlanPacket.from_dict(plan_payload) if plan_payload else None
        critic = CriticReport.from_dict(critic_payload) if critic_payload else None
        review = ModeratorReview.from_dict(review_payload) if review_payload else None

        payload: dict[str, Any] = {
            "run_dir": str(self.run_dir),
            "run_id": self.state.run_id,
            "phase": self.state.phase,
            "stage_label": stage_label_for_phase(self.state.phase),
            "iteration": self.state.iteration,
            "max_iterations": self.state.max_iterations,
            "required_record": required_record,
            "record_command_template": None
            if required_record is None
            else (
                "python3 -m planloop.cli record "
                f"--run-dir {self.run_dir} --kind {required_record.replace('_packet', '').replace('_report', '').replace('moderator_review', 'moderator')} "
                "--input-file <input-file> --json"
            ),
            "actor": None,
            "actor_label": None,
            "title": None,
            "missing_fields": [] if required_record is None else list(ARTIFACT_REQUIRED_FIELDS[required_record]),
            "blocking_conditions": [],
            "context": {
                "task_text": self.state.task_text,
                "workspace_strategy": self.state.workspace_strategy,
                "artifact_output_path": self.state.artifact_output_path,
            },
            "prompt": "",
            "product_prompt": "",
        }

        if self.state.phase == "intake" and discovery is None:
            payload.update(
                {
                    "actor": "moderator",
                    "actor_label": "Agent M (Moderator)",
                    "title": "Collect the guided intake and write the Discovery Packet",
                    "prompt": render_guided_intake_prompt(self.state.task_text),
                    "product_prompt": (
                        "Ask the short guided intake in simple English, then write the discovery packet."
                    ),
                }
            )
            return payload

        if self.state.phase == "intake" and discovery is not None:
            blockers: list[str] = []
            if is_pending_path(discovery.artifact_output_path):
                blockers.append("artifact_output_path is still pending; carry that forward explicitly in the PRD")
            payload.update(
                {
                    "actor": "moderator",
                    "actor_label": "Agent M (Moderator)",
                    "title": "Freeze the PRD from the Discovery Packet",
                    "blocking_conditions": blockers,
                    "context": {
                        **payload["context"],
                        "stated_request": discovery.stated_request,
                        "interpreted_goal": discovery.interpreted_goal,
                        "desired_end_state": discovery.desired_end_state,
                    },
                    "prompt": (
                        "You are Agent M (Moderator). Convert the Discovery Packet into `prd.json`. "
                        "Keep it minimal and precise. Do not invent new goals.\n\n"
                        f"Stated request: {discovery.stated_request}\n"
                        f"Interpreted goal: {discovery.interpreted_goal}\n"
                        f"Desired end state: {discovery.desired_end_state}\n"
                        f"Success signals:\n{_quote_join(discovery.success_signals)}\n"
                        f"Failure signals:\n{_quote_join(discovery.failure_signals)}\n"
                        f"Safety boundaries:\n{_quote_join(discovery.approval_and_safety_boundaries)}\n"
                        f"Workspace strategy: {discovery.workspace_strategy}\n"
                        f"Artifact output path: {discovery.artifact_output_path}\n"
                        f"Iteration budget: {discovery.iteration_budget}\n\n"
                        "Write `prd.json` now. Preserve the workspace strategy, output path, and iteration budget."
                    ),
                    "product_prompt": (
                        "Turn the guided intake into a crisp requirements document without adding extra scope."
                    ),
                }
            )
            return payload

        if self.state.phase == "planning" and prd is not None:
            revision_items: list[str] = []
            if critic is not None and critic.decision == "revise":
                revision_items.extend(critic.major_failures)
                revision_items.extend(critic.missing_evidence)
                revision_items.extend(critic.complexity_concerns)
                revision_items.extend(critic.safety_concerns)
                revision_items.extend(critic.testing_gaps)
                revision_items.extend(critic.questions_the_planner_must_answer)
            payload.update(
                {
                    "actor": "planner",
                    "actor_label": "Agent P (Planner)",
                    "title": "Write the minimal Plan Packet",
                    "context": {
                        **payload["context"],
                        "user_intent": prd.user_intent,
                        "workspace_strategy": prd.workspace_strategy,
                        "artifact_output_path": prd.artifact_output_path,
                    },
                    "prompt": (
                        "You are Agent P (Planner). Write `plan_packet.json` for the current iteration. "
                        "Optimize only for: (1) achieving the PRD and (2) surviving Agent C critique. "
                        "Continuously ask whether each implementation detail is necessary and minimal.\n\n"
                        f"Iteration: {self.state.iteration}/{self.state.max_iterations}\n"
                        f"User intent: {prd.user_intent}\n"
                        f"Success criteria:\n{_quote_join(prd.success_criteria)}\n"
                        f"Failure conditions:\n{_quote_join(prd.failure_conditions)}\n"
                        f"Safety constraints:\n{_quote_join(prd.safety_constraints)}\n"
                        f"Acceptance bar:\n{_quote_join(prd.acceptance_bar_for_planner_approval)}\n"
                        f"Workspace strategy: {prd.workspace_strategy}\n"
                        f"Artifact output path: {prd.artifact_output_path}\n"
                        + (
                            f"\nCritic issues to answer before resubmission:\n{_quote_join(revision_items)}\n"
                            if revision_items
                            else "\nNo open critic issues are currently recorded.\n"
                        )
                        + "\nWrite `plan_packet.json` now."
                    ),
                    "product_prompt": (
                        "Draft the minimal plan that satisfies the current requirements, names the validation steps, "
                        "and stays inside the chosen workspace and output path."
                    ),
                }
            )
            return payload

        if self.state.phase == "critique" and prd is not None and plan is not None:
            payload.update(
                {
                    "actor": "critic",
                    "actor_label": "Agent C (Critic)",
                    "title": "Critique the current plan adversarially",
                    "context": {
                        **payload["context"],
                        "user_intent": prd.user_intent,
                        "minimal_strategy": plan.minimal_strategy,
                    },
                    "prompt": (
                        "You are Agent C (Critic). Review the current plan adversarially. "
                        "Approve only if the plan is minimal, evidenced, safe, and directly aligned to the PRD. "
                        "Otherwise return `decision=revise` with concrete failures.\n\n"
                        f"Iteration: {self.state.iteration}/{self.state.max_iterations}\n"
                        f"PRD user intent: {prd.user_intent}\n"
                        f"PRD success criteria:\n{_quote_join(prd.success_criteria)}\n"
                        f"PRD safety constraints:\n{_quote_join(prd.safety_constraints)}\n"
                        f"Plan minimal strategy: {plan.minimal_strategy}\n"
                        f"Plan implementation shape:\n{_quote_join(plan.implementation_shape)}\n"
                        f"Plan TDD/QA:\n{_quote_join(plan.tdd_qa)}\n"
                        f"Plan risk controls:\n{_quote_join(plan.risk_controls)}\n\n"
                        "Write `critic_report.json` now. Probe failure modes, missing evidence, complexity rent, "
                        "safety concerns, and testing gaps."
                    ),
                    "product_prompt": (
                        "Stress-test the current plan. Approve only if it is minimal, safe, and directly supported by evidence."
                    ),
                }
            )
            return payload

        if self.state.phase == "moderator_review" and prd is not None and plan is not None and critic is not None:
            blockers = self._moderator_approval_blockers(prd.artifact_output_path)
            payload.update(
                {
                    "actor": "moderator",
                    "actor_label": "Agent M (Moderator)",
                    "title": "Review the critic-approved plan against the PRD",
                    "blocking_conditions": blockers,
                    "context": {
                        **payload["context"],
                        "user_intent": prd.user_intent,
                        "critic_decision": critic.decision,
                        "artifact_output_path": prd.artifact_output_path,
                    },
                    "prompt": (
                        "You are Agent M (Moderator). Compare the current plan against the PRD, "
                        "user value, and safety constraints. Approve only if the plan is truly compliant. "
                        "If you reject, specify exact PRD updates.\n\n"
                        f"Iteration: {self.state.iteration}/{self.state.max_iterations}\n"
                        f"User intent: {prd.user_intent}\n"
                        f"PRD success criteria:\n{_quote_join(prd.success_criteria)}\n"
                        f"PRD failure conditions:\n{_quote_join(prd.failure_conditions)}\n"
                        f"PRD safety constraints:\n{_quote_join(prd.safety_constraints)}\n"
                        f"Plan minimal strategy: {plan.minimal_strategy}\n"
                        f"Critic decision: {critic.decision}\n"
                        f"Critic major failures:\n{_quote_join(critic.major_failures)}\n"
                        f"Critic testing gaps:\n{_quote_join(critic.testing_gaps)}\n"
                        f"Artifact output path: {prd.artifact_output_path}\n"
                        + (
                            f"Approval blockers:\n{_quote_join(blockers)}\n"
                            if blockers
                            else "No approval blockers are currently detected.\n"
                        )
                        + "\nWrite `moderator_review.json` now."
                    ),
                    "product_prompt": (
                        "Review the current plan against the requirements, user value, safety boundaries, "
                        "workspace strategy, and output path. Approve only if it truly matches."
                    ),
                }
            )
            return payload

        if self.state.phase == "prd_revision" and prd is not None and review is not None:
            payload.update(
                {
                    "actor": "moderator",
                    "actor_label": "Agent M (Moderator)",
                    "title": "Revise the PRD and restart the loop",
                    "context": {
                        **payload["context"],
                        "user_intent": prd.user_intent,
                        "last_decision": review.decision,
                    },
                    "prompt": (
                        "You are Agent M (Moderator). Update `prd.json` to address the last rejection. "
                        "Append the rejection reasons to `moderator_rejection_log`, keep validated constraints, "
                        "and only change what is necessary.\n\n"
                        f"Current user intent: {prd.user_intent}\n"
                        f"Moderator rejection reasons:\n{_quote_join(review.reasons)}\n"
                        f"Required PRD updates:\n{_quote_join(review.required_prd_updates)}\n"
                        f"Residual unknowns:\n{_quote_join(review.residual_unknowns)}\n"
                        f"Iteration for next cycle: {self.state.iteration}/{self.state.max_iterations}\n\n"
                        "Write the revised `prd.json` now."
                    ),
                    "product_prompt": "Revise the requirements to address the rejection reasons, then restart planning.",
                }
            )
            return payload

        if self.state.phase == "succeeded":
            payload.update(
                {
                    "title": "Run complete",
                    "prompt": (
                        "No further action is required. The moderated PRD loop succeeded and the final plan "
                        f"document was written to: {self.state.artifact_output_path}"
                    ),
                    "product_prompt": f"Complete. The final plan document was written to: {self.state.artifact_output_path}",
                }
            )
            return payload

        if self.state.phase == "exhausted":
            blockers = [self.state.terminal_reason] if self.state.terminal_reason else []
            payload.update(
                {
                    "actor": "user",
                    "actor_label": "User / Moderator",
                    "title": "Iteration budget exhausted",
                    "blocking_conditions": blockers,
                    "prompt": (
                        "This run cannot advance further because it hit the iteration cap. "
                        "Start a new run or re-initialize with a larger `--max-iterations` value if more cycles are justified."
                    ),
                    "product_prompt": (
                        "The run hit the iteration cap. Start a new run or increase the budget if more cycles are justified."
                    ),
                }
            )
            return payload

        raise ValidationError(f"unsupported handoff state: {self.state.phase}")

    def record_discovery_packet(self, packet: DiscoveryPacket) -> None:
        if self.state.phase != "intake" or self._artifact_exists("discovery_packet"):
            raise ValidationError("discovery_packet can only be recorded once during intake")
        _write_json(self._artifact_path("discovery_packet"), packet.to_dict())
        self.state.max_iterations = packet.iteration_budget
        self.config = LoopConfig(max_iterations=packet.iteration_budget)
        self.state.workspace_strategy = packet.workspace_strategy
        self.state.artifact_output_path = packet.artifact_output_path
        self._persist_state()

    def record_prd(self, prd: PRD) -> None:
        if self.state.phase not in {"intake", "prd_revision"}:
            raise ValidationError("prd can only be recorded during intake or prd_revision")
        if not self._artifact_exists("discovery_packet") and self.state.phase == "intake":
            raise ValidationError("discovery_packet must exist before recording the first prd")
        if prd.iteration_budget != self.state.max_iterations:
            raise ValidationError("prd iteration_budget must match the current loop max_iterations")
        _write_json(self._artifact_path("prd"), prd.to_dict())
        self.state.workspace_strategy = prd.workspace_strategy
        self.state.artifact_output_path = prd.artifact_output_path
        self._set_phase("planning")
        self._persist_state()

    def record_plan_packet(self, packet: PlanPacket) -> None:
        if self.state.phase != "planning":
            raise ValidationError("plan_packet can only be recorded during planning")
        prd = PRD.from_dict(self._read_artifact("prd"))
        if packet.workspace_strategy != prd.workspace_strategy:
            raise ValidationError("plan_packet workspace_strategy must match the current prd")
        if packet.artifact_output_path != prd.artifact_output_path:
            raise ValidationError("plan_packet artifact_output_path must match the current prd")
        _write_json(self._artifact_path("plan_packet"), packet.to_dict())
        self._set_phase("critique")
        self._persist_state()

    def record_critic_report(self, report: CriticReport) -> None:
        if self.state.phase != "critique":
            raise ValidationError("critic_report can only be recorded during critique")
        if report.iteration_count != self.state.iteration:
            raise ValidationError("critic_report iteration_count must match the current iteration")
        _write_json(self._artifact_path("critic_report"), report.to_dict())
        if report.decision == "approve":
            self._set_phase("moderator_review")
            self._persist_state()
            return
        if not self._bump_iteration_or_exhaust("critic requested revision at iteration cap"):
            return
        self._set_phase("planning")
        self._persist_state()

    def record_moderator_review(self, review: ModeratorReview) -> None:
        if self.state.phase != "moderator_review":
            raise ValidationError("moderator_review can only be recorded during moderator_review")
        if review.iteration_count != self.state.iteration:
            raise ValidationError("moderator_review iteration_count must match the current iteration")
        prd = PRD.from_dict(self._read_artifact("prd"))
        _write_json(self._artifact_path("moderator_review"), review.to_dict())
        if review.decision == "approve":
            if is_pending_path(prd.artifact_output_path):
                raise ValidationError("cannot approve while artifact_output_path is still pending user answer")
            output_path = Path(prd.artifact_output_path).expanduser()
            if not output_path.parent.exists():
                raise ValidationError("artifact_output_path parent directory must already exist")
            self._write_final_plan_document(output_path)
            self.state.artifact_output_path = str(output_path)
            self._set_phase("succeeded", status="succeeded")
            self._persist_state()
            return
        if not self._bump_iteration_or_exhaust("moderator rejected at iteration cap"):
            return
        self._set_phase("prd_revision")
        self._persist_state()

    def _write_final_plan_document(self, output_path: Path) -> None:
        prd = PRD.from_dict(self._read_artifact("prd"))
        plan = PlanPacket.from_dict(self._read_artifact("plan_packet"))
        review = ModeratorReview.from_dict(self._read_artifact("moderator_review"))
        critic_payload = self._read_artifact("critic_report")
        lines = [
            "# Plan Document",
            "",
            "## Problem",
            self.state.task_text,
            "",
            "## Approved PRD Summary",
            f"- User intent: {prd.user_intent}",
            "- Success criteria:",
            *[f"  - {item}" for item in prd.success_criteria],
            "- Failure conditions:",
            *[f"  - {item}" for item in prd.failure_conditions],
            "- Safety constraints:",
            *[f"  - {item}" for item in prd.safety_constraints],
            f"- Workspace strategy: {prd.workspace_strategy}",
            f"- Artifact output path: {prd.artifact_output_path}",
            f"- Iteration budget: {prd.iteration_budget}",
            "",
            "## Approved Plan",
            *[f"- {item}" for item in plan.goal_mapping],
            "",
            "### Minimal Strategy",
            plan.minimal_strategy,
            "",
            "### Implementation Shape",
            *[f"- {item}" for item in plan.implementation_shape],
            "",
            "## TDD and QA Strategy",
            *[f"- {item}" for item in plan.tdd_qa],
            "",
            "## Key Risks and Controls",
            *[f"- {item}" for item in plan.risk_controls],
            "",
            "## Rejected Alternatives",
        ]
        rejected = critic_payload.get("major_failures", []) + critic_payload.get("complexity_concerns", [])
        if rejected:
            lines.extend(f"- {item}" for item in rejected)
        else:
            lines.append("- None recorded beyond the approved minimal path.")
        lines.extend(
            [
                "",
                "## Moderator Approval Notes",
                *[f"- {item}" for item in review.reasons],
                f"- Approved at iteration: {review.iteration_count}",
            ]
        )
        if review.residual_unknowns:
            lines.append("- Residual unknowns:")
            lines.extend(f"  - {item}" for item in review.residual_unknowns)
        _write_text(output_path, "\n".join(lines).rstrip() + "\n")

    def verify_completion(self) -> dict[str, Any]:
        missing: list[str] = []
        for kind in ("discovery_packet", "prd", "plan_packet", "critic_report", "moderator_review"):
            if not self._artifact_exists(kind):
                missing.append(kind)
        if self.state.phase != "succeeded":
            missing.append("terminal_success")
        path = self.state.artifact_output_path
        if is_pending_path(path):
            missing.append("artifact_output_path")
        else:
            final_path = Path(path).expanduser()
            if not final_path.exists():
                missing.append("final_plan_document")
        return {
            "ok": not missing,
            "missing_conditions": missing,
            "completion": self.completion_summary(),
        }
