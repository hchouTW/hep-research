"""The linearized fit operator A for Gaussian blocks at the design stage (Part B sections 6.7, 8.1, 9.2; phase 1).

beta = (theta, nu via the columns u_k of V_model, eta via the columns s_j of the data systematics, phi in profile mode),
the nuisance columns with N(0, 1) constraints (a profile-mode phi in units of its constraint sigma; an unconstrained phi
is free), so sigma_tot^design already contains their contribution (section 17, phase 1):

    Sigma_beta = (X^T W X + P)^-1,  A = Sigma_beta X^T W,  W = V_cc^-1 (the projected inverse on N_d,c^perp when the
    calibration side declares N_d,c, section 2.1),  V_cc = V_data^unc + V_MC + V_emu (+ V_learn, phase 5);
    V_emu (the surrogate's interpolation variance, section 6.4) enters W only, not Sigma_MC.

Sigma_MC = A_theta V_MC A_theta^T and Sigma_data = A_theta V_data A_theta^T (section 6.7, only Gaussian blocks:
B_m = -A, B_y = A); sigma_tot,i^design = sqrt(Sigma_theta,ii) at theta_ref, without Sigma_boot / w (Sigma_boot is
estimated with toys in phase 2, section 17), so results using it carry `provisional-thresholds`. Links: identity and
log (delta method); other links and non-Gaussian blocks are phase 2 (section 6.7: such contracts cannot be executed
before then)."""
from __future__ import annotations

import math

import numpy as np
from scipy import linalg

SUPPORTED_LINKS = ("identity", "log")


class DesignError(ValueError):
    """A design-stage computation that cannot be done: code `linear.incomplete` (phase 2 content) or
    `linear.singular` (the information matrix is singular: identifiability is P3's, phase 2)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def calibration_observables(contract: dict) -> list[dict]:
    """The calibration observables entering the likelihood (unused ones excluded, section 5.2), each a Gaussian block
    with a supported link; anything else is refused as phase-2 content."""
    unused = {u["observable"] for u in (contract.get("validation") or {}).get("unused", [])}
    out = []
    for o in contract.get("observables", []):
        if o.get("role") != "calibration" or o["name"] in unused:
            continue
        if o.get("block") != "gaussian":
            raise DesignError("linear.incomplete", f"observable {o['name']}: {o.get('block')} blocks enter the "
                              "likelihood with MC nuisances in phase 2 (section 6.7)")
        if o.get("link") not in SUPPORTED_LINKS:
            raise DesignError("linear.incomplete", f"observable {o['name']}: link {o.get('link')} is phase 2")
        out.append(o)
    return out


def projected_inverse(V: np.ndarray, constraints: list[np.ndarray], V_std: np.ndarray | None = None) -> np.ndarray:
    """S^-1 U_perp (U_perp^T V~ U_perp)^-1 U_perp^T S^-1 with S = diag(sqrt V_std,kk) (V_std = V_data^unc, the
    standardization of section 9.2; V when not given), V~ = S^-1 V S^-1 and U_perp an orthonormal basis of the
    complement of the standardized constraint directions S n (sections 2.1, 9.2)."""
    s = np.sqrt(np.diag(V if V_std is None else V_std))
    Si = np.diag(1.0 / s)
    Vt = Si @ V @ Si
    if not constraints:
        return linalg.inv(V)
    N = np.stack([s * n for n in constraints], axis=1)
    q, _ = np.linalg.qr(N, mode="complete")
    U = q[:, N.shape[1]:]
    return Si @ U @ linalg.inv(U.T @ Vt @ U) @ U.T @ Si


def operator(J: np.ndarray, V_data: np.ndarray, V_MC: np.ndarray, nuisance: np.ndarray | None = None,
             free_extra: np.ndarray | None = None, constraints: list[np.ndarray] | None = None,
             V_emu: np.ndarray | None = None) -> dict:
    """A, Sigma_beta, sigma_tot (theta block), Sigma_MC, Sigma_data for the linear Gaussian model with theta columns J,
    N(0,1)-constrained nuisance columns and free extra columns (an unconstrained profile phi)."""
    n, d = J.shape
    cols = [J]
    prior = [np.zeros(d)]
    if free_extra is not None and free_extra.size:
        cols.append(free_extra)
        prior.append(np.zeros(free_extra.shape[1]))
    if nuisance is not None and nuisance.size:
        cols.append(nuisance)
        prior.append(np.ones(nuisance.shape[1]))
    X = np.concatenate(cols, axis=1)
    P = np.diag(np.concatenate(prior))
    V = V_data + V_MC + (0.0 if V_emu is None else V_emu)
    W = projected_inverse(V, constraints or [], V_data)
    F = X.T @ W @ X + P
    if not np.all(np.isfinite(F)) or np.linalg.cond(F) > 1e14:
        raise DesignError("linear.singular", "the design-stage information matrix is singular: some direction of beta "
                          "is not identifiable (P3, phase 2)")
    Sigma = linalg.inv(F)
    Sigma = 0.5 * (Sigma + Sigma.T)
    A = Sigma @ X.T @ W
    At = A[:d]
    S_mc = At @ V_MC @ At.T
    S_data = At @ V_data @ At.T
    return {"X": X, "W": W, "Sigma_beta": Sigma, "A": A, "A_theta": At, "sigma_tot": np.sqrt(np.diag(Sigma)[:d]),
            "Sigma_MC": 0.5 * (S_mc + S_mc.T), "Sigma_data": 0.5 * (S_data + S_data.T)}


def matrix_condition(S_mc: np.ndarray, S_data: np.ndarray) -> float:
    """The largest lambda with Sigma_MC v = lambda Sigma_data v: Sigma_MC <= f Sigma_data iff it is <= f (section 6.7).
    A direction with no data covariance and some MC covariance gives inf."""
    w, U = np.linalg.eigh(S_data)
    tol = max(w.max(), 0.0) * 1e-12
    keep = w > tol
    if not keep.all():
        null = U[:, ~keep]
        if np.abs(null.T @ S_mc @ null).max() > tol:
            return math.inf
    R = U[:, keep] / np.sqrt(w[keep])
    return float(np.linalg.eigvalsh(R.T @ S_mc @ R).max())


def vmodel_columns(contract: dict, names: list[str]) -> np.ndarray:
    """Columns u_k = sqrt(lambda_k) e_k of V_model (section 5.4), in link space, all components kept (section 5.4:
    "all components may always be kept"; the truncation conditions are phase 2's). Components: squared-exponential
    kernels {kind, observables, f, length, control: {observable: z}} and explicit matrices {kind: matrix,
    observables, R}."""
    md = contract.get("model_discrepancy") or {}
    comps = md.get("components") or []
    n = len(names)
    R = np.zeros((n, n))
    idx = {nm: i for i, nm in enumerate(names)}
    for c in comps:
        kind = c.get("kind")
        obs = [o for o in c.get("observables", []) if o in idx]
        ii = [idx[o] for o in obs]
        if kind == "squared-exponential":
            z = np.array([float(c["control"][o]) for o in obs])
            K = float(c["f"]) ** 2 * np.exp(-0.5 * (z[:, None] - z[None, :]) ** 2 / float(c["length"]) ** 2)
        elif kind == "matrix":
            full = {o: k for k, o in enumerate(c["observables"])}
            M = np.array(c["R"], dtype=float)
            K = M[np.ix_([full[o] for o in obs], [full[o] for o in obs])]
        else:
            raise DesignError("linear.incomplete", f"V_model component kind {kind!r}: model ensembles and inferred "
                              "forms are phase 2")
        R[np.ix_(ii, ii)] += K
    if not R.any():
        return np.zeros((n, 0))
    lam, E = np.linalg.eigh(0.5 * (R + R.T))
    keep = lam > lam.max() * 1e-12
    order = np.argsort(lam[keep])[::-1]
    return (E[:, keep] * np.sqrt(lam[keep]))[:, order]


def systematic_columns(systematics: list[dict] | None, names: list[str], mu: np.ndarray, links: list[str]) -> np.ndarray:
    """Columns s_j of the data systematics eta_j (section 2.1: correlated systematic errors are represented by eta), in
    link space: a relative shift r_k is r_k on a log link and r_k mu_k on an identity link; an absolute shift a_k is
    a_k / mu_k and a_k."""
    cols = []
    for sj in systematics or []:
        col = np.zeros(len(names))
        for k, nm in enumerate(names):
            if nm in sj.get("relative", {}):
                r = float(sj["relative"][nm])
                col[k] = r if links[k] == "log" else r * mu[k]
            elif nm in sj.get("absolute", {}):
                a = float(sj["absolute"][nm])
                col[k] = a / mu[k] if links[k] == "log" else a
        cols.append(col)
    return np.stack(cols, axis=1) if cols else np.zeros((len(names), 0))


def _to_link(mu, J, V_data, V_mc, links):
    g = np.array([1.0 / m if l == "log" else 1.0 for m, l in zip(mu, links)])
    return (np.array([math.log(m) if l == "log" else m for m, l in zip(mu, links)]), J * g[:, None],
            V_data * np.outer(g, g), V_mc * np.outer(g, g))


def to_link_delta(mu: np.ndarray, links: list[str]) -> np.ndarray:
    """d g / d mu per observable (identity 1, log 1/mu): differences of predictions in link space."""
    return np.array([1.0 / m if l == "log" else 1.0 for m, l in zip(mu, links)])


def design(evaluator, contract: dict, plan: dict, theta_ref: dict | None = None, systematics=None,
           names: list[str] | None = None) -> dict:
    """The design-stage linearization at theta_ref (default: the prior centre, section 6.7) with the evaluator's
    Asimov prediction: J by central differences of the plan's method (common random numbers), V_MC from the
    evaluator, V_data^unc = per-event covariance / exposure of each sample (the contract's `exposure`)."""
    obs = calibration_observables(contract)
    if names is not None:
        obs = [o for o in obs if o["name"] in names]
    names = [o["name"] for o in obs]
    links = [o["link"] for o in obs]
    exposure = contract.get("exposure") or {}
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    thetas = [p for p, v in pars.items() if v["role"] == "theta"]
    phis = [p for p, v in pars.items() if v["role"] == "phi" and v.get("mode", "profile") == "profile"]
    psis = [p for p, v in pars.items() if v["role"] == "psi"]
    if theta_ref is None:
        theta_ref = {p: 0.5 * sum(pars[p]["sampling_bounds"]) for p in thetas if "sampling_bounds" in pars[p]}
    frac = float((plan.get("design") or {}).get("fd_fraction", 0.05))
    r0 = evaluator.evaluate(theta_ref, names=names)
    _check_names(r0["names"], names)
    _no_missing_support(r0, theta_ref)
    mu = r0["pred"]

    def column(p, step):
        lo = dict(theta_ref)
        hi = dict(theta_ref)
        base = theta_ref[p] if p in theta_ref else evaluator.model.nominal.get(p)   # g4sim evaluators have no model
        lo[p], hi[p] = base - step, base + step
        r_hi, r_lo = evaluator.evaluate(hi, names=names), evaluator.evaluate(lo, names=names)
        _no_missing_support(r_hi, hi)
        _no_missing_support(r_lo, lo)
        return (r_hi["pred"] - r_lo["pred"]) / (2 * step)

    def step_of(p):
        sb = pars[p].get("sampling_bounds")
        if sb:
            return frac * (sb[1] - sb[0])
        sig = (pars[p].get("constraint") or {}).get("sigma")
        if sig:
            return float(sig)
        raise DesignError("linear.incomplete", f"parameter {p}: no sampling bounds or constraint to set a step")

    J = np.stack([column(p, step_of(p)) for p in thetas], axis=1) if thetas else np.zeros((len(names), 0))
    phi_cols, phi_free = [], []
    for p in phis:
        sig = (pars[p].get("constraint") or {}).get("sigma")
        col = column(p, step_of(p))
        (phi_cols.append(col * float(sig)) if sig else phi_free.append(col))
    psi_cols = {p: column(p, step_of(p)) * float((pars[p].get("constraint") or {}).get("sigma", 0.0)) for p in psis
                if (pars[p].get("constraint") or {}).get("sigma")}
    runs = r0["runs"]
    n_data = np.array([_exposure(exposure, o, runs[k]) for k, o in enumerate(obs)], dtype=float)
    # data errors correlate only within one data sample (the contract's `sample`, else the MC run); observables of
    # different samples have independent data errors even when the MC computes them on the same events
    samples = np.array([o.get("sample") or runs[k] for k, o in enumerate(obs)], dtype=object)
    same_sample = np.equal.outer(samples, samples) & np.equal.outer(np.array(runs, dtype=object),
                                                                    np.array(runs, dtype=object))
    V_data = r0["s2"] / np.sqrt(np.outer(n_data, n_data)) * same_sample
    V_mc = r0["V_MC"]
    mu_l, J_l, Vd_l, Vm_l = _to_link(mu, J, V_data, V_mc, links)
    g = to_link_delta(mu, links)
    Ve_l = None if r0.get("V_emu") is None else np.asarray(r0["V_emu"], float) * np.outer(g, g)
    U = vmodel_columns(contract, names)
    S = systematic_columns(systematics, names, mu, links)
    Phi = np.stack([c * g for c in phi_cols], axis=1) if phi_cols else np.zeros((len(names), 0))
    Free = np.stack([c * g for c in phi_free], axis=1) if phi_free else np.zeros((len(names), 0))
    nuis = np.concatenate([U, S, Phi], axis=1)
    constraints = []
    for nd in (contract.get("validation") or {}).get("N_dc", []):
        # declared in the observables; in link space a log-link coordinate moves the observable by mu_k (review F14)
        vec = np.array([float(nd["n"].get(nm, 0.0)) * (mu[k] if links[k] == "log" else 1.0)
                        for k, nm in enumerate(names)])
        if vec.any():
            constraints.append(vec)
    op = operator(J_l, Vd_l, Vm_l, nuis, Free, constraints, Ve_l)
    psi_effect = {p: (op["A_theta"] @ (c * g)) for p, c in psi_cols.items()}
    return {"names": names, "links": links, "theta": thetas, "theta_ref": theta_ref, "mu": mu, "J": J_l,
            "V_data": Vd_l, "V_MC": Vm_l, "V_emu": Ve_l, "n_nu": U.shape[1], "n_eta": S.shape[1], "n_phi": Phi.shape[1] + Free.shape[1],
            "psi_effect": psi_effect, "runs": runs, "evaluation": r0, **op,
            "lambda_max": matrix_condition(op["Sigma_MC"], op["Sigma_data"]),
            "flags": ["provisional-thresholds"], "sigma_tot_note": "sigma_tot^design without Sigma_boot / w (phase 2)"}


def _exposure(exposure: dict, obs: dict, run: str) -> float:
    for key in (obs.get("sample"), run):
        if key is not None and key in exposure:
            return float(exposure[key])
    raise DesignError("linear.incomplete", f"observable {obs['name']}: no exposure declared for sample "
                      f"{obs.get('sample') or run} (contract `exposure`)")


def _no_missing_support(r: dict, theta: dict):
    if r.get("missing_support_runs"):
        raise DesignError("linear.missing_support", f"events not recorded at a reweighted node in runs "
                          f"{sorted(r['missing_support_runs'])} at {theta}: missing support (section 6.1), the "
                          "design-stage prediction is not defined with this plan's methods")


def _check_names(have, want):
    missing = [n for n in want if n not in have]
    if missing:
        raise DesignError("linear.unknown_observable", f"the evaluator has no observable {missing}")
