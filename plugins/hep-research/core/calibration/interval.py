"""Intervals (Part B section 7.5, with the section 7.3 rules for scans and interval toys; phase 2, WP3).
`calib_interval.py` is the CLI and the only owner of intervals and of the inference flags (section 15.3a).

- `profile_interval`: q(theta_i) = D_profile(theta_i) - D-hat <= chi2_1 quantile (1 for 68%, 3.84 for 95%), V fixed at
  the nominal fit's convergence (scan points are not iterated); scan points started from the section 7.4 starts and
  every basin; a scan point that does not converge stays inside the interval and is recorded.
- `total_halfwidth`: sqrt(sigma_q^2 + z^2 (sum_l Delta_l^2 + (Sigma_boot / w)_ii)) in the Gaussian case, Delta_l =
  max(|Delta+|, |Delta-|) (D52 (b), A8); for a toy-calibrated interval the half-width replaces sigma_q and no
  Sigma_boot / w term is added (D52, section 7.3 (a)).
- `toy_calibrated`: the explicit construction on a grid of scan points; at each point toys with the truth at the scan
  point and the nuisances at their profiled values there (constraint centres sampled around them), the frozen V-hat,
  their own replica-difference MC perturbation, each toy's own fit by section 7.4; a point is inside when
  p = (#{q_toy >= q_obs} + X + 1) / (n + 1) > alpha (non-converged toys count as q >= q_obs). All toys of one
  construction form one ensemble with one summed ratio test; on failure the interval is `incomplete` (section 7.3).
  With the physical bounds of theta respected in every fit, this is the Feldman-Cousins-style profile construction
  near a boundary; for a `multimodal` fit q is referred to the global theta-hat and the grid covers every basin, so
  the confidence set is the union over basins.
- `mcmc`: a separately declared Bayesian posterior (priors of theta and of every nuisance declared), random-walk
  Metropolis with split-R-hat and effective sample size; its output is a credible interval, labeled so, never a
  profile confidence interval (section 7.5, 15.3a).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats

from . import fit as F
from . import identify as I
from . import likelihood as L

LEVELS = {0.68: 1.0, 0.95: 3.841458820694124}


def z_of(level: float) -> float:
    return {0.68: 1.0, 0.95: 1.96}.get(level, float(stats.norm.ppf(0.5 + level / 2)))


def q_threshold(level: float) -> float:
    return LEVELS.get(level, float(stats.chi2.ppf(level, 1)))


def profile_interval(problem, fit: F.Fit, i: int, level: float = 0.68, seed=None, max_sigma: float = 6.0) -> dict:
    """The profile likelihood interval of theta_i at `level` (section 7.5)."""
    thr = q_threshold(level)
    x0 = float(fit.beta[i])
    s0 = float(fit.sigma_tot[i]) if np.isfinite(fit.sigma_tot[i]) else 1.0
    lo_b, hi_b = problem.bounds()[i]
    nonconv = []

    def q(v):
        ok, D = I.profile_point(problem, fit, i, v, seed)
        if not ok:
            nonconv.append(v)
            return -math.inf                      # stays inside (section 7.3)
        return D - fit.D - thr

    ends = []
    for sgn, bound in ((-1, lo_b), (1, hi_b)):
        prev, prev_q = x0, -thr
        end = None
        for k in np.arange(0.5, max_sigma + 1e-9, 0.5):
            v = x0 + sgn * k * s0
            hit_bound = (v <= lo_b) if sgn < 0 else (v >= hi_b)
            if hit_bound:
                v = bound
            qv = q(v)
            if qv >= 0:
                end = optimize.brentq(lambda t: max(q(t), -thr - 1.0), prev, v, xtol=1e-4 * s0) \
                    if prev_q < 0 and np.isfinite(qv) else v
                break
            prev, prev_q = v, qv
            if hit_bound:
                end = bound                       # the interval reaches the physical bound
                break
        ends.append(end if end is not None else x0 + sgn * max_sigma * s0)
    lo, hi = ends
    return {"theta": problem.layout.theta[i], "level": level, "lo": lo, "hi": hi, "center": x0,
            "half_width": 0.5 * (hi - lo), "method": "profile-likelihood", "nonconverged_scan_points": nonconv,
            "label": "confidence-interval"}


def total_halfwidth(sigma_q: float, level: float, shift_widening=None, Sigma_boot_ii: float = 0.0, w: float = 1.0,
                    toy_calibrated: bool = False) -> float:
    """The total half-width of section 7.5 in the Gaussian case. `shift_widening` = [max(|D+_l|, |D-_l|)] for the
    shift-mode phi (D52 (b)); toy-calibrated intervals get no Sigma_boot / w term (they already contain it)."""
    z = z_of(level)
    sw = float(np.sum(np.square(shift_widening))) if shift_widening is not None else 0.0
    sb = 0.0 if toy_calibrated else float(Sigma_boot_ii) / w
    return math.sqrt(sigma_q ** 2 + z * z * (sw + sb))


def region_box(intervals: dict) -> dict:
    """The G3 region: the box of the per-parameter total 68% intervals (D47 (a), A8)."""
    return {k: (None if v is None else [v["lo"], v["hi"]]) for k, v in intervals.items()}


def toy_calibrated(problem, fit: F.Fit, i: int, grid, n_toys: int, seed, level: float = 0.68,
                   make_toy=None, n_start: int | None = None) -> dict:
    """The toy-calibrated construction for theta_i on `grid` (section 7.5). `make_toy(truth_beta, rng)` returns
    (data, pert) for one toy at the truth (default: problem.simulate and problem.replica_pert). Each toy runs
    `find_extremum` for its own theta-hat and its own profile at the scan point, with V-hat frozen at the nominal
    fit's convergence (section 7.3 "Toy data and V-hat"); scan points of the toys are not iterated."""
    alpha = 1.0 - level
    d = len(problem.layout.theta)
    q_obs, X, n_all, inside, pvals = [], 0, 0, [], []
    for gi, v in enumerate(grid):
        ok, Dv = I.profile_point(problem, fit, i, float(v), seed)
        qo = (Dv - fit.D) if ok else -math.inf
        q_obs.append(qo)
        # truth at the scan point: nuisances at their profiled values there
        m = F.minimize(problem, fit.ref, _with(fit.beta, i, float(v)), fixed={i: float(v)})
        truth = m.beta
        qt, xg = [], 0
        for t in range(n_toys):
            rng = np.random.default_rng([F._seed_int(seed), i, gi, t])
            data, pert = (make_toy(truth, rng) if make_toy else (problem.simulate(truth, rng),
                                                                 problem.replica_pert(rng)))
            v_toy = _toy_view(problem, data, pert)
            ft = F.find_extremum(v_toy, (F._seed_int(seed), i, gi, t), truth, frozen=fit.ref, n_start=n_start)
            if not ft.converged:
                xg += 1
                continue
            okp, Dp = I.profile_point(v_toy, ft, i, float(v), None)
            if not okp:
                xg += 1
                continue
            qt.append(Dp - ft.D)
        X += xg
        n_all += n_toys
        p = 1.0 if not np.isfinite(qo) else F.testing_pvalue(qo, qt, xg)
        pvals.append(p)
        inside.append(p > alpha)
    kst = F.k_star(n_all, False)
    if X >= kst:
        return {"theta": problem.layout.theta[i], "level": level, "status": "incomplete",
                "finding": "interval.ratio_test", "X": X, "n": n_all, "k_star": kst}
    pts = [float(v) for v, ins in zip(grid, inside) if ins]
    res = {"theta": problem.layout.theta[i], "level": level, "status": "ok", "method": "toy-calibrated",
           "grid": [float(v) for v in grid], "p": pvals, "inside": inside, "X": X, "n": n_all,
           "label": "confidence-interval", "union": _segments(grid, inside)}
    if pts:
        res.update(lo=min(pts), hi=max(pts), half_width=0.5 * (max(pts) - min(pts)))
    return res


def _segments(grid, inside):
    segs, cur = [], None
    for v, ins in zip(grid, inside):
        if ins and cur is None:
            cur = [float(v), float(v)]
        elif ins:
            cur[1] = float(v)
        elif cur is not None:
            segs.append(cur)
            cur = None
    if cur is not None:
        segs.append(cur)
    return segs


def _with(beta, i, v):
    b = beta.copy()
    b[i] = v
    return b


def _toy_view(problem, data, pert):
    return F.view(problem, data=data, h=lambda tp, _p=pert: problem.h(tp) + _p)


def mcmc(log_post, x0: np.ndarray, scale: np.ndarray, n: int, seed, chains: int = 4, priors_declared=None) -> dict:
    """Random-walk Metropolis for a separately declared Bayesian posterior (section 7.5). `priors_declared` lists
    the priors of theta and of every nuisance; without them the request is refused. Output: credible intervals with
    split-R-hat and bulk ESS; never labeled a confidence interval."""
    if not priors_declared:
        raise F.FitError("interval.mcmc_priors", "MCMC needs the priors of theta and of all nuisances declared "
                         "(section 7.5)")
    rng = np.random.default_rng(F._seed_int(seed))
    d = x0.size
    draws = []
    for c in range(chains):
        x = x0 + scale * rng.normal(size=d)
        lp = log_post(x)
        ch = []
        for _ in range(n):
            y = x + scale * rng.normal(size=d)
            ly = log_post(y)
            if math.log(rng.uniform()) < ly - lp:
                x, lp = y, ly
            ch.append(x.copy())
        draws.append(np.array(ch[n // 2:]))
    D = np.stack(draws)                                  # chains x m x d
    rhat, ess = split_rhat(D), bulk_ess(D)
    flat = D.reshape(-1, d)
    q = np.quantile(flat, [0.16, 0.84, 0.025, 0.975], axis=0)
    return {"label": "credible-interval", "method": "mcmc", "rhat": rhat.tolist(), "ess": ess.tolist(),
            "c68": q[:2].T.tolist(), "c95": q[2:].T.tolist(), "priors": priors_declared,
            "flags": ["bayesian"], "frequentist_coverage_claim": False}


def split_rhat(D: np.ndarray) -> np.ndarray:
    c, m, d = D.shape
    h = m // 2
    S = np.concatenate([D[:, :h], D[:, h:2 * h]], axis=0)
    n = S.shape[1]
    W = S.var(axis=1, ddof=1).mean(0)
    B = n * S.mean(axis=1).var(axis=0, ddof=1)
    var = (n - 1) / n * W + B / n
    return np.sqrt(var / W)


def bulk_ess(D: np.ndarray) -> np.ndarray:
    c, m, d = D.shape
    out = []
    for j in range(d):
        x = D[:, :, j] - D[:, :, j].mean()
        acf = np.mean([np.correlate(xc, xc, "full")[m - 1:] / (np.var(xc) * m + 1e-300) for xc in x], axis=0)
        s = 0.0
        for k in range(1, m - 1, 2):
            pair = acf[k] + acf[k + 1]
            if pair < 0:
                break
            s += pair
        out.append(c * m / (1 + 2 * s))
    return np.asarray(out)


def inference_flags(result: dict) -> list:
    """The inference flags of section 15.3a: an MCMC output is a credible interval and cannot carry a frequentist
    coverage claim; a non-Gaussian export does not claim equivalence with the joint fit."""
    flags = []
    if result.get("method") == "mcmc":
        flags.append("credible-interval")
        if result.get("frequentist_coverage_claim"):
            raise F.FitError("interval.label", "a credible interval cannot pass a frequentist coverage claim")
    if result.get("non_gaussian"):
        flags.append("non-gaussian-export")
    return flags
