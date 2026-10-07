#!/usr/bin/env python3
"""Deterministic charged-particle kinematics with explicit charge, mass, and variable conventions.

Purpose: stop the classic errors (rigidity used as momentum for |Z| != 1, energy,
kinetic energy, kinetic energy per nucleon and rigidity mixed up, an unstated A or
mass) by refusing to compute unless every assumption is supplied.

What it does: converts between five variables (rigidity, momentum, total_energy,
kinetic_energy, kinetic_energy_per_nucleon), converts bin edges with the exact
bin-average flux factor and the point Jacobian, and propagates first-order
uncertainties (including mass from rigidity and velocity with an explicit
correlation). Every result is [General method] arithmetic under the stated
assumptions; it is never measured detector performance.

Conventions: R is |R| in GV; p in GeV/c; E, T (kinetic) and mass in GeV; T/A in
GeV/n. p = |Z| * |R| numerically (c = 1). Charge sign is a separate observable and
does not enter these formulas. No defaults for Z, A or mass: the caller supplies them.
Every requested value must lie in the physical domain of its variable.

Usage (from the plugin root):
  python3 core/kinematics/relativistic.py convert --from rigidity --to kinetic_energy_per_nucleon \\
      --value 20 --Z 2 --A 4 --mass 3.7274
  python3 core/kinematics/relativistic.py bins --from rigidity --to kinetic_energy_per_nucleon \\
      --edges 1 2 4 8 --Z 2 --A 4 --mass 3.7274
  python3 core/kinematics/relativistic.py mass-resolution --R 10 --beta 0.9 --Z 1 \\
      --sigma-R-rel 0.05 --sigma-beta-rel 0.001 --rho 0
Exit codes: 0 ok; 2 rejected input (message in JSON "error"). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass

VARIABLES = ("rigidity", "momentum", "total_energy", "kinetic_energy", "kinetic_energy_per_nucleon")
UNITS = {
    "rigidity": "GV",
    "momentum": "GeV/c",
    "total_energy": "GeV",
    "kinetic_energy": "GeV",
    "kinetic_energy_per_nucleon": "GeV/n",
}
LABEL = "[General method]"
NOTE = "computed kinematics under the stated assumptions; not measured detector performance"


class KinematicsError(ValueError):
    """Raised when an input is missing, unphysical, or mixes conventions."""


@dataclass(frozen=True)
class Species:
    """Assumptions that a conversion depends on. Z is |Z|; A and mass may be None."""
    Z: int | None
    A: int | None = None
    mass: float | None = None  # rest energy, GeV

    def need_Z(self) -> int:
        z = self.Z
        if z is None or isinstance(z, bool) or float(z) != int(z) or int(z) < 1:
            raise KinematicsError("|Z| must be supplied as a positive integer (rigidity is not momentum for |Z| != 1)")
        return int(z)

    def need_mass(self) -> float:
        if self.mass is None:
            raise KinematicsError("mass (rest energy, GeV) must be supplied for this conversion")
        return _positive(self.mass, "mass")

    def need_A(self) -> int:
        a = self.A
        if a is None or isinstance(a, bool) or float(a) != int(a) or int(a) < 1:
            raise KinematicsError("A must be supplied as a positive integer for kinetic energy per nucleon")
        return int(a)


def _finite(x: float, name: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise KinematicsError(f"{name} must be a finite number")
    return float(x)


def _positive(x: float, name: str) -> float:
    x = _finite(x, name)
    if x <= 0:
        raise KinematicsError(f"{name} must be positive, got {x}")
    return x


# --- single-step relations -------------------------------------------------------
def rigidity_to_momentum(R: float, Z: int) -> float:
    """p [GeV/c] = |Z| * |R| [GV]. Sign of R is ignored (magnitude convention)."""
    return Species(Z).need_Z() * abs(_positive(abs(_finite(R, "R")), "|R|"))


def momentum_to_rigidity(p: float, Z: int) -> float:
    """|R| [GV] = p / |Z|."""
    return _positive(p, "p") / Species(Z).need_Z()


def total_energy(p: float, mass: float) -> float:
    return math.hypot(_positive(p, "p"), _positive(mass, "mass"))


def momentum_from_total_energy(E: float, mass: float) -> float:
    E, m = _positive(E, "E"), _positive(mass, "mass")
    if E <= m:
        raise KinematicsError(f"total energy {E} must exceed the rest energy {m} (p would be zero or imaginary)")
    return math.sqrt(E * E - m * m)


def kinetic_energy(p: float, mass: float) -> float:
    return total_energy(p, mass) - _positive(mass, "mass")


def momentum_from_kinetic_energy(T: float, mass: float) -> float:
    T, m = _positive(T, "T"), _positive(mass, "mass")
    return math.sqrt(T * (T + 2 * m))


def beta(p: float, mass: float) -> float:
    return _positive(p, "p") / total_energy(p, mass)


def gamma(b: float) -> float:
    return 1.0 / math.sqrt(1.0 - check_beta(b) ** 2)


def check_beta(b: float) -> float:
    b = _finite(b, "beta")
    if not 0.0 < b < 1.0:
        raise KinematicsError(f"beta must satisfy 0 < beta < 1, got {b}")
    return b


def momentum_from_beta(b: float, mass: float) -> float:
    return _positive(mass, "mass") * check_beta(b) * gamma(b)


# --- variable-generic conversion ------------------------------------------------
def check_unit(variable: str, unit: str | None) -> None:
    """Reject a unit that belongs to a different variable (e.g. GV given for momentum)."""
    if variable not in VARIABLES:
        raise KinematicsError(f"unknown variable '{variable}'; choose from {', '.join(VARIABLES)}")
    if unit is not None and unit != UNITS[variable]:
        other = [v for v, u in UNITS.items() if u == unit]
        hint = f" ('{unit}' is the unit of {other[0]})" if other else ""
        raise KinematicsError(f"variable '{variable}' expects unit '{UNITS[variable]}', got '{unit}'{hint}; "
                              "do not mix rigidity, momentum, and energies")


def to_momentum(value: float, variable: str, sp: Species) -> float:
    """Momentum [GeV/c] from any supported variable under the species assumptions."""
    check_unit(variable, None)
    if variable == "rigidity":
        return rigidity_to_momentum(value, sp.need_Z())
    if variable == "momentum":
        return _positive(value, "momentum")
    if variable == "total_energy":
        return momentum_from_total_energy(value, sp.need_mass())
    if variable == "kinetic_energy":
        return momentum_from_kinetic_energy(value, sp.need_mass())
    return momentum_from_kinetic_energy(_positive(value, "T/A") * sp.need_A(), sp.need_mass())


def from_momentum(p: float, variable: str, sp: Species) -> float:
    check_unit(variable, None)
    p = _positive(p, "p")
    if variable == "rigidity":
        return momentum_to_rigidity(p, sp.need_Z())
    if variable == "momentum":
        return p
    if variable == "total_energy":
        return total_energy(p, sp.need_mass())
    if variable == "kinetic_energy":
        return kinetic_energy(p, sp.need_mass())
    return kinetic_energy(p, sp.need_mass()) / sp.need_A()


def convert(value: float, src: str, dst: str, sp: Species, unit: str | None = None) -> float:
    """Convert one value from variable `src` to `dst` (optionally validating its unit)."""
    check_unit(src, unit)
    check_unit(dst, None)
    return from_momentum(to_momentum(value, src, sp), dst, sp)


def dvar_dp(variable: str, p: float, sp: Species) -> float:
    """d(variable)/dp at momentum p (exact, all variables are increasing in p)."""
    if variable == "rigidity":
        return 1.0 / sp.need_Z()
    if variable == "momentum":
        return 1.0
    b = beta(p, sp.need_mass())
    return b if variable in ("total_energy", "kinetic_energy") else b / sp.need_A()


def flux_jacobian(value: float, src: str, dst: str, sp: Species) -> float:
    """|d src / d dst| at `value` (in `src`): differential flux converts as
    Phi_dst = Phi_src * flux_jacobian. Point Jacobian; use bin_average_factor for bins."""
    p = to_momentum(value, src, sp)
    return dvar_dp(src, p, sp) / dvar_dp(dst, p, sp)


def propagate(value: float, sigma: float, src: str, dst: str, sp: Species) -> float:
    """First-order sigma_dst = |d dst / d src| * sigma_src (single input, no correlation needed)."""
    return abs(_finite(sigma, "sigma")) / flux_jacobian(value, src, dst, sp)


def convert_bins(edges: list[float], src: str, dst: str, sp: Species, unit: str | None = None) -> dict:
    """Convert strictly increasing positive bin edges. For each bin returns the exact
    factor for a bin-averaged flux, Phi_dst_avg = Phi_src_avg * (width_src / width_dst),
    and the point Jacobian at the geometric bin centre (a convention, not exact)."""
    check_unit(src, unit)
    edges = [_positive(e, "edge") for e in edges]
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise KinematicsError("bin edges must be strictly increasing with at least two values")
    new = [convert(e, src, dst, sp) for e in edges]
    bins = []
    for lo, hi, nlo, nhi in zip(edges, edges[1:], new, new[1:]):
        centre = math.sqrt(lo * hi)
        bins.append({
            "from": [lo, hi], "to": [nlo, nhi],
            "bin_average_flux_factor": (hi - lo) / (nhi - nlo),
            "point_jacobian_at_geometric_centre": flux_jacobian(centre, src, dst, sp),
        })
    return {"edges": new, "bins": bins}


def mass_from_rigidity_beta(R: float, Z: int, b: float) -> float:
    """m [GeV] = |Z| |R| / (gamma beta) = |Z| |R| sqrt(1 - beta^2) / beta."""
    return rigidity_to_momentum(R, Z) / (gamma(b) * check_beta(b))


def mass_relative_uncertainty(sigma_R_rel: float, sigma_beta_rel: float, b: float, rho: float) -> float:
    """First-order dm/m from dR/R and dbeta/beta with an EXPLICIT correlation rho in [-1, 1].
    ln m = ln|Z|R + 0.5 ln(1-beta^2) - ln beta => dm/m = dR/R - gamma^2 dbeta/beta, so
    (dm/m)^2 = (dR/R)^2 + (gamma^2 dbeta/beta)^2 - 2 rho (dR/R)(gamma^2 dbeta/beta).
    rho = 0 means independent; it must be stated by the caller."""
    if rho is None:
        raise KinematicsError("correlation rho between dR/R and dbeta/beta must be stated explicitly (0 = independent)")
    rho = _finite(rho, "rho")
    if not -1.0 <= rho <= 1.0:
        raise KinematicsError(f"rho must lie in [-1, 1], got {rho}")
    a = abs(_finite(sigma_R_rel, "sigma_R_rel"))
    g2 = gamma(b) ** 2
    c = g2 * abs(_finite(sigma_beta_rel, "sigma_beta_rel"))
    return math.sqrt(max(a * a + c * c - 2.0 * rho * a * c, 0.0))


# --- CLI ------------------------------------------------------------------------
def _species(args: argparse.Namespace) -> Species:
    return Species(Z=args.Z, A=args.A, mass=args.mass)


def _envelope(payload: dict) -> dict:
    return {"label": LABEL, "note": NOTE, **payload}


def _run(args: argparse.Namespace) -> dict:
    if args.command == "mass-resolution":
        m = mass_from_rigidity_beta(args.R, args.Z, args.beta)
        rel = mass_relative_uncertainty(args.sigma_R_rel, args.sigma_beta_rel, args.beta, args.rho)
        return _envelope({"assumptions": {"Z": args.Z, "R_GV": args.R, "beta": args.beta, "rho": args.rho},
                          "mass_GeV": m, "gamma": gamma(args.beta),
                          "relative_mass_uncertainty_first_order": rel,
                          "caveat": "first order; non-Gaussian tails and beta resolution near 1 are not represented"})
    sp = _species(args)
    if args.command == "convert":
        result = convert(args.value, args.src, args.dst, sp, args.unit)
        return _envelope({
            "assumptions": {"Z": sp.Z, "A": sp.A, "mass_GeV": sp.mass, "charge_sign": "not used"},
            "input": {"variable": args.src, "value": args.value, "unit": UNITS[args.src]},
            "output": {"variable": args.dst, "value": result, "unit": UNITS[args.dst]},
            "flux_jacobian_abs_dsrc_ddst": flux_jacobian(args.value, args.src, args.dst, sp),
            "sigma_out": None if args.sigma is None else propagate(args.value, args.sigma, args.src, args.dst, sp),
        })
    if args.command == "bins":
        out = convert_bins(args.edges, args.src, args.dst, sp, args.unit)
        return _envelope({"assumptions": {"Z": sp.Z, "A": sp.A, "mass_GeV": sp.mass},
                          "from_variable": args.src, "to_variable": args.dst,
                          "to_unit": UNITS[args.dst], **out})
    raise AssertionError(f"unknown command {args.command!r}")  # unreachable: the subcommand is required


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def species_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--Z", type=int, default=None, help="|Z| (required for anything involving rigidity)")
        p.add_argument("--A", type=int, default=None, help="mass number (required for kinetic energy per nucleon)")
        p.add_argument("--mass", type=float, default=None, help="rest energy in GeV (required for energies and beta)")

    c = sub.add_parser("convert", help="convert one value between variables")
    c.add_argument("--from", dest="src", choices=VARIABLES, required=True)
    c.add_argument("--to", dest="dst", choices=VARIABLES, required=True)
    c.add_argument("--value", type=float, required=True)
    c.add_argument("--unit", default=None, help="if given, must match the --from variable's unit")
    c.add_argument("--sigma", type=float, default=None, help="1-sigma on --value (propagated to first order)")
    species_args(c)
    b = sub.add_parser("bins", help="convert bin edges and report flux conversion factors")
    b.add_argument("--from", dest="src", choices=VARIABLES, required=True)
    b.add_argument("--to", dest="dst", choices=VARIABLES, required=True)
    b.add_argument("--edges", type=float, nargs="+", required=True)
    b.add_argument("--unit", default=None)
    species_args(b)
    m = sub.add_parser("mass-resolution", help="first-order mass and dm/m from R and beta")
    m.add_argument("--R", type=float, required=True, help="|R| in GV")
    m.add_argument("--beta", type=float, required=True)
    m.add_argument("--Z", type=int, default=None)
    m.add_argument("--sigma-R-rel", type=float, required=True)
    m.add_argument("--sigma-beta-rel", type=float, required=True)
    m.add_argument("--rho", type=float, default=None, help="correlation of dR/R and dbeta/beta; required (0 = independent)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = _run(args)
    except KinematicsError as exc:
        print(json.dumps({"label": LABEL, "status": "rejected", "error": str(exc)}, indent=2))
        return 2
    payload["status"] = "ok"
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
