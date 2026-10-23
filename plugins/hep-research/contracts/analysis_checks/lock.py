"""Semantic lock (v6.3 C14), record and compare: which definitions, at which digests, a frozen analysis was checked
against. It records the suite and generator identity, every definition in use (semantics tables, coverage contracts,
the catalog effects and compositions they reference, the rule registry) and the member-set closure of each class a
rule resolves, so a change to a class's members is a difference and an unrelated catalog entry is not. The lock names
neither itself nor the bundle digest. A difference means the old subject's semantics cannot be reproduced from the
current definitions (unverified in M2a; snapshot reproduction is D11b). The model-card pairing contract pin went with the
model-card suite (removed in 0.28.0)."""
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
    for s in view.get("suites") or [suite]:
        if s:
            defs.append({"kind": "suite", "id": f"{s.get('suite_id')}@{s.get('version')}", "version": s.get("version"),
                         "digest": canonical_sha256(s), "owner": "core"})
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
            "readers": [{"id": f"recipe-{v}-view", "version": "1.0.0"} for v in readers],
            "suites": [{"id": s.get("suite_id"), "version": s.get("version")} for s in view.get("suites") or [suite]]}


def compare(locked: dict, current: dict) -> list[dict]:
    """Differences between a frozen lock and the lock the current definitions give, as [{kind, id, locked, current}]."""
    out = []
    for key in ("suite", "suites"):
        if locked.get(key) != current.get(key):
            out.append({"kind": key, "id": key, "locked": locked.get(key), "current": current.get(key)})
    strip = lambda g: {k: v for k, v in (g or {}).items() if k != "code_digest"}  # noqa: E731
    if strip(locked.get("generator")) != strip(current.get("generator")):
        # a changed generator *code* alone is a new assessment of unchanged definitions (C14), not a difference here
        out.append({"kind": "generator", "id": "generator", "locked": locked.get("generator"), "current": current.get("generator")})
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


def snapshot_entries(view: dict, lock: dict, registry: dict | None = None) -> dict:
    """{digest: document} for every definition the lock pins, to store content-addressed (D11b)."""
    cat = view.get("catalog") or {}
    out: dict[str, object] = {}
    for cov in view.get("coverage", {}).values():
        out[canonical_sha256(cov.get("doc"))] = cov.get("doc")
    for e in cat.get("effects", []):
        out[canonical_sha256(e)] = e
    for c in cat.get("compositions", []):
        out[canonical_sha256(c)] = c
    for cls in {m["class"] for m in lock.get("member_sets", [])}:
        entry = next((c for c in cat.get("classes", []) if c["class_id"] == cls), None)
        if entry is not None:
            members = set(entry["members"]) | {cls}
            closure = {"class": entry, "effects": [e for e in sorted(cat.get("effects", []), key=lambda x: x["effect_id"])
                                                   if e["effect_id"] in members], "catalog_version": cat.get("catalog_version")}
            out[canonical_sha256(closure)] = closure
    for s in view.get("suites") or []:
        out[canonical_sha256(s)] = s
    if registry is not None:
        out[canonical_sha256(registry)] = registry
    wanted = {d["digest"] for d in lock.get("definitions", []) if d.get("digest")} | \
        {m["closure_digest"] for m in lock.get("member_sets", []) if m.get("closure_digest")}
    return {k: v for k, v in out.items() if k in wanted}


def rebuild(lock: dict, lookup) -> tuple[dict, list[str]]:
    """The definitions a lock pins, from a snapshot store (lookup(digest) -> document or None): coverage contracts,
    catalog (effects, classes, compositions) and suites, plus the digests that are missing. Nothing is taken from
    the installed definitions: a missing digest stays missing."""
    missing: list[str] = []

    def get(digest):
        doc = lookup(digest) if digest else None
        if doc is None:
            missing.append(str(digest))
        return doc
    coverage, effects, comps, classes, suites, version, owner = {}, {}, [], [], [], None, None
    for d in lock.get("definitions", []):
        if d["kind"] == "coverage-contract":
            doc = get(d["digest"])
            if doc is not None:
                coverage[d["id"]] = {"doc": doc, "source": "snapshot"}
        elif d["kind"] == "effect":
            doc = get(d["digest"])
            version, owner = d.get("version"), d.get("owner")
            if doc is not None:
                effects[doc["effect_id"]] = doc
        elif d["kind"] == "composition":
            doc = get(d["digest"])
            if doc is not None:
                comps.append(doc)
        elif d["kind"] == "suite":
            doc = get(d["digest"])
            if doc is not None:
                suites.append(doc)
        elif d["kind"] == "rule-registry":
            get(d["digest"])
    for m in lock.get("member_sets", []):
        closure = get(m.get("closure_digest"))
        if closure is not None:
            classes.append(closure["class"])
            for e in closure["effects"]:
                effects.setdefault(e["effect_id"], e)
    order = {f"{s.get('id')}@{s.get('version')}": k for k, s in enumerate(lock.get("suites") or [lock.get("suite") or {}])}
    suites.sort(key=lambda s: order.get(f"{s.get('suite_id')}@{s.get('version')}", 99))
    catalog = {"catalog_version": version, "owner": owner, "classes": classes,
               "effects": [effects[k] for k in sorted(effects)], "compositions": comps}
    return {"coverage": coverage, "catalog": catalog, "suites": suites}, missing
