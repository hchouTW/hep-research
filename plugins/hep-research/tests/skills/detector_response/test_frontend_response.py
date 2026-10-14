"""Tests for the front-end electronics response helper (frontend_response.py).

Reference values were checked independently by numerical integration and Monte Carlo
(shot-noise ENC by simulating Poisson electrons through the shaper; Rice rates by
counting crossings of filtered white noise; Campbell moments by simulated pulse trains).
Standard library only.
"""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / 'skills' / 'detector-response' / 'scripts' / 'frontend_response.py'
sys.path.insert(0, str(SCRIPT.parent))
import frontend_response as fr  # noqa: E402

K_B = 1.380649e-23


def strict_json(text):
    def reject(constant):
        raise ValueError(f'non-finite JSON constant {constant}')
    return json.loads(text, parse_constant=reject)


def trapezoid(f, a, b, steps):
    h = (b - a) / steps
    return h * (0.5 * f(a) + 0.5 * f(b) + sum(f(a + i * h) for i in range(1, steps)))


class ShaperIntegrals(unittest.TestCase):
    def test_closed_forms_match_numerical_integration(self):
        for n in (1, 2, 3, 4):
            norm = n ** n * math.exp(-n)

            def g(t):
                return (t ** n) * math.exp(-t) / norm

            def gp(t):
                return g(t) * (n / t - 1) if t > 0 else (1.0 / norm if n == 1 else 0.0)
            ints = fr.shaper_integrals(n, 1.0)
            self.assertAlmostEqual(ints['int_g'], trapezoid(g, 0, 60, 60000), places=4)
            self.assertAlmostEqual(ints['int_g2'], trapezoid(lambda t: g(t) ** 2, 0, 60, 60000), places=4)
            self.assertAlmostEqual(ints['int_gp2'], trapezoid(lambda t: gp(t) ** 2, 0, 60, 60000), places=3)

    def test_peaking_time_is_n_tau(self):
        for n in (1, 2, 4):
            tau = 25.0
            peak = max(range(1, 2000), key=lambda i: (i / 10 / tau) ** n * math.exp(-i / 10 / tau))
            self.assertAlmostEqual(peak / 10, n * tau, delta=0.1)


class EquivalentNoiseCharge(unittest.TestCase):
    def test_shot_noise_rule_of_thumb(self):
        # CR-RC: ENC ~ 107 sqrt(I[nA] t_p[us]) electrons (MC of Poisson electrons gave 108)
        self.assertAlmostEqual(fr.enc(0, 1000, 1, leakage_na=1)['enc_electrons'], 107.4, delta=0.2)
        self.assertAlmostEqual(fr.enc(0, 4000, 1, leakage_na=1)['enc_electrons'] / 107.4, 2.0, delta=0.01)

    def test_series_noise_example(self):
        en = math.sqrt(4 * K_B * 300 * 50) * 1e9  # 50 ohm series resistance, nV/sqrt(Hz)
        self.assertAlmostEqual(fr.enc(10, 1000, 1, en_nv=en)['enc_electrons'], 54.6, delta=0.2)

    def test_optimum_shaping_time(self):
        r = fr.enc(10, 25, 1, en_nv=1, leakage_na=1000)
        self.assertAlmostEqual(r['enc_electrons'], 657, delta=2)
        self.assertAlmostEqual(r['optimum_series_vs_parallel']['peaking_ns'], 17.7, delta=0.1)
        self.assertAlmostEqual(fr.enc(10, 100, 1, en_nv=1, leakage_na=1000)['enc_electrons'], 1090, delta=3)
        self.assertAlmostEqual(fr.enc(10, 100, 1, en_nv=1, leakage_na=1)['optimum_series_vs_parallel']['peaking_ns'],
                               559, delta=2)

    def test_flicker_term_independent_of_shaping_time(self):
        a = fr.enc(10, 20, 2, af_v2=1e-12)['terms_electrons']['flicker']
        b = fr.enc(10, 2000, 2, af_v2=1e-12)['terms_electrons']['flicker']
        self.assertAlmostEqual(a, b, places=9)

    def test_leakage_temperature_scaling(self):
        self.assertAlmostEqual(1 / fr.leakage_scale(1, 20, -10), 19.0, delta=0.2)


class NoiseRate(unittest.TestCase):
    def test_rice_nu0(self):
        self.assertAlmostEqual(fr.rice_nu0(2, 1.0, 'series'), math.sqrt(3) / (2 * math.pi), places=12)
        self.assertAlmostEqual(fr.rice_nu0(2, 1.0, 'parallel'), 0.0919, places=4)
        self.assertAlmostEqual(fr.rice_nu0(4, 1.0, 'series'), 0.1233, places=4)
        self.assertAlmostEqual(fr.rice_nu0(4, 1.0, 'parallel'), 0.0602, places=4)

    def test_series_noise_cr_rc_is_undefined(self):
        self.assertIsNone(fr.rice_nu0(1, 1.0, 'series'))
        r = fr.noise_rate(4, 25, 1, 'series')
        self.assertTrue(r['validity'])
        self.assertIn('rate_per_channel_hz', r)

    def test_series_fraction_needs_mixed(self):
        with self.assertRaises(ValueError):
            fr.noise_rate(4, 25, 2, 'series', series_fraction=0.5)
        mixed = fr.noise_rate(0, 25, 2, 'mixed', series_fraction=0.5)['nu0_times_tau']
        self.assertAlmostEqual(mixed, math.sqrt(0.5 * 0.2757 ** 2 + 0.5 * 0.0919 ** 2), delta=1e-4)

    def test_fake_hits_scale_with_channels_and_window(self):
        r = fr.noise_rate(5, 25, 2, 'series', channels=10**8, window_ns=25)
        expected = 1e8 * fr.rice_nu0(2, 12.5e-9, 'series') * math.exp(-12.5) * 25e-9
        self.assertAlmostEqual(r['expected_fake_hits_per_event'], expected, delta=1e-9 * expected)
        self.assertGreater(r['expected_fake_hits_per_event'], 100)


class Timing(unittest.TestCase):
    def test_jitter_and_walk(self):
        r = fr.timing(1.0, 50, 0.5, (0.6, 1.0))
        self.assertAlmostEqual(r['jitter_ps'], 20.0)
        self.assertAlmostEqual(r['walk_ps'], 333.333, places=2)

    def test_cfd_modes(self):
        arc = fr.timing(1.0, 50, cfd_fraction=0.3, cfd_delay_ns=0.5)['cfd']
        self.assertFalse(arc['depends_on_rise_time'])
        self.assertAlmostEqual(arc['crossing_after_start_ns'], 0.5 / 0.7)
        for rise, expected in ((1.0, 3.3), (2.0, 3.6)):
            true_cfd = fr.timing(rise, 50, cfd_fraction=0.3, cfd_delay_ns=3.0)['cfd']
            self.assertTrue(true_cfd['depends_on_rise_time'])
            self.assertAlmostEqual(true_cfd['crossing_after_start_ns'], expected)


class Quantization(unittest.TestCase):
    def test_bias_survives_without_dither(self):
        low = fr.quantize(0.05)
        self.assertGreater(low['max_abs_bias_lsb'], 0.3)
        self.assertTrue(low['validity'])
        self.assertLess(fr.quantize(0.5)['max_abs_bias_lsb'], 0.005)
        self.assertFalse(fr.quantize(0.5)['validity'])
        self.assertAlmostEqual(fr.quantize(1.0)['sigma_effective_lsb'], math.sqrt(1 + 1 / 12))


class Pileup(unittest.TestCase):
    def test_campbell_moments(self):
        # 2 pulses per tau, exponential amplitudes (<a>=1, <a^2>=2); MC gave mean 5.444, var 7.404
        r = fr.pileup(2e9, 1.0, 2.0, 1.0, 1, False)
        self.assertAlmostEqual(r['mean'], 2 * math.e, places=9)
        self.assertAlmostEqual(r['sigma'] ** 2, math.e ** 2, places=9)

    def test_bipolar_zero_mean_and_transient(self):
        r = fr.pileup(2e9, 1.0, 2.0, 1.0, 1, True)
        self.assertEqual(r['mean'], 0.0)
        self.assertAlmostEqual(r['max_offset_after_rate_step'], 2.0)


class SiPM(unittest.TestCase):
    def test_saturation(self):
        self.assertAlmostEqual(fr.sipm(1000, 1000)['linearity_fraction'], 1 - math.exp(-1))
        self.assertTrue(fr.sipm(1000, 1000)['validity'])

    def test_borel_and_dark_counts(self):
        # datasheet P_ct = 0.2 -> lambda = -ln(0.8); MC of Poisson branching gave P(>1) = 1 - exp(-lambda)
        r = fr.sipm(1000, 10, 0.2, 1e9, 20)
        lam = -math.log(0.8)
        self.assertAlmostEqual(r['crosstalk_cells_per_primary']['mean_secondaries_lambda'], lam)
        self.assertAlmostEqual(r['crosstalk_cells_per_primary']['mean'], 1 / (1 - lam))
        self.assertAlmostEqual(r['crosstalk_cells_per_primary']['variance'], lam / (1 - lam) ** 3)
        with self.assertRaises(ValueError):
            fr.sipm(1000, 10, 0.7)  # lambda > 1: supercritical
        no_xt = fr.sipm(1000, 10, 0.0, 1e9, 20)['dark_counts_in_gate']
        self.assertAlmostEqual(no_xt['mean_cells'], 20.0)
        self.assertAlmostEqual(no_xt['sigma_cells'], math.sqrt(20.0))


class Ballistic(unittest.TestCase):
    def test_deficit_and_approximation(self):
        for tc, deficit in ((0.25, 0.0026), (0.5, 0.0103), (1.0, 0.0398), (2.0, 0.1407)):
            r = fr.ballistic(tc, 1.0, 1)
            self.assertAlmostEqual(r['deficit'], deficit, delta=2e-4)
        self.assertAlmostEqual(fr.ballistic(0.5, 1.0, 1)['approximation_deficit'], 0.25 / 24)
        self.assertTrue(fr.ballistic(2.0, 1.0, 1)['validity'])
        r4 = fr.ballistic(0.25, 1.0, 4)  # n (T_c/t_p)^2 / 24 for CR-(RC)^n
        self.assertAlmostEqual(r4['deficit'], r4['approximation_deficit'], delta=2e-4)


class DeadTime(unittest.TestCase):
    def test_models_and_inversion(self):
        r = fr.deadtime(100, rate_hz=1e6)
        self.assertAlmostEqual(r['measured_rate_hz'], 1e6 / 1.1)
        self.assertAlmostEqual(fr.deadtime(100, measured_hz=r['measured_rate_hz'])['true_rate_hz'], 1e6)
        p = fr.deadtime(100, rate_hz=1e6, model='paralyzable')
        self.assertAlmostEqual(p['measured_rate_hz'], 1e6 * math.exp(-0.1))
        back = fr.deadtime(100, measured_hz=p['measured_rate_hz'], model='paralyzable')
        self.assertAlmostEqual(back['true_rate_hz_low_branch'], 1e6, delta=1e-3)
        self.assertTrue(fr.deadtime(100, rate_hz=2e7, model='paralyzable')['validity'])
        near_max = fr.deadtime(100, measured_hz=0.36787 / 100e-9, model='paralyzable')
        self.assertAlmostEqual(near_max['true_rate_hz_low_branch'] * 100e-9, 0.99285, delta=2e-5)


class ClusterNoise(unittest.TestCase):
    def test_correlated_sum(self):
        self.assertAlmostEqual(fr.cluster_noise(25, 1.0, 0.1)['sigma_sum'], math.sqrt(85))
        self.assertAlmostEqual(fr.cluster_noise(9, 1.0, 0.0)['sigma_sum'], 3.0)
        with self.assertRaises(ValueError):
            fr.cluster_noise(5, 1.0, -0.5)


class CommandLine(unittest.TestCase):
    CASES = (
        ['enc', '--capacitance', '10', '--peaking', '25', '--en', '1', '--leakage', '1000'],
        ['noise-rate', '--threshold', '4', '--peaking', '25', '--order', '1', '--noise-type', 'series'],
        ['noise-rate', '--threshold', '5', '--peaking', '25', '--channels', '100000000', '--window', '25'],
        ['leakage-scale', '--current', '1', '--from-celsius', '20', '--to-celsius', '-10'],
        ['timing', '--rise', '1', '--snr', '3', '--threshold', '0.5', '--amplitudes', '0.6', '1',
         '--cfd-fraction', '0.3', '--cfd-delay', '0.5', '--tdc-lsb', '25'],
        ['quantize', '--noise-lsb', '0'],
        ['pileup', '--rate', '2e9', '--mean-amp', '1', '--peaking', '1', '--bipolar'],
        ['sipm', '--cells', '1000', '--npe', '3000', '--crosstalk', '0.2', '--dcr', '1e9', '--gate', '20'],
        ['ballistic', '--collection', '50', '--peaking', '25'],
        ['deadtime', '--dead-time', '100', '--rate', '2e7', '--model', 'paralyzable'],
        ['cluster-noise', '--channels', '25', '--sigma', '1', '--rho', '0.1'],
    )
    BAD = (
        ['enc', '--capacitance', '-1', '--peaking', '25'],
        ['enc', '--capacitance', '10', '--peaking', 'nan'],
        ['sipm', '--cells', '1000', '--npe', '10', '--crosstalk', '1'],
        ['deadtime', '--dead-time', '100', '--measured', '2e7'],
        ['timing', '--rise', '1', '--snr', '10', '--threshold', '0.5'],
        ['cluster-noise', '--channels', '0', '--sigma', '1', '--rho', '0'],
        ['noise-rate', '--threshold', '4', '--peaking', '25', '--channels', '2.5'],
        ['sipm', '--cells', '2.5', '--npe', '1'],
        ['enc', '--capacitance', '1e200', '--en', '1e200', '--peaking', '25'],
        ['enc', '--capacitance', '10', '--en', '1', '--leakage', '1', '--peaking', '1e-300'],
        ['noise-rate', '--threshold', '4', '--peaking', '25', '--series-fraction', '0.5'],
    )

    def run_cli(self, args):
        return subprocess.run([sys.executable, '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=60)

    def test_outputs_are_strict_json(self):
        for args in self.CASES:
            proc = self.run_cli(args)
            self.assertEqual(proc.returncode, 0, msg=f'{args}: {proc.stderr}')
            out = strict_json(proc.stdout)
            self.assertEqual(out['command'], args[0])

    def test_bad_inputs_fail_cleanly(self):
        for args in self.BAD:
            proc = self.run_cli(args)
            self.assertNotEqual(proc.returncode, 0, msg=str(args))
            self.assertNotIn('Traceback', proc.stderr, msg=str(args))


if __name__ == '__main__':
    unittest.main()
