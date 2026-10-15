"""ANA-P2-4: continuous broken power law with a free break. Synthetic spectrum from
skills/hep-measurement/assets/cosmic-ray-spectrum.example.json (indices 2.7 / 3.1, break 4e15), toys seeded."""
import json
import math
import random
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills' / 'hep-measurement' / 'scripts'
ASSET = ROOT / 'skills' / 'hep-measurement' / 'assets' / 'cosmic-ray-spectrum.example.json'
sys.path.insert(0, str(SCRIPTS))
from cr_spectrum_powerlaw_fit import broken_log_flux, fit_spectrum  # noqa: E402

DOC = json.loads(ASSET.read_text(encoding='utf-8'))
TRUE = DOC['generated_from']
POINTS = DOC['points']


class BrokenPowerLawTests(unittest.TestCase):
    def test_exact_spectrum_is_recovered(self):
        out = fit_spectrum(POINTS, 'broken')
        self.assertAlmostEqual(out['index_below'], TRUE['index_below_break'], places=8)
        self.assertAlmostEqual(out['index_above'], TRUE['index_above_break'], places=8)
        self.assertAlmostEqual(out['break_energy'] / TRUE['break_energy_ev'], 1.0, places=6)

    def test_model_is_continuous_at_the_break(self):
        for s in (None, 0.2):
            eb = 4e15
            lo = broken_log_flux(eb * (1 - 1e-12), 1.0, 2.7, 3.1, eb, s)
            hi = broken_log_flux(eb * (1 + 1e-12), 1.0, 2.7, 3.1, eb, s)
            self.assertLess(abs(lo - hi), 1e-9)

    def test_toys_recover_indices_and_break_within_two_sigma(self):
        rng = random.Random(20261013)
        rel = 0.05
        pulls = {'index_below': [], 'index_above': [], 'break': []}
        for _ in range(200):
            toy = [[e, f * (1 + rel * rng.gauss(0, 1)), f * rel] for e, f in POINTS]
            out = fit_spectrum(toy, 'broken')
            self.assertIsNotNone(out['p_value'])
            pulls['index_below'].append((out['index_below'] - TRUE['index_below_break']) / out['index_below_uncertainty'])
            pulls['index_above'].append((out['index_above'] - TRUE['index_above_break']) / out['index_above_uncertainty'])
            pulls['break'].append((math.log(out['break_energy'] / TRUE['break_energy_ev']))
                                  / out['log_break_energy_uncertainty'])
        for name, values in pulls.items():
            with self.subTest(name=name):
                inside = sum(1 for v in values if abs(v) < 2) / len(values)
                self.assertGreater(inside, 0.85, inside)
                self.assertLess(abs(sum(values) / len(values)), 0.5)

    def test_chi2_pvalue_and_break_label(self):
        toy = [[e, f, 0.05 * f] for e, f in POINTS]
        out = fit_spectrum(toy, 'broken')
        self.assertAlmostEqual(out['chi2'], 0.0, places=6)
        self.assertEqual(out['ndf'], len(POINTS) - 4)
        self.assertIn('global_significance.py', out['break_test']['label'])
        self.assertGreater(out['break_test']['delta_chi2_vs_single'], 0)

    def test_covariance_asymmetric_errors_pivot_and_edges(self):
        n = len(POINTS)
        cov = [[(0.05 * POINTS[i][1]) ** 2 if i == j else 0.0 for j in range(n)] for i in range(n)]
        a = fit_spectrum([[e, f, 0.05 * f] for e, f in POINTS], 'broken', pivot=1e15)
        b = fit_spectrum([[e, f] for e, f in POINTS], 'broken', covariance=cov, pivot=1e15)
        # the linearized covariance has a central finite-difference column in log E_b (h = 1e-6), so the two paths
        # agree to about eps/h relative: about 1e-8 on the supported Pythons (3.13+). Historical: 9e-8 was seen on 3.11,
        # before float sum() became compensated in 3.12; 3.11 is no longer supported and the tolerance is unchanged.
        self.assertAlmostEqual(a['index_below_uncertainty'], b['index_below_uncertainty'],
                               delta=1e-6 * a['index_below_uncertainty'])
        c = fit_spectrum([[e, f, 0.04 * f, 0.06 * f] for e, f in POINTS], 'broken')
        self.assertAlmostEqual(c['index_below'], 2.7, places=6)
        self.assertGreater(a['pivot']['flux_relative_uncertainty'], 0)
        edges = [[e / 1.1, e * 1.1] for e, _ in POINTS]
        lw = fit_spectrum([[e, f, 0.05 * f] for e, f in POINTS], 'broken', edges=edges, bin_centre='lafferty-wyatt')
        self.assertEqual(len(lw['point_energies']), n)

    def test_smooth_break_and_cli(self):
        out = fit_spectrum(POINTS, 'smooth-broken', smoothness=0.05)
        self.assertAlmostEqual(out['index_below'], 2.7, delta=0.05)
        p = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'cr_spectrum_powerlaw_fit.py'), '--input', str(ASSET),
                            '--free-break', '--pivot', '1e15'], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(json.loads(p.stdout)['break_free'])


if __name__ == '__main__':
    unittest.main()
