#!/usr/bin/env python3
"""Ring-imaging Cherenkov kinematics: thresholds, angles, photon yield, and separation.

Purpose: evaluate what a RICH radiator can actually do - which species emit at all at a
given momentum, how well the ring angle determines velocity, and where the angle
saturates and separation is lost.

What it does: for a radiator of refractive index n it computes each species' threshold
momentum, the Cherenkov angle and its saturation value, the detected photon yield, the
per-track angular resolution, and the resulting velocity and mass resolution, plus the
separation in sigma between two species and the momentum ceiling where it is lost.

Usage notes / assumptions: standard library only. Momenta in GeV/c, masses in GeV/c^2,
radiator length in cm, angles reported in both radians and milliradians. Photon yield
uses the figure-of-merit form N = N0 * L * sin^2(theta_c), with N0 in cm^-1 folding in
photon-detection efficiency and the accepted wavelength band - it is a design estimate,
not a simulation. Chromatic dispersion is represented only through the single-photon
angular resolution supplied by the user; n is treated as a single number. See
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/24-particle-identification.md.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/cherenkov_angle.py --index 1.05 --species pi K --momentum 10
"""
import argparse
import json
import math

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pid_separation_power import MASSES_GEV, kinematics, resolve_mass  # noqa: E402


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def validate_index(index):
    if isinstance(index, bool) or not isinstance(index, (int, float)):
        raise ValueError('refractive index must be a number')
    if not math.isfinite(index) or index <= 1.0:
        raise ValueError('refractive index must be greater than 1 (no Cherenkov light otherwise)')
    return float(index)


def threshold_momentum(mass_gev, index):
    """Lowest momentum that emits Cherenkov light: p_thr = m / sqrt(n^2 - 1).

    Follows from beta > 1/n.
    """
    mass_gev = _positive(mass_gev, 'mass')
    index = validate_index(index)
    return mass_gev / math.sqrt(index * index - 1.0)


def saturation_angle(index):
    """Maximum Cherenkov angle, reached as beta -> 1: arccos(1/n)."""
    return math.acos(1.0 / validate_index(index))


def cherenkov_angle(momentum_gev, mass_gev, index):
    """Cherenkov half-angle in radians, or None below threshold."""
    index = validate_index(index)
    beta = kinematics(momentum_gev, mass_gev)['beta']
    cosine = 1.0 / (index * beta)
    if cosine >= 1.0:
        return None
    return math.acos(cosine)


def photon_yield(angle_rad, radiator_length_cm, figure_of_merit_per_cm):
    """N = N0 * L * sin^2(theta_c), the standard design estimate."""
    radiator_length_cm = _positive(radiator_length_cm, 'radiator_length')
    figure_of_merit_per_cm = _positive(figure_of_merit_per_cm, 'figure_of_merit')
    return figure_of_merit_per_cm * radiator_length_cm * math.sin(angle_rad) ** 2


def track_angular_resolution(single_photon_sigma_rad, photons):
    """Per-track resolution improves as 1/sqrt(N) over the detected photons."""
    single_photon_sigma_rad = _positive(single_photon_sigma_rad, 'single_photon_resolution')
    if photons <= 0:
        return None
    return single_photon_sigma_rad / math.sqrt(photons)


def beta_resolution_from_angle(angle_rad, sigma_angle_rad):
    """dbeta/beta = tan(theta_c) * sigma_theta.

    From beta = 1/(n cos theta): dbeta/dtheta = beta tan(theta).
    """
    return math.tan(angle_rad) * sigma_angle_rad


def describe_species(momentum_gev, mass_gev, index, radiator_length_cm,
                     figure_of_merit_per_cm, single_photon_sigma_rad):
    """Full per-species RICH response at one momentum."""
    kin = kinematics(momentum_gev, mass_gev)
    threshold = threshold_momentum(mass_gev, index)
    angle = cherenkov_angle(momentum_gev, mass_gev, index)
    record = {
        'mass_gev': mass_gev,
        'beta': kin['beta'],
        'gamma': kin['gamma'],
        'threshold_momentum_gev': threshold,
        'above_threshold': angle is not None,
    }
    if angle is None:
        record['note'] = 'below Cherenkov threshold in this radiator; no ring is produced'
        return record

    photons = photon_yield(angle, radiator_length_cm, figure_of_merit_per_cm)
    sigma_angle = track_angular_resolution(single_photon_sigma_rad, photons)
    relative_beta = beta_resolution_from_angle(angle, sigma_angle)
    record.update({
        'cherenkov_angle_rad': angle,
        'cherenkov_angle_mrad': angle * 1000.0,
        'saturation_angle_mrad': saturation_angle(index) * 1000.0,
        'fraction_of_saturation': angle / saturation_angle(index),
        'detected_photons': photons,
        'track_angular_resolution_mrad': sigma_angle * 1000.0,
        'relative_beta_resolution': relative_beta,
        'relative_mass_resolution': kin['gamma'] ** 2 * relative_beta,
    })
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--index', type=float, required=True,
                        help='radiator refractive index (must exceed 1)')
    parser.add_argument('--species', nargs=2, required=True, metavar=('A', 'B'),
                        help=f'two of {sorted(MASSES_GEV)}, or masses in GeV/c^2')
    parser.add_argument('--momentum', type=float, default=10.0, help='GeV/c (default 10)')
    parser.add_argument('--radiator-length', type=float, default=2.0,
                        dest='radiator_length', help='radiator thickness in cm (default 2)')
    parser.add_argument('--figure-of-merit', type=float, default=100.0,
                        dest='figure_of_merit',
                        help='N0 in cm^-1, folding in detection efficiency (default 100)')
    parser.add_argument('--single-photon-resolution', type=float, default=5.0,
                        dest='single_photon_resolution',
                        help='single-photon angular resolution in mrad (default 5)')
    args = parser.parse_args()

    try:
        index = validate_index(args.index)
        mass_a = resolve_mass(args.species[0])
        mass_b = resolve_mass(args.species[1])
        if mass_a == mass_b:
            raise ValueError('the two species must have different masses')
        sigma_photon = _positive(args.single_photon_resolution,
                                 'single_photon_resolution') / 1000.0
        common = (index, args.radiator_length, args.figure_of_merit, sigma_photon)
        record_a = describe_species(args.momentum, mass_a, *common)
        record_b = describe_species(args.momentum, mass_b, *common)
        record_a['name'], record_b['name'] = args.species

        payload = {
            'refractive_index': index,
            'momentum_gev': args.momentum,
            'saturation_angle_mrad': saturation_angle(index) * 1000.0,
            'species_a': record_a,
            'species_b': record_b,
        }
        if record_a['above_threshold'] and record_b['above_threshold']:
            difference = abs(record_a['cherenkov_angle_rad'] - record_b['cherenkov_angle_rad'])
            payload['angle_difference_mrad'] = difference * 1000.0
            payload['n_sigma'] = difference / (record_a['track_angular_resolution_mrad'] / 1000.0)
        else:
            payload['n_sigma'] = None
            payload['note'] = ('At least one species is below threshold: identification here '
                               'rests on the presence or absence of a ring, and depends on '
                               'the ring-finding efficiency.')
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
