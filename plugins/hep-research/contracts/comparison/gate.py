#!/usr/bin/env python3
"""Comparison gate (task 7.11): decides whether a prediction can meet a measurement, before any mixed inference.

Both sides are checked for quantity, units, variables and binning, phase space / fiducial selection, frame,
conventions, level, normalization kind, included corrections, parameter point, validity range and uncertainty
representation. Declared transformations are applied in order to a description of the prediction (never to
numbers), each is recorded with the state before and after, and double counting is blocked. Nothing is inferred:
a transformation, mapping or assumption the caller does not declare does not exist.

Usage: python3 contracts/comparison/gate.py PREDICTION.json MEASUREMENT.json [--plan PLAN.json]
  PREDICTION.json: a prediction artifact. MEASUREMENT.json: a dataset-record or measurement-spec artifact.
  PLAN.json: {"transformations": [...], "mappings": [...], "measurement_conditions": {...}}
Exit 0 comparable, 1 not comparable, 2 unreadable input. Output: JSON gate result.

Transformation kinds (each {"kind", "owner", "justification", ...}):
  level-identification       {"from", "to"}: two levels treated as the same for this observable (justify why)
  fiducial-restriction       {"variable", "range": [lo, hi]}: restrict to a cut on a binned variable (edges must align)
  rebin                      {"edges"}: merge bins exactly (target edges a subset of the current edges)
  variable-change            {"from", "to", "unit", "jacobian"}: needs the Jacobian written out
  unit-conversion            {"from", "to", "factor"}
  bin-integrate              {}: bin-averaged -> bin-integrated (x bin width); from 'point' needs "method"
  multiply-by-normalization  {"normalization_kind", "value", "unit_in", "unit_out"}: cross section -> expected counts
  forward-fold               {"truth_edges", "reco_edges", "truth_level", "includes": [...]}: -> detector level
  apply-correction           {"effect"}: a correction (efficiency, acceptance, ...) applied outside a response
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from contracts.comparison.conventions import compare_conventions  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

KINDS = ("level-identification", "fiducial-restriction", "rebin", "variable-change", "unit-conversion",
         "bin-integrate", "multiply-by-normalization", "forward-fold", "apply-correction")
NON_GAUSSIAN = {"scale-envelope", "model-alternative", "truncation"}
STICKY = ["failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied"]
QUANTITY_AFTER_INTEGRATION = {"differential-cross-section": "cross-section", "differential-flux": "flux"}
EDGE_TOL = 1e-12


def _edges_equal(a, b) -> bool:
    return a is not None and b is not None and len(a) == len(b) and all(abs(x - y) <= EDGE_TOL * max(1.0, abs(y)) for x, y in zip(a, b))


def _subset(target, edges) -> bool:
    return all(any(abs(t - e) <= EDGE_TOL * max(1.0, abs(e)) for e in edges) for t in target)


def side_from_artifact(doc: dict) -> dict:
    """Reduce a prediction, dataset-record or measurement-spec artifact to what the gate compares."""
    ext = doc.get("extension", {})
    obs = ext.get("observable", {})
    side = {"artifact_type": doc.get("artifact_type"), "artifact_id": doc.get("artifact_id"),
            "observable": obs, "status": list(doc.get("status", [])), "uncertainties": [], "covariance": None,
            "parameter_point": ext.get("parameter_point", {}), "allowed_transformations": ext.get("allowed_transformations")}
    if doc.get("artifact_type") == "prediction":
        side["uncertainties"] = list(ext.get("uncertainties", [])) + list((ext.get("values") or {}).get("uncertainties", []))
    elif doc.get("artifact_type") == "dataset-record":
        side["uncertainties"] = list((ext.get("data") or {}).get("uncertainties", []))
        side["covariance"] = ext.get("covariance", {}).get("status")
        side["corrections"] = [c.get("effect_id") for c in ext.get("corrections", [])]
    elif doc.get("artifact_type") == "measurement-spec":
        side["corrections"] = [c.get("effect_id") for c in ext.get("corrections", [])]
    side.setdefault("corrections", [])
    return side


def _state(obs: dict) -> dict:
    var = (obs.get("variables") or [{}])[0]
    return {"quantity": obs.get("quantity"), "unit": obs.get("unit"), "level": obs.get("level"),
            "variable": var.get("name"), "variable_unit": var.get("unit"),
            "edges": list(var["edges"]) if "edges" in var else None, "points": var.get("points"),
            "bin_semantics": obs.get("bin_semantics"), "fiducial": bool(obs.get("phase_space", {}).get("fiducial", False)),
            "fiducial_range": None, "frame": obs.get("frame"),
            "normalization_kind": obs.get("normalization", {}).get("kind"),
            "corrections": list(obs.get("included_corrections", [])), "n_variables": len(obs.get("variables", []))}


def _mm(out, field, pred, meas, reason, resolve):
    out.append({"field": field, "prediction": pred, "measurement": meas, "reason": reason, "resolve": resolve})


def _apply(st: dict, t: dict, i: int, mism: list) -> None:
    k, where = t.get("kind"), f"transformations[{i}]"
    if k not in KINDS:
        _mm(mism, where, k, None, f"unknown transformation kind '{k}'", f"use one of {', '.join(KINDS)}")
        return
    if not t.get("owner"):
        _mm(mism, where, k, None, "transformation without an owning skill", "name the skill that owns it (contracts 7.10)")
    if k in ("level-identification", "variable-change", "unit-conversion", "apply-correction") and not t.get("justification"):
        _mm(mism, where, k, None, f"'{k}' needs a written justification", "state why it is valid for this observable")
    if k == "level-identification":
        if st["level"] != t.get("from"):
            _mm(mism, where, st["level"], t.get("from"), "level identification starts from a different level", "fix 'from'")
        elif {t.get("from"), t.get("to")} & {"unfolded", "detector"}:
            _mm(mism, where, t.get("from"), t.get("to"), "detector-level and unfolded quantities are never identified with another level",
                "forward-fold the prediction, or compare to a measurement at the prediction's level")
        else:
            st["level"] = t["to"]
    elif k == "fiducial-restriction":
        lo, hi = (t.get("range") or [None, None])
        if t.get("variable") != st["variable"] or st["edges"] is None or not _subset([lo, hi], st["edges"]):
            _mm(mism, where, st["edges"], t.get("range"), "fiducial cut is not on a binned variable with aligned edges",
                "provide the prediction differential in the cut variable with edges at the cut, or a fiducial prediction")
            return
        st["edges"] = [e for e in st["edges"] if lo - EDGE_TOL <= e <= hi + EDGE_TOL]
        st["fiducial"], st["fiducial_range"] = True, [lo, hi]
    elif k == "rebin":
        if st["edges"] is None or not _subset(t.get("edges", []), st["edges"]):
            _mm(mism, where, st["edges"], t.get("edges"), "rebinning target edges are not a subset of the current edges",
                "rebin only by merging bins, or recompute the prediction in the target bins")
            return
        if st["bin_semantics"] == "bin-averaged":
            _mm(mism, where, "bin-averaged", None, "merging bin-averaged values needs width weighting; declare bin-integrate first",
                "bin-integrate, then rebin")
            return
        st["edges"] = list(t["edges"])
    elif k == "variable-change":
        if t.get("from") != st["variable"] or not t.get("jacobian"):
            _mm(mism, where, st["variable"], t.get("to"), "variable change without a matching source variable or a Jacobian",
                "write the Jacobian and the edge mapping")
            return
        st["variable"], st["variable_unit"] = t["to"], t.get("unit", st["variable_unit"])
        if "edges" in t:
            st["edges"] = list(t["edges"])
    elif k == "unit-conversion":
        if t.get("from") != st["unit"] or not isinstance(t.get("factor"), (int, float)):
            _mm(mism, where, st["unit"], t.get("to"), "unit conversion from a different unit or without a numeric factor", "fix 'from' and 'factor'")
            return
        st["unit"] = t["to"]
    elif k == "bin-integrate":
        if st["bin_semantics"] == "point" and not t.get("method"):
            _mm(mism, where, "point", "bin-integrated", "point values cannot be compared with bins without a defined mapping",
                "integrate the prediction function over each bin and name the method")
            return
        if st["bin_semantics"] == "bin-integrated":
            _mm(mism, where, "bin-integrated", None, "already bin-integrated: integrating again double counts the bin width", "drop this step")
            return
        st["bin_semantics"] = "bin-integrated"
        st["quantity"] = QUANTITY_AFTER_INTEGRATION.get(st["quantity"], st["quantity"])
    elif k == "multiply-by-normalization":
        if st["normalization_kind"] != t.get("normalization_kind"):
            _mm(mism, where, st["normalization_kind"], t.get("normalization_kind"), "normalization kinds differ",
                "use the measurement's normalization kind, or a profile-declared conversion")
            return
        if st["bin_semantics"] != "bin-integrated":
            _mm(mism, where, st["bin_semantics"], "bin-integrated", "expected counts need bin-integrated values", "bin-integrate first")
            return
        if t.get("unit_in") != st["unit"]:
            _mm(mism, where, st["unit"], t.get("unit_in"), "the normalization value expects a different unit for the cross section",
                "convert units first (unit-conversion), then normalize")
            return
        if "normalization" in st["corrections"]:
            _mm(mism, where, "normalization", None, "normalization applied twice", "drop one of the two steps")
            return
        st["quantity"], st["unit"] = "event-count", t.get("unit_out", "1")
        st["corrections"].append("normalization")
    elif k == "forward-fold":
        if st["level"] in ("detector", "unfolded"):
            _mm(mism, where, st["level"], "detector", f"cannot forward-fold a {st['level']}-level quantity (detector effects would be counted twice)",
                "fold a truth-level prediction")
            return
        if st["level"] != t.get("truth_level"):
            _mm(mism, where, st["level"], t.get("truth_level"), "prediction level differs from the response truth level",
                "declare a justified level-identification, or use a response defined at the prediction's level")
            return
        if not _edges_equal(st["edges"], t.get("truth_edges")):
            _mm(mism, where, st["edges"], t.get("truth_edges"), "prediction bins differ from the response truth bins",
                "integrate the prediction in the response truth bins")
            return
        if st["quantity"] != "event-count":
            _mm(mism, where, st["quantity"], "event-count", "the response acts on expected truth counts", "bin-integrate and multiply by the normalization first")
            return
        for eff in t.get("includes", []):
            if eff in st["corrections"]:
                _mm(mism, where, eff, None, f"'{eff}' already applied before folding; the response includes it too", "drop the separate correction")
        st["corrections"] += [e for e in t.get("includes", []) if e not in st["corrections"]]
        st["level"], st["edges"] = "detector", list(t.get("reco_edges", []))
        st["fiducial"], st["fiducial_range"] = False, None
    elif k == "apply-correction":
        eff = t.get("effect")
        if eff in st["corrections"]:
            _mm(mism, where, eff, None, f"'{eff}' applied twice", "apply each correction once")
            return
        st["corrections"].append(eff)


def gate(prediction: dict, measurement: dict, transformations=(), mappings=(), measurement_conditions=None,
         vocab: Vocabulary | None = None) -> dict:
    """prediction / measurement: sides from side_from_artifact (or dicts of the same shape)."""
    mism, notes, record = [], [], []
    st = _state(prediction["observable"])
    allowed = prediction.get("allowed_transformations")
    for i, t in enumerate(transformations):
        if allowed is not None and t.get("kind") not in allowed:
            _mm(mism, f"transformations[{i}]", t.get("kind"), None, "the prediction's producer does not allow this transformation",
                f"allowed: {allowed}; ask the producing skill for a prediction in the needed form")
            continue
        before = copy.deepcopy(st)
        n = len(mism)
        _apply(st, t, i, mism)
        record.append({**t, "ok": len(mism) == n, "before": {k: before[k] for k in ("quantity", "unit", "level", "bin_semantics", "fiducial")},
                       "after": {k: st[k] for k in ("quantity", "unit", "level", "bin_semantics", "fiducial")}})

    m_obs = measurement["observable"]
    ms = _state(m_obs)
    for f in ("quantity", "unit", "frame", "bin_semantics", "variable", "variable_unit"):
        if st[f] != ms[f]:
            _mm(mism, f, st[f], ms[f], f"{f} differs after the declared transformations", f"declare a transformation that gives the measurement's {f}")
    if st["n_variables"] != ms["n_variables"]:
        _mm(mism, "variables", st["n_variables"], ms["n_variables"], "different number of variables", "project or integrate explicitly")
    if st["level"] != ms["level"]:
        pair = {st["level"], ms["level"]}
        reason = ("unfolded and detector-level (raw) quantities are not equivalent" if pair == {"unfolded", "detector"}
                  else "levels differ after the declared transformations")
        _mm(mism, "level", st["level"], ms["level"], reason, "forward-fold to detector level, or compare at a common declared level")
    if st["fiducial"] != ms["fiducial"]:
        _mm(mism, "phase_space.fiducial", st["fiducial"], ms["fiducial"], "fiducial and inclusive phase spaces are not equivalent",
            "restrict the prediction to the measurement's fiducial region (fiducial-restriction) or use an inclusive measurement")
    if st["edges"] is not None or ms["edges"] is not None:
        if not _edges_equal(st["edges"], ms["edges"]):
            _mm(mism, "binning", st["edges"], ms["edges"], "bin edges differ", "rebin exactly, restrict, or recompute the prediction in the measurement bins")
    elif st["points"] != ms["points"]:
        _mm(mism, "points", st["points"], ms["points"], "evaluation points differ", "evaluate the prediction at the measurement points")
    if st["normalization_kind"] != ms["normalization_kind"]:
        _mm(mism, "normalization.kind", st["normalization_kind"], ms["normalization_kind"], "normalization kinds differ",
            "use a profile-declared conversion; kinds are never assumed equivalent")

    applied = set(st["corrections"])
    for eff in measurement.get("corrections", []):
        if ms["level"] in ("unfolded", "particle-fiducial", "parton") and eff in applied and eff != "normalization":
            _mm(mism, "corrections", eff, eff, f"'{eff}' was corrected in the measurement and applied to the prediction too",
                "apply each correction on one side only")

    conv = compare_conventions(prediction["observable"].get("conventions", {}), m_obs.get("conventions", {}), list(mappings), vocab)
    for x in conv["mismatches"]:
        _mm(mism, f"conventions.{x['key']}", x.get("a"), x.get("b"), x["reason"], "declare a justified mapping, or use a variant")
    notes += [{"field": f"conventions.{n['key']}", "note": n["reason"]} for n in conv["notes"]]

    cond = measurement_conditions or {}
    for key, val in (prediction.get("parameter_point") or {}).items():
        if key not in cond:
            _mm(mism, f"parameter_point.{key}", val, None, "the measurement conditions do not state this parameter",
                "record it in the measurement's conditions")
        elif isinstance(val, (int, float)) and isinstance(cond[key], (int, float)):
            if abs(val - cond[key]) > 1e-9 * max(1.0, abs(val)):
                _mm(mism, f"parameter_point.{key}", val, cond[key], "prediction computed at a different parameter point", "recompute the prediction")
        elif val != cond[key]:
            _mm(mism, f"parameter_point.{key}", val, cond[key], "prediction computed at a different parameter point", "recompute the prediction")

    vr = prediction["observable"].get("validity_range") or {}
    if ms["edges"]:
        rng = vr.get(ms["variable"]) if isinstance(vr, dict) else None
        if rng is None:
            notes.append({"field": "validity_range", "note": "the prediction declares no validity range; coverage of the measured range is not checked"})
        elif ms["edges"][0] < rng[0] or ms["edges"][-1] > rng[1]:
            _mm(mism, "validity_range", rng, [ms["edges"][0], ms["edges"][-1]], "the measured range lies outside the prediction's validity range",
                "restrict the comparison, or extend the prediction")

    unc = {"prediction": [], "measurement": []}
    for side, items in (("prediction", prediction.get("uncertainties", [])), ("measurement", measurement.get("uncertainties", []))):
        for u in items:
            entry = {"name": u.get("name"), "kind": u.get("kind"), "correlation": u.get("correlation"),
                     "quantified": bool(u.get("values") or u.get("covariance_ref") or u.get("value") is not None)}
            if u.get("kind") in NON_GAUSSIAN:
                entry["gaussian_allowed"] = False
            unc[side].append(entry)
    cov = measurement.get("covariance")
    if cov in ("absent", "partial"):
        notes.append({"field": "covariance", "note": f"measurement covariance is {cov}: it stays {cov}; inference must not assume a diagonal matrix"})
    statuses = sorted({s for side in (prediction, measurement) for s in side.get("status", []) if s in STICKY})
    return {"comparable": not mism, "mismatches": mism, "notes": notes, "transformations": record,
            "final_prediction_state": {k: st[k] for k in ("quantity", "unit", "level", "edges", "bin_semantics", "fiducial", "corrections")},
            "conventions": conv, "uncertainty_objects": unc, "measurement_covariance": cov, "carried_statuses": statuses}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print(__doc__)
        return 2
    plan = {}
    try:
        pred = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        meas = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        if "--plan" in args:
            plan = json.loads(Path(args[args.index("--plan") + 1]).read_text(encoding="utf-8"))
    except (OSError, ValueError, IndexError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    res = gate(side_from_artifact(pred), side_from_artifact(meas), plan.get("transformations", []), plan.get("mappings", []),
               plan.get("measurement_conditions"))
    print(json.dumps(res, indent=1))
    return 0 if res["comparable"] else 1


if __name__ == "__main__":
    sys.exit(main())
