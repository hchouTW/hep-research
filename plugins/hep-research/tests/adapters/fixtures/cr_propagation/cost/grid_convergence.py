#!/usr/bin/env python3
"""Grid convergence of B/C for the cr-propagation A4 cost benchmark (r3 A4 step 2; reported, no threshold).

DRAGON2: each run's ASCII output (output/<name>.txt, columns per total kinetic energy on DRAGON2's E/n grid) is put
per nucleon by multiplying each column by its mass number A (r3 P11, as adapters/cr-propagation/assets/
dragon2_to_prediction.py does), then each isotope is moved to the rigidity axis at its own Z and A,
J_R(R) = J_ekn(E/n(R)) dE/n/dR with E/n = (sqrt((Z R)^2 + M^2) - M)/A and M = A m_u (binding and electrons neglected),
and the isotopes are summed on the rigidity axis (r3 P3): B = 10B + 11B, C = 12C + 13C + 14C. Fluxes are interpolated
linearly in ln(J) against ln(E/n) between DRAGON2 nodes (an all-zero column is skipped; a node used must be > 0). The
reported number is the largest |r_variant(R)/r_reference(R) - 1| over 200 log-spaced rigidities from 2 to 1000 GV.

Closed form (profiles/theory/cr-secondary-ratio): the point values are analytic (no spatial or energy grid); the only
discretization is the 8-node Gauss-Legendre average over each ln(E/n) bin, so its "doubled grid" is 16 nodes, on the
harmonized-v1 bins (1 to 1000 GeV/n, 20 per decade) whose 11B rigidity range lies within 2 to 1000 GV.

Usage:
  python3 grid_convergence.py --reference RUN/output/hv1_base.txt --variant x2s=RUN2/output/hv1_x2s.txt
      [--variant ...] [--plugin-root DIR] --out RESULT.json
Output: RESULT.json and the same JSON on stdout. Exit 0 written, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

M_U_GEV = 0.93149410242  # CODATA 2018 atomic mass unit, as in profiles/theory/cr-secondary-ratio/scripts/predict.py
BORON = ("NUC_5010", "NUC_5011")
CARBON = ("NUC_6012", "NUC_6013", "NUC_6014")
R_MIN_GV, R_MAX_GV, N_RIGIDITY = 2.0, 1000.0, 200


def read_columns(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("Energy [GeV]"):
        raise ValueError(f"{path}: not a DRAGON2 ASCII output")
    names = lines[0].split()[2:]
    energies, cols = [], {n: [] for n in names}
    for ln in lines[1:]:
        parts = [float(x) for x in ln.split()]
        energies.append(parts[0])
        for n, v in zip(names, parts[1:]):
            cols[n].append(v)
    return energies, cols


def isotope_flux_on_rigidity(energies: list[float], values: list[float], uid: int, rig: float) -> float:
    """Per-rigidity flux of one isotope at rigidity `rig` (GV); `values` per total kinetic energy (DRAGON2)."""
    z, a = divmod(uid, 1000)
    mass = a * M_U_GEV
    pz = z * rig
    e_n = (math.sqrt(pz * pz + mass * mass) - mass) / a
    jacobian = z * pz / (a * math.sqrt(pz * pz + mass * mass))
    if not energies[0] <= e_n <= energies[-1]:
        raise ValueError(f"NUC_{uid}: E/n = {e_n:.4g} GeV/n at R = {rig:.4g} GV is outside the run's energy grid")
    k = max(i for i in range(len(energies) - 1) if energies[i] <= e_n)
    lo, hi = values[k] * a, values[k + 1] * a
    if lo <= 0 or hi <= 0:
        raise ValueError(f"NUC_{uid}: non-positive flux at a node used near E/n = {e_n:.4g}")
    t = (math.log(e_n) - math.log(energies[k])) / (math.log(energies[k + 1]) - math.log(energies[k]))
    return math.exp((1 - t) * math.log(lo) + t * math.log(hi)) * jacobian


def ratio_on_rigidity(path: Path, grid: list[float]) -> list[float]:
    energies, cols = read_columns(path)

    def element(names: tuple[str, ...], rig: float) -> float:
        total = 0.0
        for n in names:
            if n in cols and any(v > 0 for v in cols[n]):
                total += isotope_flux_on_rigidity(energies, cols[n], int(n[4:]), rig)
        return total

    return [element(BORON, r) / element(CARBON, r) for r in grid]


def closed_form_quadrature(plugin_root: Path) -> dict:
    scripts = plugin_root / "profiles" / "theory" / "cr-secondary-ratio" / "scripts"
    sys.path.insert(0, str(scripts))
    import predict  # noqa: E402  (profile script, imported by path)

    cfg = predict.load_json(predict.DEFAULT_CONFIG)
    edges = [1.0] + [10 ** (k / 20) for k in range(1, 60)] + [1000.0]
    sec = cfg["secondary"]
    inside = [i for i, (lo, hi) in enumerate(zip(edges, edges[1:]))
              if predict.kinematics(lo, sec)[0] >= R_MIN_GV and predict.kinematics(hi, sec)[0] <= R_MAX_GV]
    point = {"D0_cm2_s": 3.0e28, "L_kpc": 4.0, "delta": 0.5, "R0_GV": 1.0, "h_kpc": 0.1, "n_H_cm3": 1.0}
    v8 = predict.bin_averaged(cfg, edges, point, n_nodes=8)
    v16 = predict.bin_averaged(cfg, edges, point, n_nodes=16)
    changes = [abs(v16[i] / v8[i] - 1.0) for i in inside]
    return {"bins_used": len(inside), "ekn_range_gev_per_n": [edges[inside[0]], edges[inside[-1] + 1]],
            "max_relative_change": max(changes), "nodes": [8, 16]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--variant", action="append", default=[], help="LABEL=PATH to a variant run's output")
    ap.add_argument("--plugin-root", type=Path, default=Path(__file__).resolve().parents[5])
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    grid = [R_MIN_GV * (R_MAX_GV / R_MIN_GV) ** (i / (N_RIGIDITY - 1)) for i in range(N_RIGIDITY)]
    try:
        ref = ratio_on_rigidity(args.reference, grid)
        result = {"rigidity_gv": [R_MIN_GV, R_MAX_GV], "n_rigidities": N_RIGIDITY,
                  "reference_bc_at": {f"{r:g}": ref[min(range(N_RIGIDITY), key=lambda i: abs(grid[i] - r))]
                                      for r in (2.0, 10.0, 100.0, 1000.0)},
                  "variants": {}}
        for item in args.variant:
            label, _, path = item.partition("=")
            var = ratio_on_rigidity(Path(path), grid)
            rel = [v / r - 1.0 for v, r in zip(var, ref)]
            imax = max(range(N_RIGIDITY), key=lambda i: abs(rel[i]))
            result["variants"][label] = {"max_abs_relative_change": abs(rel[imax]),
                                         "signed_change_at_max": rel[imax], "at_rigidity_gv": grid[imax]}
        result["closed_form_quadrature"] = closed_form_quadrature(args.plugin_root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    result["status"] = "ok"
    text = json.dumps(result, indent=1)
    args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
