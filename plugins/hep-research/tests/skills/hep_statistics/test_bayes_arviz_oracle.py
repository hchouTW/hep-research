"""hep-statistics audit T24: bayes_diagnostics.py against a pinned ArviZ release (0.23.4) and on cases where a
diagnostic must not report health. SYNTHETIC chains (independent Gaussian, AR(1) with phi = 0.9, ties, heavy tails,
two modes with chains stuck in each, one shifted chain). Tolerances (fixed by the algorithm, which follows Vehtari et
al. 2021 like ArviZ): R-hat 1e-3 absolute (observed: identical), bulk and tail ESS and quantile MCSE 1e-9 relative.
Constant chains: ArviZ reports ESS = draws for a chain that never moves; this script reports undefined diagnostics
and not-converged instead, deliberately stricter than the oracle. Without ArviZ 0.23.4 the ArviZ comparison is
skipped (unverified); the health checks and the independent SciPy oracle (IndependentOracle) always run."""
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


def split(x):
    h = x.shape[1] // 2
    return np.concatenate([x[:, :h], x[:, x.shape[1] - h:]])


def z_scale(x):
    """Rank normalization from SciPy primitives (average ranks over ties, Blom offsets, norm.ppf)."""
    from scipy.stats import norm, rankdata
    return norm.ppf((rankdata(x, method="average").reshape(x.shape) - 0.375) / (x.size + 0.25))


def rhat(x):
    n = x.shape[1]
    return np.sqrt((n * x.mean(axis=1).var(ddof=1) / x.var(axis=1, ddof=1).mean() + n - 1) / n)


def rho_hat(x):
    """Multi-chain autocorrelation (Vehtari et al. 2021, eq. 10) from direct sums, not an FFT; rho_0 = 1."""
    m, n = x.shape
    c = x - x.mean(axis=1, keepdims=True)
    acov = np.array([[c[j, : n - t] @ c[j, t:] / n for t in range(n)] for j in range(m)])
    w = acov[:, 0].mean() * n / (n - 1)
    rho = 1 - (w - acov.mean(axis=0)) / (w * (n - 1) / n + x.mean(axis=1).var(ddof=1))
    rho[0] = 1.0
    return rho


def ess(x):
    """Geyer's pair sums P_k = rho_2k + rho_2k+1 up to the first P_k <= 0 (or Stan's bound, the last pair below
    n - 1), made monotone by a running minimum, plus the improved last term: that last pair's even element if
    positive."""
    m, n = x.shape
    rho, last = rho_hat(x), (n - 3) // 2
    pairs = []
    for k in range(last + 1):
        pair = rho[2 * k] + rho[2 * k + 1]
        if pair <= 0 or k == last:
            break
        pairs.append(pair)
    tau = -1 + 2 * np.minimum.accumulate(pairs).sum() + max(rho[2 * k], 0.0)
    return m * n / max(tau, 1 / np.log10(m * n))


def ess_pre_fix(x):
    """The ESS of d161b3b7^ (the pre-fix behaviour): pairs up to the first negative one, no last term."""
    m, n = x.shape
    rho = rho_hat(x)
    total, prev = 0.0, np.inf
    for k in range(n // 2):
        pair = rho[2 * k] + rho[2 * k + 1]
        if pair < 0:
            break
        prev = min(pair, prev)
        total += prev
    return m * n / max(-1 + 2 * total, 1 / np.log10(m * n))


def mcse_quantile(x, p, ess_of=ess):
    """Vehtari et al. 2021: the 68.27% Beta interval of the quantile's rank (scipy.stats.beta); undefined (None)
    when the indicator is constant."""
    from scipy.stats import beta, norm
    e = ess_of(split((x <= np.quantile(x, p)).astype(float)))
    if not np.isfinite(e):
        return None
    lo, hi = beta.ppf([norm.cdf(-1), norm.cdf(1)], e * p + 1, e * (1 - p) + 1)
    s = np.sort(x.ravel())
    return (s[int(np.ceil(min(hi * s.size - 1, s.size - 1)))] - s[int(np.floor(max(lo * s.size - 1, 0)))]) / 2


def mcse_pre_fix(x, p):
    e = ess_pre_fix(split((x <= np.quantile(x, p)).astype(float)))
    if not np.isfinite(e):
        return None
    se = np.sqrt(p * (1 - p) / e)
    lo, hi = np.quantile(x, [max(p - se, 0.0), min(p + se, 1.0)])
    return (hi - lo) / 2


class IndependentOracle(unittest.TestCase):
    """Runs without ArviZ: R-hat, bulk and tail ESS and quantile MCSE against an implementation written from
    Vehtari et al. 2021 with SciPy primitives (rankdata, norm.ppf, beta.ppf), direct-sum autocovariances and
    Geyer's pair sums, not the script's FFT, Acklam quantile and index loop. Agreement to 1e-12 relative (observed
    1e-14). Negative control: the pre-fix ESS and MCSE (d161b3b7^, emulated here) miss the reference by 0.5% to 11%
    on the poorly mixed cases, and pre-fix constant chains reported R-hat = 1.0."""

    def test_diagnostics_match_the_reference_and_the_pre_fix_rules_do_not(self):
        missed = []
        for k, x in cases().items():
            with self.subTest(case=k):
                r = bd.diagnose_param(x, (0.05, 0.5, 0.95))
                xs = split(x)
                ref_rhat = max(rhat(z_scale(xs)), rhat(z_scale(split(np.abs(x - np.median(x))))))
                self.assertAlmostEqual(r["rhat"], ref_rhat, delta=1e-12)
                q05, q95 = np.quantile(x, [0.05, 0.95])
                tails = [split((x <= q05).astype(float)), split((x >= q95).astype(float))]
                for name, got, ref, pre in (
                        ("bulk", r["ess_bulk"], ess(z_scale(xs)), ess_pre_fix(z_scale(xs))),
                        ("tail", r["ess_tail"], min(map(ess, tails)), min(map(ess_pre_fix, tails)))):
                    self.assertAlmostEqual(got / ref, 1.0, delta=1e-12, msg=name)
                    missed.append((k, name, abs(pre / ref - 1)))
                for p in (0.05, 0.5, 0.95):
                    got, ref = r["quantiles"][str(p)]["mcse"], mcse_quantile(x, p)
                    if ref is None or ref == 0.0:
                        self.assertIn(got, (None, 0.0), p)
                        continue
                    self.assertAlmostEqual(got / ref, 1.0, delta=1e-12, msg=p)
                    missed.append((k, f"mcse {p}", abs(mcse_pre_fix(x, p) / ref - 1)))
        big = [m for m in missed if m[2] > 1e-3]
        self.assertGreater(len(big), 15, big)
        self.assertTrue({"bulk", "tail"} <= {m[1] for m in big}, big)

    def test_invariance_under_affine_and_increasing_maps_and_chain_order(self):
        """Rank-based diagnostics: ESS (bulk, tail) and the quantile indicators are unchanged by any strictly
        increasing map; R-hat (the folded part uses |x - median|) by a positive scaling, under which the MCSE scales by
        the factor (4: exact in floating point). Reordering chains changes nothing. A general affine map such as
        2.5 x - 7 can break by rounding the exact tie of the two middle draws in |x - median| (two ranks move by 1/2):
        R-hat then moves by about 6e-6 (iid case), hence 1e-4 there."""
        for k, x in cases().items():
            with self.subTest(case=k):
                r = bd.diagnose_param(x)
                for f in (np.arctan, np.cbrt, lambda v: np.exp(v / 4)):
                    t = bd.diagnose_param(f(x))
                    self.assertAlmostEqual(t["ess_bulk"] / r["ess_bulk"], 1.0, delta=1e-9)
                    self.assertAlmostEqual(t["ess_tail"] / r["ess_tail"], 1.0, delta=1e-9)
                a = bd.diagnose_param(4.0 * x)
                self.assertEqual(a["rhat"], r["rhat"])
                for p, q in r["quantiles"].items():
                    if q["mcse"] is None:
                        self.assertIsNone(a["quantiles"][p]["mcse"])
                    else:
                        self.assertEqual(a["quantiles"][p]["mcse"], 4.0 * q["mcse"])
                self.assertAlmostEqual(bd.diagnose_param(2.5 * x - 7.0)["rhat"], r["rhat"], delta=1e-4)
                o = bd.diagnose_param(x[::-1])
                self.assertAlmostEqual(o["rhat"], r["rhat"], delta=1e-12)
                self.assertAlmostEqual(o["ess_bulk"] / r["ess_bulk"], 1.0, delta=1e-12)


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
