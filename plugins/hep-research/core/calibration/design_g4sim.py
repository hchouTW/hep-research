"""The g4sim items of `calib_design.py` (Part B sections 6.1, 6.6, 11.4, 14.1; phase 3, WP-B): the support and recording
levels of section 6.1 for g4sim (the source of node 0 by `source-density/1`, generation-time filtering by the run card,
the request and the pipeline, recording levels), the event-interval check of section 6.6 with `run_seed` =
`logical_run_seed`, `replica` = 0 and the seed-block registry of section 14.1, the checks of every `g4sim-digi-job/1`
(section 6.6, built from and checked against the hashed documents), and one digitization path per readout system.

The implementation layer of the plan (section 11.4) is read here as (WP-B reading, to be reconciled with the node binding
of calib_chain.py):

    node_binding = {"nodes": {contract node: {"g4sim": "source" | "transport" | "stage:<name>" | "reconstruction",
                                              "recording": "column" | "event_file" | "moments"
                                                           | {"inputs": level, "outputs": level}}},
                    "parameters": {parameter: {"document": "request" | "detector" | "run" | "pipeline" | "conditions",
                                               "pointer": JSON Pointer of the value}},
                    "filters_ignorable": [{"filter": code, "reason": text}]}

Evaluation records (section 6.6 "Check"): plan["evaluations"] = [{run_id, use, set, logical_run_seed, first_event,
events, run_seed, replica, [scan, point | pair, efficiency_one], [digitization: {readout: "job" | "direct"}]}]; one (use,
set) is one batch of Geant4 events (re-digitized at several theta: common random numbers). Seed blocks (section 14.1):
plan["seed_blocks"] = [{block, logical_run_seed, t, m_blk, N_ev}]. Digitization jobs: plan["digi_jobs"] = [{job,
evaluation, readout, theta, map_replica, implementation}]. Event times (D87 (h)): plan["event_time"] = {kind: linear,
t0_ns, ns_per_event}. Every rejection has remedy level plan. Pure computation over loaded documents."""
from __future__ import annotations

import copy
import json
import math

from core.calibration import chain
from core.calibration.design import REWEIGHTING, CheckError, sobol_points
from core.simulation import digitize, efficiency_map, response, rng, seeds, source_density

RECORDED = ("column", "event_file")               # section 6.1: moments hold linear quantities only
LEVELS = RECORDED + ("moments",)
EVALUATED_FROM_RECORDS = frozenset(REWEIGHTING + ("rerun", "re-digitization"))
EVENT_SPACE = 2 ** 32                             # global event numbers under one logical_run_seed (section 14.1)
SENSOR_FIELDS = ("gain", "excess_noise", "dark_rate_per_ns", "gate_ns")
ELECTRONICS_FIELDS = ("noise_sigma", "threshold", "lsb", "bits")
JOB_FIELDS = ("readout", "channels", "stage", "efficiencies", "timing", "sensor", "electronics")


def _finding(code: str, message: str, **extra) -> dict:
    return {"code": code, "message": message, "remedy": "plan", **extra}


# ------------------------------------------------------------------ JSON Pointer bindings
def _segments(pointer: str) -> list:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise CheckError("binding.pointer", f"{pointer!r} is not a JSON Pointer")
    return [s.replace("~1", "/").replace("~0", "~") for s in pointer[1:].split("/")]


def pointer_get(document, pointer: str):
    node = document
    for s in _segments(pointer):
        try:
            node = node[int(s)] if isinstance(node, list) else node[s]
        except (KeyError, IndexError, ValueError, TypeError):
            raise CheckError("binding.pointer", f"{pointer} does not resolve") from None
    return node


def pointer_set(document, pointer: str, value):
    """A copy of `document` with the value at `pointer` replaced (the value must exist: a binding never adds fields)."""
    out = copy.deepcopy(document)
    parts = _segments(pointer)
    pointer_get(out, pointer)
    node = out
    for s in parts[:-1]:
        node = node[int(s)] if isinstance(node, list) else node[s]
    if isinstance(node, list):
        node[int(parts[-1])] = value
    else:
        node[parts[-1]] = value
    return out


def bindings(plan: dict) -> dict:
    return dict((plan.get("node_binding") or {}).get("parameters") or {})


def apply_theta(documents: dict, plan: dict, theta: dict) -> dict:
    """The documents with each theta value written at its binding (only the fields holding theta change, section 6.4).
    A value bound to a decimal string (detector-spec, run card, request) is written as a string."""
    out = dict(documents)
    for name, value in (theta or {}).items():
        b = bindings(plan).get(name)
        if b is None:
            continue
        doc = b["document"]
        if doc not in out:
            raise CheckError("binding.document", f"{name} binds to document {doc!r}, which is not given")
        old = pointer_get(out[doc], b["pointer"])
        out[doc] = pointer_set(out[doc], b["pointer"], _like(old, value))
    return out


def _like(old, value):
    if isinstance(old, str):                      # a decimal string of a specification (decimal/1 input grammar)
        return repr(float(value))
    if isinstance(old, int) and not isinstance(old, bool):
        return int(value)
    return float(value)


# ------------------------------------------------------------------ section 6.1: the source of node 0
def _energy_support(record: dict):
    e = record["energy"]
    if e["support"] == "discrete":
        return ("discrete", sorted(set(e["energies_MeV"])))
    if e["kind"] == "gaussian":
        return ("interval", e["low_MeV"], math.inf if e["high_MeV"] is None else e["high_MeV"])
    return ("interval", e["min_MeV"], e["max_MeV"])


def _contains(outer, inner) -> bool:
    if outer[0] == "discrete":
        return inner[0] == "discrete" and set(inner[1]) <= set(outer[1])
    if inner[0] == "discrete":
        return all(outer[1] <= v <= outer[2] for v in inner[1])
    return outer[1] <= inner[1] and inner[2] <= outer[2]


def source_support(request: dict, plan: dict, contract: dict, n_scan: int = 16, seed: int = 1) -> list:
    """Section 6.1 for node 0: q is the request's source with its `source-density/1`; the support of every theta' of
    the prior (vertices and Sobol points) must lie within supp q (a `gaussian` truncation range is its support). Only
    the energy has a density function in g4sim (`source_density.energy_density`): a theta bound to the position or
    direction is not reweightable."""
    out: list = []
    try:
        q = source_density.density(request["source"])
    except source_density.SourceError as exc:
        return [_finding("support.source_density", f"node 0 has no analytic density ({exc}); an external source is "
                         "rejected by calib_contract.py (section 5.2)")]
    sq = _energy_support(q)
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    for name, b in bindings(plan).items():
        if b.get("document") != "request" or name not in pars:
            continue
        if not b["pointer"].startswith("/source/energy/"):
            out.append(_finding("support.no_density_function", f"{name} binds to {b['pointer']}: source-density/1 gives "
                                "a density for the energy only, so it is not reweightable (next tier)", parameter=name))
            continue
        lo, hi = pars[name]["sampling_bounds"]
        for pt in [lo, hi] + [x[name] for x in sobol_points({name: [lo, hi]}, n_scan, seed)]:
            try:
                p = source_density.density(apply_theta({"request": request}, plan, {name: pt})["request"]["source"])
            except source_density.SourceError as exc:
                out.append(_finding("support.target_density", f"{name} = {pt}: {exc}", parameter=name))
                break
            if not _contains(sq, _energy_support(p)):
                out.append(_finding("support.missing", f"{name} = {pt}: the target energy support "
                                    f"{_energy_support(p)[1:]} is not within supp q {sq[1:]} (section 6.1)",
                                    parameter=name, node="source"))
                break
    return out


# ------------------------------------------------------------------ section 6.1: filtering at generation
def generation_filters(card: dict, request: dict, pipeline: dict | None) -> list:
    """The g4sim settings that filter at generation (section 6.1), each with the g4sim object where it acts."""
    out = []
    kp = card.get("kill_policy") or {}
    if kp.get("min_kinetic_energy_MeV") is not None:
        out.append({"filter": "kill_policy.min_kinetic_energy", "at": "transport", "value": kp["min_kinetic_energy_MeV"]})
    if kp.get("time_cut_ns") is not None:
        out.append({"filter": "kill_policy.time_cut", "at": "transport", "value": kp["time_cut_ns"]})
    if kp.get("kill_secondaries"):
        out.append({"filter": "kill_policy.kill_secondaries", "at": "transport", "value": kp["kill_secondaries"]})
    for s in request.get("scorers", []):
        if s.get("time_window_ns") is not None:
            out.append({"filter": f"scorer.time_window:{s['name']}", "at": "transport", "value": s["time_window_ns"]})
    keep = (request.get("truth") or {}).get("keep")
    if keep is not None and keep != ["all"]:
        out.append({"filter": "truth.pruning", "at": "transport", "value": keep})
    for st in (pipeline or {}).get("stages", []):
        if st["kind"] == "readout_external":
            out.append({"filter": f"zero_suppression:{st['name']}", "at": f"stage:{st['name']}", "value": None})
    return out


def _recording(plan: dict, node: str):
    nb = ((plan.get("node_binding") or {}).get("nodes") or {}).get(node) or {}
    r = nb.get("recording", plan.get("recording_level"))
    if isinstance(r, dict):
        return r.get("inputs"), r.get("outputs")
    return r, r


def _methods(plan: dict, contract: dict) -> dict:
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    return {p: m for p, m in (plan.get("methods") or {}).items() if p in pars}


def support_g4sim(contract: dict, plan: dict, documents: dict, n_scan: int = 16, seed: int = 1) -> dict:
    """Section 6.1 when g4sim is used: per parameter evaluated by reweighting, rerun or re-digitization, (i) the
    recording level of the inputs and outputs of each of its nodes is `column` or `event_file` (`moments`: infeasible);
    (ii) a generation-time filter acting at one of its nodes or downstream of it is missing support for that node and
    its observables, unless the plan records it as ignorable (to be confirmed by P0); (iii) the source support of node
    0. Returns the infeasible parameters (the next tier, section 3.6) with their findings."""
    graph = contract.get("stage_graph") or {"nodes": [], "edges": []}
    kids = chain.children_of(graph)
    nodes = (plan.get("node_binding") or {}).get("nodes") or {}
    where = {v.get("g4sim"): n for n, v in nodes.items()}
    ignorable = {f["filter"] for f in (plan.get("node_binding") or {}).get("filters_ignorable", []) if f.get("reason")}
    ignorable_nodes = {n for n, k in (plan.get("kernels") or {}).items() if k.get("filter_ignorable")}
    filters = generation_filters(documents.get("run") or {}, documents.get("request") or {}, documents.get("pipeline"))
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    per_par: dict = {}
    confirm = []

    def below(n):
        out, todo = {n}, [n]
        while todo:
            for c in kids.get(todo.pop(), []):
                if c not in out:
                    out.add(c)
                    todo.append(c)
        return out
    for p, m in sorted(_methods(plan, contract).items()):
        if m not in EVALUATED_FROM_RECORDS:
            continue
        fs = per_par.setdefault(p, [])
        for n in pars[p].get("nodes", []):
            for side, lvl in zip(("inputs", "outputs"), _recording(plan, n) if n != where.get("source") else ()):
                if lvl is None:
                    fs.append(_finding("support.recording_undeclared", f"{p}: the {side} of node {n} have no recording "
                                       "level in the plan (section 6.1)", parameter=p, node=n))
                elif lvl not in LEVELS:
                    raise CheckError("binding.recording", f"node {n}: recording level {lvl!r} is not one of {LEVELS}")
                elif lvl not in RECORDED:
                    fs.append(_finding("support.recording_moments", f"{p}: the {side} of node {n} are recorded as "
                                       "moments, which hold linear quantities only: reweighting or rerun is infeasible "
                                       "(section 6.1)", parameter=p, node=n))
            reach = below(n)
            for f in filters:
                fn = where.get(f["at"])
                if fn is None or fn not in reach:
                    continue
                if f["filter"] in ignorable or fn in ignorable_nodes:
                    confirm.append({"parameter": p, "filter": f["filter"], "node": fn})
                    continue
                fs.append(_finding("support.filtered", f"{p}: {f['filter']} filters at generation at node {fn}, at or "
                                   f"downstream of {n}: missing support for that node and its observables unless the "
                                   "plan records it as ignorable for every theta' (section 6.1)", parameter=p, node=fn,
                                   filter=f["filter"]))
    reweighted_source = [p for p, m in _methods(plan, contract).items() if m in REWEIGHTING
                         and bindings(plan).get(p, {}).get("document") == "request"]
    if reweighted_source:
        if documents.get("request") is None:
            raise CheckError("support.request", f"{reweighted_source} reweight node 0: the request is needed")
        for f in source_support(documents["request"], plan, contract, n_scan, seed):
            for p in ([f["parameter"]] if f.get("parameter") else reweighted_source):
                if p in reweighted_source:
                    per_par.setdefault(p, []).append(f)
    findings = [f for fs in per_par.values() for f in fs]
    return {"status": "failed" if findings else "passed", "findings": findings,
            "infeasible": sorted(p for p, fs in per_par.items() if fs), "filters": filters,
            "p0_confirms_ignorable_filters": confirm}


# ------------------------------------------------------------------ section 14.1: seed blocks
def block_seed(series: str, study: str, use: str, ensemble: str, b: int, registered=(), subset: str | None = None):
    """(S_b, t) of block b of (study, use, ensemble[, subset]): S_b = H(series, study, use, ensemble[, subset], b, t), t
    the smallest value giving a seed not yet registered (section 14.1, the allocation function)."""
    taken = set(registered)
    parts = [series, study, use, ensemble] + ([subset] if subset is not None else []) + [int(b)]
    t = 0
    while True:
        s = seeds.H(*parts, t)
        if s not in taken:
            return s, t
        t += 1


def member_interval(i: int, n_ev: int, m_blk: int) -> tuple[int, int]:
    """Member i of a block: the global event interval [i N_ev, (i + 1) N_ev), m_blk N_ev <= 2^32."""
    if m_blk * n_ev > EVENT_SPACE or not 0 <= i < m_blk:
        raise CheckError("design.block_size", f"member {i} of a block of {m_blk} x {n_ev} events")
    return i * n_ev, n_ev


def block_findings(blocks: list) -> list:
    out = []
    for blk in blocks:
        if int(blk["m_blk"]) * int(blk["N_ev"]) > EVENT_SPACE:
            out.append(_finding("design.block_size", f"block {blk['block']}: m_blk N_ev = {blk['m_blk']} x "
                                f"{blk['N_ev']} exceeds 2^32 (section 14.1)"))
    runs = [{"run_id": blk["block"], "seed": int(blk["logical_run_seed"])} for blk in blocks]
    for msg in seeds.seed_uniqueness_problems(runs):
        out.append(_finding("design.seed_collision", f"seed blocks: {msg} (section 6.6: H takes values in "
                            "[1, 2^31 - 1], so plan-derived seeds can collide)"))
    return out


# ------------------------------------------------------------------ section 6.6: event intervals
def _set_id(ev: dict, plan: dict):
    use = ev["use"]
    if use == "mapping-run":
        scan = ev.get("scan")
        shared = ((plan.get("mapping_scans") or {}).get(scan) or {}).get("seeding") == "shared"
        return (use, scan) if shared else (use, scan, ev.get("point", ev["run_id"]))
    if use == "pde-split-pair":
        return (use, ev.get("pair"))
    return (use, ev.get("set", ev["run_id"]))


def interval_findings(plan: dict) -> dict:
    """The check of section 6.6 on the plan's evaluation records. Two evaluations overlap only when they have the same
    `logical_run_seed` and intersecting global event intervals (D31). Rejected (remedy: plan): overlaps between uses
    and between independent sets of one use (one (use, set) is one batch: common random numbers); `run_seed` !=
    `logical_run_seed`; `replica` != 0; intervals beyond 2^32; colliding seed blocks. By design not overlaps: the
    mapping runs of a shared-seed theta scan, the two runs of a PDE split-check pair, and the efficiency-1 run of a
    pair that is the production mapping run (identical interval). G8 declared not run: `closure-not-tested`."""
    evs = list(plan.get("evaluations") or [])
    g8_run = (plan.get("g8") or {}).get("run", True)
    flags = [] if g8_run else ["closure-not-tested"]
    if not g8_run:
        evs = [e for e in evs if e["use"] not in ("G8", "G8-truth")]
    out = []
    for e in evs:
        try:
            rng.check_event_range(int(e["first_event"]), int(e["events"]))
        except rng.RngError:
            out.append(_finding("design.event_range", f"{e['run_id']}: [{e['first_event']}, +{e['events']}) exceeds "
                                "2^32 global event numbers"))
        if "run_seed" in e and int(e["run_seed"]) != int(e["logical_run_seed"]):
            out.append(_finding("design.run_seed", f"{e['run_id']}: response-pipeline/1 run_seed {e['run_seed']} != "
                                f"logical_run_seed {e['logical_run_seed']} (section 6.6)"))
        if int(e.get("replica", 0)) != 0:
            out.append(_finding("design.replica", f"{e['run_id']}: replica {e['replica']} != 0 (section 6.6: a "
                                "non-zero replica changes a mapped map, and keys stay those of the nominal digitization)"))
    by_seed: dict = {}
    for e in evs:
        by_seed.setdefault(int(e["logical_run_seed"]), []).append(e)
    ones = {(int(e["logical_run_seed"]), int(e["first_event"]), int(e["events"])): _set_id(e, plan) for e in evs
            if e["use"] == "pde-split-pair" and e.get("efficiency_one")}
    sid = {}
    for e in evs:                                 # the production mapping run that is a pair's efficiency-1 run
        k = (int(e["logical_run_seed"]), int(e["first_event"]), int(e["events"]))
        sid[e["run_id"]] = ones[k] if e["use"] == "mapping-run" and k in ones else _set_id(e, plan)
    seen = set()
    for s, group in by_seed.items():
        group.sort(key=lambda e: int(e["first_event"]))
        for i, a in enumerate(group):
            a1 = int(a["first_event"]) + int(a["events"])
            for b in group[i + 1:]:
                b0 = int(b["first_event"])
                if b0 >= a1:
                    break
                sa, sb = sid[a["run_id"]], sid[b["run_id"]]
                if sa == sb:
                    continue
                key = tuple(sorted((repr(sa), repr(sb))))
                if key in seen:
                    continue
                seen.add(key)
                code = "design.interval_overlap_uses" if a["use"] != b["use"] else "design.interval_overlap_sets"
                if "G8" in (a["use"], b["use"]):
                    code = "design.g8_interval_overlap"
                out.append(_finding(code, f"{a['run_id']} ({'/'.join(map(str, sa))}) and {b['run_id']} "
                                    f"({'/'.join(map(str, sb))}) share logical_run_seed {s} and events "
                                    f"[{b0}, {min(a1, b0 + int(b['events']))}): not independent (changing only the "
                                    "response is not a new seed, section 6.6)", runs=[a["run_id"], b["run_id"]]))
    out += block_findings(plan.get("seed_blocks") or [])
    out += path_findings(evs)
    return {"status": "failed" if out else "passed", "findings": out, "flags": flags,
            "evaluations": len(evs), "seeds": len(by_seed)}


def path_findings(evs: list) -> list:
    """One digitization path within a readout system (section 6.6, accepted 2026-11-09): all evaluations of one
    ensemble (use) and all re-digitizations of one batch of events use the job path or the direct path, not both."""
    out: list = []
    groups: dict = {}
    for e in evs:
        for readout, path in (e.get("digitization") or {}).items():
            if path not in ("job", "direct"):
                raise CheckError("design.digitization_path", f"{e['run_id']}: path {path!r} is job or direct")
            groups.setdefault(("use", readout, e["use"]), set()).add(path)
            groups.setdefault(("batch", readout, int(e["logical_run_seed"]), int(e["first_event"])), set()).add(path)
    for g, paths in sorted(groups.items(), key=lambda x: str(x[0])):
        if len(paths) > 1:
            out.append(_finding("design.digi_mixed_paths", f"readout {g[1]}: {g[0]} {g[2:]} is digitized on both the "
                                "g4sim-digi-job/1 path and the direct path, whose channel-stream counters differ, so the "
                                "two share no sensor or electronics noise (section 6.6)"))
    return out


# ------------------------------------------------------------------ g4sim-digi-job/1 (sections 5.1, 6.6, D83 (9), D87 (h))
def event_times(rule, first_event: int, events: int) -> dict:
    """event_time_ns of a job: the plan's rule (D87 (h)) applied to its event interval; only the linear rule
    t = t0_ns + ns_per_event x global event number is defined here."""
    if not isinstance(rule, dict) or rule.get("kind") != "linear":
        raise CheckError("design.event_time_rule", "the plan's event_time rule is {kind: linear, t0_ns, ns_per_event}")
    t0, step = int(rule["t0_ns"]), int(rule["ns_per_event"])
    return {str(e): t0 + step * e for e in range(int(first_event), int(first_event) + int(events))}


def _stage(pipeline: dict, kind: str, readout: str) -> dict:
    found = [s for s in pipeline["stages"] if s["kind"] == kind and s.get("readout") in (None, readout)]
    if len(found) != 1:
        raise CheckError("design.digi_pipeline", f"the pipeline has {len(found)} {kind} stages for readout {readout}")
    return found[0]


def _value(stage: dict, name: str):
    p = stage["parameters"].get(name)
    if p is None:
        raise CheckError("design.digi_pipeline", f"stage {stage['name']} has no parameter {name}")
    return p["value"]


def job_from_documents(pipeline: dict, map_document: dict, readout: str, bins, run_seed: int, *,
                       map_replica: int = 0, conditions: dict | None = None, event_time: dict | None = None,
                       interval: tuple | None = None) -> dict:
    """The `g4sim-digi-job/1` of one readout built from the hashed documents (the pipeline with theta applied, the map
    and its replica, the snapshot): run_seed = logical_run_seed, replica = 0; per bin the map's efficiencies (replica
    `map_replica`); the scintillation stage, the sensor and the electronics stages with the job's field names; timing
    when the scintillation stage declares `decay_ns` (transit from a mapped map's arrival times, otherwise the
    stage's `transit_ns`). With a snapshot, `conditions` and `event_time_ns` from the plan's rule over `interval`."""
    sc = _stage(pipeline, "scintillation", readout)
    se = _stage(pipeline, "sensor", readout)
    el = _stage(pipeline, "electronics", readout)
    stage = {"name": sc["name"], "light_yield_per_MeV": _value(sc, "light_yield_per_MeV"),
             "resolution_scale": _value(sc, "resolution_scale")}
    if "yield_relative_width" in sc["parameters"]:
        stage["yield_relative_width"] = _value(sc, "yield_relative_width")
    try:
        eff = {str(int(b)): response.efficiencies(map_document, int(b), map_replica) for b in sorted(set(bins), key=int)}
    except response.ResponseError as exc:
        raise CheckError("design.digi_map", str(exc)) from None
    timing = None
    if "decay_ns" in sc["parameters"]:
        mapped = map_document["form"]["kind"] == efficiency_map.FORM and "transit_edges_ns" in map_document["form"]
        if mapped:
            transit = {"kind": "mapped", "edges_ns": map_document["form"]["transit_edges_ns"],
                       "counts": {str(r["bin"]): r["transit_counts"] for r in map_document["form"]["bins"]
                                  if str(r["bin"]) in eff}}
        else:
            transit = {"kind": "exponential", "transit_ns": _value(sc, "transit_ns")}
        timing = {"decay_ns": _value(sc, "decay_ns"), "transit": transit}
        if "rise_ns" in sc["parameters"]:
            timing["rise_ns"] = _value(sc, "rise_ns")
    job = {"schema": digitize.SCHEMA, "run_seed": int(run_seed), "replica": 0, "readout": readout,
           "channels": list(map_document["channels"]), "stage": stage, "efficiencies": eff, "timing": timing,
           "sensor": {"name": se["name"], **{k: _value(se, k) for k in SENSOR_FIELDS}},
           "electronics": {"name": el["name"], **{k: _value(el, k) for k in ELECTRONICS_FIELDS}}}
    if conditions is not None:
        if event_time is None or interval is None:
            raise CheckError("design.event_time_rule", "a job with conditions needs the plan's event-time rule")
        job["conditions"] = conditions
        job["event_time_ns"] = event_times(event_time, *interval)
    return job


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def digi_job_findings(plan: dict, documents: dict) -> list:
    """Every `g4sim-digi-job/1` of the plan (section 6.6): run_seed = its evaluation's logical_run_seed; replica = 0;
    a job without conditions whose keys (if any) equal digitize.job_with_keys of the job, and keys present when it runs
    in g4sim_digi; a job with conditions without keys and digitized in Python only (D83 (9)), with event_time_ns the
    plan's rule over its interval (D87 (h)); and its stage, sensor, electronics, timing, channels and efficiencies those
    built from the hashed documents (the pipeline at the entry's theta, the map at its replica, the snapshot; section
    5.1). documents = {pipeline, maps: {name: map}, conditions: snapshot or None}."""
    evs = {e["run_id"]: e for e in plan.get("evaluations") or []}
    out = []
    for i, entry in enumerate(plan.get("digi_jobs") or []):
        job = entry["job"]
        where = f"digi_jobs[{i}]"
        ev = evs.get(entry.get("evaluation"))
        if ev is None:
            out.append(_finding("design.digi_evaluation", f"{where}: no evaluation record {entry.get('evaluation')!r}"))
            continue
        if int(job.get("run_seed", -1)) != int(ev["logical_run_seed"]):
            out.append(_finding("design.digi_run_seed", f"{where}: run_seed {job.get('run_seed')} != logical_run_seed "
                                f"{ev['logical_run_seed']} of {ev['run_id']}"))
        if int(job.get("replica", -1)) != 0:
            out.append(_finding("design.digi_replica", f"{where}: replica {job.get('replica')} != 0"))
        impl = entry.get("implementation", "python")
        if "conditions" in job:
            if "keys" in job:
                out.append(_finding("design.digi_keys_with_conditions", f"{where}: a job with conditions carries keys "
                                    "(job_with_keys refuses it; g4sim_digi would ignore its conditions, D83 (9))"))
            if impl != "python":
                out.append(_finding("design.digi_conditions_not_python", f"{where}: a job with conditions is digitized "
                                    f"by core/simulation/digitize.py only, not {impl} (D83 (9))"))
            try:
                want = event_times(plan.get("event_time"), ev["first_event"], ev["events"])
            except CheckError as exc:
                out.append(_finding(exc.code, f"{where}: {exc}"))
            else:
                if job.get("event_time_ns") != want:
                    out.append(_finding("design.digi_event_time", f"{where}: event_time_ns is not the plan's event-time "
                                        f"rule over [{ev['first_event']}, +{ev['events']}) (D87 (h))"))
        else:
            if "keys" in job:
                bare = {k: v for k, v in job.items() if k != "keys"}
                fresh = digitize.job_with_keys(bare, blocks=len(job["keys"].get("time_blocks", [])) or digitize.TIME_BLOCKS)
                if not _same(fresh["keys"], job["keys"]):
                    out.append(_finding("design.digi_stale_keys", f"{where}: keys differ from those job_with_keys "
                                        "computes from the job's run_seed and replica (a seed edited without "
                                        "recomputing the keys runs with stale streams)"))
            elif impl == "g4sim_digi":
                out.append(_finding("design.digi_keys_missing", f"{where}: g4sim_digi needs the precomputed keys"))
        try:
            maps = documents.get("maps") or {}
            if entry.get("map") not in maps:
                raise CheckError("design.digi_map", f"no map {entry.get('map')!r} among the hashed documents")
            pipe = apply_theta({"pipeline": documents["pipeline"]}, plan, entry.get("theta") or {})["pipeline"]
            want_job = job_from_documents(pipe, maps[entry["map"]], entry.get("readout", job.get("readout")),
                                          list(job.get("efficiencies", {})), ev["logical_run_seed"],
                                          map_replica=int(entry.get("map_replica", 0)))
        except CheckError as exc:
            out.append(_finding(exc.code, f"{where}: {exc}"))
            continue
        bad = [f for f in JOB_FIELDS if not _same(job.get(f), want_job.get(f))]
        if "conditions" in job and not _same(job["conditions"], documents.get("conditions")):
            bad.append("conditions")
        if bad:
            out.append(_finding("design.digi_documents", f"{where}: {', '.join(bad)} differ from the hashed documents "
                                "(section 5.1)", fields=bad))
    return out
