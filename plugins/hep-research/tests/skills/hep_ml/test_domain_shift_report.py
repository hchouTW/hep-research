"""ML4: domain_shift_report.py. Oracles: for identical distributions the classifier AUC is within its statistical range
around 0.5 and the per-feature p-values are uniform (slow tier for the uniformity scan); an injected shift is found and
attributed to the right feature; the domain_shift block is accepted by write_ml_artifact.py's schema; the per-period
breakdown isolates the shifted period. All inputs are SYNTHETIC."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-ml" / "scripts" / "domain_shift_report.py"
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else None), p.stderr


def write(path, cols):
    names = list(cols)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(names)
        for row in zip(*(cols[n] for n in names)):
            w.writerow([f"{v:.10g}" if isinstance(v, float) else v for v in row])


def sample(rng, n, shift=0.0, period=None):
    x = rng.normal(0, 1, n)
    y = rng.normal(0, 1, n) + shift
    z = rng.exponential(1.0, n)
    cols = {"x": x.tolist(), "y": y.tolist(), "z": z.tolist(), "run": [int(i // 50) for i in range(n)]}
    if period is not None:
        cols["period"] = period
    return cols


@unittest.skipIf(np is None, "numpy is not installed")
class DomainShiftReport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def files(self, shift=0.0, seed=1, n=2000, periods=False):
        rng = np.random.default_rng(seed)
        ref, tgt = self.d / "ref.csv", self.d / "tgt.csv"
        write(ref, sample(rng, n))
        if periods:
            a = sample(rng, n // 2, 0.0, ["p1"] * (n // 2))
            b = sample(rng, n // 2, shift, ["p2"] * (n // 2))
            write(tgt, {k: a[k] + b[k] for k in a})
        else:
            write(tgt, sample(rng, n, shift))
        return ref, tgt

    def args(self, ref, tgt, *extra):
        return ("--reference", ref, "--target", tgt, "--features", "x,y,z", "--group-column", "run",
                "--control-sample", "SYNTHETIC control region", "--seed", "3", *extra)

    def test_identical_distributions_show_no_shift(self):
        ref, tgt = self.files(0.0)
        code, out, err = run(*self.args(ref, tgt))
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertFalse(out["shift_detected"])
        c = out["classifier_test"]
        self.assertLess(abs(c["auc"] - 0.5), 3 * c["auc_sigma_null"])
        self.assertEqual(out["status_label"], "unvalidated")

    def test_injected_shift_is_found_and_attributed(self):
        ref, tgt = self.files(0.25)
        code, out, err = run(*self.args(ref, tgt))
        self.assertEqual(code, 1, err)
        self.assertTrue(out["shift_detected"])
        self.assertEqual(out["drivers"][0], "y")
        self.assertNotIn("x", out["drivers"])
        self.assertGreater(out["classifier_test"]["z"], 3)
        y = out["features"]["y"]
        self.assertLess(y["ks"]["p"], 1e-3)
        self.assertAlmostEqual(y["wasserstein"], 0.25, delta=0.08)

    def test_domain_shift_block_is_accepted_by_the_ml_artifact_schema(self):
        ref, tgt = self.files(0.25)
        block = self.d / "ds.json"
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block))
        self.assertEqual(code, 1, err)
        ds = json.loads(block.read_text())["domain_shift"]
        self.assertEqual(ds["control_sample"], "SYNTHETIC control region")
        self.assertEqual(ds["status"], "checked")
        self.assertNotIn("outcome", ds)  # what was done about the shift is the analyst's declaration
        schema = json.loads((ROOT / "contracts" / "schemas" / "ext_ml_artifact.json").read_text())["properties"]["domain_shift"]
        for key in schema["required"]:
            self.assertIn(key, ds)
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block, "--outcome", "uncorrected"))
        self.assertEqual(code, 2)  # uncorrected needs --nuisance
        code, out, err = run(*self.args(ref, tgt, "--domain-shift-out", block, "--outcome", "bounded-by-nuisance",
                                        "--nuisance", "ml_shift"))
        self.assertEqual(code, 1, err)
        self.assertEqual(json.loads(block.read_text())["domain_shift"]["nuisance"], "ml_shift")

    def test_per_period_breakdown(self):
        ref, tgt = self.files(0.4, periods=True)
        code, out, err = run(*self.args(ref, tgt, "--period-column", "period"))
        self.assertEqual(code, 1, err)
        per = out["periods"]
        self.assertLess(per["p2"]["y"]["ks_p"], 1e-3)
        self.assertGreater(per["p1"]["y"]["ks_p"], 1e-3)

    def test_bad_input(self):
        ref, tgt = self.files(0.0)
        for args in (self.args(ref, tgt, "--folds", "1"), ("--reference", ref, "--target", tgt, "--features", "nope",
                                                            "--control-sample", "c")):
            with self.subTest(args=args):
                code, out, _ = run(*args)
                self.assertEqual(code, 2)
                self.assertEqual(out["status"], "rejected")

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_slow_p_values_uniform_under_the_null(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import domain_shift_report as dsr
        rng = np.random.default_rng(11)
        ps = []
        for _ in range(400):
            a, b = rng.normal(0, 1, 500), rng.normal(0, 1, 500)
            ps.append(dsr.ks_test(a, np.ones(500), b, np.ones(500))["p"])
        ps = np.sort(ps)
        d = np.max(np.abs(ps - (np.arange(1, 401) - 0.5) / 400))
        self.assertLess(d, 1.36 / np.sqrt(400) + 0.02)


@unittest.skipIf(np is None, "numpy is not installed")
class ShiftCarriedByNuisance(unittest.TestCase):
    """Sci-fix ML-K05, axis C: the J9 example (examples/ml-classifier-to-inference/run.py) records the domain shift as
    bounded-by-nuisance because its template fit carries the measured shift as a Gaussian-constrained background-shape
    nuisance. Its shape_model() and fit_mu() are checked here on a SYNTHETIC three-bin template (s = 2, 5, 9;
    b = 40, 12, 3; MC statistics 5%; the +1 sigma template is the background shifted by 1.15, 1.35, 1.8, so the
    mirrored -1 sigma template stays positive) against an independent implementation: Poisson bins with the
    Barlow-Beeston-lite background profiled numerically per bin (normal of width 5% of the shifted background, as the
    core model defines it), the nuisance profiled by scipy minimize_scalar, the 68.27% interval from
    Delta(-2 ln L) = 1. Tolerances: interval ends 1e-5 (the core fit's EDM <= 1e-5 moves q by at most 2e-5, divided by
    dq/dmu of about 4 at the ends; observed 1e-11), best fit 4e-3 sigma (sqrt(2 EDM/H); observed 1e-7). Negative
    control (the pre-fix J9 fit had no nuisance, the shift was uncorrected): on Asimov data from the shifted
    background the nominal-only interval misses mu = 1, while the fit with the nuisance covers it."""

    MU0, S, B, UP_FACTOR, REL = 1.0, (2.0, 5.0, 9.0), (40.0, 12.0, 3.0), (1.15, 1.35, 1.8), 0.05

    @classmethod
    def setUpClass(cls):
        import importlib.util
        path = ROOT / "examples" / "ml-classifier-to-inference" / "run.py"
        spec = importlib.util.spec_from_file_location("ml_classifier_to_inference_run", path)
        cls.j9 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.j9)
        cls.s, cls.b = np.array(cls.S), np.array(cls.B)
        cls.up = cls.b * np.array(cls.UP_FACTOR)
        cls.t = {"signal": {"sumw": list(cls.S), "sumw2": [0.0] * 3},
                 "background": {"sumw": list(cls.B), "sumw2": ((cls.REL * cls.b) ** 2).tolist()}}

    def reference(self, n, with_nuisance):
        from scipy import optimize

        def nll(mu, theta):
            bt = self.b + theta * (self.up - self.b)  # code0 with the mirrored down template: linear on both sides
            if np.any(bt <= 0):
                return np.inf  # outside the model's domain (a negative background), as in the core model
            total = 0.5 * theta * theta if with_nuisance else 0.0
            for ni, si, bi in zip(n, mu * self.s, bt):
                sg = self.REL * bi
                total += optimize.minimize_scalar(
                    lambda bb: (si + bb) - ni * np.log(si + bb) + (bb - bi) ** 2 / (2 * sg * sg),
                    bounds=(1e-12, bi + 20 * sg), method="bounded", options={"xatol": 1e-12}).fun
            return total

        def profile(mu):
            if not with_nuisance:
                return nll(mu, 0.0)
            return optimize.minimize_scalar(lambda th: nll(mu, th), bounds=(-5, 5), method="bounded",
                                            options={"xatol": 1e-10}).fun

        best = optimize.minimize_scalar(profile, bounds=(0, 10), method="bounded", options={"xatol": 1e-10})
        f = lambda mu: 2 * (profile(mu) - best.fun) - 1  # noqa: E731
        return (best.x, optimize.brentq(f, 0.0, best.x, xtol=1e-10), optimize.brentq(f, best.x, best.x + 5, xtol=1e-10))

    def fit(self, n, with_nuisance):
        model = self.j9.shape_model(self.t, [0, 0, 0], b_up=self.up if with_nuisance else None)
        r = self.j9.fit_mu(model, list(n), model.aux_obs())
        return r["mu_hat"], r["lo"], r["hi"]

    def test_fit_with_and_without_the_nuisance_against_an_independent_profile_likelihood(self):
        nominal, shifted = self.MU0 * self.s + self.b, self.MU0 * self.s + self.up
        got = {}
        for label, n, nuisance in (("nominal", nominal, False), ("shifted", shifted, False),
                                   ("nominal+nuisance", nominal, True), ("shifted+nuisance", shifted, True)):
            with self.subTest(label):
                mu_hat, lo, hi = got[label] = self.fit(n, nuisance)
                ref = self.reference(n, nuisance)
                self.assertAlmostEqual(lo, ref[1], delta=1e-5)
                self.assertAlmostEqual(hi, ref[2], delta=1e-5)
                self.assertAlmostEqual(mu_hat, ref[0], delta=4e-3 * (hi - lo) / 2)
        self.assertEqual(got["nominal+nuisance"][0], self.MU0)  # Asimov at theta = 0: mu exactly recovered
        self.assertLess(got["nominal+nuisance"][1], got["nominal"][1])  # the nuisance widens the interval
        self.assertGreater(got["nominal+nuisance"][2], got["nominal"][2])
        # negative control: the uncorrected shift moves mu out of the nominal-only interval; the nuisance covers it
        self.assertGreater(got["shifted"][1], self.MU0)
        self.assertLess(got["shifted+nuisance"][1], self.MU0)
        self.assertGreater(got["shifted+nuisance"][2], self.MU0)

    def test_fit_against_pyhf(self):
        """Third-party oracle: the same model in pyhf (HistFactory: the signal with a normfactor, the background with a
        staterror of 5% and, with the nuisance, a histosys with the mirrored down template; pyhf's default
        interpolation for histosys is piecewise linear, code0), its own likelihood and fitter; the profile interval
        from Delta(-2 ln L) = 1 on pyhf's fixed-POI fits. Same tolerances as above (observed 2e-9)."""
        try:
            import pyhf
        except ImportError:
            self.skipTest("pyhf not installed (the stats-backends gate requires it)")
        from scipy import optimize

        pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=1e-12))

        def interval(n, with_nuisance):
            bkg = {"name": "background", "data": self.b.tolist(),
                   "modifiers": [{"name": "mcstat", "type": "staterror", "data": (self.REL * self.b).tolist()}]}
            if with_nuisance:
                down = (2 * self.b - self.up).tolist()
                bkg["modifiers"].append({"name": "shift", "type": "histosys",
                                         "data": {"hi_data": self.up.tolist(), "lo_data": down}})
            signal = {"name": "signal", "data": self.s.tolist(),
                      "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]}
            model = pyhf.Model({"channels": [{"name": "c", "samples": [signal, bkg]}]}, poi_name="mu", validate=False)
            data = list(n) + model.config.auxdata
            init, bounds = model.config.suggested_init(), model.config.suggested_bounds()
            bounds[model.config.poi_index] = (0.0, 10.0)
            pars, best = pyhf.infer.mle.fit(data, model, init_pars=init, par_bounds=bounds, return_fitted_val=True)

            def q(mu):
                return float(pyhf.infer.mle.fixed_poi_fit(mu, data, model, init_pars=init, par_bounds=bounds,
                                                          return_fitted_val=True)[1]) - float(best) - 1
            mu_hat = float(pars[model.config.poi_index])
            return mu_hat, optimize.brentq(q, 0.0, mu_hat, xtol=1e-8), optimize.brentq(q, mu_hat, mu_hat + 5, xtol=1e-8)

        nominal, shifted = self.MU0 * self.s + self.b, self.MU0 * self.s + self.up
        for label, n, nuisance in (("nominal", nominal, False), ("shifted", shifted, False),
                                   ("nominal+nuisance", nominal, True), ("shifted+nuisance", shifted, True)):
            with self.subTest(label):
                mu_hat, lo, hi = self.fit(n, nuisance)
                ref = interval(n, nuisance)
                self.assertAlmostEqual(lo, ref[1], delta=1e-5)
                self.assertAlmostEqual(hi, ref[2], delta=1e-5)
                self.assertAlmostEqual(mu_hat, ref[0], delta=4e-3 * (hi - lo) / 2)


if __name__ == "__main__":
    unittest.main()
