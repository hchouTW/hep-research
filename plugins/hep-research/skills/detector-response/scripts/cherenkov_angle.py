#!/usr/bin/env python3
"""Ring-imaging Cherenkov kinematics: thresholds, angles, photon yield, and separation.

Purpose: evaluate what a RICH radiator can actually do - which species emit at all at a
given momentum, how many photons they give, how well the ring angle determines velocity,
and where the angle saturates and separation is lost.

What it does: for a radiator of refractive index n it computes each species' threshold
momentum, the Cherenkov angle and its saturation value, the expected photon yield, the
probability of no photon at all, the per-track angular resolution, and the resulting
velocity and mass resolution, plus the separation in sigma between two species at one
momentum (or rigidity). It does not scan momentum; for a separation ceiling pass the
relative_beta_resolution to <plugin root>/skills/detector-response/scripts/pid_separation_power.py --mode velocity.

Photon regimes (per species, from the expected photon number N): none for N < 0.5, few
for 0.5 <= N < 5, gaussian for N >= 5 (provisional thresholds). Only when both species
are gaussian is an angular n_sigma given; otherwise identification rests on the presence
or absence of photons and the output gives threshold_discrimination (the probability of
at least one photon per species) instead of a Gaussian separation, and no
relative_beta_resolution for the few-photon species.

Usage notes / assumptions: standard library only. Momenta in GeV/c, masses in GeV/c^2,
radiator length in cm, angles reported in both radians and milliradians. Photon yield
uses the figure-of-merit form N = N0 * L * z^2 * sin^2(theta_c), with z the projectile charge
number (Frank-Tamm: the yield scales with z^2) and N0 in cm^-1 folding in photon-detection
efficiency and the accepted wavelength band - it is a design estimate, not a simulation.
Species are a name (He3 and He4 carry z=2), a mass, or mass:charge (e.g. 3.727:2). With
--rigidity R each species is evaluated at its own momentum p = zR; the threshold and the
angle depend on beta only, so the threshold momentum m/sqrt(n^2-1) is charge-independent and
the threshold rigidity is that momentum divided by z. Per-track resolution is sqrt(sigma_photon^2/N + sigma_track^2); the
track term (--track-resolution, default 0) covers track direction and other errors that
do not average down with N. Chromatic dispersion is represented only through the
single-photon angular resolution supplied by the user; n is treated as a single number.
Separation convention (--convention): single (default) divides by species A's per-track
resolution; quadrature by sqrt(sigma_A^2 + sigma_B^2), symmetric in the species. See
<plugin root>/skills/detector-response/references/particle-identification.md.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed or the input file is unreadable or invalid (JSON with ok false);
2 invalid input (JSON with error_kind invalid-input on stdout, the usage on stderr).
Run: python3 <plugin root>/skills/detector-response/scripts/cherenkov_angle.py --index 1.05 --species pi K --momentum 10
"""
import argparse
import json
import math

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pid_separation_power import MASSES_GEV, kinematics, resolve_species  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


# Expected-photon thresholds between the none / few / gaussian regimes (provisional).
FEW_PHOTONS = 0.5
GAUSSIAN_PHOTONS = 5.0
CONVENTIONS = ('single', 'quadrature')


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


def _charge(charge):
    if isinstance(charge, bool) or not isinstance(charge, int) or charge < 1:
        raise ValueError('charge must be an integer of at least 1')
    return charge


def photon_yield(angle_rad, radiator_length_cm, figure_of_merit_per_cm, charge=1):
    """N = N0 * L * z^2 * sin^2(theta_c), the standard design estimate (z = charge number)."""
    radiator_length_cm = _positive(radiator_length_cm, 'radiator_length')
    figure_of_merit_per_cm = _positive(figure_of_merit_per_cm, 'figure_of_merit')
    charge = _charge(charge)
    return figure_of_merit_per_cm * radiator_length_cm * charge * charge * math.sin(angle_rad) ** 2


def photon_regime(photons):
    """'none' (N < 0.5), 'few' (0.5 <= N < 5) or 'gaussian' (N >= 5) expected photons."""
    if photons < FEW_PHOTONS:
        return 'none'
    if photons < GAUSSIAN_PHOTONS:
        return 'few'
    return 'gaussian'


def track_angular_resolution(single_photon_sigma_rad, photons, track_sigma_rad=0.0):
    """Per-track resolution sqrt(sigma_photon^2 / N + sigma_track^2).

    The photon term improves as 1/sqrt(N); the track term does not.
    """
    single_photon_sigma_rad = _positive(single_photon_sigma_rad, 'single_photon_resolution')
    if isinstance(track_sigma_rad, bool) or not isinstance(track_sigma_rad, (int, float)) \
            or not math.isfinite(track_sigma_rad) or track_sigma_rad < 0:
        raise ValueError('track_resolution must be finite and nonnegative')
    if photons <= 0:
        return None
    return math.hypot(single_photon_sigma_rad / math.sqrt(photons), track_sigma_rad)


def beta_resolution_from_angle(angle_rad, sigma_angle_rad):
    """dbeta/beta = tan(theta_c) * sigma_theta.

    From beta = 1/(n cos theta): dbeta/dtheta = beta tan(theta).
    """
    return math.tan(angle_rad) * sigma_angle_rad


def describe_species(momentum_gev, mass_gev, index, radiator_length_cm,
                     figure_of_merit_per_cm, single_photon_sigma_rad, track_sigma_rad=0.0, charge=1):
    """Full per-species RICH response at one momentum, for a projectile of charge number z."""
    charge = _charge(charge)
    kin = kinematics(momentum_gev, mass_gev)
    threshold = threshold_momentum(mass_gev, index)
    angle = cherenkov_angle(momentum_gev, mass_gev, index)
    record = {
        'mass_gev': mass_gev,
        'charge': charge,
        'momentum_gev': momentum_gev,
        'beta': kin['beta'],
        'gamma': kin['gamma'],
        'threshold_momentum_gev': threshold,
        'threshold_rigidity_gv': threshold / charge,
        # Kinematic threshold only; whether a ring is seen depends on photon_regime.
        'above_threshold': angle is not None,
    }
    if angle is None:
        record.update({'expected_photons': 0.0, 'p_no_photon': 1.0, 'photon_regime': 'none',
                       'note': 'below Cherenkov threshold in this radiator; no ring is produced'})
        return record

    photons = photon_yield(angle, radiator_length_cm, figure_of_merit_per_cm, charge)
    regime = photon_regime(photons)
    record.update({
        'cherenkov_angle_rad': angle,
        'cherenkov_angle_mrad': angle * 1000.0,
        'saturation_angle_mrad': saturation_angle(index) * 1000.0,
        'fraction_of_saturation': angle / saturation_angle(index),
        'expected_photons': photons,
        'p_no_photon': math.exp(-photons),
        'photon_regime': regime,
    })
    if regime != 'gaussian':
        record['note'] = ('too few expected photons for a Gaussian angle measurement; the '
                          'species is identified (if at all) by the presence of photons')
        return record
    sigma_angle = track_angular_resolution(single_photon_sigma_rad, photons, track_sigma_rad)
    relative_beta = beta_resolution_from_angle(angle, sigma_angle)
    record.update({
        'track_angular_resolution_mrad': sigma_angle * 1000.0,
        'relative_beta_resolution': relative_beta,
        'relative_mass_resolution': kin['gamma'] ** 2 * relative_beta,
    })
    return record


def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'cherenkov_angle.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = JsonArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--index', type=float, required=True,
                        help='radiator refractive index (must exceed 1)')
    parser.add_argument('--species', nargs=2, required=True, metavar=('A', 'B'),
                        help=f'two of {sorted(MASSES_GEV)} (He3 and He4 carry z=2), masses in '
                             'GeV/c^2, or mass:charge')
    given = parser.add_mutually_exclusive_group()
    given.add_argument('--momentum', type=float, default=None, help='GeV/c (default 10)')
    given.add_argument('--rigidity', type=float, default=None,
                       help='GV; each species then has p = z * R')
    parser.add_argument('--radiator-length', type=float, default=2.0,
                        dest='radiator_length', help='radiator thickness in cm (default 2)')
    parser.add_argument('--figure-of-merit', type=float, default=100.0,
                        dest='figure_of_merit',
                        help='N0 in cm^-1, folding in detection efficiency (default 100)')
    parser.add_argument('--single-photon-resolution', type=float, default=5.0,
                        dest='single_photon_resolution',
                        help='single-photon angular resolution in mrad (default 5)')
    parser.add_argument('--track-resolution', type=float, default=0.0,
                        dest='track_resolution',
                        help='per-track angular term in mrad that does not shrink with N '
                             '(default 0)')
    parser.add_argument('--convention', choices=CONVENTIONS, default='single',
                        help='single: delta/sigma of species A (default); quadrature: '
                             'delta/sqrt(sigma_A^2 + sigma_B^2)')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        index = validate_index(args.index)
        mass_a, charge_a = resolve_species(args.species[0])
        mass_b, charge_b = resolve_species(args.species[1])
        if (mass_a, charge_a) == (mass_b, charge_b):
            raise ValueError('the two species must differ in mass or charge')
        if args.rigidity is not None:
            rigidity = _positive(args.rigidity, 'rigidity')
            momentum_a, momentum_b = charge_a * rigidity, charge_b * rigidity
        else:
            momentum = 10.0 if args.momentum is None else args.momentum
            momentum_a = momentum_b = momentum
        sigma_photon = _positive(args.single_photon_resolution,
                                 'single_photon_resolution') / 1000.0
        # Validated here as well: with both species below threshold photon_yield never runs.
        _positive(args.radiator_length, 'radiator_length')
        _positive(args.figure_of_merit, 'figure_of_merit')
        if not math.isfinite(args.track_resolution) or args.track_resolution < 0:
            raise ValueError('track_resolution must be finite and nonnegative')
        common = (index, args.radiator_length, args.figure_of_merit, sigma_photon,
                  args.track_resolution / 1000.0)
        record_a = describe_species(momentum_a, mass_a, *common, charge=charge_a)
        record_b = describe_species(momentum_b, mass_b, *common, charge=charge_b)
    except ValueError as exc:
        parser.error(str(exc))

    record_a['name'], record_b['name'] = args.species
    if args.convention == 'quadrature':
        convention, reference = 'delta_over_quadrature_sum_of_both_sigmas', None
    else:
        convention, reference = 'delta_over_sigma_of_species_a', args.species[0]
    warnings = [f'species {label}: relative beta resolution {rec["relative_beta_resolution"]:.3g} exceeds 0.1; the '
                'small-error propagation dbeta/beta = tan(theta_c) sigma_theta is not reliable there'
                for label, rec in (('a', record_a), ('b', record_b))
                if rec.get('relative_beta_resolution') is not None and rec['relative_beta_resolution'] > 0.1]
    payload = {
        'status': args.status,
        'warnings': warnings,
        'refractive_index': index,
        'input_variable': 'rigidity' if args.rigidity is not None else 'momentum',
        'momentum_gev': None if args.rigidity is not None else momentum_a,
        'rigidity_gv': args.rigidity,
        'saturation_angle_mrad': saturation_angle(index) * 1000.0,
        'species_a': record_a,
        'species_b': record_b,
        'separation_convention': convention,
        'reference_species': reference,
    }
    gaussian = (record_a['photon_regime'] == 'gaussian'
                and record_b['photon_regime'] == 'gaussian')
    if gaussian:
        difference = abs(record_a['cherenkov_angle_rad'] - record_b['cherenkov_angle_rad'])
        sigma_a = record_a['track_angular_resolution_mrad'] / 1000.0
        sigma_b = record_b['track_angular_resolution_mrad'] / 1000.0
        sigma = sigma_a if args.convention == 'single' else math.hypot(sigma_a, sigma_b)
        payload['angle_difference_mrad'] = difference * 1000.0
        payload['n_sigma'] = difference / sigma
    else:
        payload['n_sigma'] = None
        payload['threshold_discrimination'] = {
            'probability_of_at_least_one_photon': {
                'species_a': 1.0 - record_a['p_no_photon'],
                'species_b': 1.0 - record_b['p_no_photon'],
            },
            'note': ('Identification here rests on the presence or absence of photons, not '
                     'on the ring angle. A ring finder usually needs several photons, so '
                     'these are upper bounds on the ring-finding probability.'),
        }
        payload['note'] = ('At least one species has too few expected photons (photon_regime '
                           'none or few) for a Gaussian angular separation.')
    try:
        text = json.dumps(payload, indent=2, allow_nan=False)
    except ValueError:
        return _fail('result contains a non-finite number; the inputs are out of range')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
