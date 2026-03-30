#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install-claude-skill"
SOURCE = ROOT / "skills" / "planloop"


class ClaudeInstallScriptTests(unittest.TestCase):
    def test_personal_install_creates_expected_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="planloop-home-") as home_dir:
            env = dict(os.environ)
            env["HOME"] = home_dir
            result = subprocess.run(
                [str(SCRIPT), "--personal"],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            dest = Path(home_dir) / ".claude" / "skills" / "planloop"
            self.assertTrue(dest.is_symlink())
            self.assertEqual(dest.resolve(), SOURCE.resolve())
            self.assertIn("Installed planloop", result.stdout)

    def test_project_install_creates_expected_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="planloop-project-") as project_dir:
            result = subprocess.run(
                [str(SCRIPT), "--project", project_dir],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            dest = Path(project_dir) / ".claude" / "skills" / "planloop"
            self.assertTrue(dest.is_symlink())
            self.assertEqual(dest.resolve(), SOURCE.resolve())
            self.assertIn("Installed planloop", result.stdout)

    def test_personal_install_is_idempotent_for_existing_matching_symlink(self) -> None:
        with tempfile.TemporaryDirectory(prefix="planloop-home-") as home_dir:
            env = dict(os.environ)
            env["HOME"] = home_dir
            subprocess.run(
                [str(SCRIPT), "--personal"],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            second = subprocess.run(
                [str(SCRIPT), "--personal"],
                cwd=ROOT,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("Already installed", second.stdout)


if __name__ == "__main__":
    unittest.main()
