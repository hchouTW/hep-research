"""The inference form of V_model (Part B section 5.4 row "Inferred"; phase 5, gap V6 read by A25 (7)): the card's
tests (a)-(d), each negative with its positive control, the opt-in path of `linear.vmodel_columns`, the
`simcal_likelihood.py vmodel-infer` subcommand, and the S3 recovery driver (tests/core/simcal_phase5_vmodel_s3.py:
task table, local smoke, merge rule). Synthetic; no Slurm."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import simcal_fixtures as F  # noqa: E402
import simcal_phase5_vmodel_s3 as X  # noqa: E402
from core.simcal import contract as cc  # noqa: E402
from core.simcal import linear  # noqa: E402
from core.simcal import vmodel_infer as VI  # noqa: E402

# slow tier (docs/maintenance.md): about 50 s and 30 s here, several times that on CI runners; neither is a gate-listed test
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"

SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "simcal_likelihood.py"
CFG = {"sigma": 0.01, "components": [{"n": 40, "f": 0.05, "length": 0.06, "f_scale": 0.1,
                                      "length_bounds": [0.01, 1.0]}]}


def case(r=0, cfg=CFG):
    return X.draw("unit", r, cfg)


def codes(c):
    return {f["code"] for f in cc.check(c, F.releases())["findings"]}


class Refusals(unittest.TestCase):
    def setUp(self):
        self.c, self.names, self.r, self.V, self.J = case()

    def infer(self, c=None, **kw):
        return VI.infer(c or self.c, self.names, self.r, self.V, flat=self.J, **kw)

    def assert_code(self, code, fn):
        with self.assertRaises((VI.VmodelInferError, linear.DesignError)) as cm:
            fn()
        self.assertEqual(cm.exception.code, code)

    def test_a_inferred_without_holdout(self):
        """(a) The contract rule (phase 0) still rejects the inferred form without holdout, and the engine refuses it
        at use; control: holdout passes both."""
        c = F.contract()
        c["model_discrepancy"]["form"] = "inferred"
        self.assertNotIn("model_discrepancy.inferred_mode", codes(c))
        c["validation"]["mode"] = "cross-validation"
        self.assertIn("model_discrepancy.inferred_mode", codes(c))
        self.assertEqual(self.infer()["validation"], "holdout")
        bad = copy.deepcopy(self.c)
        bad["validation"]["mode"] = "cross-validation"
        self.assert_code("vmodel_infer.not_holdout", lambda: self.infer(bad))
        v = self.infer()
        linear.vmodel_columns(self.c, self.names, v)                      # control
        self.assert_code("vmodel_infer.not_holdout", lambda: linear.vmodel_columns(bad, self.names, v))

    def test_b_conditional_likelihood_refused(self):
        """(b) The engine refuses fitting f by the conditional likelihood of nu (line 1017); control: marginal."""
        self.assert_code("vmodel_infer.conditional", lambda: self.infer(likelihood="conditional"))
        self.assertTrue(self.infer(likelihood="marginal")["converged"])

    def test_b_conditional_runs_off_marginal_finite(self):
        """(b) Counterexample: with nu profiled, -ln L_cond(f) decreases without bound in f (f nu is not
        identifiable) and its optimum is the upper bound; the marginal likelihood has an interior optimum."""
        z = np.linspace(0, 1, 40)
        R0 = VI.kernel_block(z, 1.0, 0.06)
        w, E = np.linalg.eigh(R0)
        keep = w > w.max() * 1e-10
        U0 = E[:, keep] * np.sqrt(w[keep])
        Vi = np.linalg.inv(self.V)
        r = self.r - self.J @ np.linalg.lstsq(self.J, self.r, rcond=None)[0]

        def cond(logf):
            f = math.exp(logf)
            A = f * U0
            nu = np.linalg.solve(A.T @ Vi @ A + np.eye(A.shape[1]), A.T @ Vi @ r)
            e = r - A @ nu
            return 0.5 * (e @ Vi @ e + nu @ nu)

        def marg(logf):
            S = self.V + math.exp(2 * logf) * R0
            return 0.5 * (np.linalg.slogdet(S)[1] + r @ np.linalg.solve(S, r))

        grid = np.linspace(math.log(1e-3), math.log(1e4), 40)
        cv = np.array([cond(g) for g in grid])
        self.assertTrue(np.all(np.diff(cv) < 0))                          # strictly decreasing: runs off
        hi = math.log(1e4)
        oc = optimize.minimize_scalar(cond, bounds=(math.log(1e-3), hi), method="bounded")
        om = optimize.minimize_scalar(marg, bounds=(math.log(1e-3), hi), method="bounded")
        self.assertGreater(oc.x, hi - 0.01)
        self.assertLess(om.x, hi - 3.0)                                   # control: interior, finite f
        self.assertLess(abs(math.exp(om.x) / 0.05 - 1), 1.0)

    def test_inputs_refused_with_controls(self):
        fixed = copy.deepcopy(self.c)
        fixed["model_discrepancy"]["form"] = "fixed"
        self.assert_code("vmodel_infer.not_inferred", lambda: self.infer(fixed))
        noprior = copy.deepcopy(self.c)
        del noprior["model_discrepancy"]["components"][0]["infer"]["f_scale"]
        self.assert_code("vmodel_infer.prior", lambda: self.infer(noprior))
        none = copy.deepcopy(self.c)
        del none["model_discrepancy"]["components"][0]["infer"]
        self.assert_code("vmodel_infer.no_component", lambda: self.infer(none))
        mat = copy.deepcopy(self.c)
        mat["model_discrepancy"]["components"][0]["kind"] = "matrix"
        self.assert_code("vmodel_infer.kind", lambda: self.infer(mat))
        pois = copy.deepcopy(self.c)
        pois["observables"][0]["block"] = "poisson"
        self.assert_code("vmodel_infer.incomplete", lambda: self.infer(pois))
        ndc = copy.deepcopy(self.c)
        ndc["validation"]["N_dc"] = [{"n": {self.names[0]: 1.0}}]
        self.assert_code("vmodel_infer.incomplete", lambda: self.infer(ndc))
        self.assertTrue(self.infer()["converged"])                        # control

    def test_fixed_components_enter_but_stay_fixed(self):
        c = copy.deepcopy(self.c)
        c["model_discrepancy"]["components"].append({"kind": "matrix", "observables": self.names[:2],
                                                     "R": [[1e-4, 0.0], [0.0, 1e-4]]})
        v = self.infer(c)
        self.assertEqual(v["components"][1], c["model_discrepancy"]["components"][1])
        self.assertEqual(len(v["estimates"]), 1)


class SeparateVersion(unittest.TestCase):
    """(c) The inferred V_model is a separate version: its own hash, distinct from the fixed-form declaration, the
    contract never overwritten, holdout carried; used only when passed and linked."""

    def setUp(self):
        self.c, self.names, self.r, self.V, self.J = case(1)
        self.before = copy.deepcopy(self.c)
        self.v = VI.infer(self.c, self.names, self.r, self.V, flat=self.J)

    def test_distinct_hash_and_contract_unchanged(self):
        self.assertEqual(self.c, self.before)
        self.assertEqual(self.v["fixed_sha256"], VI.fixed_sha256(self.before))
        self.assertNotEqual(self.v["version_sha256"], self.v["fixed_sha256"])
        self.assertEqual(self.v["validation"], "holdout")
        d = self.before["model_discrepancy"]["components"][0]
        self.assertNotEqual(self.v["components"][0]["f"], d["f"])          # fitted in the version only

    def test_vmodel_columns_opt_in(self):
        with self.assertRaises(linear.DesignError) as cm:
            linear.vmodel_columns(self.c, self.names)
        self.assertEqual(cm.exception.code, "linear.incomplete")
        U = linear.vmodel_columns(self.c, self.names, self.v)              # control
        e = self.v["estimates"][0]
        z = np.linspace(0, 1, len(self.names))
        np.testing.assert_allclose(U @ U.T, VI.kernel_block(z, e["f"], e["length"]), atol=1e-12)
        fixed = copy.deepcopy(self.c)
        fixed["model_discrepancy"]["form"] = "fixed"
        Uf = linear.vmodel_columns(fixed, self.names)                    # the fixed form: declared f, ell
        d = self.c["model_discrepancy"]["components"][0]
        np.testing.assert_allclose(Uf @ Uf.T, VI.kernel_block(z, d["f"], d["length"]), atol=1e-12)
        with self.assertRaises(linear.DesignError) as cm:
            linear.vmodel_columns(fixed, self.names, self.v)
        self.assertEqual(cm.exception.code, "vmodel_infer.version_mismatch")

    def test_tampered_or_foreign_version_refused(self):
        bad = json.loads(json.dumps(self.v))
        bad["components"][0]["f"] = 1.0
        with self.assertRaises(linear.DesignError) as cm:
            linear.vmodel_columns(self.c, self.names, bad)
        self.assertEqual(cm.exception.code, "vmodel_infer.version")
        other = copy.deepcopy(self.c)
        other["model_discrepancy"]["components"][0]["length"] = 0.3
        with self.assertRaises(linear.DesignError) as cm:
            linear.vmodel_columns(other, self.names, self.v)
        self.assertEqual(cm.exception.code, "vmodel_infer.version_mismatch")
        linear.vmodel_columns(self.c, self.names, json.loads(json.dumps(self.v)))   # control: JSON round trip

    def test_kernel_matches_linear(self):
        z = np.array([0.0, 0.3, 1.0])
        comp = {"kind": "squared-exponential", "observables": ["a", "b", "c"], "f": 0.2, "length": 0.4,
                "control": {"a": 0.0, "b": 0.3, "c": 1.0}}
        np.testing.assert_allclose(linear.vmodel_matrix([comp], ["a", "b", "c"]), VI.kernel_block(z, 0.2, 0.4))


class Recovery(unittest.TestCase):
    def test_d_marginal_estimates_cover_the_truth(self):
        """(d) On synthetic draws with known f, ell, the central 95 % marginal posterior interval in log x covers
        log x in >= 80% of 24 draws for each; negative control: against a misstated truth (x 3) the same check
        fails."""
        hits = {"f": 0, "length": 0}
        wrong = {"f": 0, "length": 0}
        n = 24
        for r in range(n):
            c, names, res, V, J = case(100 + r)
            e = VI.infer(c, names, res, V, flat=J)["estimates"][0]
            self.assertFalse(e["at_bound"])
            for par in ("f", "length"):
                q, truth = e["log_quantiles"][par], CFG["components"][0][par]
                self.assertAlmostEqual(math.exp(q[2]), e[par])                # the estimate is the median
                hits[par] += q[0] <= math.log(truth) <= q[4]
                wrong[par] += q[0] <= math.log(3 * truth) <= q[4]
        for par in hits:
            self.assertGreaterEqual(hits[par], 0.8 * n, par)
            self.assertLess(wrong[par], 0.8 * n, par)


GAMMA_SHAPE = 0.3        # x0 = log G, G ~ Gamma(0.3): strongly skewed in log


def _skewed(x):
    """-ln density of x0 = log G, G ~ Gamma(k = GAMMA_SHAPE) (skewed, mode log k, Laplace sd k^-1/2), and
    x1 | x0 ~ N(x0, 0.3^2)."""
    return -GAMMA_SHAPE * x[0] + math.exp(x[0]) + 0.5 * ((x[1] - x[0]) / 0.3) ** 2


def _skewed_cdf(t):
    return float(special.gammainc(GAMMA_SHAPE, math.exp(t)))


def _skewed_quantiles():
    return [math.log(float(stats.gamma.ppf(p, GAMMA_SHAPE))) for p in VI.QUANTILES]


class Intervals(unittest.TestCase):
    """A26 (2) (WP-S2): the reported interval is the marginal posterior quantile interval, not the Laplace sd at the
    mode; the prior is the Jeffreys measure x Half-Normal(f) weight."""

    def test_quantiles_exact_on_a_skewed_posterior_where_laplace_undercovers(self):
        """Negative: on a skewed posterior with a known marginal (log of a Gamma(0.3) variable), the Laplace
        interval mode +- sd holds 0.53 of the posterior (not 0.683) and its centre is 0.77 sd off the median.
        Control: the marginal quantiles reproduce the exact quantiles, and their 1-sd interval holds 0.683."""
        bounds = [(-40.0, 10.0), (-45.0, 15.0)]
        x = optimize.minimize(_skewed, np.array([0.5, 0.5]), method="L-BFGS-B", bounds=bounds).x
        sd = math.sqrt(np.linalg.inv(VI._hessian(_skewed, x))[0, 0])
        self.assertAlmostEqual(sd, GAMMA_SHAPE ** -0.5, delta=0.01)
        exact = _skewed_quantiles()
        lap = _skewed_cdf(x[0] + sd) - _skewed_cdf(x[0] - sd)
        self.assertLess(lap, 0.6827 - 0.1)                                  # negative: Laplace undercovers
        self.assertGreater(abs(x[0] - exact[2]) / sd, 0.5)                  # and is off-centre
        m = VI.marginal_quantiles(_skewed, x, 0, bounds, sd)
        np.testing.assert_allclose(m["quantiles"], exact, atol=0.05)       # control
        self.assertTrue(m["laplace_marginal"])
        self.assertFalse(m["truncated"])
        q = m["quantiles"]
        self.assertAlmostEqual(_skewed_cdf(q[3]) - _skewed_cdf(q[1]), 0.6827, delta=0.01)
        self.assertAlmostEqual(m["cdf"](exact[2]), 0.5, delta=0.01)

    def test_window_widens_from_a_too_narrow_start(self):
        """A too small starting sd (0.03 of the true width) still gives the exact quantiles: the window widens
        while an edge carries density; negative: with the widening disabled (one window) the quantiles are
        wrong and the result says `truncated`."""
        bounds = [(-40.0, 10.0), (-45.0, 15.0)]
        x0 = np.array([math.log(GAMMA_SHAPE), math.log(GAMMA_SHAPE)])
        m = VI.marginal_quantiles(_skewed, x0, 0, bounds, 0.05)
        exact = _skewed_quantiles()
        np.testing.assert_allclose(m["quantiles"], exact, atol=0.05)
        self.assertFalse(m["truncated"])
        self.assertLess(m["window"][0], exact[0])
        with mock.patch.object(VI, "_WIDEN", 1):
            short = VI.marginal_quantiles(_skewed, x0, 0, bounds, 0.05)
        self.assertTrue(short["truncated"])
        self.assertGreater(np.abs(np.array(short["quantiles"]) - exact).max(), 1.0)

    def test_fisher_information_matches_the_dense_formula(self):
        """The block-wise expected Fisher information equals 0.5 tr(P S_i P S_j) formed densely, and the cached
        kernels equal `kernel_block`; negative: a kernel with ell off by 1 % gives a different information."""
        cfg = X.CONFIGS["two"]
        c, names, res, V, J = X.draw("two", 3, cfg)
        inferred, fixed = VI._components(c, names)
        post = VI.Objective(res, V, inferred, linear.vmodel_matrix(fixed, names), J)
        x = np.log([0.05, 0.08, 0.02, 0.15])

        def dense(ell_scale=1.0):
            S = post.covariance(x)
            Si = np.linalg.inv(S)
            P = Si - Si @ J @ np.linalg.solve(J.T @ Si @ J, J.T @ Si)
            D = []
            for k, comp in enumerate(inferred):
                f, ell = math.exp(x[2 * k]), math.exp(x[2 * k + 1]) * ell_scale
                K = VI.kernel_block(comp["z"], f, ell)
                for M in (2 * K, K * (comp["z"][:, None] - comp["z"][None, :]) ** 2 / ell ** 2):
                    Z = np.zeros_like(S)
                    Z[np.ix_(comp["rows"], comp["rows"])] = M
                    D.append(P @ Z)
            return np.array([[0.5 * np.trace(a @ b) for b in D] for a in D])
        info = post.fisher(x)
        np.testing.assert_allclose(info, dense(), rtol=1e-10, atol=1e-10)
        self.assertGreater(np.abs(info - dense(1.01)).max(), 1e-3)         # negative
        R = post.covariance(x) - post.base
        for k, comp in enumerate(inferred):
            np.testing.assert_allclose(R[np.ix_(comp["rows"], comp["rows"])],
                                       VI.kernel_block(comp["z"], math.exp(x[2 * k]), math.exp(x[2 * k + 1])),
                                       atol=1e-15)

    @unittest.skipUnless(SLOW, "slow (about 50 s; a weakly identified component over many draws): set HEP_SLOW_TESTS=1")
    def test_weak_component_laplace_undercovers_quantile_interval_covers(self):
        """The S3 failure, reproduced on its weakly determined component alone (n 25, f 0.02 with sigma 0.01,
        ell 0.15, bounds [0.02, 2]; 32 fixed draws). Negative (caught): WP-S's prior with the Laplace sd at the mode
        gives ell pulls biased (mean 0.41) and too wide (sd 1.27): its 95 % interval covers ell in 27 of 32.
        Control: the revised prior with the marginal quantile interval (the S3 driver's `pull`) covers in 32 of 32,
        mean -0.26 (within 2 SE = 0.35 of 0). Recorded: here the revised interval is conservative (sd 0.69)."""
        cfg = {"sigma": 0.01, "components": [{"n": 25, "f": 0.02, "length": 0.15, "f_scale": 0.05,
                                              "length_bounds": [0.02, 2.0]}]}
        old, revised = [], []
        for r in range(32):
            c, names, res, V, J = X.draw("weak", 40 + r, cfg)
            inferred, fixed = VI._components(c, names)
            wps = VI.Objective(res, V, inferred, linear.vmodel_matrix(fixed, names), J, jeffreys=False)
            b = wps.bounds()
            best = min((optimize.minimize(wps, x0, method="L-BFGS-B", bounds=b) for x0 in VI._starts(inferred, b)),
                       key=lambda o: o.fun)
            sd = math.sqrt(np.linalg.inv(VI._hessian(wps, best.x))[1, 1])
            old.append((best.x[1] - math.log(0.15)) / sd)
            e = VI.infer(c, names, res, V, flat=J)["estimates"][0]
            revised.append(X.pull(e["log_quantiles"]["length"], 0.15))
        old_a, new_a = np.array(old), np.array(revised)
        self.assertGreater(float(old_a.mean()), 0.3)                        # negative: biased
        self.assertGreater(float(old_a.std(ddof=1)), 1.15)                  # and too wide
        self.assertLessEqual(int((np.abs(old_a) <= 1.96).sum()), 28)       # 95 % interval undercovers
        self.assertGreaterEqual(int((np.abs(new_a) <= 1.96).sum()), 30)    # control: covers
        self.assertLess(abs(float(new_a.mean())), 2 / math.sqrt(32))

    def test_s3_pull_uses_the_error_toward_the_truth(self):
        q = [-2.0, -1.5, -1.0, -0.2, 0.5]                                  # median -1, errors 0.5 down, 0.8 up
        self.assertAlmostEqual(X.pull(q, math.exp(-1.5)), 1.0)              # median above truth: lower error
        self.assertAlmostEqual(X.pull(q, math.exp(-0.2)), -1.0)             # below truth: upper error
        self.assertAlmostEqual(X.pull(q, math.exp(-0.6)), -0.5)
        self.assertIsNone(X.pull([0.0, 0.0, 0.0, 0.0, 0.0], 2.0))


class Script(unittest.TestCase):
    def run_script(self, *args):
        p = subprocess.run([sys.executable, "-I", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                           timeout=120)
        return p.returncode, json.loads(p.stdout)

    def test_vmodel_infer_subcommand(self):
        c, names, r, V, J = case(2)
        with tempfile.TemporaryDirectory() as d:
            cp, ip = Path(d) / "c.json", Path(d) / "i.json"
            cp.write_text(json.dumps(c))
            ip.write_text(json.dumps({"names": names, "residual": r.tolist(), "V": V.tolist(), "flat": J.tolist()}))
            code, out = self.run_script("vmodel-infer", "--contract", cp, "--input", ip)
            self.assertEqual((code, out["status"]), (0, "ok"))
            self.assertEqual(out["version"]["kind"], "vmodel-version")
            code, out = self.run_script("vmodel-infer", "--contract", cp, "--input", ip, "--likelihood", "conditional")
            self.assertEqual((code, out["code"]), (2, "vmodel_infer.conditional"))
            c["validation"]["mode"] = "none"
            cp.write_text(json.dumps(c))
            code, out = self.run_script("vmodel-infer", "--contract", cp, "--input", ip)
            self.assertEqual((code, out["code"]), (2, "vmodel_infer.not_holdout"))


class StudyS3(unittest.TestCase):
    def test_task_table_covers_every_draw(self):
        seen: dict = {}
        for name, kw in X.TASKS:
            seen.setdefault(name, set()).update(range(kw["r0"], kw["r0"] + kw["reps"]))
        self.assertEqual(seen, {k: set(range(X.REPS)) for k in X.CONFIGS})

    @unittest.skipUnless(SLOW, "slow (about 30 s; the S3 driver's local configuration): set HEP_SLOW_TESTS=1")
    def test_local_smoke(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s3.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(X.main(["--local", "--out", str(out)]), 0)
            rep = json.loads(out.read_text())
        self.assertEqual(rep["label"], "smoke")
        self.assertEqual(set(rep["results"]), set(X.CONFIGS))
        self.assertIn("provisional-thresholds", rep["flags"])

    def test_merge_rule_negative_and_control(self):
        g = np.random.default_rng(5)
        good = [{"r": r, "pulls": {"f0": float(x), "length0": float(y)}} for r, (x, y) in
                enumerate(g.standard_normal((2000, 2)))]
        self.assertTrue(X.judge(good, 2000)["passed"])                   # control
        biased = [dict(row, pulls={"f0": row["pulls"]["f0"] + 0.3, "length0": row["pulls"]["length0"]})
                  for row in good]
        j = X.judge(biased, 2000)
        self.assertFalse(j["passed"])
        self.assertFalse(j["pulls"]["f0"]["passed"])
        wide = [dict(row, pulls={"f0": row["pulls"]["f0"], "length0": 1.5 * row["pulls"]["length0"]})
                for row in good]
        self.assertFalse(X.judge(wide, 2000)["passed"])
        undefined = [dict(good[0], pulls={"f0": None, "length0": 0.0})] + good[1:]
        j = X.judge(undefined, 2000)
        self.assertEqual((j["undefined"], j["complete"], j["passed"]), (1, False, False))
        self.assertFalse(X.judge(good[:-1], 2000)["passed"])                # a missing draw: incomplete


if __name__ == "__main__":
    unittest.main()
