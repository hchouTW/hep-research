"""ANA-P2-9: exact ratio and fraction intervals for raw counts. Synthetic counts; scipy cross-check skips without it."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-measurement' / 'scripts' / 'particle_ratio_with_uncertainty.py'
sys.path.insert(0, str(SCRIPT.parent))
from particle_ratio_with_uncertainty import exact_ratio_and_fraction  # noqa: E402

try:
    from scipy.stats import beta
except ImportError:  # optional
    beta = None


def run(*args):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


class ExactRatioTests(unittest.TestCase):
    @unittest.skipIf(beta is None, 'scipy not installed')
    def test_three_over_five_matches_the_conditional_binomial_construction(self):
        a = (1 - 0.6827) / 2
        f_lo, f_hi = beta.ppf(a, 3, 6), beta.ppf(1 - a, 4, 5)
        out = exact_ratio_and_fraction(3, 5, 'poisson-ratio')
        self.assertAlmostEqual(out['ratio_interval'][0], f_lo / (1 - f_lo), places=7)
        self.assertAlmostEqual(out['ratio_interval'][1], f_hi / (1 - f_hi), places=7)
        self.assertAlmostEqual(out['fraction_interval'][0], f_lo, places=7)

    def test_zero_numerator_is_one_sided(self):
        out = exact_ratio_and_fraction(0, 5, 'poisson-ratio')
        self.assertEqual(out['ratio_interval'][0], 0.0)
        self.assertEqual(out['interval_kind'], 'upper-limit')
        p = run('--n1', '0', '--n2', '5', '--method', 'binomial-fraction')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['fraction_interval'][0], 0.0)

    def test_delta_method_warns_at_large_relative_errors(self):
        out = json.loads(run('--n1', '3', '--sigma1', '1.732', '--n2', '5', '--sigma2', '2.236').stdout)
        self.assertAlmostEqual(out['ratio'], 0.6)
        self.assertIn('poisson-ratio', out['warning'])

    def test_exact_methods_need_integer_counts(self):
        self.assertEqual(run('--n1', '2.5', '--n2', '5', '--method', 'poisson-ratio').returncode, 2)
        self.assertEqual(run('--n1', '3', '--n2', '5').returncode, 2)  # delta needs sigmas


if __name__ == '__main__':
    unittest.main()
