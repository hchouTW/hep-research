#!/usr/bin/env python3
"""Validate a detector response (migration) matrix against its declared conventions.

Purpose: catch response-matrix bookkeeping defects before they enter an unfolding or
forward fold: wrong orientation, a normalization that contradicts the declared
convention, efficiency or acceptance counted twice (or not at all), probability lost
outside the axes, empty bins, and phase-space holes that make the problem
non-identifiable. It never modifies the matrix.

What it does: reads a JSON response card + matrix, checks it, and prints errors,
warnings, metrics and a status. With `closure` truth/reco test spectra it also folds
the truth through the matrix and reports residuals and pull summaries. Correct
normalization or a clean closure is NOT evidence that the response is physically
valid; the report says so ("physical_validity": "not_assessed").

Input JSON:
  {"metadata": {
      "truth_axis": {"variable": "rigidity", "unit": "GV", "edges": [...]},
      "reco_axis":  {"variable": "rigidity", "unit": "GV", "edges": [...]},
      "variable_conversion": "text; required only if the two variables differ",
      "orientation": "rows_reco_cols_truth" | "rows_truth_cols_reco",
      "normalization": "conditional_on_selected" | "includes_efficiency" | "counts",
      "inefficiency": "inside_matrix" | "outside_matrix",
      "acceptance":   "inside_matrix" | "outside_matrix",
      "underflow_overflow": "explicit_bins" | "folded_into_edge_bins" | "not_represented",
      "efficiency_applied_separately": bool, "acceptance_applied_separately": bool},
   "matrix": [[...]],                  # entries per the declared normalization
   "underflow": [...], "overflow": [...],   # per truth bin (explicit_bins)
   "generated_per_truth_bin": [...],   # optional (normalization "counts")
   "closure": {"truth": [...], "reco": [...], "reco_sigma": [...]},   # optional
   "tolerances": {"normalization": 1e-6, "rank": 1e-12, "condition_warn": 1e4,
                  "min_efficiency": 1e-3, "pull_warn": 3.0}}
Normalization meanings (sums are over reco bins, plus explicit under/overflow, per truth bin):
  conditional_on_selected  each truth-bin sum = 1; inefficiency/acceptance live outside
  includes_efficiency      each truth-bin sum = efficiency <= 1; inefficiency lives inside
  counts                   raw counts; sums <= generated_per_truth_bin when supplied

Usage: python3 core/stats/validate_response.py FILE.json [--strict]
Exit codes: 0 pass (or warn without --strict); 1 errors; 2 unreadable or not JSON.
Standard library only.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

if __package__ in (None, ""):  # run as a script: put the plugin root on sys.path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import json
import math
import sys
from pathlib import Path

from core.stats.validate_covariance import Report, jacobi_eigh

DEFAULT_TOL = {"normalization": 1e-6, "rank": 1e-12, "condition_warn": 1e4,
               "min_efficiency": 1e-3, "pull_warn": 3.0}
ORIENTATIONS = ("rows_reco_cols_truth", "rows_truth_cols_reco")
NORMALIZATIONS = ("conditional_on_selected", "includes_efficiency", "counts")
PLACEMENT = ("inside_matrix", "outside_matrix")
FLOW = ("explicit_bins", "folded_into_edge_bins", "not_represented")


def _num(x) -> bool:
    return not isinstance(x, bool) and isinstance(x, (int, float)) and math.isfinite(x)


def _axis(meta: dict, key: str, report: Report) -> dict | None:
    axis = meta.get(key)
    if not isinstance(axis, dict):
        report.error(f"metadata.{key}", f"{key} must be an object with variable, unit and edges")
        return None
    ok = True
    for field in ("variable", "unit"):
        if not isinstance(axis.get(field), str) or not axis[field]:
            report.error(f"metadata.{key}.{field}", f"{key}.{field} is required")
            ok = False
    edges = axis.get("edges")
    if not isinstance(edges, list) or len(edges) < 2 or not all(_num(e) for e in edges):
        report.error(f"edges.{key}", f"{key}.edges must be a list of at least two finite numbers")
        return None
    if any(b <= a for a, b in zip(edges, edges[1:])):
        report.error(f"edges.{key}", f"{key}.edges must be strictly increasing")
        return None
    return axis if ok else None


def _matrix(raw, report: Report) -> list[list[float]] | None:
    if not isinstance(raw, list) or not raw or not all(isinstance(r, list) and r for r in raw):
        report.error("shape.malformed", "matrix must be a non-empty list of non-empty rows")
        return None
    if len({len(r) for r in raw}) != 1:
        report.error("shape.ragged", f"matrix rows have different lengths {sorted({len(r) for r in raw})}")
        return None
    if not all(_num(x) for r in raw for x in r):
        report.error("entries.nonfinite", "matrix has non-numeric or non-finite entries")
        return None
    return [[float(x) for x in r] for r in raw]


def _vector(doc: dict, key: str, n: int, report: Report) -> list[float] | None:
    raw = doc.get(key)
    if raw is None:
        return None
    if not isinstance(raw, list) or len(raw) != n or not all(_num(x) and x >= 0 for x in raw):
        report.error(f"{key}.malformed", f"{key} must be {n} non-negative finite numbers (one per truth bin)")
        return None
    return [float(x) for x in raw]


def _check_metadata(meta: dict, report: Report) -> None:
    for key, allowed in (("orientation", ORIENTATIONS), ("normalization", NORMALIZATIONS),
                         ("inefficiency", PLACEMENT), ("acceptance", PLACEMENT), ("underflow_overflow", FLOW)):
        if meta.get(key) not in allowed:
            report.error(f"metadata.{key}", f"{key} must be one of {list(allowed)}, got {meta.get(key)!r}")
    for key in ("efficiency_applied_separately", "acceptance_applied_separately"):
        if not isinstance(meta.get(key), bool):
            report.warn(f"metadata.{key}", f"{key} not declared as true/false: double counting or a missing correction cannot be excluded")


def _bookkeeping(meta: dict, report: Report) -> None:
    """Consistency between where the response says corrections live and where they are applied."""
    for effect, flag in (("inefficiency", "efficiency_applied_separately"), ("acceptance", "acceptance_applied_separately")):
        where, separate = meta.get(effect), meta.get(flag)
        if where == "inside_matrix" and separate is True:
            report.error(f"double_counting.{effect}", f"{effect} is declared inside the matrix and also applied separately: it would be counted twice")
        if where == "outside_matrix" and separate is False:
            report.error(f"bookkeeping.{effect}_not_applied", f"{effect} is declared outside the matrix but not applied anywhere: the correction is missing")
    norm = meta.get("normalization")
    if norm == "conditional_on_selected" and meta.get("inefficiency") == "inside_matrix":
        report.error("metadata.inconsistent", "normalization 'conditional_on_selected' means inefficiency is outside the matrix, but inefficiency is declared inside")
    if norm == "includes_efficiency" and meta.get("inefficiency") == "outside_matrix":
        report.error("metadata.inconsistent", "normalization 'includes_efficiency' means inefficiency is inside the matrix, but it is declared outside")


def _rank_and_condition(m: list[list[float]], tol: dict, report: Report, n_reco: int, n_truth: int) -> dict:
    """Identifiability from the singular values of the reco-by-truth matrix m[i][j] (via M^T M)."""
    gram = [[sum(m[k][i] * m[k][j] for k in range(n_reco)) for j in range(n_truth)] for i in range(n_truth)]
    values, _ = jacobi_eigh(gram)
    lmax = max(values[-1], 0.0)
    metrics: dict = {}
    if lmax <= 0:
        report.error("identifiability.zero_matrix", "the matrix is identically zero")
        return {"numerical_rank": 0}
    rank = sum(1 for v in values if v > tol["rank"] * lmax)
    metrics["numerical_rank"] = rank
    metrics["n_truth_bins"] = n_truth
    if n_reco < n_truth:
        report.error("identifiability.underdetermined", f"{n_reco} reconstructed bins cannot determine {n_truth} truth bins without regularization or a model")
    if rank < n_truth:
        report.error("identifiability.rank_deficient", f"numerical rank {rank} < {n_truth} truth bins: some truth combinations are invisible to the data (phase-space hole or degenerate bins)")
    else:
        cond = math.sqrt(lmax / max(values[0], 1e-300))
        metrics["condition_number"] = cond
        if cond > tol["condition_warn"]:
            report.warn("identifiability.ill_conditioned", f"condition number {cond:.2e} exceeds {tol['condition_warn']:.1e}: unfolding will amplify noise; regularization or coarser bins are needed")
    return metrics


def _closure(doc: dict, m: list[list[float]], n_reco: int, n_truth: int, norm: str, tol: dict, report: Report) -> dict | None:
    c = doc.get("closure")
    if c is None:
        return None
    truth, reco, sig = (c.get("truth"), c.get("reco"), c.get("reco_sigma")) if isinstance(c, dict) else (None, None, None)
    if (not isinstance(truth, list) or len(truth) != n_truth or not isinstance(reco, list) or len(reco) != n_reco
            or not all(_num(x) for x in truth + reco)
            or (sig is not None and (not isinstance(sig, list) or len(sig) != n_reco or not all(_num(x) and x > 0 for x in sig)))):
        report.error("closure.malformed", f"closure needs truth ({n_truth}), reco ({n_reco}) and optionally positive reco_sigma ({n_reco}) numbers")
        return None
    pred = [sum(m[i][j] * truth[j] for j in range(n_truth)) for i in range(n_reco)]
    pulls, skipped = [], []
    for i in range(n_reco):
        sigma = sig[i] if sig else math.sqrt(pred[i]) if pred[i] > 0 else 0.0
        if sigma > 0:
            pulls.append((reco[i] - pred[i]) / sigma)
        else:
            skipped.append(i)
    interp = {"conditional_on_selected": "truth = selected-event truth (efficiency and acceptance already applied by the caller)",
              "includes_efficiency": "truth = generated events in the fiducial phase space",
              "counts": "truth = generated event counts matching the matrix counts"}[norm]
    out = {"truth_interpretation": interp, "predicted_reco": pred, "residuals": [r - p for r, p in zip(reco, pred)],
           "sigma_source": "supplied reco_sigma" if sig else "Poisson sqrt(predicted)", "skipped_bins_zero_sigma": skipped}
    if pulls:
        out.update({"chi2": sum(p * p for p in pulls), "ndof": len(pulls), "mean_pull": sum(pulls) / len(pulls),
                    "rms_pull": math.sqrt(sum(p * p for p in pulls) / len(pulls)), "max_abs_pull": max(abs(p) for p in pulls)})
        if out["max_abs_pull"] > tol["pull_warn"]:
            report.warn("closure.large_pull", f"max |pull| {out['max_abs_pull']:.2f} exceeds {tol['pull_warn']}")
    return out


def validate_response(doc: dict) -> dict:
    """Validate a response document (see module docstring). Returns the report dict."""
    report = Report()
    tol = dict(DEFAULT_TOL)
    if not isinstance(doc, dict):
        report.error("document.malformed", f"the document must be a JSON object, got {type(doc).__name__}")
        return {"status": report.status(), "errors": report.errors, "warnings": report.warnings, "metrics": {}}
    if isinstance(doc.get("tolerances"), dict):
        for k, v in doc["tolerances"].items():
            if k not in tol:
                continue
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                report.error("tolerances.malformed", f"tolerance '{k}' must be a finite non-negative number, got {v!r}")
            else:
                tol[k] = float(v)
    report.metrics["tolerances"] = tol
    meta = doc.get("metadata")
    result = {"physical_validity": "not_assessed", "input_modified": False,
              "note": "Correct normalization or closure shows internal consistency only; validate the response against data and alternative models."}
    if not isinstance(meta, dict):
        report.error("metadata.missing", "metadata object is required")
        return {"status": report.status(), "errors": report.errors, "warnings": report.warnings, "metrics": report.metrics, **result}
    _check_metadata(meta, report)
    truth_axis, reco_axis = _axis(meta, "truth_axis", report), _axis(meta, "reco_axis", report)
    matrix = _matrix(doc.get("matrix"), report)
    if truth_axis and reco_axis:
        if truth_axis["variable"] != reco_axis["variable"]:
            if not meta.get("variable_conversion"):
                report.error("axes.variable_mismatch", f"truth is '{truth_axis['variable']}' but reco is '{reco_axis['variable']}' with no variable_conversion declared")
        elif truth_axis["unit"] != reco_axis["unit"]:
            report.error("axes.unit_mismatch", f"same variable with different units: {truth_axis['unit']} vs {reco_axis['unit']}")
        else:
            te, re_ = truth_axis["edges"], reco_axis["edges"]
            if re_[-1] <= te[0] or re_[0] >= te[-1]:
                report.error("edges.no_overlap", "truth and reco ranges do not overlap")
    _bookkeeping(meta, report)
    if not (truth_axis and reco_axis and matrix) or report.errors and any(e["code"].startswith(("shape", "entries")) for e in report.errors):
        return {"status": report.status(), "errors": report.errors, "warnings": report.warnings, "metrics": report.metrics, **result}

    n_truth, n_reco = len(truth_axis["edges"]) - 1, len(reco_axis["edges"]) - 1
    rows, cols = len(matrix), len(matrix[0])
    orient = meta.get("orientation")
    expected = (n_reco, n_truth) if orient == "rows_reco_cols_truth" else (n_truth, n_reco)
    report.metrics.update({"n_truth_bins": n_truth, "n_reco_bins": n_reco, "matrix_shape": [rows, cols]})
    if orient not in ORIENTATIONS or (rows, cols) != expected:
        if orient in ORIENTATIONS and (rows, cols) == expected[::-1] and expected[0] != expected[1]:
            report.error("orientation.shape_transposed", f"shape {rows}x{cols} matches the opposite of the declared orientation '{orient}'")
        elif orient in ORIENTATIONS:
            report.error("dimensions.mismatch", f"shape {rows}x{cols} does not match {n_reco} reco and {n_truth} truth bins for orientation '{orient}'")
        return {"status": report.status(), "errors": report.errors, "warnings": report.warnings, "metrics": report.metrics, **result}

    m = matrix if orient == "rows_reco_cols_truth" else [list(col) for col in zip(*matrix)]  # m[i][j]: reco i, truth j
    scale = max(abs(x) for r in m for x in r) or 1.0
    if any(x < -1e-12 * scale for r in m for x in r):
        report.error("entries.negative", "matrix has negative entries; probabilities and counts are non-negative")
    under = _vector(doc, "underflow", n_truth, report)
    over = _vector(doc, "overflow", n_truth, report)
    flow = meta.get("underflow_overflow")
    if flow == "explicit_bins" and (under is None or over is None):
        report.warn("overflow.vectors_missing", "underflow_overflow is 'explicit_bins' but underflow/overflow vectors are not both supplied; lost probability cannot be closed")
    elif flow != "explicit_bins" and (under or over):
        report.warn("overflow.vectors_ignored", f"underflow/overflow vectors are supplied but underflow_overflow is '{flow}'")
    under_v, over_v = under or [0.0] * n_truth, over or [0.0] * n_truth
    truth_in = [sum(m[i][j] for i in range(n_reco)) for j in range(n_truth)]
    truth_sum = [truth_in[j] + under_v[j] + over_v[j] for j in range(n_truth)]
    reco_sum = [sum(m[i]) for i in range(n_reco)]
    report.metrics.update({
        "truth_bin_in_range_sum": truth_in, "truth_bin_total_sum": truth_sum, "reco_bin_sum": reco_sum,
        "underflow": under_v, "overflow": over_v})

    norm, nt = meta.get("normalization"), tol["normalization"]
    generated = doc.get("generated_per_truth_bin")
    declared_ok, other_ok = True, None
    if norm == "conditional_on_selected":
        lost = [1.0 - s for s in truth_sum]
        declared_ok = all(abs(s - 1.0) <= nt for j, s in enumerate(truth_sum) if truth_in[j] > 0)
        other_ok = all(abs(s - 1.0) <= nt for s in reco_sum)
        report.metrics["lost_probability"] = lost
        if not declared_ok:
            report.error("normalization.truth_sum", f"truth-bin sums {[round(s, 6) for s in truth_sum]} are not 1 under 'conditional_on_selected' (probability lost or duplicated)")
            if flow == "not_represented" and all(s <= 1.0 + nt for s in truth_sum):
                report.error("overflow.lost_probability", "probability leaves the reco axes and underflow/overflow is 'not_represented'; migration outside the range is unaccounted")
    elif norm == "includes_efficiency":
        lost = [1.0 - s for s in truth_sum]
        declared_ok = all(s <= 1.0 + nt for s in truth_sum)
        other_ok = all(s <= 1.0 + nt for s in reco_sum)
        report.metrics["inefficiency_per_truth_bin"] = lost
        if not declared_ok:
            report.error("normalization.exceeds_one", f"truth-bin sums {[round(s, 6) for s in truth_sum]} exceed 1 but inefficiency is declared inside the matrix")
        if declared_ok and all(abs(s - 1.0) <= nt for s in truth_sum):
            report.warn("double_counting.efficiency_not_visible", "inefficiency is declared inside the matrix but every truth bin sums to 1: it is either mislabeled conditional or efficiency is 1")
        low = [j for j, s in enumerate(truth_sum) if 0 < s < tol["min_efficiency"]]
        if low:
            report.warn("holes.low_efficiency", f"truth bins {low} have efficiency below {tol['min_efficiency']}")
    elif norm == "counts":
        if isinstance(generated, list) and len(generated) == n_truth and all(_num(g) and g >= 0 for g in generated):
            over_gen = [j for j in range(n_truth) if truth_sum[j] > generated[j] * (1 + nt) + nt]
            report.metrics["lost_counts"] = [g - s for g, s in zip(generated, truth_sum)]
            if over_gen:
                report.error("normalization.exceeds_generated", f"truth bins {over_gen} contain more counts than were generated")
        else:
            report.warn("normalization.no_generated", "normalization 'counts' without generated_per_truth_bin: lost counts and efficiency cannot be checked")

    if norm in ("conditional_on_selected", "includes_efficiency") and not declared_ok and other_ok:
        report.error("orientation.likely_transposed", "sums along the OTHER axis satisfy the declared normalization: the matrix is probably transposed relative to metadata.orientation")

    empty_truth = [j for j in range(n_truth) if truth_sum[j] == 0]
    empty_reco = [i for i in range(n_reco) if reco_sum[i] == 0]
    if empty_truth:
        report.error("empty.truth_bin", f"truth bins {empty_truth} have no response at all: a phase-space hole, unfolding cannot constrain them")
    if empty_reco:
        report.warn("empty.reco_bin", f"reco bins {empty_reco} receive nothing from any truth bin: data counts there cannot be explained")
    if not empty_truth:
        report.metrics.update(_rank_and_condition(m, tol, report, n_reco, n_truth))
    else:
        keep = [j for j in range(n_truth) if j not in empty_truth]
        if keep:
            report.metrics.update(_rank_and_condition([[m[i][j] for j in keep] for i in range(n_reco)], tol, Report(), n_reco, len(keep)))
    closure = _closure(doc, m, n_reco, n_truth, norm if norm in NORMALIZATIONS else "counts", tol, report) if not report.errors else None
    if closure is not None:
        report.metrics["closure"] = closure
    return {"status": report.status(), "errors": report.errors, "warnings": report.warnings, "metrics": report.metrics, **result}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("file", type=Path, help="JSON file described above")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("top level must be a JSON object")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}, indent=2))
        return 2
    result = validate_response(doc)
    print(json.dumps(result, indent=2))
    if result["status"] == "fail" or (args.strict and result["status"] == "warn"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
