#!/usr/bin/env python3
"""Analytic vertical Stormer geomagnetic cutoff rigidity.

Purpose: first-order estimate of the minimum rigidity a charged cosmic ray must have
to reach a given geomagnetic latitude and altitude, for a pure dipole field arriving
from the vertical (zenith) direction. See
<plugin root>/skills/detector-response/references/space-based-direct-detection.md.

What it does: evaluates the vertical (zenith angle 0) case of the Stormer formula
    R_c = C * cos^4(lambda_m) / (r^2 * (1 + sqrt(1 - sin(eps) sin(xi) cos^3(lambda_m)))^2),
where the square root is 1 for vertical arrival, so
    R_c = (C / 4) * cos^4(lambda_m) / r^2 = 14.9 GV * cos^4(lambda_m) / r^2   (r in Earth radii)
(Smart & Shea 2005, Adv. Space Res. 36, 2012). C = 59.6 GV scales with dipole moment M;
geocentric distance r, geomagnetic latitude lambda_m. Uses
the IGRF-epoch-averaged dipole moment as a default. Also converts a cutoff rigidity to
the corresponding minimum kinetic energy per nucleon for a given (Z, A).

Usage notes / assumptions: standard library only. This is the *vertical* cutoff for an
idealized dipole - it does not capture off-vertical arrival directions (which have a
higher, direction-dependent cutoff), the real non-dipolar field's "penumbra" of
partially forbidden trajectories, or backscattered/re-entrant particles below cutoff.
A rigorous cutoff for a specific orbit, epoch, and arrival direction requires particle
backtracing through a full geomagnetic field model (e.g. IGRF) and is not something
this formula replaces - see the docstring caveat repeated in the reference file.
Rigidity in GV, distance in Earth radii (default 1.0 = sea level, ignoring altitude
above the surface for simplicity), dipole moment in G*cm^3 (default value below is the
approximate present-epoch value, not tied to a specific IGRF release).
Run: python3 <plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py --latitude 0
     python3 <plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py --latitude 41.5 --altitude-re 1.0009 --charge 1 --mass-number 1
"""
import argparse
import json
import math

EARTH_RADIUS_CM = 6.371e8
DEFAULT_DIPOLE_MOMENT_G_CM3 = 8.05e25
PROTON_MASS_GEV = 0.938272  # PDG
ATOMIC_MASS_UNIT_GEV = 0.9315  # nuclear mass ~ A * u for A > 1 (binding energy ignored)


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def stormer_cutoff_gv(latitude_deg, altitude_re=1.0, dipole_moment_g_cm3=DEFAULT_DIPOLE_MOMENT_G_CM3):
    """Vertical Stormer cutoff rigidity in GV at a geomagnetic latitude (degrees) and
    geocentric distance (Earth radii)."""
    latitude_deg = _finite(latitude_deg, 'latitude_deg')
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError('latitude_deg must be between -90 and 90')
    altitude_re = _finite(altitude_re, 'altitude_re')
    if altitude_re <= 0:
        raise ValueError('altitude_re must be greater than zero')
    dipole_moment_g_cm3 = _finite(dipole_moment_g_cm3, 'dipole_moment_g_cm3')
    if dipole_moment_g_cm3 <= 0:
        raise ValueError('dipole_moment_g_cm3 must be greater than zero')

    lam = math.radians(latitude_deg)
    cos_lam = math.cos(lam)
    r_cm = altitude_re * EARTH_RADIUS_CM

    # Stormer constant C = 59.6 GV for the reference dipole moment at one Earth radius
    # (Smart & Shea 2005), scaled by (M/M_0)*(r_E/r)^2. For vertical arrival the
    # direction-dependent square root in the Stormer denominator equals 1, giving
    # (1 + 1)^2 = 4, i.e. the familiar 14.9 GV * cos^4(lambda) at the equator.
    # (The (1 + sqrt(1 + cos^3))^2 form is the westward-horizontal cutoff, not vertical.)
    reference_cutoff_gv = 59.6
    scale = (dipole_moment_g_cm3 / DEFAULT_DIPOLE_MOMENT_G_CM3) * (EARTH_RADIUS_CM / r_cm) ** 2

    return reference_cutoff_gv * scale * cos_lam ** 4 / 4.0


def cutoff_kinetic_energy_per_nucleon_gev(cutoff_rigidity_gv, charge, mass_number):
    """Minimum kinetic energy per nucleon corresponding to a cutoff rigidity, for a
    nucleus of given charge Z and mass number A (kinetic energy from
    E = sqrt((Z*e*R)^2 + m^2) - m, then divided by A)."""
    if isinstance(charge, bool) or type(charge) is not int or charge <= 0:
        raise ValueError('charge must be a positive integer')
    if isinstance(mass_number, bool) or type(mass_number) is not int or mass_number <= 0:
        raise ValueError('mass_number must be a positive integer')
    if mass_number < charge:
        raise ValueError('mass_number must be at least charge')
    cutoff_rigidity_gv = _finite(cutoff_rigidity_gv, 'cutoff_rigidity_gv')
    if cutoff_rigidity_gv < 0:
        raise ValueError('cutoff_rigidity_gv must be nonnegative')

    momentum_gev = charge * cutoff_rigidity_gv
    mass_gev = PROTON_MASS_GEV if mass_number == 1 else mass_number * ATOMIC_MASS_UNIT_GEV
    total_energy_gev = math.sqrt(momentum_gev ** 2 + mass_gev ** 2)
    kinetic_energy_gev = total_energy_gev - mass_gev
    return kinetic_energy_gev / mass_number


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--latitude', type=float, required=True, dest='latitude_deg',
                        help='geomagnetic latitude in degrees, -90 to 90')
    parser.add_argument('--altitude-re', type=float, default=1.0,
                        help='geocentric distance in Earth radii (default 1.0)')
    parser.add_argument('--dipole-moment', type=float, default=DEFAULT_DIPOLE_MOMENT_G_CM3,
                        help='dipole moment in G*cm^3 (default: approximate present epoch)')
    parser.add_argument('--charge', type=int, help='nucleus charge Z, for the energy conversion')
    parser.add_argument('--mass-number', type=int, dest='mass_number',
                        help='nucleus mass number A, for the energy conversion')
    args = parser.parse_args()

    try:
        cutoff_gv = stormer_cutoff_gv(args.latitude_deg, args.altitude_re, args.dipole_moment)
        result = {
            'latitude_deg': args.latitude_deg,
            'altitude_re': args.altitude_re,
            'vertical_cutoff_rigidity_gv': cutoff_gv,
        }
        if args.charge is not None or args.mass_number is not None:
            if args.charge is None or args.mass_number is None:
                raise ValueError('--charge and --mass-number must be given together')
            result['charge'] = args.charge
            result['mass_number'] = args.mass_number
            result['minimum_kinetic_energy_per_nucleon_gev'] = cutoff_kinetic_energy_per_nucleon_gev(
                cutoff_gv, args.charge, args.mass_number)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({
        'method': 'vertical Stormer dipole cutoff (idealized; see docstring caveats)',
        **result,
    }, indent=2))


if __name__ == '__main__':
    main()
