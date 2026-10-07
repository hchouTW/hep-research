#!/usr/bin/env python3
"""Vertical Stormer geomagnetic cutoff range and average over an inclined LEO orbit.

Purpose: a satellite in an inclined low-Earth orbit (e.g. the ISS at ~51.6 degrees)
crosses a wide range of geomagnetic latitudes every orbit, so a single-latitude
cutoff (<plugin root>/skills/hep-analysis/scripts/geomagnetic_cutoff.py) is not representative of the mission's actual
exposure. This script samples the vertical Stormer cutoff over the geomagnetic
latitude range an orbit of given inclination reaches, and reports the minimum,
maximum, and a time-weighted average. See
the bound experiment profile's instrument overview and <plugin root>/skills/detector-response/references/space-based-direct-detection.md.

What it does: for an orbit of inclination `i` (degrees) the satellite's geographic
(here treated as equal to geomagnetic, for this order-of-magnitude planning estimate -
see the caveat below) latitude oscillates approximately sinusoidally between -i and
+i over one orbit, spending more time near the turning points (+-i) than near the
equator, because latitude rate ~ cos(true anomaly) vanishes at the turning points. The
time-weighted average cutoff is therefore an integral over one quarter-orbit weighted
by dt/d(latitude) = 1/sqrt(1 - (sin(lat)/sin(i))^2)/orbital_rate, evaluated by direct
numerical quadrature (trapezoidal rule on a fine grid) - no closed form is used, since
the Stormer cutoff itself is already a nontrivial function of latitude.

Usage notes / assumptions: standard library only. This treats orbital latitude as
equal to geomagnetic latitude (ignoring the ~10-degree tilt and offset of Earth's
real, non-dipolar magnetic axis from its rotation axis) and assumes a circular orbit -
both are planning-level simplifications. It does NOT replace backtracing a real
satellite ephemeris through a full geomagnetic field model (e.g. IGRF), which is
required for a real mission's actual event-by-event cutoff, per the same caveat
already stated for the single-latitude formula in geomagnetic_cutoff.py.
Run: python3 <plugin root>/skills/hep-analysis/scripts/orbit_averaged_geomagnetic_cutoff.py --inclination 51.6 --altitude-re 1.0627
"""
import argparse
import json
import math

from geomagnetic_cutoff import DEFAULT_DIPOLE_MOMENT_G_CM3, stormer_cutoff_gv


def _finite(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0:
        raise ValueError(f'{name} must be greater than zero')
    return float(value)


def orbit_cutoff_profile(inclination_deg, altitude_re=1.0, dipole_moment_g_cm3=DEFAULT_DIPOLE_MOMENT_G_CM3,
                         n_samples=2000):
    """Time-weighted min/max/average vertical Stormer cutoff over one quarter-orbit
    of an inclined circular orbit, sampled at n_samples points in true anomaly.

    Latitude(theta) = arcsin(sin(inclination) * sin(theta)) for true anomaly theta in
    [0, pi/2] (equator crossing to the northern turning point); by symmetry this
    quarter covers the full latitude range [0, inclination] with the correct time
    weighting once doubled (equator-to-peak and peak-to-equator are mirror images).
    """
    inclination_deg = _finite(inclination_deg, 'inclination_deg')
    if not 0.0 < inclination_deg <= 90.0:
        raise ValueError('inclination_deg must be between 0 (exclusive) and 90 (inclusive)')
    if isinstance(n_samples, bool) or type(n_samples) is not int or n_samples < 10:
        raise ValueError('n_samples must be an integer of at least 10')

    inclination_rad = math.radians(inclination_deg)
    sin_i = math.sin(inclination_rad)

    thetas = [math.pi / 2.0 * k / (n_samples - 1) for k in range(n_samples)]
    latitudes_deg = []
    weights = []
    for theta in thetas:
        lat_rad = math.asin(sin_i * math.sin(theta))
        latitudes_deg.append(math.degrees(lat_rad))
        # d(theta)/dt is constant (uniform angular rate); the time weight per unit
        # theta is therefore uniform in theta, so equal-theta sampling already gives
        # the correct time weighting - no extra Jacobian factor is needed here.
        weights.append(1.0)

    cutoffs = [stormer_cutoff_gv(lat, altitude_re, dipole_moment_g_cm3) for lat in latitudes_deg]

    total_weight = math.fsum(weights)
    weighted_mean = math.fsum(w * c for w, c in zip(weights, cutoffs)) / total_weight

    return {
        'inclination_deg': inclination_deg,
        'altitude_re': altitude_re,
        'latitude_range_deg': [min(latitudes_deg), max(latitudes_deg)],
        'min_cutoff_gv': min(cutoffs),
        'max_cutoff_gv': max(cutoffs),
        'time_weighted_mean_cutoff_gv': weighted_mean,
        'n_samples': n_samples,
        'note': ('latitude treated as geomagnetic latitude (dipole-tilt/offset '
                'ignored); circular orbit assumed; see docstring caveats'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inclination', type=float, required=True, dest='inclination_deg',
                        help='orbital inclination in degrees, 0 (exclusive) to 90')
    parser.add_argument('--altitude-re', type=float, default=1.0,
                        help='geocentric distance in Earth radii (default 1.0)')
    parser.add_argument('--dipole-moment', type=float, default=DEFAULT_DIPOLE_MOMENT_G_CM3,
                        help='dipole moment in G*cm^3 (default: approximate present epoch)')
    parser.add_argument('--n-samples', type=int, default=2000, dest='n_samples',
                        help='number of true-anomaly samples over the quarter-orbit (default 2000)')
    args = parser.parse_args()

    try:
        result = orbit_cutoff_profile(args.inclination_deg, args.altitude_re,
                                      args.dipole_moment, args.n_samples)
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({
        'method': 'time-weighted quadrature over vertical Stormer dipole cutoff along an inclined circular orbit',
        **result,
    }, indent=2))


if __name__ == '__main__':
    main()
