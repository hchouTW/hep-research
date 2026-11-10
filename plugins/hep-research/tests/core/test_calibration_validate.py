"""Validation of Part B section 9 (phase 2, WP4): C_r^+ on N_d, declaration checks, the holdout statistic, power,
cross-validation bookkeeping and the decision records with the real ledger."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import data_release as DR  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402
from core.calibration import validate as V  # noqa: E402


class NullSpace(unittest.TestCase):
    def test_diag_one_zero(self):
        """C_r = diag(1, 0), N_d the second direction: k = 1 and the rejection rate of T_v under H0 is alpha (section
        15.2)."""
        C = np.diag([1.0, 0.0])
        Cp, k = V.c_r_plus(C, np.array([1.0, 1.0]), [np.array([0.0, 1.0])])
        self.assertEqual(k, 1)
        rng = np.random.default_rng(1)
        r = np.c_[rng.normal(size=20000), np.zeros(20000)]
        rate = np.mean(np.einsum("ni,ij,nj->n", r, Cp, r) > stats.chi2.ppf(0.95, 1))
        self.assertAlmostEqual(rate, 0.05, delta=0.006)

    def test_scale_invariance(self):
        """diag(100, 1e-6) and its correlation matrix give the same decision (section 8.7 note 1, 15.2)."""
        C = np.diag([100.0, 1e-6])
        s = np.sqrt(np.diag(C))
        r = np.array([12.0, 2e-3])
        Cp1, _ = V.c_r_plus(C, s, [])
        Cp2, _ = V.c_r_plus(np.eye(2), np.ones(2), [])
        self.assertAlmostEqual(V.t_v(r, Cp1), V.t_v(r / s, Cp2), places=9)
        d1 = V.declaration_check(C, s, [])
        d2 = V.declaration_check(np.eye(2), np.ones(2), [])
        self.assertEqual(d1["status"], d2["status"])

    def test_tau_num_confirmations(self):
        """The four confirmations of section 8.7 note 1 on a definitional sum t = p1 + p2."""
        rng = np.random.default_rng(2)
        A = rng.normal(size=(2, 2))
        Cp = A @ A.T + np.eye(2)
        Tm = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        C = Tm @ Cp @ Tm.T
        s = np.sqrt(np.diag(C))
        n = np.array([1.0, 1.0, -1.0])
        ok = V.declaration_check(C, s, [n], expectations=[Tm @ np.array([0.3, -0.2]) * 0])
        self.assertEqual(ok["status"], "passed")
        self.assertLess(ok["block_norm"], 1e-14)
        # a wrongly declared direction with standardized sd 1e-3 is caught
        C2 = np.diag([1.0, 1.0, 1e-6])
        bad = V.declaration_check(C2, np.ones(3), [np.array([0.0, 0.0, 1.0])])
        self.assertIn("validate.declared_direction_has_variance", bad["failures"])
        # correlation 1 - 1e-7 undeclared: the rank condition passes
        c = 1 - 1e-7
        self.assertEqual(V.declaration_check(np.array([[1, c], [c, 1]]), np.ones(2), [])["status"], "passed")
        # an undeclared exact constraint fails (c)
        self.assertIn("validate.undeclared_exact_constraint", V.declaration_check(C, s, [])["failures"])

    def test_expectation_violating_a_constraint(self):
        """An alternative hypothesis whose prediction violates an exact constraint: contract error, not power."""
        Tm = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
        C = Tm @ np.eye(2) @ Tm.T
        s = np.sqrt(np.diag(C))
        bad_alt = np.array([0.1, 0.1, 0.25])
        r = V.declaration_check(C, s, [np.array([1.0, 1.0, -1.0])], expectations=[bad_alt])
        self.assertIn("validate.expectation_violates_constraint", r["failures"])

    def test_nearly_collinear_wrong_declarations(self):
        """Two nearly collinear wrong declarations, each with small variance, together spanning a direction of
        variance 1: caught by the block norm (a) (section 15.2)."""
        C = np.diag([1.0, 1.0, 1.0])
        n1 = np.array([1.0, 1e-4, 0.0])
        n2 = np.array([1.0, -1e-4, 0.0])
        with self.assertRaises(Exception):
            V.declaration_check(C, np.ones(3), [n1, n1 * (1 + 1e-12)])     # nearly duplicate: SVD check
        res = V.declaration_check(np.diag([1e-12, 1.0, 1.0]), np.ones(3), [n1, n2])
        self.assertIn("validate.declared_direction_has_variance", res["failures"])

    def test_eigenvalue_perturbation_does_not_change_tv(self):
        rng = np.random.default_rng(3)
        A = rng.normal(size=(5, 5))
        C = A @ A.T + np.eye(5)
        w, U = np.linalg.eigh(C)
        C2 = (U * (w * (1 + 1e-12))) @ U.T
        r = rng.normal(size=5)
        s = np.sqrt(np.diag(C))
        a = V.t_v(r, V.c_r_plus(C, s, [])[0])
        b = V.t_v(r, V.c_r_plus(C2, s, [])[0])
        self.assertAlmostEqual(a, b, places=9)

    def test_removed_direction_reduces_k(self):
        s = np.ones(3)
        cons = V.remove_directions(s, [], [np.array([1.0, 0.0, 0.0])])
        self.assertEqual(V.c_r_plus(np.eye(3), s, cons)[1], 2)


def holdout_config(seed=0, nv=8):
    rng = np.random.default_rng(seed)
    cfg = T.linear_config(n=12, d=3, n_nu=1, n_eta=1)
    cfg.val = {"J": rng.normal(size=(nv, 3)), "m0": np.full(nv, 5.0), "V_data": np.eye(nv) * 0.5,
               "V_MC": np.zeros((nv, nv)), "U": rng.normal(size=(nv, 1)) * 0.3,
               "S": rng.normal(size=(nv, 1)) * 0.3}
    return cfg


class Holdout(unittest.TestCase):
    def run_null(self, reps, omit=()):
        cfg = holdout_config()
        crit = stats.chi2.ppf(0.95, 8)
        out = []
        for s in range(reps):
            p = T.make(cfg, [0.5, -0.3, 1.0], data_seed=10 + s, mc_seed=1)
            yv = p.simulate_val(p.truth, np.random.default_rng([s, 5]))
            f = F.iterate(p, T.initial_beta(p), lndet=False)
            pc = V.holdout_pieces(p, f, yv, omit=omit)
            out.append(V.t_v(pc["r"], V.c_r_plus(pc["C_r"], pc["s"], pc["constraints"])[0]))
        return np.array(out), crit

    def test_statistic_with_cross_terms_has_mean_k_and_size_alpha(self):
        """Section 15.2: mean k = dim N_d^perp, rejection rate alpha (the propagation term J_v Sigma_beta J_v^T with
        the nu, eta columns of the validation rows)."""
        Tv, crit = self.run_null(600)
        self.assertAlmostEqual(Tv.mean(), 8.0, delta=0.5)
        self.assertAlmostEqual(np.mean(Tv > crit), 0.05, delta=0.03)

    def test_omitting_the_terms_over_rejects(self):
        """The formula without the terms coupling validation to the calibration fit over-rejects (section 15.3.1)."""
        Tv, crit = self.run_null(300, omit=("propagation",))
        self.assertGreater(np.mean(Tv > crit), 0.15)

    def test_toy_path_reasons(self):
        self.assertEqual(V.toy_path_reasons({"bootstrap": True, "low_counts": False}), ["bootstrap"])
        self.assertEqual(V.toy_path_reasons({}), [])


class Power(unittest.TestCase):
    def test_required_lambda_table(self):
        self.assertEqual([round(V.required_lambda(k), 3) for k in (1, 2, 3, 5, 10)],
                         [7.849, 9.635, 10.903, 12.828, 16.241])

    def test_cross_product_unbiased_single_set_biased(self):
        """lambda = 12.8: the cross product's mean within 12.8 +- 2%, the single-set estimate biased high by
        tr(C^+ V_Delta) (section 15.3.10)."""
        rng = np.random.default_rng(4)
        k = 5
        e = np.zeros(k)
        e[0] = np.sqrt(12.8)
        Cp = np.eye(k)
        VD = np.eye(k) * 0.3
        cr, sg, sc = [], [], []
        for _ in range(20000):
            e1 = e + rng.multivariate_normal(np.zeros(k), VD)
            e2 = e + rng.multivariate_normal(np.zeros(k), VD)
            cr.append(V.cross_lambda(e1, e2, Cp))
            sg.append(V.single_lambda(e1, Cp))
            sc.append(V.single_lambda(e1, Cp, VD))
        self.assertAlmostEqual(np.mean(cr), 12.8, delta=0.256)
        self.assertAlmostEqual(np.mean(sg) - 12.8, 1.5, delta=0.2)
        self.assertAlmostEqual(np.mean(sc), 12.8, delta=0.256)

    def test_decision_rules(self):
        """One bound < 0.8 with another not computable: insufficient power (D2); all >= 0.8 sufficient; a missing
        bound otherwise incomplete."""
        self.assertEqual(V.power_decision({"a": 0.6, "b": None})["status"], "failed")
        self.assertEqual(V.power_decision({"a": 0.9, "b": None})["status"], "incomplete")
        self.assertEqual(V.power_decision({"a": 0.9, "b": 0.85})["status"], "passed")
        self.assertEqual(V.s_a(-1.0, 3.0), 0.0)
        self.assertAlmostEqual(V.s_a(9.0, 16.0, 1.0), 0.75)
        self.assertEqual(V.bonferroni_levels(2, "toy"), {"lambda": 1 - 0.0125, "rate": 1 - 0.0125})
        self.assertLess(V.clopper_pearson_lower(85, 100, 0.975), 0.85)

    def test_analytic_path_lower_bound(self):
        rng = np.random.default_rng(5)
        reps = 30.0 + rng.normal(size=50)
        r = V.power_analytic({"a": reps}, k=5)
        self.assertEqual(r["status"], "passed")
        r = V.power_analytic({"a": 8.0 + rng.normal(size=50)}, k=5)
        self.assertEqual(r["status"], "failed")


class CrossValidationBookkeeping(unittest.TestCase):
    def test_g5_proportion_and_stop(self):
        """D68 (A8): denominator = toys with G5 decided; stop at F_G5 > 0.25 sum n_req."""
        self.assertAlmostEqual(V.g5_proportion(25, 100), 0.25)
        self.assertTrue(V.g5_stop(126, 500))
        self.assertFalse(V.g5_stop(125, 500))

    def test_toy_status_order(self):
        """A toy with one fold not converged and another failing G5 is not converged (section 15.3.8)."""
        self.assertEqual(V.cv_toy_status([True, False], [False, True]), "not-converged")
        self.assertEqual(V.cv_toy_status([True, True], [False, True]), "g5-failed")
        self.assertAlmostEqual(F.eps_max_cv(20), 0.02)


class Records(unittest.TestCase):
    def setUp(self):
        self.ledger = DR.Ledger()
        self.book = V.DecisionBook()
        self.k1 = V.kappa_record("c" * 64, {"plan": 1}, "0.1")
        self.book.register(self.k1)
        self.ledger.open_validation(self.k1["kappa"], "v" * 64, ["v1"], ["c1", "c2"], {"contract_sha256": "c" * 64})

    def status(self):
        return {r["status"] for r in self.ledger.state["failure_records"] if r["kappa"] == self.k1["kappa"]}

    def test_abandon_then_decision_rejected(self):
        """Section 15.3.14: abandonment makes the record final; a later passing decision is rejected; V failed."""
        self.book.abandon(self.k1["kappa"], self.ledger)
        self.assertEqual(self.status(), {"final"})
        with self.assertRaises(V.ValidationError) as c:
            self.book.decide(self.k1["kappa"], "pass", self.ledger)
        self.assertEqual(c.exception.code, "validate.after_abandonment")
        self.assertEqual(self.status(), {"final"})
        self.assertEqual(self.book.v_status(self.k1["kappa"]), "failed")

    def test_abandon_after_pass_rejected(self):
        self.book.decide(self.k1["kappa"], "pass", self.ledger)
        self.assertEqual(self.status(), {"withdrawn"})
        with self.assertRaises(V.ValidationError) as c:
            self.book.abandon(self.k1["kappa"], self.ledger)
        self.assertEqual(c.exception.code, "validate.abandon_after_decision")
        self.assertEqual(self.status(), {"withdrawn"})

    def test_fail_and_k0(self):
        self.book.decide(self.k1["kappa"], "fail", self.ledger)
        self.assertEqual(self.status(), {"final"})
        k2 = V.kappa_record("d" * 64, {}, "0.1")
        self.book.register(k2)
        self.ledger.open_validation(k2["kappa"], "w" * 64, ["w1"], ["c9"], {"contract_sha256": "d" * 64})
        self.book.decide(k2["kappa"], "no-testable-direction", self.ledger)
        self.assertEqual(self.book.v_status(k2["kappa"]), "no-testable-direction")

    def test_k0_with_triggered_check_is_final(self):
        self.book.decide(self.k1["kappa"], "no-testable-direction", self.ledger, data_side_check_triggered=True)
        self.assertEqual(self.status(), {"final"})

    def test_power_abandonment(self):
        """T_v passes, power not computable: incomplete; abandon-power gives insufficient power, the record stays
        withdrawn, later power records are rejected (section 15.3.10)."""
        k = self.k1["kappa"]
        self.book.decide(k, "pass", self.ledger)
        self.book.record_power(k, {"status": "incomplete"})
        self.assertEqual(self.book.v_status(k), "incomplete")
        self.book.abandon_power(k)
        self.assertEqual(self.book.v_status(k), "failed")
        self.assertEqual(self.status(), {"withdrawn"})
        with self.assertRaises(V.ValidationError):
            self.book.record_power(k, {"status": "passed"})

    def test_kappa_must_be_written_first(self):
        with self.assertRaises(V.ValidationError):
            self.book.decide("x" * 64, "pass")


if __name__ == "__main__":
    unittest.main()
