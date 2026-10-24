"""Mutation-testing skeleton of the cross-artifact check (V76; architecture section 5.1, diagnostic plane A).

A mutation operator edits a draft case (files, items, context) before freezing and states the invariant the check
must keep on the mutant compared with the original:

  same     the obligation states are identical (reorder, rename of IDs mapped back)
  no-gain  the status never improves, and no obligation is removed (P4: removing or loosening agent-writable input)

  refused  (edit-report) a hand-edited report is refused by the permit's report check

Operators of the diagnostic plane listed in the architecture: relabel, rename, copy, copy+perturb, drop, loosen,
toggle-optional, reorder, edit-report. All nine are implemented (full mutation testing, release R3; the skeleton of
Phase 0 had the first four). edit-report acts on a finished report (edit_report), the others on a draft case before
freezing. Synthetic and public content only."""
from __future__ import annotations

import copy

STATUS_RANK = {"complete": 3, "incomplete": 2, "inconsistent": 1, "invalid": 0}
PENDING: tuple[str, ...] = ()


def reorder(c) -> None:
    """Reverse every list of the context and the items: the outcome may not depend on order (P5)."""
    for key, value in list(c.context.items()):
        if isinstance(value, list):
            c.context[key] = list(reversed(value))
    c.items = list(reversed(c.items))


def rename_declarations(c) -> None:
    """Give every declaration a new ID (and rename its references): IDs carry no meaning."""
    for d in c.context.get("declarations", []):
        d["declaration_id"] = "renamed-" + d["declaration_id"]


def drop_declarations(c) -> None:
    """Remove every declaration (agent-writable input): never a gain (P4)."""
    c.context["declarations"] = []


def loosen_scopes(c) -> None:
    """Drop the spec corrections' target scopes (agent-writable description): never a gain (P4)."""
    for corr in _spec_corrections(c):
        corr.pop("target_scope", None)


def relabel(c) -> None:
    """Set every artifact's status labels to 'synthetic': a label is no evidence (DR-7), so nothing may change."""
    for ref, doc in c.files.items():
        if isinstance(doc, dict) and isinstance(doc.get("status"), list):
            doc["status"] = ["synthetic"]


EVIDENCE_ROLES = ("validation-record", "calibration")


def _copy_id(item_id: str) -> str:
    return f"{item_id}-copy"


def copy_evidence(c) -> None:
    """Bind a byte copy of each validation record and auxiliary input in place of the original (a new item ID and
    file, the same content): a copy is the same source (DR-3), so nothing may change."""
    import copy as _copy
    for it in [i for i in c.items if i["role"] in EVIDENCE_ROLES]:
        doc = _copy.deepcopy(c.files[it["ref"]])
        new_id, new_ref = _copy_id(it["id"]), it["ref"].replace(".json", "-copy.json")
        c.remove(it["id"])
        c.add(it["role"], new_id, new_ref, doc)
        _rebind(c.context, it["id"], new_id)


def _rebind(node, old: str, new: str):
    """Replace every reference to an item ID in the draft context (bindings, calibrations, mappings), never an ID of
    another object."""
    if isinstance(node, dict):
        for k, v in node.items():
            if v == old and k not in ("declaration_id", "binding_id", "instance_id", "root_id"):
                node[k] = new
            else:
                _rebind(v, old, new)
    elif isinstance(node, list):
        for x in node:
            _rebind(x, old, new)


def copy_perturb(c) -> None:
    """Add, next to each validation record, a copy whose claim disagrees: contradicting evidence never gains (P4)."""
    import copy as _copy
    for it in [i for i in c.items if i["role"] == "validation-record"]:
        doc = _copy.deepcopy(c.files[it["ref"]])
        claim = doc.get("claim") or {}
        claim["relation"] = "fully_correlated" if claim.get("relation") != "fully_correlated" else "independent"
        c.add(it["role"], _copy_id(it["id"]) + "-perturbed", it["ref"].replace(".json", "-perturbed.json"), doc)


OPTIONAL_CORRECTION_FIELDS = ("application_id", "variation_id", "factor_of")


def toggle_optional(c) -> None:
    """Remove the optional fields of the spec corrections (agent-writable description): never a gain (P4)."""
    for corr in _spec_corrections(c):
        for k in OPTIONAL_CORRECTION_FIELDS:
            corr.pop(k, None)


def edit_report(report: dict) -> dict:
    """A hand edit of a finished report: every obligation that is not satisfied or not applicable is set to satisfied,
    and the summary recomputed so the report looks complete and consistent. The permit's report check must refuse it."""
    import copy as _copy
    from contracts.analysis_checks.outcomes import formal_view, summarize
    out = _copy.deepcopy(report)
    for o in out["obligations"]:
        if o["state"] not in ("satisfied", "not_applicable"):
            o.update(state="satisfied", reason="check.edited")
    s = summarize(out["obligations"], True)
    out.update(coverage=s["coverage"], consistency=s["consistency"], counts=s["counts"], status="complete",
               formal_use_view=formal_view(out["obligations"], True))
    return out


def _spec_corrections(c) -> list[dict]:
    """The spec's corrections, or none for a case without a measurement spec (a model case)."""
    spec = next((c.files[i["ref"]] for i in c.items if i["role"] == "measurement-spec"), None)
    ext = spec.get("extension") if isinstance(spec, dict) else None
    return ext.get("corrections", []) if isinstance(ext, dict) else []


OPERATORS = {"reorder": (reorder, "same"), "rename": (rename_declarations, "same"),
             "drop": (drop_declarations, "no-gain"), "loosen": (loosen_scopes, "no-gain"),
             "relabel": (relabel, "same"), "copy": (copy_evidence, "same"), "copy+perturb": (copy_perturb, "no-gain"),
             "toggle-optional": (toggle_optional, "no-gain")}
REPORT_OPERATORS = {"edit-report": (edit_report, "refused")}


def states(rep: dict) -> dict:
    return {o["obligation_id"]: o["state"] for o in rep["obligations"]}


def violations(original: dict, mutant: dict, invariant: str) -> list[str]:
    """The ways a mutant's report breaks the operator's invariant; empty when it holds."""
    out = []
    if invariant == "same":
        if states(original) != states(mutant):
            diff = sorted(k for k in set(states(original)) | set(states(mutant))
                          if states(original).get(k) != states(mutant).get(k))
            out.append(f"states differ on {diff[:5]}")
    elif invariant == "no-gain":
        if STATUS_RANK[mutant["status"]] > STATUS_RANK[original["status"]]:
            out.append(f"status improved: {original['status']} -> {mutant['status']}")
        removed = sorted(set(states(original)) - set(states(mutant)))
        if removed:
            out.append(f"obligations removed: {removed[:5]}")
    return out


def mutate(case, operator: str):
    """A deep copy of a draft case with the operator applied."""
    m = copy.deepcopy(case)
    OPERATORS[operator][0](m)
    return m
