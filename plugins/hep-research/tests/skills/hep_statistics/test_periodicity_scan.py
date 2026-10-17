"""S5: periodicity_scan.py, weighted generalized Lomb-Scargle with white, AR(1) or OU surrogates and a band-maximum
global significance. Oracles: the power equals its definition 1 - chi2(sinusoid + offset) / chi2(offset) by direct
weighted least squares; an injected sinusoid is found at its frequency; caps refuse oversized inputs unless
overridden. Slow tier: the global p-value is uniform under white noise (KS) and the AR(1) null rejects AR(1) data at
alpha +- 0.02. Inputs are SYNTHETIC."""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "periodicity_scan.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

try:
    import numpy as np
    import scipy  # noqa: F401
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False


def run(doc, *args):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), "--input", str(p), *map(str, args)],
                            capture_output=True, text=True, timeout=900)
    return cp.returncode, json.loads(cp.stdout)


def irregular_series(n, seed, amp=0.0, freq=0.1, sigma=1.0):
    rng = random.Random(seed)
    t = sorted(rng.uniform(0, 200) for _ in range(n))
    e = [sigma * (0.8 + 0.4 * rng.random()) for _ in range(n)]
    y = [5.0 + amp * math.sin(2 * math.pi * freq * ti + 0.3) + rng.gauss(0, ei) for ti, ei in zip(t, e)]
    return {"times": t, "values": y, "errors": e}


@unittest.skipUnless(HAVE, "NumPy and SciPy needed")
class Power(unittest.TestCase):
    def test_power_equals_least_squares_definition(self):
        import periodicity_scan as ps
        d = irregular_series(80, 1, amp=1.0)
        t, y, e = (np.array(d[k]) for k in ("times", "values", "errors"))
        freqs = np.array([0.013, 0.05, 0.1, 0.27])
        p = ps.gls_power(t, y, e, freqs)
        w = 1 / e ** 2
        chi0 = float(np.sum(w * (y - np.sum(w * y) / np.sum(w)) ** 2))
        for f, pf in zip(freqs, p):
            a = np.column_stack([np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t), np.ones_like(t)])
            coef, *_ = np.linalg.lstsq(a * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)
            chi1 = float(np.sum(w * (y - a @ coef) ** 2))
            self.assertAlmostEqual(pf, 1 - chi1 / chi0, delta=1e-10)

    def test_injected_sinusoid_is_found(self):
        doc = dict(irregular_series(200, 2, amp=1.2, freq=0.1),
                   frequencies={"min": 0.005, "max": 0.5, "n": 400}, band=[0.02, 0.5])
        code, out = run(doc, "--null", "white", "--surrogates", "200", "--seed", "3", "--alpha", "0.01")
        self.assertEqual(code, 0, out)  # a detection is a result, not a failed run
        self.assertEqual(out["verdict"], "periodicity")
        self.assertAlmostEqual(out["best"]["frequency"], 0.1, delta=0.5 / 400 * 2)
        self.assertLess(out["global"]["p"], 0.01)
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertEqual(out["method_kind"], "surrogate-calibrated")

    def test_no_signal_is_consistent(self):
        doc = dict(irregular_series(150, 4), frequencies={"min": 0.005, "max": 0.5, "n": 200})
        code, out = run(doc, "--null", "white", "--surrogates", "100", "--seed", "5", "--alpha", "0.01")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["verdict"], "no-periodicity")
        self.assertIn("band", out["defaults_used"])

    def test_ar1_and_ou_nulls_report_their_parameters(self):
        doc = dict(irregular_series(120, 6), frequencies={"min": 0.005, "max": 0.5, "n": 100})
        for null, key in (("ar1", "phi"), ("ou", "tau")):
            with self.subTest(null=null):
                code, out = run(doc, "--null", null, "--surrogates", "50", "--seed", "7")
                self.assertEqual(code, 0, out)
                self.assertIn(key, out["null_model"])

    def test_caps_and_bad_input(self):
        doc = dict(irregular_series(30, 8), frequencies={"min": 0.01, "max": 0.5, "n": 20000})
        code, out = run(doc, "--null", "white", "--surrogates", "10", "--seed", "1")
        self.assertEqual(code, 2, out)
        self.assertIn("--allow-outside-validated-range", out["error"])
        code, out = run(doc, "--null", "white", "--surrogates", "2", "--seed", "1", "--allow-outside-validated-range")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["range_label"], "outside-validated-range")
        for bad in ({"times": [1, 2], "values": [1, 2], "errors": [1, 0]},
                    {"times": [1, 2, 3], "values": [1, 2], "errors": [1, 1, 1]}):
            code, out = run(dict(bad, frequencies={"min": 0.1, "max": 1, "n": 5}), "--null", "white",
                            "--surrogates", "10", "--seed", "1")
            self.assertEqual(code, 2, out)
        code, out = run(doc, "--null", "white", "--surrogates", "10")  # no seed
        self.assertEqual(code, 2, out)


@unittest.skipUnless(HAVE and SLOW, "slow: set HEP_SLOW_TESTS=1")
class NullCalibrationSlow(unittest.TestCase):
    def test_global_p_uniform_under_white_noise(self):
        import periodicity_scan as ps
        from scipy.stats import kstest
        rng = np.random.default_rng(11)
        ps_vals = []
        freqs = np.linspace(0.01, 0.5, 120)
        for k in range(300):
            t = np.sort(rng.uniform(0, 200, 80))
            e = 0.8 + 0.4 * rng.random(80)
            y = rng.normal(0, e)
            ps_vals.append(ps.scan(t, y, e, freqs, None, "white", 99, 1000 + k)["global"]["p"])
        self.assertGreater(kstest(ps_vals, "uniform").pvalue, 0.01)

    def test_ar1_null_rejects_at_alpha(self):
        import periodicity_scan as ps
        rng = np.random.default_rng(12)
        freqs = np.linspace(0.01, 0.5, 100)
        alpha, n_series, rej = 0.05, 400, 0
        for k in range(n_series):
            n, phi = 100, 0.7
            x = np.empty(n)
            x[0] = rng.normal(0, 1 / math.sqrt(1 - phi * phi))
            for i in range(1, n):
                x[i] = phi * x[i - 1] + rng.normal()
            t = np.arange(n, dtype=float)
            res = ps.scan(t, x, np.ones(n), freqs, None, "ar1", 199, 5000 + k)
            rej += res["global"]["p"] < alpha
        self.assertLessEqual(abs(rej / n_series - alpha), 0.02, rej / n_series)


if __name__ == "__main__":
    unittest.main()
