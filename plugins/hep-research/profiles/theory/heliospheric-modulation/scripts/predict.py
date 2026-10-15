#!/usr/bin/env python3
"""Closed-form benchmark of theory:heliospheric-modulation: a power-law local interstellar spectrum (LIS) modulated
analytically in the force-field approximation, compared with the force-field implementation of hep-measurement.

The profile does not reimplement the force field. Every force-field number comes from
<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py, run as a separate process through its
command line (profiles may import only core and contracts; tools/check_layering.py). This file holds only the
closed forms derived and checked in derive.py, used as the independent side of the benchmark:

  Ek_total:        J = A T (T + 2m) / (T' (T' + 2m)) T'^-gamma,                       T' = T + Z phi
  Ek_per_nucleon:  J = A t (t + 2 m_n) / (t' (t' + 2 m_n)) t'^-gamma,  m_n = m / A_n,  t' = t + (Z / A_n) phi
  rigidity:        J = A p^3 E' / (p'^3 E) R'^-gamma,  p = Z R, E' = E + Z phi, p' = sqrt(E'^2 - m^2), R' = p' / Z

Benchmark (--benchmark): for each species, phi, energy kind and point of benchmarks/power-law-benchmark.json, the
script's --modulate output against the closed form (relative tolerance from the config), phi = 0 against the LIS, and
the script's --demodulate of its own modulated flux against the LIS (round trip). The inputs are synthetic.
--point evaluates one point both ways and flags a point below the Gleeson-Axford breakdown energy (helmod:C03).

Usage: python3 predict.py --benchmark [--config ../benchmarks/power-law-benchmark.json]
       python3 predict.py --point --kind rigidity --x 2.0 --mass 0.938272 --charge 1 --phi 0.6 --norm 1e4 --index 2.7
Exit 0 ok (all benchmark checks pass), 1 a check fails, 2 bad input, 3 the force-field script failed or is missing.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROFILE = HERE.parent
PLUGIN = PROFILE.parents[2]
FORCE_FIELD = PLUGIN / "skills" / "hep-measurement" / "scripts" / "solar_modulation_force_field.py"
DEFAULT_CONFIG = PROFILE / "benchmarks" / "power-law-benchmark.json"
KINDS = ("Ek_total", "Ek_per_nucleon", "rigidity")
# Gleeson & Axford (1968) p. 1016 (helmod:C03): the approximation breaks down below about these kinetic energies
# per nucleon (GeV/n) for protons and alpha particles; other species are not stated there.
BREAKDOWN_GEV_PER_N = {(1, 1): 0.300, (2, 4): 0.250}


class ScriptError(RuntimeError):
    """The force-field script failed, is missing, or returned something unreadable."""


def _check_positive(**values) -> None:
    for name, v in values.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError(f"{name} must be a finite positive number")


def closed_form(kind: str, x: float, mass: float, charge: int, phi_gv: float, norm: float, index: float,
                mass_number: int | None = None) -> float:
    """J_TOA(x) for J_LIS(x) = norm * x^-index in the variable of `kind` (derive.py, step 3)."""
    _check_positive(x=x, mass=mass, norm=norm)
    if not math.isfinite(phi_gv) or phi_gv < 0:
        raise ValueError("phi must be finite and nonnegative")
    if kind == "Ek_total":
        tp = x + charge * phi_gv
        return norm * x * (x + 2 * mass) / (tp * (tp + 2 * mass)) * tp ** (-index)
    if kind == "Ek_per_nucleon":
        if not mass_number:
            raise ValueError("Ek_per_nucleon needs mass_number")
        mn = mass / mass_number
        tp = x + charge / mass_number * phi_gv
        return norm * x * (x + 2 * mn) / (tp * (tp + 2 * mn)) * tp ** (-index)
    if kind == "rigidity":
        p = charge * x
        e = math.sqrt(p * p + mass * mass)
        ep = e + charge * phi_gv
        pp = math.sqrt(ep * ep - mass * mass)
        return norm * p ** 3 * ep / (pp ** 3 * e) * (pp / charge) ** (-index)
    raise ValueError(f"kind must be one of {', '.join(KINDS)}")


def run_force_field(mode: str, kind: str, x: float, mass: float, charge: int, phi_gv: float, *,
                    norm: float | None = None, index: float | None = None, toa_flux: float | None = None,
                    mass_number: int | None = None) -> dict:
    """One point from the hep-measurement force-field script (separate process, its documented CLI)."""
    if not FORCE_FIELD.is_file():
        raise ScriptError(f"force-field script not found: {FORCE_FIELD}")
    cmd = [sys.executable, str(FORCE_FIELD), f"--{mode}", "--energy", repr(x), "--energy-kind", kind,
           "--mass", repr(mass), "--charge", str(charge), "--phi", repr(phi_gv), "--status", "synthetic"]
    if mass_number is not None:
        cmd += ["--mass-number", str(mass_number)]
    if mode == "modulate":
        cmd += ["--lis-normalization", repr(norm), "--lis-index", repr(index)]
    else:
        cmd += ["--toa-flux", repr(toa_flux)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise ScriptError(f"force-field script exit {proc.returncode}: {proc.stderr.strip()[-400:]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ScriptError(f"unreadable force-field output: {exc}") from None


def below_breakdown(kind: str, x: float, mass: float, charge: int, mass_number: int | None) -> bool | None:
    """True if the point lies below the Gleeson-Axford breakdown energy (helmod:C03); None if not stated for it."""
    limit = BREAKDOWN_GEV_PER_N.get((charge, mass_number or 0))
    if limit is None:
        return None
    if kind == "Ek_total":
        tn = x / mass_number
    elif kind == "Ek_per_nucleon":
        tn = x
    else:
        p = charge * x
        tn = (math.sqrt(p * p + mass * mass) - mass) / mass_number
    return tn < limit


def point(kind: str, x: float, mass: float, charge: int, phi_gv: float, norm: float, index: float,
          mass_number: int | None = None) -> dict:
    cf = closed_form(kind, x, mass, charge, phi_gv, norm, index, mass_number)
    ff = run_force_field("modulate", kind, x, mass, charge, phi_gv, norm=norm, index=index, mass_number=mass_number)
    return {"kind": kind, "x": x, "phi_gv": phi_gv, "closed_form": cf, "script": ff["flux_toa"],
            "relative_difference": abs(ff["flux_toa"] - cf) / cf,
            "below_gleeson_axford_breakdown": below_breakdown(kind, x, mass, charge, mass_number),
            "status": "synthetic"}


def benchmark(cfg: dict) -> dict:
    tol = cfg["relative_tolerance"]
    norm, index = cfg["lis"]["normalization"], cfg["lis"]["index"]
    rows, worst, phi0_worst, round_trip_worst = [], 0.0, 0.0, 0.0
    for sp in cfg["species"]:
        for phi in cfg["phi_gv"]:
            for kind in KINDS:
                for x in cfg["points"][kind]:
                    mn = sp["mass_number"] if kind == "Ek_per_nucleon" else None
                    row = point(kind, x, sp["mass_gev"], sp["charge"], phi, norm, index, mn)
                    row["species"] = sp["name"]
                    worst = max(worst, row["relative_difference"])
                    if phi == 0:
                        phi0_worst = max(phi0_worst, abs(row["script"] - norm * x ** (-index)) / (norm * x ** (-index)))
                    if phi == cfg["round_trip_phi_gv"]:
                        back = run_force_field("demodulate", kind, x, sp["mass_gev"], sp["charge"], phi,
                                               toa_flux=row["script"], mass_number=mn)
                        lis = norm * back["energy_lis"] ** (-index)
                        round_trip_worst = max(round_trip_worst, abs(back["flux_lis"] - lis) / lis)
                    rows.append(row)
    checks = {"script_matches_closed_form": worst <= tol,
              "phi_zero_returns_the_lis": phi0_worst <= tol,
              "demodulate_inverts_modulate": round_trip_worst <= tol,
              "modulation_suppresses_the_flux": all(r["script"] < norm * r["x"] ** (-index)
                                                     for r in rows if r["phi_gv"] > 0)}
    return {"label": cfg["label"], "status": "synthetic", "relative_tolerance": tol,
            "max_relative_difference": worst, "max_relative_difference_phi_zero": phi0_worst,
            "max_relative_difference_round_trip": round_trip_worst, "n_points": len(rows),
            "force_field_script": str(FORCE_FIELD.relative_to(PLUGIN)), "checks": checks, "points": rows}


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    for key in ("species", "phi_gv", "points", "lis", "relative_tolerance", "round_trip_phi_gv"):
        if key not in cfg:
            raise ValueError(f"config lacks {key}")
    return cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--benchmark", action="store_true", help="run the closed-form benchmark")
    mode.add_argument("--point", action="store_true", help="one point, closed form and script")
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--kind", choices=KINDS, default="Ek_total")
    ap.add_argument("--x", type=float)
    ap.add_argument("--mass", type=float)
    ap.add_argument("--charge", type=int)
    ap.add_argument("--mass-number", type=int, dest="mass_number")
    ap.add_argument("--phi", type=float, help="modulation potential in GV")
    ap.add_argument("--norm", type=float)
    ap.add_argument("--index", type=float)
    ap.add_argument("--out", type=Path)
    opts = ap.parse_args(argv)
    try:
        if opts.benchmark:
            out = benchmark(load_config(opts.config))
            ok = all(out["checks"].values())
        else:
            if None in (opts.x, opts.mass, opts.charge, opts.phi, opts.norm, opts.index):
                raise ValueError("--point needs --x, --mass, --charge, --phi, --norm and --index")
            if opts.charge <= 0:
                raise ValueError("charge must be a positive integer")
            out = point(opts.kind, opts.x, opts.mass, opts.charge, opts.phi, opts.norm, opts.index, opts.mass_number)
            ok = True
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 2
    except ScriptError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 3
    text = json.dumps(out, indent=1) + "\n"
    if opts.out:
        opts.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
