"""P0, kernel consistency (Part B section 8.2 note 1, D53; calib_kernel_check.py).

At >= 3 theta' (including the worst-ESS point within the prior, and the spot checks of section 5.4 when there are
any), the prediction of the plan's non-full-resimulation method is compared with `resample` + `evaluate_from` at the
most upstream node the method touches, and the difference is propagated to theta with the design-stage A:

    |Delta theta_i| <= 0.1 sigma_tot,i^design + z sigma_MC(Delta theta_i),  z = z_{1 - alpha / (2M)},
    M = d x (number of theta'), alpha = 0.01 (two-sided Bonferroni, D53).

sigma_MC(Delta theta) is from the paired MC covariance of the two predictions (the same nominal events upstream of
the rerun node; new events when the rerun starts at a generator). sigma_tot^design is without Sigma_boot / w
(phase 2), so the result carries `provisional-thresholds`.

Section 5.4 spot checks (phase 3, g4sim; `required_spot_checks`): with k_B calibrated and the scintillation formula
downstream, the two k_B extremes of the prior; with r calibrated, the prior ends outside 0.15 <= r <= 1; with the
digitization light yield calibrated, its two prior extremes (the E^L/E^S split is the nominal one in all three). They go
to P0 when the scintillation node is evaluated by a P0 method (k_B rerun or a re-digitized scintillation parameter),
to P6 when it is evaluated with a surrogate model (section 8.1). A P0 configuration whose points omit one is rejected
(`p0.spot_checks_missing`); at a spot check the reference is the full g4sim_run plus response (`resample` of node
`transport`, a run told at that point; `incomplete` until it is told)."""
from __future__ import annotations

import numpy as np
from scipy.stats import norm

from core.calibration import design as design_mod
from core.calibration import design_g4sim as DG
from core.calibration import emulator, linear

ALPHA = 0.01
MARGIN = 0.1
R_VALID = (0.15, 1.0)                        # the scintillation formula's range of validity in r (g4sim section 10.3)
DIGITIZED = ("photoelectrons", "charge", "code")
FULL_NODE = "transport"                       # the g4sim node whose resample is a full g4sim_run (section 11.4)
RESPONSE_NODE = "response"


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
       alpha: float = ALPHA, spot_checks=(), required=None) -> dict:
    """P0 at the given points (theta' dicts over the parameters evaluated by the plan's P0 methods; the others stay at
    theta_ref). Not applicable when the plan uses none of the P0 methods (section 8.1). `required`: the section 5.4
    spot checks (`required_spot_checks(contract, plan)`); a P0 point set without one of them is rejected."""
    methods = {p: evaluator.default_method(p) for p in evaluator.parameters}
    appl = design_mod.applicability(methods)["gates"]["P0"]
    if appl != "applicable":
        return {"gate": "P0", "status": "not-applicable", "reason": "the plan uses none of the P0 methods (section 8.1)"}
    pts = list(points) + [dict(s) for s in spot_checks]
    missing = missing_spot_checks(pts, required or (), "P0")
    if missing:
        return {"gate": "P0", "status": "rejected", "findings": [{"code": "p0.spot_checks_missing", "message":
                f"the section 5.4 spot checks {missing} are not among the P0 points (full g4sim_run plus response at "
                "each; they cannot be omitted, section 8.2 note 1)"}], "required": list(required or ())}
    spots = {i: r["reason"] for i, pt in enumerate(pts) for r in required or () if r["gate"] == "P0"
             for q in r["points"] if emulator._same_point(pt, q, list(q))}
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
        r_m = evaluator.evaluate(theta, names=names)
        try:
            start, r_r = _reference(evaluator, plan, theta, varied, methods, (seed, k), names, k in spots)
        except LookupError as exc:                 # a full simulation not yet told (the g4sim ask/tell, section 7.1)
            return {"gate": "P0", "status": "incomplete", "reason": str(exc), "point": pt,
                    "spot_check": spots.get(k)}
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
                     "missing_support_runs": sorted(set(r_m.get("missing_support_runs", []))),
                     **({"spot_check": spots[k]} if k in spots else {})})
        if bad:
            findings.append({"code": "p0.kernel_inconsistent", "message": f"at {pt}: |Delta theta| exceeds "
                             f"0.1 sigma_tot + z sigma_MC for {bad} (the declared density does not match the actual "
                             "sampling, or the support is insufficient; remedy: plan, contract if the kernel semantics "
                             "are wrong)"})
    return {"gate": "P0", "status": "failed" if findings else "passed", "z": z, "M": M, "alpha": alpha,
            "parameters": thetas, "points": rows, "findings": findings, "flags": ["provisional-thresholds"],
            "sigma_tot_note": design.get("sigma_tot_note"),
            "spot_checks": [r for r in required or () if r["gate"] == "P0"]}


def _reference(evaluator, plan, theta, varied, methods, seeds, names, spot):
    """(start nodes, the resample + evaluate_from prediction). The toy chain reruns from the most upstream node the
    methods touch; g4sim (no chain model): a full g4sim_run plus response (node `transport`, the run told at theta) for
    a rerun parameter or a section 5.4 spot check, else the response stages on the plan's independent `reference`
    batch (new Geant4 events)."""
    if hasattr(evaluator, "rerun"):
        start = sorted({n for p in varied for n in evaluator.model.param_nodes.get(p, [])},
                       key=evaluator.model.order.index)
        return start, evaluator.rerun(start, theta, seeds, names=names, params=varied)   # streams per (seed, point)
    full = spot or any(methods.get(p) == "rerun" for p in varied)
    node = FULL_NODE if full else RESPONSE_NODE
    batch = (plan.get("evaluator") or {}).get("reference")
    sd = {} if full or batch is None else {"batch": batch}
    samples = evaluator.resample(node, theta, None, None, "nominal", None, sd)
    return [node], evaluator.evaluate_from(node, samples, theta, None, None, "nominal", sd, names=names)


# ------------------------------------------------------------------ section 5.4 spot checks (phase 3, g4sim)
def _g4sim_methods(contract: dict, plan: dict) -> dict:
    """{theta: (method, binding)} from the contract's locked bindings (section 11.4 Table 2), the plan's methods first."""
    rp = DG.resolve(plan, contract)
    own = plan.get("methods") or {}
    out = {}
    for p, b in DG.bindings(rp).items():
        m = own.get(p)
        if m is None:
            doc, ptr = b["document"], b["pointer"]
            m = ("rerun" if doc == "detector" and ptr.endswith("/birks_mm_per_MeV") else
                 "re-digitization" if doc in ("pipeline", "conditions") else
                 "analytic-reweighting" if doc == "request" and ptr.startswith("/source/") else "resimulation")
        out[p] = (m, b)
    return out


def _scintillation_pointers(plan: dict) -> tuple:
    """(light-yield pointer, r pointer) of the pipeline's scintillation stage, or suffixes when the pipeline is a path."""
    pipe = ((plan.get("evaluator") or {}).get("documents") or {}).get("pipeline")
    if isinstance(pipe, dict):
        idx = [i for i, st in enumerate(pipe.get("stages") or []) if st.get("kind") == "scintillation"]
        if not idx:
            return None, None
        base = f"/stages/{idx[0]}/parameters"
        return f"{base}/light_yield_per_MeV/value", f"{base}/resolution_scale/value"
    if pipe is None:
        return None, None
    return "/light_yield_per_MeV/value", "/resolution_scale/value"


def required_spot_checks(contract: dict, plan: dict) -> list[dict]:
    """The section 5.4 spot checks of a g4sim plan: [{parameter, reason, gate (P0 | P6), points}], each point over the
    theta of that gate's methods (the others at the prior centre). Empty for a plan without g4sim bindings."""
    try:
        meth = _g4sim_methods(contract, plan)
    except DG.CheckError:
        return []
    pars = {p["name"]: p for p in contract.get("parameters", []) if p.get("role") == "theta"}
    meth = {p: v for p, v in meth.items() if p in pars and "sampling_bounds" in pars[p]}
    if not meth:
        return []
    ly_ptr, r_ptr = _scintillation_pointers(plan)
    obs = (plan.get("evaluator") or {}).get("observables")
    digitized = obs is None or any(o.get("quantity") in DIGITIZED for o in obs)
    downstream = ly_ptr is not None and digitized

    def is_(p, ptr):
        return ptr is not None and meth[p][1]["document"] == "pipeline" and meth[p][1]["pointer"].endswith(ptr)
    kb = [p for p, (m, b) in meth.items() if b["document"] == "detector" and b["pointer"].endswith("/birks_mm_per_MeV")]
    scint_p0 = any(m in design_mod.P0_METHODS and (is_(p, ly_ptr) or is_(p, r_ptr)) for p, (m, b) in meth.items())
    bounds = {g: {p: tuple(map(float, pars[p]["sampling_bounds"])) for p, (m, _) in meth.items()
                  if (m in design_mod.P0_METHODS if g == "P0" else m == "surrogate-model")} for g in ("P0", "P6")}
    out = []

    def add(p, gate, reason, which=(0, 1)):
        b = dict(bounds[gate])
        b[p] = tuple(map(float, pars[p]["sampling_bounds"]))
        ext = emulator.extreme_points(b, p)
        out.append({"parameter": p, "gate": gate, "reason": reason, "points": [ext[i] for i in which]})
    for p in kb:
        m = meth[p][0]
        if downstream and (m in design_mod.P0_METHODS or (m == "surrogate-model" and scint_p0)):
            add(p, "P0", "k_B extremes: the E^L/E^S split stays the nominal k_B's (section 5.4)")
        elif downstream and m == "surrogate-model":
            add(p, "P6", "k_B extremes: the E^L/E^S split stays the nominal k_B's (section 5.4)")
    for p, (m, _b) in meth.items():
        if is_(p, r_ptr) and m in design_mod.P0_METHODS | {"surrogate-model"}:
            lo, hi = map(float, pars[p]["sampling_bounds"])
            which = tuple(i for i, v in enumerate((lo, hi)) if not R_VALID[0] <= v <= R_VALID[1])
            if which:
                add(p, "P0" if m in design_mod.P0_METHODS else "P6", "r outside 0.15 <= r <= 1, the range of the "
                    "scintillation formula (section 5.4)", which)
        if is_(p, ly_ptr) and m in design_mod.P0_METHODS:
            add(p, "P0", "light-yield extremes: the E^L/E^S split is the nominal light yield's (section 5.4)")
    return out


def missing_spot_checks(points: list, required, gate: str) -> list:
    """The required points of `gate` that no given point matches (all of the required point's coordinates)."""
    return [q for r in required if r["gate"] == gate for q in r["points"]
            if not any(emulator._same_point(pt, q, list(q)) for pt in points)]


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
