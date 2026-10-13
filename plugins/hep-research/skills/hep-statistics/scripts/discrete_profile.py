#!/usr/bin/env python3
"""Discrete profiling of the background functional form (envelope method) with its validation study (audit T27).
EXPERIMENTAL. Needs NumPy and SciPy.

Model: a binned spectrum on [100, 180] (40 bins) with a Gaussian signal (mean 125, width 2, yield mu * S) on a smooth
background whose functional form is not known. The candidate forms and the penalty are fixed here, before any study
(CANDIDATES, PENALTY_PER_PARAMETER): exp1 (2 parameters), pow1 (2), exp2 (4: two exponentials) and bern3 (4: a
positive Bernstein polynomial of degree 3). The envelope is Lambda(mu) = min over forms f of
[2 NLL_f(mu) + PENALTY_PER_PARAMETER * n_par(f)] (Dauncey, Kenzie, Wardle, Davies 2015, arXiv:1408.6865), so the
choice of form is profiled like a discrete nuisance. The 68.27% interval is {mu: Lambda(mu) - min Lambda <= 1}.

study: for each true background (each candidate and one outside the family) and each injected mu, seeded toys repeat
the complete procedure: every form refitted, the envelope rebuilt, the interval found. Reported per truth: the mean
bias in units of the toy spread, the interval coverage with its exact binomial interval, the spurious signal (mean
fitted mu at mu = 0), and the forms chosen at the best fit. A single fixed form is run beside it as the negative
baseline. Testing only the nominal truth is not a validation: a form outside the family is always included.

Usage: discrete_profile.py study --toys 200 --seed 1 [--out RESULTS.json]
Exit codes: 0 ok; 2 bad input. Output JSON labelled [General method] EXPERIMENTAL SYNTHETIC.
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

LABEL = "[General method] EXPERIMENTAL SYNTHETIC"
if np is not None:  # module data of the study (needs NumPy)
    EDGES = np.linspace(100.0, 180.0, 41)
    X = 0.5 * (EDGES[1:] + EDGES[:-1])
    U = (X - 100.0) / 80.0
    PENALTY_PER_PARAMETER = 1.0          # in -2 ln L units, fixed before any study
    # acceptance, fixed before the first study run: the envelope passes at a truth when |bias| <= 0.2 of the toy spread and
    # the one-sided 95% lower bound on its 68.27% coverage (Bonferroni over the rows) is at least 0.6827 - 0.05
    CRITERIA = {"max_abs_bias_over_spread": 0.2, "coverage_nominal": 0.6827, "max_coverage_deficit": 0.05, "bound_cl": 0.95}
    S_TOTAL = 30.0
    SIG = np.exp(-0.5 * ((X - 125.0) / 2.0) ** 2)
    SIG = S_TOTAL * SIG / SIG.sum()


def _exp1(p):
    return np.exp(p[0] - p[1] * U)


def _pow1(p):
    return np.exp(p[0]) * (X / 100.0) ** (-abs(p[1]))


def _exp2(p):
    return np.exp(p[0] - p[1] * U) + np.exp(p[2] - p[3] * U)


def _bern3(p):
    c = np.exp(p)                       # positive coefficients: a positive background
    return (c[0] * (1 - U) ** 3 + 3 * c[1] * U * (1 - U) ** 2 + 3 * c[2] * U ** 2 * (1 - U) + c[3] * U ** 3)


CANDIDATES = {"exp1": (_exp1, [4.0, 2.0]), "pow1": (_pow1, [4.0, 4.0]), "exp2": (_exp2, [4.0, 3.0, 2.0, 0.5]),
              "bern3": (_bern3, [4.0, 3.5, 3.0, 2.5])}
TRUTHS = {"exp1": lambda: _exp1([math.log(60.0), 2.5]), "pow1": lambda: _pow1([math.log(60.0), 4.5]),
          "bern3": lambda: _bern3(np.log([60.0, 30.0, 18.0, 9.0])),
          "outside_family": lambda: 55.0 * np.exp(-2.2 * U) * (1 + 0.25 * np.sin(2.5 * U))}


def _nll(nu, n):
    nu = np.maximum(nu, 1e-300)
    return float(np.sum(nu - n * np.log(nu)))


def fit_form(form: str, n, mu: float | None, start=None):
    """Best fit of one background form, with mu fixed or free; returns (2 NLL, parameters, mu)."""
    f, p0 = CANDIDATES[form]
    p0 = np.asarray(start if start is not None else p0, float)

    def obj(z):
        m = z[0] if mu is None else mu
        p = z[1:] if mu is None else z
        nu = m * SIG + f(p)
        if np.any(nu <= 0) or not np.all(np.isfinite(nu)):
            return 1e30
        return 2.0 * _nll(nu, n)
    z0 = np.concatenate([[0.5], p0]) if mu is None else p0
    best = None
    for z_start in (z0, z0 * 1.05):
        r = optimize.minimize(obj, z_start, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-7, "maxiter": 6000})
        r = optimize.minimize(obj, r.x, method="BFGS")
        if best is None or r.fun < best.fun:
            best = r
    m = best.x[0] if mu is None else mu
    return float(best.fun), best.x[1:] if mu is None else best.x, float(m)


def envelope(n, forms=None, mu=None):
    forms = forms or list(CANDIDATES)
    vals = {f: fit_form(f, n, mu) for f in forms}
    pen = {f: v[0] + PENALTY_PER_PARAMETER * len(CANDIDATES[f][1]) for f, v in vals.items()}
    best = min(pen, key=pen.get)
    return pen[best], best, vals[best][2]


class IntervalFailure(RuntimeError):
    """The envelope interval could not be established for this data set (counted as a failed toy)."""


def interval(n, forms=None, level=1.0):
    lam0, form0, mu0 = envelope(n, forms)
    g = lambda m: envelope(n, forms, m)[0] - lam0 - level
    if g(mu0) > -0.5 * level:      # a conditional fit at the best mu worse than the global one: a fit failure
        raise IntervalFailure("the conditional envelope at the best-fit mu is not below the threshold")
    step = 0.5
    lo = mu0 - step
    while g(lo) < 0 and lo > mu0 - 20:
        lo -= step
    hi = mu0 + step
    while g(hi) < 0 and hi < mu0 + 20:
        hi += step
    try:
        return mu0, form0, optimize.brentq(g, lo, mu0, xtol=1e-3), optimize.brentq(g, mu0, hi, xtol=1e-3)
    except ValueError as exc:
        raise IntervalFailure(f"no bracket for the interval end: {exc}") from None


def classify(rows) -> None:
    """Verdicts of each row under CRITERIA: bias_ok; coverage_verdict pass (one-sided lower bound, Bonferroni over the
    envelope rows, at least nominal - deficit), fail (the upper bound below it) or insufficient-precision (the toys
    cannot decide); pass needs both. Failed toys count as not covering."""
    from core_tail import one_sided_lower, one_sided_upper
    n_rows = sum(1 for r in rows if r["procedure"] == "envelope")
    level = 1 - (1 - CRITERIA["bound_cl"]) / n_rows
    threshold = CRITERIA["coverage_nominal"] - CRITERIA["max_coverage_deficit"]
    for r in rows:
        k = round(r["coverage_68"] * r["toys"])
        lb, ub = one_sided_lower(k, r["toys"], level), one_sided_upper(k, r["toys"], level)
        r["coverage_lower_bound"], r["coverage_upper_bound"] = lb, ub
        r["bias_ok"] = abs(r["bias_over_spread"]) <= CRITERIA["max_abs_bias_over_spread"]
        r["coverage_verdict"] = "pass" if lb >= threshold else ("fail" if ub < threshold else "insufficient-precision")
        r["pass"] = r["bias_ok"] and r["coverage_verdict"] == "pass"


PROCEDURES = {"envelope": None, "single_exp1": ["exp1"]}


def _row(args) -> dict:
    """One (truth, injected mu, procedure) row; its seeds depend only on (seed, truth index, mu, procedure), so rows
    can run in any order or in parallel and reproduce the sequential study."""
    t_idx, t_name, mu_true, label, toys, seed = args
    from core_tail import clopper_pearson
    bkg, forms = TRUTHS[t_name](), PROCEDURES[label]
    rng = np.random.default_rng([seed, t_idx, int(10 * mu_true), 0 if label == "envelope" else 1])
    est, cov, chosen, failed = [], 0, {}, 0
    for _ in range(toys):
        n = rng.poisson(mu_true * SIG + bkg)
        try:
            m0, f0, lo, hi = interval(n, forms)
        except IntervalFailure:
            failed += 1          # counted as not covering (policy count-as-noncovering)
            continue
        est.append(m0)
        cov += lo <= mu_true <= hi
        chosen[f0] = chosen.get(f0, 0) + 1
    e = np.array(est)
    return {"truth": t_name, "mu_true": mu_true, "procedure": label, "toys": toys, "failed": failed,
            "failure_policy": "count-as-noncovering",
            "mean_mu_hat": float(e.mean()), "spread": float(e.std(ddof=1)),
            "bias_over_spread": float((e.mean() - mu_true) / e.std(ddof=1)),
            "coverage_68": cov / toys, "coverage_interval_95": list(clopper_pearson(cov, toys, 0.95)),
            "forms_chosen": chosen}


def study(toys: int, seed: int, mus=(0.0, 1.0), progress: Path | None = None,
          procedures=("envelope", "single_exp1"), workers: int = 1) -> dict:
    jobs = [(t_idx, t_name, mu_true, label, toys, seed) for t_idx, t_name in enumerate(TRUTHS)
            for mu_true in mus for label in procedures]
    rows = []
    if workers > 1:
        from multiprocessing import get_context
        with get_context("spawn").Pool(workers) as pool:
            for r in pool.imap(_row, jobs):
                rows.append(r)
                if progress is not None:
                    progress.write_text(json.dumps(rows, indent=1) + "\n")
    else:
        for job in jobs:
            rows.append(_row(job))
            if progress is not None:
                progress.write_text(json.dumps(rows, indent=1) + "\n")
    classify(rows)
    return {"label": LABEL, "criteria": CRITERIA, "candidates": {k: len(v[1]) for k, v in CANDIDATES.items()},
            "penalty_per_parameter_m2lnl": PENALTY_PER_PARAMETER, "signal_total": S_TOTAL, "seed": seed,
            "procedures": list(procedures), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    s = sub.add_parser("study")
    s.add_argument("--toys", type=int, default=200)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--out")
    s.add_argument("--procedures", default="envelope,single_exp1")
    s.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy and SciPy are required"}))
        return 2
    if a.toys < 10:
        print(json.dumps({"status": "rejected", "error": "--toys must be at least 10"}))
        return 2
    procs = tuple(x for x in a.procedures.split(",") if x)
    if not set(procs) <= set(PROCEDURES):
        print(json.dumps({"status": "rejected", "error": f"--procedures must name {sorted(PROCEDURES)}"}))
        return 2
    out = study(a.toys, a.seed, progress=Path(a.out).with_suffix(".partial.json") if a.out else None,
                procedures=procs, workers=a.workers)
    text = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
if True:  # the plugin root is on sys.path: the exact binomial interval of core/stats
    import importlib
    sys.modules.setdefault("core_tail", importlib.import_module("core.stats.tail_estimation"))

if __name__ == "__main__":
    sys.exit(main())
