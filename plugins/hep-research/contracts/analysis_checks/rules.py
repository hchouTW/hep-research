"""Chain rules of the counting-chain suite (v6.3 C16): one function per rule, each turning one obligation into one
outcome {state, reason, evidence, declaration_based, declarations}. Reason codes per state are registered in
contracts/rules/registry.json; a rule the suite names but this module does not implement leaves its obligations
unverified (check.rule_not_run), and so does a rule that fails while running."""
from __future__ import annotations

from contracts.analysis_checks.context import accepted_declarations
from contracts.analysis_checks.instances import build_view
from contracts.analysis_checks.obligations import corrections as spec_corrections
from contracts.analysis_checks.scope import compare_scopes
from contracts.effect_catalog import classify


def outcome(state: str, reason: str, message: str = "", evidence=(), declarations=(), **extra) -> dict:
    out = {"state": state, "reason": reason, "message": message, "evidence": list(evidence),
           "declaration_based": bool(declarations) and state == "satisfied", "declarations": sorted(declarations)}
    out.update(extra)
    return out


def pointer_get(doc, pointer: str):
    cur = doc
    for part in [p for p in str(pointer).split("/") if p != ""]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


class Env:
    """Everything the rules read, built once from the check view."""

    def __init__(self, view: dict):
        self.view = view
        self.ctx = view.get("context") or {}
        self.axes = self.ctx.get("scope_axes") or {}
        self.items = view.get("items", {})
        self.catalog = view.get("catalog") or {}
        self.coverage = {k: v.get("doc") or {} for k, v in view.get("coverage", {}).items()}
        self.tables = view.get("tables", {})
        self.insts = {i["instance_id"]: i for i in self.ctx.get("recipe_instances", []) if isinstance(i, dict)}
        self.roots = {r["root_id"]: r for r in self.ctx.get("roots", []) if isinstance(r, dict)}
        self.corrections = {c["effect_id"]: c for c in spec_corrections(view)}
        self.spec = (self.items.get(self.ctx.get("spec")) or {}).get("doc") or {}
        self.declarations = accepted_declarations(self.ctx)
        digests = {k: v.get("sha256") for k, v in self.items.items()}
        self.views = {}
        for k, inst in enumerate(self.ctx.get("recipe_instances", [])):
            recipe = self.recipe_of(inst)
            table = self.table_of(recipe)
            self.views[inst.get("instance_id")] = build_view(recipe, str(inst.get("recipe")), table, inst,
                                                             f"/recipe_instances/{k}", digests, self.axes)

    def recipe_of(self, inst: dict) -> dict:
        doc = (self.items.get(inst.get("recipe")) or {}).get("doc")
        return doc if isinstance(doc, dict) else {}

    def table_of(self, recipe: dict) -> dict:
        return self.tables.get((recipe.get("semantics") or {}).get("table_id")) or {}

    def coverage_of(self, inst_id: str) -> dict:
        recipe = self.recipe_of(self.insts.get(inst_id, {}))
        return self.coverage.get((recipe.get("semantics") or {}).get("table_id")) or {}

    def decls(self, dtype: str) -> list[dict]:
        return [d for d in self.declarations if d.get("type") == dtype]


# --- R-INV ------------------------------------------------------------------------------------------------------
CHAIN_QUANTITIES = ("differential_flux", "integrated_flux", "counts")


def r_inv_root(ob: dict, env: Env) -> dict:
    root = env.roots.get(ob["subject"]["root"])
    if root is None:
        return outcome("unverified", "check.root_incomplete", "the root is not in the context")
    ev = [{"item": "check-context", "pointer": f"/roots/{list(env.roots).index(root['root_id'])}"}]
    if root.get("required") is False:
        return outcome("not_applicable", "check.root_not_required", "the context marks this root optional", ev)
    if root.get("quantity") not in CHAIN_QUANTITIES:
        return outcome("unsupported", "check.root_mode_unsupported",
                       f"quantity {root.get('quantity')!r} is outside the chain suite {list(CHAIN_QUANTITIES)}", ev)
    inst = env.insts.get((root.get("output") or {}).get("instance"))
    if inst is None:
        return outcome("unverified", "check.root_incomplete", "the root's output instance is missing", ev)
    recipe = env.recipe_of(inst)
    if recipe.get("estimand_kind") and recipe.get("estimand_kind") != root.get("quantity"):
        return outcome("violated", "check.root_output_conflict",
                       f"the root asks for {root.get('quantity')!r}; its instance's recipe produces {recipe.get('estimand_kind')!r}", ev)
    cmp = compare_scopes(root.get("scope"), inst.get("scope"), env.axes)
    if cmp == "different":
        return outcome("violated", "check.root_scope_conflict", "the root's scope differs from its output instance's", ev)
    binning = root.get("binning") or {}
    if cmp != "equal" or pointer_get((env.items.get(binning.get("item")) or {}).get("doc"), binning.get("pointer", "")) is None:
        return outcome("unverified", "check.root_incomplete",
                       "the scope or binning of the root cannot be established from the artifacts", ev)
    return outcome("satisfied", "check.root_complete", "estimand, binning, scope and output are bound", ev)


# --- R-MAP ------------------------------------------------------------------------------------------------------
def r_map_classification(ob: dict, env: Env) -> dict:
    eid = ob["subject"]["correction"]
    c = env.corrections.get(eid)
    if c is None:
        return outcome("unverified", "check.correction_missing", "the spec correction cannot be read")
    idx = list(env.corrections).index(eid)
    ev = [{"item": env.ctx.get("spec"), "pointer": f"/extension/corrections/{idx}"}]
    if c.get("exact_zero") is True:
        return outcome("not_applicable", "check.correction_exact_zero", "the correction is exactly zero", ev)
    cls = classify(env.catalog, str(c.get("category")))
    if cls["basis"] is None:
        return outcome("unsupported", "check.unknown_effect", f"category {c.get('category')!r} is not a catalog effect", ev)
    if cls["basis"] == "legacy-pattern":
        return outcome("unverified", "check.classified_by_legacy_pattern",
                       f"{c.get('category')!r} matches the legacy '<x>_efficiency' pattern but is not in the catalog", ev)
    parent = c.get("factor_of")
    if parent:
        comps = [k for k in env.catalog.get("compositions", []) if k["parent"] == parent]
        if comps and not any(c.get("category") in {ch["effect"] for ch in k["children"]} for k in comps):
            return outcome("violated", "check.classification_conflict",
                           f"{c.get('category')!r} is described as a factor of {parent!r}, which the catalog does not compose from it", ev)
    return outcome("satisfied", "check.classified", f"{c.get('category')!r} is a catalog effect", ev)


RULES = {"r-inv.root": r_inv_root, "r-map.classification": r_map_classification}


def evaluate(view: dict, obligations: list[dict], rules: dict | None = None) -> list[dict]:
    rules = RULES if rules is None else rules
    env = Env(view)
    out = []
    for ob in obligations:
        fn = rules.get(str(ob.get("rule_id")))
        if fn is None:
            res = outcome("unverified", "check.rule_not_run", f"rule {ob.get('rule_id')!r} is not implemented by this checker")
        else:
            try:
                res = fn(ob, env)
            except Exception as exc:  # a failing rule is visible and never a pass
                res = outcome("unverified", "check.rule_not_run", f"the rule failed: {type(exc).__name__}: {exc}")
        out.append(dict(res, obligation_id=ob["obligation_id"], rule_id=ob["rule_id"]))
    return out
