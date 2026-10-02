#!/usr/bin/env python3
"""Multiple-scattering angles and magnetic-spectrometer resolution from a material stack.

Purpose: turn a detector's material description into the numbers that explain its
tracking performance - the Highland RMS scattering angle, the accumulated material
budget, the two competing terms of the rigidity resolution, the rigidity at which they
cross, and the maximum detectable rigidity (MDR).

What it does: sums x/X0 over the layers of a JSON stack description, evaluates the PDG
Highland formula, and combines the multiple-scattering and intrinsic (Gluckstern)
contributions to sigma(R)/R. See ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/21-detector-systems-overview.md and
${CLAUDE_PLUGIN_ROOT}/skills/detector-response/references/22-tracking-and-vertexing.md for the physics.

Usage notes / assumptions: standard library only. Rigidity/momentum in GV or GeV/c,
field in tesla, lengths in metres, point resolution in micrometres. The Gluckstern
term assumes equally spaced measuring layers and a uniform field over the lever arm;
it is a design-level estimate, not a substitute for a full track fit. beta defaults to
1 (relativistic); pass --beta for slow particles, where the scattering term grows.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/detector-response/scripts/multiple_scattering.py ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/detector_stack.example.json --rigidity 100
"""
import argparse
import json
import math

# PDG Highland constant, in GeV; see ${CLAUDE_PLUGIN_ROOT}/skills/research-communication/references/13-sources.md.
HIGHLAND_MEV = 13.6
HIGHLAND_GEV = HIGHLAND_MEV / 1000.0
# p[GeV/c] = 0.299792458 * B[T] * r[m] for unit charge.
FIELD_TO_MOMENTUM = 0.299792458


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
    # The logarithmic correction is a fit valid for 1e-3 < x/X0 < 100 and turns
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
    return stack


def summarize(stack, rigidity_gv, beta=1.0, charge=1):
    layers = stack['layers']
    total_budget = math.fsum(layer['x_over_x0'] for layer in layers)
    measuring = [layer for layer in layers if layer.get('measuring', False)]
    n_points = len(measuring) if measuring else len(layers)

    ms_term = scattering_resolution_term(
        total_budget, stack['field_tesla'], stack['lever_arm_m'], beta)
    slope = intrinsic_resolution_slope(
        stack['point_resolution_um'], n_points, stack['field_tesla'], stack['lever_arm_m'])
    mdr = maximum_detectable_rigidity(ms_term, slope)

    return {
        'name': stack.get('name'),
        'layers': len(layers),
        'measuring_layers': n_points,
        'total_x_over_x0': total_budget,
        'beta': beta,
        'charge_number': charge,
        'scattering_angle_rad': highland_angle(rigidity_gv, total_budget, beta, charge),
        'rigidity_gv': rigidity_gv,
        'scattering_term': ms_term,
        'intrinsic_term': slope * rigidity_gv,
        'total_relative_resolution': resolution_at(rigidity_gv, ms_term, slope),
        'dominant_term': 'scattering' if ms_term > slope * rigidity_gv else 'intrinsic',
        'crossover_rigidity_gv': crossover_rigidity(ms_term, slope),
        'maximum_detectable_rigidity_gv': mdr,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stack', help='JSON stack description (see ${CLAUDE_PLUGIN_ROOT}/skills/hep-analysis/templates/detector_stack.example.json)')
    parser.add_argument('--rigidity', type=float, default=100.0,
                        help='rigidity in GV at which to evaluate the resolution (default 100)')
    parser.add_argument('--beta', type=float, default=1.0, help='particle beta (default 1)')
    parser.add_argument('--charge', type=int, default=1, help='charge number z (default 1)')
    args = parser.parse_args()
    try:
        stack = load_stack(args.stack)
        result = summarize(stack, args.rigidity, args.beta, args.charge)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps({
        'method': 'PDG Highland scattering with Gluckstern intrinsic term',
        **result,
        'note': ('Design-level estimate assuming equally spaced measuring layers and a '
                 'uniform field; it does not replace a full track fit.'),
    }, indent=2))


if __name__ == '__main__':
    main()
