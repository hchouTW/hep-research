"""End-to-end runs of the PyROOT scripts and assets on synthetic ROOT fixtures.

Skipped unless a Python that can `import ROOT` is available. The interpreter is
$HEP_ROOT_PYTHON if set (e.g. /opt/homebrew/bin/python3.14 for Homebrew ROOT, whose
PyROOT does not load under a conda python), else the one running the tests.
Fixtures come from <plugin root>/tests/skills/hep_computing/make_root_fixtures.py.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
PYTHON = os.environ.get('HEP_ROOT_PYTHON', sys.executable)


def _has_pyroot():
    try:
        return subprocess.run([PYTHON, '-c', 'import ROOT'], capture_output=True, timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@unittest.skipUnless(_has_pyroot(), 'PyROOT not importable (set HEP_ROOT_PYTHON)')
class RootIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.fx = Path(cls._tmp.name)
        subprocess.run([PYTHON, str(ROOT_DIR / 'tests/skills/hep_computing/make_root_fixtures.py'), str(cls.fx)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_script(self, relative, *args):
        proc = subprocess.run([PYTHON, str(ROOT_DIR / relative), *map(str, args)],
                              capture_output=True, text=True, cwd=self.fx)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        return proc.stdout

    def test_inspect_reports_leaf_types(self):
        out = self.run_script('skills/hep-computing/scripts/inspect_root_file.py', '--input', self.fx / 'events.root', '--tree', 'Events')
        self.assertIn('entries: 5000', out)
        self.assertIn('Muon_pt [Float_t]', out)

    def test_check_systematic_variations(self):
        out = self.run_script('skills/hep-analysis/scripts/check_systematic_variations.py', '--input', self.fx / 'histograms.root',
                              '--nominal', 'nominal', '--up', 'jes_Up', '--down', 'jes_Down')
        self.assertIn('up max relative bin difference', out)

    def test_compare_histograms_sees_two_percent_shift(self):
        out = self.run_script('skills/hep-computing/scripts/compare_root_histograms.py', '--reference', self.fx / 'histograms.root',
                              '--candidate', self.fx / 'histograms_candidate.root', '--hist', 'nominal')
        line = next(l for l in out.splitlines() if l.startswith('max relative bin difference'))
        self.assertAlmostEqual(float(line.split(':')[1]), 0.02, places=9)

    def test_summarize_histogram_statistics(self):
        out = self.run_script('skills/hep-computing/scripts/summarize_histogram_statistics.py', '--input', self.fx / 'histograms.root',
                              '--hist', 'nominal', '--include-flow')
        self.assertIn('integral: 20000.0', out)

    def test_roofit_workspace_summary(self):
        out = self.run_script('skills/hep-computing/scripts/roofit_workspace_summary.py', '--input', self.fx / 'workspace.root',
                              '--workspace', 'workspace')
        self.assertIn('model [RooAddPdf]', out)
        self.assertIn('data [RooDataSet] entries=1000', out)

    def test_pyroot_rdataframe_asset_cutflow(self):
        out = self.run_script('adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py', '--input', self.fx / 'events.root',
                              '--output', self.fx / 'rdf.root')
        self.assertIn('leading muon eta', out)
        self.assertTrue((self.fx / 'rdf.root').exists())

    def test_pyroot_roofit_asset_recovers_peak(self):
        out = self.run_script('adapters/root-uproot/assets/pyroot_roofit_signal_background.py', '--input', self.fx / 'histograms.root',
                              '--hist', 'mass_hist', '--output', self.fx / 'fit.root', '--min', 60, '--max', 120)
        self.assertIn('fit status: 0', out)
        check = subprocess.run([PYTHON, '-c', (
            'import ROOT,sys; r=ROOT.TFile.Open(sys.argv[1]).Get("fit_result");'
            'print(r.floatParsFinal().find("mean").getVal())'), str(self.fx / 'fit.root')],
            capture_output=True, text=True, check=True)
        self.assertAlmostEqual(float(check.stdout.split()[-1]), 91.0, delta=0.5)


if __name__ == '__main__':
    unittest.main()
