"""Tests for the sampled-waveform, Landau and hit-efficiency parts of frontend_response.py.

Oracles, each independent of the code under test:
- analytic: the closed-form pulse autocorrelation against trapezoid integration; the optimal-filter stationarity
  conditions (w . g = 1 and R w parallel to g); the Gaussian-signal efficiency in closed form; the
  threshold-spread average of the Rice rate against a numerical average over thresholds;
- independent implementation: the Landau density by the oscillatory integral
  (1/pi) int exp(-t ln t - lambda t) sin(pi t) dt (trapezoid, standard library); values recorded from SciPy 1.18.1
  (scipy.stats.landau, which is the stable law S1(1, 1, 1, 0): phi(lambda) = landau.pdf with loc ln(pi/2) and
  scale pi/2) and from scipy.integrate.quad of the efficiency integral; a NumPy/SciPy Monte Carlo of a joint amplitude
  and time least-squares fit (4000 pulses, recorded below);
- the page's own worked numbers (front-end-electronics-and-signal-processing.md, optimal filter and phase error).
Standard library only.
"""
import contextlib
import io
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / 'skills' / 'hep-detector' / 'scripts' / 'frontend_response.py'
sys.path.insert(0, str(SCRIPT.parent))
import frontend_response as fr  # noqa: E402


def trapezoid(f, a, b, steps):
    h = (b - a) / steps
    return h * (0.5 * f(a) + 0.5 * f(b) + sum(f(a + i * h) for i in range(1, steps)))


def landau_direct(lam, t_max=60.0, steps=200000):
    """Independent Landau density: the oscillatory integral, trapezoid in t (moderate lambda only)."""
    def f(t):
        return math.exp(-t * math.log(t) - lam * t) * math.sin(math.pi * t) if t > 0 else 0.0
    return trapezoid(f, 0.0, t_max, steps) / math.pi


class PulseAutocorrelation(unittest.TestCase):
    def test_closed_form_matches_numerical_integration(self):
        for n in (1, 2, 4):
            tau = 10.0
            for delta in (0.0, 7.0, 25.0, 60.0):
                num = trapezoid(lambda t: fr.pulse(t, n, tau) * fr.pulse(t + delta, n, tau), 0, 600, 60000)
                self.assertAlmostEqual(fr.pulse_autocorrelation(delta, n, tau), num, delta=1e-6 * tau)

    def test_zero_lag_is_int_g2(self):
        for n in (1, 3, 6):
            self.assertAlmostEqual(fr.pulse_autocorrelation(0.0, n, 2.5), fr.shaper_integrals(n, 2.5)['int_g2'],
                                   places=12)


class OptimalFilter(unittest.TestCase):
    def test_reference_example_correlated_noise(self):
        # page: CR-RC, t_p 25 ns, 5 samples every 25 ns from 15 ns before the peak, rho 0.6
        r = fr.optimal_filter(1, 25, 25, 5, -15, rho=0.6)
        self.assertAlmostEqual(r['sigma_template_uncorrelated'], 1.12, delta=0.005)
        self.assertAlmostEqual(r['sigma_largest_sample'], 1.07, delta=0.005)
        self.assertAlmostEqual(r['sigma_optimal'], 1.04, delta=0.005)

    def test_reference_phase_bias(self):
        # page: CR-RC^4, t_p 45 ns, white noise, samples one before to three after the peak
        r = fr.optimal_filter(4, 45, 25, 5, -25, phase_errors_ns=(-5, -2, 2, 5))
        got = {b['phase_error_ns']: 100 * b['optimal'] for b in r['relative_bias_from_phase_error']}
        self.assertAlmostEqual(got[-2], -0.04, delta=0.005)
        self.assertAlmostEqual(got[2], -0.33, delta=0.01)
        self.assertAlmostEqual(got[-5], -0.79, delta=0.01)
        self.assertAlmostEqual(got[5], -1.54, delta=0.01)
        # correlated noise, samples two before to two after: +0.9 % / -1.8 % at -/+2 ns, -5.8 % at 5 ns
        r = fr.optimal_filter(4, 45, 25, 5, -50, rho=0.6, phase_errors_ns=(-2, 2, 5))
        got = {b['phase_error_ns']: 100 * b['optimal'] for b in r['relative_bias_from_phase_error']}
        self.assertAlmostEqual(got[-2], 0.93, delta=0.01)
        self.assertAlmostEqual(got[2], -1.79, delta=0.01)
        self.assertAlmostEqual(got[5], -5.81, delta=0.01)

    def test_stationarity_and_unbiasedness(self):
        r = fr.optimal_filter(2, 30, 10, 8, -20, rho=0.4, pileup_rate_hz=5e6, pileup_rms=4.0)
        g, w = r['pulse_samples'], r['weights_optimal']
        self.assertAlmostEqual(sum(a * b for a, b in zip(w, g)), 1.0, places=12)
        times = r['sample_times_ns']
        cov = fr._noise_covariance(times, 2, 15.0, 0.4, 5e6, 4.0)
        rw = [sum(cov[i][j] * w[j] for j in range(len(w))) for i in range(len(w))]
        ratio = [a / b for a, b in zip(rw, g)]
        for x in ratio:
            self.assertAlmostEqual(x, ratio[0], places=9)  # R w = lambda g: the Lagrange condition
        self.assertAlmostEqual(ratio[0], r['sigma_optimal'] ** 2, places=9)
        # the optimum is no worse than the two other estimators
        self.assertLessEqual(r['sigma_optimal'], r['sigma_template_uncorrelated'] + 1e-12)
        self.assertLessEqual(r['sigma_optimal'], r['sigma_largest_sample'] + 1e-12)

    def test_white_noise_template_is_optimal(self):
        r = fr.optimal_filter(3, 40, 20, 6, -40)
        self.assertAlmostEqual(r['sigma_optimal'], r['sigma_template_uncorrelated'], places=12)
        self.assertAlmostEqual(r['sigma_optimal'], 1 / math.sqrt(sum(x * x for x in r['pulse_samples'])), places=12)

    def test_pileup_noise_follows_campbell(self):
        r = fr.optimal_filter(1, 25, 25, 1, 0, pileup_rate_hz=1e7, pileup_rms=2.0)
        expected = math.sqrt(1e7 * 4.0 * fr.shaper_integrals(1, 25e-9)['int_g2'])
        self.assertAlmostEqual(r['pileup_sigma_per_sample'], expected, places=12)
        self.assertAlmostEqual(r['sigma_optimal'], math.sqrt(1 + expected ** 2), places=12)

    def test_joint_amplitude_and_time_errors_match_monte_carlo(self):
        # NumPy/SciPy least-squares MC, CR-RC^4 t_p 45 ns, 5 samples from one before the peak, white noise,
        # amplitude 50: sd(amplitude) 0.778, sd(time) 0.431 ns (4000 pulses; standard errors about 1.1 %)
        r = fr.optimal_filter(4, 45, 25, 5, -25, amplitude=50)['amplitude_and_time_fit']
        self.assertAlmostEqual(r['sigma_time_ns'], 0.431, delta=0.015)
        self.assertAlmostEqual(r['sigma_amplitude'], 0.778, delta=0.03)

    def test_constraints(self):
        kw = dict(rho=0.3, pileup_rate_hz=2e6, pileup_rms=4.0, phase_errors_ns=(-2, -0.5, 0.5, 2))
        free = fr.optimal_filter(4, 45, 25, 7, -75, **kw)
        phase = fr.optimal_filter(4, 45, 25, 7, -75, constraints=('phase',), **kw)
        base = fr.optimal_filter(4, 45, 25, 7, -75, constraints=('baseline',), **kw)
        both = fr.optimal_filter(4, 45, 25, 7, -75, constraints=('phase', 'baseline'), **kw)
        times = phase['sample_times_ns']
        gp = [fr.pulse_derivative(t, 4, 11.25) for t in times]
        for r in (phase, base, both):
            self.assertAlmostEqual(sum(a * b for a, b in zip(r['weights_optimal'], r['pulse_samples'])), 1, places=10)
            self.assertGreaterEqual(r['sigma_optimal'], free['sigma_optimal'] - 1e-12)
            self.assertAlmostEqual(r['sigma_optimal_unconstrained'], free['sigma_optimal'], places=12)
        for r in (phase, both):
            self.assertAlmostEqual(sum(a * b for a, b in zip(r['weights_optimal'], gp)), 0, places=10)
            b = {x['phase_error_ns']: x['optimal'] for x in r['relative_bias_from_phase_error']}
            # first order cancelled: the bias is even in the phase error and quadratic (ratio 16 for 4x the shift)
            self.assertAlmostEqual(b[2] / b[-2], 1, delta=0.15)
            self.assertAlmostEqual(b[2] / b[0.5], 16, delta=2)
        f = {x['phase_error_ns']: x['optimal'] for x in free['relative_bias_from_phase_error']}
        self.assertLess(f[-2] * f[2], 0)  # unconstrained: first order dominates, opposite signs
        for r in (base, both):
            self.assertAlmostEqual(r['baseline_offset_gain']['optimal'], 0, places=10)
        with self.assertRaises(ValueError):
            fr.optimal_filter(4, 45, 25, 2, -25, constraints=('phase', 'baseline'))
        with self.assertRaises(ValueError):
            fr.optimal_filter(4, 45, 25, 5, -25, constraints=('phase', 'phase'))

    def test_amplitude_time_correlation_sign(self):
        # model A g(t + d): on the falling edge a larger d lowers the samples and a larger A raises them, so the
        # estimates are positively correlated; on the rising edge negatively
        falling = fr.optimal_filter(2, 20, 10, 4, 10, amplitude=100)['amplitude_and_time_fit']['correlation']
        rising = fr.optimal_filter(2, 40, 5, 4, -35, amplitude=100)['amplitude_and_time_fit']['correlation']
        self.assertGreater(falling, 0.5)
        self.assertLess(rising, -0.5)

    def test_low_amplitude_and_bad_inputs_are_flagged(self):
        r = fr.optimal_filter(4, 45, 25, 5, -25, amplitude=3)
        self.assertTrue(any('biased upward' in v for v in r['validity']))
        with self.assertRaises(ValueError):
            fr.optimal_filter(1, 25, 25, 5, -200)  # every sample before the pulse
        with self.assertRaises(ValueError):
            fr.optimal_filter(1, 25, 25, 5, -15, rho=1.0)
        with self.assertRaises(ValueError):
            fr.optimal_filter(1, 25, 25, 0, -15)


class Landau(unittest.TestCase):
    # scipy.stats.landau (SciPy 1.18.1) at lambda: pdf(lambda) = landau.pdf(lambda, loc=ln(pi/2), scale=pi/2)
    SCIPY = {-3.0: (0.0006737286139080643, 8.59212662520897e-05), -2.0: (0.04398547837936385, 0.01409435793414876),
             0.0: (0.17885416067524945, 0.28683288012541786), 1.0: (0.1452066370964019, 0.4510180928195259),
             3.0: (0.07424765459960138, 0.664205997524218), 10.0: (0.01197648738878853, 0.8829388659135639),
             50.0: (0.0004496494678722378, 0.9785569913451871)}

    def test_against_recorded_scipy_values(self):
        for lam, (pdf, cdf) in self.SCIPY.items():
            self.assertAlmostEqual(fr.landau_pdf(lam), pdf, delta=1e-10)
            self.assertAlmostEqual(fr.landau_cdf(lam), cdf, delta=1e-10)

    def test_against_the_oscillatory_integral(self):
        for lam in (-1.5, -0.2, 0.7, 4.0):
            self.assertAlmostEqual(fr.landau_pdf(lam), landau_direct(lam), delta=2e-6)

    def test_peak_and_cdf_derivative(self):
        self.assertAlmostEqual(fr.landau_pdf(fr.LANDAU_MPV), 0.180655634, delta=1e-8)
        for d in (-1e-3, 1e-3):
            self.assertLess(fr.landau_pdf(fr.LANDAU_MPV + d), fr.landau_pdf(fr.LANDAU_MPV))
        for lam in (-1.0, 0.5, 6.0):
            h = 1e-4
            slope = (fr.landau_cdf(lam + h) - fr.landau_cdf(lam - h)) / (2 * h)
            self.assertAlmostEqual(slope, fr.landau_pdf(lam), delta=1e-7)


class HitEfficiency(unittest.TestCase):
    def test_landau_efficiency_matches_quadrature_and_monte_carlo(self):
        # half the charge of MPV 23000, xi 1500 on the channel; noise 1000 and threshold spread 300.
        # scipy.integrate.quad of 1 - E[F(T + s u)]: 0.98796331; a 4e6-event MC gave 0.987947 +- 0.000055
        r = fr.hit_efficiency([9000], 1000, 'landau', mpv=23000, xi=1500, signal_fraction=0.5,
                              threshold_dispersion=300)
        self.assertAlmostEqual(r['thresholds'][0]['efficiency'], 0.98796331, delta=2e-6)
        self.assertTrue(any('charge sharing' in v for v in r['validity']))

    def test_gaussian_signal_closed_form(self):
        r = fr.hit_efficiency([30, 40], 5, 'gauss', mean=40, sigma_signal=12)
        s = math.hypot(12, 5)
        self.assertAlmostEqual(r['thresholds'][0]['efficiency'], fr._phi(10 / s), places=12)
        self.assertAlmostEqual(r['thresholds'][1]['efficiency'], 0.5, places=12)

    def test_occupancy_averaged_over_threshold_spread(self):
        # mean over Gaussian thresholds T_i ~ N(T, s_thr) of nu0 exp(-T_i^2 / 2 s_n^2), numerically
        sn, sthr, thr = 1000.0, 400.0, 4500.0
        r = fr.hit_efficiency([thr], sn, 'gauss', mean=20000, sigma_signal=1000, threshold_dispersion=sthr,
                              peaking_ns=25, order=2, window_ns=25)
        nu0 = r['nu0_hz']
        avg = trapezoid(lambda u: math.exp(-(thr + sthr * u) ** 2 / (2 * sn * sn)) * math.exp(-u * u / 2),
                        -10, 10, 20000) / math.sqrt(2 * math.pi)
        self.assertAlmostEqual(r['thresholds'][0]['noise_crossing_rate_hz'] / (nu0 * avg), 1.0, delta=1e-9)
        above = trapezoid(lambda u: fr._phi(-(thr + sthr * u) / sn) * math.exp(-u * u / 2), -10, 10, 20000)
        self.assertAlmostEqual(r['thresholds'][0]['noise_probability_above_at_sample'] * math.sqrt(2 * math.pi),
                               above, delta=1e-12)
        self.assertAlmostEqual(nu0, 0.551 / 25e-9, delta=0.001 / 25e-9)  # page: nu_0 t_p = 0.551, n = 2 series

    def test_operating_window_opens_and_closes(self):
        kw = dict(noise=1000, signal_model='landau', mpv=23000, xi=1500, threshold_dispersion=300, peaking_ns=25,
                  order=2, window_ns=25, min_efficiency=0.99, max_occupancy=1e-4)
        thresholds = [3000 + 500 * i for i in range(13)]
        full = fr.hit_efficiency(thresholds, signal_fraction=1.0, **kw)
        self.assertEqual(full['operating_window']['lowest_threshold'], 4500)
        self.assertEqual(full['operating_window']['highest_threshold'], 9000)
        shared = fr.hit_efficiency(thresholds, signal_fraction=0.5, **kw)
        self.assertEqual(shared['operating_window']['highest_threshold'], 8500)
        damaged = fr.hit_efficiency(thresholds, signal_fraction=0.2, **kw)  # e.g. trapping and sharing together
        self.assertIsNone(damaged['operating_window'])
        self.assertTrue(any('window is closed' in v for v in damaged['validity']))

    def test_inputs_are_checked(self):
        with self.assertRaises(ValueError):
            fr.hit_efficiency([1000], 100, 'landau', mpv=20000)  # no xi
        with self.assertRaises(ValueError):
            fr.hit_efficiency([1000], 100, 'gauss', mean=1, sigma_signal=1, window_ns=25)  # window without peaking
        with self.assertRaises(ValueError):
            fr.hit_efficiency([1000], 100, 'landau', mpv=20000, xi=1000, signal_fraction=1.5)


class WaveformToy(unittest.TestCase):
    ARGS = dict(order=4, peaking_ns=45, period_ns=25, samples=7, first_offset_ns=-50, amplitude=50)

    def test_closure_without_jitter_or_adc(self):
        r = fr.waveform_toy(events=20000, seed=7, rho=0.5, pileup_rate_hz=2e6, pileup_mean_amp=3,
                            pileup_amplitudes='exponential', **self.ARGS)
        self.assertEqual(r['status_label'], 'synthetic')
        for name, e in r['estimators'].items():
            self.assertLess(abs(e['closure_z_bias']), 4, name)
            self.assertLess(abs(e['closure_z_sigma']), 4, name)
        est = r['estimators']
        # the pileup mean (unipolar shaping) is a bias of mean offset times the sum of weights
        self.assertGreater(est['template_uncorrelated']['predicted_bias'], est['optimal_matched']['predicted_bias'])
        self.assertLess(est['optimal_matched']['predicted_sigma'], est['optimal_electronic']['predicted_sigma'])

    def test_baseline_constraint_removes_the_pileup_mean_bias(self):
        kw = dict(events=20000, seed=9, rho=0.3, pileup_rate_hz=3e6, pileup_mean_amp=3, **self.ARGS)
        free = fr.waveform_toy(**kw)['estimators']['optimal_matched']
        base = fr.waveform_toy(constraints=('baseline',), **kw)['estimators']['optimal_matched']
        self.assertGreater(free['bias'], 10 * free['bias_mc_error'])
        self.assertAlmostEqual(base['predicted_bias'], 0, places=10)
        self.assertLess(abs(base['closure_z_bias']), 4)
        self.assertLess(abs(base['closure_z_sigma']), 4)
        self.assertGreater(base['sigma'], free['sigma'])

    def test_seed_reproducibility(self):
        a = fr.waveform_toy(events=500, seed=3, rho=0.2, **self.ARGS)
        b = fr.waveform_toy(events=500, seed=3, rho=0.2, **self.ARGS)
        c = fr.waveform_toy(events=500, seed=4, rho=0.2, **self.ARGS)
        self.assertEqual(a, b)
        self.assertNotEqual(a['estimators'], c['estimators'])

    def test_phase_jitter_biases_downward(self):
        r = fr.waveform_toy(events=20000, seed=5, phase_jitter_ns=3, **self.ARGS)
        self.assertLess(r['estimators']['largest_sample']['closure_z_bias'], -5)
        self.assertTrue(r['validity'])

    def test_adc_saturation_is_counted(self):
        r = fr.waveform_toy(events=500, seed=2, adc_lsb=1.0, adc_bits=5, **self.ARGS)  # full scale 31 < 50 + 5
        self.assertEqual(r['saturated_events'], 500)
        self.assertLess(r['estimators']['largest_sample']['relative_bias'], -0.3)


class SCurve(unittest.TestCase):
    CHARGES = [3000.0 + 200 * i for i in range(8)]
    HITS = [1, 5, 18, 41, 66, 86, 96, 99]

    def test_fit_matches_an_independent_minimizer(self):
        # scipy.optimize.minimize (Nelder-Mead) of the same binomial likelihood: T 3676.70968, sigma 298.47143
        r = fr.scurve_fit(self.CHARGES, self.HITS, [100])
        self.assertAlmostEqual(r['threshold'], 3676.70968, delta=1e-3)
        self.assertAlmostEqual(r['noise'], 298.47143, delta=1e-3)
        self.assertTrue(r['converged'])
        self.assertGreater(r['p_value'], 0.5)

    def test_fit_is_a_maximum_and_errors_follow_fisher(self):
        r = fr.scurve_fit(self.CHARGES, self.HITS, [100])

        def ll(t, s):
            return sum(k * math.log(fr._phi((q - t) / s)) + (100 - k) * math.log(1 - fr._phi((q - t) / s))
                       for q, k in zip(self.CHARGES, self.HITS))
        best = ll(r['threshold'], r['noise'])
        for dt, ds in ((5, 0), (-5, 0), (0, 5), (0, -5)):
            self.assertLess(ll(r['threshold'] + dt, r['noise'] + ds), best)
        # a NumPy MC of 2000 scans (T 3700, sigma 300, 100 injections) gave sd(T) 17.9 and sd(sigma) 17.5,
        # pulls 0.98 and 1.02 wide; the design mode predicts 18.3 and 17.3
        d = fr.scurve_design(self.CHARGES, [100], 3700, 300)
        self.assertAlmostEqual(d['expected_sigma_threshold'], 17.9, delta=0.9)
        self.assertAlmostEqual(d['expected_sigma_noise'], 17.5, delta=0.9)

    def test_scaling_and_flags(self):
        a = fr.scurve_design(self.CHARGES, [100], 3700, 300)['expected_sigma_threshold']
        b = fr.scurve_design(self.CHARGES, [400], 3700, 300)['expected_sigma_threshold']
        self.assertAlmostEqual(a / b, 2.0, places=9)  # 1/sqrt(N)
        coarse = fr.scurve_fit([2000, 3000, 4000, 5000], [0, 2, 98, 100], [100])
        self.assertTrue(any('poorly constrained' in v for v in coarse['validity']))
        bad = fr.scurve_fit(self.CHARGES, [1, 5, 60, 20, 66, 86, 96, 99], [100])
        self.assertTrue(any('poor fit' in v for v in bad['validity']))
        with self.assertRaises(ValueError):
            fr.scurve_fit(self.CHARGES, [0] * 8, [100])  # never crosses 50 %
        with self.assertRaises(ValueError):
            fr.scurve_fit(self.CHARGES, self.HITS, [100, 100])


class ThresholdTrim(unittest.TestCase):
    def test_against_monte_carlo_of_trim_codes(self):
        # NumPy MC, 2e6 channels with codes rounded and clipped to the DAC range: residual rms 441.76 and 18.28 %
        # beyond the range for (1500, 4 bits, 250); 258.47 for (800, 5 bits, 60)
        r = fr.threshold_trim(1500, 4, 250)
        self.assertAlmostEqual(r['residual_dispersion'], 441.76, delta=1.0)
        self.assertAlmostEqual(r['fraction_beyond_range'], 0.1828, delta=0.001)
        self.assertTrue(r['validity'])
        self.assertAlmostEqual(fr.threshold_trim(800, 5, 60)['residual_dispersion'], 258.47, delta=0.6)

    def test_wide_range_limit_and_nonlinearity(self):
        r = fr.threshold_trim(1000, 10, 20)  # range +-10 sigma
        self.assertAlmostEqual(r['residual_dispersion'], 20 / math.sqrt(12), places=6)
        self.assertFalse(r['validity'])
        n = fr.threshold_trim(1000, 10, 20, dac_nonlinearity=10)
        self.assertAlmostEqual(n['residual_dispersion'], math.hypot(20 / math.sqrt(12), 10), places=6)


class InjectionGainGuidance(unittest.TestCase):
    """sci-fix C4 (S3): the calibration chain does not take the charge-injection gain for the signal gain.
    Sources: arXiv:1306.6756v2 sec. II-C (M_phys/M_cali corrects for the difference between physics and
    calibration pulses) and arXiv:0912.2642v4 sec. 3.1.2, eq. 5 (its inverse is the response ratio of a calibration
    and an ionization pulse of the same input current)."""
    PAGE = PLUGIN / 'skills' / 'hep-detector' / 'references' / 'front-end-electronics-and-signal-processing.md'

    def setUp(self):
        self.text = self.PAGE.read_text(encoding='utf-8')

    def test_injection_bullet_separates_injection_and_signal_gain(self):
        calibration = self.text.split('## Calibration of the electronics', 1)[1].split('\n## ', 1)[0]
        bullet = calibration.split('- **Charge injection**', 1)[1].split('\n- **', 1)[0]
        flat = ' '.join(bullet.split())
        self.assertIn('the injection gain and the physics-signal gain differ', flat)
        self.assertIn('cross-check with a source or minimum-ionizing particles', flat)
        for locator in ('arXiv:1306.6756v2, sec. II-C', 'arXiv:0912.2642v4, sec. 3.1.2'):
            self.assertIn(locator, flat)

    def test_misconception_is_listed(self):
        self.assertIn('**"Injection gain is the signal gain."**', self.text)


class CommandLine(unittest.TestCase):
    def run_cli(self, args):
        return subprocess.run([sys.executable, '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=120)

    def test_new_subcommands_print_json(self):
        cases = (
            ['optimal-filter', '--order', '4', '--peaking', '45', '--period', '25', '--samples', '5',
             '--first-offset', '-25', '--rho', '0.3', '--pileup-rate', '1e6', '--pileup-rms', '2', '--amplitude', '40',
             '--phase-errors', '-2', '2'],
            ['hit-efficiency', '--scan', '2000', '8000', '7', '--noise', '1000', '--mpv', '23000', '--xi', '1500',
             '--peaking', '25', '--window', '25', '--min-efficiency', '0.99', '--max-occupancy', '1e-4'],
            ['waveform-toy', '--order', '2', '--peaking', '30', '--period', '10', '--samples', '6', '--first-offset',
             '-20', '--amplitude', '20', '--events', '300', '--adc-lsb', '0.5'],
        )
        for args in cases:
            proc = self.run_cli(args)
            self.assertEqual(proc.returncode, 0, msg=f'{args}: {proc.stderr}')
            out = json.loads(proc.stdout, parse_constant=lambda c: self.fail(c))
            self.assertEqual(out['command'], args[0])
            self.assertEqual(out['status'], 'unvalidated')

    def test_non_finite_result_exits_1(self):
        for args in (['hit-efficiency', '--thresholds', '1e300', '--noise', '1e-300', '--signal-model', 'gauss',
                      '--mean', '1', '--sigma-signal', '1'],  # an exception while computing
                     ['enc', '--capacitance', '1e300', '--peaking', '25', '--en', '1e300']):  # an infinite result
            proc = self.run_cli(args)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertEqual(json.loads(proc.stdout)['error_kind'], 'failed')
            self.assertNotIn('Traceback', proc.stderr)

    def test_input_error_naming_json_exits_2(self):
        # an input error whose message names JSON (as a bad input file's would) is not a non-finite result
        def bad_input(*args):
            raise ValueError('--noise-covariance: not valid JSON')
        stdout = io.StringIO()
        argv = ['frontend_response.py', 'cluster-noise', '--channels', '3', '--sigma', '1', '--rho', '0.1']
        with mock.patch.object(fr, 'cluster_noise', bad_input), mock.patch.object(sys, 'argv', argv), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                fr.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(json.loads(stdout.getvalue())['error_kind'], 'invalid-input')

    def test_bad_inputs_exit_2(self):
        bad = (
            ['optimal-filter', '--peaking', '25', '--period', '25', '--samples', '100', '--first-offset', '0'],
            ['hit-efficiency', '--scan', '1', '0', '5', '--noise', '1', '--mpv', '10', '--xi', '1'],
            ['hit-efficiency', '--thresholds', '5', '--noise', '1', '--signal-model', 'gauss', '--mean', '10'],
            ['waveform-toy', '--peaking', '25', '--period', '25', '--samples', '5', '--first-offset', '0',
             '--amplitude', '10', '--events', '5'],
        )
        for args in bad:
            proc = self.run_cli(args)
            self.assertEqual(proc.returncode, 2, msg=f'{args}: {proc.stdout}')
            self.assertEqual(json.loads(proc.stdout)['error_kind'], 'invalid-input')


if __name__ == '__main__':
    unittest.main()
