"""ANA-P2-5: systematic-variation check with a statistical test, NaN and malformed input. Synthetic histograms."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-measurement' / 'scripts' / 'check_systematic_variations.py'
sys.path.insert(0, str(SCRIPT.parent))
import check_systematic_variations as csv_  # noqa: E402

NOM = [10000.0, 20000.0, 30000.0, 20000.0, 10000.0]


def run_json(doc, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'h.json'
        f.write_text(doc if isinstance(doc, str) else json.dumps(doc))
        return subprocess.run([sys.executable, '-I', str(SCRIPT), '--json', str(f), *extra], capture_output=True,
                              text=True, timeout=60)


class StatTestTests(unittest.TestCase):
    def test_tiny_wiggle_with_one_percent_errors_is_none(self):
        up = [x * (1 + 1e-5 * (-1) ** i) for i, x in enumerate(NOM)]
        down = [x * (1 - 1e-5 * (-1) ** i) for i, x in enumerate(NOM)]
        var = [(0.01 * x) ** 2 for x in NOM]
        out = csv_.assess(NOM, up, down, variances={'up': var, 'down': var})
        self.assertEqual((out['up']['effect'], out['down']['effect']), ('none', 'none'))
        self.assertNotEqual(out['up']['tolerance_effect'], 'none')  # the old tolerance call flagged it
        p = run_json({'nominal': NOM, 'up': up, 'down': down}, '--stat-unc', '0.01')
        self.assertEqual(json.loads(p.stdout)['up']['effect'], 'none')

    def test_genuine_five_percent_shape_change_is_shape(self):
        tilt = [1.05, 1.025, 1.0, 0.975, 0.95]
        up = [x * t for x, t in zip(NOM, tilt)]
        s = sum(NOM) / sum(up)
        up = [x * s for x in up]  # same integral, changed shape
        down = [x * (2 - t) * s for x, t in zip(NOM, tilt)]
        var = [(0.01 * x) ** 2 for x in NOM]
        out = csv_.assess(NOM, up, down, variances={'up': var, 'down': var})
        self.assertEqual(out['up']['effect'], 'shape')
        self.assertLess(out['up']['statistical_test']['shape_p_value'], 1e-6)

    def test_sumw2_in_json_and_direction_note(self):
        up = [x * 1.05 for x in NOM]
        p = run_json({'nominal': NOM, 'up': up, 'down': [x * 0.95 for x in NOM],
                      'nominal_sumw2': NOM, 'up_sumw2': up, 'down_sumw2': [x * 0.95 for x in NOM]}, '--independent')
        out = json.loads(p.stdout)
        self.assertEqual(out['up']['effect'], 'normalization')
        self.assertIsInstance(out['up']['statistical_test'], dict)
        self.assertIn('cannot be inferred from integrals', out['direction'])


def same_event_scale_shift(scale=1.03, n=20000, bins=20, width=10.0, seed=7):
    """Nominal and a scale-shifted variation filled from the SAME events (as a JES variation is), with per-sample
    sumw2 = counts, the content of the ROOT fixture in tests/skills/hep_computing/make_root_fixtures.py."""
    import random
    rng = random.Random(seed)
    nom, var = [0.0] * bins, [0.0] * bins
    for _ in range(n):
        x = rng.expovariate(1 / 50.0)
        for h, v in ((nom, x), (var, scale * x)):
            if v < bins * width:
                h[int(v // width)] += 1.0
    return nom, var


class SameEventVariationTests(unittest.TestCase):
    """Integration finding (PR #64): per-sample variances combined as if independent hid a 3% JES shift made from
    the same events ('none', 'neither variation changes this histogram')."""

    def setUp(self):
        self.nom, self.up = same_event_scale_shift(1.03)
        _, self.down = same_event_scale_shift(0.97)
        self.doc = {'nominal': self.nom, 'up': self.up, 'down': self.down,
                    'nominal_sumw2': self.nom, 'up_sumw2': self.up, 'down_sumw2': self.down}

    def test_per_sample_sumw2_without_independent_makes_no_test(self):
        out = json.loads(run_json(self.doc).stdout)
        for label in ('up', 'down'):
            self.assertNotEqual(out[label]['effect'], 'none')
            self.assertNotIn('statistical_test', out[label])
        self.assertIn('independent', out['statistical_test'])
        self.assertFalse(any('neither variation changes' in w for w in out['warnings']))

    def test_variance_of_the_difference_detects_the_shift(self):
        # the uncorrelated part of a same-event difference: events that changed bin (here Poisson on |diff|)
        doc = {'nominal': self.nom, 'up': self.up, 'down': self.down,
               'up_diff_sumw2': [max(abs(u - n), 1.0) for n, u in zip(self.nom, self.up)],
               'down_diff_sumw2': [max(abs(d - n), 1.0) for n, d in zip(self.nom, self.down)]}
        out = json.loads(run_json(doc).stdout)
        self.assertIn(out['up']['effect'], ('shape', 'mixed'))
        self.assertIsInstance(out['up']['statistical_test'], dict)

    def test_independent_flag_restores_the_combined_test(self):
        out = json.loads(run_json(self.doc, '--independent').stdout)
        self.assertIsInstance(out['up']['statistical_test'], dict)

    def test_diff_and_per_sample_variances_together_are_refused(self):
        doc = dict(self.doc, up_diff_sumw2=self.nom, down_diff_sumw2=self.nom)
        p = run_json(doc)
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('Traceback', p.stderr)

    def test_flow_bins_are_honoured_for_json(self):
        doc = {'nominal': NOM, 'up': NOM, 'down': NOM, 'underflow': {'nominal': 100, 'up': 200, 'down': 100},
               'overflow': {'nominal': 100, 'up': 100, 'down': 100}}
        plain = json.loads(run_json(doc).stdout)
        flow = json.loads(run_json(doc, '--include-flow').stdout)
        self.assertEqual(plain['up']['effect'], 'none')
        self.assertNotEqual(flow['up']['effect'], 'none')
        self.assertEqual(run_json({'nominal': NOM, 'up': NOM, 'down': NOM}, '--include-flow').returncode, 2)

    def test_nan_and_malformed_input_exit_2(self):
        for doc in ('{"nominal": [1, NaN], "up": [1, 2], "down": [1, 2]}', '{"nominal": [1, 2', '{"nominal": [1]}'):
            with self.subTest(doc=doc):
                p = run_json(doc)
                self.assertEqual(p.returncode, 2)
                self.assertNotIn('Traceback', p.stderr)



class NeitherVariationWarningTests(unittest.TestCase):
    """The 'neither variation' warning names what was actually checked: a statistical test only when one was made."""

    def test_unchanged_bins_say_no_change(self):
        out = csv_.assess(NOM, NOM, NOM)
        self.assertTrue(any('neither variation changes this histogram' in w for w in out['warnings']))

    def test_changed_bins_within_their_errors_say_not_significant(self):
        up = [x * (1 + 1e-5 * (-1) ** i) for i, x in enumerate(NOM)]
        down = [x * (1 - 1e-5 * (-1) ** i) for i, x in enumerate(NOM)]
        var = [(0.01 * x) ** 2 for x in NOM]
        out = csv_.assess(NOM, up, down, variances={'up': var, 'down': var})
        self.assertTrue(any('neither variation is significant at alpha = 0.01' in w for w in out['warnings']), out['warnings'])
        self.assertFalse(any('changes this histogram' in w for w in out['warnings']))

    def test_changed_bins_without_a_test_never_claim_significance(self):
        # one small bin moves beyond the tolerance; the integral and the peak-normalized shape stay within it
        nom = [1e6, 1.0, 1e6]
        up = [1e6, 1.0 + 2e-6, 1e6]
        out = csv_.assess(nom, up, nom)
        self.assertEqual(out['up']['effect'], 'none')
        self.assertTrue(out['up']['bins_changed'])
        self.assertFalse(any('significant' in w for w in out['warnings']), out['warnings'])
        self.assertFalse(any('changes this histogram' in w for w in out['warnings']), out['warnings'])
        self.assertTrue(any('tolerance' in w for w in out['warnings']), out['warnings'])
        self.assertNotIn('no bin differs', out['up']['note'])
        # the same with per-sample variances of same-event variations (no test made, NO_TEST_CORRELATED)
        out = csv_.assess(nom, up, nom, no_test=csv_.NO_TEST_CORRELATED)
        self.assertFalse(any('significant' in w for w in out['warnings']), out['warnings'])


if __name__ == '__main__':
    unittest.main()
