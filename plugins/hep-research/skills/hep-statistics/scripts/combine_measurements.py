#!/usr/bin/env python3
"""Combine measurements of one binned observable by generalized least squares, after the combination plan allows it.

Purpose: a combination is only as good as its joint covariance. This script first runs the contracts combination
plan (same observable after the comparison gate, covariance present for every input, every cross-dataset block
declared with evidence or a scoped assumption, shared auxiliary measurements declared, no envelope put into a
Gaussian matrix). Only then does it solve x = (H^T C^-1 H)^-1 H^T C^-1 y with the full joint covariance C.

Input JSON: {"datasets": [{"id", "observable", "covariance": "present", "auxiliary": [...], "uncertainties": [...],
              "values": [...]}...], "correlations": [...], "joint_covariance": [[...]]}
  joint_covariance is the full matrix over the concatenated values (dataset order), cross blocks included.
  Every dataset must have the same number of bins. The cross blocks must agree with the declared correlations: a pair
  declared only independent needs an all-zero block, a pair with a declared correlation needs a non-zero block.
Output: JSON {"status": "combined" | "refused", "plan", "values", "covariance", "chi2", "ndf"}.
Exit codes: 0 combined, 1 refused by the plan, a matrix contradicting the declared correlations or a
non-positive-definite matrix, 2 unreadable input or numpy not installed.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/combine_measurements.py input.json
Requires numpy (not needed for --help).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # --help works without numpy; combine() reports it
    np = None

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from contracts.comparison.combination import plan_combination  # noqa: E402


def gls(values_list, cov):
    if len({len(v) for v in values_list}) != 1:
        raise ValueError(f"every dataset needs the same number of bins; got {[len(v) for v in values_list]}")
    y = np.concatenate([np.asarray(v, float) for v in values_list])
    n = len(values_list[0])
    h = np.vstack([np.eye(n)] * len(values_list))
    c = np.asarray(cov, float)
    if c.shape != (len(y), len(y)) or not np.allclose(c, c.T, rtol=0, atol=1e-12 * np.abs(c).max()):
        raise ValueError("joint covariance must be square, symmetric and match the concatenated values")
    np.linalg.cholesky(c)  # raises LinAlgError when not positive definite
    ci = np.linalg.inv(c)
    cov_x = np.linalg.inv(h.T @ ci @ h)
    x = cov_x @ h.T @ ci @ y
    r = y - h @ x
    return x, cov_x, float(r @ ci @ r), len(y) - n


def cross_block_conflicts(datasets, cov, plan) -> list:
    """Cross blocks of the joint covariance that contradict the declared correlations (plan["cross_blocks"])."""
    c = np.asarray(cov, float)
    starts = np.cumsum([0] + [len(d["values"]) for d in datasets])
    if c.ndim != 2 or c.shape[0] != starts[-1] or c.shape[1] != starts[-1]:
        return []  # gls reports the shape mismatch
    atol = 1e-12 * np.abs(c).max() if c.size else 0.0
    conflicts = []
    for i, a in enumerate(datasets):
        for j in range(i + 1, len(datasets)):
            b = datasets[j]
            decl = plan["cross_blocks"].get(" x ".join(sorted((a["id"], b["id"]))), [])
            nonzero = bool(np.any(np.abs(c[starts[i]:starts[i + 1], starts[j]:starts[j + 1]]) > atol))
            correlated = any(not d.get("independent") for d in decl)
            if decl and not correlated and nonzero:
                conflicts.append(f"{a['id']} and {b['id']} are declared independent but their joint_covariance cross block is non-zero")
            elif correlated and not nonzero:
                conflicts.append(f"{a['id']} and {b['id']} have a declared correlation but their joint_covariance cross block is zero")
    return conflicts


def combine(doc: dict) -> dict:
    if np is None:
        raise ImportError("numpy is required to combine measurements; install it (pip install numpy)")
    plan = plan_combination(doc["datasets"], doc.get("correlations", []))
    if not plan["combinable"]:
        return {"status": "refused", "plan": plan}
    try:
        conflicts = cross_block_conflicts(doc["datasets"], doc["joint_covariance"], plan)
        if conflicts:
            return {"status": "refused", "plan": plan,
                    "reason": "joint_covariance contradicts the declared correlations: " + "; ".join(conflicts)}
        x, cov, chi2, ndf = gls([d["values"] for d in doc["datasets"]], doc["joint_covariance"])
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {"status": "refused", "plan": plan, "reason": str(exc)}
    return {"status": "combined", "plan": plan, "values": x.tolist(), "covariance": cov.tolist(), "chi2": chi2, "ndf": ndf}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if len(args) != 1:
        print(__doc__)
        return 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    try:
        res = combine(doc)
    except ImportError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    print(json.dumps(res, indent=1))
    return 0 if res["status"] == "combined" else 1


if __name__ == "__main__":
    sys.exit(main())
