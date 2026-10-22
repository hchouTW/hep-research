"""Mutation-testing skeleton of the cross-artifact check (V76; architecture section 5.1, diagnostic plane A).

A mutation operator edits a draft case (files, items, context) before freezing and states the invariant the check
must keep on the mutant compared with the original:

  same     the obligation states are identical (reorder, rename of IDs mapped back)
  no-gain  the status never improves, and no obligation is removed (P4: removing or loosening agent-writable input)

Operators of the diagnostic plane listed in the architecture: relabel, rename, copy, copy+perturb, drop, loosen,
toggle-optional, reorder, edit-report. This skeleton implements reorder, rename, drop and loosen; the others are
named in PENDING and land with the Phase 2 fixes (full mutation testing, R3). Synthetic and public content only."""
from __future__ import annotations

import copy

STATUS_RANK = {"complete": 3, "incomplete": 2, "inconsistent": 1, "invalid": 0}
PENDING = ("relabel", "copy", "copy+perturb", "toggle-optional", "edit-report")


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
    for corr in (c.doc("spec").get("extension") or {}).get("corrections", []):
        corr.pop("target_scope", None)


OPERATORS = {"reorder": (reorder, "same"), "rename": (rename_declarations, "same"),
             "drop": (drop_declarations, "no-gain"), "loosen": (loosen_scopes, "no-gain")}


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
