"""The inference engine of Part B section 7 (phase 2, WP2): minimization, the section 7.3 reference-point iteration,
the section 7.4 multi-start and basins, non-convergence classes and the ratio test, and the fit gates G1, G2, G6, G7
(with locally linear toys and the linearity check, section 8.5). `calib_fit.py` is its CLI; the ensembles of
`calib_closure.py`, `calib_design.py`, `calib_interval.py` and `calib_validate.py` call `run_estimation_ensemble`,
`testing_pvalue`, `k_star` and `w_factor` here (section 14: one implementation).

A `Problem` supplies the model:

- `layout`, `data` (`likelihood.Data`), `theta` names with `bounds` (physical) and `prior` (sampling range or
  sigma, for admission and Sobol starts), `phi_P` names;
- `h(tp: np.ndarray) -> np.ndarray`, the link-space model predictor h(theta, phi_P) of `likelihood.Likelihood`
  (the evaluator's prediction with common random numbers), and optionally `H(tp)` its Jacobian (central
  differences otherwise);
- `reference(tp, beta, frozen=None) -> likelihood.Reference`: the model-produced errors at the reference point;
  `frozen` is a V-hat to keep (section 7.3 "Toy data and V-hat"); otherwise the bootstrap is regenerated with
  common random numbers;
- `sigma_noise` (default 0) and `edm_tol` (the plan's minimizer tolerance, D79).

Covariances: D = -2 ln L; F is the expected Hessian of D; Sigma_beta = 2 F^-1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import linalg, stats
from scipy.stats import qmc

from . import likelihood as L

ITER_LIMIT = 30                 # section 7.3
CONV_FRACTION = 0.1             # change of theta-hat < 0.1 sigma_tot (max-norm, D51)
LNDET_FRACTION = 0.2            # ln det diagnostic < 0.2 sigma_tot (D51)
EPS_MAX = 0.01                  # section 7.3
RATIO_LEVEL = 1e-3              # P(X >= k*) < 1e-3 at eps = eps_max
R_ADMIT = 1.0                   # section 7.4
SEGMENT_POINTS = 19


class FitError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ ensembles (section 7.3)
def k_star(n_req: int, replacement: bool = True, eps: float = EPS_MAX, level: float = RATIO_LEVEL) -> int:
    """The smallest k with P(X >= k) < level at eps = eps_max: X ~ NegBin(n_req, 1 - eps) (non-converged members
    before the n_req-th converged one) with replacement, X ~ Bin(n_req, eps) without (section 7.3)."""
    if n_req <= 0:
        raise FitError("fit.ensemble", "n_req must be positive")
    dist = stats.nbinom(n_req, 1.0 - eps) if replacement else stats.binom(n_req, eps)
    k = 0
    while dist.sf(k - 1) >= level:          # sf(k-1) = P(X >= k)
        k += 1
    return k


def w_factor(eps_hat: float) -> float:
    """w(eps) = F_3(chi2_{1, 1-eps}) / (1 - eps): the worst-case variance factor of replacement (section 7.3); 1 at 0."""
    if eps_hat <= 0:
        return 1.0
    return float(stats.chi2.cdf(stats.chi2.ppf(1.0 - eps_hat, 1), 3) / (1.0 - eps_hat))


def eps_hat(X: int, n: int, plus: bool = False) -> float:
    """eps-hat = X / (n + X), or the add-one eps-hat+ = (X + 1) / (n + X + 1) of Sigma_boot (section 7.3)."""
    return (X + 1.0) / (n + X + 1.0) if plus else (X / (n + X) if n + X else 0.0)


def eps_max_cv(F: int) -> float:
    """eps_max,cv = min(1 - (1 - eps_max)^F, 2%) for cross-validation toys whose members are toys of F folds."""
    return min(1.0 - (1.0 - EPS_MAX) ** F, 0.02)


def testing_pvalue(T_obs: float, T_toys, X: int) -> float:
    """(#{T_toy >= T_obs} + X + 1) / (n + 1), n the total number of toys, converged and not (D49): non-converged
    toys count as statistic >= observed (section 7.3, ensembles for testing)."""
    T = np.asarray(T_toys, float)
    n = T.size + X
    return float((np.sum(T >= T_obs) + X + 1.0) / (n + 1.0))


def fullfit_gof_pvalue(T_obs: float, T_toys, X: int) -> float:
    """G6/G2 with full toys (D46, A8): non-converged full toys count as T_toy < T_obs, the direction unfavourable to
    passing a goodness-of-fit gate: (#{T_toy >= T_obs} + 1) / (n + 1) with n including them."""
    T = np.asarray(T_toys, float)
    n = T.size + X
    return float((np.sum(T >= T_obs) + 1.0) / (n + 1.0))


@dataclass
class EnsembleResult:
    values: list
    X: int
    n_completed: int
    k_star: int
    ratio_failed: bool
    nonconverged: list = field(default_factory=list)
    seeds_used: list = field(default_factory=list)


def run_estimation_ensemble(member, n_req: int, seeds, eps_max: float = EPS_MAX, carried_X: int = 0,
                            carried_converged: int = 0) -> EnsembleResult:
    """An ensemble for estimation and decision (G7, G8, Sigma_boot, C-hat_r): replace a non-converged member with the
    next unused seed until n_req converged, stopping when the summed X reaches k* (section 7.3). `member(seed)` returns
    (converged: bool, value, record). A redo continues the ensemble: the summed X and the converged members of the
    earlier attempts replace n_req in k* (section 7.3, "A redo is treated as a continuation")."""
    kst = k_star(max(n_req + carried_converged, 1), True, eps_max)
    values, bad, used = [], [], []
    X = carried_X
    it = iter(seeds)
    while len(values) < n_req:
        if X >= kst:
            return EnsembleResult(values, X, len(values) + len(bad), kst, True, bad, used)
        try:
            s = next(it)
        except StopIteration:
            raise FitError("fit.seeds", "the seed block is exhausted before the ensemble completed") from None
        used.append(s)
        ok, val, rec = member(s)
        if ok:
            values.append(val)
        else:
            X += 1
            bad.append({"seed": s, **(rec or {})})
    return EnsembleResult(values, X, len(values) + len(bad), kst, X >= kst, bad, used)


def run_testing_ensemble(member, n: int, seeds, eps_max: float = EPS_MAX, carried_X: int = 0,
                         carried_n: int = 0) -> EnsembleResult:
    """An ensemble for testing (reference distributions, power toys): no replacement, every one of the n toys run;
    the ratio test on X summed over attempts with Bin(attempts x n) (section 7.3)."""
    kst = k_star(n + carried_n, False, eps_max)
    values, bad, used = [], [], []
    it = iter(seeds)
    for _ in range(n):
        try:
            s = next(it)
        except StopIteration:
            raise FitError("fit.seeds", "the seed block is exhausted before the testing ensemble completed") from None
        used.append(s)
        ok, val, rec = member(s)
        (values.append(val) if ok else bad.append({"seed": s, **(rec or {})}))
    X = carried_X + len(bad)
    return EnsembleResult(values, X, n, kst, X >= kst, bad, used)


# ------------------------------------------------------------------ minimization
@dataclass
class Minimum:
    beta: np.ndarray
    D: float
    g: np.ndarray
    F: np.ndarray
    edm: float
    converged: bool
    steps: int
    active: list
    calls: int
    reason: str = ""


def _tp_index(lk):
    return np.r_[lk.layout_slices["theta"].start:lk.layout_slices["phi_P"].stop]


def jacobian(problem, tp, steps):
    if hasattr(problem, "H"):
        return problem.H(tp)
    cols = []
    for i, s in enumerate(steps):
        a, b = tp.copy(), tp.copy()
        a[i] += s
        b[i] -= s
        cols.append((problem.h(a) - problem.h(b)) / (2 * s))
    return np.stack(cols, axis=1) if cols else np.zeros((problem.layout.n_link, 0))


def fd_steps(problem):
    st = getattr(problem, "fd_steps", None)
    if st is not None:
        return np.asarray(st, float)
    out = []
    for lo, hi in problem.prior_box():
        out.append(1e-4 * (hi - lo))
    return np.asarray(out + [1e-3] * len(problem.layout.phi_P), float)


def minimize(problem, ref: L.Reference, beta0: np.ndarray, max_steps: int = 200, hfun=None, Hfun=None,
             fixed: dict | None = None) -> Minimum:
    """Fisher scoring with Levenberg damping and backtracking, an active set at the physical bounds of theta and the
    positivity of omega and gamma; converged when EDM = 1/2 g^T F^-1 g over the free directions passes the G1
    criterion (section 8.2, D79) with a positive-definite curvature. `fixed` = {beta index: value} holds components
    (profile scan points, segment points, restricted fits)."""
    lk = L.Likelihood(problem.layout, problem.observed, ref)
    tpi = _tp_index(lk)
    hfun = hfun or problem.h
    steps = fd_steps(problem)
    lo, hi = _beta_bounds(problem, lk)
    b = np.clip(np.asarray(beta0, float).copy(), lo, hi)
    fixed = dict(fixed or {})
    for i, v in fixed.items():
        b[i] = v
    calls = 0
    edm_g1 = edm_threshold(problem)                      # the G1 criterion (with 0.1 sigma_noise)
    edm_tol = 0.002 * float(getattr(problem, "edm_tol", 0.1))   # pursued first: a noisy objective must not stop the
    lam = 1e-3                                           # minimizer early; G1's threshold accepts a stall
    D = None
    for it in range(max_steps):
        tp = b[tpi]
        h = hfun(tp)
        calls += 1
        if Hfun is not None:
            link_jacobian = Hfun(tp)
        elif hfun is problem.h:
            link_jacobian = jacobian(problem, tp, steps)
            calls += 2 * tp.size
        else:
            link_jacobian = _fd(hfun, tp, steps)
        D = lk.deviance(b, h)
        g, F = lk.score_fisher(b, h, link_jacobian)
        free = np.ones(b.size, bool)
        for i in fixed:
            free[i] = False
        at_lo = (b <= lo + 1e-12) & (g > 0)
        at_hi = (b >= hi - 1e-12) & (g < 0)
        free &= ~(at_lo | at_hi)
        fi = np.flatnonzero(free)
        if fi.size == 0:                              # every component fixed or at an active bound
            return Minimum(b, D, g, F, 0.0, True, it, list(np.flatnonzero(~free)), calls, "")
        Ff, gf = F[np.ix_(fi, fi)], g[fi]
        try:
            sol = linalg.solve(Ff, gf, assume_a="pos")
            edm = 0.5 * float(gf @ sol)
        except (linalg.LinAlgError, ValueError):
            edm = math.inf
        if not np.isfinite(D):
            return Minimum(b, D, g, F, math.inf, False, it, [], calls, "non-finite objective")
        if edm < edm_tol:
            pd = _pd(Ff)
            return Minimum(b, D, g, F, edm, pd, it, list(np.flatnonzero(~free)), calls,
                           "" if pd else "curvature not positive definite")
        # damped step on the free components, backtracking on D
        improved = False
        for _ in range(30):
            M = Ff + lam * np.diag(np.maximum(np.diag(Ff), 1e-12))
            try:
                dstep = -linalg.solve(M, gf, assume_a="pos")
            except (linalg.LinAlgError, ValueError):
                lam *= 10
                continue
            nb = b.copy()
            nb[fi] += dstep
            nb = np.clip(nb, lo, hi)
            for i, v in fixed.items():
                nb[i] = v
            hn = hfun(nb[tpi])
            calls += 1
            Dn = lk.deviance(nb, hn)
            if np.isfinite(Dn) and Dn <= D + 1e-12 * max(1.0, abs(D)):
                b = nb
                lam = max(lam / 10, 1e-9)
                improved = True
                break
            lam *= 10
        if not improved:
            pd = _pd(Ff)
            ok = edm < edm_g1 and pd                                  # the G1 criterion exactly (section 7.4)
            return Minimum(b, D, g, F, edm, ok, it, list(np.flatnonzero(~free)), calls,
                           "" if ok else "no descent step")
    pd = _pd(Ff) if fi.size else True
    ok = edm < edm_g1 and pd
    return Minimum(b, D, g, F, edm, ok, max_steps, [], calls, "" if ok else "step limit")


def _fd(hfun, tp, steps):
    cols = []
    for i, s in enumerate(steps):
        a, b = tp.copy(), tp.copy()
        a[i] += s
        b[i] -= s
        cols.append((hfun(a) - hfun(b)) / (2 * s))
    return np.stack(cols, axis=1)


def _pd(F):
    try:
        return bool(np.linalg.eigvalsh(0.5 * (F + F.T)).min() > 0)
    except np.linalg.LinAlgError:
        return False


def _beta_bounds(problem, lk):
    lo = lk.bounds()
    hi = np.full(lo.size, np.inf)
    for i, (a, b) in enumerate(problem.bounds()):
        lo[lk.layout_slices["theta"].start + i] = a
        hi[lk.layout_slices["theta"].start + i] = b
    return lo, hi


def edm_threshold(problem) -> float:
    """G1: EDM < max(0.002 tol UP, 0.1 sigma_noise), tol the plan's minimizer tolerance (D79), UP = 1 for -2 ln L."""
    tol = float(getattr(problem, "edm_tol", 0.1))
    return max(0.002 * tol, 0.1 * float(getattr(problem, "sigma_noise", 0.0)))


def covariance(F: np.ndarray) -> np.ndarray:
    S = 2.0 * linalg.inv(F)
    return 0.5 * (S + S.T)


# ------------------------------------------------------------------ section 7.3
@dataclass
class Fit:
    beta: np.ndarray
    theta: dict
    cov_beta: np.ndarray
    sigma_tot: np.ndarray
    D: float
    edm: float
    converged: bool
    iterations: int
    reason: str
    ref: L.Reference
    lndet_shift: float = 0.0
    history: list = field(default_factory=list)
    calls: int = 0
    active: list = field(default_factory=list)
    F: np.ndarray | None = None
    flags: list = field(default_factory=list)
    basins: list = field(default_factory=list)
    nonidentified: list = field(default_factory=list)
    endpoints: list = field(default_factory=list)

    def record(self):
        return {"theta": {k: float(v) for k, v in self.theta.items()}, "sigma_tot": self.sigma_tot.tolist(),
                "D": self.D, "edm": self.edm, "converged": self.converged, "iterations": self.iterations,
                "reason": self.reason, "lndet_shift": self.lndet_shift, "flags": list(self.flags),
                "basins": self.basins, "nonidentified": self.nonidentified}


def sigma_tot(cov_beta, d, boot_cov=None, w=1.0):
    """sqrt(Sigma_theta + Sigma_boot / w)_ii (section 8.1)."""
    v = np.diag(cov_beta)[:d].copy()
    if boot_cov is not None:
        v = v + np.diag(np.asarray(boot_cov, float))[:d] / w
    return np.sqrt(v)


def iterate(problem, beta0: np.ndarray, frozen=None, boot_cov=None, w_boot: float = 1.0,
            limit: int = ITER_LIMIT, lndet: bool = True) -> Fit:
    """The section 7.3 iteration: reference quantities at the current fit point, minimize with V and u fixed,
    theta_ref <- theta-hat, until max_i |delta theta_i| / sigma_tot,i < 0.1 (sigma_tot from the curvature of the
    current fit, D51) within `limit` iterations; then the ln det diagnostic, max_i |theta_lndet,i - theta_i| /
    sigma_tot,i < 0.2. `frozen` is the V-hat of the fit a toy imitates (it is then not regenerated)."""
    lay = problem.layout
    d = len(lay.theta)
    b = np.asarray(beta0, float).copy()
    probe = L.Likelihood(lay, problem.observed, problem.reference(b[_tp_index_layout(lay)], b, frozen))
    tpi = _tp_index(probe)
    ref = probe.ref
    hist, calls, prev = [], 0, None
    m = None
    for it in range(1, limit + 1):
        m = minimize(problem, ref, b)
        calls += m.calls
        if not m.converged:
            return Fit(m.beta, _theta(problem, m.beta), _safe_cov(m.F), np.full(d, np.nan), m.D, m.edm, False, it,
                       f"minimization: {m.reason}", ref, history=hist, calls=calls, F=m.F)
        S = covariance(m.F)
        st = sigma_tot(S, d, boot_cov, w_boot)
        b = m.beta
        hist.append({"theta": b[:d].tolist(), "D": m.D})
        if prev is not None and np.max(np.abs(b[:d] - prev) / st) < CONV_FRACTION:
            fit = Fit(b, _theta(problem, b), S, st, m.D, m.edm, True, it, "", ref, history=hist, calls=calls,
                      active=m.active, F=m.F)
            if lndet:
                shift, c2 = lndet_diagnostic(problem, fit, frozen)
                fit.lndet_shift = shift
                fit.calls += c2
                if not shift < LNDET_FRACTION:
                    fit.converged = False
                    fit.reason = f"ln det diagnostic {shift:.3g} >= 0.2 sigma_tot"
            return fit
        prev = b[:d].copy()
        try:
            ref = problem.reference(b[tpi], b, frozen)
        except (ValueError, linalg.LinAlgError, FloatingPointError, ZeroDivisionError) as exc:
            # the reference quantities at the new theta_ref cannot be computed: not converged (D50 reading, A8)
            return Fit(b, _theta(problem, b), S, st, m.D, m.edm, False, it,
                       f"reference quantities not computable at theta_ref: {type(exc).__name__}", ref, history=hist,
                       calls=calls, F=m.F)
    return Fit(b, _theta(problem, b), covariance(m.F), sigma_tot(covariance(m.F), d, boot_cov, w_boot), m.D,
               m.edm, False, limit, f"no convergence within {limit} iterations", ref, history=hist, calls=calls,
               F=m.F)


def _tp_index_layout(lay):
    n = len(lay.theta) + len(lay.phi_P)
    return np.arange(n)


def _safe_cov(F):
    try:
        return covariance(F)
    except (linalg.LinAlgError, ValueError):
        return np.full(F.shape, np.nan)


def _theta(problem, b):
    return dict(zip(problem.layout.theta, b[:len(problem.layout.theta)].tolist()))


def lndet_diagnostic(problem, fit: Fit, frozen=None, rounds: int = 30) -> tuple[float, int]:
    """Minimize the full Gaussian -2 ln L including ln det V_G(theta), the bootstrap part frozen at theta_ref (section
    7.3): damped Newton steps on the full objective, with gradient = the score at V_G(beta) plus the central-difference
    gradient of the V-dependence [r^T W(theta) r + ln det V_G(theta)] at fixed residuals, and the Fisher curvature.
    Returns max_i |theta_full,i - theta_i| / sigma_tot,i and the number of evaluations."""
    if not problem.layout.gaussian_rows().size or not getattr(problem, "V_depends_on_theta", True):
        return 0.0, 0
    d = len(problem.layout.theta)
    lk0 = L.Likelihood(problem.layout, problem.observed, fit.ref)
    tpi = _tp_index(lk0)
    vhat = fit.ref if frozen is None else frozen
    lo, hi = _beta_bounds(problem, lk0)
    steps = fd_steps(problem)
    calls = 0

    def ref_at(bb):
        return problem.reference(bb[tpi], bb, vhat, bootstrap_frozen=True)

    def full(bb, r=None):
        """The full objective; a trial point where the reference quantities or the prediction cannot be computed
        (e.g. a width that is not finite) is rejected like a worse point, never an exception."""
        try:
            r = r or ref_at(bb)
            v = L.Likelihood(problem.layout, problem.observed, r).deviance(bb, problem.h(bb[tpi])) + r.ln_det
        except (ValueError, linalg.LinAlgError, FloatingPointError, ZeroDivisionError):
            return math.inf
        return v if np.isfinite(v) else math.inf

    b = fit.beta.copy()
    fb = full(b)
    for _ in range(rounds):
        r = ref_at(b)
        lk = L.Likelihood(problem.layout, problem.observed, r)
        h = problem.h(b[tpi])
        g, F = lk.score_fisher(b, h, jacobian(problem, b[tpi], steps))
        calls += 2 + 2 * tpi.size
        for j, i in enumerate(tpi):
            a, c = b.copy(), b.copy()
            a[i] += steps[j]
            c[i] -= steps[j]
            fa = full(a) - lk.deviance(a, problem.h(a[tpi]))
            fc = full(c) - lk.deviance(c, problem.h(c[tpi]))
            g[i] += (fa - fc) / (2 * steps[j])
            calls += 4
        if not np.all(np.isfinite(g)):                 # the V-dependence cannot be differenced here: stop
            break
        try:
            step = -linalg.solve(F, g, assume_a="pos")
        except (linalg.LinAlgError, ValueError):
            break
        t_ = 1.0
        while t_ > 1e-4:
            nb = np.clip(b + t_ * step, lo, hi)
            fn = full(nb)
            calls += 1
            if fn <= fb:
                break
            t_ *= 0.5
        else:
            break
        moved = np.max(np.abs(nb[:d] - b[:d]) / fit.sigma_tot)
        b, fb = nb, fn
        if moved < 1e-5:
            break
    return float(np.max(np.abs(b[:d] - fit.beta[:d]) / fit.sigma_tot)), calls


def fixed_deviance(problem, ref, beta, h):
    return L.Likelihood(problem.layout, problem.observed, ref).deviance(beta, h)


# ------------------------------------------------------------------ section 7.4
def sobol_starts(problem, n: int, seed) -> np.ndarray:
    box = np.array(problem.prior_box(), float)
    s = qmc.Sobol(d=len(box), scramble=True, seed=_seed_int(seed))
    u = s.random(n)
    return box[:, 0] + u * (box[:, 1] - box[:, 0])


def _seed_int(seed):
    if isinstance(seed, (tuple, list)):
        return int(np.random.SeedSequence(list(seed)).generate_state(1)[0])
    return int(seed)


def n_starts(d: int) -> int:
    return max(2 * d, 16)


def sigma_prior(problem) -> np.ndarray:
    """sigma_prior,i: range / sqrt(12) for a bounded uniform prior (D54) or the declared sigma."""
    return np.asarray(problem.sigma_prior(), float)


def separated(problem, ref, a: np.ndarray, b: np.ndarray, tau_bar: float) -> bool:
    """-2 ln L along the straight theta segment between two endpoints, at 19 interior points with V fixed at the
    representative's value and the nuisances profiled at each point, exceeds the larger endpoint value by more than
    tau_bar (section 7.4)."""
    lk = L.Likelihood(problem.layout, problem.observed, ref)
    d = len(problem.layout.theta)
    Da = lk.deviance(a, problem.h(a[_tp_index(lk)]))
    Db = lk.deviance(b, problem.h(b[_tp_index(lk)]))
    top = max(Da, Db)
    for t in np.linspace(0, 1, SEGMENT_POINTS + 2)[1:-1]:
        x = (1 - t) * a + t * b
        if lk.layout.n_beta > d:
            m = minimize(problem, ref, x, fixed={i: x[i] for i in range(d)}, max_steps=50)
            Dx = m.D
        else:
            Dx = lk.deviance(x, problem.h(x[_tp_index(lk)]))
        if Dx > top + tau_bar:
            return True
    return False


def find_extremum(problem, seed, beta_nominal: np.ndarray, frozen=None, boot_cov=None, w_boot: float = 1.0,
                  limit: int = ITER_LIMIT, n_start: int | None = None, extra_starts=None, fixed=None) -> Fit:
    """Section 7.4: max(2d, 16) scrambled-Sobol starts (seed from the fit's seed block), converged endpoints,
    admission sigma_tot,i <= R_admit sigma_prior,i, basins by the segment barrier tau_bar = max(0.1, 4 sigma_noise),
    the section 7.3 iteration from each representative, comparison with the full Gaussian likelihood including
    ln det V_G, theta-hat the lowest basin with ties within tau_tie = max(0.01, 4 sigma_noise) broken in
    lexicographic order of theta; `multimodal` when two or more basins are admitted."""
    lay = problem.layout
    d = len(lay.theta)
    sn = float(getattr(problem, "sigma_noise", 0.0))
    tau_bar, tau_tie = max(0.1, 4 * sn), max(0.01, 4 * sn)
    starts = sobol_starts(problem, n_start or n_starts(d), seed)
    if extra_starts is not None:
        starts = np.vstack([starts, np.atleast_2d(extra_starts)])
    ref0 = problem.reference(beta_nominal[_tp_index_layout(lay)], beta_nominal, frozen)
    sp = sigma_prior(problem)
    endpoints, nonconv = [], []
    calls = 0
    for s in starts:
        b0 = beta_nominal.copy()
        b0[:d] = s
        m = minimize(problem, ref0, b0, fixed=fixed)
        calls += m.calls
        if not m.converged:
            nonconv.append({"start": s.tolist(), "reason": m.reason})
            continue
        st = sigma_tot(covariance(m.F), d, boot_cov, w_boot)
        endpoints.append({"beta": m.beta, "D": m.D, "sigma_tot": st, "admitted": bool(np.all(st <= R_ADMIT * sp))})
    if not endpoints:                                   # D45 (A8): one further multi-start round before giving up
        for s in sobol_starts(problem, n_start or n_starts(d), (_seed_int(seed), 45)):
            b0 = beta_nominal.copy()
            b0[:d] = s
            m = minimize(problem, ref0, b0, fixed=fixed)
            calls += m.calls
            if not m.converged:
                nonconv.append({"start": s.tolist(), "reason": m.reason, "round": 2})
                continue
            st = sigma_tot(covariance(m.F), d, boot_cov, w_boot)
            endpoints.append({"beta": m.beta, "D": m.D, "sigma_tot": st,
                              "admitted": bool(np.all(st <= R_ADMIT * sp))})
    if not endpoints:
        return Fit(beta_nominal, _theta(problem, beta_nominal), np.full((lay.n_beta,) * 2, np.nan),
                   np.full(d, np.nan), math.inf, math.inf, False, 0, "no converged endpoint (section 7.4, D45)",
                   ref0, calls=calls, endpoints=nonconv)
    endpoints.sort(key=lambda e: e["D"])
    admitted = [e for e in endpoints if e["admitted"]]
    nonid = [{"theta": e["beta"][:d].tolist(), "D": e["D"],
              "sigma_ratio": (e["sigma_tot"] / sp).tolist()} for e in endpoints if not e["admitted"]]
    if not admitted:
        e = endpoints[0]
        fit = iterate(problem, e["beta"], frozen, boot_cov, w_boot, limit)
        fit.flags.append("no-admitted-endpoint")
        fit.nonidentified = nonid
        fit.calls += calls
        return fit
    reps = []
    for e in admitted:                                  # the segment with V fixed at the representative (section 7.4)
        if not any(not separated(problem, r["ref"], r["beta"], e["beta"], tau_bar) for r in reps):
            e["ref"] = problem.reference(e["beta"][_tp_index_layout(lay)], e["beta"], frozen)
            reps.append(e)
    fits = []
    for r in reps:
        f = iterate(problem, r["beta"], frozen, boot_cov, w_boot, limit)
        calls += f.calls
        f.full = f.D + f.ref.ln_det if f.converged else math.inf
        fits.append(f)
    merged = []
    for f in sorted(fits, key=lambda f: f.full):
        if not f.converged:
            merged.append(f)
            continue
        if any(g.converged and not separated(problem, g.ref, g.beta, f.beta, tau_bar) for g in merged):
            continue
        merged.append(f)
    conv = [f for f in merged if f.converged]
    if not conv:
        f = merged[0]
        f.calls = calls
        f.reason = f.reason or "no basin converged"
        return f
    best = min(f.full for f in conv)
    tied = [f for f in conv if f.full - best <= tau_tie]
    tied.sort(key=lambda f: tuple(f.beta[:d]))
    th = tied[0]
    th.basins = [{"theta": f.beta[:d].tolist(), "delta_m2lnL": float(f.full - th.full),
                  "sigma_tot": f.sigma_tot.tolist(), "converged": f.converged, "edm": f.edm} for f in merged]
    th.nonidentified = nonid
    th.endpoints = nonconv
    if len(merged) >= 2:
        th.flags.append("multimodal")
    if len(tied) >= 2:
        th.flags.append("tie")
    if any(e["D"] < min(a["D"] for a in admitted) - tau_tie for e in endpoints if not e["admitted"]):
        th.flags.append("nonidentified-below")              # G5 fails (contract), section 7.4
    if any(not f.converged for f in merged):
        th.converged = False
        th.reason = "a basin did not converge (G1 is decided per basin)"
    th.calls = calls
    return th


# ------------------------------------------------------------------ G1
def g1(fit: Fit, problem) -> dict:
    """G1: each basin converged with EDM below max(0.002 tol UP, 0.1 sigma_noise) (section 8.2); non-convergence of the
    actual fit is a G1 failure (section 7.3 Class 1)."""
    thr = edm_threshold(problem)
    per = [{"theta": b["theta"], "edm": b.get("edm", fit.edm), "converged": b["converged"]} for b in fit.basins] or \
        [{"theta": list(fit.theta.values()), "edm": fit.edm, "converged": fit.converged}]
    ok = fit.converged and all(p["converged"] and p["edm"] < thr for p in per)
    return {"gate": "G1", "status": "passed" if ok else "failed", "edm_threshold": thr, "basins": per,
            "finding": None if ok else "g1.not_converged", "reason": fit.reason, "remedy": "plan"}


# ------------------------------------------------------------------ Sigma_MC (section 6.7) and G7
def sigma_mc(problem, fit: Fit, V_MC_link: np.ndarray | None = None) -> np.ndarray:
    """The MC part of the theta covariance: A V_MC A^T for the Gaussian rows (A = Sigma_beta J^T W) plus the
    sandwiches of the auxiliary measurements (BB-lite counts, auxiliary binomial) (section 6.7: B_m)."""
    lay = problem.layout
    d = len(lay.theta)
    lk = L.Likelihood(lay, problem.observed, fit.ref)
    Finv = linalg.inv(fit.F)
    S = np.zeros((lay.n_beta, lay.n_beta))
    rows = lay.gaussian_rows()
    if rows.size and V_MC_link is not None:
        tp = fit.beta[_tp_index(lk)]
        link_jacobian = jacobian(problem, tp, fd_steps(problem))
        Jz = np.zeros((lay.n_link, lay.n_beta))
        Jz[:, _tp_index(lk)] = link_jacobian
        if lay.n_nu:
            Jz[:, lk.layout_slices["nu"]] = fit.ref.U
        if lay.n_eta:
            Jz[:, lk.layout_slices["eta"]] = fit.ref.S
        A = 2.0 * Finv @ Jz[rows].T @ fit.ref.W
        S += A @ V_MC_link @ A.T
    p = lk.unpack(fit.beta)
    for i, (bn, k) in enumerate(lay.gamma):
        tau = float(np.asarray(fit.ref.tau[bn])[k])
        if tau <= 0:
            continue
        j = lk.layout_slices["gamma"].start + i
        gk = p["gamma"][i]
        e = Finv[:, j] * (2.0 / gk)
        S += np.outer(e, e) * tau * gk
    for i, bn in enumerate(lay.delta):
        n_eff, k_eff = fit.ref.n_eff[bn]
        j = lk.layout_slices["delta"].start + i
        c = math.log(k_eff / (n_eff - k_eff))
        em = 1.0 / (1.0 + math.exp(-(c + p["delta"][i])))
        e = Finv[:, j] * 2.0
        S += np.outer(e, e) * n_eff * em * (1 - em)
    return 0.5 * (S + S.T)[:d, :d]


def g7(theta_hats: np.ndarray, mc_cov: np.ndarray, rel_tol: float = 1e-8, null_tol: float | None = None,
       sigma_tot_ref: np.ndarray | None = None, alpha: float = 0.01) -> dict:
    """G7 (section 8.2 note 7): T = sum_i (theta_i - theta_bar)^T Sigma_MC^+ (theta_i - theta_bar) < chi2_{r(K-1),
    1-alpha}, r = rank Sigma_MC with the pre-locked tolerance rel_tol; any spread in the null space of Sigma_MC beyond
    null_tol (default 1e-6 sigma_tot) fails directly; r = 0 checks zero spread only (no p-value)."""
    X = np.asarray(theta_hats, float)
    K, d = X.shape
    dev = X - X.mean(0)
    w, U = np.linalg.eigh(0.5 * (mc_cov + mc_cov.T))
    keep = w > rel_tol * max(w.max(), 0.0) if w.max() > 0 else np.zeros_like(w, bool)
    r = int(keep.sum())
    nt = null_tol if null_tol is not None else (1e-6 * float(np.max(sigma_tot_ref)) if sigma_tot_ref is not None
                                                else 1e-9)
    null = U[:, ~keep]
    spread = float(np.abs(dev @ null).max()) if null.size else 0.0
    if spread > nt:
        return {"gate": "G7", "status": "failed", "finding": "g7.null_space_spread", "rank": r, "spread": spread,
                "remedy": "plan"}
    if r == 0:
        return {"gate": "G7", "status": "passed", "rank": 0, "T": None, "spread": spread}
    Ur = U[:, keep] / np.sqrt(w[keep])
    T = float(np.sum((dev @ Ur) ** 2))
    df = r * (K - 1)
    crit = float(stats.chi2.ppf(1 - alpha, df))
    ok = T < crit
    return {"gate": "G7", "status": "passed" if ok else "failed", "T": T, "df": df, "critical": crit, "rank": r,
            "p": float(stats.chi2.sf(T, df)), "finding": None if ok else "g7.mc_noise", "remedy": "plan"}


# ------------------------------------------------------------------ locally linear toys (section 8.5), G6, G2
class Linearized:
    """h(tp) ~ h(tp0) + H (tp - tp0) around a fit point: the locally linear model of section 8.5. `pert` adds a
    toy's MC perturbation in link space (replica difference, section 6.6)."""

    def __init__(self, problem, point0: np.ndarray, pert: np.ndarray | None = None):
        self.p = problem
        self.point0 = point0.copy()
        self.h0 = problem.h(point0)
        self.link_jacobian = jacobian(problem, point0, fd_steps(problem))
        self.pert = np.zeros_like(self.h0) if pert is None else pert

    def h(self, tp):
        return self.h0 + self.link_jacobian @ (np.asarray(tp) - self.point0) + self.pert

    def H(self, tp):
        return self.link_jacobian


class _View:
    """A problem with its predictor, data or reference replaced (toys and linearized fits)."""

    def __init__(self, base, observed=None, h=None, H=None, reference=None):
        self._b = base
        self.observed = observed if observed is not None else base.observed
        self._h, self._H, self._ref = h, H, reference

    def __getattr__(self, k):
        return getattr(self._b, k)

    def h(self, tp):
        return self._h(tp) if self._h else self._b.h(tp)

    def reference(self, tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
        if self._ref is not None:
            return self._ref(tp, beta, frozen, bootstrap_frozen)
        return self._b.reference(tp, beta, frozen, bootstrap_frozen=bootstrap_frozen, bootstrap_seed=bootstrap_seed)


def view(base, **kw):
    v = _View(base, **kw)
    if kw.get("H") is not None:
        v.H = kw["H"]
    return v


def linear_toy_fit(problem, fit: Fit, toy_data, pert, ref: L.Reference, start=None) -> tuple[bool, float, np.ndarray]:
    """One locally linear toy: the linearized predictor at the fit point plus the toy's MC perturbation, the toy data,
    V-hat from `ref`; returns (converged, D at the toy's minimum, beta*)."""
    lk = L.Likelihood(problem.layout, problem.observed, fit.ref)
    point0 = fit.beta[_tp_index(lk)]
    lin = getattr(fit, "_lin", None)
    if lin is None:
        lin = Linearized(problem, point0)
        fit._lin = lin
    hl = (lambda tp, _l=lin, _p=pert: _l.h0 + _l.link_jacobian @ (np.asarray(tp) - _l.point0) + _p)
    v = view(problem, observed=toy_data, h=hl, H=lambda tp, _l=lin: _l.link_jacobian)
    m = minimize(v, ref, fit.beta if start is None else start, Hfun=v.H, hfun=hl)
    return m.converged, m.D, m.beta


def g6(problem, fit: Fit, toys, n_lin_check: int = 50, alpha: float = 0.01, allowed_fraction: float = 0.05,
       diff_threshold: float = 0.5) -> dict:
    """G6 with locally linear toys (section 8.2 note 9, 8.5): T_obs = -2 ln L at the fit (calibration set, nu and eta
    included); p = (#{T_toy >= T_obs} + X + 1) / (n + 1); `toys` yields (data, pert, ref) per toy (truth at the fit
    point, event-level noise, replica-difference MC perturbation, one independent bootstrap per toy). The linearity
    check: at the landing points beta* of the first n_lin_check toys, the fraction with |Delta chi2_full -
    Delta chi2_lin| > 0.5 must be <= 5% (D56); otherwise `g6.linearity_check_failed` and the caller switches to full
    toys or a quadratic model."""
    T_obs = fit.D
    T, X, lin_pts = [], 0, []
    lk = L.Likelihood(problem.layout, problem.observed, fit.ref)
    tpi = _tp_index(lk)
    for observed, pert, ref in toys:
        ok, D, b = linear_toy_fit(problem, fit, observed, pert, ref)
        if not ok:
            X += 1
            continue
        T.append(D)
        if len(lin_pts) < n_lin_check:
            lin_pts.append(b)
    p = testing_pvalue(T_obs, T, X)
    lin = fit._lin
    diffs = []
    D_hat = lk.deviance(fit.beta, problem.h(fit.beta[tpi]))
    Dl_hat = lk.deviance(fit.beta, lin.h(fit.beta[tpi]) - lin.pert)
    for b in lin_pts:
        full = lk.deviance(b, problem.h(b[tpi])) - D_hat
        lin_d = lk.deviance(b, lin.h0 + lin.link_jacobian @ (b[tpi] - lin.point0)) - Dl_hat
        diffs.append(abs(full - lin_d))
    frac = float(np.mean(np.asarray(diffs) > diff_threshold)) if diffs else 1.0
    lin_ok = len(diffs) >= n_lin_check and frac <= allowed_fraction
    res = {"gate": "G6", "T_obs": T_obs, "n_toys": len(T) + X, "X": X, "p": p, "linearity_fraction": frac,
           "linearity_points": len(diffs), "linearity_ok": lin_ok, "remedy": "contract"}
    if not lin_ok:
        res.update(status="incomplete", finding="g6.linearity_check_failed")
    else:
        res.update(status="passed" if p > alpha else "failed", finding=None if p > alpha else "g6.p_value")
    return res


def g6_full(problem, fit: Fit, n: int, seed, alpha: float = 0.01) -> dict:
    """G6 with full toys (section 8.5, after the linearity check fails, D56): each toy draws data from the nominal MC at
    the fit point (section 6.6), adds its own replica-difference MC perturbation and regenerates its own bootstrap
    (D46, A8), and is refitted by the section 7.3 iteration from the fit point; non-converged toys count as
    T_toy < T_obs (`fullfit_gof_pvalue`). p > alpha passes."""
    T, X, bad = [], 0, []
    for s in range(n):
        rng = np.random.default_rng([_seed_int(seed), s])
        toy = problem.with_data(problem.simulate(fit.beta, rng))
        toy.pert = np.asarray(problem.replica_pert(rng), float)
        bs = (_seed_int(seed), s, 1)
        v = view(toy, reference=lambda tp, b, frozen, bf, _bs=bs, _t=toy:
                 _t.reference(tp, b, frozen if bf else None, bootstrap_seed=_bs))
        f = iterate(v, fit.beta)
        if f.converged:
            T.append(f.D)
        else:
            X += 1
            bad.append(s)
    p = fullfit_gof_pvalue(fit.D, T, X)
    ok = p > alpha
    return {"gate": "G6", "construction": "full-toys", "T_obs": fit.D, "n_toys": n, "X": X, "p": p,
            "status": "passed" if ok else "failed", "finding": None if ok else "g6.p_value", "remedy": "contract",
            "nonconverged_toys": bad}


def chibar_pvalue(t: float, weights) -> float:
    """p of the chi-bar^2 mixture sum_j w_j chi2_j (chi2_0 a point mass at 0)."""
    if t <= 0:
        return 1.0
    return float(min(1.0, sum(w * float(stats.chi2.sf(t, j)) for j, w in enumerate(weights) if j > 0)))


def g2_statistic(problem, fit: Fit, ref=None) -> dict:
    """The G2 statistic at a fit with active bounds: in the locally linear model at the restricted fit point, the
    decrease of -2 ln L when the active theta bounds are released, t = g_A^T (F^-1)_AA ... computed as
    D_restricted - min_unrestricted of the quadratic model; with the number of active constraints."""
    lk = L.Likelihood(problem.layout, problem.observed, ref or fit.ref)
    d = len(problem.layout.theta)
    act = [i for i in fit.active if i < d]
    if not act:
        return {"t": 0.0, "active": []}
    tp = fit.beta[_tp_index(lk)]
    h = problem.h(tp)
    g, F = lk.score_fisher(fit.beta, h, jacobian(problem, tp, fd_steps(problem)))
    # the unrestricted quadratic minimum relative to the restricted one: the free directions are already at their
    # optimum given the active ones, so t = 1/2 g_A^T S_AA g_A with S_AA the Schur complement inverse on A
    Finv = linalg.inv(F)
    g_active = g[act]
    t = 0.5 * float(g_active @ Finv[np.ix_(act, act)] @ g_active)
    return {"t": t, "active": act}


def g2(problem, fit: Fit, toys, alpha: float = 0.01) -> dict:
    """G2 (section 8.2): active bounds at the fit; the reference distribution chi-bar^2 with weights from locally linear
    toys (truth the restricted fit on the boundary, V-hat as in G6, one independent bootstrap per toy, D9): the weight
    w_j is the fraction of toys whose unrestricted linear fit has j active constraints. p >= 0.01 passes; not
    significant with an active bound adds `boundary-solution`."""
    st = g2_statistic(problem, fit)
    if not st["active"]:
        return {"gate": "G2", "status": "passed", "active": [], "flags": []}
    counts = np.zeros(len(st["active"]) + 1)
    X = 0
    for observed, pert, ref in toys:
        ok, D, b = linear_toy_fit(problem, fit, observed, pert, ref)
        if not ok:
            X += 1
            continue
        lo, hi = _beta_bounds(problem, L.Likelihood(problem.layout, problem.observed, ref))
        j = sum(1 for i in st["active"] if (b[i] <= lo[i] + 1e-9 or b[i] >= hi[i] - 1e-9))
        counts[j] += 1
    n = counts.sum()
    if n == 0:
        return {"gate": "G2", "status": "incomplete", "finding": "g2.no_toys", "X": X}
    wts = counts / n
    p = chibar_pvalue(st["t"], wts)
    ok = p >= alpha
    return {"gate": "G2", "status": "passed" if ok else "failed", "t": st["t"], "weights": wts.tolist(), "p": p,
            "active": [problem.layout.theta[i] for i in st["active"]], "X": X,
            "flags": ["boundary-solution"] if ok else [], "finding": None if ok else "g2.boundary_significant",
            "remedy": "contract"}


def g3(region: dict, limits: dict) -> dict:
    """G3 (section 8.2, D47 (a)): the 68% region of theta-hat, the box of the per-parameter total intervals of section
    7.5 (`region` = {theta: [lo, hi]}), lies entirely within each declared limit (support, feasible region, surrogate
    domain; `limits` = {kind: {theta: [lo, hi]}}). A limit kind that does not apply is absent. An `incomplete`
    interval makes G3 `incomplete` (section 7.3)."""
    if any(v is None for v in region.values()):
        return {"gate": "G3", "status": "incomplete", "finding": "g3.interval_incomplete", "remedy": "plan"}
    out = []
    for kind, box in limits.items():
        for t, (lo, hi) in region.items():
            if t in box and (lo < box[t][0] or hi > box[t][1]):
                out.append({"limit": kind, "theta": t, "region": [lo, hi], "bounds": list(box[t])})
    ok = not out
    return {"gate": "G3", "status": "passed" if ok else "failed", "violations": out,
            "finding": None if ok else "g3.outside_limits", "remedy": "plan"}


def null_toys(problem, fit: Fit, n: int, seed, truth: np.ndarray | None = None):
    """Toys under the null hypothesis for G6 and G2 (section 6.6, 7.3, 8.5): data from the model's event-level noise at
    the truth point (the fit point; for G2 the restricted fit), constraint centres sampled around the true nuisances,
    a replica-difference MC perturbation per toy, and one independent bootstrap realization per toy when V_G holds a
    bootstrap block (section 8.2 note 9). Seeds are (seed, toy index): no stream is shared between toys."""
    b = fit.beta if truth is None else truth
    lk = L.Likelihood(problem.layout, problem.observed, fit.ref)
    tp = b[_tp_index(lk)]
    for i in range(n):
        rng = np.random.default_rng([_seed_int(seed), i])
        observed = problem.simulate(b, rng)
        pert = problem.replica_pert(rng, tp)
        ref = problem.reference(tp, b, None, bootstrap_seed=(_seed_int(seed), i)) \
            if getattr(problem, "has_bootstrap", False) else fit.ref
        yield observed, pert, ref
