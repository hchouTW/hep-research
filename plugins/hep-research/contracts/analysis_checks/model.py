"""Model rules of the model-card suite (v6.3 M2b, C7; design docs/dev/cross-artifact-check/m2b-model-design.md): the O03 pairings
(contracts/semantics/model_pairings.json), observation use within one evaluation (R-AUX) and cross-model sharing.

A model is a model-card item under a context ID; a parameter is (model, name); an observation is (item, JSON pointer),
so two components of one file are two observations and a shared digest merges nothing. An evaluation is one likelihood:
one card, or several multiplied, whose cross-model shared parameters are listed explicitly. Within an evaluation each
constraint term must encode a different observation: a parameter shared by several samples or channels is one term,
and so is a cross-model shared parameter. Joint evaluations of several cards are unsupported in v1 (no combiner
contract), but a repeated observation in one is still a violation: double counting is decidable without a combiner."""
from __future__ import annotations

from contracts.analysis_checks.context import accepted_declarations

AUX_KIND = "auxiliary-measurement"


def outcome(state, reason, message="", evidence=(), declarations=(), **extra):
    from contracts.analysis_checks.rules import outcome as _outcome
    return _outcome(state, reason, message, evidence, declarations, **extra)


# --- reading cards ------------------------------------------------------------------------------------------------
def card_shape(doc) -> list[str]:
    """Structural problems of a model card the rules cannot read past. Modifier types and constraint forms are not
    checked against an enum here: an unlisted pairing must reach r-model.pairing as unsupported, never as invalid."""
    if not isinstance(doc, dict):
        return ["a model card is a JSON object"]
    out = []
    if not isinstance(doc.get("poi"), str) or not doc["poi"]:
        out.append("poi is a parameter name")
    for key in ("channels", "samples", "constraints"):
        if not (isinstance(doc.get(key), list) and all(isinstance(x, dict) for x in doc[key])):
            out.append(f"{key} is a list of objects")
    if out:
        return out
    names = [c.get("name") for c in doc["channels"]]
    if not all(isinstance(n, str) and n for n in names) or len(set(names)) != len(names):
        out.append("channel names are unique strings")
    for k, s in enumerate(doc["samples"]):
        if s.get("channel") not in names:
            out.append(f"samples[{k}].channel is not a channel of the card")
        mods = s.get("modifiers")
        if not (isinstance(mods, list) and all(isinstance(m, dict) and isinstance(m.get("type"), str)
                                               and isinstance(m.get("parameter"), str) and m["parameter"] for m in mods)):
            out.append(f"samples[{k}].modifiers are objects with a type and a parameter")
    for k, c in enumerate(doc["constraints"]):
        if not (isinstance(c.get("parameter"), str) and c["parameter"] and isinstance(c.get("aux_id"), str) and c["aux_id"]):
            out.append(f"constraints[{k}] names a parameter and an aux_id")
    return out


def card(view: dict, model_id: str) -> dict | None:
    m = next((m for m in (view.get("context") or {}).get("models", []) if isinstance(m, dict) and m.get("model_id") == model_id), None)
    doc = (view.get("items", {}).get(m.get("item")) or {}).get("doc") if m else None
    return doc if isinstance(doc, dict) and not card_shape(doc) else None


def parameters(doc: dict) -> list[str]:
    names = {m["parameter"] for s in doc.get("samples", []) for m in s.get("modifiers", [])}
    return sorted(names | {c["parameter"] for c in doc.get("constraints", [])})


def uses(doc: dict, param: str) -> list[tuple[str, dict]]:
    return [(s.get("channel"), m) for s in doc.get("samples", []) for m in s.get("modifiers", []) if m.get("parameter") == param]


def constraints_of(doc: dict, param: str) -> list[dict]:
    return [c for c in doc.get("constraints", []) if c.get("parameter") == param]


def evaluation(ctx: dict, eid: str) -> dict | None:
    return next((e for e in ctx.get("evaluations", []) if isinstance(e, dict) and e.get("evaluation_id") == eid), None)


# --- obligation subjects (used by contracts.analysis_checks.obligations) -----------------------------------------
def subjects(kind: str, view: dict) -> list[tuple[str, dict]]:
    """Subjects from the intent only: model roots, card parameters and constraints, evaluations and their shared
    parameters. Bindings and declarations are never read, so masking one cannot remove an obligation."""
    ctx = view.get("context") or {}
    models = sorted(m["model_id"] for m in ctx.get("models", []) if isinstance(m, dict) and isinstance(m.get("model_id"), str))
    evals = sorted((e for e in ctx.get("evaluations", []) if isinstance(e, dict) and isinstance(e.get("evaluation_id"), str)),
                   key=lambda e: e["evaluation_id"])
    if kind == "model_root":
        return sorted((r["root_id"], {"model_root": r["root_id"]}) for r in ctx.get("model_roots", [])
                      if isinstance(r, dict) and isinstance(r.get("root_id"), str))
    if kind == "model_parameter":
        out = []
        for m in models:
            doc = card(view, m)
            out += [(f"{m}#{p}", {"model": m, "parameter": p}) for p in parameters(doc)] if doc else []
        return out
    if kind == "aux_constraint":
        out = []
        for e in evals:
            for m in sorted({x for x in e.get("models", []) if x in models}):
                doc = card(view, m)
                for aux in sorted({c["aux_id"] for c in (doc or {}).get("constraints", [])}):
                    out.append((f"{e['evaluation_id']}#{m}/{aux}", {"evaluation": e["evaluation_id"], "model": m, "aux_id": aux}))
        return out
    if kind == "shared_parameter":
        out = []
        for e in evals:
            if len(set(e.get("models", []))) > 1:
                out.append((f"{e['evaluation_id']}#combination", {"evaluation": e["evaluation_id"], "combination": True}))
                out += [(f"{e['evaluation_id']}#{p['parameter_id']}", {"evaluation": e["evaluation_id"], "parameter_id": p["parameter_id"]})
                        for p in sorted(e.get("shared_parameters", []), key=lambda p: str(p.get("parameter_id")))
                        if isinstance(p, dict) and isinstance(p.get("parameter_id"), str)]
        return out
    return []


# --- r-model.root ---------------------------------------------------------------------------------------------
def r_model_root(ob: dict, env) -> dict:
    view = env.view
    ctx = view.get("context") or {}
    rid = ob["subject"]["model_root"]
    root = next(r for r in ctx.get("model_roots", []) if r.get("root_id") == rid)
    ev = [{"root": rid}]
    e = evaluation(ctx, str(root.get("evaluation")))
    poi = root.get("poi") or {}
    if e is None:
        return outcome("unverified", "check.model_root_incomplete", f"evaluation {root.get('evaluation')!r} is not in the context", ev)
    if poi.get("model") not in e.get("models", []):
        return outcome("violated", "check.model_root_mismatch", f"the POI's model {poi.get('model')!r} is not in the evaluation", ev)
    doc = card(view, str(poi.get("model")))
    if doc is None:
        return outcome("unverified", "check.model_root_incomplete", "the POI's model card cannot be read", ev)
    if poi.get("parameter") != doc.get("poi"):
        return outcome("violated", "check.model_root_mismatch",
                       f"the root's POI {poi.get('parameter')!r} is not the card's POI {doc.get('poi')!r}", ev)
    return outcome("satisfied", "check.model_root_complete", "the root names its evaluation and the card's POI", ev)


# --- r-model.pairing ------------------------------------------------------------------------------------------
WIDTH_TOL = 1e-9  # the adapter's tolerance for hi/lo against 1 +- width


def _contract(view: dict) -> dict:
    return {p["modifier"]: p for p in (view.get("pairings") or {}).get("pairings", []) if isinstance(p, dict)}


def r_model_pairing(ob: dict, env) -> dict:
    view = env.view
    m, p = ob["subject"]["model"], ob["subject"]["parameter"]
    doc = card(view, m)
    ev = [{"model": m, "parameter": p}]
    if doc is None:
        return outcome("unverified", "check.pairing_unreadable", "the model card cannot be read", ev)
    used, cons = uses(doc, p), constraints_of(doc, p)
    if not used:
        return outcome("not_applicable", "check.pairing_unused", "a constraint on a parameter no modifier uses", ev)
    types = sorted({mod["type"] for _, mod in used})
    channels = sorted({ch for ch, _ in used})
    extra = {"channels": channels, "constraints": len(cons)}
    if len(types) > 1:
        return outcome("violated", "check.pairing_invalid", f"one parameter with modifier types {types}", ev, **extra)
    pairing = _contract(view).get(types[0])
    if pairing is None:
        return outcome("unsupported", "check.pairing_unsupported",
                       f"modifier type {types[0]!r} is not in the pairing contract", ev, **extra)
    want = pairing.get("constraint")
    if want is None:
        if types[0] == "poi" and p != doc.get("poi"):
            return outcome("violated", "check.pairing_invalid", f"a poi modifier on {p!r}, which is not the card's POI", ev, **extra)
        if cons:
            return outcome("unsupported", "check.pairing_unsupported",
                           f"a constraint on a {types[0]} parameter is not a listed pairing", ev, **extra)
        return outcome("satisfied", "check.pairing_supported", f"{pairing['id']}: {types[0]} -> {pairing.get('backend')}",
                       ev, pairing=pairing["id"], **extra)
    if not cons:
        return outcome("violated", "check.pairing_invalid", "a constrained normalization without a constraint term", ev, **extra)
    if len(cons) > 1:
        return outcome("violated", "check.pairing_invalid", f"{len(cons)} constraint terms for one parameter", ev, **extra)
    c = cons[0]
    if (c.get("kind"), c.get("form")) != (want.get("kind"), want.get("form")):
        return outcome("unsupported", "check.pairing_unsupported",
                       f"constraint {c.get('kind')}/{c.get('form')} is not listed (only {want.get('kind')}/{want.get('form')})",
                       ev, **extra)
    w = c.get("width")
    for ch, mod in used:
        if "hi" in mod and "lo" in mod:
            if not all(isinstance(mod[k], (int, float)) for k in ("hi", "lo")):
                return outcome("violated", "check.pairing_invalid", "hi and lo are numbers", ev, **extra)
            if isinstance(w, (int, float)) and (abs(mod["hi"] - 1.0 - w) > WIDTH_TOL or abs(1.0 - mod["lo"] - w) > WIDTH_TOL):
                return outcome("violated", "check.pairing_invalid",
                               f"in {ch!r}, hi/lo ({mod['hi']}, {mod['lo']}) disagree with the constraint width {w}", ev, **extra)
        elif not (isinstance(w, (int, float)) and 0 < w < 1):
            return outcome("violated", "check.pairing_invalid",
                           f"in {ch!r}, neither hi/lo nor a constraint width in (0, 1) describes the variation", ev, **extra)
    return outcome("satisfied", "check.pairing_supported",
                   f"{pairing['id']}: one {want.get('form')} constraint, {pairing.get('backend')} in {len(channels)} channel(s)",
                   ev, pairing=pairing["id"], **extra)


# --- r-aux.use (R-AUX) ----------------------------------------------------------------------------------------
def _observations(ctx: dict, model: str, aux: str) -> tuple[set, list[str]]:
    """The observations (item, pointer) bound to a model's aux_id: observes bindings, else provenance_binding
    declarations (declaration-based). A source claim alone binds nothing."""
    obs = {(str(b["from"].get("item")), str(b["from"].get("pointer", ""))) for b in ctx.get("bindings", [])
           if isinstance(b, dict) and b.get("type") == "observes" and isinstance(b.get("from"), dict)
           and isinstance(b.get("to"), dict) and b["to"].get("model") == model and b["to"].get("aux_id") == aux
           and b["from"].get("item")}
    if obs:
        return obs, []
    decls = [d for d in accepted_declarations(ctx) if d.get("type") == "provenance_binding"
             and (d.get("content") or {}).get("model") == model and (d.get("content") or {}).get("aux_id") == aux
             and (d.get("content") or {}).get("item")]
    return ({(str(d["content"]["item"]), str(d["content"].get("pointer", ""))) for d in decls},
            sorted(d["declaration_id"] for d in decls))


def _source(view: dict, item: str) -> tuple:
    """The source identity of an observation's item (DR-3, G5): an artifact envelope's artifact_id, else the item's
    frozen digest (canonical JSON, or the bytes of another file), so a copy under another item ID is the same source.
    Values are never compared: a copy with one key added is a different source (known limitation)."""
    it = (view.get("items") or {}).get(item) or {}
    doc = it.get("doc")
    if isinstance(doc, dict) and doc.get("contract_version") and doc.get("artifact_id"):
        return ("artifact", str(doc["artifact_id"]))
    if it.get("sha256"):
        return ("digest", str(it["sha256"]))
    return ("item", item)


def _overlap(a: tuple, b: tuple, view: dict | None = None) -> str:
    """same, overlap (one pointer contains the other) or distinct; with a view, items compare by source identity."""
    if (a[0] != b[0]) if view is None else (_source(view, a[0]) != _source(view, b[0])):
        return "distinct"
    if a[1] == b[1]:
        return "same"
    pa, pb = a[1].rstrip("/") + "/", b[1].rstrip("/") + "/"
    return "overlap" if pa.startswith(pb) or pb.startswith(pa) else "distinct"


def _term(e: dict, model: str, param: str) -> tuple:
    """The constraint term a (model, parameter) belongs to in an evaluation: a cross-model shared parameter is one."""
    for sp in e.get("shared_parameters", []) or []:
        if {"model": model, "parameter": param} in (sp.get("members") or []):
            return ("shared", sp.get("parameter_id"))
    return ("own", model, param)


def r_aux_use(ob: dict, env) -> dict:
    view = env.view
    ctx = view.get("context") or {}
    eid, m, aux = ob["subject"]["evaluation"], ob["subject"]["model"], ob["subject"]["aux_id"]
    e = evaluation(ctx, eid) or {}
    ev: list[dict] = [{"evaluation": eid, "model": m, "aux_id": aux}]
    doc = card(view, m)
    if doc is None:
        return outcome("unverified", "check.aux_unbound", "the model card cannot be read", ev)
    mine = [c for c in doc["constraints"] if c["aux_id"] == aux]
    if all(c.get("kind") != AUX_KIND for c in mine):
        return outcome("not_applicable", "check.aux_prior", "a prior encodes no auxiliary observation", ev)
    if len({_term(e, m, c["parameter"]) for c in mine}) > 1:
        return outcome("violated", "check.aux_repeated",
                       f"aux_id {aux!r} constrains {sorted(c['parameter'] for c in mine)}: one observation entering twice", ev)
    obs, decls = _observations(ctx, m, aux)
    if not obs:
        return outcome("unverified", "check.aux_unbound", "no observes binding names this constraint's observation", ev)
    if len(obs) > 1:
        return outcome("unverified", "check.aux_binding_ambiguous", f"bound to {len(obs)} observations", ev, decls)
    me = next(iter(obs))
    ev.append({"item": me[0], "pointer": me[1]})
    my_term = _term(e, m, mine[0]["parameter"])
    unknown, overlap, used_decls = [], [], list(decls)
    for om in sorted(set(e.get("models", []))):
        odoc = card(view, om)
        if odoc is None:
            unknown.append(f"{om} (card unreadable)")
            continue
        for c in odoc["constraints"]:
            if c.get("kind") != AUX_KIND or (om, c["aux_id"]) == (m, aux) or _term(e, om, c["parameter"]) == my_term:
                continue
            other, od = _observations(ctx, om, c["aux_id"])
            if not other:
                unknown.append(f"{om}/{c['aux_id']}")
                continue
            used_decls += od
            rel = {_overlap(me, o, view) for o in other}
            if "same" in rel:
                return outcome("violated", "check.aux_repeated",
                               f"{om}/{c['aux_id']} encodes the same observation in this evaluation", ev, used_decls)
            if "overlap" in rel:
                overlap.append(f"{om}/{c['aux_id']}")
    if overlap:
        return outcome("unverified", "check.aux_overlap_unknown",
                       f"overlapping components of one source with {sorted(overlap)}: a repeat cannot be ruled out", ev)
    if unknown:
        return outcome("unverified", "check.aux_repeat_unknown",
                       f"unbound constraints in the evaluation ({sorted(unknown)}): a repeat cannot be ruled out", ev)
    return outcome("satisfied", "check.aux_single_use", "the observation enters this evaluation through one constraint term",
                   ev, sorted(set(used_decls)))


# --- r-share.parameters ---------------------------------------------------------------------------------------
def _describe(doc: dict, param: str):
    used = uses(doc, param)
    if not used:
        return None
    cons = constraints_of(doc, param)
    return {"types": sorted({mod["type"] for _, mod in used}),
            "constraints": sorted((c.get("kind"), c.get("form"), c.get("width")) for c in cons),
            "variations": sorted({(mod.get("hi"), mod.get("lo")) for _, mod in used})}


def r_share_parameters(ob: dict, env) -> dict:
    view = env.view
    ctx = view.get("context") or {}
    eid = ob["subject"]["evaluation"]
    e = evaluation(ctx, eid) or {}
    ev = [{"evaluation": eid}]
    if ob["subject"].get("combination"):
        return outcome("unsupported", "check.joint_unsupported",
                       f"a joint evaluation of {len(set(e.get('models', [])))} model cards has no backend contract in model-card/v1 (O03)", ev)
    pid = ob["subject"]["parameter_id"]
    sp: dict = next((p for p in e.get("shared_parameters", []) if p.get("parameter_id") == pid), {})
    descs = []
    for mem in sp.get("members", []):
        doc = card(view, str(mem.get("model"))) if mem.get("model") in e.get("models", []) else None
        d = _describe(doc, str(mem.get("parameter"))) if doc else None
        if d is None:
            return outcome("unverified", "check.share_unbound",
                           f"{mem.get('model')!r} has no parameter {mem.get('parameter')!r} in this evaluation", ev)
        descs.append(d)
    if any(d != descs[0] for d in descs[1:]):
        return outcome("violated", "check.share_incompatible",
                       "the shared members differ in modifier type, constraint or variation: the merge is rejected", ev)
    return outcome("unsupported", "check.share_unsupported",
                   "compatible members, but model-card/v1 has no backend contract for merging parameters across cards (O03)", ev)


RULES = {"r-model.root": r_model_root, "r-model.pairing": r_model_pairing, "r-aux.use": r_aux_use,
         "r-share.parameters": r_share_parameters}
