#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PlanloopSkillPackageTests(unittest.TestCase):
    def test_planloop_skill_exists(self) -> None:
        self.assertTrue((ROOT / "skills" / "planloop" / "SKILL.md").exists())
        self.assertTrue((ROOT / "skills" / "planloop" / "agents" / "openai.yaml").exists())

    def test_public_files_have_no_machine_specific_absolute_paths(self) -> None:
        bad_tokens = ["/Users/", "~/.agents/", "python3 /Users/"]
        for rel in [
            "README.md",
            "docs/usage.md",
            "docs/benchmark.md",
            "examples/demo.md",
            "examples/final-plan.md",
            "skills/planloop/SKILL.md",
            "skills/planloop/agents/openai.yaml",
            "skills/planloop/references/moderator_discovery.md",
            "skills/planloop/references/prd_template.md",
            "skills/planloop/references/packet_templates.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for token in bad_tokens:
                self.assertNotIn(token, text, f"{rel} leaked machine-specific token {token}")

    def test_planloop_metadata_uses_public_name(self) -> None:
        skill_text = (ROOT / "skills" / "planloop" / "SKILL.md").read_text(encoding="utf-8")
        yaml_text = (ROOT / "skills" / "planloop" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("name: planloop", skill_text)
        self.assertIn("$planloop", skill_text)
        self.assertIn('display_name: "Planloop"', yaml_text)
        self.assertIn("$planloop", yaml_text)
        self.assertIn("one short bundled intake block", yaml_text)
        self.assertIn("The outcome is implicit", yaml_text)

    def test_planloop_skill_hard_gates_the_first_response(self) -> None:
        skill_text = (ROOT / "skills" / "planloop" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## First-Response Rule", skill_text)
        self.assertIn("the first response should contain the intake questions only", skill_text)
        self.assertIn("load [references/moderator_discovery.md]", skill_text)
        self.assertIn("Workspace` and `Artifact Output Path` in the same intake turn", skill_text)
        self.assertIn("single bundled 4-question intake block", skill_text)
        self.assertIn("do not treat that as permission to skip intake", skill_text)
        self.assertIn("the outcome is implicit: `plan` is mandatory", skill_text)

    def test_readme_prefers_public_skill_install(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Use $skill-installer to install the skill from GitHub repo <owner>/<repo> path skills/planloop.", readme)
        self.assertIn("$planloop install telegram-mcp-server", readme)
        self.assertIn("~/.claude/skills/planloop", readme)
        self.assertIn("git clone https://github.com/yonghanjung/planloop.git", readme)
        self.assertIn('ln -s "$PWD/skills/planloop" ~/.claude/skills/planloop', readme)
        self.assertIn("/planloop install telegram-mcp-server", readme)
        self.assertIn("./scripts/planloop run", readme)
        self.assertIn("./scripts/planloop-benchmark score", readme)

    def test_usage_doc_matches_public_contract(self) -> None:
        doc_text = (ROOT / "docs" / "usage.md").read_text(encoding="utf-8")
        self.assertIn("Expected first-response behavior", doc_text)
        self.assertIn("do not jump straight to a plan or recommendation", doc_text)
        self.assertIn("one short bundled intake block", doc_text)
        self.assertIn("The outcome is implicit: `plan` is mandatory.", doc_text)
        self.assertIn("~/.claude/skills/planloop", doc_text)
        self.assertIn("git clone https://github.com/yonghanjung/planloop.git", doc_text)
        self.assertIn('ln -s "$PWD/skills/planloop" ~/.claude/skills/planloop', doc_text)
        self.assertIn("/planloop install telegram-mcp-server", doc_text)
        self.assertIn("./scripts/planloop run", doc_text)

    def test_benchmark_doc_has_coverage_interpretation(self) -> None:
        doc_text = (ROOT / "docs" / "benchmark.md").read_text(encoding="utf-8")
        self.assertIn("Coverage Interpretation", doc_text)
        self.assertIn("demo_only", doc_text)
        self.assertIn("official", doc_text)
        self.assertIn("drive / walk / postpone / alternative", doc_text)
        self.assertIn("./scripts/planloop-benchmark score", doc_text)

    def test_benchmark_fixture_contains_harder_conflicting_constraints_case(self) -> None:
        text = (ROOT / "benchmarks" / "cases" / "planloop-12.json").read_text(encoding="utf-8")
        self.assertIn('"id": "ops-003"', text)
        self.assertIn("car wash is 50 meters away", text)
        self.assertIn("job interview call in 12 minutes", text)
        self.assertIn("tow-away after 10 minutes", text)
        self.assertIn("35% chance of hail in 20 minutes", text)

    def test_demo_covers_all_four_intake_fields_in_one_block(self) -> None:
        demo = (ROOT / "examples" / "demo.md").read_text(encoding="utf-8")
        for field in [
            "1. Success",
            "2. Failure",
            "3. Safety and approvals",
            "4. Workspace and output",
        ]:
            self.assertIn(field, demo)
        self.assertIn("I’ll produce a plan. I just need four quick preferences first.", demo)
        self.assertIn("I have enough to freeze the discovery packet and PRD.", demo)
        self.assertNotIn("Why this matters:", demo)
        self.assertNotIn("1. Outcome", demo)

    def test_local_entrypoints_exist(self) -> None:
        self.assertTrue((ROOT / "pyproject.toml").exists())
        self.assertTrue((ROOT / "scripts" / "planloop").exists())
        self.assertTrue((ROOT / "scripts" / "planloop-benchmark").exists())
        self.assertTrue((ROOT / "src" / "planloop" / "__main__.py").exists())


if __name__ == "__main__":
    unittest.main()
