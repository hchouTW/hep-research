#!/usr/bin/env python3
"""Power-constrained limits, efficiency intervals and ratio intervals with their exact coverage (audit T29).
EXPERIMENTAL. Needs NumPy and SciPy.

pcl         counting experiment with known background b: the classical (CLs+b) one-sided upper limit on s, constrained
            by the power threshold (Cowan, Cranmer, Gross, Vitells 2011, arXiv:1105.3166): the limit is never below
            s_min, the smallest s that the test excludes with probability at least the threshold (default 0.16, the
            -1 sigma expected limit) when s = 0. The threshold is an input, stated in the result. Exact coverage is
            computed by summing Poisson probabilities.
efficiency  k successes in n trials: the Clopper-Pearson interval (a confidence interval, coverage >= cl at every
            efficiency, computed exactly by summation) and, separately, the central credible interval of the Beta
            posterior of a stated prior (Jeffreys Beta(1/2, 1/2) or uniform Beta(1, 1)). The credible interval is a
            Bayesian statement: its frequentist coverage is reported, not claimed, and dips below cl at some
            efficiencies.
ratio       R = mu_x / mu_y from Gaussian x, y with known sigmas and correlation: Fieller's confidence set
            {R: (x - R y)^2 <= z^2 (sx^2 - 2 R rho sx sy + R^2 sy^2)}, which is a bounded interval, the complement of
            an interval (two half-lines) or the whole real line, reported as such; the delta-method interval
            x/y +- z sigma_R is reported beside it with its known failure when y is within a few sigma of zero. A
            finite symmetric error is never forced on an unbounded set.

Usage: pcl_efficiency_ratio.py pcl --n N --b B [--cl 0.95 --power-threshold 0.16]
       pcl_efficiency_ratio.py efficiency --k K --n N [--cl 0.6827 --prior jeffreys|uniform]
       pcl_efficiency_ratio.py ratio --x X --sx SX --y Y --sy SY [--rho 0 --cl 0.6827]
Exit codes: 0 ok; 2 bad input. Output JSON labelled [General method] EXPERIMENTAL.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
    from scipy import optimize, stats
except ImportError:  # pragma: no cover
    np = optimize = stats = None  # type: ignore[assignment]

LABEL = "[General method] EXPERIMENTAL"


# ------------------------------------------------------------------------------------------------- pcl
def classical_upper(n: int, b: float, cl: float) -> float:
    """s with P(N <= n | s + b) = 1 - cl (may be negative: the unconstrained CLs+b limit)."""
    a = 1 - cl
    if stats.poisson.cdf(n, b) <= a:
        return optimize.brentq(lambda mu: stats.poisson.cdf(n, mu) - a, 1e-12, b) - b
    return optimize.brentq(lambda mu: stats.poisson.cdf(n, mu) - a, b, 1e4) - b


def power_threshold_limit(b: float, cl: float, threshold: float) -> float:
    """s_min: the smallest s whose exclusion probability under s = 0 reaches the threshold (the expected limit at the
    threshold quantile of the background-only count distribution)."""
    m = 0
    while stats.poisson.cdf(m, b) < threshold:
        m += 1
    return max(classical_upper(m, b, cl), 0.0)


def pcl(n: int, b: float, cl: float = 0.95, threshold: float = 0.16) -> dict:
    if n < 0 or b < 0 or not 0 < cl < 1 or not 0 < threshold < 0.5:
        raise ValueError("need n >= 0, b >= 0, 0 < cl < 1, 0 < power threshold < 0.5")
    ul = classical_upper(n, b, cl)
    smin = power_threshold_limit(b, cl, threshold)
    return {"label": LABEL, "n": n, "b": b, "cl": cl, "power_threshold": threshold, "unconstrained_limit": ul,
            "power_constraint": smin, "pcl_limit": max(ul, smin), "constrained": ul < smin}


def pcl_coverage(s: float, b: float, cl: float = 0.95, threshold: float = 0.16) -> dict:
    top = int(stats.poisson.isf(1e-12, s + b)) + 2
    p = stats.poisson.pmf(np.arange(top + 1), s + b)
    lim = np.array([pcl(k, b, cl, threshold)["pcl_limit"] for k in range(top + 1)])
    unc = np.array([classical_upper(k, b, cl) for k in range(top + 1)])
    return {"s": s, "b": b, "coverage_pcl": float(p[lim >= s].sum()), "coverage_unconstrained": float(p[unc >= s].sum())}


# ------------------------------------------------------------------------------------------ efficiency
def clopper_pearson(k: int, n: int, cl: float) -> tuple[float, float]:
    a = (1 - cl) / 2
    lo = 0.0 if k == 0 else float(stats.beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - a, k + 1, n - k))
    return lo, hi


def beta_credible(k: int, n: int, cl: float, prior: str) -> tuple[float, float]:
    a0 = {"jeffreys": 0.5, "uniform": 1.0}[prior]
    post = stats.beta(k + a0, n - k + a0)
    return float(post.ppf((1 - cl) / 2)), float(post.ppf(1 - (1 - cl) / 2))


def efficiency(k: int, n: int, cl: float = 0.6827, prior: str = "jeffreys") -> dict:
    if not 0 <= k <= n or n < 1 or prior not in ("jeffreys", "uniform"):
        raise ValueError("need 0 <= k <= n, n >= 1 and prior jeffreys or uniform")
    return {"label": LABEL, "k": k, "n": n, "cl": cl, "estimate": k / n,
            "clopper_pearson": {"interval": list(clopper_pearson(k, n, cl)), "kind": "confidence interval (coverage >= cl)"},
            "beta_credible": {"interval": list(beta_credible(k, n, cl, prior)), "prior": prior,
                              "kind": "credible interval (posterior probability cl); frequentist coverage not guaranteed"}}


def efficiency_coverage(n: int, cl: float, eps_grid, prior: str = "jeffreys") -> dict:
    ks = np.arange(n + 1)
    cp = [clopper_pearson(int(k), n, cl) for k in ks]
    bc = [beta_credible(int(k), n, cl, prior) for k in ks]
    rows = []
    for e in eps_grid:
        p = stats.binom.pmf(ks, n, e)
        rows.append({"efficiency": float(e), "clopper_pearson": float(sum(pk for pk, (lo, hi) in zip(p, cp) if lo <= e <= hi)),
                     "beta_credible": float(sum(pk for pk, (lo, hi) in zip(p, bc) if lo <= e <= hi))})
    return {"n": n, "cl": cl, "prior": prior, "rows": rows,
            "min_coverage_clopper_pearson": min(r["clopper_pearson"] for r in rows),
            "min_coverage_beta_credible": min(r["beta_credible"] for r in rows)}


# --------------------------------------------------------------------------------------------- ratio
def fieller(x: float, sx: float, y: float, sy: float, rho: float = 0.0, cl: float = 0.6827) -> dict:
    if not (sx > 0 and sy > 0 and -1 < rho < 1 and math.isfinite(x) and math.isfinite(y) and math.isfinite(sx) and math.isfinite(sy)):
        raise ValueError("need finite x, y, sx > 0, sy > 0 and |rho| < 1")
    if y * y == stats.chi2.ppf(cl, 1) * sy * sy:
        raise ValueError("y^2 equals z^2 sy^2 exactly: the Fieller quadratic degenerates (move cl or sy slightly)")
    z2 = stats.chi2.ppf(cl, 1)
    a = y * y - z2 * sy * sy
    bq = -2 * (x * y - z2 * rho * sx * sy)
    c = x * x - z2 * sx * sx
    disc = bq * bq - 4 * a * c
    if a > 0:
        r1, r2 = sorted(((-bq - math.sqrt(disc)) / (2 * a), (-bq + math.sqrt(disc)) / (2 * a)))
        kind, sets = "bounded", [[r1, r2]]
    elif disc > 0:
        r1, r2 = sorted(((-bq - math.sqrt(disc)) / (2 * a), (-bq + math.sqrt(disc)) / (2 * a)))
        kind, sets = "complement", [[-math.inf, r1], [r2, math.inf]]
    else:
        kind, sets = "unbounded", [[-math.inf, math.inf]]
    z = math.sqrt(z2)
    if y == 0:  # the Fieller set above is still defined; the point estimate and its linearization are not (STH-T3.1)
        delta: dict = {"interval": None, "note": "y = 0: the ratio x/y and its linearization are undefined; use the Fieller set"}
    else:
        r = x / y
        sr = abs(r) * math.sqrt((sx / x) ** 2 + (sy / y) ** 2 - 2 * rho * sx * sy / (x * y)) if x != 0 else abs(sx / y)
        delta = {"interval": [r - z * sr, r + z * sr], "note": "symmetric linearization; fails when y is within a few sigma of 0"}
    return {"label": LABEL, "x": x, "y": y, "cl": cl, "fieller": {"kind": kind, "set": sets},
            "delta_method": delta,
            "denominator_significance": abs(y) / sy}


def _contains(sets, value):
    return any(lo <= value <= hi for lo, hi in sets)


def ratio_coverage(mx, sx, my, sy, rho=0.0, cl=0.6827, toys=4000, seed=1) -> dict:
    rng = np.random.default_rng(seed)
    cov = [[sx * sx, rho * sx * sy], [rho * sx * sy, sy * sy]]
    draws = rng.multivariate_normal([mx, my], cov, size=toys)
    r_true = mx / my
    f = d = 0
    kinds = {"bounded": 0, "complement": 0, "unbounded": 0}
    for x, y in draws:
        res = fieller(float(x), sx, float(y), sy, rho, cl)
        kinds[res["fieller"]["kind"]] += 1
        f += _contains(res["fieller"]["set"], r_true)
        lo, hi = res["delta_method"]["interval"]
        d += lo <= r_true <= hi
    return {"true_ratio": r_true, "denominator_over_sigma": my / sy, "toys": toys, "seed": seed,
            "coverage_fieller": f / toys, "coverage_delta_method": d / toys, "set_kinds": kinds}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("pcl")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--b", type=float, required=True)
    p.add_argument("--cl", type=float, default=0.95)
    p.add_argument("--power-threshold", type=float, default=0.16)
    e = sub.add_parser("efficiency")
    e.add_argument("--k", type=int, required=True)
    e.add_argument("--n", type=int, required=True)
    e.add_argument("--cl", type=float, default=0.6827)
    e.add_argument("--prior", default="jeffreys")
    r = sub.add_parser("ratio")
    for name in ("x", "sx", "y", "sy"):
        r.add_argument(f"--{name}", type=float, required=True)
    r.add_argument("--rho", type=float, default=0.0)
    r.add_argument("--cl", type=float, default=0.6827)
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy and SciPy are required"}))
        return 2
    if not 0 < a.cl < 1:  # also refuses NaN
        print(json.dumps({"status": "rejected", "error": f"--cl must lie in (0, 1), got {a.cl}"}))
        return 2
    try:
        if a.command == "pcl":
            out = pcl(a.n, a.b, a.cl, a.power_threshold)
        elif a.command == "efficiency":
            out = efficiency(a.k, a.n, a.cl, a.prior)
        else:
            out = fieller(a.x, a.sx, a.y, a.sy, a.rho, a.cl)
    except (ValueError, KeyError, ZeroDivisionError, OverflowError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    out["status"] = "ok"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
