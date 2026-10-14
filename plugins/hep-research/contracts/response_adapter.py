#!/usr/bin/env python3
"""Convert a `response` artifact extension into core/stats/validate_response.py input, and fold through it.

The artifact contract (contracts/schemas/ext_response.json) and the numerical validator use two vocabularies. This
module is the one place where they meet:

  artifact (extension)                     validator (metadata)
  truth_axis/reco_axis {name, unit, edges} truth_axis/reco_axis {variable, unit, edges}
  normalization conditional_on_selected    conditional_on_selected
                conditional_on_generated   includes_efficiency
                joint_counts               counts (folding needs generated_per_truth_bin: the generated events
                                           when the inefficiency is inside, the selected ones when outside)
                unnormalized               error: no probability interpretation
  acceptance    not-applicable             error: the validator needs inside or outside
  applied_separately [terms]               efficiency_applied_separately: any 'efficiency' or '<x>_efficiency' term;
                                           acceptance_applied_separately: 'acceptance' or 'exposure' listed
                                           (exposure = acceptance x live time)
  underflow_overflow (optional string)     required enum; absent -> 'not_represented', listed under assumptions
  intended_use, variable_conversion        passed through
  matrix (inline) or matrix_ref            matrix: the `matrix` argument wins, then the inline matrix, then a JSON
                                           matrix_ref resolved against base_dir (a list, or an object with "matrix";
                                           'file.json#key' selects a member). The ref must stay inside base_dir.
  underflow, overflow,                     arguments win, then the extension, then the matrix_ref object
  generated_per_truth_bin

Values that cannot be mapped are errors, never guesses: to_validator_input returns
{"ok": bool, "input": dict | None, "errors": [{"field", "message"}], "assumptions": [...]}.
A converted response that passes the validator is self-consistent under its declared metadata, not physically valid.

Usage: python3 contracts/response_adapter.py ARTIFACT.json [--validate]
Exit codes: 0 converted (and, with --validate, not 'fail'); 1 conversion errors or a failed validation;
2 unreadable input (the artifact or its matrix_ref). Output: JSON on stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.stats.validate_response import FLOW, INTENDED_USES, probability_matrix  # noqa: E402
from core.stats.validate_response import fold as _fold  # noqa: E402

NORMALIZATION = {"conditional_on_selected": "conditional_on_selected", "conditional_on_generated": "includes_efficiency",
                 "joint_counts": "counts"}


def _is_efficiency(term: str) -> bool:
    bare = term.split(":", 1)[-1]
    return bare == "efficiency" or bare.endswith("_efficiency")


def _axis(ext: dict, key: str, errors: list) -> dict | None:
    axis = ext.get(key)
    if not isinstance(axis, dict) or not all(k in axis for k in ("name", "unit", "edges")):
        errors.append({"field": key, "message": f"{key} must be an object with name, unit and edges (got {axis!r})"})
        return None
    return {"variable": axis["name"], "unit": axis["unit"], "edges": list(axis["edges"])}


def _matrix_source(ext: dict, matrix, base_dir: Path | None, errors: list) -> tuple[Any, dict]:
    """(matrix, object the matrix came from). The object supplies underflow, overflow and generated_per_truth_bin
    when the caller and the extension do not."""
    if matrix is not None:
        return matrix, {}
    if isinstance(ext.get("matrix"), list):
        return ext["matrix"], {}
    ref = ext.get("matrix_ref")
    if not ref:
        errors.append({"field": "matrix", "message": "neither matrix nor matrix_ref is present"})
        return None, {}
    file_part, _, key = str(ref).partition("#")
    path = Path(file_part) if base_dir is None else Path(base_dir) / file_part
    if base_dir is not None and not path.resolve().is_relative_to(Path(base_dir).resolve()):
        errors.append({"field": "matrix_ref", "message": f"matrix_ref {ref!r} resolves outside the artifact folder"})
        return None, {}
    if path.suffix != ".json" or not path.is_file():
        errors.append({"field": "matrix_ref", "message": f"matrix_ref {ref!r} is not a readable JSON file; load it and pass matrix="})
        return None, {}
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append({"field": "matrix_ref", "unreadable": True, "message": f"matrix_ref {ref!r} is not valid JSON: {exc}"})
        return None, {}
    if key:
        if not isinstance(data, dict) or key not in data:
            errors.append({"field": "matrix_ref", "message": f"matrix_ref {ref!r}: no member {key!r} in {file_part!r}"})
            return None, {}
        data = data[key]
    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict) and isinstance(data.get("matrix"), list):
        return data["matrix"], data
    errors.append({"field": "matrix_ref", "message": f"matrix_ref {ref!r} holds no 'matrix' list (expected a list of rows "
                   "or an object with 'matrix', and optionally 'underflow', 'overflow', 'generated_per_truth_bin')"})
    return None, {}


def to_validator_input(ext: dict, matrix=None, *, base_dir: Path | None = None, generated_per_truth_bin=None,
                       underflow=None, overflow=None, closure=None, tolerances=None) -> dict:
    """Map a response extension (and its numbers) to validate_response input; see the module docstring."""
    errors: list[dict] = []
    assumptions: list[str] = []
    if not isinstance(ext, dict):
        return {"ok": False, "input": None, "errors": [{"field": "extension", "message": "must be an object"}], "assumptions": []}
    if ext.get("form", "matrix") != "matrix":
        errors.append({"field": "form", "message": f"form {ext.get('form')!r} has no matrix to validate; "
                       "a parametrized response is checked against its validity range instead"})
    truth_axis, reco_axis = _axis(ext, "truth_axis", errors), _axis(ext, "reco_axis", errors)
    norm = ext.get("normalization")
    if norm not in NORMALIZATION:
        errors.append({"field": "normalization", "message": f"normalization {norm!r} has no validator equivalent "
                       f"(mappable: {sorted(NORMALIZATION)})"})
    for effect in ("inefficiency", "acceptance"):
        if ext.get(effect) not in ("inside_matrix", "outside_matrix"):
            errors.append({"field": effect, "message": f"{effect} {ext.get(effect)!r} must be inside_matrix or outside_matrix "
                           "for a numerical check"})
    flow = ext.get("underflow_overflow")
    if flow is None:
        flow = "not_represented"
        assumptions.append("underflow_overflow not declared: taken as 'not_represented' (probability leaving the axes is lost)")
    elif flow not in FLOW:
        errors.append({"field": "underflow_overflow", "message": f"underflow_overflow {flow!r} must be one of {list(FLOW)}"})
    use = ext.get("intended_use")
    if use is not None and use not in INTENDED_USES:
        errors.append({"field": "intended_use", "message": f"intended_use {use!r} must be one of {list(INTENDED_USES)}"})
    m, source = _matrix_source(ext, matrix, base_dir, errors)
    if errors:
        return {"ok": False, "input": None, "errors": errors, "assumptions": assumptions}
    separate = ext.get("applied_separately", [])
    meta: dict[str, Any] = {
        "truth_axis": truth_axis, "reco_axis": reco_axis, "orientation": ext.get("orientation"),
        "normalization": NORMALIZATION[str(norm)], "inefficiency": ext["inefficiency"], "acceptance": ext["acceptance"],
        "underflow_overflow": flow,
        "efficiency_applied_separately": any(_is_efficiency(t) for t in separate),
        "acceptance_applied_separately": bool({"acceptance", "exposure"} & {t.split(":", 1)[-1] for t in separate})}
    if use is not None:
        meta["intended_use"] = use
    if ext.get("variable_conversion"):
        meta["variable_conversion"] = ext["variable_conversion"]
    doc: dict[str, Any] = {"metadata": meta, "matrix": m}
    def given(name: str, value):
        return value if value is not None else ext.get(name, source.get(name))

    for key, value in (("generated_per_truth_bin", given("generated_per_truth_bin", generated_per_truth_bin)),
                       ("underflow", given("underflow", underflow)), ("overflow", given("overflow", overflow)),
                       ("closure", closure), ("tolerances", tolerances)):
        if value is not None:
            doc[key] = value
    return {"ok": True, "input": doc, "errors": [], "assumptions": assumptions}


def fold(validator_input: dict, truth: list[float], background: list[float] | None = None) -> list[float]:
    """Fold a truth spectrum through a converted (and validated) response: nu = P x + b, in reco bins."""
    meta, matrix = validator_input["metadata"], validator_input["matrix"]
    m = matrix if meta["orientation"] == "rows_reco_cols_truth" else [list(c) for c in zip(*matrix)]
    p = probability_matrix([[float(x) for x in r] for r in m], meta["normalization"],
                           validator_input.get("generated_per_truth_bin"))
    return _fold(p, [float(t) for t in truth], background)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        ext = doc["extension"] if isinstance(doc, dict) and "extension" in doc else doc
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": f"unreadable: {exc}"}, indent=2))
        return 2
    out = to_validator_input(ext, base_dir=Path(args[0]).resolve().parent)
    code = 0 if out["ok"] else 2 if any(e.get("unreadable") for e in out["errors"]) else 1
    if out["ok"] and "--validate" in args:
        from core.stats.validate_response import validate_response
        out["validation"] = validate_response(out["input"])
        code = 1 if out["validation"]["status"] == "fail" else 0
    print(json.dumps(out, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
