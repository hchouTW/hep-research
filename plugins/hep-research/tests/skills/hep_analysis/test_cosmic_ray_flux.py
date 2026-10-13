"""cosmic_ray_flux.py: bin-width unit (ANA-P0-1). Synthetic values only."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-analysis' / 'scripts' / 'cosmic_ray_flux.py'


def run(*args):
    return subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), *args], capture_output=True, text=True,
                          timeout=120)


class BinWidthUnitTests(unittest.TestCase):
    def test_tev_bin_given_in_gv(self):
        # 4 counts in a 1.3-2.0 TV bin: the width is 700 GV, not 0.7.
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700', '--bin-width-unit', 'GV')
        self.assertEqual(p.returncode, 0, p.stderr)
        out = json.loads(p.stdout)
        self.assertEqual(out['bin_width_unit'], 'GV')
        self.assertEqual(f"{out['flux']:.3e}", '2.857e-10')
        self.assertEqual(f"{out['flux_lower']:.2e}", '1.49e-10')
        self.assertEqual(f"{out['flux_upper']:.2e}", '5.12e-10')

    def test_unit_is_required_and_the_error_names_the_rule(self):
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(p.stdout, '')
        self.assertIn('--bin-width-unit', p.stderr)
        self.assertIn('600 for a 1.2-1.8 TV bin', p.stderr)
        self.assertNotIn('Traceback', p.stderr)

    def test_unknown_unit_is_refused(self):
        p = run('--counts', '4', '--exposure', '2.0e7', '--bin-width', '700', '--bin-width-unit', 'MV')
        self.assertEqual(p.returncode, 2)

    def test_help_states_the_rule(self):
        p = run('--help')
        self.assertEqual(p.returncode, 0)
        self.assertIn('never pass a width in TV', ' '.join(p.stdout.split()))

    def test_guide_has_no_tev_width_example(self):
        for path in (ROOT / 'skills').rglob('*.md'):
            self.assertNotIn('0.6 for a 1.2', path.read_text(encoding='utf-8'), str(path))


if __name__ == '__main__':
    unittest.main()
