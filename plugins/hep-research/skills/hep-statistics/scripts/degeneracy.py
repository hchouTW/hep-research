#!/usr/bin/env python3
"""Two-level degeneracy diagnostics: a Fisher screen, then profile-likelihood scans (cr-propagation A3). Needs NumPy, SciPy.

A Fisher matrix is a local linear screen; a conclusion about a degeneracy needs a profile-likelihood scan or posterior
samples, and every degeneracy records the range where it holds.

Level 1, Fisher screen (fisher_screen, screen_objects): eigen-decomposition of the Fisher matrix in the fit coordinates
(ln p on a log axis, p on a linear one). A direction is flat when its eigenvalue is below 1e-10 of the largest or its
1-sigma half-width exceeds half the box chord along it; this is the rule of covariance_fit.py's tabulated-grid fit,
moved here unchanged (that fit calls this module). Its object-form entries carry "evidence": "fisher-screen" and never a
valid_range: the screen sees only the neighbourhood of the best fit.

Level 2, profile-likelihood scans (profile_scan): -2 ln L minimized over every other coordinate (the normalization
nuisance included) at fixed values of
- "parameter": one parameter, at "values" (natural units) or "points" values spaced evenly in its fit coordinate;
- "direction": a straight line through the best fit in the fit coordinates, {name: component, ...} or "fisher" (each
  flat direction of the screen); the orthogonal complement is profiled; "values" are distances along the unit line;
- "plane": two parameters, on "values" [[...], [...]] or "points" per axis.
The degeneracy holds where the profile stays within "threshold" (default 1, in -2 ln L) of the minimum: the contiguous
region around the minimum gives valid_range. In a 1-D scan each end is where delta crosses the threshold (linear
interpolation between scan points; range_ends "threshold") or the scan edge if it never crosses there ("scan-edge":
where the box ends, not where the degeneracy breaks); in a plane the region is the 8-connected set of scan points within
the threshold and its ends are scan points. The path of the profiled minimum in that region gives the exponents: least
squares slope of each moving parameter on the pivot (the scanned parameter, the largest component of a direction, the
first of a plane) in the fit coordinates. Its entries carry "evidence": "profile-scan" and valid_range. A scan with an
unconverged profile point gives no entry (warning; exit 1 on the CLI).

Object form: {"combination", "form", "exponents", "valid_range", "broken_by", "evidence"}. For a pair (a, b) in parameter
order with d ln a = r d ln b along the flat path: "form": "power", "exponents" {a: 1, b: -r}, combination "a/b^r"; with
a linear axis: "form": "linear", combination "a - r*b" in the fit coordinates, no exponents; more than two parameters on
a Fisher flat direction: "form": "direction", the eigenvector in the combination. "broken_by" only when the caller names
the observables (scan "broken_by").

CLI: degeneracy.py synthetic-curved [--points 41] [--threshold 1.0]: a built-in SYNTHETIC study with a curved
degeneracy, D0_cm2_s proportional to L_kpc^1.2. Bins: 7 rigidity bins, 2-256 GV; prediction of a secondary-to-primary
ratio y_i = 0.3 (R_i / 10 GV)^-0.45 (u_true / u) (1 + b(L) h_i), u = D0_cm2_s / L_kpc^1.2, h_i the centred, unit
half-range tilt in ln R_i; b(L) = 0 up to L = 6 kpc and 0.05 ((L - 6 kpc) / 2 kpc)^2 above. Asimov data at D0_cm2_s =
3e28, L_kpc = 4; covariance 2% uncorrelated + 1% fully correlated; box D0_cm2_s in [1e28, 1.2e29], L_kpc in [2, 10].
Why the degeneracy is broken above 8 kpc and not only by construction: every prediction with L <= 6 kpc equals the
truth's when D0_cm2_s / L_kpc^1.2 does (exact degeneracy), while above 6 kpc the tilt changes the energy dependence,
which u (a pure normalization) cannot absorb; the profile over D0_cm2_s then rises as ((L - 6 kpc) / 2 kpc)^4 and
reaches delta -2 ln L of about 19 at 8 kpc, so the data exclude L >= 8 kpc along the valley (the output reports the
value). It stands for the case of the plan's P7 example, where a D0/L scaling holds at small halo heights and fails at
large ones; the numbers are SYNTHETIC. Output: both levels in one JSON object ("degeneracies": the fisher-screen
entry and the profile-scan entry). Real fits: covariance_fit.py fit, model tabulated-grid, with a "degeneracy_scan"
block (the scan specification above); its output then carries "degeneracies" and "profile_scans" per fit.
Exit codes: 0 done; 1 a profile point did not converge (status "failed"); 2 bad input. Output JSON labelled [General
method].
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

try:  # --help works without them; main() refuses to run without them
    import numpy as np
    from scipy import optimize
except ImportError:  # pragma: no cover
    np = optimize = None  # type: ignore[assignment]

sys.dont_write_bytecode = True

LABEL = "[General method]"
DEGENERATE_EIG = 1e-10     # eigenvalue / largest eigenvalue below which a direction is degenerate regardless of sigma
INVOLVED = 0.1             # |component| of a unit flat direction above which a parameter takes part in it
MOVES = 0.1                # |slope| on the pivot above which a profiled parameter moves with it
THRESHOLD = 1.0            # delta -2 ln L within which the profile counts as flat (one-parameter 68% level)
PENALTY = 1e4              # weight of the box penalty in a direction scan (squared distance outside, in box spans)


class ScanInputError(ValueError):
    """A malformed scan specification (exit 2)."""


# --------------------------------------------------------------------------- level 1: Fisher screen
def fisher_screen(fisher, names, span, degenerate_eig=DEGENERATE_EIG):
    """Eigen-decomposition of a Fisher matrix in the fit coordinates. Returns (condition number, eigen entries,
    degenerate [(entry, v, lambda)], kept [(entry, v, lambda)]); span = the box width per coordinate."""
    k = len(names)
    ev, evec = np.linalg.eigh(0.5 * (fisher + fisher.T))
    lam_max = max(float(ev[-1]), 1e-300)
    cond = float(lam_max / ev[0]) if ev[0] > 0 else None
    eig, degenerate, keep = [], [], []
    for lam, v in zip(ev, evec.T):
        v = v * (1 if v[np.argmax(np.abs(v))] > 0 else -1)
        sigma = float(1 / math.sqrt(lam)) if lam > 0 else None
        chord = float(min(span[i] / abs(v[i]) for i in range(k) if abs(v[i]) > 1e-12))
        flat = lam <= degenerate_eig * lam_max or sigma is None or sigma > chord / 2
        entry = {"eigenvalue": float(lam), "eigenvector": dict(zip(names, map(float, v))), "sigma": sigma,
                 "grid_chord": chord, "degenerate": bool(flat)}
        eig.append(entry)
        (degenerate if flat else keep).append((entry, v, lam))
    return cond, eig, degenerate, keep


def _coord(name, scale):
    return f"ln({name})" if scale == "log" else name


def _pair_object(a, b, r, scales_of, evidence):
    """Object form for d coord(a) = r d coord(b) along the flat path (a before b in parameter order)."""
    rt = f"{abs(r):.3g}"
    if scales_of[a] == "log" and scales_of[b] == "log":
        if rt == "1":
            text = f"{a}/{b}" if r > 0 else f"{a}*{b}"
        else:
            text = f"{a}/{b}^{rt}" if r > 0 else f"{a}*{b}^{rt}"
        return {"combination": text, "form": "power", "exponents": {a: 1.0, b: float(-r)}, "evidence": evidence}
    return {"combination": f"{_coord(a, scales_of[a])} - {r:.3g}*{_coord(b, scales_of[b])}", "form": "linear",
            "evidence": evidence}


def screen_objects(degenerate, names, scales):
    """Object-form entries (evidence fisher-screen, no valid_range) of the flat directions of fisher_screen."""
    scales_of = dict(zip(names, scales))
    out = []
    for _, v, _ in degenerate:
        inv = [i for i in range(len(names)) if abs(v[i]) > INVOLVED]
        if len(inv) == 2:
            i, j = inv
            out.append(_pair_object(names[i], names[j], float(v[i] / v[j]), scales_of, "fisher-screen"))
        elif len(inv) == 1:
            out.append({"combination": names[inv[0]], "form": "single", "evidence": "fisher-screen"})
        else:
            comps = ", ".join(f"{v[i]:.3g}" for i in inv)
            coords = ", ".join(_coord(names[i], scales[i]) for i in inv)
            out.append({"combination": f"flat direction in ({coords}) along ({comps})", "form": "direction",
                        "evidence": "fisher-screen"})
    return out


# --------------------------------------------------------------------------- level 2: profile-likelihood scans
def _num(x, what):
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
        raise ScanInputError(f"{what} must be a finite number")
    return float(x)


def parse_scan(spec, names):
    """Check a scan specification against the parameter names; returns it normalized (raises ScanInputError)."""
    if not isinstance(spec, dict):
        raise ScanInputError("degeneracy_scan must be a JSON object")
    known = {"parameter", "direction", "plane", "values", "points", "threshold", "broken_by"}
    extra = sorted(set(spec) - known)
    if extra:
        raise ScanInputError(f"degeneracy_scan: unknown keys {extra}; allowed {sorted(known)}")
    modes = [m for m in ("parameter", "direction", "plane") if m in spec]
    if len(modes) != 1:
        raise ScanInputError("degeneracy_scan needs exactly one of 'parameter', 'direction', 'plane'")
    mode = modes[0]
    out = {"mode": mode, "threshold": THRESHOLD, "broken_by": None}
    if "threshold" in spec:
        out["threshold"] = _num(spec["threshold"], "degeneracy_scan.threshold")
        if out["threshold"] <= 0:
            raise ScanInputError("degeneracy_scan.threshold must be > 0")
    if "broken_by" in spec:
        bb = spec["broken_by"]
        if not isinstance(bb, list) or not all(isinstance(s, str) and s for s in bb):
            raise ScanInputError("degeneracy_scan.broken_by must be a list of observable names")
        out["broken_by"] = list(bb)
    points = spec.get("points")
    if mode == "parameter":
        if spec["parameter"] not in names:
            raise ScanInputError(f"degeneracy_scan.parameter {spec['parameter']!r} is not one of {names}")
        out["parameter"] = spec["parameter"]
    elif mode == "plane":
        pl = spec["plane"]
        if not (isinstance(pl, list) and len(pl) == 2 and all(p in names for p in pl) and pl[0] != pl[1]):
            raise ScanInputError(f"degeneracy_scan.plane must name two different parameters of {names}")
        out["plane"] = list(pl)
    else:
        d = spec["direction"]
        if d != "fisher":
            if not isinstance(d, dict) or not d or set(d) - set(names):
                raise ScanInputError(f"degeneracy_scan.direction must be 'fisher' or {{name: component}} over {names}")
            comps = [_num(d.get(nm, 0.0), f"degeneracy_scan.direction.{nm}") for nm in names]
            if not any(comps):
                raise ScanInputError("degeneracy_scan.direction must not be zero")
            d = comps
        out["direction"] = d
    if "values" in spec:
        vals = spec["values"]
        if mode == "plane":
            if not (isinstance(vals, list) and len(vals) == 2 and all(isinstance(v, list) and len(v) >= 2 for v in vals)):
                raise ScanInputError("degeneracy_scan.values for a plane must be two lists of at least two values")
            out["values"] = [[_num(x, "degeneracy_scan.values") for x in v] for v in vals]
        else:
            if not isinstance(vals, list) or len(vals) < 2:
                raise ScanInputError("degeneracy_scan.values must be a list of at least two values")
            out["values"] = [_num(x, "degeneracy_scan.values") for x in vals]
    else:
        default = 21 if mode == "plane" else 41
        if points is None:
            points = [default, default] if mode == "plane" else default
        if mode == "plane" and isinstance(points, int) and not isinstance(points, bool):
            points = [points, points]
        flat = points if isinstance(points, list) else [points]
        if not all(isinstance(x, int) and not isinstance(x, bool) and 3 <= x <= 401 for x in flat) or \
                (mode == "plane") != isinstance(points, list) or (mode == "plane" and len(points) != 2):
            raise ScanInputError("degeneracy_scan.points must be an integer in [3, 401] (two for a plane)")
        out["points"] = points
    return out


def _to_fit(x, scale, what):
    if scale == "log":
        if x <= 0:
            raise ScanInputError(f"{what}: a log axis needs values > 0")
        return math.log(x)
    return float(x)


def _natural(t, scale):
    return float(math.exp(t)) if scale == "log" else float(t)


def _axis_values(i, scan_values, points, lo, hi, scales, names):
    if scan_values is None:
        return np.linspace(lo[i], hi[i], points)
    vals = np.array([_to_fit(x, scales[i], f"degeneracy_scan.values of {names[i]}") for x in scan_values])
    span = hi[i] - lo[i]
    if np.any(vals < lo[i] - 1e-12 * span) or np.any(vals > hi[i] + 1e-12 * span) or np.any(np.diff(vals) <= 0):
        raise ScanInputError(f"degeneracy_scan.values of {names[i]} must increase and lie inside the box "
                             f"[{_natural(lo[i], scales[i]):.6g}, {_natural(hi[i], scales[i]):.6g}]")
    return np.clip(vals, lo[i], hi[i])


def _minimize(objective, starts, bounds):
    """Lowest L-BFGS-B minimum over the starts; an abnormal stop is restarted once from where it stopped, and counts
    as converged when the restart does not move it (a stall at the minimum)."""
    opts = {"ftol": 1e-14, "gtol": 1e-10, "maxiter": 2000}
    best = None
    for s in starts:
        res = optimize.minimize(objective, s, method="L-BFGS-B", bounds=bounds, options=opts)
        how = "optimizer" if res.success else None
        if not res.success:
            again = optimize.minimize(objective, np.asarray(res.x, dtype=float), method="L-BFGS-B", bounds=bounds, options=opts)
            if again.success:
                res, how = again, "optimizer-after-restart"
            elif abs(float(again.fun) - float(res.fun)) <= 1e-10 * (1.0 + abs(float(res.fun))):
                res, how = again, "restart-stationary"
            else:
                res = again
        if best is None or float(res.fun) < best[0]:
            best = (float(res.fun), np.asarray(res.x, dtype=float), how)
    return best


def _profile_points(m2ll, p_hat, bounds, fixed_idx, fixed_rows):
    """Profile at each row of fixed values (fit coordinates) of the coordinates fixed_idx; warm-started along the scan."""
    ntot = len(p_hat)
    free = [j for j in range(ntot) if j not in fixed_idx]
    fb = [bounds[j] for j in free]
    out, prev = [], None
    for row in fixed_rows:
        def full(z, row=row):
            q = np.array(p_hat, dtype=float)
            q[list(fixed_idx)] = row
            q[free] = z
            return q
        if not free:
            q = full(np.zeros(0))
            out.append((float(m2ll(q)), q, "evaluated"))
            continue
        starts = [np.array(p_hat, dtype=float)[free]] + ([prev] if prev is not None else [])
        starts = [np.array([min(max(x, lo if lo is not None else -np.inf), hi if hi is not None else np.inf)
                            for x, (lo, hi) in zip(s, fb)]) for s in starts]
        val, z, how = _minimize(lambda z: m2ll(full(z)), starts, fb)
        prev = z
        out.append((val, full(z), how))
    return out


def _direction_points(m2ll, p_hat, bounds, k, d, ts):
    """Profile on the line p_hat + t d (grid coordinates; d a unit vector), the orthogonal complement and the
    remaining (nuisance) coordinates free; the box is kept by a penalty (the model is never evaluated outside)."""
    ntot = len(p_hat)
    lo = np.array([b[0] for b in bounds[:k]], dtype=float)
    hi = np.array([b[1] for b in bounds[:k]], dtype=float)
    span = hi - lo
    q_full = np.linalg.svd(d.reshape(1, -1))[2]
    comp = q_full[1:].T                      # k x (k-1) orthonormal complement of d
    extra = list(range(k, ntot))
    out, prev = [], None
    for t in ts:
        def full(z, t=t):
            q = np.array(p_hat, dtype=float)
            q[:k] = p_hat[:k] + t * d + comp @ z[:k - 1]
            q[extra] = z[k - 1:]
            return q

        def penalized(z):
            q = full(z)
            c = np.clip(q[:k], lo, hi)
            pen = PENALTY * float(np.sum(((q[:k] - c) / span) ** 2))
            q[:k] = c
            return float(m2ll(q)) + pen
        z0 = np.concatenate([np.zeros(k - 1), np.array(p_hat, dtype=float)[extra]])
        starts = [z0] + ([prev] if prev is not None else [])
        val, z, how = _minimize(penalized, starts, None)
        prev = z
        q = full(z)
        inside = bool(np.all(q[:k] >= lo - 1e-9 * span) and np.all(q[:k] <= hi + 1e-9 * span))
        out.append((val, np.concatenate([np.clip(q[:k], lo, hi), q[k:]]), how if inside else None))
    return out


def _slope(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    xm = x - x.mean()
    den = float(xm @ xm)
    return float(xm @ (y - y.mean()) / den) if den > 0 else 0.0


def _objects_from_path(path, pivot, names, scales, valid_range, broken_by):
    """Entries (evidence profile-scan) for each parameter that moves with the pivot along the flat path."""
    scales_of = dict(zip(names, scales))
    objs = []
    for j in range(len(names)):
        if j == pivot:
            continue
        s = _slope(path[:, pivot], path[:, j])          # d coord(j) / d coord(pivot)
        if abs(s) < MOVES:
            continue
        a, b = (j, pivot) if j < pivot else (pivot, j)
        r = s if j < pivot else 1.0 / s                 # d coord(a) = r d coord(b)
        entry = _pair_object(names[a], names[b], r, scales_of, "profile-scan")
        entry["valid_range"] = {names[a]: dict(valid_range[names[a]]), names[b]: dict(valid_range[names[b]])}
        if broken_by:
            entry["broken_by"] = list(broken_by)
        objs.append(entry)
    return objs


def _one_d(points, s_values, k, names, scales, threshold, m_ref):
    """Valid region of a 1-D scan: contiguous points around the minimum within threshold; interpolated ends."""
    deltas = np.array([v - m_ref for v, _, _ in points])
    thetas = np.array([q[:k] for _, q, _ in points])
    j0 = int(np.argmin(deltas))
    lo_i = hi_i = j0
    while lo_i > 0 and deltas[lo_i - 1] <= threshold:
        lo_i -= 1
    while hi_i < len(deltas) - 1 and deltas[hi_i + 1] <= threshold:
        hi_i += 1

    def end(i_in, i_out):
        if i_out is None:
            return thetas[i_in], float(s_values[i_in]), "scan-edge"
        f = (threshold - deltas[i_in]) / (deltas[i_out] - deltas[i_in])
        return (thetas[i_in] + f * (thetas[i_out] - thetas[i_in]),
                float(s_values[i_in] + f * (s_values[i_out] - s_values[i_in])), "threshold")
    t_lo, s_lo, kind_lo = end(lo_i, lo_i - 1 if lo_i > 0 else None)
    t_hi, s_hi, kind_hi = end(hi_i, hi_i + 1 if hi_i < len(deltas) - 1 else None)
    path = np.vstack([t_lo, thetas[lo_i:hi_i + 1], t_hi])
    vr = {}
    for i, nm in enumerate(names):
        a, b = _natural(float(path[:, i].min()), scales[i]), _natural(float(path[:, i].max()), scales[i])
        vr[nm] = {"min": a, "max": b}
    return deltas, path, vr, (s_lo, s_hi), (kind_lo, kind_hi), hi_i > lo_i


def profile_scan(m2ll, p_hat, bounds, names, scales, scan, m2ll_min, degenerate=()):
    """Level 2. m2ll(theta) on the full fit vector (grid coordinates first, then any free nuisance); p_hat the best fit;
    bounds per coordinate ((lo, hi), None for unbounded); scan from parse_scan. Returns (entries, scans, warnings)."""
    k = len(names)
    lo = np.array([b[0] for b in bounds[:k]], dtype=float)
    hi = np.array([b[1] for b in bounds[:k]], dtype=float)
    thr = scan["threshold"]
    entries, scans, warnings = [], [], []
    jobs = []
    if scan["mode"] == "parameter":
        jobs.append(("parameter", names.index(scan["parameter"])))
    elif scan["mode"] == "plane":
        jobs.append(("plane", tuple(names.index(nm) for nm in scan["plane"])))
    elif scan["direction"] == "fisher":
        for _, v, _ in degenerate:
            jobs.append(("direction", np.asarray(v, dtype=float)))
        if not jobs:
            warnings.append("degeneracy_scan direction 'fisher': the Fisher screen found no flat direction; nothing "
                            "scanned")
    else:
        jobs.append(("direction", np.asarray(scan["direction"], dtype=float)))
    for kind, what in jobs:
        rec = {"mode": kind, "threshold": thr}
        if kind == "parameter":
            i = what
            s_vals = _axis_values(i, scan.get("values"), scan.get("points"), lo, hi, scales, names)
            pts = _profile_points(m2ll, p_hat, bounds, [i], [[s] for s in s_vals])
            rec.update(parameter=names[i], coordinate=_coord(names[i], scales[i]))
            pivot = i
        elif kind == "direction":
            d = what / np.linalg.norm(what)
            span = hi - lo
            with np.errstate(divide="ignore"):
                t_lo = max(((lo[j] - p_hat[j]) / d[j]) if d[j] > 0 else ((hi[j] - p_hat[j]) / d[j])
                           for j in range(k) if abs(d[j]) > 1e-12 * span[j])
                t_hi = min(((hi[j] - p_hat[j]) / d[j]) if d[j] > 0 else ((lo[j] - p_hat[j]) / d[j])
                           for j in range(k) if abs(d[j]) > 1e-12 * span[j])
            if scan.get("values") is not None:
                s_vals = np.array(scan["values"], dtype=float)
                if np.any(s_vals < t_lo - 1e-9) or np.any(s_vals > t_hi + 1e-9) or np.any(np.diff(s_vals) <= 0):
                    raise ScanInputError(f"degeneracy_scan.values (distances along the direction) must increase and "
                                         f"lie in [{t_lo:.6g}, {t_hi:.6g}]")
            else:
                s_vals = np.linspace(t_lo, t_hi, scan["points"])
            pts = _direction_points(m2ll, p_hat, bounds, k, d, s_vals)
            rec.update(direction={_coord(nm, sc): float(c) for nm, sc, c in zip(names, scales, d)},
                       coordinate="distance along the unit direction in the fit coordinates, from the best fit")
            pivot = int(np.argmax(np.abs(d)))
        else:
            i, j = what
            pts_ax = scan.get("points") or [None, None]
            va = _axis_values(i, (scan.get("values") or [None, None])[0], pts_ax[0], lo, hi, scales, names)
            vb = _axis_values(j, (scan.get("values") or [None, None])[1], pts_ax[1], lo, hi, scales, names)
            rows = [[a, b] for a in va for b in vb]
            pts = _profile_points(m2ll, p_hat, bounds, [i, j], rows)
            rec.update(plane=[names[i], names[j]])
            pivot = i
        unconverged = sum(1 for _, _, how in pts if how is None)
        m_ref = min([m2ll_min] + [v for v, _, how in pts if how is not None])
        if m_ref < m2ll_min - 1e-6 * (1.0 + abs(m2ll_min)):
            warnings.append(f"the {kind} scan found a lower -2 ln L than the fit ({m_ref:.6g} < {m2ll_min:.6g}); "
                            "deltas are taken from the scan minimum")
        rec["unconverged_points"] = unconverged
        if kind in ("parameter", "direction"):
            deltas, path, vr, (s_lo, s_hi), ends, wide = _one_d(pts, s_vals, k, names, scales, thr, m_ref)
            if kind == "parameter":
                s_nat = [_natural(s, scales[pivot]) for s in s_vals]
                rec["flat_interval"] = {"min": _natural(s_lo, scales[pivot]), "max": _natural(s_hi, scales[pivot])}
            else:
                s_nat = [float(s) for s in s_vals]
                rec["flat_interval"] = {"min": s_lo, "max": s_hi}
            rec["range_ends"] = {"min": ends[0], "max": ends[1]}
            rec["points"] = [{"scan_value": s, "delta_m2ll": float(dl),
                              "parameters": {nm: _natural(float(q[n]), sc) for n, (nm, sc) in enumerate(zip(names, scales))},
                              "converged_by": how} for s, dl, (_, q, how) in zip(s_nat, deltas, pts)]
        else:
            deltas = np.array([v - m_ref for v, _, _ in pts]).reshape(len(va), len(vb))
            inside = deltas <= thr
            comp = np.zeros_like(inside)
            stack = [tuple(np.unravel_index(int(np.argmin(deltas)), deltas.shape))]
            while stack:
                a, b = stack.pop()
                if 0 <= a < len(va) and 0 <= b < len(vb) and inside[a, b] and not comp[a, b]:
                    comp[a, b] = True
                    stack += [(a + da, b + db) for da in (-1, 0, 1) for db in (-1, 0, 1) if da or db]
            thetas = np.array([q[:k] for _, q, _ in pts]).reshape(len(va), len(vb), k)
            sel = thetas[comp]
            vr = {nm: {"min": _natural(float(sel[:, n].min()), sc), "max": _natural(float(sel[:, n].max()), sc)}
                  for n, (nm, sc) in enumerate(zip(names, scales))}
            rows_in = [int(np.argmin(np.where(comp[a], deltas[a], np.inf))) for a in range(len(va)) if comp[a].any()]
            path = np.array([thetas[a, b] for a, b in zip([a for a in range(len(va)) if comp[a].any()], rows_in)])
            wide = int(comp.sum()) > 1 and len(path) > 1
            rec["range_ends"] = "scan points (a plane is not interpolated)"
            rec["axes"] = {names[i]: [_natural(float(x), scales[i]) for x in va],
                           names[j]: [_natural(float(x), scales[j]) for x in vb]}
            rec["delta_m2ll"] = deltas.tolist()
        rec["valid_range"] = vr
        rec["degenerate"] = bool(wide)
        if unconverged:
            warnings.append(f"the {kind} scan has {unconverged} unconverged profile point(s); no degeneracy is "
                            "concluded from it")
            rec["degenerate"] = False
        elif wide:
            objs = _objects_from_path(path, pivot, names, scales, vr, scan.get("broken_by"))
            if not objs:
                warnings.append(f"the profile is flat along {names[pivot]} without another parameter moving with it: "
                                f"{names[pivot]} is unconstrained in its flat interval, not degenerate with another "
                                "parameter")
            entries += objs
            rec["entries"] = len(objs)
        scans.append(rec)
    return entries, scans, warnings


# --------------------------------------------------------------------------- built-in synthetic study (CLI)
CURVED = {"edges_gv": [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0], "norm": 0.3, "slope": 0.45,
          "exponent": 1.2, "onset_kpc": 6.0, "scale_kpc": 2.0, "tilt": 0.05,
          "truth": {"D0_cm2_s": 3.0e28, "L_kpc": 4.0},
          "box": {"D0_cm2_s": [1.0e28, 1.2e29], "L_kpc": [2.0, 10.0]},
          "uncorrelated": 0.02, "correlated": 0.01}


def curved_prediction(d0_cm2_s, l_kpc):
    """The synthetic-curved study's prediction in its 7 bins (see the module doc); SYNTHETIC."""
    c = CURVED
    edges = np.array(c["edges_gv"])
    r = np.sqrt(edges[:-1] * edges[1:])
    lr = np.log(r)
    h = (lr - lr.mean()) / (0.5 * (lr.max() - lr.min()))
    u_true = c["truth"]["D0_cm2_s"] / c["truth"]["L_kpc"] ** c["exponent"]
    b = c["tilt"] * (max(l_kpc - c["onset_kpc"], 0.0) / c["scale_kpc"]) ** 2
    return c["norm"] * (r / 10.0) ** (-c["slope"]) * (u_true / (d0_cm2_s / l_kpc ** c["exponent"])) * (1.0 + b * h)


def synthetic_curved(points=41, threshold=THRESHOLD):
    c = CURVED
    names, scales = ["D0_cm2_s", "L_kpc"], ["log", "log"]

    def predict(theta):
        return curved_prediction(math.exp(theta[0]), math.exp(theta[1]))

    truth = np.log([c["truth"]["D0_cm2_s"], c["truth"]["L_kpc"]])
    y = predict(truth)                                         # Asimov
    cov = np.diag((c["uncorrelated"] * y) ** 2) + np.outer(c["correlated"] * y, c["correlated"] * y)
    cinv = np.linalg.inv(cov)

    def m2ll(theta):
        res = y - predict(theta)
        return float(res @ cinv @ res)
    lo = np.log([c["box"]["D0_cm2_s"][0], c["box"]["L_kpc"][0]])
    hi = np.log([c["box"]["D0_cm2_s"][1], c["box"]["L_kpc"][1]])
    bounds = list(zip(lo, hi))
    m_min, p_hat, how = _minimize(m2ll, [truth], bounds)
    step = 1e-4
    jac = np.column_stack([(predict(p_hat + step * e) - predict(p_hat - step * e)) / (2 * step) for e in np.eye(2)])
    fisher = jac.T @ cinv @ jac
    cond, eig, degenerate, _ = fisher_screen(fisher, names, hi - lo)
    level1 = screen_objects(degenerate, names, scales)
    scan = parse_scan({"parameter": "L_kpc", "points": points, "threshold": threshold}, names)
    level2, scans, warnings = profile_scan(m2ll, p_hat, bounds, names, scales, scan, m_min, degenerate)
    at8 = _profile_points(m2ll, p_hat, bounds, [1], [[math.log(8.0)]])[0]
    at6 = _profile_points(m2ll, p_hat, bounds, [1], [[math.log(6.0)]])[0]
    failed = any(s["unconverged_points"] for s in scans) or how is None
    return {"label": LABEL, "status": "failed" if failed else "ok", "study": "synthetic-curved",
            "synthetic": True, "data": "asimov",
            "model": {"description": "y_i = norm (R_i / 10 GV)^-slope (u_true / u) (1 + b(L) h_i), u = D0_cm2_s / "
                                     "L_kpc^exponent, b(L) = tilt ((L - onset_kpc) / scale_kpc)^2 above onset_kpc, 0 below; "
                                     "h_i the centred, unit half-range tilt in ln R_i",
                      **{key: c[key] for key in ("edges_gv", "norm", "slope", "exponent", "onset_kpc", "scale_kpc",
                                                 "tilt", "truth", "box", "uncorrelated", "correlated")}},
            "best_fit": {nm: _natural(float(t), sc) for nm, sc, t in zip(names, scales, p_hat)},
            "m2ll_min": m_min, "optimizer": how,
            "fisher": {"coordinates": [_coord(nm, sc) for nm, sc in zip(names, scales)], "matrix": fisher.tolist(),
                       "condition_number": cond, "eigen": eig,
                       "method": "J^T C^-1 J at the best fit, J by central differences (step 1e-4 in the fit coordinates)"},
            "degeneracies": level1 + level2, "profile_scans": scans, "warnings": warnings,
            "checks": {"delta_m2ll_profiled_at_L_kpc_6": at6[0] - m_min, "delta_m2ll_profiled_at_L_kpc_8": at8[0] - m_min},
            "note": "SYNTHETIC: the Fisher screen (local, at the best fit) finds the flat direction and its local "
                    "exponent but not where it holds; the profile scan over L_kpc (D0_cm2_s profiled) gives the range "
                    "where delta -2 ln L stays within the threshold. Exact degeneracy up to 6 kpc; the spectral tilt "
                    "above 6 kpc breaks it (delta at 8 kpc in checks)"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    sc = sub.add_parser("synthetic-curved", help="built-in SYNTHETIC study: D0_cm2_s proportional to L_kpc^1.2 up to "
                                                 "6 kpc, broken above (Fisher screen and profile scan in one output)")
    sc.add_argument("--points", type=int, default=41, help="scan points over L_kpc (3-401)")
    sc.add_argument("--threshold", type=float, default=THRESHOLD, help="delta -2 ln L of the flat region (> 0)")
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy and SciPy are required"}))
        return 2
    try:
        if not 3 <= a.points <= 401 or not (math.isfinite(a.threshold) and a.threshold > 0):
            raise ScanInputError("--points must be in [3, 401] and --threshold > 0")
        out = synthetic_curved(a.points, a.threshold)
    except ScanInputError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
