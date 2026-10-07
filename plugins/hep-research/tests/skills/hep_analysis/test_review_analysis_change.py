"""CLI and classification regressions for skills/hep-analysis/scripts/review_analysis_change.py (synthetic changes)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-analysis" / "scripts" / "review_analysis_change.py"
sys.path.insert(0, str(SCRIPT.parent))
import review_analysis_change as rac  # noqa: E402

CONTROL = {"control_sample": "Z->ee control sample (synthetic)", "independent_of_signal_region": True}


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=600)


def run_json(doc):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "changes.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        return run(str(p))


class ReviewCliTests(unittest.TestCase):
    def test_help_exits_zero(self):
        proc = run("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Decision per change", proc.stdout)

    def test_wrong_arg_count_is_usage_error(self):
        self.assertEqual(run().returncode, 2)

    def test_changes_not_list_of_objects_is_input_error(self):
        for bad in (["x"], {"a": 1}, "text", [1, 2]):
            proc = run_json({"changes": bad})
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("list of objects", json.loads(proc.stdout)["error"])


class OutcomeMotiveTests(unittest.TestCase):
    def review(self, motivation, looked_at=("control-region data",)):
        return rac.review({"id": "c", "parameter": "p", "motivation": motivation, "evidence": CONTROL, "looked_at": list(looked_at)})

    def test_control_region_modelling_calibration_accepted(self):
        m = "new Z->ee calibration to improve signal-to-background modelling in the control region"
        self.assertEqual(self.review(m)["decision"], "accept")
        proc = run_json({"changes": [{"id": "c", "parameter": "p", "motivation": m, "evidence": CONTROL,
                                      "looked_at": ["control-region data"]}]})
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_outcome_driven_motives_still_flagged(self):
        for m in ("tighten the cut to increase the significance", "tighten to remove the excess",
                  "retune so that we improve the signal yield in the signal region",
                  "change the binning to reduce the tension with the prediction"):
            self.assertEqual(self.review(m)["decision"], "flag", m)


if __name__ == "__main__":
    unittest.main()
