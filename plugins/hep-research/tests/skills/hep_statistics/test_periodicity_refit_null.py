"""sci-fix PERIODICITY-REFIT: periodicity_scan.py's red-noise global p refits the null on every surrogate.

Releases 0.14.0-0.23.0 drew the AR(1)/OU surrogates from phi (or tau) estimated once from the observed series; the
lag-1 estimate is biased low on short series, the surrogates are too white, and the p-value was anti-conservative
(no-signal AR(1) toys, n = 50, phi = 0.9: 0.253 rejected at alpha = 0.1). The default is now a double parametric
bootstrap (prepivoting, Cavaliere, Goncalves and Nielsen, arXiv:2208.02028v1, section 3.2.2, pp. 14-15) with the
first-order bias-corrected lag-1 estimate for ar1.

Oracles (expected values never come from the module):
- analytic (locator): under the null a valid p-value is uniform, P(p <= alpha) = alpha (arXiv:2208.02028v1 p. 8: "a
  test that rejects H0 whenever H_n(p_n) <= alpha is exact"; Theorem 3.2, p. 15); toys are AR(1) series drawn with
  scipy.signal.lfilter, not with the module;
- independent implementation (locator): the double bootstrap of section 3.2.2 written here from the source with
  scipy.signal.lfilter surrogates and the power by batched weighted least squares (not the Zechmeister-Kuerster closed
  form of the module), compared with the module's p on one series within a Monte Carlo tolerance;
- invariant: the size does not depend on the nuisance phi (pivotality), same toys;
- negative control: the pre-fix single-level p, re-implemented here, is anti-conservative on the same toys.
Tolerances were fixed before the first run: binomial, 3 sigma per cell (fast and slow calibration), and 0.05 for the
implementation comparison (about 4 combined Monte Carlo standard deviations at N = 1999, inner 199). Inputs SYNTHETIC.
Slow tier (HEP_SLOW_TESTS=1): the calibration over AR(1) n 50-100, phi 0.3-0.9 and OU, 400 toys each."""
import inspect
import math
import os
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "periodicity_scan.py"
sys.path.insert(0, str(SCRIPT.parent))
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

try:
    import numpy as np
    from scipy.signal import lfilter
    HAVE = True
except ImportError:  # pragma: no cover
    HAVE = False


def ar1_toys(rng, n, phi, m):
    """m stationary AR(1) series (n x m), unit variance, by scipy.signal.lfilter (x_i = phi x_{i-1} + u_i)."""
    u = rng.normal(0.0, math.sqrt(1 - phi * phi), (n, m))
    u[0] = rng.normal(0.0, 1.0, m)  # stationary start: x_0 ~ N(0, 1)
    return lfilter([1.0], [1.0, -phi], u, axis=0)


def ls_band_max(t, e, freqs):
    """Band-maximum of 1 - chi2(c + a cos + b sin) / chi2(c), each fit by weighted least squares (batched normal
    equations), for every column of Y."""
    w = 1.0 / e ** 2
    A = np.stack([np.cos(2 * np.pi * freqs[:, None] * t), np.sin(2 * np.pi * freqs[:, None] * t),
                  np.ones((len(freqs), len(t)))], axis=1)  # F x 3 x n
    G = np.einsum("fin,n,fjn->fij", A, w, A)

    def band_max(Y):
        ybar = (w @ Y) / w.sum()
        chi0 = w @ (Y - ybar) ** 2
        B = np.einsum("fin,n,nm->fim", A, w, Y)
        coef = np.linalg.solve(G, B)
        chi1 = (w @ (Y * Y))[None, :] - np.einsum("fim,fim->fm", coef, B)
        return (1 - chi1 / chi0).max(axis=0)
    return band_max


def lag1(Y, e, correct):
    """The declared ar1 null estimator: lag-1 autocorrelation about the weighted mean, optionally with the
    first-order correction + (1 + 4 phi) / n, clipped to [-0.99, 0.99]."""
    w = 1.0 / e ** 2
    r = Y - (w @ Y) / w.sum()
    phi = (r[:-1] * r[1:]).sum(axis=0) / (r * r).sum(axis=0)
    if correct:
        phi = phi + (1 + 4 * phi) / Y.shape[0]
    return np.clip(phi, -0.99, 0.99)


def double_bootstrap_p(rng, t, e, y, freqs, n_outer, n_inner):
    """arXiv:2208.02028v1 section 3.2.2 for a statistic that rejects when large: p1 = P*(T* >= T),
    p1*_j = P**(T** >= T*_j) under the null refitted on outer sample j, p = P*(p1* <= p1); Monte Carlo (1 + #)/(1 + B)."""
    band_max = ls_band_max(t, e, freqs)
    T = float(band_max(y[:, None])[0])
    phi = float(lag1(y[:, None], e, True)[0])
    outer = ar1_toys(rng, len(t), phi, n_outer)
    T1 = band_max(outer)
    p1 = (1 + np.sum(T1 >= T)) / (1 + n_outer)
    phis = lag1(outer, e, True)
    p_star = np.array([(1 + np.sum(band_max(ar1_toys(rng, len(t), float(ph), n_inner)) >= T1[j])) / (1 + n_inner)
                       for j, ph in enumerate(phis)])
    return float((1 + np.sum(p_star <= p1)) / (1 + n_outer))


def single_level_p(rng, t, e, y, freqs, n_outer):
    """Negative control: the pre-fix procedure (phi estimated once, no correction, no refit)."""
    band_max = ls_band_max(t, e, freqs)
    T = float(band_max(y[:, None])[0])
    phi = float(lag1(y[:, None], e, False)[0])
    return float((1 + np.sum(band_max(ar1_toys(rng, len(t), phi, n_outer)) >= T)) / (1 + n_outer))


_CACHE: dict = {}


def module_rates(n, phi, toys, n_outer, n_inner, seed, with_control=False):
    """Rejection fractions of the module's default p (and of the negative control) on lfilter AR(1) toys."""
    key = (n, phi, toys, n_outer, n_inner, seed, with_control)
    if key in _CACHE:
        return _CACHE[key]
    import periodicity_scan as ps
    rng = np.random.default_rng(seed)
    t, e = np.arange(n, dtype=float), np.ones(n)
    freqs = np.linspace(1.0 / (n - 1), 0.5, math.ceil(2.5 * n))
    ys = ar1_toys(rng, n, phi, toys)
    # the default path of the module; the inner count is passed only where the module has it (a parent record runs
    # this test on releases without the refit, whose scan() takes no such argument)
    kw = {"inner": n_inner} if "inner" in inspect.signature(ps.scan).parameters else {}
    p_mod, p_ctl = [], []
    for k in range(toys):
        p_mod.append(ps.scan(t, ys[:, k], e, freqs, None, "ar1", n_outer, seed * 1000 + k, **kw)["global"]["p"])
        if with_control:
            p_ctl.append(single_level_p(rng, t, e, ys[:, k], freqs, n_outer))
    rates = {a: sum(p <= a + 1e-12 for p in p_mod) / toys for a in (0.01, 0.05, 0.1)}
    ctl = {a: sum(p <= a + 1e-12 for p in p_ctl) / toys for a in (0.01, 0.05, 0.1)} if with_control else None
    _CACHE[key] = (rates, ctl)
    return rates, ctl


def bound(alpha, toys, k=3.0):
    return alpha + k * math.sqrt(alpha * (1 - alpha) / toys)


@unittest.skipUnless(HAVE, "NumPy and SciPy needed")
class RefitCalibration(unittest.TestCase):
    TOYS = 150

    def test_size_is_at_most_alpha_on_short_red_series(self):
        """Analytic oracle: P(p <= alpha) = alpha under the null, 3-sigma binomial bound per alpha (AR(1), n = 50,
        phi = 0.9, 150 toys, 99 x 99 surrogates). Negative control: the pre-fix single-level p on the same toys."""
        rates, ctl = module_rates(50, 0.9, self.TOYS, 99, 99, 21, with_control=True)
        for a in (0.05, 0.1):
            with self.subTest(alpha=a):
                self.assertLessEqual(rates[a], bound(a, self.TOYS), rates)
        # the control is asserted at alpha = 0.1 only: at 0.05 its excess (0.093 on the first run) is below the
        # 3-sigma bound of 150 toys (VALIDATION PERIODICITY-REFIT)
        self.assertGreater(ctl[0.1], bound(0.1, self.TOYS), ("the negative control must be caught", ctl))

    def test_size_does_not_depend_on_phi(self):
        """Invariant (pivotality): at n = 50 the size at alpha = 0.1 is the same for phi = 0.3 and 0.9 within
        3 binomial sigma of the difference."""
        r9, _ = module_rates(50, 0.9, self.TOYS, 99, 99, 21, with_control=True)
        r3, _ = module_rates(50, 0.3, self.TOYS, 99, 99, 22)
        self.assertLessEqual(abs(r9[0.1] - r3[0.1]), 3 * math.sqrt(2 * 0.1 * 0.9 / self.TOYS), (r3, r9))


@unittest.skipUnless(HAVE, "NumPy and SciPy needed")
class IndependentDoubleBootstrap(unittest.TestCase):
    def test_module_p_matches_the_double_bootstrap_of_the_source(self):
        """Independent implementation: one AR(1) series (n = 50, phi = 0.9), N = 1999 outer and 199 inner surrogates
        in both; |p_module - p_independent| <= 0.05."""
        import periodicity_scan as ps
        n = 50
        rng = np.random.default_rng(31)
        y = ar1_toys(rng, n, 0.9, 1)[:, 0]
        t, e = np.arange(n, dtype=float), np.ones(n)
        freqs = np.linspace(1.0 / (n - 1), 0.5, math.ceil(2.5 * n))
        p_ind = double_bootstrap_p(np.random.default_rng(32), t, e, y, freqs, 1999, 199)
        p_mod = ps.scan(t, y, e, freqs, None, "ar1", 1999, 33)["global"]["p"]
        self.assertLessEqual(abs(p_mod - p_ind), 0.05, (p_mod, p_ind))


@unittest.skipUnless(HAVE and SLOW, "slow: set HEP_SLOW_TESTS=1")
class RefitCalibrationSlow(unittest.TestCase):
    """The calibration study of VALIDATION PERIODICITY-REFIT in the slow tier: 400 toys per configuration, 199 x 199
    surrogates, 3-sigma binomial bound per alpha (15 cells per method)."""
    TOYS = 400

    def test_ar1_size_at_most_alpha(self):
        for n, phi, seed in ((50, 0.7, 41), (50, 0.9, 42), (100, 0.9, 43)):
            rates, ctl = module_rates(n, phi, self.TOYS, 199, 199, seed, with_control=(n, phi) == (50, 0.9))
            for a in (0.01, 0.05, 0.1):
                with self.subTest(n=n, phi=phi, alpha=a):
                    self.assertLessEqual(rates[a], bound(a, self.TOYS), rates)
            if ctl is not None:
                self.assertGreater(ctl[0.1], bound(0.1, self.TOYS), ("negative control", ctl))

    def test_ou_size_at_most_alpha(self):
        import periodicity_scan as ps
        rng = np.random.default_rng(44)
        n, phi = 50, 0.8
        tau = -1.0 / math.log(phi)
        rej = {a: 0 for a in (0.01, 0.05, 0.1)}
        for k in range(self.TOYS):
            t = np.sort(rng.uniform(0, n, n))
            x = np.empty(n)
            x[0] = rng.normal()
            for i in range(1, n):  # exact OU transition over each gap
                a = math.exp(-(t[i] - t[i - 1]) / tau)
                x[i] = a * x[i - 1] + math.sqrt(1 - a * a) * rng.normal()
            freqs = np.linspace(1.0 / (t[-1] - t[0]), 0.5, math.ceil(2.5 * n))
            p = ps.scan(t, x, np.ones(n), freqs, None, "ou", 199, 44_000 + k)["global"]["p"]
            for a in rej:
                rej[a] += p <= a + 1e-12
        for a, r in rej.items():
            with self.subTest(alpha=a):
                self.assertLessEqual(r / self.TOYS, bound(a, self.TOYS), rej)


if __name__ == "__main__":
    unittest.main()
