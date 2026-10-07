"""Tests for skills/hep-analysis/scripts/counting_reference.py (T11): analytic cases (moved from the detector-response
tests), the flat-prior bound at b = 0 against PDG 2024 Table 40.3 (it equals the classical upper limit there), the
tail against core/stats, and the command line."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills" / "hep-analysis" / "scripts" / "counting_reference.py"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT.parent))
from counting_reference import bayesian_upper, poisson_upper_tail  # noqa: E402
from core.stats import poisson_diagnostics as pd  # noqa: E402

PDG = json.loads((ROOT / "tests" / "core" / "fixtures" / "pdg2024_poisson_tables.json").read_text())


class CountingTests(unittest.TestCase):
    def test_zero_count_analytic(self):
        for b in (0, 3, 100, 500):
            self.assertAlmostEqual(bayesian_upper(0, b), -math.log(.05), places=10)

    def test_one_count_known_bound(self):
        self.assertAlmostEqual(bayesian_upper(1, 0), 4.743864518390578, places=10)

    def test_tail_exact_cases(self):
        self.assertEqual(poisson_upper_tail(0, 0), 1)
        self.assertEqual(poisson_upper_tail(2, 0), 0)
        self.assertAlmostEqual(poisson_upper_tail(1, 2), 1-math.exp(-2), places=14)
        self.assertAlmostEqual(poisson_upper_tail(2, 2), 1-3*math.exp(-2), places=14)
        self.assertAlmostEqual(poisson_upper_tail(10, 1), 1.114254783387207e-7, delta=1e-20)

    def test_monotonic_confidence(self):
        self.assertLess(bayesian_upper(5, 2, .9), bayesian_upper(5, 2, .95))

    def test_invalid_input_rejected(self):
        for n,b in ((-1,0),(1.5,0),(True,0),(1,-1),(1,float('nan')),(501,0)):
            with self.assertRaises(ValueError):
                bayesian_upper(n,b)
        with self.assertRaises(ValueError):
            bayesian_upper(0,0,1)

    def test_flat_prior_bound_at_zero_background_is_the_classical_limit(self):
        for n, _, up90, _, up95 in PDG["table_40_3"]["rows"]:
            for level, text in ((0.90, up90), (0.95, up95)):
                decimals = len(text.split(".")[1])
                self.assertAlmostEqual(bayesian_upper(n, 0, level), float(text), delta=0.5 * 10 ** -decimals + 1e-9,
                                       msg=(n, level))

    def test_bound_grows_with_n_and_falls_with_b(self):
        for n in range(0, 20):
            self.assertLessEqual(bayesian_upper(n, 3.0), bayesian_upper(n + 1, 3.0) + 1e-9)
            self.assertLessEqual(bayesian_upper(n, 4.0), bayesian_upper(n, 3.0) + 1e-9)

    def test_tail_agrees_with_core_stats(self):
        for n, b in ((1, 0.5), (5, 5.0), (30, 4.0), (60, 5.0), (300, 450.0), (500, 300.0)):
            self.assertAlmostEqual(poisson_upper_tail(n, b) / pd.poisson_sf(n, b), 1.0, delta=1e-9, msg=(n, b))


class CountingCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True)

    def test_json_output(self):
        res = self.run_cli("--observed", "3", "--background", "1.5", "--level", "0.9")
        self.assertEqual(res.returncode, 0, res.stderr)
        out = json.loads(res.stdout)
        self.assertAlmostEqual(out["signal_upper_bound"], bayesian_upper(3, 1.5, 0.9), places=12)
        self.assertAlmostEqual(out["background_only_upper_tail_p"], poisson_upper_tail(3, 1.5), places=14)
        self.assertIn("NOT CLs", out["method"])

    def test_bad_input_is_a_usage_error_without_traceback(self):
        for args in (("--observed", "-1", "--background", "1"), ("--observed", "2", "--background", "nan"),
                     ("--observed", "2", "--background", "1", "--level", "1.5"), ("--observed", "x", "--background", "1")):
            res = self.run_cli(*args)
            self.assertEqual(res.returncode, 2, args)
            self.assertNotIn("Traceback", res.stderr)


if __name__ == "__main__":
    unittest.main()
