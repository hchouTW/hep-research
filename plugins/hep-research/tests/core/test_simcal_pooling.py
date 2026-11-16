"""Partial pooling (phase 5, WP-Q; Part B section 3.7, section 15.3.18 line 3465; approval A25 (6)): the declaration,
the REML estimate of tau_pool against closed forms, the joint fit against the linear mixed-model solution, section
15.3.18 in A25's frequency reading with its negative control, the positive pair (different truths detected at the
planned power) and the S2 driver (labelled `synthetic`)."""
from __future__ import annotations

import copy
import dataclasses
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

import simcal_fixtures as CF  # noqa: E402

from contracts.schema import validate  # noqa: E402
from core.simcal import closure as CL  # noqa: E402
from core.simcal import contract as CC  # noqa: E402
from core.simcal import fit as F  # noqa: E402
from core.simcal import pooling as PL  # noqa: E402
from core.simcal import toys_linear as TL  # noqa: E402
from core.simcal import use as U  # noqa: E402

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
        base = len(validate(CF.contract(), "simcal_contract.json").errors)
        self.assertEqual(len(validate(c, "simcal_contract.json").errors), base)
        bad = copy.deepcopy(c)
        bad["pooling"]["segments"] = bad["pooling"]["segments"][:1]
        self.assertGreater(len(validate(bad, "simcal_contract.json").errors), base)
        bad = copy.deepcopy(c)
        bad["pooling"]["parameters"][name]["prior"] = 1
        self.assertGreater(len(validate(bad, "simcal_contract.json").errors), base)

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


# ------------------------------------------------------------------ A26 (1): grade, use and gates of pooled fits
def gated_joint(S_=4, truths=None, seed=(1, 2), d=2, val=True, collinear=False, n=8, sd=1.0, offset=None,
                bounds=None, prior=None):
    """A segmented linear toy with held-out units per segment (5 rows each)."""
    cfg = TL.linear_config(n=n, d=d, seed=3, sd=sd, bounds=bounds, prior=prior)
    if collinear is not False:                  # exactly (True) or nearly (a float: the added noise) collinear
        cfg.J[:, 1] = 2.0 * cfg.J[:, 0] + (0.0 if collinear is True else
                                           collinear * np.random.default_rng(4).normal(size=n))
    if val:
        rng = np.random.default_rng(0)
        cfg.val = {"J": rng.normal(size=(5, d)), "m0": np.full(5, 5.0), "V_data": np.eye(5) * 0.5,
                   "V_MC": np.zeros((5, 5))}
    segs = PL.segmented_linear(cfg, truths or [TRUTH[:d]] * S_, list(seed))
    if offset is not None:                      # a misfit not in the model: a constant added to one segment's rows
        segs[0].observed.y_gauss = segs[0].observed.y_gauss + offset
    return PL.Segmented(segs, [f"s{i}" for i in range(S_)], ["t0"]), segs


def all_passed(**kw):
    g = {k: "passed" for k in U.MANDATORY}
    g.update(kw)
    return g


class PooledGrade(unittest.TestCase):
    """A26 (1): a pooled result is graded by the Appendix C rules (use.aggregate, use.judge) like any result;
    `partial-pooling` is informational."""

    def test_graded_by_appendix_c(self):
        """All gates passed, holdout V passed, real data: validated-in-scope, flagged partial-pooling, every use;
        the grade is the one use.judge gives the same inputs without the flag. Negatives: G5 failed -> failed;
        G8 closure-not-tested -> calibrated-unvalidated; G6 not decided -> incomplete; V failed -> capped."""
        ok = PL.grade(all_passed(), "passed", "passed", "holdout", True)
        j = ok["judgment"]
        self.assertEqual((j["effective_grade"], "partial-pooling" in j["flags"]), ("validated-in-scope", True))
        self.assertIn("production", j["uses"])
        plain = U.judge(dict(ok["inputs"], own_flags=[]), [])
        self.assertEqual((plain["effective_grade"], plain["uses"]), (j["effective_grade"], j["uses"]))
        self.assertEqual(PL.grade(all_passed(G5="failed"), "passed", "passed", "holdout", True)
                         ["judgment"]["effective_grade"], "failed")
        self.assertEqual(PL.grade(all_passed(G8="closure-not-tested"), "passed", "passed", "holdout", True)
                         ["judgment"]["effective_grade"], "calibrated-unvalidated")
        g = all_passed()
        del g["G6"]
        inc = PL.grade(g, "passed", "passed", "holdout", True)
        self.assertEqual((inc["judgment"]["effective_grade"], inc["undecided"]), ("incomplete", ["mandatory-gate"]))
        self.assertEqual(PL.grade(all_passed(), "passed", "failed", "holdout", True)["judgment"]["effective_grade"],
                         "calibrated-unvalidated")
        self.assertEqual(PL.grade(all_passed(), "passed", "passed", "holdout", False)["judgment"]["effective_grade"],
                         "projection")

    def test_grade_report(self):
        """simcal_fit.py pool's grade section: without inputs it lists the states it decided and those still needed;
        with inputs the decided states replace the given ones (a failed G1 of the joint fit fails the result although
        the inputs say passed); malformed inputs are rejected."""
        r = PL.grade_report({"G1": "passed"})
        self.assertEqual(r["status"], "inputs-needed")
        self.assertNotIn("G1", r["needed"])
        self.assertIn("G8", r["needed"])
        given = {"gates": all_passed(), "p7": "passed", "v": "passed", "vmode": "holdout", "real_data": True}
        self.assertEqual(PL.grade_report({"G1": "passed"}, given)["judgment"]["effective_grade"], "validated-in-scope")
        self.assertEqual(PL.grade_report({"G1": "failed"}, given)["judgment"]["effective_grade"], "failed")
        for bad in ({"gates": {}}, dict(given, extra=1), dict(given, gates=[]), dict(given, vmode="sometimes")):
            with self.assertRaises(PL.PoolingError) as cm:
                PL.grade_report({"G1": "passed"}, bad)
            self.assertEqual(cm.exception.code, "pooling.grade")


class PooledHoldout(unittest.TestCase):
    """A26 (1): the holdout validates the pooled model jointly: one V test over the held-out units of all segments."""

    def fit(self, seed, truths=None):
        j, segs = gated_joint(truths=truths, seed=(seed, 3), sd=2.0)
        res = PL.fit_pooled(j, seed, multistart=False)
        self.assertTrue(res.converged, res.reason)
        yv = {n: p.simulate_val(p.truth, np.random.default_rng([seed, 5, i]), nominal=False)
              for i, (n, p) in enumerate(zip(j.names, segs))}
        return j, res, yv

    def test_one_test_over_all_segments(self):
        """k is the sum of the segments' units (one test, not one per segment); a segment without held-out units is
        rejected (negative); control: all segments given."""
        j, res, yv = self.fit(1)
        ev = PL.holdout_evidence(j, res.fit, yv, "kappa", 0.05)
        self.assertEqual((ev["evidence"]["k"], ev["units"]), (20, {f"s{i}": 5 for i in range(4)}))
        self.assertIn("evidence_sha256", ev["evidence"])
        with self.assertRaises(PL.PoolingError) as cm:
            PL.holdout_evidence(j, res.fit, {k: v for k, v in yv.items() if k != "s2"}, "kappa", 0.05)
        self.assertEqual(cm.exception.code, "pooling.validation")

    def test_joint_statistic_has_mean_k_and_size_alpha(self):
        """Equal truth, 300 replicas: mean T_v = k = 20 and rejection rate 0.05 (the joint Sigma_beta in C_r couples the
        segments through theta_bar); negative: without the propagation term the test over-rejects."""
        T, T0 = [], []
        for r in range(300):
            j, res, yv = self.fit(100 + r)
            T.append(PL.holdout_evidence(j, res.fit, yv, "kappa", 0.05)["evidence"]["T"])
            T0.append(PL.holdout_evidence(j, res.fit, yv, "kappa", 0.05, omit=("propagation",))["evidence"]["T"])
        crit = stats.chi2.ppf(0.95, 20)
        self.assertAlmostEqual(float(np.mean(T)), 20.0, delta=1.0)
        self.assertLess(abs(float(np.mean(np.asarray(T) > crit)) - 0.05), 0.04)
        self.assertGreater(float(np.mean(np.asarray(T0) > crit)), 0.12)

    def test_inconsistent_period_is_caught(self):
        """Negative: the held-out units of one period disagree with the pooled model (a shift of 3 sigma per unit in
        s0) -> the joint V test fails at alpha = 0.05 in >= 90% of 40 replicas; control: the consistent units fail in
        <= 15%."""
        fail_ok, fail_bad = [], []
        for r in range(40):
            j, res, yv = self.fit(500 + r)
            fail_ok.append(PL.holdout_evidence(j, res.fit, yv, "kappa", 0.05)["evidence"]["p"] <= 0.05)
            bad = dict(yv, s0=yv["s0"] + 3.0 * math.sqrt(0.5))
            fail_bad.append(PL.holdout_evidence(j, res.fit, bad, "kappa", 0.05)["evidence"]["p"] <= 0.05)
        self.assertGreaterEqual(np.mean(fail_bad), 0.9)
        self.assertLessEqual(np.mean(fail_ok), 0.15)


def pooled_p2_contract(n_obs, S_):
    return {"observables": [{"name": f"o{i}", "role": "calibration"} for i in range(n_obs)],
            "parameters": [{"name": "a", "role": "theta", "index": {"mechanism": "response", "channel_set": "all",
                                                                     "conditioning": "partial-pooling"}},
                           {"name": "b", "role": "theta"}],
            "pooling": {"segments": [{"name": f"P{i}"} for i in range(S_)]}}


class PooledP2(unittest.TestCase):
    def test_pseudo_rows_are_not_counted(self):
        """A26 (1) 'counting only real observation rows': one observable, four segments: n_c = 4, d_free = 2 (theta_bar,
        the common theta), ndf = 2 < 3 -> failed, although counting the 4 pseudo-rows would give ndf = 6 and pass
        (the negative a row miscount would not catch); control: five segments give ndf = 3 and pass."""
        r = PL.p2(pooled_p2_contract(1, 4))
        self.assertEqual((r["status"], r["n_c"], r["d_free"], r["ndf"]), ("failed", 4, 2, 2))
        self.assertGreaterEqual(r["ndf"] + r["pseudo_rows_excluded"], r["required"])
        r = PL.p2(pooled_p2_contract(1, 5))
        self.assertEqual((r["status"], r["ndf"]), ("passed", 3))


class PooledIdentifiability(unittest.TestCase):
    """A26 (1): P3 on the joint problem, G5 per pooled parameter on theta_bar (the fixed effects; z profiled)."""

    def test_p3_uses_the_joint_information(self):
        """Positive: a configuration one segment does not identify (sigma_post/sigma_prior > 0.4 alone) passes P3 on
        the joint problem of 8 segments; control: the single segment fails. Negative: collinear responses fail on the
        joint problem (lambda_min); judging the z_s,j too would fail every pooled P3 (their prior is N(0, 1))."""
        j, segs = gated_joint(S_=8, n=4, sd=3.0, val=False)
        from core.simcal import identify as I
        one = I.p3(segs[0], TL.initial_beta(segs[0]))
        self.assertEqual(one["status"], "failed")
        r = PL.p3(j)
        self.assertEqual((r["status"], r["pooled"]["judged"]), ("passed", ["t0", "t1"]))
        self.assertEqual(I.p3(j, j.initial_beta())["status"], "failed")
        jc, _ = gated_joint(collinear=True, val=False)
        bad = PL.p3(jc)
        self.assertEqual((bad["status"], bad["finding"]), ("failed", "p3.not_identifiable"))

    def test_g5_on_theta_bar(self):
        """G5 at the joint fit with tau_pool_hat > 0 judged on theta_bar and the common theta: passes; negative:
        nearly collinear responses fail (lambda_min); the measures are those of the fixed-effect block of the joint
        covariance."""
        j, _ = gated_joint(truths=[[0.5 + x, -0.3] for x in (-0.6, -0.2, 0.2, 0.6)], seed=(12, 0), val=False)
        res = PL.fit_pooled(j, 5)
        self.assertGreater(res.tau.tau_pool_hat[0], 0.0)
        r = PL.g5(j, res.fit, 3)
        self.assertEqual((r["status"], r["pooled"]["judged"], len(r["profile"])), ("passed", ["t0", "t1"], 2))
        C = 2.0 * linalg.inv(res.fit.F)[:2, :2]
        np.testing.assert_allclose(r["sigma_post"], np.sqrt(np.diag(C)), rtol=1e-8)
        jc, _ = gated_joint(collinear=0.05, val=False)
        resc = PL.fit_pooled(jc, 5, multistart=False)
        bad = PL.g5(jc, resc.fit, 3, profile=False)
        self.assertEqual((bad["status"], bad["finding"]), ("failed", "g5.not_identifiable"))
        self.assertLess(bad["lambda_min"], 0.05)


class PooledG2G6(unittest.TestCase):
    """A26 (1): G2 on the real parameters' bounds only (pseudo-rows and their z never counted); G6 on the joint
    problem with joint toys."""

    def test_g2_ignores_z_bounds(self):
        """Negative: a joint fit with a z_s,j recorded at its numerical bound: the unrestricted G2 statistic counts it
        as an active constraint, the pooled G2 does not (no active real bound: passed, no flag, z listed as
        excluded)."""
        j, _ = gated_joint(val=False)
        res = PL.fit_pooled(j, 5, multistart=False)
        zi = j.z_block()[0]
        f = dataclasses.replace(res.fit, active=[zi])
        self.assertEqual(F.g2_statistic(j, f)["active"], [zi])
        r = PL.g2(j, f, 200, 9)
        self.assertEqual((r["status"], r["active"], r["flags"], r["z_at_bound_excluded"]),
                         ("passed", [], [], ["t0@s0:z"]))

    def test_g2_physical_boundary_of_theta_bar(self):
        """Section 15.2 / 15.3.1 on a pooled fit, over the first 5 replicas with an active bound: theta_bar's truth on
        its physical lower bound -> G2 passes with `boundary-solution` in >= 4; the truth about 5 sigma beyond the
        bound -> G2 fails (significant) in >= 4."""
        def run(t0):
            out = []
            for r in range(40):
                j, _ = gated_joint(truths=[[t0, -0.3]] * 4, seed=(40, r), val=False,
                                   bounds=[(0.0, 10.0), (-10.0, 10.0)], prior=[(0.0, 3.0), (-3.0, 3.0)])
                res = PL.fit_pooled(j, 5, multistart=False)
                if res.fit.active:
                    out.append(PL.g2(j, res.fit, 200, (11, r)))
                if len(out) == 5:
                    return out
            self.fail("fewer than 5 replicas with an active bound")
        on = run(0.0)
        self.assertGreaterEqual(sum(g["status"] == "passed" and g["flags"] == ["boundary-solution"] for g in on), 4)
        beyond = run(-1.0)
        self.assertGreaterEqual(sum(g["status"] == "failed" and g["finding"] == "g2.boundary_significant"
                                    for g in beyond), 4)

    def test_g6_on_the_joint_problem(self):
        """G6 with joint locally linear toys: the correct pooled model passes (T_obs includes the pseudo-rows, as the
        toys do); negative: one segment's rows carry an offset the model lacks -> fails."""
        j, _ = gated_joint(val=False)
        res = PL.fit_pooled(j, 5, multistart=False)
        ok = PL.g6(j, res.fit, 500, 21)
        self.assertEqual((ok["status"], ok["rows"]), ("passed", {"real": 32, "pseudo": 4}))
        jb, _ = gated_joint(val=False, offset=np.r_[np.full(4, 2.0), np.full(4, -2.0)])
        resb = PL.fit_pooled(jb, 5, multistart=False)
        bad = PL.g6(jb, resb.fit, 500, 21)
        self.assertEqual((bad["status"], bad["finding"]), ("failed", "g6.p_value"))


def complete_pooling(joint, seed):
    """A wrong pooled fitter for the G8 negative: tau_pool fixed at 0 (the between-segment spread ignored)."""
    joint.set_tau(np.zeros(joint.P))
    f = F.iterate(joint, joint.initial_beta())
    return PL.PooledFit(None, f, 1, f.converged, "", {}, {}, {}, [])


class PooledG8(unittest.TestCase):
    """A26 (1): G8 with segment-level pseudo-data, drawn per segment from a common truth and from spread truths (theta_s
    = theta_bar + tau x_s, x ~ N(0, 1)), judged on the fixed effects; standard level, 8 segments (fast size)."""
    S8 = 8
    BOUNDS, PRIOR = [(-2.0, 10.0), (-10.0, 10.0)], [(-2.0, 3.0), (-3.0, 3.0)]

    @classmethod
    def setUpClass(cls):
        cls.cfg = TL.linear_config(n=8, d=2, seed=3, bounds=cls.BOUNDS, prior=cls.PRIOR)
        j0 = cls.joint([[0.5, -0.3]] * cls.S8, 1)
        r0 = PL.fit_pooled(j0, 1, multistart=False)
        cls.j0, cls.sd = j0, r0.fit.sigma_tot[:2]
        cls.tau_true = 2.0 * float(r0.tau.segment_sigma[0])
        cls.points = CL.injection_points(cls.PRIOR, cls.BOUNDS, cls.sd, np.array([0.5, -0.3]))
        cls.N = CL.n_c(2, "standard")["N_c"]

    @classmethod
    def joint(cls, truths, seed):
        return PL.Segmented(PL.segmented_linear(cls.cfg, truths, [seed, 11], mc_seed=seed),
                            [f"s{i}" for i in range(cls.S8)], ["t0"])

    def g8(self, spread: bool, fitter):
        pts = []
        for k, tr in enumerate(self.points):
            def make(s, tr=tr, k=k):
                truths = PL.segment_truths(self.j0, tr[:1], tr[1:], [self.tau_true] if spread else None,
                                           np.random.default_rng([s, 99]))
                return self.joint(truths, 1000 * k + s)
            pts.append(PL.closure_point(make, tr, self.N, range(k * 100000, (k + 1) * 100000), fitter))
        return CL.g8("standard", ["t0", "t1"], self.sd, *pts)

    def test_correct_pooled_fit_passes(self):
        """Positive: the REML pooled fit passes with a common truth and with spread truths."""
        fit = (lambda j, s: PL.fit_pooled(j, s, multistart=False))
        self.assertEqual(self.g8(False, fit)["status"], "passed")
        self.assertEqual(self.g8(True, fit)["status"], "passed")

    def test_ignoring_the_spread_is_caught_by_spread_truths(self):
        """Negative: a fitter with tau_pool = 0 under-covers theta_bar under spread truths -> G8 fails (68% coverage
        at the interior point); control: with a common truth the same fitter passes, so the spread truths are what
        catch it."""
        r = self.g8(True, complete_pooling)
        self.assertEqual(r["status"], "failed")
        self.assertIn(("cover68", "interior", "t0"), [(f["test"], f.get("point"), f["theta"]) for f in r["fails"]])
        self.assertEqual(self.g8(False, complete_pooling)["status"], "passed")

    def test_segment_truths(self):
        """Common truth: every theta_s = theta_bar; spread: link-space spread around theta_bar (log link)."""
        th = PL.segment_truths(self.j0, [0.4], [-0.3])
        self.assertTrue(all(np.allclose(t, [0.4, -0.3]) for t in th))
        th = PL.segment_truths(self.j0, [0.4], [-0.3], [0.5], np.random.default_rng(1))
        self.assertGreater(np.std([t[0] for t in th]), 0.1)
        self.assertTrue(all(t[1] == -0.3 for t in th))


class S2Driver(unittest.TestCase):
    """The S2 frequency-report driver: --list, --local, a task and the merge; a missing task makes the merge
    incomplete (negative), the complete array is `reported` (control)."""

    def test_driver(self):
        import simcal_phase5_pooling_s2 as D
        self.assertEqual(len(D.TASKS), 10)
        self.assertEqual(sum(t["reps"] for t in D.TASKS), 1000)
        with tempfile.TemporaryDirectory() as scratch:
            d = Path(scratch)
            out = subprocess.run([sys.executable, str(HERE / "simcal_phase5_pooling_s2.py"), "--local", "--out",
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
