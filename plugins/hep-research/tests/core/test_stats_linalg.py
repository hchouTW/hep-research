"""Tests for core/stats/_linalg.py: the strict, scale-relative Cholesky shared by core/stats (no silent repair,
units do not change the verdict, semi-definite matrices only when the caller accepts them, and then with a record).
Run from the plugin root with `python3 -m unittest discover -s tests -t .`."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import _linalg  # noqa: E402
from core.stats._linalg import LinAlgError, cholesky  # noqa: E402


def product(l):
    n = len(l)
    return [[sum(l[i][k] * l[j][k] for k in range(n)) for j in range(n)] for i in range(n)]


class CholeskyTests(unittest.TestCase):
    C = [[4.0, 1.2, 0.4], [1.2, 9.0, -2.1], [0.4, -2.1, 1.0]]

    def test_factor_reproduces_the_matrix_and_scales_with_it(self):
        l, reg = cholesky(self.C, "c")
        self.assertIsNone(reg)
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(product(l)[i][j], self.C[i][j], places=12)
        for k in (1e-12, 1e12):
            lk, _ = cholesky([[v * k for v in row] for row in self.C], "c")
            for i in range(3):
                for j in range(i + 1):
                    self.assertAlmostEqual(lk[i][j] / math.sqrt(k), l[i][j], delta=1e-12 * max(1.0, abs(l[i][j])))

    def test_indefinite_matrix_raises_with_its_name_at_any_scale(self):
        bad = [[1.0, 2.0], [2.0, 1.0]]
        for k in (1e-12, 1.0, 1e12):
            with self.assertRaisesRegex(LinAlgError, "^my matrix is not positive semi-definite"):
                cholesky([[v * k for v in row] for row in bad], "my matrix", semidefinite=True)

    def test_negative_eigenvalue_beyond_the_relative_tolerance_raises(self):
        eps = 1e-8  # correlation 1 + eps: smallest eigenvalue -eps, far beyond 1e-10
        with self.assertRaises(LinAlgError):
            cholesky([[1.0, 1.0 + eps], [1.0 + eps, 1.0]], "c", semidefinite=True)

    def test_semidefinite_only_when_accepted_and_then_recorded(self):
        singular = [[1.0, 1.0], [1.0, 1.0]]
        with self.assertRaisesRegex(LinAlgError, "singular"):
            cholesky(singular, "c")
        l, reg = cholesky(singular, "c", semidefinite=True)
        self.assertEqual(reg["matrix"], "c")
        self.assertEqual(reg["pivots_shifted"], 1)
        self.assertLessEqual(reg["max_shift_relative_to_unit_diagonal"], 1e-10)
        self.assertAlmostEqual(product(l)[1][1], 1.0 + 1e-10, places=14)

    def test_zero_variance_rows(self):
        c = [[2.0, 0.0], [0.0, 0.0]]
        with self.assertRaisesRegex(LinAlgError, "zero diagonal"):
            cholesky(c, "c")
        l, _ = cholesky(c, "c", semidefinite=True)
        self.assertEqual(l[1], [0.0, 0.0])
        with self.assertRaisesRegex(LinAlgError, "zero variance but a nonzero covariance"):
            cholesky([[2.0, 0.1], [0.1, 0.0]], "c", semidefinite=True)

    def test_rejections(self):
        for bad in ([[float("nan"), 0.0], [0.0, 1.0]], [[-1.0, 0.0], [0.0, 1.0]], [[0.0, 0.0], [0.0, 0.0]]):
            with self.assertRaises(LinAlgError):
                cholesky(bad, "c", semidefinite=True)

    def test_caller_error_type(self):
        class MyError(ValueError):
            pass
        with self.assertRaises(MyError):
            cholesky([[1.0, 2.0], [2.0, 1.0]], "c", error=MyError)


class SharedHelperTests(unittest.TestCase):
    """The helpers T16 consolidated: each reports when it did not do its job."""
    DENSE = [[4.0, 1.0, 0.5, 0.2], [1.0, 3.0, 0.4, 0.1], [0.5, 0.4, 2.0, 0.3], [0.2, 0.1, 0.3, 1.0]]

    def test_jacobi_reports_convergence(self):
        info = {}
        values, vecs = _linalg.jacobi_eigh(self.DENSE, info=info)
        self.assertTrue(info["converged"])
        self.assertEqual(values, sorted(values))
        for k, lam in enumerate(values):  # A v = lambda v
            v = [vecs[i][k] for i in range(4)]
            av = [sum(self.DENSE[i][j] * v[j] for j in range(4)) for i in range(4)]
            for i in range(4):
                self.assertAlmostEqual(av[i], lam * v[i], places=12)
        short = {}
        _linalg.jacobi_eigh(self.DENSE, max_sweeps=1, info=short)
        self.assertFalse(short["converged"])
        self.assertEqual(short["sweeps"], 1)
        self.assertGreater(short["off_diagonal"], 0.0)

    def test_the_callers_report_non_convergence(self):
        from core.stats import unfolding_diagnostics as ud
        from core.stats.validate_covariance import _check_matrix, Report, DEFAULT_TOL
        with self.assertRaisesRegex(ud.ToyError, "did not converge"):
            ud._jacobi(self.DENSE, sweeps=1)
        import os
        original = _linalg.jacobi_eigh
        _linalg.jacobi_eigh = lambda m, max_sweeps=100, **kw: original(m, 1, **kw)  # one sweep: cannot converge
        os.environ["HEP_STATS_PURE_PYTHON"] = "1"
        try:
            rep = Report()
            metrics = _check_matrix("m", self.DENSE, DEFAULT_TOL, rep, "")
        finally:
            _linalg.jacobi_eigh = original
            del os.environ["HEP_STATS_PURE_PYTHON"]
        self.assertIn("eigen_not_converged", {w["code"] for w in rep.warnings})
        self.assertEqual(metrics["eigen_solver"], "jacobi")

    def test_numpy_and_rotation_eigenvalues_agree(self):
        import os
        import random
        rng = random.Random(4)
        n = 12
        a = [[rng.gauss(0, 1) for _ in range(n)] for _ in range(n)]
        c = [[sum(a[i][k] * a[j][k] for k in range(n)) - (3.0 if i == j else 0.0) for j in range(n)] for i in range(n)]
        info = {}
        fast, _ = _linalg.eigh(c, info=info)
        os.environ["HEP_STATS_PURE_PYTHON"] = "1"
        try:
            slow_info = {}
            slow, _ = _linalg.eigh(c, info=slow_info)
        finally:
            del os.environ["HEP_STATS_PURE_PYTHON"]
        self.assertEqual(slow_info["method"], "jacobi")
        top = max(abs(x) for x in slow)
        for x, y in zip(fast, slow):
            self.assertAlmostEqual(x, y, delta=1e-12 * top)

    def test_solve_reports_how_close_to_singular(self):
        info = {}
        x = _linalg.solve([[2.0, 1.0], [1.0, 3.0]], [[1.0], [2.0]], info=info)
        self.assertAlmostEqual(x[0][0], 0.2, places=14)
        self.assertAlmostEqual(x[1][0], 0.6, places=14)
        self.assertGreater(info["min_pivot_ratio"], 0.1)
        info = {}
        _linalg.solve([[1.0, 1.0], [1.0, 1.0 + 1e-12]], [[1.0], [1.0]], info=info)
        self.assertLess(info["min_pivot_ratio"], 1e-11)

        class MyError(ValueError):
            pass
        with self.assertRaisesRegex(MyError, "singular my matrix"):
            _linalg.solve([[1.0, 2.0], [2.0, 4.0]], [[1.0], [2.0]], error=MyError, what="my matrix")

    def test_bisect_refuses_an_unbracketed_root(self):
        self.assertAlmostEqual(_linalg.bisect(lambda x: x * x - 2.0, 0.0, 2.0, 80, increasing=True), 2 ** 0.5, places=12)
        self.assertAlmostEqual(_linalg.bisect(lambda x: 2.0 - x * x, 0.0, 2.0, 80, increasing=False), 2 ** 0.5, places=12)
        with self.assertRaisesRegex(LinAlgError, "not bracketed"):
            _linalg.bisect(lambda x: x - 5.0, 0.0, 2.0, 80, increasing=True)  # the root lies beyond hi
        from core.stats import likelihood_limits as ll
        with self.assertRaisesRegex(ll.LikelihoodError, "the limit is not bracketed"):
            ll._bisect(lambda s: s - 50.0, 0.0, 10.0)  # returned 10.0 silently before

    def test_one_owner_for_each_helper(self):
        from core.stats import likelihood_limits as ll
        from core.stats import statistical_toys as st
        from core.stats import template_fit as tf
        from core.stats import unfolding_diagnostics as ud
        self.assertIs(ud._matmul, _linalg.matmul)
        self.assertIs(st._golden_min, _linalg.golden_min)
        self.assertIs(st._chol_solve, _linalg.chol_solve)
        for mod, error in ((ll, ll.LikelihoodError), (st, st.ToyError)):
            with self.assertRaises(error):
                mod._num(float("nan"), "x")
        with self.assertRaises(ll.LikelihoodError):  # a singular profile-fit matrix raised ToyError before
            ll._solve([[0.0]], [[1.0]])
        with self.assertRaises(st.ToyError):
            tf._solve([[0.0]], [[1.0]])



try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


@unittest.skipUnless(np is not None, "NumPy not installed: the eigenvalue oracle is unverified")
class EigenvalueOracleTests(unittest.TestCase):
    """Independent oracle for sci-fix COV-NOREPAIR (axis C): the verdict of the strict Cholesky on random covariance
    matrices against numpy.linalg.eigvalsh of the unit-diagonal (correlation) matrix, written here without
    _linalg. Pivots and eigenvalues are different quantities, so only matrices clearly away from the boundary are
    judged: smallest correlation eigenvalue above +1e-6 must factorize, below -1e-6 must be refused; the band
    between is not asserted. Variances span 1e-12 to 1e12, so the verdict is also checked to be unit-free.
    Negative control: the pre-fix repair (absolute jitter added until a factorization succeeds) accepts the
    indefinite matrices that the oracle and the fix refuse."""

    @staticmethod
    def _jitter_repair(c):
        a = np.array(c, dtype=float)
        jitter = 1e-10
        while jitter <= 1.0:
            try:
                np.linalg.cholesky(a + jitter * np.eye(len(a)))
                return True
            except np.linalg.LinAlgError:
                jitter *= 10.0
        return False

    def test_verdict_matches_the_eigenvalues_at_any_scale(self):
        rng = np.random.default_rng(20261018)
        judged = {"pd": 0, "indefinite": 0}
        repaired_indefinite = 0
        for _ in range(400):
            n = int(rng.integers(2, 7))
            a = rng.normal(size=(n, n))
            corr = a @ a.T
            d = np.sqrt(np.diag(corr))
            corr = corr / np.outer(d, d)
            if rng.random() < 0.5:  # push one correlation past what the others allow
                i, j = rng.choice(n, size=2, replace=False)
                corr[i, j] = corr[j, i] = float(np.clip(corr[i, j] + rng.choice([-1.0, 1.0]) * rng.uniform(0.3, 1.5), -1.5, 1.5))
            lam = float(np.linalg.eigvalsh(corr).min())
            if abs(lam) <= 1e-6:
                continue
            sd = 10.0 ** rng.uniform(-6, 6, size=n)  # variances 1e-12 .. 1e12
            cov = (corr * np.outer(sd, sd)).tolist()
            if lam > 1e-6:
                judged["pd"] += 1
                cholesky(cov, "c")  # must not raise
            else:
                judged["indefinite"] += 1
                with self.assertRaises(LinAlgError):
                    cholesky(cov, "c")
                with self.assertRaises(LinAlgError):
                    cholesky(cov, "c", semidefinite=True)
                if self._jitter_repair(corr.tolist()):
                    repaired_indefinite += 1
        self.assertGreater(judged["pd"], 50)
        self.assertGreater(judged["indefinite"], 50)
        self.assertGreater(repaired_indefinite, 0)  # negative control: the old repair hides some of them


class ExhaustiveDefinitenessTests(unittest.TestCase):
    def test_verdict_over_every_rational_unit_diagonal_3x3(self):
        """Exhaustive oracle for sci-fix COV-NOREPAIR (ledger review, 2026-10-20): every symmetric 3x3 matrix with unit
        diagonal and off-diagonal entries in {-3/2, -1, -1/2, 0, 1/2, 1, 3/2} (343 matrices: 23 positive definite,
        26 singular semidefinite, 294 indefinite), classified exactly by sympy (is_positive_definite,
        is_positive_semidefinite). The strict Cholesky accepts exactly the definite ones; with semidefinite=True it
        also accepts the singular ones and refuses every indefinite one. Same verdicts with the variances scaled to
        1e-12, 1 and 1e12 (sd 1e-6, 1, 1e6)."""
        import itertools

        import sympy

        values = [sympy.Rational(k, 2) for k in range(-3, 4)]
        counts = {"pd": 0, "psd": 0, "indefinite": 0}
        for a, b, c in itertools.product(values, repeat=3):
            m = sympy.Matrix([[1, a, b], [a, 1, c], [b, c, 1]])
            kind = "pd" if m.is_positive_definite else ("psd" if m.is_positive_semidefinite else "indefinite")
            counts[kind] += 1
            want = {"pd": (True, True), "psd": (False, True), "indefinite": (False, False)}[kind]
            unit = [[float(x) for x in row] for row in m.tolist()]
            sd = (1e-6, 1.0, 1e6)
            scaled = [[unit[i][j] * sd[i] * sd[j] for j in range(3)] for i in range(3)]
            for cov in (unit, scaled):
                with self.subTest(a=a, b=b, c=c, kind=kind, scaled=cov is scaled):
                    self.assertEqual((self._accepts(cov), self._accepts(cov, semidefinite=True)), want)
        self.assertEqual(counts, {"pd": 23, "psd": 26, "indefinite": 294})

    @staticmethod
    def _accepts(cov, **kw):
        try:
            cholesky(cov, "c", **kw)
            return True
        except LinAlgError:
            return False


@unittest.skipUnless(np is not None, "NumPy not installed: the GLS oracle is unverified")
class GlsOracleTests(unittest.TestCase):
    """Second oracle kind for sci-fix COV-NOREPAIR (axis C): the generalized-least-squares constant fit that consumes
    the strict Cholesky (statistical_toys._gls_constant) against (1) the closed form for two points, mean =
    ((c22 - c12) r1 + (c11 - c12) r2) / (c11 + c22 - 2 c12), sigma^2 = det / (c11 + c22 - 2 c12) and chi2 =
    (r1 - r2)^2 / (c11 + c22 - 2 c12), and (2) numpy.linalg.solve (LU, not Cholesky) for 2 to 6 points, with
    variances 1e-12 to 1e12. Tolerance 1e-8 relative: double-precision solves of matrices whose correlation condition
    number is kept below 1e6. An indefinite matrix gets no fit (negative control in EigenvalueOracleTests)."""

    def test_fit_matches_the_closed_form_and_an_lu_solve_at_any_scale(self):
        from core.stats import statistical_toys as st
        rng = np.random.default_rng(20261020)
        for trial in range(200):
            n = 2 if trial < 60 else int(rng.integers(3, 7))
            a = rng.normal(size=(n, n))
            corr = a @ a.T + n * np.eye(n)
            d = np.sqrt(np.diag(corr))
            corr = corr / np.outer(d, d)
            if np.linalg.cond(corr) > 1e6:
                continue
            sd = 10.0 ** rng.uniform(-6, 6) * rng.uniform(0.5, 2.0, size=n)  # one scale: the points are comparable
            cov = corr * np.outer(sd, sd)
            r = rng.normal(size=n) * sd + 3.0
            mean, sigma, chi2 = st._gls_constant(r.tolist(), cov.tolist())
            if n == 2:
                c11, c12, c22 = cov[0, 0], cov[0, 1], cov[1, 1]
                den = c11 + c22 - 2.0 * c12
                want = (((c22 - c12) * r[0] + (c11 - c12) * r[1]) / den, math.sqrt((c11 * c22 - c12 ** 2) / den),
                        (r[0] - r[1]) ** 2 / den)
            else:
                ones = np.ones(n)
                ci1, cir = np.linalg.solve(cov, ones), np.linalg.solve(cov, r)
                m = float(ones @ cir / (ones @ ci1))
                res = r - m
                want = (m, float(1.0 / math.sqrt(ones @ ci1)), float(res @ np.linalg.solve(cov, res)))
            for got, ref, what in zip((mean, sigma, chi2), want, ("mean", "sigma", "chi2")):
                self.assertAlmostEqual(got, ref, delta=1e-8 * max(abs(ref), sd.max() if what != "chi2" else 1.0),
                                       msg=(trial, n, what))


if __name__ == "__main__":
    unittest.main()
