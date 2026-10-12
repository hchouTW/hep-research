"""Reporting completeness per result type (plan T5): check supplied method metadata against a conditional policy.

A policy (assets/reporting-policies.json) lists, per result type, the fields a report needs and the method conditions
under which each applies. States in a record's reporting_context.fields: provided, missing, not-applicable (needs a
reason), unresolved. The check never chooses a method or invents a default: an absent condition key leaves a field's
applicability unresolved unless the policy says otherwise; a missing field is an unresolved finding, not a value.
"""
from __future__ import annotations

import json
from pathlib import Path

from communication_lib import report as R

STATES = ("provided", "missing", "not-applicable", "unresolved")


def load_policy(path) -> dict:
    pol = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(pol, dict) or "policy_version" not in pol or not isinstance(pol.get("result_types"), dict):
        raise ValueError(f"{path}: a policy needs policy_version and result_types")
    for rt, spec in pol["result_types"].items():
        if not isinstance(spec, dict) or not isinstance(spec.get("fields"), dict):
            raise ValueError(f"{path}: result type {rt!r} needs a fields map")
        for name, field in spec["fields"].items():
            if not isinstance(field, dict) or "description" not in field:
                raise ValueError(f"{path}: field {rt}.{name} needs a description")
    return pol


def _lookup(method: dict, dotted: str):
    node = {"method": method}
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def _condition(method: dict, cond: dict):
    """True / False / None (a referenced method key is absent)."""
    for key, want in cond.items():
        val, present = _lookup(method, key)
        if not present:
            return None
        if isinstance(want, dict) and "not" in want:
            if val == want["not"]:
                return False
        elif val != want:
            return False
    return True


def applicable(spec: dict, method: dict):
    """True / False / None for one policy field under the supplied method metadata."""
    if "when" not in spec:
        return True
    res = _condition(method, spec["when"])
    if res is None:
        absent = spec.get("when_absent", "unknown")
        return {"applicable": True, "not-applicable": False}.get(absent, None)
    return res


def check_reporting(rc: dict, policy: dict) -> dict:
    """{"result_type", "fields": {name: {"state", "applicable", "value"?, "reason"?}}, "findings": [...]}."""
    rt = rc.get("result_type")
    method = rc.get("method") if isinstance(rc.get("method"), dict) else {}
    supplied = rc.get("fields") if isinstance(rc.get("fields"), dict) else {}
    findings: list[dict] = []
    spec = (policy.get("result_types") or {}).get(rt)
    if spec is None:
        findings.append(R.finding("reporting.unknown_result_type", "error", "reporting_context.result_type",
                                  f"result type {rt!r} has no policy; known: {sorted(policy.get('result_types') or [])}",
                                  "declare one of the known result types, or extend the policy", source="reporting"))
        return {"result_type": rt, "fields": {}, "findings": findings}
    out: dict[str, dict] = {}
    for name, fspec in spec["fields"].items():
        where = f"fields.{name}"
        rec = supplied.get(name) if isinstance(supplied.get(name), dict) else None
        state = rec.get("state") if rec else "missing"
        app = applicable(fspec, method)
        entry = {"state": state, "applicable": app}
        if rec and "value" in rec:
            entry["value"] = rec["value"]
        if rec and rec.get("reason"):
            entry["reason"] = rec["reason"]
        out[name] = entry
        conflict = fspec.get("conflicts_with")
        if conflict and state == "provided" and _condition(method, conflict) is True:
            findings.append(R.finding("reporting.interval_kind_mismatch", "error", where,
                                      f"{name} is provided although the method says {conflict}: {fspec['description']}",
                                      "report the quantity that matches the declared paradigm", source="reporting"))
            continue
        if state == "provided":
            continue
        if app is None:
            entry["state"] = "unresolved"
            need = ", ".join(fspec.get("when", {}).keys())
            findings.append(R.finding("reporting.applicability_unknown", "unresolved", where,
                                      f"whether {name} applies depends on {need}, which the method metadata does not state",
                                      f"state {need} in reporting_context.method; nothing is assumed", source="reporting"))
            continue
        if app is False:
            entry["state"] = "not-applicable"
            continue
        if state == "not-applicable":
            if not str((rec or {}).get("reason") or "").strip():
                findings.append(R.finding("reporting.not_applicable_without_reason", "error", where,
                                          f"{name} is marked not-applicable without a reason", "give the reason, or provide the field", source="reporting"))
            continue
        if state == "unresolved":
            findings.append(R.finding("reporting.field_unresolved", "unresolved", where, f"{name} is marked unresolved: {fspec['description']}",
                                      "resolve it with the producing skill", source="reporting"))
            continue
        entry["state"] = "missing"
        findings.append(R.finding("reporting.field_missing", "unresolved", where, f"{name} is missing: {fspec['description']}",
                                  "supply it from the producing artifact, mark it not-applicable with a reason, or request it; no default is assumed",
                                  source="reporting"))
    return {"result_type": rt, "fields": out, "findings": findings}
