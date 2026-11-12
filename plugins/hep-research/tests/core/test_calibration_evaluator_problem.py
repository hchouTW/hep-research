"""The synthetic ZDC fixture of Part B section 15.2 as a calibration problem (phase 3, WP-F): core/calibration/
evaluator_problem.py over the g4sim evaluator, on products of the fixture's SYNTHETIC TRANSPORT STAND-IN (tests/core/
calibration_zdc_fixture.py; no Geant4). The section 15.2 "g4sim (synthetic ZDC)" items runnable without Geant4, the G8
pseudo-data path of D6 (A12) on the fixture's events, and the Geant4 production the real fixture needs (not run).
Items that need Geant4 are skipped and say so."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

import calibration_zdc_fixture as Z  # noqa: E402
import g4sim_calib_eval as E  # noqa: E402
import g4sim_simulate as simulate  # noqa: E402

from core.calibration import evaluator, identify, kernel_check, linear  # noqa: E402
from core.calibration import evaluator_problem as EP  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402

N = 300


class ResponseParametersP0(unittest.TestCase):
    """Section 15.2 synthetic ZDC item 1: response parameters by re-digitization against a full g4sim_run plus
    response (here the stand-in's products made at the new light yield): P0 passes."""

    def setup(self, wrong_birks=None):
        lo, hi = Z.PRIORS["light_yield"]
        bs = {"nominal": Z.batch(41, 0, N, use="fit", set="s"), "reference": Z.batch(42, 0, N, use="reference")}
        for v in (lo, hi):                     # the full runs at the light-yield spot checks (section 5.4)
            kb = wrong_birks if (wrong_birks is not None and v == hi) else Z.BIRKS0
            bs[f"ly{v}"] = Z.batch(41, 0, N, birks=kb, light_yield=v, point={"light_yield": v}, use="fit", set="s")
        c = Z.contract(thetas=("light_yield",), observables=("pe_mean", "pe_std"))
        p = Z.plan(bs, observables=("pe_mean", "pe_std"))
        p["evaluator"]["reference"] = "reference"
        ev = evaluator.make(p, c)
        req = kernel_check.required_spot_checks(c, p)
        return c, p, ev, req

    def test_p0_passes(self):
        c, p, ev, req = self.setup()
        self.assertEqual([(r["parameter"], r["gate"]) for r in req], [("light_yield", "P0")])
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"light_yield": 200.0}, {"light_yield": 195.0}], 5,
                            spot_checks=req[0]["points"], required=req)
        self.assertEqual(r["status"], "passed", r["points"])
        froms = {row["point"]["light_yield"]: row["rerun_from"] for row in r["points"]}
        self.assertEqual((froms[180.0], froms[195.0]), (["transport"], ["response"]))  # full run / reference batch

    def test_control_a_mislabelled_full_run_is_caught(self):
        """Control: the run told at the upper light yield was made with another k_B (a wrong detector card): P0
        fails there."""
        c, p, ev, req = self.setup(wrong_birks=0.3)
        r = kernel_check.p0(ev, c, p, linear.design(ev, c, p), [{"light_yield": 200.0}], 5,
                            spot_checks=req[0]["points"], required=req)
        self.assertEqual(r["status"], "failed")
        self.assertEqual([row["point"]["light_yield"] for row in r["points"] if row["failing"]], [220.0])

    @unittest.skip("requires Geant4: re-digitization against g4sim_run plus response with Geant4 products "
                   "(calibration_zdc_fixture.production_runs 'reference', 'LY-low', 'LY-high'; Slurm)")
    def test_with_geant4(self):
        pass


class BirksRerunAgainstResimulation(unittest.TestCase):
    """Section 15.2 synthetic ZDC item 2: edep_visible from edep_by_dedx_class at a new k_B against the edep_visible a
    run at that k_B scores, within g4sim_simulate.reweighting_bound at the new k_B (D75: a deterministic rerun)."""

    def test_within_the_bound_per_event(self):
        p = Z.products(51, 0, 200, birks=Z.BIRKS0)
        dedx: dict = {}
        for e, scorer, v, b, x, *_ in p["cells"]:
            if scorer == Z.DEDX:
                dedx.setdefault((e, v), []).append((b, x))
        for kb in (Z.BIRKS_PRIOR[0], 0.21, Z.BIRKS_PRIOR[1]):
            resim = Z.products(51, 0, 200, birks=kb)["edep_visible"]          # the same events at k_B
            worst = 0.0
            for key, rows in dedx.items():
                diff = abs(simulate.reweighted(rows, kb) - resim[key])
                bound = simulate.reweighting_bound(rows, kb)
                self.assertLessEqual(diff, bound)
                worst = max(worst, diff / bound)
            self.assertGreater(worst, 0.0)
        kb = Z.BIRKS_PRIOR[0]                                                     # control: a run at another k_B
        wrong = Z.products(51, 0, 200, birks=kb + 0.2)["edep_visible"]
        self.assertTrue(all(abs(simulate.reweighted(rows, kb) - wrong[key]) > simulate.reweighting_bound(rows, kb)
                            for key, rows in dedx.items()))

    def test_through_the_evaluator(self):
        bs = {"nominal": Z.batch(52, 0, N, use="fit")}
        ev = evaluator.make(Z.plan(bs), Z.contract(observables=("vis_mean",)))
        r = ev.evaluate({"birks": 0.3})
        truth = np.mean([sum(v for (e, vol), v in Z.products(52, 0, N, birks=0.3)["edep_visible"].items() if e == i)
                         for i in range(N)])
        k = r["names"].index("vis_mean")
        self.assertLessEqual(abs(r["pred"][k] - truth), r["birks_bound_MeV"]["vis_mean"])

    @unittest.skip("requires Geant4: the edep_visible scorer of a g4sim_run at the new k_B (production 'kB-low', "
                   "'kB-high', with an edep_visible scorer added; Slurm)")
    def test_with_geant4(self):
        pass


class CalorimeterProblem(unittest.TestCase):
    """The fixture as a fit problem: the predictor, the errors, P3, a fit on G8 pseudo-data drawn from a truth MC by
    the D6 rule of A12."""

    @classmethod
    def setUpClass(cls):
        cls.bs = {"nominal": Z.batch(61, 0, N, use="fit"), "truth": Z.batch(62, 0, 4 * N, use="G8-truth")}
        cls.c = Z.contract(observables=("pe_mean", "pe_std"), exposure=1000)
        cls.ev = evaluator.make(Z.plan(cls.bs, observables=("pe_mean", "pe_std")), cls.c)
        cls.p = EP.EvaluatorProblem(cls.ev, cls.c, seeds={"batch": "nominal"})
        # the fit uses the mean only: with common random numbers the re-digitized width jumps by ~1% under a 1e-4
        # change of k_B (one more photon in a bin redraws its whole multinomial), a staircase the minimizer cannot
        # resolve at the G1 EDM threshold (reported to the evaluator's owner; sigma_noise is 0 here)
        cls.c1 = Z.contract(observables=("pe_mean",), exposure=1000)
        cls.ev1 = evaluator.make(Z.plan(cls.bs, observables=("pe_mean",)), cls.c1)
        cls.p1 = EP.EvaluatorProblem(cls.ev1, cls.c1, seeds={"batch": "nominal"})

    def test_predictor_and_errors(self):
        tp = np.array([0.15])
        r = self.ev.evaluate({"birks": 0.15}, names=self.p.names)
        np.testing.assert_allclose(self.p.h(tp), np.log(r["pred"]))
        Vd, Vm = self.p.V_parts(tp)
        np.testing.assert_allclose(np.diag(Vd), np.diag(r["s2"]) / 1000 / r["pred"] ** 2)
        self.assertTrue(np.all(np.linalg.eigvalsh(Vm) >= -1e-15))
        self.assertGreater(Vm[0, 0], 0)

    def test_p3_and_a_fit_on_truth_mc_pseudo_data(self):
        truth = 0.15
        events = Z.truth_events(self.ev1, {"birks": truth}, "truth")
        obs = self.p1.pseudo_data(events, {"kind": "fixed", "events": 1000}, np.random.default_rng(3))
        q = self.p1.with_data(obs)
        centre = np.array([0.5 * sum(Z.BIRKS_PRIOR)])
        lk = L.Likelihood(q.layout, obs, q.reference(centre, None))
        b0 = lk.initial_beta({"birks": float(centre[0])})
        self.assertEqual(identify.p3(q, b0)["status"], "passed")
        f = F.iterate(q, b0)
        self.assertTrue(f.converged, f.reason)
        self.assertLess(abs(f.beta[0] - truth), 4 * float(f.sigma_tot[0]))

    def test_pseudo_data_follow_d6(self):
        events = Z.truth_events(self.ev, {"birks": 0.15}, "truth")
        events["weights"] = -np.ones(len(events["values"]["pe_mean"]))
        from core.calibration import closure
        with self.assertRaises(closure.ClosureError):                 # negative weights: no pseudo-data (D6)
            self.p.pseudo_data(events, {"kind": "fixed", "events": 100}, np.random.default_rng(1))
        events["weights"] = np.where(np.arange(len(events["weights"])) % 2 == 0, 3.0, 1.0)
        a = self.p.pseudo_data(events, {"kind": "fixed", "events": 100}, np.random.default_rng(1))
        self.assertEqual(a.y_gauss.shape, (2,))


class Production(unittest.TestCase):
    """The Geant4 production of the real fixture (not run): runs, events, cost, and the k_B spot-check cards from the
    evaluator's ask re-pointed at the nominal run's events."""

    def test_runs_and_cards(self):
        rows = Z.production_runs()
        self.assertEqual([r["name"] for r in rows], ["nominal", "kB-low", "kB-high", "reference", "LY-low", "LY-high"])
        self.assertTrue(all(0 < r["core_hours"] < 1 for r in rows))
        nominal = Z.batch(71, 0, 20)
        ev = evaluator.make(Z.plan({"nominal": nominal}), Z.contract())
        with tempfile.TemporaryDirectory() as folder:
            reqs = Z.production_cards(ev, str(Path(folder) / "state.json"), nominal)
        got = [r["detector"]["materials"][Z.MATERIAL]["ionisation"]["birks_mm_per_MeV"] for r in reqs]
        self.assertEqual(got, [repr(Z.BIRKS_PRIOR[0]), repr(Z.BIRKS_PRIOR[1])])
        self.assertEqual({(r["run"]["run"]["logical_run_seed"], r["run"]["run"]["first_event"]) for r in reqs},
                         {(71, 0)})
        self.assertEqual(len({r["run_sha256"] for r in reqs}), 1)                 # one card: only k_B moves

    def test_the_stand_in_is_labelled(self):
        self.assertIn("stand-in", Z.batch(1, 0, 1)["label"])
        self.assertIsInstance(evaluator.make(Z.plan({"nominal": Z.batch(1, 0, 3)}), Z.contract()), E.G4simEvaluator)


if __name__ == "__main__":
    unittest.main()
