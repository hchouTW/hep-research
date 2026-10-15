"""theory:cr-secondary-ratio benchmark: the closed-form weighted-slab solution and the 1D model's thin-disc limit,
checked against the profile's own numerical solutions (no external program). Inputs are ILLUSTRATIVE."""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "bc-benchmark.json").read_text(encoding="utf-8"))


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = predict.benchmark(CFG)
        cls.xs = predict.load_cross_sections(CFG)

    def test_all_checks_pass(self):
        self.assertTrue(all(self.b["checks"].values()), self.b["checks"])

    def test_slab_closed_form_against_ode_average(self):
        for row in self.b["rows"]:
            self.assertAlmostEqual(row["slab_numerical"] / row["slab_closed"], 1.0, delta=1e-7, msg=row["e_n_gev"])

    def test_slab_closed_form_at_hand_computed_point(self):
        # one parent, no secondary destruction: ratio = (sigma_Ps/m_H) * lambda_esc exactly
        cfg = dict(CFG, parents=[CFG["parents"][0]])
        xs = {"production_mb": {"C->B": 70.0}, "inelastic_mb": {"B": 0.0, "C": 270.0}}
        lam = 5.0
        self.assertAlmostEqual(predict.slab_ratio(lam, cfg, xs), 70e-27 / predict.M_H_G * lam, delta=1e-15)
        # infinite grammage: the ratio saturates at sum_j sigma_js r_j / sigma_s
        sat = predict.slab_ratio(1e12, CFG, self.xs)
        expect = (70.0 * 1.0 + 35.0 * 0.9) / 250.0
        self.assertAlmostEqual(sat, expect, delta=1e-9)

    def test_finite_volume_against_finite_disc_exact(self):
        for row in self.b["rows"]:
            self.assertAlmostEqual(row["finite_disc_fd"] / row["finite_disc_exact"], 1.0, delta=1e-6)

    def test_finite_volume_converges_at_second_order(self):
        params = predict.model_parameters(CFG)
        exact = predict.halo_finite_disc_exact(params, 10.0, CFG, self.xs)["ratio"]
        errs = [abs(predict.halo_finite_disc_fd(params, 10.0, CFG, self.xs, n_disc=n, n_halo=2 * n)["ratio"] / exact - 1)
                for n in (50, 100, 200)]
        self.assertLess(errs[1], errs[0] / 3)
        self.assertLess(errs[2], errs[1] / 3)

    def test_thin_disc_limit(self):
        diffs = [x["rel_diff"] for x in self.b["thin_disc_limit"]]
        self.assertTrue(all(b < a for a, b in zip(diffs, diffs[1:])), diffs)
        self.assertLess(diffs[-1], 1e-3)
        # linear in h: quartering h quarters the difference (within 10%)
        for a, b in zip(diffs, diffs[1:]):
            self.assertAlmostEqual(a / b, 4.0, delta=0.4)

    def test_stored_values_reproduced(self):
        rows = {r["e_n_gev"]: r for r in self.b["rows"]}
        self.assertAlmostEqual(rows[10.0]["slab_closed"], 0.06607329411207317, delta=1e-12)
        self.assertAlmostEqual(rows[10.0]["grammage_g_cm2"], 1.300464345848811, delta=1e-10)  # m_H = proton mass


if __name__ == "__main__":
    unittest.main()
