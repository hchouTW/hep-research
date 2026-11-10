"""Weights of Part B sections 3.6 and 6.1 (phase 1): the formula, the w = 1 check, the mixture and its merging,
step-level reweighting, and reweighting against rerun (section 15.3.1 weight formula; section 15.2)."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration import kernel_check, reweight  # noqa: E402


def chi2_p(a, b):
    """p-value of the difference of two predictions with the sum of their MC covariances (the gate-2 metric)."""
    d = a["pred"] - b["pred"]
    V = a["V_MC"] + b["V_MC"]
    keep = np.diag(V) > 0
    d, V = d[keep], V[np.ix_(keep, keep)]
    return float(stats.chi2.sf(d @ np.linalg.solve(V, d), len(d)))


class Formula(unittest.TestCase):
    def test_log_weights_by_hand(self):
        lt = np.log([0.5, 0.2])
        comps = [np.log([0.4, 0.1]), np.log([0.2, 0.3])]
        lw = reweight.log_weights(lt, comps, [3, 1], np.log([0.5, 0.5]))
        den = 0.75 * np.array([0.4, 0.1]) + 0.25 * np.array([0.2, 0.3])
        np.testing.assert_allclose(np.exp(lw), np.array([0.5, 0.2]) / den / 0.5)

    def test_nan_term_is_missing_support(self):
        self.assertTrue(np.isnan(reweight.log_weights(np.array([np.nan]), None, None)).all())

    def test_kish_and_poisson_prediction(self):
        self.assertEqual(reweight.kish(np.ones(10)), 10.0)
        self.assertAlmostEqual(reweight.poisson_ess_fraction([1000.0], 1.1), math.exp(-10.0))
        self.assertLess(reweight.poisson_ess_fraction([1000.0], 1.1), 5e-5)      # section 3.6: 4.5e-5
        self.assertEqual(reweight.merged_fractions([300, 100]), [0.75, 0.25])

    def test_w_is_one_without_proposal_at_theta0(self):
        """Section 15.3.1: S_q empty and theta' = theta_0 gives w = 1 (|w - 1| <= 1e-12)."""
        ev = E.make({"evaluator": {"kind": "toy-detector", "events": 2000}, "seeds": {"nominal": 1},
                     "methods": H.toy_design()["plan"]["methods"]})
        nodes = ["photon_generation", "pde", "gain", "momentum_measurement"]       # density nodes, nothing filtered
        w = ev.weights({}, nodes=nodes)
        self.assertNotIn("_missing_support", w)
        self.assertLessEqual(max(float(np.abs(x - 1).max()) for x in w.values()), 1e-12)
        w = ev.weights({}, nodes=["electronics"])                # zero suppression: missing support, never a weight
        self.assertEqual(w.pop("_missing_support"), ["spe"])

    def test_mixture_weights_at_theta0_are_not_one(self):
        ev = E.make({"evaluator": {"kind": "toy-detector", "events": 2000}, "seeds": {"nominal": 1},
                     "proposal": {"nodes": ["pde"], "components": [{"theta": {"pde": 0.245}}, {"theta": {"pde": 0.255}}]}})
        w = ev.weights({})
        self.assertGreater(float(np.abs(w["beam4"] - 1).max()), 1e-3)
        self.assertAlmostEqual(float(w["beam4"].mean()), 1.0, delta=0.05)


class AgainstRerun(unittest.TestCase):
    def test_s_theta_minus_s_q_nonempty(self):
        """Section 15.3.1: theta acting on two nodes, proposal broadened only on PDE (S_theta \\ S_q = {photon
        generation}): reweighting and rerun agree."""
        ev = E.make({"evaluator": {"kind": "toy-detector", "events": 10_000}, "seeds": {"nominal": 2},
                     "proposal": {"nodes": ["pde"], "components": [{"theta": {"pde": v}} for v in (0.245, 0.25, 0.255)]}})
        th = {"light_yield": 101.5, "pde": 0.253}
        rw = ev.evaluate(th)
        self.assertEqual(set(rw["methods"].values()), {"analytic-reweighting"})
        rr = ev.rerun(["photon_generation", "pde"], th, 99, params=list(th))
        self.assertGreater(chi2_p(rw, rr), 1e-3)

    def test_merging_additional_events(self):
        """Section 6.1 item 5: adding a component and recomputing c_j raises the ESS at a far point and keeps the
        reweighted prediction unbiased."""
        far = {"mu": 1.8}
        c, p = H.gaussian_chain()
        one = E.make(p)
        c, p = H.gaussian_chain(proposal={"nodes": ["x"], "components": [{"theta": {"mu": 0.0}, "fraction": 2},
                                                                          {"theta": {"mu": 1.5}, "fraction": 1}]})
        merged = E.make(p)
        self.assertGreater(merged.evaluate(far)["n_eff"][0], 3 * one.evaluate(far)["n_eff"][0])
        r = merged.evaluate(far)
        self.assertLess(abs(r["pred"][0] - 1.8), 5 * math.sqrt(r["V_MC"][0, 0]))

    def test_step_level_reweighting(self):
        """Section 3.6: a multi-step process with per-step data stored; the weight is the product over steps; it
        agrees with a rerun, and its ESS falls with the number of steps."""
        def case(n_steps):
            return H.chain_case([{"id": "shower", "kernel": "steps", "args": {"keep": "keep", "n_steps": n_steps}}],
                                [{"name": "rem_mean", "node": "shower", "var": "remaining", "link": "log"}],
                                {"keep": 0.9}, {"keep": {"nodes": ["shower"], "bounds": [0.89, 0.91]}}, {"run": 500},
                                methods={"keep": "step-level-reweighting"})
        ess = []
        for n_steps in (2, 16):
            _, p = case(n_steps)
            ev = E.make(p)
            th = {"keep": 0.905}
            rw, rr = ev.evaluate(th), ev.rerun("shower", th, 5)
            self.assertGreater(chi2_p(rw, rr), 1e-3)
            ess.append(rw["n_eff"][0])
        self.assertLess(ess[1], ess[0])

    def test_paired_covariance_is_smaller_than_the_sum(self):
        ev = E.make({"evaluator": {"kind": "toy-detector", "events": 4000}, "seeds": {"nominal": 3}})
        th = {"gain": 10.1}
        a, b = ev.evaluate(th), ev.rerun("gain", th, 4)
        Vp = kernel_check.paired_covariance(a, b)
        k = a["names"].index("beam4_e_mean")
        self.assertLess(Vp[k, k], a["V_MC"][k, k] + b["V_MC"][k, k])


if __name__ == "__main__":
    unittest.main()
