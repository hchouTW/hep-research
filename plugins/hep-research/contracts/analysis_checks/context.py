"""Check-context records (v6.3 C6, C12): cross-field checks of roots, recipe instances, typed bindings and
declarations. The structure itself is checked against contracts/schemas/check_context.json by the I/O layer.

Typed bindings: input_of (data flow between instances), response_used_by (a response used by an instance step, or by a
prediction for folding), variation_of (an instance that varies a nominal one), observes (an observation component,
item and pointer, encoded by a model's auxiliary measurement; model-card/v1). Any other type is unsupported.
Declarations carry their author (asserted_by) and basis and no confirmation field; their types are listed below. A
declaration that says a rule does not apply is never counted (declaration.rule_waiver_not_counted): only typed facts
can change an applicability judgement."""
from __future__ import annotations

from contracts.analysis_checks.scope import parse_scope

BINDING_TYPES = ("input_of", "response_used_by", "variation_of", "observes")
DECLARATION_TYPES = ("instance_mapping", "partition_exclusive", "partition_coverage", "variation_role", "correlation",
                     "applicability_fact", "provenance_binding", "execution_attribution")
AUTHOR_KINDS = ("person", "agent", "tool")
ROLES = ("nominal", "systematic", "alternative")
# input checks each context version enables (P3): a check added later is enabled for the context version that
# introduces it, so a frozen 1.0.0 context is never judged by a newer check
INPUT_CHECKS = {"1.0.0": frozenset({"item.not_an_object", "item.schema", "spec.bad_corrections", "spec.duplicate_effect_id"})}
INPUT_CHECKS["1.1.0"] = INPUT_CHECKS["1.0.0"]
# the first suite version a 1.1.0 context may select (the lowest pre-release of 1.1.0); a 1.0.0 context selects
# only versions below it
FIRST_1_1_SUITE = "1.1.0-0"


def input_check_enabled(context_version, check: str) -> bool:
    """A context of unknown version enables every 1.0.0 check (the schema refuses it separately)."""
    return check in INPUT_CHECKS.get(str(context_version), INPUT_CHECKS["1.0.0"])


def version_findings(ctx: dict) -> list[dict]:
    """Format rules of check-context 1.1.0 (release R2) that the schema cannot state: no 'required' on a root or
    ratio root (DR-2: deferral goes through an exception), and the version guard between context and suites (a 1.1.0
    context selects 1.1.0 or later suites, pre-releases included; a 1.0.0 context selects 1.0.x suites)."""
    from contracts.semver import precedence
    version = ctx.get("context_version")
    if version not in INPUT_CHECKS:
        return []
    new = version != "1.0.0"
    out = []
    if new:
        for key in ("roots", "ratio_roots"):
            for i, r in enumerate(ctx.get(key) or []):
                if isinstance(r, dict) and "required" in r:
                    out.append(_f("context.required_removed", f"$.{key}[{i}].required",
                                  "check-context 1.1.0 has no 'required': defer a root with an exception record (DR-2)"))
    for i, s in enumerate([ctx.get("suite")] + list(ctx.get("suites") or [])):
        try:
            later = precedence(str((s or {}).get("version"))) >= precedence(FIRST_1_1_SUITE)
        except ValueError:
            continue  # the schema reports a malformed version
        if later != new:
            out.append(_f("context.suite_version", "$.suite" if i == 0 else f"$.suites[{i - 1}]",
                          f"a {version} context selects {'1.1.0 or later' if new else '1.0.x'} suites, not "
                          f"{(s or {}).get('id')} {(s or {}).get('version')}"))
    return out


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
                      ("declarations", "declaration_id"), ("ratio_roots", "root_id"), ("models", "model_id"),
                      ("evaluations", "evaluation_id"), ("model_roots", "root_id")):
        ids += [(kind, r.get(key)) for r in ctx.get(kind, []) if isinstance(r, dict)]
    names = [i for _, i in ids]
    for d in sorted({i for i in names if names.count(i) > 1 and isinstance(i, str)}):
        out.append(_f("context.duplicate_id", "$", f"id '{d}' is used twice in the context"))
    models = {m.get("model_id") for m in ctx.get("models", []) if isinstance(m, dict)}
    if ("spec" in ctx or not models) and item_roles.get(ctx.get("spec")) != "measurement-spec":
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
        elif "model" in ref and ref["model"] not in models:
            out.append(_f("context.unknown_reference", where, f"model {ref['model']!r} is not in the context"))
        elif not ({"instance", "item", "prediction", "model"} & set(ref)):
            out.append(_f("context.unknown_reference", where, "a reference names an instance, an item, a prediction or a model"))

    for k, root in enumerate(ctx.get("roots", [])):
        where = f"$.roots[{k}]"
        ref_ok(root.get("output"), f"{where}.output")
        ref_ok(root.get("binning"), f"{where}.binning")
        res = parse_scope(root.get("scope"), axes)
        if not res["ok"]:
            out.append(_f("context.bad_scope", f"{where}.scope", f"{root.get('scope')!r}: {res['errors']}"))
    roots = {r.get("root_id") for r in ctx.get("roots", []) if isinstance(r, dict)}
    for k, rr in enumerate(ctx.get("ratio_roots", [])):
        for side in ("numerator", "denominator"):
            if (rr.get(side) or {}).get("root") not in roots:
                out.append(_f("context.unknown_reference", f"$.ratio_roots[{k}].{side}", "a ratio operand is a root of the context"))
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
    for k, m in enumerate(ctx.get("models", [])):
        if item_roles.get(m.get("item")) != "model-card":
            out.append(_f("context.unknown_reference", f"$.models[{k}].item", f"{m.get('item')!r} is not a model-card item"))
    evals = {}
    for k, e in enumerate(ctx.get("evaluations", [])):
        evals[e.get("evaluation_id")] = e
        for x in e.get("models", []):
            if x not in models:
                out.append(_f("context.unknown_reference", f"$.evaluations[{k}].models", f"model {x!r} is not in the context"))
        for j, sp in enumerate(e.get("shared_parameters", []) or []):
            for mem in sp.get("members", []):
                if mem.get("model") not in e.get("models", []):
                    out.append(_f("context.unknown_reference", f"$.evaluations[{k}].shared_parameters[{j}]",
                                  f"member model {mem.get('model')!r} is not in this evaluation"))
    for k, r in enumerate(ctx.get("model_roots", [])):
        if r.get("evaluation") not in evals:
            out.append(_f("context.unknown_reference", f"$.model_roots[{k}].evaluation", f"{r.get('evaluation')!r} is not an evaluation"))
    for k, b in enumerate(ctx.get("bindings", [])):
        where = f"$.bindings[{k}]"
        if b.get("type") not in BINDING_TYPES:
            out.append(_f("context.unsupported_binding", f"{where}.type", f"binding type {b.get('type')!r} is not supported"))
            continue
        ref_ok(b.get("from"), f"{where}.from")
        ref_ok(b.get("to"), f"{where}.to")
        if b.get("type") == "observes" and not ("item" in (b.get("from") or {}) and "model" in (b.get("to") or {})
                                                and (b.get("to") or {}).get("aux_id")):
            out.append(_f("context.unknown_reference", where, "an observes binding goes from an item to a model's aux_id"))
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
