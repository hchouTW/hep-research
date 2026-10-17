"""Regression tests for the validity guards and output validity of the hep-detector scripts.

Each test pins one defect from the 2026-10-12 hep-detector review (sections 3.1-3.8):
charge in dE/dx mode, non-monotonic separation, negative Bethe-Bloch loss, few-photon
Cherenkov separation, NaN in the tag-and-probe JSON, pileup weight diagnostics, the
calorimeter fit's uncertainties and range, and raw tracebacks on edge-case input.
Standard library only; synthetic inputs only.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / 'skills' / 'hep-detector' / 'scripts'
ASSETS = PLUGIN / 'skills' / 'hep-detector' / 'assets'
sys.path.insert(0, str(SCRIPTS))
import calorimeter_resolution  # noqa: E402
import cherenkov_angle  # noqa: E402
import multiple_scattering  # noqa: E402
import pid_separation_power  # noqa: E402
import pileup_reweight  # noqa: E402
import tag_and_probe_efficiency  # noqa: E402
import xmax_gaisser_hillas  # noqa: E402


def _reject_constant(name):
    raise ValueError(f'non-standard JSON constant {name}')


def strict_json(text):
    """json.loads that refuses NaN, Infinity and -Infinity, as a strict consumer would."""
    return json.loads(text, parse_constant=_reject_constant)


def run(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, timeout=600)


def run_json(testcase, script, *args, returncode=0):
    proc = run(script, *args)
    testcase.assertNotIn('Traceback', proc.stderr)
    testcase.assertEqual(proc.returncode, returncode, proc.stderr or proc.stdout)
    return strict_json(proc.stdout)


class _TempFiles:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding='utf-8')
        return path


class PidChargeAndValidityTests(unittest.TestCase):
    def test_dedx_mode_applies_z_squared_for_helium(self):
        # d vs He4 at 2 GeV/c in silicon: He4 has z=2, so its loss is 4x the z=1 value.
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                           '--species', 'd', 'He4', '--momentum', '2')
        expected = pid_separation_power.bethe_bloch_mev_per_g_cm2(2.0, pid_separation_power.MASSES_GEV['He4'], 'silicon', charge=2)
        self.assertAlmostEqual(payload['observable']['dedx_b_mev_per_g_cm2'],
                               expected['mev_per_g_cm2'], places=12)
        self.assertAlmostEqual(expected['mev_per_g_cm2'], 19.76, delta=0.01)
        self.assertGreater(payload['n_sigma'], 100.0)
        self.assertAlmostEqual(payload['n_sigma'], 121.6, delta=0.2)
        self.assertEqual(payload['species_b']['charge'], 2)

    def test_dedx_scan_reports_the_band_crossing(self):
        # pi/K in argon: the two Bethe-Bloch curves cross near 1 GeV/c (0.52 sigma there),
        # so a single ceiling at 63.5 GeV/c spanning the crossing is wrong.
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                           '--species', 'pi', 'K', '--momentum', '3', '--material', 'argon',
                           '--threshold', '2', '--relative-resolution', '0.05')
        intervals = payload['below_threshold_intervals']
        self.assertTrue(any(low <= 1.0 <= high for low, high in intervals), intervals)
        self.assertLess(payload['separation_ceiling_gev'], 1.0)
        self.assertFalse(payload['ceiling_is_lower_bound'])

    def test_scan_limit_is_flagged_as_a_lower_bound(self):
        # p/He3 in argon (z^2 = 4 apart) stays separated up to the 1000 GeV/c scan limit, so the end
        # of separation is only a lower bound. (e/pi was used before; electrons are outside the heavy-particle
        # Bethe formula since the hep-detector audit, E-P1.)
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                           '--species', 'p', 'He3', '--momentum', '2', '--material', 'argon')
        self.assertTrue(payload['ceiling_is_lower_bound'])
        self.assertEqual(payload['highest_separated_gev'], payload['scan_range'][1])
        self.assertEqual(payload['below_threshold_intervals'], [])

    def test_separation_can_dip_and_recover(self):
        # mu/p in argon: below 3 sigma between about 1.08 and 2.21 GeV/c, separated again above, and lost for good
        # above about 58 GeV/c - the old code reported only the first ceiling.
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                           '--species', 'mu', 'p', '--momentum', '0.5', '--material', 'argon')
        intervals = payload['below_threshold_intervals']
        self.assertEqual(len(intervals), 2)
        self.assertAlmostEqual(intervals[0][0], 1.0833, delta=1e-3)
        self.assertAlmostEqual(intervals[0][1], 2.2107, delta=1e-3)
        self.assertAlmostEqual(intervals[1][0], 58.141, delta=1e-2)

    def test_bethe_bloch_refuses_low_beta_gamma(self):
        # He4 at 0.05 GeV/c in xenon (beta*gamma = 0.013) used to give -676.6 MeV g^-1 cm^2.
        loss = pid_separation_power.bethe_bloch_mev_per_g_cm2(0.05, pid_separation_power.MASSES_GEV['He4'], 'xenon', charge=2)
        self.assertIsNone(loss['mev_per_g_cm2'])
        self.assertEqual(loss['validity'], 'outside')
        result = pid_separation_power.separation('dedx', 3.7274, 2.8084, 0.05, material='xenon',
                            relative_resolution=0.05)
        self.assertIsNone(result['n_sigma'])
        self.assertEqual(result['validity'], 'outside')
        for key in ('dedx_a_mev_per_g_cm2', 'dedx_b_mev_per_g_cm2'):
            value = result['observable'][key]
            self.assertTrue(value is None or value > 0, (key, value))
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                           '--species', 'He4', 'He3', '--momentum', '0.05', '--material', 'xenon')
        self.assertIsNone(payload['n_sigma'])
        self.assertEqual(payload['validity'], 'outside')

    def test_rigidity_input_is_charge_times_momentum(self):
        by_momentum = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                               '--species', 'He3', 'He4', '--momentum', '2')
        by_rigidity = run_json(self, 'pid_separation_power.py', '--mode', 'dedx',
                               '--species', 'He3', 'He4', '--rigidity', '1')
        self.assertEqual(by_rigidity['input_variable'], 'rigidity')
        self.assertEqual(by_momentum['input_variable'], 'momentum')
        self.assertAlmostEqual(by_rigidity['species_b']['momentum_gev'], 2.0, places=12)
        self.assertAlmostEqual(by_rigidity['n_sigma'], by_momentum['n_sigma'], places=12)
        self.assertAlmostEqual(by_rigidity['observable']['dedx_b_mev_per_g_cm2'],
                               by_momentum['observable']['dedx_b_mev_per_g_cm2'], places=12)
        both = run('pid_separation_power.py', '--mode', 'dedx', '--species', 'He3', 'He4',
                   '--momentum', '2', '--rigidity', '1')
        self.assertEqual(both.returncode, 2)
        self.assertNotIn('Traceback', both.stderr)

    def test_every_mode_states_its_convention(self):
        cases = (('tof', '--path', '1.2', '--time-resolution', '60'),
                 ('dedx', '--material', 'argon'),
                 ('velocity', '--beta-resolution', '1e-3'))
        for mode, *extra in cases:
            with self.subTest(mode=mode):
                payload = run_json(self, 'pid_separation_power.py', '--mode', mode,
                                   '--species', 'pi', 'K', '--momentum', '2', *extra)
                self.assertIn('separation_convention', payload)
                self.assertIn('reference_species', payload)
                if mode != 'tof':
                    self.assertEqual(payload['reference_species'], 'pi')

    def test_quadrature_convention_is_symmetric_in_species_order(self):
        cases = (('tof', '--path', '1.2', '--time-resolution', '60'),
                 ('dedx', '--material', 'argon'),
                 ('velocity', '--beta-resolution', '1e-3'))
        for mode, *extra in cases:
            with self.subTest(mode=mode):
                forward = run_json(self, 'pid_separation_power.py', '--mode', mode,
                                   '--species', 'pi', 'K', '--momentum', '2',
                                   '--convention', 'quadrature', *extra)
                backward = run_json(self, 'pid_separation_power.py', '--mode', mode,
                                    '--species', 'K', 'pi', '--momentum', '2',
                                    '--convention', 'quadrature', *extra)
                self.assertLess(abs(forward['n_sigma'] - backward['n_sigma']), 1e-12)
                self.assertIsNone(forward['reference_species'])

    def test_relativistic_rise_is_checked_for_both_species(self):
        # The electron is deep in the rise at 0.5 GeV/c; listing it second must not hide that.
        result = pid_separation_power.separation('dedx', pid_separation_power.MASSES_GEV['pi'], pid_separation_power.MASSES_GEV['e'], 0.5,
                            material='argon', relative_resolution=0.06)
        self.assertTrue(result['observable']['in_relativistic_rise'])
        self.assertTrue(result['observable']['n_sigma_optimistic'])


class CherenkovFewPhotonTests(unittest.TestCase):
    def test_near_threshold_species_has_no_gaussian_separation(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K',
                           '--momentum', '1.5425')
        kaon = payload['species_b']
        self.assertLess(kaon['expected_photons'], 1.0)
        self.assertNotEqual(kaon['photon_regime'], 'gaussian')
        self.assertAlmostEqual(kaon['p_no_photon'], math.exp(-kaon['expected_photons']), places=12)
        self.assertNotIn('relative_beta_resolution', kaon)
        self.assertIsNone(payload['n_sigma'])
        self.assertIn('threshold_discrimination', payload)

    def test_photon_regime_thresholds(self):
        for photons, regime in ((0.0, 'none'), (0.49, 'none'), (0.5, 'few'), (4.99, 'few'),
                                (5.0, 'gaussian'), (40.0, 'gaussian')):
            with self.subTest(photons=photons):
                self.assertEqual(cherenkov_angle.photon_regime(photons), regime)

    def test_track_term_does_not_shrink_with_photons(self):
        self.assertAlmostEqual(cherenkov_angle.track_angular_resolution(5e-3, 25, 1e-3),
                               math.hypot(1e-3, 1e-3), places=15)
        self.assertEqual(cherenkov_angle.track_angular_resolution(5e-3, 25), 5e-3 / 5.0)

    def test_default_track_resolution_keeps_existing_values(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K',
                           '--momentum', '10')
        theta_a = cherenkov_angle.cherenkov_angle(10.0, pid_separation_power.MASSES_GEV['pi'], 1.05)
        theta_b = cherenkov_angle.cherenkov_angle(10.0, pid_separation_power.MASSES_GEV['K'], 1.05)
        photons_a = cherenkov_angle.photon_yield(theta_a, 2.0, 100.0)
        expected = abs(theta_a - theta_b) / (5e-3 / math.sqrt(photons_a))
        self.assertAlmostEqual(payload['n_sigma'], expected, places=9)
        self.assertEqual(payload['reference_species'], 'pi')
        self.assertIn('separation_convention', payload)

    def test_quadrature_convention_is_symmetric(self):
        forward = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K',
                           '--momentum', '2', '--convention', 'quadrature')
        backward = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'K', 'pi',
                            '--momentum', '2', '--convention', 'quadrature')
        self.assertLess(abs(forward['n_sigma'] - backward['n_sigma']), 1e-12)

    def test_record_below_threshold_reports_zero_photons(self):
        record = cherenkov_angle.describe_species(2.0, pid_separation_power.MASSES_GEV['p'], 1.05, 2.0, 100.0, 5e-3)
        self.assertEqual(record['expected_photons'], 0.0)
        self.assertEqual(record['photon_regime'], 'none')


class TagAndProbeOutputTests(unittest.TestCase):
    def test_zero_probes_give_null_not_nan(self):
        payload = run_json(self, 'tag_and_probe_efficiency.py', '--pass-count', '0', '--total', '0')
        self.assertIsNone(payload['efficiency'])
        self.assertIsNone(payload['lower_bound'])
        self.assertIsNone(payload['upper_bound'])
        self.assertIn('reason', payload)

    def test_level_is_validated_even_with_zero_probes(self):
        for level in (1.5, 7, 0.0, float('nan')):
            with self.subTest(level=level):
                with self.assertRaises(ValueError):
                    tag_and_probe_efficiency.efficiency_bin(0, 0, level=level)

    def test_output_names_the_interval_level(self):
        payload = run_json(self, 'tag_and_probe_efficiency.py', '--pass-count', '92', '--total', '100')
        self.assertEqual(payload['interval_level'], 0.95)
        self.assertNotIn('lower_error', payload)
        self.assertNotIn('upper_error', payload)
        self.assertLess(payload['lower_bound'], 0.92)
        self.assertGreater(payload['upper_bound'], 0.92)


class PileupDiagnosticsTests(_TempFiles, unittest.TestCase):
    def test_shipped_example_reports_effective_size_and_max_weight(self):
        payload = run_json(self, 'pileup_reweight.py', ASSETS / 'pileup-profiles.example.json')
        self.assertAlmostEqual(payload['max_weight'], 484.8, delta=0.1)
        self.assertGreater(payload['n_eff'], 0.0)
        self.assertLess(payload['n_eff_fraction'], 0.5)
        self.assertTrue(payload['warnings'])

    def test_subnormal_mc_bin_is_not_ok(self):
        path = self.write('sub.json', json.dumps(
            {'bin_centers': [0, 1], 'data_profile': [1, 1], 'mc_profile': [5e-324, 1]}))
        payload = run_json(self, 'pileup_reweight.py', path, returncode=1)
        self.assertFalse(payload['ok'])

    def test_nan_bin_center_is_not_ok(self):
        path = self.write('nan.json', '{"bin_centers": [0, NaN], "data_profile": [1, 1], '
                                      '"mc_profile": [1, 1]}')
        payload = run_json(self, 'pileup_reweight.py', path, returncode=1)
        self.assertFalse(payload['ok'])

    def test_infinite_weight_is_never_returned(self):
        weights, _ = pileup_reweight.compute_weights([1, 1], [5e-324, 1])
        self.assertTrue(all(w is None or math.isfinite(w) for w in weights))


class CalorimeterFitTests(_TempFiles, unittest.TestCase):
    @staticmethod
    def _model(a, b, c, energy):
        return math.sqrt(a * a / energy + b * b / (energy * energy) + c * c)

    def test_weighted_fit_reports_covariance(self):
        energies = [1.0, 2.0, 5.0, 10.0, 50.0, 100.0]
        points = [[e, self._model(0.10, 0.20, 0.007, e), 0.002] for e in energies]
        points[2][1] *= 1.10  # one shifted point
        points[2][2] = 0.05   # ... with a large uncertainty
        weighted = calorimeter_resolution.fit_resolution(points)
        unweighted = calorimeter_resolution.fit_resolution([p[:2] for p in points])
        self.assertTrue(weighted['weighted'])
        self.assertFalse(unweighted['weighted'])
        # Down-weighting the shifted point keeps the fit closer to the generating values.
        self.assertLess(abs(weighted['stochastic'] - 0.10), abs(unweighted['stochastic'] - 0.10))
        covariance = weighted['covariance_squared_terms']
        self.assertEqual(len(covariance), 3)
        for i in range(3):
            self.assertGreater(covariance[i][i], 0.0)
            for j in range(3):
                self.assertAlmostEqual(covariance[i][j], covariance[j][i], delta=abs(covariance[i][i]) * 1e-9)
        # Independent check: covariance is the inverse of the weighted normal matrix.
        rows = [(1.0 / p[0], 1.0 / p[0] ** 2, 1.0) for p in points]
        weights = [1.0 / (2.0 * p[1] * p[2]) ** 2 for p in points]
        normal = [[sum(w * r[i] * r[j] for r, w in zip(rows, weights)) for j in range(3)]
                  for i in range(3)]
        for i in range(3):
            for j in range(3):
                product = sum(normal[i][k] * covariance[k][j] for k in range(3))
                self.assertAlmostEqual(product, 1.0 if i == j else 0.0, delta=1e-6)

    def test_three_points_warn_about_zero_degrees_of_freedom(self):
        points = [[e, self._model(0.10, 0.20, 0.007, e)] for e in (1.0, 10.0, 100.0)]
        result = calorimeter_resolution.fit_resolution(points)
        self.assertEqual(result['ndof'], 0)
        self.assertTrue(any('degrees of freedom' in w for w in result['warnings']))

    def test_evaluation_outside_the_fitted_range_is_flagged(self):
        points = [[e, self._model(0.10, 0.20, 0.007, e)] for e in (1.0, 2.0, 5.0, 10.0)]
        path = self.write('narrow.json', json.dumps({'points': points}))
        outside = run_json(self, 'calorimeter_resolution.py', '--fit', path, '--energy', '100')
        self.assertTrue(outside['at_requested_energy']['extrapolated'])
        inside = run_json(self, 'calorimeter_resolution.py', '--fit', path, '--energy', '5')
        self.assertFalse(inside['at_requested_energy']['extrapolated'])
        evaluated = run_json(self, 'calorimeter_resolution.py', '--evaluate', '--stochastic', '0.1',
                             '--noise', '0.2', '--constant', '0.007', '--energy', '100',
                             '--valid-range', '1', '10')
        self.assertTrue(evaluated['extrapolated'])

    def test_null_points_are_a_json_error(self):
        path = self.write('null.json', '{"points": null}')
        proc = run('calorimeter_resolution.py', '--fit', path)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)
        payload = strict_json(proc.stdout)
        self.assertFalse(payload['ok'])
        self.assertIn('points', payload['error'])


class MultipleScatteringValidityTests(unittest.TestCase):
    def test_budget_outside_highland_range_is_flagged(self):
        for budget, inside in ((1e-4, False), (0.0357, True), (150.0, False)):
            with self.subTest(budget=budget):
                stack = {'field_tesla': 1.0, 'lever_arm_m': 1.0, 'point_resolution_um': 10.0,
                         'layers': [{'x_over_x0': budget / 4, 'measuring': True}] * 4}
                result = multiple_scattering.summarize(stack, 10.0)
                self.assertEqual(result['highland_validity']['inside'], inside)
                self.assertEqual(bool(result['warnings']), not inside)

    def test_docstring_states_the_resolution_coefficient_convention(self):
        self.assertIn('0.016', multiple_scattering.__doc__)


class GaisserHillasGuardTests(unittest.TestCase):
    def test_standard_age_is_reported_alongside_the_shifted_one(self):
        self.assertAlmostEqual(xmax_gaisser_hillas.shower_age_standard(400.0, 750.0),
                               3 * 400.0 / (400.0 + 1500.0), places=15)
        payload = run_json(self, 'xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750',
                           '--x0', '-60', '--lambda-param', '60', '--depths=-100,400')
        before, at_400 = payload['profile']
        self.assertIsNone(before['n'])
        self.assertAlmostEqual(at_400['shower_age'], 0.663, delta=1e-3)
        self.assertAlmostEqual(at_400['shower_age_standard'], 0.632, delta=1e-3)

    def test_small_lambda_does_not_overflow(self):
        payload = run_json(self, 'xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750',
                           '--x0', '-60', '--lambda-param', '0.5', '--depths', '700,750,800')
        self.assertAlmostEqual(payload['n_at_x_max_check'], 2e7, delta=1e-3)

    def test_non_finite_depths_are_rejected(self):
        proc = run('xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750', '--x0', '-60',
                   '--lambda-param', '60', '--depths', 'nan,inf')
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn('Traceback', proc.stderr)
        self.assertIs(json.loads(proc.stdout)['ok'], False)  # JSON error on stdout (DR-WP2-05)


class EdgeCaseCliTests(_TempFiles, unittest.TestCase):
    """Every script, edge-case input: stdout is strict JSON (or empty on an argparse rejection,
    which exits 2 with a usage message on stderr) and stderr never carries a traceback."""

    def cases(self):
        stack = ASSETS / 'detector-stack.example.json'
        huge_stack = self.write('huge_stack.json', json.dumps({
            'field_tesla': 1e308, 'lever_arm_m': 1e308, 'point_resolution_um': 1e308,
            'layers': [{'x_over_x0': 1e308, 'measuring': True}] * 3}))
        return [
            ('tag_and_probe_efficiency.py', '--pass-count', '0', '--total', '0'),
            ('tag_and_probe_efficiency.py', '--pass-count', '0', '--total', '0', '--level', '1.5'),
            ('cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K', '--momentum', '1.5425'),
            ('cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K', '--momentum', '1.6'),
            ('pid_separation_power.py', '--mode', 'dedx', '--species', 'd', 'He4', '--momentum', '2'),
            ('pid_separation_power.py', '--mode', 'dedx', '--species', 'pi', 'K', '--momentum', '3',
             '--material', 'argon', '--threshold', '2', '--relative-resolution', '0.05'),
            ('pid_separation_power.py', '--mode', 'dedx', '--species', 'e', 'pi', '--momentum', '0.5',
             '--material', 'argon'),
            ('pid_separation_power.py', '--mode', 'dedx', '--species', 'He4', 'p', '--momentum', '0.05',
             '--material', 'xenon'),
            ('pid_separation_power.py', '--mode', 'tof', '--species', 'pi', 'K', '--momentum', '1e308'),
            ('pileup_reweight.py', ASSETS / 'pileup-profiles.example.json'),
            ('pileup_reweight.py', self.write('pu_big.json', json.dumps(
                {'bin_centers': [0, 1], 'data_profile': [1e308, 1e308], 'mc_profile': [1, 1]}))),
            ('pileup_reweight.py', self.write('pu_big_centers.json', json.dumps(
                {'bin_centers': [1e308, 1e308], 'data_profile': [1, 1], 'mc_profile': [1, 1]}))),
            ('pileup_reweight.py', self.write('pu_sub.json', json.dumps(
                {'bin_centers': [0, 1], 'data_profile': [1, 1], 'mc_profile': [5e-324, 1]}))),
            ('pileup_reweight.py', self.write('pu_nan.json',
                                              '{"bin_centers": [0, NaN], "data_profile": [1, 1], '
                                              '"mc_profile": [1, 1]}')),
            ('calorimeter_resolution.py', '--fit', self.write('cal_null.json', '{"points": null}')),
            ('calorimeter_resolution.py', '--fit', self.write('cal_tiny.json', json.dumps(
                {'points': [[1e-200, 0.1], [1.0, 0.1], [10.0, 0.05], [100.0, 0.02]]}))),
            ('calorimeter_resolution.py', '--evaluate', '--stochastic', '0.1', '--noise', '0.2',
             '--constant', '0.01', '--energy', '1e-300'),
            ('toy_spectrometer.py', 'resolution', ASSETS / 'toy-spectrometer.fictional.json', '--species', 'p', '--rigidity', '1e308'),
            ('toy_spectrometer.py', 'resolution', ASSETS / 'toy-spectrometer.fictional.json', '--species', 'p', '--rigidity', '1e-308'),
            ('toy_spectrometer.py', 'resolution', ASSETS / 'toy-spectrometer.fictional.json', '--species', 'p', '--rigidity', 'nan'),
            ('toy_spectrometer.py', 'resolution', ASSETS / 'toy-spectrometer.fictional.json', '--species', 'xx', '--rigidity', '10'),
            ('propagate_scale_distortion.py', 'events', ASSETS / 'scale-distortion-events.example.csv', '--column',
             'x', '--signed', '--edges', '1', '2', '4', '--mode', 'inverse-offset', '--delta', '1e308'),
            ('propagate_scale_distortion.py', 'events', ASSETS / 'scale-distortion-events.example.csv', '--column',
             'x', '--signed', '--edges', '1', '2', '4', '--mode', 'scale', '--scale', 'nan'),
            ('propagate_scale_distortion.py', 'events', ASSETS / 'scale-distortion-events.example.csv', '--column',
             'x', '--edges', '1', '2', '4', '--mode', 'scale', '--scale', '0.01'),
            ('multiple_scattering.py', huge_stack),
            ('multiple_scattering.py', stack, '--rigidity', '1e308'),
            ('multiple_scattering.py', stack, '--rigidity', '1e-308'),
            ('xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750', '--x0', '-60',
             '--lambda-param', '0.5', '--depths', '400,750,900'),
            ('xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750', '--x0', '-60',
             '--lambda-param', '60', '--depths', 'nan,inf'),
            ('xmax_gaisser_hillas.py', '--n-max', '2e7', '--x-max', '750', '--x0', '-60',
             '--lambda-param', '60', '--depths=-100,400'),
            ('frontend_response.py', 'enc', '--capacitance', '1e308', '--en', '1e308', '--leakage', '1e308',
             '--peaking', '1e308'),
            ('frontend_response.py', 'enc', '--capacitance', 'nan', '--en', '1', '--leakage', '1',
             '--peaking', '25'),
            ('frontend_response.py', 'noise-rate', '--threshold', '0', '--peaking', '1e-308', '--order', '2',
             '--channels', '1e308', '--window', '1e308'),
            ('frontend_response.py', 'timing', '--rise', '1', '--snr', 'inf'),
            ('frontend_response.py', 'quantize', '--noise-lsb', '1e308'),
            ('frontend_response.py', 'pileup', '--rate', '1e308', '--mean-amp', '1e308', '--peaking', '1e308',
             '--bipolar'),
            ('frontend_response.py', 'sipm', '--cells', '1', '--npe', '1e308', '--crosstalk', '0.999999',
             '--dcr', '1e308', '--gate', '1e308'),
            ('frontend_response.py', 'ballistic', '--collection', '1e308', '--peaking', '1e-308'),
            ('frontend_response.py', 'deadtime', '--dead-time', '1e308', '--rate', '1e308',
             '--model', 'paralyzable'),
            ('frontend_response.py', 'cluster-noise', '--channels', '4', '--sigma', '1e308', '--rho', '1'),
        ]

    def test_all_scripts_emit_strict_json_and_no_traceback(self):
        covered = set()
        for script, *args in self.cases():
            covered.add(script)
            with self.subTest(script=script, args=[str(a) for a in args]):
                proc = run(script, *args)
                self.assertNotIn('Traceback', proc.stderr)
                if proc.returncode == 2 and not proc.stdout:
                    self.assertIn('error:', proc.stderr)  # argparse rejection
                    continue
                payload = strict_json(proc.stdout)
                self.assertIsInstance(payload, dict)
                if proc.returncode != 0:
                    self.assertIn('error', payload)
        self.assertEqual(covered, {p.name for p in SCRIPTS.glob('*.py')})


if __name__ == '__main__':
    unittest.main()
