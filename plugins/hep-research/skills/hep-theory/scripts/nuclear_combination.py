#!/usr/bin/env python3
"""Nuclear targets: bound-nucleon combination, per-nucleon and per-nucleus conversions, and member-by-member nuclear
ratios with the set's own uncertainty rule (Th16).

Purpose: the bookkeeping that most often goes wrong with nuclear PDFs. See
<plugin root>/skills/hep-theory/references/nuclear-parton-effects.md.
Subcommands:
  combine  --Z --A --partons FILE (x f of the bound proton, flavours d u s c b dbar ubar sbar cbar bbar, optional g)
           --normalization per-nucleon|per-nucleus: f^A = (Z/A) f^{p/A} + ((A - Z)/A) f^{n/A}, with the bound neutron
           from isospin symmetry (u^{n/A} = d^{p/A}, d^{n/A} = u^{p/A}, likewise for antiquarks; s c b g unchanged);
           per nucleus multiplies by A. The input must be a bound-proton grid ("grid_kind": "bound-proton"); an
           average-nucleon grid (already combined, as some sets also ship) is refused. Klasen and Paukkunen,
           arXiv:2311.00450, Eqs. 11-12; PDG 2026 "Structure Functions", R_u^Pb in the text above Fig. 18.5 (read
           2026-10-23).
  ratio    --input FILE = {"numerator": {"set", "baseline", "error_type", "conf_level_percent", "members"},
           "denominator": {"set", "kind": "nuclear" | "proton", "error_type", "conf_level_percent", "members"},
           "paired_members": bool, replica sets also "prescription": "median-68" | "mean-std"}: R_k = numerator_k /
           denominator_k member by member, then the set's combination rule (`pdf_uncertainty.py`, same skill); the
           "headline" follows the prescription (nNNPDF3.0 Sec. 7.2 recommends the median and the central 68% interval).
           A replica set cannot use an external proton denominator (refused). The two must come from the same set (kind nuclear), or the
           denominator must be the numerator's documented proton baseline with paired members (kind proton,
           "paired_members": true). Dividing the two error bands is not offered: it loses the correlation.
  convert  --quantity cross-section|structure-function --value V --A A --from per-nucleon|per-nucleus, or
           --quantity x --value x --M-nucleon --M-nucleus --from per-nucleon|per-nucleus: per-nucleus quantities are
           A times per-nucleon ones; x_A = Q^2 / (2 M_A nu) = x_N M_N / M_A (derived here from x = Q^2 / (2 M nu), PDG
           Eq. 18.1 definitions), so per-nucleon x reaches about A when M_A ~ A M_N.
Exit codes (core/status.py): 0 ok; 1 refused (baseline mismatch, different sets, mixed error types or confidence
levels between numerator and denominator, unpaired members); 2 rejected (unreadable input, Z > A, A < 1, missing
flavour, non-finite values, member lists of different lengths, a set the combination rule refuses). Standard library
only. Derivation status: analytic-derivation (isospin combination given isospin symmetry; ratio bookkeeping).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling scripts of this skill
from core.status import add_status_argument, exit_code  # noqa: E402
from pdf_uncertainty import combine as combine_members  # noqa: E402

QUARKS = ("d", "u", "s", "c", "b")
FLAVOURS = QUARKS + tuple(q + "bar" for q in QUARKS)


class NucError(ValueError):
    def __init__(self, msg: str, status: str = "rejected"):
        super().__init__(msg)
        self.status = status


def _num(name, v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise NucError(f"{name} must be a finite number, got {v!r}")
    return float(v)


def _za(z, a) -> tuple[float, float]:
    z, a = _num("--Z", z), _num("--A", a)
    if a < 1 or z < 0 or z > a or z != int(z) or a != int(a):
        raise NucError("need integers 0 <= Z <= A and A >= 1")
    return z, a


def _read(path: str) -> dict:
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NucError(f"cannot read {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise NucError(f"{path} must hold a JSON object")
    return doc


def isospin_neutron(p: dict) -> dict:
    return dict(p, u=p["d"], d=p["u"], ubar=p["dbar"], dbar=p["ubar"])


def combine(z: float, a: float, proton: dict, normalization: str) -> dict:
    n = isospin_neutron(proton)
    per_nucleon = {f: (z / a) * proton[f] + ((a - z) / a) * n[f] for f in proton}
    if normalization == "per-nucleus":
        return {f: a * v for f, v in per_nucleon.items()}
    return per_nucleon


def ratio(doc: dict) -> dict:
    num, den = doc.get("numerator"), doc.get("denominator")
    if not isinstance(num, dict) or not isinstance(den, dict):
        raise NucError("input needs 'numerator' and 'denominator' objects")
    for side, d in (("numerator", num), ("denominator", den)):
        for key in ("set", "error_type", "conf_level_percent", "members"):
            if key not in d:
                raise NucError(f"{side} lacks '{key}'")
    if "baseline" not in num:
        raise NucError("numerator lacks 'baseline' (the proton set its nuclear modifications refer to)")
    kind = den.get("kind")
    if kind not in ("nuclear", "proton"):
        raise NucError("denominator 'kind' must be 'nuclear' (same nuclear set) or 'proton' (its baseline)")
    if num["error_type"] != den["error_type"]:
        raise NucError(f"mixed error types: {num['error_type']} / {den['error_type']}", status="refused")
    if _num("numerator conf_level_percent", num["conf_level_percent"]) != \
            _num("denominator conf_level_percent", den["conf_level_percent"]):
        raise NucError("numerator and denominator are quoted at different confidence levels", status="refused")
    if kind == "nuclear" and num["set"] != den["set"]:
        raise NucError("member-by-member ratios need one nuclear set for numerator and denominator "
                       f"({num['set']} / {den['set']})", status="refused")
    if kind == "proton" and num["error_type"].startswith("replicas"):
        raise NucError("a replica set cannot be paired member by member with an external proton set (each nuclear "
                       "replica used a random proton replica); use the set's own A = 1 grid as a nuclear denominator",
                       status="refused")
    prescription = None
    if num["error_type"].startswith("replicas"):
        prescription = num.get("prescription")
        if prescription not in ("median-68", "mean-std") or den.get("prescription", prescription) != prescription:
            raise NucError("a replica set needs \"prescription\": \"median-68\" or \"mean-std\" (the set's own rule), "
                           "the same for numerator and denominator")
    if kind == "proton":
        if num["baseline"] != den["set"]:
            raise NucError(f"baseline mismatch: {num['set']} refers to {num['baseline']}, the denominator is "
                           f"{den['set']}", status="refused")
        if doc.get("paired_members") is not True:
            raise NucError("a proton denominator needs \"paired_members\": true (its members match the nuclear set's "
                           "member by member, as the set documents)", status="refused")
    xa = [_num("numerator member", v) for v in num["members"]] if isinstance(num["members"], list) else None
    xb = [_num("denominator member", v) for v in den["members"]] if isinstance(den["members"], list) else None
    if xa is None or xb is None or len(xa) != len(xb):
        raise NucError("numerator and denominator need member lists of the same length")
    if any(v <= 0 for v in xb):
        raise NucError("a denominator member is zero or negative")
    members = [p / q for p, q in zip(xa, xb)]
    try:
        comb = combine_members(num["error_type"], members, float(num["conf_level_percent"]),
                               num_members=doc.get("num_members"))
    except ValueError as exc:
        raise NucError(f"combination rule refused the set: {exc}") from exc
    if prescription == "median-68":
        reps = sorted(members[1:])
        n = len(reps)
        median = reps[n // 2] if n % 2 else 0.5 * (reps[n // 2 - 1] + reps[n // 2])
        headline = {"rule": "median-68", "central": median, "interval_68": comb.get("replica_68_interval")}
    elif prescription == "mean-std":
        headline = {"rule": "mean-std", "central": comb["central"], "delta": comb["delta_up"]}
    else:
        headline = {"rule": num["error_type"], "central": comb["central"], "delta_up": comb["delta_up"],
                    "delta_down": comb["delta_down"]}
    return {"ratio_members": members, "headline": headline, "combination": comb,
            "method": "member by member, then the set's own rule (pdf_uncertainty.combine)"}


def convert(a) -> dict:
    v = _num("--value", a.value)
    if a.quantity == "x":
        mn, ma = _num("--M-nucleon", a.M_nucleon), _num("--M-nucleus", a.M_nucleus)
        if mn <= 0 or ma < mn:
            raise NucError("need 0 < M_nucleon <= M_nucleus")
        if v <= 0 or (a.from_ == "per-nucleus" and v > 1) or (a.from_ == "per-nucleon" and v > ma / mn):
            raise NucError("x must be in (0, 1] per nucleus, (0, M_A/M_N] per nucleon")
        out = v * mn / ma if a.from_ == "per-nucleon" else v * ma / mn
        return {"x_per_nucleus" if a.from_ == "per-nucleon" else "x_per_nucleon": out,
                "relation": "x_A = x_N M_N / M_A"}
    _, mass_a = _za(0, a.A)
    if v < 0:
        raise NucError("a cross section or structure function value must be >= 0 here")
    out = v * mass_a if a.from_ == "per-nucleon" else v / mass_a
    return {"per_nucleus" if a.from_ == "per-nucleon" else "per_nucleon": out, "relation": "per nucleus = A x per nucleon"}


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    pc = sub.add_parser("combine")
    pc.add_argument("--Z", type=float, required=True)
    pc.add_argument("--A", type=float, required=True)
    pc.add_argument("--partons", required=True)
    pc.add_argument("--normalization", choices=("per-nucleon", "per-nucleus"), required=True)
    pr = sub.add_parser("ratio")
    pr.add_argument("--input", required=True)
    pv = sub.add_parser("convert")
    pv.add_argument("--quantity", choices=("cross-section", "structure-function", "x"), required=True)
    pv.add_argument("--value", type=float, required=True)
    pv.add_argument("--from", dest="from_", choices=("per-nucleon", "per-nucleus"), required=True)
    pv.add_argument("--A", type=float)
    pv.add_argument("--M-nucleon", type=float)
    pv.add_argument("--M-nucleus", type=float)
    for p in (pc, pr, pv):
        add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    conventions = {}
    try:
        if a.cmd == "combine":
            z, mass_a = _za(a.Z, a.A)
            doc = _read(a.partons)
            kind = doc.get("grid_kind")
            if kind == "average-nucleon":
                raise NucError("this grid is already the average nucleon f^A = (Z/A) f^p/A + ((A-Z)/A) f^n/A; combining "
                               "it again applies isospin twice", status="refused")
            if kind != "bound-proton":
                raise NucError('--partons needs "grid_kind": "bound-proton" (or "average-nucleon", which is refused)')
            vals = doc.get("values") if doc.get("representation") == "xf" else None
            if not isinstance(vals, dict) or any(f not in vals for f in FLAVOURS):
                raise NucError(f'--partons must be {{"representation": "xf", "values": {{...}}}} with {list(FLAVOURS)}')
            proton = {f: _num(f, vals[f]) for f in vals if f in FLAVOURS + ("g",)}
            out = {"values": combine(z, mass_a, proton, a.normalization)}
            conventions = {"target_normalization": a.normalization, "x": "per-nucleon x (unchanged)", "isospin": "bound neutron from bound proton by "
                           "u <-> d, ubar <-> dbar; s, c, b, g unchanged",
                           "source": "Klasen and Paukkunen 2024, Eqs. 11-12; PDG 2026 Structure Functions, R_u^Pb above Fig. 18.5"}
        elif a.cmd == "ratio":
            out = ratio(_read(a.input))
        else:
            if a.quantity != "x" and a.A is None:
                raise NucError("--A is required for this quantity")
            if a.quantity == "x" and (a.M_nucleon is None or a.M_nucleus is None):
                raise NucError("--quantity x needs --M-nucleon and --M-nucleus (the caller's mass convention)")
            out = convert(a)
    except NucError as exc:
        print(json.dumps({"status": exc.status, **base, "reason": str(exc)}, indent=1))
        return exit_code(exc.status)
    print(json.dumps({"status": "ok", **base, "conventions": conventions, "derivation_status": "analytic-derivation",
                      "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
