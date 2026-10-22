"""Chain rules of the counting-chain suite (v6.3 C16): one function per rule, each turning one obligation into one
outcome {state, reason, evidence, declaration_based, declarations}. Reason codes per state are registered in
contracts/rules/registry.json; a rule the suite names but this module does not implement leaves its obligations
unverified (check.rule_not_run), and so does a rule that fails while running.

Version guard (P3): rules are dispatched by (rule_id, version). An obligation whose rule_version this checker does not
implement is never evaluated with another version's code: it stays unverified (check.rule_not_run). A fix that
changes an outcome is a new version, registered with its own source digest (contracts/rule_registry.py)."""
from __future__ import annotations

import math

from contracts.analysis_checks.context import accepted_declarations
from contracts.analysis_checks.instances import build_view
from contracts.analysis_checks.obligations import corrections as spec_corrections
from contracts.analysis_checks.scope import compare_scopes
from contracts.effect_catalog import classify
from contracts.analysis_checks import model as model_rules  # noqa: E402  (model imports this module lazily)
from contracts.analysis_checks import runs as run_rules  # noqa: E402  (runs imports this module lazily)


def outcome(state: str, reason: str, message: str = "", evidence=(), declarations=(), **extra) -> dict:
    out = {"state": state, "reason": reason, "message": message, "evidence": list(evidence),
           "declaration_based": bool(declarations) and state in ("satisfied", "not_applicable"),
           "declarations": sorted(declarations)}
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
        self.coverage = self._pinned_coverage(view)
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

    @staticmethod
    def _pinned_coverage(view: dict) -> dict:
        """Coverage per table as the D11a reader gives it through the lock's pin; without a lock (a draft) the current
        contract is read as is. A pin that does not match leaves the table without operators (unsupported)."""
        from contracts.analysis_checks.readers import read_table
        lock = view.get("lock")
        pins = {d["id"]: d.get("digest") for d in (lock or {}).get("definitions", []) if d.get("kind") == "coverage-contract"}
        out = {}
        for tid, cov in view.get("coverage", {}).items():
            doc = cov.get("doc") or {}
            if not lock:
                out[tid] = doc
                continue
            res = read_table(view.get("tables", {}).get(tid) or {}, doc, pins.get(tid))
            out[tid] = dict(doc, operators=[{k: o[k] for k in ("operator_id", "stage", "covers", "class_coverage", "factors")}
                                            for o in res["operators"].values()])
        return out

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
    if not recipe.get("estimand_kind"):
        return outcome("unverified", "check.root_incomplete", "the output instance's recipe states no estimand", ev)
    if recipe.get("estimand_kind") != root.get("quantity"):
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
    ev = correction_evidence(env, eid)
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


# --- shared: applicability, applications, location ---------------------------------------------------------------
STAGES = ("estimator", "normalization", "unfolding", "response_matrix", "response", "calibration")
RESPONSE_STAGES = ("response_matrix", "response")


def applicability(env: Env, c: dict, inst_id: str) -> tuple[str, list[str]]:
    """('yes' | 'no' | 'unbound', declaration ids): a spec target_scope equal to the instance's is an artifact fact;
    an instance_mapping declaration is declaration-based; nothing else maps a correction (no broadcast, C4)."""
    inst = env.insts.get(inst_id, {})
    ts = c.get("target_scope")
    if isinstance(ts, str):
        cmp = compare_scopes(ts, inst.get("scope"), env.axes)
        if cmp == "equal" or ts == inst.get("scope"):
            return "yes", []
        if cmp == "different":
            return "no", []
    maps = [d for d in env.decls("instance_mapping") if (d.get("content") or {}).get("correction") == c.get("effect_id")]
    if maps:
        hit = [d["declaration_id"] for d in maps if inst_id in ((d.get("content") or {}).get("instances") or [])]
        return ("yes", hit) if hit else ("no", [d["declaration_id"] for d in maps])
    return "unbound", []


def step_state(env: Env, inst_id: str, step: dict, effect: str) -> str:
    from contracts.effect_catalog import coverage_state
    return coverage_state(env.coverage_of(inst_id), str(step.get("operator")), effect, env.catalog,
                          env.table_of(env.recipe_of(env.insts.get(inst_id, {}))))["state"]


def locate(env: Env, c: dict, inst_id: str) -> tuple[str, dict | None]:
    """('one' | 'many' | 'undefined' | 'unsupported' | 'none' | 'bad_id', step): where a correction is realized."""
    view = env.views.get(inst_id) or {}
    steps = view.get("steps", [])
    cat = str(c.get("category"))
    if c.get("application_id"):
        step = next((s for s in steps if s.get("step_id") == c["application_id"]), None)
        return ("one", step) if step is not None else ("bad_id", None)
    states = [(s, step_state(env, inst_id, s, cat)) for s in steps]
    covered = [s for s, st in states if st == "covered"]
    if len(covered) == 1:
        return "one", covered[0]
    if len(covered) > 1:
        return "many", None
    if any(st == "unverified" for _, st in states):
        return "undefined", None
    if any(st == "unsupported" and s.get("operator") not in _covered_ops(env, inst_id) for s, st in states):
        return "unsupported", None
    return "none", None


def _covered_ops(env: Env, inst_id: str) -> set:
    return {o.get("operator_id") for o in env.coverage_of(inst_id).get("operators", [])}


def op_stage(env: Env, inst_id: str, operator) -> str | None:
    op = next((o for o in env.coverage_of(inst_id).get("operators", []) if o.get("operator_id") == operator), None)
    return op.get("stage") if op else None


def correction_evidence(env: Env, eid: str) -> list[dict]:
    raw = ((env.spec.get("extension") or {}).get("corrections") or []) if isinstance(env.spec, dict) else []
    idx = next((k for k, c in enumerate(raw) if isinstance(c, dict) and c.get("effect_id") == eid), None)
    return [{"item": env.ctx.get("spec"), "pointer": f"/extension/corrections/{idx}"}] if idx is not None else []


# --- R-REAL -----------------------------------------------------------------------------------------------------
def r_real_description(ob: dict, env: Env) -> dict:
    eid, inst_id = ob["subject"]["correction"], ob["subject"]["instance"]
    c = env.corrections.get(eid)
    if c is None:
        return outcome("unverified", "check.description_incomplete", "the spec correction cannot be read")
    ev = correction_evidence(env, eid)
    if c.get("applied_in") in RESPONSE_STAGES:
        return outcome("not_applicable", "check.realized_by_response",
                       "the spec places this correction in the response; R-RESP judges its use", ev)
    app, decls = applicability(env, c, inst_id)
    if app == "no":
        return outcome("not_applicable", "check.instance_out_of_scope", "the correction does not apply to this instance", ev, decls)
    if app == "unbound":
        return outcome("unverified", "check.applicability_unbound",
                       "no spec target_scope or instance_mapping binds this correction to instances (no broadcast)", ev)
    if classify(env.catalog, str(c.get("category")))["basis"] != "catalog":  # the legacy name pattern is no definition
        return outcome("unsupported", "check.unknown_effect", f"{c.get('category')!r} is not a catalog effect", ev)
    where, step = locate(env, c, inst_id)
    if where == "bad_id":
        return outcome("unverified", "check.description_incomplete",
                       f"application_id {c.get('application_id')!r} is not a step of the instance's recipe", ev)
    if where == "many":
        return outcome("unverified", "check.ambiguous_application",
                       "several steps cover this effect; an application_id selects one", ev)
    if where == "undefined":
        return outcome("unverified", "check.coverage_undefined",
                       "the operator that could realize it leaves its class members undefined", ev)
    if where == "unsupported":
        return outcome("unsupported", "check.unsupported_operator", "an operator of the instance has no coverage contract", ev)
    if where == "none":
        return outcome("violated", "check.unrealized_correction",
                       "no step of the instance realizes the correction, and every operator's coverage is defined", ev, decls)
    assert step is not None
    ev = ev + [{"instance": inst_id, "step": step.get("step_id")}]
    st = step_state(env, inst_id, step, str(c.get("category")))
    if st == "unsupported":
        return outcome("unsupported", "check.unsupported_operator", f"operator {step.get('operator')!r} has no coverage", ev)
    if st == "unverified":
        return outcome("unverified", "check.coverage_undefined", "the step's class members are undefined", ev)
    if st == "not_covered":
        return outcome("violated", "check.description_conflict",
                       f"step {step.get('step_id')!r} does not cover {c.get('category')!r}", ev, decls)
    key = _key_for(env, step, str(c.get("category")))
    for spec_field, key_field in (("target_scope", "target_scope"), ("variation_id", "variation_id"),
                                  ("calibration_digest", "calibration_digest")):
        want, have = c.get(spec_field), (key.get(key_field) or {}).get("value")
        if want is None:
            continue
        if have is None:
            return outcome("unverified", "check.description_incomplete",
                           f"the spec gives {spec_field} but the application has none to compare", ev)
        if spec_field == "target_scope" and want != have:
            rel = compare_scopes(want, have, env.axes)
            if rel in ("unknown", "invalid"):
                return outcome("unverified", "check.description_incomplete",
                               f"the spec's target_scope {want!r} cannot be compared with the application's", ev)
            same = rel == "equal"
        else:
            same = want == have
        if not same:
            return outcome("violated", "check.description_conflict",
                           f"the spec's {spec_field} differs from the application's", ev, decls)
    return outcome("satisfied", "check.description_realized", f"realized by step {step.get('step_id')!r}", ev, decls)


def _key_for(env: Env, step: dict, category: str) -> dict:
    """The correction key of the step's effect that covers this category (the class effect for a member)."""
    effects = step.get("effects", {})
    if category in effects:
        return effects[category]
    cls = classify(env.catalog, category)["class"]
    if cls in effects:
        return effects[cls]
    return next(iter(effects.values()), {}) if len(effects) == 1 else {}


# --- R-STAGE ----------------------------------------------------------------------------------------------------
def r_stage_position(ob: dict, env: Env) -> dict:
    eid, inst_id = ob["subject"]["correction"], ob["subject"]["instance"]
    c = env.corrections.get(eid)
    if c is None:
        return outcome("unverified", "check.stage_unlocated", "the spec correction cannot be read")
    ev = correction_evidence(env, eid)
    where_in = c.get("applied_in")
    if where_in not in STAGES:
        return outcome("unsupported", "check.stage_unsupported",
                       f"applied_in {where_in!r} is not a stage the suite knows {list(STAGES)}", ev)
    if where_in in RESPONSE_STAGES:
        return outcome("not_applicable", "check.realized_by_response", "the response realizes this position (R-RESP)", ev)
    app, decls = applicability(env, c, inst_id)
    if app == "no":
        return outcome("not_applicable", "check.instance_out_of_scope", "the correction does not apply to this instance", ev, decls)
    where, step = locate(env, c, inst_id)
    if where != "one" or step is None:
        return outcome("unverified", "check.stage_unlocated", "the correction is not located on one step", ev)
    stage = op_stage(env, inst_id, step.get("operator"))
    ev = ev + [{"instance": inst_id, "step": step.get("step_id")}]
    if stage is None:
        return outcome("unsupported", "check.stage_unsupported", f"operator {step.get('operator')!r} has no stage", ev)
    if stage != where_in:
        return outcome("violated", "check.stage_conflict",
                       f"the spec says {where_in!r}; step {step.get('step_id')!r} is at stage {stage!r}", ev, decls)
    return outcome("satisfied", "check.stage_consistent", f"stage {stage!r}", ev, decls)


# --- applications on a root's path -----------------------------------------------------------------------------
def path_of(env: Env, root_id: str) -> list[str]:
    from contracts.analysis_checks.obligations import path_instances
    start = ((env.roots.get(root_id) or {}).get("output") or {}).get("instance")
    return [i for i in path_instances(env.ctx, str(start)) if i in env.insts] if start in env.insts else []


def applications(env: Env, path: list[str], effect: str) -> tuple[list[dict], bool]:
    """Applications of a table effect on the path: [{instance, step, operator, scope, variation, members}], and
    whether an operator on the path has no coverage contract entry (unsupported)."""
    apps, unsupported = [], False
    for inst_id in path:
        cov_ops = {o.get("operator_id"): o for o in env.coverage_of(inst_id).get("operators", [])}
        for s in (env.views.get(inst_id) or {}).get("steps", []):
            if effect not in s.get("effects", {}):
                continue
            op = cov_ops.get(s.get("operator"))
            if op is None:
                unsupported = True
                continue
            cls_cov = (op.get("class_coverage") or {}).get(effect)
            if cls_cov is not None:
                members = None if cls_cov.get("members") is None else set(cls_cov["members"])
            elif effect in op.get("covers", []):
                members = {effect}
            else:
                continue  # the table names the effect, the coverage contract says this operator does not apply it
            key = s["effects"][effect]
            apps.append({"instance": inst_id, "step": s.get("step_id"), "operator": s.get("operator"),
                         "scope": (key.get("target_scope") or {}).get("value"),
                         "variation": (key.get("variation_id") or {}).get("value"), "members": members})
    return apps, unsupported


def _exclusion(env: Env, a: str, b: str) -> tuple[str, list[str]]:
    """('exclusive' | 'contradiction' | 'none', declaration ids) from partition_exclusive declarations. Every
    declaration naming both scopes is read, so declaration order never decides (G17): one contradicting declaration
    gives a contradiction, listing every contradicting id."""
    found: dict[str, list[str]] = {"contradiction": [], "exclusive": []}
    for d in env.decls("partition_exclusive"):
        subs = (d.get("content") or {}).get("subsets") or []
        scopes = [s.get("scope") for s in subs if isinstance(s, dict)]
        if a in scopes and b in scopes:
            sel = {s.get("scope"): s.get("selection") for s in subs if isinstance(s, dict)}
            same = sel.get(a) is not None and sel.get(a) == sel.get(b)
            found["contradiction" if same else "exclusive"].append(d["declaration_id"])
    for rel in ("contradiction", "exclusive"):
        if found[rel]:
            return rel, sorted(found[rel])
    return "none", []


# --- R-REP ------------------------------------------------------------------------------------------------------
def r_rep_repetition(ob: dict, env: Env) -> dict:
    root_id, effect = ob["subject"]["root"], ob["subject"]["effect"]
    path = path_of(env, root_id)
    apps, unsupported = applications(env, path, effect)
    ev = [{"instance": a["instance"], "step": a["step"]} for a in apps]
    if unsupported:
        return outcome("unsupported", "check.unsupported_operator", "an operator on the path has no coverage contract", ev)
    branch = _unbound_branches(env, root_id, path)
    if not apps:
        return outcome("not_applicable", "check.effect_not_applied", f"no step on the path applies {effect!r}", ev)
    worst, decls, msg = None, [], ""
    rank = {"violated": 3, "unverified": 2, "satisfied": 1}
    for i, a in enumerate(apps):
        for b in apps[i + 1:]:
            st, reason, d, m = _pair(env, a, b)
            if worst is None or rank[st] > rank[worst[0]]:
                worst, msg = (st, reason), m
            decls += d
    if worst is None or worst[0] == "satisfied":
        if branch:
            return outcome("unverified", "check.branch_unbound",
                           f"instances {branch} have the root's scope but no branch binding to it", ev)
        reason = worst[1] if worst else "check.no_repetition"
        return outcome("satisfied", reason, f"{effect!r} is applied once on the path" if not worst else msg, ev, decls)
    return outcome(worst[0], worst[1], msg, ev, decls if worst[0] == "violated" else [])


def _pair(env: Env, a: dict, b: dict) -> tuple[str, str, list[str], str]:
    if a["members"] is not None and b["members"] is not None and not (a["members"] & b["members"]):
        return "satisfied", "check.no_repetition", [], "the applications cover different members"
    cmp = compare_scopes(a["scope"], b["scope"], env.axes) if a["scope"] and b["scope"] else "unknown"
    if cmp == "invalid" and a["scope"] == b["scope"]:
        cmp = "equal"
    if cmp == "different":
        return "satisfied", "check.exclusive_scopes", [], "the applications act on disjoint scope values"
    if cmp == "invalid":
        rel, d = _exclusion(env, a["scope"], b["scope"])
        if rel == "contradiction":
            return "violated", "check.exclusion_contradiction", d, "a declared exclusion names the same selection twice"
        if rel == "exclusive":
            return "satisfied", "check.exclusive_scopes", d, "declared mutually exclusive subsets of one source"
        return "unverified", "check.scope_relation_unknown", [], f"{a['scope']!r} and {b['scope']!r} cannot be compared"
    if cmp == "unknown":
        return "unverified", "check.keys_incomplete", [], "a scope lacks an axis the other names"
    if a["members"] is None or b["members"] is None:
        return "unverified", "check.coverage_undefined", [], "the members an operator covers are undefined"
    return ("violated", "check.repeated_application", [],
            f"{a['instance']}/{a['step']} and {b['instance']}/{b['step']} apply the same members on one path and scope "
            "(variation labels and calibrations grant no exemption)")


def _unbound_branches(env: Env, root_id: str, path: list[str]) -> list[str]:
    scope = (env.roots.get(root_id) or {}).get("scope")
    return sorted(i for i, inst in env.insts.items() if i not in path and inst.get("role") == "nominal"
                  and (compare_scopes(inst.get("scope"), scope, env.axes) == "equal" or inst.get("scope") == scope))


# --- R-COMP -----------------------------------------------------------------------------------------------------
def r_comp_composition(ob: dict, env: Env) -> dict:
    root_id, comp_id = ob["subject"]["root"], ob["subject"]["composition"]
    comp = next((c for c in env.catalog.get("compositions", []) if c["composition_id"] == comp_id), None)
    if comp is None:
        return outcome("unverified", "check.coverage_undefined", f"composition {comp_id!r} is not in the catalog")
    children = {ch["effect"] for ch in comp["children"]}
    parent_steps, child_steps = [], []
    for inst_id in path_of(env, root_id):
        cov_ops = {o.get("operator_id"): o for o in env.coverage_of(inst_id).get("operators", [])}
        for s in (env.views.get(inst_id) or {}).get("steps", []):
            op = cov_ops.get(s.get("operator"))
            if op is None:
                return outcome("unsupported", "check.unsupported_operator", f"{s.get('operator')!r} has no coverage contract",
                               [{"instance": inst_id, "step": s.get("step_id")}])
            covers = set(op.get("covers", []))
            ref = {"instance": inst_id, "step": s.get("step_id")}
            if comp["parent"] in covers:
                parent_steps.append(ref)
            elif covers & children:
                child_steps.append(ref)
    ev = parent_steps + child_steps
    if parent_steps and child_steps:
        return outcome("violated", "check.decomposition_double_counted",
                       f"{comp['parent']!r} is applied and its factors are applied again on the same path", ev)
    if not parent_steps and not child_steps:
        return outcome("not_applicable", "check.composition_absent", "neither the parent nor its factors are applied", ev)
    return outcome("satisfied", "check.composition_once", "the composition is applied once on the path", ev)


def r_comp_factor_values(ob: dict, env: Env) -> dict:
    comp_id, item = ob["subject"]["composition"], ob["subject"].get("factor_table")
    comp = next((c for c in env.catalog.get("compositions", []) if c["composition_id"] == comp_id), None)
    doc = (env.items.get(item) or {}).get("doc")
    ev = [{"item": item, "pointer": "/factors"}]
    if comp is None or not isinstance(doc, dict):
        return outcome("not_applicable", "check.factor_table_absent", "no factor table is bound for this composition", ev)
    factors = doc.get("factors") or {}
    names = [comp["parent"]] + [ch["effect"] for ch in comp["children"]]
    raw = {n: (factors.get(n) or {}).get("values") for n in names}
    if any(a is None for a in raw.values()):
        return outcome("unverified", "check.factor_values_incomplete",
                       f"the factor table lacks {[n for n, a in raw.items() if a is None]}", ev)
    if not all(isinstance(a, list) and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in a)
               for a in raw.values()):
        return outcome("unsupported", "check.factor_form_unsupported",
                       "only per-bin scalar factor lists are supported (no matrices or expressions)", ev)
    arrays: dict[str, list] = {k: list(v or []) for k, v in raw.items()}
    n = len(arrays[comp["parent"]])
    if n == 0 or any(len(a) != n for a in arrays.values()):
        return outcome("unverified", "check.factor_values_incomplete", "the factor lists are empty or differ in bin count", ev)
    if not all(math.isfinite(x) for a in arrays.values() for x in a):
        return outcome("unverified", "check.factor_values_incomplete", "a factor value is not a finite number", ev)
    tol, basis = _factor_tolerance(doc, comp, arrays)
    if "tolerance" in doc:
        basis += "; the table's own tolerance is not used"
    failed = []
    for k in range(n):
        prod = 1.0
        for ch in comp["children"]:
            prod *= float(arrays[ch["effect"]][k]) ** ch["power"]
        parent = float(arrays[comp["parent"]][k])
        if abs(parent - prod) > tol * max(abs(parent), abs(prod), 1e-300):
            failed.append(k)
    bins = {"evaluated": n, "failed": len(failed), "first_failures": failed[:5]}
    tolerance = {"relative": tol, "basis": basis}
    if failed:
        return outcome("violated", "check.factor_values_inconsistent",
                       f"{len(failed)} of {n} bins break {comp_id} beyond relative tolerance {tol:.3g} ({basis})", ev,
                       bins=bins, tolerance=tolerance)
    return outcome("satisfied", "check.factor_values_consistent", f"all {n} bins agree within {tol:.3g} ({basis})", ev,
                   bins=bins, tolerance=tolerance)


DEFAULT_FACTOR_TOLERANCE = 1e-9


def _significant_digits(x) -> int:
    """Significant digits of a number as written (its shortest repr; trailing zeros are not significant)."""
    import decimal
    return len(decimal.Decimal(repr(x) if isinstance(x, float) else str(x)).normalize().as_tuple().digits)


def _factor_tolerance(doc: dict, comp: dict, arrays: dict) -> tuple[float, str]:
    """The relative tolerance of a factor relation (DR-6, G4): never the table's own 'tolerance'. Undeclared it is
    1e-9. A table declaring significant_digits d, which every value of the relation honours, gets sum|power| * u
    with u = 0.5 * 10**(1 - d), the parent's power counting 1: rounding each value to d digits moves
    parent / prod(child**power) by at most 1 - (1 - u)**sum|power| <= sum|power| * u. A declaration the values
    contradict (a value with more digits) is not used."""
    d = doc.get("significant_digits")
    if not (isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 17):
        return DEFAULT_FACTOR_TOLERANCE, "default: no significant_digits declared"
    if any(_significant_digits(x) > d for a in arrays.values() for x in a):
        return DEFAULT_FACTOR_TOLERANCE, f"default: a value has more than the declared {d} significant digits"
    total = 1 + sum(abs(ch["power"]) for ch in comp["children"])
    return max(DEFAULT_FACTOR_TOLERANCE, total * 0.5 * 10.0 ** (1 - d)), f"{d} declared significant digits, sum|power| {total}"


# --- R-RESP -----------------------------------------------------------------------------------------------------
def r_resp_response_use(ob: dict, env: Env) -> dict:
    inst_id = ob["subject"]["instance"]
    view = env.views.get(inst_id) or {}
    mstates = [(s, step_state(env, inst_id, s, "migration")) for s in view.get("steps", [])]
    unfold = [s for s, st in mstates if st == "covered"]
    if not unfold and any(st == "unsupported" for _, st in mstates):
        return outcome("unsupported", "check.response_use_unknown",
                       "an operator of the instance has no coverage contract: its use of a response is unknown",
                       [{"instance": inst_id, "step": s.get("step_id")} for s, st in mstates if st == "unsupported"])
    if not unfold and any(st == "unverified" for _, st in mstates):
        return outcome("unverified", "check.response_use_unbound", "whether an operator unfolds is undefined in its coverage",
                       [{"instance": inst_id}])
    migr = []
    for eid, c in env.corrections.items():
        if str(c.get("category")) == "migration":
            app, decls = applicability(env, c, inst_id)
            migr.append((eid, c, app, decls))
    binds = [b for b in env.ctx.get("bindings", []) if b.get("type") == "response_used_by"]
    data_side = [b for b in binds if (b.get("to") or {}).get("instance") == inst_id]
    prediction_side = [b for b in binds if "prediction" in (b.get("to") or {})]
    responses = {k: v for k, v in env.items.items() if v.get("role") == "response"}
    ev = [{"instance": inst_id, "step": s.get("step_id")} for s in unfold]
    ev += [e for eid, *_ in migr for e in correction_evidence(env, eid)]
    if unfold:
        if not data_side:
            return outcome("unverified", "check.response_use_unbound", "the unfolding step names no response_used_by binding", ev)
        for b in data_side:
            resp = (responses.get((b.get("from") or {}).get("item")) or {}).get("doc") or {}
            ext = resp.get("extension") or {}
            if ext.get("intended_use") != "unfolding" or "migration" not in (ext.get("includes") or []):
                return outcome("violated", "check.response_use_conflict",
                               "the response bound to the unfolding step is not an unfolding response with migration inside", ev)
        return outcome("satisfied", "check.response_use_consistent", "the unfolding step uses a bound unfolding response", ev)
    in_scope = [(eid, c, app, d) for eid, c, app, d in migr if app != "no"]
    excluded = sorted({x for _, _, app, d in migr if app == "no" for x in d})
    if any(c.get("applied_in") == "unfolding" and app == "yes" for _, c, app, _ in in_scope):
        decls = [x for _, c, app, d in in_scope if app == "yes" for x in d]
        return outcome("violated", "check.response_use_conflict",
                       "the spec says migration is corrected by unfolding; the instance's chain has no unfolding step",
                       ev, decls)
    for b in data_side:
        resp = (responses.get((b.get("from") or {}).get("item")) or {}).get("doc") or {}
        if (resp.get("extension") or {}).get("intended_use") == "unfolding":
            return outcome("violated", "check.response_use_conflict",
                           "a response bound for unfolding to an instance whose chain does not unfold", ev)
    if any(app == "unbound" for _, _, app, _ in in_scope):
        return outcome("unverified", "check.response_use_unbound", "a migration correction is not bound to instances", ev)
    folding = [x for x in in_scope if x[1].get("applied_in") in RESPONSE_STAGES]
    if folding:
        if prediction_side:
            return outcome("unsupported", "check.folding_unsupported",
                           "forward folding needs a folding adapter contract the suite does not have", ev)
        return outcome("unverified", "check.response_use_unbound",
                       "the spec places migration in the response, but no prediction-side response use is bound "
                       "('not_applied' only says the data side did not do it)", ev)
    if in_scope:
        return outcome("unverified", "check.response_use_unbound", "the migration correction's use cannot be established", ev)
    if responses and (prediction_side or data_side):
        return outcome("unverified", "check.response_use_unbound", "a response is bound but its use cannot be established", ev)
    if responses:
        return outcome("unverified", "check.response_use_unbound",
                       "the bundle carries responses that nothing binds to a use", ev)
    return outcome("not_applicable", "check.response_not_needed",
                   "no migration correction, no unfolding step and no response: no response use is required", ev, excluded)


# --- R-RATIO (ratio-subset/v1) ----------------------------------------------------------------------------------
RELATIONS = ("independent", "correlated", "fully_correlated")


def _ratio_parts(env: Env, rid):
    from contracts.analysis_checks.obligations import ratio_claims, spec_ratio
    rr = next((r for r in env.ctx.get("ratio_roots", []) if r.get("root_id") == rid), None)
    claims = {c["effect"]: c for c in ratio_claims(env.view)}
    return rr, spec_ratio(env.view), claims


def r_ratio_operands(ob: dict, env: Env) -> dict:
    rid = ob["subject"]["ratio_root"]
    rr, ratio, _ = _ratio_parts(env, rid)
    ev = [{"item": env.ctx.get("spec"), "pointer": "/extension/ratio"}]
    if rr is None:
        return outcome("unverified", "check.ratio_operands_unbound",
                       f"numerator {ratio.get('numerator')!r} and denominator {ratio.get('denominator')!r} are free text: "
                       "no ratio root binds them to results", ev)
    if rr.get("required") is False:
        return outcome("not_applicable", "check.ratio_not_required", "the context marks this ratio optional", ev)
    num, den = (env.roots.get((rr.get(k) or {}).get("root")) for k in ("numerator", "denominator"))
    if num is None or den is None:
        return outcome("unverified", "check.ratio_operands_unbound", "an operand is not a root of the context", ev)
    ev += [{"root": num["root_id"]}, {"root": den["root_id"]}]
    if num.get("quantity") not in CHAIN_QUANTITIES or den.get("quantity") not in CHAIN_QUANTITIES:
        return outcome("unsupported", "check.ratio_operand_unsupported", "an operand is not a chain result", ev)
    if (num.get("quantity"), num.get("unit")) != (den.get("quantity"), den.get("unit")):
        return outcome("violated", "check.ratio_operands_incompatible", "the operands differ in quantity or unit", ev)
    edges = [pointer_get((env.items.get((r.get("binning") or {}).get("item")) or {}).get("doc"),
                         (r.get("binning") or {}).get("pointer", "")) for r in (num, den)]
    if any(e is None for e in edges):
        return outcome("unverified", "check.ratio_operands_unbound", "an operand's binning cannot be resolved", ev)
    if edges[0] != edges[1]:
        return outcome("violated", "check.ratio_operands_incompatible", "the operands have different bins", ev)
    from contracts.analysis_checks.scope import parse_scope
    sa, sb = parse_scope(num.get("scope"), env.axes), parse_scope(den.get("scope"), env.axes)
    axis = rr.get("over_axis")
    if not (sa["ok"] and sb["ok"]) or set(sa["axes"]) != set(sb["axes"]) or axis not in sa["axes"]:
        return outcome("unverified", "check.ratio_operands_unbound", "the operand scopes cannot be compared on the ratio axis", ev)
    others = {k for k in sa["axes"] if k != axis}
    if any(sa["axes"][k] != sb["axes"][k] for k in others) or sa["axes"][axis] == sb["axes"][axis]:
        return outcome("violated", "check.ratio_operands_incompatible",
                       f"the operands must differ in {axis!r} only", ev)
    return outcome("satisfied", "check.ratio_operands_compatible", "two compatible chain results", ev)


def _factor_side(env: Env, root_id: str, effect: str) -> dict:
    """The factor instance one operand uses for an effect: calibration item, selector, power, values; or why not."""
    from contracts.effect_catalog import coverage_state
    cls = classify(env.catalog, effect)
    if cls["basis"] != "catalog":
        return {"status": "unsupported", "why": f"{effect!r} is not a catalog effect"}
    hits = []
    for inst_id in path_of(env, root_id):
        cov = env.coverage_of(inst_id)
        ops = {o.get("operator_id"): o for o in cov.get("operators", [])}
        table = env.table_of(env.recipe_of(env.insts[inst_id]))
        for s in (env.views.get(inst_id) or {}).get("steps", []):
            if coverage_state(cov, str(s.get("operator")), effect, env.catalog, table)["state"] == "covered":
                hits.append((inst_id, s, ops.get(s.get("operator")) or {}))
    if len(hits) != 1:
        return {"status": "unverified", "why": f"{len(hits)} steps apply {effect!r} on the operand's path"}
    inst_id, step, op = hits[0]
    powers = [f.get("power") for f in op.get("factors", []) if f.get("effect") in (effect, cls["class"])]
    if len(powers) != 1:
        return {"status": "unsupported", "why": f"operator {step.get('operator')!r} states no single power for {effect!r}"}
    cals = env.insts[inst_id].get("calibrations") or {}
    item = cals.get(effect) or cals.get(cls["class"])
    doc = (env.items.get(item) or {}).get("doc") if item else None
    entry = ((doc or {}).get("factors") or {}).get(effect) if isinstance(doc, dict) else None
    if not isinstance(entry, dict):
        return {"status": "unverified", "why": f"no calibration binds {effect!r} for the operand"}
    vals: object
    if "scalar" in entry:
        sel, vals = None, [entry["scalar"]]
    elif "by_scope" in entry:
        sel = env.insts[inst_id].get("scope")
        vals = (entry["by_scope"] or {}).get(sel)
    else:
        sel, vals = None, entry.get("values")
    if not (isinstance(vals, list) and vals and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                     and math.isfinite(v) for v in vals)):
        return {"status": "unverified", "why": f"the calibration has no finite values for {effect!r} on this side"}
    return {"status": "ok", "item": item, "selector": sel, "power": powers[0], "values": vals,
            "ref": {"instance": inst_id, "step": step.get("step_id")}}


def r_ratio_cancellation(ob: dict, env: Env) -> dict:
    rid, effect = ob["subject"]["ratio_root"], ob["subject"]["effect"]
    rr, _, claims = _ratio_parts(env, rid)
    claim = claims.get(effect)
    ev = [{"item": env.ctx.get("spec"), "pointer": "/extension/ratio/cancellations"}]
    if rr is None or claim is None:
        return outcome("unverified", "check.cancellation_unbound", "the claim or its ratio root cannot be read", ev)
    if rr.get("required") is False:
        return outcome("not_applicable", "check.cancellation_not_claimed", "the context marks this ratio optional", ev)
    if claim.get("treatment") == "approximately_cancels":
        return outcome("unverified", "check.cancellation_approximate",
                       "an approximate cancellation needs a validation record; it is never counted as exact", ev, exact=False)
    sides = [_factor_side(env, str((rr.get(k) or {}).get("root")), effect) for k in ("numerator", "denominator")]
    ev += [s["ref"] for s in sides if s.get("ref")]
    for s in sides:
        if s["status"] == "unsupported":
            return outcome("unsupported", "check.factor_undefined", s["why"], ev)
    for s in sides:
        if s["status"] != "ok":
            return outcome("unverified", "check.cancellation_unbound", s["why"], ev)
    n, d = sides
    if n["power"] != d["power"]:
        return outcome("violated", "check.cancellation_not_exact",
                       f"the factor enters with power {n['power']} and {d['power']}: a net power remains", ev, exact=False)
    if n["item"] != d["item"] or n["selector"] != d["selector"]:
        bins = None
        if len(n["values"]) == len(d["values"]):
            resid = [k for k, (a, b) in enumerate(zip(n["values"], d["values"])) if a == 0 or abs(b / a - 1.0) > 1e-12]
            bins = {"evaluated": len(n["values"]), "residual_bins": len(resid), "first_residuals": resid[:5]}
        why = ("different factor instances" if n["item"] != d["item"] else
               "the same calibration with different selections: the factor of each side remains as a ratio")
        return outcome("violated", "check.cancellation_not_exact", why, ev, exact=False, bins=bins)
    if any(v == 0 for v in n["values"]):
        return outcome("violated", "check.cancellation_domain", "the common factor is zero somewhere: it cannot cancel", ev)
    return outcome("satisfied", "check.cancellation_exact",
                   "the same factor instance, selection and power on both sides cancels exactly", ev, exact=True)


def r_ratio_correlation(ob: dict, env: Env) -> dict:
    rid, effect = ob["subject"]["ratio_root"], ob["subject"]["effect"]
    rr, _, claims = _ratio_parts(env, rid)
    claim = claims.get(effect)
    ev = [{"item": env.ctx.get("spec"), "pointer": "/extension/ratio/cancellations"}]
    if rr is None or claim is None:
        return outcome("unverified", "check.correlation_unsupported_claim", "the claim or its ratio root cannot be read", ev)
    relation = claim.get("treatment")
    if relation in ("none", "not_applicable"):
        return outcome("not_applicable", "check.correlation_not_claimed", "the spec makes no correlation claim here", ev)
    if relation not in RELATIONS:
        return outcome("unsupported", "check.correlation_relation_unsupported", f"relation {relation!r} is not supported", ev)
    operands = {(rr.get(k) or {}).get("root") for k in ("numerator", "denominator")}
    # every complete record is read, so item order never decides (G3): one contradicting record gives a violation
    incomplete = False
    agree: list[tuple[str, object]] = []
    contra: list[tuple[str, object]] = []
    for iid, it in sorted(env.items.items()):
        doc = it.get("doc")
        if it.get("role") != "validation-record" or not isinstance(doc, dict) or (doc.get("claim") or {}).get("effect") != effect:
            continue
        subjects = {s.get("root") for s in doc.get("subjects", []) if isinstance(s, dict) and s.get("version")}
        if not operands <= subjects or not all(doc.get(k) for k in ("method", "tolerance", "scope")):
            incomplete = True
            continue
        (agree if doc["claim"].get("relation") == relation else contra).append((iid, doc["claim"].get("relation")))
    if contra:
        found = ", ".join(f"{iid!r} finds {rel!r}" for iid, rel in contra)
        return outcome("violated", "check.correlation_contradicted", f"validation record {found}, the spec claims {relation!r}",
                       ev + [{"item": iid, "pointer": "/claim"} for iid, _ in contra])
    if agree:
        ids = ", ".join(repr(iid) for iid, _ in agree)
        return outcome("satisfied", "check.correlation_evidenced", f"validation record {ids} binds both operands",
                       ev + [{"item": iid, "pointer": "/subjects"} for iid, _ in agree])
    for d in env.decls("correlation"):
        c = d.get("content") or {}
        if c.get("ratio_root") == rid and c.get("effect") == effect and c.get("relation") == relation:
            if (d.get("basis") or {}).get("source") or c.get("scope"):
                return outcome("satisfied", "check.correlation_declared", "a sourced or scoped correlation declaration",
                               ev, [d["declaration_id"]])
    if incomplete:
        return outcome("unverified", "check.correlation_evidence_incomplete",
                       "a validation record names this effect but not both operands with versions, method, tolerance, scope", ev)
    return outcome("unverified", "check.correlation_unsupported_claim",
                   "a bare claim (or verification text) is not evidence: a validation record or a sourced declaration is needed", ev)


RULES = {"r-inv.root": r_inv_root, "r-map.classification": r_map_classification,
         "r-real.description": r_real_description, "r-stage.position": r_stage_position,
         "r-rep.repetition": r_rep_repetition, "r-comp.composition": r_comp_composition,
         "r-comp.factor_values": r_comp_factor_values, "r-resp.response_use": r_resp_response_use,
         "r-ratio.operands": r_ratio_operands, "r-ratio.cancellation": r_ratio_cancellation,
         "r-ratio.correlation": r_ratio_correlation}

RULES.update(model_rules.RULES)  # model-card/v1 (contracts.analysis_checks.model)
RULES.update(run_rules.RULES)  # run-lineage/v1 (contracts.analysis_checks.runs)

# The version each implementation is (P3). A fixed rule is a new version and its old code is gone: an obligation of a
# suite that names the old version stays unverified (check.rule_not_run) and is reproduced with the release that has it.
# 1.1.0 (release R2): r-rep.repetition and r-ratio.correlation read every matching declaration or record (G3, G17).
# r-comp.factor_values 1.1.0: the tolerance comes from declared significant digits, never the table (G4, DR-6).
# r-aux.use 1.1.0: an observation is its source identity plus pointer, not its item ID (G5, DR-3).
# r-run.binding 1.1.0 keeps the declaration flag whatever asserted_by says (G8, DR-1); r-run.blinding 1.1.0 applies the
# project's blinded list (G13, DR-9) and permits by lineage, not by status label (G7, DR-7); r-run.campaign 1.1.0
# requires the campaign's inputs (result binding 1.1.0) to reach the analysis (G6).
VERSIONS = {"r-rep.repetition": "1.1.0", "r-ratio.correlation": "1.1.0", "r-comp.factor_values": "1.1.0",
            "r-aux.use": "1.1.0", "r-run.binding": "1.1.0", "r-run.blinding": "1.1.0", "r-run.campaign": "1.1.0"}

# (rule_id, version) -> implementation
IMPLEMENTED = {(rid, VERSIONS.get(rid, "1.0.0")): fn for rid, fn in RULES.items()}


def implemented_versions(rule_id: str) -> list[str]:
    return sorted(v for r, v in IMPLEMENTED if r == rule_id)


def _dispatch(ob: dict, rules: dict | None):
    """(function, None) or (None, why not). A rules dict keyed by rule_id (a test double) is used as given."""
    rid, ver = str(ob.get("rule_id")), str(ob.get("rule_version"))
    if rules is not None:
        fn = rules.get(rid)
        return (fn, None) if fn is not None else (None, f"rule {rid!r} is not implemented by this checker")
    fn = IMPLEMENTED.get((rid, ver))
    if fn is not None:
        return fn, None
    have = implemented_versions(rid)
    if not have:
        return None, f"rule {rid!r} is not implemented by this checker"
    return None, f"rule {rid!r} version {ver!r} is not implemented by this checker (it implements {have}): never evaluated with another version"


class _CoverageReads(Env):
    """The evaluator's Env: records the tables whose coverage the rule being evaluated reads (A3). Rules name Env, not
    this class, so their source digests do not change."""

    coverage_read: set[str]

    def coverage_of(self, inst_id: str) -> dict:
        recipe = self.recipe_of(self.insts.get(inst_id, {}))
        self.coverage_read.add(str((recipe.get("semantics") or {}).get("table_id")))
        return super().coverage_of(inst_id)


def _bundle_coverage_flag(res: dict, env: _CoverageReads) -> dict:
    """A3 (DR-1 split, V88), check-context 1.1.0: a satisfied or not-applicable outcome that read a coverage contract
    the bundle supplied (agent-writable, not the plugin's) is declaration-based; state and reason are unchanged."""
    bundled = sorted(t for t in env.coverage_read if ((env.view.get("coverage") or {}).get(t) or {}).get("source") == "bundle")
    if not bundled or res.get("state") not in ("satisfied", "not_applicable"):
        return res
    decls = sorted(set(res.get("declarations") or []) | {f"coverage-contract:{t}" for t in bundled})
    return dict(res, declarations=decls, declaration_based=True)


def evaluate(view: dict, obligations: list[dict], rules: dict | None = None) -> list[dict]:
    env = _CoverageReads(view)
    flag_bundle_coverage = (env.ctx.get("context_version") or "1.0.0") != "1.0.0"  # A3 from check-context 1.1.0
    out = []
    for ob in obligations:
        fn, why = _dispatch(ob, rules)
        env.coverage_read = set()
        if fn is None:
            res = outcome("unverified", "check.rule_not_run", why)
        else:
            try:
                res = fn(ob, env)
            except Exception as exc:  # a failing rule is visible and never a pass
                res = outcome("unverified", "check.rule_not_run", f"the rule failed: {type(exc).__name__}: {exc}")
        if flag_bundle_coverage:
            res = _bundle_coverage_flag(res, env)
        out.append(dict(res, obligation_id=ob["obligation_id"], rule_id=ob["rule_id"]))
    return out
