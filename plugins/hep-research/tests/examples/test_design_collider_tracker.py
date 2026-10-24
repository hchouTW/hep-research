"""Example B (detector system design spec, M3; examples/design-collider-tracker): a SYNTHETIC collider tracking and
ECAL design study bound to the illustrative synthetic-collider profile (EXB-01). Reproduction of the committed results
and every pre-declared criterion: the probe fails resolution, the reasonable candidates are inconclusive on resolution
and ECAL resolution, and the hadronic resolution, trigger efficiency, pileup robustness and shower containment are
capability.unavailable, listed in the report and in the agent-prepared H3 record (EXB-02)."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "examples" / "design-collider-tracker" / "run.py"


class DesignColliderTracker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("design_collider_tracker_run", SCRIPT)
        cls.mod = importlib.util.module_from_spec(spec)
        sys.modules["design_collider_tracker_run"] = cls.mod
        spec.loader.exec_module(cls.mod)
        cls.tmp = tempfile.TemporaryDirectory()
        with contextlib.redirect_stdout(io.StringIO()):
            cls.code = cls.mod.main(["--out", cls.tmp.name])
        cls.out = Path(cls.tmp.name)
        cls.r = json.loads((cls.out / "results.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_criteria_pass(self):
        self.assertEqual(self.code, 0, self.r["pass"])
        self.assertTrue(all(self.r["pass"].values()), self.r["pass"])

    def test_reproduces_committed_output(self):
        committed = (SCRIPT.parent / "output" / "results.json").read_bytes()
        self.assertEqual((self.out / "results.json").read_bytes(), committed)

    def test_unavailable_are_listed_in_the_report(self):
        md = (self.out / "artifacts" / "reports" / "design-report.md").read_text(encoding="utf-8")
        for code in ("hadronic-energy-resolution", "trigger-efficiency", "pileup-robustness", "shower-containment"):
            self.assertIn(code, json.dumps(self.r["unavailable"]) + md)
        self.assertIn("capability.unavailable", md)

    def test_dispositions_only_for_candidates_entering_convergence(self):
        """RPT-05, MAT-04 (d): a screened-out candidate gets no proposed disposition and a derived requirement's is
        approved under the driving requirement that covers it; different magnet and ECAL hardware does not cancel in
        the equal-mass basis (ART-15)."""
        md = (self.out / "artifacts" / "reports" / "design-report.md").read_text(encoding="utf-8")
        ecal_p = next(x for x in md.splitlines() if "REQ-ECAL-001" in x and "cand-P" in x and x.startswith("|"))
        self.assertTrue(ecal_p.endswith("| none: the candidate is screened out |"), ecal_p)
        self.assertNotIn("next-study", ecal_p)
        derived = [x for x in md.splitlines() if x.startswith("|") and "(derived, under " in x and "inconclusive" in x]
        self.assertEqual(len(derived), 12)  # four derived requirements x three candidates
        for x in derived:  # MAT-04 d (3.12.0): approved at H4 under the driving requirement that covers it
            parent = x.split("(derived, under ", 1)[1].split(")", 1)[0]
            note = "none: the candidate is screened out" if "cand-P" in x else f"accept-risk (under {parent})"
            self.assertTrue(x.endswith(f"| {note} |"), x)
        self.assertIn("no item is the same subsystem with the same budget row", md)  # ART-15: different hardware
        self.assertIn("comparison basis on mass-budget at 95% one-sided CL: does not hold", md)
        self.assertIn("- orphan runs: none", md)

    def test_the_h3_record_is_prepared_not_approved(self):
        rec = json.loads((self.out / "decisions" / "h3-prepared.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["actor"]["kind"], "agent")
        self.assertIn("gate.H3_missing", self.r["gate_flags"])  # DEC-05: only a human record clears it


if __name__ == "__main__":
    unittest.main()
