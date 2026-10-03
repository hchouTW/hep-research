"""S03 verified walkthrough for skills/hep-statistics/references/nuisance-modeling.md: pyhf normsys code 1
(exponential) against code 4 (polynomial inside |alpha| < 1, exponential outside), and histosys code 0 against
code 4p, on adapters/pyhf-combine/assets/pyhf-counting.json (SYNTHETIC). Skips without pyhf (unverified)."""
import copy
import json
import math
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
COUNTING = PLUGIN / "adapters" / "pyhf-combine" / "assets" / "pyhf-counting.json"

try:
    import numpy as np
    import pyhf
    HAVE_PYHF = True
except ImportError:
    HAVE_PYHF = False

CODES = {"code4": ("code4", "code4p"), "code1": ("code1", "code0")}


def limit_and_yields(spec, code, alphas=(-1.5, -1.0, -0.5, 0.5, 1.0, 1.5), par="bkg_norm"):
    pyhf.set_backend("numpy", "scipy")
    normsys, histosys = CODES[code]
    ws = pyhf.Workspace(spec)
    model = ws.model(modifier_settings={"normsys": {"interpcode": normsys}, "histosys": {"interpcode": histosys}})
    data = ws.data(model)
    obs = pyhf.infer.intervals.upper_limits.toms748_scan(data, model, 0.5, 5.0, level=0.05, rtol=1e-6)[0]
    i = model.config.par_order.index(par)
    yields = []
    for a in alphas:
        p = model.config.suggested_init()
        p[i], p[model.config.poi_index] = a, 0.0
        yields.append(float(model.expected_actualdata(p)[0]))
    return float(obs), yields


@unittest.skipUnless(HAVE_PYHF, "pyhf not installed: interpolation walkthrough unverified")
class NormsysInterpolation(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(COUNTING.read_text(encoding="utf-8"))

    def test_symmetric_counting_card(self):
        lim4, y4 = limit_and_yields(self.spec, "code4")
        lim1, y1 = limit_and_yields(self.spec, "code1")
        self.assertAlmostEqual(lim4, 2.1529, delta=2e-4)      # the value recorded at M6
        self.assertAlmostEqual(lim1, 2.1541, delta=2e-4)
        # code 1 is exactly exponential: 20 * 1.1**a for a >= 0, 20 * 0.9**(-a) for a < 0
        for a, y in zip((-1.5, -1.0, -0.5, 0.5, 1.0, 1.5), y1):
            self.assertAlmostEqual(y, 20 * (1.1 ** a if a >= 0 else 0.9 ** (-a)), places=9)
        # code 4 equals code 1 at and beyond |a| = 1 and differs inside
        for k in (0, 1, 4, 5):
            self.assertAlmostEqual(y4[k], y1[k], places=9)
        self.assertAlmostEqual(y4[2], 18.9843, delta=1e-4)
        self.assertAlmostEqual(y4[3], 20.9863, delta=1e-4)

    def test_asymmetric_variation_changes_the_limit(self):
        spec = copy.deepcopy(self.spec)
        spec["channels"][0]["samples"][1]["modifiers"][0]["data"] = {"hi": 1.3, "lo": 0.95}
        lim4, _ = limit_and_yields(spec, "code4")
        lim1, _ = limit_and_yields(spec, "code1")
        self.assertAlmostEqual(lim4, 2.1145, delta=2e-4)
        self.assertAlmostEqual(lim1, 2.0525, delta=2e-4)
        self.assertGreater(abs(lim4 / lim1 - 1), 0.02)

    def test_default_model_uses_code4_and_code4p(self):
        model = pyhf.Workspace(self.spec).model()
        lim_default, _ = limit_and_yields(self.spec, "code4")
        data = pyhf.Workspace(self.spec).data(model)
        obs = pyhf.infer.intervals.upper_limits.toms748_scan(data, model, 0.5, 5.0, level=0.05, rtol=1e-6)[0]
        self.assertTrue(math.isclose(float(obs), lim_default, rel_tol=1e-9))


@unittest.skipUnless(HAVE_PYHF, "pyhf not installed: histosys walkthrough unverified")
class HistosysInterpolation(unittest.TestCase):
    def test_code0_linear_code4p_smooth(self):
        spec = json.loads(COUNTING.read_text(encoding="utf-8"))
        spec["channels"][0]["samples"][1]["modifiers"] = [
            {"name": "bkg_shape", "type": "histosys", "data": {"hi_data": [26.0], "lo_data": [19.0]}}]
        _, y0 = limit_and_yields(spec, "code1", par="bkg_shape")     # histosys code0
        _, y4 = limit_and_yields(spec, "code4", par="bkg_shape")     # histosys code4p
        # code 0: piecewise linear, kink at 0: +6 per unit up, +1 per unit down
        self.assertEqual([round(v, 9) for v in y0], [18.5, 19.0, 19.5, 23.0, 26.0, 29.0])
        # code 4p: linear beyond |a| = 1, a smooth polynomial inside
        self.assertAlmostEqual(y4[0], 18.5, places=9)
        self.assertAlmostEqual(y4[5], 29.0, places=9)
        self.assertAlmostEqual(y4[2], 20 - 0.5 * 3.5 + 0.25 * (3 * 0.0625 - 10 * 0.25 + 15) * 0.3125, places=9)


if __name__ == "__main__":
    unittest.main()
