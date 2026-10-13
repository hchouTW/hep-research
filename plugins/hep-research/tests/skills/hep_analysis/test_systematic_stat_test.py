"""ANA-P2-5: systematic-variation check with a statistical test, NaN and malformed input. Synthetic histograms."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'skills' / 'hep-analysis' / 'scripts' / 'check_systematic_variations.py'
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
                      'nominal_sumw2': NOM, 'up_sumw2': up, 'down_sumw2': [x * 0.95 for x in NOM]})
        out = json.loads(p.stdout)
        self.assertEqual(out['up']['effect'], 'normalization')
        self.assertIn('cannot be inferred from integrals', out['direction'])

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


if __name__ == '__main__':
    unittest.main()
