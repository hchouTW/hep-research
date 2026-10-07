#!/usr/bin/env python3
"""Comparison gate: decides whether a prediction can meet a measurement, before any mixed inference.

Both sides are checked for quantity, process, species, units, every variable axis and its binning, phase space
(the fiducial flag, structured cuts when both sides give them, otherwise the written definition), frame,
conventions, level, normalization kind, included corrections, parameter point, validity range and uncertainty
representation. Declared transformations are applied in order to a description of the prediction (never to
numbers), each is recorded with the state before and after, and double counting is blocked. Nothing is inferred:
a transformation, mapping or assumption the caller does not declare does not exist.

Process, species and phase-space definitions are free text unless the phase space lists structured "cuts"
([{"variable", "unit", "low", "high"}], null for an open side). Text that is equal after case and whitespace
normalization matches; anything else cannot be judged equal and is 'unresolved' until the plan declares a named
mapping {"field": "process" | "species" | "phase_space", "action": "equivalent", "justification": "..."}.
A mismatch carries "kind": "mismatch" (decided) or "unresolved" (equivalence not established); the result's
"status" is "comparable", "not-comparable" (any decided mismatch) or "unresolved" (only unresolved items).
Multi-dimensional observables are compared axis by axis; transformations that act on an axis (fiducial
restriction, rebin, variable change, forward folding) are rejected for them rather than applied to the first axis.

Usage: python3 contracts/comparison/gate.py PREDICTION.json MEASUREMENT.json [--plan PLAN.json]
  PREDICTION.json: a prediction artifact. MEASUREMENT.json: a dataset-record or measurement-spec artifact.
  PLAN.json: {"transformations": [...], "mappings": [...], "measurement_conditions": {...}}; a mapping with "key" is a
  conventions mapping, one with "field" a definition mapping (process, species, phase_space).
Exit 0 comparable, 1 not comparable, 2 unreadable or refused input. Output: JSON gate result.
Both artifacts are validated first; one whose fields have the wrong JSON type, or a plan that is not an object, is
refused ("status": "refused") with findings that name the field path and a code. A malformed plan entry inside a valid plan is a mismatch of kind "malformed" and is
never applied.

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
from contracts.validate import SHAPE_ERRORS, validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

KINDS = ("level-identification", "fiducial-restriction", "rebin", "variable-change", "unit-conversion",
         "bin-integrate", "multiply-by-normalization", "forward-fold", "apply-correction")
NON_GAUSSIAN = {"scale-envelope", "model-alternative", "truncation"}
STICKY = ["failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied"]
QUANTITY_AFTER_INTEGRATION = {"differential-cross-section": "cross-section", "differential-flux": "flux"}
EDGE_TOL = 1e-12
# Fields a transformation must declare before it can be applied (see the kinds in the module docstring).
AXIS_KINDS = {"fiducial-restriction", "rebin", "variable-change", "forward-fold"}
DEFINITION_FIELDS = ("process", "species", "phase_space")
NEEDS = {"level-identification": ("from", "to"), "fiducial-restriction": ("variable", "range"), "rebin": ("edges",),
         "variable-change": ("from", "to"), "unit-conversion": ("from", "to")}


def _edges_equal(a, b) -> bool:
    return a is not None and b is not None and len(a) == len(b) and all(abs(x - y) <= EDGE_TOL * max(1.0, abs(y)) for x, y in zip(a, b))


def _subset(target, edges) -> bool:
    return all(any(abs(t - e) <= EDGE_TOL * max(1.0, abs(e)) for e in edges) for t in target)


def side_from_artifact(doc: dict) -> dict:
    """Reduce a prediction, dataset-record or measurement-spec artifact to what the gate compares."""
    ext = doc.get("extension") or {}
    obs = ext.get("observable") or {}
    side = {"artifact_type": doc.get("artifact_type"), "artifact_id": doc.get("artifact_id"),
            "observable": obs, "status": list(doc.get("status") or []), "uncertainties": [], "covariance": None,
            "parameter_point": ext.get("parameter_point") or {}, "allowed_transformations": ext.get("allowed_transformations")}
    if doc.get("artifact_type") == "prediction":
        side["uncertainties"] = list(ext.get("uncertainties", [])) + list((ext.get("values") or {}).get("uncertainties", []))
    elif doc.get("artifact_type") == "dataset-record":
        side["uncertainties"] = list((ext.get("data") or {}).get("uncertainties", []))
        side["covariance"] = ext.get("covariance", {}).get("status")
        side["corrections"] = [c.get("effect_id") for c in ext.get("corrections") or [] if isinstance(c, dict)]
    elif doc.get("artifact_type") == "measurement-spec":
        side["corrections"] = [c.get("effect_id") for c in ext.get("corrections") or [] if isinstance(c, dict)]
    side.setdefault("corrections", [])
    return side


def _norm_text(x):
    return " ".join(str(x).lower().split()) if x is not None else None


def _cuts(ps):
    cuts = (ps or {}).get("cuts")
    if not isinstance(cuts, list):
        return None
    return sorted(((_norm_text(c.get("variable")), _norm_text(c.get("unit")), c.get("low"), c.get("high"))
                   for c in cuts if isinstance(c, dict)), key=_cut_key)


def _cut_key(cut) -> str:
    """A total order for cuts whose bounds may be null (an open side): None never meets < against a number."""
    return json.dumps(cut, default=str)


def _state(obs: dict) -> dict:
    var = (obs.get("variables") or [{}])[0]
    ps = obs.get("phase_space") or {}  # an explicit null is the same as no phase-space block
    species = obs.get("species")
    return {"process": _norm_text(obs.get("process")),
            "species": sorted(_norm_text(s.get("name")) for s in species if isinstance(s, dict)) if isinstance(species, list) else None,
            "phase_space_definition": _norm_text(ps.get("definition")), "cuts": _cuts(ps),
            "extra_axes": [dict(v) for v in (obs.get("variables") or [])[1:]],
            "quantity": obs.get("quantity"), "unit": obs.get("unit"), "level": obs.get("level"),
            "variable": var.get("name"), "variable_unit": var.get("unit"),
            "edges": list(var["edges"]) if "edges" in var else None, "points": var.get("points"),
            "bin_semantics": obs.get("bin_semantics"), "fiducial": bool(ps.get("fiducial", False)),
            "fiducial_range": None, "frame": obs.get("frame"),
            "normalization_kind": (obs.get("normalization") or {}).get("kind"),
            "corrections": list(obs.get("included_corrections") or []), "n_variables": len(obs.get("variables") or [])}


def _mm(out, field, pred, meas, reason, resolve, kind="mismatch"):
    out.append({"field": field, "prediction": pred, "measurement": meas, "reason": reason, "resolve": resolve, "kind": kind})


# JSON types of the plan fields the gate reads; anything else in a transformation is recorded, not read.
_T_STR = ("kind", "owner", "justification", "from", "to", "variable", "unit", "method", "effect", "normalization_kind",
          "unit_in", "unit_out", "truth_level")
_T_NUMLIST = ("range", "edges", "truth_edges", "reco_edges")
_T_NUM = ("factor", "value")


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _plan_problems(transformations, mappings, conditions) -> list[tuple[str, str]]:
    """(field path, problem) for every plan entry the gate cannot read; such entries are refused, never guessed."""
    out = []
    for name, value in (("transformations", transformations), ("mappings", mappings)):
        if not isinstance(value, (list, tuple)):
            out.append((name, f"must be a list, got {type(value).__name__}"))
    if conditions is not None and not isinstance(conditions, dict):
        out.append(("measurement_conditions", f"must be an object, got {type(conditions).__name__}"))
    for i, t in enumerate(transformations if isinstance(transformations, (list, tuple)) else []):
        where = f"transformations[{i}]"
        if not isinstance(t, dict):
            out.append((where, "must be an object"))
            continue
        for k in _T_STR:
            if t.get(k) is not None and not isinstance(t[k], str):
                out.append((f"{where}.{k}", "must be a string"))
        for k in _T_NUMLIST:
            if t.get(k) is not None and not (isinstance(t[k], list) and all(_is_num(x) for x in t[k])):
                out.append((f"{where}.{k}", "must be a list of numbers"))
        for k in _T_NUM:
            if t.get(k) is not None and not _is_num(t[k]):
                out.append((f"{where}.{k}", "must be a number"))
        if t.get("includes") is not None and not (isinstance(t["includes"], list) and all(isinstance(x, str) for x in t["includes"])):
            out.append((f"{where}.includes", "must be a list of strings"))
    for i, m in enumerate(mappings if isinstance(mappings, (list, tuple)) else []):
        where = f"mappings[{i}]"
        if not isinstance(m, dict):
            out.append((where, "must be an object"))
            continue
        if not isinstance(m.get("field"), str) and not isinstance(m.get("key"), str):
            out.append((where, "needs a string 'field' (definition mapping) or 'key' (conventions mapping)"))
        for k in ("action", "justification"):
            if m.get(k) is not None and not isinstance(m[k], str):
                out.append((f"{where}.{k}", "must be a string"))
    return out


def _apply(st: dict, t: dict, i: int, mism: list) -> None:
    k, where = t.get("kind"), f"transformations[{i}]"
    if k not in KINDS:
        _mm(mism, where, k, None, f"unknown transformation kind '{k}'", f"use one of {', '.join(KINDS)}")
        return
    if not t.get("owner"):
        _mm(mism, where, k, None, "transformation without an owning skill", "name the skill that owns it (contracts 7.10)")
    if k in ("level-identification", "variable-change", "unit-conversion", "apply-correction") and not t.get("justification"):
        _mm(mism, where, k, None, f"'{k}' needs a written justification", "state why it is valid for this observable")
    missing = [f for f in NEEDS.get(k, ()) if t.get(f) in (None, "", [])]
    rng = t.get("range")
    if k == "fiducial-restriction" and not missing and not (isinstance(rng, list) and len(rng) == 2
                                                           and all(isinstance(x, (int, float)) for x in rng)):
        missing = ["range"]
    if k in AXIS_KINDS and st["n_variables"] > 1:
        _mm(mism, where, k, st["n_variables"], f"'{k}' acts on one axis; it is not supported for a multi-dimensional observable",
            "project or integrate to one dimension explicitly, or provide the prediction in the measurement's binning")
        return
    if missing:
        _mm(mism, where, k, None, f"'{k}' is incomplete: needs {', '.join(repr(f) for f in missing)}",
            "declare every field of the transformation (see the gate's transformation kinds)")
        return
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
        # the written definition no longer describes the restricted prediction; only structured cuts do
        st["cuts"] = sorted((st["cuts"] or []) + [(_norm_text(st["variable"]), _norm_text(st["variable_unit"]), lo, hi)],
                            key=_cut_key)
        st["phase_space_definition"] = None
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
    problems = _plan_problems(transformations, mappings, measurement_conditions)
    bad = {path.split(".")[0] for path, _ in problems}
    for path, problem in problems:
        _mm(mism, path, None, None, f"malformed plan entry: {problem}", "fix the plan entry; it was not applied", "malformed")
    transformations = [t for i, t in enumerate(transformations if isinstance(transformations, (list, tuple)) else [])
                       if f"transformations[{i}]" not in bad]
    mappings = [m for i, m in enumerate(mappings if isinstance(mappings, (list, tuple)) else []) if f"mappings[{i}]" not in bad]
    if "measurement_conditions" in bad:
        measurement_conditions = None
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
    def_maps = {m.get("field"): m for m in mappings if isinstance(m, dict) and "field" in m}
    conv_maps = [m for m in mappings if not (isinstance(m, dict) and "field" in m)]
    applied_defs = []
    for f in DEFINITION_FIELDS:
        dm = def_maps.get(f)
        if f in def_maps and not (dm.get("justification") and dm.get("action") == "equivalent"):
            _mm(mism, f"mappings.{f}", dm, None, "a definition mapping needs action 'equivalent' and a written justification",
                "state why the two definitions describe the same physics", "unresolved")
            dm = None
        if f == "phase_space" and st["cuts"] is not None and ms["cuts"] is not None:
            if st["cuts"] != ms["cuts"]:
                _mm(mism, "phase_space.cuts", st["cuts"], ms["cuts"], "the structured phase-space cuts differ",
                    "restrict the prediction to the measurement's cuts, or compute it in the measurement's phase space")
            continue
        a, b = (st["phase_space_definition"], ms["phase_space_definition"]) if f == "phase_space" else (st[f], ms[f])
        if a == b:
            continue
        if dm:
            applied_defs.append(dm)
            continue
        one = a is None or b is None
        _mm(mism, f, a, b, (f"{f} is stated on one side only" if one else f"{f} differs and free-text equality cannot be established"),
            f"state the {f} on both sides{', give structured cuts' if f == 'phase_space' else ''}, or declare a mapping "
            f"{{'field': '{f}', 'action': 'equivalent', 'justification': ...}}", "unresolved")
    for f in ("quantity", "unit", "frame", "bin_semantics", "variable", "variable_unit"):
        if st[f] != ms[f]:
            _mm(mism, f, st[f], ms[f], f"{f} differs after the declared transformations", f"declare a transformation that gives the measurement's {f}")
    if st["n_variables"] != ms["n_variables"]:
        _mm(mism, "variables", st["n_variables"], ms["n_variables"], "different number of variables", "project or integrate explicitly")
    else:
        for i, (pa, ma) in enumerate(zip(st["extra_axes"], ms["extra_axes"]), start=1):
            for key, label in (("name", "name"), ("unit", "unit")):
                if pa.get(key) != ma.get(key):
                    _mm(mism, f"variables[{i}].{label}", pa.get(key), ma.get(key), f"axis {i} {label} differs",
                        "give both sides the same axes in the same order")
            if "edges" in pa or "edges" in ma:
                if not _edges_equal(pa.get("edges"), ma.get("edges")):
                    _mm(mism, f"variables[{i}].binning", pa.get("edges"), ma.get("edges"), f"axis {i} bin edges differ",
                        "recompute the prediction in the measurement bins")
            elif pa.get("points") != ma.get("points"):
                _mm(mism, f"variables[{i}].points", pa.get("points"), ma.get("points"), f"axis {i} evaluation points differ",
                    "evaluate the prediction at the measurement points")
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

    applied = {c for c in st["corrections"] if isinstance(c, str)}
    for eff in measurement.get("corrections") or []:
        if not isinstance(eff, str):
            continue
        if ms["level"] in ("unfolded", "particle-fiducial", "parton") and eff in applied and eff != "normalization":
            _mm(mism, "corrections", eff, eff, f"'{eff}' was corrected in the measurement and applied to the prediction too",
                "apply each correction on one side only")

    conv = compare_conventions(prediction["observable"].get("conventions", {}), m_obs.get("conventions", {}), conv_maps, vocab)
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
    axes = [(ms["variable"], ms["edges"])] + [(a.get("name"), a.get("edges")) for a in ms["extra_axes"]]
    for name, edges in axes:
        if not edges:
            continue
        rng = vr.get(name) if isinstance(vr, dict) else None
        if rng is None:
            notes.append({"field": "validity_range", "note": f"the prediction declares no validity range for '{name}'; coverage of the measured range is not checked"})
        elif edges[0] < rng[0] or edges[-1] > rng[1]:
            _mm(mism, "validity_range", rng, [edges[0], edges[-1]], f"the measured range of '{name}' lies outside the prediction's validity range",
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
    status = "comparable" if not mism else ("unresolved" if all(x["kind"] == "unresolved" for x in mism) else "not-comparable")
    return {"comparable": not mism, "status": status, "mismatches": mism, "notes": notes, "transformations": record,
            "definition_mappings_applied": applied_defs,
            "final_prediction_state": {k: st[k] for k in ("quantity", "unit", "level", "edges", "bin_semantics", "fiducial", "corrections")},
            "conventions": conv, "uncertainty_objects": unc, "measurement_covariance": cov, "carried_statuses": statuses}


PREDICTION_TYPES = {"prediction"}
MEASUREMENT_TYPES = {"dataset-record", "measurement-spec"}


def check(prediction_doc, measurement_doc, plan=None, vocab: Vocabulary | None = None) -> dict:
    """Check that the gate can read both artifacts and the plan, then run it; unreadable input is refused.

    The artifacts are validated, and a type or shape error (a field the gate reads having the wrong JSON type) refuses
    the comparison; a missing field does not, since the gate reports what it cannot compare. A refusal is {"comparable": false, "status": "refused", "refusal": "invalid-input", "findings": [{"path",
    "code", "message"}]}: the path names the side ("prediction:$...", "measurement:$...", "plan...") and the code is
    the validator's own code or a gate.* code. No artifact or plan, however malformed, raises.
    """
    vocab = vocab or Vocabulary()
    findings = []
    for side, doc, allowed in (("prediction", prediction_doc, PREDICTION_TYPES),
                               ("measurement", measurement_doc, MEASUREMENT_TYPES)):
        if not isinstance(doc, dict):
            findings.append({"path": f"{side}:$", "code": "gate.not_an_object", "message": "an artifact must be a JSON object"})
            continue
        for f in validate_artifact(doc, vocab).errors:
            if f.code in SHAPE_ERRORS:
                findings.append({"path": f"{side}:{f.path}", "code": f.code, "message": f.message})
        if doc.get("artifact_type") not in allowed if isinstance(doc.get("artifact_type"), str) else True:
            findings.append({"path": f"{side}:$.artifact_type", "code": "gate.wrong_artifact_type",
                             "message": f"the {side} side must be one of {sorted(allowed)}"})
    plan = {} if plan is None else plan
    if not isinstance(plan, dict):
        findings.append({"path": "plan", "code": "gate.malformed_plan", "message": "a plan must be a JSON object"})
    if findings:
        return {"comparable": False, "status": "refused", "refusal": "invalid-input", "findings": findings, "mismatches": []}
    return gate(side_from_artifact(prediction_doc), side_from_artifact(measurement_doc), plan.get("transformations", []),
                plan.get("mappings", []), plan.get("measurement_conditions"), vocab)


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print(__doc__)
        return 2
    plan = None
    try:
        pred = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        meas = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        if "--plan" in args:
            plan = json.loads(Path(args[args.index("--plan") + 1]).read_text(encoding="utf-8"))
    except (OSError, ValueError, IndexError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    res = check(pred, meas, plan)
    print(json.dumps(res, indent=1))
    if res["status"] == "refused":
        return 2
    return 0 if res["comparable"] else 1


if __name__ == "__main__":
    sys.exit(main())
