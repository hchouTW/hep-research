"""Partial pooling (phase 5, WP-Q; Part B section 3.7, section 15.3.18 line 3465; approval A25 (6)): the declaration,
the REML estimate of tau_pool against closed forms, the joint fit against the linear mixed-model solution, section
15.3.18 in A25's frequency reading with its negative control, the positive pair (different truths detected at the
planned power) and the S2 driver (labelled `synthetic`)."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import linalg, stats

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import calibration_fixtures as CF  # noqa: E402

from contracts.schema import validate  # noqa: E402
from core.calibration import contract as CC  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import pooling as PL  # noqa: E402
from core.calibration import toys_linear as TL  # noqa: E402

S = 4
TRUTH = (0.5, -0.3)
REPS = 1000


def pooled_contract(**pool):
    c = CF.contract()
    th = [p for p in c["parameters"] if p["role"] == "theta"]
    th[0]["index"] = {"mechanism": th[0].get("mechanism", "response"), "channel_set": "all",
                      "conditioning": "partial-pooling"}
    if pool.get("pooling", True) is not None:
        c["pooling"] = pool.get("pooling") or {"segments": [{"name": "P1", "conditions": {"period": [0, 1]}},
                                                            {"name": "P2", "conditions": {"period": [1, 2]}}],
                                               "parameters": {th[0]["name"]: {"link": "log", "tau_bound": 1.0}}}
    return c, th[0]["name"]


def codes(findings):
    return [f["code"] for f in findings]


class Declaration(unittest.TestCase):
    def test_missing_segments_rejected(self):
        """A pooled theta without `pooling.segments` is rejected; the declared contract is not (control)."""
        c, _ = pooled_contract(pooling=None)
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.no_segments"])
        self.assertIn("pooling.no_segments", codes(CC.check(c)["findings"]))
        with self.assertRaises(PL.PoolingError) as cm:
            PL.declaration(c)
        self.assertEqual(cm.exception.code, "pooling.no_segments")
        ok, name = pooled_contract()
        self.assertEqual(PL.contract_findings(ok), [])
        self.assertFalse([f for f in CC.check(ok)["findings"] if f["code"].startswith("pooling.")])
        spec = PL.declaration(ok)
        self.assertEqual((spec.segments, spec.pooled, spec.links[name], spec.tau_bound[name]),
                         (["P1", "P2"], [name], "log", 1.0))

    def test_other_declaration_rules(self):
        c, name = pooled_contract(pooling={"segments": [{"name": "P1"}]})
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.segments"])
        c, _ = pooled_contract(pooling={"segments": [{"name": "P1"}, {"name": "P1"}]})
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.segments"])
        c, _ = pooled_contract(pooling={"segments": [{"name": "P1"}, {"name": "P2"}],
                                        "parameters": {"nope": {}, name: {"link": "fisher-z"}}})
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.parameter_unknown", "pooling.link"])
        c, _ = pooled_contract(pooling={"segments": [{"name": "P1"}, {"name": "P2"}],
                                        "parameters": {name: {"tau_bound": -1.0}}})
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.tau_bound"])
        c, _ = pooled_contract(pooling={"segments": "P1"})
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.segments"])
        c = CF.contract()
        c["pooling"] = {"segments": [{"name": "P1"}, {"name": "P2"}]}
        self.assertEqual(codes(PL.contract_findings(c)), ["pooling.no_pooled_parameter"])
        c, _ = pooled_contract()
        phi = next(p for p in c["parameters"] if p["role"] != "theta")
        phi["index"] = {"mechanism": "response", "channel_set": "all", "conditioning": "partial-pooling"}
        self.assertIn("pooling.role", codes(PL.contract_findings(c)))

    def test_schema_field(self):
        """The optional `pooling` field: accepted when well formed; one segment or an unknown key is a schema error."""
        c, name = pooled_contract()
        base = len(validate(CF.contract(), "calibration_contract.json").errors)
        self.assertEqual(len(validate(c, "calibration_contract.json").errors), base)
        bad = copy.deepcopy(c)
        bad["pooling"]["segments"] = bad["pooling"]["segments"][:1]
        self.assertGreater(len(validate(bad, "calibration_contract.json").errors), base)
        bad = copy.deepcopy(c)
        bad["pooling"]["parameters"][name]["prior"] = 1
        self.assertGreater(len(validate(bad, "calibration_contract.json").errors), base)

    def test_default_off(self):
        """A contract without pooling is not touched: no pooling code, the hook is not entered."""
        c = CF.contract()
        self.assertFalse(PL.uses_pooling(c))
        self.assertFalse([f for f in CC.check(c)["findings"] if f["code"].startswith("pooling.")])


def balanced(seed, d=2, sd=1.0):
    cfg = TL.linear_config(n=8, d=d, seed=3, sd=sd)
    return cfg


def lin_of(segs, pooled=("t0",)):
    j = PL.Segmented(segs, [f"s{i}" for i in range(len(segs))], list(pooled))
    return j, j.linearize(j.initial_beta()[:j.d])


class Reml(unittest.TestCase):
    def test_balanced_closed_form(self):
        """One pooled parameter, identical J and V in every segment: tau_pool_hat^2 = max(0, s^2 - sigma^2) with the
        per-segment GLS estimates (sigma^2 = (J^T V^-1 J)^-1), both an exact zero and an interior value."""
        cfg = TL.linear_config(n=6, d=1, seed=5)
        seen = set()
        for r in range(12):
            segs = PL.segmented_linear(cfg, [[0.2]] * 5, [77, r])
            _, lin = lin_of(segs)
            est = PL.reml(lin, intervals=False)
            Vi = linalg.inv(segs[0].reference(np.zeros(1), None).V_G)
            J = cfg.J[:, 0]
            s2 = 1.0 / float(J @ Vi @ J)
            th = [s2 * float(J @ Vi @ (p.observed.y_gauss - cfg.m0 - p.e0)) for p in segs]
            want = math.sqrt(max(0.0, float(np.var(th, ddof=1)) - s2))
            self.assertAlmostEqual(float(est.tau_pool_hat[0]), want, delta=1e-6 * max(want, 1.0))
            seen.add(want == 0.0)
        self.assertEqual(seen, {True, False})

    def test_segment_structure_rejected(self):
        cfg = balanced(0)
        segs = PL.segmented_linear(cfg, [TRUTH] * 2, [1])
        PL.Segmented(segs, ["a", "b"], ["t0"])                                    # control
        pc = copy.deepcopy(cfg)
        pc.poisson = {"a": [5.0, 5.0], "b": [0.1, 0.1], "tau": [50.0, 50.0]}
        bad = PL.segmented_linear(pc, [TRUTH] * 2, [1])
        with self.assertRaises(PL.PoolingError) as cm:
            PL.Segmented(bad, ["a", "b"], ["t0"])
        self.assertEqual(cm.exception.code, "pooling.blocks")
        with self.assertRaises(PL.PoolingError) as cm:
            PL.Segmented(segs, ["a", "b"], ["t9"])
        self.assertEqual(cm.exception.code, "pooling.parameter_unknown")
        with self.assertRaises(PL.PoolingError) as cm:
            PL.Segmented(segs[:1], ["a"], ["t0"])
        self.assertEqual(cm.exception.code, "pooling.segments")


def mixed_model(segs, tau):
    """The linear mixed model with known tau (Henderson): beta = (theta_bar, t1, u_1..u_S), the penalized GLS
    solution and its covariance; theta_s = theta_bar + u_s."""
    Sn = len(segs)
    cfg = segs[0].cfg
    Vi = linalg.inv(segs[0].reference(np.zeros(2), None).V_G)
    k = 2 + Sn
    A, b = np.zeros((k, k)), np.zeros(k)
    for s, p in enumerate(segs):
        M = np.zeros((cfg.J.shape[0], k))
        M[:, 0], M[:, 1], M[:, 2 + s] = cfg.J[:, 0], cfg.J[:, 1], cfg.J[:, 0]
        A += M.T @ Vi @ M
        b += M.T @ Vi @ (p.observed.y_gauss - cfg.m0 - p.e0)
    if tau > 0:
        A[2:, 2:] += np.eye(Sn) / tau ** 2
    else:
        A[2:, 2:] += np.eye(Sn) * 1e12
    C = linalg.inv(A)
    x = C @ b
    T = np.zeros((Sn, k))
    T[:, 0], T[np.arange(Sn), 2 + np.arange(Sn)] = 1.0, 1.0
    return x, C, T @ x, np.sqrt(np.diag(T @ C @ T.T))


class JointFit(unittest.TestCase):
    def test_joint_fit_is_the_mixed_model_solution(self):
        """The joint fit at tau_pool_hat reproduces the penalized GLS (BLUP) values of theta_s and their sigma_tot
        from the joint curvature; theta_bar and the common theta too."""
        segs = PL.segmented_linear(balanced(0), [[0.5 + d, -0.3] for d in (-0.6, -0.2, 0.2, 0.6)], [12])
        j = PL.Segmented(segs, [f"s{i}" for i in range(S)], ["t0"])
        res = PL.fit_pooled(j, 5)
        self.assertTrue(res.converged, res.reason)
        tau = float(res.tau.tau_pool_hat[0])
        self.assertGreater(tau, 0.0)
        x, C, th, sd = mixed_model(segs, tau)
        got = [res.segments[f"s{i}"]["t0"] for i in range(S)]
        np.testing.assert_allclose([g["value_link"] for g in got], th, atol=1e-5)
        np.testing.assert_allclose([g["sigma_tot_link"] for g in got], sd, rtol=1e-4)
        self.assertAlmostEqual(res.theta_bar["t0"]["value_link"], x[0], delta=1e-5)
        self.assertAlmostEqual(res.common["t1"]["sigma_tot"], math.sqrt(C[1, 1]), delta=1e-4 * math.sqrt(C[1, 1]))

    def test_shrinkage_toward_the_common_value(self):
        """Positive control of the card: every pooled theta_s lies between its separate-fit value and theta_bar
        (one parameter per segment, so the separate fits are the no-pooling model)."""
        segs = PL.segmented_linear(TL.linear_config(n=8, d=1, seed=3), [[0.5 + d] for d in (-0.6, -0.2, 0.2, 0.6)],
                                   [12])
        j = PL.Segmented(segs, [f"s{i}" for i in range(S)], ["t0"])
        res = PL.fit_pooled(j, 5)
        self.assertGreater(res.tau.tau_pool_hat[0], 0.0)
        mean_link = res.theta_bar["t0"]["value_link"]
        for i, p in enumerate(segs):
            sep = F.find_extremum(p, 3, TL.initial_beta(p)).beta[0]
            pooled = res.segments[f"s{i}"]["t0"]["value_link"]
            self.assertLessEqual(abs(pooled - mean_link), abs(sep - mean_link) + 1e-9)
            self.assertGreaterEqual((pooled - mean_link) * (sep - mean_link), 0.0)

    def test_zero_tau_is_the_common_value_model(self):
        """tau_pool = 0 (equal truth, a replica where REML returns 0): every theta_s equals theta_bar, which is the
        GLS fit of one common parameter."""
        for r in range(20):
            segs = PL.segmented_linear(balanced(0), [TRUTH] * S, [31, r])
            j = PL.Segmented(segs, [f"s{i}" for i in range(S)], ["t0"])
            res = PL.fit_pooled(j, 5)
            if res.tau.tau_pool_hat[0] == 0.0:
                break
        self.assertEqual(res.tau.tau_pool_hat[0], 0.0)
        x, C, th, sd = mixed_model(segs, 0.0)
        for i in range(S):
            g = res.segments[f"s{i}"]["t0"]
            self.assertAlmostEqual(g["value_link"], res.theta_bar["t0"]["value_link"], places=12)
            self.assertAlmostEqual(g["value_link"], x[0], delta=1e-5)
            self.assertAlmostEqual(g["sigma_tot_link"], math.sqrt(C[0, 0]), delta=1e-4)


def replicas(truths, reps, seed):
    """tau_pool_hat, the covers-0 flag, the lower end and the naive estimate (the sample sd of the per-segment GLS
    estimates, measurement error ignored) for `reps` replicas."""
    out = []
    for r in range(reps):
        segs = PL.segmented_linear(balanced(0), truths, [seed, r])
        _, lin = lin_of(segs)
        est = PL.reml(lin)
        Vi = linalg.inv(lin.V0)
        X = lin.X
        th = []
        for s in range(len(segs)):
            rows = slice(s * 8, (s + 1) * 8)
            Xs = X[rows]
            Vs = Vi[rows, rows]
            th.append(float(linalg.solve(Xs.T @ Vs @ Xs, Xs.T @ Vs @ lin.y_work[rows])[0]))
        out.append((float(est.tau_pool_hat[0]), bool(est.covers0[0]), float(est.lower[0]),
                    float(np.std(th, ddof=1))))
    return out


class TauReturnsToZero(unittest.TestCase):
    """Section 15.3.18 "when the truth is the same in all segments, tau-hat returns to 0" in A25's reading."""

    @classmethod
    def setUpClass(cls):
        cls.equal = replicas([TRUTH] * S, REPS, 20261405)

    def test_tau_returns_to_zero(self):
        """Equal truth: tau_pool_hat = 0 in >= 50% and 0 inside the 95% set in >= 95% of 1000 replicas; the zero
        fraction also agrees with the balanced-design value P(chi2_(S-1) <= S-1) within 4 binomial sigma."""
        dec = PL.frequency_decision([t for t, *_ in self.equal], [c for _, c, *_ in self.equal])
        self.assertEqual(dec["status"], "passed", dec)
        p0 = stats.chi2.cdf(S - 1, S - 1)
        self.assertLess(abs(dec["zero_fraction"][0] - p0), 4 * math.sqrt(p0 * (1 - p0) / REPS), dec)

    def test_naive_estimator_is_caught(self):
        """Negative: an estimator that ignores the segment errors (sample sd) never returns 0 and fails the test;
        the REML estimate on the same replicas passes (control above)."""
        dec = PL.frequency_decision([n for *_, n in self.equal], [c for _, c, *_ in self.equal])
        self.assertEqual(dec["status"], "failed")
        self.assertEqual(dec["zero_fraction"], [0.0])

    def test_decision_thresholds(self):
        self.assertEqual(PL.frequency_decision([0.0, 1.0], [True] * 2)["status"], "passed")
        self.assertEqual(PL.frequency_decision([0.0, 1.0, 1.0], [True] * 3)["status"], "failed")
        self.assertEqual(PL.frequency_decision([0.0] * 20, [True] * 18 + [False] * 2)["status"], "failed")
        self.assertEqual(PL.frequency_decision([0.0] * 20, [True] * 19 + [False])["status"], "passed")

    def test_different_truths_are_detected_at_the_planned_power(self):
        """Positive pair: fixed truths spread so that the planned power (balanced design) is 0.95: tau_pool_hat > 0
        with 0 outside the 95% set in at least the planned power minus 3 binomial sigma; the equal-truth replicas
        exclude 0 in at most 5% plus 3 sigma (control)."""
        _, lin = lin_of(PL.segmented_linear(balanced(0), [TRUTH] * S, [1]))
        sigma = float(lin.segment_sigma()[0])
        c = np.array([-1.5, -0.5, 0.5, 1.5])
        lam = 1.0
        while PL.planned_power(S, lam) < 0.95:
            lam *= 1.05
        delta = sigma * math.sqrt(lam / float(c @ c))
        reps = 300
        pos = replicas([[TRUTH[0] + delta * x, TRUTH[1]] for x in c], reps, 20261406)
        power = PL.planned_power(S, lam)
        hit = np.mean([t > 0 and not cov and lo > 0 for t, cov, lo, _ in pos])
        self.assertGreaterEqual(hit, power - 3 * math.sqrt(power * (1 - power) / reps), (hit, power))
        false = np.mean([not cov for _, cov, *_ in self.equal])
        self.assertLessEqual(false, 0.05 + 3 * math.sqrt(0.05 * 0.95 / REPS))


class S2Driver(unittest.TestCase):
    """The S2 frequency-report driver: --list, --local, a task and the merge; a missing task makes the merge
    incomplete (negative), the complete array is `reported` (control)."""

    def test_driver(self):
        import calibration_phase5_pooling_s2 as D
        self.assertEqual(len(D.TASKS), 10)
        self.assertEqual(sum(t["reps"] for t in D.TASKS), 1000)
        with tempfile.TemporaryDirectory() as scratch:
            d = Path(scratch)
            out = subprocess.run([sys.executable, str(HERE / "calibration_phase5_pooling_s2.py"), "--local", "--out",
                                  str(d / "smoke.json")], capture_output=True, text=True, timeout=300)
            self.assertEqual(out.returncode, 0, out.stderr)
            rep = json.loads((d / "smoke.json").read_text())
            self.assertEqual((rep["label"], rep["report"]["repetitions"]), ("smoke", 3))
            self.assertIn("zero_fraction", rep["report"])
            tasks = [{"r0": 900000, "reps": 2}, {"r0": 900002, "reps": 2}]
            saved = list(D.TASKS)
            try:
                D.TASKS[:] = tasks
                D.run_task(0, d / "arr")
                inc = D.merge(d / "arr", d / "m1.json")
                self.assertEqual((inc["status"], inc["missing_tasks"]), ("incomplete", [1]))
                D.run_task(1, d / "arr")
                full = D.merge(d / "arr", d / "m2.json")
                self.assertEqual((full["report"]["repetitions"], full["missing_tasks"]), (4, []))
                if not full["dirty"]:
                    self.assertEqual(full["status"], "reported")
            finally:
                D.TASKS[:] = saved


if __name__ == "__main__":
    unittest.main()
