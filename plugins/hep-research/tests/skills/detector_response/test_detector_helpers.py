"""Behavioral tests for histogram failures and analytic Poisson reference cases.

Run from the skill directory with python3 -m unittest discover -s tests -v.
Uses synthetic data and standard library only; no experiment files are needed.
"""
import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
ROOT = PLUGIN
for _skill in ('hep-computing', 'hep-analysis', 'detector-response'):
    sys.path.insert(0, str(PLUGIN / 'skills' / _skill / 'scripts'))
from audit_histograms import audit
from counting_reference import bayesian_upper, poisson_upper_tail
from tag_and_probe_efficiency import clopper_pearson, efficiency_bin
from pileup_reweight import compute_weights, normalize, profile_mean, reweighted_mean
from calorimeter_resolution import crossover_energies, evaluate, fit_resolution
from cherenkov_angle import (beta_resolution_from_angle, cherenkov_angle,
                             describe_species, photon_yield, saturation_angle,
                             threshold_momentum, track_angular_resolution)
from pid_separation_power import (MASSES_GEV, bethe_bloch_mev_per_g_cm2, kinematics,
                                  mass_from_beta, mass_resolution, resolve_mass,
                                  separation, separation_ceiling, time_of_flight_ns,
                                  tof_beta_resolution)
from multiple_scattering import (crossover_rigidity, highland_angle,
                                intrinsic_resolution_slope, load_stack,
                                maximum_detectable_rigidity, resolution_at,
                                scattering_resolution_term, summarize)


class HistogramTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((ROOT / 'skills/hep-computing/assets/histograms.example.json').read_text())
        self.hist = self.bundle['histograms']['synthetic_background']

    def test_good_input_not_mutated(self):
        previous = copy.deepcopy(self.bundle)
        self.assertEqual(audit(self.bundle), ([], []))
        self.assertEqual(previous, self.bundle)

    def test_signed_mc_not_poisson(self):
        self.hist['sumw'][0] = -2
        self.assertFalse(audit(self.bundle)[0])
        self.assertTrue(audit(self.bundle)[1])
        self.bundle['kind'] = 'poisson_expectation'
        self.assertTrue(audit(self.bundle)[0])

    def test_missing_and_mismatched_variation(self):
        del self.hist['variations']['scaleDown']
        self.hist['variations']['scaleUp']['edges'][1] = 40
        self.assertEqual(len(audit(self.bundle)[0]), 2)

    def test_nonfinite_variance_and_dimensions(self):
        for field, value in [('sumw', [float('nan'), 8]), ('sumw2', [-1, 10]), ('sumw2', [1]), ('edges', [0, 0, 100])]:
            with self.subTest(field=field, value=value):
                bundle = copy.deepcopy(self.bundle)
                bundle['histograms']['synthetic_background'][field] = value
                self.assertTrue(audit(bundle)[0])

    def test_malformed_types(self):
        for bundle in (None, [], {}, {'schema_version':1,'kind':'mc','histograms':{'bad':None}}):
            self.assertTrue(audit(bundle)[0])

    def test_bool_not_numeric(self):
        self.hist['sumw'][0] = True
        self.assertTrue(audit(self.bundle)[0])

    def test_identical_variation_warns(self):
        self.hist['variations']['scaleUp'] = {k: self.hist[k][:] for k in ('edges','sumw','sumw2')}
        self.assertFalse(audit(self.bundle)[0])
        self.assertTrue(audit(self.bundle)[1])

    def test_cli_success(self):
        result = subprocess.run([sys.executable, str(ROOT/'skills/hep-computing/scripts/audit_histograms.py'), str(ROOT/'skills/hep-computing/assets/histograms.example.json')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)['ok'])


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


class TagAndProbeTests(unittest.TestCase):
    def test_known_exact_intervals(self):
        # Textbook exact Clopper-Pearson 95% intervals; independently cross-checked
        # against scipy.stats.beta.ppf during development (scipy is not a runtime
        # dependency of this package, so the expected values are hardcoded here).
        lo, hi = clopper_pearson(0, 10, 0.95)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.30849710781876385, places=10)

        lo, hi = clopper_pearson(10, 10, 0.95)
        self.assertAlmostEqual(lo, 0.6915028921812392, places=10)
        self.assertEqual(hi, 1.0)

        lo, hi = clopper_pearson(5, 20, 0.95)
        self.assertAlmostEqual(lo, 0.08657146910143451, places=8)
        self.assertAlmostEqual(hi, 0.49104587170795455, places=8)

    def test_interval_widens_with_confidence_level(self):
        lo68, hi68 = clopper_pearson(30, 100, 0.68)
        lo95, hi95 = clopper_pearson(30, 100, 0.95)
        lo99, hi99 = clopper_pearson(30, 100, 0.99)
        self.assertLess(lo99, lo95)
        self.assertLess(lo95, lo68)
        self.assertLess(hi68, hi95)
        self.assertLess(hi95, hi99)

    def test_interval_contains_point_estimate(self):
        for k, n in ((0, 10), (5, 20), (92, 100), (1, 1), (0, 1), (50, 100)):
            with self.subTest(k=k, n=n):
                point = k / n
                lo, hi = clopper_pearson(k, n, 0.95)
                self.assertLessEqual(lo, point)
                self.assertLessEqual(point, hi)

    def test_invalid_input_rejected(self):
        for k, n in ((-1, 10), (11, 10), (1.5, 10), (True, 10), (1, -1), (1, 200001)):
            with self.subTest(k=k, n=n):
                with self.assertRaises(ValueError):
                    clopper_pearson(k, n)
        with self.assertRaises(ValueError):
            clopper_pearson(1, 10, level=1.0)

    def test_efficiency_bin_zero_total_is_nan_not_error(self):
        result = efficiency_bin(0, 0)
        self.assertNotEqual(result['efficiency'], result['efficiency'])  # NaN

    def test_cli_matches_library_result(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/tag_and_probe_efficiency.py'),
             '--pass-count', '92', '--total', '100'],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        expected_lo, expected_hi = clopper_pearson(92, 100)
        self.assertAlmostEqual(payload['lower'], expected_lo, places=10)
        self.assertAlmostEqual(payload['upper'], expected_hi, places=10)

    def test_cli_rejects_pass_greater_than_total(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/tag_and_probe_efficiency.py'),
             '--pass-count', '11', '--total', '10'],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('pass_count must be', result.stderr)


class PileupReweightTests(unittest.TestCase):
    def test_weights_reproduce_data_over_mc_ratio(self):
        weights, empty = compute_weights([0.2, 0.3, 0.5], [0.5, 0.3, 0.2])
        self.assertEqual(empty, [])
        for w, d, m in zip(weights, *[normalize(p)[0] for p in ([0.2, 0.3, 0.5], [0.5, 0.3, 0.2])]):
            self.assertAlmostEqual(w, d / m, places=12)

    def test_empty_mc_bin_with_data_is_flagged_not_inf(self):
        weights, empty = compute_weights([0.1, 0.9], [1.0, 0.0])
        self.assertEqual(empty, [1])
        self.assertIsNone(weights[1])
        self.assertIsNotNone(weights[0])

    def test_empty_mc_bin_without_data_is_not_flagged(self):
        # MC has zero probability in a bin, but so does data - nothing to reweight
        # there, so it should not be reported as an error.
        weights, empty = compute_weights([0.5, 0.0, 0.5], [0.4, 0.0, 0.6])
        self.assertEqual(empty, [])
        self.assertIsNone(weights[1])

    def test_reweighted_mean_matches_data_mean_closure(self):
        bin_centers = list(range(10))
        data_profile = [1, 2, 3, 4, 5, 4, 3, 2, 1, 1]
        mc_profile = [5, 4, 3, 2, 1, 1, 1, 1, 1, 1]
        weights, empty = compute_weights(data_profile, mc_profile)
        self.assertEqual(empty, [])
        reweighted = reweighted_mean(weights, mc_profile, bin_centers)
        expected = profile_mean(data_profile, bin_centers)
        self.assertAlmostEqual(reweighted, expected, places=10)

    def test_normalize_rejects_negative_or_all_zero(self):
        with self.assertRaises(ValueError):
            normalize([0.1, -0.2, 0.5])
        with self.assertRaises(ValueError):
            normalize([0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            normalize([])

    def test_mismatched_lengths_rejected(self):
        with self.assertRaises(ValueError):
            compute_weights([0.5, 0.5], [1.0])

    def test_cli_closure_on_shipped_example(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/pileup_reweight.py'),
             str(ROOT / 'skills/detector-response/assets/pileup-profiles.example.json')],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['ok'])
        self.assertAlmostEqual(payload['mc_mean_after_reweight'], payload['data_mean'], places=6)

    def test_cli_flags_missing_mc_coverage(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as handle:
            json.dump({'bin_centers': [0, 1, 2], 'data_profile': [0.2, 0.3, 0.5], 'mc_profile': [0.6, 0.4, 0.0]}, handle)
            path = handle.name
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'skills/detector-response/scripts/pileup_reweight.py'), path],
                capture_output=True, text=True,
            )
        finally:
            os.unlink(path)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['empty_mc_bins_with_data'], [2])

    def test_cli_missing_file_fails_cleanly(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/pileup_reweight.py'), '/tmp/does-not-exist-pileup-bundle.json'],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload['ok'])
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()


class MultipleScatteringTests(unittest.TestCase):
    """Cross-checks against the closed-form PDG Highland and Gluckstern expressions,
    recomputed independently here rather than by calling the module under test."""

    def setUp(self):
        self.stack = load_stack(ROOT / 'skills/detector-response/assets/detector-stack.example.json')

    def test_highland_matches_closed_form(self):
        # theta0 = (0.0136/(beta p)) sqrt(f) [1 + 0.038 ln(f z^2/beta^2)]
        for rigidity, budget, beta in ((100.0, 0.0357, 1.0), (5.0, 0.01, 0.8), (1.0, 0.2, 1.0)):
            expected = ((0.0136 / (beta * rigidity)) * math.sqrt(budget)
                        * (1.0 + 0.038 * math.log(budget / (beta * beta))))
            self.assertAlmostEqual(highland_angle(rigidity, budget, beta), expected, places=15)

    def test_highland_scales_inversely_with_rigidity(self):
        # The prefactor is 1/(beta p), so doubling rigidity halves the angle exactly.
        self.assertAlmostEqual(highland_angle(200.0, 0.05) * 2.0,
                               highland_angle(100.0, 0.05), places=15)

    def test_highland_scales_as_sqrt_thickness_up_to_log(self):
        # Quadrupling x/X0 doubles sqrt(x/X0); the residual difference is the log term.
        thin = highland_angle(10.0, 0.01)
        thick = highland_angle(10.0, 0.04)
        self.assertGreater(thick, 2.0 * thin)  # log term adds on top of the sqrt scaling
        self.assertLess(thick, 2.6 * thin)

    def test_charge_enters_only_through_the_logarithm(self):
        # p = z R cancels the explicit z in the prefactor; only ln(f z^2) survives.
        singly = highland_angle(10.0, 0.05, 1.0, 1)
        doubly = highland_angle(10.0, 0.05, 1.0, 2)
        expected = ((0.0136 / 10.0) * math.sqrt(0.05)
                    * (1.0 + 0.038 * math.log(0.05 * 4)))
        self.assertAlmostEqual(doubly, expected, places=15)
        self.assertGreater(doubly, singly)

    def test_zero_thickness_gives_zero_angle(self):
        self.assertEqual(highland_angle(10.0, 0.0), 0.0)

    def test_negative_log_correction_is_clamped_not_negative(self):
        # For extremely thin layers 1 + 0.038 ln(f) goes negative; an RMS may not.
        self.assertEqual(highland_angle(10.0, 1e-14), 0.0)

    def test_scattering_term_matches_closed_form(self):
        expected = 0.0136 * math.sqrt(0.0357) / (0.299792458 * 1.0 * 0.8 * 1.0)
        self.assertAlmostEqual(scattering_resolution_term(0.0357, 0.8, 1.0), expected, places=15)

    def test_scattering_term_is_rigidity_independent(self):
        # It carries no rigidity argument at all; this pins the physics claim in the docs.
        term = scattering_resolution_term(0.0357, 0.8, 1.0)
        self.assertAlmostEqual(resolution_at(1.0, term, 0.0), term, places=15)
        self.assertAlmostEqual(resolution_at(1000.0, term, 0.0), term, places=15)

    def test_gluckstern_slope_matches_closed_form(self):
        expected = 10e-6 * math.sqrt(720.0 / 12.0) / (0.299792458 * 0.8 * 1.0 * 1.0)
        self.assertAlmostEqual(intrinsic_resolution_slope(10.0, 8, 0.8, 1.0), expected, places=18)

    def test_intrinsic_term_is_linear_in_rigidity(self):
        slope = intrinsic_resolution_slope(10.0, 8, 0.8, 1.0)
        self.assertAlmostEqual(resolution_at(200.0, 0.0, slope),
                               2.0 * resolution_at(100.0, 0.0, slope), places=15)

    def test_longer_lever_arm_helps_intrinsic_quadratically(self):
        short = intrinsic_resolution_slope(10.0, 8, 0.8, 1.0)
        long_arm = intrinsic_resolution_slope(10.0, 8, 0.8, 2.0)
        self.assertAlmostEqual(short / long_arm, 4.0, places=12)

    def test_crossover_is_where_terms_are_equal(self):
        ms = scattering_resolution_term(0.0357, 0.8, 1.0)
        slope = intrinsic_resolution_slope(10.0, 8, 0.8, 1.0)
        crossover = crossover_rigidity(ms, slope)
        self.assertAlmostEqual(slope * crossover, ms, places=15)

    def test_mdr_is_where_total_resolution_is_unity(self):
        ms = scattering_resolution_term(0.0357, 0.8, 1.0)
        slope = intrinsic_resolution_slope(10.0, 8, 0.8, 1.0)
        mdr = maximum_detectable_rigidity(ms, slope)
        self.assertAlmostEqual(resolution_at(mdr, ms, slope), 1.0, places=12)

    def test_mdr_undefined_when_scattering_alone_exceeds_unity(self):
        self.assertIsNone(maximum_detectable_rigidity(1.5, 1e-4))

    def test_summarize_uses_measuring_layers_and_full_budget(self):
        result = summarize(self.stack, 100.0)
        # All ten layers scatter; only the eight flagged ones measure.
        self.assertEqual(result['layers'], 10)
        self.assertEqual(result['measuring_layers'], 8)
        self.assertAlmostEqual(result['total_x_over_x0'], 0.0357, places=12)
        self.assertEqual(result['dominant_term'], 'intrinsic')

    def test_dominant_term_flips_below_crossover(self):
        crossover = summarize(self.stack, 100.0)['crossover_rigidity_gv']
        self.assertEqual(summarize(self.stack, crossover * 0.5)['dominant_term'], 'scattering')
        self.assertEqual(summarize(self.stack, crossover * 2.0)['dominant_term'], 'intrinsic')

    def test_total_is_quadrature_sum_of_the_two_terms(self):
        result = summarize(self.stack, 100.0)
        self.assertAlmostEqual(
            result['total_relative_resolution'],
            math.hypot(result['scattering_term'], result['intrinsic_term']), places=15)

    def test_slow_particles_scatter_more(self):
        fast = summarize(self.stack, 1.0, beta=1.0)['scattering_term']
        slow = summarize(self.stack, 1.0, beta=0.5)['scattering_term']
        self.assertAlmostEqual(slow / fast, 2.0, places=12)

    def test_invalid_input_raises_value_error(self):
        for bad in (lambda: highland_angle(-1.0, 0.01),
                    lambda: highland_angle(10.0, -0.01),
                    lambda: highland_angle(10.0, 0.01, 1.5),
                    lambda: highland_angle(10.0, 0.01, 0.0),
                    lambda: intrinsic_resolution_slope(10.0, 2, 0.8, 1.0),
                    lambda: intrinsic_resolution_slope(0.0, 8, 0.8, 1.0),
                    lambda: scattering_resolution_term(0.01, 0.0, 1.0)):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_reports_error_without_traceback(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
            handle.write(json.dumps({'field_tesla': 1.0, 'lever_arm_m': 1.0}))
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'skills/detector-response/scripts/multiple_scattering.py'), path],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertIn('point_resolution_um', proc.stderr)
        finally:
            os.unlink(path)

    def test_cli_runs_on_shipped_asset(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/multiple_scattering.py'),
             str(ROOT / 'skills/detector-response/assets/detector-stack.example.json'), '--rigidity', '100'],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertAlmostEqual(payload['total_x_over_x0'], 0.0357, places=12)


class CalorimeterResolutionTests(unittest.TestCase):
    """Closure against exactly-generated points, plus the analytic crossover relations."""

    TRUE = {'stochastic': 0.10, 'noise': 0.20, 'constant': 0.007}

    def setUp(self):
        self.asset = json.loads(
            (ROOT / 'skills/detector-response/assets/calorimeter-response.example.json').read_text())

    @staticmethod
    def _generate(a, b, c, energies):
        return [[e, math.sqrt(a * a / e + b * b / (e * e) + c * c)] for e in energies]

    def test_shipped_asset_declares_its_generating_parameters(self):
        self.assertEqual(self.asset['generated_from'], self.TRUE)

    def test_fit_recovers_generating_parameters_exactly(self):
        result = fit_resolution(self.asset['points'])
        for name, true_value in self.TRUE.items():
            self.assertAlmostEqual(result[name], true_value, places=10)
        self.assertEqual(result['negative_squared_terms'], [])
        self.assertLess(result['max_abs_residual_in_squared_resolution'], 1e-14)

    def test_fit_recovers_other_parameter_sets(self):
        for a, b, c in ((0.03, 0.05, 0.005), (0.50, 1.20, 0.030), (0.15, 0.00, 0.010)):
            points = self._generate(a, b, c, [1.0, 3.0, 10.0, 30.0, 100.0, 300.0])
            result = fit_resolution(points)
            # Tolerance scales with the coefficient: a term that is genuinely zero is
            # recovered to ~1e-8 absolute, limited by the conditioning of the 1/E^2
            # column, not to an arbitrary number of decimal places.
            for name, true_value in (('stochastic', a), ('noise', b), ('constant', c)):
                self.assertAlmostEqual(result[name], true_value,
                                       delta=max(1e-7, abs(true_value) * 1e-8))

    def test_fit_is_exact_with_the_minimum_three_energies(self):
        # Three unknowns, three distinct energies: the system is determined, so the
        # least-squares solution must pass through every point.
        points = self._generate(0.10, 0.20, 0.007, [1.0, 10.0, 100.0])
        result = fit_resolution(points)
        self.assertAlmostEqual(result['stochastic'], 0.10, places=8)
        self.assertLess(result['max_abs_residual_in_squared_resolution'], 1e-16)

    def test_two_distinct_energies_are_rejected(self):
        points = self._generate(0.10, 0.20, 0.007, [10.0, 100.0, 100.0, 10.0])
        with self.assertRaises(ValueError):
            fit_resolution(points)

    def test_negative_squared_term_is_flagged_not_square_rooted(self):
        # A resolution that keeps falling faster than 1/sqrt(E) has no room for a
        # positive constant term; the fit must say so rather than emit a NaN.
        points = [[1.0, 0.100], [10.0, 0.028], [100.0, 0.008], [1000.0, 0.002]]
        result = fit_resolution(points)
        self.assertIn('constant', result['negative_squared_terms'])
        self.assertIsNone(result['constant'])
        self.assertLess(result['constant_squared'], 0.0)

    def test_evaluate_matches_the_closed_form(self):
        got = evaluate(0.10, 0.20, 0.007, 100.0)
        expected = math.sqrt(0.01 / 100.0 + 0.04 / 10000.0 + 0.007 ** 2)
        self.assertAlmostEqual(got['relative_resolution'], expected, places=15)
        self.assertAlmostEqual(got['absolute_resolution_gev'], expected * 100.0, places=15)

    def test_constant_term_sets_the_high_energy_floor(self):
        # As E grows the relative resolution must approach c from above, never below.
        for energy in (1e3, 1e5, 1e7):
            resolution = evaluate(0.10, 0.20, 0.007, energy)['relative_resolution']
            self.assertGreater(resolution, 0.007)
        self.assertAlmostEqual(evaluate(0.10, 0.20, 0.007, 1e12)['relative_resolution'],
                               0.007, places=11)

    def test_dominant_term_changes_with_energy(self):
        self.assertEqual(evaluate(0.10, 0.20, 0.007, 0.5)['dominant_term'], 'noise')
        self.assertEqual(evaluate(0.10, 0.20, 0.007, 100.0)['dominant_term'], 'stochastic')
        self.assertEqual(evaluate(0.10, 0.20, 0.007, 1e5)['dominant_term'], 'constant')

    def test_crossovers_are_where_contributions_are_equal(self):
        a, b, c = 0.10, 0.20, 0.007
        crossings = crossover_energies(a, b, c)
        self.assertAlmostEqual(crossings['noise_equals_stochastic_gev'], b * b / (a * a), places=12)
        self.assertAlmostEqual(crossings['stochastic_equals_constant_gev'], a * a / (c * c), places=9)
        self.assertAlmostEqual(crossings['noise_equals_constant_gev'], b / c, places=12)
        for key, energy in crossings.items():
            terms = evaluate(a, b, c, energy)['term_contributions_squared']
            first, second = key.split('_equals_')[0], key.split('_equals_')[1].replace('_gev', '')
            self.assertAlmostEqual(terms[first], terms[second], places=12)

    def test_crossovers_are_none_when_a_term_is_absent(self):
        crossings = crossover_energies(0.10, 0.20, 0.0)
        self.assertIsNone(crossings['stochastic_equals_constant_gev'])
        self.assertIsNone(crossings['noise_equals_constant_gev'])

    def test_invalid_input_raises_value_error(self):
        for bad in (lambda: fit_resolution([[1.0, 0.1], [10.0, 0.05]]),
                    lambda: fit_resolution([[0.0, 0.1], [10.0, 0.05], [100.0, 0.02]]),
                    lambda: fit_resolution([[1.0, -0.1], [10.0, 0.05], [100.0, 0.02]]),
                    lambda: fit_resolution([[1.0], [10.0, 0.05], [100.0, 0.02]]),
                    lambda: evaluate(-0.1, 0.2, 0.007, 100.0),
                    lambda: evaluate(0.1, 0.2, 0.007, 0.0)):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_fit_on_shipped_asset(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/calorimeter_resolution.py'),
             '--fit', str(ROOT / 'skills/detector-response/assets/calorimeter-response.example.json')],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertAlmostEqual(payload['stochastic'], 0.10, places=10)

    def test_cli_reports_error_without_traceback(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
            handle.write(json.dumps({'points': [[1.0, 0.1], [10.0, 0.05]]}))
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, str(ROOT / 'skills/detector-response/scripts/calorimeter_resolution.py'), '--fit', path],
                capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertIn('three distinct energies', proc.stderr)
        finally:
            os.unlink(path)


class PidSeparationTests(unittest.TestCase):
    """Analytic cross-checks of the kinematics, TOF timing, and Bethe-Bloch behavior."""

    def test_kinematics_matches_closed_form(self):
        for momentum, mass in ((2.0, 0.13957039), (0.5, 0.93827209), (100.0, 0.000511)):
            kin = kinematics(momentum, mass)
            energy = math.sqrt(momentum ** 2 + mass ** 2)
            self.assertAlmostEqual(kin['beta'], momentum / energy, places=15)
            self.assertAlmostEqual(kin['gamma'], energy / mass, places=12)
            # The defining identity p = m beta gamma must hold.
            self.assertAlmostEqual(mass * kin['beta'] * kin['gamma'], momentum, places=12)

    def test_mass_from_beta_inverts_kinematics(self):
        for momentum, mass in ((2.0, 0.493677), (0.8, 0.93827209), (5.0, 0.13957039)):
            beta = kinematics(momentum, mass)['beta']
            self.assertAlmostEqual(mass_from_beta(momentum, beta), mass, places=10)

    def test_mass_resolution_carries_the_gamma_squared_factor(self):
        # dm/m = gamma^2 dbeta/beta is the claim the reference makes; pin it exactly.
        momentum, mass, relative = 5.0, 0.93827209, 1e-3
        gamma = kinematics(momentum, mass)['gamma']
        got = mass_resolution(momentum, mass, relative)
        self.assertAlmostEqual(got['relative_mass_resolution'], gamma ** 2 * relative, places=15)
        self.assertAlmostEqual(got['absolute_mass_resolution_gev'],
                               gamma ** 2 * relative * mass, places=15)

    def test_mass_resolution_degrades_quadratically_with_gamma(self):
        low = mass_resolution(1.0, 0.93827209, 1e-3)['relative_mass_resolution']
        high = mass_resolution(10.0, 0.93827209, 1e-3)['relative_mass_resolution']
        ratio = (kinematics(10.0, 0.93827209)['gamma'] / kinematics(1.0, 0.93827209)['gamma']) ** 2
        self.assertAlmostEqual(high / low, ratio, places=10)

    def test_time_of_flight_matches_path_over_beta_c(self):
        time_ns = time_of_flight_ns(2.0, 0.493677, 1.2)
        beta = kinematics(2.0, 0.493677)['beta']
        self.assertAlmostEqual(time_ns, 1.2 / (beta * 299792458.0) * 1e9, places=12)

    def test_heavier_species_arrives_later(self):
        self.assertGreater(time_of_flight_ns(2.0, MASSES_GEV['K'], 1.2),
                           time_of_flight_ns(2.0, MASSES_GEV['pi'], 1.2))

    def test_tof_beta_resolution_matches_closed_form(self):
        # dbeta/beta = beta c sigma_t / L
        beta = kinematics(2.0, MASSES_GEV['pi'])['beta']
        expected = beta * 299792458.0 * 60e-12 / 1.2
        self.assertAlmostEqual(tof_beta_resolution(2.0, MASSES_GEV['pi'], 1.2, 60.0),
                               expected, places=15)

    def test_tof_separation_falls_roughly_as_inverse_momentum_squared(self):
        options = {'path_m': 1.2, 'time_resolution_ps': 60.0}
        low = separation('tof', MASSES_GEV['pi'], MASSES_GEV['K'], 4.0, **options)['n_sigma']
        high = separation('tof', MASSES_GEV['pi'], MASSES_GEV['K'], 8.0, **options)['n_sigma']
        # Doubling the momentum should cost roughly a factor four in separation.
        self.assertGreater(low / high, 3.5)
        self.assertLess(low / high, 4.5)

    def test_tof_ceiling_is_where_separation_equals_threshold(self):
        options = {'path_m': 1.2, 'time_resolution_ps': 60.0}
        ceiling = separation_ceiling('tof', MASSES_GEV['pi'], MASSES_GEV['K'], 3.0, **options)
        at_ceiling = separation('tof', MASSES_GEV['pi'], MASSES_GEV['K'], ceiling, **options)
        self.assertAlmostEqual(at_ceiling['n_sigma'], 3.0, places=6)

    def test_longer_path_and_better_timing_raise_the_ceiling(self):
        base = {'path_m': 1.2, 'time_resolution_ps': 60.0}
        longer = {'path_m': 2.4, 'time_resolution_ps': 60.0}
        faster = {'path_m': 1.2, 'time_resolution_ps': 30.0}
        args = ('tof', MASSES_GEV['pi'], MASSES_GEV['K'], 3.0)
        self.assertGreater(separation_ceiling(*args, **longer),
                           separation_ceiling(*args, **base))
        self.assertGreater(separation_ceiling(*args, **faster),
                           separation_ceiling(*args, **base))

    def test_ceiling_is_none_when_never_separated(self):
        # A 10 ns timing resolution cannot separate pions from kaons anywhere.
        options = {'path_m': 1.2, 'time_resolution_ps': 10000.0}
        self.assertIsNone(
            separation_ceiling('tof', MASSES_GEV['pi'], MASSES_GEV['K'], 3.0, **options))

    def test_bethe_bloch_minimum_sits_near_beta_gamma_three(self):
        # The ionization minimum is a textbook feature near beta*gamma ~ 3-4.
        scan = [(bethe_bloch_mev_per_g_cm2(p / 1000.0, MASSES_GEV['mu'])['mev_per_g_cm2'],
                 bethe_bloch_mev_per_g_cm2(p / 1000.0, MASSES_GEV['mu'])['beta_gamma'])
                for p in range(50, 3000, 5)]
        minimum_loss, minimum_bg = min(scan)
        self.assertGreater(minimum_bg, 2.5)
        self.assertLess(minimum_bg, 4.5)
        # Silicon minimum ionization is ~1.66 MeV cm^2/g; without the density-effect
        # correction this evaluation should land close to, and slightly above, that.
        self.assertGreater(minimum_loss, 1.6)
        self.assertLess(minimum_loss, 1.8)

    def test_bethe_bloch_rises_steeply_below_the_minimum(self):
        slow = bethe_bloch_mev_per_g_cm2(0.1, MASSES_GEV['p'])['mev_per_g_cm2']
        minimum = bethe_bloch_mev_per_g_cm2(3.0, MASSES_GEV['p'])['mev_per_g_cm2']
        self.assertGreater(slow, 5.0 * minimum)

    def test_bethe_bloch_scales_with_charge_squared(self):
        singly = bethe_bloch_mev_per_g_cm2(2.0, MASSES_GEV['p'], 'silicon', 1)['mev_per_g_cm2']
        doubly = bethe_bloch_mev_per_g_cm2(2.0, MASSES_GEV['p'], 'silicon', 2)['mev_per_g_cm2']
        self.assertAlmostEqual(doubly / singly, 4.0, places=9)

    def test_bethe_bloch_flags_the_omitted_density_effect(self):
        result = bethe_bloch_mev_per_g_cm2(50.0, MASSES_GEV['pi'])
        self.assertTrue(result['density_effect_omitted'])
        self.assertTrue(result['in_relativistic_rise'])

    def test_velocity_mode_uses_the_supplied_resolution(self):
        result = separation('velocity', MASSES_GEV['pi'], MASSES_GEV['K'], 10.0,
                            relative_beta_resolution=1e-3)
        beta_a = kinematics(10.0, MASSES_GEV['pi'])['beta']
        beta_b = kinematics(10.0, MASSES_GEV['K'])['beta']
        self.assertAlmostEqual(result['n_sigma'],
                               abs(beta_a - beta_b) / (1e-3 * beta_a), places=9)

    def test_resolve_mass_accepts_names_and_numbers(self):
        self.assertEqual(resolve_mass('p'), MASSES_GEV['p'])
        self.assertAlmostEqual(resolve_mass('1.25'), 1.25, places=15)
        with self.assertRaises(ValueError):
            resolve_mass('gluino')

    def test_invalid_input_raises_value_error(self):
        for bad in (lambda: kinematics(-1.0, 0.1),
                    lambda: kinematics(1.0, 0.0),
                    lambda: mass_from_beta(1.0, 1.0),
                    lambda: mass_from_beta(1.0, 0.0),
                    lambda: bethe_bloch_mev_per_g_cm2(1.0, 0.1, 'unobtainium'),
                    lambda: separation('psychic', 0.1, 0.2, 1.0)):
            with self.assertRaises(ValueError):
                bad()

    def test_cli_runs_and_reports_a_ceiling(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/pid_separation_power.py'),
             '--mode', 'tof', '--species', 'pi', 'K', '--momentum', '2.0',
             '--path', '1.2', '--time-resolution', '60'],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertGreater(payload['n_sigma'], 0.0)
        self.assertGreater(payload['separation_ceiling_gev'], 0.0)

    def test_cli_rejects_identical_species_without_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/pid_separation_power.py'),
             '--mode', 'tof', '--species', 'pi', 'pi'],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)


class CherenkovTests(unittest.TestCase):
    """Threshold, saturation, and error-propagation checks against closed forms."""

    INDEX = 1.05

    def test_threshold_matches_closed_form(self):
        for name in ('pi', 'K', 'p'):
            expected = MASSES_GEV[name] / math.sqrt(self.INDEX ** 2 - 1.0)
            self.assertAlmostEqual(threshold_momentum(MASSES_GEV[name], self.INDEX),
                                   expected, places=12)

    def test_threshold_is_exactly_where_beta_equals_one_over_n(self):
        mass = MASSES_GEV['K']
        threshold = threshold_momentum(mass, self.INDEX)
        self.assertAlmostEqual(kinematics(threshold, mass)['beta'], 1.0 / self.INDEX, places=12)
        # At threshold the angle is zero, so no ring: the function returns None.
        self.assertIsNone(cherenkov_angle(threshold * 0.999, mass, self.INDEX))

    def test_heavier_species_have_higher_thresholds(self):
        thresholds = [threshold_momentum(MASSES_GEV[n], self.INDEX) for n in ('pi', 'K', 'p')]
        self.assertEqual(thresholds, sorted(thresholds))

    def test_saturation_angle_matches_arccos_one_over_n(self):
        self.assertAlmostEqual(saturation_angle(self.INDEX), math.acos(1.0 / self.INDEX), places=15)

    def test_angle_approaches_saturation_at_high_momentum(self):
        far = cherenkov_angle(1e6, MASSES_GEV['pi'], self.INDEX)
        self.assertAlmostEqual(far, saturation_angle(self.INDEX), places=10)
        self.assertLess(far, saturation_angle(self.INDEX))

    def test_angle_matches_arccos_one_over_n_beta(self):
        beta = kinematics(10.0, MASSES_GEV['K'])['beta']
        self.assertAlmostEqual(cherenkov_angle(10.0, MASSES_GEV['K'], self.INDEX),
                               math.acos(1.0 / (self.INDEX * beta)), places=15)

    def test_photon_yield_follows_sin_squared(self):
        angle = 0.3
        self.assertAlmostEqual(photon_yield(angle, 2.0, 100.0),
                               100.0 * 2.0 * math.sin(angle) ** 2, places=12)
        # Yield vanishes at threshold, where the angle is zero.
        self.assertEqual(photon_yield(0.0, 2.0, 100.0), 0.0)

    def test_track_resolution_improves_as_one_over_sqrt_photons(self):
        self.assertAlmostEqual(track_angular_resolution(5e-3, 25) * 5.0,
                               track_angular_resolution(5e-3, 1), places=15)

    def test_beta_resolution_uses_tangent_of_the_angle(self):
        self.assertAlmostEqual(beta_resolution_from_angle(0.3, 1e-3),
                               math.tan(0.3) * 1e-3, places=15)

    def test_below_threshold_species_reports_no_ring(self):
        record = describe_species(2.0, MASSES_GEV['p'], self.INDEX, 2.0, 100.0, 5e-3)
        self.assertFalse(record['above_threshold'])
        self.assertNotIn('cherenkov_angle_rad', record)
        self.assertIn('note', record)

    def test_mass_resolution_degrades_with_gamma_squared(self):
        low = describe_species(5.0, MASSES_GEV['pi'], self.INDEX, 2.0, 100.0, 5e-3)
        high = describe_species(50.0, MASSES_GEV['pi'], self.INDEX, 2.0, 100.0, 5e-3)
        self.assertGreater(high['relative_mass_resolution'], low['relative_mass_resolution'])

    def test_index_must_exceed_one(self):
        for bad_index in (1.0, 0.9, -1.0):
            with self.assertRaises(ValueError):
                saturation_angle(bad_index)

    def test_cli_reports_separation_and_thresholds(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/cherenkov_angle.py'),
             '--index', '1.05', '--species', 'pi', 'K', '--momentum', '10'],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertGreater(payload['n_sigma'], 0.0)
        self.assertAlmostEqual(payload['saturation_angle_mrad'],
                               math.acos(1 / 1.05) * 1000.0, places=9)

    def test_cli_rejects_index_below_one_without_traceback(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / 'skills/detector-response/scripts/cherenkov_angle.py'),
             '--index', '0.9', '--species', 'pi', 'K'],
            capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('Traceback', proc.stderr)
