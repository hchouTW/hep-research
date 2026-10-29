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
   "production_table": {"channels_mb": {"6012->5011": 70.0}, "grid_channel": "8016->6012"}   (optional),
   "convection": {"v0_kms": 10.0, "dvdz_kmskpc": 0.0}                                          (optional),
   "reacceleration": {"type": "Ptuskin94", "vA_kms": 8.0}                                     (optional),
   "half_lives_s": {"4010": 4.377e13}                                                         (optional),
   "injection_gamma": 2.3                                                                     (optional),
   "substitutes": [...], "transport": {...}                                                   (optional, recorded only)}
DimZ is 2 L / dz + 1 (equidistant z). The Convection block (type Constant, f_b = 1, z_k 0.1 kpc: V_c = v0 + dvdz
(abs(z) - z_k) above z_k, v0 below) and the Reacceleration block are written only when given, and a flag conv_flag or
reacc_flag of 1 needs its block (DRAGON2 would otherwise read an unset speed); with the flags at 0 they are off.
"half_lives_s" replaces the half-life of the listed nuclei (1000 Z + A; both of DRAGON2's columns, naked and
H-like) in a copy of data/isotope_list.dat (DRAGON2 ships 10Be with 1.51 Myr). "injection_gamma" writes the
source.param with every injection slope (alpha_0, alpha_1, alpha_2) set to that value, so the injection is a single
power law in rigidity; the abundances are kept. "production_table" writes a DRAGON2-format table (parent and daughter as Z.AA, energy in MeV, sigma on
hydrogen in mb) with each listed channel at a constant value on the energy grid of the original table's grid channel;
that channel is written at 0 mb unless listed. Channels not listed are absent, so DRAGON2 sets them to zero. DRAGON2
still adds its helium-target term and uses its own inelastic cross sections, which no data file replaces.

Translator (spec_from_transport; --from-transport goes through dragon2_translate.spec_from_transport, which first
translates or refuses sources.abundances and the injection spectrum_variable, K3): a transport block (contracts
ext_theory_spec.transport, r3 5.4, the format of tests/adapters/fixtures/cr_propagation/specs/harmonized-v1*.json)
becomes a run spec, with every
item DRAGON2 cannot express recorded under "substitutes" (never dropped silently): diffusion D0_cm2_s, R0_gv, eta,
delta map one to one to D0_1e28, DiffRefRig_GV, etaT, Delta (DRAGON2 cd588707 diffusion.cc, type Constant: D0
beta^etaT (rho/DiffRefRig)^Delta); breaks are refused; V_A (thin disc: USINE's Seo-Ptuskin D_pp; whole halo:
constant 1) becomes DRAGON2's Ptuskin94 whole-halo V_A through hep-theory's transport_conventions.py reacceleration
(run as a subprocess; thin disc -> whole halo is V_A sqrt(4 h / L) to first order, approximate with the returned
bound, the destruction/escape ratio from escape_ratio_estimate unless given); losses switch eloss_flag and the gas to
Galprop (DRAGON2 cd588707's nuclear Coulomb loss diverges where n_HII = 0, as in BronfFerr: eloss.cc:118-120; losses
with BronfFerr are refused); decay switches decay_flag with
NUBASE2020 half-lives (core.constants.physical) for 10Be, 14C, 26Al, 36Cl, 54Mn in the charge range; the gas is
BronfFerr, or Galprop with losses (DRAGON2's "Uniform" gas is not implemented in this commit), with DRAGON2's fixed
helium (He/H 0.11) and its own inelastic cross sections; the sources are OneRing from 0 to the radial boundary.

Usage:
  python3 dragon2_run.py --spec SPEC.json --out RUNDIR [--dragon BIN] [--data-dir DIR] [--source-param FILE]
                         [--environment ENV.json] [--record RUN.json] [--program-version TEXT]
                         [--prepare-only] [--timeout SECONDS]
  python3 dragon2_run.py --from-transport ITEM.json --channels CHANNELS.json --name NAME --out RUNDIR [...]
  --from-transport: a JSON object with a "transport" block (and optional "network"); CHANNELS.json maps
      "ZAAA->ZAAA" to sigma in mb; the translated spec is written to RUNDIR/NAME.spec.json and then run like --spec.
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

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION  # noqa: E402
from core.constants.physical import half_life_seconds  # noqa: E402

PROGRAM = "DRAGON2"
TABLE_NAME = "crxsecs_fragmentation_Evoli2019_cumulative_modified.dat"
ISOTOPE_LIST = "isotope_list.dat"
# long-lived radioactive secondaries propagated explicitly (r3 P6); their NUBASE2020 half-lives replace DRAGON2's
EXPLICIT_DECAYS = {4010: "Be-10", 6014: "C-14", 13026: "Al-26", 17036: "Cl-36", 25054: "Mn-54"}
# reacceleration conventions of hep-theory's transport_conventions.py (A1R): a transport block's thin-disc V_A is
# USINE's Seo-Ptuskin D_pp (constant 4/3, w); DRAGON2 runs Ptuskin94 (constant 1) in the whole halo
CONVENTIONS = PLUGIN / "skills" / "hep-theory" / "scripts" / "transport_conventions.py"
REACCELERATION_SOURCE = {"thin-disc": "usine", "whole-halo": "whole-halo"}
REACCELERATION_TARGET = "dragon2-ptuskin94"
# DRAGON2 gas models the translator writes -> whether their HII density is positive (gas.cc: BronfFerr and NS write 0)
GAS_MODELS = {"BronfFerr": False, "Galprop": True}
GAS_NOTES = {"BronfFerr": "analytic HI and H2, HII 0",
             "Galprop": "DRAGON2's analytic GALPROP-like H2, HI and HII (TGas nH2_av, nHI_av, nHII_av)"}
ESCAPE_RATIO_N_H_CM3 = 1.0
ESCAPE_RATIO_SIGMA_MB = 310.0
# grid choices of the translator (recorded in the spec): radial step 0.5 kpc, vertical step 0.02 kpc, observer 8.3 kpc
TRANSLATOR_GRID = {"dR_kpc": 0.5, "dz_kpc": 0.02, "observer_kpc": [8.3, 0.0, 0.0], "Ekfactor": 1.2}
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
    f = spec["flags"]
    conv = spec.get("convection")
    if conv is not None:
        if not isinstance(conv, dict):
            raise SpecError("convection must be an object {'v0_kms', 'dvdz_kmskpc'}")
        for k in ("v0_kms", "dvdz_kmskpc"):
            if _num(conv, k, "convection") < 0:
                raise SpecError(f"convection.{k} must be >= 0")
    if int(f["conv_flag"]) and conv is None:
        raise SpecError("conv_flag 1 needs a 'convection' block (DRAGON2 would read an unset speed)")
    reacc = spec.get("reacceleration")
    if reacc is not None:
        if not isinstance(reacc, dict) or reacc.get("type") not in ("Ptuskin94", "Ptuskin03"):
            raise SpecError("reacceleration needs 'type' (Ptuskin94 or Ptuskin03) and 'vA_kms'")
        if _num(reacc, "vA_kms", "reacceleration") < 0:
            raise SpecError("reacceleration.vA_kms must be >= 0")
    if int(f["reacc_flag"]) and reacc is None:
        raise SpecError("reacc_flag 1 needs a 'reacceleration' block (DRAGON2 would read an unset speed)")
    hl = spec.get("half_lives_s")
    if hl is not None:
        if not isinstance(hl, dict) or not hl:
            raise SpecError("half_lives_s must be a non-empty object {'1000 Z + A': seconds}")
        for key, val in hl.items():
            if not (isinstance(key, str) and key.isdigit() and int(key) > 1000):
                raise SpecError(f"half_lives_s key {key!r} must be 1000 Z + A")
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not val > 0:
                raise SpecError(f"half_lives_s[{key!r}] must be a number > 0 (seconds)")
    gamma = spec.get("injection_gamma")
    if gamma is not None and (isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or not gamma > 0):
        raise SpecError("injection_gamma must be a number > 0")
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


def write_isotope_list(original: Path, target: Path, half_lives: dict) -> list[str]:
    """Copy DRAGON2's isotope list with the half-lives of `half_lives` ({'1000 Z + A': seconds}) in both columns
    (naked and H-like); return the uids replaced. Every listed uid must be in the file."""
    lines = original.read_text(encoding="utf-8").splitlines()
    wanted = {int(k): float(v) for k, v in half_lives.items()}
    done = []
    out = [lines[0]]
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 5 and parts[0].isdigit() and parts[1].isdigit():
            uid = 1000 * int(parts[1]) + int(parts[0])
            if uid in wanted:
                rest = " ".join(parts[4:])
                line = f"{parts[0]}\t{parts[1]}\t{wanted[uid]:.6e}\t{wanted[uid]:.6e}\t{rest}"
                done.append(str(uid))
        out.append(line)
    missing = sorted(set(map(str, wanted)) - set(done))
    if missing:
        raise SpecError(f"half_lives_s: {missing} not in {original.name}")
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    return sorted(done)


def source_param_text(original: Path, gamma: float | None) -> str:
    """The source.param text; with gamma, every injection slope (columns 3, 5, 7: alpha_0, alpha_1, alpha_2) set to
    gamma and the abundances and break rigidities kept."""
    text = original.read_text(encoding="utf-8")
    if gamma is None:
        return text
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0].isdigit():
            parts[2] = parts[4] = parts[6] = f"{gamma:g}"
            line = "\t".join(parts)
        rows.append(line)
    return "\n".join(rows) + "\n"


def _transport_blocks(spec: dict) -> str:
    """Convection and Reacceleration blocks of the Galaxy element (empty when the spec has neither)."""
    out = ""
    conv = spec.get("convection")
    if conv is not None:
        out += (f'\n  <Convection type="Constant">\n    <v0_kms value="{conv["v0_kms"]}" />\n'
                f'    <dvdz_kmskpc value="{conv["dvdz_kmskpc"]}" />\n    <z_k_kpc value="0.1" />\n'
                f'    <f_b value="1" />\n  </Convection>')
    reacc = spec.get("reacceleration")
    if reacc is not None:
        out += (f'\n  <Reacceleration type="{reacc["type"]}">\n    <vA_kms value="{reacc["vA_kms"]}" />\n'
                f'  </Reacceleration>')
    return out


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
  </Diffusion>{_transport_blocks(spec)}
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


def _block(transport: dict, key: str) -> dict:
    val = transport.get(key) or {}
    if not isinstance(val, dict):
        raise SpecError(f"transport.{key} must be an object")
    return val


def _tnum(block: dict, key: str, where: str, default: float | None = None) -> float:
    val = block.get(key, default)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        raise SpecError(f"transport.{where}.{key} must be a number")
    return float(val)


def escape_ratio_estimate(diffusion: dict, big_l: float, h_pc: float, ekn_gev: float) -> float:
    """lam = h Gamma L / D (destruction over escape) for the bound of transport_conventions' zone conversion: at the
    lowest E/n of the run, A/Z = 2, Gamma = n_H v sigma with n_H = ESCAPE_RATIO_N_H_CM3 (harmonized-v1's uniform gas)
    and sigma = ESCAPE_RATIO_SIGMA_MB (the largest inelastic cross section of the ILLUSTRATIVE sets), D = D0 beta^eta
    (R/R0)^delta. The largest lam over the run's energies, so the returned bound is conservative."""
    import math
    m = 0.938
    beta = math.sqrt(1.0 - (m / (ekn_gev + m)) ** 2)
    rig = 2.0 * math.sqrt(ekn_gev * (ekn_gev + 2 * m))
    d0 = float(diffusion["D0_cm2_s"])
    diff = d0 * beta ** float(diffusion.get("eta", 1.0)) * (rig / float(diffusion.get("R0_gv", 1.0))) ** float(
        diffusion["delta"])
    kpc_cm = 3.0856775814913673e21
    gamma = ESCAPE_RATIO_N_H_CM3 * beta * 2.99792458e10 * ESCAPE_RATIO_SIGMA_MB * 1e-27
    return h_pc * 1e-3 * kpc_cm * gamma * big_l * kpc_cm / diff


def convert_reacceleration(v_a: float, source: str, target: str, big_l: float, h_pc: float, lam: float) -> dict:
    """hep-theory's transport_conventions.py reacceleration, run as a subprocess (an adapter imports no skill, R1);
    its 'conversion' object."""
    cmd = [sys.executable, str(CONVENTIONS), "reacceleration", "--alfven-speed-km-s", repr(float(v_a)), "--from",
           source, "--to", target, "--l-kpc", repr(float(big_l)), "--disc-halfwidth-pc", repr(float(h_pc)),
           "--destruction-escape-ratio", repr(float(lam))]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    try:
        doc = json.loads(proc.stdout)
    except ValueError as exc:
        raise SpecError(f"transport_conventions.py reacceleration failed: {proc.stdout}{proc.stderr}") from exc
    if proc.returncode != 0 or "conversion" not in doc:
        raise SpecError(f"transport_conventions.py reacceleration refused: {doc}")
    return doc["conversion"]


def spec_from_transport(transport: dict, name: str, channels_mb: dict, *, z_range: tuple[int, int],
                        ekn_range_gev: tuple[float, float], grid_channel: str = "8016->6012",
                        destruction_escape_ratio: float | None = None, gas_model: str | None = None) -> dict:
    """A run spec from a transport block (r3 5.4 canonical names). Items DRAGON2 cannot express exactly are recorded
    in 'substitutes'; items it cannot express at all raise SpecError (never a silent default)."""
    if not isinstance(transport, dict):
        raise SpecError("transport must be an object")
    subs: list[str] = []
    geo, dif = _block(transport, "geometry"), _block(transport, "diffusion")
    if geo.get("kind", "cylinder-2d") != "cylinder-2d":
        raise SpecError(f"geometry.kind {geo.get('kind')!r}: the translator writes DRAGON2's 2D grid only")
    big_l, radius = _tnum(geo, "L_kpc", "geometry"), _tnum(geo, "radius_kpc", "geometry", 20.0)
    h_pc = _tnum(geo, "disc_halfwidth_pc", "geometry", 100.0)
    if dif.get("breaks"):
        raise SpecError("diffusion breaks: not translated (DRAGON2's single high break rho_b, Delta_h has another "
                        "form); compare predictions with a break instead")
    dr = TRANSLATOR_GRID["dR_kpc"]
    dim_r = radius / dr
    if abs(dim_r - round(dim_r)) > 1e-9:
        raise SpecError(f"radius_kpc {radius:g} must be a multiple of {dr:g} kpc (the translator's radial step)")
    if not big_l > 0:
        raise SpecError("geometry.L_kpc must be > 0")
    # the vertical step closest to the translator's that divides 2 L into whole cells
    dz = round(2.0 * big_l / max(1, round(2.0 * big_l / TRANSLATOR_GRID["dz_kpc"])), 12)
    lo, hi = ekn_range_gev
    if not 0 < lo < hi:
        raise SpecError("ekn_range_gev must be 0 < low < high")
    flags = {"diff_flag": 1, "conv_flag": 0, "reacc_flag": 0, "eloss_flag": 0, "decay_flag": 0, "spall_flag": 1}
    spec = {
        "name": name,
        "grid": {"Rmax_kpc": radius, "DimR": int(round(dim_r)) + 1, "L_kpc": big_l, "dz_kpc": dz,
                 "observer_kpc": list(TRANSLATOR_GRID["observer_kpc"]), "Ekmin_GeV": lo, "Ekmax_GeV": hi,
                 "Ekfactor": TRANSLATOR_GRID["Ekfactor"], "Zmin": int(z_range[0]), "Zmax": int(z_range[1])},
        "diffusion": {"D0_1e28": _tnum(dif, "D0_cm2_s", "diffusion") / 1e28,
                      "DiffRefRig_GV": _tnum(dif, "R0_gv", "diffusion", 1.0),
                      "delta": _tnum(dif, "delta", "diffusion"), "etaT": _tnum(dif, "eta", "diffusion", 1.0)},
        "galaxy": {"gas": "", "sources": {"type": "OneRing", "RingMin": 0, "RingMax": radius}},
        "flags": flags,
        "production_table": {"channels_mb": dict(channels_mb), "grid_channel": grid_channel},
    }
    subs.append(f"geometry.disc_halfwidth_pc {h_pc:g}: DRAGON2 has no thin-disc parameter; its gas has its own "
                "scale heights (BronfFerr: H2 59 pc, HI 115 pc at the observer)")
    gas = _block(transport, "gas")
    losses = transport.get("losses") or []
    if gas_model is None:
        gas_model = "Galprop" if losses else "BronfFerr"
    if gas_model not in GAS_MODELS:
        raise SpecError(f"gas_model {gas_model!r}: one of {sorted(GAS_MODELS)}")
    if losses and not GAS_MODELS[gas_model]:
        raise SpecError(f"losses with gas {gas_model}: its HII density is 0, and DRAGON2 cd588707's nuclear Coulomb "
                        "loss (eloss.cc:118-120, coullog = -log(... n_HII ...)/2) diverges there; use Galprop")
    spec["galaxy"]["gas"] = gas_model
    subs.append(f"gas {gas.get('model', 'unspecified')!r}: {gas_model} ({GAS_NOTES[gas_model]}); DRAGON2's 'Uniform' "
                "gas is not implemented in cd588707 (gas.cc writes -1)")
    subs.append(f"gas He_to_H_number {gas.get('He_to_H_number', 'unspecified')}: DRAGON2's fixed helium (He/H 0.11, "
                "constants.h) with its He_to_H_CS_ratio scaling of every production cross section")
    subs.append("sources.spatial: OneRing, uniform in R from 0 to the radial boundary (DRAGON2's z profile of the ring)")
    reacc = _block(transport, "reacceleration")
    v_a = _tnum(reacc, "V_A_kms", "reacceleration", 0.0)
    if v_a > 0:
        zone = reacc.get("zone", "whole-halo")
        if zone not in ("thin-disc", "whole-halo"):
            raise SpecError(f"reacceleration.zone {zone!r}: thin-disc or whole-halo")
        if float(reacc.get("w", 1.0)) != 1.0:
            raise SpecError("reacceleration.w other than 1 is not expressible in DRAGON2's Ptuskin94 form")
        lam = destruction_escape_ratio
        if lam is None:
            lam = escape_ratio_estimate(dif, big_l, h_pc, lo)
        conv_va = convert_reacceleration(v_a, REACCELERATION_SOURCE[zone], REACCELERATION_TARGET, big_l, h_pc, lam)
        v_halo = conv_va["result"]["V_A_kms"]
        bound = conv_va.get("relative_error_bound")
        subs.append(f"reacceleration V_A_kms {v_a:g} ({zone}, relation {reacc.get('relation', 'unspecified')!r}, "
                    f"convention {REACCELERATION_SOURCE[zone]}) -> DRAGON2 Ptuskin94 whole-halo V_A "
                    f"{v_halo:.6g} km/s by transport_conventions.py reacceleration (factor "
                    f"{conv_va['result']['factor']:.6g}, {conv_va['conversion_status']}, relative error bound "
                    f"{bound if bound is None else round(bound, 6)} with destruction/escape ratio {lam:.4g})")
        spec["reacceleration"] = {"type": "Ptuskin94", "vA_kms": round(v_halo, 6)}
        flags["reacc_flag"] = 1
    conv = _block(transport, "convection")
    v_c = _tnum(conv, "V_c_kms", "convection", 0.0)
    dvdz = _tnum(conv, "dVc_dz_kms_per_kpc", "convection", 0.0)
    if v_c < 0 or dvdz < 0:
        raise SpecError("convection speeds must be >= 0")
    if v_c > 0 or dvdz > 0:
        spec["convection"] = {"v0_kms": v_c, "dvdz_kmskpc": dvdz}
        flags["conv_flag"] = 1
        subs.append("convection: DRAGON2 Constant profile, V_c = v0 + dvdz (abs(z) - 0.1 kpc) above 0.1 kpc and v0 "
                    "below (f_b = 1)")
    if losses:
        if not set(losses) <= {"ionization", "coulomb", "adiabatic"}:
            raise SpecError(f"losses {losses}: only ionization, coulomb and adiabatic are translated")
        flags["eloss_flag"] = 1
        subs.append(f"losses {sorted(losses)}: eloss_flag 1 switches DRAGON2's ionization (neutral gas) and Coulomb "
                    "(HII) losses together (the adiabatic term follows dvdz only); the run uses Galprop gas because "
                    "DRAGON2's nuclear Coulomb loss diverges where n_HII = 0 (BronfFerr; VALIDATION CRPROP-D1)")
    decay = _block(transport, "decay")
    if decay.get("enabled"):
        flags["decay_flag"] = 1
        if decay.get("lorentz_dilation", True) is not True:
            raise SpecError("decay.lorentz_dilation false is not expressible (DRAGON2 dilates)")
        if decay.get("ec_treatment", "fully-stripped") != "fully-stripped":
            raise SpecError("decay.ec_treatment: DRAGON2 propagates fully stripped nuclei only")
        half = {}
        for uid, nuclide in EXPLICIT_DECAYS.items():
            if z_range[0] <= uid // 1000 <= z_range[1]:
                half[str(uid)] = half_life_seconds(nuclide)["value"]
        if half:
            spec["half_lives_s"] = half
            subs.append(f"decay half-lives of {sorted(half)}: NUBASE2020 (core.constants.physical), replacing "
                        "DRAGON2's isotope_list.dat values (10Be 1.51 Myr there)")
    inj = (_block(transport, "sources").get("injection") or [])
    gammas = {float(i["gamma"]) for i in inj if isinstance(i, dict) and "gamma" in i}
    if len(gammas) == 1 and not any(i.get("breaks") for i in inj if isinstance(i, dict)):
        spec["injection_gamma"] = gammas.pop()
    elif inj:
        raise SpecError("sources.injection: one slope without breaks is translated; give one gamma")
    subs.append("inelastic cross sections: DRAGON2's own parametrization (not replaceable through its data files)")
    spec["substitutes"] = subs
    spec["transport"] = transport
    return spec


def prepare(spec: dict, out: Path, data_dir: Path, source_param: Path) -> dict:
    """Create the run directory; return the input files (path relative to out) that define the run."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "output").mkdir(exist_ok=True)
    data = out / "data"
    data.mkdir(exist_ok=True)
    name = spec["name"]
    (out / f"{name}.xml").write_text(render_xml(spec), encoding="utf-8")
    (out / f"{name}.source.param").write_text(source_param_text(source_param, spec.get("injection_gamma")),
                                               encoding="utf-8")
    for f in sorted(data_dir.iterdir()):
        link = data / f.name
        if link.is_symlink() or link.exists():
            link.unlink()
        if f.name == TABLE_NAME and spec.get("production_table"):
            write_table(f, link, spec["production_table"])
        elif f.name == ISOTOPE_LIST and spec.get("half_lives_s"):
            write_isotope_list(f, link, spec["half_lives_s"])
        else:
            link.symlink_to(f.resolve())
    if spec.get("half_lives_s") and not (data / ISOTOPE_LIST).is_file():
        raise SpecError(f"half_lives_s given but {ISOTOPE_LIST} is not in the data directory")
    inputs = [f"{name}.xml", f"{name}.source.param", f"data/{TABLE_NAME}", f"data/{ISOTOPE_LIST}"]
    return {p: sha256(out / p) for p in inputs if (out / p).exists()}


def _plugin_version() -> str:
    try:
        return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


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
        "contract_version": CONTRACTS_VERSION, "artifact_id": f"dragon2-run-{spec['name']}",
        "artifact_type": "computational-run",
        "objective": f"DRAGON2 run '{spec['name']}' from a run spec (adapters/cr-propagation/assets/dragon2_run.py)",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": _plugin_version(), "contracts": CONTRACTS_VERSION, "profiles": {}},
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
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--spec", type=Path)
    src.add_argument("--from-transport", type=Path, help="JSON object with a 'transport' block (r3 5.4)")
    ap.add_argument("--channels", type=Path, help="with --from-transport: production channels {'ZAAA->ZAAA': mb}")
    ap.add_argument("--name", help="with --from-transport: the run name")
    ap.add_argument("--z-range", default="4,8", help="with --from-transport: Zmin,Zmax (default 4,8)")
    ap.add_argument("--ekn-range", default="0.04,2000", help="with --from-transport: Ekmin,Ekmax in GeV/n")
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
        if args.from_transport:
            if not (args.channels and args.name):
                raise SpecError("--from-transport needs --channels and --name")
            item = json.loads(args.from_transport.read_text(encoding="utf-8"))
            zr = tuple(int(x) for x in args.z_range.split(","))
            er = tuple(float(x) for x in args.ekn_range.split(","))
            if len(zr) != 2 or len(er) != 2:
                raise SpecError("--z-range and --ekn-range take two values")
            # through dragon2_translate's source checks (K3, escalation 12), as the provider: sources it cannot
            # express (injection per energy, abundances other than DRAGON2's own) are refused, never dropped
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import dragon2_translate
            channels = json.loads(args.channels.read_text(encoding="utf-8"))
            raw = dragon2_translate.spec_from_transport(item.get("transport") if isinstance(item, dict) else None,
                                                        args.name, channels, z_range=zr, ekn_range_gev=er)
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"{args.name}.spec.json").write_text(json.dumps(raw, indent=1) + "\n", encoding="utf-8")
        else:
            raw = json.loads(args.spec.read_text(encoding="utf-8"))
        spec = check_spec(raw)
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
