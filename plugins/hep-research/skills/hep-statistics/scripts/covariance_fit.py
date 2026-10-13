#!/usr/bin/env python3
"""Fits to correlated measurements with a stated covariance model (hep-statistics audit T18, T19). Needs NumPy, SciPy.

What it enforces:
- known linear constraints (for example a normalized spectrum, sum = 1) are declared, verified to be null directions
  of the covariance, and the fit is done in the complementary subspace: chi2 and its degrees of freedom are counted
  there (n - constraints - free parameters seen by the data). A covariance singular beyond the declared constraints is
  refused; nothing is regularized silently. A near-singular one (condition number above 1e10 in the subspace) is fitted
  and reported with its condition number;
- a covariance that depends on the parameters, C(theta), uses the Gaussian likelihood
  -2 ln L = r^T C^-1 r + ln det C; leaving out ln det C (logdet=False) is available only as a negative baseline;
- multiplicative uncertainties (a normalization known to a fraction) are declared as such. cov_mode "data" scales them
  with the measured values (D'Agostini's warning: biased low, Peelle's pertinent puzzle), "model" with the fitted
  prediction (C(theta), with ln det), "nuisance" fits the normalization as an explicit parameter with its Gaussian
  constraint. "data" is never chosen by default. Measured on the Peelle setup (two measurements, 15% and 10% errors,
  20% common normalization, 1000 toys; tests/skills/hep_statistics/test_covariance_fit.py): "data" is biased by
  -0.043 +- 0.007, "model" by -0.039 +- 0.007 (a common normalization is not an additive Gaussian error, so the
  Gaussian likelihood with C(theta) is misspecified), "nuisance" by -0.002 +- 0.007: use "nuisance" for a common
  normalization; "model" is the right likelihood only when the covariance truly is Gaussian with a theta dependence.

Units: rescaling y by a and C by a^2 leaves the parameters of a scale-covariant model (rescaled), chi2 and dof unchanged.

Input (fit): {"y": [...], "cov": [[...]] (additive part), "x": [...] (abscissa, for the models),
  "model": "constant" | "line" | "exponential-normalized" (p_i = exp(-b x_i) / sum_k exp(-b x_k), parameter b),
  "constraints": [[a_1, ..., a_n], ...] (optional rows: a . y = const), "start": [...],
  "multiplicative": {"relative_cov": [[...]], "mode": "data" | "model" | "nuisance"} (optional)}

  "model_options": {"smoothness": s} for smoothly-broken-power-law, {"plugin": {"path", "function", "n_params"}} for
  plugin (a Python file defining function(theta, x) -> n predictions; it runs with your permissions)}
Models with x > 0: broken-power-law (sharp) and smoothly-broken-power-law, theta = [ln A, gamma1, gamma2, ln x_b],
  ln F = ln A - gamma1 (u - h) - gamma2 h, u = ln(x / x_b), h = max(u, 0) or s ln((1 + e^(u/s)) / 2); give start.
Input (break-scan): {"y", "cov", "x", "smoothness": 0 (sharp), "break_range": [lo, hi], "grid_points": 40}: the profile
  chi2 over ln x_b, a toy-calibrated interval for the break (not Wilks: the break is not a regular parameter) and the
  toy-calibrated no-break test.

Usage: covariance_fit.py fit --input FILE
       covariance_fit.py break-scan --input FILE [--toys 200 --seed 1 --cl 0.6827]
Exit codes: 0 fitted; 1 refused (covariance singular beyond the declared constraints, a declared constraint that is not a
null direction, no convergence); 2 bad input. Output JSON labelled [General method].
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
    from scipy import optimize
except ImportError:  # pragma: no cover
    np = optimize = None  # type: ignore[assignment]

LABEL = "[General method]"
COND_WARN = 1e10
NULL_TOL = 1e-9


class CovFitError(ValueError):
    """Refused input or a fit that cannot be done without an undeclared assumption."""


class CovFitInputError(CovFitError):
    """A malformed input (exit 2), as opposed to a refused fit (exit 1)."""


def subspace(cov: np.ndarray, constraints) -> tuple[np.ndarray, dict]:
    """Orthonormal basis Q of the complement of the declared constraint rows, after checking each row is a null direction
    of cov; returns Q and a record (rank, condition number in the subspace)."""
    n = cov.shape[0]
    scale = float(np.max(np.abs(cov))) or 1.0
    rows = np.atleast_2d(np.asarray(constraints, dtype=float)) if constraints else np.zeros((0, n))
    for k, a in enumerate(rows):
        resid = np.linalg.norm(cov @ a) / (np.linalg.norm(a) * scale)
        if resid > NULL_TOL:
            raise CovFitError(f"declared constraint {k} is not a null direction of the covariance (|C a| / (|a| max|C|) = {resid:.2e})")
    if rows.shape[0]:
        u, s, vt = np.linalg.svd(rows)
        q = vt[rows.shape[0]:].T
    else:
        q = np.eye(n)
    cr = q.T @ cov @ q
    ev = np.linalg.eigvalsh(0.5 * (cr + cr.T))
    if ev[0] <= 1e-14 * max(ev[-1], 1e-300):
        raise CovFitError(f"the covariance is singular beyond the {rows.shape[0]} declared constraint(s) (smallest/largest "
                          f"eigenvalue in the subspace {ev[0] / ev[-1]:.2e}); declare the constraint or fix the covariance; "
                          "it is not regularized")
    cond = float(ev[-1] / ev[0])
    return q, {"n": n, "constraints": int(rows.shape[0]), "rank_in_subspace": int(q.shape[1]), "condition_number": cond,
               "near_singular": cond > COND_WARN}


def break_shape(u, smoothness=0.0):
    """h(u) of the broken power law, u = ln(x / x_b): max(u, 0) for a sharp break, s ln((1 + e^(u/s)) / 2) for a
    smooth one with smoothness s > 0 (which tends to the sharp form as s -> 0)."""
    u = np.asarray(u, dtype=float)
    if smoothness <= 0:
        return np.maximum(u, 0.0)
    return smoothness * (np.logaddexp(0.0, u / smoothness) - math.log(2.0))


def bpl_log(theta, x, smoothness=0.0):
    """ln F of the broken power law, theta = [ln A, gamma1, gamma2, ln x_b]:
    ln F = ln A - gamma1 (u - h(u)) - gamma2 h(u), u = ln(x / x_b) (STH-T3.13). F(x_b) = A for the sharp form; the
    index is gamma1 below and gamma2 above the break. The same parametrization is proposed to hep-analysis for
    cr_spectrum_powerlaw_fit.py (order question Q8)."""
    u = np.log(np.asarray(x, dtype=float)) - theta[3]
    h = break_shape(u, smoothness)
    return theta[0] - theta[1] * (u - h) - theta[2] * h


def _plugin(spec, n):
    """A user model: {"path": "model.py", "function": "predict", "n_params": k}; predict(theta, x) -> n values."""
    import importlib.util
    if not isinstance(spec, dict) or not all(k in spec for k in ("path", "function", "n_params")):
        raise CovFitInputError('a plugin model needs {"path", "function", "n_params"}')
    path = Path(spec["path"])
    if not path.is_file():
        raise CovFitInputError(f"plugin file {path} not found")
    mod_spec = importlib.util.spec_from_file_location("covariance_fit_plugin", path)
    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)  # type: ignore[union-attr]
    fn = getattr(mod, spec["function"], None)
    k = spec["n_params"]
    if not callable(fn) or not (isinstance(k, int) and k >= 1):
        raise CovFitInputError("the plugin function must exist and n_params must be a positive integer")

    def f(th):
        out = np.asarray(fn(np.asarray(th, dtype=float), _plugin_x), dtype=float)
        if out.shape != (n,) or not np.all(np.isfinite(out)):
            raise CovFitError(f"the plugin returned {out.shape} or non-finite values; expected {n} finite values")
        return out
    return f, k


_plugin_x: object = None


def model_fn(name, x, options=None):
    """Prediction function and parameter count. Models: constant, line, exponential-normalized, broken-power-law
    (sharp), smoothly-broken-power-law (options.smoothness), plugin (options.plugin, see _plugin)."""
    global _plugin_x
    x = np.asarray(x, dtype=float)
    options = options or {}
    if name in ("broken-power-law", "smoothly-broken-power-law"):
        if np.any(x <= 0):
            raise CovFitInputError("a power law needs positive abscissae")
        sm = 0.0 if name == "broken-power-law" else options.get("smoothness")
        if name == "smoothly-broken-power-law" and not (isinstance(sm, (int, float)) and sm > 0):
            raise CovFitInputError("smoothly-broken-power-law needs model_options.smoothness > 0")
        return (lambda th: np.exp(bpl_log(th, x, float(sm)))), 4
    if name == "plugin":
        _plugin_x = x
        return _plugin(options.get("plugin"), len(x))
    if name == "constant":
        return (lambda th: np.full(len(x), th[0])), 1
    if name == "line":
        return (lambda th: th[0] + th[1] * x), 2
    if name == "exponential-normalized":
        def f(th):
            w = np.exp(-th[0] * (x - x[0]))
            return w / w.sum()
        return f, 1
    raise CovFitError(f"unknown model {name!r}")


def _hessian(fun, x, rel=1e-4):
    """Central finite-difference Hessian of a scalar function (the BFGS inverse-Hessian estimate is not an error)."""
    x = np.asarray(x, dtype=float)
    h = rel * np.maximum(np.abs(x), 1e-2)
    k = len(x)
    out = np.zeros((k, k))
    for i in range(k):
        for j in range(i, k):
            def at(si, sj):
                z = x.copy()
                z[i] += si * h[i]
                z[j] += sj * h[j]
                return fun(z)
            v = (at(1, 1) - at(1, -1) - at(-1, 1) + at(-1, -1)) / (4 * h[i] * h[j])
            out[i, j] = out[j, i] = v
    return out


EDM_MAX = 2e-5  # in -2 ln L units: 1e-5 in NLL, as core/stats/fit_diagnostics.py


def _verdict(fun, x):
    """Gradient, Hessian and EDM at x; refuses a non-positive-definite Hessian or EDM above EDM_MAX."""
    x = np.asarray(x, dtype=float)
    h = 1e-5 * np.maximum(np.abs(x), 1e-2)
    g = np.array([(fun(x + e) - fun(x - e)) / (2 * e[i]) for i, e in enumerate(np.diag(h))])
    hess = _hessian(fun, x)
    try:
        np.linalg.cholesky(hess)
    except np.linalg.LinAlgError:
        raise CovFitError("the Hessian at the fitted point is not positive definite (a flat or unconstrained direction)") from None
    edm = 0.5 * float(g @ np.linalg.solve(hess, g))
    if not edm <= EDM_MAX:
        raise CovFitError(f"the fit did not converge (EDM {edm:.2e} > {EDM_MAX:g})")
    return hess, edm


def _cov_at(cov_add, rel, mode, y, pred, f_scale=None):
    if rel is None:
        return cov_add
    base = y if mode == "data" else pred
    return cov_add + rel * np.outer(base, base)


def fit(y, cov, model="constant", x=None, constraints=None, start=None, multiplicative=None, logdet=True,
        model_options=None) -> dict:
    y = np.asarray(y, dtype=float)
    cov = np.asarray(cov, dtype=float)
    n = len(y)
    if cov.shape != (n, n) or not np.allclose(cov, cov.T, rtol=1e-12, atol=0):
        raise CovFitError("cov must be a symmetric n x n matrix")
    x = np.arange(n, dtype=float) if x is None else np.asarray(x, dtype=float)
    f, npar = model_fn(model, x, model_options)
    rel, mode = None, None
    if multiplicative:
        rel = np.asarray(multiplicative["relative_cov"], dtype=float)
        # STH-T3.6: n x n, finite, symmetric and positive semidefinite on its correlation scale (the
        # validate_covariance.py rule); a 1 x 1 matrix is never broadcast to every pair of points
        if rel.shape != (n, n) or not np.all(np.isfinite(rel)):
            raise CovFitInputError(f"multiplicative.relative_cov must be a finite {n} x {n} matrix, got shape {list(rel.shape)}")
        if not np.allclose(rel, rel.T, rtol=1e-10, atol=1e-15 * max(float(np.max(np.abs(rel))), 1e-300)):
            raise CovFitInputError("multiplicative.relative_cov must be symmetric")
        d = np.sqrt(np.clip(np.diag(rel), 0.0, None))
        if np.any(np.diag(rel) < 0):
            raise CovFitInputError("multiplicative.relative_cov has a negative variance")
        nz = d > 0
        if nz.any():
            corr = rel[np.ix_(nz, nz)] / np.outer(d[nz], d[nz])
            if np.linalg.eigvalsh(corr)[0] < -1e-8 * max(1.0, float(np.linalg.eigvalsh(corr)[-1])):
                raise CovFitInputError("multiplicative.relative_cov is not positive semidefinite")
        mode = multiplicative.get("mode")
        if mode not in ("data", "model", "nuisance"):
            raise CovFitError("multiplicative.mode must be data, model or nuisance (no default)")
    q, info = subspace(cov if rel is None or mode == "nuisance" else cov + rel * np.outer(y, y), constraints)
    if start is None and model in ("broken-power-law", "smoothly-broken-power-law"):
        raise CovFitInputError("a broken power law needs start [ln A, gamma1, gamma2, ln x_b] (or use break-scan)")
    th0 = np.asarray(start if start is not None else ([float(np.mean(y))] + [0.0] * (npar - 1)), dtype=float)

    if mode == "nuisance":
        # one multiplicative factor f per independent component of rel (here: rel must be rank one, a common scale)
        ev, evec = np.linalg.eigh(rel)
        if ev[-1] <= 0 or np.sum(ev > 1e-12 * ev[-1]) != 1:
            raise CovFitError("nuisance mode needs a rank-one relative covariance (one common normalization)")
        u = evec[:, -1] * math.sqrt(ev[-1])        # relative shift per unit of the nuisance

        def m2ll(p):
            th, z = p[:npar], p[npar]
            pred = f(th) * (1.0 + z * u)
            r = q.T @ (y - pred)
            cr = q.T @ cov @ q
            return float(r @ np.linalg.solve(cr, r)) + z * z
        res = optimize.minimize(m2ll, np.append(th0, 0.0), method="BFGS", options={"gtol": 1e-8})
        p = res.x
        theta, chi2 = p[:npar], float(res.fun)
        hess, edm = _verdict(m2ll, p)
        cov_theta = 2.0 * np.linalg.inv(hess)[:npar, :npar]
        extra = {"normalization_nuisance": float(p[npar])}
        dof = info["rank_in_subspace"] - npar
    else:
        def m2ll(th):
            pred = f(th)
            c = _cov_at(cov, rel, mode, y, pred)
            r = q.T @ (y - pred)
            cr = q.T @ c @ q
            val = float(r @ np.linalg.solve(cr, r))
            if logdet and rel is not None and mode == "model":
                val += float(np.linalg.slogdet(cr)[1])
            return val
        res = optimize.minimize(m2ll, th0, method="BFGS", options={"gtol": 1e-8})
        theta = res.x
        hess, edm = _verdict(m2ll, theta)
        pred = f(theta)
        c = _cov_at(cov, rel, mode, y, pred)
        r = q.T @ (y - pred)
        cr = q.T @ c @ q
        chi2 = float(r @ np.linalg.solve(cr, r))
        cov_theta = 2.0 * np.linalg.inv(hess)
        extra = {}
        jac = np.array([(q.T @ (f(theta + h) - f(theta - h))) / (2 * 1e-6) for h in np.eye(npar) * 1e-6]).T
        seen = int(np.linalg.matrix_rank(jac, tol=1e-9 * max(1.0, float(np.abs(jac).max()))))
        dof = info["rank_in_subspace"] - seen
    extra["edm"] = edm
    from scipy.stats import chi2 as chi2_dist
    return {"label": LABEL, "model": model, "theta": theta.tolist(), "theta_errors": np.sqrt(np.diag(cov_theta)).tolist(),
            "chi2": chi2, "dof": int(dof), "p_value": float(chi2_dist.sf(chi2, dof)) if dof > 0 else None,
            "covariance": info, "multiplicative_mode": mode, "logdet": bool(logdet and mode == "model"), **extra,
            "note": ("chi2 and dof are counted in the subspace orthogonal to the declared constraints; a near-singular "
                     "covariance is fitted as given and flagged, never regularized; with multiplicative uncertainties the "
                     "'data' mode is biased (Peelle's pertinent puzzle) and is reported, not recommended")}


# ------------------------------------------------------------------------------------- break position (STH-T3.13)
def _profile_bpl(Y, W, x, grid, smoothness, iters=30):
    """For every row of Y [T, n] and every ln x_b in grid: chi2 minimized over (ln A, gamma1, gamma2) by Gauss-Newton
    (ln F is linear in them at fixed x_b). Returns chi2 [T, G] and the fitted parameters [T, G, 3]."""
    Y = np.atleast_2d(Y)
    T, n = Y.shape
    lx = np.log(x)
    chi2 = np.full((T, len(grid)), np.inf)
    pars = np.zeros((T, len(grid), 3))
    w_diag = np.clip(np.diag(W), 1e-300, None)
    for g, lxb in enumerate(grid):
        u = lx - lxb
        h = break_shape(u, smoothness)
        B = np.stack([np.ones(n), -(u - h), -h], axis=1)              # [n, 3]
        ly = np.log(np.clip(Y, 1e-300, None))
        # start: weighted linear least squares in log space (weights y^2 / var)
        wl = (Y ** 2) * w_diag
        A = np.einsum("tn,ni,nj->tij", wl, B, B) + 1e-12 * np.eye(3)
        p = np.linalg.solve(A, np.einsum("tn,ni,tn->ti", wl, B, ly)[..., None])[..., 0]
        for _ in range(iters):
            F = np.exp(p @ B.T)                                       # [T, n]
            J = F[:, :, None] * B[None]                               # [T, n, 3]
            r = Y - F
            JW = np.einsum("tni,nm->tim", J, W)
            H = np.einsum("tim,tmj->tij", JW, J) + 1e-12 * np.eye(3)
            step = np.linalg.solve(H, np.einsum("tim,tm->ti", JW, r)[..., None])[..., 0]
            p = p + step
            if np.all(np.abs(step) < 1e-10 * (1 + np.abs(p))):
                break
        F = np.exp(p @ B.T)
        r = Y - F
        chi2[:, g] = np.einsum("tn,nm,tm->t", r, W, r)
        pars[:, g] = p
    return chi2, pars


def _single_pl_chi2(Y, W, x, iters=30):
    """chi2 of a single power law (the no-break null) for every row of Y."""
    Y = np.atleast_2d(Y)
    n = Y.shape[1]
    B = np.stack([np.ones(n), -np.log(x)], axis=1)
    wl = (Y ** 2) * np.clip(np.diag(W), 1e-300, None)
    p = np.linalg.solve(np.einsum("tn,ni,nj->tij", wl, B, B), np.einsum("tn,ni,tn->ti", wl, B, np.log(np.clip(Y, 1e-300, None)))[..., None])[..., 0]
    for _ in range(iters):
        F = np.exp(p @ B.T)
        J = F[:, :, None] * B[None]
        JW = np.einsum("tni,nm->tim", J, W)
        H = np.einsum("tim,tmj->tij", JW, J) + 1e-12 * np.eye(2)
        step = np.linalg.solve(H, np.einsum("tim,tm->ti", JW, Y - F)[..., None])[..., 0]
        p = p + step
        if np.all(np.abs(step) < 1e-10 * (1 + np.abs(p))):
            break
    F = np.exp(p @ B.T)
    r = Y - F
    return np.einsum("tn,nm,tm->t", r, W, r), p


def _runs(grid, d, level):
    """Intervals of {ln x_b: d <= level} in x_b, each end interpolated linearly in d between the last grid point
    inside and the first outside (a run that reaches the grid edge ends there)."""
    mask = d <= level
    out, start = [], None

    def cross(i, j):  # ln x_b between grid points i (inside) and j (outside) where d = level
        t = (level - d[i]) / (d[j] - d[i]) if d[j] != d[i] else 0.0
        return grid[i] + t * (grid[j] - grid[i])
    for k, m in enumerate(mask):
        if m and start is None:
            start = k
        if start is not None and (not m or k == len(mask) - 1):
            end = k if m else k - 1
            lo = cross(start, start - 1) if start > 0 else grid[start]
            hi = cross(end, end + 1) if end < len(mask) - 1 else grid[end]
            out.append([float(math.exp(lo)), float(math.exp(hi))])
            start = None
    return out


def break_scan(doc: dict, toys: int = 200, seed: int = 1, cl: float = 0.6827) -> dict:
    """Break position of a (smoothly) broken power law fitted to points with a full covariance: the profile chi2 over a
    grid of ln x_b, an interval calibrated with toys (the break is not a regular parameter: no Wilks), and the
    no-break test calibrated with toys under the single-power-law fit (STH-T3.13)."""
    if not isinstance(doc, dict):
        raise CovFitInputError("the input must be a JSON object")
    y = np.asarray(doc["y"], dtype=float)
    cov = np.asarray(doc["cov"], dtype=float)
    x = np.asarray(doc["x"], dtype=float)
    n = len(y)
    if y.ndim != 1 or n < 5 or x.shape != (n,) or cov.shape != (n, n) or np.any(x <= 0) or np.any(np.diff(x) <= 0):
        raise CovFitInputError("need at least 5 points, increasing positive x and an n x n covariance")
    if not np.all(np.isfinite(y)) or np.any(y <= 0):
        raise CovFitInputError("break-scan fits positive values (a power law)")
    if not np.allclose(cov, cov.T, rtol=1e-12, atol=0) or np.linalg.eigvalsh(cov)[0] <= 0:
        raise CovFitInputError("cov must be symmetric positive definite")
    if not (isinstance(toys, int) and 50 <= toys <= 100000) or not 0 < cl < 1:
        raise CovFitInputError("toys must be in [50, 100000] and cl in (0, 1)")
    sm = float(doc.get("smoothness", 0.0))
    if sm < 0:
        raise CovFitInputError("smoothness must be >= 0 (0: sharp break)")
    lo, hi = doc.get("break_range", [float(x[1]), float(x[-2])])
    if not (x[0] < lo < hi < x[-1]):
        raise CovFitInputError("break_range must lie strictly inside the x range")
    points = int(doc.get("grid_points", 40))
    if not 5 <= points <= 400:
        raise CovFitInputError("grid_points must be in [5, 400]")
    grid = np.linspace(math.log(lo), math.log(hi), points)
    W = np.linalg.inv(cov)
    chi2_obs, pars = _profile_bpl(y, W, x, grid, sm)
    j = int(np.argmin(chi2_obs[0]))
    best = np.append(pars[0, j], grid[j])
    d_obs = chi2_obs[0] - chi2_obs[0, j]
    rng = np.random.default_rng(seed)
    f_best = np.exp(bpl_log(best, x, sm))
    Yt = rng.multivariate_normal(f_best, cov, size=toys)
    Yt = np.clip(Yt, 1e-12 * np.max(f_best), None)
    chi2_t, _ = _profile_bpl(Yt, W, x, grid, sm)
    d_t = chi2_t[:, j] - chi2_t.min(axis=1)              # the toys' Delta chi2 at their true break (the best fit)
    crit = float(np.quantile(d_t, cl))
    chi2_single, p_single = _single_pl_chi2(y, W, x)
    q_break = float(chi2_single[0] - chi2_obs[0, j])
    f_null = np.exp(np.stack([np.ones(n), -np.log(x)], axis=1) @ p_single[0])
    Yn = np.clip(rng.multivariate_normal(f_null, cov, size=toys), 1e-12 * np.max(f_null), None)
    c_null, _ = _profile_bpl(Yn, W, x, grid, sm)
    q_null = _single_pl_chi2(Yn, W, x)[0] - c_null.min(axis=1)
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from core.stats.tail_estimation import toy_tail
    from scipy.stats import chi2 as chi2_dist
    k = int(np.sum(q_null >= q_break - 1e-12))
    return {"label": LABEL, "model": "broken-power-law" if sm == 0 else "smoothly-broken-power-law", "smoothness": sm,
            "parametrization": "ln F = ln A - gamma1 (u - h(u)) - gamma2 h(u), u = ln(x / x_b)",
            "best_fit": {"ln_A": float(best[0]), "gamma1": float(best[1]), "gamma2": float(best[2]), "x_b": float(math.exp(best[3]))},
            "chi2_min": float(chi2_obs[0, j]), "dof": n - 4,
            "grid": {"ln_x_b": grid.tolist(), "resolution_ln": float(grid[1] - grid[0])},
            "profile_delta_chi2": d_obs.tolist(),
            "break_interval": {"cl": cl, "critical_value_toys": crit, "intervals": _runs(grid, d_obs, crit),
                               "calibration": f"{toys} toys from the best fit with the full covariance (plug-in), seed {seed}"},
            "break_interval_wilks_for_comparison": {"critical_value": float(chi2_dist.ppf(cl, 1)),
                                                    "intervals": _runs(grid, d_obs, chi2_dist.ppf(cl, 1))},
            "break_test": {"q_obs": q_break, "p_toys": toy_tail(k, toys),
                           "p_wilks_chi2_1dof_if_x_b_known": float(chi2_dist.sf(q_break, 1)),
                           "p_wilks_chi2_2dof": float(chi2_dist.sf(q_break, 2)),
                           "note": "under no break, x_b is undefined and q is maximized over it (Davies, a look-elsewhere "
                                   "scan): neither chi2 reference is valid (chi2(1) rejects too often); use the toy p-value"},
            "toys": toys, "seed": seed,
            "note": "the break position is not a regular parameter (its profile is not quadratic and the no-break null is "
                    "on the boundary): its interval is calibrated with toys, never by Wilks; ends are known to one grid step"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--input", required=True)
    bs = sub.add_parser("break-scan", help="break position of a broken power law with a toy-calibrated interval")
    bs.add_argument("--input", required=True)
    bs.add_argument("--toys", type=int, default=200)
    bs.add_argument("--seed", type=int, default=1)
    bs.add_argument("--cl", type=float, default=0.6827)
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy and SciPy are required"}))
        return 2
    try:
        doc = json.loads(Path(a.input).read_text())
        if not isinstance(doc, dict):
            raise ValueError(f"the input must be a JSON object, got {type(doc).__name__}")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot read {a.input}: {exc}"}))
        return 2
    try:
        if a.command == "break-scan":
            out = break_scan(doc, a.toys, a.seed, a.cl)
        else:
            out = fit(doc["y"], doc["cov"], doc.get("model", "constant"), doc.get("x"), doc.get("constraints"),
                      doc.get("start"), doc.get("multiplicative"), model_options=doc.get("model_options"))
    except KeyError as exc:
        print(json.dumps({"status": "rejected", "error": f"missing {exc}"}))
        return 2
    except CovFitInputError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    except CovFitError as exc:
        print(json.dumps({"label": LABEL, "status": "refused", "error": str(exc)}))
        return 1
    out["status"] = "ok"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
