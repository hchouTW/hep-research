"""The inference form of V_model (Part B section 5.4 row "Inferred"; phase 5, gap V6 read by A25 (7)): the card's
tests (a)-(d), each negative with its positive control, the opt-in path of `linear.vmodel_columns`, the
`calib_likelihood.py vmodel-infer` subcommand, and the S3 recovery driver (tests/core/calibration_phase5_vmodel_s3.py:
task table, local smoke, merge rule). Synthetic; no Slurm."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import optimize

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_fixtures as F  # noqa: E402
import calibration_phase5_vmodel_s3 as X  # noqa: E402
from core.calibration import contract as cc  # noqa: E402
from core.calibration import linear  # noqa: E402
from core.calibration import vmodel_infer as VI  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "calib_likelihood.py"
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
        """(d) On synthetic draws with known f, ell, |log x-hat - log x| <= 2 sd_log_x in >= 80% of 24 draws for each;
        negative control: against a misstated truth (x 3) the same check fails."""
        hits = {"f": 0, "length": 0}
        wrong = {"f": 0, "length": 0}
        n = 24
        for r in range(n):
            c, names, res, V, J = case(100 + r)
            e = VI.infer(c, names, res, V, flat=J)["estimates"][0]
            self.assertFalse(e["at_bound"])
            for par, sd in (("f", "sd_log_f"), ("length", "sd_log_length")):
                truth = CFG["components"][0][par]
                hits[par] += abs(math.log(e[par] / truth)) <= 2 * e[sd]
                wrong[par] += abs(math.log(e[par] / (3 * truth))) <= 2 * e[sd]
        for par in hits:
            self.assertGreaterEqual(hits[par], 0.8 * n, par)
            self.assertLess(wrong[par], 0.8 * n, par)


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
