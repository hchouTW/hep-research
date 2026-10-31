#!/usr/bin/env python3
"""Relativistic kinematics: two-body decays, boosts, invariant masses, Mandelstam variables, thresholds, Dalitz
boundaries, rapidity and width/lifetime/c tau (Th7).

Purpose: the standard relations of the PDG Review's kinematics section as checked arithmetic, over
<plugin root>/core/kinematics/fourvector.py. Masses are given as numbers in GeV or as particle names of the bundled
PDG 2026 subset (core/constants; see physical_data.py list), and the output records each named mass with its source.
Assumptions and validity: c = 1, metric (+, -, -, -), energies and momenta in GeV; a four-vector is "E,px,py,pz";
boost --beta gives the vector in a frame moving with that velocity (|beta| < 1); thresholds are for a target at rest.
Subcommands:
  two-body M m1 m2                         p* = sqrt(lambda(M^2, m1^2, m2^2)) / 2M, E1, E2
  boost --vector V (--beta bx,by,bz | --to-rest-of W)
  invariant-mass --vector V [--vector V ...]
  mandelstam --p1 V --p2 V --p3 V --p4 V   s, t, u and the check s + t + u = sum of m^2
  threshold --beam m --target m --final m [m ...]
  dalitz M m1 m2 m3 [--m12sq X]            m12^2 range, and the m23^2 range at X
  rapidity --vector V                      rapidity and pseudorapidity
  lifetime (--width-gev G | --lifetime-s T | --ctau-m L | --particle NAME)
Output JSON: "status" (run status, core/status.py), "status_label" (--status, default unvalidated), "inputs",
"defaults_used", "masses" (named masses with source and edition) and "result" (labelled [General method]).
Exit codes: 0 ok; 2 bad input (closed channel, |beta| >= 1, unknown name, malformed vector).
Run: python3 <plugin root>/skills/hep-theory/scripts/kinematics.py two-body K0 pi+ pi+
     python3 <plugin root>/skills/hep-theory/scripts/kinematics.py threshold --beam proton --target proton --final proton proton proton proton
Standard library only.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core import constants  # noqa: E402
from core.kinematics import fourvector as fv  # noqa: E402
from core.kinematics.relativistic import KinematicsError  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402


class JsonArgumentParser(argparse.ArgumentParser):
    """argparse that also prints the reason as JSON on stdout: exit 2 = invalid input. Subparsers inherit it."""

    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


class Masses:
    """Resolve mass tokens: a number in GeV, or a particle name of the bundled PDG subset."""

    def __init__(self):
        self.used: dict[str, dict] = {}

    def __call__(self, token: str) -> float:
        try:
            return float(token)
        except ValueError:
            pass
        try:
            q = constants.particle(token, "mass", unit="GeV")
        except constants.ConstantsError as exc:
            raise KinematicsError(str(exc)) from exc
        self.used[token] = q.to_dict()
        return q.value


def vector(text: str) -> tuple[float, ...]:
    try:
        parts = tuple(float(x) for x in text.split(","))
    except ValueError as exc:
        raise KinematicsError(f"a four-vector is 'E,px,py,pz', got {text!r}") from exc
    if len(parts) != 4:
        raise KinematicsError(f"a four-vector has four components, got {text!r}")
    return parts


def three(text: str) -> tuple[float, ...]:
    try:
        parts = tuple(float(x) for x in text.split(","))
    except ValueError as exc:
        raise KinematicsError(f"beta is 'bx,by,bz', got {text!r}") from exc
    if len(parts) != 3:
        raise KinematicsError(f"beta has three components, got {text!r}")
    return parts


def evaluate(args, mass: Masses) -> dict:
    cmd = args.command
    if cmd == "two-body":
        return fv.two_body_decay(mass(args.M), mass(args.m1), mass(args.m2))
    if cmd == "boost":
        v = vector(args.vector)
        beta = three(args.beta) if args.beta else fv.beta_of(vector(args.to_rest_of))
        return {"vector": list(fv.boost(v, beta)), "beta": list(beta), "label": fv.LABEL}
    if cmd == "invariant-mass":
        return {"mass": fv.invariant_mass(*(vector(v) for v in args.vector)), "label": fv.LABEL}
    if cmd == "mandelstam":
        ps = [vector(x) for x in (args.p1, args.p2, args.p3, args.p4)]
        s, t, u = fv.mandelstam(*ps)
        msum = sum(fv.mass_squared(p) for p in ps)
        return {"s": s, "t": t, "u": u, "sum_of_masses_squared": msum, "s_plus_t_plus_u": s + t + u,
                "label": fv.LABEL}
    if cmd == "threshold":
        return fv.fixed_target_threshold(mass(args.beam), mass(args.target), [mass(m) for m in args.final])
    if cmd == "dalitz":
        M, m1, m2, m3 = (mass(x) for x in (args.M, args.m1, args.m2, args.m3))
        out: dict = {"m12sq_range": list(fv.dalitz_m12_range(M, m1, m2, m3)), "label": fv.LABEL,
                     "variables": "m12^2 = (p1 + p2)^2, m23^2 = (p2 + p3)^2"}
        if args.m12sq is not None:
            out["m12sq"] = args.m12sq
            out["m23sq_range"] = list(fv.dalitz_m23_range(M, m1, m2, m3, args.m12sq))
        return out
    if cmd == "rapidity":
        v = vector(args.vector)
        return {"rapidity": fv.rapidity(v), "pseudorapidity": fv.pseudorapidity(v), "label": fv.LABEL}
    # lifetime
    if args.particle:
        rec = constants.particle_record(args.particle)
        if "lifetime" in rec:
            q = constants.particle(args.particle, "lifetime", unit="s")
            args.input_source = q.to_dict()
            return fv.lifetime_relations(lifetime_s=q.value)
        q = constants.particle(args.particle, "width", unit="GeV")
        args.input_source = q.to_dict()
        return fv.lifetime_relations(width_gev=q.value)
    return fv.lifetime_relations(width_gev=args.width_gev, lifetime_s=args.lifetime_s, ctau_m=args.ctau_m)


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("two-body", help="two-body decay momentum and energies")
    for n in ("M", "m1", "m2"):
        p.add_argument(n, help="mass in GeV or a particle name")
    p = sub.add_parser("boost", help="Lorentz boost of a four-vector")
    p.add_argument("--vector", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--beta")
    g.add_argument("--to-rest-of", dest="to_rest_of")
    p = sub.add_parser("invariant-mass", help="invariant mass of the sum of four-vectors")
    p.add_argument("--vector", action="append", required=True)
    p = sub.add_parser("mandelstam", help="s, t, u of 1 + 2 -> 3 + 4")
    for n in ("--p1", "--p2", "--p3", "--p4"):
        p.add_argument(n, required=True)
    p = sub.add_parser("threshold", help="fixed-target reaction threshold")
    p.add_argument("--beam", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--final", nargs="+", required=True)
    p = sub.add_parser("dalitz", help="Dalitz-plot boundaries of M -> 1 2 3")
    for n in ("M", "m1", "m2", "m3"):
        p.add_argument(n)
    p.add_argument("--m12sq", type=float)
    p = sub.add_parser("rapidity", help="rapidity and pseudorapidity")
    p.add_argument("--vector", required=True)
    p = sub.add_parser("lifetime", help="width, mean lifetime and c tau")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--width-gev", type=float, dest="width_gev")
    g.add_argument("--lifetime-s", type=float, dest="lifetime_s")
    g.add_argument("--ctau-m", type=float, dest="ctau_m")
    g.add_argument("--particle")
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    given = {tok.split("=")[0] for tok in (sys.argv[1:] if argv is None else argv) if tok.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    mass, status, out = Masses(), "ok", {}
    try:
        out = {"result": evaluate(args, mass)}
        if getattr(args, "input_source", None):
            out["input_source"] = args.input_source
    except (KinematicsError, constants.ConstantsError) as exc:
        status, out = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      "masses": mass.used, **out}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
