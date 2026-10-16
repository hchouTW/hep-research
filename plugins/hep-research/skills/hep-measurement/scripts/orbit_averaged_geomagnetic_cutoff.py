#!/usr/bin/env python3
"""Vertical Stormer geomagnetic cutoff range and average over an inclined LEO orbit.

Purpose: a satellite in an inclined low-Earth orbit (e.g. the ISS at ~51.6 degrees)
crosses a wide range of geomagnetic latitudes every orbit, so a single-latitude
cutoff (<plugin root>/skills/hep-measurement/scripts/geomagnetic_cutoff.py) is not representative of the mission's actual
exposure. This script samples the vertical Stormer cutoff over the geomagnetic
latitude range an orbit of given inclination reaches, and reports the minimum,
maximum, and a time-weighted average. See
the bound experiment profile's instrument overview and <plugin root>/skills/hep-detector/references/space-based-direct-detection.md.

What it does, two modes:

  untilted (default, labelled "planning estimate"): the orbital latitude is treated as the
    geomagnetic latitude. Latitude(u) = asin(sin(i) sin(u)) over the argument of latitude u;
    u advances uniformly in time on a circular orbit, so equal-u samples are already
    time-weighted (no Jacobian factor) and the mean is a plain average over the samples.
  tilted dipole (--pole-lat and --pole-lon, the geographic coordinates of the geomagnetic
    north pole for the epoch the user takes from IGRF; no default is embedded): the ground
    track of a circular orbit is followed with Earth rotation for --days, the geomagnetic
    latitude is sin(lat_m) = sin(lat) sin(lat_p) + cos(lat) cos(lat_p) cos(lon - lon_p)
    (centred tilted dipole), and the output adds the time fraction spent below each
    --thresholds cutoff and an exposure-versus-cutoff table (time fraction per cutoff bin).

Usage notes / assumptions: standard library only. Both modes assume a circular orbit and a
centred dipole (the tilted mode ignores the dipole offset and higher multipoles), so both are
planning-level estimates. It does NOT replace backtracing a real
satellite ephemeris through a full geomagnetic field model (e.g. IGRF), which is
required for a real mission's actual event-by-event cutoff, per the same caveat
already stated for the single-latitude formula in geomagnetic_cutoff.py.
Status: --status (default unvalidated; one of the core artifact_statuses) is echoed as status.
Exit codes: 0 ok; 1 the computation failed; 2 usage or invalid input (NaN, inf, malformed file);
3 incomplete or inconclusive.
Run: python3 <plugin root>/skills/hep-measurement/scripts/orbit_averaged_geomagnetic_cutoff.py --inclination 51.6 --radius-re 1.0627
     python3 <plugin root>/skills/hep-measurement/scripts/orbit_averaged_geomagnetic_cutoff.py --inclination 51.6 --radius-re 1.065
         --pole-lat <deg N> --pole-lon <deg E> --days 30 --thresholds 1,5,10
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))  # the sibling script, also under python3 -I
from geomagnetic_cutoff import DEFAULT_DIPOLE_MOMENT_G_CM3, STATUSES, stormer_cutoff_gv  # noqa: E402


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
        'mode': 'untilted dipole (planning estimate)',
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


EARTH_GM_M3_S2 = 3.986004418e14  # IERS / WGS84 geocentric gravitational constant
EARTH_RADIUS_M = 6.371e6  # mean radius, the same Earth radius as geomagnetic_cutoff.py
SIDEREAL_DAY_S = 86164.0905


def tilted_dipole_profile(inclination_deg, pole_lat_deg, pole_lon_deg, altitude_re=1.0,
                          dipole_moment_g_cm3=DEFAULT_DIPOLE_MOMENT_G_CM3, days=30.0, step_s=10.0,
                          thresholds_gv=(), ascending_node_deg=0.0):
    """Vertical Stormer cutoff along the ground track of a circular orbit for a centred dipole whose
    north pole sits at (pole_lat_deg, pole_lon_deg) geographic; Earth rotates under the orbit."""
    inclination_deg = _finite(inclination_deg, 'inclination_deg')
    if not 0.0 < inclination_deg <= 180.0:
        raise ValueError('inclination_deg must be between 0 (exclusive) and 180')
    pole_lat_deg = _finite(pole_lat_deg, 'pole_lat_deg')
    pole_lon_deg = _finite(pole_lon_deg, 'pole_lon_deg')
    if not -90.0 <= pole_lat_deg <= 90.0:
        raise ValueError('pole_lat_deg must be between -90 and 90')
    altitude_re = _finite(altitude_re, 'altitude_re', positive=True)
    days = _finite(days, 'days', positive=True)
    step_s = _finite(step_s, 'step_s', positive=True)
    n = int(days * 86400.0 / step_s)
    if n < 10 or n > 5_000_000:
        raise ValueError('days / step_s must give between 10 and 5e6 samples')
    thresholds = sorted(_finite(t, 'threshold', positive=True) for t in thresholds_gv)
    r_m = altitude_re * EARTH_RADIUS_M
    period_s = 2.0 * math.pi * math.sqrt(r_m ** 3 / EARTH_GM_M3_S2)
    omega_orbit, omega_earth = 2.0 * math.pi / period_s, 2.0 * math.pi / SIDEREAL_DAY_S
    inc, node = math.radians(inclination_deg), math.radians(ascending_node_deg)
    plat, plon = math.radians(pole_lat_deg), math.radians(pole_lon_deg)
    cutoffs, mag_lats = [], []
    for k in range(n):
        t = k * step_s
        u = omega_orbit * t
        lat = math.asin(math.sin(inc) * math.sin(u))
        lon = node + math.atan2(math.cos(inc) * math.sin(u), math.cos(u)) - omega_earth * t
        sin_m = math.sin(lat) * math.sin(plat) + math.cos(lat) * math.cos(plat) * math.cos(lon - plon)
        lat_m = math.degrees(math.asin(max(-1.0, min(1.0, sin_m))))
        mag_lats.append(lat_m)
        cutoffs.append(stormer_cutoff_gv(lat_m, altitude_re, dipole_moment_g_cm3))
    edges = [0.0, 0.5, 1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 20]
    table = []
    for lo, hi in zip(edges, edges[1:]):
        frac = sum(1 for c in cutoffs if lo <= c < hi) / n
        table.append({'cutoff_gv': [lo, hi], 'time_fraction': frac})
    return {
        'mode': 'tilted centred dipole along the ground track (planning estimate)',
        'inclination_deg': inclination_deg, 'altitude_re': altitude_re,
        'pole_geographic_deg': [pole_lat_deg, pole_lon_deg], 'days': days, 'step_s': step_s,
        'orbital_period_s': period_s,
        'geomagnetic_latitude_range_deg': [min(mag_lats), max(mag_lats)],
        'min_cutoff_gv': min(cutoffs), 'max_cutoff_gv': max(cutoffs),
        'time_weighted_mean_cutoff_gv': math.fsum(cutoffs) / n,
        'time_fraction_below': [{'cutoff_gv': t, 'fraction': sum(1 for c in cutoffs if c < t) / n} for t in thresholds],
        'exposure_vs_cutoff': table,
        'note': ('centred tilted dipole, vertical Stormer cutoff, circular orbit; the dipole offset, '
                 'non-dipole field and off-vertical arrival are ignored: backtrace through a field model for a real '
                 'selection'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--inclination', type=float, required=True, dest='inclination_deg',
                        help='orbital inclination in degrees, 0 (exclusive) to 90')
    parser.add_argument('--radius-re', type=float, default=None, dest='radius_re',
                        help='orbit radius (geocentric distance) in Earth radii (default 1.0)')
    parser.add_argument('--altitude-re', type=float, default=None, dest='altitude_re',
                        help='deprecated alias of --radius-re (the value is a geocentric distance)')
    parser.add_argument('--dipole-moment', type=float, default=DEFAULT_DIPOLE_MOMENT_G_CM3,
                        help='dipole moment in G*cm^3 (default 8.05e25, the IGRF-14 1955 dipole; 7.69e25 for 2025)')
    parser.add_argument('--n-samples', type=int, default=2000, dest='n_samples',
                        help='number of true-anomaly samples over the quarter-orbit (default 2000, untilted mode)')
    parser.add_argument('--pole-lat', type=float, dest='pole_lat',
                        help='geographic latitude (deg N) of the geomagnetic north pole for the epoch (IGRF); selects the tilted mode')
    parser.add_argument('--pole-lon', type=float, dest='pole_lon',
                        help='geographic longitude (deg E) of the geomagnetic north pole for the epoch (IGRF)')
    parser.add_argument('--days', type=float, default=30.0, help='tilted mode: ground-track duration in days (default 30)')
    parser.add_argument('--step-s', type=float, default=10.0, dest='step_s',
                        help='tilted mode: time step in seconds (default 10)')
    parser.add_argument('--thresholds', default='',
                        help='tilted mode: comma-separated cutoffs in GV for the time fraction below each')
    parser.add_argument('--status', choices=STATUSES, default='unvalidated',
                        help='status label of the inputs, echoed as status (default unvalidated)')
    args = parser.parse_args()

    try:
        if args.radius_re is not None and args.altitude_re is not None:
            raise ValueError('give --radius-re only (--altitude-re is its deprecated alias)')
        if args.altitude_re is not None:
            print('orbit_averaged_geomagnetic_cutoff.py: warning: --altitude-re is deprecated; use --radius-re',
                  file=sys.stderr)
        args.altitude_re = args.radius_re if args.radius_re is not None else (args.altitude_re or 1.0)
        if (args.pole_lat is None) != (args.pole_lon is None):
            raise ValueError('--pole-lat and --pole-lon must be given together')
        if args.pole_lat is not None:
            thresholds = [float(x) for x in args.thresholds.split(',') if x.strip()]
            result = tilted_dipole_profile(args.inclination_deg, args.pole_lat, args.pole_lon, args.altitude_re,
                                           args.dipole_moment, args.days, args.step_s, thresholds)
            method = 'vertical Stormer cutoff along a ground track with Earth rotation, tilted centred dipole'
        else:
            result = orbit_cutoff_profile(args.inclination_deg, args.altitude_re, args.dipole_moment, args.n_samples)
            method = 'time average of the vertical Stormer dipole cutoff along an inclined circular orbit'
    except ValueError as exc:
        parser.error(str(exc))

    print(json.dumps({'status': args.status, 'method': method, **result}, indent=2))


if __name__ == '__main__':
    main()
