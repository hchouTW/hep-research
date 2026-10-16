"""hep-statistics audit T18 (covariance fits) and T19 (multiplicative uncertainties): skills/hep-statistics/scripts/
covariance_fit.py. SYNTHETIC. Criteria fixed before the runs: a mean chi2 within 4 standard errors of its dof over
toys; a bias test at 4 standard errors; oracle values to 1e-6 (closed forms) or 1e-5 (independent minimization)."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))
SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"

import covariance_fit as cf  # noqa: E402

X = np.arange(8.0)
P = np.exp(-0.3 * X)
P /= P.sum()
N = 5000
C_NORM = (np.diag(P) - np.outer(P, P)) / N          # covariance of a normalized spectrum: singular along (1, ..., 1)
ONES = [[1.0] * 8]


class RelativeCovChecksSTH36(unittest.TestCase):
    """STH-T3.6: relative_cov must be n x n, symmetric and positive semidefinite; a 1 x 1 matrix is not broadcast."""
    Y, COV = [1.0, 1.1, 0.9], (0.01 * np.eye(3)).tolist()

    def test_refusals(self):
        for rel in ([[0.01]], [[0.01, 0.002, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.01]],
                    [[0.01, 0.02, 0.0], [0.02, 0.01, 0.0], [0.0, 0.0, 0.01]], [[0.01, 0, 0], [0, -0.01, 0], [0, 0, 0.01]]):
            with self.subTest(rel=rel), self.assertRaises(cf.CovFitError):
                cf.fit(self.Y, self.COV, "constant", multiplicative={"relative_cov": rel, "mode": "data"})

    def test_valid_full_matrix_fits(self):
        rel = (0.0004 * np.ones((3, 3))).tolist()
        r = cf.fit(self.Y, self.COV, "constant", multiplicative={"relative_cov": rel, "mode": "model"})
        self.assertIn("theta", r)


BPL_X = np.logspace(0, 2, 20)
BPL_TRUTH = np.array([math.log(1e3), 2.7, 2.4, math.log(10.0)])


def _bpl_setup(truth=BPL_TRUTH, smoothness=0.0):
    f = np.exp(cf.bpl_log(truth, BPL_X, smoothness))
    return f, np.diag((0.02 * f) ** 2) + np.outer(0.01 * f, 0.01 * f)


class BrokenPowerLawSTH313(unittest.TestCase):
    """STH-T3.13: broken power laws (sharp and smooth) and a plug-in model in covariance_fit.py; the break position is
    a non-regular parameter, so its interval comes from a profile scan calibrated with toys (break-scan)."""

    def test_asimov_break_scan_recovers_the_truth(self):
        f, cov = _bpl_setup()
        r = cf.break_scan({"y": f.tolist(), "cov": cov.tolist(), "x": BPL_X.tolist(), "break_range": [3.0, 35.0],
                           "grid_points": 200}, 100, 1)
        self.assertAlmostEqual(math.log(r["best_fit"]["x_b"]), math.log(10.0), delta=r["grid"]["resolution_ln"])
        self.assertAlmostEqual(r["best_fit"]["gamma1"], 2.7, delta=0.01)
        self.assertTrue(any(lo <= 10.0 <= hi for lo, hi in r["break_interval"]["intervals"]))
        self.assertLess(r["break_test"]["p_toys"]["upper_bound"]["value"], 0.05)

    def test_smooth_model_fit_and_plugin(self):
        f, cov = _bpl_setup(smoothness=0.2)
        r = cf.fit(f.tolist(), cov.tolist(), "smoothly-broken-power-law", BPL_X.tolist(),
                   start=[math.log(900.0), 2.6, 2.5, math.log(9.0)], model_options={"smoothness": 0.2})
        self.assertTrue(np.allclose(r["theta"], BPL_TRUTH, atol=1e-4), r["theta"])
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            plug = Path(td) / "m.py"
            plug.write_text("import numpy as np\ndef predict(theta, x):\n    return theta[0] * np.exp(-x / theta[1])\n")
            xs = np.linspace(0.0, 5.0, 8)
            y = 4.0 * np.exp(-xs / 2.0)
            r = cf.fit(y.tolist(), (0.01 * np.eye(8)).tolist(), "plugin", xs.tolist(), start=[3.0, 1.5],
                       model_options={"plugin": {"path": str(plug), "function": "predict", "n_params": 2}},
                       allow_plugin=True)
            self.assertTrue(np.allclose(r["theta"], [4.0, 2.0], atol=1e-5), r["theta"])

    def test_refusals(self):
        f, cov = _bpl_setup()
        for d in ({"y": f.tolist(), "cov": cov.tolist(), "x": (-BPL_X).tolist()},
                  {"y": f.tolist(), "cov": cov.tolist(), "x": BPL_X.tolist(), "break_range": [0.5, 50.0]},
                  {"y": (-f).tolist(), "cov": cov.tolist(), "x": BPL_X.tolist()}):
            with self.assertRaises(cf.CovFitInputError):
                cf.break_scan(d, 100, 1)
        with self.assertRaises(cf.CovFitInputError):
            cf.fit(f.tolist(), cov.tolist(), "broken-power-law", BPL_X.tolist())          # no start

    def test_no_break_negative_control_shows_wilks_miscalibration(self):
        """With no break (gamma1 = gamma2) x_b is undefined and the break test maximizes over it (Davies): the Wilks
        reference for the one extra index at a known break, chi2(1), rejects far more often than its 5%; chi2(2) is not
        derived either (here it happens to land near 5%). Only the toy p-value is valid."""
        truth = BPL_TRUTH.copy()
        truth[2] = truth[1]
        f, cov = _bpl_setup(truth)
        rng = np.random.default_rng(21)
        Y = np.clip(rng.multivariate_normal(f, cov, size=400), 1e-9, None)
        grid = np.linspace(math.log(3.0), math.log(35.0), 60)
        W = np.linalg.inv(cov)
        q = cf._single_pl_chi2(Y, W, BPL_X)[0] - cf._profile_bpl(Y, W, BPL_X, grid, 0.0)[0].min(axis=1)
        from scipy.stats import chi2
        rate = float(np.mean(q > chi2.ppf(0.95, 1)))
        self.assertGreater(rate, 0.10, rate)   # Wilks (x_b known) would give 0.05

    @unittest.skipUnless(__import__("os").environ.get("HEP_SLOW_TESTS") == "1", "slow (about 6 minutes): set HEP_SLOW_TESTS=1")
    def test_slow_break_bias_and_interval_coverage(self):
        """500 toys at one truth (sharp break at x_b = 10, gamma 2.7 -> 2.4, 20 log-spaced points, 2% independent and
        1% correlated errors): bias of ln x_b below 0.2 sigma and 68.27% interval coverage within +-0.03."""
        f, cov = _bpl_setup()
        rng = np.random.default_rng(11)
        hits, est = 0, []
        for i in range(500):
            y = rng.multivariate_normal(f, cov)
            r = cf.break_scan({"y": y.tolist(), "cov": cov.tolist(), "x": BPL_X.tolist(), "break_range": [3.0, 35.0],
                               "grid_points": 200}, 100, i + 1)
            est.append(math.log(r["best_fit"]["x_b"]))
            hits += any(lo <= 10.0 <= hi for lo, hi in r["break_interval"]["intervals"])
        est = np.array(est)
        self.assertLess(abs(est.mean() - math.log(10.0)) / est.std(ddof=1), 0.2)
        self.assertLess(abs(hits / 500 - 0.6827), 0.03, hits / 500)


class T18ConstrainedSpectrum(unittest.TestCase):
    def test_unconstrained_fit_is_refused_not_regularized(self):
        y = np.random.default_rng(1).multinomial(N, P) / N
        with self.assertRaisesRegex(cf.CovFitError, "singular beyond the 0 declared"):
            cf.fit(y, C_NORM, "exponential-normalized", x=X, start=[0.2])
        with self.assertRaisesRegex(cf.CovFitError, "not a null direction"):
            cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=[[1.0] * 7 + [2.0]], start=[0.2])

    def test_dof_and_chi2_in_the_constrained_subspace(self):
        rng = np.random.default_rng(2)
        chi2, pulls = [], []
        for _ in range(400):
            y = rng.multinomial(N, P) / N
            r = cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=ONES, start=[0.2])
            self.assertEqual((r["dof"], r["covariance"]["rank_in_subspace"]), (6, 7))
            chi2.append(r["chi2"])
            pulls.append((r["theta"][0] - 0.3) / r["theta_errors"][0])
        self.assertLess(abs(np.mean(chi2) - 6), 4 * math.sqrt(2 * 6 / 400))
        self.assertLess(abs(np.std(pulls) - 1), 4 / math.sqrt(2 * 400))

    def test_diagonal_approximation_is_a_detectable_error(self):
        rng = np.random.default_rng(3)
        rho = 0.8 ** np.abs(np.subtract.outer(X, X))
        cov = 0.04 * rho
        chol = np.linalg.cholesky(cov)
        full, diag = [], []
        for _ in range(400):
            y = 1.0 + 0.05 * X + chol @ rng.standard_normal(8)
            full.append(cf.fit(y, cov, "line", x=X, start=[1.0, 0.0])["chi2"])
            diag.append(cf.fit(y, np.diag(np.diag(cov)), "line", x=X, start=[1.0, 0.0])["chi2"])
        se = 4 * math.sqrt(2 * 6 / 400)
        self.assertLess(abs(np.mean(full) - 6), se)
        self.assertGreater(abs(np.mean(diag) - 6), se)

    def test_near_singular_is_fitted_and_flagged(self):
        ev = np.array([1.0, 0.5, 0.2, 1e-11])
        q = np.linalg.qr(np.random.default_rng(4).standard_normal((4, 4)))[0]
        cov = q @ np.diag(ev) @ q.T
        r = cf.fit(np.array([1.0, 1.1, 0.9, 1.05]), cov, "constant")
        self.assertTrue(r["covariance"]["near_singular"])
        self.assertGreater(r["covariance"]["condition_number"], 1e10)

    def test_units_do_not_change_the_inference(self):
        y = np.random.default_rng(5).multinomial(N, P) / N
        a = cf.fit(y, C_NORM, "exponential-normalized", x=X, constraints=ONES, start=[0.2])
        rho = 0.5 ** np.abs(np.subtract.outer(X, X))
        yl = 2.0 + 0.1 * X + np.random.default_rng(6).standard_normal(8) * 0.1
        b1 = cf.fit(yl, 0.01 * rho, "line", x=X, start=[1.0, 0.0])
        b2 = cf.fit(1000 * yl, 1e4 * rho, "line", x=X, start=[1000.0, 0.0])
        self.assertAlmostEqual(b1["chi2"], b2["chi2"], delta=1e-6 * b1["chi2"])
        self.assertAlmostEqual(1000 * b1["theta"][1], b2["theta"][1], delta=1e-5 * abs(b2["theta"][1]))
        self.assertEqual(a["dof"], 6)

    def test_parameter_dependent_covariance_matches_the_exact_gaussian_mle(self):
        rel = 0.01 * np.eye(5)                     # 10% independent errors that scale with the model
        add = 1e-4 * np.eye(5)
        rng = np.random.default_rng(7)
        y = 10.0 * (1 + 0.1 * rng.standard_normal(5))
        r = cf.fit(y, add, "constant", multiplicative={"relative_cov": rel.tolist(), "mode": "model"}, start=[9.0])

        def m2ll(t):
            c = add + rel * t[0] ** 2
            d = y - t[0]
            return float(d @ np.linalg.solve(c, d) + np.linalg.slogdet(c)[1])
        ref = optimize.minimize(m2ll, [9.0], method="Nelder-Mead", options={"xatol": 1e-10, "fatol": 1e-12}).x[0]
        self.assertAlmostEqual(r["theta"][0], ref, delta=1e-5)
        self.assertTrue(r["logdet"])


class T19Multiplicative(unittest.TestCase):
    Y = [1.5, 1.0]
    STAT = np.diag([0.15 ** 2, 0.10 ** 2])
    REL = np.full((2, 2), 0.04)                    # 20% common normalization

    def run_mode(self, mode, y=None):
        return cf.fit(y if y is not None else self.Y, self.STAT, "constant",
                      multiplicative={"relative_cov": self.REL.tolist(), "mode": mode}, start=[1.2])

    def test_peelle_oracles(self):
        c = self.STAT + 0.04 * np.outer(self.Y, self.Y)        # GLS with the covariance scaled by the data
        w = np.linalg.solve(c, np.ones(2))
        r = self.run_mode("data")
        self.assertAlmostEqual(r["theta"][0], w @ self.Y / w.sum(), delta=1e-6)   # 0.882: below both measurements
        self.assertAlmostEqual(r["theta_errors"][0], 1 / math.sqrt(w.sum()), delta=1e-5)
        wm = np.array([1 / 0.15 ** 2, 1 / 0.10 ** 2])
        mean = wm @ self.Y / wm.sum()
        r = self.run_mode("nuisance")
        self.assertAlmostEqual(r["theta"][0], mean, delta=1e-6)                     # 1.154
        self.assertAlmostEqual(r["theta_errors"][0], math.sqrt(1 / wm.sum() + 0.04 * mean ** 2), delta=1e-4)

    def test_data_scaled_covariance_is_biased_and_the_nuisance_form_is_not(self):
        rng = np.random.default_rng(8)
        est = {m: [] for m in ("data", "model", "nuisance")}
        for _ in range(1000):
            norm = 1 + 0.2 * rng.standard_normal()
            y = norm * (1.0 + np.array([0.15, 0.10]) * rng.standard_normal(2))
            for m in est:
                est[m].append(self.run_mode(m, y)["theta"][0])
        for m, v in est.items():
            v = np.array(v)
            setattr(self, f"bias_{m}", (v.mean() - 1.0, v.std() / math.sqrt(len(v))))
        b, se = self.bias_data
        self.assertLess(b, -4 * se)                                # biased low (Peelle)
        b2, se2 = self.bias_nuisance
        self.assertLess(abs(b2), 4 * se2)                          # the normalization as a nuisance: unbiased
        # recorded, not required: the Gaussian likelihood with C(theta) and ln det is also biased low here
        # (-0.039 +- 0.007 at seed 8): a common normalization is not an additive Gaussian error
        b3, se3 = self.bias_model
        self.assertLess(b3, 0.0)

    def test_mode_is_required(self):
        with self.assertRaises(cf.CovFitError):
            cf.fit(self.Y, self.STAT, "constant", multiplicative={"relative_cov": self.REL.tolist()})


class PluginModelF09(unittest.TestCase):
    """F-09: a plugin model runs user code, so it runs only with --allow-plugin; its path is resolved relative to the
    input file; its errors become a failed JSON status (exit 1), never a traceback. Before the fix the plugin ran
    without any opt-in, from a path relative to the working directory, and its exceptions escaped."""

    PLUGIN = "import numpy as np\ndef predict(theta, x):\n    return theta[0] * np.exp(-x / theta[1])\n"

    def cli(self, td, plugin_source, *extra):
        import json
        import subprocess
        d = Path(td) / "inputs"
        d.mkdir()
        (d / "m.py").write_text(plugin_source)
        xs = np.linspace(0.0, 5.0, 8)
        doc = {"y": (4.0 * np.exp(-xs / 2.0)).tolist(), "cov": (0.01 * np.eye(8)).tolist(), "x": xs.tolist(),
               "model": "plugin", "start": [3.0, 1.5],
               "model_options": {"plugin": {"path": "m.py", "function": "predict", "n_params": 2}}}
        (d / "fit.json").write_text(json.dumps(doc))
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "fit", "--input", str(d / "fit.json"), *extra],
                             capture_output=True, text=True, timeout=300, cwd=td)    # cwd is not the input folder
        return res.returncode, json.loads(res.stdout), res.stderr

    def test_plugin_needs_the_flag(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            code, out, _ = self.cli(td, self.PLUGIN)
            self.assertEqual((code, out["status"]), (1, "refused"))
            self.assertIn("--allow-plugin", out["error"])

    def test_plugin_path_is_relative_to_the_input_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            code, out, err = self.cli(td, self.PLUGIN, "--allow-plugin")
            self.assertEqual(code, 0, out)
            self.assertTrue(np.allclose(out["theta"], [4.0, 2.0], atol=1e-5))

    def test_plugin_errors_are_failed_json(self):
        import tempfile
        for source in ("raise RuntimeError('broken at import')\n",
                       "def predict(theta, x):\n    raise ZeroDivisionError('inside the model')\n"):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as td:
                code, out, err = self.cli(td, source, "--allow-plugin")
                self.assertEqual((code, out["status"]), (1, "failed"), out)
                self.assertIn("plugin", out["error"])
                self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
