#!/usr/bin/env python3
"""Expected discovery sensitivity for a counting experiment, and a toy-calibrated goodness of fit for a binned
Poisson template model.

Subcommands:
  asimov-z  --s S --b B [--sigma-b SB]
            Median discovery significance from the Asimov data set (Cowan, Cranmer, Gross, Vitells 2011, eq. 97):
              Z_A = sqrt(2 ((s+b) ln(1 + s/b) - s)).
            With --sigma-b, the version with a background uncertainty (G. Cowan, "Discovery sensitivity for a
            counting experiment with background uncertainty", 2012 note, eq. 20), which assumes the background is
            constrained by a Poisson auxiliary measurement m ~ Pois(tau b) with tau = b / sigma_b^2 (not a Gaussian
            constraint):
              Z_A = sqrt(2 [(s+b) ln((s+b)(b+sb^2) / (b^2 + (s+b) sb^2)) - (b^2/sb^2) ln(1 + sb^2 s / (b (b+sb^2)))]).
            The large-b limits s/sqrt(b) and s/sqrt(b + sb^2) are printed only as such. For the expected median and
            1/2-sigma bands of an upper limit use core/stats poisson_diagnostics.py cls-limit (known background) or
            likelihood_limits.py profile-cls / multibin-limit.
  gof       --input FILE --toys N --seed S [--min-expected E]
            Fit nonnegative yields of fixed templates to binned counts (Poisson maximum likelihood), compute the
            saturated-model deviance D = 2 sum(nu - n + n ln(n/nu)) (zero-count terms by their limit 2 nu), and
            calibrate it with seeded toys drawn from the fitted model and refitted one by one. Pearson and Neyman
            chi2 are reported only when every fitted expectation is at least --min-expected (default 5 [Proposal])
            and every count is positive; otherwise they are withheld, not approximated. A good GoF p-value does not
            show the absence of bias: that needs closure or injection tests.

Input JSON for gof: {"observed": [n_i], "templates": {"name": [t_i], ...}} (templates are shapes; their yields are
fitted, each >= 0). Output: JSON with the statistic, the observed value, the toy p-value (binomial Monte Carlo error,
or a 95% bound with zero exceedances), the asymptotic chi2 reference (labeled as such), the seed and the toy count.
Needs NumPy (and SciPy for the chi2 reference). Exit codes: 0 ok; 1 the fit did not converge; 2 rejected input.
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


def z_asimov(s, b, sigma_b=None):
    if not (s >= 0 and b > 0) or (sigma_b is not None and not sigma_b > 0):
        raise ValueError("need s >= 0, b > 0 and sigma_b > 0")
    if sigma_b is None:
        return math.sqrt(2 * ((s + b) * math.log1p(s / b) - s))
    v = sigma_b ** 2
    t1 = (s + b) * math.log((s + b) * (b + v) / (b * b + (s + b) * v))
    t2 = (b * b / v) * math.log1p(v * s / (b * (b + v)))
    return math.sqrt(max(2 * (t1 - t2), 0.0))


def fit_yields(n, A, em_iters=30, newton_iters=100, tol=1e-10):
    """Poisson ML of nonnegative yields y (columns of A are unit-normalized shapes) for each row of n.
    A few multiplicative (EM) updates, which keep y >= 0, then damped Newton steps on the concave log-likelihood
    that stop short of the y = 0 boundary (a yield whose optimum is 0 shrinks geometrically towards it).
    Returns (y [T, J], converged [T])."""
    n = np.atleast_2d(np.asarray(n, float))
    col = A.sum(axis=0)
    y = np.tile(n.sum(axis=1, keepdims=True) / A.shape[1], (1, A.shape[1])) + 1e-9
    for _ in range(em_iters):
        nu = y @ A.T
        ratio = np.where(nu > 0, n / np.where(nu > 0, nu, 1.0), 0.0)
        y = y * (ratio @ A) / col
    conv = np.zeros(n.shape[0], bool)
    for _ in range(newton_iters):
        nu = np.maximum(y @ A.T, 1e-300)
        grad = (n / nu - 1.0) @ A                                           # [T, J]
        hess = -np.einsum("ti,ij,ik->tjk", n / nu ** 2, A, A)               # [T, J, J]
        hess -= 1e-12 * np.eye(A.shape[1])
        step = -np.linalg.solve(hess, grad[..., None])[..., 0]
        with np.errstate(divide="ignore", invalid="ignore"):
            limit = np.where(step < 0, 0.9 * y / -step, np.inf).min(axis=1)
        t = np.minimum(1.0, limit)[:, None]
        y_new = y + t * step
        conv = np.max(np.abs(y_new - y) / (1.0 + y), axis=1) < tol
        y = y_new
        if np.all(conv):
            break
    return y, conv


def deviance(n, nu):
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(n > 0, nu - n + n * np.log(n / nu), nu)
    return 2 * term.sum(axis=-1)


def gof(doc, toys, seed, min_expected=5.0):
    if not isinstance(doc, dict) or not isinstance(doc.get("templates"), dict) or not doc["templates"]:
        raise ValueError("input needs 'observed' and a non-empty 'templates' object")
    n = np.asarray(doc.get("observed", []), float)
    names = list(doc["templates"])
    A = np.asarray([doc["templates"][k] for k in names], float).T
    if n.ndim != 1 or n.size == 0 or A.shape[0] != n.size:
        raise ValueError("every template needs one entry per observed bin")
    if np.any(n < 0) or np.any(n != np.round(n)):
        raise ValueError("observed counts must be nonnegative integers")
    if not np.all(np.isfinite(A)) or np.any(A < 0) or np.any(A.sum(axis=0) <= 0):
        raise ValueError("templates must be finite, nonnegative and non-empty")
    if A.shape[1] >= n.size:
        raise ValueError("need more bins than templates for a goodness-of-fit test")
    A = A / A.sum(axis=0)
    y, conv = fit_yields(n, A)
    if not conv[0]:
        return {"status": "failed", "error": "the fit of the observed data did not converge"}, 1
    nu = (y @ A.T)[0]
    if np.any((nu <= 0) & (n > 0)):
        return {"status": "failed", "error": "a bin with data has zero fitted expectation (model infeasible)"}, 1
    d_obs = float(deviance(n, nu))
    rng = np.random.default_rng(seed)
    nt = rng.poisson(nu, size=(toys, n.size)).astype(float)
    yt, ct = fit_yields(nt, A)
    d_toys = deviance(nt, yt @ A.T)
    failed = int(np.sum(~ct))
    k = int(np.sum(d_toys >= d_obs - 1e-9))
    ndof = n.size - A.shape[1]
    res = {"status": "ok", "statistic": "saturated Poisson deviance", "observed": d_obs, "ndof": ndof,
           "fitted_yields": dict(zip(names, map(float, y[0]))), "toys": toys, "seed": seed, "exceedances": k,
           "toy_fits_not_converged": failed,
           "calibration": "toys from the fitted model, each refitted (parametric bootstrap)"}
    if failed:
        res["note"] = "some toy fits did not converge; they are kept in the count, check the model"
    if k == 0:
        res.update(p_value=None, p_upper_95=1 - 0.05 ** (1 / toys))
    else:
        p = k / toys
        res.update(p_value=p, mc_error=math.sqrt(p * (1 - p) / toys))
    try:
        from scipy.stats import chi2
        res["asymptotic_reference"] = {"p_value": float(chi2.sf(d_obs, ndof)),
                                       "label": f"chi2 with {ndof} dof; valid only for large expected counts"}
    except ImportError:
        pass
    if np.all(nu >= min_expected) and np.all(n > 0):
        res["pearson_chi2"] = float(np.sum((n - nu) ** 2 / nu))
        res["neyman_chi2"] = float(np.sum((n - nu) ** 2 / n))
    else:
        res["chi2_withheld"] = f"Pearson/Neyman chi2 need every fitted expectation >= {min_expected} and every count > 0"
    return res, 0


def build_parser():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n", 1)[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("asimov-z")
    a.add_argument("--s", type=float, required=True)
    a.add_argument("--b", type=float, required=True)
    a.add_argument("--sigma-b", type=float)
    g = sub.add_parser("gof")
    g.add_argument("--input", required=True)
    g.add_argument("--toys", type=int, default=1000)
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--min-expected", type=float, default=5.0)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "asimov-z":
            z = z_asimov(args.s, args.b, args.sigma_b)
            out = {"z_asimov": z, "s": args.s, "b": args.b, "sigma_b": args.sigma_b,
                   "formula": "Cowan et al. 2011 eq. 97" if args.sigma_b is None else
                   "Cowan 2012 note eq. 20 (Poisson auxiliary measurement, tau = b / sigma_b^2)",
                   "large_b_limit": {"value": args.s / math.sqrt(args.b + (args.sigma_b or 0) ** 2),
                                     "label": "s/sqrt(b + sigma_b^2): large-b limit only, not a significance"}}
            code = 0
        else:
            if np is None:
                raise ValueError("NumPy is required for gof")
            if args.toys < 1:
                raise ValueError("--toys must be positive")
            with open(args.input, encoding="utf-8") as fh:
                out, code = gof(json.load(fh), args.toys, args.seed, args.min_expected)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(out, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
