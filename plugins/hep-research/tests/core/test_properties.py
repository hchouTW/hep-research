"""Property-based tests (T08), with hypothesis, an optional test-only dependency: the module is skipped without it.

Invariants: upper limits are non-decreasing in n and non-increasing in b; intervals are nested in the confidence
level; covariance tools give the same verdict when the matrix is scaled by 1e-12 or 1e12; a GLS fit does not depend
on the order of its inputs; a partitioned merge does not depend on the chunking or on the order chunks finish; and
the validators never raise on arbitrary JSON. Runs are derandomized, so a failure reproduces.
Run from the plugin root with `python3 -m unittest discover -s tests -t .`.
"""
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
    HAVE = True
except ImportError:  # pragma: no cover - the skip below reports it
    HAVE = False

from contracts.comparison import gate as gate_mod  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.evidence.ledger import check_ledger  # noqa: E402
from core.partition import engine  # noqa: E402
from core.stats import poisson_diagnostics as pd  # noqa: E402
from core.stats import statistical_toys as toys  # noqa: E402
from core.stats._linalg import cholesky  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

SKIP = "hypothesis not installed (test-only dependency: pip install hypothesis)"


def fast(n=40):
    return settings(max_examples=n, deadline=None, derandomize=True, database=None,  # no .hypothesis/ folder
                    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])


if HAVE:
    counts = st.integers(min_value=0, max_value=30)
    backgrounds = st.floats(min_value=0.0, max_value=12.0, allow_nan=False)
    levels = st.sampled_from([0.6827, 0.80, 0.90, 0.95, 0.99])
    json_values = st.recursive(
        st.none() | st.booleans() | st.integers(-10**6, 10**6) | st.floats(allow_nan=True, allow_infinity=True) | st.text(max_size=8),
        lambda kids: st.lists(kids, max_size=4) | st.dictionaries(st.text(max_size=12), kids, max_size=5), max_leaves=25)

    @st.composite
    def pd_matrices(draw, max_n=6):
        n = draw(st.integers(min_value=1, max_value=max_n))
        a = [[draw(st.floats(-3, 3, allow_nan=False)) for _ in range(n)] for _ in range(n)]
        return [[sum(a[i][k] * a[j][k] for k in range(n)) + (1.0 if i == j else 0.0) for j in range(n)] for i in range(n)]
else:  # keep the decorators below importable without hypothesis; the classes are skipped
    class _Placeholder:
        def __getattr__(self, _name):
            return lambda *_a, **_k: None

    st = _Placeholder()

    def given(*_a, **_k):
        return lambda f: f

    def fast(n=40):
        return lambda f: f
    counts = backgrounds = levels = json_values = None

    def pd_matrices():
        return None


@unittest.skipUnless(HAVE, SKIP)
class LimitProperties(unittest.TestCase):
    @fast(60)
    @given(counts, backgrounds, levels)
    def test_classical_upper_limit_monotone(self, n, b, cl):
        a, more_n, more_b = pd.upper_limit(n, b, cl), pd.upper_limit(n + 1, b, cl), pd.upper_limit(n, b + 0.5, cl)
        self.assertGreaterEqual(more_n["upper_limit_on_total_mean"], a["upper_limit_on_total_mean"] - 1e-9)
        s, s_b = a["upper_limit_on_signal"], more_b["upper_limit_on_signal"]
        if s is not None and s_b is not None:
            self.assertLessEqual(s_b, s + 1e-9)

    @fast(8)
    @given(st.integers(0, 6), st.floats(0.0, 4.0, allow_nan=False), st.sampled_from([0.90, 0.95]))
    def test_feldman_cousins_upper_end_monotone(self, n, b, cl):
        """Non-decreasing in n and non-increasing in b, within one grid step (the stated accuracy)."""
        step = 0.01
        here = pd.fc_interval(n, b, cl, step)["upper"]
        self.assertGreaterEqual(pd.fc_interval(n + 1, b, cl, step)["upper"], here - step)
        self.assertLessEqual(pd.fc_interval(n, b + 0.37, cl, step)["upper"], here + step)

    @fast(60)
    @given(counts, levels, levels)
    def test_garwood_intervals_nested_in_cl(self, n, cl1, cl2):
        lo_cl, hi_cl = sorted((cl1, cl2))
        a, b = pd.central_interval(n, lo_cl), pd.central_interval(n, hi_cl)
        self.assertLessEqual(b["lower"], a["lower"] + 1e-9)
        self.assertGreaterEqual(b["upper"], a["upper"] - 1e-9)

    @fast(6)
    @given(st.integers(0, 6), st.floats(0.0, 3.0, allow_nan=False))
    def test_feldman_cousins_nested_in_cl(self, n, b):
        a, c = pd.fc_interval(n, b, 0.90, 0.01), pd.fc_interval(n, b, 0.95, 0.01)
        self.assertLessEqual(c["lower"], a["lower"] + 0.01)
        self.assertGreaterEqual(c["upper"], a["upper"] - 0.01)


@unittest.skipUnless(HAVE, SKIP)
class CovarianceProperties(unittest.TestCase):
    @fast(50)
    @given(pd_matrices(), st.sampled_from([1e-12, 1e12]))
    def test_cholesky_scales_with_the_matrix(self, c, k):
        l, _ = cholesky(c, "c")
        lk, _ = cholesky([[v * k for v in row] for row in c], "c")
        for i in range(len(c)):
            for j in range(i + 1):
                self.assertAlmostEqual(lk[i][j] / math.sqrt(k), l[i][j], delta=1e-9 * max(1.0, abs(l[i][j])))

    @fast(40)
    @given(pd_matrices(), st.sampled_from([1e-12, 1e12]))
    def test_validator_verdict_does_not_depend_on_units(self, c, k):
        doc = lambda m: {"kind": "absolute", "units": "x^2", "labels": [f"b{i}" for i in range(len(m))], "matrix": m}  # noqa: E731
        a, b = validate_covariance(doc(c)), validate_covariance(doc([[v * k for v in row] for row in c]))
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(sorted(e["code"] for e in a["errors"]), sorted(e["code"] for e in b["errors"]))

    @fast(50)
    @given(pd_matrices(), st.randoms(use_true_random=False))
    def test_gls_does_not_depend_on_input_order(self, c, rnd):
        n = len(c)
        r = [1.0 + 0.1 * rnd.uniform(-1, 1) for _ in range(n)]
        perm = list(range(n))
        rnd.shuffle(perm)
        a = toys._gls_constant(r, c)
        b = toys._gls_constant([r[p] for p in perm], [[c[p][q] for q in perm] for p in perm])
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=1e-9 * max(1.0, abs(x)))


@unittest.skipUnless(HAVE, SKIP)
class PartitionProperties(unittest.TestCase):
    @fast(25)
    @given(st.integers(1, 60), st.integers(1, 25), st.integers(0, 2**31 - 1))
    def test_merge_independent_of_chunking_and_finish_order(self, n_items, chunk_size, seed):
        def worker(ch):  # an integer histogram: summation is exact, so results must match exactly
            hist = [0] * 4
            for i in range(ch["start"], ch["stop"]):
                hist[(i * 7 + seed) % 4] += 1
            return {"hist": hist, "n": ch["stop"] - ch["start"]}

        rng = random.Random(seed)
        with tempfile.TemporaryDirectory() as td:
            single = engine.merge(*self._run(Path(td) / "one", n_items, n_items, worker))
            manifest, state = self._run(Path(td) / "many", n_items, chunk_size, worker, rng)
            many = engine.merge(manifest, state)
        self.assertEqual(single["status"], "complete")
        self.assertEqual(many["status"], "complete", many["problems"])
        self.assertEqual(single["merged"], many["merged"])
        self.assertEqual(many["merged"]["n"], n_items)

    @staticmethod
    def _run(state, n_items, chunk_size, worker, rng=None):
        manifest = engine.make_manifest("prop", n_items, chunk_size, 1)
        if rng is None:
            engine.run(manifest, state, worker)
            return manifest, state
        pending = {c["id"] for c in manifest["chunks"]}
        while pending:  # chunks finish in a random order: the others fail and are retried in a later pass
            done_now = set(rng.sample(sorted(pending), max(1, len(pending) // 2)))

            def flaky(ch):
                if ch["id"] not in done_now:
                    raise RuntimeError("not this pass")
                return worker(ch)
            engine.run(manifest, state, flaky)
            engine.reset(state, sorted(pending - done_now), "property test: next pass")
            pending -= done_now
        return manifest, state


@unittest.skipUnless(HAVE, SKIP)
class ValidatorsNeverRaise(unittest.TestCase):
    @fast(150)
    @given(json_values, json_values, json_values)
    def test_contracts_and_gate(self, a, b, plan):
        validate_artifact(a)
        gate_mod.check(a, b, plan)

    @fast(150)
    @given(json_values, json_values)
    def test_ledger(self, sources, claims):
        check_ledger(sources, claims)

    @fast(150)
    @given(json_values)
    def test_covariance_and_response_validators(self, doc):
        validate_covariance(doc)
        validate_response(doc)


if __name__ == "__main__":
    unittest.main()
