#!/usr/bin/env python3
"""Scoring side of T09, D3 stage 2: an independently written evaluation of the T09 likelihood, for t04-values-v4.md section 9.3's
likelihood check ("Coded likelihood agrees with an independently written evaluation, within 1e-9 ... Sum-to-1 alone could pass by
construction"). Case O-independent of the D3 stage 2 report.

It shares no code with the recipe light_recipe: it imports only the standard library (math, and json, sys, argparse for its
command line), never NumPy, SciPy or light_recipe, and reads no configuration file. Its constants below are written from the text
of section 4.3; its Fibonacci lattice, light model, Poisson-Gaussian charge model, normal tail, sum windows and time term are its
own. The time term takes another form than the recipe's: the first of n arrivals (order statistic), summed over the count,

    p(q, t, hit) = sum_{n>=1} Pois(n; m) N(q; n, 0.3^2 n) n f(t) (1 - F(t))^(n-1),

with f, F the normalised mixture of the channel's arrivals (signal mu_s Gaussian 1.5 ns about t0 + d/0.22, dark 0.002 uniform on
[0, 200) ns), m = mu_s + 0.002; a saturated channel uses P(Q_n >= C) in place of the density; an unhit live channel
P(no hit) = e^-m + sum_{n>=1} Pois(n; m) P(Q_n < 0.25); dead and disabled channels do not enter. The recipe uses the Poisson-process
form lambda e^{-Lambda_<} sum_k Pois(k; Lambda_>) w_{k+1}, algebraically identical.

States are light-readout/1's codes: 0 live-unhit, 1 live-hit, 2 dead, 3 disabled.
Usage (for a look by hand): t09_independent_likelihood.py --point JSON --event JSON; prints ln L, joint and charge-only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

# t04-values-v4.md section 4.3, written here from the text
R_S = 5.0                 # m
SENSORS = 1000
AREA = 0.094              # m2
SPEED = 0.22              # m / ns
ATTENUATION = 30.0        # m
F_EMIT, K_EMIT = 0.6, 5.0
DARK = 0.002              # per channel per window
WINDOW = 200.0            # ns
SIGMA_T = 1.5             # ns, per photon
Q_MEAN, Q_SIGMA = 1.0, 0.3
THRESHOLD = 0.25
UNHIT, HIT, DEAD, DISABLED = 0, 1, 2, 3
LOG_ROOT_TWO_PI = 0.5 * math.log(2.0 * math.pi)
NEG_INF = -math.inf


def lattice(count=SENSORS):
    """[(position, outward normal)] of the Fibonacci lattice: polar arccos(1 - 2(i + 0.5)/N), azimuth pi (1 + sqrt 5)(i + 0.5)."""
    out = []
    for i in range(count):
        polar = math.acos(1.0 - 2.0 * (i + 0.5) / count)
        azimuth = math.pi * (1.0 + math.sqrt(5.0)) * (i + 0.5)
        n = (math.sin(polar) * math.cos(azimuth), math.sin(polar) * math.sin(azimuth), math.cos(polar))
        out.append((tuple(R_S * c for c in n), n))
    return out


SENSOR_LIST = lattice()


def emission(c):
    return (1.0 - F_EMIT) / (4.0 * math.pi) + F_EMIT * K_EMIT * math.exp(K_EMIT * c) / (4.0 * math.pi * math.sinh(K_EMIT))


def expected(sensors, vertex, direction, e_vis):
    """Per sensor: (mu_s, distance), mu_s = 1000 E_vis A cos(incidence)/d^2 exp(-d/30) g(c)."""
    norm = math.sqrt(sum(c * c for c in direction))
    direction = [c / norm for c in direction]
    out = []
    for position, normal in sensors:
        r = [position[k] - vertex[k] for k in range(3)]
        dist = math.sqrt(sum(c * c for c in r))
        u = [c / dist for c in r]
        cos_inc = sum(u[k] * normal[k] for k in range(3))
        c = sum(u[k] * direction[k] for k in range(3))
        shape = AREA * cos_inc / (dist * dist) * math.exp(-dist / ATTENUATION) * emission(c)
        out.append((SENSORS * e_vis * shape, dist))
    return out


def log_add(a, b):
    if a == NEG_INF:
        return b
    if b == NEG_INF:
        return a
    hi, lo = (a, b) if a >= b else (b, a)
    return hi + math.log1p(math.exp(lo - hi))


def log_sum(values):
    top = max(values)
    if top == NEG_INF:
        return NEG_INF
    return top + math.log(sum(math.exp(v - top) for v in values))


def log_tail(z):
    """ln P(Z >= z), standard normal: erfc below z = 5; above, -z^2/2 - ln sqrt(2 pi) - ln of the continued fraction of the
    inverse Mills ratio, z + 1/(z + 2/(z + 3/(z + ...)))."""
    if z < 5.0:
        return math.log(0.5 * math.erfc(z / math.sqrt(2.0)))
    fraction = z
    for k in range(300, 0, -1):
        fraction = z + k / fraction
    return -0.5 * z * z - LOG_ROOT_TWO_PI - math.log(fraction)


def log_poisson(n, m):
    return n * math.log(m) - m - math.lgamma(n + 1.0)


def count_range(m, centre):
    """Photon counts n >= 1 to sum over: wide around m and the charge centre, 40 sqrt + 100 beyond them."""
    lo, hi = min(m, centre), max(m, centre)
    reach = 40.0 * math.sqrt(max(hi, 1.0)) + 100.0
    return range(max(1, int(lo - reach)), int(hi + reach) + 1)


def charge_log_weight(n, q=None, level=None):
    """ln N(q; n, 0.09 n) (density per unit charge) or ln P(Q_n >= level)."""
    s = Q_SIGMA * math.sqrt(n)
    if level is not None:
        return log_tail((level - n * Q_MEAN) / s)
    z = (q - n * Q_MEAN) / s
    return -0.5 * z * z - math.log(s) - LOG_ROOT_TWO_PI


def log_no_hit(m):
    terms = [-m]
    for n in count_range(m, 0.0):
        terms.append(log_poisson(n, m) + log_tail((n * Q_MEAN - THRESHOLD) / (Q_SIGMA * math.sqrt(n))))   # P(Q_n < T)
    return log_sum(terms)


def log_charge_term(m, q=None, level=None):
    """ln f(q | m) of a hit, or ln P(q >= level | m) of a saturated channel: the charge-only terms."""
    terms = [log_poisson(n, m) + charge_log_weight(n, q, level) for n in count_range(m, q if level is None else level)]
    return log_sum(terms)


def arrival(t, mu_s, delay_centre):
    """(ln f(t), ln (1 - F(t))) of the normalised arrival mixture of one channel."""
    m = mu_s + DARK
    z = (t - delay_centre) / SIGMA_T
    ln_signal_rate = math.log(mu_s) - 0.5 * z * z - math.log(SIGMA_T) - LOG_ROOT_TWO_PI
    ln_dark_rate = math.log(DARK / WINDOW) if 0.0 <= t < WINDOW else NEG_INF
    ln_f = log_add(ln_signal_rate, ln_dark_rate) - math.log(m)
    ln_signal_after = math.log(mu_s) + log_tail(z)
    remaining = WINDOW - min(max(t, 0.0), WINDOW)
    ln_dark_after = math.log(DARK * remaining / WINDOW) if remaining > 0.0 else NEG_INF
    return ln_f, log_add(ln_signal_after, ln_dark_after) - math.log(m)


def log_joint_term(t, mu_s, delay_centre, q=None, level=None):
    m = mu_s + DARK
    ln_f, ln_s = arrival(t, mu_s, delay_centre)
    centre = q if level is None else level
    terms = [log_poisson(n, m) + charge_log_weight(n, q, level) + math.log(n) + ln_f + (n - 1) * ln_s
             for n in count_range(m, centre)]
    return log_sum(terms)


def evaluate(states, charges, times, saturated, saturation_charge, vertex, direction, e_vis, t0, sensors=None):
    """ln L at one point: {"joint", "charge_only", "joint_terms", "charge_terms"}, the per-channel terms as lists (0.0 for dead
    and disabled channels)."""
    sensors = SENSOR_LIST if sensors is None else sensors
    if len(states) != len(sensors):
        raise ValueError(f"{len(states)} channels, {len(sensors)} sensors")
    joint_terms, charge_terms = [], []
    for i, ((mu_s, dist), state) in enumerate(zip(expected(sensors, vertex, direction, e_vis), states)):
        m = mu_s + DARK
        if state == UNHIT:
            value = log_no_hit(m)
            joint_terms.append(value)
            charge_terms.append(value)
        elif state == HIT:
            centre = t0 + dist / SPEED
            if saturated[i]:
                joint_terms.append(log_joint_term(times[i], mu_s, centre, level=saturation_charge))
                charge_terms.append(log_charge_term(m, level=saturation_charge))
            else:
                joint_terms.append(log_joint_term(times[i], mu_s, centre, q=charges[i]))
                charge_terms.append(log_charge_term(m, q=charges[i]))
        elif state in (DEAD, DISABLED):
            joint_terms.append(0.0)
            charge_terms.append(0.0)
        else:
            raise ValueError(f"channel {i}: unknown state {state!r}")
    return {"joint": math.fsum(joint_terms), "charge_only": math.fsum(charge_terms), "joint_terms": joint_terms,
            "charge_terms": charge_terms}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--point", required=True, help='JSON {"vertex", "direction", "e_vis", "t0"}')
    ap.add_argument("--event", required=True, help='JSON {"states", "charges", "times", "saturated", "saturation_charge"}')
    args = ap.parse_args(argv)
    try:
        point, event = json.loads(args.point), json.loads(args.event)
        out = evaluate(event["states"], event["charges"], event["times"], event["saturated"], event["saturation_charge"],
                       point["vertex"], point["direction"], point["e_vis"], point["t0"])
    except (ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2
    print(json.dumps({"status": "ok", "joint": out["joint"], "charge_only": out["charge_only"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
