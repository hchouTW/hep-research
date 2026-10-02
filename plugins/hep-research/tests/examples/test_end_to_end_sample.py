"""Smoke test for assets/end_to_end_sample_analysis.py (ntuple -> cutflow -> pyhf -> yields).

Skipped unless a Python with numpy and pyhf is available: $HEP_PYHF_PYTHON if set,
else the interpreter running the tests.
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get('HEP_PYHF_PYTHON', sys.executable)


def _has_pyhf():
    try:
        return subprocess.run([PYTHON, '-c', 'import numpy, pyhf'], capture_output=True,
                              timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@unittest.skipUnless(_has_pyhf(), 'numpy/pyhf not importable (set HEP_PYHF_PYTHON)')
class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name)
        cls.proc = subprocess.run([PYTHON, str(ROOT_DIR / 'assets/end_to_end_sample_analysis.py'),
                                   '--outdir', str(cls.out), '--seed', '1'],
                                  capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr[-2000:])

    def cutflow(self):
        with (self.out / 'cutflow.csv').open() as handle:
            return {(r['sample'], r['cut']): r for r in csv.DictReader(handle)}

    def test_normalization_uses_full_signed_weight_sum(self):
        rows = self.cutflow()
        # lumi (1e5 pb^-1) * xsec, independent of negative weights and of any cut.
        self.assertAlmostEqual(float(rows[('ttbar', 'all')]['sumw']), 6000.0, places=6)
        self.assertAlmostEqual(float(rows[('signal', 'all')]['sumw']), 200.0, places=6)

    def test_regions_are_orthogonal_and_complete(self):
        rows = self.cutflow()
        for sample in ('ttbar', 'signal'):
            both = int(rows[(sample, 'njet >= 3')]['entries'])
            split = int(rows[(sample, 'CR: njet == 3')]['entries']) + int(rows[(sample, 'SR: njet >= 4')]['entries'])
            self.assertEqual(both, split)

    def test_fit_recovers_injected_signal(self):
        summary = json.loads((self.out / 'summary.json').read_text())
        mu = summary['fitted']['mu']
        tolerance = 3 * mu['error'] if mu['error'] else 0.5
        self.assertLess(abs(mu['value'] - 1.0), tolerance)
        self.assertAlmostEqual(summary['fitted']['mu_bkg']['value'], 1.0, delta=0.1)
        self.assertIn('pseudo-data', summary['data_label'])

    def test_yield_table_printed_with_labelled_pseudo_data(self):
        self.assertIn('## SR', self.proc.stdout)
        self.assertIn('| pseudo-data (not observed) |', self.proc.stdout)


if __name__ == '__main__':
    unittest.main()
