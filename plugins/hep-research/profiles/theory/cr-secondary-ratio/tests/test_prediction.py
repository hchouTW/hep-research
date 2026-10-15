"""theory:cr-secondary-ratio prediction tests: evaluation at arbitrary parameter points and on grids, the D0/L
degeneracy, the slab/diffusion mapping, refusals, and no experiment content. Inputs are ILLUSTRATIVE."""
import json
import subprocess
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import predict  # noqa: E402

CFG = json.loads((ROOT / "benchmarks" / "bc-benchmark.json").read_text(encoding="utf-8"))


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class PredictionTests(unittest.TestCase):
    def test_ratio_falls_with_energy_as_grammage_does(self):
        p = predict.evaluate(CFG)
        self.assertTrue(all(b < a for a, b in zip(p["ratio"], p["ratio"][1:])))
        self.assertTrue(all(b < a for a, b in zip(p["grammage_g_cm2"], p["grammage_g_cm2"][1:])))

    def test_high_energy_slope_tends_to_minus_delta(self):
        # when 1/lambda_esc >> sigma_s/m_H, ratio ~ lambda_esc ~ R^-delta
        cfg = dict(CFG, energies_gev_per_n=[1e4, 1e5])
        r = predict.evaluate(cfg)["ratio"]
        import math
        slope = math.log(r[1] / r[0]) / math.log(10.0)
        self.assertAlmostEqual(slope, -CFG["transport"]["delta"], delta=0.01)

    def test_D0_over_L_degeneracy(self):
        base = predict.evaluate(CFG)
        for c in (0.3, 2.0, 7.5):
            p = predict.evaluate(CFG, {"D0_cm2_s": CFG["transport"]["D0_cm2_s"] * c,
                                       "L_kpc": CFG["transport"]["L_kpc"] * c})
            for a, b in zip(p["ratio"], base["ratio"]):
                self.assertAlmostEqual(a / b, 1.0, delta=1e-12)
            self.assertAlmostEqual(p["parameter_point"]["D0_over_L_cm2_s_per_kpc"],
                                   base["parameter_point"]["D0_over_L_cm2_s_per_kpc"], delta=1e15)
        moved = predict.evaluate(CFG, {"L_kpc": 8.0})["ratio"]
        self.assertGreater(moved[0] / base["ratio"][0] - 1, 0.05)

    def test_chi2_hessian_has_a_flat_direction_along_D0_over_L(self):
        import numpy as np
        y = np.array(predict.evaluate(CFG)["ratio"])
        sig = 0.02 * y

        def chi2(ld, ll):
            m = np.array(predict.evaluate(CFG, {"D0_cm2_s": CFG["transport"]["D0_cm2_s"] * np.exp(ld),
                                                "L_kpc": CFG["transport"]["L_kpc"] * np.exp(ll)})["ratio"])
            return float(np.sum(((m - y) / sig) ** 2))
        e = 1e-3
        h11 = (chi2(e, 0) - 2 * chi2(0, 0) + chi2(-e, 0)) / e ** 2
        h22 = (chi2(0, e) - 2 * chi2(0, 0) + chi2(0, -e)) / e ** 2
        h12 = (chi2(e, e) - chi2(e, -e) - chi2(-e, e) + chi2(-e, -e)) / (4 * e ** 2)
        w, v = np.linalg.eigh(np.array([[h11, h12], [h12, h22]]))
        self.assertLess(abs(w[0]) / w[1], 1e-6)
        flat = v[:, 0] / np.linalg.norm(v[:, 0])
        self.assertAlmostEqual(abs(flat @ np.array([1, 1]) / np.sqrt(2)), 1.0, delta=1e-6)  # (ln D0, ln L) move together

    def test_weighted_slab_with_mapped_lambda0_equals_diffusion(self):
        t = CFG["transport"]
        lam0 = t["n_H_cm3"] * predict.M_H_G * t["h_kpc"] * predict.KPC_CM * predict.C_CM_S * t["L_kpc"] \
            * predict.KPC_CM / t["D0_cm2_s"]
        slab = predict.evaluate(dict(CFG, model="weighted-slab", leaky_box={"lambda0_g_cm2": lam0,
                                                                           "delta": t["delta"], "R0_GV": t["R0_GV"]}))
        for a, b in zip(slab["ratio"], predict.evaluate(CFG)["ratio"]):
            self.assertAlmostEqual(a / b, 1.0, delta=1e-12)

    def test_cross_section_alternative_changes_the_prediction(self):
        nom = predict.evaluate(CFG)["ratio"]
        alt = predict.evaluate(CFG, xs_set=CFG["alternative_cross_section_sets"][0])["ratio"]
        self.assertTrue(all(a > b for a, b in zip(alt, nom)))

    def test_grid_is_row_major_and_matches_point_evaluation(self):
        axes = {"D0_cm2_s": [1.5e28, 3e28, 6e28], "L_kpc": [2.0, 4.0]}
        g = predict.grid(CFG, axes)
        self.assertEqual(len(g["points"]), 6)
        self.assertEqual([p["parameter_point"]["L_kpc"] for p in g["points"][:2]], [2.0, 4.0])
        one = predict.evaluate(CFG, {"D0_cm2_s": 6e28, "L_kpc": 2.0})["ratio"]
        self.assertEqual(g["points"][4]["ratio"], one)
        self.assertTrue(g["illustrative"])

    def test_bin_average_lies_between_edge_values(self):
        edges = CFG["energy_bin_edges_gev_per_n"]
        avg = predict.bin_averaged(CFG, edges)
        at_edges = predict.evaluate(dict(CFG, energies_gev_per_n=edges))["ratio"]
        for i, a in enumerate(avg):
            self.assertTrue(at_edges[i + 1] < a < at_edges[i])

    def test_refusals(self):
        with self.assertRaises(predict.InputError):
            predict.evaluate(CFG, {"L_kpc": -1.0})
        with self.assertRaises(predict.InputError):
            predict.evaluate(CFG, {"sigma": 1.0})
        with self.assertRaises(predict.InputError):
            predict.evaluate(dict(CFG, model="galprop"))
        with self.assertRaises(predict.InputError):
            predict.halo_finite_disc_exact(dict(CFG["transport"], h_kpc=5.0), 10.0, CFG, predict.load_cross_sections(CFG))
        with self.assertRaises(predict.InputError):
            predict.bin_averaged(CFG, [10.0, 3.0])

    def test_cli_point_grid_and_bad_input(self):
        script = str(ROOT / "scripts" / "predict.py")
        ok = subprocess.run([sys.executable, script, "--set", "L_kpc=6"], capture_output=True, text=True, timeout=120)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["parameter_point"]["L_kpc"], 6.0)
        gr = subprocess.run([sys.executable, script, "--grid", "D0_cm2_s=1e28,2e28", "--grid", "L_kpc=3,6"],
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(gr.returncode, 0, gr.stderr)
        self.assertEqual(len(json.loads(gr.stdout)["points"]), 4)
        bad = subprocess.run([sys.executable, script, "--set", "D0=1"], capture_output=True, text=True, timeout=120)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(json.loads(bad.stdout)["status"], "failed")

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts
                        and f.name != "sources.json")
        for word in ("profiles/experiments", "blinding\":", "experiment:", "AMS", "PAMELA"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
