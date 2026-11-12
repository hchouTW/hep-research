"""Stage graph, candidate methods and reference coverage (Part B sections 3.1, 3.4, 3.6; gate P4; owner
calib_chain.py).

The semantic layer (contract): stage_graph {nodes, edges}, parameters[] (name, role, nodes) and references[] (type,
edge, observation). The implementation layer (plan): kernels {node: {stored: {inputs, outputs, steps},
support_declared}}. A reference lies on an edge, written {"from": a, "to": b} for an edge between two nodes,
{"into": root} for the edge flowing into a root node, or {"out_of": node} for the output edge of an observation node.

Checks owned here (section 14): the DAG and injection-point splitting (with the comparison nodes of redundant
measurements, section 3.4), candidate methods (section 3.6; from section 11.4 Table 2 when g4sim is used, phase 3),
and the directed reachability condition (P4). Standard library only.
"""
from __future__ import annotations

import re

KERNELS = ("density", "deterministic", "black-box")
NODE_KINDS = ("stage", "observation", "comparison")
REFERENCE_TYPES = ("known-input", "mid-chain-injection", "internal-constraint", "redundant-measurement",
                   "population-feature", "tag-and-probe")
# Cost tiers of section 3.6, cheapest first.
METHOD_TIER = {"analytic-reweighting": "low", "step-level-reweighting": "low", "learned-density-ratio": "low",
               "rerun": "medium", "resimulation": "high", "surrogate-model": "high"}
METHOD_ORDER = tuple(METHOD_TIER)


def _finding(code, path, message):
    return {"code": code, "path": path, "message": message}


def node_index(graph: dict) -> dict:
    return {n["id"]: n for n in graph.get("nodes", []) if isinstance(n, dict) and "id" in n}


def parents_of(graph: dict) -> dict:
    out: dict[str, list] = {n: [] for n in node_index(graph)}
    for e in graph.get("edges", []):
        out.setdefault(e["to"], []).append(e["from"])
    return out


def children_of(graph: dict) -> dict:
    out: dict[str, list] = {n: [] for n in node_index(graph)}
    for e in graph.get("edges", []):
        out.setdefault(e["from"], []).append(e["to"])
    return out


def check_graph(graph) -> list[dict]:
    """Section 3.1 and 5.2 `stage_graph`: nodes declared once with a kernel nature, edges between declared nodes, no
    cycle; a comparison node has exactly two upstream observation nodes (section 5.2 clause 4)."""
    out: list[dict] = []
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        return [_finding("graph.shape", "$.stage_graph", "a stage graph has lists 'nodes' and 'edges'")]
    ids: list = [n.get("id") for n in graph["nodes"] if isinstance(n, dict)]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        out.append(_finding("graph.duplicate_node", "$.stage_graph.nodes", f"node {dup!r} declared twice"))
    nodes = node_index(graph)
    for i, n in enumerate(graph["nodes"]):
        p = f"$.stage_graph.nodes[{i}]"
        if n.get("kernel") not in KERNELS:
            out.append(_finding("graph.kernel_nature", p, f"node {n.get('id')!r} must declare its kernel nature "
                                f"({', '.join(KERNELS)})"))
        if n.get("kind", "stage") not in NODE_KINDS:
            out.append(_finding("graph.node_kind", p, f"node kind must be one of {list(NODE_KINDS)}"))
    seen_edges = set()
    for i, e in enumerate(graph["edges"]):
        p = f"$.stage_graph.edges[{i}]"
        if e.get("from") not in nodes or e.get("to") not in nodes:
            out.append(_finding("graph.edge_endpoint", p, f"edge {e.get('from')!r} -> {e.get('to')!r} names an "
                                "undeclared node"))
        elif (e["from"], e["to"]) in seen_edges:
            out.append(_finding("graph.duplicate_edge", p, "edge declared twice"))
        seen_edges.add((e.get("from"), e.get("to")))
    if out:
        return out
    cyc = _cycle(graph)
    if cyc:
        out.append(_finding("graph.cycle", "$.stage_graph.edges", "the stage graph must be a DAG; cycle "
                            + " -> ".join(cyc)))
    pa = parents_of(graph)
    for nid, n in nodes.items():
        if n.get("kind") == "comparison":
            ups = pa.get(nid, [])
            if len(ups) != 2 or any(nodes[u].get("kind") != "observation" for u in ups):
                out.append(_finding("graph.comparison_upstream", f"$.stage_graph.nodes[{nid}]",
                                    f"comparison node {nid!r} must have exactly two upstream observation nodes, "
                                    f"not {ups}"))
    return out


def _cycle(graph: dict):
    ch = children_of(graph)
    state: dict[str, int] = {}
    for start in sorted(ch):
        if state.get(start):
            continue
        stack, path = [(start, iter(ch[start]))], [start]
        state[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                state[node] = 2
                stack.pop()
                path.pop()
            elif state.get(nxt) == 1:
                return path[path.index(nxt):] + [nxt]
            elif not state.get(nxt):
                state[nxt] = 1
                stack.append((nxt, iter(ch[nxt])))
                path.append(nxt)
    return None


def edge_kind(edge) -> str | None:
    if not isinstance(edge, dict):
        return None
    if set(edge) == {"from", "to"}:
        return "between"
    if set(edge) == {"into"}:
        return "into"
    if set(edge) == {"out_of"}:
        return "out_of"
    return None


def check_references(graph: dict, references) -> list[dict]:
    """Injection-point splitting (section 3.1) and the placement rules of section 3.4: a mid-chain injection lies on
    an edge between two declared nodes (an injection inside a node means the node was not split); a known input on
    the edge into a root; a redundant measurement on the output edge of a comparison node; every reference names its
    observation node."""
    out: list[dict] = []
    nodes = node_index(graph)
    pa = parents_of(graph)
    edges = {(e["from"], e["to"]) for e in graph.get("edges", [])}
    for i, r in enumerate(references or []):
        p = f"$.references[{i}]"
        t, e, kind = r.get("type"), r.get("edge"), edge_kind(r.get("edge"))
        if t not in REFERENCE_TYPES:
            out.append(_finding("reference.type", p, f"reference type must be one of {list(REFERENCE_TYPES)}"))
            continue
        obs = r.get("observation")
        if nodes.get(obs, {}).get("kind") not in ("observation", "comparison"):
            out.append(_finding("reference.observation", p, f"observation {obs!r} is not an observation or "
                                "comparison node"))
        if t == "mid-chain-injection":
            if isinstance(e, dict) and "inside" in e:
                out.append(_finding("reference.injection_not_split", p, f"injection point inside node "
                                    f"{e['inside']!r}: split the node so that the injection falls on an edge "
                                    "(section 3.1)"))
            elif kind != "between" or (e["from"], e["to"]) not in edges:
                out.append(_finding("reference.injection_not_split", p, "a mid-chain injection lies on an edge "
                                    "between two declared nodes of the stage graph (section 3.1)"))
        elif t == "known-input":
            if kind != "into" or e["into"] not in nodes or pa.get(e["into"]):
                out.append(_finding("reference.known_input_edge", p, "a known input lies on the edge flowing into a "
                                    "root node (section 3.4)"))
        elif t == "redundant-measurement":
            if kind != "out_of" or nodes.get(e["out_of"], {}).get("kind") != "comparison" or e["out_of"] != obs:
                out.append(_finding("reference.redundant_without_comparison", p, "a redundant measurement is declared "
                                    "with a comparison node and lies on its output edge (section 5.2 clause 4)"))
        else:
            if kind is None or (kind == "between" and (e["from"], e["to"]) not in edges) or (
                    kind in ("into", "out_of") and next(iter(e.values())) not in nodes):
                out.append(_finding("reference.edge", p, "the reference names an edge of the stage graph"))
    return out


# ------------------------------------------------------------------ directed reachability (P4)
def _reaches(graph: dict, s: str, o: str, skip: tuple | None) -> bool:
    """A directed path from s to o that does not pass through edge `skip` (a (from, to) pair); s == o is a path."""
    ch = children_of(graph)
    seen, todo = {s}, [s]
    while todo:
        n = todo.pop()
        if n == o:
            return True
        for m in ch.get(n, ()):
            if (n, m) != skip and m not in seen:
                seen.add(m)
                todo.append(m)
    return False


def ancestors(graph: dict, o: str) -> set[str]:
    pa = parents_of(graph)
    out, todo = set(), [o]
    while todo:
        for p in pa.get(todo.pop(), ()):
            if p not in out:
                out.add(p)
                todo.append(p)
    return out


def can_constrain(graph: dict, reference: dict, node: str) -> bool:
    """Section 3.4: a parameter on `node` can possibly be constrained by `reference` through its observation node o
    only if (1) the reference edge e is upstream of o, or is the output edge of o, and (2) there is a directed path
    from the node to o that does not pass through e. A necessary condition only; P3 and G5 decide identifiability."""
    e, o = reference["edge"], reference["observation"]
    kind = edge_kind(e)
    up = ancestors(graph, o) | {o}
    if kind == "out_of":
        cond1, skip = e["out_of"] == o, None
    elif kind == "into":
        cond1, skip = e["into"] in up, None
    else:
        cond1, skip = e["to"] in up, (e["from"], e["to"])
    return cond1 and _reaches(graph, node, o, skip)


def p4(contract: dict) -> dict:
    """Gate P4 (reference coverage): each theta can possibly be constrained by at least one enabled reference.
    Returns {"status": "passed"|"failed", "parameters": {name: [reference ids]}, "unconstrainable": [...]}.
    Remedy level: contract (add a reference)."""
    graph = contract["stage_graph"]
    refs = [r for r in contract.get("references", []) if r.get("enabled", True)]
    out, bad = {}, []
    for par in contract.get("parameters", []):
        if par.get("role") != "theta":
            continue
        by = sorted(r["id"] for r in refs if any(can_constrain(graph, r, n) for n in par["nodes"]))
        out[par["name"]] = by
        if not by:
            bad.append(par["name"])
    return {"gate": "P4", "status": "failed" if bad else "passed", "parameters": out, "unconstrainable": bad,
            "remedy_level": "contract" if bad else None}


# ------------------------------------------------------------------ candidate methods (section 3.6)
def node_candidates(node: dict, kernel_plan: dict) -> set[str]:
    """Candidate methods for a parameter acting on one node, from the node's kernel nature (contract) and its stored
    products (plan)."""
    stored = kernel_plan.get("stored", {})
    out = set()
    k = node.get("kernel")
    if k == "density" and stored.get("inputs") and stored.get("outputs") and kernel_plan.get("support_declared"):
        out.add("analytic-reweighting")
    if "physics-process" in node.get("mechanisms", ()) and stored.get("steps"):
        out.add("step-level-reweighting")
    if k != "density" and node.get("post_hoc_correction") and stored.get("inputs") and stored.get("outputs"):
        out.add("learned-density-ratio")                        # phase 5; G4-L applies
    if k == "deterministic" and stored.get("inputs"):
        out.add("rerun")
    if k == "black-box" and node.get("samplable") and stored.get("inputs"):
        out |= {"resimulation", "surrogate-model"}
    if k == "density" and node.get("samplable") and stored.get("inputs"):
        # rerunning a density kernel from its stored inputs with new random numbers is resimulation of that node:
        # the next tier when reweighting is infeasible (section 3.6, 15.3.1; phase-1 reading, reported)
        out.add("resimulation")
    return out


def candidate_methods(contract: dict, plan: dict) -> dict:
    """Candidate methods per parameter (section 3.6 step 1; the final method is P5's, calib_design.py). A parameter
    acting on several nodes takes the methods every one of its nodes allows. With g4sim (a plan with node_binding),
    candidates come from section 11.4 Table 2 (g4sim_candidates)."""
    if plan.get("node_binding"):
        return g4sim_candidates(contract, plan)
    nodes = node_index(contract["stage_graph"])
    kernels = plan.get("kernels", {})
    out = {}
    for par in contract.get("parameters", []):
        sets = [node_candidates(nodes[n], kernels.get(n, {})) for n in par["nodes"]]
        common = set.intersection(*sets) if sets else set()
        out[par["name"]] = [{"method": m, "tier": METHOD_TIER[m]} for m in METHOD_ORDER if m in common]
    none = sorted(p for p, ms in out.items() if not ms)
    return {"status": "ok" if not none else "failed", "parameters": out, "without_candidate": none}


# ------------------------------------------------------------------ the g4sim binding (section 11.4, phase 3)
# Table 1: abstract node -> g4sim object and the kernel property it must have (None: depends on the stage).
TABLE1 = {"0": ("source", "density"), "1": ("g4sim_run", "black-box"), "2": ("response:quanta", "density"),
          "3": ("response:transport", None), "4a": ("conversion", "density"), "4b": ("response:sensor", None),
          "5e": ("response:electronics", None), "5r": ("response:readout", None),
          "6-7": ("reconstruction", "deterministic")}
RECORDED = ("column", "event_file")         # section 6.1: moments hold linear quantities only
REWEIGHTABLE = ("poisson", "binomial", "multinomial")
NO_HANDOFF_BEFORE = ("2", "3", "4a", "4b")  # the hand-offs are 3->4 and 4->5 only (section 19): no stored input
RECORDED_OVERLAY_RUN = False                # D83 (7): geant4_run.py run-spec takes no overlay (section 19, C25)
DISCRETE_RUN_FIELDS = ("/physics/reference_list", "/physics/em_option", "/physics/em_constructor",
                       "/physics/extra_constructors", "/physics/fast_sim")
_PIPE_VALUE = re.compile(r"^/stages/(\d+)/parameters/([^/]+)/value$")
_SNAPSHOT = re.compile(r"^/iovs/\d+/rows/\d+/([^/]+)$")
_OVERLAY = re.compile(r"^/shifts/\d+/(delta_mm|rotation/zyx_deg)/[0-2]$")
_MATERIAL = re.compile(r"^/materials/([^/]+)/(.*)$")
WEIGHTED = ("analytic-reweighting", "step-level-reweighting", "learned-density-ratio")


def _bf(code, path, message):
    return {"code": "binding." + code, "path": path, "message": message}


def binding_row(binding: dict) -> tuple[str | None, str | None]:
    """(Table 2 row, refusal message) of one field binding {document, pointer} (section 11.4 Table 2, D86, D87)."""
    doc, ptr = binding.get("document"), str(binding.get("pointer", ""))
    if doc == "simulation-request":
        return ("source", None) if ptr.startswith("/source/") else (None, "a request field outside the source is "
                                                                    "in no row of Table 2")
    if doc == "detector-spec":
        m = _MATERIAL.match(ptr)
        if m and m.group(2) == "ionisation/birks_mm_per_MeV":
            return "birks", None
        if m and m.group(2) in ("scintillation/yield_per_MeV", "scintillation/resolution_scale"):
            return None, ("LY and RESOLUTIONSCALE bind to light_yield_per_MeV and resolution_scale of the scintillation "
                          "stage of response-pipeline/1; the detector-spec material fields stay nominal (Table 2, A5)")
        if m and m.group(2).startswith("scintillation/"):
            return None, "a scintillation field other than the Birks constant, LY and r is in no row of Table 2"
        if (m and m.group(2).startswith("optical/")) or ptr.startswith("/optical_surfaces/"):
            return "optical", None
        return "geometry", None
    if doc == "run-card":
        if ptr.split("/")[1:2] in (["run"], ["output"]):
            return None, "the run and output blocks are outside the model identity (section 5.1)"
        if ptr.startswith(DISCRETE_RUN_FIELDS):
            return None, ("a physics list, EM option or fast-simulation model is a discrete model M, never a theta "
                          "(Table 2)")
        return "geometry", None
    if doc == "response-pipeline":
        m = _PIPE_VALUE.match(ptr)
        if not m:
            return None, ("a pipeline binding is a stage parameter's value, /stages/<i>/parameters/<name>/value; "
                          "run_seed and replica are seeds (section 5.1)")
        return ("ly" if m.group(2) in ("light_yield_per_MeV", "resolution_scale") else "response"), None
    if doc == "condition-snapshot":
        m = _SNAPSHOT.match(ptr)
        if m and m.group(1) in ("gain_factor", "threshold"):
            return "conditions", None
        if m and m.group(1) == "dead":
            return None, "dead is discrete: ψ only, a different dead-channel set is a different model (D87 (d))"
        if m and m.group(1) == "temperature_K":
            return None, "temperature_K has no role: no g4sim stage reads it (D87 (e))"
        return None, "a snapshot binding is /iovs/<k>/rows/<j>/<quantity> (D87)"
    if doc == "alignment-overlay":
        return ("misalignment", None) if _OVERLAY.match(ptr) else (None, "an overlay binding is an entry of "
                                                                     "delta_mm or rotation/zyx_deg (D87 (f))")
    if doc == "reconstruction":
        return "reconstruction", None
    if doc == "evaluator":
        return "evaluator", None
    return None, f"document {doc!r} is not one of the g4sim documents"


def binding_findings(contract: dict) -> list[dict]:
    """Contract-level rules of the binding (section 5.1, 11.4, D86, D87): each theta and phi of a g4sim contract is
    bound to at least one field; each binding lies in a row of Table 2; a theta on the snapshot is conditioned
    piecewise-independently on its IOVs (D87 (c)). Called by calib_contract.py check."""
    out: list[dict] = []
    if contract.get("simulator") != "g4sim":
        return out
    for i, par in enumerate(contract.get("parameters", [])):
        path = f"$.parameters[{i}]"
        binds = par.get("bindings") or []
        if par.get("role") in ("theta", "phi") and not binds:
            out.append(_bf("unbound", path, f"{par.get('name')!r} is bound to no specification field: the mask list "
                           "is locked with the binding of parameters to the fields (section 5.1)"))
        for j, b in enumerate(binds):
            row, why = binding_row(b)
            if row is None:
                out.append(_bf("not_in_table_2", f"{path}.bindings[{j}]", why or ""))
            elif row == "conditions" and par.get("role") == "theta" \
                    and (par.get("index") or {}).get("conditioning") != "piecewise-independent":
                out.append(_bf("conditions_structure", path, "a theta on condition-snapshot rows is conditioned "
                               "piecewise-independently on the snapshot's IOVs (D87 (c), section 3.7)"))
    return out


def _entry(method, form, preconditions):
    return {"method": method, "tier": METHOD_TIER[method], "form": form, "event_weights": method in WEIGHTED,
            "preconditions": preconditions}


def _row_methods(row, par, nb, contract, plan) -> tuple[list, list]:
    """(candidates, excluded) of one Table 2 row for a parameter whose nodes carry the bindings nb."""
    stored = set().union(*[set(b.get("stored", [])) for b in nb]) if nb else set()
    recorded = all(b.get("recording", plan.get("recording_level")) in RECORDED for b in nb) if nb else False
    fast = (plan.get("node_binding") or {}).get("fast_sim_envelope") or {}
    cand, excl = [], []

    def need_record(method, form, quantity, pre):
        if not recorded:
            excl.append({"method": method, "reason": "recorded only as moments (or undeclared): reweighting and rerun "
                         "need column or event_file (section 6.1)"})
        elif quantity and quantity not in stored:
            excl.append({"method": method, "reason": f"{quantity} is not recorded (section 6.3)"})
        else:
            cand.append(_entry(method, form, pre))
    if row == "source":
        if (contract.get("source") or {}).get("density") != "analytic":
            excl.append({"method": "analytic-reweighting", "reason": "the source is not density: analytic"})
        elif not all(b.get("support_declared") for b in nb):
            excl.append({"method": "analytic-reweighting", "reason": "no declared support (section 6.1)"})
        else:
            need_record("analytic-reweighting", "source-density/1", None, ["support condition (section 6.1)"])
    elif row in ("geometry", "optical"):
        pre = ["a new geometry_id or run card for each design point"]
        if row == "optical":
            pre.append("the mapping run of each design point redone; production run resimulated (map-stale, S7)")
        cand += [_entry("resimulation", "g4sim_run", pre), _entry("surrogate-model", "g4sim_run", pre)]
    elif row == "birks":
        found = _MATERIAL.match(_binding(par, "detector-spec"))
        mat = found.group(1) if found else None
        if mat in fast.get("materials", []):
            excl.append({"method": "rerun", "reason": "the material lies inside a fast_sim_envelope: a model deposit "
                         "is a zero-length step, edep_visible ~ 0 (C29, D83 (12))"})
        else:
            need_record("rerun", "deterministic-rerun from edep_by_dedx_class (D75: no event weights, G4 does not "
                        "apply)", "edep_by_dedx_class", ["discretization bound k_B(b-a)/(1+k_B a) (section 5.4; "
                        "the evaluator calls reweighting_bound)", "the detector-spec Birks constant stays nominal; "
                        "only the full-simulation spot checks of section 5.4 write a new k_B"])
    elif row == "ly":
        stages = {b.get("stage") for b in nb}
        if stages & set(fast.get("stages", [])):
            excl.append({"method": "rerun", "reason": "the stage's volumes lie inside a fast_sim_envelope: no "
                         "scintillation parameter can be calibrated there (C29, D83 (12))"})
        else:
            need_record("rerun", "re-digitization", "edep_visible_ly_split", ["r within the valid range (section "
                        "5.4)"])
            only_ly = all(str(b.get("pointer", "")).endswith("/light_yield_per_MeV/value")
                          for b in par.get("bindings", []) if b.get("document") == "response-pipeline")
            if cand and only_ly and all(b.get("poisson_interval_only") for b in nb):
                cand.insert(0, _entry("analytic-reweighting", "LY only, Poisson interval only", []))
    elif row == "response":
        handoff = all(b.get("table1") not in NO_HANDOFF_BEFORE for b in nb)
        density = all(b.get("distribution") in REWEIGHTABLE for b in nb)
        if density and handoff and {"handoff_inputs", "handoff_outputs"} <= stored and recorded:
            cand.append(_entry("analytic-reweighting", "stage hand-off file (3->4, 4->5)", []))
        elif density:
            excl.append({"method": "analytic-reweighting", "reason": "the stage's inputs and outputs are not both "
                         "stored in a hand-off; there is none before stage 3 (section 19)"})
        if "hits" in stored or "handoff_inputs" in stored:
            need_record("rerun", "re-digitization", None, ["nodes 3 and 4a re-digitized as a whole from the hit "
                        "file (section 11.4)"])
        else:
            excl.append({"method": "rerun", "reason": "no hit file or stage hand-off recorded"})
    elif row == "conditions":
        if "hits" in stored:
            need_record("rerun", "re-digitization (Python only: g4sim_digi ignores conditions, C24, D83 (9))", None,
                        ["exact common random numbers"])
        else:
            excl.append({"method": "rerun", "reason": "no hit file recorded"})
    elif row == "reconstruction":
        need_record("rerun", "deterministic rerun from the simreco column file", "simreco_columns", [])
    return cand, excl


def _binding(par, document):
    return next(b["pointer"] for b in par.get("bindings", []) if b.get("document") == document)


def g4sim_findings(contract: dict, plan: dict) -> list[dict]:
    """Plan-level rules of section 11.4: Table 1 objects and kernel properties of the bound nodes; no injection
    reference with a known photon count between light collection and PDE (edge 3/4a) unless the PDE split of section
    6.7 is declared, and no single-photoelectron injection (edge into 4b: no hand-off before stage 3, section 19);
    a misaligned geometry has no recorded run (D83 (7)), and a plan that varies alignment applies an overlay at every
    design point, the nominal one included (D86)."""
    out = []
    if contract.get("simulator") != "g4sim":
        out.append(_bf("simulator", "$.plan.node_binding", "a g4sim node binding needs a contract with simulator g4sim"))
    nb = (plan.get("node_binding") or {}).get("nodes") or {}
    nodes = node_index(contract["stage_graph"])
    for nid, b in sorted(nb.items()):
        path = f"$.plan.node_binding.nodes[{nid}]"
        if nid not in nodes:
            out.append(_bf("node", path, f"node {nid!r} is not in the stage graph"))
            continue
        row = TABLE1.get(str(b.get("table1")))
        if row is None:
            out.append(_bf("table1", path, f"table1 must be one of {sorted(TABLE1)} (section 11.4 Table 1)"))
        elif row[1] is not None and nodes[nid].get("kernel") != row[1]:
            out.append(_bf("kernel_property", path, f"node {nid!r} bound to {row[0]} has kernel property {row[1]}, not "
                           f"{nodes[nid].get('kernel')!r} (Table 1)"))
        if row is not None and b.get("table1") in NO_HANDOFF_BEFORE and "handoff_inputs" in b.get("stored", []):
            out.append(_bf("no_handoff", path, "no stage hand-off exists before stage 3, so the inputs of nodes 2-4b "
                           "cannot be stored (section 19)"))
    split = bool((plan.get("node_binding") or {}).get("pde_split"))
    for i, r in enumerate(contract.get("references", [])):
        e = r.get("edge") or {}
        if r.get("type") != "mid-chain-injection" or edge_kind(e) != "between":
            continue
        a, b = (str((nb.get(e["from"]) or {}).get("table1")), str((nb.get(e["to"]) or {}).get("table1")))
        if (a, b) == ("3", "4a") and not split:
            out.append(_bf("injection_light_pde", f"$.references[{i}]", "an injection reference with a known photon "
                           "count between light collection and PDE needs the PDE split of section 6.7: on the "
                           "efficiency-map path epsilon_c combines them (section 11.4)"))
        if b == "4b" and a in ("2", "3", "4a"):
            out.append(_bf("injection_single_pe", f"$.references[{i}]", "no single-photoelectron injection reference: "
                           "no hand-off exists before response stage 3 (section 11.4, section 19)"))
    aligned = [p["name"] for p in contract.get("parameters", []) if p.get("role") in ("theta", "phi")
               and any(b.get("document") == "alignment-overlay" for b in p.get("bindings", []))]
    if aligned:
        if not RECORDED_OVERLAY_RUN:
            out.append(_bf("misalignment_no_recorded_run", "$.parameters", f"{aligned}: a misaligned geometry enters "
                           "only once a recorded run can apply the overlay; geant4_run.py run-spec takes none (D83 (7), "
                           "section 19 C25)"))
        bare = [j for j, d in enumerate(plan.get("design_points") or []) if not (isinstance(d, dict) and d.get("overlay"))]
        if bare:
            out.append(_bf("overlay_every_point", "$.plan.design_points", f"design points {bare[:5]} apply no overlay: a "
                           "plan that varies alignment applies one at every design point, the nominal included (D86)"))
    return out


def g4sim_candidates(contract: dict, plan: dict) -> dict:
    """Candidate methods from section 11.4 Table 2 (phase 3): each theta/phi's bindings give its Table 2 rows; a
    parameter takes the methods all its rows allow, under the preconditions the plan's node binding records
    (plan.node_binding: {nodes: {node: {table1, stored, recording, distribution, stage, support_declared,
    poisson_interval_only}}, fast_sim_envelope: {materials, stages}, pde_split}). Each candidate states its form,
    whether it forms event weights (the G4 applicability, D75) and its preconditions; excluded methods give a
    reason. PDE-split bindings (document "evaluator") take the row of section 6.7 (pde_split.candidates)."""
    findings = binding_findings(contract) + g4sim_findings(contract, plan)
    nb_all = (plan.get("node_binding") or {}).get("nodes") or {}
    out, excluded = {}, {}
    blocked = {f["path"] for f in findings}
    for i, par in enumerate(contract.get("parameters", [])):
        if par.get("role") not in ("theta", "phi"):
            continue
        nb = [nb_all.get(n) or {} for n in par.get("nodes", [])]
        rows = {binding_row(b)[0] for b in par.get("bindings", [])}
        if "evaluator" in rows:                   # the PDE split of section 6.7 (routes 2_1, 3 and 1)
            stored = set().union(*[set(b.get("stored", [])) for b in nb]) if nb else set()
            recorded = bool(nb) and all(b.get("recording", plan.get("recording_level")) in RECORDED for b in nb)
            from core.calibration import pde_split    # NumPy/SciPy: imported only for a PDE split
            c, x = pde_split.candidates(par, contract, plan, stored, recorded)
            out[par["name"]] = [_entry(*e) for e in c] if rows == {"evaluator"} else []
            if x:
                excluded[par["name"]] = x
            continue
        sets: list[list] = []
        excl: list[dict] = []
        for row in sorted(r for r in rows if r):
            if row == "misalignment":
                excl.append({"method": "resimulation", "reason": "no recorded run of a misaligned geometry (D83 (7))"})
                sets.append([])
                continue
            c, x = _row_methods(row, par, nb, contract, plan)
            sets.append(c)
            excl += x
        names = set.intersection(*[{e["method"] for e in s} for s in sets]) if sets else set()
        if any(p == f"$.parameters[{i}]" or p.startswith(f"$.parameters[{i}].") for p in blocked):
            names = set()
        merged = [e for e in (sets[0] if sets else []) if e["method"] in names]
        out[par["name"]] = sorted(merged, key=lambda e: METHOD_ORDER.index(e["method"]))
        if excl:
            excluded[par["name"]] = excl
    none = sorted(p for p, ms in out.items() if not ms)
    status = "failed" if findings or none else "ok"
    return {"status": status, "parameters": out, "excluded": excluded, "without_candidate": none, "findings": findings}
