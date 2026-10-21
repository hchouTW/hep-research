#!/usr/bin/env python3
"""Multiple-scattering angles and magnetic-spectrometer resolution from a material stack.

Purpose: turn a detector's material description into the numbers that explain its
tracking performance - the Highland RMS scattering angle, the accumulated material
budget, the two competing terms of the rigidity resolution, the rigidity at which they
cross, and the maximum detectable rigidity (MDR).

What it does: sums x/X0 over the layers of a JSON stack description, evaluates the PDG
Highland formula, and combines the multiple-scattering and intrinsic (Gluckstern)
contributions to sigma(R)/R. See <plugin root>/skills/hep-detector/references/detector-systems-overview.md and
<plugin root>/skills/hep-detector/references/tracking-and-vertexing.md for the physics.

Usage notes / assumptions: standard library only. Rigidity/momentum in GV or GeV/c,
field in tesla, lengths in metres, point resolution in micrometres. The Gluckstern
term assumes equally spaced measuring layers and a uniform field over the lever arm;
it is a design-level estimate, not a substitute for a full track fit. PDG states it for many
(N >= 10) points: with fewer measuring layers it overstates the intrinsic term (by 5.4% at
N = 4, 2.4% at N = 8), so the output also gives the exact least-squares coefficient for N
equally spaced points and a warning; tracker_resolution.py fits the actual layer positions. beta: with --mass
or --species (name or mass:charge) it is derived from the rigidity at every R,
beta(R) = zR / sqrt((zR)^2 + m^2), and the crossover and the MDR are solved with beta(R)
(beta_source "derived"); --beta fixes one value for every rigidity (and is refused when it
contradicts the mass); without either, beta = 1 (relativistic). The scattering term grows
as 1/beta for slow particles.
Measuring layers: layers with "measuring": true are the points of the curvature fit; the
flag must be a boolean. With no layer flagged, every layer is used and a warning says so.
MDR: the rigidity where the total sigma(R)/R reaches 1 (mdr_definition); the intrinsic-only
value 1/k is reported as mdr_intrinsic_only_gv.

Validity: the Highland formula is a fit; RPP 2024 Eq. 34.16 gives no numerical accuracy (the beta dependence is poor
for large Z and small x). The range 1e-3 < x/X0 < 100 of total material, quoted in earlier sources but not in RPP 2024,
is kept as an operating guard: outside it the output carries highland_validity.inside = false and a warning.
Resolution-term convention: the scattering term of sigma(R)/R uses
0.0136 GeV * sqrt(x/X0) / (0.3 beta B L), the Highland constant without its log factor,
so the term stays independent of rigidity. The PDG tracking section writes the same term
with 0.016 GeV/c instead; the two differ by about 15%, a convention difference within
the precision of a design estimate. State which coefficient was used when comparing.
Status: --status (default: the input file's "status", else unvalidated; one of the core artifact_statuses) is
echoed as status.
Exit codes: 0 ok; 1 the computation failed or the input file is unreadable or invalid (JSON with ok false);
2 invalid input (JSON with error_kind invalid-input on stdout, the usage on stderr).
Run: python3 <plugin root>/skills/hep-detector/scripts/multiple_scattering.py <plugin root>/skills/hep-detector/assets/detector-stack.example.json --rigidity 100
"""
import argparse
import json
import math
import sys
from pathlib import Path

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': 'invalid-input', 'error': message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: error: {message}\n')


sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pid_separation_power import resolve_species  # noqa: E402

# PDG Highland constant, in GeV; see <plugin root>/skills/hep-citations/references/primary-sources-and-version-checks.md.
HIGHLAND_MEV = 13.6
HIGHLAND_GEV = HIGHLAND_MEV / 1000.0
# p[GeV/c] = 0.299792458 * B[T] * r[m] for unit charge.
FIELD_TO_MOMENTUM = 0.299792458
# Range of total x/X0 over which the Highland fit is quoted (PDG).
HIGHLAND_RANGE = (1e-3, 100.0)


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} must be finite and greater than zero')
    return float(value)


def _validate_beta(beta):
    if isinstance(beta, bool) or not isinstance(beta, (int, float)):
        raise ValueError('beta must be a number')
    if not math.isfinite(beta) or not 0 < beta <= 1:
        raise ValueError('beta must be finite and in the interval (0, 1]')
    return float(beta)


def highland_angle(rigidity_gv, x_over_x0, beta=1.0, charge=1):
    """RMS projected multiple-scattering angle in radians (PDG Highland formula).

    theta0 = (13.6 MeV / (beta * p)) * z * sqrt(x/X0) * [1 + 0.038 * ln(x z^2/(X0 beta^2))]

    The momentum entering the prefactor is p = z * R for a particle of charge number z
    and rigidity R, so the explicit z factors cancel in the prefactor and survive only
    inside the logarithm.
    """
    rigidity_gv = _positive(rigidity_gv, 'rigidity')
    beta = _validate_beta(beta)
    if isinstance(charge, bool) or not isinstance(charge, int) or charge < 1:
        raise ValueError('charge must be a positive integer charge number')
    if isinstance(x_over_x0, bool) or not isinstance(x_over_x0, (int, float)):
        raise ValueError('x_over_x0 must be a number')
    if not math.isfinite(x_over_x0) or x_over_x0 < 0:
        raise ValueError('x_over_x0 must be finite and nonnegative')
    if x_over_x0 == 0:
        return 0.0
    log_argument = x_over_x0 * charge * charge / (beta * beta)
    correction = 1.0 + 0.038 * math.log(log_argument)
    # The logarithmic correction is a fit (range 1e-3 < x/X0 < 100 kept as a guard; not in RPP 2024) and turns
    # negative for very thin layers; clamp at zero rather than return a negative RMS.
    correction = max(correction, 0.0)
    return (HIGHLAND_GEV / (beta * rigidity_gv)) * math.sqrt(x_over_x0) * correction


def scattering_resolution_term(x_over_x0, field_tesla, lever_arm_m, beta=1.0):
    """Multiple-scattering contribution to sigma(R)/R, independent of rigidity.

    0.0136 GeV * sqrt(x/X0) / (0.3 * beta * B * L), the standard spectrometer form
    written with the accumulated budget instead of sqrt(L * X0).
    """
    field_tesla = _positive(field_tesla, 'field_tesla')
    lever_arm_m = _positive(lever_arm_m, 'lever_arm_m')
    beta = _validate_beta(beta)
    if x_over_x0 < 0:
        raise ValueError('x_over_x0 must be nonnegative')
    return (HIGHLAND_GEV * math.sqrt(x_over_x0)
            / (FIELD_TO_MOMENTUM * beta * field_tesla * lever_arm_m))


def intrinsic_resolution_slope(point_resolution_um, n_points, field_tesla, lever_arm_m):
    """Gluckstern coefficient k such that the intrinsic term of sigma(R)/R equals k * R.

    k = sigma_x * sqrt(720 / (N + 4)) / (0.3 * B * L^2)
    """
    sigma_m = _positive(point_resolution_um, 'point_resolution_um') * 1e-6
    field_tesla = _positive(field_tesla, 'field_tesla')
    lever_arm_m = _positive(lever_arm_m, 'lever_arm_m')
    if isinstance(n_points, bool) or not isinstance(n_points, int) or n_points < 3:
        raise ValueError('n_points must be an integer of at least 3 (a curvature fit needs three points)')
    return (sigma_m * math.sqrt(720.0 / (n_points + 4.0))
            / (FIELD_TO_MOMENTUM * field_tesla * lever_arm_m * lever_arm_m))


GLUCKSTERN_MIN_POINTS = 10  # PDG states the Gluckstern measurement term for N >= 10 uniformly spaced points


def exact_equal_spacing_coefficient(n_points):
    """Exact least-squares curvature coefficient for N equally spaced points over the lever arm (sigma_k * L^2 /
    sigma_x), the value that sqrt(720 / (N + 4)) approximates: sqrt(720 (N-1)^3 / ((N-2) N (N+1) (N+2)));
    8 sqrt(3/2) at N = 3."""
    if isinstance(n_points, bool) or not isinstance(n_points, int) or n_points < 3:
        raise ValueError('n_points must be an integer of at least 3 (a curvature fit needs three points)')
    n = n_points
    return math.sqrt(720.0 * (n - 1) ** 3 / ((n - 2) * n * (n + 1) * (n + 2)))


def crossover_rigidity(ms_term, slope):
    """Rigidity where the intrinsic term equals the scattering term."""
    if slope <= 0:
        raise ValueError('intrinsic slope must be greater than zero')
    return ms_term / slope


def maximum_detectable_rigidity(ms_term, slope):
    """Rigidity where the total sigma(R)/R reaches 1. None if scattering alone exceeds 1."""
    if ms_term >= 1.0:
        return None
    return math.sqrt(1.0 - ms_term * ms_term) / slope


def resolution_at(rigidity_gv, ms_term, slope):
    """Total sigma(R)/R = sqrt(ms^2 + (k R)^2)."""
    rigidity_gv = _positive(rigidity_gv, 'rigidity')
    return math.hypot(ms_term, slope * rigidity_gv)


def beta_of_rigidity(rigidity_gv, mass_gev, charge=1):
    """beta = zR / sqrt((zR)^2 + m^2) for rigidity R (GV), mass m (GeV/c^2) and charge number z."""
    momentum = charge * _positive(rigidity_gv, 'rigidity')
    return momentum / math.hypot(momentum, _positive(mass_gev, 'mass'))


def _bisect_log(f, low, high, iterations=200):
    """Root of f on [low, high] (f(low) and f(high) of opposite sign), bisected in log R."""
    f_low = f(low)
    for _ in range(iterations):
        mid = math.sqrt(low * high)
        if mid in (low, high):
            break
        f_mid = f(mid)
        if (f_mid > 0) == (f_low > 0):
            low, f_low = mid, f_mid
        else:
            high = mid
    return math.sqrt(low * high)


def crossover_with_beta(ms1, slope, beta_of, low=1e-6, high=1e9):
    """Rigidity where ms1/beta(R) = k R; ms1/beta(R) - k R decreases monotonically in R."""
    def f(rigidity):
        return ms1 / beta_of(rigidity) - slope * rigidity
    if f(low) <= 0 or f(high) >= 0:
        return None
    return _bisect_log(f, low, high)


def mdr_with_beta(ms1, slope, beta_of, high=1e12):
    """Upper rigidity where hypot(ms1/beta(R), k R) = 1; None when the resolution never gets below 1."""
    if ms1 >= 1.0:
        return None

    def g(rigidity):
        return math.hypot(ms1 / beta_of(rigidity), slope * rigidity) - 1.0
    start = math.sqrt(1.0 - ms1 * ms1) / slope  # the beta = 1 value; beta(R) <= 1 puts the root at or below it
    if g(start) < 0:
        return _bisect_log(g, start, high) if g(high) > 0 else None
    low = start
    for _ in range(400):
        low /= 2.0
        if g(low) < 0:
            return _bisect_log(g, low, start)
    return None


def load_stack(path):
    with open(path, encoding='utf-8') as handle:
        stack = json.load(handle)
    if not isinstance(stack, dict):
        raise ValueError('stack file must contain a JSON object')
    for field in ('field_tesla', 'lever_arm_m', 'point_resolution_um', 'layers'):
        if field not in stack:
            raise ValueError(f'stack file is missing required field {field!r}')
    layers = stack['layers']
    if not isinstance(layers, list) or not layers:
        raise ValueError('layers must be a non-empty list')
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict) or 'x_over_x0' not in layer:
            raise ValueError(f'layer {index} must be an object with an x_over_x0 field')
        if not isinstance(layer['x_over_x0'], (int, float)) or isinstance(layer['x_over_x0'], bool):
            raise ValueError(f'layer {index} x_over_x0 must be a number')
        if not math.isfinite(layer['x_over_x0']) or layer['x_over_x0'] < 0:
            raise ValueError(f'layer {index} x_over_x0 must be finite and nonnegative')
        if 'measuring' in layer and not isinstance(layer['measuring'], bool):
            raise ValueError(f'layer {index} measuring must be true or false, not {layer["measuring"]!r}')
    return stack


def highland_validity(x_over_x0):
    """Whether a total material budget is inside the range the Highland fit covers."""
    low, high = HIGHLAND_RANGE
    return {'range_x_over_x0': [low, high], 'inside': low <= x_over_x0 <= high}


def summarize(stack, rigidity_gv, beta=1.0, charge=1, mass_gev=None, beta_source=None):
    """Material budget, resolution terms, crossover and MDR. With mass_gev, beta is derived from the rigidity at
    every R (beta argument ignored); otherwise beta is the same at every rigidity."""
    layers = stack['layers']
    try:
        total_budget = math.fsum(layer['x_over_x0'] for layer in layers)
    except OverflowError:
        raise ValueError('the summed x/X0 overflows; the layer budgets are not physical') from None
    measuring = [layer for layer in layers if layer.get('measuring', False)]
    n_points = len(measuring) if measuring else len(layers)

    if mass_gev is not None:
        def beta_of(rigidity):
            return beta_of_rigidity(rigidity, mass_gev, charge)
        beta = beta_of(rigidity_gv)
        beta_source = beta_source or 'derived from rigidity, charge and mass'
    else:
        beta = _validate_beta(beta)

        def beta_of(rigidity):
            return beta
        beta_source = beta_source or ('fixed: assumed at every rigidity' if beta != 1.0
                                      else 'default 1 (relativistic)')
    ms1 = scattering_resolution_term(total_budget, stack['field_tesla'], stack['lever_arm_m'], 1.0)
    ms_term = ms1 / beta
    slope = intrinsic_resolution_slope(
        stack['point_resolution_um'], n_points, stack['field_tesla'], stack['lever_arm_m'])
    if mass_gev is None:
        crossover = crossover_rigidity(ms_term, slope)
        mdr = maximum_detectable_rigidity(ms_term, slope)
    else:
        crossover = crossover_with_beta(ms1, slope, beta_of)
        mdr = mdr_with_beta(ms1, slope, beta_of)
    validity = highland_validity(total_budget)
    warnings = []
    if not measuring:
        warnings.append(f'no layer is marked measuring: all {len(layers)} layers, passive ones included, are used '
                        'as measuring points')
    exact = exact_equal_spacing_coefficient(n_points)
    gluckstern = math.sqrt(720.0 / (n_points + 4.0))
    if n_points < GLUCKSTERN_MIN_POINTS:
        warnings.append(
            f'{n_points} measuring layers: the Gluckstern term (stated for N >= {GLUCKSTERN_MIN_POINTS}) overstates the '
            f'intrinsic term by {100 * (gluckstern / exact - 1):.1f}% against the exact fit of {n_points} equally spaced '
            'points (intrinsic_coefficient); for the actual layer positions use tracker_resolution.py momentum')
    if not validity['inside']:
        warnings.append(
            f'total x/X0 = {total_budget:.4g} is outside the Highland range '
            f'{HIGHLAND_RANGE[0]:g}-{HIGHLAND_RANGE[1]:g}; the scattering angle and the '
            'scattering term are extrapolations')

    return {
        'name': stack.get('name'),
        'layers': len(layers),
        'measuring_layers': n_points,
        'total_x_over_x0': total_budget,
        'highland_validity': validity,
        'beta': beta,
        'beta_source': beta_source,
        'mass_gev': mass_gev,
        'charge_number': charge,
        'scattering_angle_rad': highland_angle(rigidity_gv, total_budget, beta, charge),
        'rigidity_gv': rigidity_gv,
        'scattering_term': ms_term,
        'intrinsic_term': slope * rigidity_gv,
        'intrinsic_coefficient': {'gluckstern': gluckstern, 'exact_equal_spacing': exact,
                                  'exact_over_gluckstern_variance': (exact / gluckstern) ** 2,
                                  'used': 'gluckstern'},
        'total_relative_resolution': resolution_at(rigidity_gv, ms_term, slope),
        'dominant_term': 'scattering' if ms_term > slope * rigidity_gv else 'intrinsic',
        'crossover_rigidity_gv': crossover,
        'maximum_detectable_rigidity_gv': mdr,
        'mdr_definition': 'rigidity where the total sigma(R)/R reaches 1 (scattering and intrinsic terms)',
        'mdr_intrinsic_only_gv': 1.0 / slope,
        'warnings': warnings,
    }


def _resolve_status(given, document):
    """--status when given, else the input file's 'status' (checked against STATUSES), else unvalidated."""
    if given:
        return given
    status = document.get('status') if isinstance(document, dict) else None
    if status is None:
        return 'unvalidated'
    if status not in STATUSES:
        raise ValueError(f'input status {status!r} is not one of {list(STATUSES)}')
    return status


def _fail(message, kind='failed'):
    print(json.dumps({'status': 'failed', 'ok': False, 'error_kind': kind, 'error': message}, indent=2))
    print(f'multiple_scattering.py: error: {message}', file=sys.stderr)
    return 1


def main():
    parser = JsonArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stack', help='JSON stack description (see <plugin root>/skills/hep-detector/assets/detector-stack.example.json)')
    parser.add_argument('--rigidity', type=float, default=100.0,
                        help='rigidity in GV at which to evaluate the resolution (default 100)')
    parser.add_argument('--beta', type=float, default=None,
                        help='particle beta, the same at every rigidity (default 1, or derived with --mass)')
    parser.add_argument('--charge', type=int, default=None, help='charge number z (default 1)')
    particle = parser.add_mutually_exclusive_group()
    particle.add_argument('--mass', type=float, default=None,
                          help='particle mass in GeV/c^2: beta is derived from the rigidity')
    particle.add_argument('--species', default=None,
                          help='a name (p, He4, ...) or mass:charge: sets the mass and the charge number')
    parser.add_argument('--status', choices=STATUSES, default=None,
                        help="status label of the inputs, echoed as status (default: the input file's status, "
                             'else unvalidated)')
    args = parser.parse_args()
    try:
        _positive(args.rigidity, 'rigidity')
        charge, mass = (1 if args.charge is None else args.charge), args.mass
        if args.species is not None:
            mass, species_charge = resolve_species(args.species)
            if args.charge is not None and args.charge != species_charge:
                raise ValueError(f'--charge {args.charge} contradicts the charge {species_charge} of --species')
            charge = species_charge
        if charge < 1:
            raise ValueError('charge must be a positive integer charge number')
        beta = 1.0 if args.beta is None else _validate_beta(args.beta)
        if mass is not None:
            _positive(mass, 'mass')
            derived = beta_of_rigidity(args.rigidity, mass, charge)
            if args.beta is not None and abs(args.beta - derived) > 1e-6 * derived:
                raise ValueError(f'--beta {args.beta:g} conflicts with beta {derived:.6g} from the rigidity, charge and '
                                 'mass; give one or the other')
    except ValueError as exc:
        parser.error(str(exc))
    try:
        stack = load_stack(args.stack)
        status = _resolve_status(args.status, stack)
        result = summarize(stack, args.rigidity, beta, charge, mass_gev=mass)
    except (OSError, ValueError, TypeError, OverflowError, ZeroDivisionError) as exc:
        return _fail(str(exc))
    try:
        text = json.dumps({
            'status': status,
            'method': 'PDG Highland scattering with Gluckstern intrinsic term',
            **result,
            'note': ('Design-level estimate assuming equally spaced measuring layers and a '
                     'uniform field; it does not replace a full track fit.'),
        }, indent=2, allow_nan=False)
    except ValueError:
        return _fail('result contains a non-finite number; the inputs are outside the range '
                     'where this estimate is representable in floating point')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
