"""ANA-P2-2: tabulated nuclear masses (AME2020 + CODATA 2022) and the --radius-re rename. Reference values: PDG/CODATA
deuteron mass 1875.61294 MeV, alpha 3727.3794 MeV, proton 938.27209 MeV."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills' / 'hep-measurement' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from geomagnetic_cutoff import cutoff_kinetic_energy_per_nucleon_gev, nuclear_mass_gev  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, '-I', str(SCRIPTS / 'geomagnetic_cutoff.py'), *args], capture_output=True,
                          text=True, timeout=60)


class NuclearMassTests(unittest.TestCase):
    def test_tabulated_masses(self):
        for (z, a), mev in {(1, 1): 938.27209, (1, 2): 1875.61294, (2, 4): 3727.3794}.items():
            with self.subTest(z=z, a=a):
                mass, source = nuclear_mass_gev(z, a)
                self.assertAlmostEqual(mass * 1000, mev, delta=0.01)  # MeV
                self.assertIn(source, ('AME2020 table', 'CODATA 2022 proton mass'))

    def test_fallback_is_flagged(self):
        mass, source = nuclear_mass_gev(26, 56)
        self.assertIn('approximation', source)
        self.assertAlmostEqual(mass, 56 * 0.93149410372)

    def test_deuteron_energy_uses_the_real_mass(self):
        e = cutoff_kinetic_energy_per_nucleon_gev(4.0, 1, 2)
        m = 1.87561294
        self.assertAlmostEqual(e, ((4.0 ** 2 + m ** 2) ** 0.5 - m) / 2, places=6)

    def test_radius_re_and_deprecated_alias(self):
        new = run('--latitude', '40', '--radius-re', '1.0627')
        old = run('--latitude', '40', '--altitude-re', '1.0627')
        self.assertEqual(new.returncode, 0, new.stderr)
        self.assertEqual(old.returncode, 0, old.stderr)
        self.assertIn('deprecated', old.stderr)
        self.assertEqual(json.loads(new.stdout)['vertical_cutoff_rigidity_gv'],
                         json.loads(old.stdout)['vertical_cutoff_rigidity_gv'])
        self.assertEqual(run('--latitude', '40', '--radius-re', '1', '--altitude-re', '1').returncode, 2)

    def test_mass_source_in_output(self):
        out = json.loads(run('--latitude', '40', '--charge', '1', '--mass-number', '2').stdout)
        self.assertEqual(out['mass_source'], 'AME2020 table')
        self.assertAlmostEqual(out['nuclear_mass_gev'], 1.87561294, places=6)


if __name__ == '__main__':
    unittest.main()
