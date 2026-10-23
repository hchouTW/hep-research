#!/usr/bin/env python3
"""Gaussian-ansatz TMD structure functions at leading order, without evolution: the unpolarized SIDIS structure
function F_UU,T(x, z, P_hT), the Drell-Yan q_T shape, and the Sivers sign change between SIDIS and Drell-Yan (Th18).

Purpose: worked, checkable examples of TMD conventions. The Gaussian ansatz with flavour-independent widths is a
model (heuristic-argument), used for examples and analytic checks only; TMD evolution is not included. See
<plugin root>/skills/hep-theory/references/sidis-and-tmd.md.
Subcommands:
  sidis   --x --z, --partons FILE (f_1 number densities and D_1 fragmentation values per quark and antiquark flavour,
          {"f1": {flavour: f(x)}, "D1": {flavour: D(z)}} for d u s c b dbar ubar sbar cbar bbar), --kperp2 <k_perp^2>
          (GeV^2, distribution width), --pperp2 <p_perp^2> (GeV^2, fragmentation width, hadron momentum relative to the
          quark), --PhT values (GeV):
            F_UU,T(x, z, P_hT) = x sum_q e_q^2 f_1^q(x) D_1^q(z) exp(-P_hT^2/<P_T^2>) / (pi <P_T^2>),
            <P_T^2> = <p_perp^2> + z^2 <k_perp^2>
          (Anselmino et al., hep-ph/0501196v2, Eqs. 34-39, with the convolution of Bacchetta et al., hep-ph/0611265v2,
          Eqs. 4.1-4.2); its integral over d^2 P_hT is the collinear x sum_q e_q^2 f_1 D_1 (their Eq. 2.15).
  dy      --k1perp2 --k2perp2 (GeV^2, widths of the two TMD distributions), --qT values: the normalized q_T shape
          exp(-q_T^2/<q_T^2>)/(pi <q_T^2>), <q_T^2> = <k_1perp^2> + <k_2perp^2> (derived here: the convolution of two
          Gaussians; no fragmentation, so no z factor). Multiply by the LO collinear cross section (drell_yan_lo.py).
  sivers  --sidis-value V (a Sivers function value or moment in the SIDIS convention, with its notation): the
          Drell-Yan value is -V (time reversal with the Wilson lines of the two processes: Trento conventions,
          hep-ph/0410050v2, Eq. 14); the notation (f_1T^perp or Delta^N f, their Eqs. 2-4) is recorded, not converted.
Exit codes (core/status.py): 0 ok; 2 rejected (unreadable input, missing flavour, negative or non-finite widths or
values, z or x outside (0, 1], P_hT < 0). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

QUARKS = ("d", "u", "s", "c", "b")
FLAVOURS = QUARKS + tuple(q + "bar" for q in QUARKS)
E2 = {"d": 1 / 9, "u": 4 / 9, "s": 1 / 9, "c": 4 / 9, "b": 1 / 9}


class TMDError(ValueError):
    """Input the tool cannot use (rejected, exit 2)."""


def _pos(name, v, allow_zero=False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)) or v < 0 or \
            (v == 0 and not allow_zero):
        raise TMDError(f"{name} must be a finite number {'>=' if allow_zero else '>'} 0, got {v!r}")
    return float(v)


def collinear_sum(x: float, f1: dict, d1: dict) -> float:
    return x * sum(E2[f.replace("bar", "")] * f1[f] * d1[f] for f in FLAVOURS)


def sidis(x, z, f1, d1, kperp2, pperp2, phts) -> dict:
    width = pperp2 + z * z * kperp2
    coll = collinear_sum(x, f1, d1)
    rows = [{"PhT_GeV": p, "F_UU_T": coll * math.exp(-p * p / width) / (math.pi * width)} for p in phts]
    return {"collinear_F_UU_T": coll, "PT2_width_GeV2": width, "rows": rows,
            "normalization": "int d^2 P_hT F_UU,T = collinear_F_UU_T"}


def dy_shape(k1, k2, qts) -> dict:
    width = k1 + k2
    return {"qT2_width_GeV2": width,
            "rows": [{"qT_GeV": q, "shape_per_GeV2": math.exp(-q * q / width) / (math.pi * width)} for q in qts],
            "normalization": "int d^2 q_T shape = 1"}


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = input the tool cannot use."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=JsonArgumentParser)
    ps = sub.add_parser("sidis")
    ps.add_argument("--x", type=float, required=True)
    ps.add_argument("--z", type=float, required=True)
    ps.add_argument("--partons", required=True)
    ps.add_argument("--kperp2", type=float, required=True)
    ps.add_argument("--pperp2", type=float, required=True)
    ps.add_argument("--PhT", type=float, nargs="+", required=True)
    pd = sub.add_parser("dy")
    pd.add_argument("--k1perp2", type=float, required=True)
    pd.add_argument("--k2perp2", type=float, required=True)
    pd.add_argument("--qT", type=float, nargs="+", required=True)
    pv = sub.add_parser("sivers")
    pv.add_argument("--sidis-value", type=float, required=True)
    pv.add_argument("--notation", choices=("f1T_perp", "DeltaN_f"), required=True)
    for p in (ps, pd, pv):
        add_status_argument(p)
    a = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(a).items() if k != "status"}
    base = {"status_label": a.status, "inputs": inputs}
    conventions = {"model": "Gaussian ansatz, flavour-independent widths, no evolution (heuristic-argument)"}
    try:
        if a.cmd == "sidis":
            x, z = _pos("--x", a.x), _pos("--z", a.z)
            if x > 1 or z > 1:
                raise TMDError("x and z must be in (0, 1]")
            try:
                doc = json.loads(Path(a.partons).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise TMDError(f"cannot read --partons {a.partons}: {exc}") from exc
            if not isinstance(doc, dict) or not all(isinstance(doc.get(k), dict) for k in ("f1", "D1")):
                raise TMDError('--partons must be {"f1": {flavour: f(x)}, "D1": {flavour: D(z)}}')
            f1 = {f: _pos(f"f1.{f}", doc["f1"].get(f), True) for f in FLAVOURS}
            d1 = {f: _pos(f"D1.{f}", doc["D1"].get(f), True) for f in FLAVOURS}
            phts = [_pos("--PhT", p, True) for p in a.PhT]
            out = sidis(x, z, f1, d1, _pos("--kperp2", a.kperp2), _pos("--pperp2", a.pperp2), phts)
            conventions["source"] = ("Anselmino et al. hep-ph/0501196v2 Eqs. 34-39; Bacchetta et al. hep-ph/0611265v2 "
                                     "Eqs. 2.15, 4.1-4.2 (read 2026-10-23)")
        elif a.cmd == "dy":
            qts = [_pos("--qT", q, True) for q in a.qT]
            out = dy_shape(_pos("--k1perp2", a.k1perp2), _pos("--k2perp2", a.k2perp2), qts)
            conventions["source"] = "convolution of two normalized Gaussians (derived here)"
        else:
            v = a.sidis_value
            if not math.isfinite(v):
                raise TMDError("--sidis-value must be finite")
            out = {"sidis_value": v, "drell_yan_value": -v, "notation": a.notation,
                   "rule": "f_1T^perp,DY = -f_1T^perp,SIDIS (Trento conventions, hep-ph/0410050v2 Eq. 14)"}
            conventions["source"] = "Trento conventions hep-ph/0410050v2 Eqs. 2-4, 14 (read 2026-10-23)"
    except TMDError as exc:
        print(json.dumps({"status": "rejected", **base, "reason": str(exc)}, indent=1))
        return exit_code("rejected")
    status = "heuristic-argument" if a.cmd != "sivers" else "analytic-derivation (time reversal; cited)"
    print(json.dumps({"status": "ok", **base, "conventions": conventions, "derivation_status": status,
                      "outputs": out}, indent=1))
    return exit_code("ok")


if __name__ == "__main__":
    sys.exit(main())
