"""T22: saturated-model goodness of fit of the shape-limit model (likelihood_limits.py shape-gof). The statistic
follows chi-square(bins - 1) at moderate counts, the toy p-value is uniform under the null at low counts (where the
chi-square reference is not), the statistic equals an independent Poisson deviance without nuisances, and a distorted
spectrum is rejected."""
import contextlib
import io
import json
import math
import random
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402
from core.stats.statistical_toys import chi2_sf  # noqa: E402

B = [30.0, 25.0, 20.0, 15.0, 10.0]
S = [2.0, 4.0, 6.0, 4.0, 2.0]
NUIS = [{"name": "bn", "kind": "background_norm", "sigma": 0.1},
        {"name": "sh", "kind": "background_shape", "up": [33, 26, 20, 14, 8], "down": [27, 24, 20, 16, 12]}]


def model(b, s, nuis):
    bins, parsed, chol = ll._load_shape({"bins": [{"n": 1, "b": x, "s": y} for x, y in zip(b, s)], "nuisances": nuis})
    return ll._ShapeModel(bins, parsed, chol)


class GofTests(unittest.TestCase):
    def test_null_distribution_is_chi2_at_moderate_counts(self):
        m = model(B, S, NUIS)
        rng = random.Random(1)
        ts = []
        for _ in range(500):
            ns = [ppf(rng.random(), b + s) for b, s in zip(B, S)]
            aux = [rng.gauss(0.0, 1.0) for _ in range(m.k)]  # auxiliary measurements fluctuate around the truth too
            ts.append(ll._gof_stat(m, ns, aux, None)[0])
        # 5 bins, mu fitted: 4 degrees of freedom (each nuisance brings one parameter and one auxiliary measurement)
        self.assertLess(abs(statistics.fmean(ts) - 4.0), 0.4)
        self.assertLess(abs(sum(chi2_sf(t, 4) < 0.05 for t in ts) / len(ts) - 0.05), 0.03)

    def test_toy_p_value_is_uniform_at_low_counts(self):
        b, s = [3.0, 2.5, 2.0, 1.5, 1.0], [0.4, 0.8, 1.2, 0.8, 0.4]
        rng = random.Random(5)
        ps = []
        for i in range(200):
            ns = [ppf(rng.random(), x + y) for x, y in zip(b, s)]
            doc = {"bins": [{"n": n, "b": x, "s": y} for n, x, y in zip(ns, b, s)], "nuisances": NUIS[:1]}
            ps.append(ll.shape_gof(doc, 150, 1000 + i)["toy_p_value"])
        # binomial standard deviations for 200 data sets: 0.021 and 0.035
        self.assertLess(abs(sum(p <= 0.1 for p in ps) / len(ps) - 0.1), 0.06)
        self.assertLess(abs(sum(p <= 0.5 for p in ps) / len(ps) - 0.5), 0.1)

    def test_equals_an_independent_deviance_without_nuisances(self):
        ns = [35, 22, 30, 14, 6]
        doc = {"bins": [{"n": n, "b": b, "s": s} for n, b, s in zip(ns, B, S)]}
        nu = [1.5 * s + b for s, b in zip(S, B)]
        dev = 2.0 * sum(v - n + (n * math.log(n / v) if n else 0.0) for n, v in zip(ns, nu))
        r = ll.shape_gof(doc, 0, 1, mu=1.5)
        self.assertAlmostEqual(r["statistic"], dev, places=6)
        self.assertEqual(r["asymptotic_chi2_reference"]["ndf"], 5)
        free = ll.shape_gof(doc, 0, 1)
        self.assertLessEqual(free["statistic"], dev + 1e-9)  # fitting mu can only lower it

    def test_a_distorted_spectrum_is_rejected(self):
        ns = [55, 30, 20, 8, 2]  # far steeper than any allowed background shape
        doc = {"bins": [{"n": n, "b": b, "s": s} for n, b, s in zip(ns, B, S)], "nuisances": NUIS}
        r = ll.shape_gof(doc, 300, 2)
        self.assertLess(r["toy_p_value"], 0.02)
        self.assertLess(r["asymptotic_chi2_reference"]["p_value"], 0.02)
        good = ll.shape_gof(dict(doc, bins=[{"n": round(b + s), "b": b, "s": s} for b, s in zip(B, S)]), 300, 2)
        self.assertGreater(good["toy_p_value"], 0.5)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "g.json"
            path.write_text(json.dumps({"bins": [{"n": n, "b": b, "s": s} for n, b, s in zip([33, 30, 24, 18, 12], B, S)]}))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = ll.main(["shape-gof", "--input", str(path), "--toys", "100", "--seed", "4"])
        out = json.loads(buf.getvalue())
        self.assertEqual((code, out["status"], out["toys"]), (0, "ok", 100))


if __name__ == "__main__":
    unittest.main()
