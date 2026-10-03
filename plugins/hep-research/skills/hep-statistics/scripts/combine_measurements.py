#!/usr/bin/env python3
"""Combine measurements of one binned observable by generalized least squares, after the combination plan allows it.

Purpose: a combination is only as good as its joint covariance. This script first runs the contracts combination
plan (same observable after the comparison gate, covariance present for every input, every cross-dataset block
declared with evidence or a scoped assumption, shared auxiliary measurements declared, no envelope put into a
Gaussian matrix). Only then does it solve x = (H^T C^-1 H)^-1 H^T C^-1 y with the full joint covariance C.

Input JSON: {"datasets": [{"id", "observable", "covariance": "present", "auxiliary": [...], "uncertainties": [...],
              "values": [...]}...], "correlations": [...], "joint_covariance": [[...]]}
  joint_covariance is the full matrix over the concatenated values (dataset order), cross blocks included.
Output: JSON {"status": "combined" | "refused", "plan", "values", "covariance", "chi2", "ndf"}.
Exit codes: 0 combined, 1 refused by the plan or a non-positive-definite matrix, 2 unreadable input.
Run: python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-statistics/scripts/combine_measurements.py input.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from contracts.comparison.combination import plan_combination  # noqa: E402


def gls(values_list, cov):
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


def combine(doc: dict) -> dict:
    plan = plan_combination(doc["datasets"], doc.get("correlations", []))
    if not plan["combinable"]:
        return {"status": "refused", "plan": plan}
    try:
        x, cov, chi2, ndf = gls([d["values"] for d in doc["datasets"]], doc["joint_covariance"])
    except (ValueError, np.linalg.LinAlgError) as exc:
        return {"status": "refused", "plan": plan, "reason": str(exc)}
    return {"status": "combined", "plan": plan, "values": x.tolist(), "covariance": cov.tolist(), "chi2": chi2, "ndf": ndf}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1 or args[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    res = combine(doc)
    print(json.dumps(res, indent=1))
    return 0 if res["status"] == "combined" else 1


if __name__ == "__main__":
    sys.exit(main())
