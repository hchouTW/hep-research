#!/usr/bin/env python3
"""Species separation power for time-of-flight, ionization, and velocity-based PID.

Purpose: answer the question every particle-identification system must answer - up to
what momentum can these two species actually be told apart, and by how many sigma at a
given momentum. The dominant effect is that mass resolution degrades as gamma^2 times
the velocity resolution, so every velocity-based technique has a momentum ceiling.

What it does: for two species at a given momentum it reports beta, gamma, the mass
resolution implied by the measurement, and the separation in sigma, then scans momentum
to locate the ceiling where separation falls below a requested threshold. Three modes:
  tof      - separation from the flight-time difference over a known path
  dedx     - separation from mean Bethe-Bloch ionization loss in a named material
  velocity - separation from a directly supplied relative velocity resolution
             (use this for a RICH; ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/cherenkov_angle.py derives that input)

Usage notes / assumptions: standard library only. Momenta in GeV/c, masses in GeV/c^2,
flight path in metres, timing resolution in picoseconds. Separation is quoted as
|difference of means| / sigma of the single measurement (not divided by sqrt(2)); state
the convention when comparing against another source. The Bethe-Bloch evaluation omits
the density-effect correction, which suppresses the relativistic rise - dedx-mode
numbers above the ionization minimum are therefore optimistic and are flagged as such.
See ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/particle-identification.md.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/pid_separation_power.py --mode tof --species pi K --momentum 2.0 --path 1.2 --time-resolution 60
"""
import argparse
import json
import math

# Masses in GeV/c^2 (PDG); see ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/references/primary-sources-and-version-checks.md.
MASSES_GEV = {
    'e': 0.00051099895,
    'mu': 0.1056583755,
    'pi': 0.13957039,
    'K': 0.493677,
    'p': 0.93827209,
    'd': 1.87561294,
    'He3': 2.80839160,
    'He4': 3.72737940,
}

C_M_PER_S = 299792458.0
ELECTRON_MASS_MEV = 0.51099895
# Bethe-Bloch coefficient, MeV mol^-1 cm^2.
BETHE_K = 0.307075

# (Z/A, mean excitation energy I in eV) for a few common detector materials.
MATERIALS = {
    'silicon': (0.49848, 173.0),
    'argon': (0.45059, 188.0),
    'xenon': (0.41129, 482.0),
    'neon': (0.49555, 137.0),
    'water': (0.55508, 75.0),
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
    dict flags when the evaluation is in that region.
    """
    if material not in MATERIALS:
        raise ValueError(f'unknown material {material!r}; use one of {sorted(MATERIALS)}')
    if isinstance(charge, bool) or not isinstance(charge, int) or charge < 1:
        raise ValueError('charge must be a positive integer charge number')
    z_over_a, excitation_ev = MATERIALS[material]
    kin = kinematics(momentum_gev, mass_gev)
    beta, gamma = kin['beta'], kin['gamma']
    mass_mev = mass_gev * 1000.0
    mass_ratio = ELECTRON_MASS_MEV / mass_mev
    t_max_mev = (2.0 * ELECTRON_MASS_MEV * beta * beta * gamma * gamma
                 / (1.0 + 2.0 * gamma * mass_ratio + mass_ratio * mass_ratio))
    excitation_mev = excitation_ev * 1e-6
    log_term = math.log(2.0 * ELECTRON_MASS_MEV * beta * beta * gamma * gamma
                        * t_max_mev / (excitation_mev * excitation_mev))
    loss = (BETHE_K * charge * charge * z_over_a / (beta * beta)
            * (0.5 * log_term - beta * beta))
    return {
        'mev_per_g_cm2': loss,
        'beta_gamma': kin['beta_gamma'],
        'density_effect_omitted': True,
        'in_relativistic_rise': kin['beta_gamma'] > 4.0,
    }


def separation(mode, mass_a, mass_b, momentum_gev, **options):
    """Separation in sigma between two species at one momentum, for the chosen mode."""
    kin_a = kinematics(momentum_gev, mass_a)
    kin_b = kinematics(momentum_gev, mass_b)

    if mode == 'tof':
        path_m = options['path_m']
        time_resolution_ps = _positive(options['time_resolution_ps'], 'time_resolution')
        time_a = time_of_flight_ns(momentum_gev, mass_a, path_m)
        time_b = time_of_flight_ns(momentum_gev, mass_b, path_m)
        difference_ps = abs(time_a - time_b) * 1000.0
        n_sigma = difference_ps / time_resolution_ps
        observable = {'time_a_ns': time_a, 'time_b_ns': time_b,
                      'time_difference_ps': difference_ps}
        beta_resolution = tof_beta_resolution(momentum_gev, mass_a, path_m,
                                              time_resolution_ps)
    elif mode == 'dedx':
        material = options.get('material', 'silicon')
        relative = _positive(options['relative_resolution'], 'relative_resolution')
        loss_a = bethe_bloch_mev_per_g_cm2(momentum_gev, mass_a, material)
        loss_b = bethe_bloch_mev_per_g_cm2(momentum_gev, mass_b, material)
        sigma = relative * loss_a['mev_per_g_cm2']
        n_sigma = abs(loss_a['mev_per_g_cm2'] - loss_b['mev_per_g_cm2']) / sigma
        observable = {'dedx_a_mev_per_g_cm2': loss_a['mev_per_g_cm2'],
                      'dedx_b_mev_per_g_cm2': loss_b['mev_per_g_cm2'],
                      'material': material,
                      'density_effect_omitted': True,
                      'in_relativistic_rise': loss_a['in_relativistic_rise']}
        beta_resolution = None
    elif mode == 'velocity':
        beta_resolution = _positive(options['relative_beta_resolution'],
                                    'relative_beta_resolution')
        sigma_beta = beta_resolution * kin_a['beta']
        n_sigma = abs(kin_a['beta'] - kin_b['beta']) / sigma_beta
        observable = {'beta_difference': abs(kin_a['beta'] - kin_b['beta']),
                      'sigma_beta': sigma_beta}
    else:
        raise ValueError("mode must be one of 'tof', 'dedx', 'velocity'")

    result = {
        'mode': mode,
        'momentum_gev': momentum_gev,
        'species_a': {'mass_gev': mass_a, **kin_a},
        'species_b': {'mass_gev': mass_b, **kin_b},
        'observable': observable,
        'n_sigma': n_sigma,
    }
    if beta_resolution is not None:
        result['relative_beta_resolution'] = beta_resolution
        result['species_a']['mass_resolution'] = mass_resolution(
            momentum_gev, mass_a, beta_resolution)
    return result


def separation_ceiling(mode, mass_a, mass_b, threshold_sigma=3.0,
                       low_gev=0.05, high_gev=1000.0, **options):
    """Highest momentum at which separation still reaches threshold_sigma.

    Separation is monotonically falling in momentum for these modes above the
    ionization minimum, so a bisection is valid once the bracket is confirmed.
    """
    threshold_sigma = _positive(threshold_sigma, 'threshold_sigma')
    if separation(mode, mass_a, mass_b, low_gev, **options)['n_sigma'] < threshold_sigma:
        return None
    if separation(mode, mass_a, mass_b, high_gev, **options)['n_sigma'] >= threshold_sigma:
        return high_gev
    for _ in range(200):
        mid = math.sqrt(low_gev * high_gev)
        if separation(mode, mass_a, mass_b, mid, **options)['n_sigma'] >= threshold_sigma:
            low_gev = mid
        else:
            high_gev = mid
    return low_gev


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=('tof', 'dedx', 'velocity'), required=True)
    parser.add_argument('--species', nargs=2, required=True, metavar=('A', 'B'),
                        help=f'two of {sorted(MASSES_GEV)}, or masses in GeV/c^2')
    parser.add_argument('--momentum', type=float, default=2.0, help='GeV/c (default 2)')
    parser.add_argument('--path', type=float, default=1.0, help='tof: flight path in m')
    parser.add_argument('--time-resolution', type=float, default=60.0,
                        dest='time_resolution', help='tof: timing resolution in ps')
    parser.add_argument('--material', default='silicon',
                        choices=sorted(MATERIALS), help='dedx: absorber material')
    parser.add_argument('--relative-resolution', type=float, default=0.06,
                        dest='relative_resolution', help='dedx: relative dE/dx resolution')
    parser.add_argument('--beta-resolution', type=float, default=1e-3,
                        dest='beta_resolution', help='velocity: relative dbeta/beta')
    parser.add_argument('--threshold', type=float, default=3.0,
                        help='separation in sigma required at the ceiling (default 3)')
    args = parser.parse_args()

    options = {'path_m': args.path, 'time_resolution_ps': args.time_resolution,
               'material': args.material, 'relative_resolution': args.relative_resolution,
               'relative_beta_resolution': args.beta_resolution}
    try:
        mass_a = resolve_mass(args.species[0])
        mass_b = resolve_mass(args.species[1])
        if mass_a == mass_b:
            raise ValueError('the two species must have different masses')
        result = separation(args.mode, mass_a, mass_b, args.momentum, **options)
        result['species_a']['name'] = args.species[0]
        result['species_b']['name'] = args.species[1]
        result['threshold_sigma'] = args.threshold
        result['separation_ceiling_gev'] = separation_ceiling(
            args.mode, mass_a, mass_b, args.threshold, **options)
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))

    print(json.dumps({
        **result,
        'note': ('Separation is |difference of means| / sigma of one measurement. '
                 'Above the ceiling the two species are not resolved by this technique '
                 'alone.'),
    }, indent=2))


if __name__ == '__main__':
    main()
