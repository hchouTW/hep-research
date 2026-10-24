"""Geant4 program A1.4-A1.10: core/stats/distributions.py, batch_means.py, decisions.py and core/simulation/seeds.py,
summary.py.

Oracles: t and F quantiles against scipy.stats (a third-party implementation) and the values printed in the program
spec (Appendix B); the seed hash against the byte-level definition of A1.4 evaluated here with hashlib; histogram
quantiles and modes against closed forms; summaries against direct sums over the same events; the decision rules of
A1.8 and A1.10 as a truth table; and a usage test that imports only core, as an adapter would."""
import json
import math
import random
import statistics
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.simulation import seeds, summary as S  # noqa: E402
from core.stats import batch_means as M, decisions as D, distributions as T  # noqa: E402


class Distributions(unittest.TestCase):
    def test_t_and_f_quantiles_against_scipy(self):
        from scipy import stats
        for q in (0.001, 0.0227, 0.05, 0.16, 0.5, 0.84135, 0.9, 0.95, 0.975, 0.977, 0.99833, 0.9999):
            for nu in (1, 1.5, 2.7, 5, 15, 18.0, 22.1, 30, 31, 100, 1000):
                with self.subTest(q=q, nu=nu):
                    self.assertAlmostEqual(T.t_ppf(q, nu), stats.t.ppf(q, nu), delta=1e-9 * max(1, abs(stats.t.ppf(q, nu))))
                    self.assertAlmostEqual(T.t_cdf(stats.t.ppf(q, nu), nu), q, delta=1e-10)
        for q in (0.05, 0.5, 0.9, 0.95, 0.99):
            for d1 in (1, 2.5, 15, 31):
                for d2 in (1, 3.3, 15, 31, 200):
                    ref = stats.f.ppf(q, d1, d2)
                    with self.subTest(q=q, d1=d1, d2=d2):
                        self.assertAlmostEqual(T.f_ppf(q, d1, d2), ref, delta=1e-8 * max(1, ref))
                        self.assertAlmostEqual(T.f_cdf(ref, d1, d2), q, delta=1e-10)

    def test_values_printed_in_the_program_spec(self):
        """Program spec, A Appendix B (computed there with scipy, printed to 3-4 digits)."""
        printed = [(T.f_ppf(0.90, 15, 15), 1.972), (T.f_ppf(0.95, 15, 15), 2.403), (T.f_ppf(0.90, 31, 31), 1.594),
                   (T.t_ppf(0.95, 30), 1.697), (T.t_ppf(0.95, 15), 1.753), (T.t_ppf(0.975, 15), 2.131),
                   (T.t_ppf(1 - 0.05 / 30, 30), 3.189)]
        for got, want in printed:
            self.assertAlmostEqual(got, want, delta=0.0006)

    def test_bad_input_is_refused(self):
        for args in ((0.0, 5), (1.0, 5), (0.5, 0), (0.5, -1), (0.5, math.inf)):
            with self.subTest(args=args), self.assertRaises(T.DistributionError):
                T.t_ppf(*args)


class SeedHash(unittest.TestCase):
    @staticmethod
    def spec_h(*xs):
        """The byte-level definition of A1.4, evaluated directly."""
        import hashlib
        d = hashlib.sha256("\x1f".join(str(x) for x in xs).encode("utf-8")).digest()
        return int.from_bytes(d[:8], "big") % (2 ** 31 - 1) + 1

    def test_against_the_definition_and_range(self):
        rng = random.Random(7)
        for _ in range(500):
            xs = tuple(rng.choice([rng.randrange(0, 10 ** 9), f"id-{rng.randrange(100)}"]) for _ in range(rng.randrange(1, 5)))
            h = seeds.H(*xs)
            self.assertEqual(h, self.spec_h(*xs))
            self.assertTrue(1 <= h <= 2 ** 31 - 1)

    def test_fixed_vectors(self):
        """Pinned vectors for the C++ twin (SimHash.hh, stage A2) to reproduce."""
        s = seeds.logical_run_seed("j14-mpv", "nominal", "cut-0.01")
        self.assertEqual(s, self.spec_h("j14-mpv", "nominal", "cut-0.01"))
        self.assertEqual(seeds.job_seeds(s, 0), (self.spec_h(s, 0, 0), self.spec_h(s, 0, 1)))
        self.assertNotEqual(seeds.H(1, 23), seeds.H(12, 3))  # the separator keeps parts apart

    def test_non_integer_or_string_parts_are_refused(self):
        for bad in ((1.5,), (True,), (None,), ()):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                seeds.H(*bad)


OBS = [{"name": "x", "source_column": "x", "bins": {"lo": 0.0, "hi": 1.0, "width": 0.1}, "thresholds": [0.5]},
       {"name": "x_sel", "source_column": "x", "selection": [{"column": "fate", "op": "==", "value": 1}],
        "bins": {"lo": 0.0, "hi": 1.0, "width": 0.1}}]


def events(n, seed=1, first=0):
    rng = random.Random(seed)
    return [{"event": first + i, "x": rng.uniform(-0.2, 1.2), "fate": rng.choice([0, 1])} for i in range(n)]


class Summary(unittest.TestCase):
    def test_blocks_selection_overflow_and_sums(self):
        rows = events(170)
        s = S.build(rows, OBS, block_size=10, blocks=16)
        self.assertEqual((s["run"]["events_in_blocks"], s["run"]["events_ignored"]), (160, 10))
        x, xs = S.observable(s, "x"), S.observable(s, "x_sel")
        for b in range(16):
            mine = [r for r in rows if r["event"] // 10 == b]
            blk, sel = x["blocks"][b], xs["blocks"][b]
            self.assertEqual((blk["events"], blk["n"]), (10, 10))
            self.assertEqual(sel["n"], sum(r["fate"] == 1 for r in mine))
            self.assertAlmostEqual(blk["sum"], math.fsum(r["x"] for r in mine), places=12)
            self.assertAlmostEqual(blk["sumsq"], math.fsum(r["x"] ** 2 for r in mine), places=12)
            self.assertEqual(blk["underflow"], sum(r["x"] < 0 for r in mine))
            self.assertEqual(blk["overflow"], sum(r["x"] >= 1.0 for r in mine))
            self.assertEqual(sum(blk["hist"]) + blk["underflow"] + blk["overflow"], 10)
            self.assertEqual(blk["count_if"], [sum(r["x"] > 0.5 for r in mine)])
            self.assertEqual((blk["min"], blk["max"]), (min(r["x"] for r in mine), max(r["x"] for r in mine)))

    def test_jobs_merge_to_the_single_run(self):
        rows = events(160)
        whole = S.build(rows, OBS, 10, 16)
        parts = [S.build(rows[:73], OBS, 10, 16), S.build(rows[73:], OBS, 10, 16)]
        merged = S.merge(parts)
        for o_w, o_m in zip(whole["observables"], merged["observables"]):
            for bw, bm in zip(o_w["blocks"], o_m["blocks"]):
                for k in ("events", "n", "hist", "underflow", "overflow", "count_if", "min", "max"):
                    self.assertEqual(bw[k], bm[k], k)
                self.assertAlmostEqual(bw["sum"], bm["sum"], places=12)

    def test_the_summary_schema(self):
        from contracts.schema import validate
        self.assertTrue(validate(S.build(events(40), OBS, 10, 4), "simulation_summary.json").ok)
        self.assertTrue(validate(OBS, "simulation_observables.json").ok)
        self.assertFalse(validate([dict(OBS[0], bins={"lo": 0, "hi": 1})], "simulation_observables.json").ok)

    def test_neumaier_keeps_small_terms(self):
        acc = S.Neumaier()
        for x in [1e16, 1.0, -1e16] * 1000:
            acc.add(x)
        self.assertEqual(acc.value, 1000.0)


class BatchMeans(unittest.TestCase):
    def test_mean_se_and_covariance(self):
        th = [1.0, 2.0, 4.0, 3.0]
        r = M.batch_mean(th)
        self.assertEqual((r["value"], r["dof"]), (2.5, 3))
        self.assertAlmostEqual(r["se"], statistics.stdev(th) / 2.0)
        cov = M.covariance([[1, 2], [2, 4], [4, 8], [3, 6]])
        self.assertAlmostEqual(cov[0][0], r["se"] ** 2)
        self.assertAlmostEqual(cov[0][1], 2 * r["se"] ** 2)

    def test_statistical_uncertainty_is_the_68_percent_t_halfwidth(self):
        self.assertAlmostEqual(M.t_halfwidth(1.0, 15), 1.0345, delta=1e-3)  # A1.6: about 1.03 SE at K = 16

    def test_histogram_quantile_closed_form(self):
        counts = [10, 30, 40, 20]  # bins of width 0.5 from 1.0: the median (50th of 100) is 10/40 into [2.0, 2.5)
        self.assertAlmostEqual(M.hist_quantile(counts, 1.0, 0.5, 0.5)["value"], 2.0 + 0.5 * (50 - 40) / 40)
        self.assertEqual(M.hist_quantile(counts, 1.0, 0.5, 0.05, underflow=10)["reason"], "quantile-in-underflow")
        self.assertEqual(M.hist_quantile(counts, 1.0, 0.5, 0.99, overflow=10)["reason"], "quantile-in-overflow")

    def test_block_mode_is_the_parabola_vertex(self):
        for vertex in (3.2, 3.5, 3.8, 4.4):  # y = 100 - (x - vertex)^2 at the bin centres x = k + 0.5
            counts = [100 - (k + 0.5 - vertex) ** 2 for k in range(8)]
            self.assertAlmostEqual(M.block_mode(counts, 0.0, 1.0)["value"], vertex, places=9)
        self.assertTrue(M.block_mode([5, 3, 1], 0.0, 1.0)["fallback"])  # fullest bin at the edge
        self.assertEqual(M.block_mode([1, 5, 5, 1], 0.0, 1.0)["value"], 2.0)  # tie: lowest index, flat top -> vertex

    def test_mpv_falls_back_and_flags(self):
        hists = [[1, 5, 3]] * 12 + [[5, 3, 1]] * 4
        self.assertEqual(M.mpv(hists, 0.0, 1.0)["status"], "ok")
        self.assertEqual(M.mpv([[1, 5, 3]] * 11 + [[5, 3, 1]] * 5, 0.0, 1.0)["status"], "incomplete")

    def test_exact_intervals_reuse_the_existing_ones(self):
        from core.stats.poisson_diagnostics import central_interval
        from core.stats.tail_estimation import clopper_pearson
        self.assertEqual(M.exact_proportion(3, 40, 0.9), clopper_pearson(3, 40, 0.9))
        g = central_interval(7, 0.9)
        self.assertEqual(M.exact_count(7, 0.9), (g["lower"], g["upper"]))
        self.assertTrue(M.low_count([3, 0, 5]) and M.low_count([30, 30, 30]) and not M.low_count([40, 40, 40]))

    def test_rate_ratio_interval_against_scipy(self):
        from scipy import stats
        n1, n2, cl = 30, 50, 0.9
        lo, hi = M.rate_ratio_interval(n1, n2, cl)
        plo, phi = stats.beta.ppf(0.05, n1, n2 + 1), stats.beta.ppf(0.95, n1 + 1, n2)
        self.assertAlmostEqual(lo, plo / (1 - plo), places=8)
        self.assertAlmostEqual(hi, phi / (1 - phi), places=8)


class Decisions(unittest.TestCase):
    def test_equivalence_truth_table(self):
        tol, nu = 0.02, 30
        t95, tm = T.t_ppf(0.95, nu), T.t_ppf(1 - 0.05 / 3, nu)
        se = 0.004
        cases = [(0.0, True, "pass"), (tol - t95 * se - 1e-6, True, "pass"), (tol - t95 * se + 1e-6, True, "unresolved"),
                 (0.0, False, "unresolved"), (tol + tm * se + 1e-6, True, "fail"), (tol + tm * se + 1e-6, False, "fail"),
                 (tol + tm * se - 1e-6, True, "unresolved")]
        for diff, met, verdict in cases:
            for sign in (1, -1):
                with self.subTest(diff=sign * diff, met=met):
                    r = D.equivalence(sign * diff, se, nu, tol, m=3, targets_met=met)
                    self.assertEqual(r["verdict"], verdict)
                    self.assertIn(r["reason"], D.REASONS)

    def test_interval_branch(self):
        self.assertEqual(D.equivalence(None, None, None, 0.1, interval90=(-0.05, 0.08))["verdict"], "pass")
        self.assertEqual(D.equivalence(None, None, None, 0.1, interval90=(0.12, 0.3), interval_m=(0.11, 0.4))["verdict"],
                         "fail")
        self.assertEqual(D.equivalence(None, None, None, 0.1, interval90=(0.05, 0.3))["verdict"], "unresolved")

    def test_welch_and_detection_limit(self):
        self.assertAlmostEqual(D.welch_dof(1.0, 15, 1.0, 15), 30.0)
        self.assertAlmostEqual(D.welch_dof(1.0, 15, math.sqrt(2), 15), 27.0, delta=0.05)  # A Appendix B: 27 at ratio 2
        dl = D.detection_limit(0.05, -0.01, 0.004, 30)["value"]
        self.assertAlmostEqual(dl, 0.05 + 0.01 + T.t_ppf(0.977, 30) * 0.004)


class CoreOnlyUsage(unittest.TestCase):
    def test_an_adapter_style_caller_imports_only_core(self):
        """Reads a summary, computes block estimators and calls equivalence, importing nothing but core."""
        code = ("import sys; sys.path.insert(0, %r)\n"
                "from core.simulation import summary as S\nfrom core.stats import batch_means as M, decisions as D\n"
                "import random\nrng = random.Random(3)\n"
                "obs = [{'name': 'x', 'source_column': 'x', 'bins': {'lo': 0, 'hi': 1, 'width': 0.05}}]\n"
                "a = S.build([{'event': i, 'x': rng.random()} for i in range(1600)], obs, 100, 16)\n"
                "b = S.build([{'event': i, 'x': rng.random()} for i in range(1600)], obs, 100, 16)\n"
                "ra = M.batch_mean(S.block_means(S.observable(a, 'x')))\n"
                "rb = M.batch_mean(S.block_means(S.observable(b, 'x')))\n"
                "d, se = D.difference(ra['value'], ra['se'], rb['value'], rb['se'])\n"
                "print(D.equivalence(d, se, D.welch_dof(ra['se'], 15, rb['se'], 15), 0.2)['verdict'])\n"
                "print(sorted(m for m in sys.modules if m.split('.')[0] in ('contracts', 'skills', 'adapters')))\n"
                % str(PLUGIN))
        p = subprocess.run([sys.executable, "-I", "-B", "-c", code], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        verdict, mods = p.stdout.splitlines()
        self.assertEqual((verdict, json.loads(mods.replace("'", '"'))), ("pass", []))


if __name__ == "__main__":
    unittest.main()
