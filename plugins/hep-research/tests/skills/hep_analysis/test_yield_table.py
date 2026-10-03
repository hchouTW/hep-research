"""CLI tests for ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/make_yield_table.py, including its error paths.

Run from the skill directory: python3 -m unittest discover -s tests -v
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # plugin root (tests/skills/<skill>/<this file>)
SCRIPT = ROOT / 'skills/hep-analysis/scripts/make_yield_table.py'


def run(csv_text=None, path=None, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        if path is None:
            path = Path(tmp) / 'yields.csv'
            path.write_text(csv_text, encoding='utf-8')
        return subprocess.run([sys.executable, str(SCRIPT), '--input', str(path), *extra],
                              capture_output=True, text=True)


class YieldTableTests(unittest.TestCase):
    def test_groups_by_region_and_sorts_samples(self):
        proc = run('region,sample,yield,uncertainty\nSR,ttbar,10.5,1.2\nCR,wjets,100,10\nSR,data,12,\n')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertLess(out.index('## CR'), out.index('## SR'))
        self.assertLess(out.index('| data |'), out.index('| ttbar |'))
        self.assertIn('| ttbar | 10.500 +/- 1.200 |', out)
        self.assertIn('| data | 12.000 |', out)  # blank uncertainty -> value only

    def test_negative_yield_is_reported_not_clipped(self):
        # Signed NLO weights can give a negative weighted yield; it must pass through unchanged.
        proc = run('region,sample,yield\nSR,ttV,-0.4\n', None, '--precision', '1')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('| ttV | -0.4 |', proc.stdout)

    def test_missing_required_column_fails(self):
        proc = run('region,sample\nSR,ttbar\n')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("missing required columns: ['yield']", proc.stderr)

    def test_missing_file_fails(self):
        proc = run(path=Path('/nonexistent/yields.csv'))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('does not exist', proc.stderr)

    def test_empty_file_fails(self):
        proc = run('')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('missing a header row', proc.stderr)

    def test_non_numeric_yield_fails(self):
        proc = run('region,sample,yield\nSR,ttbar,abc\n')
        self.assertNotEqual(proc.returncode, 0)

    def test_errors_are_reported_without_traceback(self):
        for proc in (run(path=Path('/nonexistent/yields.csv')), run(''), run('region,sample\nSR,ttbar\n'),
                     run('region,sample,yield\nSR,ttbar,abc\n')):
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn('Traceback', proc.stderr)
            self.assertTrue(proc.stderr.startswith('error: '), proc.stderr)


if __name__ == '__main__':
    unittest.main()
