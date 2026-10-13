"""hep-statistics audit T22 (independent outer-toy validation of unfolding) and T23 (response toys). SYNTHETIC.

T22: inversion covers at nominal per bin and jointly; a covariance that omits the efficiency or the finite-MC response
term while the generation has it undercovers (the negative baselines), and including the term restores coverage;
Tikhonov with GCV chosen inside every toy on an alternative truth undercovers, and its per-toy choices vary.
Criteria (fixed before the runs): |coverage - 0.6827| <= 4 binomial standard errors for a valid procedure; a negative
baseline must fall below 0.6827 by more than 4 standard errors in at least one bin.
T23: response toys record generated, used and skipped (with the reason) and never fill or renormalize a column; the
independent-Poisson-cell model is flagged where a high-efficiency column exceeds efficiency 1 (the multinomial model
never does)."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.stats import unfolding_diagnostics as ud  # noqa: E402

N, TOYS, NOMINAL = 6, 1000, 0.6827
SE = math.sqrt(NOMINAL * (1 - NOMINAL) / TOYS)


def response(eff0=0.6, step=0.05):
    r = [[0.0] * N for _ in range(N)]
    for j in range(N):
        w = [math.exp(-0.5 * ((i - j) / 0.7) ** 2) for i in range(N)]
        for i in range(N):
            r[i][j] = (eff0 + step * j) * w[i] / sum(w)
    return r


TRUTH = [4000 * math.exp(-0.5 * j) for j in range(N)]
TEST = [4000 * math.exp(-0.35 * j) for j in range(N)]
BASE = {"response": response(), "truth": TRUTH}
EFF = {"sigma": 0.05, "correlation": {"kind": "full"}}


def run(doc, method="tsvd", values=(N,), crit="fixed", seed=1):
    return ud.outer_coverage(doc, method, list(values), crit, TOYS, seed)


class T22OuterCoverage(unittest.TestCase):
    def assertCovers(self, r):
        for b in r["per_bin"]:
            self.assertLess(abs(b["coverage"] - NOMINAL), 4 * SE, r["per_bin"])
        self.assertLess(abs(r["simultaneous_coverage"] - NOMINAL), 4 * SE)

    def test_inversion_covers_marginally_and_jointly(self):
        r = run(BASE)
        self.assertEqual(r["outcomes"]["ok"], TOYS)
        self.assertCovers(r)
        for b in r["per_bin"]:
            self.assertLess(abs(b["bias"]), 4 * b["bias_standard_error"])

    def test_efficiency_term_negative_baseline(self):
        self.assertCovers(run(dict(BASE, efficiency_uncertainty=EFF)))
        bad = run(dict(BASE, efficiency_uncertainty=EFF, covariance_omits=["efficiency"]))
        self.assertLess(bad["min_marginal_coverage"], NOMINAL - 4 * SE)
        self.assertFalse(bad["sources_in_covariance"]["efficiency"])

    def test_finite_mc_negative_baseline(self):
        self.assertCovers(run(dict(BASE, mc_events_per_truth_bin=[3000] * N)))
        bad = run(dict(BASE, mc_events_per_truth_bin=[3000] * N, covariance_omits=["response"]))
        self.assertLess(bad["min_marginal_coverage"], NOMINAL - 4 * SE)

    def test_regularization_chosen_inside_each_toy(self):
        r = run(dict(BASE, test_truth=TEST), "tikhonov", (1e-5, 1e-4, 1e-3, 1e-2, 1e-1), "gcv")
        self.assertGreater(len(r["chosen_settings"]), 1)                     # the choice is redone per toy
        self.assertEqual(sum(r["chosen_settings"].values()), r["outcomes"]["ok"])
        self.assertLess(r["simultaneous_coverage"], NOMINAL - 4 * SE)       # regularization costs joint coverage
        self.assertEqual(r["generation_truth"], "test_truth")

    def test_input_checks_and_cli(self):
        for call in (lambda: ud.outer_coverage(BASE, "dagostini", [3], "fixed", 100, 1),
                     lambda: ud.outer_coverage(BASE, "tsvd", [N], "aic", 100, 1),
                     lambda: ud.outer_coverage(dict(BASE, covariance_omits=["data"]), "tsvd", [N], "fixed", 100, 1)):
            with self.assertRaises(ud.ToyError):
                call()


class T23ResponseToys(unittest.TestCase):
    def doc(self, eff0, gen):
        return {"response": response(eff0, 0.0), "truth": TRUTH, "mc_events_per_truth_bin": [gen] * N}

    def test_accounting_and_generation_model(self):
        cells = ud.response_stat(self.doc(0.98, 200), "tsvd", N, 300, 3, "poisson_cells")
        multi = ud.response_stat(self.doc(0.98, 200), "tsvd", N, 300, 3, "multinomial")
        for r in (cells, multi):
            self.assertEqual(r["toys_generated"], 300)
            self.assertEqual(r["toys_used"] + sum(r["toys_skipped"].values()), 300)
        self.assertGreater(cells["toys_with_a_column_efficiency_above_one"], 0)   # independent cells exceed 1
        self.assertEqual(multi["toys_with_a_column_efficiency_above_one"], 0)

    def test_empty_columns_are_skipped_and_counted(self):
        r = ud.response_stat(self.doc(0.3, 5), "tsvd", N, 300, 3, "multinomial")
        self.assertGreater(r["toys_skipped"]["empty_truth_column"], 0)
        self.assertEqual(r["toys_used"] + r["toys_skipped"]["empty_truth_column"], 300)
        with self.assertRaisesRegex(ud.ToyError, r"used of 300 generated; skipped"):
            ud.response_stat(self.doc(0.3, 2), "tsvd", N, 300, 3, "multinomial")


def _dag_example(n=15):
    truth = [2000.0 * math.exp(-0.25 * j) + 50.0 for j in range(n)]
    resp = [[0.0] * n for _ in range(n)]
    for j in range(n):
        eff = 0.8 - 0.01 * j
        w = [math.exp(-0.5 * ((i - j) / 0.8) ** 2) for i in range(n)]
        sw = sum(w)
        for i in range(n):
            resp[i][j] = eff * w[i] / sw
    return resp, truth


class DagostiniUnfoldSTH315(unittest.TestCase):
    """STH-T3.15: D'Agostini unfolding of data with its covariance. 15 x 15 response; the analytic variances (data and
    response terms) agree with toys (data and response redrawn, NumPy oracle) within 10% per bin; mc_events above
    1e5 are accepted on this analytic path."""

    def test_variances_agree_with_toys(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest("NumPy needed for the toy oracle")
        from core.stats import unfolding_diagnostics as ud
        resp, truth = _dag_example()
        n = len(truth)
        mu = [sum(resp[i][j] * truth[j] for j in range(n)) for i in range(n)]
        gen = [20000.0] * n
        iters = 4
        r = ud.dagostini_unfold({"response": resp, "data": mu, "mc_events_per_truth_bin": gen}, iters, "multinomial")
        var = [r["covariance_total"][a][a] for a in range(n)]
        rng = np.random.default_rng(7)
        R = np.array(resp)
        eff = R.sum(axis=0)
        est = []
        for _ in range(1500):
            d = rng.poisson(mu).astype(float)
            Rt = np.empty_like(R)
            for j in range(n):
                probs = np.append(R[:, j], 1.0 - eff[j])
                Rt[:, j] = rng.multinomial(int(gen[j]), probs)[:-1] / gen[j]
            t = np.ones(n) * d.sum() / max(Rt.sum(), 1e-12)
            e = Rt.sum(axis=0)
            for _ in range(iters):
                fold = Rt @ t
                t = (Rt.T @ (d / np.where(fold > 0, fold, 1.0))) * t / e
            est.append(t)
        tv = np.var(np.array(est), axis=0, ddof=1)
        for a in range(n):
            self.assertLess(abs(var[a] / tv[a] - 1.0), 0.10, (a, var[a], tv[a]))

    def test_large_mc_counts_and_refusals(self):
        from core.stats import unfolding_diagnostics as ud
        resp, truth = _dag_example(5)
        mu = [sum(resp[i][j] * truth[j] for j in range(5)) for i in range(5)]
        r = ud.dagostini_unfold({"response": resp, "data": mu, "mc_events_per_truth_bin": [1e8] * 5}, 3)
        self.assertEqual(len(r["estimate"]), 5)
        self.assertLess(max(r["covariance_response"][a][a] / r["covariance_data"][a][a] for a in range(5)), 1e-3)
        for bad in ({"response": resp, "data": mu[:4]}, {"response": resp, "data": [0.0] * 5},
                    {"response": resp, "data": mu, "mc_events_per_truth_bin": [0.5] * 5}):
            with self.assertRaises(ud.ToyError):
                ud.dagostini_unfold(bad, 3)


if __name__ == "__main__":
    unittest.main()
