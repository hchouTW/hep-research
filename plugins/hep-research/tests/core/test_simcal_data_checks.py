"""The locking-stage checks of calib_data (Part B sections 2.1, 9.2; phase 2, WP4): resolution and rounding, shapes
and totals, guaranteed enclosures and the data-side constraint check."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import data_checks as D  # noqa: E402


class Resolution(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(D.unit(3.14159, {"kind": "fixed", "decimals": 2}), 0.01)
        self.assertAlmostEqual(D.unit(123.4, {"kind": "significant", "digits": 3}), 1.0)
        self.assertAlmostEqual(D.unit(9.87, {"kind": "significant", "digits": 3}), 0.01)
        self.assertEqual(D.unit(5.0, {"kind": "float64"}), 0.0)
        self.assertGreater(D.unit(5.0, {"kind": "float32"}), 0.0)
        self.assertEqual(D.resolution(37.0, 6.0, {"kind": "count"}), 0.0)     # integer counts: no rounding

    def test_signed_near_zero_uses_window_maximum(self):
        """One significant digit, nominal near 0: rho from the largest magnitude within +-5 sigma (section 15.2)."""
        rho = D.resolution(0.001, 0.02, {"kind": "significant", "digits": 1})
        self.assertAlmostEqual(rho, 0.1)                 # max |.| = 0.101 -> unit 0.1, not 0.001


class Rounding(unittest.TestCase):
    def test_single_observable_boundary(self):
        """rho <= 0.2 sigma for a single observable."""
        self.assertTrue(D.rounding_ratio(np.eye(1), np.array([0.2]), np.ones(1))["passed"])
        self.assertFalse(D.rounding_ratio(np.eye(1), np.array([0.21]), np.ones(1))["passed"])

    def test_pair_boundary(self):
        """Correlation c, rho/sigma = r each: the condition is 1 - |c| >= 25 r^2, both signs (section 2.1)."""
        for r in (0.02, 0.05, 0.1, 0.15, 0.19):          # (at r = 0.2 the boundary is c = 0)
            cb = 1 - 25 * r * r
            for sgn in (1, -1):
                for c, ok in ((cb - 1e-6, True), (cb + 1e-6, False)):
                    C = np.array([[1, sgn * c], [sgn * c, 1]])
                    self.assertEqual(D.rounding_ratio(C, np.array([r, r]), np.ones(2))["passed"], ok)

    def test_rejections_of_section_15_3_5(self):
        """Efficiency to two decimals with sigma = 0.001; a pair each legal alone with correlation 0.999."""
        self.assertFalse(D.rounding_ratio(np.eye(1) * 1e-6, np.array([0.01]), np.array([1e-3]))["passed"])
        C = np.array([[1, 0.999], [0.999, 1]])
        self.assertTrue(D.rounding_ratio(np.eye(1), np.array([0.15]), np.ones(1))["passed"])
        self.assertFalse(D.rounding_ratio(C, np.array([0.15, 0.15]), np.ones(2))["passed"])

    def test_double_precision_observable(self):
        """A double-precision observable with zero partial correlation does not change the ratio; direct correlation c
        raises it by 1 / (1 - c^2) (section 8.7 note 2)."""
        base = D.rounding_ratio(np.eye(1), np.array([0.1]), np.ones(1))["ratio"]
        same = D.rounding_ratio(np.eye(2), np.array([0.1, 0.0]), np.ones(2))["ratio"]
        self.assertAlmostEqual(base, same)
        c = 0.6
        C = np.array([[1, c], [c, 1]])
        up = D.rounding_ratio(C, np.array([0.1, 0.0]), np.ones(2))["ratio"]
        self.assertAlmostEqual(up / base, 1 / (1 - c * c), places=9)

    def test_rotation_invariance(self):
        rng = np.random.default_rng(1)
        Q = np.linalg.qr(rng.normal(size=(4, 4)))[0]
        C = Q @ np.diag([1.0, 1.0, 2.0, 2.0]) @ Q.T
        s = np.sqrt(np.diag(C))
        a = D.rounding_ratio(C, 0.05 * s, s)["ratio"]
        P = np.eye(4)[[1, 0, 3, 2]]
        b = D.rounding_ratio(P @ C @ P.T, 0.05 * (P @ s), P @ s)["ratio"]
        self.assertAlmostEqual(a, b, places=10)

    def test_sigma_zero_rules(self):
        with self.assertRaises(D.CheckError):
            D.rounding_ratio(np.diag([1.0, 0.0]), np.array([0.1, 0.01]), np.array([1.0, 0.0]))
        r = D.rounding_ratio(np.diag([1.0, 0.0]), np.array([0.1, 0.0]), np.array([1.0, 0.0]))
        self.assertTrue(r["passed"])                     # sigma0 = rho = 0 removed before standardization

    def test_constraint_projection(self):
        """With N_d,c the decision is on N_d,c^perp: t = p1 + p2 without projection is infinite (exact constraint
        direction with rounding), with projection finite."""
        Tm = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        C = Tm @ np.eye(2) @ Tm.T
        s = np.sqrt(np.diag(C))
        rho = 0.05 * s
        self.assertEqual(D.rounding_ratio(C, rho, s)["ratio"], math.inf)
        self.assertTrue(D.rounding_ratio(C, rho, s, [np.array([1.0, 1.0, -1.0])])["passed"])

    def test_shared_rounding_m2(self):
        """m = 2 derived quantities sharing one rounding: the difference (m - 1) rho^2/12 is 1/300 = 0.33% of the
        smallest allowed variance 25 rho^2 (section 8.7 note 2)."""
        rho = 0.1
        self.assertAlmostEqual(((2 - 1) * rho * rho / 12) / (25 * rho * rho), 1 / 300)

    def test_vertex_catches_violation_at_prior_edge(self):
        """A ratio monotone in theta, violated only at the upper prior edge: the vertices of the evaluation points
        catch it while the interior scan points pass (section 15.3.5)."""
        pts = D.evaluation_points([(0.0, 1.0)], np.array([[0.2], [0.5], [0.8]]), {})

        def at(th, nu):
            sigma = 1.0 - 0.85 * th[0]                    # the noise shrinks with theta: rounding grows relative
            r = D.rounding_ratio(np.eye(1) * sigma ** 2, np.array([0.04]), np.array([sigma]))
            return {"value": r["ratio"], "passed": r["passed"]}
        worst = D.worst_over_points(pts, at)
        self.assertFalse(worst["passed"])
        self.assertEqual(worst["theta"], [1.0])
        inner = D.worst_over_points([(np.array([0.8]), {})], at)
        self.assertTrue(inner["passed"])

    def test_evaluation_points_nuisance_axes(self):
        pts = D.evaluation_points([(0, 1), (0, 1)], np.zeros((2, 2)), {"nu0": 1.0, "eta0": 0.5})
        self.assertEqual(len(pts), (2 + 4) * (1 + 4))


class Shapes(unittest.TestCase):
    def test_merging_and_rejection(self):
        E = np.array([[30.0, 8.0, 6.0, 50.0, 40.0], [28.0, 9.0, 7.0, 45.0, 44.0]])
        r = D.n_min_and_merging(E)
        self.assertTrue(r["passed"])
        self.assertLess(r["K"], 5)
        self.assertTrue(all(E[:, g].sum(axis=1).min() >= 20 for g in r["groups"]))
        bad = D.n_min_and_merging(np.array([[5.0, 4.0]]))
        self.assertEqual(bad["finding"], "data.n_min")

    def test_merging_depends_on_expectations_only(self):
        """The representation never changes in toys: merging is a function of the expectations (section 15.2)."""
        E = np.array([[30.0, 8.0, 6.0, 50.0]])
        self.assertEqual(D.n_min_and_merging(E)["groups"], D.n_min_and_merging(E.copy())["groups"])

    def test_totals_and_block_conversion(self):
        self.assertEqual(D.n_exp_check([12.0, 9.5])["finding"], "data.n_exp")
        self.assertTrue(D.n_exp_check([12.0, 10.0])["passed"])
        self.assertTrue(D.block_conversion(counts_by_point=[6.0, 5.0])["passed"])
        self.assertFalse(D.block_conversion(binomial_by_point=[[100, 0.97]])["passed"])


class Enclosures(unittest.TestCase):
    def test_linear_is_exact(self):
        """For linear f the enclosure is exactly sum |df/dx_k| u_k / 2 (section 9.2)."""
        r = D.enclosure(lambda a, b: 2 * a - 3 * b, [1.23, 4.56], [0.01, 0.01])
        self.assertAlmostEqual(r["half"], 0.5 * (2 * 0.01 + 3 * 0.01), places=12)

    def test_nonlinear_is_a_bound(self):
        rng = np.random.default_rng(2)
        f = (lambda a, b: a * b / (a + b))
        x, u = [3.21, 1.87], [0.01, 0.01]
        r = D.enclosure(f, x, u)
        fx = x[0] * x[1] / (x[0] + x[1])
        for _ in range(2000):
            a = x[0] + rng.uniform(-u[0] / 2, u[0] / 2)
            b = x[1] + rng.uniform(-u[1] / 2, u[1] / 2)
            self.assertLessEqual(abs(a * b / (a + b) - fx), r["half"])

    def test_d73_sum_across_a_decimal_boundary(self):
        """t = a + b in 3 significant digits whose observed value crosses a decimal boundary: with the last-digit unit
        of the values actually read as the tolerance a correct release never triggers; the negative control (the
        unit at the predicted central value, prediction of t 1.3 sigma_t below the boundary) triggers in about 6% of
        checks (section 15.3.5 with the D73 wording, A8)."""
        rng = np.random.default_rng(3)
        fmt = {"kind": "significant", "digits": 3}
        sa = sb = 0.3
        st = math.hypot(sa, sb)
        mt = 10.0 - 1.3 * st
        ma, mb = mt / 2, mt / 2
        trig_ok = trig_neg = 0
        n = 20000

        def rnd(v):
            u = D.unit(v, fmt)
            return round(v / u) * u
        for _ in range(n):
            a, b = rng.normal(ma, sa), rng.normal(mb, sb)
            t = a + b
            ra, rb, rt = rnd(a), rnd(b), rnd(t)
            half = [D.unit(rt, fmt) / 2, D.unit(ra, fmt) / 2, D.unit(rb, fmt) / 2]
            trig_ok += D.constraint_check(np.array([1.0, -1.0, -1.0]), 0.0, np.array([rt, ra, rb]), half)["triggered"]
            halfp = [D.unit(mt, fmt) / 2, D.unit(ma, fmt) / 2, D.unit(mb, fmt) / 2]
            trig_neg += D.constraint_check(np.array([1.0, -1.0, -1.0]), 0.0, np.array([rt, ra, rb]),
                                           halfp)["triggered"]
        self.assertEqual(trig_ok, 0)
        self.assertAlmostEqual(trig_neg / n, 0.06, delta=0.015)

    def test_d4_unbounded_enclosure_rejected_at_locking(self):
        """A ratio whose denominator is a difference that can straddle 0 in a fixed-decimal format: the format admits
        an unbounded enclosure, the contract is rejected at locking (D4, A8); a denominator bounded away from 0 is
        accepted."""
        u = (lambda v: 0.01)
        self.assertTrue(D.admits_unbounded(lambda a, b, c: a / (b - c), [(0.5, 1.0), (0.9, 1.1), (0.9, 1.1)], u))
        self.assertFalse(D.admits_unbounded(lambda a, b: a / b, [(0.5, 1.0), (2.0, 3.0)], u))
        with self.assertRaises(D.CheckError):
            D.enclosure(lambda a: a.log(), [0.0], [0.01])

    def test_residual_identity(self):
        r = np.array([3.0, -1.0, -2.0])
        self.assertFalse(D.residual_identity_check(np.ones(3), r)["triggered"])
        self.assertTrue(D.residual_identity_check(np.ones(3), r + 1e-6)["triggered"])


if __name__ == "__main__":
    unittest.main()
