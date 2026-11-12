"""The phase-3 section 8.7 calibration drivers (tests/core/calibration_phase3_cals.py: rows 2004 P6, 2008, 2009): the
task table, the local smoke run of every family, the exact map covariance of the theta-noise study against its
sampler, and the merge and decision logic, where a failing configuration is reported as failed (negative) next to a
passing control. Synthetic; no Slurm."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import calibration_phase3_cals as X  # noqa: E402


class TaskTable(unittest.TestCase):
    def test_tasks_cover_every_registered_repetition(self):
        reps: dict = {}
        for name, kw in X.TASKS:
            key = (name, X._key(name, kw), kw.get("where"))
            reps.setdefault(key, set()).update(range(kw["r0"], kw["r0"] + kw["reps"]))
        for H in X.P6_H:
            self.assertEqual(reps[("p6", str(H), None)], set(range(X.P6_REPS)))
        for n, s, m in X.th_configs():
            k = X.th_key(n, s, m)
            self.assertEqual(reps[("theta", k, "interior")], set(range(X.TH_REPS)))
            self.assertEqual(reps[("theta", k, "boundary")], set(range(X.TH_CLOSURE_COUNT)))
        self.assertEqual(reps[("pde", "exact|table", None)], set(range(X.PDE_EXACT_REPS)))
        self.assertEqual(reps[("pde", "power|0.5", None)], set(range(X.PDE_POWER_REPS)))
        self.assertEqual(reps[("pde", "replicas|None", None)], set(range(X.PDE_MAPS)))
        self.assertEqual(len(X.th_configs()), 12)
        self.assertEqual(X.TH_CLOSURE_COUNT, 412)

    def test_seeds_differ_between_calibrations_configurations_and_repetitions(self):
        s = {X._int(c, r, j, 1) for c in (1, 2, 3) for r in range(20) for j in range(4)}
        self.assertEqual(len(s), 3 * 20 * 4)

    def test_rule_counts(self):
        self.assertEqual(X.max_false_alarms(1000, 0.01), 16)          # the registered phase-1 rule of row 2004
        self.assertEqual(X.P6_MAX_FALSE_ALARMS, 29)


class LocalSmoke(unittest.TestCase):
    def test_every_family_runs_and_is_labelled(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "local.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(X.main(["--local", "--out", str(out)]), 0)
            rep = json.loads(out.read_text())
        self.assertEqual(rep["label"], "smoke")
        self.assertEqual(set(rep["results"]), {"p6", "theta", "pde"})
        for r in rep["results"].values():
            self.assertIn("provisional-thresholds", r["flags"])
        self.assertIn("not run", rep["results"]["pde"]["geant4"])
        th = rep["results"]["theta"]["configurations"]["1e+06|0.1|shared"]
        self.assertIn("g8", th)
        self.assertEqual(set(rep["results"]["pde"]["replicas"]) & {"1", "24"}, {"1", "24"})


class ExactMapCovariance(unittest.TestCase):
    def test_sampler_realizes_the_exact_covariance(self):
        """The coupled mapping-run sampler against map_covariance (divergence 0 = nested, 0.3, 1 = independent)."""
        pts = X.th_points(0.2)
        e = X.eps_true(pts)
        n_b = 400
        for div in (0.0, 0.3, 1.0):
            g = np.random.default_rng(3)
            draws = np.array([X.sample_maps(e, n_b, div, g)[:, 2] for _ in range(4000)])
            emp = np.cov(draws.T)
            ana = X.map_covariance(e, n_b, div)[:, :, 2, 2]
            np.testing.assert_allclose(draws.mean(0), e[:, 2], atol=4 * np.sqrt(ana.diagonal().max() / 4000))
            self.assertLess(np.max(np.abs(emp - ana)) / ana.diagonal().max(), 0.1, div)
        self.assertTrue(np.all(X.map_covariance(e, n_b, 1.0)[0, 1] == 0))


def p6_rows(n, fails):
    rows = []
    for r in range(n):
        f = r < fails
        rec = {"failed": f, "delta_m_failed": False, "z_only_failed": False, "max_ratio": 0.3, "chi2": 120.0,
               "dof": 120, "chi2_failed": f}
        rows.append({"r": r, "0.0": rec, "1.0": rec, "data_term_over_sigma_delta": 1.0})
    return rows


def th_rows(n, sd, s=0.05, kappa=0.01, where="interior", seed=0, bias=0.0):
    g = np.random.default_rng(seed)
    out = []
    for r in range(n):
        p = bias + sd * g.standard_normal()
        out.append({"r": r, "where": where, "converged": True, "error": 0.03 * p, "pull": p, "pull_design": p,
                    "sigma_hat": 0.03, "cover68": bool(abs(p) <= 1), "cover95": bool(abs(p) <= 1.96), "s": s,
                    "kappa": kappa, "p5_passed": s <= 0.25 and kappa <= 0.05, "nugget": 1e-6})
    return out


class Decisions(unittest.TestCase):
    """Each rule: a configuration that breaks it is reported as failed; the passing control next to it passes."""

    def test_p6_false_alarm_count(self):
        ok = X.p6_judge({"40|0.0": p6_rows(2000, 29)})
        self.assertTrue(ok["passed"])
        self.assertAlmostEqual(ok["configurations"]["40|0.0"]["pull_chi2_size"], 29 / 2000)
        bad = X.p6_judge({"40|0.0": p6_rows(2000, 29), "8|0.0": p6_rows(2000, 30)})
        self.assertFalse(bad["passed"])
        self.assertFalse(bad["configurations"]["8|0.0"]["passed"])
        self.assertTrue(bad["configurations"]["40|0.0"]["passed"])
        # v = 1 (an error drawn at V_emu) is reported, not judged (the user's decision of 2026-11-12)
        rep = X.p6_judge({"40|0.0": p6_rows(2000, 29), "8|1.0": p6_rows(2000, 300)})
        self.assertTrue(rep["passed"])
        self.assertEqual((rep["configurations"]["8|1.0"]["judged"], rep["configurations"]["8|1.0"]["passed"]),
                         (False, None))
        self.assertFalse(X.p6_judge({"40|0.0": p6_rows(1999, 0)})["passed"])        # incomplete is not a pass

    def test_theta_pull_width_and_g8(self):
        good = th_rows(2000, 1.0) + th_rows(412, 1.0, where="boundary", seed=1)
        wide = th_rows(2000, 1.12, seed=2) + th_rows(412, 1.0, where="boundary", seed=3)
        out = X.th_judge({"good": good, "wide": wide})
        self.assertTrue(out["configurations"]["good"]["passed"], out["configurations"]["good"])
        self.assertEqual(out["configurations"]["good"]["g8"]["status"], "passed")
        self.assertFalse(out["configurations"]["wide"]["passed"])
        self.assertFalse(out["passed"])
        biased = th_rows(2000, 1.0, seed=4, bias=0.4) + th_rows(412, 1.0, where="boundary", seed=5)
        b = X.th_judge({"biased": biased})["configurations"]["biased"]
        self.assertEqual((b["g8"]["status"], b["passed"]), ("failed", False))         # G8 bias caught

    def test_theta_outside_the_bounds_is_reported_not_judged(self):
        out = X.th_judge({"outside": th_rows(2000, 1.3, kappa=0.12) + th_rows(412, 1.3, where="boundary", seed=1),
                          "good": th_rows(2000, 1.0) + th_rows(412, 1.0, where="boundary", seed=1)})
        self.assertIsNone(out["configurations"]["outside"]["passed"])
        self.assertFalse(out["configurations"]["outside"]["within_bounds"])
        self.assertTrue(out["passed"])
        short = X.th_judge({"good": th_rows(1500, 1.0) + th_rows(412, 1.0, where="boundary", seed=1)})
        self.assertFalse(short["passed"])                                              # incomplete

    def test_pde_exact_pass_rate_and_replica_ratio(self):
        def ex(n, k):
            return [{"r": r, "passed": r < k, "codes": [] if r < k else ["pde_split.dtheta"], "p_value": 0.5,
                     "dof": 12, "dtheta_over_sd": 0.0, "sized": True} for r in range(n)]

        def maps(ratio, n=200):
            b = {"bin": 0, "sum_emp_over_mult": ratio, "sum_emp_over_dirichlet": 1.0, "sum_dirichlet_over_mult":
                 ratio, "chan_emp_over_mult": [ratio, ratio], "corr_emp": -0.1, "corr_mult": -0.1}
            return [{"r": r, "grids": {str(K): {"grid_check": "passed", "bins": [b]} for K in X.PDE_GRIDS},
                     "centre": {"0": [0.1, 0.1]}} for r in range(n)]
        power = {f"power|{rho}": [{"r": r, "rejected": True, "codes": [], "rejected_without_rows": True,
                                   "codes_without_rows": ["pde_split.dtheta"], "chi2_p": 0.0,
                                   "dtheta_over_bound": 2.0} for r in range(500)] for rho in X.PDE_RHO}
        ok = X.pde_judge({"exact|scale": ex(2000, 1900), "exact|table": ex(2000, 1880), "replicas|None": maps(0.995),
                          **power})
        self.assertTrue(ok["passed"], ok)
        bad = X.pde_judge({"exact|scale": ex(2000, 1860), "exact|table": ex(2000, 1880), "replicas|None": maps(0.995),
                           **power})
        self.assertEqual((bad["passed"], bad["exact"]["scale"]["passed"], bad["exact"]["table"]["passed"]),
                         (False, False, True))
        low = X.pde_judge({"exact|scale": ex(2000, 1900), "exact|table": ex(2000, 1880), "replicas|None": maps(0.96),
                           **power})
        self.assertFalse(low["passed"])
        self.assertFalse(low["replicas"]["6"]["passed"])


class Merge(unittest.TestCase):
    def test_missing_tasks_make_the_merge_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            rec = {"task": 0, "family": "p6", "key": "8", "kwargs": {}, "rows": p6_rows(50, 0), "seconds": 1.0,
                   "provenance": {"commit": "abc", "dirty": False}, "flags": X.FLAGS}
            (Path(d) / "task_0000.json").write_text(json.dumps(rec))
            out = Path(d) / "merged.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(X.main(["--merge", d, "--out", str(out)]), 1)
            rep = json.loads(out.read_text())
        self.assertFalse(rep["complete"])
        self.assertEqual(len(rep["missing_tasks"]), len(X.TASKS) - 1)
        self.assertFalse(rep["passed"]["p6"])                       # 50 of 2000 repetitions: not a pass


if __name__ == "__main__":
    unittest.main()
