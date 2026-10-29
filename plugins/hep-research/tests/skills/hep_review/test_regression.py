"""hep-review regression suite (spec v9 T08): every committed pilot result is re-scored by its frozen driver from its
committed evidence and must reproduce the committed score exactly. A change to the scoring code, the kernel or the
evidence that would alter a published number fails here."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
DEV = ROOT / "docs" / "dev" / "hep-review"
for p in (ROOT, ROOT / "skills" / "hep-review" / "scripts", DEV / "pilot", DEV / "pilot" / "g2h", DEV / "pilot" / "g2x",
          DEV / "g3"):
    sys.path.insert(0, str(p))
sys.dont_write_bytecode = True

import run_pilot  # noqa: E402
import run_g2h  # noqa: E402
import run_g2x  # noqa: E402
import run_g3  # noqa: E402


def committed(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def roundtrip(d: dict) -> dict:
    return json.loads(json.dumps(d, sort_keys=True))


class PilotScores(unittest.TestCase):
    def test_g2_score_reproduces(self):
        e = DEV / "pilot" / "g2"
        out = run_pilot.cmd_score(SimpleNamespace(run=str(e), expected=str(e / "expected"),
                                                  grades=str(e / "grades" / "combined.json")))
        self.assertEqual(roundtrip(out), committed(e / "score.json"))

    def test_g2h_score_reproduces(self):
        e = DEV / "pilot" / "g2h" / "evidence"
        out = run_g2h.cmd_score(SimpleNamespace(run=str(e), expected=str(e / "expected"),
                                                grades=str(e / "grades" / "combined.json")))
        self.assertEqual(roundtrip(out), committed(e / "score.json"))

    def test_g2x_score_reproduces(self):
        e = DEV / "pilot" / "g2x" / "evidence"
        out = run_g2x.cmd_score(SimpleNamespace(run=str(e), gold=str(e / "published" / "gold"),
                                                combined=str(e / "grader-runs" / "combined.json")))
        self.assertEqual(roundtrip(out), committed(e / "score.json"))

    def test_g3_score_reproduces(self):
        e = DEV / "g3" / "evidence"
        out = run_g3.cmd_score(SimpleNamespace(run=str(e), gold=str(e / "published" / "gold"),
                                               combined=str(e / "grader-runs" / "combined.json")))
        self.assertEqual(roundtrip(out), committed(e / "score.json"))

    def test_g3_measured_rates_are_what_the_report_says(self):
        g3 = committed(DEV / "g3" / "evidence" / "score.json")
        detection = g3["measured"]["defect_detection"]["all"]
        self.assertEqual((detection["k"], detection["n"], detection["ci95"]), (71, 72, [0.925, 0.9996]))
        self.assertEqual(g3["measured"]["c02_false_alarm"]["k"], 0)
        self.assertEqual(g3["claim_decision"]["state"], "evaluated-scope")

    def test_published_gates_are_what_the_reports_say(self):
        g2 = committed(DEV / "pilot" / "g2" / "score.json")
        g2h = committed(DEV / "pilot" / "g2h" / "evidence" / "score.json")
        g2x = committed(DEV / "pilot" / "g2x" / "evidence" / "score.json")
        self.assertEqual((g2["engineering_gate"]["pass"], g2["scientific_gate"]["pass"]), (True, True))
        self.assertEqual((g2h["engineering_gate"]["pass"], g2h["scientific_gate"]["pass"]), (True, True))
        self.assertEqual((g2x["engineering_gate"]["pass"], g2x["scientific_gate"]["pass"]), (False, True))
        self.assertEqual(g2x["known_defect_level"], {"defect_trials": 39, "identified_with_valid_reason": 37,
                                                     "unadjudicated": 0})


if __name__ == "__main__":
    unittest.main()
