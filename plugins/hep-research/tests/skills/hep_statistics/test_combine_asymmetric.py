"""T22: Barlow's asymmetric-uncertainty combinations (combine_asymmetric.py).

measurements: exact limits (one measurement, symmetric errors), and a closure against the exact pooled likelihood of
exponential lifetimes, whose per-measurement intervals are strongly asymmetric. sources: identity for one source,
quadrature for symmetric ones, and the cumulants and quantiles of a Monte Carlo sum of the sources."""
import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "combine_asymmetric.py"
sys.path.insert(0, str(SCRIPT.parent))
import combine_asymmetric as ca  # noqa: E402

METHODS = ("linear_variance", "linear_sigma")


def lifetime(ts):
    """Exponential-lifetime MLE with the Delta lnL = 1/2 interval of the exact likelihood."""
    n, tb = len(ts), statistics.fmean(ts)
    ll = lambda tau: -n * (math.log(tau) + tb / tau)
    target = ll(tb) - 0.5

    def cross(inside, outside):
        for _ in range(200):
            mid = 0.5 * (inside + outside)
            inside, outside = (mid, outside) if ll(mid) > target else (inside, mid)
        return 0.5 * (inside + outside)
    return tb, cross(tb, 20 * tb) - tb, tb - cross(tb, 1e-3 * tb)


class MeasurementTests(unittest.TestCase):
    def test_each_likelihood_is_minus_half_at_the_quoted_errors(self):
        for method in METHODS:
            self.assertAlmostEqual(ca.log_likelihood(2.7, 2.0, 0.7, 0.4, method), -0.5, places=12)
            self.assertAlmostEqual(ca.log_likelihood(1.6, 2.0, 0.7, 0.4, method), -0.5, places=12)

    def test_one_measurement_comes_back(self):
        for method in METHODS:
            r = ca.combine_measurements({"measurements": [{"value": 2.0, "plus": 0.7, "minus": 0.4}], "method": method})
            self.assertAlmostEqual(r["value"], 2.0, places=6)
            self.assertAlmostEqual(r["plus"], 0.7, places=6)
            self.assertAlmostEqual(r["minus"], 0.4, places=6)

    def test_symmetric_errors_give_the_weighted_mean(self):
        meas = [(1.0, 0.5), (1.6, 0.3), (1.2, 0.8)]
        w = [1 / s ** 2 for _, s in meas]
        mean = sum(x * wi for (x, _), wi in zip(meas, w)) / sum(w)
        chi2 = sum((x - mean) ** 2 * wi for (x, _), wi in zip(meas, w))
        for method in METHODS:
            r = ca.combine_measurements({"measurements": [{"value": x, "plus": s, "minus": s} for x, s in meas], "method": method})
            self.assertAlmostEqual(r["value"], mean, places=6)
            self.assertAlmostEqual(r["plus"], 1 / math.sqrt(sum(w)), places=6)
            self.assertAlmostEqual(r["minus"], 1 / math.sqrt(sum(w)), places=6)
            self.assertAlmostEqual(r["consistency_chi2"], chi2, places=6)

    def test_closure_against_the_exact_pooled_lifetime_likelihood(self):
        # three measurements of 6 decays each (intervals skewed about 1.4 : 1); the pooled 18-decay likelihood is exact
        rng = random.Random(1)
        toys = 800
        stats = {m: {"dv": [], "plus": [], "minus": [], "cover": 0} for m in METHODS}
        exact_cover = 0
        for _ in range(toys):
            groups = [[rng.expovariate(1.0) for _ in range(6)] for _ in range(3)]
            meas = [dict(zip(("value", "plus", "minus"), lifetime(g))) for g in groups]
            ex = lifetime(sum(groups, []))
            exact_cover += ex[0] - ex[2] <= 1.0 <= ex[0] + ex[1]
            for m in METHODS:
                r = ca.combine_measurements({"measurements": meas, "method": m})
                s = stats[m]
                s["dv"].append((r["value"] - ex[0]) / ex[1])
                s["plus"].append(r["plus"] / ex[1])
                s["minus"].append(r["minus"] / ex[2])
                s["cover"] += r["value"] - r["minus"] <= 1.0 <= r["value"] + r["plus"]
        for m, s in stats.items():
            self.assertLess(abs(statistics.fmean(s["dv"])), 0.05, m)          # central value: a few % of an error
            self.assertLess(abs(statistics.fmean(s["plus"]) - 1), 0.10, m)    # errors within 10% of the exact ones
            self.assertLess(abs(statistics.fmean(s["minus"]) - 1), 0.10, m)
            self.assertLess(abs(s["cover"] - exact_cover) / toys, 0.05, m)    # coverage close to the exact interval's

    def test_rejections_and_failures(self):
        with self.assertRaises(ca.CombineError):
            ca.combine_measurements({"measurements": [{"value": 1.0, "plus": 0.0, "minus": 0.1}]})
        with self.assertRaises(ca.CombineError):
            ca.combine_measurements({"measurements": [{"value": 1.0, "plus": 0.1, "minus": 0.1}], "method": "average"})


class SourceTests(unittest.TestCase):
    def test_one_source_comes_back_unchanged(self):
        for model in ("quadratic", "piecewise"):
            r = ca.combine_sources({"value": 1.0, "sources": [{"up": 0.7, "down": -0.4}], "model": model})
            self.assertAlmostEqual(r["up"], 0.7, places=6)
            self.assertAlmostEqual(r["down"], -0.4, places=6)
            self.assertAlmostEqual(r["value"], 1.0, places=9)

    def test_symmetric_sources_add_in_quadrature(self):
        for model in ("quadratic", "piecewise"):
            r = ca.combine_sources({"value": 1.0, "sources": [{"up": 0.3, "down": -0.3}, {"up": 0.4, "down": -0.4}], "model": model})
            self.assertAlmostEqual(r["plus"], 0.5, places=6)
            self.assertAlmostEqual(r["minus"], 0.5, places=6)
            self.assertAlmostEqual(r["central_shift"], 0.0, places=9)

    def test_cumulants_and_quantiles_match_a_monte_carlo_sum(self):
        srcs = [{"up": 0.8, "down": -0.5}, {"up": 0.3, "down": -0.6}, {"up": 1.0, "down": -0.9}, {"up": 0.4, "down": 0.1}]
        shapes = {"quadratic": lambda u, d, nu: 0.5 * (u - d) * nu + 0.5 * (u + d) * nu * nu,
                  "piecewise": lambda u, d, nu: u * nu if nu > 0 else -d * nu}
        for model, f in shapes.items():
            r = ca.combine_sources({"value": 10.0, "sources": srcs, "model": model})
            rng = random.Random(3)
            xs = sorted(10.0 + sum(f(s["up"], s["down"], rng.gauss(0, 1)) for s in srcs) for _ in range(100000))
            m = statistics.fmean(xs)
            self.assertAlmostEqual(m - 10.0, r["total_cumulants"]["mean"], delta=0.015, msg=model)
            self.assertAlmostEqual(statistics.pvariance(xs), r["total_cumulants"]["variance"], delta=0.03, msg=model)
            self.assertAlmostEqual(statistics.fmean((x - m) ** 3 for x in xs), r["total_cumulants"]["third_cumulant"], delta=0.06, msg=model)
            q = lambda p: xs[int(p * len(xs))]
            self.assertAlmostEqual(r["value"], q(0.5), delta=0.03, msg=model)
            self.assertAlmostEqual(r["value"] + r["down"], q(0.1587), delta=0.04, msg=model)
            self.assertAlmostEqual(r["value"] + r["up"], q(0.8413), delta=0.04, msg=model)

    def test_one_sided_source_keeps_its_cumulants(self):
        # both shifts positive: the total is described again by the model, with the same three cumulants and a shifted
        # central value (the description need not be one-sided)
        for model in ("quadratic", "piecewise"):
            r = ca.combine_sources({"value": 0.0, "sources": [{"up": 1.0, "down": 0.4}], "model": model})
            want = ca.source_cumulants(1.0, 0.4, model)
            got = ca.source_cumulants(r["up"], r["down"], model)
            self.assertAlmostEqual(got[1], want[1], places=6, msg=model)
            self.assertAlmostEqual(got[2], want[2], places=6, msg=model)
            self.assertAlmostEqual(r["value"] + got[0], want[0], places=6, msg=model)


class CliTests(unittest.TestCase):
    def run_cli(self, sub, doc):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.json"
            path.write_text(json.dumps(doc))
            r = subprocess.run([sys.executable, "-I", str(SCRIPT), sub, "--input", str(path)], capture_output=True, text=True, timeout=120)
        return r.returncode, json.loads(r.stdout)

    def test_cli(self):
        code, out = self.run_cli("measurements", {"measurements": [{"value": 1.9, "plus": 0.7, "minus": 0.5},
                                                                    {"value": 2.4, "plus": 0.6, "minus": 0.8}]})
        self.assertEqual((code, out["status"]), (0, "combined"))
        # skewed in opposite directions and far apart: the two approximate likelihoods have no common domain
        code, out = self.run_cli("measurements", {"measurements": [{"value": 0.0, "plus": 1.0, "minus": 0.1},
                                                                    {"value": -2.0, "plus": 0.1, "minus": 1.0}]})
        self.assertEqual((code, out["status"]), (1, "failed"))
        code, out = self.run_cli("sources", {"value": "x", "sources": []})
        self.assertEqual((code, out["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()
