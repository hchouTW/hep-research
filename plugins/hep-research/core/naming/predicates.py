"""The ten predicates of the semantic naming engine (spec §7.6).

A predicate judges one entity under one rule and returns (reason_code, issue, extra): the engine maps the reason code
to one of the five states through the rule's outcome contract, so a predicate never names a state itself. extra may
hold "proposed", "evidence" (list of strings), "locations" (where the problem is seen) and "related" (entity ids the
judgement involves, for the reporting scope). Waivers and the kinds a rule covers are applied by the engine first.

forbidden, pattern, vocabulary, uniqueness, pairing, reference, declared-match and status-honesty are deterministic;
similarity is heuristic and never gives violated (I1: names alike are a question, not a finding); semantic reads the
agent's annotations and decides only at high confidence. Standard library only.
"""
from __future__ import annotations

import re

from core.naming.tokens import content_tokens, tokenize

FILE_SURFACES = ("N2", "N14")


def _fixed(e, ctx) -> list[str]:
    kind = ctx.surface(e["surface"])["kinds"].get(e["entity_kind"], {})
    return list(kind.get("fixed_names", []))


def entity_tokens(e, ctx, include_glossary: bool = True) -> list[str]:
    cache = ctx.__dict__.setdefault("_tokens", {})
    key = (e["entity_id"], include_glossary)
    if key not in cache:
        protected = ctx.vocab.protected(_fixed(e, ctx), include_glossary=include_glossary)
        cache[key] = tokenize(e["name"], protected, strip_extension=e["surface"] in FILE_SURFACES)
    return cache[key]


def forbidden(e, rule, ctx):
    if e["name"] in _fixed(e, ctx):
        return "naming.fixed_name", f"{e['name']} is fixed by an external tool", {}
    table = ctx.forbidden
    if e["name"] in table["whole_names"] or e["name"].lower() in table["whole_names"]:
        return "naming.forbidden_whole_name", f"the whole name {e['name']} is in the forbidden table", \
            {"evidence": ["core/naming/data/forbidden.json whole_names"]}
    toks = content_tokens(entity_tokens(e, ctx, include_glossary=False))
    generic = set(table["generic_tokens"])
    if toks and all(t.lower() in generic for t in toks):
        return "naming.generic_tokens_only", f"every word of {e['name']} is generic ({', '.join(toks)})", \
            {"evidence": ["core/naming/data/forbidden.json generic_tokens"]}
    return "naming.not_generic", "", {}


def pattern(e, rule, ctx):
    params = rule.get("params", {})
    target = e["name"]
    if params.get("on") == "stem":
        target = re.sub(r"(\.[A-Za-z0-9]{1,8})+$", "", target) or target
    if "must_not_match" in params:
        if re.search(params["must_not_match"], target):
            return params.get("violated_code", "naming.format_mismatch"), params.get(
                "issue", f"{e['name']} matches {params['must_not_match']}"), {}
        return "naming.format_ok", "", {}
    fmt = ctx.surface(e["surface"])["kinds"].get(e["entity_kind"], {}).get("format")
    if not fmt:
        return "naming.no_format", "", {}
    if re.fullmatch(fmt, e["name"]):
        return "naming.format_ok", "", {}
    return "naming.format_mismatch", f"{e['name']} does not match the {e['entity_kind']} format {fmt}", \
        {"evidence": [f"contracts/naming/surfaces.json {e['surface']} kinds.{e['entity_kind']}.format"]}


def vocabulary(e, rule, ctx):
    toks = content_tokens(entity_tokens(e, ctx))
    unresolved = [t for t in toks if ctx.vocab.resolve(t) is None]
    if unresolved:
        return "naming.token_unresolved", f"{', '.join(unresolved)} in {e['name']} resolves in no vocabulary layer", \
            {"evidence": ["glossary, profile vocabulary, core/naming/data, word shape"]}
    return "naming.tokens_resolve", "", {}


def _container_key(e, within: str):
    """Where two declarations of one name and one kind collide."""
    s = e["scope"]
    if within == "file":
        return (e["surface"], e["entity_kind"], s["file"])
    if within == "surface":
        return (e["surface"], e["entity_kind"])
    return (e["surface"], e["entity_kind"], s["file"], s["container"])


def uniqueness(e, rule, ctx):
    if e["change"] == "removed":
        return "naming.removed", "", {}
    if e["references_status"] != "complete":
        return "naming.references_partial", "references were not fully searched", {}
    if rule.get("params", {}).get("by") == "concept":
        cid = (e.get("meaning") or {}).get("concept_id")
        if not cid:
            return "naming.unique", "", {}
        same = [x for x in ctx.entities_in(e["surface"]) if x is not e and x["change"] != "removed"
                and (x.get("meaning") or {}).get("concept_id") == cid and x["name"] != e["name"]]
        if same:
            return "naming.duplicate_record", f"{e['name']} and {', '.join(sorted({x['name'] for x in same}))} name one " \
                f"record ({cid})", {"related": [x["entity_id"] for x in same],
                                    "evidence": [f"{x['scope']['file']}:{x['scope']['span'][0]}" for x in same]}
        return "naming.unique", "", {}
    within = rule.get("params", {}).get("within", "container")
    groups = ctx.__dict__.setdefault("_groups", {})
    if within not in groups:
        g: dict[tuple, list] = {}
        for x in ctx.entities:
            if x["change"] != "removed":
                g.setdefault(_container_key(x, within) + (x["name"],), []).append(x)
        groups[within] = g
    dups = [x for x in groups[within].get(_container_key(e, within) + (e["name"],), []) if x is not e]
    if dups:
        return "naming.duplicate_name", f"{e['name']} is declared {len(dups) + 1} times in {e['scope']['container']}", \
            {"related": [x["entity_id"] for x in dups],
             "evidence": [f"also declared at {x['scope']['file']}:{x['scope']['span'][0]}" for x in dups]}
    return "naming.unique", "", {}


def pairing(e, rule, ctx):
    params = rule.get("params", {})
    for s in params.get("needs", []):
        if s not in ctx.inventories:
            return "naming.inventory_missing", f"the {s} inventory is needed and was not supplied", {}
    suffixes = params.get("suffixes", ["Up", "Down"])
    if params.get("via") == "targets":
        if e["change"] == "removed":
            return "naming.not_paired", "", {}
        derived = [(t, hits) for t, hits in ctx.targets.get(e["entity_id"], []) if t.get("derived")]
        if not derived:
            return "naming.not_paired", "", {}
        missing = [f"{t['name']}" + (f" in {t['file']}" if t.get("file") else "") for t, hits in derived if not hits]
        if missing:
            return "naming.pair_missing", f"{e['name']} needs {', '.join(missing[:6])}, which the " \
                f"{derived[0][0]['surface']} inventory does not hold", {"evidence": [f"{derived[0][0]['surface']} inventory"]}
        return "naming.pair_complete", "", {}
    hit = next((s for s in suffixes if e["name"].endswith(s) and len(e["name"]) > len(s)), None)
    if hit is None or e["change"] == "removed":
        return "naming.not_paired", "", {}
    base = e["name"][:-len(hit)]
    names = {x["name"] for x in ctx.entities_in(e["surface"])
             if x["scope"]["file"] == e["scope"]["file"] and x["scope"]["container"] == e["scope"]["container"]
             and x["change"] != "removed"}
    missing = [base + s for s in suffixes if base + s not in names]
    if missing:
        return "naming.pair_missing", f"{e['name']} has no partner {', '.join(missing)}", {"proposed": None}
    return "naming.pair_complete", "", {}


def reference(e, rule, ctx):
    if e["change"] == "removed":
        alive = [x for x in ctx.by_name.get((e["surface"], e["name"]), []) if x["change"] != "removed"]
        if e["references"] and not alive:
            locs = [r["from"] for r in e["references"]]
            return "naming.reference_to_removed", f"{e['name']} was removed and is still referenced", \
                {"locations": locs, "related": [r["from"] for r in e["references"] if r["from"] in ctx.by_id]}
    if e["change"] != "removed":
        for t, hits in ctx.targets.get(e["entity_id"], []):
            if t.get("derived"):
                continue  # a name derived from this one (a shape histogram) is the pairing rule's
            if t["surface"] not in ctx.inventories:
                return "naming.target_inventory_missing", \
                    f"{e['name']} refers to {t['surface']} {t['name']}; no {t['surface']} inventory was supplied", {}
            if not hits:
                where = f" in {t['file']}" if t.get("file") else ""
                return "naming.target_missing", f"{e['name']} refers to {t['surface']} {t['name']}{where}, which no " \
                    f"{t['surface']} entity declares", {"evidence": [f"{t['surface']} inventory"]}
    if e["references_status"] != "complete":
        return "naming.references_partial", "references were not fully searched", {}
    return "naming.references_resolve", "", {}


def _members(decl) -> list[dict] | None:
    sources = decl.get("sources") if isinstance(decl, dict) else None
    if decl.get("declaration") is None or not isinstance(sources, list):
        return None
    if not all(isinstance(s, dict) and isinstance(s.get("members"), list) and "id" in s for s in sources):
        return None
    return sources


def _member_of(e, member: str) -> bool:
    """A member is an entity id, "<container>/<name>" or a bare name (every entity of that name)."""
    if "/" not in member and ":" not in member:
        return e["name"] == member
    return member in (e["entity_id"], f"{e['scope']['container']}/{e['name']}")


def declared_match(e, rule, ctx):
    name = rule.get("params", {}).get("declaration", "correlation-inventory")
    if name == "glossary":
        return _glossary_match(e, rule, ctx)
    decl = ctx.declarations.get(name)
    if decl is None:
        return "naming.declaration_missing", f"no {name} declaration was supplied", {}
    sources = _members(decl)
    if sources is None:
        return "naming.declaration_format_unknown", f"the {name} declaration has no sources with members", {}
    pool = ctx.entities_in(e["surface"])

    def resolve(member):
        return [x for x in pool if _member_of(x, member) and x["change"] != "removed"]
    mine = [s for s in sources if any(_member_of(e, m) for m in s["members"])]
    if not mine:
        return "naming.no_shared_sources", "", {}
    for s in mine:
        found = [resolve(m) for m in s["members"]]
        if any(not f for f in found):
            return "naming.workspace_partial", f"source {s['id']} lists a member the inventory does not hold", {}
        others = [x for f in found for x in f if x is not e]
        if s.get("correlated", True):
            differ = [x for x in others if x["name"] != e["name"]]
            if differ:
                return "naming.correlated_names_differ", \
                    f"{e['name']} and {', '.join(sorted({x['name'] for x in differ}))} share source {s['id']} " \
                    "(declared correlated) but have different names", \
                    {"related": [x["entity_id"] for x in differ], "evidence": [f"{name}: source {s['id']}"]}
        else:
            other_members = [x for m, f in zip(s["members"], found) if not _member_of(e, m) for x in f]
            same = [x for x in other_members if x["name"] == e["name"]]
            if same:
                return "naming.decorrelated_names_equal", \
                    f"{e['name']} is declared uncorrelated within source {s['id']} but the name is shared", \
                    {"related": [x["entity_id"] for x in same], "evidence": [f"{name}: source {s['id']}"]}
    for s in sources:
        if s in mine:
            continue
        clash = [x for m in s["members"] for x in resolve(m) if x["name"] == e["name"]]
        if clash:
            return "naming.decorrelated_names_equal", \
                f"{e['name']} names both source {mine[0]['id']} and source {s['id']}: the same name would correlate them", \
                {"related": [x["entity_id"] for x in clash], "evidence": [f"{name}: sources {mine[0]['id']}, {s['id']}"]}
    return "naming.names_match_declaration", "", {}


def _phrase(text: str) -> tuple[str, ...]:
    return tuple(w for w in re.split(r"[\s_\-./]+", str(text).lower()) if w)


def glossary_spellings(glossary) -> list[tuple[dict, set, set]]:
    """(entry, identifier phrases, other spellings) for every glossary entry that declares identifiers."""
    out = []
    for entry in (glossary or {}).get("entries", []):
        idents = {_phrase(i) for i in entry.get("identifiers") or [] if _phrase(i)}
        if not idents:
            continue
        other = {_phrase(t) for t in (entry.get("preferred") or {}).values()}
        other |= {_phrase(t) for terms in (entry.get("aliases") or {}).values() for t in terms or []}
        other |= {_phrase(a) for a in entry.get("abbreviations") or []}
        out.append((entry, idents, {o for o in other if o and o not in idents}))
    return out


def _contains(toks: tuple, phrase: tuple) -> int:
    n = len(phrase)
    return next((i for i in range(len(toks) - n + 1) if toks[i:i + n] == phrase), -1)


def _glossary_match(e, rule, ctx):
    spell = ctx.__dict__.get("_spellings")
    if spell is None:
        spell = ctx.__dict__["_spellings"] = glossary_spellings(getattr(ctx.vocab, "glossary", None))
    if not spell:
        return "naming.no_glossary_identifiers", "", {}
    toks = tuple(t.lower() for t in entity_tokens(e, ctx))
    for entry, idents, other in spell:
        if any(_contains(toks, i) >= 0 for i in idents):
            return "naming.concept_identifier_used", "", {}
        for o in sorted(other, key=len, reverse=True):
            at = _contains(toks, o)
            if at >= 0:
                ident = "_".join(sorted(idents, key=len)[0])
                proposed = "_".join(toks[:at] + (ident,) + toks[at + len(o):])
                return "naming.concept_identifier_differs", \
                    f"{e['name']} spells {entry['id']} as {'_'.join(o)}; the glossary identifier is {ident}", \
                    {"proposed": proposed, "evidence": [f"glossary entry {entry['id']} identifiers"]}
    return "naming.no_declared_concept", "", {}


def status_honesty(e, rule, ctx):
    params = rule.get("params", {})
    claims = set(params.get("claim_tokens", ["final", "observed", "approved"]))
    weak = set(params.get("weak_labels", ["synthetic", "asimov", "preliminary"]))
    toks = {t.lower() for t in entity_tokens(e, ctx)}
    claimed = sorted(toks & claims)
    if not claimed:
        return "naming.no_status_claim", "", {}
    label = (e.get("meaning") or {}).get("status_label")
    if not label:
        return "naming.status_label_missing", f"{e['name']} claims {', '.join(claimed)} and has no status label", {}
    if label in weak:
        return "naming.name_hides_status", f"a {label} product named {e['name']} ({', '.join(claimed)})", \
            {"evidence": [f"status label {label}"]}
    return "naming.status_compatible", "", {}


def _normalized(name: str, how) -> str:
    out = name
    if "case" in how:
        out = out.lower()
    if "separators" in how:
        out = re.sub(r"[_\-.\s]", "", out)
    return out


def _declared_distinct(a, b, ctx, decl_name) -> bool:
    decl = ctx.declarations.get(decl_name) if decl_name else None
    sources = _members(decl) if decl else None
    if not sources:
        return False
    sa = {s["id"] for s in sources if any(_member_of(a, m) for m in s["members"])}
    sb = {s["id"] for s in sources if any(_member_of(b, m) for m in s["members"])}
    return bool(sa and sb and not sa & sb)


def _annotated_distinct(a, b, ctx) -> bool:
    for x, y in ((a, b), (b, a)):
        ann = ctx.annotations.get(x["entity_id"]) or {}
        if y["entity_id"] in (ann.get("intended_distinct") or []):
            return True
    return False


def similarity(e, rule, ctx):
    if e["change"] == "removed":
        return "naming.removed", "", {}
    params = rule.get("params", {})
    how = params.get("normalize", ["case", "separators"])
    across = params.get("across", "container")
    pool = [x for x in ctx.entities_in(e["surface"]) if x["change"] != "removed"]
    if across in ("container", "channel") and len({x["scope"]["container"] for x in pool}) < 2:
        return "naming.single_channel", "", {}
    key = _normalized(e["name"], how)
    near = [x for x in pool if x["name"] != e["name"] and _normalized(x["name"], how) == key
            and (across not in ("container", "channel") or x["scope"]["container"] != e["scope"]["container"])]
    if not near:
        return "naming.no_near_duplicates", "", {}
    open_, codes = [], set()
    for x in near:
        if _declared_distinct(e, x, ctx, params.get("declaration")):
            codes.add("naming.declared_distinct")
        elif _annotated_distinct(e, x, ctx) and not ctx.surface(e["surface"])["requires_declarations"]:
            codes.add("naming.annotated_distinct")  # where names are declared (N10), only the declaration decides
        else:
            open_.append(x)
    if open_:
        where = ", ".join(f"{x['name']} in {x['scope']['container']}" for x in open_)
        return "naming.near_duplicate_needs_review", f"{e['name']} is close to {where}: a typo or a deliberate " \
            "difference; only a declaration or an annotation decides", {"related": [x["entity_id"] for x in open_]}
    return ("naming.declared_distinct" if "naming.declared_distinct" in codes else "naming.annotated_distinct"), "", {}


def semantic(e, rule, ctx):
    if e["change"] not in ("added", "modified"):
        return "naming.unchanged", "", {}
    ann = ctx.annotations.get(e["entity_id"])
    if not ann or not ann.get("semantic_verdict"):
        return "naming.not_reviewed", f"{e['name']} has no semantic review", {}
    extra = {"proposed": ann.get("proposed"), "evidence": list(ann.get("evidence") or []),
             "confidence": ann.get("confidence")}
    if ann.get("confidence") != "high":
        return "naming.confidence_insufficient", f"the review of {e['name']} has {ann.get('confidence')} confidence", extra
    referrers = {r["from"] for r in e["references"]}
    read = set(ann.get("referrers_read") or [])
    if e["references_status"] != "complete" or not referrers <= read:
        missing = sorted(referrers - read)
        why = "references were not fully searched" if e["references_status"] != "complete" else \
            f"referrers not read: {', '.join(missing[:5])}"
        return "naming.confidence_unsupported", f"high confidence for {e['name']} is not supported: {why}", \
            {**extra, "confidence": "medium"}
    if ann["semantic_verdict"] == "consistent":
        return "naming.semantic_consistent", "", extra
    return "naming.semantic_inconsistent", f"{e['name']} does not say what it holds or does", extra


PREDICATES = {"forbidden": forbidden, "pattern": pattern, "vocabulary": vocabulary, "uniqueness": uniqueness,
              "pairing": pairing, "reference": reference, "declared-match": declared_match,
              "status-honesty": status_honesty, "similarity": similarity, "semantic": semantic}
DETERMINISM = {"similarity": "heuristic", "semantic": "review"}
