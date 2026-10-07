#!/usr/bin/env python3
"""Validate a covariance matrix (and optional statistical/systematic blocks) without modifying it.

Purpose: catch covariance defects that silently bias a fit of an unfolded spectrum,
a ratio, or a combined systematic (asymmetry, negative variance, non-PSD, impossible
correlations, zero-variance rows with covariance, near-singularity, blocks that do
not add up).

What it does: reads a JSON document, runs the checks, and prints errors, warnings,
diagnostic metrics and a machine-readable status. It never replaces the matrix.
The optional --demo-psd-clip computes an eigenvalue-clipped matrix strictly as a
[Proposal] diagnostic and reports how much eigenvalues, diagonal entries,
correlations and the total uncertainty change; it is not a repair recipe (a
construction error must be fixed at its source).

Input JSON:
  {"labels": ["b0","b1",...],            # required, unique, length n
   "matrix": [[...], ...],               # required, n x n (this is the TOTAL if blocks are given)
   "kind": "absolute" | "relative",      # required (relative = dimensionless fractions)
   "units": "m^-2 sr^-1 s^-1 GV^-1",     # recommended; absolute matrices use squared flux units
   "blocks": {"stat": [[...]], "syst": [[...]]},   # optional; matrix must equal their sum
   "weights": [...],                     # optional, for the total-uncertainty metric (default all ones)
   "tolerances": {"symmetry": 1e-8, "psd": 1e-8, "correlation": 1e-8,
                  "condition_warn": 1e10, "rank": 1e-12, "block_sum": 1e-8}}
Tolerances are relative: symmetry, correlation and block_sum to the largest |entry|;
psd and rank to the largest eigenvalue.

Usage: python3 core/stats/validate_covariance.py FILE.json [--strict] [--demo-psd-clip]
Exit codes: 0 pass (or warn without --strict); 1 errors (or warnings with --strict);
2 file unreadable or not JSON. Standard library only.
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

DEFAULT_TOL = {"symmetry": 1e-8, "psd": 1e-8, "correlation": 1e-8,
               "condition_warn": 1e10, "rank": 1e-12, "block_sum": 1e-8}
EPS = sys.float_info.epsilon


def jacobi_eigh(matrix: list[list[float]], max_sweeps: int = 100) -> tuple[list[float], list[list[float]]]:
    """Eigen-decomposition of a real symmetric matrix by cyclic Jacobi rotations.
    Returns (eigenvalues ascending, eigenvectors as columns in matching order)."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    scale = sum(x * x for row in a for x in row) or 1.0
    for _ in range(max_sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(i + 1, n))
        if off <= (EPS ** 2) * scale * 1e-4:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if apq == 0.0:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    order = sorted(range(n), key=lambda i: a[i][i])
    return [a[i][i] for i in order], [[v[k][i] for i in order] for k in range(n)]


class Report:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.metrics: dict = {}

    def error(self, code: str, message: str) -> None:
        self.errors.append({"code": code, "message": message})

    def warn(self, code: str, message: str) -> None:
        self.warnings.append({"code": code, "message": message})

    def status(self) -> str:
        return "fail" if self.errors else ("warn" if self.warnings else "pass")


def _as_matrix(raw, name: str, report: Report) -> list[list[float]] | None:
    """Return a float matrix, or record a malformed-input error and return None."""
    if not isinstance(raw, list) or not raw or not all(isinstance(r, list) for r in raw):
        report.error("shape.malformed", f"{name} must be a non-empty list of rows")
        return None
    bad = [(i, j) for i, r in enumerate(raw) for j, x in enumerate(r)
           if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)]
    if bad:
        report.error("entries.nonfinite", f"{name} has {len(bad)} non-numeric or non-finite entries, first at row {bad[0][0]}, col {bad[0][1]}")
        return None
    n = len(raw)
    if any(len(r) != n for r in raw):
        report.error("shape.non_square", f"{name} is not square: row lengths {sorted({len(r) for r in raw})} for {n} rows")
        return None
    return [[float(x) for x in r] for r in raw]


def _max_abs(m: list[list[float]]) -> float:
    return max((abs(x) for r in m for x in r), default=0.0)


def _check_matrix(name: str, m: list[list[float]], tol: dict, report: Report, prefix: str) -> dict:
    """Symmetry, diagonal, zero-variance, correlation, PSD and conditioning checks for one matrix."""
    n = len(m)
    scale = _max_abs(m) or 1.0
    asym = max((abs(m[i][j] - m[j][i]) for i in range(n) for j in range(i)), default=0.0)
    metrics = {"n": n, "max_abs_entry": scale, "max_asymmetry": asym}
    if asym > tol["symmetry"] * scale:
        report.error(f"{prefix}symmetry", f"{name}: max |C_ij - C_ji| = {asym:.3e} exceeds {tol['symmetry']:.1e} x max|entry|")
    s = [[(m[i][j] + m[j][i]) / 2.0 for j in range(n)] for i in range(n)]
    diag = [s[i][i] for i in range(n)]
    neg = [i for i, d in enumerate(diag) if d < 0]
    if neg:
        report.error(f"{prefix}negative_diagonal", f"{name}: negative variance in rows {neg}")
    dmax = max(diag) if diag else 0.0
    zero_rows = [i for i, d in enumerate(diag) if abs(d) <= 1e-15 * max(dmax, 1e-300)]
    for i in zero_rows:
        cov = max((abs(s[i][j]) for j in range(n) if j != i), default=0.0)
        if cov > tol["symmetry"] * scale:
            report.error(f"{prefix}zero_variance_covariance", f"{name}: row {i} has zero variance but covariance up to {cov:.3e}")
    metrics["zero_variance_rows"] = zero_rows
    max_rho, bad_rho = 0.0, []
    for i in range(n):
        for j in range(i):
            if diag[i] > 0 and diag[j] > 0:
                rho = s[i][j] / math.sqrt(diag[i] * diag[j])
                max_rho = max(max_rho, abs(rho))
                if abs(rho) > 1.0 + tol["correlation"]:
                    bad_rho.append((j, i, rho))
    metrics["max_abs_correlation"] = max_rho
    if bad_rho:
        j, i, rho = bad_rho[0]
        report.error(f"{prefix}correlation_bound", f"{name}: {len(bad_rho)} correlation(s) outside [-1, 1]; first rho[{j},{i}] = {rho:.6f}")
    if any(not math.isfinite(x) for x in diag):
        return metrics
    values, _ = jacobi_eigh(s)
    lmax, lmin = values[-1], values[0]
    noise = 10.0 * n * EPS * max(abs(lmax), abs(lmin))
    metrics.update({"eigenvalue_min": lmin, "eigenvalue_max": lmax, "roundoff_level": noise})
    if lmin < -noise:
        if lmin >= -tol["psd"] * max(lmax, 1e-300):
            report.warn(f"{prefix}psd_small_negative", f"{name}: smallest eigenvalue {lmin:.3e} is beyond round-off ({noise:.1e}) but within the stated PSD tolerance {tol['psd']:.1e} x largest")
        else:
            report.error(f"{prefix}not_psd", f"{name}: smallest eigenvalue {lmin:.3e} is negative beyond tolerance ({tol['psd']:.1e} x largest {lmax:.3e}); suspect a construction error, not numerics")
    positive = [x for x in values if x > tol["rank"] * lmax]
    metrics["numerical_rank"] = len(positive) if lmax > 0 else 0
    if lmax > 0 and lmin > 0:
        cond = lmax / lmin
        metrics["condition_number"] = cond
        if cond > tol["condition_warn"]:
            report.warn(f"{prefix}ill_conditioned", f"{name}: condition number {cond:.2e} exceeds {tol['condition_warn']:.1e}")
    elif lmax > 0:
        metrics["condition_number"] = None  # singular: smallest eigenvalue <= 0
    if lmax > 0 and len(positive) < n:
        report.warn(f"{prefix}rank_deficient", f"{name}: numerical rank {len(positive)} < {n}; may mean an implicit constraint or an over-regularized unfolding")
    return metrics


def clip_demo(m: list[list[float]], weights: list[float] | None) -> dict:
    """[Proposal] diagnostic: clip negative eigenvalues; report the changes. Input is not modified."""
    n = len(m)
    s = [[(m[i][j] + m[j][i]) / 2.0 for j in range(n)] for i in range(n)]
    values, vec = jacobi_eigh(s)
    clipped = [max(x, 0.0) for x in values]
    c = [[sum(vec[i][k] * clipped[k] * vec[j][k] for k in range(n)) for j in range(n)] for i in range(n)]

    def corr(mat):
        return [[mat[i][j] / math.sqrt(mat[i][i] * mat[j][j]) if mat[i][i] > 0 and mat[j][j] > 0 else 0.0
                 for j in range(n)] for i in range(n)]

    def variance(mat):
        w = weights or [1.0] * n
        return sum(w[i] * mat[i][j] * w[j] for i in range(n) for j in range(n))

    r0, r1 = corr(s), corr(c)
    v0, v1 = variance(s), variance(c)
    t0 = math.sqrt(v0) if v0 >= 0 else None  # a negative total variance is itself a defect
    t1 = math.sqrt(v1) if v1 >= 0 else None
    return {
        "label": "[Proposal] diagnostic only; the supplied matrix was not modified",
        "eigenvalues_before": values, "eigenvalues_after": clipped,
        "eigenvalues_clipped": sum(1 for a, b in zip(values, clipped) if a != b),
        "max_abs_eigenvalue_change": max(abs(a - b) for a, b in zip(values, clipped)),
        "max_relative_diagonal_change": max((abs(c[i][i] - s[i][i]) / s[i][i] for i in range(n) if s[i][i] > 0), default=0.0),
        "max_abs_correlation_change": max((abs(r1[i][j] - r0[i][j]) for i in range(n) for j in range(n)), default=0.0),
        "total_variance_before": v0, "total_variance_after": v1,
        "total_uncertainty_before": t0, "total_uncertainty_after": t1,
        "total_uncertainty_relative_change": (t1 - t0) / t0 if t0 and t1 is not None else None,
        "total_uncertainty_weights": "supplied" if weights else "all ones (sum over all bins)",
        "caution": "clipping is defensible only for round-off-level negatives; otherwise fix the construction",
    }


def validate_covariance(doc: dict, demo_clip: bool = False) -> dict:
    """Validate a covariance document (see module docstring). Returns the report dict."""
    report = Report()
    tol = dict(DEFAULT_TOL)
    if isinstance(doc.get("tolerances"), dict):
        tol.update({k: float(v) for k, v in doc["tolerances"].items() if k in tol})
    report.metrics["tolerances"] = tol
    if doc.get("kind") not in ("absolute", "relative"):
        report.error("metadata.kind", "kind must be 'absolute' or 'relative'")
    if not doc.get("units"):
        report.warn("metadata.units", "units not declared; absolute matrices need squared quantity units")
    matrix = _as_matrix(doc.get("matrix"), "matrix", report)
    labels = doc.get("labels")
    if matrix is not None:
        n = len(matrix)
        if not isinstance(labels, list) or len(labels) != n:
            report.error("labels.dimension", f"labels must be a list of {n} entries matching the matrix, got {None if labels is None else len(labels)}")
        elif len(set(map(str, labels))) != n:
            report.error("labels.duplicate", "labels are not unique")
    elif not isinstance(labels, list):
        report.error("labels.dimension", "labels missing")
    if matrix is not None and not any(e["code"].startswith("shape") or e["code"].startswith("entries") for e in report.errors):
        report.metrics["total"] = _check_matrix("matrix", matrix, tol, report, "")
    blocks = doc.get("blocks")
    if isinstance(blocks, dict) and blocks and matrix is not None:
        parsed = {}
        for name, raw in blocks.items():
            m = _as_matrix(raw, f"block '{name}'", report)
            if m is None:
                continue
            if len(m) != len(matrix):
                report.error("blocks.dimension", f"block '{name}' has size {len(m)} but the total matrix has size {len(matrix)}")
                continue
            parsed[name] = m
            report.metrics[f"block_{name}"] = _check_matrix(f"block '{name}'", m, tol, report, f"block.{name}.")
        if len(parsed) == len(blocks):
            n = len(matrix)
            total_sum = [[sum(b[i][j] for b in parsed.values()) for j in range(n)] for i in range(n)]
            diff = max(abs(matrix[i][j] - total_sum[i][j]) for i in range(n) for j in range(n))
            scale = _max_abs(matrix) or 1.0
            report.metrics["block_sum_max_abs_difference"] = diff
            if diff > tol["block_sum"] * scale:
                report.error("blocks.sum_mismatch", f"matrix differs from the sum of blocks {sorted(parsed)} by up to {diff:.3e}")
            for name, b in parsed.items():
                worse = [i for i in range(n) if b[i][i] > matrix[i][i] + tol["block_sum"] * scale]
                if worse:
                    report.error("blocks.component_exceeds_total", f"block '{name}' variance exceeds the total in rows {worse}")
    elif blocks is not None and not isinstance(blocks, dict):
        report.error("blocks.malformed", "blocks must be an object mapping names to matrices")
    result = {"status": report.status(), "errors": report.errors, "warnings": report.warnings,
              "metrics": report.metrics, "input_modified": False,
              "note": "Passing checks means self-consistency only; it does not show the covariance is the right one."}
    if demo_clip and matrix is not None and not any(e["code"].startswith(("shape", "entries")) for e in report.errors):
        weights = doc.get("weights") if isinstance(doc.get("weights"), list) and len(doc["weights"]) == len(matrix) else None
        result["diagnostic_proposal"] = clip_demo(matrix, weights)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("file", type=Path, help="JSON file described above")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    parser.add_argument("--demo-psd-clip", action="store_true", help="add an eigenvalue-clipping [Proposal] diagnostic")
    args = parser.parse_args(argv)
    try:
        doc = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("top level must be a JSON object")
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}, indent=2))
        return 2
    result = validate_covariance(doc, demo_clip=args.demo_psd_clip)
    print(json.dumps(result, indent=2))
    if result["status"] == "fail" or (args.strict and result["status"] == "warn"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
