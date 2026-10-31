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
  "t0" (Ball et al., arXiv:0912.2276v2, Sec. 6; read 2026-10-23) scales the multiplicative part with a FIXED prior
  prediction t0 ("t0_prediction", one value per point), so the covariance does not move with the fit (unlike "model",
  which uses the fitted prediction and its ln det); "t0_iterations" k refits k times with t0 set to the previous fit's
  prediction (their Sec. 6.3). Ball et al. show that the nuisance ("penalty trick") form is unbiased for one experiment
  but biased when several experiments with different normalizations are combined, and that the iterated t0 form is
  unbiased in both cases (their Secs. 4 and 6). With one common normalization and a constant model the t0 central
  value does not depend on t0 (only its error does; their Eqs. 81-82); with separate normalizations it does and the
  iteration converges to a self-consistent t0 (tests/skills/hep_statistics/test_covariance_fit.py).

Units: rescaling y by a and C by a^2 leaves the parameters of a scale-covariant model (rescaled), chi2 and dof unchanged.

Input (fit): {"y": [...], "cov": [[...]] (additive part), "x": [...] (abscissa, for the models),
  "model": "constant" | "line" | "exponential-normalized" (p_i = exp(-b x_i) / sum_k exp(-b x_k), parameter b),
  "constraints": [[a_1, ..., a_n], ...] (optional rows: a . y = const), "start": [...],
  "multiplicative": {"relative_cov": [[...]], "mode": "data" | "model" | "nuisance" | "t0", "t0_prediction": [...]
  and "t0_iterations": k for t0} (optional)}

  "model_options": {"smoothness": s} for smoothly-broken-power-law, {"plugin": {"path", "function", "n_params"}} for
  plugin (a Python file defining function(theta, x) -> n predictions; it runs with your permissions, so only with
  --allow-plugin; a relative path is read from the input file's folder; an exception in it is "status": "failed",
  exit 1)}
Models with x > 0: broken-power-law (sharp) and smoothly-broken-power-law, theta = [ln A, gamma1, gamma2, ln x_b],
  ln F = ln A - gamma1 (u - h) - gamma2 h, u = ln(x / x_b), h = max(u, 0) or s ln((1 + e^(u/s)) / 2); give start.
Input (fit, joint datasets with optional scale nuisances; S4): {"model", "model_options", "start",
  "datasets": [{"name", "y", "cov", "x", "scale_nuisance": {"sigma", "kind": energy|rigidity|momentum|generic}}]}:
  one model fitted to all datasets (block-diagonal covariance); a dataset with scale_nuisance is predicted as
  Phi(x / (1 + s)) / (1 + s) with a fitted s constrained by N(0, sigma^2); output "scale_nuisances" [{dataset, kind,
  sigma, s, error, pull}]. A top-level scale_nuisance with y, cov, x is one dataset. Without a declaration nothing
  changes: the plain fit path is not used for these inputs and is unchanged.
Input (break-scan): {"y", "cov", "x", "smoothness": 0 (sharp), "break_range": [lo, hi], "grid_points": 40}: the profile
  chi2 over ln x_b, a toy-calibrated interval for the break (not Wilks: the break is not a regular parameter) and the
  toy-calibrated no-break test.

Input (fit, "model": "tabulated-grid"): a fit of parameters tabulated on a grid of predictions (for example propagation
  parameters D0 and L), multilinear interpolation between nodes, no extrapolation, no user code. Grid representation:
  ONE prediction artifact PER GRID NODE (contracts/schemas/ext_prediction.json admits this without a schema change:
  "representation": "grid", the node in "parameter_point", the observable's bins in "values"); a single artifact cannot
  carry the parameter axes, since its "values" are binned in the observable's variables only.
  {"model": "tabulated-grid",
   "measurement": "data.json" | {dataset-record},        data, bins and uncertainty components (paths: relative to the
   "predictions": ["node-1.json", ...] | [{...}, ...],    input file); every node of the full grid, once
   "grid": {"parameters": [{"name": "D0", "scale": "log"}, {"name": "L", "scale": "log"}]},   names: parameter_point
          keys; scale "log" interpolates and fits in ln p (p > 0), "linear" in p; >= 2 nodes per axis
   "gate_plan": {"transformations", "mappings", "measurement_conditions"} (optional; contracts/comparison/gate.py),
   "multiplicative": {"relative_cov": [[...]], "mode": "nuisance"} (optional: a common cross-section normalization of
          the prediction, rank one, fitted as a constrained nuisance as in "fit"; only "nuisance" for a grid),
   "model_set": {"alternative_key": "xs_set", "prescription": {"kind": "min-max", "owner": "hep-theory",
          "justification": "..."}} (optional: the parameter_point key that names a cross-section set; each set is a full
          grid, fitted separately; contracts/comparison/model_set.py model_set() and envelope() give the spread),
   "theory_spec": "spec.json" | {theory-spec} (optional; its degenerate_directions are compared with the fit; an
          object entry contributes its "combination", contracts 3.14.0),
   "combinations": ["D0/L"] (optional monomials of grid parameters to report, e.g. "D0/L", "D0*L^2"),
   "start": {"D0": 3.0, "L": 4.0} (optional, inside the grid),
   "degeneracy_scan": {"parameter": "L"} | {"direction": "fisher" | {"D0": 1, "L": 1}} | {"plane": ["D0", "L"]}, with
          optional "values", "points", "threshold" (default 1), "broken_by" (optional: profile-likelihood scans by
          degeneracy.py, which also does the Fisher screen; adds "degeneracies" (object form, evidence fisher-screen
          without valid_range, then profile-scan with valid_range) and "profile_scans" to each fit)}
  Every prediction is gated (contracts/comparison/gate.py check()) against the measurement first; one that is not
  comparable, or a fit without a measurement to gate against, is refused (exit 1). The grid parameters (and the
  alternative key) are what is fitted, so the gate is given them as measurement conditions equal to the node's own
  values; every other parameter_point key must be stated in gate_plan.measurement_conditions and match.
  Data covariance: assembled from the measurement's uncertainty components (uncorrelated: diagonal; fully-correlated:
  outer product; covariance: the matrix in covariance_ref, a JSON {"matrix"} or bare matrix, each file added once); with
  no components, the dataset's covariance ref (status "present"). A component with correlation "unknown" or an
  unreadable ref, or no covariance at all, is recorded under "missing" with status "incomplete" (exit 3): a diagonal
  matrix is never assumed.
  Degenerate directions (degeneracy.py, Fisher screen): eigen-decomposition of the Fisher matrix J^T C^-1 J in the fit
  coordinates (nuisance profiled), J by central differences; a direction is degenerate when its 1-sigma half-width
  exceeds half the grid chord along it or its eigenvalue is below 1e-10 of the largest. Each is reported with its eigenvector and the
  condition number and compared with the theory spec's degenerate_directions (a monomial such as "D0/L" predicts a flat
  direction along which it is constant); a mismatch is a warning. Parameters along a degenerate direction get no error;
  combinations orthogonal to it get one (pseudo-inverse over the constrained directions).
  Output: "fits" (one per cross-section set: parameters, chi2, dof, fisher, degenerate_directions, combinations),
  "cross_section_uncertainty" {"mode": "none" | "nuisance" | "model-set" | "nuisance+model-set"}, "envelope" (model
  set), "gate", "warnings", "carried_statuses".
  A best fit on the grid edge with chi2 still falling outward (more than 1e-3 per cell) is refused: the minimum is not
  inside the grid and nothing is extrapolated.

Usage: covariance_fit.py fit --input FILE [--allow-plugin]
       covariance_fit.py break-scan --input FILE [--toys 200 --seed 1 --cl 0.6827]
Exit codes: 0 fitted; 1 refused (covariance singular beyond the declared constraints, a declared constraint that is not a
null direction, no convergence (a grid fit whose optimizer stopped and whose restart neither succeeds nor passes the EDM
check: "status": "failed" with "reason"); for a grid: a prediction not gated, not comparable or refused by the gate, a minimum outside the grid);
2 bad input; 3 incomplete (a data covariance or uncertainty correlation is missing: "status": "incomplete" with
"missing"). Output JSON labelled [General method].
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

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
    from scipy import optimize
except ImportError:  # pragma: no cover
    np = optimize = None  # type: ignore[assignment]

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats import broken_power_law as _bpl  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import degeneracy as _deg  # noqa: E402  (same skill: Fisher screen and profile scans, cr-propagation A3)

LABEL = "[General method]"
COND_WARN = 1e10
NULL_TOL = 1e-9


class CovFitError(ValueError):
    """Refused input or a fit that cannot be done without an undeclared assumption."""


class CovFitInputError(CovFitError):
    """A malformed input (exit 2), as opposed to a refused fit (exit 1)."""


class CovFitPluginError(CovFitError):
    """The user's plugin model raised or misbehaved: status 'failed', exit 1 (F-09)."""


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
    smooth one with smoothness s > 0 (which tends to the sharp form as s -> 0); core/stats/broken_power_law.py."""
    return _bpl.break_shape(np.asarray(u, dtype=float), smoothness)


def bpl_log(theta, x, smoothness=0.0):
    """ln F of the broken power law, theta = [ln A, gamma1, gamma2, ln x_b]:
    ln F = ln A - gamma1 (u - h(u)) - gamma2 h(u), u = ln(x / x_b) (STH-T3.13). F(x_b) = A for the sharp and the
    smooth form; the index is gamma1 below and gamma2 above the break. The plugin's one parametrization (STH Q8),
    shared with hep-measurement cr_spectrum_powerlaw_fit.py through core/stats/broken_power_law.py."""
    return _bpl.log_flux(np.asarray(x, dtype=float), theta[0], theta[1], theta[2], theta[3], smoothness)


def _plugin(spec, n, allow=False, base_dir=None):
    """A user model: {"path": "model.py", "function": "predict", "n_params": k}; predict(theta, x) -> n values. It runs
    user code, so only with allow (--allow-plugin); a relative path is resolved against base_dir (the input file's
    folder); its exceptions become CovFitPluginError (F-09)."""
    import importlib.util
    if not isinstance(spec, dict) or not all(k in spec for k in ("path", "function", "n_params")):
        raise CovFitInputError('a plugin model needs {"path", "function", "n_params"}')
    if not allow:
        raise CovFitError("a plugin model runs your Python file with your permissions; pass --allow-plugin "
                          "(allow_plugin=True) to run it")
    path = Path(spec["path"])
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    if not path.is_file():
        raise CovFitInputError(f"plugin file {path} not found")
    sys.dont_write_bytecode = True  # importing the plugin leaves no __pycache__ next to it
    try:
        mod_spec = importlib.util.spec_from_file_location("covariance_fit_plugin", path)
        mod = importlib.util.module_from_spec(mod_spec)
        mod_spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:  # noqa: BLE001 - any failure of user code is reported, never a traceback
        raise CovFitPluginError(f"the plugin {path} failed to load: {type(exc).__name__}: {exc}") from exc
    fn = getattr(mod, spec["function"], None)
    k = spec["n_params"]
    if not callable(fn) or not (isinstance(k, int) and k >= 1):
        raise CovFitInputError("the plugin function must exist and n_params must be a positive integer")

    def f(th):
        try:
            out = np.asarray(fn(np.asarray(th, dtype=float), _plugin_x), dtype=float)
        except Exception as exc:  # noqa: BLE001
            raise CovFitPluginError(f"the plugin function {spec['function']} raised {type(exc).__name__}: {exc}") from exc
        if out.shape != (n,) or not np.all(np.isfinite(out)):
            raise CovFitError(f"the plugin returned {out.shape} or non-finite values; expected {n} finite values")
        return out
    return f, k


_plugin_x: object = None


def model_fn(name, x, options=None, allow_plugin=False, base_dir=None):
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
        return _plugin(options.get("plugin"), len(x), allow_plugin, base_dir)
    if name == "tabulated-grid":
        raise CovFitInputError("tabulated-grid takes predictions and a measurement, not y and cov: use grid_fit(doc) or "
                               "the fit command with the tabulated-grid input")
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


def _cov_at(cov_add, rel, mode, y, pred, f_scale=None, t0=None):
    if rel is None:
        return cov_add
    base = y if mode == "data" else (t0 if mode == "t0" else pred)
    return cov_add + rel * np.outer(base, base)


def _relative_cov(relative_cov, n):
    """STH-T3.6: n x n, finite, symmetric and positive semidefinite on its correlation scale (the validate_covariance.py
    rule); a 1 x 1 matrix is never broadcast to every pair of points."""
    rel = np.asarray(relative_cov, dtype=float)
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
    return rel


def _rank_one(rel):
    """The relative shift per unit of a common normalization nuisance: rel must be rank one."""
    ev, evec = np.linalg.eigh(rel)
    if ev[-1] <= 0 or np.sum(ev > 1e-12 * ev[-1]) != 1:
        raise CovFitError("nuisance mode needs a rank-one relative covariance (one common normalization)")
    return evec[:, -1] * math.sqrt(ev[-1])


def fit(y, cov, model="constant", x=None, constraints=None, start=None, multiplicative=None, logdet=True,
        model_options=None, allow_plugin=False, base_dir=None) -> dict:
    y = np.asarray(y, dtype=float)
    cov = np.asarray(cov, dtype=float)
    n = len(y)
    if cov.shape != (n, n) or not np.allclose(cov, cov.T, rtol=1e-12, atol=0):
        raise CovFitError("cov must be a symmetric n x n matrix")
    x = np.arange(n, dtype=float) if x is None else np.asarray(x, dtype=float)
    f, npar = model_fn(model, x, model_options, allow_plugin, base_dir)
    rel, mode = None, None
    if multiplicative:
        rel = _relative_cov(multiplicative["relative_cov"], n)
        mode = multiplicative.get("mode")
        if mode not in ("data", "model", "nuisance", "t0"):
            raise CovFitError("multiplicative.mode must be data, model, nuisance or t0 (no default)")
        if mode == "t0" and any(k.startswith("_") for k in multiplicative) and not getattr(fit, "_inner", False):
            raise CovFitError("multiplicative keys starting with '_' are internal")
        if mode == "t0" and not getattr(fit, "_inner", False):
            t0 = multiplicative.get("t0_prediction")
            iters = multiplicative.get("t0_iterations")
            if t0 is None or iters is None:
                raise CovFitError("t0 mode needs t0_prediction (a fixed prior prediction per point) and t0_iterations")
            t0 = np.asarray(t0, dtype=float)
            if t0.shape != (n,) or not np.all(np.isfinite(t0)) or isinstance(iters, bool) or not isinstance(iters, int) \
                    or iters < 0:
                raise CovFitError("t0_prediction must hold n finite values and t0_iterations an integer >= 0")
            sub = dict(multiplicative, t0_iterations=0)
            res = None
            fit._inner = True
            try:
                for _ in range(iters + 1):
                    res = fit(y, cov, model, x, constraints, start, dict(sub, t0_prediction=t0.tolist()), logdet,
                              model_options, allow_plugin, base_dir)
                    t0 = np.asarray(model_fn(model, x, model_options, allow_plugin, base_dir)[0](np.asarray(res["theta"])))
            finally:
                fit._inner = False
            res["t0_iterations"] = iters
            return res
    t0v = np.asarray(multiplicative["t0_prediction"], dtype=float) if mode == "t0" else None
    q, info = subspace(cov if rel is None or mode == "nuisance" else cov + rel * np.outer(y if t0v is None else t0v,
                                                                                         y if t0v is None else t0v),
                       constraints)
    if start is None and model in ("broken-power-law", "smoothly-broken-power-law"):
        raise CovFitInputError("a broken power law needs start [ln A, gamma1, gamma2, ln x_b] (or use break-scan)")
    th0 = np.asarray(start if start is not None else ([float(np.mean(y))] + [0.0] * (npar - 1)), dtype=float)

    if mode == "nuisance":
        # one multiplicative factor f per independent component of rel (here: rel must be rank one, a common scale)
        u = _rank_one(rel)                         # relative shift per unit of the nuisance

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
            c = _cov_at(cov, rel, mode, y, pred, t0=t0v)
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
        c = _cov_at(cov, rel, mode, y, pred, t0=t0v)
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


# ------------------------------------------------------------------------------------- per-dataset scale nuisance (S4)
SCALE_KINDS = ("energy", "rigidity", "momentum", "generic")


def _scale_decl(d, name):
    sn = d.get("scale_nuisance")
    if sn is None:
        return None
    if not isinstance(sn, dict) or set(sn) != {"sigma", "kind"}:
        raise CovFitInputError(f"dataset {name!r}: scale_nuisance must be exactly {{sigma, kind}}")
    sig, kind = sn["sigma"], sn["kind"]
    if isinstance(sig, bool) or not isinstance(sig, (int, float)) or not math.isfinite(sig) or sig <= 0:
        raise CovFitInputError(f"dataset {name!r}: scale_nuisance.sigma must be a finite number > 0")
    if kind not in SCALE_KINDS:
        raise CovFitInputError(f"dataset {name!r}: scale_nuisance.kind must be one of {list(SCALE_KINDS)}")
    return {"sigma": float(sig), "kind": kind}


def fit_datasets(doc: dict, allow_plugin=False, base_dir=None) -> dict:
    """Joint fit of one model to several datasets (block-diagonal covariance); a dataset may declare
    scale_nuisance {sigma, kind}: its prediction is Phi(x / (1 + s)) / (1 + s) with s a fitted nuisance constrained by
    N(0, sigma^2), for an abscissa (energy, rigidity, momentum) known to a relative scale. A top-level scale_nuisance
    with y, cov, x is a single dataset."""
    if doc.get("multiplicative") or doc.get("constraints"):
        raise CovFitInputError("the datasets mode takes no multiplicative or constraints (fit each dataset alone)")
    if "datasets" in doc:
        sets = doc["datasets"]
        if not isinstance(sets, list) or not sets:
            raise CovFitInputError("datasets must be a non-empty list of {name, y, cov, x}")
    else:
        sets = [{"name": "dataset", "y": doc["y"], "cov": doc["cov"], "x": doc.get("x"),
                 "scale_nuisance": doc.get("scale_nuisance")}]
    model, opts = doc.get("model", "constant"), doc.get("model_options")
    data, names = [], []
    for i, d in enumerate(sets):
        if not isinstance(d, dict):
            raise CovFitInputError("every dataset must be an object with y, cov and x")
        name = str(d.get("name", f"dataset-{i}"))
        if name in names:
            raise CovFitInputError(f"duplicate dataset name {name!r}")
        names.append(name)
        y = np.asarray(d["y"], dtype=float)
        cov = np.asarray(d["cov"], dtype=float)
        n = len(y)
        if cov.shape != (n, n) or not np.allclose(cov, cov.T, rtol=1e-12, atol=0) or not np.all(np.isfinite(cov)):
            raise CovFitInputError(f"dataset {name!r}: cov must be a symmetric {n} x {n} matrix")
        x = np.arange(n, dtype=float) if d.get("x") is None else np.asarray(d["x"], dtype=float)
        if x.shape != (n,):
            raise CovFitInputError(f"dataset {name!r}: x must have {n} entries")
        q, info = subspace(cov, None)
        f, npar = model_fn(model, x, opts, allow_plugin, base_dir)
        data.append({"name": name, "y": y, "cov": cov, "x": x, "f": f, "scale": _scale_decl(d, name), "info": info})
    nuis = [k for k, d in enumerate(data) if d["scale"]]
    start = doc.get("start")
    if start is None and model in ("broken-power-law", "smoothly-broken-power-law"):
        raise CovFitInputError("a broken power law needs start [ln A, gamma1, gamma2, ln x_b] (or use break-scan)")
    y_all = np.concatenate([d["y"] for d in data])
    th0 = np.asarray(start if start is not None else ([float(np.mean(y_all))] + [0.0] * (npar - 1)), dtype=float)

    def pred(d, th, s):
        if s == 0.0:
            return d["f"](th)
        f_s, _ = model_fn(model, d["x"] / (1.0 + s), opts, allow_plugin, base_dir)
        return f_s(th) / (1.0 + s)

    def parts(p):
        th, svals = p[:npar], dict(zip(nuis, p[npar:]))
        out = []
        for k, d in enumerate(data):
            s = float(svals.get(k, 0.0))
            if s <= -1.0:
                return None
            r = d["y"] - pred(d, th, s)
            out.append(float(r @ np.linalg.solve(d["cov"], r)))
        pen = sum((float(svals[k]) / data[k]["scale"]["sigma"]) ** 2 for k in nuis)
        return out, pen

    def m2ll(p):
        v = parts(p)
        return float("inf") if v is None else sum(v[0]) + v[1]
    res = optimize.minimize(m2ll, np.append(th0, np.zeros(len(nuis))), method="BFGS", options={"gtol": 1e-8})
    p = res.x
    hess, edm = _verdict(m2ll, p)
    cov_p = 2.0 * np.linalg.inv(hess)
    err = np.sqrt(np.diag(cov_p))
    chi2_sets, pen = parts(p)
    chi2 = float(sum(chi2_sets) + pen)
    dof = int(len(y_all) - npar)
    from scipy.stats import chi2 as chi2_dist
    scale_out = [{"dataset": data[k]["name"], "kind": data[k]["scale"]["kind"], "sigma": data[k]["scale"]["sigma"],
                  "s": float(p[npar + j]), "error": float(err[npar + j]),
                  "pull": float(p[npar + j] / data[k]["scale"]["sigma"])} for j, k in enumerate(nuis)]
    return {"label": LABEL, "model": model, "mode": "datasets", "theta": p[:npar].tolist(),
            "theta_errors": err[:npar].tolist(), "chi2": chi2, "dof": dof,
            "p_value": float(chi2_dist.sf(chi2, dof)) if dof > 0 else None, "edm": edm,
            "datasets": [{"name": d["name"], "n": len(d["y"]), "chi2": c, "covariance": d["info"]}
                         for d, c in zip(data, chi2_sets)],
            "scale_nuisances": scale_out, "constraint_chi2": float(pen),
            "note": ("Phi_obs(x) = Phi_model(x / (1 + s)) / (1 + s) for a dataset that declares scale_nuisance, with a "
                     "Gaussian constraint (s / sigma)^2 counted in chi2; dof = total points - model parameters (each "
                     "constrained nuisance adds one parameter and one constraint)")}


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


# --------------------------------------------------------------------------- tabulated-grid fits (ams02 order, WP1)
class CovFitIncomplete(CovFitError):
    """A needed input is missing (a data covariance, an uncertainty correlation): status "incomplete", exit 3."""

    def __init__(self, message, missing):
        super().__init__(message)
        self.missing = missing


GRID_EDGE_SLOPE = 1e-3     # chi2 rise per grid cell, moving inward from an edge, above which the minimum is outside
DEGENERATE_EIG = _deg.DEGENERATE_EIG     # eigenvalue / largest eigenvalue below which a direction is degenerate
MATCH_COS = 0.1            # |g . v| / (|g| |v|) below which a flat direction v keeps the monomial with gradient g constant


def _load_json(ref, base: Path, what: str):
    if isinstance(ref, dict):
        return ref
    if not isinstance(ref, str):
        raise CovFitInputError(f"{what} must be a JSON object or a path, got {type(ref).__name__}")
    path = Path(ref) if Path(ref).is_absolute() else base / ref
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CovFitInputError(f"cannot read {what} {path}: {exc}") from None


def _matrix_from(obj, n):
    m = obj.get("matrix") if isinstance(obj, dict) else obj
    if isinstance(obj, dict) and obj.get("kind", "absolute") != "absolute":
        raise CovFitInputError("a covariance file must hold an absolute matrix (kind 'absolute')")
    m = np.asarray(m, dtype=float)
    if m.shape != (n, n) or not np.all(np.isfinite(m)) or not np.allclose(m, m.T, rtol=1e-10, atol=0):
        raise CovFitInputError(f"a covariance must be a finite symmetric {n} x {n} matrix, got shape {list(m.shape)}")
    return m


def data_covariance(ext: dict, base: Path, n: int) -> tuple[np.ndarray, dict]:
    """The data covariance from a dataset-record extension, assembled from its uncertainty components; never diagonal
    by assumption. Raises CovFitIncomplete listing what is missing."""
    comps = (ext.get("data") or {}).get("uncertainties") or []
    total, missing, used, files = np.zeros((n, n)), [], [], {}
    for i, c in enumerate(comps):
        name = c.get("name", f"component {i}") if isinstance(c, dict) else f"component {i}"
        if not isinstance(c, dict):
            raise CovFitInputError(f"uncertainty component {i} is not an object")
        corr, vals = c.get("correlation"), c.get("values")
        if corr in ("uncorrelated", "fully-correlated"):
            v = np.asarray(vals if vals is not None else [], dtype=float)
            if v.shape != (n,) or not np.all(np.isfinite(v)):
                missing.append({"component": name, "reason": f"'{corr}' needs {n} finite values"})
                continue
            total += np.diag(v ** 2) if corr == "uncorrelated" else np.outer(v, v)
            used.append({"component": name, "correlation": corr})
        elif corr == "covariance":
            ref = c.get("covariance_ref")
            if not ref:
                missing.append({"component": name, "reason": "correlation 'covariance' without covariance_ref"})
                continue
            if ref not in files:
                path = base / ref
                try:
                    files[ref] = _matrix_from(json.loads(path.read_text(encoding="utf-8")), n)
                except (OSError, ValueError) as exc:
                    missing.append({"component": name, "reason": f"covariance_ref {ref} unreadable: {exc}"})
                    continue
                total += files[ref]
            used.append({"component": name, "correlation": "covariance", "ref": ref})
        else:
            missing.append({"component": name, "reason": f"correlation {corr!r}: no covariance can be built"})
    block = ext.get("covariance") or {}
    if not comps:
        if block.get("status") == "present" and block.get("ref"):
            try:
                total = _matrix_from(json.loads((base / block["ref"]).read_text(encoding="utf-8")), n)
                used.append({"component": "dataset covariance", "correlation": "covariance", "ref": block["ref"]})
            except (OSError, ValueError) as exc:
                missing.append({"component": "dataset covariance", "reason": f"ref {block['ref']} unreadable: {exc}"})
        else:
            missing.append({"component": "dataset covariance",
                            "reason": f"no uncertainty components and covariance status {block.get('status')!r}"})
    if missing:
        raise CovFitIncomplete("the data covariance is incomplete; it is recorded as missing, never replaced by a "
                               "diagonal matrix", missing)
    return total, {"source": "uncertainty components" if comps else "dataset covariance ref", "components": used,
                   "dataset_covariance_status": block.get("status")}


def _monomial(text, names):
    """'D0/L', 'D0*L^2', 'D0 / L (note)' -> {name: exponent}; None when it names no grid parameter or cannot be read."""
    import re
    s = re.sub(r"\(.*?\)", "", str(text)).replace(" ", "")
    if not s:
        return None
    out, sign = {}, 1.0
    for tok in re.split(r"([*/])", s):
        if tok in ("*", "/"):
            sign = 1.0 if tok == "*" else -1.0
            continue
        m = re.fullmatch(r"([A-Za-z_][\w.]*)(?:\^(-?\d+(?:\.\d+)?))?", tok)
        if not m or m.group(1) not in names:
            return None
        out[m.group(1)] = out.get(m.group(1), 0.0) + sign * float(m.group(2) or 1.0)
    return {k: v for k, v in out.items() if v != 0} or None


class _Grid:
    """Values on a rectilinear grid in fit coordinates (ln p for log axes): V[i1, ..., ik, bin]; multilinear
    interpolation; outside the grid it refuses."""

    def __init__(self, axes, values):
        self.axes = [np.asarray(a, dtype=float) for a in axes]
        self.V = np.asarray(values, dtype=float)
        self.lo = np.array([a[0] for a in self.axes])
        self.hi = np.array([a[-1] for a in self.axes])

    def inside(self, t, tol=1e-12):
        span = self.hi - self.lo
        return bool(np.all(t >= self.lo - tol * span) and np.all(t <= self.hi + tol * span))

    def __call__(self, t):
        t = np.asarray(t, dtype=float)
        if not self.inside(t):
            raise CovFitError(f"point {t.tolist()} (fit coordinates) lies outside the grid {self.lo.tolist()} - "
                              f"{self.hi.tolist()}: the grid is not extrapolated")
        idx, w = [], []
        for a, x in zip(self.axes, np.clip(t, self.lo, self.hi)):
            i = int(min(max(np.searchsorted(a, x, side="right") - 1, 0), len(a) - 2))
            idx.append(i)
            w.append((x - a[i]) / (a[i + 1] - a[i]))
        out = np.zeros(self.V.shape[-1])
        for corner in range(2 ** len(idx)):
            weight, sel = 1.0, []
            for k, (i, wk) in enumerate(zip(idx, w)):
                bit = (corner >> k) & 1
                weight *= wk if bit else 1.0 - wk
                sel.append(i + bit)
            if weight:
                out += weight * self.V[tuple(sel)]
        return out

    def cell(self, k, x):
        a = self.axes[k]
        i = int(min(max(np.searchsorted(a, x, side="right") - 1, 0), len(a) - 2))
        return float(a[i + 1] - a[i])


def _grid_one(grid: _Grid, names, scales, y, cov, u, start, monomials, declared, scan=None):
    """Fit one grid (one cross-section set): best fit, Fisher matrix, degenerate directions, combinations."""
    k, n = len(names), len(y)
    _, info = subspace(cov, None)                 # refuses a singular covariance, reports its condition number
    chol = np.linalg.cholesky(cov)
    from scipy.linalg import solve_triangular
    nz = 1 if u is not None else 0

    def m2ll(p):
        pred = grid(p[:k])
        if nz:
            pred = pred * (1.0 + p[k] * u)
        r = solve_triangular(chol, y - pred, lower=True)
        return float(r @ r) + (float(p[k]) ** 2 if nz else 0.0)

    if start is None:
        # start at the best node; among nodes tied with it (a flat valley) the one nearest the grid centre
        nodes = [np.array([a[i] for a, i in zip(grid.axes, node)]) for node in np.ndindex(*[len(a) for a in grid.axes])]
        vals = np.array([m2ll(np.append(t, [0.0] * nz)) for t in nodes])
        tied = np.flatnonzero(vals <= vals.min() + 1e-9 * (1.0 + abs(vals.min())))
        centre = 0.5 * (grid.lo + grid.hi)
        start = min((nodes[i] for i in tied), key=lambda t: float(np.sum(((t - centre) / (grid.hi - grid.lo)) ** 2)))
    p0 = np.append(start, [0.0] * nz)
    bounds = [(lo, hi) for lo, hi in zip(grid.lo, grid.hi)] + [(None, None)] * nz
    opts = {"ftol": 1e-14, "gtol": 1e-10, "maxiter": 2000}
    res = optimize.minimize(m2ll, p0, method="L-BFGS-B", bounds=bounds, options=opts)
    convergence = {"optimizer": str(res.message), "restarted": False}
    if not res.success:
        # a line search can stop abnormally at a point that is already the minimum (an Asimov fit starts there): restart
        # once from where it stopped before judging; the EDM check below decides if the restart does not succeed (F-01)
        res = optimize.minimize(m2ll, np.asarray(res.x, dtype=float), method="L-BFGS-B", bounds=bounds, options=opts)
        convergence.update(restarted=True, optimizer_after_restart=str(res.message))
    p = np.asarray(res.x, dtype=float)
    p[:k] = np.clip(p[:k], grid.lo, grid.hi)
    chi2 = m2ll(p)
    if not np.isfinite(chi2):
        raise CovFitError("the grid fit did not converge (non-finite chi2)")
    at_edge = []
    for j in range(k):
        span = grid.hi[j] - grid.lo[j]
        side = -1 if p[j] - grid.lo[j] <= 1e-6 * span else (1 if grid.hi[j] - p[j] <= 1e-6 * span else 0)
        if not side:
            continue
        cellw = grid.cell(j, p[j])
        h = 0.01 * cellw
        z1, z2 = p.copy(), p.copy()
        z1[j] -= side * h
        z2[j] -= 2 * side * h
        # one-sided first derivative inward, second order (the curvature term cancels): chi2 change per cell
        slope = (4 * m2ll(z1) - m2ll(z2) - 3 * chi2) / (2 * h) * cellw
        at_edge.append(names[j])
        if slope > GRID_EDGE_SLOPE:
            raise CovFitError(f"the best fit lies on the {'lower' if side < 0 else 'upper'} grid edge of {names[j]} with "
                              f"chi2 still falling outward ({slope:.3g} per cell): the minimum is outside the grid; extend "
                              "the grid (nothing is extrapolated)")
    # Fisher matrix J^T C^-1 J in the fit coordinates (+1 for the constrained nuisance). J by central differences over
    # one grid cell (one-sided at an edge): a finer step sees the kinks of the multilinear interpolation at the nodes,
    # which would invent a constraint along a direction the tabulated model does not constrain
    pred0 = grid(p[:k]) * ((1.0 + p[k] * u) if nz else 1.0)
    jac = np.zeros((n, k + nz))
    def at(j, step):
        z = p.copy()
        z[j] += step
        return grid(z[:k]) * ((1.0 + z[k] * u) if nz else 1.0)
    for j in range(k):
        h = min(grid.cell(j, p[j]), 0.5 * (grid.hi[j] - grid.lo[j]))
        # every step is cut at the grid edges: a point inside an edge cell has less than one cell on one side
        hu, hd = min(h, grid.hi[j] - p[j]), min(h, p[j] - grid.lo[j])
        if min(hu, hd) > 1e-6 * h:
            # three-point central difference with unequal steps (second order; hu = hd gives the symmetric one)
            jac[:, j] = (hd ** 2 * at(j, hu) - hu ** 2 * at(j, -hd) - (hd ** 2 - hu ** 2) * pred0) / (hu * hd * (hu + hd))
        else:   # at an edge: second-order one-sided difference (a first-order one is biased by the curvature)
            sgn = 1.0 if hu >= hd else -1.0
            room = max(hu, hd)
            if len(grid.axes[j]) > 2:
                s = min(h, 0.5 * room)
                jac[:, j] = sgn * (-3 * pred0 + 4 * at(j, sgn * s) - at(j, 2 * sgn * s)) / (2 * s)
            else:
                s = min(h, room)
                jac[:, j] = sgn * (at(j, sgn * s) - pred0) / s
    if nz:
        jac[:, k] = grid(p[:k]) * u
    wj = solve_triangular(chol, jac, lower=True)
    fisher = wj.T @ wj
    if nz:
        fisher[k, k] += 1.0
        fk = fisher[:k, :k] - np.outer(fisher[:k, k], fisher[k, :k]) / fisher[k, k]     # nuisance profiled
    else:
        fk = fisher
    if res.success:
        convergence["converged_by"] = "optimizer"
    else:
        # EDM in -2 ln L units from the optimizer's gradient, projected on the bounds (a component pushing outward at an
        # active bound is not a distance to the minimum), with the Hessian 2 J^T C^-1 J (+ the nuisance constraint)
        g = np.asarray(getattr(res, "jac", np.full(k + nz, np.inf)), dtype=float)
        lo = np.append(grid.lo, [-np.inf] * nz)
        hi = np.append(grid.hi, [np.inf] * nz)
        span_all = np.where(np.isfinite(hi - lo), hi - lo, 1.0)
        g = np.where(((p - lo) <= 1e-6 * span_all) & (g > 0) | ((hi - p) <= 1e-6 * span_all) & (g < 0), 0.0, g)
        edm = float(0.25 * g @ np.linalg.pinv(fisher, rcond=1e-12) @ g) if np.all(np.isfinite(g)) else float("inf")
        convergence.update(edm=edm, edm_max=EDM_MAX)
        convergence["converged_by"] = "edm" if edm <= EDM_MAX else None
    cond, eig, degenerate, keep = _deg.fisher_screen(fk, names, grid.hi - grid.lo, DEGENERATE_EIG)
    warnings = []
    g_of = {}
    for text, mono in monomials.items():
        if mono is None:
            continue
        if any(scales[names.index(nm)] == "linear" and p[names.index(nm)] <= 0 for nm in mono):
            warnings.append(f"combination {text!r} needs positive parameters at the best fit; not reported")
            continue
        # gradient of ln(monomial) in the fit coordinates: e for a log axis, e / p for a linear one
        g_of[text] = np.array([mono.get(nm, 0.0) * (1.0 if sc == "log" else 1.0 / p[i]) for i, (nm, sc) in enumerate(zip(names, scales))])
    for entry, v, _ in degenerate:
        entry["condition_number"] = cond
        entry["matches_theory_spec"] = None
        for text in declared:
            g = g_of.get(text)
            if g is None:
                continue
            mentioned = np.array([1.0 if names[i] in monomials[text] else 0.0 for i in range(k)])
            if abs(g @ v) / (np.linalg.norm(g) * np.linalg.norm(v)) < MATCH_COS and np.linalg.norm(v * mentioned) >= 0.9:
                entry["matches_theory_spec"] = text
                break
    # parameters and combinations: covariance from the constrained directions only
    pinv = sum((np.outer(v, v) / lam for _, v, lam in keep), np.zeros((k, k)))
    params = []
    for i, (nm, sc) in enumerate(zip(names, scales)):
        along = [e for e, v, _ in degenerate if abs(v[i]) > 0.1]
        t = float(p[i])
        params.append({"name": nm, "scale": sc, "fit_coordinate": f"ln {nm}" if sc == "log" else nm,
                       "best_fit": math.exp(t) if sc == "log" else t, "best_fit_coordinate": t,
                       "error_coordinate": None if along else float(math.sqrt(max(pinv[i, i], 0.0))),
                       "constrained": not along, "grid_range": [float(math.exp(grid.lo[i]) if sc == "log" else grid.lo[i]),
                                                                float(math.exp(grid.hi[i]) if sc == "log" else grid.hi[i])],
                       "at_grid_edge": nm in at_edge})
    combos = []
    for text, g in g_of.items():
        mono = monomials[text]
        ln_val = sum(e * (p[names.index(nm)] if scales[names.index(nm)] == "log" else math.log(p[names.index(nm)]))
                     for nm, e in mono.items())
        along = [e for e, v, _ in degenerate if abs(g @ v) / (np.linalg.norm(g) * np.linalg.norm(v)) >= MATCH_COS]
        sig = None if along else float(math.sqrt(max(g @ pinv @ g, 0.0)))
        combos.append({"name": text, "value": float(math.exp(ln_val)), "ln_value": float(ln_val), "sigma_ln": sig,
                       "constrained": not along})
    for nm in at_edge:
        warnings.append(f"the best fit lies on the grid edge of {nm} along a flat direction; its position there is not "
                        "a measurement")
    n_constrained = len(keep)
    dof = n - n_constrained
    from scipy.stats import chi2 as chi2_dist
    out = {"parameters": params, "chi2": float(chi2), "dof": int(dof),
           "p_value": float(chi2_dist.sf(chi2, dof)) if dof > 0 else None,
           "covariance": info,
           "fisher": {"coordinates": [pr["fit_coordinate"] for pr in params], "matrix": fk.tolist(),
                      "condition_number": cond, "eigen": eig,
                      "method": "J^T C^-1 J at the best fit, J by central differences over one grid cell"
                                + ("; the normalization nuisance profiled (Schur complement)" if nz else "")},
           "degenerate_directions": [e for e, _, _ in degenerate], "combinations": combos, "warnings": warnings,
           "prediction_at_best_fit": pred0.tolist(), "converged": convergence["converged_by"] is not None,
           "optimizer_message": str(res.message), "convergence": convergence}
    if nz:
        out["normalization_nuisance"] = float(p[k])
    if scan is not None:    # level 2 (degeneracy.py): only on request, so the outputs without a scan are unchanged
        level2, out["profile_scans"], scan_warn = _deg.profile_scan(m2ll, p, bounds, names, scales, scan, chi2, degenerate)
        out["degeneracies"] = _deg.screen_objects(degenerate, names, scales) + level2
        warnings += scan_warn
    return out


def grid_fit(doc: dict, base: Path | str = ".") -> dict:
    """Fit grid parameters to a measurement from one gated prediction artifact per grid node (see the module doc)."""
    from contracts.comparison.gate import check as gate_check
    base = Path(base)
    if doc.get("measurement") is None:
        raise CovFitError("ungated: no measurement artifact to gate the predictions against; a grid prediction is fitted "
                          "only after contracts/comparison/gate.py finds it comparable with the measurement")
    meas = _load_json(doc["measurement"], base, "measurement")
    preds_in = doc.get("predictions")
    if not isinstance(preds_in, list) or not preds_in:
        raise CovFitInputError("predictions must be a non-empty list (one prediction artifact per grid node)")
    preds = [_load_json(r, base, f"prediction {i}") for i, r in enumerate(preds_in)]
    gspec = doc.get("grid")
    if not isinstance(gspec, dict) or not isinstance(gspec.get("parameters"), list) or not gspec["parameters"]:
        raise CovFitInputError('grid.parameters must list the grid axes: [{"name": ..., "scale": "log" | "linear"}]')
    names, scales = [], []
    for a in gspec["parameters"]:
        if not isinstance(a, dict) or not isinstance(a.get("name"), str) or a.get("scale", "linear") not in ("log", "linear"):
            raise CovFitInputError('each grid parameter is {"name": str, "scale": "log" | "linear"}')
        names.append(a["name"])
        scales.append(a.get("scale", "linear"))
    if len(set(names)) != len(names):
        raise CovFitInputError("grid parameter names must be unique")
    ms_spec = doc.get("model_set")
    alt_key = ms_spec.get("alternative_key") if isinstance(ms_spec, dict) else None
    if ms_spec is not None and not (isinstance(alt_key, str) and alt_key and alt_key not in names):
        raise CovFitInputError("model_set.alternative_key must name a parameter_point key that is not a grid axis")
    plan = doc.get("gate_plan") or {}
    if not isinstance(plan, dict):
        raise CovFitInputError("gate_plan must be an object")

    # 1. gate every prediction against the measurement
    failures, statuses, gate_ok = [], set(), 0
    for i, pr in enumerate(preds):
        ext = pr.get("extension") if isinstance(pr, dict) else None
        if not isinstance(ext, dict) or ext.get("representation") != "grid":
            raise CovFitInputError(f"prediction {i} must be a prediction artifact with representation 'grid'")
        pp = ext.get("parameter_point") or {}
        cond = dict(plan.get("measurement_conditions") or {})
        for key in names + ([alt_key] if alt_key else []):
            if key in pp:
                cond[key] = pp[key]
        res = gate_check(pr, meas, dict(plan, measurement_conditions=cond))
        statuses.update(res.get("carried_statuses") or [])
        if not res.get("comparable"):
            failures.append({"prediction": pr.get("artifact_id"), "status": res.get("status"),
                             "mismatches": [{k: m.get(k) for k in ("field", "reason")} for m in res.get("mismatches", [])][:5],
                             "findings": res.get("findings", [])[:5]})
        else:
            gate_ok += 1
    if failures:
        raise CovFitError(f"{len(failures)} of {len(preds)} prediction(s) did not pass the comparison gate; they are not "
                          "fitted: " + json.dumps(failures[:3]))

    # 2. data and covariance (from the gated measurement only)
    if meas.get("artifact_type") != "dataset-record" or not isinstance((meas.get("extension") or {}).get("data"), dict):
        raise CovFitInputError("the measurement must be a dataset-record with data values to fit")
    mext = meas["extension"]
    y = np.asarray(mext["data"].get("values"), dtype=float)
    n = len(y)
    edges = mext["data"].get("edges")
    cov, cov_info = data_covariance(mext, base, n)

    # 3. nodes -> grids, one per cross-section set
    by_alt: dict = {}
    for i, pr in enumerate(preds):
        ext = pr["extension"]
        pp = ext.get("parameter_point") or {}
        vals = ext.get("values") or {}
        v = np.asarray(vals.get("values"), dtype=float)
        if v.shape != (n,) or not np.all(np.isfinite(v)):
            raise CovFitInputError(f"prediction {i} has {list(v.shape)} values, the measurement {n}")
        if vals.get("edges") is not None and edges is not None and (len(vals["edges"]) != len(edges) or not np.allclose(vals["edges"], edges, rtol=1e-12)):
            raise CovFitInputError(f"prediction {i} values are binned differently from the measurement data")
        node = []
        for nm, sc in zip(names, scales):
            x = pp.get(nm)
            if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) or (sc == "log" and x <= 0):
                raise CovFitInputError(f"prediction {i}: parameter_point.{nm} must be a finite number{' > 0' if sc == 'log' else ''}")
            node.append(math.log(x) if sc == "log" else float(x))
        alt = pp.get(alt_key) if alt_key else None
        if alt_key and alt is None:
            raise CovFitInputError(f"prediction {i} has no parameter_point.{alt_key}")
        by_alt.setdefault(json.dumps(alt), []).append((tuple(node), v, pr))
    grids = {}
    for alt, rows in by_alt.items():
        axes = [sorted({r[0][j] for r in rows}) for j in range(len(names))]
        if any(len(a) < 2 for a in axes):
            raise CovFitInputError("every grid axis needs at least two nodes")
        shape = [len(a) for a in axes]
        if len(rows) != int(np.prod(shape)) or len({r[0] for r in rows}) != len(rows):
            raise CovFitInputError(f"cross-section set {json.loads(alt)!r}: {len(rows)} predictions do not form a full "
                                   f"grid of {shape} distinct nodes")
        V = np.zeros(shape + [n])
        for node, v, _ in rows:
            V[tuple(a.index(x) for a, x in zip(axes, node))] = v
        grids[alt] = (_Grid(axes, V), rows[0][2])

    # 4. cross-section uncertainty
    u = None
    mult = doc.get("multiplicative")
    if mult is not None:
        if not isinstance(mult, dict) or mult.get("mode") != "nuisance":
            raise CovFitInputError("for a grid, multiplicative.mode must be 'nuisance' (a common normalization fitted with "
                                   "its Gaussian constraint); the data- and model-scaled forms are biased (Peelle)")
        u = _rank_one(_relative_cov(mult.get("relative_cov"), n))
    mode = "+".join(m for m, on in (("nuisance", u is not None), ("model-set", ms_spec is not None)) if on) or "none"
    warnings = []
    if mode == "none":
        warnings.append("no cross-section uncertainty was declared (multiplicative nuisance or model_set); the fit "
                        "treats the predictions as exact")
    if ms_spec is not None and len(grids) < 2:
        raise CovFitInputError("model_set needs predictions for at least two values of the alternative key")
    if ms_spec is None and len(grids) > 1:
        raise CovFitInputError("predictions repeat grid nodes; declare model_set.alternative_key if they are alternatives")

    # 5. theory spec and combinations
    declared = []
    if doc.get("theory_spec") is not None:
        spec = _load_json(doc["theory_spec"], base, "theory_spec")
        # a string entry is the combination; an object entry (contracts 3.14.0) contributes its 'combination'
        entries = (spec.get("extension") or {}).get("degenerate_directions") or []
        declared = [c for c in (d.get("combination") if isinstance(d, dict) else d for d in entries) if isinstance(c, str)]
    else:
        warnings.append("no theory spec given: degenerate directions are reported but not compared")
    wanted = list(dict.fromkeys(declared + [c for c in (doc.get("combinations") or []) if isinstance(c, str)]))
    monomials = {t: _monomial(t, names) for t in wanted}
    for t in declared:
        if monomials.get(t) is None or len(monomials[t]) < 2:
            warnings.append(f"theory-spec degenerate direction {t!r} does not name two or more grid parameters "
                            f"{names}; not compared")
    for t in wanted:
        if t not in declared and monomials.get(t) is None:
            warnings.append(f"combination {t!r} is not a monomial of the grid parameters; not reported")
    start = doc.get("start")
    t0 = None
    if start is not None:
        if not isinstance(start, dict) or set(start) != set(names):
            raise CovFitInputError(f"start must give every grid parameter: {names}")
        if not all(isinstance(start[nm], (int, float)) and not isinstance(start[nm], bool) and math.isfinite(start[nm])
                   and (sc == "linear" or start[nm] > 0) for nm, sc in zip(names, scales)):
            raise CovFitInputError("start values must be finite numbers (> 0 on a log axis)")
        t0 = np.array([math.log(start[nm]) if sc == "log" else float(start[nm]) for nm, sc in zip(names, scales)])

    scan = _deg.parse_scan(doc["degeneracy_scan"], names) if doc.get("degeneracy_scan") is not None else None

    # 6. fit each cross-section set
    fits = []
    for alt, (grid, _) in grids.items():
        if t0 is not None and not grid.inside(t0):
            raise CovFitError(f"start {start} lies outside the grid: nothing is extrapolated")
        r = _grid_one(grid, names, scales, y, cov, u, t0, monomials, [t for t in declared if monomials.get(t) and len(monomials[t]) >= 2],
                      scan)
        r["alternative"] = json.loads(alt)
        r["covariance"].update(cov_info)
        found = [e for e in r["degenerate_directions"]]
        for e in found:
            if e["matches_theory_spec"] is None and declared:
                r["warnings"].append(f"degenerate direction {e['eigenvector']} is not among the theory spec's "
                                     f"degenerate_directions {declared}")
            elif e["matches_theory_spec"] is None and doc.get("theory_spec") is not None:
                r["warnings"].append(f"degenerate direction {e['eigenvector']} found; the theory spec lists none")
        matched = {e["matches_theory_spec"] for e in found}
        for t in declared:
            if monomials.get(t) and len(monomials[t]) >= 2 and t not in matched:
                r["warnings"].append(f"the theory spec lists {t!r} as degenerate, but the data constrain the direction "
                                     "it predicts in this fit")
        fits.append(r)

    # 7. model alternatives and their spread
    envelope_out = None
    if ms_spec is not None:
        from contracts.comparison.model_set import envelope, model_set
        reps = [rep for _, rep in grids.values()]
        ms = model_set(reps)
        if not ms.get("ok"):
            raise CovFitError("the cross-section alternatives are not a valid model set: " + json.dumps(ms.get("problems")))
        cols = [f"{pr['name']}" for pr in fits[0]["parameters"]] + [c["name"] for c in fits[0]["combinations"]]
        rows = {rep.get("artifact_id"): [pr["best_fit"] for pr in f["parameters"]] + [c["value"] for c in f["combinations"]]
                for rep, f in zip(reps, fits)}
        env = envelope(ms, rows, ms_spec.get("prescription"))
        if not env.get("ok"):
            raise CovFitInputError(f"envelope over the cross-section sets refused: {env.get('reason')}")
        envelope_out = {"columns": cols, **env["uncertainty"],
                        "note": "min-max over the separate fits of each cross-section set; a model-alternative object, "
                                "never Gaussian. Along a degenerate direction a parameter's spread is not meaningful; "
                                "read the constrained combinations"}
    for f in fits:
        warnings += [w for w in f.pop("warnings") if w not in warnings]
    return {"label": LABEL, "model": "tabulated-grid",
            "grid_representation": "one prediction artifact per grid node (representation 'grid', node in parameter_point)",
            "grid": {"parameters": [{"name": nm, "scale": sc} for nm, sc in zip(names, scales)],
                     "nodes_per_set": int(np.prod([len(a) for a in next(iter(grids.values()))[0].axes])),
                     "interpolation": "multilinear in the fit coordinates; no extrapolation"},
            "gate": {"predictions_gated": len(preds), "comparable": gate_ok},
            "cross_section_uncertainty": {"mode": mode, "alternative_key": alt_key,
                                          "alternatives": [f["alternative"] for f in fits] if alt_key else None},
            "fits": fits, "envelope": envelope_out, "theory_spec_degenerate_directions": declared,
            "warnings": warnings, "carried_statuses": sorted(statuses),
            "note": ("predictions gated against the measurement before fitting; data covariance assembled from declared "
                     "components only; the best-fit position along a degenerate direction is not a measurement")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fit")
    p.add_argument("--input", required=True)
    p.add_argument("--allow-plugin", action="store_true",
                   help="run a plugin model (a Python file named in the input, relative to the input's folder); it "
                        "runs with your permissions")
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
        elif doc.get("model") == "tabulated-grid":
            out = grid_fit(doc, Path(a.input).resolve().parent)
        elif "datasets" in doc or "scale_nuisance" in doc:
            out = fit_datasets(doc, a.allow_plugin, Path(a.input).resolve().parent)
        else:
            out = fit(doc["y"], doc["cov"], doc.get("model", "constant"), doc.get("x"), doc.get("constraints"),
                      doc.get("start"), doc.get("multiplicative"), model_options=doc.get("model_options"),
                      allow_plugin=a.allow_plugin, base_dir=Path(a.input).resolve().parent)
    except KeyError as exc:
        print(json.dumps({"status": "rejected", "error": f"missing {exc}"}))
        return 2
    except (CovFitInputError, _deg.ScanInputError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    except CovFitIncomplete as exc:
        print(json.dumps({"label": LABEL, "status": "incomplete", "error": str(exc), "missing": exc.missing}, indent=1))
        return 3
    except CovFitPluginError as exc:
        print(json.dumps({"label": LABEL, "status": "failed", "error": str(exc)}))
        return 1
    except CovFitError as exc:
        print(json.dumps({"label": LABEL, "status": "refused", "error": str(exc)}))
        return 1
    except (TypeError, ValueError, AttributeError) as exc:     # a field of the wrong JSON type
        print(json.dumps({"status": "rejected", "error": f"bad input: {type(exc).__name__}: {exc}"}))
        return 2
    # a grid fit whose optimizer stopped before converging is a failed fit, not a result (F-01); the other models
    # refuse non-convergence earlier through the EDM check of _verdict
    stalled = [f for f in out.get("fits") or [] if not f.get("converged", True)]
    if stalled:
        out["status"] = "failed"
        out["reason"] = ("the grid fit did not converge: " + "; ".join(
            f"cross-section set {f.get('alternative')!r}: {f.get('optimizer_message')}" for f in stalled))
        print(json.dumps(out, indent=1))
        return 1
    out["status"] = "ok"
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
