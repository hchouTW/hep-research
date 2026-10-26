"""Declarations the naming engine judges against (spec §2, §7.6 declared-match): the correlation inventory.

Two forms are read (spec Q1, provisional until hep-measurement and hep-statistics settle it):
  - an explicit declaration {"declaration": "correlation-inventory", "sources": [{"id", "correlated", "members"}]};
    a member is an entity id, "<container>/<name>" or a bare nuisance name (every nuisance of that name);
  - a measurement-spec artifact, read from the fields it already has: each entry of extension.systematics is one
    source, keyed by its correlation_key (entries sharing a key are one source) or else its name; its members are
    its nuisance_names when given, else its name; correlated unless era_correlation is "uncorrelated". An entry with
    era_correlation "partial" needs a decomposition the spec states in prose, so it is left out (its nuisances are
    then judged by no source: not_applicable, never satisfied by default).
correlation_inventory(doc) returns the explicit form, or raises ValueError for anything else. Standard library only.
"""
from __future__ import annotations

CORRELATION = "correlation-inventory"


def from_measurement_spec(spec: dict) -> dict:
    ext = spec.get("extension") or {}
    sources: dict[str, dict] = {}
    left_out = []
    for item in ext.get("systematics") or []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        era = item.get("era_correlation")
        if era == "partial":
            left_out.append(item["name"])
            continue
        key = item.get("correlation_key") or item["name"]
        members = item.get("nuisance_names") or [item["name"]]
        src = sources.setdefault(str(key), {"id": str(key), "correlated": era != "uncorrelated", "members": []})
        if era == "uncorrelated":
            src["correlated"] = False
        src["members"] += [m for m in members if isinstance(m, str) and m not in src["members"]]
    out = {"declaration": CORRELATION, "derived_from": f"measurement-spec {spec.get('artifact_id', '')}".strip(),
           "sources": list(sources.values())}
    if left_out:
        out["left_out"] = left_out
    return out


def correlation_inventory(doc: dict) -> dict:
    if doc.get("artifact_type") == "measurement-spec":
        return from_measurement_spec(doc)
    if doc.get("declaration") == CORRELATION and isinstance(doc.get("sources"), list):
        return doc
    raise ValueError("not a correlation inventory: give {\"declaration\": \"correlation-inventory\", \"sources\": [...]} "
                     "or a measurement-spec artifact")
