"""Geant4 program C2.1: paired mode of core/stats/decisions.py, the values accumulator of core/simulation/summary.py
with empirical quantiles (core/stats/batch_means.py, core/simulation/estimates.py), and seed_group in
core/simulation/seeds.py.

Oracles: coverage and rejection toys with known truth (common random numbers drawn here); empirical quantiles against
numpy.quantile (method linear, a third-party implementation of Hyndman-Fan type 7); summaries against the events
that built them; the uniqueness rule as a truth table."""
import json
import math
import random
import statistics
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.simulation import estimates as E, seeds, summary as S  # noqa: E402
from core.stats import batch_means as M, decisions as D  # noqa: E402
from core.stats.distributions import t_ppf  # noqa: E402

K = 16


def crn_blocks(rng, mu_a, mu_b, common=1.0, own=0.2):
    """Block estimates of two designs on common random numbers: a shared block effect plus each design's own noise."""
    u = [rng.gauss(0, common) for _ in range(K)]
    return [mu_a + x + rng.gauss(0, own) for x in u], [mu_b + x + rng.gauss(0, own) for x in u]


class PairedMode(unittest.TestCase):
    def test_absolute_statistic_is_the_mean_block_difference(self):
        a, b = [1.0, 2.0, 4.0, 3.0], [0.5, 1.0, 3.0, 2.5]
        r = D.paired_statistic((a, b), "absolute")
        d = [x - y for x, y in zip(a, b)]
        self.assertAlmostEqual(r["value"], statistics.fmean(d), delta=1e-15)
        self.assertAlmostEqual(r["se"], statistics.stdev(d) / 2, delta=1e-15)
        self.assertEqual(r["dof"], 3)

    def test_relative_statistic_at_r(self):
        a, b = [2.2, 1.9, 2.4], [2.0, 2.1, 2.0]
        r = D.paired_statistic((a, b), "relative", 0.1)
        bbar = statistics.fmean(b)
        z = [(x - 1.1 * y) / bbar for x, y in zip(a, b)]
        self.assertAlmostEqual(r["value"], statistics.fmean(z), delta=1e-15)
        self.assertAlmostEqual(r["se"], statistics.stdev(z) / math.sqrt(3), delta=1e-15)

    def test_coverage_of_the_90_percent_interval(self):
        rng, trials, hit = random.Random(20261025), 4000, 0
        for _ in range(trials):
            a, b = crn_blocks(rng, 5.3, 5.0)
            r = D.paired_statistic((a, b), "absolute")
            h = t_ppf(0.95, r["dof"]) * r["se"]
            hit += abs(r["value"] - 0.3) <= h
        cov, mc = hit / trials, math.sqrt(0.9 * 0.1 / trials)
        self.assertLessEqual(abs(cov - 0.90), 0.02 + 3 * mc, cov)

    def test_relative_test_rejects_at_most_alpha_at_the_bound(self):
        rng, trials, rejected, r_bound = random.Random(7), 4000, 0, 0.05
        for _ in range(trials):
            u = [rng.gauss(0, 0.8) for _ in range(K)]
            b = [10.0 + x + rng.gauss(0, 0.3) for x in u]
            a = [(1 + r_bound) * (10.0 + x) + rng.gauss(0, 0.3) for x in u]
            z = D.paired_statistic((a, b), "relative", r_bound)
            rejected += z["value"] + t_ppf(0.95, z["dof"]) * z["se"] < 0   # "a < (1 + r) b" claimed at 95 %
        p, mc = rejected / trials, math.sqrt(0.05 * 0.95 / trials)
        self.assertLessEqual(p, 0.05 + 3 * mc, p)

    def test_pairing_reduces_the_variance_of_the_difference(self):
        rng = random.Random(3)
        paired, indep = [], []
        for _ in range(500):
            a, b = crn_blocks(rng, 1.0, 1.0)
            paired.append(D.paired_statistic((a, b), "absolute")["value"])
            a2, _ = crn_blocks(rng, 1.0, 1.0)
            indep.append(statistics.fmean(a2) - statistics.fmean(b))
        ratio = statistics.variance(indep) / statistics.variance(paired)
        self.assertGreater(ratio, 2.0, ratio)   # gate G-C2a's default threshold

    def test_paired_equivalence_and_change(self):
        rng = random.Random(11)
        a, b = crn_blocks(rng, 1.000, 1.0, own=0.002)
        eq = D.equivalence(None, None, None, 0.05, pairing="paired", blocks=(a, b))
        self.assertEqual(eq["verdict"], "pass", eq)
        self.assertEqual(eq["paired"]["pairing"], "paired")
        a, b = crn_blocks(rng, 1.20, 1.0, own=0.002)
        self.assertEqual(D.change(None, None, None, 0.05, pairing="paired", blocks=(a, b))["verdict"], "changed")
        a, b = crn_blocks(rng, 1.0, 1.0, own=0.002)
        self.assertEqual(D.change(None, None, None, 0.05, pairing="paired", blocks=(a, b), mode="absolute")["verdict"],
                         "unchanged")

    def test_se_target_is_a_quarter_of_the_tolerance(self):
        rng = random.Random(5)
        a, b = crn_blocks(rng, 1.0, 1.0, own=0.08)   # se of the relative difference about 0.02 > 0.05 / 4
        eq = D.equivalence(None, None, None, 0.05, pairing="paired", blocks=(a, b))
        self.assertNotEqual(eq["verdict"], "pass")
        self.assertGreater(eq["paired"]["se"], 0.05 / 4)

    def test_bad_paired_input(self):
        with self.assertRaises(D.DecisionError):
            D.paired_statistic(([1.0, 2.0], [1.0]), "absolute")
        with self.assertRaises(D.DecisionError):
            D.equivalence(0.0, 0.1, 5, 0.1, pairing="matched")
        self.assertEqual(D.equivalence(0.0, 0.01, 15, 0.1)["verdict"], "pass")   # the default is independent


def rows_for(values_per_event):
    return [{"event": i, "x": x} for i, x in enumerate(values_per_event)]


DECL = {"name": "x", "source_column": "x", "selection": [], "bins": {"lo": -10.0, "hi": 10.0, "width": 0.5},
        "thresholds": [], "values": True}


class ValuesAccumulator(unittest.TestCase):
    def test_values_are_kept_per_block_in_event_order(self):
        rng = random.Random(1)
        xs = [rng.gauss(0, 1) for _ in range(64)]
        rows = rows_for(xs)
        rng.shuffle(rows)
        doc = S.build(rows, [DECL], 16, 4)
        obs = S.observable(doc, "x")
        self.assertEqual([b["values"] for b in obs["blocks"]], [xs[i * 16:(i + 1) * 16] for i in range(4)])
        self.assertEqual(obs["quantile_method"], "hyndman-fan-7")
        self.assertEqual(doc["merge"]["values"], "concat")

    def test_values_omitted_above_values_max(self):
        doc = S.build(rows_for([0.1] * 40), [dict(DECL, values_max=9)], 10, 4)
        obs = S.observable(doc, "x")
        self.assertIn("values_omitted", obs)
        self.assertTrue(all("values" not in b for b in obs["blocks"]))
        with self.assertRaises(S.SummaryError):
            S.block_values(obs)

    def test_jobs_merge_by_concatenation(self):
        rng = random.Random(2)
        xs = [rng.uniform(-1, 1) for _ in range(64)]
        whole = S.build(rows_for(xs), [DECL], 16, 4)
        a = S.build([r for r in rows_for(xs) if r["event"] % 16 < 8], [DECL], 16, 4)
        b = S.build([r for r in rows_for(xs) if r["event"] % 16 >= 8], [DECL], 16, 4)
        self.assertEqual(S.block_values(S.observable(S.merge([a, b]), "x")),
                         S.block_values(S.observable(whole, "x")))

    def test_merge_beyond_values_max_omits(self):
        small = S.build(rows_for([0.1] * 4), [dict(DECL, values_max=6)], 8, 1)
        merged = S.merge([small, S.build([{"event": i, "x": 0.2} for i in range(4, 8)], [dict(DECL, values_max=6)], 8, 1)])
        self.assertIn("values_omitted", S.observable(merged, "x"))

    def test_empirical_quantile_against_numpy(self):
        import numpy as np
        rng = random.Random(4)
        for n in (1, 2, 3, 10, 101, 1000):
            xs = [rng.expovariate(1.0) for _ in range(n)]
            for q in (0.0, 0.05, 0.25, 0.5, 0.68, 0.9, 1.0):
                with self.subTest(n=n, q=q):
                    self.assertAlmostEqual(M.empirical_quantile(xs, q)["value"], float(np.quantile(xs, q)),
                                           delta=1e-12 * max(1.0, abs(float(np.quantile(xs, q)))))
        self.assertEqual(M.empirical_quantile([], 0.5)["status"], "incomplete")

    def test_quantile_estimator_uses_values_when_kept(self):
        rng = random.Random(6)
        xs = [rng.gauss(0, 1) for _ in range(160)]
        with_v = S.build(rows_for(xs), [DECL], 10, 16)
        r = E.estimate(with_v, {"name": "x", "estimator": "quantile", "quantile": 0.84})
        per = [M.empirical_quantile(xs[i * 10:(i + 1) * 10], 0.84)["value"] for i in range(16)]
        self.assertAlmostEqual(r["value"], statistics.fmean(per), delta=1e-12)
        self.assertEqual(r["quantile_method"], "hyndman-fan-7")
        without = S.build(rows_for(xs), [{k: v for k, v in DECL.items() if k != "values"}], 10, 16)
        r2 = E.estimate(without, {"name": "x", "estimator": "quantile", "quantile": 0.84})
        self.assertIn("linear within the bin", r2["method"])
        self.assertNotIn("quantile_method", r2)

    def test_block_estimates_average_to_the_estimate(self):
        rng = random.Random(8)
        xs = [rng.gauss(0, 1) for _ in range(1600)]
        doc = S.build(rows_for(xs), [dict(DECL, thresholds=[0.5], bins={"lo": -10.0, "hi": 10.0, "width": 0.05})],
                      100, 16)
        for decl in ({"name": "x"}, {"name": "x", "estimator": "proportion"},
                     {"name": "x", "estimator": "quantile", "quantile": 0.84},
                     {"name": "x", "estimator": "gaussian-core"}):
            with self.subTest(decl=decl):
                b = E.block_estimates(doc, decl)
                self.assertEqual(b["status"], "ok")
                self.assertAlmostEqual(statistics.fmean(b["thetas"]), E.estimate(doc, decl)["value"], delta=1e-12)
        self.assertEqual(E.block_estimates(doc, {"name": "x", "estimator": "mode"})["status"], "incomplete")

    def test_summaries_without_values_still_read_and_validate(self):
        from contracts import schema
        doc = S.build(rows_for([0.5] * 32), [{k: v for k, v in DECL.items() if k != "values"}], 8, 4)
        self.assertNotIn("values", doc["merge"])
        self.assertTrue(all("values" not in b for b in doc["observables"][0]["blocks"]))
        sch = json.loads((PLUGIN / "contracts" / "schemas" / "simulation_summary.json").read_text())
        self.assertTrue(schema.validate(doc, sch).ok)
        self.assertTrue(schema.validate(S.build(rows_for([0.5] * 32), [DECL], 8, 4), sch).ok)


class SeedGroup(unittest.TestCase):
    def test_search_and_confirmation_seeds(self):
        s = seeds.search_group_seed("SEARCH-1", "gen-3")
        self.assertEqual(s, seeds.H("SEARCH-1", "search", "gen-3"))
        sid = seeds.confirmation_study_id("SEARCH-1", "abc", "momentum-resolution-core",
                                          {"species": "proton", "rigidity_GV": 1})
        self.assertEqual(sid, "confirm:SEARCH-1:abc:momentum-resolution-core:rigidity_GV=1,species=proton")
        self.assertNotEqual(seeds.logical_run_seed(sid, "nominal", "p0"), s)

    def test_uniqueness_rule(self):
        base = {"blocks": 16, "block_size": 64, "seeding": "per-event"}
        ok = [dict(base, run_id="a", seed=5, spec_sha256="x", seed_group="g1"),
              dict(base, run_id="b", seed=5, spec_sha256="y", seed_group="g1"),
              dict(base, run_id="c", seed=6, spec_sha256="x", seed_group=None)]
        self.assertEqual(seeds.seed_uniqueness_problems(ok), [])
        outside = ok + [dict(base, run_id="d", seed=6, spec_sha256="z", seed_group=None)]
        self.assertIn("outside one declared seed_group", seeds.seed_uniqueness_problems(outside)[0])
        same_spec = [ok[0], dict(ok[1], spec_sha256="x")]
        self.assertIn("same spec hash", seeds.seed_uniqueness_problems(same_spec)[0])
        diff_k = [ok[0], dict(ok[1], blocks=8)]
        self.assertIn("differ in blocks", seeds.seed_uniqueness_problems(diff_k)[0])


if __name__ == "__main__":
    unittest.main()
