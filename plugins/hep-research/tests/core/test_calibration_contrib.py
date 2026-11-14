"""The contribution decomposition of Part B section 10.5 (core/calibration/contrib.py, phase 4) and the effects_off
hook of the section 7.1 evaluator on the toy chain (section 15.1 kernels): section 15.3.18 "when some actually
evaluated subset does not reach the ESS threshold, no decomposition is output" with its positive control, the
n > 10 permutation-sampling path, and the required variance-or-resolution declaration. Everything is `synthetic`.

The chain: x_base ~ N(0, 0.3) (not an effect), then x_i ~ N(x_{i-1}, s_i) for each effect i; the observable is the
width of the last x, so its variance is 0.09 + sum s_i^2 and the variance terms are s_i^2 (removal: s_i = 0)."""
from __future__ import annotations

import itertools
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_phase1 as H  # noqa: E402
from core.calibration import contrib as C  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402


def chain(n_effects: int, method: str = "resimulation", removal: float = 0.0, n: int = 4000, n_data: int = 200,
          widths=None, seed=None):
    """(contract, plan, nominal widths) of the smearing chain with n_effects declared effects."""
    widths = list(widths or [0.5 + 0.1 * i for i in range(n_effects)])
    nodes = [{"id": "base", "kernel": "normal", "args": {"out": "base", "scale": "s_base"}}]
    nominal, params = {"s_base": 0.3}, {"s_base": {"nodes": ["base"], "bounds": [0.1, 1.0]}}
    for i in range(n_effects):
        prev = f"x{i - 1}" if i else "base"
        nodes.append({"id": f"x{i}", "kernel": "normal", "parents": [prev],
                      "args": {"out": f"x{i}", "scale": f"s{i}", "parent": prev}})
        nominal[f"s{i}"] = widths[i]
        params[f"s{i}"] = {"nodes": [f"x{i}"], "bounds": [0.0, 3.0]}
    last = f"x{n_effects - 1}"
    c, p = H.chain_case(nodes, [{"name": "res", "node": last, "var": last, "functional": "std", "link": "log",
                                 "class": "core-width"}], nominal, params, {"run": n_data},
                        methods={k: method for k in params if k != "s_base"}, n=n,
                        **({} if seed is None else {"seed": seed}))
    c["effects"] = [{"name": f"e{i}", "removal": {f"s{i}": removal}} for i in range(n_effects)]
    return c, p, widths


def decompose(case, quantity="variance", **kw):
    c, p, _ = case
    return C.decompose(E.make(p, c), c, {}, "res", quantity, **kw)


class EffectsOffHook(unittest.TestCase):
    """Section 7.1: effects_off carries the declared values after removal; evaluating with it equals evaluating at
    those values; anything without its declared value is refused; no effects_off leaves the evaluation unchanged."""

    def setUp(self):
        c, p, _ = chain(2)
        self.ev = E.make(p, c)

    def test_equals_evaluation_at_the_removal_values(self):
        a = self.ev.evaluate({}, effects_off={"e0": {"s0": 0.0}}, names=["res"])
        b = self.ev.evaluate({"s0": 0.0}, names=["res"])
        np.testing.assert_array_equal(a["pred"], b["pred"])
        base = self.ev.evaluate({}, names=["res"])
        np.testing.assert_array_equal(base["pred"], self.ev.evaluate({}, effects_off={}, names=["res"])["pred"])
        self.assertGreater(base["pred"][0], a["pred"][0])

    def test_refused_without_declared_values(self):
        for bad in (["e0"], {"e0": {"s0": "zero"}}, {"e0": {"nope": 0.0}},
                    {"e0": {"s0": 0.0}, "e1": {"s0": 0.1}}):         # bare names, non-number, unknown, conflict
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.ev.evaluate({}, effects_off=bad)


class Decomposition(unittest.TestCase):
    """Section 15.3.18 and its positive control (exhaustive path, n <= 10)."""

    @classmethod
    def setUpClass(cls):
        cls.case = chain(3)
        cls.ok = decompose(cls.case)

    def test_positive_control_outputs_the_decomposition(self):
        r = self.ok
        self.assertEqual((r["status"], r["method"], r["object"], r["n_subsets_evaluated"]),
                         ("ok", "exhaustive", "variance", 8))
        self.assertTrue(all(s["ess_passed"] for s in r["subsets"]))
        for i, w in enumerate(self.case[2]):                     # variance terms close to s_i^2
            self.assertAlmostEqual(r["terms"][f"e{i}"], w * w, delta=0.08 * w * w + 0.02)
        self.assertEqual(r["forced_joint_fits"], [])

    def test_terms_sum_to_the_total_on_every_permutation(self):
        r = self.ok
        self.assertAlmostEqual(r["sum_of_terms"], r["total"], places=12)
        q = {frozenset(s["present"]): s["q"] for s in r["subsets"]}
        names = list(r["effects"])
        for total in C.permutation_sums(q, names, itertools.permutations(names)):
            self.assertAlmostEqual(total, r["total"], places=12)

    def test_bootstrap_covariance(self):
        r = self.ok
        cov = np.array(r["covariance"]["matrix"])
        self.assertEqual(r["covariance"]["order"], list(r["effects"]))
        np.testing.assert_allclose(cov, cov.T)
        self.assertGreaterEqual(np.linalg.eigvalsh(cov).min(), -1e-12)
        self.assertTrue(np.all(np.diag(cov) > 0))
        # the terms sum to the total on every replica too: the summed covariance is the variance of the total
        self.assertAlmostEqual(cov.sum(), r["total_sd"] ** 2, delta=1e-9 * max(1.0, cov.sum()))

    def test_bootstrap_covariance_is_calibrated(self):
        """Review F7: over 20 independent MC samples the spread of each term agrees with the mean bootstrap sd (ratio
        within 0.6-1.5: the sd of a 20-sample sd is about 16%), and the terms recover s_i^2 within 4 standard errors."""
        terms, sds = [], []
        for seed in range(1, 21):
            r = decompose(chain(3, seed=seed), bootstrap=200, bootstrap_seed=seed)
            terms.append([r["terms"][f"e{i}"] for i in range(3)])
            sds.append(np.sqrt(np.diag(np.array(r["covariance"]["matrix"]))))
        terms, sds = np.array(terms), np.array(sds)
        ratio = terms.std(axis=0, ddof=1) / sds.mean(axis=0)
        self.assertTrue(np.all((ratio > 0.6) & (ratio < 1.5)), ratio)
        se = terms.std(axis=0, ddof=1) / np.sqrt(len(terms))
        np.testing.assert_array_less(np.abs(terms.mean(axis=0) - [0.25, 0.36, 0.49]), 4 * se + 1e-12)

    def test_negative_some_subset_below_the_ess_threshold(self):
        """Reweighting the widths down (removal 0.4) with N_req = 10 N_data = 3000 of N = 4000: the subsets with
        effects removed fall below the threshold (all present passes with unit weights). No decomposition."""
        r = decompose(chain(3, method="analytic-reweighting", removal=0.4, n_data=300))
        self.assertEqual((r["status"], r["finding"], r["decomposition"]), ("failed", "contrib.ess", None))
        for key in ("terms", "total", "covariance", "sum_of_terms", "q_all_present"):
            self.assertNotIn(key, r)
        self.assertTrue(all("q" not in s and "value" not in s for s in r["subsets"]))
        self.assertTrue(r["failing_subsets"])
        self.assertTrue(any(s["ess_passed"] for s in r["subsets"]))
        self.assertTrue(all(s["n_eff"] < s["n_req"] for s in r["failing_subsets"]))

    def test_negative_exactly_one_subset_fails(self):
        """Only the subset with both effects removed is below the threshold: still no decomposition (the control is
        the same chain resimulated, test_positive_control)."""
        case = chain(2, method="analytic-reweighting", removal=0.4, n_data=320)
        r = decompose(case)
        self.assertEqual((r["status"], r["finding"]), ("failed", "contrib.ess"), r["subsets"])
        self.assertEqual([s["present"] for s in r["failing_subsets"]], [[]])
        self.assertEqual(sum(s["ess_passed"] for s in r["subsets"]), 3)
        ok = decompose(chain(2, method="resimulation", removal=0.4, n_data=320))
        self.assertEqual(ok["status"], "ok")

    def test_missing_support_fails(self):
        """Reweighting a width to 0 has no density: missing support, never a weight; no decomposition."""
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            r = decompose(chain(2, method="analytic-reweighting", removal=0.0))
        self.assertEqual((r["status"], r["finding"]), ("failed", "contrib.ess"))


class Sampling(unittest.TestCase):
    """n > 10: permutation sampling with its sampling error; the ESS rule holds on the subsets it evaluates."""

    def test_permutation_sampling(self):
        case = chain(11, n=2000, n_data=100)
        r = decompose(case, permutations=30)
        self.assertEqual((r["status"], r["method"], r["n_effects"]), ("ok", "permutation-sampling", 11))
        self.assertLess(r["n_subsets_evaluated"], 2 ** 11)
        self.assertAlmostEqual(r["sum_of_terms"], r["total"], places=10)
        se = np.array([r["sampling_error"][f"e{i}"] for i in range(11)])
        self.assertTrue(np.all(se > 0))
        self.assertEqual(np.array(r["sampling_covariance"]["matrix"]).shape, (11, 11))
        for i, w in enumerate(case[2]):
            self.assertAlmostEqual(r["terms"][f"e{i}"], w * w, delta=5 * se[i] + 0.1 * w * w + 0.05)
        again = decompose(case, permutations=30)
        self.assertEqual(again["terms"], r["terms"])                # fixed seeds: reproducible

    def test_sampling_negative(self):
        r = decompose(chain(11, n=2000, method="analytic-reweighting", removal=0.4, n_data=150), permutations=5)
        self.assertEqual((r["status"], r["finding"]), ("failed", "contrib.ess"))
        self.assertNotIn("terms", r)


class Declarations(unittest.TestCase):
    def test_object_is_required(self):
        case = chain(2)
        for quantity in (None, "", "width"):
            with self.subTest(quantity=quantity), self.assertRaises(C.ContribError) as cm:
                decompose(case, quantity=quantity)
            self.assertEqual(cm.exception.code, "contrib.object")

    def test_variance_and_resolution_objects(self):
        case = chain(2)
        v, s = decompose(case, "variance"), decompose(case, "resolution")
        self.assertEqual((v["object"], s["object"]), ("variance", "resolution"))
        self.assertAlmostEqual(v["q_all_present"], s["q_all_present"] ** 2, places=12)
        self.assertAlmostEqual(s["sum_of_terms"], s["total"], places=12)

    def test_effect_declarations(self):
        c, p, _ = chain(2)
        ev = E.make(p, c)
        bad = [[], [{"name": "e0", "removal": {}}], [{"name": "e0", "removal": {"nope": 0.0}}],
               [{"name": "e0", "removal": {"s0": 0.0}}, {"name": "e0", "removal": {"s1": 0.0}}],
               [{"name": "e0", "removal": {"s0": 0.0}}, {"name": "e1", "removal": {"s0": 0.2}}]]
        for effects in bad:
            with self.subTest(effects=effects), self.assertRaises(C.ContribError):
                C.decompose(ev, dict(c, effects=effects), {}, "res", "variance")
        with self.assertRaises(C.ContribError):
            C.decompose(ev, c, {}, "res", "variance", select=["e9"])
        with self.assertRaises(C.ContribError):
            C.decompose(ev, c, {}, "unknown", "variance")
        r = C.decompose(ev, c, {}, "res", "variance", select=["e1"])
        self.assertEqual(list(r["terms"]), ["e1"])
        self.assertAlmostEqual(r["terms"]["e1"], r["total"], places=12)

    def test_evaluator_that_cannot_remove_effects_is_incomplete(self):
        c, p, _ = chain(2)
        ev = E.make(p, c)

        class NoRemoval:
            parameters, observables = ev.parameters, ev.observables

            def evaluate(self, theta, phi=None, psi=None, model="nominal", effects_off=(), seeds=None, names=None):
                if effects_off:
                    raise NotImplementedError("no effects_off")
                return ev.evaluate(theta, names=names)

        class NoInfluence(NoRemoval):
            def evaluate(self, theta, phi=None, psi=None, model="nominal", effects_off=(), seeds=None, names=None):
                return {k: v for k, v in ev.evaluate(theta, effects_off=effects_off, names=names).items()
                        if k != "influence"}

        for stub, code in ((NoRemoval(), "contrib.effects_off"), (NoInfluence(), "contrib.bootstrap")):
            with self.subTest(code=code), self.assertRaises(C.ContribError) as cm:
                C.decompose(stub, c, {}, "res", "variance")
            self.assertEqual((cm.exception.code, cm.exception.status), (code, "incomplete"))


if __name__ == "__main__":
    unittest.main()
