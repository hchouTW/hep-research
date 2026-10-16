"""Obligation inventory (v6.3 C10): a deterministic, versioned generator over the frozen analysis intent.

generate(suite, view) iterates each rule's subject kind over the roots, recipe instances and spec corrections of the
context, the recipes and tables of the bundle and the catalog compositions. It never reads bindings or declarations,
so masking one cannot remove an obligation. Obligation IDs are '<rule>:<subject key>' built from context IDs and spec
effect IDs (never file names or list positions), the items are sorted, and the digest is the canonical SHA-256 of
generator, suite and items: the same subject under the same suite version regenerates byte-identically."""
from __future__ import annotations

from contracts.release_manifest import canonical_sha256

PREREQUISITES = {
    "root": ["root intent fields", "output instance"],
    "correction": ["spec correction category", "effect catalog"],
    "correction_instance": ["spec correction", "instance view", "coverage contract", "applicability (spec target_scope "
                            "or an instance_mapping declaration)"],
    "root_effect": ["instance views on the root's path", "input_of bindings", "coverage contract"],
    "root_composition": ["instance views on the root's path", "catalog composition", "coverage contract"],
    "instance_factor": ["factor table bound to the instance", "catalog composition"],
    "instance": ["instance view", "spec migration corrections", "response items", "response_used_by bindings"],
    "ratio_root": ["ratio root operands (chain roots)", "their binning and scopes"],
    "ratio_cancellation": ["spec ratio cancellation claim", "factor instance per side (calibration binding, selector)",
                           "factor power per side (coverage contract)"],
    "ratio_correlation": ["spec ratio correlation claim", "validation record or sourced correlation declaration"],
}


def spec_ratio(view: dict) -> dict:
    spec = (view.get("items", {}).get(view["context"].get("spec")) or {}).get("doc") or {}
    ratio = (spec.get("extension") or {}).get("ratio") if isinstance(spec, dict) and isinstance(spec.get("extension"), dict) else None
    return ratio if isinstance(ratio, dict) else {}


def ratio_claims(view: dict) -> list[dict]:
    claims = spec_ratio(view).get("cancellations")
    return [c for c in claims if isinstance(c, dict) and isinstance(c.get("effect"), str)] if isinstance(claims, list) else []


CANCEL = ("cancels", "approximately_cancels")


def corrections(view: dict) -> list[dict]:
    spec = (view.get("items", {}).get(view["context"].get("spec")) or {}).get("doc") or {}
    ext = spec.get("extension") if isinstance(spec, dict) else None
    out = ext.get("corrections") if isinstance(ext, dict) else None
    return [c for c in out if isinstance(c, dict) and isinstance(c.get("effect_id"), str)] if isinstance(out, list) else []


def path_instances(ctx: dict, start: str) -> list[str]:
    """The instances whose output reaches `start` through input_of bindings, `start` included, sorted."""
    feeds: dict[str, set[str]] = {}
    for b in ctx.get("bindings", []):
        if b.get("type") == "input_of" and isinstance(b.get("from"), dict) and isinstance(b.get("to"), dict):
            feeds.setdefault(str(b["to"].get("instance")), set()).add(str(b["from"].get("instance")))
    seen, todo = {start}, [start]
    while todo:
        for nxt in feeds.get(todo.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return sorted(seen)


def instance_effects(view: dict, inst: dict) -> set[str]:
    recipe = (view.get("items", {}).get(inst.get("recipe")) or {}).get("doc") or {}
    table = view.get("tables", {}).get((recipe.get("semantics") or {}).get("table_id")) or {}
    ops = {o["operator_id"]: o for o in table.get("operators", [])}
    return {e for s in recipe.get("steps", []) for e in ops.get(s.get("operator"), {}).get("applies", [])}


def _subjects(kind: str, view: dict, structural: bool) -> list[tuple[str, dict]]:
    ctx = view["context"]
    insts = {i["instance_id"]: i for i in ctx.get("recipe_instances", []) if isinstance(i, dict) and "instance_id" in i}
    roots = [r for r in ctx.get("roots", []) if isinstance(r, dict) and "root_id" in r]
    comps = (view.get("catalog") or {}).get("compositions", [])
    if kind == "root":
        return [(r["root_id"], {"root": r["root_id"]}) for r in roots]
    if kind == "correction":
        return [(c["effect_id"], {"correction": c["effect_id"]}) for c in corrections(view)]
    if kind == "correction_instance":
        return [(f"{c['effect_id']}@{i}", {"correction": c["effect_id"], "instance": i})
                for c in corrections(view) for i in sorted(insts)]
    if kind == "instance":
        return [(i, {"instance": i}) for i in sorted(insts)]
    if kind in ("ratio_root", "ratio_cancellation", "ratio_correlation"):
        rr = sorted(r["root_id"] for r in ctx.get("ratio_roots", []) if isinstance(r, dict) and "root_id" in r)
        if not spec_ratio(view):
            return []
        if kind == "ratio_root":
            return [(r, {"ratio_root": r}) for r in rr] or [("spec", {"ratio_root": None})]
        want = (lambda c: c.get("treatment") in CANCEL) if kind == "ratio_cancellation" else (lambda c: c.get("treatment") not in CANCEL)
        return [(f"{r}#{c['effect']}", {"ratio_root": r, "effect": c["effect"]}) for r in rr for c in ratio_claims(view) if want(c)]
    out = []
    for r in roots:
        start = (r.get("output") or {}).get("instance")
        if start not in insts:
            continue
        path = [i for i in path_instances(ctx, str(start)) if i in insts]
        effects = set().union(*(instance_effects(view, insts[i]) for i in path)) if path else set()
        if kind == "root_effect":
            out += [(f"{r['root_id']}#{e}", {"root": r["root_id"], "effect": e}) for e in sorted(effects)]
        elif kind == "root_composition":
            covered = _covered_on_path(view, [insts[i] for i in path])
            out += [(f"{r['root_id']}#{c['composition_id']}", {"root": r["root_id"], "composition": c["composition_id"]})
                    for c in comps if covered & ({c["parent"]} | {ch["effect"] for ch in c["children"]})]
    if kind == "instance_factor":
        for i in sorted(insts):
            cals = insts[i].get("calibrations") or {}
            for c in comps:
                item = cals.get(c["parent"])
                doc = (view.get("items", {}).get(item) or {}).get("doc")
                if isinstance(doc, dict) and "factor_table_version" in doc:
                    out.append((f"{i}#{c['composition_id']}", {"instance": i, "composition": c["composition_id"],
                                                               "factor_table": item}))
    return out


def _covered_on_path(view: dict, insts: list[dict]) -> set[str]:
    out: set[str] = set()
    for inst in insts:
        recipe = (view.get("items", {}).get(inst.get("recipe")) or {}).get("doc") or {}
        tid = (recipe.get("semantics") or {}).get("table_id")
        cov = ((view.get("coverage", {}).get(tid) or {}).get("doc")) or {}
        ops = {o["operator_id"]: o for o in cov.get("operators", [])}
        for s in recipe.get("steps", []):
            out |= set(ops.get(s.get("operator"), {}).get("covers", []))
    return out


def generate(suite: dict, view: dict) -> dict:
    items = []
    for rule in suite.get("rules", []):
        for key, subject in _subjects(rule.get("subject", ""), view, True):
            items.append({"obligation_id": f"{rule['rule_id']}:{key}", "rule_id": rule["rule_id"],
                          "rule_version": rule["version"], "subject": subject,
                          "prerequisites": PREREQUISITES.get(rule.get("subject", ""), [])})
    items.sort(key=lambda o: o["obligation_id"])
    head = {"generator": dict(suite.get("generator", {})), "suite": {"id": suite.get("suite_id"), "version": suite.get("version")}}
    return dict(head, items=items, digest=canonical_sha256(dict(head, items=items)))


def generate_all(suites: list[dict], view: dict) -> dict:
    """One inventory over several suites (the primary first): items merged and sorted, one digest."""
    parts = [generate(s, view) for s in suites]
    items = sorted((i for p in parts for i in p["items"]), key=lambda o: o["obligation_id"])
    if len(parts) == 1:
        return parts[0]
    head = {"generator": [p["generator"] for p in parts], "suite": [p["suite"] for p in parts]}
    return dict(head, items=items, digest=canonical_sha256(dict(head, items=items)))


def check_inventory(frozen: dict, regenerated: dict) -> list[dict]:
    """Findings when the frozen inventory is not what the same suite version regenerates (input invalid)."""
    out: list[dict] = []
    if canonical_sha256({k: frozen.get(k) for k in ("generator", "suite", "items")}) != frozen.get("digest"):
        out.append({"code": "inventory.digest", "message": "the frozen inventory does not match its own digest"})
    if frozen.get("digest") != regenerated.get("digest") or frozen.get("items") != regenerated.get("items"):
        d = diff(frozen.get("items", []), regenerated.get("items", []))
        out.append({"code": "inventory.mismatch", "message": "regenerating the inventory under the same suite version "
                    f"gives another result (added {len(d['added'])}, removed {len(d['removed'])})", "delta": d})
    return out


def diff(old_items: list, new_items: list) -> dict:
    a = {o["obligation_id"] for o in old_items if isinstance(o, dict)}
    b = {o["obligation_id"] for o in new_items if isinstance(o, dict)}
    return {"added": sorted(b - a), "removed": sorted(a - b)}
