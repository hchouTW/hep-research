#!/usr/bin/env python3
"""Combine results with asymmetric uncertainties by Barlow's methods.

Subcommands:
  measurements  Several measurements x_i (+sigma+_i, -sigma-_i) of one quantity, assumed independent. Each enters as an
                approximate log-likelihood that is -1/2 at x_i + sigma+_i and at x_i - sigma-_i (R. Barlow, "Asymmetric
                statistical errors", physics/0406120):
                  linear_variance (default): ln L = -1/2 (x - x_i)^2 / (s+ s- + (s+ - s-)(x - x_i))
                  linear_sigma:              ln L = -1/2 ((x - x_i) / (s + s' (x - x_i)))^2,
                                             s = 2 s+ s- / (s+ + s-), s' = (s+ - s-) / (s+ + s-)
                The sum is maximized; the combined errors are where it falls by 1/2. Also reported: -2 ln L at the
                maximum as a consistency chi-square with n - 1 degrees of freedom (approximate, like the likelihoods).
                Symmetric errors give the weighted mean exactly.
  sources       One result with several independent sources of asymmetric uncertainty, each given by the signed
                shifts of the result when its nuisance goes to +1 and -1 sigma ("up", "down"). Each source is a
                function f(nu) of a unit Gaussian nu (R. Barlow, "Asymmetric systematic errors", physics/0306138):
                  quadratic (default): f = a nu + b nu^2, a = (up - down)/2, b = (up + down)/2
                  piecewise:           f = up nu for nu > 0, -down nu for nu < 0 (two half-Gaussians)
                The cumulants (mean, variance, third cumulant) of the sources add; the total is described again by
                the same model, matched in variance and third cumulant, and the central value moves so that the
                mean is kept: quoted value = value + total mean - model mean. The description of the total need not
                be one-sided even when a source is. Adding the up and down shifts in quadrature separately has no such
                justification and is not done.

Input JSON (measurements): {"quantity": "...", "method": "linear_variance",
                            "measurements": [{"name": "A", "value": 1.9, "plus": 0.7, "minus": 0.5}, ...]}
Input JSON (sources):      {"value": 10.0, "model": "quadratic",
                            "sources": [{"name": "jes", "up": 0.8, "down": -0.5}, ...]}
"plus" and "minus" are positive magnitudes; "up" and "down" are signed shifts (a one-sided source has both of one sign).

Usage: combine_asymmetric.py measurements --input FILE | combine_asymmetric.py sources --input FILE
Exit codes: 0 combined; 1 the combination failed (no maximum, or a skewness the model cannot represent); 2 bad input.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

NEG = -1e300
SQ2PI = math.sqrt(2.0 * math.pi)


class CombineError(ValueError):
    """Input that cannot be combined, or a combination that failed."""


def _num(x, name, positive=False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise CombineError(f"{name} must be a finite number, got {x!r}")
    if positive and x <= 0:
        raise CombineError(f"{name} must be positive, got {x!r}")
    return float(x)


# ---------------------------------------------------------------------------------------- measurements
def log_likelihood(x: float, value: float, plus: float, minus: float, method: str) -> float:
    d = x - value
    if method == "linear_variance":
        v = plus * minus + (plus - minus) * d
        return -0.5 * d * d / v if v > 0 else NEG
    s, sp = 2.0 * plus * minus / (plus + minus), (plus - minus) / (plus + minus)
    w = s + sp * d
    return -0.5 * (d / w) ** 2 if w > 0 else NEG


def _golden_max(f, lo, hi, iters=200):
    g = (math.sqrt(5) - 1) / 2
    x1, x2 = hi - g * (hi - lo), lo + g * (hi - lo)
    f1, f2 = f(x1), f(x2)
    for _ in range(iters):
        if f1 < f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + g * (hi - lo)
            f2 = f(x2)
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - g * (hi - lo)
            f1 = f(x1)
    return 0.5 * (lo + hi)


def _crossing(f, inside, outside, target, iters=200):
    """x between inside (f > target) and outside (f <= target) where f = target, by bisection."""
    for _ in range(iters):
        mid = 0.5 * (inside + outside)
        if f(mid) > target:
            inside = mid
        else:
            outside = mid
    return 0.5 * (inside + outside)


def combine_measurements(doc: dict) -> dict:
    if not isinstance(doc, dict) or not isinstance(doc.get("measurements"), list) or len(doc["measurements"]) < 1:
        raise CombineError("input needs a list 'measurements'")
    method = doc.get("method", "linear_variance")
    if method not in ("linear_variance", "linear_sigma"):
        raise CombineError("method must be linear_variance or linear_sigma")
    meas = []
    for i, m in enumerate(doc["measurements"]):
        if not isinstance(m, dict):
            raise CombineError(f"measurement {i} must be an object with value, plus and minus")
        meas.append((str(m.get("name", f"m{i}")), _num(m.get("value"), f"measurement {i} value"),
                     _num(m.get("plus"), f"measurement {i} plus", True), _num(m.get("minus"), f"measurement {i} minus", True)))
    total = lambda x: sum(log_likelihood(x, v, p, mi, method) for _, v, p, mi in meas)
    lo = min(v - 5 * mi for _, v, _, mi in meas)
    hi = max(v + 5 * p for _, v, p, _ in meas)
    # every term is finite on the intersection of the measurements' domains; search there
    dom_lo, dom_hi = lo, hi
    for _, v, p, mi in meas:
        if p > mi:  # the variance or width goes to zero below the value
            edge = v - (p * mi / (p - mi) if method == "linear_variance" else 2 * p * mi / (p - mi))
            dom_lo = max(dom_lo, edge)
        elif mi > p:
            edge = v + (p * mi / (mi - p) if method == "linear_variance" else 2 * p * mi / (mi - p))
            dom_hi = min(dom_hi, edge)
    if not dom_lo < dom_hi:
        raise CombineError("the approximate likelihoods have no common domain (the measurements are too skewed and too far apart)")
    eps = 1e-9 * (dom_hi - dom_lo)
    a, b = dom_lo + eps, dom_hi - eps
    x_hat = _golden_max(total, a, b)
    l_max = total(x_hat)
    if not math.isfinite(l_max) or l_max <= NEG / 2:
        raise CombineError("no finite maximum of the combined likelihood")
    if total(a) > l_max - 0.5 or total(b) > l_max - 0.5:
        raise CombineError("the combined likelihood does not fall by 1/2 inside its domain; the approximation does not hold here")
    up = _crossing(total, x_hat, b, l_max - 0.5) - x_hat
    down = x_hat - _crossing(total, x_hat, a, l_max - 0.5)
    chi2 = -2.0 * l_max
    ndf = len(meas) - 1
    return {"status": "combined", "method": method, "quantity": doc.get("quantity"), "value": x_hat, "plus": up, "minus": down,
            "consistency_chi2": chi2, "ndf": ndf, "inputs": [{"name": n, "value": v, "plus": p, "minus": mi} for n, v, p, mi in meas],
            "note": ("approximate likelihoods built from each quoted interval only; correlations between the measurements "
                     "are not modeled (use combine_measurements.py with a covariance for that); the chi-square uses the "
                     "same approximation")}


# --------------------------------------------------------------------------------------------- sources
def source_cumulants(up: float, down: float, model: str) -> tuple[float, float, float]:
    """Mean, variance and third cumulant of f(nu) for one source."""
    if model == "quadratic":
        a, b = 0.5 * (up - down), 0.5 * (up + down)
        return b, a * a + 2 * b * b, 6 * a * a * b + 8 * b ** 3
    m1 = (up + down) / SQ2PI
    m2 = 0.5 * (up * up + down * down)
    m3 = 2.0 * (up ** 3 + down ** 3) / SQ2PI
    return m1, m2 - m1 * m1, m3 - 3 * m2 * m1 + 2 * m1 ** 3


def _model_from_cumulants(k2: float, k3: float, model: str) -> tuple[float, float]:
    """(up, down) of one source of the given model with variance k2 and third cumulant k3."""
    if k2 <= 0:
        return 0.0, 0.0
    if model == "quadratic":
        bmax = math.sqrt(k2 / 2.0)
        g = lambda b: 6 * k2 * b - 4 * b ** 3 - k3  # increasing on [-bmax, bmax]
        if not g(-bmax) <= 0 <= g(bmax):
            raise CombineError(f"the total skewness {k3 / k2 ** 1.5:.3g} is beyond what the quadratic model can describe "
                               f"({2 * math.sqrt(2):.3g} in magnitude)")
        lo, hi = -bmax, bmax
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if g(mid) < 0 else (lo, mid)
        b = 0.5 * (lo + hi)
        a = math.sqrt(max(k2 - 2 * b * b, 0.0))
        return a + b, b - a
    # piecewise: up = cos(phi), down = -sin(phi) at unit scale; the skewness falls from about +0.995 to -0.995
    gamma = k3 / k2 ** 1.5
    skew = lambda phi: (lambda c: c[2] / c[1] ** 1.5)(source_cumulants(math.cos(phi), -math.sin(phi), "piecewise"))
    lo, hi = 1e-9, math.pi / 2 - 1e-9
    if not skew(hi) <= gamma <= skew(lo):
        raise CombineError(f"the total skewness {gamma:.3g} is beyond what the piecewise model can describe (about 0.995 in magnitude)")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if skew(mid) > gamma else (lo, mid)
    phi = 0.5 * (lo + hi)
    u, d = math.cos(phi), -math.sin(phi)
    scale = math.sqrt(k2 / source_cumulants(u, d, "piecewise")[1])
    return u * scale, d * scale


def combine_sources(doc: dict) -> dict:
    if not isinstance(doc, dict) or not isinstance(doc.get("sources"), list) or not doc["sources"]:
        raise CombineError("input needs a value and a list 'sources'")
    value = _num(doc.get("value"), "value")
    model = doc.get("model", "quadratic")
    if model not in ("quadratic", "piecewise"):
        raise CombineError("model must be quadratic or piecewise")
    k1 = k2 = k3 = 0.0
    rows = []
    for i, s in enumerate(doc["sources"]):
        if not isinstance(s, dict):
            raise CombineError(f"source {i} must be an object with up and down")
        up, down = _num(s.get("up"), f"source {i} up"), _num(s.get("down"), f"source {i} down")
        c = source_cumulants(up, down, model)
        k1, k2, k3 = k1 + c[0], k2 + c[1], k3 + c[2]
        rows.append({"name": str(s.get("name", f"s{i}")), "up": up, "down": down, "mean": c[0], "variance": c[1], "third_cumulant": c[2]})
    up, down = _model_from_cumulants(k2, k3, model)
    model_mean = source_cumulants(up, down, model)[0]
    central = value + k1 - model_mean
    return {"status": "combined", "model": model, "input_value": value, "value": central, "up": up, "down": down,
            "plus": max(up, down, 0.0), "minus": max(-up, -down, 0.0), "central_shift": central - value,
            "total_cumulants": {"mean": k1, "variance": k2, "third_cumulant": k3,
                                "skewness": k3 / k2 ** 1.5 if k2 > 0 else 0.0},
            "sources": rows,
            "note": ("sources are independent, each a function of its own unit-Gaussian nuisance through the chosen model; "
                     "the total is matched in mean, variance and third cumulant, not in its full shape; the quoted value "
                     "moves by central_shift so the mean is kept; the result depends on the model, so state it")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    for name, helptext in (("measurements", "combine measurements of one quantity"),
                           ("sources", "add asymmetric uncertainty sources on one result")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--input", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot read {args.input}: {exc}"}))
        return 2
    try:
        out = combine_measurements(doc) if args.command == "measurements" else combine_sources(doc)
    except CombineError as exc:
        failed = any(w in str(exc) for w in ("no finite maximum", "does not fall", "beyond what", "no common domain"))
        print(json.dumps({"status": "failed" if failed else "rejected", "error": str(exc)}))
        return 1 if failed else 2
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
