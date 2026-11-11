"""Validation (Part B section 9; phase 2, WP4). `calib_validate.py` is its CLI and the sole owner of the validation
statistics, C_r^+ on N_d, the declaration checks (a)(b)(c), the decision of bootstrap rank deficiency at opening,
the toy-replica readiness decision, the minimum numbers of toys, the G5 proportion of cross-validation toys (with
`calib_design.py` calling it for P7), cross-validation, power and its simultaneous lower bound, the report of k and
the unused observables, and the records (kappa, decision records, abandonment, power abandonment). The failure-record
states change in `calib_data.py` (data_release.Ledger.apply_decision) from the decision records written here.

Conventions: residuals r_v = y_v - mu_v(beta-hat) in link space for Gaussian rows; S = diag(s_i), s_i = sigma_i^(0)
the model's data standard deviation at theta_ref without rounding (section 9.2); constraint vectors n_j in the same
coordinates as r. tau_num = 1e-10 (section 8.7).
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
from scipy import linalg, optimize, stats

from . import fit as F
from . import likelihood as L

TAU_NUM = 1e-10
ALPHA_P = 0.05


class ValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ N_d and C_r^+ (section 9.2)
def complement(s: np.ndarray, constraints: list) -> tuple[np.ndarray, np.ndarray]:
    """(U_perp, n-tilde) in standardized coordinates: n-tilde_j = S n_j / ||S n_j||, U_perp an orthonormal basis of the
    complement of their span. Dependent or nearly duplicate declarations are rejected (section 5.2 SVD check)."""
    n = s.size
    if not constraints:
        return np.eye(n), np.zeros((n, 0))
    N = np.stack([s * np.asarray(c, float) for c in constraints], axis=1)
    N = N / np.linalg.norm(N, axis=0)
    U = L.complement_basis([N[:, j] for j in range(N.shape[1])], n)
    return U, N


def c_r_plus(C_r: np.ndarray, s: np.ndarray, constraints: list) -> tuple[np.ndarray, int]:
    """C_r^+ = S^-1 U_perp (U_perp^T C~_r U_perp)^-1 U_perp^T S^-1, k = dim N_d^perp. Never made invertible by a
    small diagonal term."""
    U, _ = complement(s, constraints)
    k = U.shape[1]
    if k == 0:
        return np.zeros_like(C_r), 0
    Ct = C_r / np.outer(s, s)
    M = U.T @ Ct @ U
    SU = U / s[:, None]
    return SU @ linalg.inv(0.5 * (M + M.T)) @ SU.T, k


def declaration_check(C_r0: np.ndarray, s: np.ndarray, constraints: list, expectations: list | None = None,
                      tau: float = TAU_NUM, toy_residuals: np.ndarray | None = None) -> dict:
    """(a) ||P_N C~_r(0) P_N|| <= tau (with toys: the largest sample variance of the unrounded toy residuals on
    span{n~_j}); (b) the residual expectations of the nominal model, the design points and every alternative hypothesis
    are <= sqrt(tau) on every n~_j; (c) lambda_min(U_perp^T C~_r(0) U_perp) > tau. C_r(0) without rounding terms.
    Any failure is a contract error (exit 2); N_d^perp empty passes (c) (section 9.2)."""
    U, N = complement(s, constraints)
    Ct = C_r0 / np.outer(s, s)
    out = {"k0": int(U.shape[1]), "failures": []}
    if N.shape[1]:
        if toy_residuals is not None:
            proj = (np.asarray(toy_residuals) / s) @ N
            a = float(np.max(np.var(proj, axis=0, ddof=1)))
        else:
            P = N @ np.linalg.pinv(N)
            a = float(np.linalg.norm(P @ Ct @ P, 2))
        out["block_norm"] = a
        if a > tau:
            out["failures"].append("validate.declared_direction_has_variance")
        worst = 0.0
        for e in expectations or []:
            worst = max(worst, float(np.max(np.abs((np.asarray(e) / s) @ N))))
        out["max_expectation"] = worst
        if worst > math.sqrt(tau):
            out["failures"].append("validate.expectation_violates_constraint")
    if U.shape[1]:
        lam = float(np.linalg.eigvalsh(U.T @ Ct @ U).min())
        out["lambda_min"] = lam
        if lam <= tau:
            out["failures"].append("validate.undeclared_exact_constraint")
    out["status"] = "passed" if not out["failures"] else "failed"
    return out


def residual_covariance(V_vv, J_v, Sigma_beta, A=None, V_cv=None, d_cols=None, omit=()) -> np.ndarray:
    """C_r = V_vv + J_v Sigma_beta J_v^T - J_v A V_cv - V_vc A^T J_v^T + sum_l d_l d_l^T (section 9.2); V_cv = 0 in
    holdout. `omit` drops terms (negative controls only): 'propagation', 'cross', 'shift'."""
    C = np.array(V_vv, float, copy=True)
    if "propagation" not in omit:
        C = C + J_v @ Sigma_beta @ J_v.T
    if A is not None and V_cv is not None and "cross" not in omit:
        X = J_v @ A @ V_cv
        C = C - X - X.T
    if d_cols is not None and np.size(d_cols) and "shift" not in omit:
        C = C + d_cols @ d_cols.T
    return 0.5 * (C + C.T)


def t_v(r: np.ndarray, Cp: np.ndarray) -> float:
    return float(r @ Cp @ r)


def toy_path_reasons(spec: dict) -> list:
    """The cases in which T_v is calibrated with toys (section 9.2, D58): low counts (a validation bin with expected
    count < n_min at an evaluation point of section 2.1), an active boundary (a component of beta-hat within 1 sigma_tot
    of a boundary: the `boundary-solution` criterion), nonlinearity (the section 8.5 check fails at theta_ref or theta-hat),
    non-Gaussian blocks, an estimated C_r, a bootstrap part in V, free-omega validation shapes or event samples
    entirely in validation with free normalization (fixed to the toy path at locking)."""
    keys = ("low_counts", "active_boundary", "nonlinearity", "non_gaussian", "estimated_c_r", "bootstrap",
            "free_validation_totals")
    return [k for k in keys if spec.get(k)]


def remove_directions(s: np.ndarray, constraints: list, removed: list) -> list:
    """Directions removed after opening (N_obs = 0, N_tot,s = 0, components 0 and their collapse, bootstrap rank
    deficiency of samples entirely in validation; section 2.1): their projections on N_d^perp are merged into the null
    space. Returns the enlarged constraint list (k decreases accordingly)."""
    U, N = complement(s, constraints)
    out = list(constraints)
    for v in removed:
        vt = s * np.asarray(v, float)
        p = U @ (U.T @ vt)
        if np.linalg.norm(p) > 1e-12 * max(1.0, np.linalg.norm(vt)):
            out.append(p / s)
            U, N = complement(s, out)
    return out


def holdout_pieces(problem, fit, y_v: np.ndarray, d_cols=None, omit=()) -> dict:
    """The holdout residual and its covariance at the fit (Gaussian validation rows): r = y_v - (h_v(theta-hat) +
    U_v nu-hat + S_v eta-hat); J_v over (theta, phi_P, nu, eta) and zeros for the other nuisances; V_vv = validation
    V_data + V_MC; s_i from the validation V_data (sigma_i^(0))."""
    lay = problem.layout
    lk = L.Likelihood(lay, problem.data, fit.ref)
    sl = lk.sl
    tpi = F._tp_index(lk)
    tp = fit.beta[tpi]
    v = problem.cfg.val if hasattr(problem, "cfg") else problem.val
    U, S = problem.val_columns()
    hv = problem.h_val(tp)
    steps = F.fd_steps(problem)
    cols = []
    for j, st in enumerate(steps):
        a, b = tp.copy(), tp.copy()
        a[j] += st
        b[j] -= st
        cols.append((problem.h_val(a) - problem.h_val(b)) / (2 * st))
    nv = hv.size
    Jv = np.zeros((nv, lay.n_beta))
    Jv[:, tpi] = np.stack(cols, axis=1) if cols else np.zeros((nv, 0))
    if lay.n_nu:
        Jv[:, sl["nu"]] = U
    if lay.n_eta:
        Jv[:, sl["eta"]] = S
    mu = hv + (U @ fit.beta[sl["nu"]] if lay.n_nu else 0.0) + (S @ fit.beta[sl["eta"]] if lay.n_eta else 0.0)
    r = np.asarray(y_v, float) - mu
    V_vv = np.asarray(v["V_data"], float) + np.asarray(v["V_MC"], float)
    C = residual_covariance(V_vv, Jv, fit.Sigma_beta, d_cols=d_cols, omit=omit)
    s = np.sqrt(np.diag(np.asarray(v["V_data"], float)))
    return {"r": r, "C_r": C, "s": s, "J_v": Jv, "constraints": list(v.get("constraints", []))}


# ------------------------------------------------------------------ estimated C_r (section 9.2)
def chat_min_toys(k: int) -> int:
    """n >= max(500, 10k) (section 8.7)."""
    return max(500, 10 * int(k))


def chat_factor(n: int, k: int) -> float:
    """Quadratic forms with C-hat_r^+ are multiplied by (n - k - 2) / (n - 1) (section 9.2)."""
    return (n - k - 2.0) / (n - 1.0)


def estimate_c_r(residuals: np.ndarray, s: np.ndarray, constraints: list) -> dict:
    """C-hat_r on N_d^perp from toy residuals (rows), never redefining the null space from empirical eigenvalues."""
    R = np.asarray(residuals, float)
    n = R.shape[0]
    U, _ = complement(s, constraints)
    k = U.shape[1]
    if n < chat_min_toys(k):
        raise ValidationError("validate.too_few_toys", f"C-hat_r needs n >= max(500, 10k) = {chat_min_toys(k)}")
    Z = (R / s) @ U
    M = np.cov(Z, rowvar=False).reshape(k, k)
    SU = U / s[:, None]
    return {"C_plus": SU @ linalg.inv(M) @ SU.T, "k": k, "n": n, "factor": chat_factor(n, k)}


# ------------------------------------------------------------------ power (section 9.4)
def required_lambda(k: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """lambda with P(chi'2_k(lambda) > chi2_{k,1-alpha}) = power (7.849, 9.635, 10.903, 12.828, 16.241 for k = 1, 2,
    3, 5, 10 at alpha = 0.05)."""
    c = stats.chi2.ppf(1 - alpha, k)
    return float(optimize.brentq(lambda lam: stats.ncx2.sf(c, k, lam) - power, 1e-6, 500.0))


def analytic_power(lam: float, k: int, alpha: float = 0.05) -> float:
    if lam <= 0:
        return alpha
    return float(stats.ncx2.sf(stats.chi2.ppf(1 - alpha, k), k, lam))


def cross_lambda(e1: np.ndarray, e2: np.ndarray, Cp: np.ndarray) -> float:
    """lambda-hat_cross = e(1)^T C^+ e(2): unbiased when C and the response are fixed; may be negative (section 9.4)."""
    return float(np.asarray(e1) @ Cp @ np.asarray(e2))


def single_lambda(e: np.ndarray, Cp: np.ndarray, V_delta: np.ndarray | None = None) -> float:
    """The single-set estimate, minus tr(C^+ V_Delta) when V_Delta is given (the second unbiased form, section 9.4)."""
    v = float(np.asarray(e) @ Cp @ np.asarray(e))
    return v - float(np.trace(Cp @ V_delta)) if V_delta is not None else v


def lambda_lower_bound(cross_reps, level: float) -> float:
    """The one-sided lower bound of lambda-hat_cross from R independent MC repetitions: mean - z_level sd / sqrt(R)
    (the declared quantile method: normal approximation; section 8.7 row of line 2017, calibration 14)."""
    x = np.asarray(cross_reps, float)
    R = x.size
    if R < 2:
        raise ValidationError("validate.power_incomplete", "the lower bound needs >= 2 independent MC repetitions")
    return float(x.mean() - stats.norm.ppf(level) * x.std(ddof=1) / math.sqrt(R))


def clopper_pearson_lower(k: int, n: int, level: float) -> float:
    return 0.0 if k == 0 else float(stats.beta.ppf(1 - level, k, n - k + 1))


def bonferroni_levels(m: int, path: str, alpha_P: float = ALPHA_P) -> dict:
    """Simultaneous 1 - alpha_P over m alternatives: 1 - alpha_P/m per hypothesis on the analytic path; on the toy path
    two one-sided bounds at 1 - alpha_P/(2m) each (D59)."""
    if path == "analytic":
        return {"lambda": 1 - alpha_P / m}
    return {"lambda": 1 - alpha_P / (2 * m), "rate": 1 - alpha_P / (2 * m)}


def s_a(lam_low: float, lam_single: float, w: float = 1.0) -> float:
    """s_a = sqrt(max(0, w lam_low) / lam_single); 0 when lam_low <= 0 or lam_single = 0 (section 6.6)."""
    if lam_low <= 0 or lam_single <= 0:
        return 0.0
    return math.sqrt(max(0.0, w * lam_low) / lam_single)


def power_decision(bounds: dict) -> dict:
    """bounds = {alternative: lower bound or None (not computable)}: any computed bound < 0.8 decides insufficient
    power at once (failure takes precedence); all >= 0.8 sufficient; otherwise incomplete (section 9.4, D2)."""
    low = {a: b for a, b in bounds.items() if b is not None}
    if any(b < 0.8 for b in low.values()):
        return {"status": "failed", "finding": "power.insufficient", "bounds": bounds}
    if len(low) < len(bounds):
        return {"status": "incomplete", "finding": "power.not_computed", "bounds": bounds}
    return {"status": "passed", "bounds": bounds}


def power_analytic(cross_reps: dict, k: int, alpha: float = 0.05, alpha_P: float = ALPHA_P) -> dict:
    """The analytic path: per alternative a, lambda_low from its repetitions at 1 - alpha_P/m, power lower bound
    = the chi'2 power at lambda_low."""
    m = len(cross_reps)
    lev = bonferroni_levels(m, "analytic", alpha_P)["lambda"]
    out = {}
    for a, reps in cross_reps.items():
        if reps is None:
            out[a] = None
            continue
        lam_low = lambda_lower_bound(reps, lev)
        out[a] = analytic_power(lam_low, k, alpha)
    return power_decision(out)


# ------------------------------------------------------------------ cross-validation bookkeeping (section 9.3)
def g5_proportion(failed: int, decided: int) -> float:
    """(toys failing G5) / (toys for which G5 was decided, all folds converged) (D68, A8)."""
    return failed / decided if decided else 0.0


def g5_stop(failed: int, n_req_sum: int) -> bool:
    """Renewal stops at F_G5 > 0.25 sum_a n_req (the earlier stop under the D68 denominator, A8; section 14.1)."""
    return failed > 0.25 * n_req_sum


def cv_toy_status(fold_converged: list, fold_g5: list) -> str:
    """One cross-validation toy: not converged if any fold did not converge after multi-start (G5 then not decided);
    else failing G5 if any fold fails G5 (conditioning: not counted, renewed, not in the ratio test)."""
    if not all(fold_converged):
        return "not-converged"
    return "g5-failed" if not all(fold_g5) else "ok"


# ------------------------------------------------------------------ records (section 9.5)
def kappa_record(contract_sha256: str, plan: dict, engine_version: str) -> dict:
    """The validation configuration kappa, written before any validation statistic is computed: the plan's hash at
    that time binds the statistic."""
    ph = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    kid = hashlib.sha256(f"{contract_sha256}|{ph}|{engine_version}".encode()).hexdigest()
    return {"kappa": kid, "contract_sha256": contract_sha256, "plan_sha256": ph, "engine_version": engine_version}


class DecisionBook:
    """The decision records of calib_validate (section 9.5): pass, fail, no-testable-direction, abandoned; power
    records and power abandonment. Feeds `data_release.Ledger.apply_decision`."""

    def __init__(self, state: dict | None = None):
        self.state = state or {"schema": "calibration-decisions/1", "kappas": {}, "decisions": [], "power": []}

    def register(self, kappa: dict) -> None:
        self.state["kappas"].setdefault(kappa["kappa"], kappa)

    def _decision(self, kappa):
        d = [x for x in self.state["decisions"] if x["kappa"] == kappa]
        return d[-1] if d else None

    def decide(self, kappa: str, outcome: str, ledger=None, data_side_check_triggered: bool = False, **extra) -> dict:
        if kappa not in self.state["kappas"]:
            raise ValidationError("validate.kappa_unregistered", "write kappa before computing any statistic")
        prev = self._decision(kappa)
        if prev is not None and prev["outcome"] == "abandoned":
            raise ValidationError("validate.after_abandonment", "this kappa was abandoned: no further decision record "
                                  "is accepted (section 9.5)")
        if prev is not None:
            # recomputation with the same kappa reproduces the record; it does not write a new outcome
            if prev["outcome"] != outcome:
                raise ValidationError("validate.decided", "this kappa already has a decision record")
            return prev
        rec = {"kappa": kappa, "outcome": outcome, "data_side_check_triggered": bool(data_side_check_triggered),
               **extra}
        self.state["decisions"].append(rec)
        if ledger is not None and any(r["kappa"] == kappa for r in ledger.state["failure_records"]):
            ledger.apply_decision(rec)
        return rec

    def abandon(self, kappa: str, ledger) -> dict:
        """Accepted only for a kappa whose failure record is still pending (opened, not decided)."""
        if self._decision(kappa) is not None:
            raise ValidationError("validate.abandon_after_decision", "a decision record exists: abandonment is "
                                  "rejected and the record keeps its state (section 9.5)")
        recs = [r for r in ledger.state["failure_records"] if r["kappa"] == kappa]
        if not recs or any(r["status"] != "pending" for r in recs):
            raise ValidationError("validate.abandon_not_pending", "abandonment needs a pending failure record")
        rec = {"kappa": kappa, "outcome": "abandoned"}
        self.state["decisions"].append(rec)
        ledger.apply_decision(rec)
        return rec

    def record_power(self, kappa: str, bound: dict) -> dict:
        if any(p["kappa"] == kappa and p.get("abandoned") for p in self.state["power"]):
            raise ValidationError("validate.power_abandoned", "power abandonment was declared: no further power "
                                  "records are accepted for this kappa")
        rec = {"kappa": kappa, **bound}
        self.state["power"].append(rec)
        return rec

    def abandon_power(self, kappa: str) -> dict:
        """Accepted only when T_v (T_cv) was decided as passing and the power lower bound is not yet computed."""
        d = self._decision(kappa)
        if d is None or d["outcome"] != "pass":
            raise ValidationError("validate.abandon_power", "power abandonment needs a passing T_v or T_cv decision")
        if any(p["kappa"] == kappa and p.get("status") in ("passed", "failed") for p in self.state["power"]):
            raise ValidationError("validate.abandon_power", "the power lower bound is already computed")
        rec = {"kappa": kappa, "abandoned": True, "status": "insufficient"}
        self.state["power"].append(rec)
        return rec

    def v_status(self, kappa: str) -> str:
        """The V state of kappa's own result from its records."""
        d = self._decision(kappa)
        if d is None:
            return "incomplete"
        if d["outcome"] in ("fail", "abandoned") or d.get("data_side_check_triggered"):
            return "failed"
        if d["outcome"] == "no-testable-direction":
            return "no-testable-direction"
        pw = [p for p in self.state["power"] if p["kappa"] == kappa]
        if any(p.get("abandoned") for p in pw):
            return "failed"                                   # insufficient power, calibrated-unvalidated
        last = pw[-1] if pw else None
        if last is None or last.get("status") == "incomplete":
            return "incomplete"
        return "passed" if last.get("status") == "passed" else "failed"


# ------------------------------------------------------------------ the toy path (sections 9.2, 9.4, 6.6, 7.3)
def _toy_problem(problem, data, pert):
    return F.view(problem, data=data, h=lambda tp, _p=pert: problem.h(tp) + _p)


def holdout_toy(problem, fit, truth, rng, shift_prior: bool = True, alt_shift=None, n_start=None, seed=None):
    """One complete holdout toy (section 9.2): calibration and validation data from the model's event-level noise at
    the truth (shift-mode phi drawn from its prior, the fit still fixing them at nominal, section 6.6 item 1; an
    alternative's shift s_a delta-hat_a added to both predictions for power toys), the toy's own replica-difference
    perturbations of both predictions, its fit by section 7.4 with V-hat frozen at the nominal fit's. Returns
    (converged, residual, toy fit)."""
    q = len(getattr(problem, "shift_names", []) or [])
    phis = rng.normal(size=q) if (q and shift_prior) else None
    data = problem.simulate(truth, rng, phis) if phis is not None else problem.simulate(truth, rng)
    yv = problem.simulate_val(truth, rng, phis)
    if alt_shift is not None:
        dc, dv = alt_shift
        data.y_gauss = data.y_gauss + dc
        yv = yv + dv
    pert = problem.replica_pert(rng)
    pv = problem.replica_pert_val(rng)
    tp = _toy_problem(problem, data, pert)
    tp.h_val = lambda x, phis=None, _p=pv: problem.h_val(x) + _p
    ft = F.find_extremum(tp, seed if seed is not None else int(rng.integers(2 ** 31)), truth, frozen=fit.ref,
                         n_start=n_start) if n_start != 0 else F.iterate(tp, truth, frozen=fit.ref)
    if not ft.converged:
        return False, None, ft
    pc = holdout_pieces(tp, ft, yv)
    return True, pc["r"], ft


def reference_distribution(problem, fit, Cp, n: int, seed, n_start=None, carried=(0, 0)) -> dict:
    """The T_v reference distribution with complete toys under the null hypothesis (truth: the nominal fit's
    convergence point), counted per section 7.3 (no replacement; non-converged toys count as T >= observed; the
    ratio test on X summed over attempts before any p-value)."""
    def member(i):
        rng = np.random.default_rng([F._seed_int(seed), int(i)])
        ok, r, _ = holdout_toy(problem, fit, fit.beta, rng, n_start=n_start, seed=(F._seed_int(seed), int(i)))
        return ok, (t_v(r, Cp) if ok else None), {}
    res = F.run_testing_ensemble(member, n, range(n), carried_X=carried[0], carried_n=carried[1])
    return {"T": res.values, "X": res.X, "n": n, "ratio_failed": res.ratio_failed, "k_star": res.k_star}


def toy_pvalue(T_obs: float, ref: dict) -> dict:
    """The p-value only after the ratio test passed (section 7.3); otherwise V is incomplete."""
    if ref["ratio_failed"]:
        return {"status": "incomplete", "finding": "validate.ratio_test", "X": ref["X"]}
    return {"status": "ok", "p": F.testing_pvalue(T_obs, ref["T"], ref["X"] - 0), "X": ref["X"]}


def estimate_c_r_toys(problem, fit, s, constraints, seed, n=None, n_start=None) -> dict:
    """C-hat_r from its own set of null toys (their own replicas, separate from the reference toys), an estimation
    ensemble with replacement (section 7.3), n >= max(500, 10k)."""
    U, _ = complement(s, constraints)
    n = n or chat_min_toys(U.shape[1])

    def member(i):
        rng = np.random.default_rng([F._seed_int(seed), 1, int(i)])
        ok, r, _ = holdout_toy(problem, fit, fit.beta, rng, n_start=n_start, seed=(F._seed_int(seed), 1, int(i)))
        return ok, r, {}
    res = F.run_estimation_ensemble(member, n, range(10 * n + 100))
    if res.ratio_failed:
        return {"status": "incomplete", "finding": "validate.ratio_test", "X": res.X}
    est = estimate_c_r(np.array(res.values), s, constraints)
    w = F.w_factor(F.eps_hat(res.X, len(res.values)))
    return {"status": "ok", **est, "X": res.X, "w": w}


def power_toys(problem, fit, Cp, ref: dict, alt: dict, n: int, seed, alpha: float = 0.05, level: float = 0.975,
               n_start=None) -> dict:
    """The toy path of section 9.4 for one alternative: toys with the truth m_nom(theta-hat) + s_a delta-hat_a
    (`alt` = {dc, dv, s_a}), each redoing the fit and T_v, rejected when p <= alpha with the calibrated reference
    distribution; non-converged toys count as not rejecting; the one-sided Clopper-Pearson lower bound at `level`."""
    if ref["ratio_failed"]:
        return {"status": "incomplete", "finding": "validate.ratio_test"}
    sa = alt["s_a"]
    rej, X = 0, 0
    for i in range(n):
        rng = np.random.default_rng([F._seed_int(seed), 2, int(i)])
        ok, r, _ = holdout_toy(problem, fit, fit.beta, rng, alt_shift=(sa * alt["dc"], sa * alt["dv"]),
                               n_start=n_start, seed=(F._seed_int(seed), 2, int(i)))
        if not ok:
            X += 1
            continue
        if F.testing_pvalue(t_v(r, Cp), ref["T"], ref["X"]) <= alpha:
            rej += 1
    if X >= F.k_star(n, False):
        return {"status": "incomplete", "finding": "validate.ratio_test", "X": X}
    return {"status": "ok", "rejections": rej, "n": n, "X": X, "rate": rej / n,
            "lower": clopper_pearson_lower(rej, n, level)}


# ------------------------------------------------------------------ cross-validation (section 9.3)
def fold_fit(problem, rows, seed, frozen=None, n_start=None):
    """The training fit of one fold (the calibration rows not in the fold): section 7.4 with multi-start; the fold's
    own V-hat at convergence."""
    sub = problem.subset(np.setdiff1d(np.arange(problem.cfg.J.shape[0]), rows))
    b0 = sub_initial(sub)
    f = F.find_extremum(sub, seed, b0, frozen=frozen, n_start=n_start) if n_start != 0 else F.iterate(sub, b0,
                                                                                                    frozen=frozen)
    return sub, f


def sub_initial(sub):
    lk = L.Likelihood(sub.layout, sub.data, sub.reference(np.zeros(len(sub.layout.theta)), None))
    return lk.initial_beta(dict(zip(sub.layout.theta, np.zeros(len(sub.layout.theta)))))


def out_of_fold_residual(problem, sub, f, rows):
    """r_f = y_f - (h_f(beta-hat_f) + U_f nu-hat + S_f eta-hat): the out-of-fold residual of the fold's rows."""
    c = problem.cfg
    sl = sub.layout.slices()
    th = f.beta[:sub.d]
    mu = c.m0[rows] + c.J[rows] @ th + problem.e0[rows] + (problem.pert[rows] if np.ndim(problem.pert) else 0.0)
    if c.U is not None:
        mu = mu + c.U[rows] @ f.beta[sl["nu"]]
    if c.S is not None:
        mu = mu + c.S[rows] @ f.beta[sl["eta"]]
    return problem.data.y_gauss[rows] - mu


def cv_statistic(problem, folds, seed, Cplus: dict, factors: dict, n_start=None, g5=None) -> dict:
    """T_cv = sum_f r_f^T C-hat_{r,f}^+ r_f (times the fold's correction factor). A fold that does not converge or
    fails G5 makes cross-validation unusable: T_cv not computed, V incomplete, remedy plan (section 9.3)."""
    T, parts = 0.0, []
    for fi, rows in enumerate(folds):
        sub, f = fold_fit(problem, rows, (F._seed_int(seed), fi), n_start=n_start)
        if not f.converged:
            return {"status": "incomplete", "finding": "validate.fold_not_converged", "fold": fi, "remedy": "plan"}
        if g5 is not None and g5(sub, f)["status"] != "passed":
            return {"status": "incomplete", "finding": "validate.fold_g5", "fold": fi, "remedy": "plan"}
        r = out_of_fold_residual(problem, sub, f, rows)
        q = float(r @ Cplus[fi] @ r) * factors.get(fi, 1.0)
        parts.append(q)
        T += q
    return {"status": "ok", "T_cv": T, "parts": parts}


def cv_toy(problem, folds, truth, rng, seed, n_start=None, g5=None, frozen_by_fold=None):
    """One cross-validation toy: data at the truth, its own replica perturbation reused at the theta of every fold
    (section 6.6), every fold refitted with that fold's V-hat frozen (section 7.3). Returns (status, residuals by
    fold)."""
    data = problem.simulate(truth, rng)
    pert = problem.replica_pert(rng)
    tp = problem.with_data(data)
    tp.pert = pert
    res, conv, g5s = [], [], []
    for fi, rows in enumerate(folds):
        sub, f = fold_fit(tp, rows, (F._seed_int(seed), fi), (frozen_by_fold or {}).get(fi), n_start)
        conv.append(f.converged)
        if not f.converged:
            break
        g5s.append(True if g5 is None else g5(sub, f)["status"] == "passed")
        res.append(out_of_fold_residual(tp, sub, f, rows))
    st = cv_toy_status(conv, g5s if len(g5s) == len(folds) else g5s + [True] * (len(folds) - len(g5s)))
    return st, res


def cv_ensemble(problem, folds, truth, n_req: int, seed, n_start=None, g5=None, replacement: bool = True) -> dict:
    """A cross-validation toy ensemble (C-hat_{r,f} with replacement; reference toys without): members are toys;
    non-converged toys enter the ratio test with eps_max,cv; toys failing G5 are renewed and not counted in the ratio
    test; the summed G5 proportion (D68: over toys with G5 decided) > 20% at the end of an attempt makes V
    incomplete with no redo; renewal stops at F_G5 > 0.25 sum n_req (section 9.3, 14.1, 19-14.1f)."""
    eps = F.eps_max_cv(len(folds))
    kst = F.k_star(n_req, replacement, eps)
    vals, X, g5f, decided, i = [], 0, 0, 0, 0
    while len(vals) < n_req:
        if g5_stop(g5f, n_req):
            break
        if X >= kst:
            break
        rng = np.random.default_rng([F._seed_int(seed), 3, i])
        st, res = cv_toy(problem, folds, truth, rng, (F._seed_int(seed), 3, i), n_start, g5)
        i += 1
        if st == "not-converged":
            X += 1
            if not replacement:
                vals.append(None)
            continue
        decided += 1
        if st == "g5-failed":
            g5f += 1
            continue
        vals.append(res)
        if not replacement and len(vals) >= n_req:
            break
    prop = g5_proportion(g5f, decided)
    if prop > 0.20:
        return {"status": "incomplete", "finding": "validate.cv_g5_proportion", "proportion": prop,
                "remedy": "plan", "redo": False}
    if X >= kst:
        return {"status": "incomplete", "finding": "validate.ratio_test", "X": X, "k_star": kst, "eps_max": eps}
    return {"status": "ok", "values": [v for v in vals if v is not None], "X": X, "g5_failed": g5f,
            "proportion": prop, "eps_max": eps}


# ------------------------------------------------------------------ shapes conditioned on the total (section 2.1)
def shape_holdout_pieces(counts, p_hat, G, Sigma_beta, other=None) -> dict:
    """The holdout residual of a free-omega validation shape conditioned on its observed total N_obs (section 2.1 "C_r
    and the observed total in holdout"): r = n - N_obs p(beta-hat), C = N_obs (diag p - p p^T) + N_obs^2 G Sigma_beta
    G^T (G = dp/dbeta); with another validation observable o (`other` = {r, V, J}): the cross term N_obs G Sigma_beta
    J_o^T and o's own V_oo + J_o Sigma_beta J_o^T. The sum of the shape's residuals is 0 by construction and is declared
    in N_d (the returned constraint). N_obs = 0 removes the shape's K - 1 directions (the fallback of section 2.1):
    the caller passes such a shape to `remove_directions`."""
    n = np.asarray(counts, float)
    p = np.asarray(p_hat, float)
    N = float(n.sum())
    G = np.asarray(G, float)
    K = n.size
    r = n - N * p
    C = N * (np.diag(p) - np.outer(p, p)) + N * N * G @ Sigma_beta @ G.T
    s = np.sqrt(np.maximum(N, 1.0) * p * (1 - p))
    cons = [np.r_[np.ones(K), np.zeros(0)]]
    if other is not None:
        ro, Vo, Jo = (np.asarray(other[k], float) for k in ("r", "V", "J"))
        m = ro.size
        X = N * G @ Sigma_beta @ Jo.T
        C = np.block([[C, X], [X.T, Vo + Jo @ Sigma_beta @ Jo.T]])
        r = np.r_[r, ro]
        s = np.r_[s, np.sqrt(np.diag(Vo))]
        cons = [np.r_[np.ones(K), np.zeros(m)]]
    return {"r": r, "C_r": 0.5 * (C + C.T), "s": s, "constraints": cons, "N_obs": N}


# ------------------------------------------------------------------ event samples conditioned on N_tot,s (section 2.1)
def conditioned_sets(summary, n_by_component, B: int, seed) -> np.ndarray:
    """B sets of an event sample's summary statistics, each drawing exactly n_by_component[j] events in component j
    from the model (`summary(n_by_component, rng)` -> summary vector): the bootstrap of section 2.1 (c) conditioned on the
    vector of component totals (not on their sum, not on a shape's own passing count). Seeds (seed, b)."""
    out = []
    for b in range(B):
        rng = np.random.default_rng([int(np.random.SeedSequence(
            [int(x) for x in (seed if isinstance(seed, (list, tuple)) else [seed])]).generate_state(1)[0]), b])
        out.append(np.asarray(summary(list(n_by_component), rng), float))
    return np.array(out)


def toy_calibrated_pvalue(observed: np.ndarray, center: np.ndarray, C: np.ndarray, toys: np.ndarray) -> float:
    """p of T = (y - c)^T C^+ (y - c) against toys drawn by the same conditioning (the toy path of section 9.2:
    a bootstrap covariance always calibrates T_v with toys)."""
    Ci = np.linalg.pinv(C)
    t = lambda y: float((y - center) @ Ci @ (y - center))  # noqa: E731
    T = np.array([t(y) for y in toys])
    return F.testing_pvalue(t(observed), T, 0)
