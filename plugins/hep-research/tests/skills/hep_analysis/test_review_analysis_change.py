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


class DataExposureTests(unittest.TestCase):
    """T4.4 / K06: a missing, string or unrecognized looked_at is unknown exposure, never unexposed."""

    def change(self, **kw):
        return dict({"id": "c", "parameter": "p", "motivation": "new calibration from the control sample", "evidence": CONTROL}, **kw)

    def test_missing_looked_at_is_unknown_not_accepted(self):
        r = rac.review(self.change())
        self.assertEqual(r["data_exposure"], {"state": "unknown", "basis": "none"})
        self.assertEqual(r["decision"], "exposure-unknown")

    def test_string_looked_at_is_not_read_as_unexposed(self):
        r = rac.review(self.change(looked_at="control-region data"))
        self.assertEqual(r["data_exposure"], {"state": "unknown", "basis": "legacy-text"})
        self.assertEqual(r["decision"], "exposure-unknown")
        r = rac.review(self.change(looked_at="signal-region data"))
        self.assertEqual((r["data_exposure"]["state"], r["decision"]), ("exposed", "flag"))

    def test_unrecognized_legacy_text_is_unknown(self):
        for entry in ("the plots", "everything in the notebook", "", 3):
            r = rac.review(self.change(looked_at=["simulation", entry]))
            self.assertEqual(r["data_exposure"]["state"], "unknown", entry)
            self.assertNotEqual(r["decision"], "accept", entry)

    def test_grammar_accepts_plain_control_entries(self):
        for entry in ("control-region data", "Control region events only", "validation sample", "sidebands",
                      "sideband (low mass) plots", "simulation", "MC samples", "Monte-Carlo distributions", "test beam data",
                      "cosmic-ray calibration runs", "calibration data"):
            self.assertTrue(rac.control_only(entry), entry)

    def test_recognized_legacy_text_is_unexposed(self):
        r = rac.review(self.change(looked_at=["control-region data", "simulation", "sideband (low mass)"]))
        self.assertEqual(r["data_exposure"], {"state": "unexposed", "basis": "legacy-text"})
        self.assertEqual(r["decision"], "accept")

    def test_empty_list_is_unknown(self):
        r = rac.review(self.change(looked_at=[]))
        self.assertEqual((r["data_exposure"]["state"], r["decision"]), ("unknown", "exposure-unknown"))

    def test_control_words_followed_by_signal_region_are_not_unexposed(self):
        for entry in ("control region, then signal region yields", "sideband and signal region events",
                      "simulation tuned to the signal region", "MC compared with SR counts",
                      "control region plus the signal window", "calibration after unblinding",
                      "control region and the full data spectrum", "simulation and data in the search region",
                      "Monte Carlo vs data, all bins", "control-region data; signal-region data",
                      "data-MC distributions", "data-MC plots", "data mc distributions", "Monte Carlo data plots",
                      "simulation data events", "MC (data)", "test data", "test sample", "test events",
                      "sidebands high mass region data", "calibration data high mass region", "high mass data",
                      "control region data simulation", "contr\u043el region data"):
            r = rac.review(self.change(looked_at=[entry]))
            self.assertNotEqual(r["data_exposure"]["state"], "unexposed", entry)
            self.assertNotEqual(r["decision"], "accept", entry)

    def test_structured_record_used_and_legacy_can_only_raise_it(self):
        rec = {"state": "unexposed", "basis": "structured-record", "record_ref": "exposure/c.json"}
        r = rac.review(self.change(data_exposure=rec))
        self.assertEqual((r["data_exposure"], r["decision"]), (rec, "accept"))
        r = rac.review(self.change(data_exposure=rec, looked_at=["unblinded result"]))
        self.assertEqual((r["data_exposure"]["state"], r["decision"]), ("exposed", "flag"))
        r = rac.review(self.change(data_exposure=dict(rec, state="exposed"), looked_at=["simulation"]))
        self.assertEqual(r["decision"], "flag")
        r = rac.review(self.change(data_exposure=dict(rec, state="incomplete")))
        self.assertEqual(r["decision"], "exposure-unknown")

    def test_malformed_structured_record_is_input_error(self):
        for bad in ({"state": "probably-not", "basis": "structured-record"}, {"state": "unexposed", "basis": "legacy-text"},
                    {"state": "unexposed"}, "unexposed", {"state": "unexposed", "basis": "structured-record", "x": 1}):
            with self.assertRaises(rac.BadExposure):
                rac.review(self.change(data_exposure=bad))
            proc = run_json({"changes": [self.change(data_exposure=bad)]})
            self.assertEqual(proc.returncode, 2, proc.stdout)
            self.assertIn("data_exposure", json.loads(proc.stdout)["error"])

    def test_cli_counts_unknown_exposure_without_flagging(self):
        proc = run_json({"changes": [self.change()]})
        self.assertEqual(proc.returncode, 0, proc.stdout)
        out = json.loads(proc.stdout)
        self.assertEqual((out["flagged"], out["exposure_unknown"]), (0, 1))


if __name__ == "__main__":
    unittest.main()
