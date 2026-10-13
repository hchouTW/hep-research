"""T12 regression: an unchanged systematic integral with a changed shape is a shape effect, not a propagation failure.

Uses the JSON input path of skills/hep-analysis/scripts/check_systematic_variations.py (no PyROOT needed).
Histogram contents below are synthetic.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN / "skills" / "hep-analysis" / "scripts"))
import check_systematic_variations as csv_  # noqa: E402

NOMINAL = [100.0, 200.0, 300.0, 200.0, 100.0]
SHIFTED = [90.0, 190.0, 300.0, 215.0, 105.0]  # same integral (900), events migrate to higher bins
SCALED = [x * 1.05 for x in NOMINAL]


class ClassifyTests(unittest.TestCase):
    def test_T12_unchanged_integral_changed_shape_is_shape_effect(self):
        r = csv_.classify_variation(NOMINAL, SHIFTED)
        self.assertEqual(r["effect"], "shape")
        self.assertAlmostEqual(r["integral_rel_change"], 0.0, places=12)
        self.assertAlmostEqual(r["migration_fraction"], 20.0 / 900.0, places=12)
        self.assertIn("NOT a propagation failure", r["note"])

    def test_T12_assess_does_not_warn_about_propagation_for_shape_only(self):
        down = [110.0, 210.0, 300.0, 185.0, 95.0]
        out = csv_.assess(NOMINAL, SHIFTED, down)
        self.assertEqual((out["up"]["effect"], out["down"]["effect"]), ("shape", "shape"))
        self.assertFalse(any("propagation" in w for w in out["warnings"]))
        self.assertIn("not assessed", out["sensitivity"])

    def test_normalization_and_mixed(self):
        self.assertEqual(csv_.classify_variation(NOMINAL, SCALED)["effect"], "normalization")
        self.assertEqual(csv_.classify_variation(NOMINAL, [x * 1.05 for x in SHIFTED])["effect"], "mixed")
        self.assertAlmostEqual(csv_.classify_variation(NOMINAL, SCALED)["migration_fraction"], 0.0, places=12)

    def test_identical_histogram_asks_to_confirm_not_to_conclude(self):
        out = csv_.assess(NOMINAL, list(NOMINAL), list(NOMINAL))
        self.assertEqual(out["up"]["effect"], "none")
        self.assertTrue(any("confirm propagation" in w for w in out["warnings"]))
        self.assertIn("negligible effect can be genuine", out["up"]["note"])

    def test_same_direction_variations_are_flagged(self):
        out = csv_.assess(NOMINAL, SCALED, [x * 1.02 for x in NOMINAL])
        self.assertTrue(any("same direction" in w for w in out["warnings"]))

    def test_mismatched_bins_rejected(self):
        with self.assertRaises(ValueError):
            csv_.classify_variation(NOMINAL, NOMINAL[:-1])

    def test_cli_json_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "h.json"
            f.write_text(json.dumps({"nominal": NOMINAL, "up": SHIFTED, "down": SCALED}))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(csv_.main(["--json", str(f), "--format", "json"]), 0)
            out = json.loads(buf.getvalue())
            self.assertEqual(out["up"]["effect"], "shape")
            self.assertEqual(out["down"]["effect"], "normalization")


class PropagationBehaviourTests(unittest.TestCase):
    """P4-1: the invariant 'an unchanged integrated yield does not show the systematic was not propagated', as behaviour
    (it replaces a test of the guide's wording)."""

    def test_unchanged_integral_is_never_reported_as_not_propagated(self):
        out = csv_.assess(NOMINAL, SHIFTED, [110.0, 210.0, 300.0, 185.0, 95.0])
        for label in ("up", "down"):
            self.assertAlmostEqual(out[label]["integral_rel_change"], 0.0, places=12)
            self.assertNotEqual(out[label]["effect"], "none")
            self.assertNotIn("confirm", out[label]["note"])

    def test_only_a_histogram_unchanged_in_every_bin_asks_to_confirm_propagation(self):
        out = csv_.assess(NOMINAL, list(NOMINAL), list(NOMINAL))
        self.assertFalse(out["up"]["bins_changed"])
        self.assertTrue(any("confirm propagation" in w for w in out["warnings"]))


if __name__ == "__main__":
    unittest.main()
