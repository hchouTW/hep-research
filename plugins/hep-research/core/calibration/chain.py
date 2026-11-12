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
    candidates come from section 11.4 Table 2, added in phase 3: refused here (incomplete)."""
    if plan.get("node_binding"):
        return {"status": "incomplete", "reason": "g4sim node binding: candidate methods from section 11.4 Table 2 "
                "are added in phase 3"}
    nodes = node_index(contract["stage_graph"])
    kernels = plan.get("kernels", {})
    out = {}
    for par in contract.get("parameters", []):
        sets = [node_candidates(nodes[n], kernels.get(n, {})) for n in par["nodes"]]
        common = set.intersection(*sets) if sets else set()
        out[par["name"]] = [{"method": m, "tier": METHOD_TIER[m]} for m in METHOD_ORDER if m in common]
    none = sorted(p for p, ms in out.items() if not ms)
    return {"status": "ok" if not none else "failed", "parameters": out, "without_candidate": none}
