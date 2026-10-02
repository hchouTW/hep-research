"""adapters/pyhf-combine: the pyhf counting workspace runs with pyhf, and its asymptotic CLs limit agrees with an
independent profile-likelihood implementation (scipy) of the same model. SYNTHETIC workspace (s=5, b=20, n=20,
10% background normsys). Skipped, and therefore unverified, where pyhf is not installed."""
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "adapters" / "pyhf-combine" / "assets" / "pyhf-counting.json"
try:
    import numpy as np
    import pyhf
    from scipy.optimize import brentq, minimize_scalar
    from scipy.stats import norm
    HAVE = True
except ImportError:
    HAVE = False

S, B, N = 5.0, 20.0, 20


def _b(alpha):  # pyhf normsys default interpolation (code 1): exponential in alpha
    return B * (1.1 ** alpha if alpha >= 0 else 0.9 ** (-alpha))


def _nll(mu, alpha, n):
    lam = mu * S + _b(alpha)
    return lam - n * math.log(lam) + math.lgamma(n + 1) + 0.5 * alpha ** 2


def _profile(mu, n):
    return minimize_scalar(lambda a: _nll(mu, a, n), bounds=(-5, 5), method="bounded", options={"xatol": 1e-10}).fun


def _global(n):
    best = minimize_scalar(lambda m: _profile(m, n), bounds=(0, 10), method="bounded", options={"xatol": 1e-10})
    return best.x, best.fun


def _qtilde(mu, n):
    mu_hat, nll_hat = _global(n)
    return 0.0 if mu_hat > mu else max(2 * (_profile(mu, n) - nll_hat), 0.0)


def independent_cls_limit(n_obs, cl=0.95):
    n_asimov = B  # background-only Asimov data (alpha = 0)

    def cls(mu):
        q, qa = _qtilde(mu, n_obs), _qtilde(mu, n_asimov)
        sq, sqa = math.sqrt(q), math.sqrt(qa)
        clsb = 1 - norm.cdf(sq)
        clb = norm.cdf(sqa - sq)
        return clsb / clb - (1 - cl)
    return brentq(cls, 0.5, 6.0, xtol=1e-6)


@unittest.skipUnless(HAVE, "pyhf, numpy or scipy not installed")
class PyhfCountingTests(unittest.TestCase):
    def test_workspace_is_valid_and_synthetic_numbers_match_the_doc(self):
        ws = pyhf.Workspace(json.loads(WS.read_text(encoding="utf-8")))
        m = ws.model()
        self.assertEqual(m.config.poi_name, "mu")
        self.assertEqual(ws.data(m, include_auxdata=False), [N])

    def test_asymptotic_cls_limit_matches_independent_implementation(self):
        ws = pyhf.Workspace(json.loads(WS.read_text(encoding="utf-8")))
        m = ws.model()
        obs, exp = pyhf.infer.intervals.upper_limits.upper_limit(ws.data(m), m, scan=np.linspace(0, 5, 501), level=0.05)
        ref = independent_cls_limit(N)
        self.assertAlmostEqual(float(obs), ref, delta=0.01)
        self.assertAlmostEqual(float(obs), 2.153, delta=0.002)  # value documented with the legacy Combine template
        self.assertAlmostEqual(float(exp[2]), float(obs), delta=1e-6)  # n equals b, so observed = median expected


if __name__ == "__main__":
    unittest.main()
