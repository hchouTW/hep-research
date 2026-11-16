"""The phase-4 gate harness (tests/core/calibration_phase4_gates.py): its judging rule on recorded outcomes."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase4_gates as G  # noqa: E402


class Judge(unittest.TestCase):
    KINDS = {"m.C.test_neg": "negative", "m.C.test_pos": "positive"}

    def test_all_passing_passes_and_marks_negatives_caught(self):
        j = G.judge_tests("x", "p", self.KINDS, {"m.C.test_neg": {"outcome": "passed"},
                                                  "m.C.test_pos": {"outcome": "passed"}})
        self.assertTrue(j["passed"])
        self.assertEqual({r["test"]: r["status"] for r in j["tests"]}, {"m.C.test_neg": "caught", "m.C.test_pos": "passed"})

    def test_a_failure_a_skip_or_a_test_not_run_fails(self):
        for outs in ({"m.C.test_neg": {"outcome": "failed"}, "m.C.test_pos": {"outcome": "passed"}},
                     {"m.C.test_neg": {"outcome": "skipped"}, "m.C.test_pos": {"outcome": "passed"}},
                     {"m.C.test_pos": {"outcome": "passed"}}):
            with self.subTest(outs=sorted(outs)):
                self.assertFalse(G.judge_tests("x", "p", self.KINDS, outs)["passed"])

    def test_the_table_names_every_section_15_3_19_case(self):
        """Review F9: the case table is complete and every mapped test name loads (a renamed test would otherwise
        surface only as a gate failure)."""
        self.assertEqual(len(G.CASES), 19)
        self.assertTrue(all(ids for _, ids in G.CASES))
        loader = unittest.TestLoader()
        names = [t for _, ids in G.CASES for t in ids] + list(G.CONTRIB["tests"]) + list(G.GENERIC["tests"])
        for name in names:
            with self.subTest(name=name):
                self.assertGreater(loader.loadTestsFromName(name).countTestCases(), 0)


if __name__ == "__main__":
    unittest.main()
