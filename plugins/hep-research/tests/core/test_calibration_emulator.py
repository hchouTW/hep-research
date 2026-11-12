"""The surrogate model of phase 3 (Part B sections 6.4, 6.5, 7.1, 8.1, 8.2 note 4, 15.3.1, 15.3.16; approval A12 for
the G8 hook of section 19-5): the kriging surrogate (weights, V_MC, V_emu, the domain), ask/tell with its state file,
the training set (D80), P6 with its negative tests (each with a positive control), the surrogate-model tier of
calib_design.py's final methods, V_emu in the design-stage covariance, and the G8 surrogate pseudo-data and
spot-check bookkeeping. Everything runs on the toy detector of section 15.1 or on synthetic arrays (`synthetic`)."""
from __future__ import annotations

import copy
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import design, emulator as EM, linear  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")
SPE = ["spe_e_mean", "spe_e_width", "spe_efficiency"]


def toy_case(bounds=(1.0, 16.0), n_design=16, held_back=16, seed=9, mode="interpolate", spot_checks=None,
             only_threshold=False):
    """The toy detector with the threshold (a resimulation-level parameter: zero suppression at generation) evaluated
    by a surrogate over a wide prior, where the single-photoelectron efficiency is strongly nonlinear in it."""
    d = copy.deepcopy(H.toy_design())
    c, p = d["contract"], d["plan"]
    for q in c["parameters"]:
        if q["name"] == "threshold":
            q["sampling_bounds"] = list(bounds)
    c["observables"] = [o for o in c["observables"] if o["name"] in SPE]
    if only_threshold:
        c["parameters"] = [q for q in c["parameters"] if q["name"] == "threshold"]
    p["methods"]["threshold"] = "surrogate-model"
    p["design"]["surrogate"] = {"n_design": n_design, "held_back": held_back, "seed": seed, "mode": mode,
                                "spot_checks": spot_checks or []}
    return c, p


def smooth_surrogate(n=12, mode="interpolate", noise=0.0, seed=1):
    """A 2-d surrogate of an analytic response (known interpolation error) for the unit tests of the smoother."""
    rng = np.random.default_rng(seed)
    pts = [{"a": float(x), "b": float(y)} for x, y in rng.uniform(0, 1, (n, 2))]
    f = np.array([[np.sin(3 * q["a"]) + q["b"] ** 2, q["a"] - q["b"]] for q in pts])
    f = f + noise * rng.standard_normal(f.shape)
    v = np.array([np.diag([1e-4, 4e-4]) for _ in pts])
    return EM.Surrogate(["a", "b"], {"a": [0, 1], "b": [0, 1]}, pts, f, v, ["s", "d"], mode), pts, f


class SurrogateModel(unittest.TestCase):
    def test_interpolates_with_weights_summing_to_one(self):
        sur, pts, f = smooth_surrogate()
        for j in (0, 5):
            w = sur.weights(pts[j])
            self.assertAlmostEqual(float(w.sum()), 1.0, places=10)
            np.testing.assert_allclose(sur.predict(pts[j])["pred"], f[j], atol=1e-5)
            self.assertLess(float(np.max(np.diag(sur.v_emu(pts[j])))), 1e-6)
        mid = {"a": 0.5, "b": 0.5}
        self.assertGreater(float(np.diag(sur.v_emu(mid)).max()), 0.0)
        self.assertTrue(sur.interpolates_exactly)
        q = sur.predict(mid)
        np.testing.assert_allclose(q["pred"], q["weights"] @ f)
        self.assertEqual(q["V_MC"].shape, (2, 2))
        self.assertTrue(np.all(np.linalg.eigvalsh(q["V_MC"]) >= -1e-15))

    def test_regression_mode_does_not_pass_through_the_points(self):
        sur, pts, f = smooth_surrogate(n=24, mode="regression", noise=0.05)
        self.assertFalse(sur.interpolates_exactly)
        self.assertGreaterEqual(sur.nugget, EM.NUGGET_BOUNDS[0])
        self.assertGreater(float(np.abs(sur.predict(pts[0])["pred"] - f[0]).max()), 1e-4)

    def test_linear_response_is_reproduced_exactly(self):
        """The trend is in the basis: a linear response is reproduced at any point (the weights reproduce it)."""
        rng = np.random.default_rng(3)
        pts = [{"a": float(x)} for x in rng.uniform(2, 5, 8)]
        f = np.array([[3.0 * q["a"] - 1.0] for q in pts])
        sur = EM.Surrogate(["a"], {"a": [2, 5]}, pts, f)
        self.assertAlmostEqual(float(sur.predict({"a": 4.321})["pred"][0]), 3 * 4.321 - 1, places=6)

    def test_weight_derivatives_match_finite_differences(self):
        """The inputs WP-D's theta-noise item needs: d w / d theta_i, d^2 w / d theta_i^2 in parameter units."""
        rng = np.random.default_rng(4)
        pts = [{"a": float(x), "b": float(y)} for x, y in rng.uniform(0, 1, (10, 2))]
        f = np.array([[np.sin(3 * q["a"]) * q["b"]] for q in pts])
        sur = EM.Surrogate(["a", "b"], {"a": [0, 2], "b": [0, 1]}, [{"a": 2 * q["a"], "b": q["b"]} for q in pts], f)
        t, h = {"a": 0.9, "b": 0.4}, 1e-4
        d1, d2 = sur.weight_derivatives(t, "a")
        wp, w0, wm = (sur.weights({**t, "a": t["a"] + s}) for s in (h, 0.0, -h))
        np.testing.assert_allclose(d1, (wp - wm) / (2 * h), atol=1e-5)
        np.testing.assert_allclose(d2, (wp - 2 * w0 + wm) / h ** 2, atol=1e-2 * np.abs(d2).max() + 1e-4)
        self.assertAlmostEqual(float(d1.sum()), 0.0, places=8)

    def test_query_outside_the_domain_is_rejected(self):
        """Section 6.4: queries outside the domain are always rejected; the edge is inside (positive control)."""
        sur, _, _ = smooth_surrogate()
        sur.predict({"a": 1.0, "b": 0.0})
        for bad in ({"a": 1.01, "b": 0.5}, {"a": 0.5}):
            with self.assertRaises(EM.OutsideDomain):
                sur.predict(bad)

    def test_record_round_trip(self):
        sur, _, _ = smooth_surrogate()
        back = EM.Surrogate.from_record(sur.record())
        t = {"a": 0.3, "b": 0.7}
        np.testing.assert_allclose(back.predict(t)["pred"], sur.predict(t)["pred"], rtol=1e-12)
        np.testing.assert_allclose(back.v_emu(t), sur.v_emu(t), rtol=1e-10, atol=1e-18)


class _Slow:
    """A batch evaluator that hands over one finished result per tell() (asynchronous ask/tell)."""

    def __init__(self, inner):
        self.inner, self.seeds, self.queue = inner, inner.seeds, []

    def ask(self, reqs):
        self.queue += reqs
        return [q["run_id"] for q in reqs]

    def tell(self, run_ids=None):
        if not self.queue:
            return {}
        q = self.queue.pop(0)
        self.inner.ask([q])
        return self.inner.tell([q["run_id"]])


class AskTell(unittest.TestCase):
    def setUp(self):
        self.c, self.p = toy_case(n_design=4, held_back=0)
        self.ev = E.make(self.p, self.c)

    def state(self):
        return EM.new_state([{"threshold": 3.0}, {"threshold": 6.0}], "training", {"threshold": 5.0},
                            EM.common_seeds(self.ev), SPE)

    def test_run_ids_and_toy_ask_tell(self):
        st = self.state()
        self.assertEqual([e["run_id"] for e in st["entries"]], ["training-0000", "training-0001"])
        reqs = EM.ask(st)
        self.assertEqual(self.ev.ask(reqs), ["training-0000", "training-0001"])
        got = self.ev.tell()
        self.assertEqual(sorted(got), ["training-0000", "training-0001"])
        self.assertEqual(self.ev.tell(), {})                                   # each handed over once
        for rid, r in got.items():
            EM.tell(st, rid, r)
        self.assertTrue(EM.complete(st))
        full = self.ev.evaluate({"threshold": 6.0}, names=SPE)
        np.testing.assert_allclose(st["entries"][1]["result"]["pred"], full["pred"])

    def test_refusals(self):
        """Negative tests of the state file, each against the accepted case."""
        st = self.state()
        res = self.ev.evaluate({"threshold": 3.0}, names=SPE)
        with self.assertRaises(EM.EmulatorError) as cm:
            EM.tell(st, "training-0000", res)                                  # told before it was asked
        self.assertEqual(cm.exception.code, "emulator.not_submitted")
        EM.ask(st, n=1)
        EM.tell(st, "training-0000", res)                                      # positive control
        EM.tell(st, "training-0000", res)                                      # the same result again: accepted
        other = dict(res, pred=res["pred"] + 1.0)
        with self.assertRaises(EM.EmulatorError) as cm:
            EM.tell(st, "training-0000", other)
        self.assertEqual(cm.exception.code, "emulator.second_result")
        with self.assertRaises(EM.EmulatorError) as cm:
            EM.tell(st, "nope", res)
        self.assertEqual(cm.exception.code, "emulator.unknown_run_id")
        EM.ask(st)
        with self.assertRaises(EM.EmulatorError) as cm:
            EM.tell(st, "training-0001", dict(res, names=["x", "y", "z"]))
        self.assertEqual(cm.exception.code, "emulator.names")
        with self.assertRaises(EM.EmulatorError):
            EM.ask({"schema": "other", "entries": []})

    def test_asynchronous_drive(self):
        st = self.state()
        r = EM.drive(_Slow(self.ev), st, max_rounds=1)
        self.assertEqual(r["status"], "incomplete")
        self.assertTrue(r["outstanding"])
        r = EM.drive(_Slow(self.ev), self.state())
        self.assertEqual(r["status"], "ok")


class P6Arrays(unittest.TestCase):
    """P6 on synthetic arrays (section 8.2 note 4): the |Delta m| part, the pull chi2, Bonferroni z."""

    def arrays(self, H, k=3, scale=1.0, seed=0, v_emu=0.0):
        rng = np.random.default_rng(seed)
        cov = np.diag(np.full(k, 1.0))
        dm = scale * rng.standard_normal((H, k))
        return dm, np.repeat(cov[None], H, 0), np.repeat((v_emu * np.eye(k))[None], H, 0)

    def test_bonferroni_z(self):
        self.assertAlmostEqual(EM.bonferroni_z(40), 3.66226, places=4)        # z_{1 - 0.01 / 80}
        r = EM.p6(*self.arrays(8), v_data=np.ones(3))
        self.assertEqual((r["parts"]["delta_m"]["M"], r["alpha"]), (24, 0.01))
        self.assertIn("provisional-thresholds", r["flags"])

    def test_delta_m_fails_on_a_large_difference(self):
        dm, cd, ve = self.arrays(8)
        self.assertEqual(EM.p6(dm, cd, ve, np.ones(3))["status"], "passed")   # positive control
        dm[2, 1] = 0.3 + EM.bonferroni_z(24) + 0.5
        r = EM.p6(dm, cd, ve, np.ones(3))
        self.assertEqual((r["status"], r["parts"]["delta_m"]["n_exceeding"]), ("failed", 1))
        self.assertIn("p6.delta_m", {f["code"] for f in r["findings"]})
        self.assertEqual(r["remedy"], "plan")

    def test_twenty_held_out_points_decide_only_delta_m(self):
        """Section 15.3.16: 20 held-out points -> P6 decides only the |Delta m| part (not incomplete)."""
        dm, cd, ve = self.arrays(20, scale=2.0)
        r = EM.p6(dm, cd, ve, np.full(3, 100.0))
        self.assertEqual(r["status"], "passed")
        self.assertEqual(r["parts"]["pull_chi2"]["status"], "not-executed")
        dm, cd, ve = self.arrays(30, scale=2.0)
        self.assertEqual(EM.p6(dm, cd, ve, np.full(3, 100.0))["parts"]["pull_chi2"]["status"], "failed")

    def test_pull_chi2_catches_an_understated_v_emu(self):
        """>= 30 held-out points: differences twice sigma_Delta with V_emu = 0 fail the pull chi2 although each
        |Delta m| is within its bound; with the matching V_emu (= 3 sigma_Delta^2) they pass (positive control)."""
        dm, cd, ve = self.arrays(40, scale=2.0, seed=2)
        r = EM.p6(dm, cd, ve, np.full(3, 100.0))
        self.assertEqual((r["parts"]["delta_m"]["status"], r["parts"]["pull_chi2"]["status"]), ("passed", "failed"))
        self.assertIn("p6.pull_chi2", {f["code"] for f in r["findings"]})
        ok = EM.p6(dm, cd, np.repeat((3.0 * np.eye(3))[None], 40, 0), np.full(3, 100.0))
        self.assertEqual(ok["status"], "passed")

    def test_no_held_out_points_is_rejected(self):
        with self.assertRaises(EM.EmulatorError):
            EM.p6(np.zeros((0, 3)), np.zeros((0, 3, 3)), np.zeros((0, 3, 3)), np.ones(3))
        with self.assertRaises(EM.EmulatorError):
            EM.p6(np.full((2, 1), np.nan), np.ones((2, 1, 1)), np.zeros((2, 1, 1)), np.ones(1))

    def test_from_input_with_bootstrap_replicas(self):
        rng = np.random.default_rng(5)
        doc = {"v_data": [1.0, 1.0], "points": [{"delta_m": [0.1, -0.2],
                                                  "delta_replicas": rng.standard_normal((200, 2)).tolist()}
                                                 for _ in range(4)]}
        self.assertEqual(EM.p6_from_input(doc)["status"], "passed")
        doc["points"][0].pop("delta_replicas")
        with self.assertRaises(EM.EmulatorError):
            EM.p6_from_input(doc)


class P6Toy(unittest.TestCase):
    """P6 on the toy detector: the held-back points evaluated with full simulation (resimulation with the scan's
    common random numbers) against the surrogate trained on the training points."""

    def test_too_few_design_points(self):
        """Section 15.3.1 P6: with 4 training design points the surrogate misses the nonlinear threshold response and
        P6 fails; with 16 (positive control, same held-back count and seed family) it passes."""
        c, p = toy_case(n_design=4, held_back=12)
        r = EM.p6_from_evaluator(E.make(p, c), c, p)
        self.assertEqual(r["status"], "failed")
        self.assertIn("p6.delta_m", {f["code"] for f in r["findings"]})
        self.assertGreater(r["parts"]["delta_m"]["max_ratio"], 1.3)
        c, p = toy_case(n_design=16, held_back=16)
        r = EM.p6_from_evaluator(E.make(p, c), c, p)
        self.assertEqual(r["status"], "passed", r["findings"])
        self.assertLess(r["parts"]["delta_m"]["max_ratio"], 0.7)
        self.assertEqual(r["parts"]["pull_chi2"]["status"], "not-executed")    # 16 < 30 held-out points

    def test_spot_checks_are_held_back_and_mandatory(self):
        """Section 15.3.16 (stand-in for k_B on the toy): the two extreme points of the parameter are among P6's
        held-out points when the plan lists them; a required spot check missing from the held-out set is rejected."""
        bounds = {"threshold": [1.0, 16.0]}
        ext = EM.extreme_points(bounds, "threshold")
        c, p = toy_case(n_design=8, held_back=4, spot_checks=ext)
        cfg = EM.settings(c, p)
        held = EM.design(cfg)["held_back"]
        self.assertEqual(len(held), 6)
        EM.check_spot_checks(held, ext, ["threshold"])                         # positive control
        r = EM.p6_from_evaluator(E.make(p, c), c, p, required_spot_checks=ext)
        self.assertIn(r["status"], ("passed", "failed"))
        c, p = toy_case(n_design=8, held_back=4)
        with self.assertRaises(EM.EmulatorError) as cm:
            EM.p6_from_evaluator(E.make(p, c), c, p, required_spot_checks=ext)
        self.assertEqual(cm.exception.code, "p6.spot_checks_missing")


class Combination(unittest.TestCase):
    """The surrogate in the evaluator (section 6.5, outside to inside) and V_emu in the covariance."""

    @classmethod
    def setUpClass(cls):
        cls.c, cls.p = toy_case(n_design=12, held_back=0)
        cls.ev = E.make(cls.p, cls.c)
        cls.tr = EM.training_set(cls.ev, cls.c, cls.p)
        cls.sur = cls.tr["surrogate"]

    def test_training_set_uses_common_random_numbers(self):
        st = self.tr["state"]
        self.assertEqual({e["seeds"]["nominal"] for e in st["entries"]}, {self.p["seeds"]["nominal"]})
        self.assertEqual(len(st["entries"]), 12)
        self.assertEqual(self.tr["settings"]["parameters"], ["threshold"])

    def test_evaluator_with_the_surrogate(self):
        ev = E.make(self.p, self.c)
        ev.attach_surrogate(self.sur)
        pt = self.sur.points[3]
        r = ev.evaluate(pt, names=SPE)
        np.testing.assert_allclose(r["pred"], self.ev.evaluate(pt, names=SPE)["pred"], atol=1e-6)
        self.assertEqual(r["methods"]["threshold"], "surrogate-model")
        mid = ev.evaluate({"threshold": 8.3}, names=SPE)
        self.assertEqual(mid["V_emu"].shape, (3, 3))
        self.assertGreater(float(np.diag(mid["V_emu"]).max()), 0.0)
        with self.assertRaises(EM.OutsideDomain):
            ev.evaluate({"threshold": 17.0}, names=SPE)
        # inner method: the gain is reweighted at each design point (section 6.5); at a design point the surrogate
        # equals the full evaluation at the same other parameters
        r = ev.evaluate({**pt, "gain": 10.2}, names=SPE)
        np.testing.assert_allclose(r["pred"], self.ev.evaluate({**pt, "gain": 10.2}, names=SPE)["pred"], atol=1e-6)

    def test_v_emu_enters_w_not_sigma_mc(self):
        """V_cc = V_data + V_MC + V_emu (linear.py): a surrogate's V_emu raises sigma_tot^design and leaves the
        matrix condition's Sigma_MC alone (positive control: V_emu = 0 reproduces the operator)."""
        rng = np.random.default_rng(1)
        J = rng.standard_normal((6, 2))
        Vd, Vm = np.eye(6) * 0.04, np.eye(6) * 0.004
        a = linear.operator(J, Vd, Vm)
        b = linear.operator(J, Vd, Vm, V_emu=np.eye(6) * 0.02)
        z = linear.operator(J, Vd, Vm, V_emu=np.zeros((6, 6)))
        np.testing.assert_allclose(z["sigma_tot"], a["sigma_tot"])
        self.assertTrue(np.all(b["sigma_tot"] > a["sigma_tot"]))
        np.testing.assert_allclose(np.diag(b["Sigma_MC"]) / np.diag(b["Sigma_data"]),
                                   np.diag(a["Sigma_MC"]) / np.diag(a["Sigma_data"]), rtol=0.3)


class FinalMethod(unittest.TestCase):
    """Section 3.6 step 2: with no resimulation budget a black-box parameter moves to the surrogate-model tier, whose
    feasibility is P6 (calib_design.py)."""

    def case(self, n_design):
        c, p = toy_case(n_design=n_design, held_back=12, only_threshold=True)
        for nd in c["stage_graph"]["nodes"]:
            if nd["id"] == "electronics":
                nd["kernel"] = "black-box"
        p["methods"]["threshold"] = "resimulation"
        p["event_budget"] = {"resimulation": False}
        return c, p

    def test_surrogate_tier_decided_by_p6(self):
        c, p = self.case(16)
        m = design.final_methods(E.make(p, c), c, p)
        self.assertEqual((m["status"], m["methods"]), ("ok", {"threshold": "surrogate-model"}))
        self.assertEqual([x["P6"] for x in m["log"] if x["method"] == "surrogate-model"], ["passed"])
        c, p = self.case(4)                                                    # P6 fails: no feasible method
        m = design.final_methods(E.make(p, c), c, p)
        self.assertEqual(m["status"], "failed")
        self.assertIn("p5.no_feasible_method", {f["code"] for f in m["findings"]})


class G8Hook(unittest.TestCase):
    """Approval A12 (section 19-5): surrogate pseudo-data for the bulk of G8, a full-simulation spot check at the
    injection points with seeds independent of the training set."""

    @classmethod
    def setUpClass(cls):
        cls.c, cls.p = toy_case(n_design=12, held_back=0)
        cls.ev = E.make(cls.p, cls.c)
        cls.tr = EM.training_set(cls.ev, cls.c, cls.p)

    def test_pseudo_data_moments(self):
        V = np.array([[2.0, 0.5], [0.5, 1.0]])
        y = EM.surrogate_pseudo_data([1.0, -1.0], V, 20000, seed=(7, 1))
        np.testing.assert_allclose(y.mean(0), [1.0, -1.0], atol=0.04)
        np.testing.assert_allclose(np.cov(y, rowvar=False), V, atol=0.06)
        np.testing.assert_array_equal(y, EM.surrogate_pseudo_data([1.0, -1.0], V, 20000, seed=(7, 1)))

    def test_spot_check_seeds_independent_of_training(self):
        inj = [{"threshold": 6.0}, {"threshold": 1.5}]
        st = self.tr["state"]
        with self.assertRaises(EM.EmulatorError) as cm:                         # shares the scan's seed
            EM.spot_check_plan(inj, st, [{"nominal": self.p["seeds"]["nominal"]}, {"nominal": 99}])
        self.assertEqual(cm.exception.code, "g8.spot_check_not_independent")
        with self.assertRaises(EM.EmulatorError):                              # two spot checks share a seed
            EM.spot_check_plan(inj, st, [{"nominal": 98}, {"nominal": 98}])
        with self.assertRaises(EM.EmulatorError):                              # overlapping event intervals
            EM.spot_check_plan(inj, st, [98, 99], intervals=[[0, 100]], training_intervals=[[50, 150]])
        sp = EM.spot_check_plan(inj, st, [98, 99], base_theta=self.tr["settings"]["theta_ref"], names=SPE,
                                intervals=[[200, 300]], training_intervals=[[0, 150]])
        self.assertEqual([e["seeds"] for e in sp["entries"]], [{"nominal": 98}, {"nominal": 99}])
        self.assertEqual(EM.spot_check_record(sp, self.tr["surrogate"], self.c)["status"], "incomplete")
        EM.drive(self.ev, sp)
        rec = EM.spot_check_record(sp, self.tr["surrogate"], self.c)
        self.assertEqual(rec["status"], "not-decided")
        self.assertEqual(rec["p6_form"]["gate"], "P6")
        self.assertEqual(len(rec["points"]), 2)


if __name__ == "__main__":
    unittest.main()
