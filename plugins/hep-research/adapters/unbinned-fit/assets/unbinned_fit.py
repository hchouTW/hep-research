#!/usr/bin/env python3
"""Extended unbinned maximum-likelihood fit (Gaussian signal + exponential background) with a toy coverage check.

Purpose: replace "guidance only" for unbinned fits with a small, tested fitting script. It is a starting point, not a
fitting framework: one observable on a closed range [lo, hi], a Gaussian peak and an exponential background, both
normalized on the range, extended likelihood in the yields. SciPy only (D5); iminuit is not needed.

Model, on lo <= x <= hi:
  -log L = (n_sig + n_bkg) - sum_i log(n_sig g(x_i; mu, sigma) + n_bkg e(x_i; slope))
  g: Gaussian normalized on the range; e: exp(slope (x - lo)) normalized on the range (relative to lo: no overflow).
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
Exit 0 ok, 1 refused input or failed fit, 2 bad arguments (including an unknown profile_parameter), 3 NumPy or SciPy
not installed (status missing-dependency).
A fit with n_sig on its lower bound is a boundary estimate ("boundary": ["n_sig"]): its profile interval starts at
the bound; coverage counts such toys through the profile interval only (boundary_toys) and not in the Hesse pulls.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import numpy as np
    from scipy import optimize, special
    MISSING = None
except ImportError as _exc:  # reported by main() (exit 3), so --help works without NumPy and SciPy
    MISSING = _exc.name or "numpy or scipy"

LABEL = "[General method]"
NAMES = ["n_sig", "n_bkg", "mu", "sigma", "slope"]


class FitError(ValueError):
    pass


class BadArgument(ValueError):
    """A refused configuration (exit 2), as opposed to a failed fit (exit 1)."""


def _norm_gauss(lo, hi, mu, sigma):
    return 0.5 * (special.erf((hi - mu) / (math.sqrt(2) * sigma)) - special.erf((lo - mu) / (math.sqrt(2) * sigma)))


def _norm_exp(lo, hi, slope):
    """Normalization of exp(slope (x - lo)) on [lo, hi]: relative to lo, so a range far from 0 cannot overflow."""
    w = hi - lo
    if abs(slope) * w < 1e-8:
        return w
    return math.expm1(slope * w) / slope


def nll(theta, x, lo, hi):
    n_sig, n_bkg, mu, sigma, slope = theta
    g = np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (math.sqrt(2 * math.pi) * sigma * _norm_gauss(lo, hi, mu, sigma))
    e = np.exp(slope * (x - lo)) / _norm_exp(lo, hi, slope)
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
    # n_sig at its lower bound is a boundary estimate, not a failed fit: the profile interval then starts at the bound
    # and the Hesse error is not used (coverage counts the toy through the profile interval only; STH-T3.2)
    signal_boundary = on_bound == ["n_sig"] and theta[0] - bounds[0][0] < 1e-6 * max(1.0, bounds[0][1] - bounds[0][0])
    if on_bound and not signal_boundary:
        problems.append(f"on a bound: {on_bound}")
    # Hessian steps on each parameter's natural scale (yields ~ sqrt(N), mu and sigma ~ sigma, slope ~ 1/width), so the
    # steps neither vanish nor swamp a parameter when the range is far from 0 or wide (STH-T3.2)
    steps = 1e-3 * _scales(dict(zip(NAMES, theta)), lo, hi)
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
        if not signal_boundary:
            problems.append("Hessian is not positive definite")
    out = {"parameters": dict(zip(NAMES, map(float, theta))), "nll_min": float(res.fun), "problems": problems,
           "boundary": ["n_sig"] if signal_boundary else []}
    if cov is not None:
        out["edm"] = edm
    k = NAMES.index(profile_parameter)
    if cov is not None:
        out["hesse_errors"] = dict(zip(NAMES, map(float, np.sqrt(np.abs(np.diag(cov))))))
        out["covariance"] = cov.tolist()
    if cov is not None or signal_boundary:
        err = float(np.sqrt(abs(cov[k][k]))) if cov is not None else _scales(dict(zip(NAMES, theta)), lo, hi)[k]
        out["profile_interval"] = {profile_parameter: _profile(f, theta, bounds, _scales(start, lo, hi), k, err)}
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
        # one bracket policy on both sides: step out by err (doubling after the third step) for at most 12 steps or to
        # the bound; a lower side of n_sig that reaches its bound below the level ends at the bound (the physical
        # boundary), any other side reaching its bound is None (open within the parameter's bounds)
        step, at_bound = err, False
        for i in range(12):
            if (sign < 0 and b <= lim) or (sign > 0 and b >= lim):
                b = lim
            if prof(b) > 0:
                break
            if b == lim:
                at_bound = True
                break
            step = step * 2 if i >= 2 else step
            a, b = b, b + sign * step
        if at_bound and k == 0 and sign < 0:
            ends.append(float(lim))
            continue
        if at_bound:
            b = None
        if b is None:
            ends.append(None)
            continue
        start = theta[others].copy()
        try:
            ends.append(float(optimize.brentq(prof, min(a, b), max(a, b), xtol=1e-6 * max(1.0, abs(err)))))
        except ValueError:
            # the refitted profile is not monotonic between the bracket ends (another local minimum of the other
            # parameters): the interval is not established; the fit is reported as failed and counted, never dropped
            raise FitError(f"profile interval of {NAMES[k]} not bracketed (non-monotonic profile)") from None
    return ends


def generate(truth, lo, hi, rng):
    n_s, n_b = rng.poisson(truth["n_sig"]), rng.poisson(truth["n_bkg"])
    sig = []
    while len(sig) < n_s:
        draw = rng.normal(truth["mu"], truth["sigma"], size=2 * (n_s - len(sig)) + 10)
        sig.extend(draw[(draw >= lo) & (draw <= hi)][: n_s - len(sig)])
    u = rng.random(n_b)
    s = truth["slope"]
    bkg = lo + u * (hi - lo) if abs(s) * (hi - lo) < 1e-8 else lo + np.log1p(u * np.expm1(s * (hi - lo))) / s
    return np.concatenate([np.array(sig), bkg])


def coverage(cfg, toys, seed):
    lo, hi = map(float, cfg["range"])
    truth, start = cfg["truth"], cfg.get("start", cfg["truth"])
    pp = cfg.get("profile_parameter", "n_sig")
    rng = np.random.default_rng(seed)
    pulls = {k: [] for k in NAMES}
    hesse_cov, prof_cov, failed, boundary_toys = {k: 0 for k in NAMES}, 0, [], 0
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
        if r["boundary"] or "hesse_errors" not in r:
            boundary_toys += 1  # n_sig on its lower bound: counted through the profile interval, no Hesse pull
            lo_end, hi_end = r["profile_interval"][pp]
            prof_cov += (lo_end is not None and hi_end is not None and lo_end <= truth[pp] <= hi_end)
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
    hesse_good = good - boundary_toys
    se = math.sqrt(0.6827 * 0.3173 / good)
    return {"label": LABEL, "data": "SYNTHETIC toys from the configured truth", "toys": toys, "seed": seed,
            "config": cfg, "fits_used": good, "fits_failed": len(failed), "failed": failed[:20],
            "boundary_toys": boundary_toys,
            "pull_mean": {k: float(np.mean(v)) if v else None for k, v in pulls.items()},
            "pull_width": {k: float(np.std(v, ddof=1)) if len(v) > 1 else None for k, v in pulls.items()},
            "pull_mean_standard_error": 1 / math.sqrt(max(hesse_good, 1)),
            "hesse_68_coverage": {k: v / hesse_good if hesse_good else None for k, v in hesse_cov.items()},
            "profile_68_coverage": {pp: prof_cov / good}, "coverage_standard_error": se,
            "note": ("coverage is the fraction of successful toy fits whose interval contains the truth; nominal 0.6827 "
                     "with the binomial standard error given; failed fits are excluded from the fractions and counted "
                     "separately, so a large failure count makes the coverage optimistic; toys with n_sig on its lower "
                     "bound (boundary_toys) enter the profile coverage with the interval starting at the bound and are "
                     "left out of the Hesse pulls and coverage, which are undefined there")}


def _check_cfg(cfg):
    lo, hi = map(float, cfg["range"])
    t = cfg["truth"]
    if not hi > lo or any(k not in t for k in NAMES) or t["sigma"] <= 0 or t["n_sig"] <= 0 or t["n_bkg"] <= 0:
        raise FitError("config needs range [lo < hi] and truth with positive n_sig, n_bkg, sigma, and mu, slope")
    if cfg.get("profile_parameter", "n_sig") not in NAMES:
        raise BadArgument(f"profile_parameter must be one of {NAMES}, got {cfg.get('profile_parameter')!r}")
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
    if MISSING:  # exit 3, a missing dependency (hep-computing script contract)
        print(json.dumps({"status": "missing-dependency", "reason": f"{MISSING} is not installed: pip install numpy scipy"}))
        return 3
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
    except BadArgument as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2
    except (FitError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    import sys as _sys
    try:
        sys.exit(main())
    except OSError as _exc:  # a missing or unreadable input: one line, no traceback
        print(f"unbinned_fit.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2)
