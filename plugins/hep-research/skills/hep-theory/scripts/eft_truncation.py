#!/usr/bin/env python3
"""Dimension-6 EFT prediction from supplied SM, linear and quadratic coefficients, with the truncation made explicit.

Purpose: keep the conventions of an EFT prediction visible (see <plugin root>/skills/hep-theory/references/smeft-and-eft.md):
  X(C) = X_SM + sum_i (C_i / Lambda^2) A_i + sum_ij (C_i C_j / Lambda^4) B_ij      (B symmetric, i <= j counted once)
The script evaluates the linear (order 1/Lambda^2) and the linear+quadratic (adds 1/Lambda^4 squared dimension-6
terms) predictions, their ratio, and flags points where the quadratic part exceeds a stated fraction of the
linear part (the truncation is then not under control). It checks that only C/Lambda^2 enters (rescaling C and
Lambda together leaves X unchanged) and refuses coefficient keys that are not in the declared operator list.
It does not compute A or B: they come from a generator or a paper with their basis, normalization and input scheme.

Input JSON: {"basis": "...", "normalization": "C_i / Lambda^2", "input_scheme": "...", "lambda_tev": 1.0,
             "operators": ["cHq3", ...], "x_sm": float, "linear": {"cHq3": A, ...},
             "quadratic": {"cHq3*cHq3": B, ...}, "points": [{"cHq3": 0.5}, ...], "quadratic_flag_fraction": 0.3}
Run: python3 eft_truncation.py input.json. Exit 0 ok (flags reported), 1 refused input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys

REQUIRED = ("basis", "normalization", "input_scheme", "lambda_tev", "operators", "x_sm", "linear")


def evaluate(doc: dict) -> dict:
    missing = [k for k in REQUIRED if k not in doc]
    if missing:
        raise ValueError(f"missing convention or input fields: {missing}")
    ops = set(doc["operators"])
    lam2 = float(doc["lambda_tev"]) ** 2
    quad = doc.get("quadratic", {})
    unknown = [k for k in doc["linear"] if k not in ops] + [p for k in quad for p in k.split("*") if p not in ops]
    if unknown:
        raise ValueError(f"coefficients not in the declared operator list: {sorted(set(unknown))}")
    frac = float(doc.get("quadratic_flag_fraction", 0.3))
    rows = []
    for pt in doc.get("points", []):
        bad = [k for k in pt if k not in ops]
        if bad:
            raise ValueError(f"point uses undeclared operators {bad}")
        lin = sum(float(pt.get(k, 0.0)) * a for k, a in doc["linear"].items()) / lam2
        qd = sum(float(pt.get(i, 0.0)) * float(pt.get(j, 0.0)) * b
                 for key, b in quad.items() for i, j in [key.split("*")]) / lam2 ** 2
        rows.append({"point": pt, "linear_term": lin, "quadratic_term": qd, "x_linear": doc["x_sm"] + lin,
                     "x_linear_plus_quadratic": doc["x_sm"] + lin + qd,
                     "truncation_flag": bool(quad) and abs(qd) > frac * abs(lin)})
    return {"basis": doc["basis"], "normalization": doc["normalization"], "input_scheme": doc["input_scheme"],
            "lambda_tev": doc["lambda_tev"], "quadratic_terms_supplied": bool(quad), "points": rows,
            "note": "linear and linear+quadratic are different truncations, not an uncertainty band; "
                    "dimension-8 terms at 1/Lambda^4 are not included in either"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    opts = ap.parse_args(argv)
    try:
        out = evaluate(json.loads(open(opts.input, encoding="utf-8").read()))
    except ValueError as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}))
        return 1
    print(json.dumps(dict(out, status="ok"), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
