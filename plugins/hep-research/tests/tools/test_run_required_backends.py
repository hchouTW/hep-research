"""tools/run_required_backends.py --no-skips: a module whose skips are unverified evidence (here the slow-tier
published-table tests run without HEP_SLOW_TESTS) passes without the flag, since no skip names a required backend,
and fails with it; the report lists every skipped test. --allow-skip-reason: a skip meant for the backend's absence
is allowed, any other skip naming the backend still fails."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "run_required_backends.py"
MODULE = "tests.core.test_published_tables"


def run(*extra, module=MODULE):
    env = {k: v for k, v in os.environ.items() if k != "HEP_SLOW_TESTS"}
    proc = subprocess.run([sys.executable, str(TOOL), "--require", "json", "--modules", module, *extra], cwd=ROOT,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc.returncode, json.loads(proc.stdout)


class NoSkipsTests(unittest.TestCase):
    def test_skips_pass_unless_no_skips_is_given(self):
        code, report = run()
        self.assertEqual(code, 0, report)
        self.assertGreater(report["skipped"], 0)
        self.assertNotIn("skipped_tests", report)
        code, report = run("--no-skips")
        self.assertEqual(code, 1, report)
        self.assertFalse(report["ok"])
        self.assertEqual(len(report["skipped_tests"]), report["skipped"])
        self.assertTrue(all("HEP_SLOW_TESTS" in s for s in report["skipped_tests"]), report["skipped_tests"])


class AllowSkipReasonTests(unittest.TestCase):
    FIXTURE = "tests.tools.required_backend_fixture"

    def test_only_the_allowed_reason_is_excused(self):
        code, report = run(module=self.FIXTURE)
        self.assertEqual((code, len(report["skipped_for_a_required_backend"])), (1, 2), report)
        code, report = run("--allow-skip-reason", "only meaningful when json is not installed", module=self.FIXTURE)
        self.assertEqual(code, 1, report)
        self.assertEqual([s.split(": ")[0].rsplit(".", 1)[-1] for s in report["skipped_for_a_required_backend"]],
                         ["test_needs_the_backend"])
        self.assertEqual(len(report["skips_allowed_by_reason"]), 1)
        code, report = run("--allow-skip-reason", "only meaningful when json is not installed",
                           "--allow-skip-reason", "json not installed", module=self.FIXTURE)
        self.assertEqual((code, report["ok"]), (0, True), report)

class VersionMatchTests(unittest.TestCase):
    def test_a_requirement_without_a_local_label_ignores_the_installed_label(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from run_required_backends import version_matches
        for installed, required, want in (("2.14.1+cpu", "2.14.1", True), ("2.14.1", "2.14.1", True),
                                          ("2.14.1+cpu", "2.14.1+cpu", True), ("2.14.1", "2.14.1+cpu", False),
                                          ("2.14.1+cu124", "2.14.1+cpu", False), ("2.14.10", "2.14.1", False),
                                          ("2.14.1.post1", "2.14.1", False), (None, "2.14.1", False)):
            with self.subTest(installed=installed, required=required):
                self.assertEqual(version_matches(installed, required), want)

if __name__ == "__main__":
    unittest.main()
