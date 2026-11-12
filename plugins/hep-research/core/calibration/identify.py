"""P3 and G5: identifiability (Part B sections 8.2, 8.3, 3.5; phase 2, WP3). `calib_identify.py` is the CLI;
`calib_design.py` (the P3 of each cross-validation training fold) and `calib_validate.py` (G5 of each fold and toy)
call these functions (section 14: one implementation).

Measures (section 8.3): lambda_min of the correlation matrix of the theta block of Sigma = F^-1 (F the information
over all of beta, nuisances profiled); sigma_post,i / sigma_prior,i with sigma_prior,i = range / sqrt(12) for a
bounded uniform prior (D54). P3 at the prior centre with Asimov data: lambda_min >= 0.1, ratio <= 0.4. G5 at
theta-hat: lambda_min >= 0.05, ratio <= 0.5, and the profile Delta(-2 ln L) >= 4 within the prior range on both
sides of every theta_i; G5 also fails when section 7.4 admits no endpoint or finds a non-identified stationary point
more than tau_tie below the lowest basin. Hints come from the section 3.5 degeneracy modes the problem declares
(`degeneracy_modes`: [{mode, parameters, signal}]); they take no part in the decision.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import linalg

from . import fit as F
from . import likelihood as L

P3_LAMBDA, P3_RATIO = 0.1, 0.4
G5_LAMBDA, G5_RATIO, G5_PROFILE = 0.05, 0.5, 4.0


def measures(cov_theta: np.ndarray, sigma_prior) -> dict:
    s = np.sqrt(np.diag(cov_theta))
    R = cov_theta / np.outer(s, s)
    w, V = np.linalg.eigh(0.5 * (R + R.T))
    return {"lambda_min": float(w.min()), "direction": V[:, 0].tolist(),
            "ratio": (s / np.asarray(sigma_prior, float)).tolist(), "sigma_post": s.tolist()}


def information(problem, beta: np.ndarray, ref: L.Reference | None = None) -> np.ndarray:
    """The expected information over beta at beta (Asimov: F does not depend on the observed values), as the
    covariance Sigma_beta = 2 F^-1 of D = -2 ln L."""
    lk = L.Likelihood(problem.layout, problem.observed, ref or problem.reference(beta[F._tp_index_layout(problem.layout)],
                                                                             beta))
    tpi = F._tp_index(lk)
    h = problem.h(beta[tpi])
    _, Fm = lk.score_fisher(beta, h, F.jacobian(problem, beta[tpi], F.fd_steps(problem)))
    return Fm


def _sigma_theta(Fm, d):
    try:
        S = 2.0 * linalg.inv(Fm)
    except (linalg.LinAlgError, ValueError):
        return None
    if not np.all(np.isfinite(S)) or np.any(np.diag(S)[:d] <= 0):
        return None
    return 0.5 * (S + S.T)[:d, :d]


def hints(problem, direction, names) -> list:
    """Section 3.5 modes whose parameters carry the near-null direction (loading >= 0.3)."""
    heavy = {n for n, v in zip(names, direction) if abs(v) >= 0.3}
    out = []
    for m in getattr(problem, "degeneracy_modes", []) or []:
        par = set(m["parameters"])
        if heavy & par and (heavy <= par or len(heavy & par) >= 2):     # the direction lies in the mode's parameters
            out.append({"mode": m["mode"], "parameters": m["parameters"], "signal": m.get("signal")})
    if not out:
        out.append({"mode": "unspecified", "parameters": sorted(heavy), "signal": None})
    return out


def p3(problem, beta_ref: np.ndarray, ref: L.Reference | None = None) -> dict:
    """P3 at the prior centre with Asimov data (section 8.2): not identifiable when lambda_min(R_corr) < 0.1 or any
    sigma_post / sigma_prior > 0.4 (remedy level contract; plan for efficiency-map error, phase 3)."""
    d = len(problem.layout.theta)
    S = _sigma_theta(information(problem, beta_ref, ref), d)
    names = problem.layout.theta
    if S is None:
        return {"gate": "P3", "status": "failed", "finding": "p3.not_identifiable", "singular": True,
                "hints": hints(problem, np.ones(d) / math.sqrt(d), names), "remedy": "contract"}
    m = measures(S, F.sigma_prior(problem))
    bad = m["lambda_min"] < P3_LAMBDA or max(m["ratio"]) > P3_RATIO
    res = {"gate": "P3", "status": "failed" if bad else "passed", **m, "thresholds": [P3_LAMBDA, P3_RATIO],
           "finding": "p3.not_identifiable" if bad else None, "remedy": "contract"}
    if bad:
        res["hints"] = hints(problem, m["direction"] if m["lambda_min"] < P3_LAMBDA else
                             [1.0 if r > P3_RATIO else 0.0 for r in m["ratio"]], names)
    return res


def profile_point(problem, fit: F.Fit, i: int, value: float, seed=None, n_start: int | None = None):
    """One profile scan point: theta_i fixed at `value`, the rest minimized with V fixed at the nominal fit's value
    (no iteration, section 7.3 "Scan points are not iterated"), started from the section 7.4 starts and from the
    representative of every basin with theta_i set to the scan value. Returns (converged, D)."""
    d = len(problem.layout.theta)
    starts = []
    for b in (fit.basins or [{"theta": fit.beta[:d].tolist()}]):
        x = fit.beta.copy()
        x[:d] = b["theta"]
        x[i] = value
        starts.append(x)
    if seed is not None:
        for s in F.sobol_starts(problem, n_start or F.n_starts(d), (F._seed_int(seed), i, int(1e6 * value) % 2**31)):
            x = fit.beta.copy()
            x[:d] = s
            x[i] = value
            starts.append(x)
    best, ok = math.inf, False
    for x in starts:
        m = F.minimize(problem, fit.ref, x, fixed={i: value})
        if m.converged and m.D < best:
            best, ok = m.D, True
    return ok, best


def profile_reach(problem, fit: F.Fit, i: int, seed=None, points: int = 8) -> dict:
    """Whether the profile rises by >= 4 within the prior range on both sides of theta-hat_i. Scan points that do
    not converge count as Delta < 4 (the direction in which G5 fails, section 7.3) and are recorded."""
    lo, hi = problem.prior_box()[i]
    x0 = float(fit.beta[i])
    out = {"theta": problem.layout.theta[i], "sides": {}, "nonconverged": []}
    for side, end in (("low", lo), ("high", hi)):
        reached = False
        for t in np.linspace(0, 1, points + 1)[1:]:
            v = x0 + t * (end - x0)
            ok, D = profile_point(problem, fit, i, v, seed)
            if not ok:
                out["nonconverged"].append(v)
                continue
            if D - fit.D >= G5_PROFILE:
                reached = True
                break
        out["sides"][side] = reached
    return out


def g5(problem, fit: F.Fit, seed=None, profile: bool = True) -> dict:
    """G5 at theta-hat (section 8.2): lambda_min >= 0.05, sigma_post/sigma_prior <= 0.5, profile Delta >= 4; fails
    also by section 7.4 admission. Remedy level contract, plan when the failure comes only from non-converged
    profile scan points (section 7.3, note 8)."""
    d = len(problem.layout.theta)
    names = problem.layout.theta
    flags = set(fit.flags)
    if "no-admitted-endpoint" in flags or "nonidentified-below" in flags:
        return {"gate": "G5", "status": "failed", "finding": "g5.not_identifiable", "remedy": "contract",
                "reason": "section 7.4 admission", "nonidentified": fit.nonidentified}
    S = None if fit.F is None else _sigma_theta(fit.F, d)
    if S is None:
        return {"gate": "G5", "status": "failed", "finding": "g5.not_identifiable", "singular": True,
                "hints": hints(problem, np.ones(d) / math.sqrt(d), names), "remedy": "contract"}
    m = measures(S, F.sigma_prior(problem))
    bad = m["lambda_min"] < G5_LAMBDA or max(m["ratio"]) > G5_RATIO
    prof, numerical = [], False
    if profile and not bad:
        for i in range(d):
            pr = profile_reach(problem, fit, i, seed)
            prof.append(pr)
            if not all(pr["sides"].values()):
                bad = True
                if pr["nonconverged"]:
                    numerical = True
    res = {"gate": "G5", "status": "failed" if bad else "passed", **m, "profile": prof,
           "thresholds": [G5_LAMBDA, G5_RATIO, G5_PROFILE], "finding": "g5.not_identifiable" if bad else None,
           "remedy": "plan" if (bad and numerical) else "contract"}
    if bad:
        res["hints"] = hints(problem, m["direction"], names)
    return res
