"""Dependencies between calibration results (Part B sections 5.2 clause 5, 10.2, 10.3, 10.4; owner calib_deps.py).

Phase 0 content (section 17): hash references, cycle checks, derivation of upstream roles from usage, and the
acyclic computation of version ids. Upstream invalidation (section 10.3) and the conflict rules of section 10.4 are
later phases. Standard library only.

Roles are derived, never declared (section 10.2): any central usage makes the upstream `central`; only variation sets
or envelopes make it `variation`; no usage is rejected. A role written in the contract must equal the derived one.
"""
from __future__ import annotations

import re

from core.canonical import canonical_sha256

# Section 5.2 clause 5: the usages an upstream reference can declare, and the role each implies (section 10.2).
CENTRAL_USAGES = frozenset({"phi-center", "nuisance-posterior", "xi", "fixed-value"})
VARIATION_USAGES = frozenset({"variation-set", "envelope"})
USAGES = CENTRAL_USAGES | VARIATION_USAGES
ROLES = ("central", "variation")

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DependencyError(ValueError):
    """A dependency the workflow rejects; `code` is a stable name, `path` locates it."""

    def __init__(self, code: str, message: str, path: str = "$"):
        super().__init__(message)
        self.code, self.path = code, path


def derive_role(usages) -> str:
    """Role of an upstream from its usages (Appendix C.3 "Role"). Raises ValueError on no or unknown usage."""
    usages = set(usages)
    if not usages:
        raise ValueError("upstream reference without usage")
    unknown = usages - USAGES
    if unknown:
        raise ValueError(f"unknown usage {sorted(unknown)}")
    return "central" if usages & CENTRAL_USAGES else "variation"


def is_hash_reference(value) -> bool:
    """A result is cited by its SHA-256 (lower-case hex), never by numbers or a name (section 15.3.17)."""
    return isinstance(value, str) and bool(SHA256.match(value))


def check_upstream_entries(entries) -> list[dict]:
    """Section 5.2 clause 5 for a contract's upstream[]: each entry cites a result by hash and lists its usages; a
    written role must equal the derived one. Returns findings (code, path, message); empty means accepted."""
    out: list[dict] = []
    if not isinstance(entries, list):
        return [{"code": "upstream.not_list", "path": "$.upstream", "message": "upstream must be a list"}]
    seen: set[str] = set()
    for i, e in enumerate(entries):
        p = f"$.upstream[{i}]"
        if not isinstance(e, dict):
            out.append({"code": "upstream.not_object", "path": p, "message": "an upstream entry is an object"})
            continue
        ref = e.get("result_sha256")
        if not is_hash_reference(ref):
            out.append({"code": "upstream.not_hash", "path": f"{p}.result_sha256",
                        "message": "an upstream result is cited by its SHA-256, not by numbers or a name"})
        elif ref in seen:
            out.append({"code": "upstream.duplicate", "path": f"{p}.result_sha256",
                        "message": "the same upstream result is listed twice; list all its usages in one entry"})
        else:
            seen.add(str(ref))                  # a hash reference: a string
        try:
            role = derive_role(e.get("usages") or [])
        except ValueError as exc:
            out.append({"code": "upstream.usage", "path": f"{p}.usages", "message": str(exc)})
            continue
        if "role" in e and e["role"] != role:
            out.append({"code": "upstream.role_mismatch", "path": f"{p}.role",
                        "message": f"role written as {e['role']!r} but the usages {sorted(e['usages'])} make it "
                                   f"{role!r}; roles are derived from usage (section 10.2)"})
    return out


def find_cycle(graph: dict) -> list[str] | None:
    """A cycle in a result dependency graph {result: [upstream results]}, as a list of results closing on its first
    element, or None. Section 10.3: cycles are rejected and must be merged into one joint fit."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in graph}
    for ups in graph.values():
        for u in ups:
            colour.setdefault(u, WHITE)
    for start in sorted(colour):
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(sorted(graph.get(start, ()))))]
        path = [start]
        colour[start] = GREY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                colour[node] = BLACK
                stack.pop()
                path.pop()
            elif colour[nxt] == GREY:
                return path[path.index(nxt):] + [nxt]
            elif colour[nxt] == WHITE:
                colour[nxt] = GREY
                stack.append((nxt, iter(sorted(graph.get(nxt, ())))))
                path.append(nxt)
    return None


def check_acyclic(graph: dict) -> None:
    cyc = find_cycle(graph)
    if cyc:
        raise DependencyError("deps.cycle", "circular dependency " + " -> ".join(cyc)
                              + "; merge the cycle into one joint fit (section 10.3)")


def central_closure(result: str, upstreams: dict) -> set[str]:
    """Every result in the `central` dependency closure of `result` (section 10.4, version lineage): its central
    upstreams taken recursively. upstreams maps a result to its upstream[] entries ({result_sha256, usages})."""
    out: set[str] = set()
    todo = [result]
    while todo:
        r = todo.pop()
        for e in upstreams.get(r, ()):
            u = e["result_sha256"]
            if derive_role(e["usages"]) == "central" and u not in out:
                out.add(u)
                todo.append(u)
    return out


# ------------------------------------------------------------------ versions (section 10.4, acyclic ids)
# Fields that are the version's own id, the final result hash, or back-filled from them: never inside update_digest.
BACKFILLED = frozenset({"version_id", "result_sha256", "result_hash"})


def _strip_backfilled(payload: dict) -> dict:
    """The payload without its own top-level id and result-hash fields; nested values are content and stay."""
    return {k: v for k, v in payload.items() if k not in BACKFILLED}


def update_digest(payload: dict) -> str:
    """update_digest = hash(contract, data and plan hashes, engine version, parent versions, fit and export values),
    excluding its own id, the final result hash and fields back-filled from them (section 10.4)."""
    required = ("contract_sha256", "data_sha256", "plan_sha256", "engine_version", "parent_versions", "values")
    missing = [k for k in required if k not in payload]
    if missing:
        raise DependencyError("version.payload_incomplete", f"version payload lacks {missing}")
    for i, p in enumerate(payload["parent_versions"]):
        if not is_hash_reference(p):
            raise DependencyError("version.parent_not_hash", "a parent version is cited by its id (SHA-256)",
                                  f"$.parent_versions[{i}]")
    body = _strip_backfilled(payload)
    body["parent_versions"] = sorted(set(payload["parent_versions"]))   # the order of listing is not content
    return canonical_sha256(body)


def version_id(payload: dict) -> str:
    """version id = hash(normalized list of parent version ids, update_digest). Normalized: sorted, without
    duplicates, so the order in which parents are listed does not change the id."""
    return canonical_sha256({"parents": sorted(set(payload["parent_versions"])),
                             "update_digest": update_digest(payload)})


def finalize_result(result: dict, payload: dict) -> dict:
    """Write the version id into the result, then compute the result hash over the result with the id (and without
    a result hash field). Returns a new dict with version_id and result_sha256. The id never depends on the hash."""
    out = {k: v for k, v in result.items() if k not in ("result_sha256", "result_hash")}
    out["version_id"] = version_id(payload)
    out["result_sha256"] = canonical_sha256({k: v for k, v in out.items() if k != "result_sha256"})
    return out


def rebuild_order(versions: dict) -> list[str]:
    """Rebuild versions in acyclic order: versions maps an id to its payload. Each id is recomputed from its payload
    after its parents (a parent outside the set is taken as given). Raises on a cycle among parents or an id that
    does not recompute (section 15.3a: versions and result hashes can be rebuilt in acyclic order)."""
    graph = {v: [p for p in pl["parent_versions"] if p in versions] for v, pl in versions.items()}
    check_acyclic(graph)
    done: list[str] = []
    placed: set[str] = set()
    while len(done) < len(versions):
        ready = sorted(v for v in versions if v not in placed and all(p in placed for p in graph[v]))
        for v in ready:
            got = version_id(versions[v])
            if got != v:
                raise DependencyError("version.not_reproducible", f"version {v[:12]} recomputes to {got[:12]}")
            done.append(v)
            placed.add(v)
    return done
