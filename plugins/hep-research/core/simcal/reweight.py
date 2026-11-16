"""Event weights of Part B section 3.6 and 6.1 (simcal_reweight.py; G4 is phase 2, G4-L phase 5).

The weight formula, with S_theta the nodes whose parameters change and S_q the nodes with a broadened proposal:

    w_i = prod_{s in S_theta} K_s(x_si | x_pa(s),i; theta') prod_{s in S_q \\ S_theta} K_s(x_si | ...; theta_0)
          / ( [sum_j c_j prod_{s in S_q} q_js(x_si | ...)] prod_{s in S_theta \\ S_q} K_s(x_si | ...; theta_0) )

c_j = n_j / N (balance heuristic); the denominator of every event is recomputed with all q_j, old events included, so
merging additional events (section 6.1 item 5) is adding a component and recomputing c_j. Check: S_q empty and
theta' = theta_0 gives w = 1. Step-level reweighting is the same formula with K_s a product over the stored steps."""
from __future__ import annotations

import math

import numpy as np
from scipy import special


def log_weights(log_target: np.ndarray, log_components: list[np.ndarray] | None, fractions: list[float] | None,
                log_nominal_outside_q: np.ndarray | None = None) -> np.ndarray:
    """log w for each event.

    log_target: sum over s in S_theta u S_q of log K_s(x; theta') (theta_0 for the nodes of S_q \\ S_theta).
    log_components: for each mixture component j, sum over s in S_q of log q_js(x) (None or [] when S_q is empty).
    fractions: c_j = n_j / N, normalized here.
    log_nominal_outside_q: sum over s in S_theta \\ S_q of log K_s(x; theta_0).
    A NaN term (an output not recorded: zero suppression, filtering) gives NaN: missing support, never a weight."""
    lw = np.asarray(log_target, dtype=float).copy()
    if log_components:
        c = np.asarray(fractions, dtype=float)
        c = c / c.sum()
        stack = np.stack([math.log(cj) + np.asarray(lc, dtype=float) for cj, lc in zip(c, log_components)])
        lw = lw - special.logsumexp(stack, axis=0)
    if log_nominal_outside_q is not None:
        lw = lw - np.asarray(log_nominal_outside_q, dtype=float)
    return lw


def formula_log_weights(logpdf, density_nodes, s_theta, sq, fractions, components, target: dict, generation: dict,
                        regenerated=frozenset()) -> np.ndarray:
    """The section 3.6 formula over one sample, with its set bookkeeping: S_theta (the density nodes whose
    parameters change) and S_q (the proposal's nodes), each without the nodes regenerated at theta' (drawn from the
    target, they leave the formula) and without nodes that are not density kernels in this sample (an injected
    reference). logpdf(node, params) -> log density per event is the evaluator's query; components are the mixture's
    parameter overrides, fractions their realized c_j = n_j / N."""
    s_theta = [s for s in s_theta if s in density_nodes and s not in regenerated]
    sq = [s for s in sq if s in density_nodes and s not in regenerated]
    num = sum((logpdf(s, target) for s in sorted(set(s_theta) | set(sq))), np.zeros(1))
    comp_terms = [sum((logpdf(s, {**generation, **c}) for s in sq), np.zeros(1)) for c in components] if sq else []
    outside = sum((logpdf(s, generation) for s in s_theta if s not in sq), np.zeros(1))
    with np.errstate(invalid="ignore"):
        return log_weights(num, comp_terms, fractions, outside)


def step_log_density(step_logpdfs: np.ndarray) -> np.ndarray:
    """Step-level reweighting: the kernel density of an event is the product over its stored steps (rows: steps)."""
    return np.asarray(step_logpdfs, dtype=float).sum(axis=0)


def kish(w: np.ndarray) -> float:
    """Kish effective sample size (sum w)^2 / sum w^2 (section 6.7)."""
    w = np.asarray(w, dtype=float)
    s2 = float((w ** 2).sum())
    return float(w.sum() ** 2 / s2) if s2 > 0 else 0.0


def merged_fractions(sizes: list[int]) -> list[float]:
    """c_j = n_j / N after merging additional events (section 6.1 item 5): every event's denominator is recomputed
    with these fractions and all components."""
    total = float(sum(sizes))
    return [n / total for n in sizes]


def poisson_ess_fraction(mu_per_channel, r: float) -> float:
    """Predicted N_eff / N for reweighting Poisson counts with means mu_ch to r mu_ch (section 3.6):
    exp(-sum_ch mu_ch (r - 1)^2)."""
    return math.exp(-float(np.sum(mu_per_channel)) * (r - 1.0) ** 2)


def summary(weights: dict) -> dict:
    """Per run: the number of events, the Kish ESS, the largest weight fraction, and max |w - 1| (the section 3.6 check
    is 0 when S_q is empty and theta' is the generation point)."""
    out = {}
    for rid, x in weights.items():
        x = np.asarray(x, dtype=float)
        tot = float(x.sum())
        out[rid] = {"n": int(len(x)), "kish": kish(x), "max_weight_fraction": float(x.max() / tot) if tot > 0 else None,
                    "max_abs_w_minus_1": float(np.abs(x - 1).max()) if len(x) else 0.0}
    return out


# ------------------------------------------------------------------ G4 (section 8.2 note 6; phase 2)
def pareto_k(w: np.ndarray) -> float:
    """The generalized-Pareto shape k of the largest weights: the Zhang-Stephens (2009) estimate with its weak prior,
    on the exceedances of the M = min(N/5, 3 sqrt(N)) largest weights over the next one (as in PSIS). k >= 0.5 means
    infinite variance of raw importance weights (section 8.2 note 6)."""
    w = np.sort(np.asarray(w, float))
    w = w[np.isfinite(w) & (w > 0)]
    N = w.size
    if N < 25:
        return math.inf
    M = int(min(N / 5, 3 * math.sqrt(N)))
    x = w[-M:] - w[-M - 1]
    x = np.sort(x[x > 0])
    n = x.size
    if n < 5:
        return 0.0
    m = 30 + int(math.sqrt(n))
    b = 1 - np.sqrt(m / (np.arange(1, m + 1) - 0.5))
    b = b / (3.0 * x[int(n / 4 + 0.5) - 1]) + 1.0 / x[-1]
    kb = np.log1p(-b[:, None] * x[None, :]).mean(axis=1)
    lik = n * (np.log(-(b / kb)) - kb - 1)
    with np.errstate(over="ignore"):
        wts = 1.0 / np.exp(lik - lik[:, None]).sum(axis=1)
    keep = wts >= 10 * np.finfo(float).eps
    wts, b = wts[keep], b[keep]
    wts = wts / wts.sum()
    bpost = float(np.sum(b * wts))
    k = float(np.log1p(-bpost * x).mean())
    return float((n * k + 10 * 0.5) / (n + 10))


def g4(weights_by_obs: dict, n_req: dict, smoothed: bool = False) -> dict:
    """G4: for each observable N_eff,k >= N_req,k (section 6.7) and Pareto k < 0.5 for raw weights (< 0.7 with
    PSIS-smoothed weights), over the event-level product weights of the events entering observable k (D41).
    `node_diag` is a diagnostic only. Remedy level plan."""
    lim = 0.7 if smoothed else 0.5
    rows, bad = [], []
    for k, w in weights_by_obs.items():
        ess = kish(np.asarray(w, float))
        pk = pareto_k(w)
        r = {"observable": k, "n_eff": ess, "n_req": float(n_req[k]), "pareto_k": pk}
        rows.append(r)
        if ess < float(n_req[k]):
            bad.append({"observable": k, "code": "g4.ess"})
        if not pk < lim:
            bad.append({"observable": k, "code": "g4.pareto_k"})
    ok = not bad
    return {"gate": "G4", "status": "passed" if ok else "failed", "observables": rows, "findings": bad,
            "finding": bad[0]["code"] if bad else None, "pareto_limit": lim, "remedy": "plan"}


# ------------------------------------------------------------------ G4-L (section 8.2, phase 5)
G4L_ALPHA = 0.01                    # section 8.7 row 2004 (P0's z; G4-L "same form as P0", reading L8)
G4L_MARGIN = 0.1
G4L_METHODS = ("bonferroni",)


def g4l_structural(record: dict, contract: dict | None = None) -> list[dict]:
    """The structural part of G4-L (reading L5): the learned ratio's record must show cross-fitting (every fold's
    training events disjoint from the events its weights apply to, from the index sets), probability calibration and
    the prior-ratio correction (section 6.2); the contract must state G4-L's alpha and multiple-comparison method
    (section 8.1, acceptance.gates["G4-L"]; alpha may be tightened below 0.01, never loosened)."""
    out = []
    disjoint = record.get("train_apply_disjoint")          # A33 (review F4): from the index sets, not the declaration
    sets_ok = isinstance(disjoint, list) and len(disjoint) == int(record.get("folds", 0)) and all(disjoint)
    if not record.get("cross_fitted") or int(record.get("folds", 0)) < 2 or not sets_ok:
        out.append({"code": "g4l.no_cross_fitting", "message": f"the weights are applied to events their classifier "
                    f"was trained on (folds {record.get('folds')}, disjoint {record.get('train_apply_disjoint')}): "
                    "cross-fitting is required (section 6.2; remedy: plan)"})
    if record.get("calibration") in (None, "none"):
        out.append({"code": "g4l.uncalibrated", "message": "the classifier output is not probability-calibrated "
                    "(section 6.2; remedy: plan)"})
    if not record.get("prior_ratio_corrected"):
        out.append({"code": "g4l.prior_ratio", "message": "the classifier output is not corrected for the prior ratio "
                    "(section 6.2; remedy: plan)"})
    if record.get("target", "node-density-ratio") != "node-density-ratio":
        out.append({"code": "g4l.sbi_refused", "message": "a learned ratio is a node density ratio only (A25)"})
    if contract is not None:
        decl = ((contract.get("acceptance") or {}).get("gates") or {}).get("G4-L")
        if not isinstance(decl, dict) or "alpha" not in decl or "multiple_comparison" not in decl:
            out.append({"code": "g4l.alpha_undeclared", "message": "the contract states G4-L's overall false-alarm "
                        "rate and multiple-comparison method (section 8.1: acceptance.gates['G4-L'] = {alpha, "
                        "multiple_comparison}; remedy: contract)"})
        else:
            a = decl["alpha"]
            if isinstance(a, bool) or not isinstance(a, (int, float)) or not 0 < a <= G4L_ALPHA:
                out.append({"code": "g4l.alpha", "message": f"alpha {a!r}: 0 < alpha <= {G4L_ALPHA} (section 8.7 row "
                            "2004; a threshold may be tightened, never loosened)"})
            if decl["multiple_comparison"] not in G4L_METHODS:
                out.append({"code": "g4l.alpha", "message": f"multiple comparison {decl['multiple_comparison']!r}: "
                            f"one of {list(G4L_METHODS)} (the P0 form)"})
    return out


def g4l_alpha(contract: dict | None) -> float:
    decl = (((contract or {}).get("acceptance") or {}).get("gates") or {}).get("G4-L") or {}
    a = decl.get("alpha", G4L_ALPHA)
    return float(a) if isinstance(a, (int, float)) and not isinstance(a, bool) and 0 < a <= G4L_ALPHA else G4L_ALPHA


def g4l(closures: list, design: dict, record: dict, contract: dict | None = None, alpha: float | None = None) -> dict:
    """G4-L: the difference from `learned_closure`, propagated to theta with A, in the form of P0 (section 8.2 note 1):
    for each parameter |Delta theta_i| <= 0.1 sigma_tot,i^design + z sigma(Delta theta_i), z = z_{1 - alpha/(2M)},
    M = d x (number of theta'). closures: per theta' {point, learned, direct, V_train}: `learned` the fold-averaged
    held-out prediction with the learned ratio, `direct` the same held-out sample with the node resampled at theta'
    (each with per-event `influence`), V_train the covariance over repeated trainings (observable space).
    sigma^2 = the paired MC variance of the closure + the repeated-training variance (reading L4). A structural
    finding (g4l_structural) rejects. Remedy level plan; `provisional-thresholds` (no section 8.7 row, L8)."""
    from scipy.stats import norm

    from core.simcal import kernel_check, linear
    structural = g4l_structural(record, contract)
    if len(closures) < 3:
        structural.append({"code": "g4l.too_few_points", "message": f"G4-L needs >= 3 theta' (the P0 form), "
                           f"{len(closures)} given"})
    a = float(alpha) if alpha is not None else g4l_alpha(contract)
    names, links, thetas = design["names"], design["links"], design["theta"]
    A, sig = np.asarray(design["A_theta"], float), np.asarray(design["sigma_tot"], float)
    M = len(thetas) * max(len(closures), 1)
    z = float(norm.ppf(1.0 - a / (2.0 * M)))
    g = linear.to_link_delta(design["mu"], links)
    rows, findings = [], []
    for c in closures:
        lp, dp = np.asarray(c["learned"]["pred"], float), np.asarray(c["direct"]["pred"], float)
        dm = g * (lp - dp)
        V = kernel_check.paired_covariance(c["learned"], c["direct"])
        if c.get("V_train") is not None:
            V = V + np.asarray(c["V_train"], float)
        Vd = V * np.outer(g, g)
        dth = A @ dm
        s = np.sqrt(np.maximum(np.diag(A @ Vd @ A.T), 0.0))
        bound = G4L_MARGIN * sig + z * s
        bad = [thetas[i] for i in np.where(~np.isfinite(dth) | (np.abs(dth) > bound))[0]]
        rows.append({"point": c["point"], "delta_theta": dth.tolist(), "sigma": s.tolist(), "bound": bound.tolist(),
                     "max_ratio": float(np.nanmax(np.abs(dth) / bound)), "failing": bad})
        if bad:
            findings.append({"code": "g4l.closure", "message": f"at {c['point']}: the held-out closure difference "
                             f"exceeds 0.1 sigma_tot + z sigma for {bad} (the density-ratio estimate is not "
                             "trustworthy; remedy: plan)"})
    status = "rejected" if structural else "failed" if findings else "passed"
    return {"gate": "G4-L", "status": status, "z": z, "M": M, "alpha": a, "parameters": thetas, "observables": names,
            "points": rows, "findings": structural + findings, "finding": (structural + findings or [{}])[0].get("code"),
            "record": record, "remedy": "plan", "flags": ["provisional-thresholds"]}


def g4l_run(evaluator, contract: dict, design: dict, points: list, alpha: float | None = None,
            training_variance: bool = True) -> dict:
    """G4-L on an evaluator with a learned ratio: at each theta' the closure of every fold (learned_closure(fold)),
    averaged over the folds on the same held-out sample, and the repeated-training covariance there (v_learn's
    training part); then `g4l`. The points are P0's (>= 3 theta' including the worst-ESS point, reading L4)."""
    from core.simcal import learned
    record = evaluator.learned_record()
    spec = evaluator._learned_spec
    bad = learned.check_spec(spec, getattr(evaluator.model, "param_nodes", None), None, contract)
    if bad:
        return {"gate": "G4-L", "status": "rejected", "findings": bad, "finding": bad[0]["code"], "record": record,
                "remedy": "plan"}
    names = design["names"]
    closures = []
    for pt in points:
        th = {**(design.get("theta_ref") or {}), **pt}
        try:
            cl = [evaluator.learned_closure(k, th, names) for k in range(int(record["folds"]))]
        except learned.OutsideSupport as exc:
            return {"gate": "G4-L", "status": "rejected", "findings": [{"code": exc.code, "message": str(exc)}],
                    "finding": exc.code, "record": record, "remedy": "plan"}
        lrn = dict(cl[0]["learned"])
        lrn["pred"] = np.mean([c["learned"]["pred"] for c in cl], axis=0)
        lrn["influence"] = {run: {j: (np.mean([c["learned"]["influence"][run][j][0] for c in cl], axis=0), col[1])
                                  for j, col in cols.items()} for run, cols in cl[0]["learned"]["influence"].items()}
        vt = evaluator.v_learn(th, names)["V_learn_train"] if training_variance else None
        closures.append({"point": th, "learned": lrn, "direct": cl[0]["direct"], "V_train": vt})
    return g4l(closures, design, record, contract, alpha)
