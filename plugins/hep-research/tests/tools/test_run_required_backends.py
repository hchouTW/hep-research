"""tools/run_required_backends.py --no-skips: a module whose skips are unverified evidence (here the slow-tier
published-table tests run without HEP_SLOW_TESTS) passes without the flag, since no skip names a required backend,
and fails with it; the report lists every skipped test."""
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


def run(*extra):
    env = {k: v for k, v in os.environ.items() if k != "HEP_SLOW_TESTS"}
    proc = subprocess.run([sys.executable, str(TOOL), "--require", "json", "--modules", MODULE, *extra], cwd=ROOT,
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


if __name__ == "__main__":
    unittest.main()
