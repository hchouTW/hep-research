"""P0, kernel consistency (Part B section 8.2 note 1, D53; calib_kernel_check.py).

At >= 3 theta' (including the worst-ESS point within the prior, and the spot checks of section 5.4 when there are
any), the prediction of the plan's non-full-resimulation method is compared with `resample` + `evaluate_from` at the
most upstream node the method touches, and the difference is propagated to theta with the design-stage A:

    |Delta theta_i| <= 0.1 sigma_tot,i^design + z sigma_MC(Delta theta_i),  z = z_{1 - alpha / (2M)},
    M = d x (number of theta'), alpha = 0.01 (two-sided Bonferroni, D53).

sigma_MC(Delta theta) is from the paired MC covariance of the two predictions (the same nominal events upstream of
the rerun node; new events when the rerun starts at a generator). sigma_tot^design is without Sigma_boot / w
(phase 2), so the result carries `provisional-thresholds`. The k_B spot checks of the g4sim fixture are phase 3."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from core.calibration import design as design_mod
from core.calibration import linear

ALPHA = 0.01
MARGIN = 0.1


def paired_covariance(a: dict, b: dict, independent_runs=()) -> np.ndarray:
    """MC covariance of pred_a - pred_b from the per-event influence columns of both (same observables, same order):
    sum_i (c_a - c_b)(c_a - c_b)^T on runs whose events are shared, V_a + V_b on runs with new events."""
    k = len(a["pred"])
    V = np.zeros((k, k))
    for run, cols_a in a["influence"].items():
        cols_b = b["influence"].get(run, {})
        js = sorted(cols_a)
        Ma = np.stack([cols_a[j][0] for j in js], axis=1)
        Mb = np.stack([cols_b[j][0] for j in js], axis=1) if cols_b else np.zeros_like(Ma)
        if run in independent_runs or Ma.shape != Mb.shape:
            block = Ma.T @ Ma + Mb.T @ Mb
        else:
            D = Ma - Mb
            block = D.T @ D
        V[np.ix_(js, js)] = block
    return V


def p0(evaluator, contract: dict, plan: dict, design: dict, points: list[dict], seed: int,
       alpha: float = ALPHA, spot_checks=()) -> dict:
    """P0 at the given points (theta' dicts over the parameters evaluated by the plan's P0 methods; the others stay at
    theta_ref). Not applicable when the plan uses none of the P0 methods (section 8.1)."""
    methods = {p: evaluator.default_method(p) for p in evaluator.parameters}
    appl = design_mod.applicability(methods)["gates"]["P0"]
    if appl != "applicable":
        return {"gate": "P0", "status": "not-applicable", "reason": "the plan uses none of the P0 methods (section 8.1)"}
    pts = list(points) + [dict(s) for s in spot_checks]
    if len(pts) < 3:
        return {"gate": "P0", "status": "rejected", "findings": [{"code": "p0.too_few_points", "message":
                f"P0 needs >= 3 theta' (section 8.2 note 1), {len(pts)} given"}]}
    names, links, thetas = design["names"], design["links"], design["theta"]
    A, sig = design["A_theta"], design["sigma_tot"]
    d = len(thetas)
    M = d * len(pts)
    z = float(norm.ppf(1.0 - alpha / (2.0 * M)))
    theta_ref = design["theta_ref"]
    rows, findings = [], []
    for k, pt in enumerate(pts):
        theta = {**theta_ref, **pt}
        varied = [p for p in pt if methods.get(p) in design_mod.P0_METHODS]
        if not varied:
            return {"gate": "P0", "status": "rejected", "findings": [{"code": "p0.no_p0_parameter", "message":
                    f"point {pt} varies no parameter evaluated by a P0 method"}]}
        start = sorted({n for p in varied for n in evaluator.model.param_nodes.get(p, [])},
                       key=evaluator.model.order.index)
        r_m = evaluator.evaluate(theta, names=names)
        r_r = evaluator.rerun(start, theta, (seed, k), names=names, params=varied)   # streams per (seed, point)
        g = linear.to_link_delta(design["mu"], links)
        dm = g * (r_m["pred"] - r_r["pred"])
        Vd = paired_covariance(r_m, r_r, r_r.get("independent_runs", ())) * np.outer(g, g)
        dth = A @ dm
        smc = np.sqrt(np.maximum(np.diag(A @ Vd @ A.T), 0.0))
        bound = MARGIN * sig + z * smc
        ratio = np.abs(dth) / bound
        bad = [thetas[i] for i in np.where(~np.isfinite(dth) | (np.abs(dth) > bound))[0]]
        rows.append({"point": pt, "rerun_from": start, "delta_theta": dth.tolist(), "sigma_mc": smc.tolist(),
                     "bound": bound.tolist(), "max_ratio": float(np.nanmax(ratio)) if np.isfinite(ratio).any()
                     else float("inf"), "failing": bad,
                     "missing_support_runs": sorted(set(r_m.get("missing_support_runs", [])))})
        if bad:
            findings.append({"code": "p0.kernel_inconsistent", "message": f"at {pt}: |Delta theta| exceeds "
                             f"0.1 sigma_tot + z sigma_MC for {bad} (the declared density does not match the actual "
                             "sampling, or the support is insufficient; remedy: plan, contract if the kernel semantics "
                             "are wrong)"})
    return {"gate": "P0", "status": "failed" if findings else "passed", "z": z, "M": M, "alpha": alpha,
            "parameters": thetas, "points": rows, "findings": findings, "flags": ["provisional-thresholds"],
            "sigma_tot_note": design.get("sigma_tot_note")}


def worst_ess_and_next(p5_result: dict, n_more: int = 2) -> list[dict]:
    """The worst-ESS Sobol point of a P5 scan and the next points of the same scan (the gate-2 design)."""
    worst = p5_result["items"]["ess"]["worst_point"]
    others = [r["point"] for r in p5_result["per_point"] if r["point"] != worst]
    return [worst] + others[:n_more]


def default_points(evaluator, contract: dict, plan: dict) -> list[dict]:
    """The default theta' of P0 (section 8.2 note 1): the worst-ESS point of a P5 scan over the parameters the plan
    evaluates by a P0 method, and the next two points of that scan (with only deterministic reruns, every point has
    unit weights and the first three scan points are taken)."""
    from core.calibration import design as d
    pars = [p for p in evaluator.parameters if evaluator.default_method(p) in d.P0_METHODS]
    return worst_ess_and_next(d.p5(evaluator, contract, plan, items=("ess",), scan_parameters=pars))
