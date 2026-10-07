"""T22: HistFactory interpolation codes in shape-limit. code0/code1/code4 for asymmetric normalization factors and
code0/code4p for shapes reproduce pyhf, code4 and code4p are smooth where code0 and code1 kink, and an Asimov data set
made at a known nuisance value is fitted back to it."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402

THETAS = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5)
# pyhf 0.7.6 (numpy backend), lo = 0.9 and hi = 1.15: factors for code0 are 1 + the printed shift
PYHF_NORM = {"code0": [0.85, 0.9, 0.95, 1.0, 1.075, 1.15, 1.225],
             "code1": [0.853815, 0.9, 0.948683, 1.0, 1.072381, 1.15, 1.233238],
             "code4": [0.853815, 0.9, 0.946847, 1.0, 1.070659, 1.15, 1.233238]}
# pyhf 0.7.6: down 8, nominal 10, up 13, additive shifts
PYHF_SHAPE = {"code0": [-3.0, -2.0, -1.0, 0.0, 1.5, 3.0, 4.5], "code4p": [-3.0, -2.0, -1.051758, 0.0, 1.448242, 3.0, 4.5]}


def norm(code, hi=1.15, lo=0.9):
    return {"hi": hi, "lo": lo, "interpolation": code, "c4": ll._code4_coefficients(hi, lo)}


def deriv(f, x, h=1e-5, side=0):
    if side < 0:
        return (f(x) - f(x - h)) / h
    if side > 0:
        return (f(x + h) - f(x)) / h
    return (f(x + h) - f(x - h)) / (2 * h)


class PyhfReferenceTests(unittest.TestCase):
    def test_normalization_codes(self):
        for code, want in PYHF_NORM.items():
            got = [ll._interp_norm(t, norm(code)) for t in THETAS]
            for g, w, t in zip(got, want, THETAS):
                self.assertAlmostEqual(g, w, delta=2e-6, msg=(code, t))

    def test_shape_codes(self):
        for code, want in PYHF_SHAPE.items():
            for t, w in zip(THETAS, want):
                self.assertAlmostEqual(ll._interp_shape(t, 10.0, 13.0, 8.0, code), w, delta=2e-6, msg=(code, t))

    def test_live_pyhf_if_installed(self):
        try:
            import numpy as np
            import pyhf
        except ImportError:
            self.skipTest("pyhf not installed")
        pyhf.set_backend("numpy")
        grid = [x / 10 for x in range(-25, 26)]
        for hi, lo in ((1.15, 0.9), (1.4, 0.5), (0.95, 1.05)):
            for code in ("code0", "code1", "code4"):
                f = getattr(pyhf.interpolators, code)(np.array([[[[lo], [1.0], [hi]]]]))
                for t in grid:
                    want = float(np.asarray(f(np.array([[t]]))).ravel()[0]) + (1.0 if code == "code0" else 0.0)
                    self.assertAlmostEqual(ll._interp_norm(t, norm(code, hi, lo)), want, delta=1e-9, msg=(code, hi, lo, t))
        for nom, up, down in ((10.0, 13.0, 8.0), (5.0, 4.0, 7.0)):
            for code in ("code0", "code4p"):
                f = getattr(pyhf.interpolators, code)(np.array([[[[down], [nom], [up]]]]))
                for t in grid:
                    want = float(np.asarray(f(np.array([[t]]))).ravel()[0])
                    self.assertAlmostEqual(ll._interp_shape(t, nom, up, down, code), want, delta=1e-9, msg=(code, t))


class SmoothnessTests(unittest.TestCase):
    def test_code4_and_code4p_are_smooth_where_code0_and_code1_kink(self):
        shape = lambda code: (lambda t: ll._interp_shape(t, 10.0, 13.0, 8.0, code))
        normf = lambda code: (lambda t: ll._interp_norm(t, norm(code)))
        for f, smooth in ((normf("code4"), True), (shape("code4p"), True), (normf("code0"), False),
                          (normf("code1"), False), (shape("code0"), False)):
            left, right = deriv(f, 0.0, side=-1), deriv(f, 0.0, side=1)
            if smooth:
                self.assertAlmostEqual(left, right, delta=1e-3)
            else:
                self.assertGreater(abs(left - right), 0.02)

    def test_value_slope_and_curvature_join_at_plus_minus_one(self):
        for f in (lambda t: ll._interp_norm(t, norm("code4", 1.3, 0.6)), lambda t: ll._interp_shape(t, 10.0, 13.0, 8.0, "code4p")):
            for x in (-1.0, 1.0):
                self.assertAlmostEqual(f(x - 1e-9), f(x + 1e-9), delta=1e-7)
                self.assertAlmostEqual(deriv(f, x - 1e-3), deriv(f, x + 1e-3), delta=2e-3)
                curv = lambda y: (f(y + 1e-3) - 2 * f(y) + f(y - 1e-3)) / 1e-6
                self.assertAlmostEqual(curv(x - 2e-3), curv(x + 2e-3), delta=2e-2)


class FitClosureTests(unittest.TestCase):
    def test_asimov_at_a_known_nuisance_is_fitted_back(self):
        bins = [{"n": 0, "b": 40.0, "s": 5.0}, {"n": 0, "b": 30.0, "s": 10.0}, {"n": 0, "b": 20.0, "s": 5.0}]
        nuis = [{"name": "shape", "kind": "background_shape", "interpolation": "code4p", "up": [44.0, 30.0, 17.0], "down": [37.0, 31.0, 22.0]},
                {"name": "norm", "kind": "background_norm", "hi": 1.12, "lo": 0.85}]
        bins_p, parsed, chol = ll._load_shape({"bins": bins, "nuisances": nuis})
        model = ll._ShapeModel(bins_p, parsed, chol)
        for theta in ([0.4, -0.3], [-0.7, 0.6]):
            asimov = model.expected(1.0, theta)
            # the auxiliary measurements sit at the same values, as in an Asimov data set
            mu_hat, th_hat, _ = model.glob(asimov, theta)
            self.assertAlmostEqual(mu_hat, 1.0, delta=2e-3)
            for got, want in zip(th_hat, theta):
                self.assertAlmostEqual(got, want, delta=2e-3)

    def test_input_checks(self):
        bins = [{"n": 3, "b": 2.0, "s": 1.0}]
        for bad in ({"kind": "background_norm", "hi": 1.1, "lo": 0.9, "interpolation": "code4p"},
                    {"kind": "background_norm", "hi": 1.1, "lo": 0.9, "prior": "lognormal"},
                    {"kind": "background_norm", "sigma": 0.1, "interpolation": "code4"},
                    {"kind": "background_shape", "up": [2.2], "down": [1.8], "interpolation": "code4"}):
            with self.assertRaises(ll.LikelihoodError, msg=bad):
                ll._load_shape({"bins": bins, "nuisances": [bad]})
        out = ll.shape_limit({"bins": bins, "nuisances": [{"name": "n", "kind": "background_norm", "hi": 1.1, "lo": 0.9}]}, 0.95, 0, 1)
        self.assertEqual(out["interpolation"], {"n": "code4"})
        self.assertTrue(math.isfinite(out["asymptotic_observed_upper_limit"]))


if __name__ == "__main__":
    unittest.main()
