#!/usr/bin/env python3
"""Likelihood-ratio estimation by classification, checked against an analytic oracle (audit T30). EXPERIMENTAL.
Needs NumPy. A calibratable example, not a production simulation-based-inference tool: model training beyond this
belongs to hep-ml (ml-artifact handoff), and its use in an inference to hep-statistics with this check.

Model: x ~ Normal(theta + nu, 1) with a nuisance nu ~ Normal(0, sigma_nu) marginalized; hypotheses theta0 = 0 and
theta1. The exact marginal densities are Normal(theta, 1 + sigma_nu^2), so the exact log-ratio is quadratic in x (here
linear, the variances being equal). A logistic classifier on the features (1, x, x^2) is trained (Newton/IRLS) on
equal samples of the two hypotheses; its logit estimates log r(x) = log p1(x) / p0(x).

Checks, with their thresholds and sample sizes fixed here before any run (CHECKS):
- accuracy: the RMS difference between estimated and exact log r on held-out data below 0.05;
- seed stability: the spread of the estimated log r over independent training seeds below 0.05 (RMS);
- calibration: the density-ratio identities E_p0[r(x)] = 1 and E_p1[1 / r(x)] = 1 on fresh samples drawn from the
  model the estimator is meant for; a deviation beyond 4 standard errors fails. The power of this test against the
  stated alternatives (data with sigma_nu doubled: a domain shift; an estimator trained with sigma_nu = 0: a wrong
  nuisance model) is estimated by simulation and must be at least 0.9: otherwise the check is underpowered and its
  pass is not evidence (status inconclusive). One p-value above 0.05 proves nothing.

Usage: ratio_estimation.py check [--theta1 0.5 --sigma-nu 0.5 --n 20000 --seed 1 --power-runs 30]
Exit codes: 0 pass; 1 fail; 3 inconclusive (underpowered). Output JSON labelled [General method] EXPERIMENTAL SYNTHETIC.
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

try:  # --help works without them; main() refuses to run without them (STH-T3.1)
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

LABEL = "[General method] EXPERIMENTAL SYNTHETIC"
CHECKS = {"max_rms_logr_error": 0.05, "max_seed_rms_spread": 0.05, "calibration_z": 4.0, "power_min": 0.9,
          "train_size": 40000, "test_size": 20000, "seeds": 5}


def sample(rng, theta, sigma_nu, n):
    return theta + sigma_nu * rng.standard_normal(n) + rng.standard_normal(n)


def features(x):
    return np.column_stack([np.ones_like(x), x, x * x])


def train(rng, theta1, sigma_nu, n):
    x = np.concatenate([sample(rng, 0.0, sigma_nu, n), sample(rng, theta1, sigma_nu, n)])
    y = np.concatenate([np.zeros(n), np.ones(n)])
    f = features(x)
    w = np.zeros(f.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-(f @ w)))
        g = f.T @ (y - p)
        h = (f * (p * (1 - p))[:, None]).T @ f + 1e-9 * np.eye(f.shape[1])
        step = np.linalg.solve(h, g)
        w += step
        if np.max(np.abs(step)) < 1e-10:
            break
    return w


def log_r_hat(w, x):
    return features(x) @ w


def log_r_exact(x, theta1, sigma_nu):
    v = 1 + sigma_nu ** 2
    return (-(x - theta1) ** 2 + x ** 2) / (2 * v)


def calibration(w, rng, theta1, sigma_nu_data, n):
    x0, x1 = sample(rng, 0.0, sigma_nu_data, n), sample(rng, theta1, sigma_nu_data, n)
    r0, inv1 = np.exp(log_r_hat(w, x0)), np.exp(-log_r_hat(w, x1))
    z0 = (r0.mean() - 1) / (r0.std(ddof=1) / math.sqrt(n))
    z1 = (inv1.mean() - 1) / (inv1.std(ddof=1) / math.sqrt(n))
    return {"z_E0_r": float(z0), "z_E1_inv_r": float(z1), "reject": bool(max(abs(z0), abs(z1)) > CHECKS["calibration_z"])}


def check(theta1=0.5, sigma_nu=0.5, n=CHECKS["test_size"], seed=1, power_runs=30) -> dict:
    rng = np.random.default_rng(seed)
    ws = [train(np.random.default_rng([seed, k]), theta1, sigma_nu, CHECKS["train_size"]) for k in range(CHECKS["seeds"])]
    xt = np.concatenate([sample(rng, 0.0, sigma_nu, n), sample(rng, theta1, sigma_nu, n)])
    exact = log_r_exact(xt, theta1, sigma_nu)
    est = np.array([log_r_hat(w, xt) for w in ws])
    rms_err = float(np.sqrt(np.mean((est[0] - exact) ** 2)))
    spread = float(np.sqrt(np.mean(est.std(axis=0, ddof=1) ** 2)))
    cal = calibration(ws[0], rng, theta1, sigma_nu, n)
    power = None
    if power_runs:
        prng = np.random.default_rng([seed, 999])
        wrong = train(np.random.default_rng([seed, 998]), theta1, 0.0, CHECKS["train_size"])
        shift = sum(calibration(ws[0], prng, theta1, 2 * sigma_nu, n)["reject"] for _ in range(power_runs)) / power_runs
        misfit = sum(calibration(wrong, prng, theta1, sigma_nu, n)["reject"] for _ in range(power_runs)) / power_runs
        power = {"domain_shift_sigma_nu_doubled": shift, "estimator_trained_without_nuisance": misfit}
    ok = rms_err <= CHECKS["max_rms_logr_error"] and spread <= CHECKS["max_seed_rms_spread"] and not cal["reject"]
    under = power is None or min(power.values()) < CHECKS["power_min"]
    status = "fail" if not ok else ("inconclusive" if under else "pass")
    return {"label": LABEL, "status": status, "checks": CHECKS, "theta1": theta1, "sigma_nu": sigma_nu, "seed": seed,
            "rms_logr_error_vs_exact": rms_err, "seed_rms_spread": spread, "calibration": cal, "power": power,
            "note": ("the oracle is exact only for this Gaussian model; a passing check validates this estimator on this "
                     "model and sample size, not the method in general")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check")
    c.add_argument("--theta1", type=float, default=0.5)
    c.add_argument("--sigma-nu", type=float, default=0.5)
    c.add_argument("--n", type=int, default=CHECKS["test_size"])
    c.add_argument("--seed", type=int, default=1)
    c.add_argument("--power-runs", type=int, default=30)
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy is required"}))
        return 2
    if a.n < 100 or a.power_runs < 0 or not (math.isfinite(a.theta1) and math.isfinite(a.sigma_nu) and a.sigma_nu >= 0):
        print(json.dumps({"status": "rejected", "error": "need --n >= 100, --power-runs >= 0, finite --theta1 and --sigma-nu >= 0"}))
        return 2
    out = check(a.theta1, a.sigma_nu, a.n, a.seed, a.power_runs)
    print(json.dumps(out, indent=1))
    return {"pass": 0, "fail": 1, "inconclusive": 3}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
