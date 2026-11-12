"""G8, the closure test (Part B section 8.4, with the section 7.3 ensemble rules; phase 2, WP5). `calib_closure.py`
is its CLI.

- Injection points: an interior point >= 2 sigma_tot^design from any physical boundary (bias and coverage), and a
  boundary point at 0.5 sigma_tot^design from a boundary (D55 (i), A8; undercoverage only, one-tailed).
- Pseudo-data from the high-statistics truth MC of the point, resampled with replacement following the data's
  sampling model (D55 (a), A8); each pseudo-data set goes through the full fit with its own MC of nominal size and
  its own bootstrap; its interval toys freeze its own V-hat. Non-converged pseudo-data are replaced (not counted as not
  covered); the ratio test on X summed over both points (n_req = 2 N_c); the interval toys of the whole of G8 form one
  separate ensemble with one ratio test.
- Decision: Holm over the family (standard: bias at the interior point for d parameters, 68% undercoverage at both
  points; full adds 95% undercoverage at both), alpha_G8 = 0.05; bias fails when Holm-significant and
  |b-bar| > 0.2 sigma_tot^design (injected value); coverage by the one-tailed exact binomial against
  c0' = (c - eps_max) / (1 - eps_max).
- N_c = max(N_bias, N_cov) with N_cov the smallest N whose power >= 0.8 holds for N and every larger N (the sawtooth of
  the exact binomial), computed at p1' = p1 / (1 - eps_max).
- Screening: only the Asimov bias is reported, `closure-not-tested`. Remedy level contract when the pseudo-data
  theta-hat fall in a non-truth basin (D57 (2), A8), plan otherwise.
"""
from __future__ import annotations

import math
from functools import cache

import numpy as np
from scipy import stats

from . import fit as F

ALPHA_G8 = 0.05
EPS_MAX = F.EPS_MAX
P1 = {("standard", 0.68): 0.50, ("full", 0.68): 0.58, ("full", 0.95): 0.90}


def family_size(d: int, level: str) -> int:
    return {"standard": 3 * d, "full": 5 * d}[level]


def c0_prime(c: float) -> float:
    return (c - EPS_MAX) / (1.0 - EPS_MAX)


def n_bias(d: int, level: str, delta: float = 0.5, power: float = 0.8) -> int:
    """N_bias >= ((z_{1 - alpha/(2m)} + z_0.8) / 0.5)^2 (the normal approximation of section 8.4)."""
    m = family_size(d, level)
    z = stats.norm.ppf(1 - ALPHA_G8 / (2 * m)) + stats.norm.ppf(power)
    return int(math.ceil((z / delta) ** 2))


@cache
def coverage_power(N: int, c0: float, p1: float, a: float) -> float:
    """Power of the one-tailed exact binomial test of undercoverage at level a, null c0, true coverage p1."""
    kc = int(stats.binom.ppf(a, N, c0))
    while kc >= 0 and stats.binom.cdf(kc, N, c0) > a:
        kc -= 1
    if kc < 0:
        return 0.0
    return float(stats.binom.cdf(kc, N, p1))


def n_cov(d: int, level: str, c: float, horizon: int = 400) -> int:
    """The smallest N such that the power is >= 0.8 for N and for all larger N (checked over `horizon` further N),
    at null c0' and true coverage p1' = p1 / (1 - eps_max), level alpha_G8 / m (section 8.4)."""
    m = family_size(d, level)
    a = ALPHA_G8 / m
    c0 = c0_prime(c)
    p1 = P1[(level, c)] / (1.0 - EPS_MAX)
    N = 10
    while True:
        if coverage_power(N, c0, p1, a) >= 0.8 and all(coverage_power(N + j, c0, p1, a) >= 0.8
                                                       for j in range(1, horizon)):
            return N
        N += 1


def n_c(d: int, level: str) -> dict:
    nb = n_bias(d, level)
    c68 = n_cov(d, level, 0.68)
    c95 = n_cov(d, level, 0.95) if level == "full" else 0
    return {"N_bias": nb, "N_cov_68": c68, "N_cov_95": c95, "N_c": max(nb, c68, c95)}


def holm(pvals: dict, alpha: float = ALPHA_G8) -> dict:
    """Holm step-down: {test: significant}."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, stop = {}, False
    for i, (k, p) in enumerate(items):
        if not stop and p <= alpha / (m - i):
            out[k] = True
        else:
            stop = True
            out[k] = False
    return out


def decide(level: str, names: list, interior: dict, boundary: dict, sigma_design: np.ndarray) -> dict:
    """The G8 decision from the pseudo-data results. `interior`/`boundary` = {pulls?, errors: [N x d] theta-hat -
    truth, cover68: [N x d] bool, cover95: [N x d] bool, nontruth_basin: [N] bool}."""
    p = {}
    err = np.asarray(interior["errors"], float)
    N = err.shape[0]
    bbar = err.mean(0)
    se = err.std(0, ddof=1) / math.sqrt(N)
    for i, nm in enumerate(names):
        t = bbar[i] / se[i] if se[i] > 0 else (math.inf if bbar[i] else 0.0)
        p[("bias", nm)] = float(2 * stats.t.sf(abs(t), N - 1))
    levels = [0.68] + ([0.95] if level == "full" else [])
    for pt_name, pt in (("interior", interior), ("boundary", boundary)):
        for c in levels:
            cov = np.asarray(pt[f"cover{int(c * 100)}"], bool)
            for i, nm in enumerate(names):
                x = int(cov[:, i].sum())
                p[(f"cover{int(c * 100)}", pt_name, nm)] = float(stats.binom.cdf(x, cov.shape[0], c0_prime(c)))
    sig = holm(p)
    fails = []
    for i, nm in enumerate(names):
        if sig[("bias", nm)] and abs(bbar[i]) > 0.2 * sigma_design[i]:
            fails.append({"test": "bias", "theta": nm, "b_bar": float(bbar[i]), "p": p[("bias", nm)]})
    for k, s in sig.items():
        if k[0] != "bias" and s:
            fails.append({"test": k[0], "point": k[1], "theta": k[2], "p": p[k]})
    nontruth = bool(np.any(interior.get("nontruth_basin", [False])) or np.any(boundary.get("nontruth_basin",
                                                                                            [False])))
    ok = not fails
    return {"gate": "G8", "status": "passed" if ok else "failed", "level": level, "family": len(p), "fails": fails,
            "p": {"|".join(map(str, k)): v for k, v in p.items()}, "b_bar": bbar.tolist(),
            "finding": None if ok else "g8.closure",
            "remedy": None if ok else ("contract" if nontruth else "plan")}


def screening(asimov_bias: np.ndarray) -> dict:
    return {"gate": "G8", "status": "not-decided", "level": "screening", "asimov_bias": np.asarray(asimov_bias).tolist(),
            "flags": ["closure-not-tested"]}


def not_executed(reason: str) -> dict:
    """The plan declares that G8 is not executed: no decision, `closure-not-tested` (section 8.4)."""
    return {"gate": "G8", "status": "not-decided", "reason": reason, "flags": ["closure-not-tested"]}


def injection_points(theta_box: list, bounds: list, sigma_design: np.ndarray, center: np.ndarray, which: int = 0):
    """An interior point (the given centre, moved inward so that it is >= 2 sigma_tot^design from every physical
    boundary) and a boundary point 0.5 sigma_tot^design inside the lower boundary of parameter `which` (D55 (i))."""
    c = np.asarray(center, float).copy()
    for i, (lo, hi) in enumerate(bounds):
        if np.isfinite(lo):
            c[i] = max(c[i], lo + 2 * sigma_design[i])
        if np.isfinite(hi):
            c[i] = min(c[i], hi - 2 * sigma_design[i])
    b = c.copy()
    lo = bounds[which][0]
    if not np.isfinite(lo):
        raise F.FitError("g8.no_boundary", "the boundary point needs a finite physical boundary")
    b[which] = lo + 0.5 * sigma_design[which]
    return c, b


def run_point(make_pseudo, fit_and_cover, n_req: int, seeds, truth_basin=None) -> dict:
    """The pseudo-data of one injection point as an estimation ensemble with replacement (section 7.3).
    `make_pseudo(seed)` returns a problem with its pseudo-data and its own MC; `fit_and_cover(problem, seed)` returns
    (converged, error = theta-hat - truth, cover68, cover95, interval toys {n, X}, basin_ok)."""
    errors, c68, c95, nontruth, toys_x, toys_n = [], [], [], [], 0, 0

    def member(s):
        pr = make_pseudo(s)
        ok, err, cv68, cv95, itoys, basin_ok = fit_and_cover(pr, s)
        return ok, (err, cv68, cv95, itoys, basin_ok), {}
    res = F.run_estimation_ensemble(member, n_req, seeds)
    for err, cv68, cv95, itoys, basin_ok in res.values:
        errors.append(err)
        c68.append(cv68)
        c95.append(cv95)
        nontruth.append(not basin_ok)
        toys_x += itoys.get("X", 0)
        toys_n += itoys.get("n", 0)
    return {"errors": np.array(errors), "cover68": np.array(c68), "cover95": np.array(c95),
            "nontruth_basin": np.array(nontruth), "X": res.X, "n_completed": res.n_completed,
            "interval_toys": {"X": toys_x, "n": toys_n}, "seeds_used": res.seeds_used}


def g8(level: str, names, sigma_design, interior: dict, boundary: dict) -> dict:
    """G8 at standard or full level: the summed ratio test of the pseudo-data fits (n_req = 2 N_c), the summed ratio
    test of the interval toys of the whole of G8 (on failure G8 is incomplete and only the interval toys are
    regenerated), then the decision."""
    X = interior["X"] + boundary["X"]
    N = interior["errors"].shape[0]
    kst = F.k_star(2 * N)
    if X >= kst:
        return {"gate": "G8", "status": "failed", "finding": "g8.ratio_test", "X": X, "k_star": kst,
                "remedy": "plan"}
    it = {"X": interior["interval_toys"]["X"] + boundary["interval_toys"]["X"],
          "n": interior["interval_toys"]["n"] + boundary["interval_toys"]["n"]}
    if it["n"] and it["X"] >= F.k_star(it["n"], False):
        return {"gate": "G8", "status": "incomplete", "finding": "g8.interval_toys_ratio_test", **it}
    return decide(level, list(names), interior, boundary, np.asarray(sigma_design, float))
