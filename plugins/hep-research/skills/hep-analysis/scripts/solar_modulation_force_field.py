#!/usr/bin/env python3
"""Force-field approximation for solar modulation of the cosmic-ray spectrum.

Purpose: convert between the local interstellar spectrum (LIS, outside the
heliosphere) and the flux measured at 1 AU, given a single effective modulation
potential phi - the standard first-order correction described in
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/35-space-based-direct-detection.md and the bound experiment profile's modules,
needed because space-based magnetic spectrometers measure at 1 AU during a specific, time-
varying solar-activity epoch, not the LIS directly.

What it does: implements
    E_LIS = E_TOA + |Z| * phi
    J_TOA(E_TOA) = ((2*m*E_TOA + E_TOA^2) / (2*m*E_LIS + E_LIS^2)) * J_LIS(E_LIS)
for a particle of total rest mass m (GeV), absolute charge |Z|, and *total* kinetic
energy E (GeV), phi in GV (Gleeson & Axford 1968). For kinetic energy per nucleon the
shift is (|Z|/A)*phi with m the nucleon mass, so pass E = A * E_per_nucleon and
m = A * m_nucleon (or convert back afterwards); using per-nucleon E with |Z|*phi
over-modulates every A > 1 nucleus (by 2x for He-4). Two modes:
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
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/35-space-based-direct-detection.md; do not use it to correct data taken
during such a transient. Energies must be finite and positive; phi and mass must be
finite and nonnegative; charge must be a positive integer.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/solar_modulation_force_field.py --modulate --energy 1.0 --mass 0.938272 --charge 1 --phi 0.5 --lis-normalization 1e4 --lis-index 2.7
     python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/scripts/solar_modulation_force_field.py --demodulate --energy 1.0 --mass 0.938272 --charge 1 --phi 0.5 --toa-flux 123.4
"""
import argparse
import json
import math


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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--modulate', action='store_true',
                      help='forward model: LIS power law -> predicted TOA flux')
    mode.add_argument('--demodulate', action='store_true',
                      help='invert: a measured TOA flux point -> equivalent LIS energy/flux')
    parser.add_argument('--energy', type=float, required=True, dest='energy_toa',
                        help='TOA (1 AU) kinetic energy in GeV')
    parser.add_argument('--mass', type=float, required=True, help='rest mass in GeV')
    parser.add_argument('--charge', type=int, required=True, help='absolute charge |Z| (positive integer)')
    parser.add_argument('--phi', type=float, required=True, help='modulation potential in GV (or consistent units)')
    parser.add_argument('--lis-normalization', type=float, dest='lis_normalization',
                        help='(--modulate only) LIS power-law normalization A in J_LIS(E) = A * E^-gamma')
    parser.add_argument('--lis-index', type=float, dest='lis_index',
                        help='(--modulate only) LIS power-law index gamma')
    parser.add_argument('--toa-flux', type=float, dest='toa_flux',
                        help='(--demodulate only) the measured flux at 1 AU/TOA energy')
    args = parser.parse_args()

    try:
        if args.modulate:
            if args.lis_normalization is None or args.lis_index is None:
                raise ValueError('--modulate requires --lis-normalization and --lis-index')

            def lis_flux_func(e):
                return power_law_lis(e, args.lis_normalization, args.lis_index)

            result = modulate(args.energy_toa, args.mass, args.charge, args.phi, lis_flux_func)
            method = 'force-field approximation (modulation: LIS model given, TOA flux predicted)'
        else:
            if args.toa_flux is None:
                raise ValueError('--demodulate requires --toa-flux')
            result = demodulate(args.energy_toa, args.mass, args.charge, args.phi, args.toa_flux)
            method = 'force-field approximation (demodulation: measured TOA flux inverted to LIS)'
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()
