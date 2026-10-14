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
idealized dipole - it does not capture off-vertical arrival directions (the cutoff is
east-west asymmetric: for positive particles lower from the west and higher from the
east than the vertical value), the real non-dipolar field's "penumbra" of
partially forbidden trajectories, or backscattered/re-entrant particles below cutoff.
A rigorous cutoff for a specific orbit, epoch, and arrival direction requires particle
backtracing through a full geomagnetic field model (e.g. IGRF) and is not something
this formula replaces - see the docstring caveat repeated in the reference file.
Rigidity in GV, geocentric distance in Earth radii (--radius-re, default 1.0 = the surface; the old name
--altitude-re is a deprecated alias, since the value is a distance from the Earth's centre, not an altitude), dipole moment in G*cm^3 (default value below is the
approximate present-epoch value, not tied to a specific IGRF release).
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed; 2 usage or invalid input (NaN, inf, malformed file);
3 incomplete or inconclusive.
Run: python3 <plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py --latitude 0
     python3 <plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py --latitude 41.5 --radius-re 1.0009 --charge 1 --mass-number 2
Nuclear masses: tabulated AME2020 values for 1H to 18O (see ATOMIC_MASS_U); other (Z, A) use A x u and the output
says so (mass_source).
"""
import argparse
import json
import math
import sys

EARTH_RADIUS_CM = 6.371e8
DEFAULT_DIPOLE_MOMENT_G_CM3 = 8.05e25
PROTON_MASS_GEV = 0.93827208943  # CODATA 2022 m_p c^2
# Atomic masses in u from AME2020 (Wang et al., Chinese Phys. C 45 (2021) 030003; file mass.mas20, read
# 2026-10-13 from https://www-nds.iaea.org/amdc/ame2020/mass_1.mas20.txt). Nuclear mass = atomic mass x m_u c^2 -
# Z m_e c^2 (CODATA 2022: m_u c^2 = 931.49410372 MeV, m_e c^2 = 0.51099895069 MeV); the electron binding energy
# (below 1 keV for Z <= 8) is neglected.
ATOMIC_MASS_U = {
    (1, 1): 1.007825031898,  # 1H
    (1, 2): 2.014101777844,  # 2H
    (1, 3): 3.01604928132,  # 3H
    (2, 3): 3.01602932197,  # 3He
    (2, 4): 4.00260325413,  # 4He
    (3, 6): 6.01512288742,  # 6Li
    (3, 7): 7.01600343426,  # 7Li
    (4, 7): 7.016928714,  # 7Be
    (4, 9): 9.012183062,  # 9Be
    (4, 10): 10.013534692,  # 10Be
    (5, 10): 10.012936862,  # 10B
    (5, 11): 11.009305166,  # 11B
    (6, 12): 12.0,  # 12C
    (6, 13): 13.00335483534,  # 13C
    (6, 14): 14.00324198862,  # 14C
    (7, 14): 14.00307400425,  # 14N
    (7, 15): 15.00010889827,  # 15N
    (8, 16): 15.99491461926,  # 16O
    (8, 17): 16.99913175595,  # 17O
    (8, 18): 17.99915961214,  # 18O
}
ATOMIC_MASS_UNIT_GEV = 0.93149410372  # CODATA 2022 m_u c^2
ELECTRON_MASS_GEV = 0.00051099895069  # CODATA 2022 m_e c^2


def nuclear_mass_gev(charge, mass_number):
    """(mass in GeV, source) of a bare nucleus: tabulated AME2020 value, or A x u flagged as an approximation."""
    key = (charge, mass_number)
    if key == (1, 1):
        return PROTON_MASS_GEV, 'CODATA 2022 proton mass'
    if key in ATOMIC_MASS_U:
        return ATOMIC_MASS_U[key] * ATOMIC_MASS_UNIT_GEV - charge * ELECTRON_MASS_GEV, 'AME2020 table'
    return mass_number * ATOMIC_MASS_UNIT_GEV, 'approximation A x u (binding energy ignored; not tabulated)'
STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


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
    mass_gev = nuclear_mass_gev(charge, mass_number)[0]
    total_energy_gev = math.sqrt(momentum_gev ** 2 + mass_gev ** 2)
    kinetic_energy_gev = total_energy_gev - mass_gev
    return kinetic_energy_gev / mass_number


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--latitude', type=float, required=True, dest='latitude_deg',
                        help='geomagnetic latitude in degrees, -90 to 90')
    parser.add_argument('--radius-re', type=float, default=None, dest='radius_re',
                        help='geocentric distance in Earth radii (default 1.0, the surface)')
    parser.add_argument('--altitude-re', type=float, default=None, dest='altitude_re',
                        help='deprecated alias of --radius-re (the value is a geocentric distance)')
    parser.add_argument('--dipole-moment', type=float, default=DEFAULT_DIPOLE_MOMENT_G_CM3,
                        help='dipole moment in G*cm^3 (default: approximate present epoch)')
    parser.add_argument('--charge', type=int, help='nucleus charge Z, for the energy conversion')
    parser.add_argument('--mass-number', type=int, dest='mass_number',
                        help='nucleus mass number A, for the energy conversion')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        if args.radius_re is not None and args.altitude_re is not None:
            raise ValueError('give --radius-re only (--altitude-re is its deprecated alias)')
        if args.altitude_re is not None:
            print('geomagnetic_cutoff.py: warning: --altitude-re is deprecated; use --radius-re (a geocentric distance)',
                  file=sys.stderr)
        radius = args.radius_re if args.radius_re is not None else (args.altitude_re if args.altitude_re is not None else 1.0)
        cutoff_gv = stormer_cutoff_gv(args.latitude_deg, radius, args.dipole_moment)
        result = {
            'latitude_deg': args.latitude_deg,
            'radius_re': radius,
            'vertical_cutoff_rigidity_gv': cutoff_gv,
        }
        if args.charge is not None or args.mass_number is not None:
            if args.charge is None or args.mass_number is None:
                raise ValueError('--charge and --mass-number must be given together')
            result['charge'] = args.charge
            result['mass_number'] = args.mass_number
            result['minimum_kinetic_energy_per_nucleon_gev'] = cutoff_kinetic_energy_per_nucleon_gev(
                cutoff_gv, args.charge, args.mass_number)
            result['nuclear_mass_gev'], result['mass_source'] = nuclear_mass_gev(args.charge, args.mass_number)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({
        'status': args.status,
        'method': 'vertical Stormer dipole cutoff (idealized; see docstring caveats)',
        **result,
    }, indent=2))


if __name__ == '__main__':
    main()
