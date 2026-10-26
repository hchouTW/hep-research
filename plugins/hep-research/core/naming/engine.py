"""Semantic naming engine (spec §7-§8): classify an inventory, judge it against the rule registry, select the
reporting scope, decide each finding's action and validate a change set.

classify(inventories, surfaces, declarations): tokens, references_status (§7.3), contract_level and contract_basis
(§7.4) for every entity; the extractor never fills these.
judge(...): every active rule on every entity of its surfaces, over the complete inventory; a waiver (explicit
entity ids, waivable rules only) or a kind the rule does not cover gives not_applicable; an inventory that scanned zero
inputs, or a surface the caller expects without an inventory, gives unsupported for each of its rules. The state of a
result comes from the rule's outcome contract through the state_for function the caller passes (contracts layer).
action_for(...): the decision procedure of §8.2 (no-rename restrictions first, then the matrix, then the request
scope); severity settings never reach it (I8).
validate_change_set(...): the six ordered checks of §8.4.
core imports only core; the report shape and the severities live in contracts/naming_check.py. Standard library only.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from core.naming import predicates as P
from core.naming.model import max_level, stable_key
from core.naming.vocab import forbidden_table

ENGINE_VERSION = "1.0.0"
RELATIONAL = ("uniqueness", "reference", "pairing", "declared-match", "similarity")
DEDUP_PREDICATES = ("uniqueness",)


def _matches(t: dict, x: dict) -> bool:
    return (x["surface"] == t["surface"] and x["name"] == t["name"] and x["change"] != "removed"
            and (not t.get("entity_kind") or x["entity_kind"] == t["entity_kind"])
            and (not t.get("file") or x["scope"]["file"] == t["file"])
            and (not t.get("container") or x["scope"]["container"] == t["container"]))


def link_targets(entities) -> dict[str, list]:
    """Resolve each entity's targets (names it refers to on its own or another surface) against the supplied
    entities: {entity_id: [(target, [matching entities])]}. A matching entity gains the reference {from: the
    referring entity's id, kind: the target's kind} (once), so its level, reference checks and change sets see it."""
    by_name: dict[tuple, list] = {}
    for x in entities:
        by_name.setdefault((x["surface"], x["name"]), []).append(x)
    out: dict[str, list] = {}
    for e in entities:
        for t in e.get("targets") or []:
            hits = [x for x in by_name.get((t["surface"], t["name"]), []) if _matches(t, x)]
            out.setdefault(e["entity_id"], []).append((t, hits))
            for x in hits:
                if not any(r["from"] == e["entity_id"] for r in x["references"]):
                    x["references"].append({"from": e["entity_id"], "kind": t.get("kind", "refers-to")})
    return out


def glossary_concepts(entities, vocab) -> None:
    """meaning.concept_id from the glossary (source glossary) when a name holds a spelling of exactly one entry
    that declares identifiers, and no review or extractor filled it."""
    spellings = P.glossary_spellings(getattr(vocab, "glossary", None))
    if not spellings:
        return
    for e in entities:
        if e["meaning"].get("concept_id"):
            continue
        toks = tuple(t.lower() for t in e.get("tokens") or [])
        hit = [entry["id"] for entry, idents, other in spellings if any(P._contains(toks, ph) >= 0 for ph in idents | other)]
        if len(hit) == 1:
            e["meaning"]["concept_id"] = f"term:{hit[0]}"
            e["meaning"]["source"] = "glossary"


class Context:
    def __init__(self, entities, surfaces, vocab, declarations=None, annotations=None, inventories=(), targets=None,
                 untrusted_changes=()):
        self.entities = entities
        self.surfaces = {s["surface_id"]: s for s in surfaces}
        self.vocab = vocab
        self.declarations = declarations or {}
        self.annotations = annotations or {}
        self.inventories = set(inventories)
        self.forbidden = forbidden_table()
        self.targets = targets if targets is not None else {}
        self.untrusted_changes = set(untrusted_changes)  # surfaces whose "unchanged" marks prove nothing (semantic)
        self.by_id = {e["entity_id"]: e for e in entities}
        self.by_name: dict[tuple, list] = {}
        self._by_surface: dict[str, list] = {}
        for e in entities:
            self.by_name.setdefault((e["surface"], e["name"]), []).append(e)
            self._by_surface.setdefault(e["surface"], []).append(e)

    def surface(self, sid: str) -> dict:
        return self.surfaces[sid]

    def entities_in(self, sid: str) -> list:
        return self._by_surface.get(sid, [])


def _root(r: str) -> str:
    r = str(r).replace("\\", "/").strip("/")
    return "" if r in ("", ".") else r


def covers(coverage, surface: str, roots) -> bool:
    """True when the coverage strings ("<surface>:<glob>") cover the full range of surface within every scope root:
    "<surface>:**" or "<surface>:<ancestor of the root>/**"."""
    globs = [c.split(":", 1)[1] for c in coverage if c.startswith(f"{surface}:")]
    for r in [_root(x) for x in roots] or [""]:
        ok = False
        for g in globs:
            if g in ("**", "./**"):
                ok = True
            elif g.endswith("/**"):
                base = _root(g[:-3])
                ok = base == "" or r == base or r.startswith(base + "/")
            if ok:
                break
        if not ok:
            return False
    return True


def references_status(e: dict, roots, registry: dict) -> str:
    """complete only when the search covered the whole project for this surface and every surface that refers to it:
    an inventory of a narrower --scope never proves that no file outside it uses the name (its status is partial)."""
    if not e["search_coverage"]:
        return "not_searched"
    if "" not in {_root(r) for r in roots}:
        return "partial"
    needed = {e["surface"]} | {s["surface"] for s in registry[e["surface"]]["referenced_by"]}
    return "complete" if all(covers(e["search_coverage"], s, roots) for s in needed) else "partial"


def _ref_file(ref_from: str, by_id: dict) -> str | None:
    if ref_from in by_id:
        return by_id[ref_from]["scope"]["file"]
    if "#" in ref_from and ":" in ref_from.split("#", 1)[0]:
        return ref_from.split("#", 1)[0].split(":", 1)[1]
    return ref_from.rsplit(":", 1)[0] if ":" in ref_from else ref_from


def declared_names(declarations: dict) -> dict[str, list[str]]:
    """{member (entity id or container/name): [declaration names]} for every declaration with sources."""
    out: dict[str, list[str]] = {}
    for name, decl in (declarations or {}).items():
        for s in (decl or {}).get("sources", []) if isinstance(decl, dict) else []:
            for m in s.get("members", []) if isinstance(s, dict) else []:
                out.setdefault(m, []).append(name)
    return out


def classify(entities, roots_of: dict, surfaces, declarations=None, vocab=None) -> list[dict]:
    """Fill the engine fields in place and return the entities. roots_of maps a surface to its scope roots."""
    registry = {s["surface_id"]: s for s in surfaces}
    by_id = {e["entity_id"]: e for e in entities}
    declared = declared_names(declarations or {})
    ctx = Context(entities, surfaces, vocab) if vocab is not None else None
    for e in entities:
        reg = registry[e["surface"]]
        e["tokens"] = P.entity_tokens(e, ctx) if ctx is not None else list(e.get("tokens", []))
        e["references_status"] = references_status(e, roots_of.get(e["surface"], ["."]), registry)
        kind = reg["kinds"].get(e["entity_kind"], {})
        basis = []
        floor = kind.get("level_floor", "C0")
        if floor != "C0":
            basis.append(f"kind-floor:{e['entity_kind']}")
        source_level = "C4" if e["source"] == "external" else "C0"
        if e["source"] == "external":
            basis.append("source:external")
        refs = e["references"]
        if e["references_status"] != "complete":
            evidence = "C2"
            basis.append(f"evidence:references-{e['references_status']}")
        elif all(r.get("kind") == "in-scope" for r in refs):
            evidence = "C0"
        elif all(_ref_file(r["from"], by_id) == e["scope"]["file"] for r in refs):
            evidence = "C1"
            basis.append("evidence:same-file")
        else:
            evidence = "C2"
            basis.append("evidence:other-files")
        names = declared.get(e["entity_id"], []) + declared.get(f"{e['scope']['container']}/{e['name']}", [])
        declared_level = "C3" if names else "C0"
        basis += [f"declared:{n}" for n in dict.fromkeys(names)]
        e["contract_level"] = max_level(floor, source_level, evidence, declared_level)
        e["contract_basis"] = basis
    return entities


def merge_annotations(entities, annotations: dict) -> None:
    """Meaning fields a review filled in replace the unknown ones (meaning.source becomes annotation)."""
    for e in entities:
        ann = annotations.get(e["entity_id"])
        if not ann or not ann.get("meaning"):
            continue
        filled = {k: v for k, v in ann["meaning"].items() if k in ("concept_id", "unit", "status_label") and v is not None}
        if filled:
            e["meaning"].update(filled)
            e["meaning"]["source"] = "annotation"


def _waived(waivers, rule, eid, keys=None) -> bool:
    """An explicit entity id, or the id without its @line (so an edit above the name does not drop the waiver) when
    that key names one declaration only: a second same-name declaration added later is never waived with it."""
    ids = {eid} | ({stable_key(eid)} if keys is None or keys.get(stable_key(eid), 0) == 1 else set())
    return rule.get("waivable", False) and any(w.get("rule_id") == rule["rule_id"] and ids & set(w.get("entity_ids") or [])
                                               for w in waivers or [])


def judge(inventories, rules, surfaces, *, vocab, state_for, declarations=None, annotations=None, waivers=(),
          expect=(), report_all=False, deterministic_only=False, untrusted_changes=()) -> dict:
    """Judge the inventories. Returns {"entities", "results", "reported", "not_run", "notes"}: results hold one entry per
    (entity, rule) (entity_id None for a surface-level unsupported result); reported is the subset in the reporting
    scope (§7.7)."""
    entities = [e for inv in inventories for e in inv["entities"]]
    roots_of = {inv["surface"]: inv["scope_roots"] for inv in inventories}
    annotations = annotations or {}
    merge_annotations(entities, annotations)
    targets = link_targets(entities)
    classify(entities, roots_of, surfaces, declarations, vocab)
    glossary_concepts(entities, vocab)
    supplied = {inv["surface"] for inv in inventories}
    ctx = Context(entities, surfaces, vocab, declarations, annotations, supplied, targets, untrusted_changes)
    active = [r for r in rules if r["lifecycle"] == "active"
              and not (deterministic_only and r["determinism"] != "deterministic")]
    results, not_run, notes = [], [], []
    if vocab.shadowed:
        notes.append(f"vocabulary shadowing: {'; '.join(vocab.shadowed[:20])}")
    empty = {inv["surface"] for inv in inventories if inv["inputs_scanned"] == 0}
    skipped = {inv["surface"]: len(inv.get("skipped_inputs") or []) for inv in inventories
               if inv.get("skipped_inputs") and inv["inputs_scanned"]}
    missing = [s for s in dict.fromkeys(expect) if s not in supplied]
    for sid in sorted(empty) + sorted(skipped) + missing:
        why = (f"the {sid} extractor scanned zero inputs" if sid in empty else
               f"the {sid} extractor could not read {skipped[sid]} input(s) (skipped_inputs)" if sid in skipped else
               f"no {sid} inventory was supplied" + ("" if ctx.surfaces[sid]["extractor"] else
                                                     " (its extractor is not implemented yet)"))
        for r in active:
            if sid in r["surfaces"] and r["predicate"] != "semantic":
                results.append(_result(None, sid, r, "naming.no_inputs", why, {}, state_for))
                not_run.append({"check": f"{r['rule_id']}@{r['version']} on {sid}", "reason": why, "required": True})
    stable_counts: dict[str, int] = {}
    for e in entities:
        stable_counts[stable_key(e["entity_id"])] = stable_counts.get(stable_key(e["entity_id"]), 0) + 1
    for e in entities:
        for r in active:
            if e["surface"] not in r["surfaces"] or e["surface"] in empty:
                continue
            kinds = r.get("params", {}).get("kinds")
            if kinds and e["entity_kind"] not in kinds:
                results.append(_result(e, e["surface"], r, "naming.kind_not_covered", "", {}, None))
                continue
            sources = r.get("params", {}).get("sources")
            if sources and e["source"] not in sources:
                results.append(_result(e, e["surface"], r, "naming.external_name", "", {}, None))
                continue
            if _waived(waivers, r, e["entity_id"], stable_counts):
                results.append(_result(e, e["surface"], r, "naming.waived", "", {}, None))
                continue
            code, issue, extra = P.PREDICATES[r["predicate"]](e, r, ctx)
            results.append(_result(e, e["surface"], r, code, issue, extra, state_for))
    changed = {e["entity_id"] for e in entities if e["change"] != "unchanged"}
    reported = []
    for res in results:
        eid = res["entity_id"]
        if report_all or eid is None or eid in changed or (
                res["predicate"] in RELATIONAL and set(res["extra"].get("related", [])) & changed):
            reported.append(res)
    return {"entities": entities, "results": results, "reported": reported, "not_run": not_run, "notes": notes,
            "context": ctx}


def _result(e, sid, rule, code, issue, extra, state_for) -> dict:
    state = "not_applicable" if state_for is None else state_for(rule, code)
    return {"entity_id": e["entity_id"] if e else None, "surface": sid, "rule_id": rule["rule_id"],
            "rule_version": rule["version"], "predicate": rule["predicate"], "determinism": rule["determinism"],
            "owner": rule["owner"], "state": state, "reason_code": code, "issue": issue, "extra": extra}


def rename_policy(e: dict, registry: dict) -> str:
    reg = registry[e["surface"]]
    return reg["kinds"].get(e["entity_kind"], {}).get("rename_policy", reg["rename_policy"])


def action_for(result: dict, e: dict | None, registry: dict, in_request: bool) -> tuple[str, dict | None]:
    """(action, handoff) for one result, per §8.2."""
    state = result["state"]
    if state in ("satisfied", "not_applicable"):
        return "none", None
    if state == "unsupported" or e is None:
        return "report-missing", None
    if state == "unverified":
        return "gather-evidence", None
    policy, level = rename_policy(e, registry), e["contract_level"]
    owner = registry[e["surface"]]["owner"]
    if level == "C4" or policy == "never":
        return "propose-alias", None
    if policy == "dedup-only" and result["predicate"] not in DEDUP_PREDICATES:
        return "report-only", None
    if level in ("C0", "C1"):
        action = "fix"
    elif level == "C2":
        action = "fix-with-change-set"
    else:
        return "propose-then-change-set-after-approval", {
            "owner": owner, "rerun": [f"{owner}: redo the steps that read {e['name']}",
                                      "naming_check.py check on the changed inventories"],
            "policy": policy}
    if not in_request:
        action = "propose"
    return action, None


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _proposed_problem(proposed, e: dict, entities, registry: dict, policy: str):
    """(code, message) when the new name may not be used: a forbidden whole name, a name off the kind's format, or a
    name another live entity of the same kind already has (on N10 anywhere: one name is one correlated parameter, so a
    rename onto it would merge two sources). On a dedup-only surface the new name must be the duplicate's."""
    if not proposed or proposed == e["name"]:
        return ("naming.proposed_invalid", "the change set proposes no new name")
    if proposed in forbidden_table()["whole_names"]:
        return ("naming.proposed_invalid", f"{proposed} is in the forbidden table")
    fmt = registry[e["surface"]]["kinds"].get(e["entity_kind"], {}).get("format")
    if fmt and e["source"] == "project" and not re.fullmatch(fmt, proposed):
        return ("naming.proposed_invalid", f"{proposed} does not match the {e['entity_kind']} format {fmt}")
    same = [x for x in entities if x is not e and x["surface"] == e["surface"] and x["change"] != "removed"
            and x["entity_kind"] == e["entity_kind"] and x["name"] == proposed]
    if policy == "dedup-only":
        return None if same else ("naming.proposed_invalid",
                                  f"{e['surface']} renames only onto the duplicate's name; no {proposed} exists")
    wide = registry[e["surface"]]["requires_declarations"]
    clash = [x for x in same if wide or (x["scope"]["file"], x["scope"]["container"]) ==
             (e["scope"]["file"], e["scope"]["container"])]
    if clash:
        where = f"{clash[0]['scope']['file']}:{clash[0]['scope']['span'][0]}"
        why = " (on this surface one name is one correlated parameter: declare it first)" if wide else ""
        return ("naming.proposed_collides", f"{proposed} already names {clash[0]['entity_kind']} at {where}{why}")
    return None


def _loc(x: dict) -> str:
    return f"{x['scope']['file']}:{x['scope']['span'][0]}"


def validate_change_set(cs: dict, entities, surfaces, project_root, supplied_surfaces, inventory_digests=()) -> dict:
    """The ordered checks of §8.4; stops at the first failure. Returns {status, exit_code, check, code, message}."""
    registry = {s["surface_id"]: s for s in surfaces}
    by_id = {e["entity_id"]: e for e in entities}
    e = by_id.get(cs["entity_id"])

    def out(status, code_, check, code, message):
        return {"status": status, "exit_code": code_, "check": check, "code": code, "message": message}
    if e is None:
        return out("input-error", 2, 0, "naming.change_set_entity_unknown",
                   f"{cs['entity_id']} is in none of the supplied inventories")
    policy = rename_policy(e, registry)
    if cs.get("contract_level") and cs["contract_level"] != e["contract_level"]:
        return out("fail", 1, 1, "naming.change_set_level_mismatch",
                   f"the change set records {cs['contract_level']}; the inventory gives {e['name']} "
                   f"{e['contract_level']}: rebuild the change set from the inventory")
    if e["contract_level"] == "C4" or policy == "never":
        return out("fail", 1, 1, "naming.rename_forbidden",
                   f"{e['name']} is {e['contract_level']} with rename policy {policy}: never renamed; propose an alias")
    if policy == "dedup-only":
        cid = (e.get("meaning") or {}).get("concept_id")
        dups = [x for x in entities if x is not e and x["surface"] == e["surface"] and x["change"] != "removed"
                and (x["name"] == e["name"] or (cid and (x.get("meaning") or {}).get("concept_id") == cid))]
        trigger = cs.get("trigger") or {}
        if not dups or trigger.get("predicate") != "uniqueness":
            return out("fail", 1, 1, "naming.rename_not_dedup",
                       f"{e['surface']} renames only to remove a duplicate (the same name, or two names of one record); "
                       f"{e['name']} has none" if not dups else f"the change set's trigger ({trigger.get('rule_id') or 'none'}) is "
                       "not a uniqueness finding: name the duplicate finding in trigger")
    bad = _proposed_problem(cs.get("proposed"), e, entities, registry, policy)
    if bad:
        return out("fail", 1, 1, bad[0], bad[1])
    if e["references_status"] != "complete":
        return out("incomplete", 3, 2, "naming.references_incomplete",
                   f"references of {e['name']} are {e['references_status']}: search them all before renaming")
    derived = [t for t in e.get("targets") or [] if t.get("derived")]
    needed = list(dict.fromkeys([s["surface"] for s in registry[e["surface"]]["referenced_by"]] +
                                [s["surface"] for s in registry[e["surface"]]["references_to"] if s.get("derived")] +
                                [t["surface"] for t in derived]))
    lacking = [s for s in needed if s not in supplied_surfaces]
    if lacking:
        return out("incomplete", 3, 3, "naming.inventory_missing",
                   f"no inventory for {', '.join(lacking)}, which refer to {e['surface']} names")
    stale = [p for p, d in sorted(cs["source_sha256"].items()) if file_sha256(Path(project_root) / p) != d]
    stale_inv = [d for d in cs["inventory_digests"].values() if inventory_digests and d not in set(inventory_digests)]
    if inventory_digests and not cs["inventory_digests"]:
        return out("incomplete", 3, 4, "naming.change_set_digests_missing",
                   "the change set records no inventory digests: record the sha256 of each inventory it was built from")
    if stale or stale_inv:
        what = ", ".join(stale) if stale else "the inventories"
        return out("incomplete", 3, 4, "naming.change_set_stale",
                   f"{what} changed since the change set was built: re-run the inventory")
    replaced = {r["location"] for r in cs["replacements"]}

    def covered(ref_from: str) -> bool:
        x = by_id.get(ref_from)
        return ref_from in replaced or (x is not None and _loc(x) in replaced)
    unmatched = [r["from"] for r in e["references"] if not covered(r["from"])]
    for t in derived:  # a name derived from this one (Combine's <process>_<nuisance>Up) is renamed with it
        hits = [x for x in entities if _matches(t, x)]
        unmatched += [x["entity_id"] for x in hits if not covered(x["entity_id"])]
    if unmatched:
        return out("fail", 1, 5, "naming.replacement_missing",
                   f"{len(unmatched)} reference(s) have no replacement, e.g. {', '.join(unmatched[:3])}")
    if e["contract_level"] == "C3":
        ap = cs.get("approval") or {}
        if not (ap.get("required") and ap.get("by") and ap.get("at")):
            return out("fail", 1, 6, "naming.approval_missing", f"{e['name']} is C3: record the user's approval first")
        if ap.get("proposed") not in (None, cs["proposed"]):
            return out("fail", 1, 6, "naming.approval_other_name",
                       f"the approval is for {ap['proposed']}, the change set proposes {cs['proposed']}: ask again")
        owner = registry[e["surface"]]["owner"]
        if (cs.get("handoff") or {}).get("owner") != owner:
            return out("fail", 1, 6, "naming.handoff_missing",
                       f"{e['name']} is C3: the change set hands back to {owner}, the owner of {e['surface']}")
    if policy == "deprecate" and not (cs.get("deprecated_alias") or {}).get("old"):
        return out("fail", 1, 6, "naming.deprecated_alias_missing",
                   f"{e['surface']} {e['entity_kind']} renames keep the old name as a deprecated alias")
    return out("pass", 0, 6, "naming.change_set_valid", f"the change set for {e['name']} passes the six checks")


def is_inside(path: Path, folder: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except ValueError:
        return False
