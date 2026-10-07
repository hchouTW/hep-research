"""Tests for skills/hep-computing/scripts/audit_histograms.py (moved from the detector-response tests, T11): the
shipped synthetic bundle passes unchanged, and each histogram defect is reported."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
from audit_histograms import audit  # noqa: E402


class HistogramTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads((ROOT / 'skills/hep-computing/assets/histograms.example.json').read_text())
        self.hist = self.bundle['histograms']['synthetic_background']

    def test_good_input_not_mutated(self):
        previous = copy.deepcopy(self.bundle)
        self.assertEqual(audit(self.bundle), ([], []))
        self.assertEqual(previous, self.bundle)

    def test_signed_mc_not_poisson(self):
        self.hist['sumw'][0] = -2
        self.assertFalse(audit(self.bundle)[0])
        self.assertTrue(audit(self.bundle)[1])
        self.bundle['kind'] = 'poisson_expectation'
        self.assertTrue(audit(self.bundle)[0])

    def test_missing_and_mismatched_variation(self):
        del self.hist['variations']['scaleDown']
        self.hist['variations']['scaleUp']['edges'][1] = 40
        self.assertEqual(len(audit(self.bundle)[0]), 2)

    def test_nonfinite_variance_and_dimensions(self):
        for field, value in [('sumw', [float('nan'), 8]), ('sumw2', [-1, 10]), ('sumw2', [1]), ('edges', [0, 0, 100])]:
            with self.subTest(field=field, value=value):
                bundle = copy.deepcopy(self.bundle)
                bundle['histograms']['synthetic_background'][field] = value
                self.assertTrue(audit(bundle)[0])

    def test_malformed_types(self):
        for bundle in (None, [], {}, {'schema_version':1,'kind':'mc','histograms':{'bad':None}}):
            self.assertTrue(audit(bundle)[0])

    def test_bool_not_numeric(self):
        self.hist['sumw'][0] = True
        self.assertTrue(audit(self.bundle)[0])

    def test_identical_variation_warns(self):
        self.hist['variations']['scaleUp'] = {k: self.hist[k][:] for k in ('edges','sumw','sumw2')}
        self.assertFalse(audit(self.bundle)[0])
        self.assertTrue(audit(self.bundle)[1])

    def test_cli_success(self):
        result = subprocess.run([sys.executable, str(ROOT/'skills/hep-computing/scripts/audit_histograms.py'), str(ROOT/'skills/hep-computing/assets/histograms.example.json')], capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
