"""CLI and classification regressions for skills/hep-measurement/scripts/review_analysis_change.py (synthetic changes)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-measurement" / "scripts" / "review_analysis_change.py"
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


def change(**kw):
    base = {"id": "c", "parameter": "cut", "old": 1, "new": 2, "motivation": "new calibration from the control sample",
            "evidence": dict(CONTROL), "looked_at": ["control-region data"]}
    base.update(kw)
    return base


class EvasionTests(unittest.TestCase):
    """ANA-P2-8: the four documented evasions (audit appendix) and variants no longer pass."""

    def decide(self, c):
        return rac.review(c)["decision"]

    def test_prominent_bump(self):
        for text in ("tighten cut to make the bump more prominent", "loosen the cut so the peak looks more significant",
                     "make the excess more visible"):
            with self.subTest(text=text):
                self.assertIn(self.decide(change(motivation=text)), ("flag", "needs-human-review"))

    def test_sr_seen_in_motivation_despite_looked_at(self):
        c = change(motivation="after seeing SR mass peak shift we recalibrated", looked_at=["simulation"])
        self.assertEqual(self.decide(c), "flag")
        c = change(description="we noticed the signal region was low", looked_at=["simulation"])
        self.assertEqual(self.decide(c), "flag")

    def test_string_boolean_is_bad_input(self):
        c = change(evidence={"control_sample": "x", "independent_of_signal_region": "no"})
        with self.assertRaises(rac.BadExposure):
            rac.review(c)
        p = run_json({"changes": [c]})
        self.assertEqual(p.returncode, 2)
        with self.assertRaises(rac.BadExposure):
            rac.review(change(after_unblinding="yes"))

    def test_after_unblinding_with_unexposed_record(self):
        c = change(after_unblinding=True, looked_at=None,
                   data_exposure={"state": "unexposed", "basis": "structured-record", "record_ref": "r1"})
        out = rac.review(c)
        self.assertEqual(out["decision"], "flag")
        self.assertTrue(any("contradict" in r for r in out["reasons"]))

    def test_region_named_without_saying_what_was_seen_needs_review(self):
        out = run_json({"changes": [change(motivation="adjust the cut used in the signal region")]})
        self.assertEqual(out.returncode, 1)
        self.assertEqual(json.loads(out.stdout)["changes"][0]["decision"], "needs-human-review")

    def test_calibration_with_provenance_is_still_accepted(self):
        for text in ("new calibration from the Z peak in control-region data", "update energy scale from test beam"):
            with self.subTest(text=text):
                self.assertEqual(self.decide(change(motivation=text)), "accept")


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
        self.assertEqual(proc.returncode, 1, proc.stdout)       # F-05: every non-accept verdict exits 1 (was 0)
        out = json.loads(proc.stdout)
        self.assertEqual((out["flagged"], out["exposure_unknown"]), (0, 1))


class NonAcceptVerdictsAndUnjudgedText(unittest.TestCase):
    """F-05: every non-accept verdict exits 1, and text the English-only patterns cannot read is needs-human-review.
    Before the fix a tuning motivation written in Chinese, with a control sample recorded, was judged accept (exit 0),
    and needs-provenance and exposure-unknown exited 0."""

    STRUCTURED = {"state": "unexposed", "basis": "structured-record", "record_ref": "exposure.json#1"}

    def test_chinese_tuning_motivation_is_not_accepted(self):
        for text in ("為了讓訊號區的超出更顯著，把能量刻度調高 2%", "为了让信号区的超出更显著，调整了能量刻度"):
            with self.subTest(text=text):
                c = change(motivation=text, data_exposure=dict(self.STRUCTURED))
                row = rac.review(c)
                self.assertEqual(row["decision"], "needs-human-review", row)
                self.assertTrue(any("cannot read" in r for r in row["reasons"]), row)
                p = run_json({"changes": [c]})
                self.assertEqual(p.returncode, 1, p.stdout)

    def test_every_non_accept_verdict_exits_1(self):
        cases = {"needs-provenance": change(evidence={}),
                 "exposure-unknown": change(looked_at=["full data"])}
        for decision, c in cases.items():
            with self.subTest(decision=decision):
                self.assertEqual(rac.review(c)["decision"], decision)
                p = run_json({"changes": [c]})
                self.assertEqual(p.returncode, 1, p.stdout)
        p = run_json({"changes": [change()]})
        self.assertEqual(json.loads(p.stdout)["changes"][0]["decision"], "accept")
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_accented_latin_text_is_still_read(self):
        self.assertEqual(rac.review(change(motivation="new calibration from the control sample (naïve fit replaced)"))
                         ["decision"], "accept")


if __name__ == "__main__":
    unittest.main()
