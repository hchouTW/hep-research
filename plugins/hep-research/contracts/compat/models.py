"""Competing theory models (T03): several predictions of one observable stay distinct alternatives.

model_set(prediction_docs) -> {"ok", "problems", "alternatives"}
  Each prediction keeps its own theory spec, assumptions and parameter point; none needs an experiment binding.
envelope(model_set_result, values_by_id, prescription=None) -> {"ok", ...}
  An envelope over alternatives is a 'model-alternative' uncertainty object. It is built only from a prescription
  owned by hep-theory, is never Gaussian, and does not replace the alternatives it summarizes.
"""
from __future__ import annotations

from itertools import combinations

from contracts.compat.gate import gate, side_from_artifact


def model_set(prediction_docs) -> dict:
    problems, alts = [], []
    seen_ids, seen_specs = set(), {}
    for d in prediction_docs:
        if d.get("artifact_type") != "prediction":
            problems.append({"code": "models.not_prediction", "message": f"{d.get('artifact_id')} is a {d.get('artifact_type')}"})
            continue
        aid, ext = d.get("artifact_id"), d.get("extension", {})
        if aid in seen_ids:
            problems.append({"code": "models.duplicate_id", "message": f"two predictions share id {aid}"})
        seen_ids.add(aid)
        spec = ext.get("theory_spec_ref")
        if not spec:
            problems.append({"code": "models.no_theory_spec", "message": f"{aid} names no theory spec, so its assumptions are unknown"})
        elif spec in seen_specs:
            problems.append({"code": "models.shared_theory_spec",
                             "message": f"{aid} and {seen_specs[spec]} point to the same theory spec; alternatives need their own assumptions"})
        seen_specs.setdefault(spec, aid)
        alts.append({"id": aid, "theory_spec_ref": spec, "parameter_point": ext.get("parameter_point", {}),
                     "expression": ext.get("expression"), "status": d.get("status", []),
                     "experiment_bindings": d.get("bindings", {}).get("experiments", [])})
    sides = [side_from_artifact(d) for d in prediction_docs if d.get("artifact_type") == "prediction"]
    for a, b in combinations(sides, 2):
        g = gate(dict(a, parameter_point={}, allowed_transformations=None), b, [], [], {})
        for m in g["mismatches"]:
            problems.append({"code": "models.different_observable", "message": f"{a['artifact_id']} vs {b['artifact_id']}: {m['field']}: {m['reason']}"})
    return {"ok": not problems, "problems": problems, "alternatives": alts}


def envelope(ms: dict, values_by_id: dict, prescription: dict | None = None) -> dict:
    if not ms.get("ok"):
        return {"ok": False, "reason": "the model set itself is not valid"}
    if not prescription or prescription.get("owner") != "hep-theory" or not prescription.get("justification"):
        return {"ok": False, "reason": "model alternatives are distinct uncertainty objects; an envelope needs a hep-theory prescription "
                                       "with a justification, and is never Gaussian"}
    if prescription.get("kind") != "min-max":
        return {"ok": False, "reason": f"unsupported envelope kind '{prescription.get('kind')}'"}
    rows = [values_by_id[a["id"]] for a in ms["alternatives"]]
    lo = [min(v) for v in zip(*rows)]
    hi = [max(v) for v in zip(*rows)]
    return {"ok": True, "uncertainty": {"name": "model envelope", "kind": "model-alternative", "correlation": "unknown",
                                        "gaussian": False, "lower": lo, "upper": hi, "members": [a["id"] for a in ms["alternatives"]],
                                        "prescription": prescription}}
