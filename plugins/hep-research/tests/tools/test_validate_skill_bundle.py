"""tools/validate_skill_bundle.py: the maintenance check of hep-computing's task-authoring files (moved out of the
skill with the example-authoring tools)."""
from __future__ import annotations

import subprocess
import sys
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


if __name__ == "__main__":
    unittest.main()
