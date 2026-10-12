"""hep-statistics audit T24: bayes_diagnostics.py against a pinned ArviZ release (0.23.4) and on cases where a
diagnostic must not report health. SYNTHETIC chains (independent Gaussian, AR(1) with phi = 0.9, ties, heavy tails,
two modes with chains stuck in each, one shifted chain). Tolerances (fixed by the algorithm, which follows Vehtari et
al. 2021 like ArviZ): R-hat 1e-3 absolute (observed: identical), bulk and tail ESS and quantile MCSE 1e-9 relative.
Constant chains: ArviZ reports ESS = draws for a chain that never moves; this script reports undefined diagnostics
and not-converged instead, deliberately stricter than the oracle. Without ArviZ 0.23.4 the oracle comparison is
skipped (unverified); the health checks always run."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import bayes_diagnostics as bd  # noqa: E402

try:
    import arviz as az
    ARVIZ = az.__version__ == "0.23.4"
except ImportError:
    ARVIZ = False


def cases():
    rng = np.random.default_rng(1)

    def ar1(phi, c=4, n=1000):
        x, e = np.zeros((c, n)), rng.standard_normal((c, n))
        for i in range(1, n):
            x[:, i] = phi * x[:, i - 1] + e[:, i]
        return x
    return {"iid": rng.standard_normal((4, 1000)), "ar1": ar1(0.9), "ties": rng.integers(0, 3, (4, 1000)).astype(float),
            "heavy_tails": rng.standard_cauchy((4, 1000)),
            "two_modes_stuck": np.concatenate([rng.normal(-3, 1, (2, 1000)), rng.normal(3, 1, (2, 1000))]),
            "shifted_chain": rng.standard_normal((4, 1000)) + np.array([[0], [0], [0], [0.5]])}


class Health(unittest.TestCase):
    def test_unhealthy_chains_are_never_converged(self):
        c = cases()
        expected = {"iid": "converged", "heavy_tails": "converged", "ties": "converged", "ar1": "not-converged",
                    "two_modes_stuck": "not-converged", "shifted_chain": "not-converged"}
        for k, x in c.items():
            r = bd.diagnose_param(x)
            self.assertEqual(bd.classify(r), expected[k], k)
        const = bd.diagnose_param(np.ones((4, 1000)))
        self.assertEqual(bd.classify(const), "not-converged")
        self.assertTrue(np.isnan(const["rhat"]))
        self.assertEqual(const["constant_chains"], 4)
        one_stuck = c["iid"].copy()
        one_stuck[2] = 0.3
        self.assertEqual(bd.classify(bd.diagnose_param(one_stuck)), "not-converged")

    def test_ties_do_not_crash_and_undefined_mcse_is_flagged(self):
        r = bd.diagnose_param(np.random.default_rng(2).integers(0, 2, (4, 500)).astype(float), (0.05, 0.5, 0.99))
        self.assertIsNone(r["quantiles"]["0.99"]["mcse"])
        self.assertTrue(any("undefined" in f for f in r["flags"]))


@unittest.skipUnless(ARVIZ, "ArviZ 0.23.4 not installed: the oracle comparison is unverified")
class ArviZOracle(unittest.TestCase):
    def test_rhat_ess_and_mcse_match(self):
        for k, x in cases().items():
            with self.subTest(case=k):
                r = bd.diagnose_param(x, (0.05, 0.5, 0.95))
                self.assertLessEqual(abs(r["rhat"] - float(az.rhat(x, method="rank"))), 1e-3)
                self.assertAlmostEqual(r["ess_bulk"] / float(az.ess(x, method="bulk")), 1.0, delta=1e-9)
                self.assertAlmostEqual(r["ess_tail"] / float(az.ess(x, method="tail")), 1.0, delta=1e-9)
                for p in (0.05, 0.5, 0.95):
                    a = float(az.mcse(x, method="quantile", prob=p))
                    ours = r["quantiles"][str(p)]["mcse"]
                    if a == 0.0 or ours is None:
                        self.assertIn(ours, (0.0, None))
                    else:
                        self.assertAlmostEqual(ours / a, 1.0, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
