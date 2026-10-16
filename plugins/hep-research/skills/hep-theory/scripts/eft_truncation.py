#!/usr/bin/env python3
"""Dimension-6 EFT prediction from supplied SM, linear and quadratic coefficients, with the truncation made explicit.

Purpose: keep the conventions of an EFT prediction visible (see <plugin root>/skills/hep-theory/references/smeft-and-eft.md):
  X(C) = X_SM + sum_i (C_i / Lambda^2) A_i + sum_ij (C_i C_j / Lambda^4) B_ij      (B symmetric, i <= j counted once)
The script evaluates the linear (order 1/Lambda^2) and the linear+quadratic (adds 1/Lambda^4 squared dimension-6
terms) predictions, their ratio, and flags points where the quadratic part exceeds a stated fraction of the
linear part (the truncation is then not under control). It checks that only C/Lambda^2 enters: every point is re-evaluated at (4 C, 2 Lambda) and must give the same linear
and quadratic terms within a relative 1e-12 (`rescaling_check`). It refuses coefficient keys that are not in the
declared operator list, quadratic keys that are not one 'i*j' pair, the same pair spelled twice ('a*b' and 'b*a'),
empty conventions or operator list, lambda_tev <= 0, and non-finite numbers. An off-diagonal B_ij multiplies
C_i C_j once (no implicit factor 2); an input with one must state `cross_term_convention`. The flag fraction used
(default 0.3) is reported with its source.
It does not compute A or B: they come from a generator or a paper with their basis, normalization and input scheme.

Input JSON: {"basis": "...", "normalization": "C_i / Lambda^2", "input_scheme": "...", "lambda_tev": 1.0,
             "operators": ["cHq3", ...], "x_sm": float, "linear": {"cHq3": A, ...},
             "quadratic": {"cHq3*cHq3": B, ...}, "points": [{"cHq3": 0.5}, ...], "quadratic_flag_fraction": 0.3 (optional),
             "cross_term_convention": "..." (required when an off-diagonal key exists)}
Run: python3 eft_truncation.py input.json [--status LABEL]. Output JSON: "status" (run status, core/status.py) and
"status_label" (the inputs' artifact label, default unvalidated). Exit 0 ok (flags reported), 1 refused input,
2 unreadable input. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # sibling imports leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument  # noqa: E402

REQUIRED = ("basis", "normalization", "input_scheme", "lambda_tev", "operators", "x_sm", "linear")
RESCALE_TOL = 1e-12
CROSS_TERMS = ("an off-diagonal B_ij (i != j, key 'i*j' in either order, given once) multiplies C_i C_j / Lambda^4 "
               "once: no implicit factor 2 is applied")


def _finite(name: str, x) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"{name} must be a number, got {x!r}")
    v = float(x)
    if not math.isfinite(v):
        raise ValueError(f"{name} is not finite ({v})")
    return v


def _text(doc: dict, name: str) -> str:
    v = doc[name]
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty string (a convention travels with the prediction)")
    return v


def _terms(pt: dict, linear: dict, quad: dict, lam2: float) -> tuple[float, float]:
    lin = sum(pt.get(k, 0.0) * a for k, a in linear.items()) / lam2
    qd = sum(pt.get(i, 0.0) * pt.get(j, 0.0) * b for (i, j), b in quad.items()) / lam2 ** 2
    return lin, qd


def _close(x: float, y: float) -> bool:
    return abs(x - y) <= RESCALE_TOL * max(abs(x), abs(y)) or x == y


def evaluate(doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise ValueError("input must be a JSON object")
    missing = [k for k in REQUIRED if k not in doc]
    if missing:
        raise ValueError(f"missing convention or input fields: {missing}")
    basis, normalization, scheme = (_text(doc, k) for k in ("basis", "normalization", "input_scheme"))
    ops_list = doc["operators"]
    if (not isinstance(ops_list, list) or not ops_list
            or not all(isinstance(o, str) and o.strip() and "*" not in o for o in ops_list)):
        raise ValueError("operators must be a non-empty list of operator names (strings without '*')")
    if len(set(ops_list)) != len(ops_list):
        raise ValueError(f"operators lists a name twice: {ops_list}")
    ops = set(ops_list)
    lam = _finite("lambda_tev", doc["lambda_tev"])
    if lam <= 0:
        raise ValueError(f"lambda_tev must be > 0, got {lam}")
    lam2 = lam ** 2
    x_sm = _finite("x_sm", doc["x_sm"])
    if not isinstance(doc["linear"], dict):
        raise ValueError("linear must be an object {operator: A_i}")
    unknown = [k for k in doc["linear"] if k not in ops]
    if unknown:
        raise ValueError(f"coefficients not in the declared operator list: {sorted(set(unknown))}")
    linear = {k: _finite(f"linear[{k}]", a) for k, a in doc["linear"].items()}
    raw_quad = doc.get("quadratic", {})
    if not isinstance(raw_quad, dict):
        raise ValueError("quadratic must be an object {'i*j': B_ij}")
    quad: dict[tuple[str, str], float] = {}
    spelled: dict[tuple[str, str], str] = {}
    for key, b in raw_quad.items():
        parts = key.split("*")
        if len(parts) != 2:
            raise ValueError(f"quadratic key {key!r} does not split into exactly two operators 'i*j'")
        bad = [p for p in parts if p not in ops]
        if bad:
            raise ValueError(f"coefficients not in the declared operator list: {sorted(set(bad))} (key {key!r})")
        pair = (min(parts), max(parts))
        if pair in quad:
            raise ValueError(f"duplicate quadratic term: {spelled[pair]!r} and {key!r} are the same B_ij "
                             "(give each pair once)")
        quad[pair], spelled[pair] = _finite(f"quadratic[{key}]", b), key
    off_diagonal = sorted(spelled[p] for p in quad if p[0] != p[1])
    if off_diagonal:
        conv = doc.get("cross_term_convention")
        if not isinstance(conv, str) or not conv.strip():
            raise ValueError(f"off-diagonal quadratic terms {off_diagonal} need a cross_term_convention string "
                             "stating how B_ij enters (the script uses: " + CROSS_TERMS + ")")
    if "quadratic_flag_fraction" in doc:
        frac = _finite("quadratic_flag_fraction", doc["quadratic_flag_fraction"])
        if frac < 0:
            raise ValueError(f"quadratic_flag_fraction must be >= 0, got {frac}")
        frac_info = {"value": frac, "source": "input"}
    else:
        frac = 0.3
        frac_info = {"value": frac, "source": "default"}
    points = doc.get("points", [])
    if not isinstance(points, list):
        raise ValueError("points must be a list of objects {operator: C_i}")
    rows = []
    for n, raw in enumerate(points):
        if not isinstance(raw, dict):
            raise ValueError(f"point {n} must be an object {{operator: C_i}}")
        bad = [k for k in raw if k not in ops]
        if bad:
            raise ValueError(f"point uses undeclared operators {bad}")
        pt = {k: _finite(f"point {n} {k}", v) for k, v in raw.items()}
        lin, qd = _terms(pt, linear, quad, lam2)
        lin4, qd4 = _terms({k: 4 * v for k, v in pt.items()}, linear, quad, (2 * lam) ** 2)
        rescale = "pass" if _close(lin, lin4) and _close(qd, qd4) else "fail"
        rows.append({"point": raw, "linear_term": lin, "quadratic_term": qd, "x_linear": x_sm + lin,
                     "x_linear_plus_quadratic": x_sm + lin + qd,
                     "truncation_flag": bool(quad) and abs(qd) > frac * abs(lin), "rescaling_check": rescale})
    overall = "fail" if any(r["rescaling_check"] == "fail" for r in rows) else ("pass" if rows else "not-run")
    return {"basis": basis, "normalization": normalization, "input_scheme": scheme,
            "lambda_tev": doc["lambda_tev"], "quadratic_terms_supplied": bool(quad), "points": rows,
            "cross_terms": CROSS_TERMS, "cross_term_convention": doc.get("cross_term_convention"),
            "quadratic_flag_fraction": frac_info,
            "rescaling_check": overall,
            "rescaling_rule": f"each point re-evaluated at (4 C, 2 Lambda); linear and quadratic terms must agree "
                              f"within a relative {RESCALE_TOL:g}",
            "note": "linear and linear+quadratic are different truncations, not an uncertainty band; "
                    "dimension-8 terms at 1/Lambda^4 are not included in either"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("input")
    add_status_argument(ap)
    opts = ap.parse_args(argv)
    try:
        text = open(opts.input, encoding="utf-8").read()
    except OSError as exc:  # a missing or unreadable input: JSON status, exit 2
        print(json.dumps({"status": "rejected", "error": f"cannot read {opts.input}: {exc}"}))
        return 2
    try:
        out = evaluate(json.loads(text))
    except (ValueError, TypeError) as exc:
        print(json.dumps({"status": "failed", "status_label": opts.status, "reason": str(exc)}))
        return 1
    print(json.dumps(dict(out, status="ok", status_label=opts.status), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
