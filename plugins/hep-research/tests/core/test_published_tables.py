"""Regression against published tables (T07). Each reference is transcribed by script into tests/core/fixtures/ with
its source, and the tolerance is the printed precision of the table unless stated.

- Feldman and Cousins, Phys. Rev. D 57 (1998) 3873, arXiv:physics/9711021: Table IV (90% CL) and Table VI (95% CL),
  n0 = 0..10, b = 0..5 (fixtures/fc1998_tables.json). Slow tier (about 6 minutes); within 0.01 as the order asks.
- Particle Data Group, Review of Particle Physics 2024, Statistics review, Table 40.3 (one-sided Poisson limits with no
  background, which are the ends of Garwood central intervals at 80% and 90% CL) and Table 40.4 (unified intervals
  with no background) (fixtures/pdg2024_poisson_tables.json).
- Li and Ma, ApJ 272 (1983) 317, eq. 17. The paper prints no table of values (its results are figures), so eq. 17 is
  checked against an independent transcription of the printed formula and its exact limits, not against numbers.
Run from the plugin root with `python3 -m unittest discover -s tests -t .`; HEP_SLOW_TESTS=1 adds the slow tier.
"""
import json
import math
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))
from core.stats import poisson_diagnostics as pd  # noqa: E402
import li_ma_significance as lm  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
SLOW = os.environ.get("HEP_SLOW_TESTS") == "1"
PDG = json.loads((FIX / "pdg2024_poisson_tables.json").read_text())
FC = json.loads((FIX / "fc1998_tables.json").read_text())["tables"]


def printed_tolerance(text: str) -> float:
    """Half a unit in the last printed digit, plus a little for the bisection."""
    decimals = len(text.split(".")[1]) if "." in text else 0
    return 0.5 * 10.0 ** -decimals + 1e-9


class PdgPoissonLimitTests(unittest.TestCase):
    def test_one_sided_upper_limits_table_40_3(self):
        for n, _, up90, _, up95 in PDG["table_40_3"]["rows"]:
            for cl, text in ((0.90, up90), (0.95, up95)):
                ul = pd.upper_limit(n, 0.0, cl)["upper_limit_on_total_mean"]
                self.assertAlmostEqual(ul, float(text), delta=printed_tolerance(text), msg=(n, cl))

    def test_one_sided_lower_limits_are_garwood_ends_table_40_3(self):
        for n, lo90, _, lo95, _ in PDG["table_40_3"]["rows"]:
            for central_cl, text in ((0.80, lo90), (0.90, lo95)):
                lower = pd.central_interval(n, central_cl)["lower"]
                if text is None:
                    self.assertEqual(lower, 0.0, msg=n)
                else:
                    self.assertAlmostEqual(lower, float(text), delta=printed_tolerance(text), msg=(n, central_cl))

    def test_pdg_unified_intervals_match_the_fc_fixture(self):
        """Two transcriptions of the same published numbers (PDG 40.4 is the b = 0 column of FC IV and VI)."""
        by_cl = {t["cl"]: t for t in FC}
        for n, mu1_90, mu2_90, mu1_95, mu2_95 in PDG["table_40_4"]["rows"]:
            for cl, lo, hi in ((0.90, mu1_90, mu2_90), (0.95, mu1_95, mu2_95)):
                fc_lo, fc_hi, _ = by_cl[cl]["rows"][str(n)][0]
                self.assertEqual((fc_lo, fc_hi), (float(lo), float(hi)), msg=(n, cl))

    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_unified_intervals_table_40_4(self):
        for n, mu1_90, mu2_90, mu1_95, mu2_95 in PDG["table_40_4"]["rows"]:
            for cl, lo, hi in ((0.90, mu1_90, mu2_90), (0.95, mu1_95, mu2_95)):
                iv = pd.fc_interval(n, 0.0, cl)
                self.assertAlmostEqual(iv["lower"], float(lo), delta=0.01, msg=(n, cl))
                self.assertAlmostEqual(iv["upper"], float(hi), delta=0.01, msg=(n, cl))


class FeldmanCousinsTableTests(unittest.TestCase):
    @unittest.skipUnless(SLOW, "slow: set HEP_SLOW_TESTS=1")
    def test_tables_iv_and_vi(self):
        """Every n0 = 0 to 10, b = 0 to 5 entry of Tables IV and VI within 0.01, lower and upper ends."""
        for table in FC:
            for n0 in range(0, 11):
                for b, (lo, hi, _italic) in zip(table["b"], table["rows"][str(n0)]):
                    iv = pd.fc_interval(n0, b, table["cl"])
                    msg = (table["table"], n0, b)
                    self.assertAlmostEqual(iv["lower"], lo, delta=0.01, msg=msg)
                    self.assertAlmostEqual(iv["upper"], hi, delta=0.01, msg=msg)


def li_ma_eq17(n_on: int, n_off: int, alpha: float) -> float:
    """Li & Ma (1983) eq. 17, written from the printed formula:
    S = sqrt(2) { N_on ln[((1 + a) / a) (N_on / (N_on + N_off))] + N_off ln[(1 + a) (N_off / (N_on + N_off))] }^(1/2),
    with the sign of N_on - a N_off and 0 ln 0 = 0."""
    total = n_on + n_off
    first = n_on * math.log((1 + alpha) / alpha * n_on / total) if n_on else 0.0
    second = n_off * math.log((1 + alpha) * n_off / total) if n_off else 0.0
    return math.copysign(math.sqrt(2.0) * math.sqrt(max(first + second, 0.0)), n_on - alpha * n_off)


class LiMaTests(unittest.TestCase):
    def test_eq17_on_a_grid(self):
        for n_on in (0, 1, 3, 10, 25, 100, 1000):
            for n_off in (0, 1, 5, 40, 200, 3000):
                for alpha in (0.05, 0.2, 1.0, 3.0):
                    if n_on + n_off == 0:
                        continue
                    got = lm.li_ma_significance(n_on, n_off, alpha)["significance"]
                    self.assertAlmostEqual(got, li_ma_eq17(n_on, n_off, alpha), delta=1e-9, msg=(n_on, n_off, alpha))

    def test_exact_limits(self):
        self.assertEqual(lm.li_ma_significance(20, 40, 0.5)["significance"], 0.0)  # N_on = alpha N_off
        # no OFF counts: S = sqrt(2 N_on ln((1 + a) / a))
        self.assertAlmostEqual(lm.li_ma_significance(9, 0, 0.25)["significance"], math.sqrt(18 * math.log(5.0)), places=12)


if __name__ == "__main__":
    unittest.main()
