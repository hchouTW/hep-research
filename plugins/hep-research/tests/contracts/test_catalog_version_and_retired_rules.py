"""The effect catalog version 1.1.0 (description_required) and its compatibility rule, and the retirement of the
cross-artifact check (decision-retire.md): every new or changed rule in contracts/rules/registry.json is retired, and
no checker, suite or coverage contract is left to run them. Reproduce old reports with the last release that has the
check."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class CatalogVersion(unittest.TestCase):
    def test_catalog_1_1_0_requires_descriptions(self):
        import json
        cat = json.loads((ROOT / "contracts" / "vocab" / "effects.json").read_text())
        self.assertEqual(cat["catalog_version"], "1.1.0")
        self.assertEqual({e["effect_id"] for e in cat["effects"] if not e["description_required"]}, {"bin_width"})


class CheckRetired(unittest.TestCase):
    def test_every_new_or_changed_rule_is_retired(self):
        import json
        reg = json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text())
        for r in reg["rules"]:
            if r["kind"] != "legacy":
                with self.subTest(rule=f"{r['rule_id']}@{r['version']}"):
                    self.assertEqual(r["lifecycle"], "retired")

    def test_no_checker_suite_or_coverage_is_left(self):
        for rel in ("contracts/analysis_checks", "contracts/rules/suites", "contracts/semantics/coverage",
                    "contracts/migrate.py", "contracts/analysis_check.py"):
            with self.subTest(path=rel):
                self.assertFalse((ROOT / rel).exists())

    def test_retired_entry_points_are_removed(self):
        # 0.49.0 removed the refusing pointers: check-report and the two review flags are now unknown (usage, exit 2)
        import contextlib
        import io
        import subprocess
        from contracts import permit
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(permit.main(["check-report", "report.json"]), 2)
        self.assertIn("invalid choice", err.getvalue())
        script = ROOT / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py"
        for flag in ("--check-bundle", "--check-root"):
            with self.subTest(flag=flag):
                proc = subprocess.run([sys.executable, str(script), "spec.json", flag, "x"], capture_output=True,
                                      text=True, timeout=60)
                self.assertEqual(proc.returncode, 2)
                self.assertIn("unrecognized arguments", proc.stderr)


if __name__ == "__main__":
    unittest.main()
