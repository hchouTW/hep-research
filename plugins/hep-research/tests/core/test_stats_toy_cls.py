"""T22: toy-based CLs for shape-limit. For one bin with a known background the toy CLs limit reproduces the exact
Poisson CLs limit; with a nuisance at large counts it agrees with the asymptotic CLs result; the expected limits come
from the same toys and are ordered. (A scan over 40 seeds with 1000 toys gave a mean of 5.412 +- 0.046 against the
exact 5.395 for n = 3, b = 3: no bias beyond toy noise.)"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats._poisson import cdf  # noqa: E402


def exact_cls(n, b, cl=0.95):
    lo, hi = 0.0, 60.0
    for _ in range(100):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if cdf(n, m + b) / cdf(n, b) > 1 - cl else (lo, m)
    return lo


class ToyClsTests(unittest.TestCase):
    def test_counting_matches_the_exact_cls_limit(self):
        # 3000 toys: the toy-noise standard deviation of the limit is about 0.17 here
        r = ll.shape_limit({"bins": [{"n": 3, "b": 3.0, "s": 1.0}]}, 0.95, 0, 5, 3000, 24)["toy_cls"]
        self.assertAlmostEqual(r["observed_upper_limit"], exact_cls(3, 3.0), delta=0.45)
        exp = [r["expected"][k] for k in ("-2sigma", "-1sigma", "median", "+1sigma", "+2sigma")]
        self.assertEqual(exp, sorted(exp))
        # the median background-only count is 3, so the median expected limit is the n = 3 limit (up to toy noise)
        self.assertAlmostEqual(r["expected"]["median"], exact_cls(3, 3.0), delta=0.6)

    def test_large_counts_with_a_nuisance_agree_with_the_asymptotic_cls(self):
        doc = {"bins": [{"n": 52, "b": 50.0, "s": 5.0}, {"n": 37, "b": 40.0, "s": 5.0}],
               "nuisances": [{"kind": "background_norm", "sigma": 0.1}]}
        r = ll.shape_limit(doc, 0.95, 0, 1, 300, 16)
        toy, asym = r["toy_cls"], r["asymptotic_expected_limits"]["cls"]
        self.assertLess(abs(toy["observed_upper_limit"] / r["asymptotic_observed_cls_upper_limit"] - 1), 0.12)
        self.assertLess(abs(toy["expected"]["median"] / asym["median"] - 1), 0.15)
        self.assertNotIn("not_reached", toy)

    def test_cli_and_input_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.json"
            path.write_text(json.dumps({"bins": [{"n": 2, "b": 2.0, "s": 1.0}]}))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = ll.main(["shape-limit", "--input", str(path), "--cls-toys", "200", "--cls-points", "8", "--seed", "3"])
        out = json.loads(buf.getvalue())
        self.assertEqual((code, out["status"]), (0, "ok"))
        self.assertEqual(len(out["toy_cls"]["grid"]), 8)
        with self.assertRaises(ll.LikelihoodError):
            ll.shape_limit({"bins": [{"n": 2, "b": 2.0, "s": 1.0}]}, 0.95, 0, 1, 200, 3)
        with self.assertRaises(ll.LikelihoodError):
            ll.shape_limit({"bins": [{"n": 2, "b": 2.0, "s": 1.0}]}, 0.95, 0, 1, 50, 16)


if __name__ == "__main__":
    unittest.main()
