"""G8, the closure test of Part B section 8.4 (phase 2, WP5)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import closure as C  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402


class Design(unittest.TestCase):
    def test_n_c_table_of_section_8_4(self):
        """N_bias, N_cov(68%), N_cov(95%) and N_c with the non-convergence margin, d = 3, 6, 11."""
        expect = {3: ((53, 99, 99), (369, 518, 518)), 6: ((59, 114, 114), (416, 576, 576)),
                  11: ((65, 124, 124), (453, 623, 623))}
        for d, (std, full) in expect.items():
            s, f = C.n_c(d, "standard"), C.n_c(d, "full")
            self.assertEqual((s["N_bias"], s["N_cov_68"], s["N_c"]), std)
            self.assertEqual((f["N_cov_68"], f["N_cov_95"], f["N_c"]), full)

    def test_holm(self):
        sig = C.holm({"a": 0.001, "b": 0.02, "c": 0.04})
        self.assertEqual(sig, {"a": True, "b": True, "c": True})
        self.assertEqual(C.holm({"a": 0.001, "b": 0.03, "c": 0.04})["b"], False)

    def test_c0_prime(self):
        self.assertAlmostEqual(C.c0_prime(0.95), 0.9495, places=4)


def synthetic(N, d, bias=0.0, cov=0.68, seed=0, nontruth=False):
    rng = np.random.default_rng(seed)
    err = rng.normal(bias, 1.0, size=(N, d))
    z68, z95 = 1.0 * (cov / 0.68) if cov < 0.68 else 1.0, 1.96
    if cov < 0.68:
        from scipy import stats
        z68 = stats.norm.ppf(0.5 + cov / 2)
    return {"errors": err, "cover68": np.abs(err - bias * 0) <= z68, "cover95": np.abs(err) <= z95,
            "nontruth_basin": np.full(N, nontruth), "X": 0, "interval_toys": {"X": 0, "n": 0}}


class Decision(unittest.TestCase):
    def test_correct_method_passes(self):
        r = C.g8("standard", ["a", "b", "c"], np.ones(3), synthetic(99, 3, seed=20), synthetic(99, 3, seed=120))
        self.assertEqual(r["status"], "passed")
        self.assertEqual(r["family"], 9)

    def test_bias_needs_significance_and_size(self):
        """A significant bias of 0.15 sigma does not fail (|b-bar| <= 0.2 sigma); 0.5 sigma fails."""
        small = C.g8("standard", ["a"], np.ones(1), synthetic(5000, 1, bias=0.15, seed=3), synthetic(99, 1, seed=4))
        self.assertNotIn("bias", [f["test"] for f in small["fails"]])
        big = C.g8("standard", ["a"], np.ones(1), synthetic(99, 1, bias=0.5, seed=5), synthetic(99, 1, seed=6))
        self.assertIn("bias", [f["test"] for f in big["fails"]])
        self.assertEqual(big["remedy"], "plan")

    def test_undercoverage_and_nontruth_basin_remedy(self):
        r = C.g8("standard", ["a"], np.ones(1), synthetic(99, 1, cov=0.45, seed=7),
                 synthetic(99, 1, seed=8, nontruth=True))
        self.assertEqual(r["status"], "failed")
        self.assertIn("cover68", [f["test"] for f in r["fails"]])
        self.assertEqual(r["remedy"], "contract")             # D57 (2), A8

    def test_ratio_tests(self):
        a, b = synthetic(99, 1, seed=9), synthetic(99, 1, seed=10)
        a["X"] = 9
        self.assertEqual(C.g8("standard", ["a"], np.ones(1), a, b)["finding"], "g8.ratio_test")
        a["X"] = 0
        a["interval_toys"] = {"X": 30, "n": 1000}
        self.assertEqual(C.g8("standard", ["a"], np.ones(1), a, b)["status"], "incomplete")

    def test_screening_and_not_executed(self):
        self.assertIn("closure-not-tested", C.screening([0.01])["flags"])
        self.assertIn("closure-not-tested", C.not_executed("too costly")["flags"])

    def test_injection_points(self):
        c, b = C.injection_points([(0, 5)], [(0.0, 10.0)], np.array([0.3]), np.array([0.2]))
        self.assertAlmostEqual(c[0], 0.6)
        self.assertAlmostEqual(b[0], 0.15)


class LinearToyG8(unittest.TestCase):
    """One G8 at the standard level on a linear toy with count-type errors (V changes with theta): the correct
    fitter passes; a fitter that omits ln det and minimizes chi^2 with V(theta) has a bias of about 0.5 sigma and is
    caught (section 15.3.1). The probability statement of the gate is the gate harness's (card, gate 1 item 10)."""

    def setUp(self):
        self.cfg = T.linear_config(n=20, d=1, count_c=1.0, sd=0.5, bounds=[(-2.0, 10.0)], prior=[(-2.0, 3.0)])
        self.cfg.J[:, 0] = np.abs(self.cfg.J[:, 0]) + 0.5
        self.N = C.n_c(1, "standard")["N_c"]

    def g8_run(self, bad: bool):
        cfg = self.cfg
        p0 = T.make(cfg, [0.5], 1, 2)
        sd = F.iterate(p0, T.initial_beta(p0)).sigma_tot
        interior, boundary = C.injection_points(cfg.prior, cfg.bounds, sd, np.array([0.5]))

        def maker(truth):
            def make(s):
                return T.make(cfg, truth, data_seed=int(1e6 * truth[0]) % 1000 + 10 * s + 3, mc_seed=s + 7)
            return make

        def fit_and_cover(p, s):
            f = F.iterate(p, T.initial_beta(p), lndet=False)
            th = f.beta[0]
            if bad:
                def chi2(x):
                    r = p.reference(np.array([x]), None)
                    return L.Likelihood(p.layout, p.observed, r).deviance(np.r_[x], p.h(np.array([x])))
                th = optimize.minimize_scalar(chi2, bounds=(-2, 10), method="bounded").x
            err = np.array([th - p.truth[0]])
            st = f.sigma_tot
            return f.converged, err, np.abs(err) <= st, np.abs(err) <= 1.96 * st, {"n": 0, "X": 0}, True
        ri = C.run_point(maker(interior), fit_and_cover, self.N, range(10_000))
        rb = C.run_point(maker(boundary), fit_and_cover, self.N, range(20_000, 30_000))
        return C.g8("standard", ["t0"], sd, ri, rb)

    def test_correct_fitter_passes(self):
        self.assertEqual(self.g8_run(False)["status"], "passed")

    def test_fitter_without_lndet_is_caught(self):
        r = self.g8_run(True)
        self.assertEqual(r["status"], "failed")
        self.assertIn("bias", [f["test"] for f in r["fails"]])


class WeightedTruthD6(unittest.TestCase):
    """D6 as approved in A12 (phase 3): G8 pseudo-data from a weighted truth MC."""

    def test_positive_weights_resampled_proportional_to_w(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=4000)
        w = np.exp(0.5 * x)                                          # reweighting a N(0, 1) sample to N(0.5, 1)
        src = C.pseudo_data_source([{"name": "truth", "weights": w}])
        self.assertEqual((src["status"], src["kind"]), ("ok", "positive-weights"))
        n = C.pseudo_data_size({"kind": "fixed", "events": 500}, rng)
        means = [x[C.resample_truth(w, n, rng)].mean() for _ in range(400)]
        target = float(np.sum(w * x) / np.sum(w))
        self.assertLess(abs(np.mean(means) - target), 4 * np.std(means) / np.sqrt(400))
        idx = C.resample_truth(w, 5000, rng)
        self.assertGreater(len(idx) - len(set(idx.tolist())), 0)                      # with replacement
        sizes = [C.pseudo_data_size({"kind": "poisson", "mean": 300.0}, rng) for _ in range(200)]
        self.assertGreater(np.std(sizes), 10)                                         # Poisson around the exposure
        with self.assertRaises(C.ClosureError):
            C.pseudo_data_size({"kind": "multinomial"}, rng)

    def test_negative_weights_form_no_pseudo_data(self):
        """Negative: a sample with negative weights -> no pseudo-data; alone, G8 is a `gap`. Positive control: a
        separate unweighted truth sample is used, the negative one listed as skipped, and G8 decides."""
        w = np.ones(100)
        w[3] = -0.2
        with self.assertRaises(C.ClosureError) as caught:
            C.resample_truth(w, 50, np.random.default_rng(2))
        self.assertEqual(caught.exception.code, "g8.negative_weights")
        gap = C.pseudo_data_source([{"name": "nlo", "weights": w}])
        self.assertEqual((gap["status"], gap["finding"]), ("gap", "g8.no_positive_truth_sample"))
        r = C.g8("standard", ["a"], np.ones(1), synthetic(99, 1, seed=4), synthetic(99, 1, seed=5), source=gap)
        self.assertEqual((r["gate"], r["status"]), ("G8", "gap"))
        ok = C.pseudo_data_source([{"name": "nlo", "weights": w}, {"name": "lo", "weights": None}])
        self.assertEqual((ok["status"], ok["sample"], ok["kind"], ok["skipped_negative_weights"]),
                         ("ok", "lo", "unweighted", ["nlo"]))
        r = C.g8("standard", ["a"], np.ones(1), synthetic(99, 1, seed=4), synthetic(99, 1, seed=5), source=ok)
        self.assertIn(r["status"], ("passed", "failed"))
        self.assertEqual(C.truth_sample_kind(np.zeros(5)), "negative-weights")      # no positive weight at all


if __name__ == "__main__":
    unittest.main()
