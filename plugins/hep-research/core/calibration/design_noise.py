"""The phase-2 items of `calib_design.py` (Part B sections 2.1, 6.6, 6.7, 8.2 note 3, 9.3, 9.4, 14; phase 2, WP4):
Sigma_boot by toys and its P5 item, the Jacobian MC-noise bias b_J and its P5 item, P7 (calling the
implementations of `validate.py`), the fold-split rules of cross-validation (with the P3 of each training fold from
`identify.py`), the rejected toy and bootstrap practices, and the independence check of toy replicas by
non-repeating seeds (for non-g4sim evaluators; the g4sim event-interval check is phase 3).
"""
from __future__ import annotations

import math

import numpy as np
from scipy import linalg

from . import fit as F
from . import identify as I
from . import likelihood as L
from . import linear
from . import validate as V

F_DEFAULT = 0.1
BJ_BOUND = 0.10                    # approval A9 (2026-11-11): tightened from Part B's 0.15 after calibration 7


class DesignError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ Sigma_boot (section 2.1 (iii))
def sigma_boot(problem, beta_ref: np.ndarray, seed, N_t: int = 10, K_b: int = 6, source: str = "toys",
               n_start: int | None = 0) -> dict:
    """Sigma_boot from N_t toy data sets at theta_ref (data noise; nu, eta sampled from their constraints), each
    refitted with K_b independent bootstrap realizations (each its own interval of uniforms): the pooled within-toy
    covariance of beta-hat with nu_b = N_t (K_b - 1). Replacement within each toy; one ratio test over all N_t K_b
    realizations with X summed; w with eps-hat+ = (X + 1) / (n + X + 1). The fits use sigma_tot without Sigma_boot for
    their convergence criterion (section 7.3). Asimov is not a source (its estimate is always 0)."""
    if source != "toys":
        raise DesignError("design.sigma_boot_source", "Sigma_boot is estimated with toy data, never with Asimov "
                          "(section 2.1 (iii))")
    d = len(problem.layout.theta)
    if N_t < 10 or K_b < 6 or N_t * (K_b - 1) < max(50, d + 5):
        raise DesignError("design.sigma_boot_size", "N_t >= 10, K_b >= 6 and nu_b >= max(50, d + 5) are required")
    n_tot = N_t * K_b
    kst = F.k_star(n_tot)
    X, groups, bad = 0, [], []
    for t in range(N_t):
        rng = np.random.default_rng([F._seed_int(seed), t])
        data = problem.simulate(beta_ref, rng)
        toy = problem.with_data(data)
        vals = []
        r = 0
        while len(vals) < K_b:
            if X >= kst:
                return {"status": "failed", "finding": "p5.sigma_boot_ratio_test", "X": X, "k_star": kst,
                        "remedy": "plan"}
            bs = (F._seed_int(seed), t, r)
            r += 1
            view = F.view(toy, reference=lambda tp, b, frozen, bf, _bs=bs, _t=toy:
                          _t.reference(tp, b, frozen if bf else None, bootstrap_seed=_bs))
            f = F.iterate(view, beta_ref) if n_start == 0 else F.find_extremum(view, bs, beta_ref, n_start=n_start)
            if not f.converged:
                X += 1
                bad.append({"toy": t, "realization": bs})
                continue
            vals.append(f.beta.copy())
        groups.append(np.array(vals))
    within = sum(np.cov(g, rowvar=False) * (K_b - 1) for g in groups) / (N_t * (K_b - 1))
    eps_p = F.eps_hat(X, n_tot, plus=True)
    w = F.w_factor(eps_p)
    return {"status": "ok", "Sigma_boot": 0.5 * (within + within.T), "nu_b": N_t * (K_b - 1), "X": X, "w": w,
            "eps_plus": eps_p, "nonconverged": bad}


def p5_sigma_boot(Sigma_boot_theta: np.ndarray, w: float, Sigma_data: np.ndarray, f: float = F_DEFAULT) -> dict:
    """P5: Sigma_boot / w <= f Sigma_data (the same matrix condition as for Sigma_MC, section 6.7, D7), at the
    design-stage theta_ref."""
    lam = linear.matrix_condition(np.asarray(Sigma_boot_theta) / w, Sigma_data)
    ok = lam <= f
    return {"item": "sigma_boot", "lambda_max": lam, "f": f, "w": w, "passed": ok,
            "finding": None if ok else "p5.sigma_boot", "remedy": "plan"}


# ------------------------------------------------------------------ b_J (section 8.2 note 3)
def b_J(J: np.ndarray, W: np.ndarray, Ks: list) -> np.ndarray:
    """b_J = -F^-1 (t - u), t_l = tr(W K_l), u_l = sum_j (J_l^T W K_j q_j + J_j^T W K_l q_j), F = J^T W J, q_j the
    j-th column of W J F^-1, K_l = Cov(d e / d theta_l, e) (settled by computation, en/compute-19-13.md)."""
    Fm = J.T @ W @ J
    Fi = linalg.inv(Fm)
    Q = W @ J @ Fi
    d = J.shape[1]
    t = np.array([np.trace(W @ Ks[l]) for l in range(d)])
    u = np.array([sum(J[:, l] @ W @ Ks[j] @ Q[:, j] + J[:, j] @ W @ Ks[l] @ Q[:, j] for j in range(d))
                  for l in range(d)])
    return -Fi @ (t - u)


def p5_b_J(points: list, bound: float = BJ_BOUND) -> dict:
    """P5's b_J item over the scan points: each point {J, W, K: [K_l], sigma_tot}; |b_J,i| <= BJ_BOUND sigma_tot,i^design
    at every point, the worst deciding (0.10 by approval A9; Part B's design value was 0.15). K_l = 0 passes."""
    worst = (0.0, None)
    for i, p in enumerate(points):
        if not any(np.any(K) for K in p["K"]):
            continue
        b = b_J(p["J"], p["W"], p["K"])
        r = float(np.max(np.abs(b) / np.asarray(p["sigma_tot"])))
        if r > worst[0]:
            worst = (r, i)
    ok = worst[0] <= bound
    return {"item": "b_J", "max_ratio": worst[0], "point": worst[1], "bound": bound, "passed": ok,
            "finding": None if ok else "p5.b_J", "flags": ["provisional-thresholds"], "remedy": "plan",
            "increase_mc_factor": worst[0] / bound if not ok else 1.0}


# ------------------------------------------------------------------ P7 (sections 8.2 note 5, 9.4)
def p7(mode: str, k0: int, alternatives: dict, path: str, k: int | None = None, alpha: float = 0.05,
       toy_results: dict | None = None) -> dict:
    """P7 at the design stage. mode none -> not-applicable; k0 = 0 decided before opening -> no-testable-direction.
    Analytic path: `alternatives` = {a: [lambda-hat_cross per independent MC repetition] or None (cannot be computed)}.
    Toy path: `toy_results` = {a: {rejections, n, X} or None} with the Clopper-Pearson bound at 1 - alpha_P/(2m).
    The power toys' ratio test failing -> P7 incomplete (redone with the next seed block)."""
    if mode == "none":
        return {"gate": "P7", "status": "not-applicable"}
    if k0 == 0:
        return {"gate": "P7", "status": "no-testable-direction"}
    if path == "analytic":
        r = V.power_analytic(alternatives, k if k is not None else k0, alpha)
    else:
        m = len(toy_results or {})
        lev = V.bonferroni_levels(m, "toy")["rate"]
        bounds = {}
        for a, tr in (toy_results or {}).items():
            if tr is None or tr.get("status") == "incomplete":
                bounds[a] = None
            else:
                bounds[a] = V.clopper_pearson_lower(tr["rejections"], tr["n"], lev)
        if any(tr is not None and tr.get("status") == "incomplete" and tr.get("finding") == "validate.ratio_test"
               for tr in (toy_results or {}).values()):
            return {"gate": "P7", "status": "incomplete", "finding": "p7.ratio_test", "remedy": "plan"}
        r = V.power_decision(bounds)
    st = {"passed": "passed", "failed": "failed", "incomplete": "incomplete"}[r["status"]]
    return {"gate": "P7", "status": st, "path": path, **{k_: v for k_, v in r.items() if k_ != "status"},
            "finding": {"failed": "p7.insufficient_power", "incomplete": "p7.power_not_computed"}.get(st)}


# ------------------------------------------------------------------ cross-validation fold split (section 9.3)
def fold_split_check(contract: dict, folds: dict) -> list:
    """The fold-split rules: a shape (all its bins) and a derived quantity with its components in one fold; the
    observables of a general-form relation that depends on observed component totals in one fold; the observables
    spanned by any declared N_d,c in one fold. `folds` = {observable: fold}. Returns findings (remedy plan)."""
    out = []
    groups = []
    for o in contract.get("observables", []):
        if o.get("bins_of"):
            groups.append(("shape", [o["name"], o["bins_of"]]))
        if o.get("derived_from"):
            groups.append(("derived", [o["name"], *o["derived_from"]]))
    val = contract.get("validation") or {}
    for nd in val.get("N_dc", []):
        groups.append(("N_dc", [k for k, v in nd["n"].items() if v]))
    for rel in val.get("total_dependent_relations", []):
        groups.append(("relation", list(rel["observables"])))
    shapes = {}
    for o, f in folds.items():
        base = o.split("[")[0]
        shapes.setdefault(base, set()).add(f)
    for base, fs in shapes.items():
        if len(fs) > 1:
            out.append({"code": "design.fold_splits_shape", "observable": base, "remedy": "plan"})
    for kind, obs in groups:
        fs = {folds.get(o) for o in obs if o in folds}
        if len(fs) > 1:
            out.append({"code": f"design.fold_splits_{kind}", "observables": obs, "remedy": "plan"})
    return out


def fold_p3(problem, folds_rows: list, beta_ref: np.ndarray) -> list:
    """P3 of each training fold with its Asimov Fisher (calling identify.p3): any failing fold rejects the split."""
    out = []
    n = V._n_rows(problem)
    for fi, rows in enumerate(folds_rows):
        sub = problem.subset(np.setdiff1d(np.arange(n), rows))
        if hasattr(sub, "cfg"):
            lk = L.Likelihood(sub.layout, sub.data, sub.reference(beta_ref[:sub.d], None))
            b = lk.initial_beta(dict(zip(sub.layout.theta, beta_ref[:sub.d])))
        else:                                        # the toy detector: beta_ref restricted to the fold's layout
            b = np.asarray(beta_ref, float)[:sub.layout.n_beta]
        r = I.p3(sub, b)
        if r["status"] != "passed":
            out.append({"code": "design.fold_p3", "fold": fi, "p3": r["finding"], "remedy": "plan"})
    return out


# ------------------------------------------------------------------ practices and seeds (sections 2.1, 6.6, 8.4)
CONSTRUCTIONS = ("replica-difference", "full")
REJECTED = {"philox-only": "design.toy_philox_only", "nominal-reuse": "design.toy_nominal_reuse",
            "nominal-truth-single-replica": "design.toy_single_replica", "parametric-gaussian":
            "design.toy_parametric_mc"}


def practice_findings(plan: dict) -> list:
    """Rejected plans (remedy level plan): a toy MC construction other than replica difference or full (Philox only,
    the nominal reused without perturbation, nominal as truth with a single replica, N(0, V_MC) sampling); bootstrap
    events reused by reweighting; G8 declared with pseudo-data sharing the fit MC."""
    out = []
    toys = plan.get("toys") or {}
    c = toys.get("construction", "replica-difference")
    if c not in CONSTRUCTIONS:
        out.append({"code": REJECTED.get(c, "design.toy_construction"), "construction": c, "remedy": "plan"})
    if (plan.get("bootstrap") or {}).get("reuse_by_reweighting"):
        out.append({"code": "design.bootstrap_reweighted", "remedy": "plan"})
    g8 = plan.get("g8") or {}
    if g8.get("run") and g8.get("fit_mc") == "shared":
        out.append({"code": "design.g8_shared_mc", "remedy": "plan"})
    p7 = plan.get("p7") or {}
    if p7.get("mc_sets") == "shared-events":
        out.append({"code": "design.p7_shared_mc", "remedy": "plan"})
    return out


def seed_independence(uses: dict) -> list:
    """Toy replicas, bootstrap realizations, pseudo-data and fit MC of a non-g4sim evaluator are independent when no
    seed (key) repeats across uses (section 6.6, 17): `uses` = {use: [seed keys]}. Returns the repeated keys."""
    seen, out = {}, []
    for use, keys in uses.items():
        for k in keys:
            kk = tuple(k) if isinstance(k, (list, tuple)) else (k,)
            if kk in seen:
                out.append({"code": "design.seed_overlap", "seed": list(kk), "uses": [seen[kk], use]})
            else:
                seen[kk] = use
    return out
