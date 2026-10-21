"""tools/validate_skill_bundle.py: the maintenance check of hep-computing's task-authoring files (moved out of the
skill with the example-authoring tools)."""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "validate_skill_bundle.py"


class BundleInPluginTests(unittest.TestCase):
    def test_validator_passes_on_the_plugin_layout(self) -> None:
        proc = subprocess.run([sys.executable, str(TOOL)],
                              capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Bundle OK", proc.stdout)

    def test_help_prints_usage_without_validating(self) -> None:
        proc = subprocess.run([sys.executable, str(TOOL), "--help"],
                              capture_output=True, text=True, timeout=600)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("usage:", proc.stdout)
        self.assertNotIn("Bundle OK", proc.stdout)


class DescriptionLimitTests(unittest.TestCase):
    """T01: a folded block description was read as its first line only and passed the 1,024-character limit."""

    def problems_with_description(self, desc_lines: str) -> list[str]:
        spec = importlib.util.spec_from_file_location("validate_skill_bundle_t01", TOOL)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as td:
            copy = Path(td) / "hep-computing"
            shutil.copytree(mod.ROOT, copy, ignore=shutil.ignore_patterns("__pycache__"))
            skill = copy / "SKILL.md"
            text = re.sub(r"^description:.*$", lambda _m: desc_lines, skill.read_text(encoding="utf-8"), count=1,
                          flags=re.M)
            skill.write_text(text, encoding="utf-8")
            return mod.problems_of(copy)

    def test_folded_description_over_the_limit_is_a_problem(self):
        long = " ".join(["word"] * 400)  # 1,999 characters
        problems = self.problems_with_description(f"description: >-\n  {long[:1000]}\n  {long[1000:]}")
        self.assertTrue(any("description is" in p and "limit is 1024" in p for p in problems), problems)

    def test_short_folded_description_passes(self):
        self.assertEqual(self.problems_with_description("description: >-\n  Use when a short\n  folded text."), [])


if __name__ == "__main__":
    unittest.main()
