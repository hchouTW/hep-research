#!/usr/bin/env python3
"""Projection of an uncertainty budget (and an optional Asimov significance) to k times the present exposure (S2).

Method: with the exposure multiplied by k,
  - the statistical uncertainty falls as sigma_stat / sqrt(k);
  - each systematic follows its scaling class (the M5 classes of the measurement spec, field `scaling`; see
    <plugin root>/skills/hep-measurement/references/systematics.md, "Scaling class"), with N_ctrl the size of the
    control sample that sets it, which grows by k only when the entry says `control_grows_with_exposure: true`:
      statistical-like  sigma(k) = sigma / sqrt(f)
      floor             sigma(k) = sigma
      mixed             sigma(k)^2 = a^2 + b^2 / f        (a the floor, b the statistical part at the present N_ctrl)
    with f = k when the control sample grows with the exposure, f = 1 otherwise;
  - the total is the quadrature sum (the sources are taken as independent; the output says so);
  - with "counting" {s, b} the Asimov discovery significance at k, s and b scaled by k: Z_A = sqrt(2 ((s+b)
    ln(1 + s/b) - s)), or, with a background uncertainty sigma_b = sigma_b_rel x b (its own scaling class), the form
    for a Poisson auxiliary measurement of the background; both as stated, with their sources and validity, in
    <plugin root>/skills/hep-statistics/references/inference-recipes.md ("Expected sensitivity");
  - with "reach" {target: "total" | "z", value, k_max} the smallest k in [1, k_max] at which the total falls to the
    value or Z_A rises to it (bisection on a monotonic function of k), or null when it is not reached (for example
    below the floor of the systematics).
Assumptions and validity: every scaling class is declared, never guessed; no correlations between sources; Gaussian
uncertainties; the projection says nothing about new systematics a larger data set exposes.
Labels: every output carries the label `projection` (a core artifact status); a statistical result labeled
`projection` fails the publication gate (contracts/validate.py publication_gate, gate.projection).

Input JSON: {"quantity": TEXT, "stat": SIGMA,
             "systematics": [{"name": TEXT, "scaling": "statistical-like" | "floor" | "mixed",
                              "sigma": SIGMA (statistical-like, floor) | "a": A, "b": B (mixed),
                              "control_grows_with_exposure": true | false}, ...],
             "counting": {"s": S, "b": B, "sigma_b_rel": R (optional), "sigma_b_scaling": CLASS (with sigma_b_rel),
                          "sigma_b_control_grows_with_exposure": true | false (with sigma_b_rel, unless floor)} (optional),
             "reach": {"target": "total" | "z", "value": X, "k_max": K} (optional)}
Output JSON: "status" (ok, rejected), "status_label" (--status, default unvalidated), "label" ("projection"),
"inputs", "defaults_used", "assumptions", "projections" [{k, stat, systematics [{name, scaling, sigma}], total,
asimov_z?}], "reach" (when asked), "note".
Exit codes: 0 ok; 2 bad input (a missing or unknown scaling class, a negative or non-finite size, k <= 0).
Run: python3 <plugin root>/skills/hep-statistics/scripts/project_uncertainty.py budget.json --k 2,4,10
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "projection"
CLASSES = ("statistical-like", "floor", "mixed")
NOTE = ("a projection, not a result: labeled 'projection', it cannot pass the publication gate; it says nothing about "
        "systematics a larger data set may expose")


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _size(x, name: str, positive: bool = False) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0 or (positive and x == 0):
        raise InputError(f"{name} must be a finite number {'> 0' if positive else '>= 0'}")
    return float(x)


def _grows(d: dict, name: str, key: str = "control_grows_with_exposure") -> bool:
    v = d.get(key)
    if not isinstance(v, bool):
        raise InputError(f"{name}: {key} must be true or false (no default)")
    return v


def parse(doc) -> dict:
    if not isinstance(doc, dict):
        raise InputError("the input must be a JSON object")
    stat = _size(doc.get("stat"), "stat")
    systs = []
    for i, s in enumerate(doc.get("systematics", [])):
        if not isinstance(s, dict) or not isinstance(s.get("name"), str) or not s["name"].strip():
            raise InputError(f"systematic {i} needs a name")
        cls = s.get("scaling")
        if cls not in CLASSES:
            raise InputError(f"systematic {s['name']}: scaling must be one of {list(CLASSES)} (M5), got {cls!r}")
        entry = {"name": s["name"], "scaling": cls, "grows": _grows(s, s["name"])}
        if cls == "mixed":
            entry["a"], entry["b"] = _size(s.get("a"), f"{s['name']} a"), _size(s.get("b"), f"{s['name']} b")
        else:
            entry["sigma"] = _size(s.get("sigma"), f"{s['name']} sigma")
        systs.append(entry)
    out = {"quantity": doc.get("quantity"), "stat": stat, "systematics": systs}
    c = doc.get("counting")
    if c is not None:
        if not isinstance(c, dict):
            raise InputError("counting must be an object {s, b}")
        cnt = {"s": _size(c.get("s"), "counting s", True), "b": _size(c.get("b"), "counting b", True)}
        if "sigma_b_rel" in c:
            cnt["sigma_b_rel"] = _size(c["sigma_b_rel"], "counting sigma_b_rel")
            cls = c.get("sigma_b_scaling")
            if cls not in ("statistical-like", "floor"):
                raise InputError("counting sigma_b_scaling must be statistical-like or floor")
            cnt["sigma_b_scaling"] = cls
            cnt["grows"] = cls == "statistical-like" and _grows(c, "counting", "sigma_b_control_grows_with_exposure")
        out["counting"] = cnt
    r = doc.get("reach")
    if r is not None:
        if not isinstance(r, dict) or r.get("target") not in ("total", "z"):
            raise InputError("reach.target must be 'total' or 'z'")
        if r["target"] == "z" and c is None:
            raise InputError("a significance reach needs counting {s, b}")
        k_max = _size(r.get("k_max"), "reach k_max", True)
        if k_max < 1:
            raise InputError("reach k_max must be >= 1")
        out["reach"] = {"target": r["target"], "value": _size(r.get("value"), "reach value", True), "k_max": k_max}
    return out


def systematic_at(s: dict, k: float) -> float:
    f = k if s["grows"] else 1.0
    if s["scaling"] == "statistical-like":
        return s["sigma"] / math.sqrt(f)
    if s["scaling"] == "floor":
        return s["sigma"]
    return math.sqrt(s["a"] ** 2 + s["b"] ** 2 / f)


def asimov_z(s: float, b: float, sigma_b: float = 0.0) -> float:
    """Asimov discovery significance, without or with a background uncertainty (inference-recipes.md)."""
    if sigma_b <= 0.0:
        return math.sqrt(max(2.0 * ((s + b) * math.log1p(s / b) - s), 0.0))
    v = sigma_b * sigma_b
    t1 = (s + b) * math.log((s + b) * (b + v) / (b * b + (s + b) * v))
    t2 = (b * b / v) * math.log1p(v * s / (b * (b + v)))
    return math.sqrt(max(2.0 * (t1 - t2), 0.0))


def project(model: dict, k: float) -> dict:
    stat = model["stat"] / math.sqrt(k)
    systs = [{"name": s["name"], "scaling": s["scaling"], "sigma": systematic_at(s, k)} for s in model["systematics"]]
    total = math.sqrt(stat * stat + math.fsum(s["sigma"] ** 2 for s in systs))
    row: dict = {"k": k, "stat": stat, "systematics": systs, "total": total}
    c = model.get("counting")
    if c:
        s, b = c["s"] * k, c["b"] * k
        sb = 0.0
        if "sigma_b_rel" in c:
            rel = c["sigma_b_rel"] / (math.sqrt(k) if c["grows"] else 1.0)
            sb = rel * b
        row["asimov_z"] = asimov_z(s, b, sb)
    return row


def reach(model: dict) -> dict:
    r = model["reach"]
    if r["target"] == "total":
        def met(k):
            return project(model, k)["total"] <= r["value"]
    else:
        def met(k):
            return project(model, k)["asimov_z"] >= r["value"]
    lo, hi = 1.0, r["k_max"]
    out = {"target": r["target"], "value": r["value"], "k_max": hi}
    if met(lo):
        k = lo
    elif not met(hi):
        floor = math.sqrt(math.fsum(systematic_at(s, float("inf")) ** 2 for s in model["systematics"]))
        return {**out, "k": None, "note": f"not reached by k_max; the total cannot fall below the systematic floor "
                                          f"{floor:.6g} at any k"}
    else:
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            lo, hi = (lo, mid) if met(mid) else (mid, hi)
            if hi / lo - 1.0 < 1e-12:
                break
        k = hi
    row = project(model, k)
    return {**out, "k": k, "total_at_k": row["total"], **({"asimov_z_at_k": row["asimov_z"]} if "asimov_z" in row else {})}


def parse_k(text: str) -> list[float]:
    try:
        ks = [float(x) for x in text.split(",") if x.strip()]
    except ValueError as exc:
        raise InputError(f"--k must be a comma-separated list of numbers, got {text!r}") from exc
    if not ks or any(not math.isfinite(k) or k <= 0 for k in ks):
        raise InputError("every exposure factor k must be a finite number > 0")
    return ks


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="JSON uncertainty budget (format above)")
    ap.add_argument("--k", required=True, help="comma-separated exposure factors, e.g. 2,4,10")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        ks = parse_k(args.k)
        model = parse(json.loads(Path(args.input).read_text(encoding="utf-8")))
        body = {"quantity": model["quantity"], "projections": [project(model, k) for k in ks],
                "assumptions": {"combination": "quadrature sum of independent sources",
                                "statistical": "sigma_stat / sqrt(k)",
                                "classes": "M5 scaling classes as declared per source"},
                "note": NOTE}
        if "reach" in model:
            body["reach"] = reach(model)
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "label": LABEL, "inputs": inputs,
                      "defaults_used": defaults, **body}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
