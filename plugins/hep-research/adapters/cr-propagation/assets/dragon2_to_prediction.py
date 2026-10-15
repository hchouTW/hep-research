#!/usr/bin/env python3
"""Convert DRAGON2 local-spectrum output into one `prediction` artifact (representation "grid") per run.

One DRAGON2 run is one node of a parameter grid: this script reads the run's ASCII output (output/<name>.txt: a header
"Energy [GeV]" followed by one column per species, e.g. NUC_5011 for 1000 Z + A, fluxes at the observer on DRAGON2's
kinetic-energy-per-nucleon grid, each column per total kinetic energy, so it is multiplied by its mass number A to
put it per nucleon), forms a ratio of summed columns (for B/C: NUC_5010,NUC_5011 over
NUC_6012,NUC_6013,NUC_6014), averages it over the requested bins and writes a prediction whose parameter_point is the
node. Many such artifacts form the grid that skills/hep-statistics/scripts/covariance_fit.py (model "tabulated-grid")
fits; each must pass contracts/comparison/gate.py against the measurement first.

Bin average (stated, not inferred): the ratio averaged uniformly in ln(E/n) over each bin, with 8-point Gauss-Legendre
nodes in ln(E/n) on a piecewise-linear interpolation of ln(ratio) in ln(E/n) between DRAGON2's energy nodes. Bin edges
outside DRAGON2's energy range are refused (no extrapolation). With --points instead of --edges the ratio is written at
DRAGON2's own nodes inside the range ("point" semantics). A zero or negative ratio at a node used is refused.

Usage:
  python3 dragon2_to_prediction.py --txt RUN/output/NAME.txt --numerator NUC_5010,NUC_5011
      --denominator NUC_6012,NUC_6013,NUC_6014 (--edges 10,30,100 | --points 10,1000) --level LEVEL
      --param D0=3e28 --param L=4 [--param KEY=VALUE ...] --out PRED.json
      [--observable OBS.json] [--theory-spec-ref REF] [--run-record RUN.json] [--artifact-id ID] [--status S ...]
  --level: the observable level of the prediction (core levels: parton, particle-fiducial, detector, unfolded; a
      local interstellar ratio usually needs a profile's level term, which contracts/validate.py accepts with
      --profiles-from). --observable: a JSON object merged over the default observable (process, species,
      phase_space, conventions, normalization, ...); variables, bin_semantics and unit are always set here.
  --param values parse as numbers when they can, else stay strings; the grid axes named in the fit must be numbers.
  --run-record: the run's computational-run artifact; its id and the output's SHA-256 (checked against the file) go
      into the prediction's inputs.
Output: JSON with "status" ("ok" or "error"). Exit 0 written, 2 bad input (unreadable output, unknown column,
edges outside the energy range, hash mismatch), 3 numpy missing.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import sys
from pathlib import Path

GL_NODES = 8
DEFAULT_STATUS = ["unvalidated"]


class ConvertError(ValueError):
    """Input that cannot be converted."""


def read_output(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    """(energies in GeV/n, {column: values}) from a DRAGON2 ASCII output file."""
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines or not lines[0].startswith("Energy [GeV]"):
        raise ConvertError(f"{path.name}: not a DRAGON2 ASCII output (no 'Energy [GeV]' header)")
    names = lines[0].split()[2:]
    energies, cols = [], {n: [] for n in names}
    for i, ln in enumerate(lines[1:], start=2):
        parts = ln.split()
        if len(parts) != len(names) + 1:
            raise ConvertError(f"{path.name} line {i}: {len(parts)} fields, header has {len(names) + 1}")
        try:
            row = [float(x) for x in parts]
        except ValueError as exc:
            raise ConvertError(f"{path.name} line {i}: {exc}") from exc
        energies.append(row[0])
        for n, v in zip(names, row[1:]):
            cols[n].append(v)
    if len(energies) < 2 or any(b <= a for a, b in zip(energies, energies[1:])):
        raise ConvertError(f"{path.name}: energies must be at least two and strictly increasing")
    return energies, cols


def mass_number(column: str) -> int:
    """Mass number A of an output column: NUC_<1000 Z + A> gives A, Pri_p and Sec_p give 1."""
    if column in ("Pri_p", "Sec_p"):
        return 1
    if column.startswith("NUC_") and column[4:].isdigit() and int(column[4:]) % 1000 > 0:
        return int(column[4:]) % 1000
    raise ConvertError(f"column {column!r}: no mass number, so it cannot be put per nucleon (use NUC_<1000 Z + A>, "
                       "Pri_p or Sec_p)")


def ratio(cols: dict, numerator: list[str], denominator: list[str]) -> list[float]:
    """Ratio of summed columns at equal E/n. DRAGON2 writes its internal density per total kinetic energy (dragon.cc
    writes GetFluxAtSunPosition, which computes weight = A but does not apply it, and particle.cc scales the spallation
    source by A_parent / A_daughter), so every column is multiplied by its mass number A to put it per nucleon."""
    for c in numerator + denominator:
        if c not in cols:
            raise ConvertError(f"column {c!r} not in the output (have: {', '.join(sorted(cols))})")
    num = [sum(v) for v in zip(*([mass_number(c) * x for x in cols[c]] for c in numerator))]
    den = [sum(v) for v in zip(*([mass_number(c) * x for x in cols[c]] for c in denominator))]
    return [n / d if d > 0 else float("nan") for n, d in zip(num, den)]


def _interp_log(energies: list[float], values: list[float], e: float) -> float:
    """ln(value) linear in ln(E) between the bracketing nodes; e must lie inside the node range."""
    import bisect
    j = min(max(bisect.bisect_right(energies, e) - 1, 0), len(energies) - 2)
    e0, e1, v0, v1 = energies[j], energies[j + 1], values[j], values[j + 1]
    if not (v0 > 0 and v1 > 0):
        raise ConvertError(f"the ratio is not positive at {e0:g} or {e1:g} GeV/n; a log interpolation is undefined")
    t = (math.log(e) - math.log(e0)) / (math.log(e1) - math.log(e0))
    return math.exp((1 - t) * math.log(v0) + t * math.log(v1))


def bin_average(energies: list[float], values: list[float], edges: list[float]) -> list[float]:
    """Average of the ratio uniformly in ln(E) over each bin (Gauss-Legendre, GL_NODES nodes)."""
    import numpy as np
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise ConvertError("edges must be at least two strictly increasing values")
    lo, hi = energies[0], energies[-1]
    if edges[0] < lo * (1 - 1e-12) or edges[-1] > hi * (1 + 1e-12):
        raise ConvertError(f"edges [{edges[0]:g}, {edges[-1]:g}] leave the run's energy range [{lo:g}, {hi:g}] GeV/n")
    x, w = np.polynomial.legendre.leggauss(GL_NODES)
    out = []
    for a, b in zip(edges, edges[1:]):
        la, lb = math.log(a), math.log(b)
        pts = 0.5 * (lb - la) * x + 0.5 * (lb + la)
        vals = [_interp_log(energies, values, min(max(math.exp(p), lo), hi)) for p in pts]
        out.append(float(0.5 * sum(wi * v for wi, v in zip(w, vals))))
    return out


def parse_param(items: list[str]) -> dict:
    out = {}
    for it in items:
        if "=" not in it:
            raise ConvertError(f"--param {it!r} must read KEY=VALUE")
        k, v = it.split("=", 1)
        k = k.strip()
        if not k:
            raise ConvertError(f"--param {it!r} has an empty key")
        try:
            num = float(v)
            out[k] = num if math.isfinite(num) else v
        except ValueError:
            out[k] = v
    if not out:
        raise ConvertError("at least one --param is needed: the parameter point is the grid node")
    return out


def default_observable(numerator: list[str], denominator: list[str]) -> dict:
    return {
        "quantity": "ratio",
        "process": f"ratio of summed DRAGON2 local fluxes {'+'.join(numerator)} / {'+'.join(denominator)}",
        "phase_space": {"definition": "DRAGON2 local spectrum at the observer position, before solar modulation",
                        "fiducial": False},
        "normalization": {"kind": "exposure", "value": "not-applicable",
                          "convention": "ratio of two fluxes at the same E/n; the normalization cancels"},
        "frame": "Galactic rest frame (interstellar gas at rest)",
        "conventions": {
            "energy_variable": "kinetic energy per nucleon E/n in GeV/n (DRAGON2's energy grid), the ratio at equal E/n "
                               "of fluxes per E/n (DRAGON2's columns, per total kinetic energy, times A)",
            "frame": "Galactic rest frame (interstellar gas at rest); observer position as in the run's XML",
            "mass_approximation": "DRAGON2: beta and momentum per nucleon from E/n with the proton mass; rigidity "
                                  "(A/|Z|) times momentum per nucleon",
        },
    }


def build(args) -> dict:
    energies, cols = read_output(args.txt)
    num = [c.strip() for c in args.numerator.split(",") if c.strip()]
    den = [c.strip() for c in args.denominator.split(",") if c.strip()]
    if not num or not den:
        raise ConvertError("--numerator and --denominator need at least one column each")
    r = ratio(cols, num, den)
    point = parse_param(args.param)
    obs = default_observable(num, den)
    if args.observable:
        extra = json.loads(args.observable.read_text(encoding="utf-8"))
        if not isinstance(extra, dict):
            raise ConvertError("--observable must hold a JSON object")
        obs.update(extra)
    if args.level:
        obs["level"] = args.level
    if not isinstance(obs.get("level"), str) or not obs["level"]:
        raise ConvertError("an observable level is needed: --level or 'level' in --observable")
    if args.edges is not None:
        edges = _floats(args.edges, "--edges")
        values = bin_average(energies, r, edges)
        semantics = "bin-averaged"
        var = {"name": "kinetic_energy_per_nucleon", "unit": "GeV/n", "edges": edges}
        vals = {"edges": edges, "values": values, "unit": "1"}
        rng = [edges[0], edges[-1]]
        method = ("ratio averaged uniformly in ln(E/n) over each bin: 8-point Gauss-Legendre in ln(E/n) on ln(ratio) "
                  "interpolated linearly in ln(E/n) between DRAGON2 energy nodes")
    else:
        lo, hi = _floats(args.points, "--points")
        sel = [i for i, e in enumerate(energies) if lo <= e <= hi]
        if len(sel) < 1:
            raise ConvertError(f"no DRAGON2 energy node in [{lo:g}, {hi:g}] GeV/n")
        pts = [energies[i] for i in sel]
        values = [r[i] for i in sel]
        semantics = "point"
        var = {"name": "kinetic_energy_per_nucleon", "unit": "GeV/n", "points": pts}
        vals = {"points": pts, "values": values, "unit": "1"}
        rng = [pts[0], pts[-1]]
        method = "ratio at DRAGON2's own energy nodes (no interpolation)"
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ConvertError("the ratio is not finite and positive everywhere in the requested range")
    obs.update({"variables": [var], "bin_semantics": semantics, "unit": "1",
                "validity_range": {"variable": "kinetic_energy_per_nucleon", "min": rng[0], "max": rng[1],
                                   "unit": "GeV/n"}})
    obs.setdefault("conventions", {})
    inputs = []
    out_sha = hashlib.sha256(args.txt.read_bytes()).hexdigest()
    if args.run_record:
        rec = json.loads(args.run_record.read_text(encoding="utf-8"))
        hashes = (rec.get("extension") or {}).get("output_hashes") or {}
        if out_sha not in hashes.values():
            raise ConvertError(f"{args.txt.name}: its SHA-256 is not among the run record's output_hashes (not an "
                               "output of that run)")
        inputs.append({"ref": str(args.run_record.name), "artifact_type": "computational-run",
                       "artifact_id": rec.get("artifact_id"), "status": rec.get("status", []),
                       "sha256": hashlib.sha256(args.run_record.read_bytes()).hexdigest()})
        if "failed" in (rec.get("status") or []):
            raise ConvertError("the run record has status 'failed': its output is not a prediction")
    status = sorted(set(args.status or DEFAULT_STATUS))
    node = "-".join(f"{k}_{v:g}" if isinstance(v, float) else f"{k}_{v}" for k, v in point.items())
    doc = {
        "contract_version": "2.9.0",
        "artifact_id": args.artifact_id or f"dragon2-grid-node-{node}",
        "artifact_type": "prediction",
        "objective": f"one grid node of a DRAGON2 run ({args.txt.name}): {obs['process']}",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": "0.11.0", "contracts": "2.9.0", "profiles": {}},
        "provenance": {"producer_skill": "hep-computing", "created": _dt.date.today().isoformat(), "evidence_ids": []},
        "inputs": inputs, "outputs": [], "status": status, "unresolved_inputs": [],
        "extension": {
            "observable": obs,
            "derivation_status": "numerical-evidence",
            "parameter_point": point,
            "representation": "grid",
            "values": vals,
            "uncertainties": [],
            "allowed_transformations": [f"rebin (recompute from the run output: {method}; never merge averaged values)"],
        },
    }
    if args.theory_spec_ref:
        doc["extension"]["theory_spec_ref"] = args.theory_spec_ref
    return doc


def _floats(text: str, flag: str) -> list[float]:
    try:
        vals = [float(x) for x in text.split(",") if x.strip()]
    except ValueError as exc:
        raise ConvertError(f"{flag}: {exc}") from exc
    if flag == "--points" and len(vals) != 2:
        raise ConvertError("--points takes LOW,HIGH")
    return vals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--txt", required=True, type=Path)
    ap.add_argument("--numerator", required=True)
    ap.add_argument("--denominator", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--edges")
    g.add_argument("--points")
    ap.add_argument("--level")
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--observable", type=Path)
    ap.add_argument("--theory-spec-ref")
    ap.add_argument("--run-record", type=Path)
    ap.add_argument("--artifact-id")
    ap.add_argument("--status", action="append")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        import numpy  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "missing-dependency", "error": "numpy is needed for the Gauss-Legendre nodes"}))
        return 3
    try:
        doc = build(args)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "out": str(args.out), "artifact_id": doc["artifact_id"],
                      "n_values": len(doc["extension"]["values"]["values"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
