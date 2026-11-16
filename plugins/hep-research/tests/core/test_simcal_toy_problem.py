"""The toy detector as a fit problem (phase 2): bootstrap V-hat, data, fit (section 15.1 toy detector, synthetic)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import fit as F  # noqa: E402
from core.calibration import problems  # noqa: E402
from core.calibration import toy  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402

NAMES = [f"beam{e}_e_mean" for e in (1, 2, 3, 4)] + [f"beam{e}_e_width" for e in (1, 2, 3, 4)] + \
    ["light_e_mean", "light_e_width", "spe_e_mean", "spe_e_width"]
THETA = {"light_yield": {"bounds": (20, 400), "prior": (80, 120)}, "pde": {"bounds": (0.01, 0.99), "prior": (0.2, 0.3)},
         "gain": {"bounds": (1, 100), "prior": (8, 12)}}


def calorimeter(exposure=400, mc=4000, thickness_by_yield=False):
    return TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), NAMES, THETA, exposure=exposure, mc_events=mc,
                         phi_P={"material_thickness": (1.0, 0.05)},
                         eta=[{"relative": {n: 0.01 for n in NAMES if "mean" in n}}], thickness_by_yield=thickness_by_yield)


class Bootstrap(unittest.TestCase):
    def test_per_set_summary_equals_observe(self):
        p = calorimeter()
        m = p._data_model
        ev = toy.ChainEvaluator(m, {"seeds": {"nominal": 1}})
        gen = ev.generate(7, params=dict(m.nominal))
        events = {r: v["events"] for r, v in gen["runs"].items()}
        one = TP.per_set_summaries(m, events, NAMES, 1)[0]
        ref = toy.observe(m, events, {r: np.ones(m.runs[r].n) for r in events}, NAMES)["pred"]
        np.testing.assert_allclose(one, ref, rtol=1e-12)

    def test_vhat_agrees_with_the_delta_method_cross_check(self):
        """The event-level parametric bootstrap at theta_ref against the per-event covariance / exposure (the delta
        method, a cross-check only, section 2.1): diagonal within 20% (B = 500)."""
        p = calorimeter()
        V = p.bootstrap_vhat({}, 3)
        r = p.ev.evaluate({}, names=NAMES)
        D = p._dlink(r["pred"])
        Vd = r["s2"] / p.exposure * np.outer(D, D)
        ratio = np.diag(V) / np.diag(Vd)
        self.assertTrue(np.all(np.abs(ratio - 1) < 0.2), ratio)

    def test_common_random_numbers(self):
        """The same seed regenerates the same V-hat at the same theta_ref; a nearby theta_ref moves it only slightly
        (section 2.1 (i))."""
        p = calorimeter()
        a, b = p.bootstrap_vhat({}, 3), p.bootstrap_vhat({}, 3)
        np.testing.assert_array_equal(a, b)
        c = p.bootstrap_vhat({"light_yield": 100.5}, 3)
        self.assertLess(np.max(np.abs(c - a) / np.sqrt(np.outer(np.diag(a), np.diag(a)))), 0.05)


class Fit(unittest.TestCase):
    def test_fit_converges_with_sigma_noise(self):
        """The fit converges with sigma_noise > 0 from the MC seeds. The thickness is evaluated as its equivalent light
        yield (smooth in t); resimulated with common random numbers it is a staircase on discrete counts along a
        direction exactly degenerate with the light yield, where Fisher scoring can stall (seen 2026-11-11 after the
        width estimator changed by O(1/N): a marginal case, not a property this test checks)."""
        p = calorimeter(thickness_by_yield=True)
        truth = p.initial_beta({"light_yield": 100, "pde": 0.25, "gain": 10.0})
        p.observed = p.simulate(truth, np.random.default_rng(5), nominal=False)
        p.sigma_noise = TP.estimate_sigma_noise(p, truth)
        self.assertGreater(p.sigma_noise, 0.0)
        f = F.iterate(p, p.initial_beta(), lndet=False)
        self.assertTrue(f.converged)
        # light yield and thickness are degenerate (LY exp(-t/lambda)); pde and gain are measured
        self.assertLess(abs(f.beta[1] - 0.25) / f.sigma_tot[1], 4.0)
        self.assertLess(abs(f.beta[2] - 10.0) / f.sigma_tot[2], 4.0)
        self.assertAlmostEqual(f.beta[0] * np.exp(-f.beta[3] / 10.0) / (100 * np.exp(-0.1)), 1.0, delta=0.03)

    def test_noisy_objective_does_not_stop_early(self):
        """With sigma_noise > 0 the G1 threshold is loose (0.1 sigma_noise); the minimizer still pursues 0.002 tol, so
        fits from distant starts agree within 0.05 sigma (a precise minimum, needed by the gate-2 comparison). The thickness
        is evaluated by its equivalent yield (smooth); resimulated, the objective is a staircase below ~0.01 in t."""
        p = calorimeter(thickness_by_yield=True)
        truth = p.initial_beta({"light_yield": 100, "pde": 0.25, "gain": 10.0})
        p.observed = p.simulate(truth, np.random.default_rng(5), nominal=False)
        p.sigma_noise = TP.estimate_sigma_noise(p, truth)
        a = F.iterate(p, p.initial_beta({"light_yield": 85, "pde": 0.21, "gain": 8.5}), lndet=False)
        b = F.iterate(p, p.initial_beta({"light_yield": 115, "pde": 0.29, "gain": 11.5}), lndet=False)
        self.assertTrue(a.converged and b.converged)
        self.assertLess(float(np.max(np.abs(a.beta[:3] - b.beta[:3]) / a.sigma_tot)), 0.05)

    def test_thickness_by_yield_agrees_with_resimulation(self):
        """The equivalent-yield evaluation of the thickness agrees with its resimulation within the MC error (both
        estimate the same law; section 3.6)."""
        a = calorimeter(mc=20000)
        b = calorimeter(mc=20000, thickness_by_yield=True)
        tp = np.array([100.0, 0.25, 10.0, 1.05])
        ra = a._predict(a.params_of(tp)[0])
        rb = b._predict(b.params_of(tp)[0])
        z = (ra["pred"] - rb["pred"]) / np.sqrt(np.diag(ra["V_MC"]) + np.diag(rb["V_MC"]))
        self.assertLess(float(np.max(np.abs(z))), 4.0)

    def test_null_toys_centre_on_the_nominal_prediction(self):
        """Toys under the null hypothesis draw from the nominal MC weighted to the truth: their mean is the nominal MC
        prediction (section 6.6), within the toys' standard error."""
        p = calorimeter(mc=4000, thickness_by_yield=True)
        tp = np.array([100.0, 0.25, 10.0, 1.0])
        nom = p._to_link(p._predict(p.params_of(tp)[0])["pred"])
        ys = np.array([p.observe_nominal(p.params_of(tp)[0], np.random.default_rng([9, i])) for i in range(200)])
        z = (ys.mean(0) - nom) / (ys.std(0, ddof=1) / np.sqrt(len(ys)))
        self.assertLess(float(np.max(np.abs(z))), 4.0)

    def test_validation_observables_are_a_separate_sample(self):
        """Holdout on the toy detector (section 9.2, review F1): the validation rows come from their own nominal MC
        and their own data; their null toys centre on the validation nominal prediction; V_data from their bootstrap."""
        val = ["beam2_e_width", "beam4_e_width"]
        p = TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), NAMES, THETA, exposure=400, mc_events=4000,
                          val_names=val, thickness_by_yield=True)
        tp = np.array([100.0, 0.25, 10.0])
        nom = p.h_val(tp)
        ys = np.array([p.simulate_val(np.r_[tp, np.zeros(p.layout.n_beta - 3)], np.random.default_rng([8, i]))
                       for i in range(150)])
        z = (ys.mean(0) - nom) / (ys.std(0, ddof=1) / np.sqrt(len(ys)))
        self.assertLess(float(np.max(np.abs(z))), 4.0)
        p.set_val_point(tp)
        v = p.val
        self.assertEqual(v["V_data"].shape, (2, 2))
        ratio = np.diag(v["V_data"]) / ys.var(0, ddof=1)
        self.assertTrue(np.all(np.abs(ratio - 1) < 0.35), ratio)        # bootstrap vs toy spread (150 toys)
        self.assertFalse(np.allclose(p.replica_pert_val(np.random.default_rng(1)), 0))

    def test_subset_restricts_the_rows(self):
        p = calorimeter()
        p.observed = p.asimov(p.initial_beta())
        s = p.subset([0, 2, 9])
        self.assertEqual(s.names, [NAMES[0], NAMES[2], NAMES[9]])
        np.testing.assert_allclose(s.observed.y_gauss, p.observed.y_gauss[[0, 2, 9]])
        np.testing.assert_allclose(s.h(p.initial_beta()[:4]), p.h(p.initial_beta()[:4])[[0, 2, 9]])

    def test_count_observables_with_bb_lite(self):
        """Count observables (section 2.1 block rules): an absolute Poisson histogram of the track-5 momenta with
        BB-lite; the fit converges and the auxiliary-measurement part of the covariance is about
        sqrt(exposure / MC) of sigma_tot (MC 10x the data); data counts have a Poisson total."""
        th = {"momentum_scale": {"bounds": (0.5, 1.5), "prior": (0.98, 1.02)},
              "sum_term_a": {"bounds": (0.2, 3.0), "prior": (0.8, 1.2)}}
        counts = {"h": {"source": "track5_p_mean", "edges": np.linspace(4.86, 5.14, 11), "kind": "absolute",
                        "bb": True}}
        p = TP.ToyProblem(lambda n: toy.build_toy(n, "full", 1.0, ["track5"]), [], th, exposure=2000,
                          mc_events=20000, counts=counts)
        b = np.r_[[1.004, 1.05], np.zeros(p.layout.n_beta - 2)]
        totals = [p.simulate(b, np.random.default_rng([4, i]), nominal=False).counts["h"].sum() for i in range(3)]
        self.assertGreater(len(set(totals)), 1)                         # a Poisson total, not a fixed one
        p.observed = p.simulate(b, np.random.default_rng(5), nominal=False)
        f = F.iterate(p, p.initial_beta())
        self.assertTrue(f.converged, f.reason)
        ratio = np.sqrt(np.diag(F.sigma_mc(p, f, None))[:2]) / f.sigma_tot
        self.assertTrue(np.all((ratio > 0.2) & (ratio < 0.45)), ratio)

    def test_factory_needs_a_toy_evaluator_and_one_exposure(self):
        with self.assertRaises(problems.ProblemError):
            problems.model_builder({"evaluator": {"kind": "g4sim"}})
        with self.assertRaises(problems.ProblemError):
            problems.from_inputs({"observables": [], "parameters": [], "exposure": {"a": 1, "b": 2}},
                                 {"evaluator": {"kind": "toy-detector"}})


if __name__ == "__main__":
    unittest.main()
