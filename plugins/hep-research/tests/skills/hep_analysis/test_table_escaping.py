"""ANA-P2-10: table escaping, NaN refusal, status and totals. Synthetic tables."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills' / 'hep-analysis' / 'scripts'
ASSET = ROOT / 'skills' / 'hep-analysis' / 'assets' / 'systematics.csv'


def run(script, *args):
    return subprocess.run([sys.executable, '-I', str(SCRIPTS / script), *args], capture_output=True, text=True, timeout=60)


def yields(text, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / 'y.csv'
        f.write_text(text, encoding='utf-8')
        return run('make_yield_table.py', '--input', str(f), '--status', 'synthetic', *extra)


class TableTests(unittest.TestCase):
    def test_pipe_in_sample_is_escaped(self):
        out = yields('region,sample,yield\nSR,a|b,1.5\n').stdout
        self.assertIn('| a\\|b | 1.500 |', out)
        self.assertTrue(out.startswith('Status: synthetic'))

    def test_nan_yield_is_refused(self):
        self.assertEqual(yields('region,sample,yield\nSR,ttbar,nan\n').returncode, 2)

    def test_totals_state_their_rule(self):
        out = yields('region,sample,yield,uncertainty\nSR,a,3,0.3\nSR,b,4,0.4\n', '--totals').stdout
        self.assertIn('| **Total** | 7.000 +/- 0.500 |', out)
        self.assertIn('quadrature (assumes independent samples)', out)

    def test_label_injection_and_newlines_are_neutralized(self):
        p = run('systematics_table_tex.py', '--input', str(ASSET), '--status', 'synthetic',
                '--label', 'tab:x}\\input{/etc/passwd', '--caption', 'line one\nline two')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn('\\input', p.stdout)
        self.assertIn('\\label{tab:x--input--etc-passwd}', p.stdout)
        self.assertIn('line one line two', p.stdout)
        self.assertIn('status: synthetic', p.stdout)


if __name__ == '__main__':
    unittest.main()
