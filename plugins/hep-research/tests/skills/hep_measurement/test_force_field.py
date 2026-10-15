"""ANA-P2-3: force-field input validation and energy kinds. Oracle computed by hand: He-4 (m = 3.7273794 GeV, Z = 2,
A = 4) at 1 GeV/n, phi = 0.5 GV: E = 4 GeV, E' = 5 GeV, (2mE + E^2)/(2mE' + E'^2) = 45.8190/62.2738 = 0.735768.
(The audit quoted 0.73578; the hand value rounds to 0.73577.) Synthetic values only."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-measurement' / 'scripts' / 'solar_modulation_force_field.py'
M_HE4 = 3.7273794
BASE = ['--mass', str(M_HE4), '--charge', '2', '--phi', '0.5', '--lis-normalization', '1e4', '--lis-index', '2.7']


def run(*args):
    return subprocess.run([sys.executable, '-I', str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def ok(*args):
    p = run(*args)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


class ForceFieldTests(unittest.TestCase):
    def test_jacobian_is_the_same_in_all_energy_kinds(self):
        jac = (2 * M_HE4 * 4 + 16) / (2 * M_HE4 * 5 + 25)
        self.assertAlmostEqual(jac, 0.735768, places=6)
        rigidity = math.sqrt(4 * (4 + 2 * M_HE4)) / 2
        for args in (['--energy', '4'], ['--energy', '1', '--energy-kind', 'Ek_per_nucleon', '--mass-number', '4'],
                     ['--energy', repr(rigidity), '--energy-kind', 'rigidity']):
            with self.subTest(args=args):
                out = ok('--modulate', *args, *BASE)
                self.assertAlmostEqual(out['jacobian'], jac, places=9)
                self.assertAlmostEqual(out['kinetic_energy_lis_gev'], 5.0, places=9)

    def test_rigidity_flux_factor_includes_beta(self):
        rigidity = math.sqrt(4 * (4 + 2 * M_HE4)) / 2
        out = ok('--modulate', '--energy', repr(rigidity), '--energy-kind', 'rigidity', *BASE)
        beta = lambda ek: math.sqrt(ek * (ek + 2 * M_HE4)) / (ek + M_HE4)  # noqa: E731
        self.assertAlmostEqual(out['flux_factor'], out['jacobian'] * beta(4.0) / beta(5.0), places=9)

    def test_phi_in_mv_and_uncertainty(self):
        a = ok('--modulate', '--energy', '4', *BASE)
        b = ok('--modulate', '--energy', '4', *[x if x != '0.5' else '500' for x in BASE], '--phi-unit', 'MV',
               '--phi-uncertainty', '50')
        self.assertAlmostEqual(a['flux_toa'], b['flux_toa'], places=9)
        self.assertGreater(b['sigma_flux_toa_from_phi'], 0)

    def test_tabulated_lis(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / 'lis.json'
            table.write_text(json.dumps({'variable': 'Ek_total', 'points': [[1, 1e4], [10, 1e4 * 10 ** -2.7]]}))
            out = ok('--modulate', '--energy', '4', '--mass', str(M_HE4), '--charge', '2', '--phi', '0.5',
                     '--lis-table', str(table))
            ref = ok('--modulate', '--energy', '4', *BASE)
            self.assertAlmostEqual(out['flux_toa'] / ref['flux_toa'], 1.0, places=9)
            p = run('--modulate', '--energy', '9.5', '--mass', str(M_HE4), '--charge', '2', '--phi', '0.5',
                    '--lis-table', str(table))
            self.assertEqual(p.returncode, 2)  # LIS needed above the table: no extrapolation

    def test_phi_zero_returns_the_lis_exactly(self):
        for kind, extra in (('Ek_total', []), ('Ek_per_nucleon', ['--mass-number', '4']), ('rigidity', [])):
            with self.subTest(kind=kind):
                out = ok('--modulate', '--energy', '3', '--energy-kind', kind, *extra, '--mass', str(M_HE4),
                         '--charge', '2', '--phi', '0', '--lis-normalization', '1e4', '--lis-index', '2.7')
                self.assertEqual(out['flux_toa'], out['flux_lis'])
                self.assertEqual(out['jacobian'], 1.0)

    def test_per_nucleon_shift_scales_with_z_over_a(self):
        # (Z, A, nuclear mass in GeV; synthetic inputs): p, He-4, C-12
        for z, a, m in ((1, 1, 0.93827208943), (2, 4, M_HE4), (6, 12, 11.174862)):
            with self.subTest(z=z, a=a):
                out = ok('--modulate', '--energy', '1', '--energy-kind', 'Ek_per_nucleon', '--mass-number', str(a),
                         '--mass', str(m), '--charge', str(z), '--phi', '0.6', '--lis-normalization', '1e4',
                         '--lis-index', '2.7')
                self.assertAlmostEqual(out['energy_lis'] - 1.0, z / a * 0.6, places=9)

    def test_rigidity_conversion_is_the_core_one(self):
        sys.path.insert(0, str(ROOT))
        from core.kinematics.relativistic import Species, convert
        out = ok('--modulate', '--energy', '3.0', '--energy-kind', 'rigidity', *BASE)
        sp = Species(Z=2, A=4, mass=M_HE4)
        self.assertAlmostEqual(out['kinetic_energy_toa_gev'], convert(3.0, 'rigidity', 'kinetic_energy', sp), places=12)
        self.assertAlmostEqual(out['energy_lis'], convert(out['kinetic_energy_lis_gev'], 'kinetic_energy', 'rigidity', sp),
                               places=12)
        text = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('from core.kinematics.relativistic import', text)
        self.assertIn('Eqs. (13)-(16)', text)

    def test_invalid_inputs_exit_2(self):
        for bad in (['--lis-index=nan'], ['--lis-normalization', '-1'], ['--phi', 'nan']):
            with self.subTest(bad=bad):
                args = ['--modulate', '--energy', '4', *BASE, *bad]
                p = run(*args)
                self.assertEqual(p.returncode, 2, p.stdout)
                self.assertNotIn('Traceback', p.stderr)
        p = run('--modulate', '--energy', '1', '--energy-kind', 'Ek_per_nucleon', *BASE)
        self.assertEqual(p.returncode, 2)


if __name__ == '__main__':
    unittest.main()
