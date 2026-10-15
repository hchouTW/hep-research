"""cosmic_ray_flux.py: bin-width unit (ANA-P0-1). Synthetic values only."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-measurement' / 'scripts' / 'cosmic_ray_flux.py'


def run(*args):
    return subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), *args], capture_output=True, text=True,
                          timeout=120)


class BinWidthUnitTests(unittest.TestCase):
    def test_tev_bin_given_in_gv(self):
        # 4 counts in a 1.3-2.0 TV bin: the width is 700 GV, not 0.7.
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700', '--bin-width-unit', 'GV')
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out['bin_width_unit'], 'GV')
        self.assertEqual(f"{out['flux']:.3e}", '2.857e-10')
        self.assertEqual(f"{out['flux_lower']:.2e}", '1.49e-10')
        self.assertEqual(f"{out['flux_upper']:.2e}", '5.12e-10')

    def test_unit_is_required_and_the_error_names_the_rule(self):
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, '')
        self.assertIn('--bin-width-unit', p.stderr)
        self.assertIn('600 for a 1.2-1.8 TV bin', p.stderr)
        self.assertNotIn('Traceback', p.stderr)

    def test_unknown_unit_is_refused(self):
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700', '--bin-width-unit', 'MV')
        self.assertEqual(p.returncode, 2)

    def test_help_states_the_rule(self):
        p = run('--help')
        self.assertEqual(p.returncode, 0)
        self.assertIn('never pass a width in TV', ' '.join(p.stdout.split()))

    def test_guide_has_no_tev_width_example(self):
        for path in (ROOT / 'skills').rglob('*.md'):
            self.assertNotIn('0.6 for a 1.2', path.read_text(encoding='utf-8'), str(path))


sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT.parent))
from core.stats.poisson_diagnostics import fc_interval  # noqa: E402
from cosmic_ray_flux import flux_from_counts  # noqa: E402

try:
    from scipy.stats import chi2
except ImportError:  # optional
    chi2 = None


class BoundedBackgroundTests(unittest.TestCase):
    """ANA-P0-2: the interval is on s >= 0, never negative; no 500 ceiling."""

    def test_large_background_gives_an_upper_limit(self):
        out = flux_from_counts(3, 1.0, 1.0, background=10, background_sigma=1)
        self.assertEqual(out['method_id'], 'cousins-highland')
        self.assertEqual(out['flux_lower'], 0.0)
        self.assertEqual(out['interval_kind'], 'upper-limit')
        self.assertTrue(0 < out['flux_upper_limit'] < 10)
        self.assertIn('approximation', out['note'])

    def test_zero_counts_known_background_is_upper_limit_only(self):
        out = flux_from_counts(0, 1.0, 1.0, background=2, level=0.90)
        self.assertEqual(out['method_id'], 'feldman-cousins')
        self.assertEqual(out['interval_kind'], 'upper-limit')
        self.assertAlmostEqual(out['flux_upper_limit'], 1.26, delta=0.01)  # FC 1998 table

    def test_known_background_equals_core_fc_interval(self):
        for n, b, cl in ((0, 2.0, 0.90), (3, 10.0, 0.6827), (5, 1.0, 0.90), (10, 3.0, 0.95), (2, 0.5, 0.6827)):
            with self.subTest(n=n, b=b, cl=cl):
                iv = fc_interval(n, b, cl)
                out = flux_from_counts(n, 2.0, 0.5, background=b, level=cl)
                self.assertAlmostEqual(out['net_count_interval'][0], iv['lower'], delta=iv['grid_step'])
                self.assertAlmostEqual(out['net_count_interval'][1], iv['upper'], delta=iv['grid_step'])
                self.assertAlmostEqual(out['flux_upper'], iv['upper'] / 1.0, delta=iv['grid_step'])

    @unittest.skipIf(chi2 is None, 'scipy not installed')
    def test_large_counts_match_scipy_garwood(self):
        level = 0.6827
        for n in (480, 1000, 10000):
            with self.subTest(n=n):
                out = flux_from_counts(n, 1.0, 1.0, level=level)
                lo = chi2.ppf((1 - level) / 2, 2 * n) / 2
                hi = chi2.ppf(1 - (1 - level) / 2, 2 * n + 2) / 2
                self.assertAlmostEqual(out['flux_lower'] / lo, 1.0, delta=1e-6)
                self.assertAlmostEqual(out['flux_upper'] / hi, 1.0, delta=1e-6)

    def test_large_counts_succeed_without_scipy(self):
        for n in (480, 1000, 10000):
            out = flux_from_counts(n, 1.0, 1.0)
            self.assertTrue(out['flux_lower'] < n < out['flux_upper'])

    def test_naive_reproduces_the_old_numbers_and_is_labelled(self):
        out = flux_from_counts(42, 1.5e7, 10, background=8, background_sigma=1.5, method='naive')
        self.assertTrue(out['approximate'])
        self.assertIn('approximate', out['method'])
        self.assertAlmostEqual(out['flux'], 2.2666666666666666e-07, delta=1e-18)
        self.assertAlmostEqual(out['flux_lower'], 1.824870008083926e-07, delta=1e-15)
        self.assertAlmostEqual(out['flux_upper'], 2.7786827063333226e-07, delta=1e-15)

    def test_naive_never_prints_a_negative_bound(self):
        out = flux_from_counts(3, 1.0, 1.0, background=10, background_sigma=1, method='naive')
        self.assertGreaterEqual(out['flux_lower'], 0.0)
        self.assertGreaterEqual(out['flux_upper'], 0.0)
        self.assertTrue(out['warnings'])

    def test_no_negative_bound_on_a_seeded_grid(self):
        import random
        rng = random.Random(20261013)
        points = [(rng.randint(0, 50), round(rng.uniform(0.0, 20.0), 2)) for _ in range(6)]
        for n, b in points:
            for method in ('auto', 'naive'):
                with self.subTest(n=n, b=b, method=method):
                    out = flux_from_counts(n, 1.0, 1.0, background=b, method=method)
                    for key in ('flux', 'flux_lower', 'flux_upper'):
                        self.assertGreaterEqual(out[key], 0.0)
                    self.assertLessEqual(out['flux_lower'], out['flux_upper'])

    def test_exposure_uncertainty_is_separate(self):
        out = flux_from_counts(42, 1.5e7, 10, exposure_rel_uncertainty=0.05)
        ref = flux_from_counts(42, 1.5e7, 10)
        self.assertAlmostEqual(out['flux_syst_exposure'], 0.05 * out['flux'])
        self.assertEqual(out['flux_lower'], ref['flux_lower'])

    def test_method_must_fit_the_inputs(self):
        with self.assertRaises(ValueError):
            flux_from_counts(3, 1.0, 1.0, background=1, method='garwood')
        with self.assertRaises(ValueError):
            flux_from_counts(3, 1.0, 1.0, background=1, background_sigma=0.5, method='feldman-cousins')
        with self.assertRaises(ValueError):
            flux_from_counts(3, 1.0, 1.0, background=1, background_sigma=0.5, method='profile-fc')

    def test_profile_fc_is_seeded(self):
        a = flux_from_counts(3, 1.0, 1.0, background=1, background_sigma=0.5, method='profile-fc', toys=200, seed=3)
        b = flux_from_counts(3, 1.0, 1.0, background=1, background_sigma=0.5, method='profile-fc', toys=200, seed=3)
        self.assertEqual(a['flux_upper'], b['flux_upper'])
        self.assertEqual((a['toys'], a['seed']), (200, 3))

    def test_above_the_fc_grid_exits_3_and_names_the_alternative(self):
        p = run('--counts', '480', '--exposure', '1', '--bin-width', '1', '--background', '10', '--bin-width-unit', 'GV')
        self.assertEqual(p.returncode, 3)
        self.assertEqual(p.stdout, '')
        self.assertIn('profile-fc', p.stderr)


if __name__ == '__main__':
    unittest.main()
