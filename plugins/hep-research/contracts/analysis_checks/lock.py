"""Semantic lock (v6.3 C14), record and compare: which definitions, at which digests, a frozen analysis was checked
against. It records the suite and generator identity, every definition in use (semantics tables, coverage contracts,
the catalog effects and compositions they reference, the rule registry) and the member-set closure of each class a
rule resolves, so a change to a class's members is a difference and an unrelated catalog entry is not. The lock names
neither itself nor the bundle digest. A difference means the old subject's semantics cannot be reproduced from the
current definitions (unverified in M2a; snapshot reproduction is D11b)."""
from __future__ import annotations

from contracts.effect_catalog import resolve_members
from contracts.release_manifest import canonical_sha256


def _effects_in_use(view: dict) -> tuple[set[str], set[str]]:
    """(effect ids, class ids) the coverage contracts in use and the spec corrections reference."""
    from contracts.analysis_checks.obligations import corrections
    effects: set[str] = set()
    classes: set[str] = set()
    for cov in view.get("coverage", {}).values():
        for op in (cov.get("doc") or {}).get("operators", []):
            effects |= set(op.get("covers", [])) | {f.get("effect") for f in op.get("factors", []) if f.get("effect")}
            classes |= set(op.get("class_coverage", {}))
    effects |= {str(c.get("category")) for c in corrections(view)}
    cat = view.get("catalog") or {}
    by_id = {e["effect_id"]: e for e in cat.get("effects", [])}
    classes |= {by_id[e]["class"] for e in effects if e in by_id and by_id[e].get("class")}
    return effects, classes


def build_lock(suite: dict, generator_code_digest: str, view: dict, registry_digest: str | None) -> dict:
    cat = view.get("catalog") or {}
    effects, classes = _effects_in_use(view)
    member_sets = [resolve_members(cat, c) for c in sorted(classes)]
    members = {m for ms in member_sets for m in (ms.get("members") or [])}
    comps = [c for c in cat.get("compositions", [])
             if ({c["parent"]} | {ch["effect"] for ch in c["children"]}) & effects]
    for c in comps:
        effects |= {c["parent"]} | {ch["effect"] for ch in c["children"]}
    defs = []
    for tid, table in sorted(view.get("tables", {}).items()):
        defs.append({"kind": "semantics-table", "id": tid, "version": table.get("table_version"),
                     "digest": canonical_sha256(table), "owner": "bundle"})
    for tid, cov in sorted(view.get("coverage", {}).items()):
        defs.append({"kind": "coverage-contract", "id": tid, "version": (cov.get("doc") or {}).get("coverage_version"),
                     "digest": canonical_sha256(cov.get("doc")), "owner": cov.get("source")})
    for e in sorted(effects | members):
        entry = next((x for x in cat.get("effects", []) if x["effect_id"] == e), None)
        defs.append({"kind": "effect", "id": e, "version": cat.get("catalog_version"),
                     "digest": canonical_sha256(entry) if entry is not None else None, "owner": cat.get("owner")})
    for c in sorted(comps, key=lambda x: x["composition_id"]):
        defs.append({"kind": "composition", "id": c["composition_id"], "version": cat.get("catalog_version"),
                     "digest": canonical_sha256(c), "owner": cat.get("owner")})
    if registry_digest is not None:
        defs.append({"kind": "rule-registry", "id": "contracts/rules/registry.json", "version": None,
                     "digest": registry_digest, "owner": "core"})
    readers = sorted({str(doc.get("recipe_version")) for i in (view.get("context") or {}).get("recipe_instances", [])
                      if isinstance(i, dict)
                      for doc in [((view.get("items", {}).get(i.get("recipe")) or {}).get("doc")) or {}]
                      if isinstance(doc, dict)})
    return {"lock_version": "1.0.0", "suite": {"id": suite.get("suite_id"), "version": suite.get("version")},
            "generator": dict(suite.get("generator", {}), code_digest=generator_code_digest),
            "definitions": defs, "member_sets": [{k: m[k] for k in ("class", "members", "strategy", "closure_digest")}
                                                 for m in member_sets],
            "readers": [{"id": f"recipe-{v}-view", "version": "1.0.0"} for v in readers]}


def compare(locked: dict, current: dict) -> list[dict]:
    """Differences between a frozen lock and the lock the current definitions give, as [{kind, id, locked, current}]."""
    out = []
    for key in ("suite", "generator"):
        if locked.get(key) != current.get(key):
            out.append({"kind": key, "id": key, "locked": locked.get(key), "current": current.get(key)})
    a = {(d["kind"], d["id"]): d.get("digest") for d in locked.get("definitions", [])}
    b = {(d["kind"], d["id"]): d.get("digest") for d in current.get("definitions", [])}
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append({"kind": k[0], "id": k[1], "locked": a.get(k), "current": b.get(k)})
    ma = {m["class"]: m["closure_digest"] for m in locked.get("member_sets", [])}
    mb = {m["class"]: m["closure_digest"] for m in current.get("member_sets", [])}
    for k in sorted(set(ma) | set(mb)):
        if ma.get(k) != mb.get(k):
            out.append({"kind": "member-set", "id": k, "locked": ma.get(k), "current": mb.get(k)})
    if locked.get("readers") != current.get("readers"):
        out.append({"kind": "readers", "id": "readers", "locked": locked.get("readers"), "current": current.get("readers")})
    return out
