"""Tests for core/stats/_linalg.py: the strict, scale-relative Cholesky shared by core/stats (no silent repair,
units do not change the verdict, semi-definite matrices only when the caller accepts them, and then with a record).
Run from the plugin root with `python3 -m unittest discover -s tests -t .`."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
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


if __name__ == "__main__":
    unittest.main()
