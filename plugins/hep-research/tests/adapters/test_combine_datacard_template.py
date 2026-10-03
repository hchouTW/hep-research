"""Checks for ${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/combine_datacard_template.txt.

The structural tests always run: they fill the template with the counting model of
${CLAUDE_PLUGIN_ROOT}/adapters/pyhf-combine/assets/pyhf-counting.json (s=5, b=20, n=20, 10% background normalization) and check
that the card is well formed.

The Combine run is skipped unless `combine` and `text2workspace.py` are on PATH or
$HEP_COMBINE_WRAPPER names a command that runs its arguments inside a Combine
environment (e.g. a script ending in `exec env -i PATH=<env>/bin ... "$@"`). Its
result must match pyhf on the same model: 95% CLs observed and median expected
upper limit on mu of 2.153 (pyhf 0.7.6, asymptotic).
"""
import os
import re
import shlex
import shutil
import string
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]  # plugin root (tests/adapters/<this file>)
TEMPLATE = ROOT_DIR / 'adapters/pyhf-combine/assets/combine_datacard_template.txt'
WRAPPER = shlex.split(os.environ.get('HEP_COMBINE_WRAPPER', ''))
PYHF_LIMIT = 2.153

VALUES = dict(num_channels=1, num_backgrounds=1, shapes_file='shapes.root', channel='sr',
              observation=-1, channel_bins='sr sr', process_names='signal background',
              process_ids='0 1', rates='-1 -1', year='2018', lumi_effects='1.0 1.0',
              rate_nuisances='bkg_norm lnN - 0.9/1.1', shape_nuisances='')

MAKE_SHAPES = '''
import ROOT
f = ROOT.TFile("shapes.root", "RECREATE")
f.mkdir("sr").cd()
for name, val in [("signal", 5.0), ("background", 20.0), ("data_obs", 20.0)]:
    h = ROOT.TH1D(name, name, 1, 0.0, 1.0)
    h.SetBinContent(1, val)
    h.Write()
f.Close()
'''


def fill(values=VALUES):
    return TEMPLATE.read_text().format(**values)


def _has_combine():
    if WRAPPER:
        return True
    return bool(shutil.which('combine') and shutil.which('text2workspace.py'))


class TemplateStructureTests(unittest.TestCase):
    def test_placeholders_are_the_documented_set(self):
        fields = {f for _, f, _, _ in string.Formatter().parse(TEMPLATE.read_text()) if f}
        self.assertEqual(fields, set(VALUES))

    def test_filled_card_columns_are_consistent(self):
        rows = {}
        for line in fill().splitlines():
            parts = line.split()
            if parts and parts[0] in ('bin', 'process', 'rate'):
                rows.setdefault(parts[0], []).append(parts[1:])
            elif len(parts) > 2 and parts[1] in ('lnN', 'shape'):
                rows.setdefault('nuisance', []).append(parts[2:])
        ncol = len(rows['bin'][1])
        self.assertEqual(ncol, 2)
        for key in ('process', 'rate', 'nuisance'):
            for row in rows[key]:
                self.assertEqual(len(row), ncol, f'{key} row {row}')
        self.assertIn('$CHANNEL/$PROCESS_$SYSTEMATIC', fill())


@unittest.skipUnless(_has_combine(), 'Combine not available (set HEP_COMBINE_WRAPPER)')
class CombineRunTests(unittest.TestCase):
    def run_cmd(self, *args, cwd):
        proc = subprocess.run([*WRAPPER, *args], capture_output=True, text=True, cwd=cwd, timeout=600)
        self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-2000:])
        return proc.stdout

    def test_limit_matches_pyhf(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'make_shapes.py').write_text(MAKE_SHAPES)
            Path(tmp, 'card.txt').write_text(fill())
            self.run_cmd('python3', 'make_shapes.py', cwd=tmp)
            self.run_cmd('text2workspace.py', 'card.txt', '-o', 'ws.root', cwd=tmp)
            # --strictBounds: without it the observed-limit search sets r above its range, which ROOT 6.40 rejects
            out = self.run_cmd('combine', '-M', 'AsymptoticLimits', 'ws.root', '--rMax', '10', '--strictBounds', cwd=tmp)
        observed = float(re.search(r'Observed Limit: r < ([\d.]+)', out).group(1))
        median = float(re.search(r'Expected 50\.0%: r < ([\d.]+)', out).group(1))
        self.assertAlmostEqual(observed, PYHF_LIMIT, delta=0.02 * PYHF_LIMIT)
        self.assertAlmostEqual(median, PYHF_LIMIT, delta=0.02 * PYHF_LIMIT)


if __name__ == '__main__':
    unittest.main()
