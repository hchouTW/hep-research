#!/usr/bin/env python3
"""Force-field approximation for solar modulation of the cosmic-ray spectrum.

Purpose: convert between the local interstellar spectrum (LIS, outside the
heliosphere) and the flux measured at 1 AU, given a single effective modulation
potential phi - the standard first-order correction described in
<plugin root>/skills/hep-detector/references/space-based-direct-detection.md and the bound experiment profile's modules,
needed because space-based magnetic spectrometers measure at 1 AU during a specific, time-
varying solar-activity epoch, not the LIS directly.

What it does: implements
    E_LIS = E_TOA + |Z| * phi
    J_TOA(E_TOA) = ((2*m*E_TOA + E_TOA^2) / (2*m*E_LIS + E_LIS^2)) * J_LIS(E_LIS)
for a particle of total rest mass m (GeV), absolute charge |Z|, and *total* kinetic
energy E (GeV), phi in GV (Gleeson & Axford, Astrophys. J. 154 (1968) 1011, Eqs. (13)-(16)). Conversions between
energy kinds and their Jacobians use core/kinematics/relativistic.py. --energy-kind selects the input variable: Ek_total (GeV),
Ek_per_nucleon (GeV/n, with --mass-number; the shift is then (|Z|/A) phi per nucleon) or rigidity (GV); the
phase-space factor ("jacobian") is the same in every kind, and the flux per unit of the chosen variable is
multiplied by dE/dx at each point ("flux_factor": 1 for Ek_total and Ek_per_nucleon, beta_TOA/beta_LIS for
rigidity). --mass is the rest mass of the whole nucleus. --phi-unit GV|MV. --phi-uncertainty is propagated to the
derived flux by a central difference. --lis-table takes a tabulated LIS instead of a power law. Two modes:
  --modulate: given a LIS power law J_LIS(E) = A * E^-gamma, predict the flux an
    instrument at 1 AU would measure at a given TOA energy.
  --demodulate: given a *measured* TOA flux value at a given TOA energy (no LIS model
    needed), invert the same relation to recover the equivalent LIS energy and the
    LIS flux implied by that single measurement.
These are genuinely different operations (forward model-to-observable vs. inverting
one data point), not the same calculation run twice.

Usage notes / assumptions: standard library only. This is a one-parameter effective
model - it does not capture charge-sign-dependent drift, heliolatitude dependence, or
short-timescale transients (Forbush decreases, SEP events), all flagged in
<plugin root>/skills/hep-detector/references/space-based-direct-detection.md; do not use it to correct data taken
during such a transient. Energies, mass and LIS parameters must be finite and positive; phi finite and
nonnegative; charge a positive integer. NaN or inf input exits 2.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed; 2 usage or invalid input (NaN, inf, malformed file);
3 incomplete or inconclusive.
Run: python3 <plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py --modulate --energy 1.0 --mass 0.938272 --charge 1 --phi 0.5 --lis-normalization 1e4 --lis-index 2.7
     python3 <plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py --demodulate --energy 1.0 --mass 0.938272 --charge 1 --phi 0.5 --toa-flux 123.4
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.kinematics.relativistic import KinematicsError, Species, convert  # noqa: E402
from core.kinematics.relativistic import flux_jacobian as kin_flux_jacobian  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


def _finite(value, name, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if allow_zero:
        if value < 0:
            raise ValueError(f'{name} must be nonnegative')
    elif value <= 0:
        raise ValueError(f'{name} must be greater than zero')
    return float(value)


def _validate_charge(charge):
    if isinstance(charge, bool) or type(charge) is not int or charge <= 0:
        raise ValueError('charge must be a positive integer')
    return charge


def power_law_lis(energy, normalization, index):
    return normalization * energy ** (-index)


def flux_jacobian(energy_toa, energy_lis, mass):
    """(2mE + E^2) / (2mE' + E'^2), the force-field flux-conservation factor
    relating a TOA phase-space element to the corresponding LIS one."""
    return (2.0 * mass * energy_toa + energy_toa ** 2) / (2.0 * mass * energy_lis + energy_lis ** 2)


def modulate(energy_toa, mass, charge, phi, lis_flux_func):
    """Forward force-field model: given a LIS flux function, predict the flux at
    1 AU (TOA) for a particle of rest mass, charge, and modulation potential phi."""
    energy_toa = _finite(energy_toa, 'energy_toa', allow_zero=False)
    mass = _finite(mass, 'mass', allow_zero=False)
    phi = _finite(phi, 'phi')
    charge = _validate_charge(charge)

    energy_lis = energy_toa + charge * phi
    jacobian = flux_jacobian(energy_toa, energy_lis, mass)
    lis_flux = lis_flux_func(energy_lis)
    return {
        'energy_toa': energy_toa,
        'energy_lis': energy_lis,
        'jacobian': jacobian,
        'flux_lis': lis_flux,
        'flux_toa': jacobian * lis_flux,
    }


def demodulate(energy_toa, mass, charge, phi, toa_flux):
    """Invert the force-field relation for one measured (energy_toa, toa_flux)
    point: recover the equivalent LIS energy and the LIS flux implied by it."""
    energy_toa = _finite(energy_toa, 'energy_toa', allow_zero=False)
    mass = _finite(mass, 'mass', allow_zero=False)
    phi = _finite(phi, 'phi')
    charge = _validate_charge(charge)
    toa_flux = _finite(toa_flux, 'toa_flux', allow_zero=False)

    energy_lis = energy_toa + charge * phi
    jacobian = flux_jacobian(energy_toa, energy_lis, mass)
    return {
        'energy_toa': energy_toa,
        'energy_lis': energy_lis,
        'jacobian': jacobian,
        'flux_toa': toa_flux,
        'flux_lis': toa_flux / jacobian,
    }


ENERGY_KINDS = ('Ek_total', 'Ek_per_nucleon', 'rigidity')


CORE_VARIABLE = {'Ek_total': 'kinetic_energy', 'Ek_per_nucleon': 'kinetic_energy_per_nucleon', 'rigidity': 'rigidity'}


def _species(charge, mass, mass_number):
    return Species(Z=charge, A=mass_number, mass=mass)


def to_total_kinetic(value, kind, mass, charge, mass_number=None):
    """Total kinetic energy (GeV) from a value of the given kind (GeV, GeV/n or GV), via core/kinematics."""
    if kind not in CORE_VARIABLE:
        raise ValueError(f'energy kind must be one of {", ".join(ENERGY_KINDS)}')
    if kind == 'Ek_per_nucleon' and mass_number is None:
        raise ValueError('--energy-kind Ek_per_nucleon needs --mass-number')
    try:
        return convert(value, CORE_VARIABLE[kind], 'kinetic_energy', _species(charge, mass, mass_number))
    except KinematicsError as exc:
        raise ValueError(str(exc)) from None


def from_total_kinetic(ek, kind, mass, charge, mass_number=None):
    try:
        return convert(ek, 'kinetic_energy', CORE_VARIABLE[kind], _species(charge, mass, mass_number))
    except KinematicsError as exc:
        raise ValueError(str(exc)) from None


def variable_factor(ek, kind, mass, charge=1, mass_number=None):
    """|dE_kin/dx| at a point (core flux_jacobian): turns a flux per GeV of total kinetic energy into a flux per unit
    of x (1 for Ek_total, A for Ek_per_nucleon, |Z| beta for rigidity)."""
    try:
        return kin_flux_jacobian(ek, 'kinetic_energy', CORE_VARIABLE[kind], _species(charge, mass, mass_number))
    except KinematicsError as exc:
        raise ValueError(str(exc)) from None


def load_lis_table(path, kind):
    """Log-log interpolated LIS from {"variable": <energy kind>, "points": [[x, flux], ...]}; refuses extrapolation."""
    import json as _json
    with open(path, encoding='utf-8') as fh:
        doc = _json.load(fh, parse_constant=lambda t: (_ for _ in ()).throw(ValueError(f'non-finite {t} in the LIS table')))
    if not isinstance(doc, dict) or doc.get('variable') != kind or not isinstance(doc.get('points'), list):
        raise ValueError(f'LIS table must be {{"variable": "{kind}", "points": [[x, flux], ...]}} in the --energy-kind')
    pts = sorted((_finite(x, 'LIS x', allow_zero=False), _finite(y, 'LIS flux', allow_zero=False))
                 for x, y in (pt if isinstance(pt, (list, tuple)) and len(pt) == 2 else (None, None)
                              for pt in doc['points']))
    if len(pts) < 2 or any(b[0] <= a[0] for a, b in zip(pts, pts[1:])):
        raise ValueError('the LIS table needs at least two points with distinct x')

    def lis(x):
        if not pts[0][0] <= x <= pts[-1][0]:
            raise ValueError(f'LIS evaluated at {x:g}, outside the table [{pts[0][0]:g}, {pts[-1][0]:g}]')
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                t = math.log(x / x0) / math.log(x1 / x0)
                return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
        return pts[-1][1]
    return lis


def force_field(value, kind, mass, charge, phi_gv, mode, lis=None, toa_flux=None, mass_number=None):
    """One force-field point in any energy kind. The phase-space factor (2mE + E^2)/(2mE' + E'^2) is the same in every
    kind; the flux per unit of x picks up dE/dx at each point (1 per GeV or per GeV/n, beta for rigidity)."""
    ek = to_total_kinetic(_finite(value, 'energy', allow_zero=False), kind, mass, charge, mass_number)
    ek_lis = ek + charge * phi_gv
    jac = flux_jacobian(ek, ek_lis, mass)
    factor = jac * (variable_factor(ek, kind, mass, charge, mass_number)
                    / variable_factor(ek_lis, kind, mass, charge, mass_number))
    x_lis = from_total_kinetic(ek_lis, kind, mass, charge, mass_number)
    out = {'energy_kind': kind, 'energy_toa': value, 'energy_lis': x_lis, 'kinetic_energy_toa_gev': ek,
           'kinetic_energy_lis_gev': ek_lis, 'jacobian': jac, 'flux_factor': factor}
    if mode == 'modulate':
        out['flux_lis'] = lis(x_lis)
        out['flux_toa'] = factor * out['flux_lis']
    else:
        out['flux_toa'] = toa_flux
        out['flux_lis'] = toa_flux / factor
    for key in ('flux_lis', 'flux_toa'):
        if not math.isfinite(out[key]):
            raise ValueError(f'{key} is not finite for these inputs')
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--modulate', action='store_true',
                      help='forward model: LIS (power law or table) -> predicted TOA flux')
    mode.add_argument('--demodulate', action='store_true',
                      help='invert: a measured TOA flux point -> equivalent LIS energy/flux')
    parser.add_argument('--energy', type=float, required=True, dest='energy_toa',
                        help='TOA (1 AU) value of the energy variable (see --energy-kind)')
    parser.add_argument('--energy-kind', choices=ENERGY_KINDS, default='Ek_total', dest='energy_kind',
                        help='Ek_total (GeV, default), Ek_per_nucleon (GeV/n, needs --mass-number) or rigidity (GV); '
                             'fluxes are per unit of this variable')
    parser.add_argument('--mass', type=float, required=True, help='rest mass of the nucleus in GeV')
    parser.add_argument('--charge', type=int, required=True, help='absolute charge |Z| (positive integer)')
    parser.add_argument('--mass-number', type=int, dest='mass_number', help='mass number A (for Ek_per_nucleon)')
    parser.add_argument('--phi', type=float, required=True, help='modulation potential (unit: --phi-unit)')
    parser.add_argument('--phi-unit', choices=('GV', 'MV'), default='GV', dest='phi_unit',
                        help='unit of --phi and --phi-uncertainty (default GV)')
    parser.add_argument('--phi-uncertainty', type=float, dest='phi_uncertainty',
                        help='1-sigma uncertainty on phi, propagated to the derived flux by a central difference')
    parser.add_argument('--lis-normalization', type=float, dest='lis_normalization',
                        help='(--modulate) LIS power-law normalization A in J_LIS(x) = A * x^-gamma, x in --energy-kind')
    parser.add_argument('--lis-index', type=float, dest='lis_index',
                        help='(--modulate) LIS power-law index gamma')
    parser.add_argument('--lis-table', dest='lis_table',
                        help='(--modulate) JSON {"variable": <energy kind>, "points": [[x, flux], ...]}, log-log '
                             'interpolated, no extrapolation')
    parser.add_argument('--toa-flux', type=float, dest='toa_flux',
                        help='(--demodulate only) the measured flux at 1 AU/TOA energy')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        scale = 1e-3 if args.phi_unit == 'MV' else 1.0
        mass = _finite(args.mass, 'mass', allow_zero=False)
        charge = _validate_charge(args.charge)
        phi = _finite(args.phi, 'phi') * scale
        if args.mass_number is not None and (args.mass_number < charge or args.mass_number <= 0):
            raise ValueError('mass_number must be a positive integer of at least charge')
        lis = None
        if args.modulate:
            if args.lis_table:
                if args.lis_normalization is not None or args.lis_index is not None:
                    raise ValueError('give --lis-table or the power-law parameters, not both')
                lis = load_lis_table(args.lis_table, args.energy_kind)
                lis_desc = {'lis_table': args.lis_table}
            else:
                if args.lis_normalization is None or args.lis_index is None:
                    raise ValueError('--modulate requires --lis-normalization and --lis-index (or --lis-table)')
                norm = _finite(args.lis_normalization, 'lis_normalization', allow_zero=False)
                if isinstance(args.lis_index, bool) or not math.isfinite(args.lis_index):
                    raise ValueError('lis_index must be a finite number')

                def lis(x):
                    return power_law_lis(x, norm, args.lis_index)
                lis_desc = {'lis_normalization': norm, 'lis_index': args.lis_index}
            method = 'force-field approximation (modulation: LIS model given, TOA flux predicted)'
        else:
            if args.toa_flux is None:
                raise ValueError('--demodulate requires --toa-flux')
            _finite(args.toa_flux, 'toa_flux', allow_zero=False)
            lis_desc = {}
            method = 'force-field approximation (demodulation: measured TOA flux inverted to LIS)'
        mode_name = 'modulate' if args.modulate else 'demodulate'

        def point(phi_gv):
            return force_field(args.energy_toa, args.energy_kind, mass, charge, phi_gv, mode_name, lis, args.toa_flux,
                               args.mass_number)

        result = point(phi)
        result.update(lis_desc, phi_gv=phi)
        if args.phi_uncertainty is not None:
            dphi = _finite(args.phi_uncertainty, 'phi_uncertainty') * scale
            key = 'flux_toa' if args.modulate else 'flux_lis'
            if dphi > 0:
                h = min(dphi, phi) / 2 if phi > 0 else dphi / 2
                lo, hi = point(max(phi - h, 0.0))[key], point(phi + h)[key]
                width = (phi + h) - max(phi - h, 0.0)
                result['phi_uncertainty_gv'] = dphi
                result[f'sigma_{key}_from_phi'] = abs(hi - lo) / width * dphi
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps({'status': args.status, 'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()
