"""Behavioral tests for the astroparticle-physics scripts (Li & Ma significance,
geomagnetic cutoff, cosmic-ray spectrum fitting, Gaisser-Hillas profile evaluation).

Run from the skill directory with python3 -m unittest discover -s tests -v.
Uses synthetic data and standard library only; no experiment files are needed.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
ROOT = PLUGIN
for _skill in ('hep-statistics', 'detector-response', 'hep-analysis'):
    sys.path.insert(0, str(PLUGIN / 'skills' / _skill / 'scripts'))
from li_ma_significance import li_ma_significance
from geomagnetic_cutoff import cutoff_kinetic_energy_per_nucleon_gev, stormer_cutoff_gv
from cr_spectrum_powerlaw_fit import fit_power_law, fit_segmented
from xmax_gaisser_hillas import gaisser_hillas, half_max_depths, shower_age


class LiMaSignificanceTests(unittest.TestCase):
    def test_equal_on_off_with_alpha_one_is_zero(self):
        result = li_ma_significance(50, 50, 1.0)
        self.assertAlmostEqual(result['significance'], 0.0, places=10)
        self.assertAlmostEqual(result['excess'], 0.0, places=10)

    def test_both_zero_counts_is_zero_by_convention(self):
        result = li_ma_significance(0, 0, 1.0)
        self.assertEqual(result['significance'], 0.0)

    def test_off_zero_boundary_matches_closed_form(self):
        # With N_off = 0, off_term = 0 and on_term = N_on * ln((1+alpha)/alpha).
        result = li_ma_significance(10, 0, 1.0)
        expected = math.sqrt(2.0 * 10 * math.log(2.0))
        self.assertAlmostEqual(result['significance'], expected, places=10)

    def test_on_zero_boundary_is_negative_and_symmetric_in_magnitude(self):
        positive = li_ma_significance(10, 0, 1.0)
        negative = li_ma_significance(0, 10, 1.0)
        self.assertAlmostEqual(negative['significance'], -positive['significance'], places=10)

    def test_excess_sign_matches_significance_sign(self):
        deficit = li_ma_significance(5, 20, 1.0)
        self.assertLess(deficit['significance'], 0.0)
        self.assertLess(deficit['excess'], 0.0)
        excess = li_ma_significance(30, 5, 1.0)
        self.assertGreater(excess['significance'], 0.0)
        self.assertGreater(excess['excess'], 0.0)

    def test_significance_grows_with_larger_excess_at_fixed_alpha(self):
        smaller = li_ma_significance(15, 5, 1.0)
        larger = li_ma_significance(30, 5, 1.0)
        self.assertLess(smaller['significance'], larger['significance'])

    def test_rejects_negative_or_non_integer_counts(self):
        with self.assertRaises(ValueError):
            li_ma_significance(-1, 5, 1.0)
        with self.assertRaises(ValueError):
            li_ma_significance(5.5, 5, 1.0)

    def test_rejects_nonpositive_alpha(self):
        with self.assertRaises(ValueError):
            li_ma_significance(10, 5, 0.0)
        with self.assertRaises(ValueError):
            li_ma_significance(10, 5, -0.5)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-statistics/scripts/li_ma_significance.py'),
             '--on', '15', '--off', '5', '--alpha', '0.5'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = li_ma_significance(15, 5, 0.5)
        self.assertAlmostEqual(payload['significance'], expected['significance'], places=10)

    def test_cli_rejects_bad_alpha_cleanly_not_with_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-statistics/scripts/li_ma_significance.py'),
             '--on', '10', '--off', '5', '--alpha', '-1'],
            capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


class GeomagneticCutoffTests(unittest.TestCase):
    def test_equatorial_cutoff_matches_known_dipole_value(self):
        # Vertical Stormer cutoff, Smart & Shea 2005 (Adv. Space Res. 36, 2012):
        # Rc = 14.9 GV * cos^4(lambda) / r^2, i.e. 59.6/4 = 14.9 GV at the equator.
        cutoff = stormer_cutoff_gv(0.0)
        self.assertAlmostEqual(cutoff, 14.9, places=6)
        # cos^4 latitude dependence: at 60 deg, 14.9 / 16.
        self.assertAlmostEqual(stormer_cutoff_gv(60.0), 14.9 / 16.0, places=6)
        # 1/r^2 altitude dependence: ISS-like r = 1.0627 Earth radii.
        self.assertAlmostEqual(stormer_cutoff_gv(0.0, altitude_re=1.0627), 14.9 / 1.0627 ** 2, places=6)

    def test_cutoff_decreases_monotonically_toward_the_pole(self):
        latitudes = [0.0, 20.0, 40.0, 60.0, 80.0, 90.0]
        cutoffs = [stormer_cutoff_gv(lat) for lat in latitudes]
        self.assertEqual(cutoffs, sorted(cutoffs, reverse=True))

    def test_cutoff_is_symmetric_in_latitude_sign(self):
        self.assertAlmostEqual(stormer_cutoff_gv(41.5), stormer_cutoff_gv(-41.5), places=10)

    def test_polar_cutoff_is_essentially_zero(self):
        self.assertLess(stormer_cutoff_gv(90.0), 1e-20)

    def test_cutoff_falls_with_increasing_altitude(self):
        surface = stormer_cutoff_gv(30.0, altitude_re=1.0)
        higher = stormer_cutoff_gv(30.0, altitude_re=1.5)
        self.assertLess(higher, surface)

    def test_rejects_latitude_out_of_range(self):
        with self.assertRaises(ValueError):
            stormer_cutoff_gv(91.0)
        with self.assertRaises(ValueError):
            stormer_cutoff_gv(-91.0)

    def test_rejects_nonpositive_altitude_or_dipole_moment(self):
        with self.assertRaises(ValueError):
            stormer_cutoff_gv(0.0, altitude_re=0.0)
        with self.assertRaises(ValueError):
            stormer_cutoff_gv(0.0, dipole_moment_g_cm3=-1.0)

    def test_kinetic_energy_conversion_is_positive_and_below_momentum_equivalent(self):
        # For an ultra-relativistic proton, kinetic energy per nucleon approaches the
        # cutoff rigidity (momentum) itself but must remain strictly below it.
        cutoff = stormer_cutoff_gv(0.0)
        kinetic = cutoff_kinetic_energy_per_nucleon_gev(cutoff, charge=1, mass_number=1)
        self.assertGreater(kinetic, 0.0)
        self.assertLess(kinetic, cutoff)

    def test_kinetic_energy_conversion_rejects_bad_charge_or_mass(self):
        with self.assertRaises(ValueError):
            cutoff_kinetic_energy_per_nucleon_gev(10.0, charge=0, mass_number=1)
        with self.assertRaises(ValueError):
            cutoff_kinetic_energy_per_nucleon_gev(10.0, charge=3, mass_number=2)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/geomagnetic_cutoff.py'), '--latitude', '41.5'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = stormer_cutoff_gv(41.5)
        self.assertAlmostEqual(payload['vertical_cutoff_rigidity_gv'], expected, places=10)


class SpectrumPowerLawFitTests(unittest.TestCase):
    def setUp(self):
        self.gamma1, self.gamma2, self.break_e = 2.7, 3.1, 4.0e15
        self.a1 = 1.0e5
        self.a2 = self.a1 * self.break_e ** (self.gamma2 - self.gamma1)

    def _flux(self, energy):
        if energy < self.break_e:
            return self.a1 * energy ** -self.gamma1
        return self.a2 * energy ** -self.gamma2

    def test_single_power_law_is_recovered_exactly(self):
        points = [[e, self.a1 * e ** -self.gamma1] for e in (1e14, 3e14, 1e15, 3e15, 1e16)]
        result = fit_power_law(points)
        self.assertAlmostEqual(result['index'], self.gamma1, places=8)
        self.assertAlmostEqual(result['normalization_at_e1'], self.a1, delta=self.a1 * 1e-6)
        self.assertLess(result['max_abs_residual_log_flux'], 1e-8)

    def test_segmented_fit_recovers_both_indices_and_break(self):
        energies = [1e14, 3e14, 1e15, 2e15, 4e15, 8e15, 2e16, 5e16, 1e17]
        points = [[e, self._flux(e)] for e in energies]
        result = fit_segmented(points, self.break_e)
        self.assertAlmostEqual(result['below_break']['index'], self.gamma1, places=8)
        self.assertAlmostEqual(result['above_break']['index'], self.gamma2, places=8)
        self.assertAlmostEqual(result['index_change'], self.gamma2 - self.gamma1, places=8)

    def test_single_fit_on_broken_spectrum_shows_large_residual(self):
        # A single power law forced onto a genuinely broken spectrum should show
        # much larger residuals than the correctly segmented fit.
        energies = [1e14, 3e14, 1e15, 2e15, 4e15, 8e15, 2e16, 5e16, 1e17]
        points = [[e, self._flux(e)] for e in energies]
        single = fit_power_law(points)
        segmented = fit_segmented(points, self.break_e)
        self.assertGreater(single['max_abs_residual_log_flux'],
                           10 * max(segmented['below_break']['max_abs_residual_log_flux'],
                                    segmented['above_break']['max_abs_residual_log_flux']))

    def test_weighted_fit_uses_supplied_sigma(self):
        points_unweighted = [[e, self.a1 * e ** -self.gamma1] for e in (1e14, 3e14, 1e15, 3e15, 1e16)]
        points_weighted = [[e, f, f * 0.05] for e, f in points_unweighted]
        result = fit_power_law(points_weighted)
        self.assertTrue(result['weighted'])
        self.assertAlmostEqual(result['index'], self.gamma1, places=6)

    def test_requires_at_least_two_distinct_energies(self):
        with self.assertRaises(ValueError):
            fit_power_law([[1e15, 1e-30]])

    def test_rejects_nonpositive_energy_or_flux(self):
        with self.assertRaises(ValueError):
            fit_power_law([[1e15, 1e-30], [-1e15, 1e-31]])
        with self.assertRaises(ValueError):
            fit_power_law([[1e15, 1e-30], [2e15, 0.0]])

    def test_segmented_fit_requires_enough_points_on_each_side(self):
        points = [[1e14, self._flux(1e14)], [3e14, self._flux(3e14)], [1e17, self._flux(1e17)]]
        with self.assertRaises(ValueError):
            fit_segmented(points, self.break_e)

    def test_cli_matches_library_result_on_shipped_asset(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py'),
             '--input', str(ROOT / 'skills/hep-analysis/assets/cosmic-ray-spectrum.example.json'),
             '--break-energy', '4.0e15'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        self.assertAlmostEqual(payload['below_break']['index'], self.gamma1, places=6)
        self.assertAlmostEqual(payload['above_break']['index'], self.gamma2, places=6)

    def test_cli_missing_file_fails_cleanly_not_with_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/cr_spectrum_powerlaw_fit.py'),
             '--input', str(ROOT / 'skills/hep-analysis/assets/does_not_exist.json')],
            capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


class GaisserHillasTests(unittest.TestCase):
    def setUp(self):
        self.n_max, self.x_max, self.x0, self.lam = 2.0e7, 750.0, -60.0, 60.0

    def test_value_at_x_max_equals_n_max(self):
        value = gaisser_hillas(self.x_max, self.n_max, self.x_max, self.x0, self.lam)
        self.assertAlmostEqual(value, self.n_max, delta=self.n_max * 1e-9)

    def test_profile_is_smaller_away_from_maximum(self):
        at_max = gaisser_hillas(self.x_max, self.n_max, self.x_max, self.x0, self.lam)
        before = gaisser_hillas(self.x_max - 200, self.n_max, self.x_max, self.x0, self.lam)
        after = gaisser_hillas(self.x_max + 200, self.n_max, self.x_max, self.x0, self.lam)
        self.assertLess(before, at_max)
        self.assertLess(after, at_max)

    def test_undefined_at_or_before_x0_is_nan(self):
        self.assertTrue(math.isnan(gaisser_hillas(self.x0, self.n_max, self.x_max, self.x0, self.lam)))
        self.assertTrue(math.isnan(gaisser_hillas(self.x0 - 10, self.n_max, self.x_max, self.x0, self.lam)))

    def test_shower_age_is_one_at_x_max_and_zero_at_x0(self):
        self.assertAlmostEqual(shower_age(self.x_max, self.x_max, self.x0), 1.0, places=10)
        self.assertAlmostEqual(shower_age(self.x0, self.x_max, self.x0), 0.0, places=10)

    def test_shower_age_increases_monotonically_with_depth(self):
        depths = [0.0, 300.0, 600.0, 750.0, 900.0, 1200.0]
        ages = [shower_age(d, self.x_max, self.x0) for d in depths]
        self.assertEqual(ages, sorted(ages))

    def test_rejects_x_max_not_greater_than_x0(self):
        with self.assertRaises(ValueError):
            gaisser_hillas(500.0, self.n_max, self.x0, self.x0, self.lam)
        with self.assertRaises(ValueError):
            shower_age(500.0, self.x0, self.x0)

    def test_half_maximum_depths_bracket_x_max_and_are_at_half_height(self):
        rising, falling = half_max_depths(self.n_max, self.x_max, self.x0, self.lam)
        self.assertLess(rising, self.x_max)
        self.assertGreater(falling, self.x_max)
        rising_value = gaisser_hillas(rising, self.n_max, self.x_max, self.x0, self.lam)
        falling_value = gaisser_hillas(falling, self.n_max, self.x_max, self.x0, self.lam)
        self.assertAlmostEqual(rising_value, 0.5 * self.n_max, delta=self.n_max * 1e-4)
        self.assertAlmostEqual(falling_value, 0.5 * self.n_max, delta=self.n_max * 1e-4)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/xmax_gaisser_hillas.py'),
             '--n-max', str(self.n_max), '--x-max', str(self.x_max),
             '--x0', str(self.x0), '--lambda-param', str(self.lam),
             '--depths', '400,750,900'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        self.assertAlmostEqual(payload['n_at_x_max_check'], self.n_max, delta=self.n_max * 1e-6)
        middle_entry = next(p for p in payload['profile'] if p['depth'] == 750.0)
        self.assertAlmostEqual(middle_entry['n'], self.n_max, delta=self.n_max * 1e-6)

    def test_cli_rejects_bad_geometry_cleanly_not_with_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/xmax_gaisser_hillas.py'),
             '--n-max', '1e7', '--x-max', '100', '--x0', '200', '--lambda-param', '60'],
            capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


if __name__ == '__main__':
    unittest.main()
