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

Usage: covariance_fit.py fit --input FILE
Exit codes: 0 fitted; 1 refused (covariance singular beyond the declared constraints, a declared constraint that is not a
null direction, no convergence); 2 bad input. Output JSON labelled [General method].
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy import optimize

LABEL = "[General method]"
COND_WARN = 1e10
NULL_TOL = 1e-9


class CovFitError(ValueError):
    """Refused input or a fit that cannot be done without an undeclared assumption."""


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


def model_fn(name, x):
    x = np.asarray(x, dtype=float)
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


def fit(y, cov, model="constant", x=None, constraints=None, start=None, multiplicative=None, logdet=True) -> dict:
    y = np.asarray(y, dtype=float)
    cov = np.asarray(cov, dtype=float)
    n = len(y)
    if cov.shape != (n, n) or not np.allclose(cov, cov.T, rtol=1e-12, atol=0):
        raise CovFitError("cov must be a symmetric n x n matrix")
    x = np.arange(n, dtype=float) if x is None else np.asarray(x, dtype=float)
    f, npar = model_fn(model, x)
    rel, mode = None, None
    if multiplicative:
        rel = np.asarray(multiplicative["relative_cov"], dtype=float)
        mode = multiplicative.get("mode")
        if mode not in ("data", "model", "nuisance"):
            raise CovFitError("multiplicative.mode must be data, model or nuisance (no default)")
    q, info = subspace(cov if rel is None or mode == "nuisance" else cov + rel * np.outer(y, y), constraints)
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--input", required=True)
    a = ap.parse_args(argv)
    try:
        doc = json.loads(Path(a.input).read_text())
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot read {a.input}: {exc}"}))
        return 2
    try:
        out = fit(doc["y"], doc["cov"], doc.get("model", "constant"), doc.get("x"), doc.get("constraints"),
                  doc.get("start"), doc.get("multiplicative"))
    except KeyError as exc:
        print(json.dumps({"status": "rejected", "error": f"missing {exc}"}))
        return 2
    except CovFitError as exc:
        print(json.dumps({"label": LABEL, "status": "refused", "error": str(exc)}))
        return 1
    out["status"] = "ok"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
