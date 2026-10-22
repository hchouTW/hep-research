"""tools/run_required_backends.py --no-skips: a module whose skips are unverified evidence (here the slow-tier
published-table tests run without HEP_SLOW_TESTS) passes without the flag, since no skip names a required backend,
and fails with it; the report lists every skipped test. --allow-skip-reason: a skip meant for the backend's absence
is allowed, any other skip naming the backend still fails. --from-ledger: the ledger's oracle nodes run one by one and
each outcome is classified by the records' requires (environment error, unverified, does not hold, skipped)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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

class FromLedgerTests(unittest.TestCase):
    NODE = "tests/tools/ledger_backend_fixture.py::Fixture::"
    EXPECT = {"test_holds": ("pass", [], []), "test_needs_an_absent_core_dependency": (
        "environment-error", ["hep_fixture_absent_core"], []), "test_needs_an_absent_backend": (
        "unverified", [], ["hep_fixture_absent_backend"]), "test_does_not_hold": ("does-not-hold", [], []),
        "test_skips_for_the_slow_tier": ("skipped", [], []),
        "test_imports_an_undeclared_module": ("environment-error", [], [])}

    def run_ledger(self, methods, *extra):
        fixes = [{"id": f"E{i}", "independence": [{"kind": "analytic", "test": self.NODE + m, "basis": "locator",
                                                   "detail": "-", "requires": {"core": self.EXPECT[m][1],
                                                                               "backend": self.EXPECT[m][2]}}]}
                 for i, m in enumerate(methods)]
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ledger.json"
            ledger.write_text(json.dumps({"fixes": fixes}))
            proc = subprocess.run([sys.executable, str(TOOL), "--from-ledger", str(ledger), *extra], cwd=ROOT,
                                  capture_output=True, text=True, timeout=300)
        return proc.returncode, json.loads(proc.stdout)

    def test_each_outcome_is_classified_by_the_records_requires(self):
        code, report = self.run_ledger(list(self.EXPECT))
        self.assertEqual(code, 1, report)
        self.assertEqual({r["node"].rsplit("::", 1)[1]: r["class"] for r in report["node_results"]},
                         {m: e[0] for m, e in self.EXPECT.items()})
        self.assertEqual(report["classes"], {"pass": 1, "environment-error": 2, "unverified": 1, "does-not-hold": 1,
                                             "skipped": 1})
        self.assertEqual(report["modules"], ["tests.tools.ledger_backend_fixture"])
        self.assertEqual(report["modules_not_in_MODULES"], ["tests.tools.ledger_backend_fixture"])
        self.assertEqual(len(report["problems"]), 3, report["problems"])

    def test_unverified_and_skipped_fail_only_with_no_skips(self):
        for methods, extra, want in ((["test_holds"], (), 0), (["test_holds"], ("--no-skips",), 0),
                                     (["test_needs_an_absent_backend", "test_skips_for_the_slow_tier"], (), 0),
                                     (["test_needs_an_absent_backend"], ("--no-skips",), 1),
                                     (["test_skips_for_the_slow_tier"], ("--no-skips",), 1),
                                     (["test_needs_an_absent_backend"], ("--require", "hep_fixture_absent_backend"), 1),
                                     (["test_does_not_hold"], (), 1),
                                     (["test_needs_an_absent_core_dependency"], (), 1)):
            with self.subTest(methods=methods, extra=extra):
                code, report = self.run_ledger(methods, *extra)
                self.assertEqual((code, report["ok"]), (want, want == 0), report)

    def test_the_shipped_ledger_nodes_and_modules(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from run_required_backends import LEDGER, MODULES, ledger_nodes, node_module
        nodes = ledger_nodes(LEDGER)
        doc = json.loads(LEDGER.read_text(encoding="utf-8"))
        self.assertEqual(set(nodes), {r["test"] for f in doc["fixes"] for r in f.get("independence", [])})
        self.assertIn("tests.skills.hep_detector.test_hep_detector_audit", {node_module(n) for n in nodes} - set(MODULES))
        self.assertEqual(nodes["tests/core/test_constants.py::PdgPackageTests::test_bundled_masses_equal_the_package"]
                         ["backend"], ["pdg"])


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
