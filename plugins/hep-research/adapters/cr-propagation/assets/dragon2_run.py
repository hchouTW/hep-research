#!/usr/bin/env python3
"""Prepare and run one DRAGON2 propagation run from a JSON run spec, and record it as a computational-run artifact.

DRAGON2 (https://github.com/cosmicrays/DRAGON2-Beta_version) reads its input XML from the command line and its data
tables from ./data relative to the working directory, and writes ./output/<name>.txt (local spectra at the observer).
This script builds a run directory with that layout, never touching the DRAGON2 tree:

  <out>/<name>.xml            written from the spec (layout below)
  <out>/<name>.source.param   copied from --source-param (source abundances and injection slopes)
  <out>/data/                 one symlink per file of --data-dir; the production-cross-section table is replaced by a
                              file written from the spec's "production_table" when it is given
  <out>/output/<name>.txt     DRAGON2's ASCII output; <out>/dragon.log its stdout and stderr

Run spec (JSON; every key required unless marked optional):
  {"name": "run1",
   "grid": {"Rmax_kpc": 20, "DimR": 41, "L_kpc": 4, "dz_kpc": 0.02, "observer_kpc": [8.3, 0, 0],
            "Ekmin_GeV": 0.5, "Ekmax_GeV": 2000, "Ekfactor": 1.2, "Zmin": 5, "Zmax": 8},
   "diffusion": {"D0_1e28": 3.0, "DiffRefRig_GV": 1.0, "delta": 0.5, "etaT": 1.0},
   "galaxy": {"gas": "BronfFerr", "sources": {"type": "OneRing", "RingMin": 0, "RingMax": 20}},
   "flags": {"diff_flag": 1, "conv_flag": 0, "reacc_flag": 0, "eloss_flag": 0, "decay_flag": 0, "spall_flag": 1},
   "production_table": {"channels_mb": {"6012->5011": 70.0}, "grid_channel": "8016->6012"}   (optional)}
DimZ is 2 L / dz + 1 (equidistant z). Reacceleration and convection blocks are not written: with their flags at 0
they are off. "production_table" writes a DRAGON2-format table (parent and daughter as Z.AA, energy in MeV, sigma on
hydrogen in mb) with each listed channel at a constant value on the energy grid of the original table's grid channel;
that channel is written at 0 mb unless listed. Channels not listed are absent, so DRAGON2 sets them to zero. DRAGON2
still adds its helium-target term and uses its own inelastic cross sections, which no data file replaces.

Usage:
  python3 dragon2_run.py --spec SPEC.json --out RUNDIR [--dragon BIN] [--data-dir DIR] [--source-param FILE]
                         [--environment ENV.json] [--record RUN.json] [--program-version TEXT]
                         [--prepare-only] [--timeout SECONDS]
  --dragon defaults to $HEP_DRAGON2_BIN, --data-dir to $HEP_DRAGON2_DATA, --source-param to
  <data-dir>/../examples/BaseModel_DRAGONxsec.source.param. --environment is a manifest written by
  skills/hep-computing/scripts/environment_manifest.py record; its "environment" and "tools" are copied into the record.
  --record writes a computational-run artifact (input hashes, program and version, command, environment, output
  hashes, exit status); a failed run is recorded with status "failed".
Output: JSON with "status" ("ok", "prepared", "failed", "missing-dependency", "error"). Exit 0 ok (or prepared),
1 DRAGON2 failed or wrote no output, 2 bad input, 3 the DRAGON2 binary or data directory is missing.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PROGRAM = "DRAGON2"
TABLE_NAME = "crxsecs_fragmentation_Evoli2019_cumulative_modified.dat"
GRID_KEYS = ("Rmax_kpc", "DimR", "L_kpc", "dz_kpc", "observer_kpc", "Ekmin_GeV", "Ekmax_GeV", "Ekfactor", "Zmin", "Zmax")
DIFF_KEYS = ("D0_1e28", "DiffRefRig_GV", "delta", "etaT")
FLAG_KEYS = ("diff_flag", "conv_flag", "reacc_flag", "eloss_flag", "decay_flag", "spall_flag")


class SpecError(ValueError):
    """A run spec that cannot be turned into a DRAGON2 input."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _num(block: dict, key: str, where: str) -> float:
    val = block.get(key)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise SpecError(f"{where}.{key} must be a number")
    return float(val)


def check_spec(spec: dict) -> dict:
    """Validate the spec; return it with derived DimZ. Raises SpecError."""
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a JSON object")
    name = spec.get("name")
    if not isinstance(name, str) or not name or not all(c.isalnum() or c in "-_" for c in name):
        raise SpecError("name must be a non-empty string of letters, digits, '-' or '_'")
    for block, keys in (("grid", GRID_KEYS), ("diffusion", DIFF_KEYS), ("flags", FLAG_KEYS)):
        if not isinstance(spec.get(block), dict):
            raise SpecError(f"'{block}' must be an object")
        for k in keys:
            if k == "observer_kpc":
                obs = spec[block].get(k)
                if not (isinstance(obs, list) and len(obs) == 3 and all(isinstance(x, (int, float)) for x in obs)):
                    raise SpecError("grid.observer_kpc must be [x, y, z]")
            else:
                _num(spec[block], k, block)
    g = spec["grid"]
    if g["L_kpc"] <= 0 or g["dz_kpc"] <= 0 or g["Rmax_kpc"] <= 0:
        raise SpecError("L_kpc, dz_kpc and Rmax_kpc must be > 0")
    nz = 2.0 * g["L_kpc"] / g["dz_kpc"]
    if abs(nz - round(nz)) > 1e-9:
        raise SpecError("2 L / dz must be an integer")
    gal = spec.get("galaxy")
    if not isinstance(gal, dict) or not isinstance(gal.get("gas"), str) or not isinstance(gal.get("sources"), dict):
        raise SpecError("galaxy needs 'gas' (string) and 'sources' (object with 'type')")
    if not isinstance(gal["sources"].get("type"), str):
        raise SpecError("galaxy.sources.type must be a string")
    pt = spec.get("production_table")
    if pt is not None:
        ch = pt.get("channels_mb") if isinstance(pt, dict) else None
        if not isinstance(ch, dict) or not ch or not isinstance(pt.get("grid_channel"), str):
            raise SpecError("production_table needs 'channels_mb' (non-empty object) and 'grid_channel'")
        for key, val in ch.items():
            _uid_pair(key)
            if isinstance(val, bool) or not isinstance(val, (int, float)) or val < 0:
                raise SpecError(f"production_table.channels_mb[{key!r}] must be a number >= 0")
        _uid_pair(pt["grid_channel"])
    return dict(spec, DimZ=int(round(nz)) + 1)


def _uid_pair(key: str) -> tuple[int, int]:
    try:
        a, b = (int(x) for x in key.split("->"))
    except ValueError as exc:
        raise SpecError(f"channel {key!r} must read 'ZAAA->ZAAA' (1000 Z + A), e.g. '6012->5011'") from exc
    if a < 1001 or b < 1001:
        raise SpecError(f"channel {key!r}: uids are 1000 Z + A")
    return a, b


def _table_id(uid: int) -> str:
    """DRAGON2 table notation Z.AA (A < 100), e.g. 6012 -> '6.12'."""
    z, a = divmod(uid, 1000)
    if a >= 100:
        raise SpecError(f"mass number {a} cannot be written in the table's Z.AA notation")
    return f"{z}.{a:02d}"


def write_table(original: Path, target: Path, pt: dict) -> int:
    """Write the replacement production table; return the number of rows."""
    grid_p, grid_d = (_table_id(u) for u in _uid_pair(pt["grid_channel"]))
    energies = []
    with open(original, encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            parts = line.split()
            if len(parts) >= 3 and parts[0] == grid_p and parts[1] == grid_d:
                energies.append(parts[2])
    if not energies:
        raise SpecError(f"grid channel {pt['grid_channel']} not found in {original.name}")
    channels = dict(pt["channels_mb"])
    channels.setdefault(pt["grid_channel"], 0.0)
    # the grid channel first: DRAGON2 takes its energy grid from the 8.16 -> 6.12 rows
    order = [pt["grid_channel"]] + [k for k in channels if k != pt["grid_channel"]]
    rows = ['"   Parent    Daughter\tEnergy(MeV)\t\tXsecH(mb)\tXsexErr(mb)\tReference']
    for key in order:
        p, d = (_table_id(u) for u in _uid_pair(key))
        rows += [f"    {p}     {d}\t{e:>12}\t{float(channels[key]):12.6f}\t0.0000\t\tuser-spec" for e in energies]
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return len(rows) - 1


def render_xml(spec: dict) -> str:
    g, d, f, gal = spec["grid"], spec["diffusion"], spec["flags"], spec["galaxy"]
    src = dict(gal["sources"])
    src_type = src.pop("type")
    src_children = "".join(f'<{k} value="{v}" />' for k, v in src.items())
    flags = "\n".join(f'  <{k} value="{int(f[k])}" />' for k in FLAG_KEYS)
    x, y, z = g["observer_kpc"]
    return f"""<?xml version="1.0" ?>
<Output>
  <partialstore />
  <feedback value="1" />
</Output>
<Grid type="2D">
  <Observer>
    <x value="{x}" />
    <y value="{y}" />
    <z value="{z}" />
  </Observer>
  <Rmax value="{g['Rmax_kpc']}" />
  <L value="{g['L_kpc']}" />
  <DimR value="{int(g['DimR'])}" />
  <DimZ value="{spec['DimZ']}" />
  <Ekmin value="{g['Ekmin_GeV']}" />
  <Ekmax value="{g['Ekmax_GeV']}" />
  <Ekfactor value="{g['Ekfactor']}" />
  <NuclearChain>
    <Zmax value="{int(g['Zmax'])}" />
    <Zmin value="{int(g['Zmin'])}" />
  </NuclearChain>
</Grid>
<Algorithm>
  <OpSplit>
    <Nrept value="30" />
    <Dtfactor value=".25" />
    <Dtmin value="0.001" />
    <Dtmax value="64." />
  </OpSplit>
</Algorithm>
<Galaxy>
  <Gas type="{gal['gas']}" />
  <SNR type="{src_type}">{src_children}</SNR>
  <XCOmode type="SM96" />
  <Diffusion type="Constant">
    <D0_1e28 value="{d['D0_1e28']}" />
    <DiffRefRig value="{d['DiffRefRig_GV']}" />
    <Delta value="{d['delta']}" />
    <etaT value="{d['etaT']}" />
  </Diffusion>
  <CrossSection type="DRAGON2" leptopt="Kamae" apopt="Winkler" ApCs="2" />
  <MagneticField type="Pshirkov">
    <B0disk value="2.e-06" />
    <B0halo value="4.e-06" />
    <B0turb value="7.5e-06" />
  </MagneticField>
</Galaxy>
<Flags>
{flags}
</Flags>
<CR>
  <ProtNormEn_GeV value="53.645" />
  <ProtNormFlux value="2.57e-1" />
  <ElNormEn_GeV value="33." />
  <ElNormFlux value="0.0046" />
  <ElNormEnExtra_GeV value="20." />
  <ElNormFluxExtra value="2.3e-03" />
</CR>
"""


def prepare(spec: dict, out: Path, data_dir: Path, source_param: Path) -> dict:
    """Create the run directory; return the input files (path relative to out) that define the run."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "output").mkdir(exist_ok=True)
    data = out / "data"
    data.mkdir(exist_ok=True)
    name = spec["name"]
    (out / f"{name}.xml").write_text(render_xml(spec), encoding="utf-8")
    (out / f"{name}.source.param").write_bytes(source_param.read_bytes())
    for f in sorted(data_dir.iterdir()):
        link = data / f.name
        if link.is_symlink() or link.exists():
            link.unlink()
        if f.name == TABLE_NAME and spec.get("production_table"):
            write_table(f, link, spec["production_table"])
        else:
            link.symlink_to(f.resolve())
    inputs = [f"{name}.xml", f"{name}.source.param", f"data/{TABLE_NAME}"]
    return {p: sha256(out / p) for p in inputs if (out / p).exists()}


def record(args, spec, out: Path, inputs: dict, command: list[str], rc: int, outputs: dict, env: dict | None,
           seconds: float | None) -> dict:
    tools = [{"name": PROGRAM, "version": args.program_version,
              "binary": str(args.dragon), "binary_sha256": sha256(args.dragon) if args.dragon.is_file() else None}]
    environment = {}
    if env:
        environment = env.get("environment", {})
        tools += [t for t in env.get("tools", []) if t.get("name") != PROGRAM]
    failed = rc != 0 or not outputs
    return {
        "contract_version": "2.9.0", "artifact_id": f"dragon2-run-{spec['name']}", "artifact_type": "computational-run",
        "objective": f"DRAGON2 run '{spec['name']}' from a run spec (adapters/cr-propagation/assets/dragon2_run.py)",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": "0.11.0", "contracts": "2.9.0", "profiles": {}},
        "provenance": {"producer_skill": "hep-computing", "created": _dt.date.today().isoformat(), "evidence_ids": []},
        "inputs": [], "outputs": [], "unresolved_inputs": [],
        "status": ["failed"] if failed else ["unvalidated"],
        "extension": {
            "input_manifest": [{"path": p, "sha256": h} for p, h in inputs.items()],
            "tools": tools,
            "commands": [" ".join(command)],
            "environment": environment,
            "seeds": {"note": "DRAGON2 is deterministic: no random numbers are drawn"},
            "tolerances": {"note": "none applied by the run; DRAGON2 time-step schedule Dtmax 64 Myr to Dtmin 0.001 "
                                   "Myr, factor 0.25, 30 steps per level (written into the XML)"},
            "resources": {"wall_seconds": round(seconds, 1) if seconds is not None else None},
            "exit_status": rc,
            "output_hashes": outputs,
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dragon", type=Path, default=os.environ.get("HEP_DRAGON2_BIN"))
    ap.add_argument("--data-dir", type=Path, default=os.environ.get("HEP_DRAGON2_DATA"))
    ap.add_argument("--source-param", type=Path)
    ap.add_argument("--environment", type=Path)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--program-version", default=os.environ.get("HEP_DRAGON2_VERSION", "unknown"),
                    help="recorded in tools, e.g. 'git cd588707 (DRAGON 3.1.0 beta)'; default $HEP_DRAGON2_VERSION")
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--timeout", type=float, default=3600.0)
    args = ap.parse_args(argv)

    try:
        spec = check_spec(json.loads(args.spec.read_text(encoding="utf-8")))
        env = json.loads(args.environment.read_text(encoding="utf-8")) if args.environment else None
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    if args.data_dir is None or not Path(args.data_dir).is_dir():
        print(json.dumps({"status": "missing-dependency",
                          "error": "DRAGON2 data directory not found: pass --data-dir or set HEP_DRAGON2_DATA"}))
        return 3
    data_dir = Path(args.data_dir)
    source_param = args.source_param or data_dir.parent / "examples" / "BaseModel_DRAGONxsec.source.param"
    if not source_param.is_file():
        print(json.dumps({"status": "error", "error": f"source.param file not found: {source_param}"}))
        return 2
    try:
        inputs = prepare(spec, args.out, data_dir, source_param)
    except (OSError, SpecError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    if args.prepare_only:
        print(json.dumps({"status": "prepared", "run_dir": str(args.out), "inputs": inputs}))
        return 0
    if args.dragon is None or not Path(args.dragon).is_file() or not os.access(args.dragon, os.X_OK):
        print(json.dumps({"status": "missing-dependency",
                          "error": "DRAGON2 executable not found: pass --dragon or set HEP_DRAGON2_BIN"}))
        return 3
    args.dragon = Path(args.dragon).resolve()
    command = [str(args.dragon), f"{spec['name']}.xml"]
    t0 = time.monotonic()
    try:
        with open(args.out / "dragon.log", "w", encoding="utf-8") as log:
            rc = subprocess.run(command, cwd=args.out, stdout=log, stderr=subprocess.STDOUT,
                                timeout=args.timeout).returncode
    except subprocess.TimeoutExpired:
        rc = -1
    seconds = time.monotonic() - t0
    txt = args.out / "output" / f"{spec['name']}.txt"
    outputs = {f"output/{txt.name}": sha256(txt)} if rc == 0 and txt.is_file() else {}
    rec = record(args, spec, args.out, inputs, command, rc, outputs, env, seconds)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    ok = rc == 0 and bool(outputs)
    print(json.dumps({"status": "ok" if ok else "failed", "exit_status": rc, "run_dir": str(args.out),
                      "output": str(txt) if ok else None, "wall_seconds": round(seconds, 1),
                      "record": str(args.record) if args.record else None}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
