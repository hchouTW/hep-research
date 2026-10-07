"""S06: skills/hep-statistics/scripts/sensitivity_and_gof.py. Asimov significance with and without a background
uncertainty against an independent numerical profile of q0, and the calibration of the toy goodness of fit:
uniform p-values for a correct model (KS at alpha = 0.01 on 300 datasets, slow: HEP_SLOW_TESTS=1) and small
p-values for a wrong one. All inputs SYNTHETIC."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "sensitivity_and_gof.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

try:
    import numpy as np
    from scipy import optimize, stats
    import sensitivity_and_gof as sg
    HAVE = True
except ImportError:
    HAVE = False


def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def shapes():
    x = np.arange(20) + 0.5
    bkg = np.exp(-x / 8)
    sig = np.exp(-0.5 * ((x - 10) / 1.5) ** 2)
    return bkg / bkg.sum(), sig / sig.sum()


class AsimovSignificance(unittest.TestCase):
    def test_known_background(self):
        code, out = run("asimov-z", "--s", "5", "--b", "20")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["z_asimov"], 1.07572, delta=1e-5)
        self.assertIn("large-b limit", out["large_b_limit"]["label"])

    @unittest.skipUnless(HAVE, "numpy/scipy not installed: profile cross-check unverified")
    def test_background_uncertainty_matches_numerical_profile(self):
        s, b, sb = 5.0, 20.0, 2.0
        code, out = run("asimov-z", "--s", "5", "--b", "20", "--sigma-b", "2")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["z_asimov"], 0.97554, delta=1e-5)
        # independent path: Asimov data n = s + b, m = tau b with tau = b / sb^2; profile b numerically
        tau = b / sb ** 2
        n, m = s + b, tau * b

        def nll(mu_s, bb):
            lam1, lam2 = mu_s + bb, tau * bb
            return lam1 - n * math.log(lam1) + lam2 - m * math.log(lam2)
        free = optimize.minimize(lambda v: nll(v[0], v[1]), [4.0, 19.0], method="Nelder-Mead",
                                 options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 20000})
        null = optimize.minimize_scalar(lambda bb: nll(0.0, bb), bounds=(1e-6, 100), method="bounded",
                                        options={"xatol": 1e-12})
        z_num = math.sqrt(2 * (null.fun - free.fun))
        self.assertAlmostEqual(out["z_asimov"], z_num, delta=1e-6)

    def test_rejects_bad_input(self):
        p = subprocess.run([sys.executable, str(SCRIPT), "asimov-z", "--s", "5", "--b", "0"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


@unittest.skipUnless(HAVE, "numpy/scipy not installed: goodness of fit unverified")
class GoodnessOfFit(unittest.TestCase):
    def test_fit_matches_direct_maximization(self):
        bkg, sig = shapes()
        n = np.random.default_rng(1).poisson(200 * bkg + 60 * sig).astype(float)
        A = np.array([bkg, sig]).T
        y, conv = sg.fit_yields(n, A)
        ref = optimize.minimize(lambda v: np.sum(A @ v - n * np.log(A @ v)), [100, 50], bounds=[(1e-9, None)] * 2,
                                method="L-BFGS-B", options={"ftol": 1e-15, "gtol": 1e-12})
        self.assertTrue(conv[0])
        np.testing.assert_allclose(y[0], ref.x, rtol=1e-4)

    def test_cli_reports_calibration_and_withholds_chi2(self):
        bkg, sig = shapes()
        n = np.random.default_rng(2).poisson(200 * bkg + 60 * sig).astype(int)
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "gof.json"
            f.write_text(json.dumps({"observed": n.tolist(), "templates": {"bkg": bkg.tolist(), "sig": sig.tolist()}}))
            p = subprocess.run([sys.executable, str(SCRIPT), "gof", "--input", str(f), "--toys", "300", "--seed", "4"],
                               capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual((out["toys"], out["seed"], out["ndof"]), (300, 4, 18))
        self.assertIn("refitted", out["calibration"])
        self.assertIn("chi2_withheld", out)            # the tail bins have expectations below 5

    def test_zero_count_terms_use_their_limit(self):
        self.assertAlmostEqual(float(sg.deviance(np.array([0.0, 3.0]), np.array([2.0, 3.0]))), 4.0)

    def test_wrong_model_gives_small_p(self):
        # configuration fixed in advance: data 200 background + 60 signal; the fit uses the background shape only
        bkg, sig = shapes()
        rng = np.random.default_rng(5)
        ps = []
        for _ in range(40):
            n = rng.poisson(200 * bkg + 60 * sig).astype(int)
            out, code = sg.gof({"observed": n.tolist(), "templates": {"bkg": bkg.tolist()}}, 200, int(rng.integers(1e9)))
            self.assertEqual(code, 0)
            ps.append(out["p_value"] if out["p_value"] is not None else 0.0)
        print(f"\nGoF wrong model: median p = {float(np.median(ps)):.4f} over 40 datasets")
        self.assertLess(float(np.median(ps)), 0.05)

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_toy_calibrated_p_values_are_uniform(self):
        # 300 datasets from a fixed model (200 background + 60 signal); each is fitted with both templates and
        # calibrated with 200 toys from its own fitted model, refitted one by one (batched over datasets).
        bkg, sig = shapes()
        A = np.array([bkg, sig]).T
        rng = np.random.default_rng(20261003)
        n = rng.poisson(200 * bkg + 60 * sig, size=(300, 20)).astype(float)
        y, conv = sg.fit_yields(n, A)
        self.assertTrue(conv.all())
        nu = y @ A.T
        d_obs = sg.deviance(n, nu)
        toys = rng.poisson(np.repeat(nu, 200, axis=0)).astype(float)
        yt, ct = sg.fit_yields(toys, A)
        self.assertGreater(ct.mean(), 0.99)
        d_t = sg.deviance(toys, yt @ A.T).reshape(300, 200)
        p = (d_t >= d_obs[:, None] - 1e-9).mean(axis=1)
        ks = stats.kstest(p, "uniform")
        print(f"\nGoF calibration: KS D = {ks.statistic:.4f}, p = {ks.pvalue:.3f}, mean p = {p.mean():.3f}")
        self.assertGreater(ks.pvalue, 0.01)


if __name__ == "__main__":
    unittest.main()
