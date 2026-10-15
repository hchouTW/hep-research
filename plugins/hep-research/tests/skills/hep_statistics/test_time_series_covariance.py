"""WP2: the time-bin covariance recipe of skills/hep-statistics/references/time-series-inference.md, on SYNTHETIC data.

The recipe (section "Time-bin covariance"): C = C_stat + C_tind + C_tdep for one flux series F_t in T time bins, with
C_stat diagonal, C_tind = sum_k a_k a_k^T with a_k = delta_k F (a time-independent relative uncertainty, fully
correlated in time, rank one per source) and C_tdep = sum_j D_j R_j D_j with D_j = diag(eps_j F) and a valid time
correlation R_j[t, t'] = exp(-|t - t'| / tau_j) (tau -> 0: independent bins; tau -> infinity: fully correlated).

Checked here, all on a synthetic series (no experiment's numbers): the blocks add up and pass
core/stats/validate_covariance.py; the total is positive definite; the time-independent block is rank one per source
with correlation exactly 1; the two limits of tau; the exponential correlation on equally spaced bins is AR(1) (its
inverse is tridiagonal); the time-independent part does not average down over bins while the statistical part does;
it cancels in a ratio of two time bins; seeded toys drawn from C reproduce the variance of the mean; and a
nearest-neighbour-only correlation of 0.7 (a common invalid shortcut) is not positive semi-definite and is refused by
the validator. Tolerances are set before running.

No helper script: the construction is a few lines of linear algebra, so the test implements the documented recipe
itself (build_time_covariance below) rather than adding a builder to a fit script."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
VALIDATOR = PLUGIN / "core" / "stats" / "validate_covariance.py"
REFERENCE = PLUGIN / "skills" / "hep-statistics" / "references" / "time-series-inference.md"

try:
    import numpy as np
    HAVE_NP = True
except ImportError:  # pragma: no cover
    HAVE_NP = False


def exp_correlation(times, tau):
    """R[t, t'] = exp(-|t - t'| / tau); tau = 0 gives the identity, tau = inf a matrix of ones."""
    dt = np.abs(np.subtract.outer(times, times))
    if tau == 0:
        return np.eye(len(times))
    if np.isinf(tau):
        return np.ones_like(dt)
    return np.exp(-dt / tau)


def build_time_covariance(flux, stat, rel_tind, rel_tdep, times):
    """The documented recipe. flux, stat: length-T arrays; rel_tind: list of relative uncertainties (scalar or length
    T) fully correlated in time; rel_tdep: list of (relative uncertainty, tau). Returns the blocks and their sum."""
    flux = np.asarray(flux, float)
    blocks = {"stat": np.diag(np.asarray(stat, float) ** 2)}
    tind = np.zeros((len(flux), len(flux)))
    for delta in rel_tind:
        a = np.broadcast_to(np.asarray(delta, float), flux.shape) * flux
        tind += np.outer(a, a)
    blocks["time_independent"] = tind
    tdep = np.zeros_like(tind)
    for eps, tau in rel_tdep:
        d = np.broadcast_to(np.asarray(eps, float), flux.shape) * flux
        tdep += np.outer(d, d) * exp_correlation(times, tau)
    blocks["time_dependent"] = tdep
    return blocks, sum(blocks.values())


def synthetic_series(T=24):
    t = np.arange(T, dtype=float)                       # equally spaced bins, unit spacing
    flux = 100.0 * (1.0 + 0.2 * np.sin(2 * np.pi * t / 11.0))  # a smooth synthetic variation
    stat = 0.01 * flux                                   # 1% statistical
    return t, flux, stat


def run_validator(matrix, blocks=None):
    doc = {"labels": [f"t{i}" for i in range(len(matrix))], "matrix": np.asarray(matrix).tolist(),
           "kind": "absolute", "units": "flux^2"}
    if blocks is not None:
        doc["blocks"] = {k: v.tolist() for k, v in blocks.items()}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cov.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(VALIDATOR), str(path)], capture_output=True, text=True, timeout=120)
    return proc.returncode, json.loads(proc.stdout)


@unittest.skipUnless(HAVE_NP, "needs NumPy")
class TimeBinCovariance(unittest.TestCase):
    def setUp(self):
        self.t, self.flux, self.stat = synthetic_series()
        # two time-independent sources (3% and 2%), one drift with a 6-bin correlation time (1.5%)
        self.blocks, self.C = build_time_covariance(self.flux, self.stat, [0.03, 0.02], [(0.015, 6.0)], self.t)

    def test_reference_states_the_recipe(self):
        text = REFERENCE.read_text(encoding="utf-8")
        for needle in ("C_tind", "C_tdep", "exp(-|t - t'| / tau)", "test_time_series_covariance.py"):
            self.assertIn(needle, text)

    def test_blocks_add_up_and_pass_the_validator(self):
        code, out = run_validator(self.C, self.blocks)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["errors"], [])
        # expected and documented: the fully correlated block is rank deficient on its own; nothing else is flagged
        self.assertEqual([w["code"] for w in out["warnings"]], ["block.time_independent.rank_deficient"])
        self.assertTrue(np.allclose(self.C, self.C.T))
        self.assertGreater(np.linalg.eigvalsh(self.C).min(), 0.0)  # positive definite: invertible for a chi2

    def test_time_independent_block_is_fully_correlated(self):
        _, one = build_time_covariance(self.flux, np.zeros_like(self.flux), [0.03], [], self.t)
        self.assertEqual(np.linalg.matrix_rank(one, tol=1e-9 * one.max()), 1)
        sd = np.sqrt(np.diag(one))
        self.assertTrue(np.allclose(one / np.outer(sd, sd), 1.0, atol=1e-12))
        # two constant fractions of the same F add in quadrature into one rank-one term
        both = self.blocks["time_independent"]
        self.assertTrue(np.allclose(both, (0.03 ** 2 + 0.02 ** 2) * np.outer(self.flux, self.flux)))
        # a source whose fraction varies with time adds a second direction; still singular on its own,
        # the statistical part is what makes the total invertible
        frac = 0.02 * (1.0 + 0.5 * self.t / self.t.max())
        b, _ = build_time_covariance(self.flux, self.stat, [0.03, frac], [], self.t)
        self.assertEqual(np.linalg.matrix_rank(b["time_independent"], tol=1e-9 * self.C.max()), 2)

    def test_limits_of_the_correlation_time(self):
        d = 0.015 * self.flux
        _, zero = build_time_covariance(self.flux, np.zeros_like(d), [], [(0.015, 0.0)], self.t)
        self.assertTrue(np.allclose(zero, np.diag(d ** 2)))
        _, near0 = build_time_covariance(self.flux, np.zeros_like(d), [], [(0.015, 1e-3)], self.t)
        self.assertLess(np.abs(near0 - np.diag(d ** 2)).max(), 1e-12 * d.max() ** 2)
        _, inf = build_time_covariance(self.flux, np.zeros_like(d), [], [(0.015, np.inf)], self.t)
        self.assertTrue(np.allclose(inf, np.outer(d, d)))
        _, big = build_time_covariance(self.flux, np.zeros_like(d), [], [(0.015, 1e6)], self.t)
        self.assertLess(np.abs(big - np.outer(d, d)).max() / d.max() ** 2, 1e-4)

    def test_exponential_correlation_is_ar1(self):
        tau = 6.0
        R = exp_correlation(self.t, tau)
        phi = np.exp(-1.0 / tau)
        self.assertTrue(np.allclose(R[0], phi ** self.t))
        P = np.linalg.inv(R)
        off = np.abs(np.triu(P, 2)).max()
        self.assertLess(off, 1e-10 * np.abs(P).max())  # AR(1): precision matrix is tridiagonal

    def test_correlated_part_does_not_average_down(self):
        T = len(self.flux)
        w = np.full(T, 1.0 / T)
        var_tind = w @ self.blocks["time_independent"] @ w
        expected = (0.03 ** 2 + 0.02 ** 2) * self.flux.mean() ** 2
        self.assertAlmostEqual(var_tind / expected, 1.0, places=12)
        var_stat = w @ self.blocks["stat"] @ w
        self.assertAlmostEqual(var_stat, np.sum(self.stat ** 2) / T ** 2, places=12)
        # doubling the number of bins (same flux per bin) halves the statistical part, leaves the correlated one
        t2, f2, s2 = synthetic_series(2 * T)
        b2, _ = build_time_covariance(f2, s2, [0.03, 0.02], [], t2)
        w2 = np.full(2 * T, 1.0 / (2 * T))
        self.assertAlmostEqual((w2 @ b2["time_independent"] @ w2) / ((0.03 ** 2 + 0.02 ** 2) * f2.mean() ** 2), 1.0,
                               places=12)

    def test_time_independent_part_cancels_in_a_ratio(self):
        i, j = 3, 15
        g = np.zeros(len(self.flux))  # Jacobian of r = F_i / F_j
        g[i] = 1.0 / self.flux[j]
        g[j] = -self.flux[i] / self.flux[j] ** 2
        self.assertLess(abs(g @ self.blocks["time_independent"] @ g), 1e-12 * (g @ self.C @ g))
        self.assertGreater(g @ self.blocks["time_dependent"] @ g, 0.0)

    def test_toys_reproduce_the_variance_of_the_mean(self):
        rng = np.random.default_rng(20261015)
        toys = rng.multivariate_normal(self.flux, self.C, size=20000)
        T = len(self.flux)
        w = np.full(T, 1.0 / T)
        predicted = w @ self.C @ w
        observed = np.var(toys @ w, ddof=1)
        # relative standard error of a sample variance from 20,000 Gaussian draws is sqrt(2/19999) ~ 1%; allow 5 sigma
        self.assertLess(abs(observed / predicted - 1.0), 0.05)

    def test_nearest_neighbour_shortcut_is_not_psd(self):
        T = 20
        d = np.full(T, 1.0)
        bad = np.eye(T) + 0.7 * (np.eye(T, k=1) + np.eye(T, k=-1))
        # tridiagonal Toeplitz eigenvalues 1 + 2 rho cos(k pi / (T + 1)): negative once rho > 1 / (2 cos(pi/(T+1)))
        self.assertLess(np.linalg.eigvalsh(bad).min(), 0.0)
        code, out = run_validator(np.outer(d, d) * bad)
        self.assertEqual(code, 1)
        self.assertTrue(any(e["code"].endswith("not_psd") for e in out["errors"]), out["errors"])
        ok = np.eye(T) + 0.4 * (np.eye(T, k=1) + np.eye(T, k=-1))  # below 1/2: positive definite
        self.assertGreater(np.linalg.eigvalsh(ok).min(), 0.0)


if __name__ == "__main__":
    unittest.main()
