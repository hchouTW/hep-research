"""Geant4 program A1, evidence of the three S1 entries (docs/evidence/sci-fixes.json): GEANT4-BATCH-MEANS-SE,
GEANT4-LOW-COUNT-EXACT and GEANT4-MPV-ESTIMATOR. Each has two independent oracle kinds, an invariant test and a
negative control that emulates the pre-fix estimator inside the test.

Oracles never import the expected values from core: they come from SciPy and SymPy (their own definitions), NumPy's
least-squares polynomial fit, exact rational arithmetic (fractions) over finite domains, and exact enumeration of
binomial outcomes. Needs the core scientific stack (requirements-core.txt: numpy, scipy, sympy)."""
import math
import random
import sys
import unittest
from fractions import Fraction
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.stats import batch_means as M  # noqa: E402


class BatchMeansSE(unittest.TestCase):
    """GEANT4-BATCH-MEANS-SE: theta = mean of K block estimates, SE = sd/sqrt(K) on K - 1 dof, t intervals."""

    def test_against_scipy_sem_and_t_interval(self):
        """Third-party definition: scipy.stats.sem and scipy.stats.t.interval of the block estimates."""
        from scipy import stats
        rng = random.Random(3)
        for k in (2, 3, 16, 31, 64):
            for _ in range(20):
                th = [rng.gauss(5.0, 2.0) for _ in range(k)]
                r = M.batch_mean(th)
                self.assertAlmostEqual(r["se"], stats.sem(th), delta=1e-12 * max(1.0, stats.sem(th)))
                for cl in (0.6827, 0.90, 0.95):
                    lo, hi = stats.t.interval(cl, k - 1, loc=r["value"], scale=stats.sem(th))
                    h = M.t_halfwidth(r["se"], r["dof"], cl)
                    self.assertAlmostEqual(r["value"] - h, lo, delta=1e-9 * max(1.0, abs(lo)))
                    self.assertAlmostEqual(r["value"] + h, hi, delta=1e-9 * max(1.0, abs(hi)))

    def test_t_halfwidth_has_its_coverage_under_sympy_student_t(self):
        """Symbolic third party: sympy.stats.StudentT gives P(|T| <= t_halfwidth(1, nu, c)) = c."""
        import sympy
        from sympy.stats import StudentT, cdf
        for nu in (3, 15, 30):
            F = cdf(StudentT("T", nu))
            for cl in (0.6827, 0.90):
                h = M.t_halfwidth(1.0, nu, cl)
                got = float(sympy.N(F(sympy.Float(h, 30)) - F(sympy.Float(-h, 30)), 30))
                self.assertAlmostEqual(got, cl, delta=1e-9)

    def test_invariants(self):
        """Shift invariance, scale equivariance and permutation invariance of (value, SE)."""
        rng = random.Random(4)
        th = [rng.gauss(0, 1) for _ in range(16)]
        r = M.batch_mean(th)
        for c in (-3.0, 0.5, 1e6):
            s = M.batch_mean([x + c for x in th])
            self.assertAlmostEqual(s["se"], r["se"], delta=1e-9 * (1 + abs(c)) * r["se"])
            g = M.batch_mean([x * c for x in th])
            self.assertAlmostEqual(g["se"], abs(c) * r["se"], delta=1e-9 * abs(c) * r["se"])
        rng.shuffle(th)
        self.assertAlmostEqual(M.batch_mean(th)["se"], r["se"], delta=1e-15)

    def test_negative_control_the_pre_fix_event_bootstrap_undercovers_correlated_blocks(self):
        """Negative control emulating the pre-fix SE (a bootstrap of the events) on runs whose events are correlated
        within a block (a block offset of sd 1 on noise of sd 1, K = 16, B = 50): the event bootstrap SE is about
        sd/sqrt(N) and its 90 % intervals cover far below 0.90; batch means cover at 0.90 (a general result the
        coverage oracle checks)."""
        import numpy as np
        rng = np.random.default_rng(5)
        k, b, toys = 16, 50, 400
        cov_bm = cov_boot = 0
        t90 = M.t_halfwidth(1.0, k - 1, 0.90)
        for _ in range(toys):
            x = rng.normal(0.0, 1.0, (k, 1)) + rng.normal(0.0, 1.0, (k, b))
            r = M.batch_mean(x.mean(axis=1))
            cov_bm += abs(r["value"]) <= t90 * r["se"]
            flat = x.ravel()
            boot = [rng.choice(flat, flat.size).mean() for _ in range(100)]  # the pre-fix seeded event bootstrap
            cov_boot += abs(flat.mean()) <= 1.645 * float(np.std(boot, ddof=1))
        sigma = math.sqrt(0.9 * 0.1 / toys)
        self.assertLessEqual(abs(cov_bm / toys - 0.90), 0.02 + 3 * sigma, cov_bm / toys)
        self.assertLess(cov_boot / toys, 0.60, cov_boot / toys)


class LowCountExact(unittest.TestCase):
    """GEANT4-LOW-COUNT-EXACT: Clopper-Pearson for proportions and the conditional binomial for a rate ratio."""

    @staticmethod
    def binom_pmf(k, n, p):
        return math.comb(n, k) * p ** k * (1 - p) ** (n - k)

    def test_coverage_by_exact_enumeration(self):
        """Exhaustive: for n = 1..30 and p on a grid, the probability over every outcome k = 0..n that the 90 %
        interval covers p is at least 0.90; the rate-ratio interval covers r at least 0.90 for every total N = 1..25
        (exact enumeration of n1 given N)."""
        cl = 0.90
        for n in range(1, 31):
            ivs = [M.exact_proportion(k, n, cl) for k in range(n + 1)]
            for p in [i / 50 for i in range(1, 50)]:
                cov = sum(self.binom_pmf(k, n, p) for k, (lo, hi) in enumerate(ivs) if lo <= p <= hi)
                self.assertGreaterEqual(cov, cl - 1e-9, (n, p))
        for total in range(1, 26):
            ivs = [M.rate_ratio_interval(n1, total - n1, cl) for n1 in range(total + 1)]
            for r in (0.2, 0.5, 1.0, 2.0, 5.0):
                q = r / (1 + r)
                cov = sum(self.binom_pmf(n1, total, q) for n1, (lo, hi) in enumerate(ivs) if lo <= r <= hi)
                self.assertGreaterEqual(cov, cl - 1e-9, (total, r))

    def test_against_scipy_binomtest(self):
        """Third-party definition: scipy.stats.binomtest(k, n).proportion_ci(method='exact')."""
        from scipy import stats
        for n in (1, 5, 17, 99):
            for k in range(n + 1):
                ci = stats.binomtest(k, n).proportion_ci(confidence_level=0.90, method="exact")
                lo, hi = M.exact_proportion(k, n, 0.90)
                self.assertAlmostEqual(lo, ci.low, delta=1e-9)
                self.assertAlmostEqual(hi, ci.high, delta=1e-9)

    def test_invariants(self):
        """Complement symmetry: the interval of k in n mirrors that of n - k; nesting in the confidence level."""
        for n in (3, 10, 40):
            for k in range(n + 1):
                lo, hi = M.exact_proportion(k, n, 0.9)
                lo2, hi2 = M.exact_proportion(n - k, n, 0.9)
                self.assertAlmostEqual(lo, 1 - hi2, delta=1e-12)
                self.assertAlmostEqual(hi, 1 - lo2, delta=1e-12)
                w68, w95 = M.exact_proportion(k, n, 0.6827), M.exact_proportion(k, n, 0.95)
                self.assertTrue(w95[0] <= lo <= w68[0] and w68[1] <= hi <= w95[1])

    def test_negative_control_the_pre_fix_normal_interval_undercovers(self):
        """Negative control emulating the pre-fix proportion SE (sqrt(max(p(1-p), 1/n^2)/n), normal 90 % interval)
        by the same exact enumeration: at n = 20, p = 0.05 it covers far below 0.90."""
        n, p = 20, 0.05
        cov = 0.0
        for k in range(n + 1):
            ph = k / n
            se = math.sqrt(max(ph * (1 - ph), 1 / n ** 2) / n)
            if ph - 1.645 * se <= p <= ph + 1.645 * se:
                cov += self.binom_pmf(k, n, p)
        self.assertLess(cov, 0.75)


class MpvEstimator(unittest.TestCase):
    """GEANT4-MPV-ESTIMATOR: the vertex of the parabola through the fullest bin and its neighbours."""

    def test_vertex_against_numpy_polyfit(self):
        """Third-party algorithm: numpy.polyfit of degree 2 through the three bin centres (an exact interpolation)."""
        import numpy as np
        rng = random.Random(6)
        for _ in range(500):
            counts = [rng.randint(0, 40) for _ in range(9)]
            k = max(range(9), key=lambda i: (counts[i], -i))
            if k in (0, 8) or counts[k - 1] - 2 * counts[k] + counts[k + 1] == 0:
                continue
            lo, w = rng.uniform(-1, 1), rng.uniform(0.001, 2.0)
            xs = [lo + (k + d + 0.5) * w for d in (-1, 0, 1)]
            a, b, _ = np.polyfit(xs, counts[k - 1:k + 2], 2)
            self.assertAlmostEqual(M.block_mode(counts, lo, w)["value"], -b / (2 * a), delta=1e-9 * (1 + abs(b / a)))

    def test_vertex_by_exact_linear_algebra_over_a_finite_domain(self):
        """Exhaustive: every triple (y-, y0, y+) in 0..12 with y0 the strict or lowest-index maximum and a
        non-zero curvature: the vertex from the closed form equals the stationary point of the interpolating
        parabola solved by Gaussian elimination in exact rationals (bins of width 1 from 0, fullest bin 1)."""
        n = 0
        for ym in range(13):
            for y0 in range(13):
                for yp in range(13):
                    if not (y0 >= ym and y0 > yp and y0 >= max(ym, yp)) or ym - 2 * y0 + yp == 0 or y0 == ym:
                        continue
                    rows = [[Fraction(x * x), Fraction(x), Fraction(1), Fraction(y)]
                            for x, y in ((Fraction(1, 2), ym), (Fraction(3, 2), y0), (Fraction(5, 2), yp))]
                    for c in range(3):
                        piv = next(r for r in range(c, 3) if rows[r][c] != 0)
                        rows[c], rows[piv] = rows[piv], rows[c]
                        for r in range(3):
                            if r != c and rows[r][c] != 0:
                                f = rows[r][c] / rows[c][c]
                                rows[r] = [a - f * b for a, b in zip(rows[r], rows[c])]
                    a, b = rows[0][3] / rows[0][0], rows[1][3] / rows[1][1]
                    want = float(-b / (2 * a))
                    got = M.block_mode([ym, y0, yp, 0], 0.0, 1.0)["value"]
                    self.assertAlmostEqual(got, want, delta=1e-12, msg=(ym, y0, yp))
                    n += 1
        self.assertGreater(n, 500)

    def test_invariants(self):
        """Translation equivariance (shifting the counts by j bins moves the mode by j w) and invariance under scaling
        all counts; the vertex stays within the fullest bin's neighbours."""
        rng = random.Random(7)
        for _ in range(200):
            counts = [rng.randint(1, 30) for _ in range(7)]
            r = M.block_mode(counts, 0.0, 0.5)
            if r["fallback"]:
                continue
            for j in (1, 3):
                self.assertAlmostEqual(M.block_mode([0] * j + counts, 0.0, 0.5)["value"], r["value"] + j * 0.5,
                                       delta=1e-12)
            self.assertAlmostEqual(M.block_mode([7 * c for c in counts], 0.0, 0.5)["value"], r["value"], delta=1e-12)
            k = max(range(7), key=lambda i: (counts[i], -i))
            self.assertLessEqual(abs(r["value"] - (k + 0.5) * 0.5), 0.5 + 1e-12)

    def test_negative_control_the_pre_fix_five_point_fit_is_biased_on_a_landau_peak(self):
        """Negative control emulating the pre-fix MPV (least-squares parabola through the fullest bin and two bins on
        each side) on the exact expected bin contents of J14's peak (Moyal, mode 0.085 MeV, width 1.5 xi; CDF
        erfc(exp(-l/2)/sqrt(2))) with 2 keV bins: at infinite statistics its bias exceeds tol/10 = 0.002 for every bin
        phase, while the three-point vertex stays below it."""
        mode, xi, w = 0.085, 1.5 * 0.00535, 0.002

        def cdf(x):
            return math.erfc(math.exp(-((x - mode) / xi) / 2) / math.sqrt(2))

        for i in range(20):
            lo = 0.05 + i / 20 * w
            edges = [lo + j * w for j in range(80)]
            p = [cdf(b) - cdf(a) for a, b in zip(edges, edges[1:])]
            k = max(range(len(p)), key=p.__getitem__)
            xs, ys = range(-2, 3), [p[k + x] for x in range(-2, 3)]
            sx2, sx4 = sum(x * x for x in xs), sum(x ** 4 for x in xs)
            b1 = sum(x * y for x, y in zip(xs, ys)) / sx2
            a2 = (5 * sum(x * x * y for x, y in zip(xs, ys)) - sx2 * sum(ys)) / (5 * sx4 - sx2 * sx2)
            old = lo + (k + 0.5 - b1 / (2 * a2)) * w
            new = M.block_mode(p, lo, w)["value"]
            self.assertGreater((old - mode) / mode, 0.002)
            self.assertLess((new - mode) / mode, 0.002)


if __name__ == "__main__":
    unittest.main()
