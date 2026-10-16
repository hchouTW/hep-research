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
    return [{"item": env.ctx.get("spec"), "pointer": f"/extension/corrections/{list(env.corrections).index(eid)}"}]


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
        same = compare_scopes(want, have, env.axes) == "equal" or want == have if spec_field == "target_scope" else want == have
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
    """('exclusive' | 'contradiction' | 'none', declaration ids) from partition_exclusive declarations."""
    for d in env.decls("partition_exclusive"):
        subs = (d.get("content") or {}).get("subsets") or []
        scopes = [s.get("scope") for s in subs if isinstance(s, dict)]
        if a in scopes and b in scopes:
            sel = {s.get("scope"): s.get("selection") for s in subs if isinstance(s, dict)}
            if sel.get(a) is not None and sel.get(a) == sel.get(b):
                return "contradiction", [d["declaration_id"]]
            return "exclusive", [d["declaration_id"]]
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
    if any(len(a) != n for a in arrays.values()):
        return outcome("unverified", "check.factor_values_incomplete", "the factor lists have different bin counts", ev)
    tol = float((doc.get("tolerance") or {}).get("relative", 1e-9))
    failed = []
    for k in range(n):
        prod = 1.0
        for ch in comp["children"]:
            prod *= float(arrays[ch["effect"]][k]) ** ch["power"]
        parent = float(arrays[comp["parent"]][k])
        if abs(parent - prod) > tol * max(abs(parent), abs(prod), 1e-300):
            failed.append(k)
    bins = {"evaluated": n, "failed": len(failed), "first_failures": failed[:5]}
    if failed:
        return outcome("violated", "check.factor_values_inconsistent",
                       f"{len(failed)} of {n} bins break {comp_id} beyond relative tolerance {tol}", ev, bins=bins)
    return outcome("satisfied", "check.factor_values_consistent", f"all {n} bins agree within {tol}", ev, bins=bins)


# --- R-RESP -----------------------------------------------------------------------------------------------------
def r_resp_response_use(ob: dict, env: Env) -> dict:
    inst_id = ob["subject"]["instance"]
    view = env.views.get(inst_id) or {}
    unfold = [s for s in view.get("steps", []) if step_state(env, inst_id, s, "migration") == "covered"]
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
                   "no migration correction, no unfolding step and no response: no response use is required", ev)


RULES = {"r-inv.root": r_inv_root, "r-map.classification": r_map_classification,
         "r-real.description": r_real_description, "r-stage.position": r_stage_position,
         "r-rep.repetition": r_rep_repetition, "r-comp.composition": r_comp_composition,
         "r-comp.factor_values": r_comp_factor_values, "r-resp.response_use": r_resp_response_use}


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
