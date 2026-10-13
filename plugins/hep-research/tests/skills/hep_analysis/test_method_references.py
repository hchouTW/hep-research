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


class EstimandTests(unittest.TestCase):
    def test_example_estimands_pass_the_validator(self):
        sys.path.insert(0, str(ROOT))
        from contracts.validate import validate_artifact
        examples = re.findall(r'^- (?:Collider|Cosmic ray|Neutrino): "(.*?)"', text('measurements-and-unfolding.md'),
                              re.M | re.S)
        self.assertEqual(len(examples), 3)
        template = json.loads((ROOT / 'skills' / 'hep-analysis' / 'assets' / 'measurement_spec.template.json')
                              .read_text(encoding='utf-8'))
        for est in examples:
            with self.subTest(estimand=est[:40]):
                template['extension']['estimand'] = ' '.join(est.split())
                rep = validate_artifact(template, strict=True)
                self.assertTrue(rep.ok, rep.as_dict())
        template['extension']['estimand'] = 'helium flux'
        self.assertFalse(validate_artifact(template).ok)


class SystematicsBudgetTests(unittest.TestCase):
    def test_worked_budget(self):
        import math
        shifts = [1.2, -0.4, 2.0, 0.8]
        self.assertEqual(max(abs(x) for x in shifts), 2.0)
        self.assertAlmostEqual(math.sqrt(sum(x * x for x in shifts) / 4), 1.25, delta=0.005)
        self.assertAlmostEqual(math.hypot(2.0, 1.5, 0.5), 2.55, delta=0.005)
        self.assertAlmostEqual(math.hypot(2.0, 0.5), 2.06, delta=0.005)
        t = text('systematics.md')
        for number in ('2.55%', '2.06%', '1.25%'):
            self.assertIn(number, t)


class TimeDependenceTests(unittest.TestCase):
    def test_exposure_weighted_average(self):
        n, e = (100, 30), (1.0e4, 2.0e3)
        weighted = sum(n) / sum(e)
        plain = (n[0] / e[0] + n[1] / e[1]) / 2
        self.assertAlmostEqual(weighted, 1.083e-2, delta=1e-5)
        self.assertAlmostEqual(plain, 1.25e-2, places=9)
        self.assertAlmostEqual(plain / weighted - 1, 0.15, delta=0.01)
        self.assertIn('1.083e-2', text('correction-chain.md'))


if __name__ == '__main__':
    unittest.main()
