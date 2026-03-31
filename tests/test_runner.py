#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from planloop.runner import (  # noqa: E402
    CriticReport,
    DiscoveryPacket,
    LoopConfig,
    ModeratedPrdLoop,
    ModeratorReview,
    PRD,
    PlanPacket,
    ValidationError,
    build_guided_intake_artifacts,
    guided_intake_questions,
    render_guided_intake_prompt,
    synthesize_critic_report,
)


def make_run_root() -> Path:
    return Path(tempfile.mkdtemp(prefix="planloop-run-test-"))


def make_output_path(root: Path, name: str = "plan.md") -> str:
    return str(root / name)


def discovery_dict(*, output_path: str = "Path pending user answer", iteration_budget: int = 5) -> dict:
    return {
        "stated_request": "Install telegram-mcp-server.",
        "interpreted_goal": "Create a plan for a safe install workflow.",
        "desired_end_state": "A reviewable plan exists.",
        "success_signals": ["Plan is concise.", "Plan is actionable."],
        "failure_signals": ["Plan is overbuilt."],
        "approval_and_safety_boundaries": ["No external side effects."],
        "workspace_strategy": "branch",
        "artifact_output_path": output_path,
        "iteration_budget": iteration_budget,
        "moderator_confidence": "high",
    }


def prd_dict(*, output_path: str, iteration_budget: int = 5) -> dict:
    return {
        "user_intent": "Produce a clean install plan for telegram-mcp-server.",
        "in_scope": ["Produce a reviewable install plan."],
        "out_of_scope": ["Do not execute the install."],
        "user_values": ["Keep the plan minimal and explicit."],
        "success_criteria": ["Plan covers setup, validation, and stop points."],
        "failure_conditions": ["Touches unrelated systems."],
        "safety_constraints": ["Pause before external side effects."],
        "non_negotiable_approval_gates": ["Do not skip moderator approval."],
        "workspace_strategy": "branch",
        "artifact_output_path": output_path,
        "iteration_budget": iteration_budget,
        "acceptance_bar_for_planner_approval": ["Minimal path only."],
        "moderator_rejection_log": [],
    }


def plan_dict(*, output_path: str) -> dict:
    return {
        "goal_mapping": ["Map install prerequisites to the PRD."],
        "minimal_strategy": "Use the smallest local install and verification path.",
        "implementation_shape": ["docs/install.md", "scripts/validate.sh"],
        "tdd_qa": ["Run targeted validation commands."],
        "risk_controls": ["Stop before any external mutation."],
        "workspace_strategy": "branch",
        "artifact_output_path": output_path,
        "critique_responses": [],
        "open_assumptions": [],
        "why_this_is_minimal": "It avoids unnecessary abstractions.",
    }


def borderline_plan_dict(*, output_path: str) -> dict:
    return {
        "goal_mapping": ["Map install prerequisites to the PRD."],
        "minimal_strategy": " ".join(["minimal"] * 80),
        "implementation_shape": [f"Step {idx}" for idx in range(1, 8)],
        "tdd_qa": ["Run a verification command that confirms the plan output exists."],
        "risk_controls": [f"Pause for approval before writing the final plan to {output_path}."],
        "workspace_strategy": "branch",
        "artifact_output_path": output_path,
        "critique_responses": [],
        "open_assumptions": [],
        "why_this_is_minimal": "It stays close to the current path.",
    }


def critic_report(*, decision: str, iteration_count: int) -> dict:
    return {
        "decision": decision,
        "iteration_count": iteration_count,
        "major_failures": [] if decision == "approve" else ["Need a clearer validation step."],
        "missing_evidence": [],
        "complexity_concerns": [],
        "safety_concerns": [],
        "testing_gaps": [] if decision == "approve" else ["Validation commands are underspecified."],
        "questions_the_planner_must_answer": [] if decision == "approve" else ["What exact command proves the install worked?"],
    }


def moderator_review(*, decision: str, iteration_count: int) -> dict:
    return {
        "decision": decision,
        "iteration_count": iteration_count,
        "prd_compliance": ["Matches the current PRD."],
        "user_value_alignment": ["Keeps the plan minimal and reviewable."],
        "safety_review": ["Still stops before risky actions."],
        "reasons": ["The current decision is justified."],
        "required_prd_updates": [] if decision == "approve" else ["Tighten the validation expectations."],
        "residual_unknowns": [],
    }


def cli_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)
    return env


class PlanloopRunnerTests(unittest.TestCase):
    def test_loop_persists_critic_mode(self) -> None:
        run_root = make_run_root()
        loop = ModeratedPrdLoop.create(
            task_text="Install telegram-mcp-server.",
            run_root=run_root,
            config=LoopConfig(max_iterations=3, critic_mode="balanced"),
        )
        self.assertEqual(loop.state.critic_mode, "balanced")
        reloaded = ModeratedPrdLoop.load(loop.run_dir)
        self.assertEqual(reloaded.state.critic_mode, "balanced")
        handoff = reloaded.next_handoff()
        self.assertEqual(handoff["critic_mode"], "balanced")
        self.assertEqual(handoff["critic_mode_label"], "Balanced")

    def test_guided_intake_artifacts_build_from_option_answers(self) -> None:
        output_path = "/tmp/planloop-test-plan.md"
        discovery, prd, intake_summary = build_guided_intake_artifacts(
            task_text="Install telegram-mcp-server.",
            success_answer="C",
            failure_answer="B",
            safety_answer="A",
            workspace_answer="B",
            artifact_output_path=output_path,
            iteration_budget=5,
        )
        self.assertEqual(discovery.workspace_strategy, "branch")
        self.assertEqual(discovery.artifact_output_path, output_path)
        self.assertEqual(prd.workspace_strategy, "branch")
        self.assertIn("produce an approved plan", discovery.interpreted_goal.lower())
        self.assertIn("recommendation", discovery.desired_end_state.lower())
        self.assertIn("reviewable plan", " ".join(prd.in_scope).lower())
        self.assertIn("minimal", " ".join(prd.user_values).lower())
        self.assertIn("do not skip moderator intake", " ".join(prd.non_negotiable_approval_gates).lower())
        self.assertIn(output_path, prd.success_criteria[-1])
        self.assertEqual(intake_summary["moderator_confidence"], "high")
        self.assertNotIn("outcome_answer", intake_summary)

    def test_guided_intake_artifacts_build_from_custom_answers(self) -> None:
        discovery, prd, intake_summary = build_guided_intake_artifacts(
            task_text="Install telegram-mcp-server.",
            success_answer="The checklist is approved; The output file exists",
            failure_answer="Do not touch unrelated repos",
            safety_answer="Pause before any networked mutation",
            workspace_answer="use a worktree",
            artifact_output_path="/tmp/planloop-custom-plan.md",
            iteration_budget=4,
        )
        self.assertEqual(discovery.workspace_strategy, "worktree")
        self.assertEqual(prd.iteration_budget, 4)
        self.assertEqual(intake_summary["moderator_confidence"], "medium")
        self.assertIn("approved plan", discovery.interpreted_goal.lower())
        self.assertIn("output file exists", " ".join(discovery.success_signals).lower())
        self.assertIn("Pause before any networked mutation", prd.safety_constraints)

    def test_next_handoff_starts_with_guided_moderator_intake(self) -> None:
        run_root = make_run_root()
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        handoff = loop.next_handoff()
        self.assertEqual(handoff["phase"], "intake")
        self.assertEqual(handoff["stage_label"], "Clarify")
        self.assertEqual(handoff["actor"], "moderator")
        self.assertEqual(handoff["required_record"], "discovery_packet")
        self.assertIn("Ask these questions", handoff["prompt"])
        self.assertIn("degraded single-thread mode", handoff["prompt"])
        self.assertIn("The outcome is implicit: produce a plan.", handoff["prompt"])
        self.assertNotIn("Why this matters", handoff["prompt"])
        self.assertNotIn("Outcome", handoff["prompt"])
        self.assertIn("artifact_output_path", handoff["missing_fields"])
        self.assertIn("-m planloop.cli record", handoff["record_command_template"])

    def test_guided_intake_questions_use_four_field_contract(self) -> None:
        questions = guided_intake_questions()
        self.assertEqual([question["id"] for question in questions], ["success", "failure", "safety", "workspace"])
        self.assertEqual(len(questions), 4)
        prompt = render_guided_intake_prompt("Install telegram-mcp-server.")
        self.assertIn("Ask at most 4 short questions.", prompt)
        self.assertIn("degraded single-thread mode", prompt)
        self.assertNotIn("Why this matters", prompt)
        self.assertNotIn("Outcome", prompt)

    def test_happy_path_writes_final_plan_document(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root)
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="approve", iteration_count=1)))
        loop.record_moderator_review(ModeratorReview.from_dict(moderator_review(decision="approve", iteration_count=1)))
        self.assertEqual(loop.state.phase, "succeeded")
        self.assertTrue(Path(output_path).exists())
        self.assertIn("Approved PRD Summary", Path(output_path).read_text(encoding="utf-8"))

    def test_critic_revision_bumps_iteration_and_exhausts_at_cap(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root)
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path, iteration_budget=2)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path, iteration_budget=2)))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="revise", iteration_count=1)))
        self.assertEqual(loop.state.phase, "planning")
        self.assertEqual(loop.state.iteration, 2)
        handoff = loop.next_handoff()
        self.assertEqual(handoff["actor"], "planner")
        self.assertIn("What exact command proves the install worked?", handoff["prompt"])
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="revise", iteration_count=2)))
        self.assertEqual(loop.state.phase, "exhausted")
        self.assertEqual(loop.state.status, "exhausted")

    def test_moderator_reject_requires_prd_revision(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root)
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="approve", iteration_count=1)))
        loop.record_moderator_review(ModeratorReview.from_dict(moderator_review(decision="reject", iteration_count=1)))
        self.assertEqual(loop.state.phase, "prd_revision")
        self.assertEqual(loop.state.iteration, 2)

    def test_cannot_approve_while_output_path_is_pending(self) -> None:
        run_root = make_run_root()
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict()))
        loop.record_prd(PRD.from_dict(prd_dict(output_path="Path pending user answer")))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path="Path pending user answer")))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="approve", iteration_count=1)))
        handoff = loop.next_handoff()
        self.assertEqual(handoff["phase"], "moderator_review")
        self.assertIn("artifact_output_path is still pending user answer", handoff["blocking_conditions"])
        review_path = Path(loop.state.artifact_paths["moderator_review"])
        with self.assertRaises(ValidationError):
            loop.record_moderator_review(ModeratorReview.from_dict(moderator_review(decision="approve", iteration_count=1)))
        self.assertFalse(review_path.exists())
        self.assertEqual(loop.state.phase, "moderator_review")

    def test_auto_finish_reuses_the_same_prd_synthesis_as_guided_intake(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "parity-plan.md")
        discovery, direct_prd, _ = build_guided_intake_artifacts(
            task_text="Install telegram-mcp-server.",
            success_answer="The checklist is approved; The output file exists",
            failure_answer="Do not touch unrelated repos",
            safety_answer="Pause before any networked mutation",
            workspace_answer="use a worktree",
            artifact_output_path=output_path,
            iteration_budget=4,
        )
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(discovery)
        payload = loop.auto_finish()
        recorded_prd = PRD.from_dict(json.loads(Path(loop.state.artifact_paths["prd"]).read_text(encoding="utf-8")))
        self.assertEqual(recorded_prd.to_dict(), direct_prd.to_dict())
        self.assertTrue(payload["final_plan_exists"])

    def test_plan_path_and_prd_path_must_match(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root)
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        bad_plan = plan_dict(output_path=make_output_path(run_root, "different.md"))
        with self.assertRaises(ValidationError):
            loop.record_plan_packet(PlanPacket.from_dict(bad_plan))

    def test_next_handoff_reports_terminal_success(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root)
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="approve", iteration_count=1)))
        loop.record_moderator_review(ModeratorReview.from_dict(moderator_review(decision="approve", iteration_count=1)))
        handoff = loop.next_handoff()
        self.assertEqual(handoff["phase"], "succeeded")
        self.assertEqual(handoff["stage_label"], "Complete")
        self.assertIsNone(handoff["actor"])
        self.assertIsNone(handoff["required_record"])
        self.assertIn(output_path, handoff["prompt"])

    def test_auto_finish_completes_from_planning(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "auto-finish-plan.md")
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        payload = loop.auto_finish()
        self.assertEqual(loop.state.phase, "succeeded")
        self.assertTrue(payload["final_plan_exists"])
        self.assertEqual(payload["generated_artifacts"], ["plan_packet", "critic_report", "moderator_review"])
        self.assertTrue(Path(output_path).exists())

    def test_balanced_critic_mode_is_more_permissive_than_adversarial(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "borderline-plan.md")
        prd = PRD.from_dict(prd_dict(output_path=output_path))
        plan = PlanPacket.from_dict(borderline_plan_dict(output_path=output_path))
        balanced = synthesize_critic_report(
            prd=prd,
            plan=plan,
            iteration_count=1,
            critic_mode="balanced",
        )
        adversarial = synthesize_critic_report(
            prd=prd,
            plan=plan,
            iteration_count=1,
            critic_mode="adversarial",
        )
        self.assertEqual(balanced.decision, "approve")
        self.assertEqual(adversarial.decision, "revise")
        self.assertIn("final output path", " ".join(adversarial.missing_evidence))

    def test_verify_completion_requires_explicit_approvals(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "verify-plan.md")
        loop = ModeratedPrdLoop.create(task_text="Install telegram-mcp-server.", run_root=run_root)
        loop.record_discovery_packet(DiscoveryPacket.from_dict(discovery_dict(output_path=output_path)))
        loop.record_prd(PRD.from_dict(prd_dict(output_path=output_path)))
        loop.record_plan_packet(PlanPacket.from_dict(plan_dict(output_path=output_path)))
        loop.record_critic_report(CriticReport.from_dict(critic_report(decision="approve", iteration_count=1)))
        loop.record_moderator_review(ModeratorReview.from_dict(moderator_review(decision="approve", iteration_count=1)))
        completion = loop.verify_completion()
        self.assertTrue(completion["ok"])
        self.assertNotIn("critic_approval", completion["missing_conditions"])
        self.assertNotIn("moderator_approval", completion["missing_conditions"])

    def test_run_command_interactive_creates_discovery_and_prd(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "interactive-plan.md")
        cmd = [
            str(ROOT / "scripts" / "planloop"),
            "run",
            "--task-text",
            "Install telegram-mcp-server.",
            "--run-root",
            str(run_root),
            "--json",
        ]
        user_input = "\n".join(["C", "B", "A", "B", output_path]) + "\n"
        proc = subprocess.run(cmd, input=user_input, text=True, capture_output=True, check=False, env=cli_env())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["result_type"], "interactive_run")
        self.assertEqual(payload["critic_mode"], "adversarial")
        self.assertEqual(payload["state"]["critic_mode"], "adversarial")
        self.assertEqual(payload["state"]["phase"], "planning")
        self.assertEqual(payload["next_handoff"]["stage_label"], "Draft Plan")
        self.assertTrue(Path(payload["state"]["artifact_paths"]["discovery_packet"]).exists())
        self.assertTrue(Path(payload["state"]["artifact_paths"]["prd"]).exists())
        self.assertNotIn("outcome_answer", payload["intake_summary"])

    def test_run_command_accepts_balanced_critic_mode(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "interactive-balanced-plan.md")
        cmd = [
            str(ROOT / "scripts" / "planloop"),
            "run",
            "--task-text",
            "Install telegram-mcp-server.",
            "--run-root",
            str(run_root),
            "--critic-mode",
            "balanced",
            "--json",
        ]
        user_input = "\n".join(["B", "B", "A", "B", output_path]) + "\n"
        proc = subprocess.run(cmd, input=user_input, text=True, capture_output=True, check=False, env=cli_env())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["critic_mode"], "balanced")
        self.assertEqual(payload["state"]["critic_mode"], "balanced")
        self.assertEqual(payload["next_handoff"]["critic_mode"], "balanced")

    def test_run_command_auto_finish_writes_final_plan(self) -> None:
        run_root = make_run_root()
        output_path = make_output_path(run_root, "interactive-auto-plan.md")
        cmd = [
            str(ROOT / "scripts" / "planloop"),
            "run",
            "--task-text",
            "Install telegram-mcp-server.",
            "--run-root",
            str(run_root),
            "--auto-finish",
            "--json",
        ]
        user_input = "\n".join(["B", "C", "A", "B", output_path]) + "\n"
        proc = subprocess.run(cmd, input=user_input, text=True, capture_output=True, check=False, env=cli_env())
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["auto_finish"])
        self.assertEqual(payload["state"]["phase"], "succeeded")
        self.assertTrue(payload["final_plan_exists"])
        self.assertIn("moderator_review", payload["generated_artifacts"])
        self.assertTrue(Path(output_path).exists())


if __name__ == "__main__":
    unittest.main()
