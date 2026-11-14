"""P3, G5 (section 8.3), P8, G9 (section 5.5) and the intervals of section 7.5 (phase 2, WP3)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import fit as F  # noqa: E402
from core.calibration import identify as I  # noqa: E402
from core.calibration import interval as Iv  # noqa: E402
from core.calibration import shift as Sh  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402

TRUTH = [0.5, -0.3, 1.0]


def product_config():
    cfg = T.linear_config(n=20, d=3)
    cfg.J[:, 1] = cfg.J[:, 0] + 1e-4 * np.random.default_rng(9).normal(size=20)
    cfg.degeneracy_modes = [{"mode": "binomial thinning chain", "parameters": ["t0", "t1"],
                             "signal": "inject a reference with known photon number between the stages"}]
    return cfg


class Identifiability(unittest.TestCase):
    def test_p3_product_not_identifiable_with_hint(self):
        """Two parameters that act only together (yield x PDE without photon-source injection, section 15.3.1)."""
        p = T.make(product_config(), TRUTH, 3, 4)
        r = I.p3(p, T.initial_beta(p))
        self.assertEqual(r["finding"], "p3.not_identifiable")
        self.assertEqual(r["hints"][0]["mode"], "binomial thinning chain")

    def test_p3_passes_when_separated(self):
        p = T.make(T.linear_config(n=20, d=3), TRUTH, 3, 4)
        r = I.p3(p, T.initial_beta(p))
        self.assertEqual(r["status"], "passed")
        self.assertGreaterEqual(r["lambda_min"], 0.1)

    def test_g5_product_fails_and_separated_passes(self):
        p = T.make(product_config(), TRUTH, 3, 4)
        fe = F.find_extremum(p, 3, T.initial_beta(p))
        self.assertEqual(I.g5(p, fe, seed=5)["finding"], "g5.not_identifiable")
        q = T.make(T.linear_config(n=20, d=3), TRUTH, 3, 4)
        fq = F.find_extremum(q, 3, T.initial_beta(q))
        self.assertEqual(I.g5(q, fq, seed=5)["status"], "passed")

    def test_g5_nonconverged_scan_points_are_a_plan_remedy(self):
        """A profile that cannot be evaluated beyond some theta: the scan points do not converge, G5 fails in that
        direction with remedy level plan (section 7.3, note 8)."""
        q = T.make(T.linear_config(n=20, d=3), TRUTH, 3, 4)
        fq = F.iterate(q, T.initial_beta(q))
        base_h = q.h
        bad = F.view(q, h=lambda tp: base_h(tp) if tp[0] < fq.beta[0] + 0.5 * fq.sigma_tot[0] else
                     np.full_like(base_h(tp), np.nan))
        r = I.g5(bad, fq, seed=5)
        self.assertEqual(r["status"], "failed")
        self.assertEqual(r["remedy"], "plan")


def orth_vector(J, seed=7):
    Q, _ = np.linalg.qr(np.c_[J, np.random.default_rng(seed).normal(size=(J.shape[0], 1))])
    return Q[:, J.shape[1]]


class Shift(unittest.TestCase):
    def config(self, info, resp=None):
        c = T.linear_config(n=20, d=3)
        c.phi_cols = (np.sqrt(info) * orth_vector(c.J))[:, None]
        c.phi_resp = resp
        return c

    def test_p8(self):
        """Information c = 0.3 on the shift-mode phi fails, 0.05 passes (section 15.3.1)."""
        for info, status in ((0.3, "failed"), (0.05, "passed")):
            p = T.make(self.config(info), TRUTH, 3, 4)
            r = Sh.p8(p, T.initial_beta(p))
            self.assertEqual(r["status"], status)
            self.assertAlmostEqual(r["lambda_max"], info, places=6)

    def test_p8_flat_staircase_is_incomplete(self):
        """A shift-mode phi whose predictions are a staircase coarser than P8's finite-difference step (a resimulated
        phi under common random numbers) reads an exactly flat derivative: P8 is incomplete (p8.derivative_unresolved),
        not a vacuous pass (WP-H finding). Control: the same size of effect, smooth in phi, is decided."""
        J0 = T.linear_config(n=20, d=3).J[:, 0]
        stair = self.config(0.0, lambda ph, tp: J0 * 0.5 * np.round(np.asarray(ph)[0] / 0.5) * 0.5)
        r = Sh.p8(T.make(stair, TRUTH, 3, 4), T.initial_beta(T.make(stair, TRUTH, 3, 4)))
        self.assertEqual((r["status"], r["finding"]), ("incomplete", "p8.derivative_unresolved"))
        smooth = self.config(0.0, lambda ph, tp: J0 * 0.5 * np.asarray(ph)[0])
        p = T.make(smooth, TRUTH, 3, 4)
        self.assertIn(Sh.p8(p, T.initial_beta(p))["status"], ("passed", "failed"))

    def responses(self):
        p0 = T.make(self.config(0.05), TRUTH, 3, 4)
        st = F.iterate(p0, T.initial_beta(p0)).sigma_tot[0]
        J = p0.cfg.J
        b = 2.0 * st
        return {"expansive": lambda ph: -J[:, 0] * b * (ph[0] + 0.3 * ph[0] ** 3 / 6),
                "compressive": lambda ph: -J[:, 0] * b * (ph[0] - 0.3 * ph[0] ** 3 / 6),
                "quadratic": lambda ph: -J[:, 0] * b * (ph[0] + 0.25 * ph[0] ** 2),
                "linear": lambda ph: -J[:, 0] * b * ph[0]}

    def g9(self, name):
        p = T.make(self.config(0.05, self.responses()[name]), TRUTH, 3, 4)
        f = F.iterate(p, T.initial_beta(p))
        return Sh.g9(p, f, Sh.p8(p, T.initial_beta(p)), multistart=False)

    def test_g9_expansive_cubic_fails_with_delta_017(self):
        """Delta theta-hat = b(phi + 0.3 phi^3 / 6), |b| = 2 sigma_tot: Delta_i = 0.17 > 0.06 (section 15.3.1)."""
        r = self.g9("expansive")
        self.assertEqual(r["finding"], "g9.linearity")
        self.assertAlmostEqual(max(r["Delta"]), 0.17, delta=0.01)

    def test_g9_quadratic_fails_compressive_and_linear_pass(self):
        self.assertEqual(self.g9("quadratic")["finding"], "g9.linearity")
        self.assertEqual(self.g9("compressive")["status"], "passed")
        self.assertEqual(self.g9("linear")["status"], "passed")

    def test_g9_information_at_fit_point(self):
        """Condition 1 holds at theta_ref (0.09 <= c) but not at theta-hat (> 1.5c): G9 fails (section 15.3.1)."""
        c = T.linear_config(n=20, d=3)
        o = orth_vector(c.J)
        c.phi_cols = (0.3 * o)[:, None]
        c.phi_resp = lambda ph, tp: o * 0.3 * 0.6 * tp[0] * ph[0]
        p = T.make(c, [1.0, -0.3, 1.0], 3, 4)
        p8 = Sh.p8(p, T.initial_beta(p))
        self.assertEqual(p8["status"], "passed")
        r = Sh.g9(p, F.iterate(p, T.initial_beta(p)), p8, multistart=False)
        self.assertIn("g9.information", r["findings"])

    def test_g9_not_decided_without_p8_and_refit_nonconvergence_fails(self):
        p = T.make(self.config(0.3), TRUTH, 3, 4)
        f = F.iterate(p, T.initial_beta(p))
        self.assertEqual(Sh.g9(p, f, Sh.p8(p, T.initial_beta(p)))["status"], "not-decided")
        q = T.make(self.config(0.05), TRUTH, 3, 4)
        fq = F.iterate(q, T.initial_beta(q))
        base = q.h_shift
        q.h_shift = lambda tp, ph: base(tp, ph) if abs(ph[0]) < 1.5 else np.full_like(base(tp, ph), np.nan)
        r = Sh.g9(q, fq, Sh.p8(q, T.initial_beta(q)), multistart=False)
        self.assertEqual(r["finding"], "g9.refit_not_converged")

    def test_g9_not_applicable_without_shift_phi(self):
        p = T.make(T.linear_config(n=20, d=3), TRUTH, 3, 4)
        self.assertEqual(Sh.p8(p, T.initial_beta(p))["status"], "not-applicable")

    def test_widening_and_symmetric_columns(self):
        """D52 (b): the widening is max(|D+|, |D-|), the d_l and G_s columns the symmetric difference."""
        r = self.g9("quadratic")
        w, a = np.array(r["widening"]), np.array(r["symmetric"])
        self.assertTrue(np.all(w >= np.abs(a) - 1e-12))
        self.assertGreater(float(np.max(w - np.abs(a))), 0.0)


class Intervals(unittest.TestCase):
    def setUp(self):
        self.p = T.make(T.linear_config(n=20, d=3), TRUTH, 3, 4)
        self.f = F.iterate(self.p, T.initial_beta(self.p))

    def test_profile_equals_sigma_in_the_linear_gaussian(self):
        for level, z in ((0.68, 1.0), (0.95, 1.96)):
            r = Iv.profile_interval(self.p, self.f, 0, level)
            self.assertAlmostEqual(r["half_width"] / z, self.f.sigma_tot[0], delta=2e-3 * self.f.sigma_tot[0])
            self.assertEqual(r["label"], "confidence-interval")

    def test_total_halfwidth(self):
        """sqrt(sigma_q^2 + z^2 (sum Delta^2 + Sigma_boot/w)); toy-calibrated intervals do not add Sigma_boot / w
        (adding it is the negative control, section 15.3.9)."""
        self.assertAlmostEqual(Iv.total_halfwidth(1.0, 0.68, [0.3], 0.02, 0.891),
                               np.sqrt(1 + 0.09 + 0.02 / 0.891))
        self.assertAlmostEqual(Iv.total_halfwidth(1.0, 0.95, [0.3], 0.02, 0.891, toy_calibrated=True),
                               np.sqrt(1 + 1.96 ** 2 * 0.09))
        self.assertGreater(Iv.total_halfwidth(1.0, 0.68, None, 0.02, 0.891), 1.0)

    def test_toy_calibrated_agrees_with_profile(self):
        c1 = T.linear_config(n=10, d=1, prior=[(-3, 3)])
        p1 = T.make(c1, [0.4], 3, 4)
        f1 = F.iterate(p1, T.initial_beta(p1))
        s = f1.sigma_tot[0]
        grid = f1.beta[0] + s * np.linspace(-1.6, 1.6, 9)
        r = Iv.toy_calibrated(p1, f1, 0, grid, 100, 11, 0.68, n_start=4)
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["inside"], [False, False, True, True, True, True, True, False, False])
        self.assertEqual(len(r["union"]), 1)

    def test_metropolis_posterior_is_a_labeled_credible_interval(self):
        r = Iv.metropolis_posterior(lambda x: -0.5 * float(x @ x), np.zeros(2), np.ones(2), 4000, 3, priors_declared={"t0": "N(0,1)"})
        self.assertEqual(r["label"], "credible-interval")
        self.assertLess(max(r["rhat"]), 1.05)
        self.assertAlmostEqual(r["c68"][0][1], 1.0, delta=0.15)
        self.assertEqual(Iv.inference_flags(r), ["credible-interval"])
        with self.assertRaises(F.FitError):
            Iv.metropolis_posterior(lambda x: 0.0, np.zeros(1), np.ones(1), 10, 1)
        with self.assertRaises(F.FitError):
            Iv.inference_flags({**r, "frequentist_coverage_claim": True})

    def test_region_box_for_g3(self):
        r = Iv.profile_interval(self.p, self.f, 0, 0.68)
        box = Iv.region_box({"t0": r})
        self.assertAlmostEqual(box["t0"][1] - box["t0"][0], 2 * r["half_width"])


if __name__ == "__main__":
    unittest.main()
