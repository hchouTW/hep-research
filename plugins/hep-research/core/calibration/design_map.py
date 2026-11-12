"""The efficiency-map items of `calib_design.py` (Part B sections 6.6, 6.7 "Two efficiency map modes", 8.2 P5 note 3
fifth item, 14; D28, D83 (1), D84, D85 by approval A12; phase 3, WP-D).

- The theta-noise item of P5 (map varies with theta): on the Sobol scan points (the worst deciding), s_i =
  sigma_i sqrt(tr(C^-1 sum_jl dw_j dw_l Sigma_jl)), kappa_i = sigma_i^2 sqrt(tr(C^-1 sum_jl d2w_j d2w_l Sigma_jl)),
  C = V_G + sum_jl w_j w_l Sigma_jl, Sigma_jl = U_j E_j (U_l E_l)^T or the analytic covariance; Sigma_jl = 0 for j != l
  with independent seeds and in the fallback. s_i <= 0.25 and kappa_i <= 0.05 (design values of section 8.7 row 2008,
  uncalibrated: `provisional-thresholds`; directions mixed between parameters are not covered, D85 (3)). The weights
  and their derivatives are the surrogate's (`emulator.Surrogate.weight_derivatives`).
- The D84 design-stage G6 size check (approval A12): the G6 size of the full basis from toys that redraw the replica
  set (replicas r > R, which g4sim generates on demand), each toy fitting with its own replica set and a truth map
  error from a further replica; size <= 1.5 alpha; on failure, increase R (a plan change) or toy-calibrate the G6
  reference with redrawn replicas. The plan records R and the check.
- Plan checks (remedy level plan): the seeds of the mapping runs of a shared-seed scan (one logical_run_seed and the
  interval [0, N_map) in every mapping-run record; overlaps with other uses are `design_g4sim.interval_findings`'s,
  reused, not repeated here); the practices section 6.7 rejects (g4sim's per-map replicas as independent under the
  shared seed; comonotone coupling by common uniforms or one g4sim key; coupled replicas with independent seeds; an
  interpolating surrogate; independent seeds without a passing theta-noise item; joint-pattern replicas without a
  pattern table); the fixed-map U: the linear construction only for observables the plan records as linear in eps;
  R >= 100.
- The primaries of a shared-seed scan agree event by event; the job route with g4sim's replica r reproduces the
  photoelectrons of `response.scintillation_event` with map_replica = r (once per scan).
- D83 (1) (approval A12): a built map is checked against `efficiency-map/1` with the single exemption of
  `form.uniformity` (which g4sim's own schema does not list), recorded as the known defect D83 (1) in the result.

The plan's efficiency-map block (WP-D reading; Part B fixes no field names):

    plan["efficiency_map"] = {mode: fixed | varies-with-theta, R, linear_in_eps: [observable],
                              u_construction: {observable: digitized | map_replica | linear}           (fixed map),
                              affected: [observable], through_surrogate: [observable]}     (map varies with theta)
    plan["mapping_scans"][scan] = {seeding: shared | independent, map_term: joint-pattern | analytic | g4sim-replicas
                                   | fallback (| common-uniforms | scan-key: rejected), points: [...], N_map, R,
                                   pattern_table: true | false}                                (map varies with theta)
"""
from __future__ import annotations

import math

import numpy as np
from scipy import linalg, stats

from core.simulation import efficiency_map, response

from . import design_g4sim as DG
from . import map_basis as MB

S_BOUND = 0.25                     # section 8.7 row 2008, design value (provisional-thresholds)
KAPPA_BOUND = 0.05
G6_SIZE_FACTOR = 1.5               # D84: size <= 1.5 alpha (section 8.7)
SEEDINGS = ("shared", "independent")
MAP_TERMS = ("joint-pattern", "analytic", "g4sim-replicas", "fallback")
COMONOTONE = ("common-uniforms", "scan-key")
U_FIXED = ("digitized", "map_replica", "linear")
UNIFORMITY_PATH = "$.form.uniformity"


def _finding(code: str, message: str, **extra) -> dict:
    return {"code": code, "message": message, "remedy": "plan", **extra}


# ------------------------------------------------------------------ the theta-noise item of P5
def _cross(a, b, U_list, Sigma, seeding):
    """sum_jl a_j b_l Sigma_jl (n x n)."""
    if Sigma is not None:
        J = Sigma.shape[0]
        if seeding == "shared":
            return np.einsum("j,l,jlab->ab", a, b, Sigma)
        return sum(a[j] * b[j] * Sigma[j, j] for j in range(J))
    if seeding == "shared":
        A = sum(float(x) * u for x, u in zip(a, U_list))
        B = sum(float(x) * u for x, u in zip(b, U_list))
        return A @ B.T
    return sum(float(x) * float(y) * (u @ u.T) for x, y, u in zip(a, b, U_list))


def theta_noise(surrogate, points: list, sigma_tot: dict, U_list=None, Sigma=None, seeding: str = "shared") -> dict:
    """P5's theta-noise item. points [{theta, V_G}]; sigma_tot {parameter: sigma_tot,i^design}; U_list the U_j (n x R
    each) or Sigma (J x J x n x n) the analytic Sigma_jl; seeding shared (the joint covariance), independent or
    fallback (Sigma_jl = 0 for j != l: the independent-seed value, also from shared-seed or pilot mapping runs)."""
    if seeding not in ("shared", "independent", "fallback"):
        raise DG.CheckError("design.theta_noise_seeding", f"seeding {seeding!r}: shared, independent or fallback")
    if (U_list is None) == (Sigma is None):
        raise DG.CheckError("design.theta_noise_input", "give the U_j or the analytic Sigma_jl, not both")
    Us = None if U_list is None else [np.atleast_2d(np.asarray(u, float)) for u in U_list]
    Sg = None if Sigma is None else np.asarray(Sigma, float)
    J = len(Us) if Us is not None else (0 if Sg is None else Sg.shape[0])
    if J != len(surrogate.points):
        raise DG.CheckError("design.theta_noise_input", f"{J} design points of the map term, {len(surrogate.points)} "
                            "of the surrogate")
    mode = "shared" if seeding == "shared" else "independent"
    pars = [p for p in surrogate.parameters if p in sigma_tot]
    worst: dict = {p: {"s": 0.0, "kappa": 0.0, "point_s": None, "point_kappa": None} for p in pars}
    for k, pt in enumerate(points):
        th = pt["theta"]
        w = surrogate.weights(th)
        C = np.asarray(pt["V_G"], float) + _cross(w, w, Us, Sg, mode)
        cf = linalg.cho_factor(0.5 * (C + C.T))
        for p in pars:
            d1, d2 = surrogate.weight_derivatives(th, p)
            sig = float(sigma_tot[p])
            s = sig * math.sqrt(max(float(np.trace(linalg.cho_solve(cf, _cross(d1, d1, Us, Sg, mode)))), 0.0))
            kap = sig ** 2 * math.sqrt(max(float(np.trace(linalg.cho_solve(cf, _cross(d2, d2, Us, Sg, mode)))), 0.0))
            if s > worst[p]["s"]:
                worst[p].update(s=s, point_s=k)
            if kap > worst[p]["kappa"]:
                worst[p].update(kappa=kap, point_kappa=k)
    bad = [p for p in pars if worst[p]["s"] > S_BOUND or worst[p]["kappa"] > KAPPA_BOUND]
    return {"item": "theta_noise", "seeding": seeding, "per_parameter": worst, "bounds": {"s": S_BOUND,
            "kappa": KAPPA_BOUND}, "passed": not bad, "failing": bad, "points": len(points),
            "finding": "p5.theta_noise" if bad else None, "remedy": "plan",
            "remedies": ["more photons per mapping run", "a smoother surrogate model",
                         "the shared seed with joint-pattern replicas (if independent seeds fail)"] if bad else [],
            "flags": ["provisional-thresholds"],
            "note": "directions mixed between parameters are not covered (D85 (3))"}


# ------------------------------------------------------------------ D84: the design-stage G6 size check
def g6_size(J, V_G, draw_set, draw_truth, n_toys: int, alpha: float = 0.01, seed=20261112, level: float = 0.95) -> dict:
    """The G6 size of the full basis at the design stage (D84, approval A12), linear Gaussian at theta_ref: toy t has
    data noise N(0, V_G), a truth map error draw_truth(t) (a replica outside every toy's fitted set), and fits with the
    map term of its own replica set draw_set(t) (R x n_obs predictions); T = the GLS chi2 of y with C = V_G + U U^T,
    U = M (the full basis; U U^T = M M^T); p from chi2_{n - d}, the locally linear toys' reference when the map term is
    the model's. Size <= 1.5 alpha passes (point estimate; the Clopper-Pearson interval is reported)."""
    Jm = np.atleast_2d(np.asarray(J, float))
    V = np.asarray(V_G, float)
    n, d = Jm.shape
    if n - d < 1:
        raise DG.CheckError("design.g6_size_input", "G6 needs n_obs > d")
    Lv = np.linalg.cholesky(V)
    gen = np.random.default_rng(np.random.SeedSequence([int(s) for s in np.atleast_1d(seed)]))
    rej = 0
    R = None
    for t in range(n_toys):
        P = np.asarray(draw_set(t), float)
        R = P.shape[0]
        U = MB.replica_differences(P)
        C = V + U @ U.T
        y = Lv @ gen.normal(size=n) + np.asarray(draw_truth(t), float)
        cf = linalg.cho_factor(C)
        Ciy, CiJ = linalg.cho_solve(cf, y), linalg.cho_solve(cf, Jm)
        b = linalg.solve(Jm.T @ CiJ, Jm.T @ Ciy, assume_a="pos")
        T = float(y @ Ciy - (Jm.T @ Ciy) @ b)
        rej += int(stats.chi2.sf(T, n - d) < alpha)
    size = rej / n_toys
    a = 1.0 - level
    lo = float(stats.beta.ppf(a / 2, rej, n_toys - rej + 1)) if rej else 0.0
    hi = float(stats.beta.ppf(1 - a / 2, rej + 1, n_toys - rej)) if rej < n_toys else 1.0
    bound = G6_SIZE_FACTOR * alpha
    ok = size <= bound
    return {"item": "g6_size", "check": "D84", "R": R, "n_toys": n_toys, "rejections": rej, "size": size,
            "interval": [lo, hi], "level": level, "alpha": alpha, "bound": bound, "passed": ok,
            "finding": None if ok else "design.g6_size_d84", "remedy": "plan",
            "remedies": [] if ok else ["increase R (a plan change)",
                                       "toy-calibrate the G6 reference distribution with redrawn replicas"],
            "flags": ["provisional-thresholds"]}


def g4sim_replica_toys(maps: dict, J_eps, R: int):
    """draw_set, draw_truth for `g6_size` from g4sim's replicas of a fixed map set and an observable linear in eps
    (J_eps: n_obs x native coordinates): toy t fits with replicas [R + 1 + t (R + 1), ... + R) and takes the truth from
    the next one, centred on the Dirichlet mean (the truth deviation of the map, k/n being its estimate)."""
    Jm = np.atleast_2d(np.asarray(J_eps, float))
    MB._replica_numbers(maps, R)
    centre = MB.dirichlet_mean(maps)

    def base(t):
        return R + 1 + t * (R + 1)

    def draw_set(t):
        return np.stack([Jm @ MB.map_vector(maps, r) for r in range(base(t), base(t) + R)])

    def draw_truth(t):
        return Jm @ (MB.map_vector(maps, base(t) + R) - centre)

    return draw_set, draw_truth


# ------------------------------------------------------------------ plan checks of section 6.7
def mapping_seed_findings(plan: dict) -> list:
    """Shared seed: every mapping-run record of the scan has the scan's one logical_run_seed and the interval
    [0, N_map) (written into every mapping-run card). Overlaps with other uses and between the points of an
    independent-seed scan are design_g4sim.interval_findings' (calib_design.py intervals)."""
    out = []
    evs = [e for e in plan.get("evaluations") or [] if e.get("use") == "mapping-run"]
    for scan, cfg in sorted((plan.get("mapping_scans") or {}).items()):
        runs = [e for e in evs if e.get("scan") == scan]
        if cfg.get("seeding") != "shared" or not runs:
            continue
        seeds = {int(e["logical_run_seed"]) for e in runs}
        if len(seeds) > 1:
            out.append(_finding("design.map_shared_seed", f"scan {scan}: the mapping runs use logical_run_seed "
                                f"{sorted(seeds)}; the shared seed is one seed for every design point (D28)"))
        n_map = cfg.get("N_map")
        for e in runs:
            if int(e["first_event"]) != 0 or (n_map is not None and int(e["events"]) != int(n_map)):
                out.append(_finding("design.map_shared_interval", f"scan {scan}: {e['run_id']} has [{e['first_event']}, "
                                    f"+{e['events']}); the shared seed uses [0, N_map) in every mapping run (D28)"))
        if len({int(e["events"]) for e in runs}) > 1:
            out.append(_finding("design.map_shared_interval", f"scan {scan}: the mapping runs differ in N_map"))
    return out


def map_plan_findings(plan: dict, theta_noise_result: dict | None = None, contract: dict | None = None) -> list:
    """The practices section 6.7 rejects and the U-construction rules (remedy level plan). With the contract, also the
    block rule of the mode where the map varies with theta (`block_findings`)."""
    out = [] if contract is None else block_findings(plan, contract)
    em = plan.get("efficiency_map") or {}
    mode = em.get("mode")
    if mode not in (None, "fixed", "varies-with-theta"):
        out.append(_finding("design.map_mode", f"efficiency_map.mode {mode!r}: fixed or varies-with-theta"))
        return out
    linear = set(em.get("linear_in_eps") or [])
    R = em.get("R")
    if R is not None and int(R) < efficiency_map.MINIMUM_REPLICAS:
        out.append(_finding("design.map_replicas", f"R = {R} < {efficiency_map.MINIMUM_REPLICAS} (g4sim section 10.4; "
                            "whether more are needed is the D84 check)"))
    if mode == "fixed":
        for obs, how in sorted((em.get("u_construction") or {}).items()):
            if how not in U_FIXED:
                out.append(_finding("design.map_u_construction", f"{obs}: U construction {how!r}, one of {U_FIXED}"))
            elif how == "linear" and obs not in linear:
                out.append(_finding("design.map_linear_not_linear", f"{obs}: the linear construction U = J B_map is "
                                    "allowed only for an observable the plan records as linear in eps; digitize at "
                                    "the replicas through g4sim-digi-job/1 (section 6.7, decided 2026-11-09)"))
        return out
    if mode != "varies-with-theta":
        return out
    sur = ((plan.get("design") or {}).get("surrogate") or {}).get("mode", "interpolate")
    if sur == "interpolate":
        out.append(_finding("design.map_interpolating_surrogate", "the map varies with theta: a surrogate that "
                            "interpolates the design points exactly inherits their map noise in its slope (section "
                            "6.7, D28); use mode regression"))
    scans = plan.get("mapping_scans") or {}
    if not scans:
        out.append(_finding("design.map_scan_missing", "the map varies with theta but the plan declares no mapping scan"))
    for scan, cfg in sorted(scans.items()):
        seeding, term = cfg.get("seeding"), cfg.get("map_term")
        where = f"scan {scan}"
        if seeding not in SEEDINGS:
            out.append(_finding("design.map_seeding", f"{where}: seeding {seeding!r}, one of {SEEDINGS}"))
            continue
        if term in COMONOTONE:
            out.append(_finding("design.map_comonotone_replicas", f"{where}: replicas coupled across design points by "
                                "common uniforms or by one g4sim key for the scan are comonotone (0.1% of the variance "
                                "of the difference; no slope or curvature noise; section 6.7)"))
            continue
        if term not in MAP_TERMS:
            out.append(_finding("design.map_term", f"{where}: map_term {term!r}, one of {MAP_TERMS}"))
            continue
        if seeding == "shared" and term == "g4sim-replicas":
            out.append(_finding("design.map_per_map_replicas", f"{where}: under the shared seed g4sim's per-map "
                                "replicas, keyed by each map's own hash, are independent across design points and "
                                "miss the correlated map error (0.37-0.50 of the map variance; D28); use joint-pattern "
                                "replicas, the analytic covariance, or the fallback"))
        if seeding == "independent" and term != "g4sim-replicas":
            out.append(_finding("design.map_coupled_independent", f"{where}: with independent seeds the map term uses "
                                f"g4sim's replicas of each map (one phi_j per design point), not {term}"))
        if seeding == "independent":
            tn = theta_noise_result
            if tn is None:
                out.append(_finding("design.map_independent_theta_noise", f"{where}: independent seeds are allowed "
                                    "only when the theta-noise item of P5 passes with Sigma_jl = 0; give its result"))
            elif tn.get("seeding") not in ("independent", "fallback") or not tn.get("passed"):
                out.append(_finding("design.map_independent_theta_noise", f"{where}: the theta-noise item with "
                                    "Sigma_jl = 0 did not pass (or was computed with the joint covariance)"))
        if term in ("joint-pattern", "analytic") and cfg.get("pattern_table") is False:
            out.append(_finding("design.map_no_pattern_table", f"{where}: {term} needs the pattern table (the mapping "
                                "runs' photons.csv and primaries.csv); without it, the fallback"))
        if term == "analytic":
            bad = sorted(o for o in (cfg.get("observables") or []) if o not in linear)
            if bad:
                out.append(_finding("design.map_analytic_nonlinear", f"{where}: the analytic covariance is for "
                                    f"observables linear in eps only; {bad} are not recorded as linear"))
        Rs = cfg.get("R")
        if term != "analytic" and Rs is not None and int(Rs) < efficiency_map.MINIMUM_REPLICAS:
            out.append(_finding("design.map_replicas", f"{where}: R = {Rs} < {efficiency_map.MINIMUM_REPLICAS}"))
    return out


def block_findings(plan: dict, contract: dict) -> list:
    """Map varies with theta (section 6.7): an observable the map affects (efficiency_map.affected and the scans'
    observables) is in a Gaussian block, or enters through a surrogate model with the error in the map term
    (efficiency_map.through_surrogate); the MC nuisances of Poisson and binomial blocks carry only the noise of MC
    counts and have no place for the map noise. Remedy level plan (convert to a Gaussian summary statistic, or predict
    it through the surrogate)."""
    em = plan.get("efficiency_map") or {}
    if em.get("mode") != "varies-with-theta":
        return []
    affected = set(em.get("affected") or [])
    for cfg in (plan.get("mapping_scans") or {}).values():
        affected |= set(cfg.get("observables") or [])
    via = set(em.get("through_surrogate") or [])
    blocks = {o["name"]: o.get("block", "gaussian") for o in contract.get("observables") or []}
    out = []
    for name in sorted(affected):
        if name not in blocks:
            out.append(_finding("design.map_observable_unknown", f"{name}: affected by the map but not a contract "
                                "observable"))
        elif blocks[name] in ("poisson", "binomial") and name not in via:
            out.append(_finding("design.map_nongaussian_block", f"{name}: a {blocks[name]} block affected by an "
                                "efficiency map that varies with theta; its MC nuisances carry only the noise of MC "
                                "counts, so it must be a Gaussian block (a Gaussian summary statistic) or enter "
                                "through the surrogate model with the error in U(theta) phi_map (section 6.7)"))
    return out


def primaries_findings(rows_by_point: dict) -> list:
    """The primaries.csv of a shared-seed scan agree event by event (rows as read, keyed by their event column)."""
    out: list = []
    items = list(rows_by_point.items())
    if len(items) < 2:
        return out
    ref_name, ref = items[0]
    ref_rows = {str(r[0]): list(map(str, r)) for r in ref}
    for name, rows in items[1:]:
        cur = {str(r[0]): list(map(str, r)) for r in rows}
        if set(cur) != set(ref_rows):
            diff = sorted(set(cur) ^ set(ref_rows), key=lambda x: (len(x), x))
            out.append(_finding("design.map_primaries", f"{name} and {ref_name} have different events (first {diff[0]})",
                                point=name, event=diff[0]))
            continue
        bad = [e for e in sorted(ref_rows, key=lambda x: (len(x), x)) if cur[e] != ref_rows[e]]
        if bad:
            out.append(_finding("design.map_primaries", f"{name} and {ref_name} disagree from event {bad[0]} "
                                f"({len(bad)} events): the shared seed needs the same primaries (D28)",
                                point=name, event=bad[0]))
    return out


def job_route_findings(pipeline: dict, map_document: dict, readout: str, rows: list, replica: int,
                       job: dict | None = None) -> list:
    """Once per scan: the job route with g4sim's own replica r of map j (efficiency_map.efficiencies per bin)
    reproduces, event by event, the photoelectrons per (event, volume, channel) of response.scintillation_event with
    map_replica = r and the yield factor of response.yield_factor (charge and code are not compared: the job's channel
    streams are counted by volume ID x C + c). rows: (event, volume, bin, E^L, E^S, n^L); `job` the plan's job of
    replica r (default: built from the documents by design_g4sim.job_from_documents)."""
    from core.simulation import digitize
    run_seed = int(pipeline["run_seed"])
    if int(pipeline.get("replica", 0)) != 0:
        return [_finding("design.replica", "the pipeline's replica is not 0 (section 6.6)")]
    if job is None:                               # the job of replica r as calib_design.py builds it
        job = DG.job_from_documents(pipeline, map_document, readout, sorted({int(r[2]) for r in rows}), run_seed,
                                    map_replica=int(replica))
    job = {**job, "timing": None}                 # photoelectrons only: the times are not compared
    got, _ = digitize.digitize(job, rows)
    sc = DG._stage(pipeline, "scintillation", readout)
    width = float(job["stage"].get("yield_relative_width", 0.0))
    grouped: dict = {}
    for event, volume, b, large, small, steps in rows:
        grouped.setdefault((int(event), int(volume)), {})[int(b)] = (large, small, steps)
    chans = list(map_document["channels"])
    want = {}
    for (event, volume), bins in grouped.items():
        f = response.yield_factor(pipeline, event, volume, width)
        pe = response.scintillation_event(pipeline, sc, event, volume, bins, map_document, f, map_replica=int(replica))
        for c, name in enumerate(chans):
            want[(event, volume, c)] = pe[name]
    out = []
    for event, volume, c, photoelectrons, _, _ in got:
        if want.get((event, volume, c)) != photoelectrons:
            out.append(_finding("design.map_job_route", f"event {event}, volume {volume}, channel {chans[c]}: the job "
                                f"route gives {photoelectrons} photoelectrons, map_replica = {replica} gives "
                                f"{want.get((event, volume, c))}", event=event))
            break
    return out


def map_schema_findings(errors: list) -> dict:
    """D83 (1), approval A12: the schema errors of a built map (as {path, code, message}) with the single exemption of
    `form.uniformity`; the exemption is recorded as the known defect D83 (1)."""
    exempt = [e for e in errors if e.get("path") == UNIFORMITY_PATH and e.get("code") == "schema.additional"]
    rest = [e for e in errors if e not in exempt]
    return {"status": "failed" if rest else "passed", "findings": [{**e, "remedy": "plan"} for e in rest],
            "known_defects": ["D83 (1)"] if exempt else [],
            "note": "form.uniformity, written by g4sim_efficiency_map.py build, is not listed by efficiency-map/1 "
                    "(D83 (1)); the map is never rewritten to drop it" if exempt else None}
