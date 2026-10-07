"""Behavioral tests for the AMS-02-case-study scripts: orbit-averaged geomagnetic
cutoff, the solar-modulation force-field approximation, particle-ratio error
propagation, and cosmic-ray flux/statistics from counts.

Run from the skill directory with python3 -m unittest discover -s tests -v.
Uses synthetic data and standard library only; no experiment files are needed.
Expected values for the exact-Poisson interval tests were independently
cross-checked against scipy.stats.chi2's Garwood-interval formula during
development (see VALIDATION.md); the test file itself does not depend on scipy.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
ROOT = PLUGIN
for _skill in ('hep-analysis',):
    sys.path.insert(0, str(PLUGIN / 'skills' / _skill / 'scripts'))
from geomagnetic_cutoff import stormer_cutoff_gv
from orbit_averaged_geomagnetic_cutoff import orbit_cutoff_profile
from solar_modulation_force_field import demodulate, modulate, power_law_lis
from particle_ratio_with_uncertainty import ratio_and_fraction
from cosmic_ray_flux import flux_from_counts, poisson_interval


class OrbitAveragedCutoffTests(unittest.TestCase):
    def test_near_equatorial_orbit_matches_single_latitude_value(self):
        profile = orbit_cutoff_profile(1.0)
        equatorial = stormer_cutoff_gv(0.0)
        self.assertAlmostEqual(profile['max_cutoff_gv'], equatorial, delta=0.01)

    def test_min_and_max_bracket_the_time_weighted_mean(self):
        profile = orbit_cutoff_profile(51.6, altitude_re=1.0627)
        self.assertLessEqual(profile['min_cutoff_gv'], profile['time_weighted_mean_cutoff_gv'])
        self.assertLessEqual(profile['time_weighted_mean_cutoff_gv'], profile['max_cutoff_gv'])

    def test_higher_inclination_reaches_lower_minimum_cutoff(self):
        low_inclination = orbit_cutoff_profile(20.0)
        high_inclination = orbit_cutoff_profile(70.0)
        self.assertGreater(low_inclination['min_cutoff_gv'], high_inclination['min_cutoff_gv'])

    def test_polar_orbit_minimum_is_essentially_zero(self):
        profile = orbit_cutoff_profile(90.0)
        self.assertLess(profile['min_cutoff_gv'], 1e-10)

    def test_latitude_range_matches_inclination(self):
        profile = orbit_cutoff_profile(51.6)
        self.assertAlmostEqual(profile['latitude_range_deg'][0], 0.0, places=6)
        self.assertAlmostEqual(profile['latitude_range_deg'][1], 51.6, places=6)

    def test_rejects_out_of_range_inclination(self):
        with self.assertRaises(ValueError):
            orbit_cutoff_profile(0.0)
        with self.assertRaises(ValueError):
            orbit_cutoff_profile(91.0)

    def test_rejects_too_few_samples(self):
        with self.assertRaises(ValueError):
            orbit_cutoff_profile(51.6, n_samples=5)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/orbit_averaged_geomagnetic_cutoff.py'),
             '--inclination', '51.6', '--altitude-re', '1.0627'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = orbit_cutoff_profile(51.6, altitude_re=1.0627)
        self.assertAlmostEqual(payload['time_weighted_mean_cutoff_gv'],
                               expected['time_weighted_mean_cutoff_gv'], places=8)


class SolarModulationForceFieldTests(unittest.TestCase):
    MASS_PROTON_GEV = 0.938272

    def test_zero_potential_leaves_flux_unchanged(self):
        result = modulate(5.0, self.MASS_PROTON_GEV, 1, 0.0,
                          lambda e: power_law_lis(e, 1e4, 2.7))
        self.assertAlmostEqual(result['flux_toa'], result['flux_lis'], places=10)
        self.assertAlmostEqual(result['energy_toa'], result['energy_lis'], places=10)
        self.assertAlmostEqual(result['jacobian'], 1.0, places=10)

    def test_modulation_suppresses_low_energy_flux(self):
        result = modulate(1.0, self.MASS_PROTON_GEV, 1, 0.5,
                          lambda e: power_law_lis(e, 1e4, 2.7))
        self.assertLess(result['flux_toa'], result['flux_lis'])

    def test_demodulate_inverts_modulate_exactly(self):
        forward = modulate(1.0, self.MASS_PROTON_GEV, 1, 0.5,
                           lambda e: power_law_lis(e, 1e4, 2.7))
        inverse = demodulate(1.0, self.MASS_PROTON_GEV, 1, 0.5, forward['flux_toa'])
        self.assertAlmostEqual(inverse['flux_lis'], forward['flux_lis'], places=8)
        self.assertAlmostEqual(inverse['energy_lis'], forward['energy_lis'], places=10)

    def test_higher_charge_shifts_energy_more_at_fixed_phi(self):
        proton = modulate(1.0, self.MASS_PROTON_GEV, 1, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))
        helium = modulate(1.0, 3.727, 2, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))
        self.assertGreater(helium['energy_lis'] - 1.0, proton['energy_lis'] - 1.0)

    def test_rejects_nonpositive_energy_or_mass(self):
        with self.assertRaises(ValueError):
            modulate(-1.0, self.MASS_PROTON_GEV, 1, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))
        with self.assertRaises(ValueError):
            modulate(1.0, 0.0, 1, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))

    def test_rejects_bad_charge(self):
        with self.assertRaises(ValueError):
            modulate(1.0, self.MASS_PROTON_GEV, 0, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))
        with self.assertRaises(ValueError):
            modulate(1.0, self.MASS_PROTON_GEV, 1.5, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))

    def test_cli_modulate_matches_library(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/solar_modulation_force_field.py'),
             '--modulate', '--energy', '1.0', '--mass', str(self.MASS_PROTON_GEV),
             '--charge', '1', '--phi', '0.5', '--lis-normalization', '1e4', '--lis-index', '2.7'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = modulate(1.0, self.MASS_PROTON_GEV, 1, 0.5, lambda e: power_law_lis(e, 1e4, 2.7))
        self.assertAlmostEqual(payload['flux_toa'], expected['flux_toa'], places=8)

    def test_cli_requires_lis_params_for_modulate(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/solar_modulation_force_field.py'),
             '--modulate', '--energy', '1.0', '--mass', str(self.MASS_PROTON_GEV),
             '--charge', '1', '--phi', '0.5'],
            capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


class ParticleRatioTests(unittest.TestCase):
    def test_ratio_and_fraction_match_direct_arithmetic(self):
        result = ratio_and_fraction(1200, 40, 85000, 300)
        self.assertAlmostEqual(result['ratio'], 1200 / 85000, places=10)
        self.assertAlmostEqual(result['fraction'], 1200 / 86200, places=10)

    def test_zero_uncertainty_gives_zero_propagated_uncertainty(self):
        result = ratio_and_fraction(100, 0.0, 200, 0.0)
        self.assertEqual(result['sigma_ratio'], 0.0)
        self.assertEqual(result['sigma_fraction'], 0.0)

    def test_uncertainty_matches_independent_quadrature_formula(self):
        n1, s1, n2, s2 = 1200.0, 40.0, 85000.0, 300.0
        result = ratio_and_fraction(n1, s1, n2, s2)
        expected_sigma_ratio = (n1 / n2) * math.sqrt((s1 / n1) ** 2 + (s2 / n2) ** 2)
        self.assertAlmostEqual(result['sigma_ratio'], expected_sigma_ratio, places=10)

    def test_positive_correlation_reduces_ratio_uncertainty(self):
        independent = ratio_and_fraction(1200, 40, 85000, 300, correlation=0.0)
        correlated = ratio_and_fraction(1200, 40, 85000, 300, correlation=0.5)
        self.assertLess(correlated['sigma_ratio'], independent['sigma_ratio'])

    def test_fraction_is_between_zero_and_one(self):
        result = ratio_and_fraction(1, 0.5, 1000, 30)
        self.assertGreater(result['fraction'], 0.0)
        self.assertLess(result['fraction'], 1.0)

    def test_rejects_nonpositive_yields(self):
        with self.assertRaises(ValueError):
            ratio_and_fraction(0, 1, 100, 5)
        with self.assertRaises(ValueError):
            ratio_and_fraction(100, 1, -5, 5)

    def test_rejects_correlation_out_of_range(self):
        with self.assertRaises(ValueError):
            ratio_and_fraction(100, 5, 200, 10, correlation=1.5)
        with self.assertRaises(ValueError):
            ratio_and_fraction(100, 5, 200, 10, correlation=-1.5)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/particle_ratio_with_uncertainty.py'),
             '--n1', '1200', '--sigma1', '40', '--n2', '85000', '--sigma2', '300'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = ratio_and_fraction(1200, 40, 85000, 300)
        self.assertAlmostEqual(payload['sigma_fraction'], expected['sigma_fraction'], places=10)


class CosmicRayFluxTests(unittest.TestCase):
    def test_exact_garwood_interval_matches_independent_chi2_cross_check(self):
        # Independently cross-checked against scipy.stats.chi2's Garwood formula
        # for n=42, 68.27% confidence: (35.545043400971, 49.532336662489).
        lower, upper = poisson_interval(42, level=0.6827)
        self.assertAlmostEqual(lower, 35.545043400971096, places=6)
        self.assertAlmostEqual(upper, 49.5323366624895, places=6)

    def test_exact_garwood_interval_at_90_percent_matches_cross_check(self):
        # Cross-checked against scipy.stats.chi2 for n=42, 90%: (31.938130721517, 54.323946486754).
        lower, upper = poisson_interval(42, level=0.90)
        self.assertAlmostEqual(lower, 31.938130721517155, places=6)
        self.assertAlmostEqual(upper, 54.323946486753826, places=6)

    def test_zero_observed_gives_zero_lower_bound(self):
        lower, upper = poisson_interval(0)
        self.assertEqual(lower, 0.0)
        self.assertGreater(upper, 0.0)

    def test_interval_brackets_the_observed_count(self):
        lower, upper = poisson_interval(100)
        self.assertLess(lower, 100)
        self.assertGreater(upper, 100)

    def test_flux_central_value_matches_direct_division(self):
        result = flux_from_counts(42, exposure=1.5e7, bin_width=10.0)
        self.assertAlmostEqual(result['flux'], 42.0 / (1.5e7 * 10.0), places=15)

    def test_background_subtraction_reduces_net_counts(self):
        result = flux_from_counts(42, exposure=1.5e7, bin_width=10.0, background=8.0, background_sigma=1.5)
        self.assertAlmostEqual(result['net_counts'], 34.0, places=10)
        self.assertLess(result['flux'], flux_from_counts(42, exposure=1.5e7, bin_width=10.0)['flux'])

    def test_larger_exposure_gives_smaller_flux(self):
        small_exposure = flux_from_counts(42, exposure=1e6, bin_width=10.0)
        large_exposure = flux_from_counts(42, exposure=1e8, bin_width=10.0)
        self.assertGreater(small_exposure['flux'], large_exposure['flux'])

    def test_rejects_nonpositive_exposure_or_bin_width(self):
        with self.assertRaises(ValueError):
            flux_from_counts(42, exposure=0.0, bin_width=10.0)
        with self.assertRaises(ValueError):
            flux_from_counts(42, exposure=1e6, bin_width=-1.0)

    def test_rejects_negative_or_noninteger_counts(self):
        with self.assertRaises(ValueError):
            flux_from_counts(-1, exposure=1e6, bin_width=1.0)
        with self.assertRaises(ValueError):
            flux_from_counts(4.5, exposure=1e6, bin_width=1.0)

    def test_count_beyond_exact_tool_range_raises_clear_error(self):
        with self.assertRaises(ValueError):
            poisson_interval(501)

    def test_cli_matches_library_result(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/cosmic_ray_flux.py'),
             '--counts', '42', '--exposure', '1.5e7', '--bin-width', '10'],
            capture_output=True, text=True, check=True, timeout=600)
        payload = json.loads(proc.stdout)
        expected = flux_from_counts(42, exposure=1.5e7, bin_width=10.0)
        self.assertAlmostEqual(payload['flux'], expected['flux'], places=15)
        self.assertAlmostEqual(payload['flux_lower'], expected['flux_lower'], places=15)

    def test_cli_rejects_bad_input_cleanly_not_with_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/hep-analysis/scripts/cosmic_ray_flux.py'),
             '--counts', '-1', '--exposure', '1e6', '--bin-width', '1'],
            capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


if __name__ == '__main__':
    unittest.main()
