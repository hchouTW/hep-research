"""Composition diagnostics: what happens when several profiles (experiments and theory domains) are used together.

Checks that namespaces stay disjoint, dependencies are present, and every cross-profile correlation is backed by
evidence or a justified, scoped assumption. Identifiers with the same local name in different namespaces are
different things (T06): the diagnostics say so and never imply a correlation between them.

compose(profiles, correlations=(), ids=()) -> {"ok", "errors", "notes", "namespaces", "kinds"}
  profiles: loaded profile.json dicts.
  correlations: [{"between": [id_a, id_b], "evidence_ids": [...]} or {"between": [...], "assumption":
                 {"justification": str, "scope": str}}]; ids are namespaced ('<ns>:<local>').
  ids: namespaced identifiers in use (datasets, nuisances, claims), checked for local-name clashes.
"""
from __future__ import annotations

from contracts.vocab import NAMESPACED, declared_namespaces


def compose(profiles, correlations=(), ids=()) -> dict:
    errors, notes = [], []
    owner = {}
    for p in profiles:
        for ns in declared_namespaces(p):
            if ns in owner and owner[ns] != p["id"]:
                errors.append({"code": "compose.namespace_collision", "message": f"namespace '{ns}' declared by {owner[ns]} and {p['id']}"})
            owner.setdefault(ns, p["id"])
    present = {p["id"] for p in profiles}
    for p in profiles:
        for dep in p.get("depends_on", []):
            dep_id = dep["id"] if isinstance(dep, dict) else dep
            if dep_id not in present:
                errors.append({"code": "compose.missing_dependency", "message": f"{p['id']} depends on {dep_id}, which is not loaded"})

    def ns_of(i):
        m = NAMESPACED.match(i or "")
        return m.group(1) if m else None

    by_local = {}
    for i in ids:
        ns = ns_of(i)
        if ns is None:
            errors.append({"code": "compose.unqualified_id", "message": f"'{i}' is not namespaced; qualify it with its profile namespace"})
            continue
        if ns not in owner:
            errors.append({"code": "compose.unknown_namespace", "message": f"'{i}' uses namespace '{ns}', which no loaded profile declares"})
        by_local.setdefault(i.split(":", 1)[1], set()).add(i)
    for local, full in sorted(by_local.items()):
        if len(full) > 1:
            notes.append({"code": "compose.same_local_name", "message": f"{sorted(full)} share the local name '{local}' but are distinct; "
                          "no correlation is implied without an explicit mapping"})

    for k, c in enumerate(correlations):
        pair = c.get("between", [])
        if len(pair) != 2 or any(ns_of(x) is None for x in pair):
            errors.append({"code": "compose.correlation_ids", "message": f"correlations[{k}] needs two namespaced ids"})
            continue
        a = c.get("assumption") or {}
        if not c.get("evidence_ids") and not (a.get("justification") and a.get("scope")):
            errors.append({"code": "compose.correlation_unsupported",
                           "message": f"correlation {pair} needs evidence ids or an assumption with justification and scope"})
        elif ns_of(pair[0]) != ns_of(pair[1]):
            notes.append({"code": "compose.cross_profile_correlation",
                          "message": f"cross-profile correlation {pair} accepted on {'evidence' if c.get('evidence_ids') else 'a scoped assumption'}"})
    kinds = {}
    for p in profiles:
        kinds.setdefault(p["kind"], []).append(p["id"])
    return {"ok": not errors, "errors": errors, "notes": notes, "namespaces": owner, "kinds": kinds}
