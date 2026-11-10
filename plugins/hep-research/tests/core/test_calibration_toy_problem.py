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


def calorimeter(exposure=400, mc=4000):
    return TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), NAMES, THETA, exposure=exposure, mc_events=mc,
                         phi_P={"material_thickness": (1.0, 0.05)},
                         eta=[{"relative": {n: 0.01 for n in NAMES if "mean" in n}}])


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
        p = calorimeter()
        truth = p.initial_beta({"light_yield": 100, "pde": 0.25, "gain": 10.0})
        p.data = p.simulate(truth, np.random.default_rng(5))
        p.sigma_noise = TP.estimate_sigma_noise(p, truth)
        self.assertGreater(p.sigma_noise, 0.0)
        f = F.iterate(p, p.initial_beta(), lndet=False)
        self.assertTrue(f.converged)
        # light yield and thickness are degenerate (LY exp(-t/lambda)); pde and gain are measured
        self.assertLess(abs(f.beta[1] - 0.25) / f.sigma_tot[1], 4.0)
        self.assertLess(abs(f.beta[2] - 10.0) / f.sigma_tot[2], 4.0)
        self.assertAlmostEqual(f.beta[0] * np.exp(-f.beta[3] / 10.0) / (100 * np.exp(-0.1)), 1.0, delta=0.03)

    def test_factory_needs_a_toy_evaluator_and_one_exposure(self):
        with self.assertRaises(problems.ProblemError):
            problems.model_builder({"evaluator": {"kind": "g4sim"}})
        with self.assertRaises(problems.ProblemError):
            problems.from_inputs({"observables": [], "parameters": [], "exposure": {"a": 1, "b": 2}},
                                 {"evaluator": {"kind": "toy-detector"}})


if __name__ == "__main__":
    unittest.main()
