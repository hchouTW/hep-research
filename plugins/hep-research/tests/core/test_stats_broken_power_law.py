"""STH Q8: one broken-power-law parametrization (core/stats/broken_power_law.py) shared by hep-measurement
cr_spectrum_powerlaw_fit.py and hep-statistics covariance_fit.py. Both tools give identical model values, and on the
same synthetic points with a full covariance their fitted parameters agree within a stated tolerance."""
import math
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PLUGIN), str(PLUGIN / "skills" / "hep-measurement" / "scripts"),
                str(PLUGIN / "skills" / "hep-statistics" / "scripts")]
from core.stats import broken_power_law as bpl  # noqa: E402

try:
    import numpy as np
    import scipy  # noqa: F401
except ImportError:  # pragma: no cover
    np = None

TRUTH = [math.log(5.0), 2.7, 2.4, math.log(30.0)]  # [ln A, gamma1, gamma2, ln x_b]
# Measured on 40 seeded toys per model (20 points, 2% uncorrelated + 1% fully correlated): largest difference between
# the two tools 0.17 sigma (sharp, covariance_fit started at the cr_spectrum fit) and 0.11 sigma (smooth). The tools
# minimize different objectives (chi2 in log flux with the linearized covariance vs chi2 in flux), so they agree to a
# fraction of sigma, not exactly. On noise-free (Asimov) points both return the truth.
AGREE_SIGMA = 0.3


class Formula(unittest.TestCase):
    def test_value_at_break_is_a_and_indices(self):
        for s in (None, 0.0, 0.05, 0.3, 1.0):
            with self.subTest(s=s):
                self.assertAlmostEqual(bpl.log_flux(30.0, 1.5, 2.7, 2.4, math.log(30.0), s), 1.5, places=14)
                # far from the break the local slope is -gamma1 below and -gamma2 above
                lo = (bpl.log_flux(1e-6 * 30, 0, 2.7, 2.4, math.log(30.0), s)
                      - bpl.log_flux(1.001e-6 * 30, 0, 2.7, 2.4, math.log(30.0), s)) / math.log(1.001)
                hi = (bpl.log_flux(1e6 * 30, 0, 2.7, 2.4, math.log(30.0), s)
                      - bpl.log_flux(1.001e6 * 30, 0, 2.7, 2.4, math.log(30.0), s)) / math.log(1.001)
                self.assertAlmostEqual(lo, 2.7, places=6)
                self.assertAlmostEqual(hi, 2.4, places=6)

    def test_closed_form_and_sharp_limit(self):
        x, xb, a, g1, g2, s = 70.0, 30.0, 2.0, 2.7, 2.4, 0.3
        closed = a * (x / xb) ** -g1 * ((1 + (x / xb) ** (1 / s)) / 2) ** (-(g2 - g1) * s)
        self.assertAlmostEqual(math.exp(bpl.log_flux(x, math.log(a), g1, g2, math.log(xb), s)) / closed, 1.0, places=13)
        for x in (3.0, 29.0, 31.0, 300.0):
            self.assertAlmostEqual(bpl.log_flux(x, 0.3, g1, g2, math.log(xb), 1e-4),
                                   bpl.log_flux(x, 0.3, g1, g2, math.log(xb), None), places=3)

    def test_no_overflow_and_bad_smoothness(self):
        self.assertTrue(math.isfinite(bpl.break_shape(800.0, 0.01)))
        self.assertEqual(bpl.break_shape(-800.0, 0.01), -0.01 * math.log(2.0))
        for bad in (-0.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                bpl.break_shape(0.0, bad)
        with self.assertRaises(ValueError):
            bpl.log_flux(0.0, 0, 2.7, 2.4, 0.0)

    @unittest.skipIf(np is None, "NumPy needed for the array path")
    def test_array_path_equals_float_path(self):
        x = np.geomspace(1, 1000, 31)
        for s in (None, 0.3):
            arr = bpl.log_flux(x, 0.2, 2.7, 2.4, math.log(30.0), s)
            flt = [bpl.log_flux(float(e), 0.2, 2.7, 2.4, math.log(30.0), s) for e in x]
            self.assertEqual(arr.tolist(), flt)


@unittest.skipIf(np is None, "covariance_fit.py needs NumPy and SciPy")
class BothTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import covariance_fit
        import cr_spectrum_powerlaw_fit
        cls.cf, cls.cr = covariance_fit, cr_spectrum_powerlaw_fit
        cls.x = np.geomspace(3, 300, 20)

    def test_identical_model_values(self):
        thetas = (TRUTH, [0.0, 2.0, 3.1, math.log(4.0)], [-3.0, 2.9, 2.6, math.log(150.0)])
        for th in thetas:
            for s in (None, 0.05, 0.3):
                with self.subTest(theta=th, s=s):
                    stat = self.cf.bpl_log(th, self.x, s or 0.0)
                    ana = [self.cr.broken_log_flux(float(e), th[0], th[1], th[2], math.exp(th[3]), s) for e in self.x]
                    core = bpl.log_flux(self.x, *th, s)
                    self.assertEqual(stat.tolist(), core.tolist())
                    np.testing.assert_allclose(ana, core, rtol=0, atol=1e-12)  # exp/log round trip of x_b only

    def fits(self, y, cov, s, start=None):
        a = self.cr.fit_spectrum([[float(e), float(v)] for e, v in zip(self.x, y)],
                                 "broken" if s is None else "smooth-broken", smoothness=s, covariance=cov.tolist())
        pa = [math.log(a["normalization_at_break"]), a["index_below"], a["index_above"], math.log(a["break_energy"])]
        st = self.cf.fit(y, cov, "broken-power-law" if s is None else "smoothly-broken-power-law", self.x,
                         start=pa if start is None else start, model_options={"smoothness": s} if s else None)
        return np.array(pa), np.array(st["theta"]), np.array(st["theta_errors"]), a

    def covariance(self, truth):
        return np.diag((0.02 * truth) ** 2) + np.outer(0.01 * truth, 0.01 * truth)

    def test_asimov_both_recover_the_truth(self):
        for s in (None, 0.3):
            with self.subTest(s=s):
                truth = np.exp(bpl.log_flux(self.x, *TRUTH, s))
                pa, ps, err, a = self.fits(truth, self.covariance(truth), s, start=TRUTH)
                np.testing.assert_allclose(pa, TRUTH, rtol=0, atol=1e-6)
                self.assertLess(float(np.max(np.abs(ps - np.array(TRUTH)) / err)), 1e-3)
                # same uncertainties: the linearized log-space and the flux-space covariance coincide at zero residual
                np.testing.assert_allclose([a["index_below_uncertainty"], a["index_above_uncertainty"],
                                            a["log_break_energy_uncertainty"]], err[1:], rtol=1e-3)

    def test_toys_agree_within_stated_tolerance(self):
        rng = np.random.default_rng(20261013)
        for s in (None, 0.3):
            truth = np.exp(bpl.log_flux(self.x, *TRUTH, s))
            cov = self.covariance(truth)
            for t in range(8):
                with self.subTest(s=s, toy=t):
                    pa, ps, err, _ = self.fits(rng.multivariate_normal(truth, cov), cov, s)
                    self.assertLess(float(np.max(np.abs(pa - ps) / err)), AGREE_SIGMA)


if __name__ == "__main__":
    unittest.main()
