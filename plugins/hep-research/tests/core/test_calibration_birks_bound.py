"""Section 5.4 (Part B line 1041; approval A17): P5 feasibility of the k_B rerun from edep_by_dedx_class. The
class-discretization bound at the largest k_B within the prior, propagated to theta via A, must be <= 0.1
sigma_tot^design, else the rerun is infeasible and k_B is resimulated (design.birks_discretization, the P5 item and
design.final_methods)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

import calibration_zdc_fixture as Z  # noqa: E402
import g4sim_calib_eval  # noqa: E402,F401  (registers the g4sim evaluator)
import numpy as np  # noqa: E402

from core.calibration import chain, design, evaluator  # noqa: E402

N = 400
CANDIDATES = {"parameters": {"birks": [{"method": "rerun"}, {"method": "resimulation"}]}}   # section 11.4 Table 2


def methods(ev, c, p):
    """final_methods with the fixture's candidate list (its contract carries no stage graph)."""
    with mock.patch.object(chain, "candidate_methods", return_value=CANDIDATES):
        return design.final_methods(ev, c, p)


def setup(priors=None, thetas=("birks",)):
    bs = {"nominal": Z.batch(61, 0, N)}
    c = Z.contract(thetas=thetas, priors=priors)
    p = Z.plan(bs)
    return evaluator.make(p, c), c, p


class BirksDiscretization(unittest.TestCase):
    def test_the_bound_at_the_largest_prior_birks_fails_and_moves_birks_to_resimulation(self):
        """Negative: the fixture's prior (0.02, 0.4) -> the bound at k_B 0.4 moves theta far beyond 0.1 sigma_tot."""
        ev, c, p = setup()
        r = design.birks_discretization(ev, c, p)
        self.assertEqual((r["status"], r["parameter"], r["k_B_max"]), ("failed", "birks", 0.4))
        self.assertGreater(r["max_ratio"], design.BIRKS_BOUND)
        self.assertEqual(r["findings"][0]["code"], "p5.birks_discretization")
        m = methods(ev, c, p)
        self.assertEqual(m["status"], "ok")
        self.assertEqual(m["methods"]["birks"], "resimulation")
        rerun = next(x for x in m["log"] if x["method"] == "rerun")
        self.assertFalse(rerun["feasible"])
        self.assertEqual(rerun["birks_discretization"]["status"], "failed")

    def test_a_small_birks_prior_passes_and_keeps_the_rerun(self):
        """Positive control: the bound grows with k_B; at a prior up to 1e-5 it is far below 0.1 sigma_tot."""
        ev, c, p = setup(priors={"birks": (0.0, 1e-5)})
        r = design.birks_discretization(ev, c, p)
        self.assertEqual(r["status"], "passed")
        self.assertLessEqual(r["max_ratio"], design.BIRKS_BOUND)
        self.assertEqual(methods(ev, c, p)["methods"]["birks"], "rerun")

    def test_the_shift_moves_the_visible_energy_by_the_bound(self):
        """The evaluator's hook: +-bound moves the prediction in opposite directions, the plain one in between."""
        ev, c, p = setup()
        pt = {"birks": 0.4}
        mid = np.asarray(ev.evaluate(pt)["pred"])
        up = np.asarray(ev.birks_bound_shift(pt, 1)["pred"])
        down = np.asarray(ev.birks_bound_shift(pt, -1)["pred"])
        self.assertGreater(up[0], mid[0])
        self.assertLess(down[0], mid[0])
        np.testing.assert_allclose(np.asarray(ev.evaluate(pt)["pred"]), mid)    # the hook leaves no state behind
        with self.assertRaises(g4sim_calib_eval.DG.CheckError):
            ev.birks_bound_shift(pt, 2)

    def test_the_downward_shift_never_makes_a_visible_energy_negative(self):
        """On the Geant4 ZDC products some (event, volume) bounds exceed their visible energy; -bound stops at 0."""
        ev, c, p = setup()
        ev._bound_sign = -1
        try:
            rows = [(60, 0.5)]                       # (dE/dx class, energy): a high-dE/dx class, bound >> visible
            sim = g4sim_calib_eval.simulate
            self.assertLess(sim.reweighted(rows, 0.4) - sim.reweighting_bound(rows, 0.4), 0.0)   # the case exists
            self.assertEqual(ev._kb_visible(rows, 0.4), 0.0)
        finally:
            ev._bound_sign = 0

    def test_no_rerun_no_item(self):
        ev, c, p = setup(thetas=("light_yield",))
        self.assertIsNone(design.birks_discretization(ev, c, p))


if __name__ == "__main__":
    unittest.main()
