"""theory:dis-parton-model prediction tests on the SYNTHETIC toy: positivity, F_L <= F_2, alpha_s -> 0, the two
numerical routes, bad inputs refused, and no experiment content."""
import json
import math
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = predict.load_json(predict.DEFAULT_CONFIG)


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required")
class PredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = predict.predict(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.p["checks"].values()), self.p["checks"])

    def test_no_hard_coded_checks(self):
        self.assertNotIn("units_dimensionless", self.p["checks"])

    def test_hand_check_quark_only_pins_16_over_3(self):
        """u quark only, q = 1, gluon off: F_2 = (4/9) z, F_L = (alpha_s/4pi) (16/3)(4/9) x^2 (1/x - 1)."""
        cfg = dict(CFG, flavours=[{"name": "u", "charge": "2/3", "quark": [["1", "0", 0]], "antiquark": []}], gluon=[])
        x, a_s = 0.2, 0.2
        exact = a_s / (4 * math.pi) * (16 / 3) * (4 / 9) * x * x * (1 / x - 1)
        self.assertAlmostEqual(predict.fl(cfg, x, a_s) / exact, 1.0, places=12)
        self.assertAlmostEqual(predict.fl_convolution_route(cfg, x, a_s) / exact, 1.0, places=12)

    def test_grid_and_labels(self):
        self.assertEqual(len(self.p["rows"]), len(CFG["x_points"]) * len(CFG["q2_points_gev2"]))
        self.assertIn("SYNTHETIC", self.p["label"])
        self.assertAlmostEqual(self.p["sum_e2"], 10 / 9, places=14)  # u, d, s, c

    def test_fl_scales_with_alpha_s(self):
        x = 0.05
        self.assertAlmostEqual(predict.fl(CFG, x, 0.3) / predict.fl(CFG, x, 0.1), 3.0, places=12)
        self.assertEqual(predict.fl(CFG, x, 0.0), 0.0)

    def test_hand_check_gluon_only(self):
        """Gluon only, g = 1 (b = 0, a = 0): F_L = (alpha_s/4pi) 8 sum e^2 x^2 int_x^1 (1 - x/z)/z^2 dz."""
        cfg = dict(CFG, flavours=[dict(f, quark=[], antiquark=[]) for f in CFG["flavours"]], gluon=[["1", "0", 0]])
        x, a_s = 0.2, 0.2
        exact = a_s / (4 * math.pi) * 8 * (10 / 9) * x * x * ((1 / x - 1) - x * (1 / x ** 2 - 1) / 2)
        self.assertAlmostEqual(predict.fl(cfg, x, a_s) / exact, 1.0, places=12)
        self.assertAlmostEqual(predict.fl_convolution_route(cfg, x, a_s) / exact, 1.0, places=12)

    def test_negative_density_refused(self):
        bad = json.loads(json.dumps(CFG))
        bad["gluon"] = [["-1", "0", 1]]
        with self.assertRaises(predict.InputError):
            predict.predict(bad)

    def test_x_outside_range_refused(self):
        with self.assertRaises(predict.InputError):
            predict.predict(dict(CFG, x_points=[0.0, 0.5]))

    def test_alpha_s_per_q2(self):
        with self.assertRaises(predict.InputError):
            predict.predict(dict(CFG, alpha_s_at_q2=[0.2]))

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        self.assertTrue(all(c["status"] == "demonstrated-on-synthetic-data" for c in prof["capabilities"]))
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "luminosity_pb", "experiment:"):
            self.assertNotIn(word, text)
        for doc in ("README.md", "index.md"):
            self.assertIn("ynthetic only", (ROOT / doc).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
