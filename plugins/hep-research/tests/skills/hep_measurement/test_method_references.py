"""ANA-P3: the worked numeric examples (synthetic) in the hep-measurement method references are recomputed here, and every
reference is reachable from the guide's routing table."""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REFS = ROOT / 'skills' / 'hep-measurement' / 'references'
SCRIPTS = ROOT / 'skills' / 'hep-measurement' / 'scripts'


def text(name):
    return (REFS / name).read_text(encoding='utf-8')


class ReachabilityTests(unittest.TestCase):
    def test_every_reference_is_routed_from_the_guide(self):
        guide = text('hep-measurement-guide.md')
        for path in sorted(REFS.glob('*.md')):
            if path.name == 'hep-measurement-guide.md':
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
        template = json.loads((ROOT / 'skills' / 'hep-measurement' / 'assets' / 'measurement_spec.template.json')
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


class SpilloverTests(unittest.TestCase):
    def test_power_law_smearing_factor(self):
        import math
        gamma = 2.7
        for s, quoted in ((0.10, 0.015), (0.30, 0.14)):
            # numerical: true dN/dx ~ exp(-(gamma-1) x) in x = ln E, Gaussian smearing in x
            k = gamma - 1
            h = s / 50
            num = sum(math.exp(-k * (-i * h)) * math.exp(-0.5 * (i * h / s) ** 2) for i in range(-400, 401)) * h
            ratio = num / (s * math.sqrt(2 * math.pi))
            self.assertAlmostEqual(ratio, math.exp(k * k * s * s / 2), places=6)
            self.assertAlmostEqual(ratio - 1, quoted, delta=0.003)


class ChargeConfusionTests(unittest.TestCase):
    def test_confusion_bias_and_inversion(self):
        n_plus, r, c_plus, c_minus = 1.0e8, 1.0e-4, 1.0e-5, 0.0
        n_minus = r * n_plus
        obs_plus = (1 - c_plus) * n_plus + c_minus * n_minus
        obs_minus = c_plus * n_plus + (1 - c_minus) * n_minus
        self.assertAlmostEqual(obs_minus / n_plus, 1.1e-4, delta=1e-9)
        det = (1 - c_plus) * (1 - c_minus) - c_plus * c_minus
        true_minus = ((1 - c_plus) * obs_minus - c_plus * obs_plus) / det
        self.assertAlmostEqual(true_minus / n_plus, r, delta=1e-12)
        self.assertIn('1.1e-4', text('backgrounds.md'))


class NucleiTests(unittest.TestCase):
    def test_survival_and_feed_down(self):
        import math
        surv = math.exp(-10 / 20)
        self.assertAlmostEqual(surv, 0.607, delta=5e-4)
        self.assertAlmostEqual(1 / surv, 1.65, delta=5e-3)
        self.assertAlmostEqual(1000 * (1 - 0.55) * 0.10, 45.0)
        t = text('correction-chain.md')
        self.assertIn('P = 0.607', t)
        self.assertIn('= 45 events', t)


class TriggerEfficiencyTests(unittest.TestCase):
    def test_unbiased_sample_and_bootstrap(self):
        sys.path.insert(0, str(ROOT))
        from core.stats.tail_estimation import clopper_pearson
        lo, hi = clopper_pearson(1900, 2000, 0.6827)
        self.assertAlmostEqual(lo, 0.945, delta=0.001)
        self.assertAlmostEqual(hi, 0.955, delta=0.001)
        self.assertAlmostEqual(0.90 * 0.98, 0.882)
        t = text('analysis-design.md')
        self.assertIn('[0.945, 0.955]', t)
        self.assertIn('eps(T2) = 0.882', t)


class OptimizationTests(unittest.TestCase):
    def test_figures_of_merit(self):
        import math
        s, b = 10.0, 100.0
        self.assertAlmostEqual(s / math.sqrt(s + b), 0.953, delta=5e-4)
        self.assertAlmostEqual(math.sqrt(2 * ((s + b) * math.log(1 + s / b) - s)), 0.984, delta=5e-4)
        self.assertAlmostEqual(0.5 / (3 / 2 + math.sqrt(b)), 0.0435, delta=5e-5)
        t = text('analysis-design.md')
        for n in ('0.953', '0.984', '0.0435'):
            self.assertIn(n, t)


class FixedTargetTests(unittest.TestCase):
    def test_empty_target_and_absorption(self):
        import math
        self.assertEqual(1000 - 100 * (1.0e12 / 5.0e11), 800)
        l_eff = 40 * (1 - math.exp(-2 / 40))
        self.assertAlmostEqual(l_eff, 1.951, delta=5e-4)
        self.assertAlmostEqual(1 - l_eff / 2, 0.025, delta=5e-4)
        t = text('correction-chain.md')
        self.assertIn('L_eff = 1.951 cm', t)


class LookElsewhereTests(unittest.TestCase):
    def test_independent_trials(self):
        from statistics import NormalDist
        p_global = 1 - (1 - 1.0e-3) ** 50
        self.assertAlmostEqual(p_global, 0.0488, delta=5e-5)
        self.assertAlmostEqual(NormalDist().inv_cdf(1 - p_global), 1.66, delta=0.005)
        self.assertAlmostEqual(NormalDist().inv_cdf(1 - 1.0e-3), 3.09, delta=0.005)
        self.assertIn('0.0488', text('analysis-design.md'))


if __name__ == '__main__':
    unittest.main()
