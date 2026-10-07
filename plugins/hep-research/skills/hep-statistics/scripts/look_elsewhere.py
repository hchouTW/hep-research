#!/usr/bin/env python3
"""Local and global significance for a 1D signal scan over a binned, known background (look-elsewhere effect).

Purpose: a scan over a signal position (mass, energy, time) reports the largest local excess; its global p-value
must account for every position tried. This script computes the local discovery statistic along the scan and the
global p-value by brute-force toys or by the Gross-Vitells upcrossing method, and says which one it used.

Model: bins i with known background b_i > 0 and observed counts n_i; at each scan point m_k a signal template
s_ik >= 0 with yield mu >= 0, n_i ~ Pois(b_i + mu s_ik). The one-sided statistic q0(m_k) = 2 [ln L(mu_hat) - ln L(0)]
for mu_hat > 0, else 0; local p = Phi_bar(sqrt(q0)) (half chi2, Wilks/Chernoff). The background is exactly known: a
background uncertainty or a background fit is not modeled (use toys of the full procedure for that).

Subcommands:
  local          q0 and the asymptotic local p and Z at every scan point, and the maximum.
  brute          global p = fraction of seeded background-only toys whose maximum q0 over the scan reaches the
                 observed maximum; binomial Monte Carlo error, or a 95% upper bound with zero exceedances.
  gross-vitells  global p ~= p_local(c) + <N(c0)> exp(-(c - c0)/2) (Gross & Vitells 2010, eq. 3, chi2 with one
                 degree of freedom, an upper bound for large c), with <N(c0)> the mean number of upcrossings of the
                 level c0 by q0(m) along the scan, counted in a small seeded toy set. The same toys give the empirical
                 P(max q0 > c) up to the level where they still have 10 exceedances: beyond it the extrapolation is
                 not checked and a warning says so.

Every result reports local Z/p, global Z/p, the method, the trials factor (global p / local p), the seed and the
toy counts. The global p is never reported below the local p. A one-point scan needs no correction: global = local.

Input JSON: {"background": [b_i], "observed": [n_i], "scan": {"parameter": "mass", "grid": [m_k ascending],
  and either "bin_centers": [x_i] with "signal_shape": {"kind": "gaussian", "width": w} (template normalized to
  unit total over the bins), or "templates": [[s_ik over bins] per grid point]}}
Usage: python3 look_elsewhere.py {local,brute,gross-vitells} --input FILE [--toys N --seed S] [--ref-level C0]
Needs NumPy. Exit codes: 0 ok; 2 rejected input.
"""
from __future__ import annotations

import argparse
import json
import math
import sys

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

CHUNK = 2000


def _phi_bar(z):
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _z_of_p(p):
    """One-sided Z for p in (0, 1), by bisection on the normal tail (standard library only)."""
    if p <= 0:
        return math.inf
    if p >= 0.5:
        return 0.0 if p == 0.5 else -_z_of_p(1 - p)
    lo, hi = 0.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _phi_bar(mid) > p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def load(doc):
    """Validate the input and return (background, observed, grid, templates [K x B], parameter name)."""
    if not isinstance(doc, dict):
        raise ValueError("input must be a JSON object")
    b = np.asarray(doc.get("background", []), float)
    n = np.asarray(doc.get("observed", []), float)
    scan = doc.get("scan") or {}
    grid = np.asarray(scan.get("grid", []), float)
    if b.ndim != 1 or b.size == 0 or n.shape != b.shape:
        raise ValueError("background and observed must be non-empty lists of the same length")
    if not np.all(np.isfinite(b)) or np.any(b <= 0):
        raise ValueError("background must be finite and positive in every bin")
    if np.any(n < 0) or np.any(n != np.round(n)):
        raise ValueError("observed counts must be nonnegative integers")
    if grid.ndim != 1 or grid.size == 0:
        raise ValueError("the scan grid is empty")
    if not np.all(np.isfinite(grid)) or np.any(np.diff(grid) <= 0):
        raise ValueError("the scan grid must be finite and strictly increasing")
    if "templates" in scan:
        t = np.asarray(scan["templates"], float)
        if t.shape != (grid.size, b.size):
            raise ValueError("templates must have one row per grid point and one entry per bin")
    else:
        x = np.asarray(scan.get("bin_centers", []), float)
        shape = scan.get("signal_shape") or {}
        if x.shape != b.shape:
            raise ValueError("bin_centers must have one entry per bin")
        if shape.get("kind") != "gaussian" or not (isinstance(shape.get("width"), (int, float)) and shape["width"] > 0):
            raise ValueError('signal_shape must be {"kind": "gaussian", "width": w > 0}')
        t = np.exp(-0.5 * ((x[None, :] - grid[:, None]) / float(shape["width"])) ** 2)
        tot = t.sum(axis=1, keepdims=True)
        if np.any(tot <= 0):
            raise ValueError("a scan point has no signal inside the binned range")
        t = t / tot
    if not np.all(np.isfinite(t)) or np.any(t < 0) or np.any(t.sum(axis=1) <= 0):
        raise ValueError("signal templates must be finite, nonnegative and non-empty")
    return b, n, grid, t, scan.get("parameter", "parameter")


def q0_scan(n, b, t, iters=60):
    """q0 for every row of n (shape [T, B]) at every template (t: [K, B]); returns [T, K]."""
    n = np.atleast_2d(n)
    out = np.empty((n.shape[0], t.shape[0]))
    for start in range(0, n.shape[0], CHUNK):
        nn = n[start:start + CHUNK][:, None, :]                  # [T, 1, B]
        s = t[None, :, :]                                        # [1, K, B]
        stot = t.sum(axis=1)[None, :]                            # [1, K]
        g0 = np.sum(nn * s / b, axis=2) - stot                   # score at mu = 0
        mu = np.zeros(g0.shape)
        active = g0 > 0
        # Newton from mu = 0: the score is decreasing and convex in mu, so the iterates increase monotonically to
        # the root without overshooting.
        for _ in range(iters):
            lam = b + mu[..., None] * s
            g = np.sum(nn * s / lam, axis=2) - stot
            h = np.sum(nn * s * s / lam ** 2, axis=2)
            step = np.where(active & (h > 0), g / np.where(h > 0, h, 1.0), 0.0)
            mu = mu + np.maximum(step, 0.0)
            if np.all(np.abs(step) <= 1e-12 * (1 + mu)):
                break
        lam = b + mu[..., None] * s
        with np.errstate(divide="ignore", invalid="ignore"):
            ll = np.sum(np.where(nn > 0, nn * np.log(lam / b), 0.0), axis=2) - mu * stot
        out[start:start + CHUNK] = np.where(active, np.maximum(2 * ll, 0.0), 0.0)
    return out


def local(b, n, grid, t, param):
    q = q0_scan(n, b, t)[0]
    k = int(np.argmax(q))
    rows = [{param: float(m), "q0": float(v), "local_p": _phi_bar(math.sqrt(v)), "local_z": math.sqrt(v)}
            for m, v in zip(grid, q)]
    return {"scan": rows, "max": {param: float(grid[k]), "q0": float(q[k]), "local_p": _phi_bar(math.sqrt(q[k])),
                                  "local_z": math.sqrt(q[k])}}, q


def _toys(b, toys, seed):
    rng = np.random.default_rng(seed)
    return rng.poisson(b, size=(toys, b.size)).astype(float)


def _summary(q_obs, p_local, p_global, method, extra):
    note = None
    if p_global is not None and p_global < p_local:
        note = "the estimate fell below the local p-value (Monte Carlo noise); the global p is set to the local p"
        p_global = p_local
    res = {"local_p": p_local, "local_z": math.sqrt(q_obs), "global_p": p_global,
           "global_z": None if p_global is None else _z_of_p(p_global), "method": method,
           "trials_factor": None if p_global is None or p_local == 0 else p_global / p_local}
    if note:
        res["note"] = note
    res.update(extra)
    return res


def brute(b, n, grid, t, param, toys, seed):
    loc, q = local(b, n, grid, t, param)
    q_obs, p_loc = loc["max"]["q0"], loc["max"]["local_p"]
    if grid.size == 1:
        return {**loc, "global": _summary(q_obs, p_loc, p_loc, "none-needed", {"note": "one scan point: global = local"})}
    qmax = q0_scan(_toys(b, toys, seed), b, t).max(axis=1)
    k = int(np.sum(qmax >= q_obs - 1e-9))
    extra = {"toys": toys, "seed": seed, "exceedances": k}
    if k == 0:
        extra.update(global_p_upper_95=1 - 0.05 ** (1 / toys))
        res = _summary(q_obs, p_loc, None, "toys", extra)
        res["note"] = "no toy reached the observed maximum: the global p-value is only bounded"
        return {**loc, "global": res}
    p = k / toys
    extra["mc_error"] = math.sqrt(p * (1 - p) / toys)
    return {**loc, "global": _summary(q_obs, p_loc, p, "toys", extra)}


def upcrossings(q, c0):
    """Number of upcrossings of the level c0 along each scan (rows of q)."""
    above = q > c0
    return np.sum(~above[:, :-1] & above[:, 1:], axis=1) + 0  # crossings between grid points


def gross_vitells(b, n, grid, t, param, toys, seed, c0):
    loc, _ = local(b, n, grid, t, param)
    q_obs, p_loc = loc["max"]["q0"], loc["max"]["local_p"]
    if grid.size == 1:
        return {**loc, "global": _summary(q_obs, p_loc, p_loc, "none-needed", {"note": "one scan point: global = local"})}
    qt = q0_scan(_toys(b, toys, seed), b, t)
    nu = upcrossings(qt, c0)
    n_mean = float(nu.mean())
    p_gv = min(1.0, p_loc + n_mean * math.exp(-(q_obs - c0) / 2))
    qmax = np.sort(qt.max(axis=1))
    validated = float(qmax[-10]) if toys >= 10 else None  # highest level with 10 toy exceedances
    warnings = []
    if q_obs <= c0:
        warnings.append("the observed maximum is not above the reference level: the upcrossing formula does not apply")
    if validated is None or q_obs > validated:
        warnings.append(f"extrapolated beyond the levels checked by these toys (q0 up to {validated}); the "
                        "Gross-Vitells form is an asymptotic upper bound, validate it with brute toys at a lower level")
    extra = {"toys": toys, "seed": seed, "reference_level_c0": c0, "mean_upcrossings": n_mean,
             "mean_upcrossings_mc_error": float(nu.std(ddof=1) / math.sqrt(toys)) if toys > 1 else None,
             "extrapolation_distance": q_obs - c0, "checked_up_to_q0": validated, "warnings": warnings}
    return {**loc, "global": _summary(q_obs, p_loc, p_gv, "gross-vitells", extra)}


def gv_curve(b, t, toys, seed, c0, levels):
    """Gross-Vitells global p at given q0 levels from one toy set (used by tests and studies)."""
    qt = q0_scan(_toys(b, toys, seed), b, t)
    n_mean = float(upcrossings(qt, c0).mean())
    return [min(1.0, _phi_bar(math.sqrt(c)) + n_mean * math.exp(-(c - c0) / 2)) for c in levels], n_mean


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n", 1)[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("local", "brute", "gross-vitells"):
        s = sub.add_parser(name)
        s.add_argument("--input", required=True)
        if name != "local":
            s.add_argument("--toys", type=int, default=20000 if name == "brute" else 1000)
            s.add_argument("--seed", type=int, required=True)
        if name == "gross-vitells":
            s.add_argument("--ref-level", type=float, default=1.0, help="reference level c0 of q0 (default 1)")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy is required"}))
        return 2
    try:
        with open(args.input, encoding="utf-8") as fh:
            b, n, grid, t, param = load(json.load(fh))
        if args.cmd != "local" and args.toys < 1:
            raise ValueError("--toys must be positive")
        if args.cmd == "gross-vitells" and not args.ref_level > 0:
            raise ValueError("--ref-level must be positive")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    if args.cmd == "local":
        res, _ = local(b, n, grid, t, param)
        res["note"] = "local significance only: a scan needs a global p-value (brute or gross-vitells)"
    elif args.cmd == "brute":
        res = brute(b, n, grid, t, param, args.toys, args.seed)
    else:
        res = gross_vitells(b, n, grid, t, param, args.toys, args.seed, args.ref_level)
    res = {"tool": "look_elsewhere", "command": args.cmd, "scan_points": int(grid.size), "bins": int(b.size),
           "assumption": "known background; one-sided q0; asymptotic local p", **res}
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
