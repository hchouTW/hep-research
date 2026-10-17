#!/usr/bin/env python3
"""Species separation power for time-of-flight, ionization, and velocity-based PID.

Purpose: answer the question every particle-identification system must answer - up to
what momentum can these two species actually be told apart, and by how many sigma at a
given momentum. The dominant effect is that mass resolution degrades as gamma^2 times
the velocity resolution, so every velocity-based technique has a momentum ceiling.

What it does: for two species at a given momentum (or rigidity) it reports beta, gamma,
the mass resolution implied by the measurement, and the separation in sigma, then scans
momentum to find every interval where separation falls below a requested threshold.
Three modes:
  tof      - separation from the flight-time difference over a known path
  dedx     - separation from mean Bethe-Bloch ionization loss in a named material
  velocity - separation from a directly supplied relative velocity resolution
             (use this for a RICH; <plugin root>/skills/hep-detector/scripts/cherenkov_angle.py derives that input)

Usage notes / assumptions: standard library only. Momenta in GeV/c, rigidities in GV,
masses in GeV/c^2, flight path in metres, timing resolution in picoseconds. A species is
a name (He3 and He4 carry z=2), a mass, or mass:charge (e.g. 3.727:2). --rigidity R sets
p = |z| R for each species, which is what a magnetic spectrometer measures for nuclei.
Separation conventions (--convention, stated in the output as separation_convention and
reference_species): single (default) is |difference of means| / sigma of one measurement
of the reference species A (for tof, the common timing sigma); quadrature is
|difference| / sqrt(sigma_A^2 + sigma_B^2), symmetric in the species and a factor
sqrt(2) smaller when the widths are equal. State the convention when comparing.
dE/dx: the charge enters as z^2. The Bethe-Bloch evaluation is refused below
beta*gamma = 0.1 (shell corrections and charge exchange dominate; the formula can go
negative there) and for electrons and positrons (mass below 10 MeV/c^2), whose collision loss
differs (identical particles, Moller and Bhabha scattering): validity is then "outside" and
no n_sigma is given. Inputs outside plausible ranges (time resolution 1 ps - 10 ns, relative
dE/dx resolution 0.01-0.5, relative beta resolution above 0.1) add a warning. It also omits the
density-effect correction, which suppresses the relativistic rise, so numbers with either
species above beta*gamma = 4 are optimistic and flagged (n_sigma_optimistic). The dE/dx
bands of two species can cross, so separation is not monotonic in momentum: the scan
reports below_threshold_intervals, the ceiling is the end of the first separated range,
highest_separated is the top of the last separated range, and ceiling_is_lower_bound is
true when the scan limit is reached still separated (the true end lies beyond it).
See <plugin root>/skills/hep-detector/references/particle-identification.md.
Defaults (F-06): the output lists the values used ("inputs") and those taken by default ("defaults_used"); a
defaulted detector parameter of the chosen mode (tof: path 1 m, time resolution 60 ps; dedx: silicon, 6%;
velocity: 1e-3) is also a warning, because the default describes no particular detector.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed or the input file is unreadable or invalid (JSON with ok false);
2 invalid input (JSON with error_kind invalid-input on stdout, the usage on stderr).
Run: python3 <plugin root>/skills/hep-detector/scripts/pid_separation_power.py --mode tof --species pi K --momentum 2.0 --path 1.2 --time-resolution 60
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402

DEFAULTS = {'path': 1.0, 'time_resolution': 60.0, 'material': 'silicon', 'relative_resolution': 0.06,
            'beta_resolution': 1e-3, 'threshold': 3.0, 'convention': 'single'}
MODE_PARAMETERS = {'tof': ('path', 'time_resolution'), 'dedx': ('material', 'relative_resolution'),
                   'velocity': ('beta_resolution',)}  # detector parameters per mode: a default is warned (F-06)
STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


# Masses in GeV/c^2 from core/constants (Th9): CODATA 2022 for the electron, muon, proton and light nuclei (bare
# nuclei: deuteron, helion, alpha particle), PDG 2026 for the charged pion and kaon.
_CODATA = {'e': 'electron_mass_energy', 'mu': 'muon_mass_energy', 'p': 'proton_mass_energy',
           'd': 'deuteron_mass_energy', 'He3': 'helion_mass_energy', 'He4': 'alpha_particle_mass_energy'}
MASSES_GEV = {name: constants.constant(key, unit='GeV').value for name, key in _CODATA.items()}
MASSES_GEV.update({'pi': constants.particle('pi+', 'mass', unit='GeV').value,
                   'K': constants.particle('K+', 'mass', unit='GeV').value})
MASSES_GEV = {k: MASSES_GEV[k] for k in ('e', 'mu', 'pi', 'K', 'p', 'd', 'He3', 'He4')}

# Charge numbers |z| of the named species; anything else defaults to 1.
CHARGES = {'He3': 2, 'He4': 2}

# Bethe-Bloch is not evaluated below this beta*gamma (provisional limit; see docstring).
BETHE_MIN_BETA_GAMMA = 0.1
# Below this mass (between m_e and m_mu) the projectile is taken as an electron or positron, for which the
# heavy-particle Bethe formula does not apply (PDG RPP 2024, rev. March 2025, sec. 34.4.1).
ELECTRON_LIKE_MAX_GEV = 0.01
# Plausible input ranges; outside them the output warns that the unit is probably wrong.
TIME_RESOLUTION_RANGE_PS = (1.0, 1.0e4)
DEDX_RESOLUTION_RANGE = (0.01, 0.5)
BETA_RESOLUTION_MAX = 0.1
# Scan range and density (points per decade) for the separation scan.
SCAN_LOW = 0.05
SCAN_HIGH = 1000.0
SCAN_POINTS_PER_DECADE = 200

CONVENTIONS = ('single', 'quadrature')

C_M_PER_S = 299792458.0
ELECTRON_MASS_MEV = constants.constant('electron_mass_energy').value  # CODATA 2022, MeV
# Bethe-Bloch coefficient, MeV mol^-1 cm^2.
BETHE_K = 0.307075

# (Z/A, mean excitation energy I in eV) for a few common detector materials, from the PDG Atomic and Nuclear
# Properties tables (water: "water (liquid)", I = 79.7 eV, read 2026-10-14).
MATERIALS = {
    'silicon': (0.49848, 173.0),
    'argon': (0.45059, 188.0),
    'xenon': (0.41129, 482.0),
    'neon': (0.49555, 137.0),
    'water': (0.55508, 79.7),
}


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def resolve_mass(name):
    """Mass in GeV/c^2 from a species name or a numeric string."""
    if name in MASSES_GEV:
        return MASSES_GEV[name]
    try:
        return _positive(float(name), 'mass')
    except ValueError:
        raise ValueError(
            f'unknown species {name!r}; use one of {sorted(MASSES_GEV)} or a mass in GeV/c^2')


def resolve_species(name):
    """(mass in GeV/c^2, charge number) from a name, a mass, or 'mass:charge'."""
    if ':' in name:
        mass_text, charge_text = name.split(':', 1)
        try:
            charge = int(charge_text)
        except ValueError:
            raise ValueError(f'charge in {name!r} must be a positive integer') from None
        if charge < 1:
            raise ValueError(f'charge in {name!r} must be a positive integer')
        return resolve_mass(mass_text), charge
    return resolve_mass(name), CHARGES.get(name, 1)


def kinematics(momentum_gev, mass_gev):
    """beta, gamma and energy for a particle of given momentum and mass."""
    momentum_gev = _positive(momentum_gev, 'momentum')
    mass_gev = _positive(mass_gev, 'mass')
    energy = math.hypot(momentum_gev, mass_gev)
    beta = momentum_gev / energy
    gamma = energy / mass_gev
    return {'beta': beta, 'gamma': gamma, 'beta_gamma': beta * gamma, 'energy_gev': energy}


def mass_from_beta(momentum_gev, beta):
    """m = p * sqrt(1/beta^2 - 1). The inverse of the kinematics above."""
    momentum_gev = _positive(momentum_gev, 'momentum')
    if isinstance(beta, bool) or not isinstance(beta, (int, float)):
        raise ValueError('beta must be a number')
    if not math.isfinite(beta) or not 0 < beta < 1:
        raise ValueError('beta must be finite and strictly between zero and one')
    return momentum_gev * math.sqrt(1.0 / (beta * beta) - 1.0)


def mass_resolution(momentum_gev, mass_gev, relative_beta_resolution):
    """dm/m = gamma^2 * (dbeta/beta) at fixed momentum.

    This is the gamma^2 amplification that ends every velocity-based technique.
    """
    if relative_beta_resolution < 0:
        raise ValueError('relative_beta_resolution must be nonnegative')
    kin = kinematics(momentum_gev, mass_gev)
    relative = kin['gamma'] ** 2 * relative_beta_resolution
    return {'relative_mass_resolution': relative,
            'absolute_mass_resolution_gev': relative * mass_gev}


def time_of_flight_ns(momentum_gev, mass_gev, path_m):
    """Flight time in nanoseconds over a path of path_m metres."""
    path_m = _positive(path_m, 'path')
    beta = kinematics(momentum_gev, mass_gev)['beta']
    return path_m / (beta * C_M_PER_S) * 1e9


def tof_beta_resolution(momentum_gev, mass_gev, path_m, time_resolution_ps):
    """Relative velocity resolution implied by a timing resolution.

    beta = L/(c t)  =>  dbeta/beta = dt/t = beta c sigma_t / L.
    """
    time_resolution_ps = _positive(time_resolution_ps, 'time_resolution')
    path_m = _positive(path_m, 'path')
    beta = kinematics(momentum_gev, mass_gev)['beta']
    return beta * C_M_PER_S * (time_resolution_ps * 1e-12) / path_m


def bethe_bloch_mev_per_g_cm2(momentum_gev, mass_gev, material='silicon', charge=1):
    """Mean ionization loss in MeV cm^2/g, without the density-effect correction.

    -<dE/dx> = K z^2 (Z/A) (1/beta^2) [ 0.5 ln(2 m_e c^2 beta^2 gamma^2 T_max / I^2)
                                        - beta^2 ]
    Omitting the density effect makes the relativistic rise too steep; the returned
    dict flags when the evaluation is in that region. Below beta*gamma = 0.1 the formula
    is outside its validity (it can turn negative): the loss is then None and validity
    is 'outside'. A negative loss is never returned.
    """
    if material not in MATERIALS:
        raise ValueError(f'unknown material {material!r}; use one of {sorted(MATERIALS)}')
    if isinstance(charge, bool) or not isinstance(charge, int) or charge < 1:
        raise ValueError('charge must be a positive integer charge number')
    z_over_a, excitation_ev = MATERIALS[material]
    kin = kinematics(momentum_gev, mass_gev)
    beta, gamma = kin['beta'], kin['gamma']
    record = {
        'mev_per_g_cm2': None,
        'beta_gamma': kin['beta_gamma'],
        'density_effect_omitted': True,
        'in_relativistic_rise': kin['beta_gamma'] > 4.0,
        'validity': 'outside',
    }
    if kin['beta_gamma'] < BETHE_MIN_BETA_GAMMA:
        record['validity_reason'] = (
            f'beta*gamma = {kin["beta_gamma"]:.3g} is below {BETHE_MIN_BETA_GAMMA}, where '
            'shell corrections and charge exchange dominate')
        return record
    if mass_gev < ELECTRON_LIKE_MAX_GEV:
        record['validity_reason'] = (
            'electron or positron: the heavy-particle Bethe formula does not apply (identical particles for '
            'electrons, Moller and Bhabha cross sections, a different maximum energy transfer, and bremsstrahlung); '
            'use the electron stopping power of Seltzer and Berger, Int. J. Appl. Radiat. Isot. 33 (1982) 1189 '
            '(PDG, Passage of particles through matter, sec. 34.4.1)')
        return record
    mass_mev = mass_gev * 1000.0
    mass_ratio = ELECTRON_MASS_MEV / mass_mev
    t_max_mev = (2.0 * ELECTRON_MASS_MEV * beta * beta * gamma * gamma
                 / (1.0 + 2.0 * gamma * mass_ratio + mass_ratio * mass_ratio))
    excitation_mev = excitation_ev * 1e-6
    log_term = math.log(2.0 * ELECTRON_MASS_MEV * beta * beta * gamma * gamma
                        * t_max_mev / (excitation_mev * excitation_mev))
    loss = (BETHE_K * charge * charge * z_over_a / (beta * beta)
            * (0.5 * log_term - beta * beta))
    if not math.isfinite(loss) or loss <= 0.0:
        record['validity_reason'] = 'the Bethe-Bloch bracket is not positive here'
        return record
    record['mev_per_g_cm2'] = loss
    record['validity'] = 'inside'
    return record


def _momenta(value, charge_a, charge_b, input_variable):
    """Per-species momenta: the value itself, or |z| times a rigidity."""
    value = _positive(value, input_variable)
    if input_variable == 'momentum':
        return value, value
    if input_variable == 'rigidity':
        return charge_a * value, charge_b * value
    raise ValueError("input_variable must be 'momentum' or 'rigidity'")


def _convention_labels(mode, convention):
    if convention == 'quadrature':
        return 'delta_over_quadrature_sum_of_both_sigmas', None
    if mode == 'tof':
        # The timing resolution is common to both species, so the choice of A is moot.
        return 'delta_over_common_time_sigma', None
    return 'delta_over_sigma_of_species_a', 'a'


def separation(mode, mass_a, mass_b, momentum_gev, charge_a=1, charge_b=1,
               input_variable='momentum', convention='single', **options):
    """Separation in sigma between two species at one momentum (or rigidity).

    momentum_gev is a rigidity in GV when input_variable is 'rigidity'; each species then
    has p = |z| R. convention 'single' divides by one measurement's sigma (species A's,
    or the common timing sigma for tof); 'quadrature' by sqrt(sigma_A^2 + sigma_B^2).
    """
    if convention not in CONVENTIONS:
        raise ValueError(f'convention must be one of {CONVENTIONS}')
    momentum_a, momentum_b = _momenta(momentum_gev, charge_a, charge_b, input_variable)
    kin_a = kinematics(momentum_a, mass_a)
    kin_b = kinematics(momentum_b, mass_b)
    validity = None

    if mode == 'tof':
        path_m = options['path_m']
        time_resolution_ps = _positive(options['time_resolution_ps'], 'time_resolution')
        time_a = time_of_flight_ns(momentum_a, mass_a, path_m)
        time_b = time_of_flight_ns(momentum_b, mass_b, path_m)
        difference_ps = abs(time_a - time_b) * 1000.0
        sigma = (time_resolution_ps if convention == 'single'
                 else math.sqrt(2.0) * time_resolution_ps)
        n_sigma = difference_ps / sigma
        observable = {'time_a_ns': time_a, 'time_b_ns': time_b,
                      'time_difference_ps': difference_ps}
        beta_resolution = tof_beta_resolution(momentum_a, mass_a, path_m,
                                              time_resolution_ps)
    elif mode == 'dedx':
        material = options.get('material', 'silicon')
        relative = _positive(options['relative_resolution'], 'relative_resolution')
        loss_a = bethe_bloch_mev_per_g_cm2(momentum_a, mass_a, material, charge_a)
        loss_b = bethe_bloch_mev_per_g_cm2(momentum_b, mass_b, material, charge_b)
        rise = loss_a['in_relativistic_rise'] or loss_b['in_relativistic_rise']
        observable = {'dedx_a_mev_per_g_cm2': loss_a['mev_per_g_cm2'],
                      'dedx_b_mev_per_g_cm2': loss_b['mev_per_g_cm2'],
                      'material': material,
                      'density_effect_omitted': True,
                      'in_relativistic_rise': rise,
                      'in_relativistic_rise_a': loss_a['in_relativistic_rise'],
                      'in_relativistic_rise_b': loss_b['in_relativistic_rise'],
                      # Without the density effect the rise is too steep, so a separation
                      # with either species in the rise is overestimated.
                      'n_sigma_optimistic': rise}
        if loss_a['validity'] == 'inside' and loss_b['validity'] == 'inside':
            validity = 'inside'
            value_a, value_b = loss_a['mev_per_g_cm2'], loss_b['mev_per_g_cm2']
            sigma = (relative * value_a if convention == 'single'
                     else relative * math.hypot(value_a, value_b))
            n_sigma = abs(value_a - value_b) / sigma
        else:
            validity = 'outside'
            n_sigma = None
            observable['validity_reason'] = '; '.join(
                f'species {label}: {loss["validity_reason"]}'
                for label, loss in (('a', loss_a), ('b', loss_b))
                if loss['validity'] != 'inside')
        beta_resolution = None
    elif mode == 'velocity':
        beta_resolution = _positive(options['relative_beta_resolution'],
                                    'relative_beta_resolution')
        sigma_beta = beta_resolution * kin_a['beta']
        if convention == 'quadrature':
            sigma_beta = beta_resolution * math.hypot(kin_a['beta'], kin_b['beta'])
        n_sigma = abs(kin_a['beta'] - kin_b['beta']) / sigma_beta
        observable = {'beta_difference': abs(kin_a['beta'] - kin_b['beta']),
                      'sigma_beta': sigma_beta}
    else:
        raise ValueError("mode must be one of 'tof', 'dedx', 'velocity'")

    label, reference = _convention_labels(mode, convention)
    result = {
        'mode': mode,
        'input_variable': input_variable,
        f'{input_variable}_{"gev" if input_variable == "momentum" else "gv"}': momentum_gev,
        'species_a': {'mass_gev': mass_a, 'charge': charge_a, 'momentum_gev': momentum_a, **kin_a},
        'species_b': {'mass_gev': mass_b, 'charge': charge_b, 'momentum_gev': momentum_b, **kin_b},
        'observable': observable,
        'n_sigma': n_sigma,
        'separation_convention': label,
        'reference_species': reference,
    }
    if validity is not None:
        result['validity'] = validity
    if beta_resolution is not None:
        result['relative_beta_resolution'] = beta_resolution
        result['species_a']['mass_resolution'] = mass_resolution(
            momentum_a, mass_a, beta_resolution)
    return result


def _separated(mode, mass_a, mass_b, value, threshold_sigma, options):
    """True/False against the threshold, or None where the model is not evaluable."""
    n_sigma = separation(mode, mass_a, mass_b, value, **options)['n_sigma']
    return None if n_sigma is None else n_sigma >= threshold_sigma


def _refine(mode, mass_a, mass_b, threshold_sigma, options, low, high):
    """Geometric bisection for the boundary between grid points low and high."""
    state_low = _separated(mode, mass_a, mass_b, low, threshold_sigma, options)
    for _ in range(200):
        mid = math.sqrt(low * high)
        if mid in (low, high):
            break
        if _separated(mode, mass_a, mass_b, mid, threshold_sigma, options) == state_low:
            low = mid
        else:
            high = mid
    return low


def separation_scan(mode, mass_a, mass_b, threshold_sigma=3.0,
                    low_gev=SCAN_LOW, high_gev=SCAN_HIGH, **options):
    """Scan separation over a log grid and report where it is below threshold.

    Separation is not assumed monotonic (dE/dx bands cross). Returns the intervals
    below threshold, the intervals where the model is not evaluable, the ceiling (end of
    the separated range that starts at the first evaluable point; None if that point is
    already below threshold), the upper end of the highest separated range, and
    ceiling_is_lower_bound: true when the scan ends still separated, so the upper end of
    separation lies beyond the scan (and so does the ceiling when nothing is below).
    Boundaries are refined by bisection; features narrower than the grid step
    (1/SCAN_POINTS_PER_DECADE of a decade) can be missed.
    """
    threshold_sigma = _positive(threshold_sigma, 'threshold_sigma')
    low_gev = _positive(low_gev, 'scan low edge')
    high_gev = _positive(high_gev, 'scan high edge')
    steps = max(2, int(math.ceil(math.log10(high_gev / low_gev) * SCAN_POINTS_PER_DECADE)))
    grid = [low_gev * (high_gev / low_gev) ** (i / steps) for i in range(steps + 1)]
    grid[-1] = high_gev
    states = [_separated(mode, mass_a, mass_b, v, threshold_sigma, options) for v in grid]

    def runs(target):
        intervals, start = [], None
        for i, state in enumerate(states):
            if state is target and start is None:
                start = grid[0] if i == 0 else _refine(
                    mode, mass_a, mass_b, threshold_sigma, options, grid[i - 1], grid[i])
            elif state is not target and start is not None:
                intervals.append([start, _refine(
                    mode, mass_a, mass_b, threshold_sigma, options, grid[i - 1], grid[i])])
                start = None
        if start is not None:
            intervals.append([start, grid[-1]])
        return intervals

    below = runs(False)
    not_evaluable = runs(None)
    evaluable = [i for i, state in enumerate(states) if state is not None]
    ceiling = None
    if evaluable and states[evaluable[0]]:
        first = evaluable[0]
        end = next((i for i in range(first, len(states)) if not states[i]), None)
        ceiling = grid[-1] if end is None else _refine(
            mode, mass_a, mass_b, threshold_sigma, options, grid[end - 1], grid[end])
    separated = runs(True)
    return {'below_threshold_intervals': below, 'not_evaluable_intervals': not_evaluable,
            'ceiling': ceiling, 'highest_separated': separated[-1][1] if separated else None,
            'ceiling_is_lower_bound': bool(states[-1]),
            'scan_range': [low_gev, high_gev]}


def separation_ceiling(mode, mass_a, mass_b, threshold_sigma=3.0,
                       low_gev=SCAN_LOW, high_gev=SCAN_HIGH, **options):
    """Highest momentum of the separated range that starts at low_gev (see separation_scan).

    Returns high_gev when the whole scan stays separated - then only a lower bound.
    """
    return separation_scan(mode, mass_a, mass_b, threshold_sigma, low_gev, high_gev,
                           **options)['ceiling']


def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'pid_separation_power.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = JsonArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=('tof', 'dedx', 'velocity'), required=True)
    parser.add_argument('--species', nargs=2, required=True, metavar=('A', 'B'),
                        help=f'two of {sorted(MASSES_GEV)}, masses in GeV/c^2, or mass:charge')
    given = parser.add_mutually_exclusive_group()
    given.add_argument('--momentum', type=float, default=None, help='GeV/c (default 2)')
    given.add_argument('--rigidity', type=float, default=None,
                       help='GV; each species then has p = |z| * R')
    parser.add_argument('--path', type=float, default=None, help='tof: flight path in m (default 1, warned)')
    parser.add_argument('--time-resolution', type=float, default=None,
                        dest='time_resolution', help='tof: timing resolution in ps (default 60, warned)')
    parser.add_argument('--material', default=None,
                        choices=sorted(MATERIALS), help='dedx: absorber material (default silicon, warned)')
    parser.add_argument('--relative-resolution', type=float, default=None,
                        dest='relative_resolution', help='dedx: relative dE/dx resolution (default 0.06, warned)')
    parser.add_argument('--beta-resolution', type=float, default=None,
                        dest='beta_resolution', help='velocity: relative dbeta/beta (default 1e-3, warned)')
    parser.add_argument('--threshold', type=float, default=None,
                        help='separation in sigma that counts as separated (default 3)')
    parser.add_argument('--convention', choices=CONVENTIONS, default=None,
                        help='single: delta/sigma of species A (default); quadrature: '
                             'delta/sqrt(sigma_A^2 + sigma_B^2)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    # F-06: a parameter left out takes its default, which is reported in defaults_used; a defaulted detector parameter
    # of the chosen mode is also a warning (the default describes no particular detector)
    defaults_used = {}
    for name, default in DEFAULTS.items():
        if getattr(args, name) is None:
            setattr(args, name, default)
            if name in MODE_PARAMETERS[args.mode] or name in ('threshold', 'convention'):
                defaults_used[name] = default
    input_variable = 'rigidity' if args.rigidity is not None else 'momentum'
    if args.rigidity is None and args.momentum is None:
        defaults_used['momentum'] = 2.0
    value = args.rigidity if args.rigidity is not None else (
        args.momentum if args.momentum is not None else 2.0)
    try:
        mass_a, charge_a = resolve_species(args.species[0])
        mass_b, charge_b = resolve_species(args.species[1])
        if (mass_a, charge_a) == (mass_b, charge_b):
            raise ValueError('the two species must differ in mass or charge')
        _positive(args.threshold, 'threshold')
        options = {'path_m': args.path, 'time_resolution_ps': args.time_resolution,
                   'material': args.material, 'relative_resolution': args.relative_resolution,
                   'relative_beta_resolution': args.beta_resolution,
                   'charge_a': charge_a, 'charge_b': charge_b,
                   'input_variable': input_variable, 'convention': args.convention}
        result = separation(args.mode, mass_a, mass_b, value, **options)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))

    warnings = [f'{name} not given: the default {defaults_used[name]!r} describes no particular detector; give the '
                'value of yours' for name in MODE_PARAMETERS[args.mode] if name in defaults_used]
    if args.mode == 'tof' and not TIME_RESOLUTION_RANGE_PS[0] <= args.time_resolution <= TIME_RESOLUTION_RANGE_PS[1]:
        warnings.append(f'time resolution {args.time_resolution:g} ps is outside 1 ps - 10 ns; check the unit (ps)')
    if args.mode == 'dedx' and not DEDX_RESOLUTION_RANGE[0] <= args.relative_resolution <= DEDX_RESOLUTION_RANGE[1]:
        warnings.append(f'relative dE/dx resolution {args.relative_resolution:g} is outside 0.01-0.5; it is a '
                        'fraction, not a percentage')
    if args.mode == 'velocity' and args.beta_resolution > BETA_RESOLUTION_MAX:
        warnings.append(f'relative beta resolution {args.beta_resolution:g} is above {BETA_RESOLUTION_MAX:g}; '
                        'it is a fraction, not a percentage')
    try:
        result['warnings'] = warnings
        result['species_a']['name'] = args.species[0]
        result['species_b']['name'] = args.species[1]
        if result['reference_species'] == 'a':
            result['reference_species'] = args.species[0]
        result['threshold_sigma'] = args.threshold
        scan = separation_scan(args.mode, mass_a, mass_b, args.threshold, **options)
        unit = 'gev' if input_variable == 'momentum' else 'gv'
        result['scan_variable'] = input_variable
        result['scan_range'] = scan['scan_range']
        result[f'separation_ceiling_{unit}'] = scan['ceiling']
        result[f'highest_separated_{unit}'] = scan['highest_separated']
        result['ceiling_is_lower_bound'] = scan['ceiling_is_lower_bound']
        result['below_threshold_intervals'] = scan['below_threshold_intervals']
        result['not_evaluable_intervals'] = scan['not_evaluable_intervals']
        inputs = {'mode': args.mode, 'species': list(args.species), input_variable: value,
                  **{name: getattr(args, name) for name in MODE_PARAMETERS[args.mode]},
                  'threshold': args.threshold, 'convention': args.convention}
        text = json.dumps({
            'status': args.status,
            'inputs': inputs,
            'defaults_used': defaults_used,
            **result,
            'note': ('n_sigma follows separation_convention (single: one measurement of the '
                     'reference species; quadrature: both widths). The ceiling is the end of '
                     'the first separated range; separation can recover above it (see '
                     'below_threshold_intervals). dE/dx omits the density effect, so values '
                     'in the relativistic rise are optimistic.'),
        }, indent=2, allow_nan=False)
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        message = str(exc)
        if 'JSON compliant' in message:
            message = 'result contains a non-finite number; the inputs are out of range'
        return _fail(message)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
