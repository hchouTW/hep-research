"""ANA-P2-1: orbit-averaged cutoff with a tilted dipole and Earth rotation. The pole position is a synthetic test input
(an IGRF-like epoch value given by the caller), not a default of the script."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills' / 'hep-analysis' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from geomagnetic_cutoff import stormer_cutoff_gv  # noqa: E402
from orbit_averaged_geomagnetic_cutoff import orbit_cutoff_profile, tilted_dipole_profile  # noqa: E402

POLE = (80.7, -72.7)  # synthetic test input


class TiltedDipoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = tilted_dipole_profile(51.6, *POLE, altitude_re=1.065, days=30, step_s=20, thresholds_gv=[1, 5])

    def test_latitude_range_reaches_inclination_plus_tilt(self):
        lo, hi = self.p['geomagnetic_latitude_range_deg']
        expected = 51.6 + (90.0 - POLE[0])
        self.assertAlmostEqual(hi, expected, delta=0.3)
        self.assertAlmostEqual(lo, -expected, delta=0.3)

    def test_minimum_cutoff_is_the_stormer_value_at_the_extreme_latitude(self):
        expected = stormer_cutoff_gv(51.6 + 90.0 - POLE[0], 1.065)  # about 0.73 GV
        self.assertAlmostEqual(self.p['min_cutoff_gv'], expected, delta=0.05 * expected)
        self.assertLess(self.p['min_cutoff_gv'], 0.8)
        untilted = orbit_cutoff_profile(51.6, altitude_re=1.065)
        self.assertGreater(untilted['min_cutoff_gv'], 2.5 * self.p['min_cutoff_gv'])

    def test_time_fractions_and_table_are_consistent(self):
        fr = {x['cutoff_gv']: x['fraction'] for x in self.p['time_fraction_below']}
        self.assertTrue(0 < fr[1.0] < fr[5.0] < 1)
        self.assertAlmostEqual(sum(r['time_fraction'] for r in self.p['exposure_vs_cutoff']), 1.0, places=9)

    def test_untilted_mode_is_labelled_planning(self):
        self.assertIn('planning estimate', orbit_cutoff_profile(51.6)['mode'])

    def test_cli_tilted_mode_and_pole_pair(self):
        script = str(SCRIPTS / 'orbit_averaged_geomagnetic_cutoff.py')
        p = subprocess.run([sys.executable, '-I', script, '--inclination', '51.6', '--pole-lat', '80.7',
                            '--pole-lon', '-72.7', '--days', '2', '--step-s', '60'], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('tilted', json.loads(p.stdout)['mode'])
        p = subprocess.run([sys.executable, '-I', script, '--inclination', '51.6', '--pole-lat', '80.7'],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 2)

    def test_docstring_no_longer_claims_a_jacobian(self):
        text = (SCRIPTS / 'orbit_averaged_geomagnetic_cutoff.py').read_text(encoding='utf-8')
        self.assertNotIn('trapezoidal rule', text)


if __name__ == '__main__':
    unittest.main()
