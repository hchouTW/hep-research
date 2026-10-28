#!/usr/bin/env python3
"""Read USINE local-flux tables and turn them into ratios of bin integrals (a numerical prediction).

USINE V3.5 'usine -l' writes one table per quantity, local_fluxes_<NAME>_Ekn_<model>_SolMod0DFF_phi0_00GV.out: '#'
header lines (program, date, model, quantity, modulation, column titles) and two columns, E_k/n in GeV/n and the
unmodulated local interstellar flux per E_k/n in (GeV/n m^2 s sr)^-1 (r3 P11: the unit is read from the header and
checked). This reader uses the isotope tables only; USINE's own element-ratio tables are read only to check it.
A run with solar modulation (usine_translate.py --phi, work package F1) also writes each isotope's force-field
modulated table, local_fluxes_<NAME>_Ekn_<model>_SolMod0DFF_phi<phi>GV.out (phi with USINE's rounding in the name),
whose first column is the top-of-atmosphere E_k/n; with phi > 0 the reader reads those tables, after checking that the
header's 'SolMod0DFF_phi<value>GV' equals the requested phi within USINE's printed precision (5e-4 GV), so every
isotope is modulated with its own Z and A before any ratio is formed (r3 P4).

Values (r3 P2, P3): an element ratio X/Y in a bin is the bin integral of the summed numerator isotopes over the bin
integral of the summed denominator isotopes, never the bin average of the ratio. On the axis ekn every isotope is
integrated over the same E_k/n bin; on the axis rigidity each isotope is integrated over the E_k/n interval of the
rigidity bin for its own Z and A (the integral of a flux per rigidity over a rigidity bin equals the integral of the
flux per E_k/n over the mapped interval, so no Jacobian is needed), then the isotopes are summed. Between USINE's
nodes the flux is a power law (log-log interpolation; linear where a node value is 0), integrated exactly. Rigidity
from E_k/n with the bare-nucleus mass of core.constants.physical (AME2020): R = sqrt(T (T + 2M)) / Z, T = A E_k/n.
An isotope of the observable that is not in the run's network contributes nothing (it is listed in the prediction);
an observable none of whose numerator or denominator isotopes is in the network is refused.

Usage:
  python3 usine_to_prediction.py --run-dir RUNDIR --observable B/C --axis rigidity --edges 2,5,10,100
                                 [--model Model2DKisoVc] [--param D0_cm2_s=3e28 ...] [--out P.json]
  RUNDIR is the directory written by usine_translate.py run (its out/ folder and translation.json).
Output: JSON {"status": "ok", "prediction": {...}} (or "error"). Exit 0 ok, 2 bad input or missing table.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
from core.constants.physical import nuclear_mass_gev  # noqa: E402

FLUX_UNIT = "[GeV/n m^{2} s sr]^{-1}"
ELEMENTS = {1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N", 8: "O"}
# observable -> (numerator isotopes, denominator isotopes, species names for the prediction)
OBSERVABLES = {
    "B/C": (["10B", "11B"], ["12C", "13C", "14C"], ["boron", "carbon"]),  # 14C: in USINE's own network (B1X)
    "10Be/9Be": (["10Be"], ["9Be"], ["beryllium-10", "beryllium-9"]),
    "Be/B": (["7Be", "9Be", "10Be"], ["10B", "11B"], ["beryllium", "boron"]),
}
VARIABLE = {"ekn": ("kinetic_energy_per_nucleon", "GeV/n"), "rigidity": ("rigidity", "GV")}


class ReadError(ValueError):
    """A USINE table that cannot be read, or a request it cannot answer."""


def charge_and_mass(nuclide: str) -> tuple[int, int]:
    digits = "".join(c for c in nuclide if c.isdigit())
    symbol = nuclide[len(digits):]
    z = {v: k for k, v in ELEMENTS.items()}.get(symbol.capitalize())
    if not digits or z is None:
        raise ReadError(f"nuclide {nuclide!r}: expected '<A><element>' with Z <= 8")
    return z, int(digits)


PHI_PRINT_TOLERANCE_GV = 5e-4  # USINE prints phi with 3 decimals in the table header
MODULATION_HEADER = re.compile(r"SolMod0DFF_phi([0-9.]+)GV")


def table_name(nuclide_or_ratio: str, model: str, axis: str = "Ekn") -> str:
    """USINE's table name of a quantity per E_k/n ('Ekn') or per rigidity ('R')."""
    return f"local_fluxes_{nuclide_or_ratio.upper().replace('/', '')}_{axis}_{model}_SolMod0DFF_phi0_00GV.out"


def read_table(path: Path, phi_gv: float = 0.0) -> tuple[list[float], list[float], dict]:
    """(E_k/n nodes, values, header) of one USINE table at modulation phi_gv (0: unmodulated); the header holds
    'quantity', 'model', 'columns'."""
    header, xs, ys = [], [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line[1:].strip())
        elif line.strip():
            parts = line.split()
            if len(parts) != 2:
                raise ReadError(f"{Path(path).name}: a data line has {len(parts)} columns, expected 2")
            xs.append(float(parts[0]))
            ys.append(float(parts[1]))
    if len(header) < 6 or not header[0].startswith("USINE"):
        raise ReadError(f"{Path(path).name}: not a USINE table (header {header[:2]})")
    if not xs or any(b <= a for a, b in zip(xs, xs[1:])):
        raise ReadError(f"{Path(path).name}: E_k/n nodes must be increasing")
    if any(not math.isfinite(y) or y < 0 for y in ys):
        raise ReadError(f"{Path(path).name}: negative or non-finite values")
    meta = {"program": header[0], "model": header[2], "quantity": header[3], "modulation": header[4],
            "columns": header[5]}
    if not meta["columns"].startswith(("Ekn [GeV/n]", "R [GV]")):
        raise ReadError(f"{Path(path).name}: first column is neither E_k/n in GeV/n nor R in GV ({meta['columns']!r})")
    m = MODULATION_HEADER.search(meta["modulation"])
    if not m:
        raise ReadError(f"{Path(path).name}: no force-field modulation in the header ({meta['modulation']!r})")
    if abs(float(m.group(1)) - float(phi_gv)) > PHI_PRINT_TOLERANCE_GV:
        raise ReadError(f"{Path(path).name}: table at phi = {m.group(1)} GV, {float(phi_gv):g} GV requested")
    meta["phi_gv"] = float(m.group(1))
    return xs, ys, meta


def modulated_table(out_dir: Path, nuclide: str, model: str) -> Path:
    """The one force-field modulated table of an isotope in a run's output folder (phi > 0)."""
    hits = [p for p in sorted(Path(out_dir).glob(f"local_fluxes_{nuclide.upper()}_Ekn_{model}_SolMod0DFF_phi*GV.out"))
            if not p.name.endswith("_phi0_00GV.out")]
    if len(hits) != 1:
        raise ReadError(f"{nuclide}: {len(hits)} modulated tables in {Path(out_dir).name}, expected one")
    return hits[0]


def read_isotope(out_dir: Path, nuclide: str, model: str, phi_gv: float = 0.0) -> tuple[list[float], list[float]]:
    path = modulated_table(out_dir, nuclide, model) if phi_gv else Path(out_dir) / table_name(nuclide, model)
    xs, ys, meta = read_table(path, phi_gv)
    if not meta["columns"].startswith("Ekn [GeV/n]"):
        raise ReadError(f"table of {nuclide} is not per E_k/n")
    if meta["quantity"].upper() != nuclide.upper():
        raise ReadError(f"table of {nuclide} holds {meta['quantity']}")
    if FLUX_UNIT not in meta["columns"]:
        raise ReadError(f"{nuclide}: flux unit is not {FLUX_UNIT} ({meta['columns']!r}) (r3 P11)")
    return xs, ys


def _segment_integral(x0, x1, y0, y1, a, b) -> float:
    """Integral over [a, b] within the node interval [x0, x1] of the power law through (x0, y0), (x1, y1)."""
    if y0 <= 0 or y1 <= 0:
        ya = y0 + (y1 - y0) * (a - x0) / (x1 - x0)
        yb = y0 + (y1 - y0) * (b - x0) / (x1 - x0)
        return 0.5 * (ya + yb) * (b - a)
    s = math.log(y1 / y0) / math.log(x1 / x0)
    if abs(s + 1.0) < 1e-12:
        return y0 * x0 * math.log(b / a)
    return y0 * x0 / (s + 1.0) * ((b / x0) ** (s + 1.0) - (a / x0) ** (s + 1.0))


def integrate(xs: list[float], ys: list[float], a: float, b: float) -> float:
    """Integral of the log-log interpolated table over [a, b] (inside the nodes)."""
    if not xs[0] * (1 - 1e-9) <= a < b <= xs[-1] * (1 + 1e-9):
        raise ReadError(f"interval [{a:g}, {b:g}] GeV/n leaves the table's range [{xs[0]:g}, {xs[-1]:g}]")
    a, b = max(a, xs[0]), min(b, xs[-1])
    total = 0.0
    for i in range(len(xs) - 1):
        lo, hi = max(a, xs[i]), min(b, xs[i + 1])
        if hi > lo:
            total += _segment_integral(xs[i], xs[i + 1], ys[i], ys[i + 1], lo, hi)
    return total


def interpolate(xs: list[float], ys: list[float], x: float) -> float:
    """Log-log interpolated value at x (linear where a node value is 0)."""
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            if ys[i] <= 0 or ys[i + 1] <= 0:
                return ys[i] + (ys[i + 1] - ys[i]) * (x - xs[i]) / (xs[i + 1] - xs[i])
            s = math.log(ys[i + 1] / ys[i]) / math.log(xs[i + 1] / xs[i])
            return ys[i] * (x / xs[i]) ** s
    raise ReadError(f"{x:g} GeV/n is outside the table's range")


def ekn_from_rigidity(rigidity_gv: float, z: int, a: int) -> float:
    mass = nuclear_mass_gev(z, a)
    return (math.sqrt((rigidity_gv * z) ** 2 + mass ** 2) - mass) / a


def rigidity_from_ekn(ekn_gev: float, z: int, a: int) -> float:
    t = ekn_gev * a
    return math.sqrt(t * (t + 2.0 * nuclear_mass_gev(z, a))) / z


def bin_integral(tables: dict, nuclide: str, low: float, high: float, axis: str) -> float:
    xs, ys = tables[nuclide]
    if axis == "ekn":
        return integrate(xs, ys, low, high)
    z, a = charge_and_mass(nuclide)
    return integrate(xs, ys, ekn_from_rigidity(low, z, a), ekn_from_rigidity(high, z, a))


def present(observable: str, species) -> tuple[list[str], list[str]]:
    if observable not in OBSERVABLES:
        raise ReadError(f"observable {observable!r}: one of {sorted(OBSERVABLES)}")
    num, den, _ = OBSERVABLES[observable]
    num_in, den_in = [n for n in num if n in species], [d for d in den if d in species]
    if not num_in or not den_in:
        raise ReadError(f"{observable} needs at least one of {num} and one of {den} in the network {sorted(species)}")
    return num_in, den_in


def ratio_of_bin_integrals(tables: dict, observable: str, edges: list[float], axis: str) -> list[float]:
    """r3 P2/P3 ratio per bin; tables: nuclide -> (E_k/n nodes, flux per E_k/n)."""
    if axis not in VARIABLE:
        raise ReadError(f"axis {axis!r}: ekn or rigidity")
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ReadError("edges must be increasing, at least two")
    num, den = present(observable, tables)
    out = []
    for low, high in zip(edges, edges[1:]):
        n = sum(bin_integral(tables, s, low, high, axis) for s in num)
        d = sum(bin_integral(tables, s, low, high, axis) for s in den)
        if d <= 0:
            raise ReadError(f"{observable}: denominator integral is 0 in [{low:g}, {high:g}]")
        out.append(n / d)
    return out


def point_ratio(tables: dict, observable: str, x: float, axis: str) -> float:
    """The ratio at one point (sum of fluxes at equal E_k/n, or per rigidity at equal rigidity): used only to check
    the reader against USINE's own element-ratio tables."""
    num, den = present(observable, tables)

    def flux(s):
        xs, ys = tables[s]
        if axis == "ekn":
            return interpolate(xs, ys, x)
        z, a = charge_and_mass(s)
        mass = nuclear_mass_gev(z, a)
        de_dr = x * z * z / (a * math.sqrt((x * z) ** 2 + mass ** 2))  # d(E_k/n)/dR
        return interpolate(xs, ys, ekn_from_rigidity(x, z, a)) * de_dr

    return sum(flux(s) for s in num) / sum(flux(s) for s in den)


def read_run(out_dir: Path, model: str, species, phi_gv: float = 0.0) -> dict:
    """nuclide -> (E_k/n nodes, flux) for every species of the run, modulated at phi_gv (0: unmodulated)."""
    return {s: read_isotope(out_dir, s, model, phi_gv) for s in species}


def prediction(observable: str, axis: str, edges: list[float], values: list[float], point: dict, run: dict) -> dict:
    """A numerical prediction (contracts ext_prediction) of one observable from one USINE run."""
    var_name, unit = VARIABLE[axis]
    num, den = present(observable, run["species"])
    species = OBSERVABLES[observable][2]
    absent = [s for s in OBSERVABLES[observable][0] + OBSERVABLES[observable][1] if s not in run["species"]]
    mod = run.get("solar_modulation")
    where = (f" (r = {run['observer_kpc']} kpc, z = 0)" if run.get("observer_kpc") else " (z = 0)")
    return {
        "observable": {
            "quantity": "ratio",
            "process": (f"force-field modulated {observable} (USINE SolMod0DFF, phi = {mod['phi_gv']:.10g} GV, per "
                        "isotope)" if mod else f"unmodulated local interstellar {observable}")
                       + f" from a USINE V3.5 run ({run['model']}): ratio of "
                       f"bin integrals of {'+'.join(num)} over {'+'.join(den)}"
                       + (f" ({', '.join(absent)} not in the network)" if absent else ""),
            "species": [{"name": s} for s in species],
            "variables": [{"name": var_name, "unit": unit, "edges": edges}],
            "phase_space": {"definition": (f"USINE flux near Earth after force-field solar modulation of the local "
                                           f"interstellar flux at the observer{where}" if mod else
                                           f"USINE local interstellar flux at the observer{where}, before solar "
                                           "modulation"), "fiducial": False},
            "level": "top-of-atmosphere" if mod else "crsr:local-interstellar",
            "normalization": {"kind": "exposure", "value": "not-applicable",
                              "convention": "ratio of two bin-integrated fluxes; the normalization cancels"},
            "bin_semantics": "bin-averaged",
            "unit": "1",
            "conventions": {
                "energy_variable": f"{var_name} in {unit}: the ratio of the bin-integrated fluxes (r3 P2; equal to the "
                                   "ratio of their bin averages), isotopes summed at equal "
                                   + ("rigidity" if axis == "rigidity" else "E/n") + " (P3)",
                "frame": "Galactic rest frame (interstellar gas at rest)",
                "mass_approximation": "bare-nucleus masses of AME2020 (core.constants.physical) for the rigidity "
                                      "mapping; USINE's own kinematics inside the run",
            },
            "validity_range": {"variable": var_name, "min": edges[0], "max": edges[-1], "unit": unit},
        },
        "derivation_status": "numerical-evidence",
        "parameter_point": {**{k: float(v) for k, v in point.items()}, "usine_run": run["name"],
                            "transport_substitutes": list(run.get("substitutes", []))},
        "representation": "numerical",
        "values": {"edges": edges, "values": values, "unit": "1"},
        "uncertainties": [],
        "allowed_transformations": (["level-identification",
                                     "level-identification: top-of-atmosphere to top-of-instrument for an instrument "
                                     "in space (no atmosphere to cross)",
                                     "rebin (recompute the bin integrals from the run's tables; never merge ratios)"]
                                    if mod else
                                    ["solar modulation per isotope (outside this reader)",
                                     "rebin (recompute the bin integrals from the run's tables; never merge ratios)"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog="Exit 0 ok, 2 bad input.")
    ap.add_argument("--run-dir", required=True, type=Path, help="run directory written by usine_translate.py run")
    ap.add_argument("--observable", required=True, choices=sorted(OBSERVABLES))
    ap.add_argument("--axis", required=True, choices=sorted(VARIABLE))
    ap.add_argument("--edges", required=True, help="comma-separated bin edges (GeV/n or GV)")
    ap.add_argument("--param", action="append", default=[], help="NAME=VALUE written into parameter_point")
    ap.add_argument("--phi", type=float, default=None,
                    help="read the modulated tables at this phi in GV (default: the run's translation.json)")
    ap.add_argument("--out", type=Path, help="prediction JSON to write")
    args = ap.parse_args(argv)
    try:
        run = json.loads((args.run_dir / "translation.json").read_text(encoding="utf-8"))
        edges = [float(x) for x in args.edges.split(",")]
        point = {k: float(v) for k, v in (p.split("=", 1) for p in args.param)}
        phi = args.phi if args.phi is not None else ((run.get("solar_modulation") or {}).get("phi_gv") or 0.0)
        run = dict(run, solar_modulation=(dict(run.get("solar_modulation") or {"model": "SolMod0DFF"}, phi_gv=phi)
                                          if phi else None))
        tables = read_run(args.run_dir / "out", run["model"], run["species"], phi)
        values = ratio_of_bin_integrals(tables, args.observable, edges, args.axis)
        pred = prediction(args.observable, args.axis, edges, values, point, run)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    if args.out:
        args.out.write_text(json.dumps(pred, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "prediction": pred if not args.out else str(args.out), "values": values}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
