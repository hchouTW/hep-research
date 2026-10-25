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
- the page's own worked numbers (front-end-electronics-and-signal-processing.md, optimal filter and phase error);
- table signal model (FE1): a Landau density table against the Landau model truncated at the table's end (the Landau
  itself checked above against SciPy and the oscillatory integral), with a +300 e shifted table as negative control;
  a Gaussian density table against the closed form, with a 5 % wider table as negative control; a count table
  computed by hand (bin edges at the midpoints, uniform within a bin).
- measured noise covariance (FE2): a rho^|i-j| matrix against the --rho path (to 1e-12); the sample covariance of
  20 000 draws against the input matrix within 4 Gaussian standard errors per element (AR(1) draws as negative
  control); the common-mode variance 0.3 (sum w)^2 of a linear estimator in closed form; SHA-256 recomputed.
- batch S-curve (FE3): per-channel results against single fits; the corrected dispersion against the generated
  spread (150 e) and against each batch's own true-threshold sd (Monte Carlo, 60 batches of 200 channels, hits
  drawn with erfc), the uncorrected sd as negative control; the MAD against sqrt(150^2 + mean fit error^2), the
  unscaled MAD as negative control; median and count recomputed from the per-channel results.
- simreco block (FE4): the efficiency, occupancy and threshold fraction of a Gaussian signal in closed form, composed
  by hand (eps ** sides, (occupancy x channels) ** sides, threshold / mean), one side as negative control; the
  merged tail source against the simreco spec schema and checks (adapters/geant4/assets/simreco_spec.py); the default
  output compared byte for byte with the output without the new options.
Standard library only.
"""
import contextlib
import io
import json
import math
import subprocess
import sys
import tempfile
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



class HitEfficiencyTable(unittest.TestCase):
    """FE1: the table (measured or simulated spectrum) signal model of hit-efficiency."""
    MPV, XI, NOISE = 23000.0, 1500.0, 1000.0
    THRESHOLDS = list(range(16000, 24001, 1000))
    STEP, Q_LO, Q_HI = 25.0, 8000.0, 60000.0  # step <= 150 e as FE1-1 asks; 25 e keeps the interpolation < 1e-3

    @classmethod
    def setUpClass(cls):
        n = int((cls.Q_HI - cls.Q_LO) / cls.STEP)
        cls.charges = [cls.Q_LO + i * cls.STEP for i in range(n + 1)]
        cls.density = [fr.landau_pdf(cls._lam(q)) / cls.XI for q in cls.charges]
        # oracle: the Landau model truncated at the table's upper end (the table is normalized over its range)
        top = fr.landau_cdf(cls._lam(cls.Q_HI))
        cache = {}

        def cdf(q):
            key = round(q, 3)
            if key not in cache:
                cache[key] = min(fr.landau_cdf(cls._lam(min(q, cls.Q_HI))), top) / top
            return cache[key]
        cls.truncated_ineff = {t: fr._gauss_expect(cdf, t, cls.NOISE) for t in cls.THRESHOLDS}

    @classmethod
    def _lam(cls, q):
        return (q - cls.MPV) / cls.XI + fr.LANDAU_MPV

    def table_ineff(self, charges, density, **kw):
        r = fr.hit_efficiency(self.THRESHOLDS, self.NOISE, 'table', spectrum=('density', charges, density), **kw)
        return {row['threshold']: row['inefficiency'] for row in r['thresholds']}, r

    def test_landau_density_table_reproduces_landau(self):  # FE1-1
        ineff, r = self.table_ineff(self.charges, self.density)
        for t in self.THRESHOLDS:
            self.assertLess(abs(ineff[t] / self.truncated_ineff[t] - 1), 1e-3, msg=t)
        self.assertGreater(self.truncated_ineff[16000], 1e-6)  # the deep tail is really probed (1.8e-6 untruncated)
        self.assertTrue(any('table ends at' in v for v in r['validity']))  # a Landau table is always truncated

    def test_shifted_table_fails_the_check(self):  # FE1-2, negative control
        shifted = [q + 300 for q in self.charges]
        ineff, _ = self.table_ineff(shifted, self.density)
        for t in self.THRESHOLDS:
            self.assertGreater(abs(ineff[t] / self.truncated_ineff[t] - 1), 0.09, msg=t)

    def test_gaussian_density_table_matches_closed_form(self):  # FE1-3
        mu, sig, step = 20000.0, 1000.0, 50.0
        qs = [mu - 10 * sig + i * step for i in range(int(20 * sig / step) + 1)]
        dens = [math.exp(-((q - mu) / sig) ** 2 / 2) for q in qs]  # unnormalized: the tool normalizes
        total = math.hypot(sig, self.NOISE)
        thresholds = list(range(17000, 23001, 500))
        r = fr.hit_efficiency(thresholds, self.NOISE, 'table', spectrum=('density', qs, dens))
        for row in r['thresholds']:
            want = 0.5 * math.erfc((row['threshold'] - mu) / (total * math.sqrt(2)))
            self.assertLess(abs(row['efficiency'] - want), 1e-4, msg=row['threshold'])
        self.assertFalse(any('table ends at' in v for v in r['validity']))
        wider = [math.exp(-((q - mu) / (1.05 * sig)) ** 2 / 2) for q in qs]  # negative control: 5 % wider signal
        r = fr.hit_efficiency(thresholds, self.NOISE, 'table', spectrum=('density', qs, wider))
        worst = max(abs(row['efficiency'] - 0.5 * math.erfc((row['threshold'] - mu) / (total * math.sqrt(2))))
                    for row in r['thresholds'])
        self.assertGreater(worst, 1e-3)

    def test_count_table_bins_and_signal_fraction(self):
        # bin centres 0, 1, 2, 3 with counts 1, 2, 3, 4: edges -0.5, 0.5, 1.5, 2.5, 3.5, uniform within a bin
        spectrum = ('count', [0.0, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0])
        r = fr.hit_efficiency([1.0, 3.0], 1e-6, 'table', spectrum=spectrum)
        self.assertAlmostEqual(r['thresholds'][0]['inefficiency'], (1 + 2 * 0.5) / 10, places=9)
        self.assertAlmostEqual(r['thresholds'][1]['inefficiency'], (1 + 2 + 3 + 4 * 0.5) / 10, places=9)
        self.assertEqual(r['signal']['charge_range_on_channel'], [-0.5, 3.5])
        half = fr.hit_efficiency([0.5, 1.5], 1e-6, 'table', spectrum=spectrum, signal_fraction=0.5)
        self.assertAlmostEqual(half['thresholds'][0]['inefficiency'], r['thresholds'][0]['inefficiency'], places=9)
        outside = fr.hit_efficiency([5.0], 1e-6, 'table', spectrum=spectrum)
        self.assertAlmostEqual(outside['thresholds'][0]['efficiency'], 0.0, places=12)
        self.assertTrue(any('outside the table range' in v for v in outside['validity']))

    def test_model_and_file_must_agree(self):
        with self.assertRaises(ValueError):
            fr.hit_efficiency([1.0], 1.0, 'table')
        with self.assertRaises(ValueError):
            fr.hit_efficiency([1.0], 1.0, 'gauss', mean=5, sigma_signal=1, spectrum=('count', [0.0, 1.0], [1.0, 1.0]))

    def test_bad_spectrum_files_are_invalid_input(self):  # FE1-4
        cases = {
            'empty': b'', 'header only': b'charge,density\n', 'one row': b'charge,density\n1,2\n',
            'wrong names': b'q,density\n1,2\n2,3\n', 'three columns': b'charge,density,x\n1,2,3\n2,3,4\n',
            'short row': b'charge,count\n1,2\n2\n', 'not a number': b'charge,count\n1,2\n2,abc\n',
            'nan': b'charge,count\n1,2\n2,nan\n', 'inf': b'charge,count\n1,inf\n2,3\n',
            'not increasing': b'charge,count\n2,2\n1,3\n', 'repeated charge': b'charge,count\n1,2\n1,3\n',
            'negative': b'charge,density\n1,5\n2,-1\n3,4\n',  # positive total
            'zero total': b'charge,count\n1,0\n2,0\n',
            'not utf-8': b'charge,count\n1,2\n2,\xff\xfe\n',
        }
        with tempfile.TemporaryDirectory() as tmp:
            paths = {'missing': str(Path(tmp) / 'absent.csv')}
            for i, (name, data) in enumerate(cases.items()):
                path = Path(tmp) / f'case{i}.csv'
                path.write_bytes(data)
                paths[name] = str(path)
            for name, path in paths.items():
                proc = subprocess.run([sys.executable, '-I', str(SCRIPT), 'hit-efficiency', '--thresholds', '1',
                                       '--noise', '1', '--signal-model', 'table', '--spectrum', path],
                                      capture_output=True, text=True, timeout=120)
                with self.subTest(name):
                    self.assertEqual(proc.returncode, 2, proc.stdout)
                    self.assertEqual(json.loads(proc.stdout)['error_kind'], 'invalid-input')
                    self.assertNotIn('Traceback', proc.stderr)
            good = Path(tmp) / 'good.csv'
            good.write_text('charge,count\n0,1\n1,2\n2,3\n3,4\n', encoding='utf-8')
            proc = subprocess.run([sys.executable, '-I', str(SCRIPT), 'hit-efficiency', '--thresholds', '1',
                                   '--noise', '1e-6', '--signal-model', 'table', '--spectrum', str(good)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertAlmostEqual(json.loads(proc.stdout)['thresholds'][0]['inefficiency'], 0.2, places=9)

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



def exponential_matrix(rho, m, common=0.0):
    return [[rho ** abs(i - j) + common for j in range(m)] for i in range(m)]


class MeasuredNoiseCovariance(unittest.TestCase):
    """FE2: a measured per-sample noise covariance for optimal-filter and waveform-toy."""
    ARGS = dict(order=4, peaking_ns=45, period_ns=25, samples=7, first_offset_ns=-50)
    CLI = ['--order', '4', '--peaking', '45', '--period', '25', '--samples', '7', '--first-offset', '-50']

    def test_exponential_matrix_equals_rho(self):  # FE2-1
        cov = exponential_matrix(0.6, 7)
        for kw in ({}, {'constraints': ['phase']}, {'pileup_rate_hz': 1e6, 'pileup_rms': 2.0, 'amplitude': 40.0}):
            a = fr.optimal_filter(rho=0.6, **self.ARGS, **kw)
            b = fr.optimal_filter(noise_covariance=cov, **self.ARGS, **kw)
            for key in ('sigma_optimal', 'sigma_template_uncorrelated', 'sigma_largest_sample'):
                self.assertAlmostEqual(a[key], b[key], delta=1e-12)
            for x, y in zip(a['weights_optimal'], b['weights_optimal']):
                self.assertAlmostEqual(x, y, delta=1e-12)
        toy = dict(amplitude=50, events=20000, pileup_rate_hz=1e6, pileup_mean_amp=2.0, **self.ARGS)
        a = fr.waveform_toy(rho=0.6, **toy)
        b = fr.waveform_toy(noise_covariance=cov, **toy)
        for name, est in b['estimators'].items():
            self.assertAlmostEqual(est['predicted_sigma'], a['estimators'][name]['predicted_sigma'], delta=1e-12)
            self.assertLess(abs(est['closure_z_sigma']), 4, name)
            self.assertLess(abs(est['closure_z_bias']), 4, name)

    def test_common_mode_matrix_is_generated(self):  # FE2-2
        import random
        cov = exponential_matrix(0.6, 7, common=0.3)
        _, lower, _ = fr.measured_covariance(cov, 7)
        n = 20000

        def sample_covariance(draw):
            rng = random.Random(7)
            xs = [draw(rng) for _ in range(n)]
            mean = [sum(x[i] for x in xs) / n for i in range(7)]
            return [[sum((x[i] - mean[i]) * (x[j] - mean[j]) for x in xs) / (n - 1) for j in range(7)]
                    for i in range(7)]
        got = sample_covariance(lambda rng: fr.correlated_noise(rng, lower))
        for i in range(7):
            for j in range(7):
                se = math.sqrt((cov[i][i] * cov[j][j] + cov[i][j] ** 2) / n)  # Gaussian standard error of s_ij
                self.assertLess(abs(got[i][j] - cov[i][j]), 4 * se, (i, j))
        # negative control: the AR(1) noise without the common mode is far from this matrix
        _, ar_lower, _ = fr.measured_covariance(exponential_matrix(0.6, 7), 7)
        ar = sample_covariance(lambda rng: fr.correlated_noise(rng, ar_lower))
        worst = max(abs(ar[i][j] - cov[i][j]) / math.sqrt((cov[i][i] * cov[j][j] + cov[i][j] ** 2) / n)
                    for i in range(7) for j in range(7))
        self.assertGreater(worst, 4)
        r = fr.waveform_toy(noise_covariance=cov, amplitude=50, events=20000, **self.ARGS)
        self.assertEqual(r['noise_model'], 'measured')
        for name, est in r['estimators'].items():
            self.assertLess(abs(est['closure_z_sigma']), 4, name)
            self.assertLess(abs(est['closure_z_bias']), 4, name)
        # the common mode adds 0.3 sum(w)^2 to the variance of each linear estimator
        base = fr.optimal_filter(rho=0.6, **self.ARGS)
        w = [x / sum(g * g for g in base['pulse_samples']) for x in base['pulse_samples']]
        cm = fr.optimal_filter(noise_covariance=cov, **self.ARGS)
        self.assertAlmostEqual(cm['sigma_template_uncorrelated'] ** 2,
                               base['sigma_template_uncorrelated'] ** 2 + 0.3 * sum(w) ** 2, delta=1e-12)

    def test_bad_matrices_are_refused_not_repaired(self):  # FE2-3
        good = exponential_matrix(0.6, 7)
        indefinite = [row[:] for row in good]
        indefinite[0][6] = indefinite[6][0] = 0.99
        asymmetric = [row[:] for row in good]
        asymmetric[0][1] = 0.5
        nonfinite = [row[:] for row in good]
        nonfinite[2][2] = float('nan')
        cases = {'not positive definite': indefinite, 'singular': [[1.0] * 7 for _ in range(7)],
                 'not symmetric': asymmetric, 'wrong dimension': exponential_matrix(0.6, 6),
                 'ragged': [row[:6] if i == 3 else row for i, row in enumerate(good)], 'non-finite': nonfinite}
        for name, m in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                fr.optimal_filter(noise_covariance=m, **self.ARGS)
        self.assertEqual(indefinite[0][6], 0.99)  # the input is left as it was
        for name in ('not positive definite', 'singular'):  # refused by the check itself, not repaired
            with self.subTest(name), self.assertRaises(ValueError):
                fr.measured_covariance(cases[name], 7)

    def test_bad_files_are_invalid_input(self):
        good = json.dumps({'covariance': exponential_matrix(0.6, 7)})
        cases = {'does not parse': '{"covariance": [[1, 2]', 'no key': '{"cov": [[1]]}', 'not an object': '[[1]]',
                 'not rows': '{"covariance": [1, 2]}', 'empty': '{"covariance": []}',
                 'a string entry': good.replace('1.0', '"x"', 1), 'a boolean entry': good.replace('1.0', 'true', 1),
                 'NaN token': good.replace('1.0', 'NaN', 1), 'Infinity token': good.replace('1.0', 'Infinity', 1),
                 'wrong dimension': json.dumps({'covariance': exponential_matrix(0.6, 5)})}
        with tempfile.TemporaryDirectory() as tmp:
            paths = {'missing': str(Path(tmp) / 'absent.json')}
            for i, (name, text) in enumerate(cases.items()):
                path = Path(tmp) / f'case{i}.json'
                path.write_text(text, encoding='utf-8')
                paths[name] = str(path)
            bad_bytes = Path(tmp) / 'latin.json'
            bad_bytes.write_bytes(b'{"covariance": [[\xff]]}')
            paths['not utf-8'] = str(bad_bytes)
            good_path = Path(tmp) / 'good.json'
            good_path.write_text(good, encoding='utf-8')
            for cmd, extra in (('optimal-filter', []), ('waveform-toy', ['--amplitude', '20', '--events', '100'])):
                for name, path in paths.items():
                    proc = subprocess.run([sys.executable, '-I', str(SCRIPT), cmd, *self.CLI, *extra,
                                           '--noise-covariance', path], capture_output=True, text=True, timeout=120)
                    with self.subTest(cmd=cmd, case=name):
                        self.assertEqual(proc.returncode, 2, proc.stdout)
                        self.assertEqual(json.loads(proc.stdout)['error_kind'], 'invalid-input')
                        self.assertNotIn('Traceback', proc.stderr)
                proc = subprocess.run([sys.executable, '-I', str(SCRIPT), cmd, *self.CLI, *extra, '--rho', '0.6',
                                       '--noise-covariance', str(good_path)], capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 2, proc.stdout)  # --rho and --noise-covariance exclude each other
                proc = subprocess.run([sys.executable, '-I', str(SCRIPT), cmd, *self.CLI, *extra,
                                       '--noise-covariance', str(good_path)], capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual(json.loads(proc.stdout)['noise_model'], 'measured')

    def test_noise_model_and_hash(self):  # FE2-4
        import hashlib
        cov = exponential_matrix(0.6, 7)
        want = hashlib.sha256(json.dumps([[float(v) for v in row] for row in cov],
                                         separators=(',', ':')).encode('utf-8')).hexdigest()
        measured = fr.optimal_filter(noise_covariance=cov, **self.ARGS)
        self.assertEqual(measured['noise_model'], 'measured')
        self.assertEqual(measured['noise_covariance_sha256'], want)
        ar1 = fr.optimal_filter(rho=0.6, **self.ARGS)
        self.assertEqual(ar1['noise_model'], 'ar1')
        self.assertIsNone(ar1['noise_covariance_sha256'])
        toy = fr.waveform_toy(noise_covariance=cov, amplitude=20, events=100, **self.ARGS)
        self.assertEqual(toy['noise_covariance_sha256'], want)
        changed = [row[:] for row in cov]
        changed[3][4] = changed[4][3] = cov[3][4] + 1e-9
        self.assertNotEqual(fr.optimal_filter(noise_covariance=changed, **self.ARGS)['noise_covariance_sha256'], want)

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



def scan_batch(rng, n_channels, spread, mean=3700.0, noise=300.0, injections=100,
               charges=tuple(3000.0 + 200 * i for i in range(8))):
    """Synthetic threshold scans: thresholds N(mean, spread^2), binomial hits with Phi((Q - T)/noise) (erfc)."""
    channels, truth = {}, []
    for c in range(n_channels):
        t = rng.gauss(mean, spread)
        truth.append(t)
        hits = []
        for q in charges:
            prob = 0.5 * math.erfc(-(q - t) / (noise * math.sqrt(2)))
            hits.append(sum(1 for _ in range(injections) if rng.random() < prob))
        channels[f'ch{c}'] = (list(charges), [injections] * len(charges), hits)
    return channels, truth


def sample_sd(xs):
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


class SCurveBatch(unittest.TestCase):
    """FE3: batch S-curve fits of many channels and the threshold-dispersion summary."""
    BATCHES = 60

    @classmethod
    def setUpClass(cls):
        import random
        rng = random.Random(2)  # seed 1 draws true thresholds with sd 151.6 over 200 batches (a 3-sigma excursion)
        cls.runs = []
        for _ in range(cls.BATCHES):
            channels, truth = scan_batch(rng, 200, 150.0)
            cls.runs.append((channels, truth, fr.scurve_batch(channels)))

    def mc(self, values):
        mean = sum(values) / len(values)
        return mean, sample_sd(values) / math.sqrt(len(values))

    def test_batch_equals_single_fits(self):  # FE3-1
        channels, _, out = self.runs[0]
        by_name = {r['channel']: r for r in out['channels']}
        for name, (qs, ns, ks) in channels.items():
            single = fr.scurve_fit(qs, ks, ns)
            got = by_name[name]
            for key, value in single.items():
                if key != 'assumptions':
                    self.assertEqual(got[key], value, (name, key))

    def test_corrected_dispersion_recovers_the_spread(self):  # FE3-2
        corrected = [out['summary']['threshold_dispersion_corrected'] for _, _, out in self.runs]
        mean, se = self.mc(corrected)
        self.assertLess(abs(mean - 150.0), 3 * se, (mean, se))
        # seed-independent form: against each batch's own true-threshold sd
        paired = [out['summary']['threshold_dispersion_corrected'] - sample_sd(truth) for _, truth, out in self.runs]
        mean_p, se_p = self.mc(paired)
        self.assertLess(abs(mean_p), 3 * se_p, (mean_p, se_p))
        # negative control: the uncorrected sd is biased up by the fit error (about 18 e in quadrature)
        raw = [out['summary']['threshold_sd'] - sample_sd(truth) for _, truth, out in self.runs]
        mean_r, se_r = self.mc(raw)
        self.assertGreater(mean_r, 3 * se_r)

    def test_unresolved_dispersion_is_clipped_at_zero(self):  # FE3-3
        import random
        seen_clipped = False
        for spread in (0.0, 5.0):
            rng = random.Random(11)
            for _ in range(8):
                channels, _ = scan_batch(rng, 50, spread)
                out = fr.scurve_batch(channels)
                value = out['summary']['threshold_dispersion_corrected']
                self.assertTrue(math.isfinite(value) and value >= 0)
                clipped = out['summary']['threshold_sd'] ** 2 <= out['summary']['mean_fit_error_squared']
                self.assertEqual(clipped, any('dispersion not above the fit error' in v for v in out['validity']))
                if clipped:
                    self.assertEqual(value, 0.0)
                    seen_clipped = True
                    json.dumps(out, allow_nan=False)  # always finite: never an exit 1
        self.assertTrue(seen_clipped)

    def test_failed_and_excluded_channels_stay_out(self):  # FE3-4
        import random
        channels, _ = scan_batch(random.Random(3), 20, 150.0)
        charges = channels['ch0'][0]
        channels['dead'] = (charges, [100] * 8, [0, 0, 0, 1, 2, 1, 0, 3])  # never crosses 50 %
        channels['noisy'] = (charges, [100] * 8, [0, 10, 45, 50, 52, 55, 90, 100])  # converges, p ~ 1e-12
        out = fr.scurve_batch(channels)
        self.assertEqual([f['channel'] for f in out['failed_channels']], ['dead'])
        self.assertIn('noisy', [e['channel'] for e in out['excluded_channels']])
        self.assertIn('p < 1e-3', [e for e in out['excluded_channels'] if e['channel'] == 'noisy'][0]['reasons'])
        clean = fr.scurve_batch({k: v for k, v in channels.items() if k not in ('dead', 'noisy')})
        self.assertEqual(out['summary']['threshold_sd'], clean['summary']['threshold_sd'])
        self.assertEqual(out['n_failed'], 1)
        self.assertEqual(out['n_included'] + out['n_excluded'] + out['n_failed'], out['n_channels'])
        self.assertTrue(any('more than 5 %' in v for v in out['validity']))  # 2 of 22

    def test_mad_scale_and_recomputed_fields(self):  # FE3-5
        # the MAD of the fitted thresholds estimates their spread, sqrt(150^2 + fit error^2), for Gaussian thresholds
        mads, want = [], []
        for _, _, out in self.runs:
            mads.append(out['summary']['threshold_mad_sigma'])
            want.append(math.sqrt(150.0 ** 2 + out['summary']['mean_fit_error_squared']))
        mean, se = self.mc([m - w for m, w in zip(mads, want)])
        self.assertLess(abs(mean), 3 * se, (mean, se))
        unscaled = [m / 1.4826 - w for m, w in zip(mads, want)]  # negative control: the MAD without the factor
        mean_u, se_u = self.mc(unscaled)
        self.assertGreater(abs(mean_u), 3 * se_u)
        for _, _, out in self.runs[:5]:
            inc = sorted(r['noise'] for r in out['channels'] if r['included'])
            mid = len(inc) // 2
            median = inc[mid] if len(inc) % 2 else (inc[mid - 1] + inc[mid]) / 2
            self.assertEqual(out['summary']['median_noise'], median)
            bad = sum(1 for r in out['channels'] if r['p_value'] < 1e-3)
            self.assertEqual(out['summary']['fitted_channels_with_p_below_1e-3'], bad)

    def test_scan_file_cli_and_bad_files(self):
        import random
        channels, _ = scan_batch(random.Random(4), 5, 150.0)
        lines = ['channel,charge,injections,hits']
        for name, (qs, ns, ks) in channels.items():
            lines += [f'{name},{q:g},{n},{k}' for q, n, k in zip(qs, ns, ks)]
        good = '\n'.join(lines) + '\n'
        cases = {'empty': '', 'header only': 'channel,charge,injections,hits\n',
                 'wrong header': good.replace('hits', 'k', 1), 'three columns': 'channel,charge,injections\na,1,2\n',
                 'not a number': good.replace('3000,', 'abc,', 1), 'nan charge': good.replace('3000,', 'nan,', 1),
                 'fractional injections': good.replace(',100,', ',100.5,', 1),
                 'hits above injections': 'channel,charge,injections,hits\na,1,10,11\n',
                 'zero injections': 'channel,charge,injections,hits\na,1,0,0\n',
                 'empty channel': 'channel,charge,injections,hits\n,1,10,1\n',
                 'not increasing': 'channel,charge,injections,hits\na,2,10,1\na,1,10,2\n'}
        with tempfile.TemporaryDirectory() as tmp:
            paths = {'missing': str(Path(tmp) / 'absent.csv')}
            for i, (name, text) in enumerate(cases.items()):
                path = Path(tmp) / f'case{i}.csv'
                path.write_text(text, encoding='utf-8')
                paths[name] = str(path)
            raw = Path(tmp) / 'latin.csv'
            raw.write_bytes(b'channel,charge,injections,hits\n\xff,1,10,1\n')
            paths['not utf-8'] = str(raw)
            good_path = Path(tmp) / 'good.csv'
            good_path.write_text(good, encoding='utf-8')
            argvs = {name: ['--scan-file', path] for name, path in paths.items()}
            argvs['with --charges'] = ['--scan-file', str(good_path), '--charges', '1', '2', '3']
            argvs['with --injections'] = ['--scan-file', str(good_path), '--injections', '100']
            argvs['no input'] = ['--hits', '1', '2', '3']
            for name, extra in argvs.items():
                proc = subprocess.run([sys.executable, '-I', str(SCRIPT), 's-curve', *extra], capture_output=True,
                                      text=True, timeout=120)
                with self.subTest(name):
                    self.assertEqual(proc.returncode, 2, proc.stdout)
                    self.assertEqual(json.loads(proc.stdout)['error_kind'], 'invalid-input')
                    self.assertNotIn('Traceback', proc.stderr)
            proc = subprocess.run([sys.executable, '-I', str(SCRIPT), 's-curve', '--scan-file', str(good_path)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = json.loads(proc.stdout)
            self.assertEqual(out['mode'], 'batch')
            self.assertEqual(out['summary']['threshold_sd'], fr.scurve_batch(channels)['summary']['threshold_sd'])

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


class SimrecoBlock(unittest.TestCase):
    """FE4: hit-efficiency results as the noise-digitization numbers of the Geant4 adapter's simreco (new options
    only; simreco and its defaults are unchanged)."""
    GAUSS = ['--noise', '1000', '--signal-model', 'gauss', '--mean', '6000', '--sigma-signal', '800', '--peaking', '25',
             '--window', '50']

    def run_cli(self, args):
        return subprocess.run([sys.executable, '-I', str(SCRIPT), 'hit-efficiency', *args], capture_output=True,
                              text=True, timeout=120)

    def block(self, args):
        proc = self.run_cli(args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_block_composed_from_the_closed_form(self):
        thr, sn, mu, ss, channels = 4500.0, 1000.0, 6000.0, 800.0, 640
        out = self.block(['--thresholds', str(thr), *self.GAUSS, '--simreco-channels', str(channels)])
        eps = fr._phi((mu - thr) / math.hypot(ss, sn))  # closed form
        nu0 = out['nu0_hz']
        occ = fr._phi(-thr / sn) + nu0 * math.exp(-thr * thr / (2 * sn * sn)) * 50e-9
        b = out['simreco_noise_digitization']
        self.assertEqual(set(b), {'threshold', 'efficiency', 'noise_hits_per_plane'})
        self.assertAlmostEqual(b['threshold'], thr / mu, places=14)
        self.assertAlmostEqual(b['efficiency'], eps ** 2, places=12)
        self.assertAlmostEqual(b['noise_hits_per_plane'] / (occ * channels) ** 2, 1, places=10)
        d = out['simreco_derivation']
        self.assertEqual((d['sides'], d['channels_per_side'], d['reference']), (2, channels, 'gauss mean'))
        # negative control: one side is not two (eps 0.93: the two differ by more than 5 %)
        one = self.block(['--thresholds', str(thr), *self.GAUSS, '--simreco-channels', str(channels),
                          '--simreco-sides', '1'])['simreco_noise_digitization']
        self.assertAlmostEqual(one['efficiency'], eps, places=12)
        self.assertGreater(one['efficiency'] - b['efficiency'], 0.05)
        self.assertAlmostEqual(one['noise_hits_per_plane'] / (occ * channels), 1, places=10)
        self.assertEqual(self.block(['--thresholds', str(thr), *self.GAUSS, '--simreco-channels', str(channels),
                                     '--simreco-sides', '1'])['simreco_derivation']['sides'], 1)

    def test_threshold_in_enc_units(self):
        enc = self.block(['--threshold-enc', '4.5', *self.GAUSS, '--simreco-channels', '640'])
        charge = self.block(['--thresholds', '4500', *self.GAUSS, '--simreco-channels', '640'])
        self.assertEqual(enc, charge)
        noisier = self.block(['--threshold-enc', '4', '--noise', '1200', *self.GAUSS[2:]])  # GAUSS[:2] is --noise
        self.assertEqual(noisier['thresholds'][0]['threshold'], 4800.0)
        landau = self.block(['--threshold-enc', '5', '--noise', '1000', '--mpv', '23000', '--xi', '1500',
                             '--peaking', '25', '--window', '25', '--simreco-channels', '640'])
        self.assertEqual(landau['thresholds'][0]['threshold'], 5000.0)
        self.assertAlmostEqual(landau['simreco_noise_digitization']['threshold'], 5000 / 23000, places=14)
        self.assertEqual(landau['simreco_derivation']['reference'], 'landau most probable value')

    def test_table_reference_is_its_peak(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'spectrum.csv'
            path.write_text('charge,count\n4000,1\n5000,8\n6000,30\n7000,12\n8000,2\n', encoding='utf-8')
            out = self.block(['--thresholds', '3000', '--noise', '500', '--signal-model', 'table', '--spectrum',
                              str(path), '--peaking', '25', '--window', '25', '--simreco-channels', '100'])
        self.assertEqual(out['simreco_derivation']['reference_signal'], 6000.0)
        self.assertAlmostEqual(out['simreco_noise_digitization']['threshold'], 0.5, places=14)

    def test_default_output_is_unchanged(self):
        """Without the new options the output is byte for byte what it was; with them every other key is the same."""
        base = ['--thresholds', '4500', *self.GAUSS]
        plain = self.run_cli(base)
        r = fr.hit_efficiency([4500.0], 1000.0, 'gauss', mean=6000.0, sigma_signal=800.0, peaking_ns=25.0,
                              window_ns=50.0)
        want = json.dumps({'status': 'unvalidated', 'command': 'hit-efficiency', **r}, indent=2, allow_nan=False)
        self.assertEqual(plain.stdout, want + '\n')
        self.assertNotIn('simreco', plain.stdout)
        with_block = json.loads(self.run_cli([*base, '--simreco-channels', '640']).stdout)
        before = json.loads(plain.stdout)
        added = with_block.pop('simreco_noise_digitization'), with_block.pop('simreco_derivation')
        self.assertTrue(all(added))
        self.assertEqual(with_block.pop('assumptions')[:-1], before.pop('assumptions'))
        self.assertEqual(with_block, before)

    def test_block_passes_the_simreco_spec_checks(self):
        assets = PLUGIN / 'adapters' / 'geant4' / 'assets'
        sys.path[:0] = [str(PLUGIN), str(assets)]
        try:
            import simreco_spec
        finally:
            del sys.path[:2]
        j15 = json.loads((PLUGIN / 'tests/adapters/fixtures/geant4_b1/j15_nominal.spec.json').read_text('utf-8'))
        block = self.block(['--threshold-enc', '5', '--noise', '1000', '--mpv', '23000', '--xi', '1500', '--peaking',
                            '25', '--window', '25', '--simreco-channels', '640'])['simreco_noise_digitization']
        spec = {'schema': 'simreco.spec/1', 'point_resolution_um': {'bending': 10.0, 'non_bending': 30.0},
                'radiation_length_mm': {'G4_Si': 93.7}, 'tof': {'sigma_t_ps': 100.0},
                'tail_sources': {'noise-digitization': {'on': True, 'pitch_y_um': 80, 'pitch_z_um': 200,
                                                        'sharing_um': 2, **block}}}
        self.assertEqual(simreco_spec.check(spec, j15), [])
        eff = simreco_spec.effective(spec, j15, 0, {})
        self.assertEqual({k: eff['reco']['tail_sources']['noise-digitization'][k] for k in block}, block)

    def test_bad_simreco_inputs_exit_2(self):
        bad = (
            ['--thresholds', '4000', '5000', *self.GAUSS, '--simreco-channels', '10'],  # two thresholds
            ['--thresholds', '4000', '--noise', '1000', '--signal-model', 'gauss', '--mean', '6000',
             '--sigma-signal', '800', '--simreco-channels', '10'],  # no occupancy per window
            ['--thresholds', '4000', *self.GAUSS, '--simreco-channels', '0'],
            ['--thresholds', '4000', *self.GAUSS, '--simreco-channels', '10', '--simreco-sides', '3'],
            ['--thresholds', '4000', *self.GAUSS, '--simreco-sides', '1'],  # sides without channels
            ['--thresholds', '4000', *self.GAUSS, '--signal-fraction', '0.5', '--simreco-channels', '10'],
            ['--thresholds', '7000', *self.GAUSS, '--simreco-channels', '10'],  # above the mean: fraction > 1
            ['--threshold-enc', '0', *self.GAUSS],
            ['--threshold-enc', 'nan', *self.GAUSS],
            ['--threshold-enc', '4', '--thresholds', '4000', *self.GAUSS],
        )
        for args in bad:
            with self.subTest(args=args):
                proc = self.run_cli(args)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertEqual(json.loads(proc.stdout)['error_kind'], 'invalid-input')
                self.assertNotIn('Traceback', proc.stderr)


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
