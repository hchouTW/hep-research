"""T22: profile-likelihood contours of two signal strengths (likelihood_limits.py contour). Coverage of the Wilks
2-dof regions from toys at the true point, and the contour checked point by point against an independent Poisson
deviance."""
import contextlib
import io
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402

BINS = [{"n": 0, "b": 60.0, "s1": 20.0, "s2": 5.0}, {"n": 0, "b": 50.0, "s1": 10.0, "s2": 10.0},
        {"n": 0, "b": 60.0, "s1": 5.0, "s2": 20.0}, {"n": 0, "b": 40.0, "s1": 8.0, "s2": 8.0}]
TRUE = (1.0, 1.0)


def deviance(ns, nus):
    return 2.0 * sum(nu - n + (n * math.log(n / nu) if n > 0 else 0.0) for n, nu in zip(ns, nus))


class CoverageTests(unittest.TestCase):
    def coverage(self, nuisances, toys, seed):
        doc = {"bins": [dict(x, n=1) for x in BINS], "nuisances": nuisances}
        bins1, bins2, nuis, chol = ll._load_two_poi(doc)
        model = ll._TwoPoiModel(bins1, bins2, nuis, chol)
        sig, bkg = model.means(*TRUE, [0.0] * model.k)
        rng = random.Random(seed)
        hits = {0.6827: 0, 0.95: 0}
        for _ in range(toys):
            ns = [ppf(rng.random(), a + b) for a, b in zip(sig, bkg)]
            aux = [rng.gauss(0.0, 1.0) for _ in range(model.k)]
            q = model.q(*TRUE, ns, aux)
            for c in hits:
                hits[c] += q <= -2.0 * math.log(1.0 - c)
        return {c: h / toys for c, h in hits.items()}

    def test_wilks_regions_cover(self):
        for nuisances, seed in (([], 3), ([{"name": "bn", "kind": "background_norm", "sigma": 0.1}], 4)):
            cov = self.coverage(nuisances, 2000, seed)
            # binomial errors 0.0104 and 0.0049
            self.assertLess(abs(cov[0.6827] - 0.6827), 0.035, (nuisances, cov))
            self.assertLess(abs(cov[0.95] - 0.95), 0.015, (nuisances, cov))


class ContourTests(unittest.TestCase):
    DOC = {"bins": [{"n": 92, "b": 60.0, "s1": 20.0, "s2": 5.0}, {"n": 64, "b": 50.0, "s1": 10.0, "s2": 10.0},
                    {"n": 79, "b": 60.0, "s1": 5.0, "s2": 20.0}, {"n": 61, "b": 40.0, "s1": 8.0, "s2": 8.0}]}

    def test_points_sit_on_the_level_of_an_independent_deviance(self):
        r = ll.profile_contour(self.DOC, (0.6827, 0.95), 24)
        ns = [x["n"] for x in self.DOC["bins"]]
        nus = lambda a, b: [a * x["s1"] + b * x["s2"] + x["b"] for x in self.DOC["bins"]]
        best = deviance(ns, nus(r["best_fit"]["mu1"], r["best_fit"]["mu2"]))
        # the best fit is a minimum of the independent deviance
        for d1, d2 in ((1e-3, 0), (-1e-3, 0), (0, 1e-3), (0, -1e-3)):
            self.assertGreaterEqual(deviance(ns, nus(r["best_fit"]["mu1"] + d1, r["best_fit"]["mu2"] + d2)), best - 1e-9)
        for c, v in r["contours"].items():
            self.assertEqual(len(v["points"]), 24, c)
            for x, y in v["points"]:
                self.assertAlmostEqual(deviance(ns, nus(x, y)) - best, v["q_level"], delta=2e-4, msg=(c, x, y))
        self.assertNotIn("rays_not_closed", r)
        self.assertGreater(r["covariance_from_hessian"][0][0], 0)

    def test_a_nuisance_widens_the_contour(self):
        plain = ll.profile_contour(self.DOC, (0.95,), 12)
        wide = ll.profile_contour(dict(self.DOC, nuisances=[{"kind": "background_norm", "sigma": 0.15}]), (0.95,), 12)
        area = lambda pts: 0.5 * abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))))
        self.assertGreater(area(wide["contours"]["0.95"]["points"]), 1.2 * area(plain["contours"]["0.95"]["points"]))

    def test_cli_and_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps(self.DOC))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = ll.main(["contour", "--input", str(path), "--cl", "0.9", "--rays", "8"])
        out = json.loads(buf.getvalue())
        self.assertEqual((code, out["status"], list(out["contours"])), (0, "ok", ["0.9"]))
        for bad in ({"bins": [{"n": 1, "b": 1.0, "s1": 1.0, "s2": 1.0}]},
                    dict(self.DOC, nuisances=[{"kind": "signal_shape", "up": [1] * 4, "down": [1] * 4}]),
                    {"bins": [{"n": 1, "b": 1.0, "s": 1.0}, {"n": 1, "b": 1.0, "s": 1.0}]}):
            with self.assertRaises(ll.LikelihoodError):
                ll.profile_contour(bad)


if __name__ == "__main__":
    unittest.main()
