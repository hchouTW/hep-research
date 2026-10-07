"""adapters/unbinned-fit: fit and seeded toy coverage on synthetic data."""
from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
SCRIPT = PLUGIN / "adapters" / "unbinned-fit" / "assets" / "unbinned_fit.py"
SPEC = importlib.util.spec_from_file_location("unbinned_fit", SCRIPT)
uf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(uf)
CFG = {"range": [0.0, 10.0], "truth": {"n_sig": 150, "n_bkg": 800, "mu": 5.0, "sigma": 0.4, "slope": -0.25}}


class UnbinnedFitTests(unittest.TestCase):
    def test_fit_recovers_a_large_sample(self):
        truth = dict(CFG["truth"], n_sig=3000, n_bkg=16000)
        x = uf.generate(truth, 0.0, 10.0, np.random.default_rng(7))
        r = uf.fit(x, 0.0, 10.0, truth)
        self.assertEqual(r["problems"], [])
        for k in uf.NAMES:
            self.assertLess(abs(r["parameters"][k] - truth[k]), 4 * r["hesse_errors"][k], k)
        lo, hi = r["profile_interval"]["n_sig"]
        err = r["hesse_errors"]["n_sig"]
        # large sample: the profile interval is close to the symmetric Hessian one
        self.assertAlmostEqual((hi - lo) / 2, err, delta=0.05 * err)
        self.assertLess(lo, r["parameters"]["n_sig"])
        self.assertGreater(hi, r["parameters"]["n_sig"])

    def test_nll_matches_a_direct_sum(self):
        x = np.array([1.0, 4.9, 5.2, 8.0])
        t = [10.0, 40.0, 5.0, 0.4, -0.25]
        g = lambda v: math.exp(-0.5 * ((v - 5) / 0.4) ** 2) / (math.sqrt(2 * math.pi) * 0.4 * uf._norm_gauss(0, 10, 5, 0.4))  # noqa: E731
        e = lambda v: math.exp(-0.25 * v) * 0.25 / (1 - math.exp(-2.5))  # noqa: E731
        want = 50 - sum(math.log(10 * g(v) + 40 * e(v)) for v in x)
        self.assertAlmostEqual(uf.nll(t, x, 0.0, 10.0), want, places=10)

    def test_coverage_is_nominal_within_its_error(self):
        res = uf.coverage(CFG, toys=80, seed=11)
        self.assertEqual(res["fits_failed"], 0, res["failed"])
        se = res["coverage_standard_error"]
        for k, c in res["hesse_68_coverage"].items():
            self.assertLess(abs(c - 0.6827), 3.5 * se, k)
        self.assertLess(abs(res["profile_68_coverage"]["n_sig"] - 0.6827), 3.5 * se)
        for k, m in res["pull_mean"].items():
            self.assertLess(abs(m), 3.5 * res["pull_mean_standard_error"], k)

    def test_coverage_check_detects_a_wrong_model(self):
        # fitting a Gaussian peak to a peak twice as wide as configured truth would pass; instead give the toys a
        # different truth than the coverage is computed against: the pulls of mu must reveal the shift
        cfg = json.loads(json.dumps(CFG))
        shifted = dict(cfg["truth"], mu=5.4)
        rng = np.random.default_rng(5)
        pulls = []
        for _ in range(30):
            r = uf.fit(uf.generate(shifted, 0.0, 10.0, rng), 0.0, 10.0, cfg["truth"])
            pulls.append((r["parameters"]["mu"] - cfg["truth"]["mu"]) / r["hesse_errors"]["mu"])
        self.assertGreater(np.mean(pulls), 5)

    def test_cli_refuses_bad_input(self):
        with tempfile.TemporaryDirectory() as td:
            cfg, data = Path(td) / "c.json", Path(td) / "d.json"
            cfg.write_text(json.dumps(CFG))
            data.write_text(json.dumps([1.0, 12.0]))
            p = subprocess.run([sys.executable, str(SCRIPT), "fit", "--data", str(data), "--config", str(cfg)],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 1)
            self.assertIn("inside the range", p.stdout)
            bad = dict(CFG, truth=dict(CFG["truth"], sigma=-1))
            cfg.write_text(json.dumps(bad))
            p = subprocess.run([sys.executable, str(SCRIPT), "coverage", "--config", str(cfg), "--toys", "10"],
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
