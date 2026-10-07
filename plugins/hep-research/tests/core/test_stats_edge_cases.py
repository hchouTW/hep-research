"""Precision and edge cases for every public core/stats entry point (T10).

NaN, +inf and -inf in each numeric argument, and in each numeric leaf of a document input, and empty lists and empty
documents, must give the module's named error (a ValueError subclass), never another exception and never a result
that carries the bad value along. The validators report instead of raising: every such leaf must make them fail.
Also: p-values far below 1e-10, the mean limit, and zero or low counts in blinded bins.
Run from the plugin root with `python3 -m unittest discover -s tests -t .`.
"""
import copy
import json
import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.blinding import blinding as bl  # noqa: E402
from core.stats import _poisson  # noqa: E402
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import poisson_diagnostics as pd  # noqa: E402
from core.stats import statistical_toys as st  # noqa: E402
from core.stats import template_fit as tf  # noqa: E402
from core.stats import unfolding_diagnostics as ud  # noqa: E402
from core.stats.validate_covariance import validate_covariance  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from tests.contracts.mutations import _parent, paths  # noqa: E402
from tests.core.test_stats_likelihood_limits import SHAPE, doc as ll_doc  # noqa: E402
from tests.core.test_stats_statistical_toys import BKG, RESPONSE, SIG, RatioMeasuredTests  # noqa: E402
from tests.core.test_stats_template_fit import make_doc as tf_doc, make_weighted  # noqa: E402
from tests.core.test_stats_unfolding_diagnostics import make_doc as unf_doc, multinomial_cell_covariance  # noqa: E402

BAD = (float("nan"), float("inf"), -float("inf"))
FIX = ROOT / "tests" / "core" / "fixtures"

# (name, call, valid arguments, named error)
SCALAR = [
    ("central_interval", pd.central_interval, [3, 0.68], pd.DiagnosticsError),
    ("upper_limit", pd.upper_limit, [3, 1.0, 0.9], pd.DiagnosticsError),
    ("fc_interval", lambda *a: pd.fc_interval(*a, step=0.05), [2, 1.0, 0.9], pd.DiagnosticsError),
    ("cls_limit", pd.cls_limit, [2, 1.0, 0.95, 0.3, 10], pd.DiagnosticsError),
    ("coverage", pd.coverage, [2.0, 0.68, 100, 1], pd.DiagnosticsError),
    ("poisson_cdf", pd.poisson_cdf, [2, 1.5], pd.DiagnosticsError),
    ("poisson_sf", pd.poisson_sf, [2, 1.5], pd.DiagnosticsError),
    ("log_poisson_sf", pd.log_poisson_sf, [2, 1.5], pd.DiagnosticsError),
    ("profile_limit", ll.profile_limit, [5, 2.0, 0.5, 0.95, 100, 1], ll.LikelihoodError),
    ("profile_significance", ll.profile_significance, [8, 2.0, 0.5, 100, 1], ll.LikelihoodError),
    ("profile_cls", ll.profile_cls, [3, 2.0, 0.5, 0.95, 100, 100, 1], ll.LikelihoodError),
    ("profile_fc", ll.profile_fc, [3, 2.0, 0.5, 0.9, 100, 1], ll.LikelihoodError),
    ("neyman_limit", ll.neyman_limit, [3, 2.0, 0.5, 0.9, 0.05, 100, 1, 5], ll.LikelihoodError),
    ("neyman_coverage", ll.neyman_coverage, [2.0, 2.0, 0.5, 0.9, 0.05, 50, 50, 1, 5], ll.LikelihoodError),
    ("boundary", st.boundary, [5, 2.0, 100, 1], st.ToyError),
    ("chi2_sf", st.chi2_sf, [3.0, 2], st.ToyError),
    ("ratio_toys", st.ratio_toys, [100.0, 80.0, [], 100, 1], st.ToyError),
    ("template_stat", st.template_stat, [SIG, BKG, 100, 0.5, 50, 50, 100, 1], st.ToyError),
    ("template_bb", st.template_bb, [SIG, BKG, 100, 0.5, 50, 50, 100, 1], st.ToyError),
    ("poisson_draw", lambda mu: st.poisson_draw(random.Random(1), mu), [3.0], st.ToyError),
]
# outcomes that are correct although no error is raised: the bad value is mathematically meaningful
SCALAR_ALLOWED = {("chi2_sf", 0, "inf"): 0.0}


def response_doc():
    d = unf_doc(gen=3000)
    d["response_covariance"] = multinomial_cell_covariance(d)
    return d


# (name, call on a document, valid document, named error, fields the call does not read or may be empty)
DOCS = [
    ("multibin_limit", lambda d: ll.multibin_limit(d, 0.95, 100, 1),
     ll_doc("independent", [0.3, 0.3], [{"n": 5, "b": 2.0, "s": 1.0}, {"n": 3, "b": 2.0, "s": 1.0}]), ll.LikelihoodError, ()),
    ("shape_limit", lambda d: ll.shape_limit(d, 0.95, 0, 1), SHAPE, ll.LikelihoodError, ("nuisances",)),
    ("ratio_cov", lambda d: st.ratio_cov(d, 100, 1),
     {"numerator": [400.0, 300.0], "denominator": [800.0, 600.0],
      "systematics": [{"name": "x", "sigma_num": 0.03, "sigma_den": 0.0, "num_den_rho": 0.0,
                       "bin_correlation": {"kind": "exponential", "length": 1.5}}]}, st.ToyError, ("systematics",)),
    ("ratio_measured", lambda d: st.ratio_measured(d, 100, 1), RatioMeasuredTests.doc(), st.ToyError, ()),
    ("unfold_scan", lambda d: st.unfold_scan(d, 100, 1), RESPONSE, st.ToyError, ()),
    ("closure", lambda d: ud.closure(d, "tikhonov", 1e-3, 50, 1), unf_doc(), ud.ToyError,
     ("truth_edges", "model", "mc_events_per_truth_bin")),  # read by fold-compare and response-stat
    ("response_measured", lambda d: ud.response_measured(d, "tikhonov", 1e-3), response_doc(), ud.ToyError,
     ("truth_edges", "mc_events_per_truth_bin", "test_truth", "model")),
    ("bb_fit", tf.bb_fit, tf_doc(), st.ToyError, ("true_yields",)),  # read by bb_toys, which rejects non-finite values
    ("wbb_fit", tf.wbb_fit, make_weighted(), st.ToyError, ("nuisances", "true_yields")),  # true_yields: toys only
]


def nonfinite(x) -> bool:
    if isinstance(x, float):
        return not math.isfinite(x)
    if isinstance(x, dict):
        return any(nonfinite(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return any(nonfinite(v) for v in x)
    return False


def numeric_leaves(doc):
    return [p for p in paths(doc) if isinstance(_parent(doc, p)[p[-1]], (int, float)) and not isinstance(_parent(doc, p)[p[-1]], bool)]


class NonFiniteAndEmptyInputs(unittest.TestCase):
    def test_every_baseline_is_valid(self):
        """Otherwise the error cases below could raise for the wrong reason."""
        for name, call, base, _ in SCALAR:
            with self.subTest(call=name):
                self.assertFalse(nonfinite(call(*base)) and name != "poisson_draw")
        for name, call, base, _, _ in DOCS:
            with self.subTest(call=name):
                call(copy.deepcopy(base))

    def test_scalar_arguments(self):
        for name, call, base, error in SCALAR:
            for i, v in enumerate(base):
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    continue
                for bad in BAD:
                    args = list(base)
                    args[i] = bad
                    with self.subTest(call=name, arg=i, value=bad):
                        allowed = SCALAR_ALLOWED.get((name, i, str(bad)), "raise")
                        if allowed == "raise":
                            with self.assertRaises(error):
                                call(*args)
                        else:
                            self.assertEqual(call(*args), allowed)

    def test_document_leaves_and_empty_lists(self):
        for name, call, base, error, optional in DOCS:
            leaves = [p for p in numeric_leaves(base) if p[0] not in optional]
            random.Random(1).shuffle(leaves)
            lists = [p for p in paths(base) if isinstance(_parent(base, p)[p[-1]], list) and p[0] not in optional]
            cases = [(p, bad) for p in leaves[:25] for bad in BAD] + [(p, []) for p in lists[:15]] + [((), {})]
            for path, bad in cases:
                doc = copy.deepcopy(base)
                if path:
                    _parent(doc, path)[path[-1]] = bad
                else:
                    doc = {}
                with self.subTest(call=name, at=".".join(map(str, path)) or "document", value=bad):
                    with self.assertRaises(error):
                        call(doc)

    def test_validators_fail_on_every_nonfinite_leaf(self):
        for name, call, fixture in (("validate_covariance", validate_covariance, "cov_valid.json"),
                                    ("validate_response", validate_response, "response_valid.json")):
            base = json.loads((FIX / fixture).read_text())
            self.assertEqual(call(base)["status"] in ("pass", "warn"), True, name)
            for path in numeric_leaves(base):
                for bad in BAD:
                    doc = copy.deepcopy(base)
                    _parent(doc, path)[path[-1]] = bad
                    with self.subTest(call=name, at=".".join(map(str, path)), value=bad):
                        self.assertEqual(call(doc)["status"], "fail")
            for empty in ({}, [], None, "x"):
                self.assertEqual(call(empty)["status"], "fail", (name, empty))

    def test_z_from_log_p_edges(self):
        self.assertEqual(pd.z_from_log_p(-math.inf), math.inf)
        self.assertIsNone(pd.z_from_log_p(0.0))
        for bad in (float("nan"), 0.5, math.inf, "x"):
            with self.assertRaises(pd.DiagnosticsError):
                pd.z_from_log_p(bad)

    def test_chi2_sf_edges(self):
        self.assertEqual(st.chi2_sf(math.inf, 3), 0.0)
        self.assertEqual(st.chi2_sf(0.0, 3), 1.0)
        for args in ((float("nan"), 2), (-1.0, 2), (-math.inf, 2), (3.0, 0), (3.0, 2.5), (3.0, True)):
            with self.assertRaises(st.ToyError):
                st.chi2_sf(*args)


class TinyPValues(unittest.TestCase):
    def test_p_values_far_below_1e_10(self):
        for n, b in ((30, 2.0), (60, 5.0), (120, 3.0), (400, 1.0)):
            lp = pd.log_poisson_sf(n, b)
            self.assertLess(lp, math.log(1e-10))
            sig = ll.profile_significance(n, b, 0.0, 100, 1)
            self.assertAlmostEqual(sig["log_p_value_exact_poisson"], lp, places=9)
            self.assertTrue(math.isfinite(sig["significance_exact_poisson_z"]))
            if lp > -745:
                self.assertGreater(sig["p_value_exact_poisson"], 0.0)
        self.assertGreater(pd.z_from_log_p(pd.log_poisson_sf(400, 1.0)), 30.0)

    def test_tail_continuity_across_the_summation_switch(self):
        """The tail switches from 1 - cdf to an upward sum at n - 1 = mu: no jump there."""
        for mu in (3.0, 47.0, 480.0, 5e4):
            k = int(mu) + 1
            a, b = _poisson.log_sf(k, mu), _poisson.log_sf(k + 1, mu)
            direct = math.log(math.exp(a) - math.exp(_poisson.log_pmf(k, mu)))
            self.assertAlmostEqual(b, direct, delta=1e-10, msg=mu)


class MeanLimitBoundaries(unittest.TestCase):
    def test_the_limit_itself_is_accepted_and_beyond_is_rejected(self):
        m = _poisson.MAX_MEAN
        self.assertTrue(0.0 < pd.poisson_cdf(int(m), m) < 1.0)
        for call in (lambda: pd.poisson_cdf(3, m * (1 + 1e-12)), lambda: pd.upper_limit(3, m * 1.01),
                     lambda: pd.coverage(m * 1.01, 0.68, 100, 1)):
            with self.assertRaises(pd.DiagnosticsError):
                call()
        with self.assertRaises(st.ToyError):
            st.poisson_draw(random.Random(1), m * 1.01)

    def test_limits_near_the_top_fail_rather_than_clip(self):
        n = int(_poisson.MAX_MEAN) - 100
        with self.assertRaises(pd.SolveFailed):
            pd.upper_limit(n, 0.0, 0.95)
        iv = pd.central_interval(n - 3000)
        self.assertLess(iv["upper"], _poisson.MAX_MEAN)


class BlindedLowCounts(unittest.TestCase):
    EDGES = [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_zero_and_low_count_blinded_bins(self):
        sealed = bl.seal(self.EDGES, [12.0, 0.0, 3.0, 40.0], {"variable": "x", "low": 1.0, "high": 3.0})
        self.assertIn(0.0, sealed)
        self.assertIn(3.0, sealed)
        quiet = "run_0 step 3/10 v0.3 2026-03-01 seed=1234567\n"
        self.assertEqual(bl.scan_text(quiet, sealed), [])
        hits = bl.scan_text("blinded bin 2 count 3\nbin 1: 0 events\n", sealed)
        self.assertEqual(sorted(h["sealed_value"] for h in hits), [0.0, 3.0])
        self.assertTrue(all(h.get("weak") for h in hits))

    def test_logs_in_three_encodings(self):
        import tempfile
        sealed = [1234.567]
        with tempfile.TemporaryDirectory() as td:
            for name, enc in (("u8.log", "utf-8"), ("u16.log", "utf-16"), ("l1.log", "latin-1")):
                (Path(td) / name).write_bytes(f"résultat 1234.567\n".encode(enc))
            rep = bl.scan_paths([td], sealed)
        self.assertEqual(sorted(Path(h["file"]).name for h in rep["leaks"]), ["l1.log", "u16.log", "u8.log"])


if __name__ == "__main__":
    unittest.main()
