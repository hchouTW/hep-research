"""ANA-P3: the worked numeric examples (synthetic) in the hep-analysis method references are recomputed here, and every
reference is reachable from the guide's routing table."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REFS = ROOT / 'skills' / 'hep-analysis' / 'references'
SCRIPTS = ROOT / 'skills' / 'hep-analysis' / 'scripts'


def text(name):
    return (REFS / name).read_text(encoding='utf-8')


class ReachabilityTests(unittest.TestCase):
    def test_every_reference_is_routed_from_the_guide(self):
        guide = text('hep-analysis-guide.md')
        for path in sorted(REFS.glob('*.md')):
            if path.name in ('hep-analysis-guide.md', 'data-pipelines.md'):
                continue
            with self.subTest(ref=path.name):
                self.assertIn(f']({path.name}', guide)


class CorrectionChainTests(unittest.TestCase):
    def test_worked_flux(self):
        n, b, acc, t, dr = 40, 4, 0.05, 1.0e5, 10.0
        eps = 0.90 * 0.80 * 0.75
        self.assertAlmostEqual(eps, 0.54)
        flux = (n - b) / (acc * t * eps * dr)
        self.assertAlmostEqual(flux, 1.333e-3, delta=1e-6)
        self.assertIn('1.333e-3', text('correction-chain.md'))
        p = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'cosmic_ray_flux.py'), '--counts', '40', '--background',
                            '4', '--exposure', '2.7e3', '--bin-width', '10', '--bin-width-unit', 'GV'],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertAlmostEqual(json.loads(p.stdout)['flux'], flux, places=12)

    def test_wrong_denominator_factor(self):
        self.assertAlmostEqual(0.54 / (0.90 * 0.80 * 0.54), 1.389, delta=1e-3)
        self.assertIn('1.39 times too high', text('correction-chain.md'))

    def test_factor_names_are_the_validator_categories(self):
        sys.path.insert(0, str(ROOT))
        from contracts.vocab import Vocabulary
        vocab = Vocabulary()
        for cat in re.findall(r'`([a-z]+_efficiency)`', text('correction-chain.md')):
            self.assertTrue(vocab.has('response_corrections', cat), cat)


if __name__ == '__main__':
    unittest.main()
