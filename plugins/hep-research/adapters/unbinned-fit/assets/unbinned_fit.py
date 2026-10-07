#!/usr/bin/env python3
"""Extended unbinned maximum-likelihood fit (Gaussian signal + exponential background) with a toy coverage check.

Purpose: replace "guidance only" for unbinned fits with a small, tested fitting script. It is a starting point, not a
fitting framework: one observable on a closed range [lo, hi], a Gaussian peak and an exponential background, both
normalized on the range, extended likelihood in the yields. SciPy only (D5); iminuit is not needed.

Model, on lo <= x <= hi:
  -log L = (n_sig + n_bkg) - sum_i log(n_sig g(x_i; mu, sigma) + n_bkg e(x_i; slope))
  g: Gaussian normalized on the range; e: exp(slope x) normalized on the range.
Uncertainties: the inverse of the numerical Hessian at the minimum (symmetric, "hesse") and the profile-likelihood
interval of one parameter (2 delta(-log L) = 1, other parameters refitted, "profile"). Neither is assumed to cover:
`coverage` measures it with seeded toys generated from the configured truth (Poisson total, multinomial split).

Subcommands:
  fit       --data X.json (a list of x values, or {"x": [...]}) --config C.json   fit result, covariance, profile interval
  coverage  --config C.json --toys N --seed S                                       pull mean/width and interval coverage

Config: {"range": [lo, hi], "truth": {"n_sig": .., "n_bkg": .., "mu": .., "sigma": .., "slope": ..},
         "start": {...} (optional, default truth), "profile_parameter": "n_sig" (default)}.
Output JSON is labelled [General method] and, for coverage, SYNTHETIC; seed, toys and config are echoed.
A fit is "failed" (counted, never dropped silently) when -log L still falls on a repeat minimizer pass, the
estimated distance to the minimum (EDM = g^T H^-1 g / 2) exceeds 1e-3, the Hessian is not positive definite, or a
parameter sits on a bound.

Usage: python3 unbinned_fit.py coverage --config cfg.json --toys 300 --seed 1
Exit 0 ok, 1 refused input or failed fit, 2 bad arguments.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import optimize, special

LABEL = "[General method]"
NAMES = ["n_sig", "n_bkg", "mu", "sigma", "slope"]


class FitError(ValueError):
    pass


def _norm_gauss(lo, hi, mu, sigma):
    return 0.5 * (special.erf((hi - mu) / (math.sqrt(2) * sigma)) - special.erf((lo - mu) / (math.sqrt(2) * sigma)))


def _norm_exp(lo, hi, slope):
    if abs(slope) * (hi - lo) < 1e-8:
        return hi - lo
    return (math.exp(slope * hi) - math.exp(slope * lo)) / slope


def nll(theta, x, lo, hi):
    n_sig, n_bkg, mu, sigma, slope = theta
    g = np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (math.sqrt(2 * math.pi) * sigma * _norm_gauss(lo, hi, mu, sigma))
    e = np.exp(slope * x) / _norm_exp(lo, hi, slope)
    dens = n_sig * g + n_bkg * e
    if np.any(dens <= 0) or not np.all(np.isfinite(dens)):
        return 1e300
    return float(n_sig + n_bkg - np.sum(np.log(dens)))


def _bounds(lo, hi, n):
    width = hi - lo
    return [(1e-6, 10 * n + 10), (1e-6, 10 * n + 10), (lo, hi), (width * 1e-3, width), (-50 / width, 50 / width)]


def _scales(start, lo, hi):
    """Typical step of each parameter: yields move by sqrt(N), the shape parameters by a fraction of their scale."""
    return np.array([math.sqrt(max(start["n_sig"], 1.0)), math.sqrt(max(start["n_bkg"], 1.0)), 0.1 * start["sigma"],
                     0.1 * start["sigma"], 0.1 / (hi - lo)])


def _minimize(f, x0, bounds, scale):
    """L-BFGS-B in scaled variables on f - f(x0), so the tolerance is not lost against a large -log L; repeated
    from its own result until -log L stops falling (a second pass guards against an early stop)."""
    f0 = f(x0)
    g = lambda z: f(z * scale) - f0  # noqa: E731
    zb = [(a / s, b / s) for (a, b), s in zip(bounds, scale)]
    z, best, stable = x0 / scale, None, False
    for _ in range(5):
        r = optimize.minimize(g, z, method="L-BFGS-B", bounds=zb, options={"maxiter": 5000, "ftol": 1e-15, "gtol": 1e-9})
        if best is not None and best.fun - r.fun < 1e-7:
            best, stable = (r if r.fun < best.fun else best), True
            break
        best, z = r, r.x
    best.x, best.fun, best.stable = best.x * scale, best.fun + f0, stable
    return best


def _hessian(f, x0, steps):
    k = len(x0)
    h = np.zeros((k, k))
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.eye(k)[i] * steps[i], np.eye(k)[j] * steps[j]
            h[i, j] = h[j, i] = (f(x0 + ei + ej) - f(x0 + ei - ej) - f(x0 - ei + ej) + f(x0 - ei - ej)) / (4 * steps[i] * steps[j])
    return h


def fit(x, lo, hi, start, profile_parameter="n_sig"):
    x = np.asarray(x, dtype=float)
    if x.size == 0 or np.any(x < lo) or np.any(x > hi):
        raise FitError("data must be non-empty and inside the range")
    bounds = _bounds(lo, hi, x.size)
    f = lambda t: nll(t, x, lo, hi)  # noqa: E731
    res = _minimize(f, np.array([start[k] for k in NAMES], float), bounds, _scales(start, lo, hi))
    theta = res.x
    # L-BFGS-B often ends with "ABNORMAL" (line search) at a true minimum when ftol is this tight, so convergence is
    # judged by a repeat pass that no longer lowers -log L and by the estimated distance to the minimum (EDM) below
    problems = [] if res.stable else ["-log L still falling after 5 minimizer passes"]
    on_bound = [NAMES[i] for i, (a, b) in enumerate(bounds) if min(theta[i] - a, b - theta[i]) < 1e-6 * max(1.0, abs(b - a))]
    if on_bound:
        problems.append(f"on a bound: {on_bound}")
    steps = np.array([max(1e-4 * abs(v), 1e-5 * (hi - lo)) for v in theta])
    steps[:2] = np.maximum(1e-3 * np.sqrt(np.maximum(theta[:2], 1.0)), 1e-4)
    hess = _hessian(f, theta, steps)
    try:
        cov = np.linalg.inv(hess)
        if np.any(np.linalg.eigvalsh(0.5 * (cov + cov.T)) <= 0):
            raise np.linalg.LinAlgError
        grad = np.array([(f(theta + e) - f(theta - e)) / (2 * s) for e, s in zip(np.diag(steps), steps)])
        free = [i for i in range(len(theta)) if NAMES[i] not in on_bound]
        edm = float(0.5 * grad[free] @ cov[np.ix_(free, free)] @ grad[free])
        if edm > 1e-3:
            problems.append(f"estimated distance to minimum {edm:.2g} > 1e-3")
    except np.linalg.LinAlgError:
        cov = None
        problems.append("Hessian is not positive definite")
    out = {"parameters": dict(zip(NAMES, map(float, theta))), "nll_min": float(res.fun), "problems": problems}
    if cov is not None:
        out["edm"] = edm
    if cov is not None:
        out["hesse_errors"] = dict(zip(NAMES, map(float, np.sqrt(np.diag(cov)))))
        out["covariance"] = cov.tolist()
        out["profile_interval"] = {profile_parameter: _profile(f, theta, bounds, _scales(start, lo, hi), NAMES.index(profile_parameter),
                                                               float(np.sqrt(cov[NAMES.index(profile_parameter)] [NAMES.index(profile_parameter)])))}
    return out


def _profile(f, theta, bounds, scale, k, err):
    """Profile interval of parameter k at 2 delta(-log L) = 1; None on a side where it is not found inside the bounds."""
    others = [i for i in range(len(theta)) if i != k]
    fmin = f(theta)
    start = theta[others].copy()

    def prof(v):
        nonlocal start
        g = lambda t: f(np.insert(t, k, v))  # noqa: E731
        r = _minimize(g, start, [bounds[i] for i in others], scale[others])
        start = r.x
        return r.fun - fmin - 0.5

    ends = []
    for sign in (-1, 1):
        start = theta[others].copy()
        a, b = theta[k], theta[k] + sign * err
        lim = bounds[k][0] if sign < 0 else bounds[k][1]
        for _ in range(6):
            if (sign < 0 and b <= lim) or (sign > 0 and b >= lim):
                b = lim
            if prof(b) > 0:
                break
            if b == lim:
                b = None
                break
            a, b = b, b + sign * err
        if b is None:
            ends.append(None)
            continue
        start = theta[others].copy()
        ends.append(float(optimize.brentq(prof, min(a, b), max(a, b), xtol=1e-6 * max(1.0, abs(err)))))
    return ends


def generate(truth, lo, hi, rng):
    n_s, n_b = rng.poisson(truth["n_sig"]), rng.poisson(truth["n_bkg"])
    sig = []
    while len(sig) < n_s:
        draw = rng.normal(truth["mu"], truth["sigma"], size=2 * (n_s - len(sig)) + 10)
        sig.extend(draw[(draw >= lo) & (draw <= hi)][: n_s - len(sig)])
    u = rng.random(n_b)
    s = truth["slope"]
    bkg = lo + u * (hi - lo) if abs(s) * (hi - lo) < 1e-8 else np.log(np.exp(s * lo) + u * (np.exp(s * hi) - np.exp(s * lo))) / s
    return np.concatenate([np.array(sig), bkg])


def coverage(cfg, toys, seed):
    lo, hi = map(float, cfg["range"])
    truth, start = cfg["truth"], cfg.get("start", cfg["truth"])
    pp = cfg.get("profile_parameter", "n_sig")
    rng = np.random.default_rng(seed)
    pulls = {k: [] for k in NAMES}
    hesse_cov, prof_cov, failed = {k: 0 for k in NAMES}, 0, []
    for t in range(toys):
        x = generate(truth, lo, hi, rng)
        try:
            r = fit(x, lo, hi, start, pp)
        except FitError as exc:
            failed.append({"toy": t, "problems": [str(exc)]})
            continue
        if r["problems"]:
            failed.append({"toy": t, "problems": r["problems"]})
            continue
        for k in NAMES:
            p = (r["parameters"][k] - truth[k]) / r["hesse_errors"][k]
            pulls[k].append(p)
            hesse_cov[k] += abs(p) <= 1
        lo_end, hi_end = r["profile_interval"][pp]
        prof_cov += (lo_end is not None and hi_end is not None and lo_end <= truth[pp] <= hi_end)
    good = toys - len(failed)
    if good == 0:
        raise FitError("every toy fit failed")
    se = math.sqrt(0.6827 * 0.3173 / good)
    return {"label": LABEL, "data": "SYNTHETIC toys from the configured truth", "toys": toys, "seed": seed,
            "config": cfg, "fits_used": good, "fits_failed": len(failed), "failed": failed[:20],
            "pull_mean": {k: float(np.mean(v)) for k, v in pulls.items()},
            "pull_width": {k: float(np.std(v, ddof=1)) for k, v in pulls.items()},
            "pull_mean_standard_error": 1 / math.sqrt(good),
            "hesse_68_coverage": {k: v / good for k, v in hesse_cov.items()},
            "profile_68_coverage": {pp: prof_cov / good}, "coverage_standard_error": se,
            "note": ("coverage is the fraction of successful toy fits whose interval contains the truth; nominal 0.6827 "
                     "with the binomial standard error given; failed fits are excluded from the fractions and counted "
                     "separately, so a large failure count makes the coverage optimistic")}


def _check_cfg(cfg):
    lo, hi = map(float, cfg["range"])
    t = cfg["truth"]
    if not hi > lo or any(k not in t for k in NAMES) or t["sigma"] <= 0 or t["n_sig"] <= 0 or t["n_bkg"] <= 0:
        raise FitError("config needs range [lo < hi] and truth with positive n_sig, n_bkg, sigma, and mu, slope")
    return lo, hi


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("fit")
    pf.add_argument("--data", type=Path, required=True)
    pf.add_argument("--config", type=Path, required=True)
    pc = sub.add_parser("coverage")
    pc.add_argument("--config", type=Path, required=True)
    pc.add_argument("--toys", type=int, default=200)
    pc.add_argument("--seed", type=int, default=1)
    opts = ap.parse_args(argv)
    try:
        cfg = json.loads(opts.config.read_text(encoding="utf-8"))
        lo, hi = _check_cfg(cfg)
        if opts.cmd == "fit":
            d = json.loads(opts.data.read_text(encoding="utf-8"))
            r = fit(d["x"] if isinstance(d, dict) else d, lo, hi, cfg.get("start", cfg["truth"]),
                    cfg.get("profile_parameter", "n_sig"))
            out = {"label": LABEL, **r}
            print(json.dumps(out, indent=1))
            return 1 if r["problems"] else 0
        if not 10 <= opts.toys <= 20000:
            raise FitError("--toys must be between 10 and 20000")
        print(json.dumps(coverage(cfg, opts.toys, opts.seed), indent=1))
        return 0
    except (FitError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
