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


class GuideWordingTests(unittest.TestCase):
    def test_entry_point_does_not_equate_unchanged_yields_with_failure(self):
        guide = (PLUGIN / "skills/hep-analysis/references/hep-analysis-guide.md").read_text(encoding="utf-8")
        self.assertNotIn("identical yields mean the variation did not propagate", guide)
        self.assertIn("An unchanged integrated yield does not show the variation failed to propagate", guide)
        skill = (PLUGIN / "skills/hep-analysis/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("An unchanged integrated yield does not show the systematic was not propagated", skill)


if __name__ == "__main__":
    unittest.main()
