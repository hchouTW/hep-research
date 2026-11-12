"""The design-stage checks owned by calib_design.py in phase 1 (Part B sections 3.6, 6.1, 6.4, 6.7, 8.1, 8.2):
Sobol design points and the P6 held-back set (D80), P2 (D77), the support condition, P5 with feasibility and the final
method (D41, D42; Sigma_boot and b_J are phase 2, the theta-noise item phase 3), and the applicability of the
mandatory gates.

Thresholds: f = 0.1 (section 6.7, a design value calibrated in phase 2), so every P5 result carries
`provisional-thresholds`."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import qmc

from core.calibration import chain, linear

F_DEFAULT = 0.1
REWEIGHTING = ("analytic-reweighting", "step-level-reweighting")
P0_METHODS = frozenset(REWEIGHTING + ("learned-density-ratio", "rerun", "re-digitization"))
TAIL_CLASSES = ("tail",)


class CheckError(ValueError):
    """Input a check refuses (exit 2): code p5.tail_functional, design.bounds, ..."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ Sobol design points (section 6.4, D80)
def sobol_points(bounds: dict, n: int, seed: int) -> list[dict]:
    """n scrambled Sobol points within the box `bounds` {parameter: [lo, hi]} (a power of two keeps the balance)."""
    names = sorted(bounds)
    if not names:
        return [{} for _ in range(n)]
    for p in names:
        lo, hi = bounds[p]
        if not hi > lo:
            raise CheckError("design.bounds", f"parameter {p}: sampling bounds {bounds[p]} are empty")
    s = qmc.Sobol(len(names), scramble=True, seed=int(seed))
    m = int(round(math.log2(n))) if n > 0 else 0
    u = s.random_base2(m) if 2 ** m == n else s.random(n)
    lo = np.array([bounds[p][0] for p in names])
    hi = np.array([bounds[p][1] for p in names])
    pts = lo + u * (hi - lo)
    return [dict(zip(names, map(float, row))) for row in pts]


def design_points(bounds: dict, n: int, seed: int, held_back: int = 0, spot_checks=()) -> dict:
    """The plan's design points: n Sobol points, of which the last `held_back` are held back for P6, plus the spot-check
    points of section 5.4, which are always held back (evaluated with full simulation, section 6.4)."""
    if held_back > n:
        raise CheckError("design.held_back", f"{held_back} held-back points of {n}")
    pts = sobol_points(bounds, n, seed)
    return {"training": pts[: n - held_back], "held_back": pts[n - held_back:] + [dict(p) for p in spot_checks],
            "seed": int(seed), "n": n}


# ------------------------------------------------------------------ P2 (section 8.2 note 2, D77)
def p2(contract: dict) -> dict:
    """ndf = n_c - dim N_d,c - d_free >= max(3, d_free). n_c: K per count shape, K - 1 per Gaussian shape, 1 per scalar,
    unused observables excluded. d_free: the parameters of beta without an external constraint (theta, an
    unconstrained profile phi, one omega per free-omega count shape, section 2.1); constrained nuisances add a
    constraint term and a parameter and do not change ndf (execution-log reading)."""
    unused = {u["observable"] for u in (contract.get("validation") or {}).get("unused", [])}
    n_c, omega, counted = 0, 0, []
    for o in contract.get("observables", []):
        if o.get("role") != "calibration" or o["name"] in unused:
            continue
        vec = o.get("vector")
        if vec:
            k = int(vec["K"])
            if vec.get("data_side") == "count":
                n_c += k
                counted.append((o["name"], k))
                if o.get("shape_class") == "free-omega":      # its own omega in beta (section 2.1)
                    omega += 1
            else:
                n_c += k - 1
                counted.append((o["name"], k - 1))
        else:
            n_c += 1
            counted.append((o["name"], 1))
    dim_ndc = len((contract.get("validation") or {}).get("N_dc", []))
    pars = contract.get("parameters", [])
    theta = sum(1 for p in pars if p["role"] == "theta")
    free_phi = sum(1 for p in pars if p["role"] == "phi" and p.get("mode", "profile") == "profile"
                   and not (p.get("constraint") or {}).get("sigma"))
    d_free = theta + free_phi + omega
    ndf = n_c - dim_ndc - d_free
    need = max(3, d_free)
    ok = ndf >= need
    return {"gate": "P2", "status": "passed" if ok else "failed", "n_c": n_c, "dim_N_dc": dim_ndc, "d_free": d_free,
            "ndf": ndf, "required": need, "counted": counted,
            "findings": [] if ok else [{"code": "p2.insufficient_ndf", "message": f"ndf = {ndf} < max(3, d_free) = "
                                        f"{need}: G6 cannot test; add calibration observables (remedy: contract)"}]}


# ------------------------------------------------------------------ applicability (section 8.1)
def applicability(methods: dict, held_back: int = 0, shift_phi: bool = False) -> dict:
    """Derived from the plan's methods, never declared: P0 applies with any of analytic or step-level reweighting,
    learned density ratio, deterministic rerun, re-digitization; P6 with a surrogate model (its chi2 part only with
    >= 30 held-back points); G4 with event weights; G4-L with a learned density ratio; P8 and G9 with a shift-mode
    phi; the others always. G8 goes to closure-not-tested when it decides nothing (section 8.4), never here."""
    used = set(methods.values())
    na = "not-applicable"
    out = {g: "applicable" for g in ("P2", "P3", "P4", "P5", "G1", "G2", "G3", "G5", "G6", "G7", "G8")}
    out["P0"] = "applicable" if used & P0_METHODS else na
    out["P6"] = "applicable" if "surrogate-model" in used else na
    out["G4"] = "applicable" if used & set(REWEIGHTING) else na
    out["G4-L"] = "applicable" if "learned-density-ratio" in used else na
    out["P8"] = out["G9"] = "applicable" if shift_phi else na
    p6_parts = {"delta_m": out["P6"] == "applicable", "pull_chi2": out["P6"] == "applicable" and held_back >= 30}
    return {"gates": out, "P6_parts": p6_parts}


# ------------------------------------------------------------------ support (section 6.1)
def covered(lo, hi, intervals) -> np.ndarray:
    """Per event: is [lo, hi] inside the union of the intervals [lo_j, hi_j] (the mixture components' supports)?"""
    L = np.stack([np.broadcast_to(i[0], np.shape(lo)) for i in intervals])
    H = np.stack([np.broadcast_to(i[1], np.shape(lo)) for i in intervals])
    order = np.argsort(L, axis=0)
    L, H = np.take_along_axis(L, order, 0), np.take_along_axis(H, order, 0)
    cur = np.array(lo, dtype=float)
    for j in range(L.shape[0]):
        reach = L[j] <= cur + 1e-12
        cur = np.where(reach, np.maximum(cur, H[j]), cur)
    return cur >= np.asarray(hi) - 1e-12


def support_check(evaluator, contract: dict, plan: dict, params: list[str], n_scan: int = 16, seed: int = 1) -> dict:
    """Section 6.1 for each parameter evaluated by reweighting: it must act entirely through its kernel's density
    (item 3); a kernel that filters or zero-suppresses at generation is missing support unless the plan records that
    the filtering cannot change the observables for any theta' within the prior (kernels[node].filter_ignorable,
    to be confirmed by P0); and the proposal's support (the union over its mixture components) must contain the
    target support at every prior vertex and Sobol point. The evaluator answers queries (support_query); the
    decision is made here."""
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    ignorable = {n for n, k in (plan.get("kernels") or {}).items() if k.get("filter_ignorable")}
    findings, seen = [], set()

    def add(code, par, node, rid, msg):
        if (code, par, node) not in seen:
            seen.add((code, par, node))
            findings.append({"code": code, "parameter": par, "node": node, "run": rid, "message": msg})
    for p in params:
        bounds = pars[p].get("sampling_bounds")
        pts = [{p: bounds[0]}, {p: bounds[1]}] + (sobol_points({p: bounds}, n_scan, seed) if bounds else [])
        for q in evaluator.support_query(p):
            node, rid = q["node"], q["run"]
            if q["kind"] != "density" or not q["density_parameter"]:
                add("support.not_density_parameter", p, node, rid, f"{p} does not act entirely through the density of "
                    f"{node} (section 6.1 item 3)")
                continue
            if q["filtered"] and node not in ignorable:
                add("support.filtered", p, node, rid, f"{node} filters or zero-suppresses at generation: missing "
                    "support unless the plan records the filtering as ignorable for every theta' (section 6.1)")
            gen = q["proposal_supports"]
            if gen[0] is None:
                continue
            for pt in pts:
                tgt = q["target_support"](pt)
                if any(not covered(lo, hi, [g[var] for g in gen]).all() for var, (lo, hi) in tgt.items()):
                    add("support.missing", p, node, rid, f"the proposal's support at {node} does not contain the "
                        f"target support at {pt} (supp q must contain the union over the prior)")
                    break
    return {"status": "passed" if not findings else "failed", "findings": findings}


# ------------------------------------------------------------------ P5 (section 6.7, 8.2 note 3, D41, D42)
def _bootstrap_s2(x, w, kind, B, rng):
    """s_k^2: the variance of one event's contribution, from an event bootstrap of the functional under the target
    (multinomial resamples of the events with probability proportional to their weights, section 6.7)."""
    n = len(x)
    if n < 2:
        return float("nan")
    p = w / w.sum()
    est = np.empty(B)
    for b in range(B):
        idx = rng.choice(n, size=n, p=p)
        xb = x[idx]
        if kind == "std":
            est[b] = xb.std()
        else:
            est[b] = xb.mean()
    return float(n * est.var(ddof=1))


def _tail_check(contract, names):
    classes = {o["name"]: o.get("functional") for o in contract.get("observables", [])}   # calibration-functional/1
    tails = [n for n in names if classes.get(n) in TAIL_CLASSES]
    if tails:
        raise CheckError("p5.tail_functional", f"P5 on tail-type functionals {tails}: their determining region is not "
                         "defined yet, so no P5 or G4 decision is made on them (approval A7, D41)")


def p5(evaluator, contract: dict, plan: dict, systematics=None, items=("ess", "v_mc_diagonal", "matrix_condition"),
       f: float = F_DEFAULT, n_scan: int | None = None, seed: int | None = None, scan_parameters=None) -> dict:
    """P5 on one set of Sobol points within the prior (section 3.6: the prior range is scanned; by default every theta
    with sampling bounds, or the `scan_parameters` given, the others at theta_ref): the ESS item (N_eff,k >= N_req,k =
    s_k^2 / (f V^unc_data,kk), N_eff over the events entering observable k, D41), the per-observable item
    V_MC,kk <= f V^unc_data,kk for Gaussian blocks (D42), and the matrix condition Sigma_MC <= f Sigma_data point by
    point with that point's Asimov; the worst point of each item decides. Missing support at any point (an event not
    recorded at a reweighted node) fails P5. Sigma_boot and b_J (phase 2) and the theta-noise item (phase 3) are listed
    under `deferred`."""
    obs = linear.calibration_observables(contract)
    names = [o["name"] for o in obs]
    _tail_check(contract, names)
    dz = plan.get("design") or {}
    n_scan = int(n_scan or dz.get("n_scan", 64))
    seed = int(seed if seed is not None else dz.get("scan_seed", 20261112))
    B = int(dz.get("bootstrap", 0))
    rng = np.random.default_rng(int(dz.get("bootstrap_seed", 20261113)))
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    theta_ref = {p: 0.5 * sum(v["sampling_bounds"]) for p, v in pars.items()
                 if v["role"] == "theta" and v.get("sampling_bounds")}
    scan = [p for p in (scan_parameters if scan_parameters is not None else theta_ref) if p in theta_ref
            and pars[p]["sampling_bounds"][1] > pars[p]["sampling_bounds"][0]]
    pts = sobol_points({p: pars[p]["sampling_bounds"] for p in scan}, n_scan, seed) if scan else [{}]
    rw = scan
    missing: dict[int, list] = {}
    exposure = contract.get("exposure") or {}
    worst: dict[str, tuple] = {"ess": (math.inf, None, None), "v_mc_diagonal": (-math.inf, None, None),
             "matrix_condition": (-math.inf, None, None)}
    per_point = []
    for i, pt in enumerate(pts):
        theta = {**theta_ref, **pt}
        r = evaluator.evaluate(theta, names=names)
        if r.get("missing_support_runs"):
            missing.setdefault(i, sorted(r["missing_support_runs"]))
        n_data = np.array([linear._exposure(exposure, o, r["runs"][k]) for k, o in enumerate(obs)], dtype=float)
        v_data = np.diag(r["s2"]) / n_data
        row: dict[str, Any] = {"point": pt}
        if "ess" in items:
            if B > 0:                                          # the explicit event bootstrap (a check; slow)
                s2k = np.array([_bootstrap_s2(x, w, kind, B, rng) for x, w, kind in r["samples"]])
            else:                                              # its B -> infinity limit: weighted influence variance
                s2k = np.asarray(r["per_event_var"], dtype=float)
            n_req = s2k / (f * v_data)
            ratio = np.nan_to_num(r["n_eff"] / n_req, nan=0.0)        # an undefined ratio fails (review F6)
            k = int(np.argmin(ratio))
            row["ess_ratio_min"] = float(ratio[k])
            if ratio[k] < worst["ess"][0]:
                worst["ess"] = (float(ratio[k]), i, names[k])
        if "v_mc_diagonal" in items:
            q = np.nan_to_num(np.diag(r["V_MC"]) / (f * v_data), nan=np.inf)
            k = int(np.argmax(q))
            row["v_mc_ratio_max"] = float(q[k])
            if q[k] > worst["v_mc_diagonal"][0]:
                worst["v_mc_diagonal"] = (float(q[k]), i, names[k])
        if "matrix_condition" in items and i not in missing:   # undefined where support is missing (finding below)
            d = linear.design(evaluator, contract, plan, theta_ref=theta, systematics=systematics, names=names)
            row["lambda_over_f"] = d["lambda_max"] / f
            if row["lambda_over_f"] > worst["matrix_condition"][0]:
                worst["matrix_condition"] = (row["lambda_over_f"], i, None)
        per_point.append(row)
    result_items, findings = {}, []
    if "ess" in items:
        v, i, k = worst["ess"]
        ok = v >= 1.0
        result_items["ess"] = {"status": "passed" if ok else "failed", "min_neff_over_nreq": v,
                               "worst_point": pts[i] if i is not None else None, "observable": k}
        if not ok:
            findings.append({"code": "p5.ess", "message": f"N_eff/N_req = {v:.3g} < 1 for {k} at the worst Sobol "
                             f"point {pts[i]} (remedy: plan; broaden the proposal, add events, or the next-tier method)"})
    if "v_mc_diagonal" in items:
        v, i, k = worst["v_mc_diagonal"]
        ok = v <= 1.0
        result_items["v_mc_diagonal"] = {"status": "passed" if ok else "failed", "max_vmc_over_f_vdata": v,
                                         "worst_point": pts[i] if i is not None else None, "observable": k}
        if not ok:
            findings.append({"code": "p5.v_mc_diagonal", "message": f"V_MC,kk > f V_data,kk for {k} (ratio {v:.3g}) "
                             f"at {pts[i]} (approval A7, D42; remedy: plan)"})
    if "matrix_condition" in items:
        v, i, _ = worst["matrix_condition"]
        ok = v <= 1.0
        result_items["matrix_condition"] = {"status": "passed" if ok else "failed", "max_lambda_over_f": v,
                                            "worst_point": pts[i] if i is not None else None}
        if not ok:
            findings.append({"code": "p5.matrix_condition", "message": f"Sigma_MC is not <= f Sigma_data: largest "
                             f"generalized eigenvalue / f = {v:.3g} at {pts[i]} (remedy: plan)"})
    if missing:
        i0 = min(missing)
        findings.append({"code": "p5.missing_support", "message": f"events not recorded at a reweighted node in runs "
                         f"{missing[i0]} at {pts[i0]} (and {len(missing) - 1} more points): missing support, the "
                         "reweighting cannot be used there (section 6.1; remedy: plan)"})
    status = "failed" if findings else "passed"
    return {"gate": "P5", "status": status, "items": result_items, "findings": findings, "f": f,
            "scan": {"n": len(pts), "seed": seed, "parameters": rw}, "per_point": per_point,
            "deferred": ["sigma_boot (section 2.1, phase 2)", "b_J (section 8.2 note 3, phase 2)",
                         "theta-noise s_i, kappa_i (mode where the map varies with theta, phase 3)"],
            "flags": ["provisional-thresholds"]}


# ------------------------------------------------------------------ feasibility and the final method (section 3.6)
def final_methods(evaluator, contract: dict, plan: dict, f: float = F_DEFAULT, n_scan: int | None = None) -> dict:
    """The cheapest feasible candidate per parameter (section 3.6 step 2): reweighting if its support holds and the
    ESS item of P5 holds over its own prior scan (and jointly with the other reweighted parameters); rerun if the plan's
    storage is acceptable; resimulation as the plan decides (a declared budget); a surrogate model if P6 passes.
    An infeasible reweighting moves to the next tier automatically (section 15.3.1)."""
    cands = chain.candidate_methods(contract, plan)
    if cands.get("status") == "incomplete":
        return {"status": "incomplete", "reason": cands["reason"]}
    order = {p: [c["method"] for c in v] for p, v in cands["parameters"].items()}
    storage_ok = (plan.get("storage") or {}).get("acceptable", True)
    resim_ok = (plan.get("event_budget") or {}).get("resimulation", True)
    pars = [p for p in order if p in evaluator.parameters]
    chosen, log = {}, []
    for p in pars:
        for m in order[p]:
            if m in REWEIGHTING:
                sup = support_check(evaluator, contract, plan, [p])
                if sup["status"] != "passed":
                    log.append({"parameter": p, "method": m, "feasible": False, "reason": sup["findings"]})
                    continue
                trial = dict(evaluator.methods)
                evaluator.methods = {**trial, p: m}       # p scanned alone, the others at theta_ref
                try:
                    r = p5(evaluator, contract, plan, items=("ess",), f=f, n_scan=n_scan, scan_parameters=[p])
                finally:
                    evaluator.methods = trial
                ok = r["items"]["ess"]["status"] == "passed"
                log.append({"parameter": p, "method": m, "feasible": ok,
                            "min_neff_over_nreq": r["items"]["ess"]["min_neff_over_nreq"]})
                if ok:
                    chosen[p] = m
                    break
            elif m == "rerun":
                log.append({"parameter": p, "method": m, "feasible": bool(storage_ok)})
                if storage_ok:
                    chosen[p] = m
                    break
            elif m == "resimulation":
                log.append({"parameter": p, "method": m, "feasible": bool(resim_ok)})
                if resim_ok:
                    chosen[p] = m
                    break
            elif m == "surrogate-model":                    # feasible when P6 passes (calib_emulator.py, phase 3)
                from core.calibration import emulator
                r6 = emulator.feasibility(evaluator, contract, plan, p)
                log.append({"parameter": p, "method": m, "feasible": r6["feasible"], "P6": r6["status"],
                            **({"reason": r6["reason"]} if "reason" in r6 else {})})
                if r6["status"] == "incomplete":
                    return {"status": "incomplete", "reason": f"{p}: P6 of the surrogate model is incomplete "
                            f"({r6.get('reason', 'evaluations outstanding')})", "log": log}
                if r6["feasible"]:
                    chosen[p] = m
                    break
        if p not in chosen:
            return {"status": "failed", "findings": [{"code": "p5.no_feasible_method", "message": f"no feasible method "
                    f"for {p} among {order[p]}"}], "log": log}
    # joint ESS with every reweighted parameter at once (event-level product weights)
    while True:
        evaluator.methods = {**evaluator.methods, **chosen}
        rw = [p for p, m in chosen.items() if m in REWEIGHTING]
        if len(rw) <= 1:
            break
        r = p5(evaluator, contract, plan, items=("ess",), f=f, n_scan=n_scan, scan_parameters=rw)
        if r["items"]["ess"]["status"] == "passed":
            break
        weakest = min(rw, key=lambda q: next(x["min_neff_over_nreq"] for x in log if x["parameter"] == q
                                             and x["method"] in REWEIGHTING and x["feasible"]))
        nxt = [m for m in order[weakest] if m not in REWEIGHTING]
        log.append({"parameter": weakest, "method": chosen[weakest], "feasible": False, "reason": "joint ESS"})
        if not nxt:
            return {"status": "failed", "findings": [{"code": "p5.no_feasible_method", "message": f"joint ESS fails "
                    f"and {weakest} has no next-tier method"}], "log": log}
        chosen[weakest] = "resimulation" if "resimulation" in nxt else nxt[0]
    changed = {p: m for p, m in chosen.items() if order[p] and m != order[p][0]}
    return {"status": "ok", "methods": chosen, "moved_to_next_tier": changed, "log": log,
            "flags": ["provisional-thresholds"]}



def p5_with_final_methods(evaluator, contract: dict, plan: dict, systematics=None, items=("ess", "v_mc_diagonal",
                          "matrix_condition"), f: float = F_DEFAULT) -> dict:
    """P5 as section 3.6 step 2 has it: the final method first (an infeasible reweighting moves to the next tier
    automatically), then the P5 items with the final methods (review F5)."""
    m = final_methods(evaluator, contract, plan, f=f)
    if m["status"] != "ok":
        return {"gate": "P5", **m}
    evaluator.methods = {**evaluator.methods, **m["methods"]}
    r = p5(evaluator, contract, plan, systematics, items=items, f=f)
    r["final_methods"] = m["methods"]
    r["moved_to_next_tier"] = m["moved_to_next_tier"]
    return r


def g4_inputs(evaluator, contract: dict, theta: dict, f: float = F_DEFAULT) -> tuple[dict, dict, list]:
    """The inputs of G4 at one parameter point (section 6.7, D41): the event-level product weights of the events
    entering each calibration observable, and N_req,k = s_k^2 / (f V^unc_data,kk) with s_k^2 the weighted influence
    variance. Returns (weights_by_obs, n_req, missing_support_runs); `calib_reweight.py g4` decides with reweight.g4."""
    obs = linear.calibration_observables(contract)
    names = [o["name"] for o in obs]
    r = evaluator.evaluate(theta, names=names)
    exposure = contract.get("exposure") or {}
    n_data = np.array([linear._exposure(exposure, o, r["runs"][k]) for k, o in enumerate(obs)], dtype=float)
    v_data = np.diag(r["s2"]) / n_data
    n_req = np.asarray(r["per_event_var"], float) / (f * v_data)
    weights = {names[k]: np.asarray(r["samples"][k][1], float) for k in range(len(names))}
    return weights, dict(zip(names, n_req.tolist())), sorted(r.get("missing_support_runs") or [])
