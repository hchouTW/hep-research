"""S9: time_structure.py. changepoint (binary segmentation or PELT, threshold or penalty calibrated by toys to a
declared false-alarm rate, toys drawn from a declared covariance when given) and lag (cross-correlation with
autocorrelation-preserving surrogates, a look-elsewhere correction over lags, hysteresis between the rising and
falling branches). Oracles: injected steps and lags are recovered; without a covariance the output says
"independence assumed"; slow tier: the false-alarm rate equals its declared value, and with AR(1) noise the declared
covariance restores it. Inputs are SYNTHETIC."""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "time_structure.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

try:
    import numpy as np
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False


def run(sub, doc, *args):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "in.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        cp = subprocess.run([sys.executable, "-B", str(SCRIPT), sub, "--input", str(p), *map(str, args)],
                            capture_output=True, text=True, timeout=900)
    return cp.returncode, json.loads(cp.stdout)


def step_series(n=80, k=50, step=1.5, seed=1):
    rng = np.random.default_rng(seed)
    e = np.full(n, 0.5)
    y = 10.0 + np.where(np.arange(n) >= k, step, 0.0) + rng.normal(0, e)
    return {"times": list(range(n)), "values": y.tolist(), "errors": e.tolist()}


def ar1_cov(n, phi, sd):
    i = np.arange(n)
    return (sd ** 2 * phi ** np.abs(np.subtract.outer(i, i))).tolist()


@unittest.skipUnless(HAVE, "NumPy needed")
class ChangePoint(unittest.TestCase):
    def test_injected_step_found_by_both_methods(self):
        for method in ("segmentation", "pelt"):
            with self.subTest(method=method):
                code, out = run("changepoint", step_series(), "--method", method, "--false-alarm", "0.05",
                                "--toys", "300", "--seed", "2")
                self.assertEqual(code, 0, out)
                idx = [c["index"] for c in out["change_points"]]
                self.assertEqual(len(idx), 1, out["change_points"])
                self.assertLessEqual(abs(idx[0] - 50), 1)
                self.assertIn("independence assumed", " ".join(out["warnings"]))
                self.assertEqual(out["calibration"]["false_alarm_rate"], 0.05)

    def test_no_step_gives_no_change(self):
        code, out = run("changepoint", step_series(step=0.0, seed=3), "--method", "pelt", "--false-alarm", "0.05",
                        "--toys", "300", "--seed", "4")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["change_points"], [])

    def test_declared_covariance_is_used(self):
        doc = dict(step_series(n=40, k=20, step=0.0, seed=5), covariance=ar1_cov(40, 0.6, 0.5))
        code, out = run("changepoint", doc, "--method", "segmentation", "--false-alarm", "0.05", "--toys", "300",
                        "--seed", "6")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["calibration"]["toys_from"], "declared covariance")
        self.assertNotIn("independence assumed", " ".join(out["warnings"]))

    def test_bad_input(self):
        doc = step_series()
        for args in (("--method", "pelt", "--false-alarm", "1.5", "--toys", "300", "--seed", "1"),
                     ("--method", "pelt", "--false-alarm", "0.05", "--toys", "300")):
            code, out = run("changepoint", doc, *args)
            self.assertEqual(code, 2, out)
        code, out = run("changepoint", dict(doc, covariance=[[1.0]]), "--method", "pelt", "--false-alarm", "0.05",
                        "--toys", "300", "--seed", "1")
        self.assertEqual(code, 2, out)


@unittest.skipUnless(HAVE, "NumPy needed")
class Lag(unittest.TestCase):
    def lagged(self, lag=5, n=300, seed=7):
        rng = np.random.default_rng(seed)
        a = np.zeros(n + lag)
        for i in range(1, n + lag):
            a[i] = 0.8 * a[i - 1] + rng.normal()
        b = a[:n] + 0.5 * rng.normal(size=n)          # b(t) = a(t - lag) + noise
        return {"times": list(range(n)), "a": a[lag:].tolist(), "b": b.tolist()}

    def test_injected_lag_recovered_with_global_p(self):
        code, out = run("lag", self.lagged(), "--max-lag", "20", "--surrogates", "200", "--seed", "8")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["best_lag"], 5)  # b lags a by 5 samples (positive: b later)
        self.assertLess(out["global_p"], 0.01)
        self.assertIn("lags", out["look_elsewhere"])

    def test_independent_series_not_significant(self):
        rng = np.random.default_rng(9)
        doc = {"times": list(range(200)), "a": rng.normal(size=200).tolist(), "b": rng.normal(size=200).tolist()}
        code, out = run("lag", doc, "--max-lag", "10", "--surrogates", "200", "--seed", "10")
        self.assertEqual(code, 0, out)
        self.assertGreater(out["global_p"], 0.01)

    def test_hysteresis_between_branches(self):
        t = np.arange(200)
        a = np.sin(np.pi * t / 199)                    # rises, then falls
        rising = t <= np.argmax(a)
        b = 2.0 * a + np.where(rising, 0.0, 0.3)       # the falling branch sits 0.3 higher
        b = b + np.random.default_rng(11).normal(0, 0.02, 200)
        doc = {"times": t.tolist(), "a": a.tolist(), "b": b.tolist()}
        code, out = run("lag", doc, "--max-lag", "5", "--surrogates", "50", "--seed", "12", "--hysteresis-bins", "5")
        self.assertEqual(code, 0, out)
        diffs = [row["difference"] for row in out["hysteresis"]["bins"]]
        for d in diffs:
            self.assertAlmostEqual(d, -0.3, delta=0.05)  # rising minus falling
        self.assertLess(out["hysteresis"]["p_value"], 1e-6)

    def test_uneven_times_refused(self):
        doc = self.lagged()
        doc["times"][3] += 0.5
        code, out = run("lag", doc, "--max-lag", "5", "--surrogates", "20", "--seed", "1")
        self.assertEqual(code, 2, out)


@unittest.skipUnless(HAVE and SLOW, "slow: set HEP_SLOW_TESTS=1")
class FalseAlarmSlow(unittest.TestCase):
    def rate(self, method, n_series, gen, cov=None):
        import time_structure as ts
        hits = 0
        for k in range(n_series):
            y, e = gen(k)
            res = ts.changepoint(np.arange(len(y)), y, e, method, 0.1, 300, 100 + k, cov=cov)
            hits += bool(res["change_points"])
        return hits / n_series

    def test_false_alarm_rate_equals_declared(self):
        def gen(k):
            rng = np.random.default_rng(1000 + k)
            e = np.full(60, 0.4)
            return rng.normal(0, e), e
        for method in ("segmentation", "pelt"):
            with self.subTest(method=method):
                r = self.rate(method, 300, gen)
                self.assertLessEqual(abs(r - 0.1), 3 * math.sqrt(0.1 * 0.9 / 300), r)

    def test_declared_covariance_restores_the_rate_under_ar1_noise(self):
        n, phi, sd = 50, 0.6, 0.5
        cov = np.array(ar1_cov(n, phi, sd))
        chol = np.linalg.cholesky(cov)

        def gen(k):
            rng = np.random.default_rng(2000 + k)
            return chol @ rng.normal(size=n), np.full(n, sd)
        naive = self.rate("segmentation", 200, gen)
        declared = self.rate("segmentation", 200, gen, cov=cov)
        self.assertGreater(naive, 0.25)
        self.assertLessEqual(abs(declared - 0.1), 3 * math.sqrt(0.1 * 0.9 / 200), declared)


if __name__ == "__main__":
    unittest.main()
