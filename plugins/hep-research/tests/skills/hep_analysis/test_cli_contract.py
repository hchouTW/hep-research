"""ANA-P2-0: one CLI contract for every hep-analysis script.

--help exits 0; a NaN input exits 2; a malformed file (for scripts that read one) exits 2 without a traceback; a valid
run carries the `status` label. Exit codes follow the repository convention: 0 ok, 1 finding or failed computation,
2 usage or invalid input, 3 incomplete. Synthetic values only.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'skills' / 'hep-analysis' / 'scripts'
CORE_STATUSES = sorted(json.loads((ROOT / 'contracts' / 'vocab' / 'core.json').read_text(encoding='utf-8'))
                       ['vocabularies']['artifact_statuses'])

HIST = {'edges': [0, 1, 2, 3, 4], 'values': [1, 2, 3, 4]}
NAN_HIST = '{"edges": [0, 1, 2], "values": [1, NaN]}'
SYS_JSON = {'nominal': [10, 20, 30], 'up': [11, 20, 30], 'down': [9, 20, 30]}
SPECTRUM = {'points': [[10, 1.0], [20, 0.18], [40, 0.03], [80, 0.006]]}
CHANGES = {'changes': [{'id': 'c1', 'parameter': 'p', 'old': 1, 'new': 2, 'motivation': 'new calibration',
                        'evidence': {'control_sample': 'Z->ee', 'evidence_ids': [], 'independent_of_signal_region': True},
                        'looked_at': ['control-region data']}]}
YIELDS = 'region,sample,yield,uncertainty\nSR,ttbar,10.5,1.2\n'
SYST_CSV = ('name,source,effect,applied_via,affected_processes,correlation_key,payload,validation\n'
            'jes,calibration,shape,rerun,all,jes,p,v\n')

# script: (valid args, NaN args, malformed-file args or None, how the status is reported)
# '{f}' is replaced by a file written from the given text.
CASES = {
    'check_systematic_variations.py': ((['--json', '{f}'], json.dumps(SYS_JSON)),
                                       (['--json', '{f}'], '{"nominal": [1, NaN], "up": [1, 2], "down": [1, 2]}'),
                                       (['--json', '{f}'], '{"nominal": [1, 2'), 'json'),
    'cosmic_ray_flux.py': ((['--counts', '4', '--exposure', '2e7', '--bin-width', '700', '--bin-width-unit', 'GV'], None),
                           (['--counts', '4', '--exposure', 'nan', '--bin-width', '700', '--bin-width-unit', 'GV'], None),
                           None, 'json'),
    'counting_reference.py': ((['--observed', '3', '--background', '1'], None),
                              (['--observed', '3', '--background', 'nan'], None), None, 'json'),
    'cr_spectrum_powerlaw_fit.py': ((['--input', '{f}'], json.dumps(SPECTRUM)),
                                    (['--input', '{f}'], '{"points": [[10, NaN], [20, 1], [30, 0.5]]}'),
                                    (['--input', '{f}'], '{"points": [[10, 1]'), 'json'),
    'geomagnetic_cutoff.py': ((['--latitude', '40'], None), (['--latitude', 'nan'], None), None, 'json'),
    'make_yield_table.py': ((['--input', '{f}', '--status', 'synthetic'], YIELDS),
                            (['--input', '{f}', '--status', 'synthetic'], 'region,sample,yield\nSR,ttbar,nan\n'),
                            (['--input', '{f}', '--status', 'synthetic'], 'region,sample\nSR,ttbar\n'), 'text'),
    'mask_blinded_bins.py': ((['--hist', '{f}', '--low', '1', '--high', '2'], json.dumps(HIST)),
                             (['--hist', '{f}', '--low', '1', '--high', '2'], NAN_HIST),
                             (['--hist', '{f}', '--low', '1', '--high', '2'], '{"edges": [0, 1'), 'json'),
    'orbit_averaged_geomagnetic_cutoff.py': ((['--inclination', '51.6', '--n-samples', '50'], None),
                                             (['--inclination', 'nan'], None), None, 'json'),
    'particle_ratio_with_uncertainty.py': ((['--n1', '3', '--sigma1', '1.7', '--n2', '5', '--sigma2', '2.2'], None),
                                           (['--n1', 'nan', '--sigma1', '1', '--n2', '5', '--sigma2', '2'], None),
                                           None, 'json'),
    'review_analysis_change.py': ((['{f}'], json.dumps(CHANGES)),
                                  (['{f}'], '{"changes": [{"id": "c", "old": NaN}]}'),
                                  (['{f}'], '{"changes": ['), 'json'),
    'solar_modulation_force_field.py': ((['--modulate', '--energy', '1', '--mass', '0.938272', '--charge', '1',
                                          '--phi', '0.5', '--lis-normalization', '1e4', '--lis-index', '2.7'], None),
                                        (['--modulate', '--energy', '1', '--mass', '0.938272', '--charge', '1',
                                          '--phi', '0.5', '--lis-normalization', '1e4', '--lis-index=nan'], None),
                                        None, 'json'),
    'systematics_table_tex.py': ((['--input', '{f}', '--status', 'synthetic'], SYST_CSV),
                                 (['--input', '{f}', '--status', 'synthetic'], SYST_CSV.replace(',p,v', ',nan,v')),
                                 (['--input', '{f}', '--status', 'synthetic', '--columns', 'nonexistent'], SYST_CSV),
                                 'text'),
}


def run(script, spec):
    args, text = spec
    with tempfile.TemporaryDirectory() as tmp:
        if text is not None:
            f = Path(tmp) / 'input.txt'
            f.write_text(text, encoding='utf-8')
            args = [str(f) if a == '{f}' else a for a in args]
        return subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / script), *args], capture_output=True,
                              text=True, timeout=120, cwd=tmp)


class CliContractTests(unittest.TestCase):
    def test_every_script_is_covered(self):
        self.assertEqual(sorted(p.name for p in SCRIPTS.glob('*.py')), sorted(CASES))

    def test_help_documents_status_and_exit_codes(self):
        for script in CASES:
            with self.subTest(script=script):
                p = run(script, (['--help'], None))
                self.assertEqual(p.returncode, 0, p.stderr)
                text = ' '.join(p.stdout.split()).lower()
                self.assertIn('exit code', text)
                self.assertIn('status', text)

    def test_valid_run_carries_status(self):
        for script, (valid, _, _, kind) in CASES.items():
            with self.subTest(script=script):
                p = run(script, valid)
                self.assertIn(p.returncode, (0, 1), p.stderr)
                if kind == 'json':
                    self.assertIn(json.loads(p.stdout)['status'], CORE_STATUSES)
                else:
                    self.assertTrue('synthetic' in p.stdout.lower(), p.stdout)

    def test_nan_input_exits_2(self):
        for script, (_, nan, _, _) in CASES.items():
            with self.subTest(script=script):
                p = run(script, nan)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertNotIn('Traceback', p.stderr)

    def test_malformed_file_exits_2_without_traceback(self):
        for script, (_, _, bad, _) in CASES.items():
            if bad is None:
                continue
            with self.subTest(script=script):
                p = run(script, bad)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertNotIn('Traceback', p.stderr)
                self.assertTrue(p.stderr.strip())
                self.assertIn('error', p.stderr.strip().splitlines()[-1].lower())  # the reason is one line

    def test_status_lists_match_the_core_vocabulary(self):
        sys.path.insert(0, str(SCRIPTS))
        import importlib
        for name in ('cosmic_ray_flux', 'counting_reference', 'cr_spectrum_powerlaw_fit', 'geomagnetic_cutoff',
                     'mask_blinded_bins', 'particle_ratio_with_uncertainty', 'review_analysis_change',
                     'solar_modulation_force_field', 'check_systematic_variations', 'make_yield_table'):
            with self.subTest(script=name):
                self.assertEqual(sorted(importlib.import_module(name).STATUSES), CORE_STATUSES)
        import systematics_table_tex
        self.assertEqual(sorted(set(systematics_table_tex.STATUSES) - {'published'}), CORE_STATUSES)

    def test_flux_tool_contract_failure_states_match(self):
        contract = json.loads((ROOT / 'contracts' / 'tool_contracts' / 'cosmic_ray_flux.json').read_text(encoding='utf-8'))
        declared = {f['exit_code'] for f in contract['operations'][0]['failure_states']}
        self.assertEqual(declared, {1, 2, 3})


if __name__ == '__main__':
    unittest.main()
