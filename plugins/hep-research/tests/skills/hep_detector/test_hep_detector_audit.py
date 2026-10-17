"""Regression tests for the second-pass (V4) audit of the hep-detector scripts.

Added from the hep-detector audit appendix (2026-10-13); every class passes since the
fixes of DR-WP1 and DR-WP2. AuditFollowUpTests covers the second-pass findings (N-*) that the
appendix only sketched.

Each test pins one confirmed defect (IDs as in V4_E.md) and states the intended
behaviour after the fix. Expected numbers were computed independently (closed forms,
numpy lstsq, scipy brentq / beta.ppf, PDG tables) and are hard-coded here.
Standard library only; synthetic inputs only.

Place in tests/skills/hep_detector/ to run with the suite; from the work dir set
HEP_PLUGIN to the plugin root.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(os.environ.get('HEP_PLUGIN') or Path(__file__).resolve().parents[3])
SCRIPTS = PLUGIN / 'skills' / 'hep-detector' / 'scripts'
ASSETS = PLUGIN / 'skills' / 'hep-detector' / 'assets'
sys.path.insert(0, str(SCRIPTS))
import pid_separation_power  # noqa: E402
import xmax_gaisser_hillas  # noqa: E402

TIMEOUT_S = 10


def _reject_constant(name):
    raise ValueError(f'non-standard JSON constant {name}')


def strict_json(text):
    return json.loads(text, parse_constant=_reject_constant)


def run(testcase, script, *args):
    try:
        return subprocess.run([sys.executable, '-I', '-B', str(SCRIPTS / script), *map(str, args)],
                              capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        testcase.fail(f'{script} {args} did not finish within {TIMEOUT_S} s')


def run_json(testcase, script, *args, returncode=0):
    proc = run(testcase, script, *args)
    testcase.assertNotIn('Traceback', proc.stderr)
    testcase.assertEqual(proc.returncode, returncode, proc.stderr[-400:] or proc.stdout[-400:])
    return strict_json(proc.stdout)


class _TempFiles:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, payload):
        path = self.tmp / name
        path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding='utf-8')
        return path


# --------------------------------------------------------------------- E-X1, E-X2, N-X1
class GaisserHillasBracketingTests(unittest.TestCase):
    def test_huge_x_max_terminates(self):
        """E-X1: x_max = 1e20 hung forever (upper += step is a no-op). After the fix the
        script must finish: either a JSON error (exit 1) or a correct width. For
        x_max >> lambda the profile is Gaussian with sigma^2 = lambda (x_max - x0), so
        FWHM = 2 sqrt(2 ln2 * 60 * (1e20 + 60)) = 1.8240358e11 g/cm^2."""
        proc = run(self, 'xmax_gaisser_hillas.py', '--n-max', '1', '--x-max', '1e20',
                   '--x0', '-60', '--lambda-param', '60')
        self.assertNotIn('Traceback', proc.stderr)
        payload = strict_json(proc.stdout)
        if proc.returncode == 0:
            self.assertAlmostEqual(payload['half_maximum_depths']['full_width_half_maximum'],
                                   1.8240358e11, delta=1e-4 * 1.8240358e11)
        else:
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(payload['ok'])

    def test_falling_edge_for_large_lambda(self):
        """Guard for the new bracketing: lambda=3e5 g/cm^2, x_max=750, x0=-60 has its
        falling half maximum at 213208.505291 (scipy brentq). Passes today; must keep
        passing with the multiplicative step."""
        payload = run_json(self, 'xmax_gaisser_hillas.py', '--n-max', '1', '--x-max', '750',
                           '--x0', '-60', '--lambda-param', '3e5')
        self.assertAlmostEqual(payload['half_maximum_depths']['falling_edge'], 213208.505291,
                               delta=1e-3)

    def test_wide_profile_is_not_refused_by_the_fixed_cap(self):
        """N-X2: the guard upper > x_max + 1e6 refuses a valid profile whose falling half
        maximum lies more than 1e6 g/cm^2 past x_max. x_max=5e6, x0=-60, lambda=2e5:
        falling edge 6271594.238044 (scipy brentq on the log1p form)."""
        payload = run_json(self, 'xmax_gaisser_hillas.py', '--n-max', '1', '--x-max', '5e6',
                           '--x0', '-60', '--lambda-param', '2e5')
        self.assertAlmostEqual(payload['half_maximum_depths']['falling_edge'], 6271594.238044,
                               delta=1e-3)

    def test_tiny_lambda_names_the_cause(self):
        """E-X2: lambda = 1e-300 gave 'math range error'."""
        proc = run(self, 'xmax_gaisser_hillas.py', '--n-max', '1', '--x-max', '750',
                   '--x0', '-60', '--lambda-param', '1e-300')
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('lambda', strict_json(proc.stdout)['error'])

    def test_profile_is_accurate_far_from_the_origin(self):
        """N-X1: exponent*log(base) + (x_max-X)/lambda cancels catastrophically when
        x_max >> lambda. With u = (X-x_max)/(x_max-x0), N/N_max = exp(e (log1p(u) - u)).
        For x_max=1e15, X=x_max+3e8, lambda=60: 0.47236662355903 (current: 0.47200, -8e-4)."""
        value = xmax_gaisser_hillas.gaisser_hillas(1e15 + 3e8, 1.0, 1e15, -60.0, 60.0)
        self.assertAlmostEqual(value, 0.47236662355903103, delta=1e-9)


# --------------------------------------------------------------------- E-C1
class CherenkovChargeTests(unittest.TestCase):
    # n=1.05, p=40 GeV/c, L=2 cm, N0=100/cm, 5 mrad: He4 beta=0.995687, theta=0.296014 rad,
    # z=1 yield 17.0188937; with z^2: 68.0755750, sigma_theta = 5/sqrt(68.0756) = 0.6060024 mrad.
    HE4_PHOTONS = 68.07557492992738  # with the CODATA 2022 alpha-particle mass (Th9); 68.07557496982115 with 3.72737940 GeV
    HE4_SIGMA_MRAD = 0.6060024015969153

    def test_helium_yield_scales_with_z_squared(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'p', 'He4',
                           '--momentum', '40')
        he4 = payload['species_b']
        self.assertEqual(he4['charge'], 2)
        self.assertAlmostEqual(he4['expected_photons'], self.HE4_PHOTONS, delta=1e-9)
        self.assertAlmostEqual(he4['track_angular_resolution_mrad'], self.HE4_SIGMA_MRAD, delta=1e-9)
        # The threshold and the angle depend on beta only, not on z.
        # 11.642377294538912 with the CODATA 2022 alpha-particle mass (Th9); 11.642377257681904 with 3.72737940 GeV
        self.assertAlmostEqual(he4['threshold_momentum_gev'], 11.642377294538912, delta=1e-9)
        # 0.2960136490467237 with the CODATA 2022 alpha-particle mass (Th9); 0.2960136491360844 with 3.72737940 GeV
        self.assertAlmostEqual(he4['cherenkov_angle_rad'], 0.2960136490467237, delta=1e-12)

    def test_mass_colon_charge_syntax_is_accepted(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'p',
                           '3.7273794118:2', '--momentum', '40')  # the CODATA 2022 mass, stated
        self.assertAlmostEqual(payload['species_b']['expected_photons'], self.HE4_PHOTONS, delta=1e-9)

    def test_rigidity_input_gives_p_equals_z_r(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'p', 'He4',
                           '--rigidity', '20')
        self.assertAlmostEqual(payload['species_b']['momentum_gev'], 40.0, delta=1e-12)
        self.assertAlmostEqual(payload['species_b']['expected_photons'], self.HE4_PHOTONS, delta=1e-9)


# --------------------------------------------------------------------- E-K1..E-K4
class CalorimeterFitDefaultTests(_TempFiles, unittest.TestCase):
    ENERGIES = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]

    def _points(self):
        # Truth a=0.10, b=0.20, c=0.007 with alternating +-2 % relative scatter on sigma/E.
        points = []
        for i, e in enumerate(self.ENERGIES):
            r = math.sqrt(0.01 / e + 0.04 / e ** 2 + 0.007 ** 2) * (1.02 if i % 2 == 0 else 0.98)
            points.append([float(e), r])
        return points

    def test_unweighted_default_uses_constant_relative_error(self):
        """E-K1: without per-point errors the fit must weight y=r^2 by 1/r^4 (dr proportional to r).
        numpy lstsq with that weight: a=0.0998441202, b=0.2009894690, c=0.0069524903.
        Today's unit-weight fit gives c=0.01218 (+74 %)."""
        path = self.write('noisy.json', {'points': self._points()})
        payload = run_json(self, 'calorimeter_resolution.py', '--fit', path)
        self.assertIn('relative', payload['method'])
        self.assertAlmostEqual(payload['constant'], 0.006952490267382184, delta=1e-9)
        self.assertAlmostEqual(payload['stochastic'], 0.09984412015741675, delta=1e-9)
        self.assertAlmostEqual(payload['noise'], 0.2009894690454992, delta=1e-9)

    def test_percent_input_is_refused(self):
        """E-K2: sigma_E/E given in percent (22.4 for 22.4 %) was fitted silently."""
        path = self.write('pct.json', {'points': [[1, 22.4], [10, 3.8], [100, 1.24], [1000, 0.77]]})
        proc = run(self, 'calorimeter_resolution.py', '--fit', path)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('fraction', strict_json(proc.stdout)['error'])

    def test_negative_squared_term_is_a_failure_with_one_warnings_list(self):
        """E-K3: exit 0, a stray 'warning' key, and a half-filled result."""
        path = self.write('negc.json', {'points': [[1, 0.1], [10, 0.0316228], [100, 0.009]]})
        proc = run(self, 'calorimeter_resolution.py', '--fit', path)
        self.assertEqual(proc.returncode, 1)
        payload = strict_json(proc.stdout)
        self.assertFalse(payload['ok'])
        self.assertNotIn('warning', payload)
        self.assertTrue(any('negative' in w for w in payload['warnings']))
        self.assertIsNone(payload['stochastic'])

    def test_evaluate_without_coefficients_has_no_dominant_term(self):
        """E-K4: --evaluate alone gave resolution 0 and dominant_term 'stochastic'."""
        proc = run(self, 'calorimeter_resolution.py', '--evaluate')
        if proc.returncode == 0:
            self.assertIsNone(strict_json(proc.stdout)['dominant_term'])
        else:
            self.assertEqual(proc.returncode, 2)


# --------------------------------------------------------------------- E-P1..E-P3
class PidElectronAndUnitTests(unittest.TestCase):
    def test_electron_dedx_is_outside_the_heavy_particle_formula(self):
        """E-P1: e vs pi at 0.2 GeV/c gave n_sigma 3.39 with validity 'inside'."""
        for species in ('e', '0.00051099895'):
            with self.subTest(species=species):
                payload = run_json(self, 'pid_separation_power.py', '--mode', 'dedx', '--species',
                                   species, 'pi', '--momentum', '0.2')
                self.assertEqual(payload['validity'], 'outside')
                self.assertIsNone(payload['n_sigma'])
                self.assertIn('electron', payload['observable']['validity_reason'])

    def test_sub_picosecond_timing_is_flagged(self):
        """E-P2: --time-resolution 0.06 (ns typed as ps) gave 1840 sigma silently."""
        payload = run_json(self, 'pid_separation_power.py', '--mode', 'tof', '--species', 'pi', 'K',
                           '--momentum', '2', '--path', '1.2', '--time-resolution', '0.06')
        self.assertTrue(any('ps' in w for w in payload.get('warnings', [])))

    def test_water_uses_the_pdg_mean_excitation_energy(self):
        """E-P3: PDG AtomicNuclearProperties lists I = 79.7 eV for liquid water. A muon at
        0.3 GeV/c then loses 2.03897040 MeV cm^2/g (closed form); with 75 eV, 2.05062."""
        loss = pid_separation_power.bethe_bloch_mev_per_g_cm2(
            0.3, pid_separation_power.MASSES_GEV['mu'], 'water')['mev_per_g_cm2']
        self.assertAlmostEqual(loss, 2.03897039968383, delta=1e-9)


# --------------------------------------------------------------------- E-M1..E-M3
class MultipleScatteringBetaTests(_TempFiles, unittest.TestCase):
    STACK = ASSETS / 'detector-stack.example.json'

    def test_beta_is_derived_from_rigidity_charge_and_mass(self):
        """E-M1: a proton at R = 1 GV has beta = 1/hypot(1, 0.93827209) = 0.7292562022;
        Highland with x/X0 = 0.0357: theta0 = 3.161971177e-3 rad."""
        payload = run_json(self, 'multiple_scattering.py', self.STACK, '--rigidity', '1',
                           '--mass', '0.93827209')
        self.assertAlmostEqual(payload['beta'], 0.7292562021748294, delta=1e-12)
        self.assertAlmostEqual(payload['scattering_angle_rad'], 0.003161971176904367, delta=1e-14)

    def test_helium_beta_uses_z_times_rigidity(self):
        z, rigidity, mass = 2, 2.0, 3.7273794
        expected = z * rigidity / math.hypot(z * rigidity, mass)
        payload = run_json(self, 'multiple_scattering.py', self.STACK, '--rigidity', str(rigidity),
                           '--charge', str(z), '--mass', str(mass))
        self.assertAlmostEqual(payload['beta'], expected, delta=1e-12)

    def test_conflicting_beta_and_mass_are_refused(self):
        proc = run(self, 'multiple_scattering.py', self.STACK, '--rigidity', '100', '--beta', '0.5',
                   '--mass', '0.93827209')
        self.assertEqual(proc.returncode, 2)
        # Exit 2 alone is not enough: today an unknown --mass also exits 2. The refusal must
        # be the conflict check, reported as JSON (see UniformErrorTests).
        self.assertNotIn('unrecognized arguments', proc.stderr)
        self.assertIn('beta', strict_json(proc.stdout)['error'])

    def test_crossover_solves_with_beta_of_rigidity(self):
        """B=0.5 T, L=0.5 m, 300 um, 4 layers, x/X0=0.3, proton: ms(R) = 0.0993891/beta(R),
        k = 0.0759472/GV; ms(R) = k R at R = 1.534037342 GV (brentq). Fixed beta=1 gives 1.3087."""
        stack = self.write('slow.json', {
            'field_tesla': 0.5, 'lever_arm_m': 0.5, 'point_resolution_um': 300.0,
            'layers': [{'x_over_x0': 0.075, 'measuring': True}] * 4})
        payload = run_json(self, 'multiple_scattering.py', stack, '--rigidity', '1',
                           '--mass', '0.93827209')
        self.assertAlmostEqual(payload['crossover_rigidity_gv'], 1.5340373422150493, delta=1e-6)

    def test_measuring_flag_must_be_boolean(self):
        """E-M2: "measuring": "no" counted as a measuring layer."""
        stack = self.write('str.json', {
            'field_tesla': 1, 'lever_arm_m': 1, 'point_resolution_um': 10,
            'layers': [{'x_over_x0': 0.01, 'measuring': 'no'}] * 3 + [{'x_over_x0': 0.01}]})
        proc = run(self, 'multiple_scattering.py', stack)
        self.assertEqual(proc.returncode, 1)  # file-content error: JSON + exit 1, as pileup's NaN-center test
        self.assertIn('measuring', strict_json(proc.stdout)['error'])

    def test_missing_measuring_flags_warn(self):
        stack = self.write('noflag.json', {
            'field_tesla': 1, 'lever_arm_m': 1, 'point_resolution_um': 10,
            'layers': [{'x_over_x0': 0.01}] * 3})
        payload = run_json(self, 'multiple_scattering.py', stack)
        self.assertTrue(any('measuring' in w for w in payload['warnings']))

    def test_mdr_definition_is_named(self):
        """E-M3: MDR = sqrt(1 - ms^2)/k = 3096.065 GV here; 1/k = 3096.243 GV."""
        payload = run_json(self, 'multiple_scattering.py', self.STACK)
        self.assertIn('mdr_definition', payload)


# --------------------------------------------------------------------- E-6 status labels
STATUS_CASES = {
    'calorimeter_resolution.py': ['--fit', ASSETS / 'calorimeter-response.example.json'],
    'cherenkov_angle.py': ['--index', '1.05', '--species', 'pi', 'K'],
    'frontend_response.py': ['enc', '--capacitance', '10', '--peaking', '25'],
    'multiple_scattering.py': [ASSETS / 'detector-stack.example.json'],
    'pid_separation_power.py': ['--mode', 'tof', '--species', 'pi', 'K'],
    'pileup_reweight.py': [ASSETS / 'pileup-profiles.example.json'],
    'tag_and_probe_efficiency.py': ['--pass-count', '92', '--total', '100'],
    'xmax_gaisser_hillas.py': ['--n-max', '2e7', '--x-max', '750', '--x0', '-60',
                               '--lambda-param', '60'],
}


# Scripts written after F-04 follow the plugin-wide contract of core/status.py instead: "status" is the run status
# and the artifact label is echoed as "status_label" (toy_spectrometer.py: its output is always synthetic; propagate_scale_distortion.py, build_response.py and mix_period_responses.py take --status).
OUTDIR = Path(tempfile.gettempdir())
F04_CASES = {
    'species_response.py': ['from-rates', '--rates', ASSETS / 'sign-rates.example.json', '--out', OUTDIR / 'species.json'],
    'charge_confusion_rate.py': ['gaussian-core', '--edges', '10', '100', '--sigma-inv-r', '0.002'],
    'survival_feeddown.py': ['compute', '--layers', ASSETS / 'survival-layers.example.json', '--species',
                             ASSETS / 'survival-species.example.json', '--xs', ASSETS / 'survival-xs.example.json'],
    'tracker_resolution.py': ['momentum', '--positions-m', '0', '0.5', '1', '--point-resolution-um', '10',
                              '--field-tesla', '1', '--x-over-x0', '0.05', '--charge', '1', '--beta', '1', '--pt', '10'],
    'mix_period_responses.py': ['stack', '--period', f"e1={ASSETS / 'response-synthetic.example.json'}", '--out',
                                OUTDIR / 'stack.json'],
    'build_response.py': ['build', ASSETS / 'response-events.example.csv', '--truth-col', 'truth', '--reco-col',
                          'reco', '--weight-col', 'weight', '--selected-col', 'selected', '--truth-edges', '0', '10',
                          '20', '30', '--reco-edges', '0', '10', '20', '30', '--variable', 'x', '--unit', 'GeV',
                          '--normalization', 'conditional_on_generated', '--acceptance', 'outside_matrix',
                          '--residual', 'difference', '--intended-use', 'forward_folding', '--artifact-id', 'a',
                          '--objective', 'SYNTHETIC', '--created', '2026-10-17', '--out', OUTDIR / 'resp.json'],
    'stability_monitor.py': [ASSETS / 'stability-series.example.csv', '--time-column', 'time_s', '--value-column',
                             'value', '--error-column', 'error', '--false-alarm', '0.05', '--toys', '500',
                             '--seed', '1'],
    'multisample_pid.py': ['charge', ASSETS / 'multisample-events.example.csv', '--layers', 'l1,l2,l3,l4',
                           '--response', ASSETS / 'multisample-response.example.json', '--method',
                           'truncated-mean', '--truncate-high', '0.25', '--no-path-correction'],
    'toy_spectrometer.py': ['resolution', ASSETS / 'toy-spectrometer.fictional.json', '--species', 'p',
                            '--rigidity', '10'],
    'propagate_scale_distortion.py': ['events', ASSETS / 'scale-distortion-events.example.csv', '--column', 'x',
                                      '--signed', '--edges', '1', '2', '4', '--mode', 'scale', '--scale', '0.01'],
}


class StatusLabelTests(_TempFiles, unittest.TestCase):
    """E-6: replicate cosmic_ray_flux.py: --status (choices = core artifact_statuses,
    default unvalidated) echoed as the top-level key 'status'."""

    # The three file-input scripts read the status of their input; the shipped assets say "synthetic".
    FILE_STATUS = {'calorimeter_resolution.py', 'multiple_scattering.py', 'pileup_reweight.py'}

    def test_every_script_echoes_status(self):
        self.assertEqual(set(STATUS_CASES) | set(F04_CASES), {p.name for p in SCRIPTS.glob('*.py')})
        self.assertFalse(set(STATUS_CASES) & set(F04_CASES))
        for script, args in STATUS_CASES.items():
            with self.subTest(script=script):
                default = run_json(self, script, *args)
                self.assertEqual(default.get('status'), 'synthetic' if script in self.FILE_STATUS else 'unvalidated')
                labelled = run_json(self, script, *args, '--status', 'synthetic')
                self.assertEqual(labelled.get('status'), 'synthetic')

    def test_f04_scripts_report_a_run_status_and_a_label(self):
        sys.path.insert(0, str(PLUGIN))
        from core.status import ARTIFACT_LABELS, RUN_STATUSES
        for script, args in F04_CASES.items():
            with self.subTest(script=script):
                payload = run_json(self, script, *args)
                self.assertIn(payload.get('status'), RUN_STATUSES)
                self.assertIn(payload.get('status_label'), ARTIFACT_LABELS)

    def test_status_in_an_input_file_propagates(self):
        stack = json.loads((ASSETS / 'detector-stack.example.json').read_text(encoding='utf-8'))
        stack['status'] = 'synthetic'
        payload = run_json(self, 'multiple_scattering.py', self.write('s.json', stack))
        self.assertEqual(payload['status'], 'synthetic')


    def test_statuses_tuple_matches_the_core_vocabulary(self):
        import ast
        vocab = json.loads((PLUGIN / 'contracts' / 'vocab' / 'core.json').read_text(encoding='utf-8'))
        expected = set(vocab['vocabularies']['artifact_statuses'])
        for path in sorted(p for p in SCRIPTS.glob('*.py') if p.name not in F04_CASES):
            with self.subTest(script=path.name):
                tree = ast.parse(path.read_text(encoding='utf-8'))
                values = [ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                          and any(getattr(t, 'id', None) == 'STATUSES' for t in node.targets)]
                self.assertEqual(len(values), 1)
                self.assertEqual(set(values[0]), expected)
                self.assertEqual(len(values[0]), len(expected))


# --------------------------------------------------------------------- E-17 uniform JSON errors
INVALID_CASES = [
    ('calorimeter_resolution.py', ['--evaluate', '--energy', '-1']),
    ('calorimeter_resolution.py', []),                                  # argparse: mode missing
    ('cherenkov_angle.py', ['--index', '0.9', '--species', 'pi', 'K']),
    ('frontend_response.py', ['enc', '--capacitance', '-1', '--peaking', '25']),
    ('frontend_response.py', ['no-such-command']),                      # argparse: bad choice
    ('multiple_scattering.py', [ASSETS / 'detector-stack.example.json', '--beta', '2']),
    ('pid_separation_power.py', ['--mode', 'tof', '--species', 'pi', 'pi']),
    ('pileup_reweight.py', []),                                         # argparse: bundle missing
    ('tag_and_probe_efficiency.py', ['--pass-count', '5', '--total', '3']),
    ('tag_and_probe_efficiency.py', ['--pass-count', 'x', '--total', '3']),  # argparse: type
    ('xmax_gaisser_hillas.py', ['--n-max', '1', '--x-max', '1', '--x0', '2', '--lambda-param', '1']),
]


class UniformErrorTests(unittest.TestCase):
    def test_invalid_input_is_exit_2_with_a_json_error(self):
        for script, args in INVALID_CASES:
            with self.subTest(script=script, args=[str(a) for a in args]):
                proc = run(self, script, *args)
                self.assertEqual(proc.returncode, 2)
                self.assertNotIn('Traceback', proc.stderr)
                self.assertIn('error:', proc.stderr)
                payload = strict_json(proc.stdout)
                self.assertIs(payload['ok'], False)
                self.assertEqual(payload['status'], 'failed')  # core artifact_statuses
                self.assertEqual(payload['error_kind'], 'invalid-input')
                self.assertTrue(payload['error'])


# --------------------------------------------------------------------- E-T2, E-F1, E-U1
class SmallCliTests(_TempFiles, unittest.TestCase):
    def test_tag_and_probe_names_the_interval_type(self):
        """E-T2: 0/50 at 0.95 gives the central upper end 0.0711217 (beta.ppf(0.975, 1, 50));
        the one-sided 95 % limit would be 1 - 0.05**(1/50) = 0.0581551."""
        payload = run_json(self, 'tag_and_probe_efficiency.py', '--pass-count', '0', '--total', '50')
        self.assertEqual(payload['interval_type'], 'central')
        self.assertAlmostEqual(payload['upper_bound'], 0.07112173646419764, delta=1e-9)

    def test_channels_must_be_an_integer(self):
        """E-F1: --channels 2.5 was accepted."""
        proc = run(self, 'frontend_response.py', 'noise-rate', '--threshold', '4', '--peaking', '25',
                   '--channels', '2.5', '--window', '100')
        self.assertEqual(proc.returncode, 2)

    def test_leakage_scale_has_a_subcommand(self):
        """E-F1: (263.15/293.15)^2 exp(-1.21/(2k) (1/263.15 - 1/293.15)) = 0.0525378697."""
        payload = run_json(self, 'frontend_response.py', 'leakage-scale', '--current', '1',
                           '--from-celsius', '20', '--to-celsius', '-10')
        self.assertAlmostEqual(payload['leakage_na'], 0.05253786967313066, delta=1e-12)

    def test_unsorted_bin_centers_are_refused(self):
        """E-U1."""
        path = self.write('pu.json', {'data_profile': [1, 2, 3], 'mc_profile': [1, 2, 3],
                                      'bin_centers': [2, 0, 1]})
        proc = run(self, 'pileup_reweight.py', path)
        self.assertEqual(proc.returncode, 1)  # file-content error, as test_nan_bin_center_is_not_ok
        payload = strict_json(proc.stdout)
        self.assertFalse(payload['ok'])
        self.assertIn('bin_centers', payload['error'])

    def test_raw_profile_totals_are_reported(self):
        """E-U1: the example data profile sums to 0.99964060 (mass lost above the last bin)."""
        payload = run_json(self, 'pileup_reweight.py', ASSETS / 'pileup-profiles.example.json')
        self.assertAlmostEqual(payload['input_totals']['data'], 0.9996405979750262, delta=1e-12)



# --------------------------------------------------------------------- N-C1, N-F2, E-U1 edges, E-M1 species
class AuditFollowUpTests(_TempFiles, unittest.TestCase):
    def test_radiator_length_is_checked_below_threshold(self):
        """N-C1: with both species below threshold the radiator length was never validated."""
        proc = run(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K', '--momentum', '0.3',
                   '--radiator-length', '-1')
        self.assertEqual(proc.returncode, 2)
        self.assertIn('radiator_length', strict_json(proc.stdout)['error'])

    def test_large_velocity_resolution_warns(self):
        payload = run_json(self, 'cherenkov_angle.py', '--index', '1.05', '--species', 'pi', 'K', '--momentum', '10',
                           '--single-photon-resolution', '5000')
        self.assertTrue(any('beta resolution' in w for w in payload['warnings']), payload['warnings'])

    def test_enc_without_noise_has_no_dominant_term(self):
        """N-F2."""
        payload = run_json(self, 'frontend_response.py', 'enc', '--capacitance', '0', '--peaking', '25')
        self.assertIsNone(payload['dominant_term'])

    def test_bin_center_outside_its_edges_is_refused(self):
        path = self.write('pu.json', {'data_profile': [1, 2, 3], 'mc_profile': [1, 2, 3],
                                      'bin_centers': [0.5, 1.5, 3.5], 'bin_edges': [0, 1, 2, 3]})
        proc = run(self, 'pileup_reweight.py', path)
        self.assertEqual(proc.returncode, 1)
        self.assertIn('outside its bin', strict_json(proc.stdout)['error'])

    def test_species_sets_mass_and_charge_and_refuses_a_conflicting_charge(self):
        stack = ASSETS / 'detector-stack.example.json'
        by_species = run_json(self, 'multiple_scattering.py', stack, '--rigidity', '2', '--species', 'He4')
        by_mass = run_json(self, 'multiple_scattering.py', stack, '--rigidity', '2', '--charge', '2',
                           '--mass', str(pid_separation_power.MASSES_GEV['He4']))
        self.assertAlmostEqual(by_species['beta'], by_mass['beta'], delta=1e-15)
        self.assertEqual(by_species['charge_number'], 2)
        proc = run(self, 'multiple_scattering.py', stack, '--species', 'He4', '--charge', '1')
        self.assertEqual(proc.returncode, 2)

    def test_mdr_with_derived_beta_is_close_to_the_relativistic_value(self):
        """At a few TV a proton has beta = 1 to 1e-7, so the MDR solved with beta(R) equals the closed form."""
        stack = ASSETS / 'detector-stack.example.json'
        fixed = run_json(self, 'multiple_scattering.py', stack)
        derived = run_json(self, 'multiple_scattering.py', stack, '--species', 'p')
        self.assertEqual(derived['beta_source'], 'derived from rigidity, charge and mass')
        self.assertAlmostEqual(derived['maximum_detectable_rigidity_gv'], fixed['maximum_detectable_rigidity_gv'],
                               delta=1e-6 * fixed['maximum_detectable_rigidity_gv'])


if __name__ == '__main__':
    unittest.main()
