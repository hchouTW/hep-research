"""S01 regressions for skills/hep-statistics/scripts/li_ma_significance.py and the Li & Ma passage of
astroparticle-statistics.md: the statistic is S = sqrt(-2 ln lambda) (no extra sqrt(2)), its normal reading is
asymptotic, and the script gives toy-calibrated and exact conditional p-values. All inputs are SYNTHETIC."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-statistics" / "scripts" / "li_ma_significance.py"
REF = PLUGIN / "skills" / "hep-statistics" / "references" / "astroparticle-statistics.md"
sys.path.insert(0, str(SCRIPT.parent))

import li_ma_significance as lm  # noqa: E402

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


def run(*args):
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def independent_toy_p(n_on, n_off, alpha, toys, seed):
    """Same model, different code path (NumPy generator, vectorized statistic)."""
    rng = np.random.default_rng(seed)
    b = (n_on + n_off) / (1.0 + alpha)
    on = rng.poisson(alpha * b, toys).astype(float)
    off = rng.poisson(b, toys).astype(float)
    tot = on + off
    with np.errstate(divide="ignore", invalid="ignore"):
        t_on = np.where(on > 0, on * np.log((1 + alpha) / alpha * on / tot), 0.0)
        t_off = np.where(off > 0, off * np.log((1 + alpha) * off / tot), 0.0)
    mag = np.sqrt(np.clip(2.0 * (t_on + t_off), 0.0, None))
    s = np.where(on - alpha * off > 0, mag, np.where(on - alpha * off < 0, -mag, 0.0))
    s_obs = lm.li_ma_significance(n_on, n_off, alpha)["significance"]
    k = int(np.sum(s >= s_obs - 1e-9))
    return k / toys, math.sqrt(max(k, 1) / toys * (1 - k / toys) / toys)


class ReferenceText(unittest.TestCase):
    def test_no_sqrt2_equivalence_and_no_low_count_validity_claim(self):
        text = " ".join(REF.read_text(encoding="utf-8").split())
        self.assertNotIn("sqrt(2) * sqrt(-2 ln(lambda))", text)
        self.assertNotIn("does not require large counts", text)
        self.assertIn("S = sqrt(-2 ln lambda)", text)
        self.assertIn("Wilks", text)

    def test_script_docstring(self):
        doc = " ".join(lm.__doc__.split())
        self.assertNotIn("remains valid at low counts", doc)
        self.assertIn("sqrt(-2 ln lambda)", doc)
        self.assertIn("--exact-conditional", doc)

    def test_stale_link_label_fixed(self):
        self.assertNotIn("[35, low-count", REF.read_text(encoding="utf-8"))

    def test_statistic_equals_sqrt_minus_two_log_lambda(self):
        n_on, n_off, a = 4, 2, 0.25
        b0 = (n_on + n_off) / (1 + a)                 # background-only fit
        ll0 = n_on * math.log(a * b0) - a * b0 + n_off * math.log(b0) - b0
        ll1 = n_on * math.log(n_on) - n_on + n_off * math.log(n_off) - n_off   # saturated: free signal
        self.assertAlmostEqual(lm.li_ma_significance(n_on, n_off, a)["significance"],
                               math.sqrt(-2 * (ll0 - ll1)), places=12)


class PValues(unittest.TestCase):
    def test_default_output_unchanged(self):
        code, out, _ = run("--on", "15", "--off", "5", "--alpha", "0.5")
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(list(d), ["method", "n_on", "n_off", "alpha", "excess", "significance", "on_term",
                                   "off_term", "caveat"])

    def test_exact_conditional(self):
        code, out, _ = run("--on", "4", "--off", "2", "--alpha", "0.25", "--exact-conditional")
        self.assertEqual(code, 0)
        rows = {r["method"]: r for r in json.loads(out)["p_values"]}
        self.assertAlmostEqual(rows["exact-conditional-binomial"]["p_value"], 0.01696, delta=1e-5)
        self.assertIn("conservative", rows["exact-conditional-binomial"]["label"])
        self.assertAlmostEqual(rows["asymptotic-wilks"]["p_value"], 6.646e-3, delta=1e-6)

    @unittest.skipUnless(HAVE_NP, "numpy not installed: independent toy check unverified")
    def test_toys_low_counts_against_independent_code(self):
        code, out, _ = run("--on", "4", "--off", "2", "--alpha", "0.25", "--toys", "200000", "--seed", "1")
        self.assertEqual(code, 0)
        d = json.loads(out)
        row = {r["method"]: r for r in d["p_values"]}["toys-plugin-background"]
        self.assertEqual((row["toys"], row["seed"]), (200000, 1))
        p_ind, se_ind = independent_toy_p(4, 2, 0.25, 200000, 7)
        se = math.hypot(row["mc_error"], se_ind)
        self.assertLess(abs(row["p_value"] - p_ind), 3 * se)
        # the asymptotic value undershoots at these counts; the toy value is the calibrated one
        self.assertGreater(row["p_value"], 1.2 * {r["method"]: r for r in d["p_values"]}["asymptotic-wilks"]["p_value"])

    def test_toys_large_counts_agree_with_asymptotic(self):
        # (30, 100, 0.2), S = 1.88: (the r1 point (50, 100, 0.2) has S = 4.97, beyond 2e5 toys)
        code, out, _ = run("--on", "30", "--off", "100", "--alpha", "0.2", "--toys", "200000", "--seed", "3")
        self.assertEqual(code, 0)
        rows = {r["method"]: r for r in json.loads(out)["p_values"]}
        toy, asym = rows["toys-plugin-background"], rows["asymptotic-wilks"]["p_value"]
        self.assertTrue(abs(toy["p_value"] - asym) < 3 * toy["mc_error"] or abs(toy["p_value"] / asym - 1) < 0.10,
                        (toy, asym))

    def test_zero_exceedances_give_a_bound(self):
        code, out, _ = run("--on", "30", "--off", "0", "--alpha", "0.1", "--toys", "1000", "--seed", "2")
        self.assertEqual(code, 0)
        row = {r["method"]: r for r in json.loads(out)["p_values"]}["toys-plugin-background"]
        self.assertEqual(row["exceedances"], 0)
        self.assertIsNone(row["p_value"])
        self.assertAlmostEqual(row["p_upper_95"], 1 - 0.05 ** (1 / 1000), places=12)

    def test_toys_need_a_seed(self):
        code, _, err = run("--on", "4", "--off", "2", "--alpha", "0.25", "--toys", "100")
        self.assertEqual(code, 2)
        self.assertIn("--seed", err)


if __name__ == "__main__":
    unittest.main()
