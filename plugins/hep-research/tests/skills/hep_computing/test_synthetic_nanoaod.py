"""Tests for <plugin root>/skills/hep-computing/scripts/make_synthetic_nanoaod.py (the synthetic NanoAOD-like test sample).

The expectations the script prints are computed in pure Python; these tests check them
against an independent awkward recomputation, check the file is a TTree (not an RNTuple),
that the Runs totals equal the signed sums over the full sample, and that a seed is
reproducible. Skipped without numpy, awkward and uproot. Run from the skill directory:
python3 -m unittest discover -s tests -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
SCRIPT = ROOT / 'skills' / 'hep-computing' / 'scripts' / 'make_synthetic_nanoaod.py'
sys.path.insert(0, str(ROOT / 'skills' / 'hep-computing' / 'scripts'))

try:
    import awkward as ak
    import numpy as np
    import uproot
    HAVE = True
except ImportError:
    HAVE = False


def run(out, *extra):
    proc = subprocess.run([sys.executable, str(SCRIPT), '--out', str(out), *extra],
                          capture_output=True, text=True, check=True, timeout=600)
    return json.loads(proc.stdout)


@unittest.skipUnless(HAVE, 'numpy, awkward and uproot are required')
class SyntheticNanoAODTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'sample.root'

    def tearDown(self):
        self.tmp.cleanup()

    def test_file_is_ttree_with_events_and_runs(self):
        run(self.path)
        classes = uproot.open(self.path).classnames()
        self.assertEqual(classes, {'Events;1': 'TTree', 'Runs;1': 'TTree'})

    def test_expectations_match_independent_awkward_recomputation(self):
        summary = run(self.path)
        a = uproot.open(self.path)['Events'].arrays()
        keep = (a.Jet_pt > 30) & (abs(a.Jet_eta) < 2.5)
        ok = ak.num(a.Jet_pt[keep]) >= 2
        self.assertEqual(summary['n_selected_events'], int(ak.sum(ok)))
        self.assertAlmostEqual(summary['sumw_selected'], float(ak.sum(a.genWeight[ok])), places=6)
        self.assertEqual(summary['sumw2_selected'], float(ak.sum(a.genWeight[ok] ** 2)))

    def test_leading_pair_mass_matches_vectorised_calculation(self):
        summary = run(self.path)
        a = uproot.open(self.path)['Events'].arrays()
        keep = (a.Jet_pt > 30) & (abs(a.Jet_eta) < 2.5)
        ok = ak.num(a.Jet_pt[keep]) >= 2
        pt, eta, phi, m = (x[keep][ok] for x in (a.Jet_pt, a.Jet_eta, a.Jet_phi, a.Jet_mass))
        def comp(i):
            p, e, f, mm = (ak.to_numpy(x[:, i]).astype(float) for x in (pt, eta, phi, m))
            return (p * np.cos(f), p * np.sin(f), p * np.sinh(e),
                    np.sqrt((p * np.cosh(e)) ** 2 + mm ** 2))
        j1, j2 = comp(0), comp(1)
        mass = np.sqrt((j1[3] + j2[3]) ** 2 - sum((j1[k] + j2[k]) ** 2 for k in range(3)))
        w = ak.to_numpy(a.genWeight[ok]).astype(float)
        self.assertAlmostEqual(summary['mjj_weighted_mean_GeV'], float(np.average(mass, weights=w)), places=3)
        self.assertAlmostEqual(summary['mjj_max_GeV'], float(mass.max()), places=3)

    def test_runs_tree_holds_full_sample_signed_totals(self):
        summary = run(self.path, '--events', '250', '--seed', '7')
        f = uproot.open(self.path)
        w = ak.to_numpy(f['Events']['genWeight'].array()).astype(float)
        r = f['Runs'].arrays()
        self.assertEqual(int(r['genEventCount'][0]), 250)
        self.assertAlmostEqual(float(r['genEventSumw'][0]), w.sum(), places=9)
        self.assertAlmostEqual(float(r['genEventSumw2'][0]), (w ** 2).sum(), places=9)
        self.assertEqual(summary['genEventSumw_full_sample'], float(w.sum()))
        self.assertLess(w.sum(), len(w))  # negative weights are present

    def test_same_seed_same_file_and_numbers(self):
        other = Path(self.tmp.name) / 'other.root'
        first, second = run(self.path, '--seed', '3'), run(other, '--seed', '3')
        for key in ('n_selected_events', 'sumw_selected', 'mjj_weighted_mean_GeV'):
            self.assertEqual(first[key], second[key])
        self.assertNotEqual(first['n_selected_events'], run(Path(self.tmp.name) / 'x.root', '--seed', '4')['n_selected_events'])

    def test_summary_is_labelled_synthetic(self):
        summary = run(self.path)
        self.assertTrue(summary['synthetic'])
        self.assertIn('SYNTHETIC', summary['note'])

    def test_bad_arguments_are_rejected(self):
        proc = subprocess.run([sys.executable, str(SCRIPT), '--out', str(self.path), '--events', '0'],
                              capture_output=True, text=True, timeout=600)
        self.assertNotEqual(proc.returncode, 0)


BLOCK = ("import runpy, sys\n"
         "for name in sys.argv[2].split(','):\n"
         "    sys.modules[name] = None\n"
         "sys.argv = [sys.argv[1]] + sys.argv[3:]\n"
         "runpy.run_path(sys.argv[0], run_name='__main__')\n")


class MissingPackagesTests(unittest.TestCase):
    """Runs the script with numpy/uproot made unimportable; needs no third-party package itself."""

    def run_blocked(self, blocked, *args):
        return subprocess.run([sys.executable, '-c', BLOCK, str(SCRIPT), blocked, *args], capture_output=True, text=True, timeout=600)

    def test_help_works_without_numpy(self):
        proc = self.run_blocked('numpy', '--help')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('usage:', proc.stdout)

    def test_missing_packages_give_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            for blocked in ('numpy', 'uproot', 'numpy,uproot'):
                out = Path(tmp) / 'sample.root'
                proc = self.run_blocked(blocked, '--out', str(out))
                self.assertNotEqual(proc.returncode, 0)
                self.assertNotIn('Traceback', proc.stderr)
                self.assertIn('missing required package(s)', proc.stderr)
                for name in blocked.split(','):
                    self.assertIn(name, proc.stderr)
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
