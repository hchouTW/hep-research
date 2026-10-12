"""Toy CLs stability, toy ensembles and failure accounting (hep-statistics audit T11, T12, T13). All inputs SYNTHETIC.

T11: the toy CLs limit of shape-limit keeps its CLs+b and CLb exceedance counts, an exact-interval range for the
limit, and does not call a limit resolved where the CLb denominator was floored; doubling the toys or refining the grid
or changing the seed moves the limit by less than the combined Monte Carlo range plus one grid step (fixed before the
runs), and doubling the toys narrows the range.
T12: the ensemble is chosen explicitly; seeds derive from (seed, toy index), so tasks merge to the single run; merges
refuse duplicates and gaps; every toy is refitted; ensembles are never pooled.
T13: with injected failures (5% fit failures, empty data, invalid responses, timeouts) the outcome counts sum to the
toys generated and the coverage keeps C/N, (C+F)/N and C/(N-F); the failure policy picks the headline, so discarding
failures cannot raise it.
"""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import toy_ensemble as te  # noqa: E402
from core.stats.poisson_diagnostics import upper_limit  # noqa: E402

DOC = {"bins": [{"n": 4, "b": 3.0, "s": 1.0}, {"n": 2, "b": 1.5, "s": 0.8}],
       "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.1}]}


class T11ToyCls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {key: ll.shape_limit(DOC, 0.95, 0, seed, cls_toys=toys, cls_points=pts)["toy_cls"]
                    for key, (toys, pts, seed) in {"base": (200, 12, 1), "double": (400, 12, 2), "fine": (200, 18, 3)}.items()}

    def test_counts_and_ranges_are_kept(self):
        r = self.runs["base"]
        self.assertTrue(r["observed_limit_resolved"])
        lo, hi = r["observed_limit_mc_range"]
        self.assertLess(lo, r["observed_upper_limit"])
        self.assertLess(r["observed_upper_limit"], hi)
        for row in r["exceedance_counts"]:
            self.assertEqual(row["n"], 200)
            self.assertLessEqual(row["k_sb"], row["n"])
            if row["k_b"]:
                self.assertAlmostEqual(row["cls"], row["k_sb"] / row["k_b"])

    def test_budget_grid_and_seed_changes_stay_within_the_combined_uncertainty(self):
        base = self.runs["base"]
        for key in ("double", "fine"):
            other = self.runs[key]
            half = lambda r: 0.5 * (r["observed_limit_mc_range"][1] - r["observed_limit_mc_range"][0])
            allowed = half(base) + half(other) + max(base["grid_step"], other["grid_step"])
            self.assertLess(abs(base["observed_upper_limit"] - other["observed_upper_limit"]), allowed, key)
        width = lambda r: r["observed_limit_mc_range"][1] - r["observed_limit_mc_range"][0]
        self.assertLess(width(self.runs["double"]), width(base))

    def test_floored_denominator_is_not_a_resolved_limit(self):
        # a deep deficit (no events where 14 are expected): CLb = P(q >= q_obs | b) is about 1e-6, below 1/toys
        doc = {"bins": [{"n": 0, "b": 8.0, "s": 1.0}, {"n": 0, "b": 6.0, "s": 0.8}],
               "nuisances": [{"name": "bkg", "kind": "background_norm", "sigma": 0.1}]}
        r = ll.shape_limit(doc, 0.95, 0, 1, cls_toys=100, cls_points=8)["toy_cls"]
        self.assertTrue(r["cls_denominator_unresolved_at"])
        self.assertFalse(r["observed_limit_resolved"])


def counting_model():
    return ll._ShapeModel(*ll._load_shape(DOC))


class T12Ensembles(unittest.TestCase):
    def test_kind_is_required(self):
        with self.assertRaises(TypeError):
            te.EnsembleSpec(seed=1, n_toys=10)                # type: ignore[call-arg]
        with self.assertRaises(te.EnsembleError):
            te.EnsembleSpec("toys", 1, 10)
        with self.assertRaises(te.EnsembleError):
            te.EnsembleSpec("plug-in", 1, 10, max_attempts=3)   # retries are not configured

    def test_partitions_are_disjoint_and_merge_to_the_single_run(self):
        parts = te.partition(103, 4)
        self.assertEqual(parts[0][0], 0)
        self.assertEqual(parts[-1][1], 103)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(parts, parts[1:])))
        m = counting_model()
        gen = ll.shape_toy_generator(m, m.aux_obs(), 1.0, "conditional-fluctuated-aux")
        ev = ll.shape_q_evaluator(m, 1.0)
        single = te.run(te.EnsembleSpec("conditional-fluctuated-aux", 11, 40), gen, ev)
        tasks = [te.run(te.EnsembleSpec("conditional-fluctuated-aux", 11, 40, task_id=t, n_tasks=3), gen, ev) for t in range(3)]
        merged = te.merge(tasks)
        self.assertEqual(merged["rows"], single["rows"])
        with self.assertRaises(te.EnsembleError):
            te.merge(tasks + [tasks[0]])                     # duplicate partition
        with self.assertRaises(te.EnsembleError):
            te.merge(tasks[:2])                              # missing partition
        again = te.run(te.EnsembleSpec("conditional-fluctuated-aux", 11, 40), gen, ev)
        self.assertEqual(again["rows"], single["rows"])
        other = te.run(te.EnsembleSpec("conditional-fluctuated-aux", 12, 40), gen, ev)
        self.assertNotEqual(other["rows"], single["rows"])

    def test_every_toy_is_refitted(self):
        m = counting_model()
        before = m.log.fits["toy"]
        res = te.run(te.EnsembleSpec("plug-in", 3, 25), ll.shape_toy_generator(m, m.aux_obs(), 1.0, "plug-in"),
                     ll.shape_q_evaluator(m, 1.0))
        q_computed = sum(1 for _, o, v in res["rows"] if o == "ok" and v is not None)
        self.assertEqual(q_computed, 25)
        self.assertGreaterEqual(m.log.fits["toy"] - before, 25)   # at least the global fit of every toy

    def test_ensembles_differ_and_are_never_pooled(self):
        m = counting_model()
        aux = m.aux_obs()
        rows = {}
        for kind in te.ENSEMBLES:
            gen = ll.shape_toy_generator(m, aux, 1.0, kind)
            rows[kind] = te.run(te.EnsembleSpec(kind, 5, 30), gen, lambda d, i: d)["rows"]
        fixed = {tuple(r[2][1]) for r in rows["conditional-fixed-aux"]}
        fluct = {tuple(r[2][1]) for r in rows["conditional-fluctuated-aux"]}
        self.assertEqual(fixed, {tuple(aux)})                    # auxiliary measurements fixed
        self.assertGreater(len(fluct), 1)                        # auxiliary measurements redrawn
        a = te.run(te.EnsembleSpec("plug-in", 5, 10), ll.shape_toy_generator(m, aux, 1.0, "plug-in"), lambda d, i: 1.0)
        b = te.run(te.EnsembleSpec("unconditional-prior", 5, 10), ll.shape_toy_generator(m, aux, 1.0, "unconditional-prior"),
                   lambda d, i: 1.0)
        with self.assertRaises(te.EnsembleError):
            te.merge([a, b])
        self.assertEqual(te.coverage(a, lambda v: True, 0.95)["ensemble"], "plug-in")


class T13FailureAccounting(unittest.TestCase):
    def campaign(self, policy):
        """Coverage of the 95% classical upper limit at s = 3, b = 1 with injected failures (deterministic by index)."""
        s_true, b = 3.0, 1.0

        def generate(rng, i):
            if i % 97 == 13:
                raise te.ToyFailure("empty_data")
            return te_ppf(rng.random(), s_true + b)

        def evaluate(n, i):
            if i % 20 == 7:                                   # 5% optimizer failures
                raise te.ToyFailure("fit_failed")
            if i % 101 == 50:
                raise ValueError("invalid response matrix")      # an unclassified exception: outcome error
            if i % 89 == 3:
                raise te.ToyFailure("timeout")
            if i % 113 == 9:
                raise te.ToyFailure("invalid_data")
            ul = upper_limit(n, b, 0.95)["upper_limit_on_signal"]
            return ul if ul is not None else 0.0
        spec = te.EnsembleSpec("plug-in", 2026, 4000, failure_policy=policy)
        res = te.run(spec, generate, evaluate)
        return res, te.coverage(res, lambda ul: ul >= s_true, 0.95)

    def test_outcomes_sum_and_bounds(self):
        res, cov = self.campaign("count-as-noncovering")
        self.assertEqual(sum(res["outcomes"].values()), res["generated"])
        for o in ("fit_failed", "empty_data", "error", "timeout", "invalid_data"):
            self.assertGreater(res["outcomes"][o], 0, o)
        self.assertAlmostEqual(res["outcomes"]["fit_failed"] / res["generated"], 0.05, delta=0.005)
        c, f, n = cov["covered"], cov["failed"], cov["generated"]
        self.assertEqual(cov["failures_as_noncovering"]["value"], c / n)
        self.assertEqual(cov["failures_as_covering"]["value"], (c + f) / n)
        self.assertEqual(cov["conditional_on_success"]["value"], c / (n - f))
        self.assertEqual(cov["headline"], cov["failures_as_noncovering"])
        # the classical limit covers at least 95% among successes; counting failures as not covering it falls below
        self.assertGreaterEqual(cov["conditional_on_success"]["interval"][1], 0.95)
        self.assertLess(cov["failures_as_noncovering"]["value"], 0.95)
        self.assertFalse(te.coverage_gate(cov)["pass"])            # failures are not discarded to pass the gate

    def test_policies(self):
        _, cov = self.campaign("report-bounds")
        lo, hi = cov["headline"]["bounds"]
        self.assertLess(lo, hi)
        _, cov = self.campaign("count-as-covering")
        self.assertEqual(cov["headline"], cov["failures_as_covering"])
        with self.assertRaises(te.EnsembleError):
            te.EnsembleSpec("plug-in", 1, 10, failure_policy="drop-failures")


def te_ppf(u, mu):
    from core.stats._poisson import ppf
    return ppf(u, mu)


class GateRule(unittest.TestCase):
    def test_gate_uses_a_lower_bound_with_multiplicity(self):
        res = {"generated": 20000, "rows": [(i, "ok", i < 18960) for i in range(20000)],
               "outcomes": {"ok": 20000}, "ensemble": {"kind": "plug-in", "failure_policy": "count-as-noncovering"}}
        cov = te.coverage(res, lambda v: v, 0.95)
        self.assertAlmostEqual(cov["standard_error_at_nominal"], math.sqrt(0.95 * 0.05 / 20000), places=12)
        one = te.coverage_gate(cov, n_tests=1)
        many = te.coverage_gate(cov, n_tests=20)
        self.assertTrue(one["pass"])                                 # 0.948 observed, lower bound above 0.94
        self.assertLess(many["lower_bound"], one["lower_bound"])


if __name__ == "__main__":
    unittest.main()
