"""Check-context records (v6.3 C6, C12): cross-field checks of roots, recipe instances, typed bindings and
declarations. The structure itself is checked against contracts/schemas/check_context.json by the I/O layer.

Typed bindings: input_of (data flow between instances), response_used_by (a response used by an instance step, or by a
prediction for folding), variation_of (an instance that varies a nominal one). Any other type is unsupported.
Declarations carry their author (asserted_by) and basis and no confirmation field; their types are listed below. A
declaration that says a rule does not apply is never counted (declaration.rule_waiver_not_counted): only typed facts
can change an applicability judgement."""
from __future__ import annotations

from contracts.analysis_checks.scope import parse_scope

BINDING_TYPES = ("input_of", "response_used_by", "variation_of")
DECLARATION_TYPES = ("instance_mapping", "partition_exclusive", "partition_coverage", "variation_role", "correlation",
                     "applicability_fact", "provenance_binding", "execution_attribution")
AUTHOR_KINDS = ("person", "agent", "tool")
ROLES = ("nominal", "systematic", "alternative")


def _f(code: str, where: str, message: str) -> dict:
    return {"code": code, "where": where, "message": message}


def _is_waiver(decl: dict) -> bool:
    content: dict = decl["content"] if isinstance(decl.get("content"), dict) else {}
    return decl.get("type") in ("not_applicable", "rule_not_applicable", "waiver") or "rule" in content


def check_context(ctx: dict, item_roles: dict) -> list[dict]:
    out: list[dict] = []
    axes = ctx.get("scope_axes") or {}
    instances = {i.get("instance_id"): i for i in ctx.get("recipe_instances", []) if isinstance(i, dict)}
    ids: list[tuple[str, object]] = []
    for kind, key in (("roots", "root_id"), ("recipe_instances", "instance_id"), ("bindings", "binding_id"),
                      ("declarations", "declaration_id")):
        ids += [(kind, r.get(key)) for r in ctx.get(kind, []) if isinstance(r, dict)]
    names = [i for _, i in ids]
    for d in sorted({i for i in names if names.count(i) > 1 and isinstance(i, str)}):
        out.append(_f("context.duplicate_id", "$", f"id '{d}' is used twice in the context"))
    if item_roles.get(ctx.get("spec")) != "measurement-spec":
        out.append(_f("context.unknown_reference", "$.spec", f"{ctx.get('spec')!r} is not the bundle's measurement-spec"))

    def ref_ok(ref, where: str) -> None:
        if not isinstance(ref, dict):
            out.append(_f("context.unknown_reference", where, "a reference is an object"))
        elif "instance" in ref and ref["instance"] not in instances:
            out.append(_f("context.unknown_reference", where, f"instance {ref['instance']!r} is not in the context"))
        elif "item" in ref and ref["item"] not in item_roles:
            out.append(_f("context.unknown_reference", where, f"item {ref['item']!r} is not in the bundle"))
        elif "prediction" in ref and ref["prediction"] not in item_roles:
            out.append(_f("context.unknown_reference", where, f"prediction {ref['prediction']!r} is not in the bundle"))
        elif not ({"instance", "item", "prediction"} & set(ref)):
            out.append(_f("context.unknown_reference", where, "a reference names an instance, an item or a prediction"))

    for k, root in enumerate(ctx.get("roots", [])):
        where = f"$.roots[{k}]"
        ref_ok(root.get("output"), f"{where}.output")
        ref_ok(root.get("binning"), f"{where}.binning")
        res = parse_scope(root.get("scope"), axes)
        if not res["ok"]:
            out.append(_f("context.bad_scope", f"{where}.scope", f"{root.get('scope')!r}: {res['errors']}"))
    for k, inst in enumerate(ctx.get("recipe_instances", [])):
        where = f"$.recipe_instances[{k}]"
        if item_roles.get(inst.get("recipe")) != "recipe":
            out.append(_f("context.unknown_reference", f"{where}.recipe", f"{inst.get('recipe')!r} is not a recipe item"))
        for eff, item in (inst.get("calibrations") or {}).items():
            if item_roles.get(item) != "calibration":
                out.append(_f("context.unknown_reference", f"{where}.calibrations.{eff}", f"{item!r} is not a calibration item"))
        if inst.get("role") not in ROLES:
            out.append(_f("context.bad_role", f"{where}.role", f"role must be one of {list(ROLES)}"))
        elif inst.get("role") != "nominal" and inst.get("nominal") not in instances:
            out.append(_f("context.variation_unbound", f"{where}.nominal", "a systematic or alternative names its nominal"))
        res = parse_scope(inst.get("scope"), axes)
        if not res["ok"]:
            out.append(_f("context.bad_scope", f"{where}.scope", f"{inst.get('scope')!r}: {res['errors']}"))
    for k, b in enumerate(ctx.get("bindings", [])):
        where = f"$.bindings[{k}]"
        if b.get("type") not in BINDING_TYPES:
            out.append(_f("context.unsupported_binding", f"{where}.type", f"binding type {b.get('type')!r} is not supported"))
            continue
        ref_ok(b.get("from"), f"{where}.from")
        ref_ok(b.get("to"), f"{where}.to")
    for k, d in enumerate(ctx.get("declarations", [])):
        where = f"$.declarations[{k}]"
        if _is_waiver(d):
            out.append(_f("declaration.rule_waiver_not_counted", where,
                          "a declaration that a rule does not apply is not counted: give a typed applicability fact"))
        elif d.get("type") not in DECLARATION_TYPES:
            out.append(_f("context.unknown_declaration_type", f"{where}.type", f"declaration type {d.get('type')!r}"))
        author, basis = d.get("asserted_by"), d.get("basis")
        if not (isinstance(author, dict) and author.get("kind") in AUTHOR_KINDS and author.get("id")
                and isinstance(basis, dict) and (basis.get("source") or basis.get("rationale"))):
            out.append(_f("context.declaration_unattributed", where, "a declaration names asserted_by {kind, id} and a basis"))
    return out


def accepted_declarations(ctx: dict, findings: list[dict] | None = None) -> list[dict]:
    """The declarations rules may use: typed, attributed, never a rule waiver."""
    return [d for d in ctx.get("declarations", []) if isinstance(d, dict) and not _is_waiver(d)
            and d.get("type") in DECLARATION_TYPES and isinstance(d.get("asserted_by"), dict)
            and d["asserted_by"].get("kind") in AUTHOR_KINDS and d["asserted_by"].get("id")
            and isinstance(d.get("basis"), dict) and (d["basis"].get("source") or d["basis"].get("rationale"))]
