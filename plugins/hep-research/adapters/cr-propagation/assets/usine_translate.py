#!/usr/bin/env python3
"""Translate a cosmic-ray transport block into a USINE V3.5 run, run USINE, and record the run.

USINE (https://gitlab.com/dmaurin/USINE, GPL-2.0) is a separate program: this adapter never copies its source or its
shipped input files. It writes its own run directory and points USINE at the installation through HEP_USINE_BIN (the
'usine' executable) and HEP_USINE_DATA (USINE's 'inputs' folder: atomic properties, the nuclear chart, solar-system
abundances). The run directory holds only files written here:

  <run>/usine.init.par    USINE initialisation file (one 'group @ subgroup @ parameter @ M=0|1 @ value' per line)
  <run>/xs_production.dat production cross sections on hydrogen, every pair of the network (zero where the set has
                          no channel), USINE's straight-ahead table format, constant in energy (ILLUSTRATIVE sets)
  <run>/xs_inelastic.dat  inelastic cross sections on hydrogen of every species of the network, same format
  <run>/norm_points.dat   normalisation points of the parents (not data; below; ILLUSTRATIVE sets)
  <run>/out/              USINE's outputs: local_fluxes_<NAME>_Ekn_<model>_SolMod0DFF_phi0_00GV.out per species
                          (unmodulated local interstellar flux per E_k/n, (GeV/n m^2 s sr)^-1) and the log
  <run>/usine.log         stdout and stderr

Transport block (contracts ext_theory_spec.transport, r3 5.4, canonical names) to USINE:
- geometry.kind 'cylinder-2d' -> Model2DKisoVc (L = L_kpc, h = disc_halfwidth_pc / 1000, R = radius_kpc, rhole =
  local_bubble_radius_kpc, observer at r = OBSERVER_KPC); 'slab-1d' -> Model1DKisoVc (L, h, rhole; no radial
  boundary). Any other kind is refused.
- diffusion: K = beta^eta K0 (Rig/R0)^delta times one factor per break, with K0 = D0_cm2_s / KPC2_PER_MYR_CM2_S in
  kpc^2/Myr (IAU parsec, Julian year; r3 P1); s_convention 'usine' only. A low break (R_break_gv, delta_below, s)
  gives (1 + (R_break/Rig)^((delta - delta_below)/s))^s, the form of the plugin's convention table
  (transport_conventions.py). USINE's source fixes no form (K is a formula of the initialisation file) and its
  inputs/ files carry no low break; the initialisation files of Génolini et al. 2019 shipped in USINE V3.5's
  doc/DocFiles/2019-Génolini-benchmarks-BC.tar.gz (BIG, SLIM) write (1+(Rlow/Rig)^((deltalow+delta)/slow))^slow,
  the same form with deltalow = -delta_below (work package F1). A high break (R_break_gv, delta_above, s; work package B1X) gives
  (1 + (Rig/R_break)^((delta - delta_above)/s))^(-s), USINE V3.5's shipped K formula (inputs/init.TEST.par line 133,
  init.Model1D.par line 89, init.Model2D.par line 96: (1 + (Rig/Rbreak)^(Deltabreak/sbreak))^(-sbreak)) with
  Deltabreak = delta - delta_above.
- reacceleration: USINE reaccelerates in the thin disc only (r3 P1). zone 'thin-disc' passes V_A_kms unchanged;
  'whole-halo' is converted by transport_conventions.py reacceleration (subprocess; V_A sqrt(L/(3h)) at first order,
  approximate with the bound (1 + lam)/5 at the largest lam = h Gamma L / D over the run's species and energies,
  recorded; refused with USINE's own cross sections, whose inelastic files are not read). The momentum diffusion is the
  form of USINE V3.5's shipped initialisation files (inputs/init.TEST.par, Kpp of Model1DKisoVc and Model2DKisoVc),
  Kpp = (4/3) (V_A beta E_tot)^2 / (delta (4 - delta^2) (4 - delta) w K), with V_A in kpc/Myr (the IAU/Julian
  factor; with USINE's own inputs the factor 1.022712e-3 written in USINE's shipped Kpp, init.TEST.par line 134,
  recorded); the relation must name Seo-Ptuskin.
- convection: constant V_c_kms (Model1DKisoVc wind W0, Model2DKisoVc wind W1, vertical); a gradient
  dVc_dz_kms_per_kpc other than 0 is refused (USINE's KisoVc models have a constant wind).
- losses: 'ionization', 'coulomb', 'adiabatic' switch IsELossIon, IsELossCoulomb, IsELossAdiabatic; any other
  name is refused.
- decay.enabled: BETA decay and BETA-fed daughters on (rate ln 2 / (gamma t_1/2), USINE TUAxesCrE); ec_treatment
  'fully-stripped' keeps electron-capture nuclei stable (7Be, r3 P6, recorded), 'laboratory-half-life' decays them at
  the chart's half-life, ln 2 / (gamma t_1/2) (USINE src/TUAxesCrE.cc GammaRadEC_perMyr); the USINE chart's BETA
  half-lives of the network are checked against NUBASE2020 (core.constants.physical), never replaced
  (check_half_lives).
- gas: densities read from gas.model ('n_H = <number> cm^-3', or 'n_HI = .., n_HII = .., n_H2 = .. cm^-3'), in the
  thin disc; every density term needs its unit cm^-3 (a term without it is refused, never read as 0; a term not
  written at all is 0, recorded). With the ILLUSTRATIVE sets all neutral (HI = n_H; USINE's Coulomb loss, on HII, is then zero) and
  He_to_H_number recorded but not used (cross sections on hydrogen only; no helium cross section is invented). With
  USINE's own files He = He_to_H_number (HI + HII + 2 H2) and the targets are H and He.
- sources: one injection slope without breaks, dQ/dX = q beta^eta Rig^-gamma with X the item's spectrum_variable
  (harmonized-v1 states it; escalation 12): 'kinetic_energy_per_nucleon' or 'total_energy' give USINE's POWERLAW
  template per E_k/n with eta_s = eta, 'rigidity' gives eta_s = eta - 1 (dRig/dE_k/n = (A/|Z|)/beta; the constant A,
  A/|Z| is absorbed by the normalisation), exact; spectrum_variable not given: kinetic_energy_per_nucleon and eta 0
  when not given, both recorded; spatial distribution uniform in r up to radius_kpc (template CST) in the 2D model.
  sources.abundances: with the ILLUSTRATIVE sets only harmonized-v1's 'fixed by the parent list of
  theory:cr-secondary-ratio' (or none, recorded) is translated, any other text is refused; with USINE's own files
  only 'data-normalised ...' (below).
- cross sections and abundances, one of:
  (a) the ILLUSTRATIVE sets of theory:cr-secondary-ratio (ILLUSTRATIVE_SETS, equal to the profile's
      models/xs-illustrative-A.json and xs-illustrative-decay.json, checked by the adapter tests). Set A is
      element-level: C, O and B are placed on 12C, 16O and 11B (10B is in the network without production; it carries
      B's inelastic cross section). Parent abundances: USINE scales each parent's source until its unmodulated local
      flux at NORM_EKN_GEV equals the parent ratio of theory:cr-secondary-ratio (PARENT_RATIOS, O/C = 0.9), through
      its NormList and the generated norm_points.dat. species.network_top and species.isotopic must agree with the
      set (refused otherwise).
  (b) USINE's own files (work package B1X), named 'usine:<path under USINE's inputs folder>' in production_set and
      inelastic_set (e.g. 'usine:XS_NUCLEI/sigProdGALPROP17_OPT12.dat') and read in place from HEP_USINE_DATA, never
      copied (GPL-2.0); without HEP_USINE_DATA the run is refused (exit 3). The network is every nucleus of USINE's
      chart from 1H to species.network_top (e.g. 'Si-30'); sources.abundances 'data-normalised usine:<data file>
      <elements>:<experiment>@<E_k/n>[;...]' becomes USINE's NormList on that data file (source isotopic fractions
      from solar-system abundances with the FIP bias, kSSISOTFRAC, kSSISOTABUND, kFIPBIAS); network elements in no
      group are pure secondaries, and a trailing 'pure:<isotope>,...' (e.g. 'pure:13C,15N,17O,18O', as in the
      initialisation files of Génolini et al. 2019 shipped with USINE) makes isotopes of normalised elements pure
      secondaries too (work package F1).
  Any other set is refused (SpecError), never replaced.
- production modifiers (work package F1; USINE's own files only; run option, not a transport field): a channel
  '<A><el>+<H|He>-><A><el>' with norm, slope_le and threshold_ekn_gev is multiplied by norm and, below the threshold,
  by (E_k/n / threshold)^slope_le, the transformation of USINE V3.5's fit-mode XS parameters Norm, SlopeLE and EThresh
  (src/TUXSections.cc lines 3912-3921), here applied to the nodes of USINE's table and written to
  <run>/xs_production_modified.dat (that channel only; USINE replaces a reaction read again from a second fProd file,
  src/TUXSections.cc line 56). The file holds numbers computed from USINE's GPL-2.0 table: run directory only, never
  rendered into a fixture, listed in the record with derived_from_usine_inputs.
- solar modulation (work package F1; run option phi > 0): USINE's force field SolMod0DFF (Phi = |Z| phi / A per
  nucleon, Rig0 = 0.2 GV) applied per isotope by USINE ('usine -l' quantities at phi); the modulated isotope tables
  (local_fluxes_<NAME>_Ekn_<model>_SolMod0DFF_phi<phi>GV.out) are written next to the unmodulated ones (r3 P4: per
  isotope, before any ratio).
- tertiary chains, ghost nuclei, exotic primaries, antinuclei: off.
Every item USINE does not express exactly, every transport field the translator does not use (family, free,
sources.spatial, diffusion.form, ...) and every default it fills for a field left out is listed in the translation's
'substitutes'; a key it does not know is refused (work package B1X, acceptance B1X-4).

Energy grid: USINE's nuclear E_k/n grid is logarithmic with POINTS_PER_DECADE nodes per decade aligned on decades,
from below 0.8 times the lowest to above 1.25 times the highest E_k/n asked for, and always containing NORM_EKN_GEV;
--ekn-grid N,LOW,HIGH gives it explicitly (recorded).

Usage:
  python3 usine_translate.py translate --transport SPEC.json --name NAME --out RUNDIR --ekn-range LOW,HIGH
                                      [--data-dir DIR] [--points-per-decade N | --ekn-grid N,LOW,HIGH]
                                      [--phi GV] [--production-modifiers MODS.json]
  python3 usine_translate.py run --transport SPEC.json --name NAME --out RUNDIR --ekn-range LOW,HIGH
                                [--usine BIN] [--data-dir DIR] [--record RUN.json] [--timeout SECONDS]
                                [--points-per-decade N | --ekn-grid N,LOW,HIGH] [--phi GV]
                                [--production-modifiers MODS.json]
  SPEC.json is a transport block, or an object with a 'transport' key (a harmonized-v1 file). --usine defaults to
  $HEP_USINE_BIN and --data-dir to $HEP_USINE_DATA; USINE's own variable USINE is set to the installation folder (the
  parent of the executable's folder) for the run. 'translate' writes the run directory and translation.json without
  running; 'run' also runs USINE and writes a computational-run record (input and output hashes, version, command,
  wall time; a failed run is recorded with status failed). The record's input_manifest gives each generated file's
  sha256 as run (absolute paths inside usine.init.par) and committed_form_sha256 (written with the placeholders
  <TOOL_HOME>/inputs and <RUN_DIR>, the form committed as a fixture), plus USINE's own files read in place.
Output: JSON with "status" ("prepared", "ok", "failed", "missing-dependency", "error").
Exit codes: 0 ok (or prepared), 1 USINE failed or wrote no output, 2 bad input or a transport item USINE cannot
express, 3 the USINE executable or data folder (or a USINE file the transport names) is missing. USINE itself
returns exit status 1 on every path, so a run
is judged by its outputs and its log, never by its exit status.
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))
from core.constants.physical import half_life  # noqa: E402

PROGRAM = "USINE"
PROGRAM_VERSION = ("V3.5 (git tag V3.5, commit fb53006db41d1a640bf1b5af1a4b0f899ca59673; built with Apple clang 21.0.0 "
                   "against ROOT 6.38.04)")
CONTRACT_VERSION = "3.14.0"
PLUGIN_VERSION = "0.53.0"

# units (r3 P1): IAU 2012 parsec = 648000/pi au, au = 149 597 870 700 m; Julian year of 365.25 d
KPC_CM = 648000.0 / math.pi * 1.495978707e13 * 1e3
MYR_S = 1e6 * 365.25 * 86400.0
KPC2_PER_MYR_CM2_S = KPC_CM ** 2 / MYR_S
KPC_PER_MYR_PER_KM_S = 1e5 * MYR_S / KPC_CM
# km/s -> kpc/Myr factor of USINE V3.5's shipped Kpp formula (inputs/init.TEST.par line 134, Model1DKisoVc), as written
USINE_MOMENTUM_DIFFUSION_FACTOR = "1.022712e-3"

OBSERVER_KPC = 8.3  # galactocentric radius of the observer in the 2D model (the DRAGON2 adapter's observer position)
POINTS_PER_DECADE = 20
NORM_EKN_GEV = 10.0
HALF_LIFE_RTOL = 1e-3
N_BESSEL = 100  # Fourier-Bessel terms of Model2DKisoVc (USINE's shipped 2D example uses 9; see VALIDATION CRPROP-B1)
XS_GRID_GEV = (1.0e-3, 1.0e6)  # E_k/n range of the generated constant cross-section tables
CHART_FILE = "crcharts_Zmax30_ghost97.dat"
ATOMIC_FILE = "atomic_properties.dat"
SOLAR_FILE = "solarsystem_abundances2003.dat"
MODELS = {"cylinder-2d": "Model2DKisoVc", "slab-1d": "Model1DKisoVc"}
LOSS_SWITCHES = {"ionization": "IsELossIon", "coulomb": "IsELossCoulomb", "adiabatic": "IsELossAdiabatic"}
ELEMENTS = {1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N", 8: "O"}
PARENT_RATIOS = {"C": 1.0, "O": 0.9}  # theory:cr-secondary-ratio benchmarks/bc-benchmark.json, observed ratio to C

# The ILLUSTRATIVE cross-section sets of theory:cr-secondary-ratio (round placeholders, not data; mb on hydrogen),
# written onto USINE isotopes. Set A is element-level: its element names are placed on the isotopes of ISOTOPE_OF.
ILLUSTRATIVE_SETS = {
    "xs-illustrative-A": {
        "isotopic": False,
        "production_mb": {"C->B": 70.0, "O->B": 35.0},
        "inelastic_mb": {"B": 250.0, "C": 270.0, "O": 310.0},
        "isotope_of": {"C": ["12C"], "O": ["16O"], "B": ["10B", "11B"]},
        "secondary_isotope": {"B": "11B"},
    },
    "xs-illustrative-decay": {
        "isotopic": True,
        "production_mb": {"C->7Be": 10.0, "C->9Be": 6.0, "C->10Be": 4.0, "C->10B": 20.0, "C->11B": 50.0,
                          "O->7Be": 10.0, "O->9Be": 5.0, "O->10Be": 2.0, "O->10B": 10.0, "O->11B": 25.0},
        "inelastic_mb": {"7Be": 200.0, "9Be": 215.0, "10Be": 220.0, "10B": 240.0, "11B": 250.0, "C": 270.0,
                         "O": 310.0},
        "isotope_of": {"C": ["12C"], "O": ["16O"]},
        "secondary_isotope": {},
    },
}
NUCLIDE = re.compile(r"^(\d+)([A-Z][a-z]?)$")
GAS_TERM = re.compile(r"n_(HII|HI|H2|H)\s*=\s*([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*cm\^?-3")
# any density term, with or without its unit: a term GAS_TERM does not match is refused, never set to 0 (escalation 12)
GAS_TERM_ANY_UNIT = re.compile(r"n_(HII|HI|H2|H)\s*=\s*([-+0-9.eE]+)\s*([^\s,;)]*)")
# sources.injection[].spectrum_variable X of dQ/dX = q beta^eta Rig^-gamma -> the beta exponent added to eta for
# USINE's POWERLAW per E_k/n: dRig/dE_k/n = (A/|Z|)/beta and dE_tot/dE_k/n = A (constants per species, absorbed by the
# normalisation), so rigidity gives eta_s = eta - 1 and the per-energy variables eta_s = eta, exactly (escalation 12)
SPECTRUM_VARIABLE_ETA_SHIFT = {"kinetic_energy_per_nucleon": 0.0, "total_energy": 0.0, "rigidity": -1.0}
DEFAULT_SPECTRUM_VARIABLE = "kinetic_energy_per_nucleon"
# sources.abundances of the ILLUSTRATIVE sets: the parent list of theory:cr-secondary-ratio (harmonized-v1's text)
PARENT_LIST_ABUNDANCES = "fixed by the parent list of theory:cr-secondary-ratio"
# element symbols Z = 1..30 (USINE's charts stop at Zn) and USINE's own files named 'usine:<path>.dat'
SYMBOLS = ("H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K",
           "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn")
USINE_FILE = re.compile(r"usine:((?:[A-Za-z0-9_+.-]+/)*[A-Za-z0-9_+-][A-Za-z0-9_+.-]*\.dat)")
# isotopes tabulated in a run with USINE's own inputs: those of the reader's observables (B/C, 10Be/9Be, Be/B)
TABLED_ISOTOPES = ("7Be", "9Be", "10Be", "10B", "11B", "12C", "13C", "14C")


class SpecError(ValueError):
    """A transport block (or run request) that cannot be turned into a USINE run."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def charge_and_mass(nuclide: str) -> tuple[int, int]:
    """'10Be' -> (4, 10)."""
    m = NUCLIDE.match(nuclide)
    z = {v: k for k, v in ELEMENTS.items()}.get(m.group(2)) if m else None
    if z is None:
        raise SpecError(f"nuclide {nuclide!r}: expected '<A><element>' with Z <= 8, e.g. '10Be'")
    return z, int(m.group(1))


def usine_name(nuclide: str) -> str:
    """USINE's spelling in output file names: upper case ('10Be' -> '10BE')."""
    return nuclide.upper()


def _block(transport: dict, key: str) -> dict:
    val = transport.get(key) or {}
    if not isinstance(val, dict):
        raise SpecError(f"transport.{key} must be an object")
    return val


def _num(block: dict, key: str, where: str, default=None) -> float:
    val = block.get(key, default)
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(float(val)):
        raise SpecError(f"transport.{where}.{key} must be a finite number")
    return float(val)


def illustrative_set(name: str) -> tuple[str, dict]:
    for key, xs in ILLUSTRATIVE_SETS.items():
        if re.search(rf"(^|[/ ]){re.escape(key)}(\.json)?($|[ (])", name or ""):
            return key, xs
    raise SpecError(f"cross-section set {name!r}: this translator writes only the ILLUSTRATIVE sets of "
                    f"theory:cr-secondary-ratio ({', '.join(ILLUSTRATIVE_SETS)}); no other set is substituted")


def network(xs: dict) -> tuple[list[str], dict, dict]:
    """(isotopes from light to heavy, production channels 'P->C' -> mb, inelastic per isotope) on USINE isotopes."""
    def isotopes(name: str) -> list[str]:
        return xs["isotope_of"].get(name, [name])

    prod: dict[str, float] = {}
    for key, value in xs["production_mb"].items():
        parent, child = key.split("->")
        target = xs["secondary_isotope"].get(child, child)
        for p in isotopes(parent):
            prod[f"{p}->{target}"] = float(value)
    inel = {iso: float(v) for name, v in xs["inelastic_mb"].items() for iso in isotopes(name)}
    species = sorted({s for k in prod for s in k.split("->")} | set(inel),
                     key=lambda n: (charge_and_mass(n)[0], charge_and_mass(n)[1]))
    missing = [s for s in species if s not in inel]
    if missing:
        raise SpecError(f"no inelastic cross section for {missing} in the set")
    return species, prod, inel


def energy_grid(ekn_range_gev, points_per_decade: int = POINTS_PER_DECADE) -> dict:
    lo, hi = (float(x) for x in ekn_range_gev)
    if not 0 < lo < hi:
        raise SpecError("the E_k/n range must be 0 < low < high")
    n = int(points_per_decade)
    if n < 2:
        raise SpecError("points_per_decade must be at least 2")
    norm_k = round(n * math.log10(NORM_EKN_GEV))
    k_lo = min(math.floor(n * math.log10(0.8 * lo) + 1e-9), norm_k)
    k_hi = max(math.ceil(n * math.log10(1.25 * hi) - 1e-9), norm_k)
    return {"n_points": k_hi - k_lo + 1, "ekn_min_gev": 10.0 ** (k_lo / n), "ekn_max_gev": 10.0 ** (k_hi / n),
            "points_per_decade": n}


# keys the translator reads per block; any other key is refused (CRPROP-B1X, B1X-4: nothing is silently ignored)
TRANSPORT_KEYS = {
    "geometry": {"kind", "L_kpc", "radius_kpc", "disc_halfwidth_pc", "local_bubble_radius_kpc"},
    "diffusion": {"form", "D0_cm2_s", "R0_gv", "eta", "delta", "breaks"},
    "reacceleration": {"V_A_kms", "zone", "relation", "w"},
    "convection": {"V_c_kms", "dVc_dz_kms_per_kpc"},
    "decay": {"enabled", "lorentz_dilation", "ec_treatment"},
    "gas": {"model", "He_to_H_number"},
    "sources": {"spatial", "injection", "abundances"},
    "cross_sections": {"production_set", "inelastic_set", "ghost_threshold"},
    "species": {"network_top", "isotopic"},
}
TOP_KEYS = set(TRANSPORT_KEYS) | {"losses", "family", "free"}
BREAK_KEYS = {"low": {"kind", "R_break_gv", "delta_below", "s", "s_convention"},
              "high": {"kind", "R_break_gv", "delta_above", "s", "s_convention"}}
INJECTION_KEYS = {"species_group", "gamma", "eta", "breaks", "spectrum_variable"}
ELECTRON_CAPTURE_TREATMENTS = ("fully-stripped", "laboratory-half-life")


def _given(block: dict, key: str, where: str, default, defaults: list[str], unit: str = ""):
    """block[key], or default with a record in `defaults` (never a silent default)."""
    if key in block:
        return block[key]
    defaults.append(f"{where}.{key} = {default}{unit}")
    return default


def _check_keys(transport: dict) -> None:
    unknown = sorted(set(transport) - TOP_KEYS)
    if unknown:
        raise SpecError(f"transport keys {unknown} are not read by this translator; nothing is ignored silently")
    for block, keys in TRANSPORT_KEYS.items():
        extra = sorted(set(_block(transport, block)) - keys)
        if extra:
            raise SpecError(f"transport.{block} keys {extra} are not read by this translator")


def _nuclide(name: str, where: str) -> tuple[int, int]:
    """'Si-30' or '30Si' -> (14, 30), elements up to Zn (USINE's charts stop at Z = 30)."""
    m = re.fullmatch(r"([A-Z][a-z]?)-(\d+)", name or "") or re.fullmatch(r"(\d+)([A-Z][a-z]?)", name or "")
    if not m:
        raise SpecError(f"{where} {name!r}: expected '<element>-<A>' (e.g. 'Si-30')")
    sym, a = (m.group(1), m.group(2)) if not m.group(1).isdigit() else (m.group(2), m.group(1))
    if sym not in SYMBOLS:
        raise SpecError(f"{where} {name!r}: element beyond Z = 30 (USINE's nuclear charts stop at Zn)")
    return SYMBOLS.index(sym) + 1, int(a)


def usine_file(name: str, where: str) -> str:
    """'usine:XS_NUCLEI/x.dat' -> 'XS_NUCLEI/x.dat' (a file of USINE's inputs folder, read in place)."""
    m = USINE_FILE.fullmatch(name or "")
    if not m or ".." in m.group(1).split("/"):
        raise SpecError(f"{where} {name!r}: USINE's own files are named 'usine:<path under USINE's inputs folder>.dat'")
    return m.group(1)


def _gas(gas: dict, subs: list[str]) -> dict:
    """{'HI', 'HII', 'H2'} in cm^-3 from gas.model ('n_H = x cm^-3', or any of 'n_HI = x', 'n_HII = y', 'n_H2 = z')."""
    text = str(gas.get("model", ""))
    unitless = [f"n_{k} = {v}{(' ' + u) if u else ''}" for k, v, u in GAS_TERM_ANY_UNIT.findall(text)
                if not re.fullmatch(r"cm\^?-3", u)]
    if unitless:
        raise SpecError(f"gas.model {text!r}: density term(s) {unitless} without the unit cm^-3; give every density "
                        "as 'n_<H|HI|HII|H2> = <number> cm^-3' (a term without its unit is not read as 0)")
    parts = {k: float(v) for k, v in GAS_TERM.findall(text)}
    if set(parts) == {"H"}:
        return {"HI": parts["H"], "HII": 0.0, "H2": 0.0}
    if parts and "H" not in parts:
        dens = {k: parts.get(k, 0.0) for k in ("HI", "HII", "H2")}
        missing = [k for k in ("HI", "HII", "H2") if k not in parts]
        if missing:
            subs.append(f"gas.model {text!r}: {', '.join(missing)} not given, 0 cm^-3")
        return dens
    raise SpecError(f"gas.model {gas.get('model')!r}: give the density as 'n_H = <number> cm^-3' or as "
                    "'n_HI = <x> cm^-3, n_HII = <y> cm^-3, n_H2 = <z> cm^-3'")


def _abundances(text: str, elements: list[str]) -> tuple[str, list[tuple[list[str], str, float]], list[str]]:
    """'data-normalised usine:<file>.dat C,N,O:HEAO@10.6;H,He:PAMELA@20 [pure:13C,15N]' -> (file, [(elements,
    experiment, E_k/n)], [pure-secondary isotopes]). The optional 'pure:' list names isotopes of normalised elements
    that get no source (USINE PureSecondaries, e.g. 13C as in Génolini et al. 2019's initialisation files)."""
    m = re.fullmatch(r"data-normalised\s+(usine:\S+)\s+(\S+)(?:\s+pure:(\S+))?", (text or "").strip())
    if not m:
        raise SpecError(f"sources.abundances {text!r}: with USINE's own cross sections give "
                        "'data-normalised usine:<data file>.dat <elements>:<experiment>@<E_k/n in GeV/n>[;...] "
                        "[pure:<isotope>,...]'")
    groups, seen = [], set()
    for item in m.group(2).split(";"):
        g = re.fullmatch(r"([A-Z][a-z]?(?:,[A-Z][a-z]?)*):([A-Za-z0-9_-]+)@([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)", item)
        if not g:
            raise SpecError(f"sources.abundances group {item!r}: expected '<elements>:<experiment>@<E_k/n>'")
        names = g.group(1).split(",")
        bad = [e for e in names if e not in elements or e in seen]
        if bad:
            raise SpecError(f"sources.abundances: {bad} not in the network {elements[0]}-{elements[-1]} or "
                            "listed twice")
        seen.update(names)
        groups.append((names, g.group(2), float(g.group(3))))
    pure_isotopes = []
    for iso in (m.group(3) or "").split(",") if m.group(3) else []:
        z, a = _nuclide(iso, "sources.abundances pure")
        if SYMBOLS[z - 1] not in seen:
            raise SpecError(f"sources.abundances pure {iso!r}: its element is not normalised to data (an element in no "
                            "group is already a pure secondary)")
        pure_isotopes.append(f"{a}{SYMBOLS[z - 1]}")
    return usine_file(m.group(1), "sources.abundances"), groups, pure_isotopes


def explicit_grid(grid: dict) -> dict:
    try:
        n, lo, hi = int(grid["n_points"]), float(grid["ekn_min_gev"]), float(grid["ekn_max_gev"])
    except (KeyError, TypeError, ValueError):
        raise SpecError("energy grid: give n_points, ekn_min_gev and ekn_max_gev") from None
    if n < 2 or not 0 < lo < hi:
        raise SpecError("energy grid: n_points >= 2 and 0 < ekn_min_gev < ekn_max_gev")
    return {"n_points": n, "ekn_min_gev": lo, "ekn_max_gev": hi, "points_per_decade": None}


CONVENTIONS_SCRIPT = PLUGIN_ROOT / "skills" / "hep-theory" / "scripts" / "transport_conventions.py"
LIGHT_CM_S = 2.99792458e10
NUCLEON_MASS_GEV = 0.9314941  # atomic mass unit in GeV: per-nucleon mass for the lam bound only
MB_CM2 = 1e-27


def destruction_escape_max(spec: dict, d0_cm2_s: float, h_kpc: float, l_kpc: float) -> tuple[float, str, float]:
    """(largest lam, nuclide, E_k/n in GeV/n) of lam = h Gamma L / D over the run's species and energy grid
    (transport_conventions.convert_reacceleration's destruction over escape): Gamma = n_gas sigma_inel beta c on the
    run's gas (HI + HII + 2 H2) with the set's inelastic cross sections, D = D0 beta^eta (R/R0)^delta times the break
    factors of the K formula. Masses per nucleon are the atomic mass unit (a bound, not a prediction)."""
    p, g = spec["transport_pars"], spec["energy_grid"]
    n_gas = spec["gas_cm3"]["HI"] + spec["gas_cm3"]["HII"] + 2.0 * spec["gas_cm3"]["H2"]
    n = g["n_points"]
    nodes = [g["ekn_min_gev"] * (g["ekn_max_gev"] / g["ekn_min_gev"]) ** (i / (n - 1)) for i in range(n)]
    best = (0.0, "", 0.0)
    for nuc in spec["species"]:
        z, a = charge_and_mass(nuc)
        for ekn in nodes:
            gamma = 1.0 + ekn / NUCLEON_MASS_GEV
            beta = math.sqrt(1.0 - 1.0 / gamma ** 2)
            rig = a / z * math.sqrt(ekn * (ekn + 2.0 * NUCLEON_MASS_GEV))
            diff = d0_cm2_s * beta ** p["eta_t"] * (rig / p["R0"]) ** p["delta"]
            for key in sorted(k for k in p if k[:2] in ("Rl", "Rh")):
                i = key[2:]
                if key[:2] == "Rl":
                    diff *= (1 + (p[key] / rig) ** ((p["delta"] - p[f"dl{i}"]) / p[f"sl{i}"])) ** p[f"sl{i}"]
                else:
                    diff *= (1 + (rig / p[key]) ** ((p["delta"] - p[f"dh{i}"]) / p[f"sh{i}"])) ** (-p[f"sh{i}"])
            rate = n_gas * spec["inelastic_mb"][nuc] * MB_CM2 * beta * LIGHT_CM_S
            lam = h_kpc * KPC_CM * rate * l_kpc * KPC_CM / diff
            if lam > best[0]:
                best = (lam, nuc, ekn)
    return best


def thin_disc_alfven_speed(v_a_halo: float, l_kpc: float, h_kpc: float, w: float, lam: float) -> dict:
    """Whole-halo V_A to USINE's thin disc with the same D_pp constant and w, by the hep-theory conversion
    (transport_conventions.py reacceleration, called as a subprocess, r3 R1; work package A1R): its 'conversion'
    (V_A sqrt(L/(3h)) at first order, approximate with bound (1 + lam)/5 on the second-order term)."""
    cmd = [sys.executable, str(CONVENTIONS_SCRIPT), "reacceleration", "--alfven-speed-km-s", repr(v_a_halo),
           "--from", "whole-halo", "--to", "thin-disc", "--l-kpc", repr(l_kpc), "--disc-halfwidth-pc",
           repr(h_kpc * 1000.0), "--destruction-escape-ratio", repr(lam), "--w-from", repr(w), "--w-to", repr(w)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    try:
        out = json.loads(proc.stdout)["conversion"]
    except (ValueError, KeyError):
        raise SpecError(f"reacceleration zone conversion failed (transport_conventions.py exit {proc.returncode}): "
                        f"{(proc.stdout + proc.stderr)[-300:]}") from None
    if proc.returncode != 0 or out.get("conversion_status") not in ("exact", "approximate"):
        raise SpecError(f"reacceleration zone conversion refused: {out.get('reason')}")
    return out


def translate(transport: dict, name: str, ekn_range_gev, points_per_decade: int = POINTS_PER_DECADE,
              grid: dict | None = None, phi_gv: float = 0.0, production_modifiers: list | None = None,
              tolerances: dict | None = None) -> dict:
    """The run spec of one USINE run (pure data, no path). Items USINE expresses only approximately, and defaults the
    transport block leaves to the translator, are listed in 'substitutes'; items it cannot express raise SpecError.
    grid ({'n_points', 'ekn_min_gev', 'ekn_max_gev'}) replaces the derived energy grid. phi_gv > 0 asks USINE for the
    force-field modulated isotope fluxes as well (solar_modulation); production_modifiers (USINE's own cross sections
    only) rescale production channels as USINE's fit mode does (production_modifier)."""
    if not isinstance(transport, dict):
        raise SpecError("transport must be an object")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", name):
        raise SpecError("name: 1-80 letters, digits, '-' or '_'")
    _check_keys(transport)
    subs: list[str] = []
    defaults: list[str] = []
    geo, dif = _block(transport, "geometry"), _block(transport, "diffusion")
    kind = _given(geo, "kind", "geometry", "cylinder-2d", defaults)
    if kind not in MODELS:
        raise SpecError(f"geometry.kind {kind!r}: the translator writes {sorted(MODELS)} only")
    model = MODELS[kind]
    big_l = _num(geo, "L_kpc", "geometry")
    h_pc = _num(geo, "disc_halfwidth_pc", "geometry", _given(geo, "disc_halfwidth_pc", "geometry", 100.0, defaults,
                                                                " pc"))
    if big_l <= 0 or h_pc <= 0:
        raise SpecError("geometry.L_kpc and geometry.disc_halfwidth_pc must be > 0")
    h_kpc = h_pc / 1000.0
    rhole = _num(geo, "local_bubble_radius_kpc", "geometry",
                 _given(geo, "local_bubble_radius_kpc", "geometry", 0.0, defaults, " kpc (no local bubble)"))
    if rhole < 0:
        raise SpecError("geometry.local_bubble_radius_kpc must be >= 0")
    geometry = {"L": big_l, "h": h_kpc, "rhole": rhole}
    if model == "Model2DKisoVc":
        radius = _num(geo, "radius_kpc", "geometry", _given(geo, "radius_kpc", "geometry", 20.0, defaults, " kpc"))
        if radius <= OBSERVER_KPC:
            raise SpecError(f"geometry.radius_kpc must exceed the observer radius {OBSERVER_KPC} kpc")
        geometry["R"] = radius
        subs.append(f"observer at r = {OBSERVER_KPC} kpc, z = 0 (not fixed by the transport block); no central hole")
    elif "radius_kpc" in geo:
        subs.append(f"geometry.radius_kpc {geo['radius_kpc']}: not used, the 1D model has no radial boundary")
    if rhole > 0:
        subs.append(f"local bubble of radius {rhole:g} kpc (USINE rhole): USINE damps BETA-unstable fluxes in the disc "
                    "only (valid at z = 0)")

    d0 = _num(dif, "D0_cm2_s", "diffusion")
    if d0 <= 0:
        raise SpecError("diffusion.D0_cm2_s must be > 0")
    pars = {"Va": 0.0, "Vc": 0.0, "K0": d0 / KPC2_PER_MYR_CM2_S, "delta": _num(dif, "delta", "diffusion"),
            "eta_t": _num(dif, "eta", "diffusion", _given(dif, "eta", "diffusion", 1.0, defaults)),
            "R0": _num(dif, "R0_gv", "diffusion", _given(dif, "R0_gv", "diffusion", 1.0, defaults, " GV"))}
    if pars["R0"] <= 0:
        raise SpecError("diffusion.R0_gv must be > 0")
    if "form" in dif:
        subs.append(f"diffusion.form {dif['form']!r}: not parsed; K = beta^eta K0 (Rig/R0)^delta times the break "
                    "factors is fixed by the canonical fields")
    k_formula = "beta^eta_t*K0*(Rig/R0)^delta"
    breaks = _given(dif, "breaks", "diffusion", [], defaults, " (no break)") or []
    if not isinstance(breaks, list):
        raise SpecError("diffusion.breaks must be a list")
    kinds = []
    for i, brk in enumerate(breaks, start=1):
        where = f"diffusion.breaks[{i - 1}]"
        bkind = brk.get("kind") if isinstance(brk, dict) else None
        if bkind not in BREAK_KEYS:
            raise SpecError(f"{where}: kind 'low' or 'high' with s_convention 'usine' is translated")
        if set(brk) - BREAK_KEYS[bkind]:
            raise SpecError(f"{where}: {sorted(set(brk) - BREAK_KEYS[bkind])} do not belong to a {bkind} break")
        if _given(brk, "s_convention", where, "usine", defaults) != "usine":
            raise SpecError(f"{where}: only s_convention 'usine' is translated")
        slope = "delta_below" if bkind == "low" else "delta_above"
        r_b, d_b, s_b = (_num(brk, k, where) for k in ("R_break_gv", slope, "s"))
        if r_b <= 0 or s_b <= 0:
            raise SpecError(f"{where}: R_break_gv and s must be > 0")
        if bkind == "low":
            pars.update({f"Rl{i}": r_b, f"dl{i}": d_b, f"sl{i}": s_b})
            k_formula += f"*(1+(Rl{i}/Rig)^((delta-dl{i})/sl{i}))^sl{i}"
        else:
            pars.update({f"Rh{i}": r_b, f"dh{i}": d_b, f"sh{i}": s_b})
            k_formula += f"*(1+(Rig/Rh{i})^((delta-dh{i})/sh{i}))^(-sh{i})"
        kinds.append(bkind)
    if "low" in kinds:
        subs.append("low break form (1 + (R_break/Rig)^((delta - delta_below)/s))^s of the plugin's 'usine' convention "
                    "(transport_conventions.py), the K formula of the BIG and SLIM initialisation files of Génolini et "
                    "al. 2019 shipped with USINE V3.5 (doc/DocFiles/2019-Génolini-benchmarks-BC.tar.gz: "
                    "(1+(Rlow/Rig)^((deltalow+delta)/slow))^slow) with deltalow = -delta_below")
    if "high" in kinds:
        subs.append("high break form (1 + (Rig/R_break)^((delta - delta_above)/s))^(-s): USINE V3.5's shipped K "
                    "formula (inputs/init.TEST.par line 133) with Deltabreak = delta - delta_above")

    reacc = _block(transport, "reacceleration")
    v_a = _num(reacc, "V_A_kms", "reacceleration", _given(reacc, "V_A_kms", "reacceleration", 0.0, defaults,
                                                          " km/s"))
    w = _num(reacc, "w", "reacceleration", _given(reacc, "w", "reacceleration", 1.0, defaults))
    if v_a < 0 or w <= 0:
        raise SpecError("reacceleration.V_A_kms must be >= 0 and w > 0")
    if v_a > 0:
        zone = _given(reacc, "zone", "reacceleration", "thin-disc", defaults)
        if zone not in ("thin-disc", "whole-halo"):
            raise SpecError(f"reacceleration.zone {zone!r}: thin-disc or whole-halo")
        relation = str(_given(reacc, "relation", "reacceleration", "Seo-Ptuskin 1994", defaults))
        if "seo" not in relation.lower():
            raise SpecError(f"reacceleration.relation {reacc.get('relation')!r}: only Seo-Ptuskin is translated")
        subs.append(f"reacceleration.relation {relation!r}: momentum diffusion Kpp of USINE's shipped files "
                    "(Seo-Ptuskin form)")
    elif set(reacc) & {"zone", "relation"}:
        subs.append("reacceleration off (V_A = 0): " + ", ".join(f"{k} {reacc[k]!r}" for k in ("zone", "relation")
                                                                if k in reacc) + " not used")
    pars["Va"] = round(v_a, 9)
    pars["w"] = w
    conv = _block(transport, "convection")
    v_c = _num(conv, "V_c_kms", "convection", _given(conv, "V_c_kms", "convection", 0.0, defaults, " km/s"))
    if v_c < 0:
        raise SpecError("convection.V_c_kms must be >= 0")
    if _num(conv, "dVc_dz_kms_per_kpc", "convection",
            _given(conv, "dVc_dz_kms_per_kpc", "convection", 0.0, defaults, " km/s/kpc")) != 0.0:
        raise SpecError("convection.dVc_dz_kms_per_kpc: USINE's KisoVc models have a constant wind; no gradient")
    pars["Vc"] = v_c

    switches = {"IsDecayBETA": False, "IsDecayFedBETA": False, "IsDecayEC": False, "IsDecayFedEC": False,
                "IsDestruction": True, "IsELossAdiabatic": False, "IsELossBremss": False, "IsELossCoulomb": False,
                "IsELossIC": False, "IsELossIon": False, "IsELossSynchrotron": False, "IsEReacc": v_a > 0,
                "IsPrimExotic": False, "IsPrimStandard": True, "IsSecondaries": True, "IsTertiaries": False,
                "IsWind": v_c > 0}
    losses = _given(transport, "losses", "transport", [], defaults, " (no energy losses)")
    if not isinstance(losses, list) or not set(losses) <= set(LOSS_SWITCHES):
        raise SpecError(f"losses {losses}: only {sorted(LOSS_SWITCHES)} are translated")
    for loss in losses:
        switches[LOSS_SWITCHES[loss]] = True
    if "adiabatic" in losses and v_c == 0:
        subs.append("adiabatic losses with V_c = 0: USINE's adiabatic term (proportional to V_c/h) vanishes")
    decay = _block(transport, "decay")
    if _given(decay, "enabled", "decay", False, defaults, " (no decay)"):
        if _given(decay, "lorentz_dilation", "decay", True, defaults) is not True:
            raise SpecError("decay.lorentz_dilation false: USINE's decay rate is ln 2 / (gamma t_1/2)")
        ec = _given(decay, "ec_treatment", "decay", "fully-stripped", defaults)
        if ec not in ELECTRON_CAPTURE_TREATMENTS:
            raise SpecError(f"decay.ec_treatment {ec!r}: only {list(ELECTRON_CAPTURE_TREATMENTS)} are translated")
        switches.update(IsDecayBETA=True, IsDecayFedBETA=True)
        if ec == "fully-stripped":
            subs.append("electron-capture decay off: fully stripped nuclei (7Be) are stable (r3 P6)")
        else:
            switches.update(IsDecayEC=True, IsDecayFedEC=True)
            subs.append("electron-capture decay on at the laboratory half-life of USINE's chart, rate ln 2 / (gamma "
                        "t_1/2) (USINE V3.5 src/TUAxesCrE.cc GammaRadEC_perMyr); electron attachment and stripping are "
                        "not modelled (r3 P6)")
    elif set(decay) & {"lorentz_dilation", "ec_treatment"}:
        subs.append("decay off: " + ", ".join(f"{k} {decay[k]!r}" for k in ("lorentz_dilation", "ec_treatment")
                                              if k in decay) + " not used")

    xs_block = _block(transport, "cross_sections")
    prod_name = str(xs_block.get("production_set", ""))
    inel_name = str(_given(xs_block, "inelastic_set", "cross_sections", prod_name, defaults, " (the production set)"))
    usine_xs = prod_name.startswith("usine:") or inel_name.startswith("usine:")
    if "ghost_threshold" in xs_block:
        subs.append(f"cross_sections.ghost_threshold {xs_block['ghost_threshold']!r}: not parsed; ghost nuclei are not "
                    f"loaded (IsLoadGhosts false; the cumulative cross sections of USINE's chart {CHART_FILE}) and "
                    "tertiary chains are off")
    species_block = _block(transport, "species")
    src = _block(transport, "sources")
    inj = src.get("injection") or []
    if not isinstance(inj, list) or any(not isinstance(i, dict) or set(i) - INJECTION_KEYS for i in inj):
        raise SpecError(f"sources.injection: a list of objects with {sorted(INJECTION_KEYS)}")
    gammas = {float(i["gamma"]) for i in inj if "gamma" in i}
    etas = {float(i["eta"]) for i in inj if "eta" in i}
    if len(gammas) != 1 or len(etas) > 1 or any(i.get("breaks") for i in inj):
        raise SpecError("sources.injection: one slope without breaks is translated; give one gamma (and at most one "
                        "eta)")
    gamma = gammas.pop()
    eta = etas.pop() if etas else 0.0
    variables = {i["spectrum_variable"] for i in inj if "spectrum_variable" in i}
    if len(variables) > 1 or not variables <= set(SPECTRUM_VARIABLE_ETA_SHIFT):
        raise SpecError(f"sources.injection spectrum_variable {sorted(map(str, variables))}: one of "
                        f"{sorted(SPECTRUM_VARIABLE_ETA_SHIFT)} for every item")
    variable = variables.pop() if variables else _given({}, "spectrum_variable", "sources.injection",
                                                        DEFAULT_SPECTRUM_VARIABLE, defaults,
                                                        " (USINE's POWERLAW is a density per E_k/n)")
    eta_s = eta + SPECTRUM_VARIABLE_ETA_SHIFT[variable]
    groups = [str(i["species_group"]) for i in inj if "species_group" in i]
    if groups:
        subs.append(f"sources.injection species_group {groups}: one slope for every primary of the network")
    if "spatial" in src:
        subs.append(f"sources.spatial {src['spatial']!r}: not parsed; "
                    + ("uniform in r up to radius_kpc in the thin disc (template CST)" if model == "Model2DKisoVc"
                       else "the 1D model's sources fill the thin disc"))
    common = {"name": name, "program": PROGRAM, "model": model, "geometry": geometry, "transport_pars": pars,
              "K_formula": k_formula,
              "energy_grid": explicit_grid(grid) if grid else energy_grid(ekn_range_gev, points_per_decade),
              "n_bessel": N_BESSEL, "observer_kpc": OBSERVER_KPC if model == "Model2DKisoVc" else None,
              "switches": switches}
    gas = _block(transport, "gas")
    dens = _gas(gas, subs)
    he_ratio = gas.get("He_to_H_number")
    if usine_xs:
        mode = _usine_inputs(transport, xs_block, prod_name, inel_name, species_block, src, dens, he_ratio, subs,
                             defaults)
    else:
        mode = _illustrative(transport, xs_block, prod_name, inel_name, species_block, src, dens, he_ratio, subs,
                             defaults)
    late = mode.pop("_late_notes")
    spec = dict(common, **mode)
    if v_a > 0 and reacc.get("zone", "thin-disc") == "whole-halo":
        if usine_xs:
            raise SpecError("reacceleration.zone whole-halo with USINE's own cross sections: the zone conversion needs "
                            "lam = h Gamma L / D, and the translator does not read USINE's inelastic files; give the "
                            "thin-disc V_A")
        lam, nuc, ekn = destruction_escape_max(spec, d0, h_kpc, big_l)
        conv_out = thin_disc_alfven_speed(v_a, big_l, h_kpc, w, lam)
        disc = conv_out["result"]["V_A_kms"]
        subs.append(f"reacceleration V_A_kms {v_a:g} in the whole halo: thin-disc V_A = {disc:.6g} km/s (factor "
                    f"{conv_out['result']['factor']:.6g} = sqrt(L/(3h)), transport_conventions.py reacceleration, same "
                    f"c and w); {conv_out['conversion_status']}, relative_error_bound "
                    f"{conv_out['relative_error_bound']:.4g} = (1 + lam)/5 on the second-order term in V_A^2 of the disc flux, with lam = h Gamma L / D = "
                    f"{lam:.4g}, its largest value over the run's species and E_k/n grid ({nuc} at {ekn:.4g} GeV/n)"
                    + ("; convection is on, outside the conversion's assumptions" if v_c > 0 else ""))
        v_a = disc
        spec["transport_pars"]["Va"] = round(v_a, 9)
        spec["reacceleration_conversion"] = {k: conv_out[k] for k in ("conversion_status", "relative_error_bound",
                                                                       "result")} | {"lam_max": lam}
    # km/s -> kpc/Myr in Kpp: the derived IAU/Julian factor, or with USINE's own inputs the factor of USINE's shipped
    # Kpp formula (inputs/init.TEST.par line 134), so that USINE's own configuration is reproduced exactly
    factor = USINE_MOMENTUM_DIFFUSION_FACTOR if usine_xs else f"{KPC_PER_MYR_PER_KM_S:.9e}"
    spec["Kpp_formula"] = f"(4./3.)*(Va*{factor}*beta*Etot)^2/(delta*(4-delta^2)*(4-delta)*w*K00)"
    if usine_xs and v_a > 0:
        subs.append(f"Kpp with USINE's shipped km/s -> kpc/Myr factor {factor} (inputs/init.TEST.par line 134), "
                    f"{1 - float(factor) / KPC_PER_MYR_PER_KM_S:.1e} below the IAU parsec and Julian year value "
                    f"{KPC_PER_MYR_PER_KM_S:.9e} used with the ILLUSTRATIVE sets")
    spec["source"] = {"gamma": gamma, "eta_s": eta_s, "spatial": "CST" if model == "Model2DKisoVc" else None}
    subs.append(f"source spectrum dQ/dE_k/n = q beta^eta_s Rig^-{gamma:g} (USINE POWERLAW, eta_s = {eta_s:g}: "
                f"spectrum_variable {variable!r} with eta {eta:g}"
                + (", dRig/dE_k/n = (A/|Z|)/beta" if variable == "rigidity" else "") + ")"
                + (", uniform in r up to radius_kpc in the thin disc (template CST)"
                   if model == "Model2DKisoVc" else ""))
    subs.extend(late)
    if "family" in transport:
        subs.append(f"family {transport['family']!r}: a label of the model family, not read by the translator")
    if "free" in transport:
        subs.append(f"free {transport['free']}: one run fixes every parameter; a fit varies the free ones")
    spec["solar_modulation"] = solar_modulation(phi_gv, subs)
    spec["usine_tolerances"] = usine_tolerances(tolerances, subs)
    spec["production_modifiers"] = [production_modifier(m, spec) for m in (production_modifiers or [])]
    for mod in spec["production_modifiers"]:
        subs.append(f"production cross section {mod['channel']} of {spec['usine_inputs']['production']} times "
                    f"{mod['norm']:.10g}, and below {mod['threshold_ekn_gev']:.10g} GeV/n times (E_k/n / "
                    f"{mod['threshold_ekn_gev']:.10g})^{mod['slope_le']:.10g} (USINE V3.5 fit-mode XS parameters Norm, "
                    "SlopeLE, EThresh, src/TUXSections.cc lines 3912-3921), applied to the table's nodes and read by "
                    "USINE as a second production file that replaces this channel only")
    if defaults:
        subs.append("not given in the transport block, the translator's value used: " + "; ".join(defaults))
    if spec["energy_grid"]["points_per_decade"] is None:
        subs.append(f"energy grid given explicitly: {spec['energy_grid']['n_points']} E_k/n nodes from "
                    f"{spec['energy_grid']['ekn_min_gev']:g} to {spec['energy_grid']['ekn_max_gev']:g} GeV/n")
    spec.update(substitutes=subs, transport=copy.deepcopy(transport))
    return spec


DEFAULT_TOLERANCES = {"EPS_ITERCONV": 1e-6, "EPS_INTEGR": 1e-4, "EPS_NORMDATA": 1e-10}


def usine_tolerances(given, subs: list[str]) -> dict:
    """USINE's numerical tolerances of the run (UsineRun @ Calculation); the defaults unless given (work package F1,
    dispatch 2: tighter tolerances to lower the noise of -2 ln L); a change is recorded."""
    out = dict(DEFAULT_TOLERANCES)
    for key, value in (given or {}).items():
        if key not in out:
            raise SpecError(f"USINE tolerance {key!r}: one of {sorted(out)}")
        v = float(value)
        if not (math.isfinite(v) and 0 < v < 1):
            raise SpecError(f"USINE tolerance {key} = {value!r}: a number in (0, 1)")
        out[key] = v
    if out != DEFAULT_TOLERANCES:
        subs.append("USINE tolerances " + ", ".join(f"{k} {v:g}" for k, v in out.items()) + " (defaults "
                    + ", ".join(f"{k} {v:g}" for k, v in DEFAULT_TOLERANCES.items()) + ")")
    return out


FORCE_FIELD_RIG0_GV = 0.2  # USINE SolMod0DFF Rig0 (as in USINE's shipped initialisation files)
CHANNEL = re.compile(r"(\d+)([A-Z][a-z]?)\+(H|He)->(\d+)([A-Z][a-z]?)")
MODIFIED_PRODUCTION_FILE = "xs_production_modified.dat"


def solar_modulation(phi_gv, subs: list[str]) -> dict | None:
    """USINE's force-field modulation (SolMod0DFF) at phi_gv, or None for the unmodulated run (phi = 0)."""
    try:
        phi = float(phi_gv)
    except (TypeError, ValueError):
        raise SpecError(f"phi_gv {phi_gv!r}: a number in GV") from None
    if not math.isfinite(phi) or phi < 0:
        raise SpecError(f"phi_gv {phi_gv!r}: a finite number >= 0 GV")
    if phi == 0:
        return None
    subs.append(f"solar modulation: USINE's force field SolMod0DFF (Gleeson and Axford; Phi = |Z| phi / A per nucleon, "
                f"phi = {phi:.10g} GV, Rig0 = {FORCE_FIELD_RIG0_GV} GV) applied by USINE to each isotope before the "
                "reader forms ratios (r3 P4); the unmodulated tables are written too")
    return {"model": "SolMod0DFF", "phi_gv": phi, "rig0_gv": FORCE_FIELD_RIG0_GV}


def production_modifier(mod, spec: dict) -> dict:
    """One production-channel change {'channel': '12C+H->11B', 'norm', 'slope_le', 'threshold_ekn_gev'}: sigma times
    norm, and below the threshold times (E_k/n / threshold)^slope_le (USINE's fit-mode XS parameters)."""
    if spec.get("mode") != "usine-inputs":
        raise SpecError("production modifiers act on USINE's own production file; the ILLUSTRATIVE sets have none")
    if not isinstance(mod, dict) or set(mod) != {"channel", "norm", "slope_le", "threshold_ekn_gev"}:
        raise SpecError("a production modifier is {'channel', 'norm', 'slope_le', 'threshold_ekn_gev'}")
    m = CHANNEL.fullmatch(str(mod["channel"]))
    if not m:
        raise SpecError(f"production modifier channel {mod['channel']!r}: '<A><element>+<H|He>-><A><element>'")
    proj, frag = (int(m.group(1)), m.group(2)), (int(m.group(4)), m.group(5))
    for a, sym in (proj, frag):
        if sym not in SYMBOLS or (SYMBOLS.index(sym) + 1, a) > tuple(spec["network_top"]):
            raise SpecError(f"production modifier channel {mod['channel']!r}: {a}{sym} is not in the network")
    if m.group(3) not in spec["targets"]:
        raise SpecError(f"production modifier channel {mod['channel']!r}: target {m.group(3)} is not a target of the run")
    norm, slope, thr = (float(mod[k]) for k in ("norm", "slope_le", "threshold_ekn_gev"))
    if not (math.isfinite(norm) and norm > 0 and math.isfinite(slope) and math.isfinite(thr) and thr > 0):
        raise SpecError(f"production modifier {mod['channel']}: norm > 0, finite slope_le, threshold_ekn_gev > 0")
    return {"channel": mod["channel"], "projectile": f"{proj[0]}{proj[1]}", "target": m.group(3),
            "fragment": f"{frag[0]}{frag[1]}", "norm": norm, "slope_le": slope, "threshold_ekn_gev": thr}


def modified_production_table(spec: dict, data_dir: Path) -> str:
    """USINE's production table restricted to the modified channels, each scaled as production_modifier says, in
    USINE's file format (written into the run directory at run time, never committed: GPL-2.0 numbers)."""
    lines = (Path(data_dir) / spec["usine_inputs"]["production"]).read_text(encoding="utf-8").splitlines()
    body = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    kind, unit, targets = body[0].split()
    e_min, e_max, n_e = float(body[1].split()[0]), float(body[1].split()[1]), int(body[1].split()[2])
    target_list = targets.split(",")
    out = ["# production cross sections of USINE's " + spec["usine_inputs"]["production"] + " for the modified "
           "channels only, scaled by usine_translate.py (production_modifier); run-time file, not committed",
           f" {kind}    {unit}      {targets}", "", f"{body[1]}", ""]
    for mod in spec["production_modifiers"]:
        label = f"{mod['projectile']} -> {mod['fragment']}"
        try:
            start = next(i for i, ln in enumerate(lines) if ln.strip() == label)
        except StopIteration:
            raise SpecError(f"production modifier: {label} not found in {spec['usine_inputs']['production']}") from None
        rows = [ln.split() for ln in lines[start + 1:start + 1 + n_e]]
        if len(rows) != n_e or any(len(r) != len(target_list) for r in rows):
            raise SpecError(f"production modifier: the {label} block of {spec['usine_inputs']['production']} does not "
                            f"have {n_e} rows of {len(target_list)} targets")
        col = target_list.index(mod["target"])
        out.append(label)
        for i, row in enumerate(rows):
            ekn = e_min * (e_max / e_min) ** (i / (n_e - 1))
            vals = [float(v) for v in row]
            bias = (ekn / mod["threshold_ekn_gev"]) ** mod["slope_le"] if ekn < mod["threshold_ekn_gev"] else 1.0
            vals[col] *= mod["norm"] * bias
            out.append("\t".join(f"{v:.6e}" for v in vals))
        out.append("")
    return "\n".join(out) + "\n"


def _illustrative(transport, xs_block, prod_name, inel_name, species_block, src, dens, he_ratio, subs,
                  defaults) -> dict:
    """The ILLUSTRATIVE cross sections and parent ratios of theory:cr-secondary-ratio (work package B1)."""
    n_h = dens["HI"]
    if dens["HII"] or dens["H2"]:
        raise SpecError("gas: with the ILLUSTRATIVE sets give one neutral density 'n_H = <number> cm^-3'")
    subs.append(f"gas {transport['gas'].get('model')!r}: HI = {n_h:g} cm^-3, HII = H2 = 0 in the thin disc of "
                "half-thickness h; USINE's Coulomb loss acts on HII and is therefore zero")
    if he_ratio:
        subs.append(f"gas He_to_H_number {he_ratio}: not used; the ILLUSTRATIVE cross sections are on "
                    "hydrogen only and no helium cross section is invented (He density 0, target H)")
    prod_key, xs = illustrative_set(prod_name)
    inel_key, _ = illustrative_set(inel_name)
    if inel_key != prod_key:
        raise SpecError(f"production set {prod_key} and inelastic set {inel_key} differ; give one ILLUSTRATIVE set")
    species, prod, inel = network(xs)
    top = max(species, key=charge_and_mass)
    _given(species_block, "network_top", "species", top, defaults, f" (the network of {prod_key})")
    _given(species_block, "isotopic", "species", xs["isotopic"], defaults, f" ({prod_key})")
    subs.append(f"cross_sections.production_set {prod_name!r} and inelastic_set {inel_name!r}: the ILLUSTRATIVE set "
                f"{prod_key}")
    if "network_top" in species_block and _nuclide(species_block["network_top"], "species.network_top") \
            != charge_and_mass(top):
        raise SpecError(f"species.network_top {species_block['network_top']!r}: the network of {prod_key} ends at "
                        f"{top}; the translator does not extend or cut it")
    if "isotopic" in species_block and species_block["isotopic"] is not xs["isotopic"]:
        raise SpecError(f"species.isotopic {species_block['isotopic']}: set {prod_key} is "
                        f"{'isotopic' if xs['isotopic'] else 'element-level'}")
    if not xs["isotopic"]:
        subs.append(f"element-level set {prod_key}: C, O and B on 12C, 16O and 11B (10B without production, with B's "
                    "inelastic cross section)")
    subs.append("production channels not in the set are zero (USINE needs every pair of the network)")
    parents = sorted({k.split("->")[0] for k in prod}, key=charge_and_mass)
    parent_elements = sorted({ELEMENTS[charge_and_mass(p)[0]] for p in parents})
    if not set(parent_elements) <= set(PARENT_RATIOS):
        raise SpecError(f"parents {parent_elements}: abundances known only for {sorted(PARENT_RATIOS)}")
    abund = str(src.get("abundances", ""))
    if abund.startswith("data-normalised"):
        raise SpecError("sources.abundances 'data-normalised ...' needs USINE's own cross-section files "
                        "(cross_sections 'usine:...'); the ILLUSTRATIVE sets use the parent ratios")
    late = [f"parent abundances: each parent source scaled until its unmodulated local flux at E_k/n = "
            f"{NORM_EKN_GEV:g} GeV/n is in the ratio "
            f"{', '.join(f'{k} {v:g}' for k, v in PARENT_RATIOS.items() if k in parent_elements)}"
            " (theory:cr-secondary-ratio parent list); USINE NormList with generated points, not data"]
    if not abund:
        late.append(f"sources.abundances not given: {PARENT_LIST_ABUNDANCES!r} (the ILLUSTRATIVE sets' parent list)")
    elif abund.strip() != PARENT_LIST_ABUNDANCES:
        raise SpecError(f"sources.abundances {abund!r}: with the ILLUSTRATIVE sets only {PARENT_LIST_ABUNDANCES!r} is "
                        "translated (the parent ratios above); data-normalised abundances need USINE's own cross "
                        "sections; nothing else is replaced")
    late.append("tertiary chains, ghost nuclei and exotic primaries off")
    return {"mode": "illustrative", "gas_cm3": {"HI": n_h, "HII": 0.0, "H2": 0.0, "He": 0.0}, "targets": ["H"],
            "species": species, "parents": parents, "production_mb": prod, "inelastic_mb": inel,
            "cross_section_set": prod_key, "norm_points": {e: PARENT_RATIOS[e] for e in parent_elements},
            "norm_ekn_gev": NORM_EKN_GEV,
            "beta_unstable": [s for s in species if s == "10Be"] if transport.get("decay", {}).get("enabled") else [],
            "_late_notes": late}


def _usine_inputs(transport, xs_block, prod_name, inel_name, species_block, src, dens, he_ratio, subs,
                  defaults) -> dict:
    """USINE's own cross-section files and data-normalised source abundances, read in place from HEP_USINE_DATA
    (GPL-2.0: never copied; work package B1X)."""
    prod_file = usine_file(prod_name, "cross_sections.production_set")
    inel_file = usine_file(inel_name, "cross_sections.inelastic_set")
    if "network_top" not in species_block:
        raise SpecError("species.network_top: with USINE's own cross sections the network runs from 1H to the "
                        "isotope named there (e.g. 'Si-30')")
    z_top, a_top = _nuclide(species_block["network_top"], "species.network_top")
    if z_top < 6:
        raise SpecError("species.network_top: the network must reach carbon at least")
    if species_block.get("isotopic", True) is not True:
        raise SpecError("species.isotopic false: USINE's own cross sections are isotopic")
    if "isotopic" not in species_block:
        subs.append("species.isotopic not given: USINE's network is isotopic")
    elements = list(SYMBOLS[:z_top])
    data_file, groups, pure_isotopes = _abundances(str(src.get("abundances", "")), elements)
    normed = {e for g in groups for e in g[0]}
    pure = [e for e in elements if e not in normed] + pure_isotopes
    n_h = dens["HI"] + dens["HII"] + 2.0 * dens["H2"]
    he = float(he_ratio) * n_h if he_ratio else 0.0
    targets = ["H", "He"] if he > 0 else ["H"]
    subs.append(f"gas {transport['gas'].get('model')!r}: HI = {dens['HI']:g}, HII = {dens['HII']:g}, H2 = "
                f"{dens['H2']:g} cm^-3, He = He_to_H_number x (HI + HII + 2 H2) = {he:.6g} cm^-3 in the thin disc; "
                f"targets {', '.join(targets)}")
    subs.append(f"cross sections: USINE's own files {prod_file} (production) and {inel_file} (inelastic), read in "
                "place from HEP_USINE_DATA (GPL-2.0, never copied)")
    late = [f"source abundances: solar-system isotopic fractions and abundances with the FIP bias (USINE kSSISOTFRAC, "
            f"kSSISOTABUND, kFIPBIAS, {SOLAR_FILE}), then each element normalised to data of USINE's {data_file}: "
            + "; ".join(f"{','.join(n)} to {exp} at {e:g} GeV/n" for n, exp, e in groups)
            + f"; pure secondaries {','.join(pure) or 'none'}"
            + (f" (isotopes {','.join(pure_isotopes)} of normalised elements without a source)" if pure_isotopes
               else ""),
            f"network: every nucleus of USINE's chart {CHART_FILE} from 1H to {a_top}{SYMBOLS[z_top - 1]}; no "
            "antinuclei; tertiary chains, ghost nuclei and exotic primaries off"]
    tabled = [s for s in TABLED_ISOTOPES if charge_and_mass(s)[0] <= z_top]
    return {"mode": "usine-inputs", "gas_cm3": dict(dens, He=he), "targets": targets, "species": tabled,
            "network_range": f"[1H,{a_top}{SYMBOLS[z_top - 1]}]", "network_top": [z_top, a_top],
            "pure_secondaries": pure, "usine_inputs": {"production": prod_file, "inelastic": inel_file,
                                                       "norm_data": data_file},
            "norm_groups": [{"elements": n, "experiment": exp, "ekn_gev": e} for n, exp, e in groups],
            "cross_section_set": f"usine:{prod_file} + usine:{inel_file}",
            "beta_unstable": "chart" if transport.get("decay", {}).get("enabled") else [],
            "_late_notes": late}


def _eps(x: float) -> str:
    """A tolerance as USINE's shipped files write it ('1.e-6'), so default runs render byte-identically."""
    mant, exp = f"{float(x):.10e}".split("e")
    mant = mant.rstrip("0").rstrip(".")
    return f"{mant if mant != '1' else '1.'}e{int(exp)}"


def _fmt(x: float) -> str:
    return f"{float(x):.10g}"


def _xs_table(title: str, rows: list[tuple[str, float]]) -> str:
    lo, hi = XS_GRID_GEV
    lines = [f"# {title}", "# ILLUSTRATIVE placeholders of theory:cr-secondary-ratio, written by usine_translate.py "
             "(not data; constant in energy)", "#  Type  Unit     Targets", " sigma    mb      H", "",
             "# EknMIN[GeV/n]   EknMAX[GeV/n]   nEkn  (PROJECTILE GRID)", f"{lo:.6e}      {hi:.6e}    2", ""]
    for label, value in rows:
        lines += [label, f"{value:.6e}", f"{value:.6e}", ""]
    return "\n".join(lines)


def render(spec: dict, data_dir: str, run_dir: str) -> dict[str, str]:
    """The files of the run directory (name -> text). data_dir and run_dir are written as given (absolute paths for
    a run; placeholders such as <TOOL_HOME>/inputs and <RUN_DIR> for a fixture)."""
    sp = spec["species"]
    native = spec.get("mode") == "usine-inputs"
    m, g, p, grid = spec["model"], spec["geometry"], spec["transport_pars"], spec["energy_grid"]
    par_names = ["Va", "Vc", "K0", "delta", "eta_t", "R0", "w"] + sorted(k for k in p if k[:2] in ("Rl", "dl", "sl",
                                                                                                  "Rh", "dh", "sh"))
    par_units = {"Va": "km/s", "Vc": "km/s", "K0": "kpc^2/Myr", "R0": "GV"}
    src = spec["source"]
    if native:
        ui = spec["usine_inputs"]
        norm_lines = [f"Base @ CRData @ fCRData @ M=1 @ {data_dir}/{ui['norm_data']}",
                      "Base @ CRData @ NormList @ M=0 @ " + ";".join(
                          f"{','.join(n['elements'])}:{n['experiment']}|{_fmt(n['ekn_gev'])}|kEkn"
                          for n in spec["norm_groups"])]
        crs, parents_line, pure = spec["network_range"], "-", ",".join(spec["pure_secondaries"]) or "-"
        xs_lines = [f"Base @ XSections @ fProd @ M=1 @ {data_dir}/{ui['production']}",
                    f"Base @ XSections @ fTotInelAnn @ M=1 @ {data_dir}/{ui['inelastic']}"]
        if spec.get("production_modifiers"):
            xs_lines.insert(1, f"Base @ XSections @ fProd @ M=1 @ {run_dir}/{MODIFIED_PRODUCTION_FILE}")
    else:
        e = spec["norm_ekn_gev"]
        norm_lines = [f"Base @ CRData @ fCRData @ M=1 @ {run_dir}/norm_points.dat",
                      f"Base @ CRData @ NormList @ M=0 @ {','.join(spec['norm_points'])}:NORM|{_fmt(e)}|kEkn"]
        crs, parents_line = ",".join(sp), "-"
        pure = (",".join(sorted({ELEMENTS[charge_and_mass(s)[0]] for s in sp if s not in spec["parents"]},
                                key=lambda x: list(ELEMENTS.values()).index(x))) or "-")
        xs_lines = [f"Base @ XSections @ fProd @ M=1 @ {run_dir}/xs_production.dat",
                    f"Base @ XSections @ fTotInelAnn @ M=1 @ {run_dir}/xs_inelastic.dat"]
    lines = [
        f"# USINE initialisation file written by usine_translate.py (hep-research adapter cr-propagation), run {spec['name']}",
        *norm_lines,
        f"Base @ EnergyGrid @ NBins @ M=0 @ {grid['n_points']}",
        f"Base @ EnergyGrid @ NUC_EknRange @ M=0 @ [{grid['ekn_min_gev']:.10e},{grid['ekn_max_gev']:.10e}]",
        f"Base @ EnergyGrid @ ANTINUC_EknRange @ M=0 @ [{grid['ekn_min_gev']:.10e},{grid['ekn_max_gev']:.10e}]",
        f"Base @ EnergyGrid @ LEPTONS_EkRange @ M=0 @ [{grid['ekn_min_gev']:.10e},{grid['ekn_max_gev']:.10e}]",
        f"Base @ ListOfCRs @ fAtomicProperties @ M=0 @ {data_dir}/{ATOMIC_FILE}",
        f"Base @ ListOfCRs @ fChartsForCRs @ M=0 @ {data_dir}/{CHART_FILE}",
        "Base @ ListOfCRs @ IsLoadGhosts @ M=0 @ false",
        f"Base @ ListOfCRs @ ListOfCRs @ M=0 @ {crs}",
        f"Base @ ListOfCRs @ ListOfParents @ M=0 @ {parents_line}",
        f"Base @ ListOfCRs @ PureSecondaries @ M=0 @ {pure}",
        f"Base @ ListOfCRs @ SSRelativeAbund @ M=0 @ {data_dir}/{SOLAR_FILE}",
        "Base @ MediumCompo @ Targets @ M=0 @ " + ",".join(spec["targets"]),
        "Base @ XSections @ Tertiaries @ M=0 @ -",
        *xs_lines,
    ]
    if m == "Model2DKisoVc":
        lines += [f"{m} @ Base @ NBessel @ M=0 @ {spec['n_bessel']}", f"{m} @ Base @ NIntegrR @ M=0 @ 1000",
                  f"{m} @ Base @ NIntegrZ @ M=0 @ 200",
                  f"{m} @ Geometry @ ParNames @ M=0 @ L,h,R,rhole", f"{m} @ Geometry @ ParUnits @ M=0 @ kpc,kpc,kpc,kpc",
                  f"{m} @ Geometry @ ParVals @ M=0 @ {_fmt(g['L'])},{_fmt(g['h'])},{_fmt(g['R'])},{_fmt(g['rhole'])}",
                  f"{m} @ Geometry @ TAxis @ M=0 @ -", f"{m} @ Geometry @ XAxis @ M=0 @ r:[0,R],10,LIN",
                  f"{m} @ Geometry @ YAxis @ M=0 @ z:[0,L],10,LIN", f"{m} @ Geometry @ ZAxis @ M=0 @ -",
                  f"{m} @ Geometry @ XSun @ M=0 @ {_fmt(spec['observer_kpc'])}", f"{m} @ Geometry @ YSun @ M=0 @ 0",
                  f"{m} @ Geometry @ ZSun @ M=0 @ -"]
    else:
        lines += [f"{m} @ Geometry @ ParNames @ M=0 @ L,h,rhole", f"{m} @ Geometry @ ParUnits @ M=0 @ kpc,kpc,kpc",
                  f"{m} @ Geometry @ ParVals @ M=0 @ {_fmt(g['L'])},{_fmt(g['h'])},{_fmt(g['rhole'])}",
                  f"{m} @ Geometry @ TAxis @ M=0 @ -", f"{m} @ Geometry @ XAxis @ M=0 @ z:[0,L],10,LIN",
                  f"{m} @ Geometry @ YAxis @ M=0 @ -", f"{m} @ Geometry @ ZAxis @ M=0 @ -",
                  f"{m} @ Geometry @ XSun @ M=0 @ -", f"{m} @ Geometry @ YSun @ M=0 @ -",
                  f"{m} @ Geometry @ ZSun @ M=0 @ -"]
    gas = spec["gas_cm3"]
    lines += [f"{m} @ ISM @ ParNames @ M=0 @ -", f"{m} @ ISM @ ParUnits @ M=0 @ -", f"{m} @ ISM @ ParVals @ M=0 @ -"]
    lines += [f"{m} @ ISM @ Density @ M=1 @ {k}:FORMULA|{_fmt(gas[k])}" for k in ("HI", "HII", "H2", "He")]
    lines += [f"{m} @ ISM @ Te @ M=0 @ FORMULA|1.e4"]
    lines += [f"{m} @ SrcPointLike @ {k} @ M=1 @ -" for k in ("Species", "SpectAbundInit", "SpectTempl",
                                                               "SpectValsPerCR", "SrcXPosition", "SrcYPosition",
                                                               "SrcZPosition", "TStart", "TStop")]
    if native:
        species_line, abund_line, qvals = "ALL", "kSSISOTFRAC,kSSISOTABUND,kFIPBIAS", ""
    else:
        species_line, abund_line = ",".join(spec["parents"]), "-"
        qvals = "," + ",".join(f"{q}=1.e-5" for q in spec["parents"])
    lines += [f"{m} @ SrcSteadyState @ Species @ M=1 @ ASTRO_STD|{species_line}",
              f"{m} @ SrcSteadyState @ SpectAbundInit @ M=1 @ ASTRO_STD|{abund_line}",
              f"{m} @ SrcSteadyState @ SpectTempl @ M=1 @ ASTRO_STD|POWERLAW|q",
              f"{m} @ SrcSteadyState @ SpectValsPerCR @ M=1 @ ASTRO_STD|q[PERCR:DEFAULT=1.e-5{qvals}];"
              f"alpha[SHARED:{_fmt(src['gamma'])}];eta_s[SHARED:{_fmt(src['eta_s'])}]",
              f"{m} @ SrcSteadyState @ SpatialTempl @ M=1 @ ASTRO_STD|{src['spatial'] or '-'}",
              f"{m} @ SrcSteadyState @ SpatialValsPerCR @ M=1 @ ASTRO_STD|-",
              f"{m} @ Transport @ ParNames @ M=0 @ {','.join(par_names)}",
              f"{m} @ Transport @ ParUnits @ M=0 @ {','.join(par_units.get(n, '-') for n in par_names)}",
              f"{m} @ Transport @ ParVals @ M=0 @ {','.join(_fmt(p[n]) for n in par_names)}"]
    lines += ([f"{m} @ Transport @ Wind @ M=1 @ W0:FORMULA|0", f"{m} @ Transport @ Wind @ M=1 @ W1:FORMULA|Vc"]
              if m == "Model2DKisoVc" else [f"{m} @ Transport @ Wind @ M=1 @ W0:FORMULA|Vc"])
    lines += [f"{m} @ Transport @ VA @ M=0 @ FORMULA|Va", f"{m} @ Transport @ K @ M=1 @ K00:FORMULA|{spec['K_formula']}",
              f"{m} @ Transport @ Kpp @ M=0 @ FORMULA|{spec['Kpp_formula']}",
              "SolMod0DFF @ Base @ ParNames @ M=0 @ phi", "SolMod0DFF @ Base @ ParUnits @ M=0 @ GV",
              "SolMod0DFF @ Base @ ParVals @ M=0 @ 0", "SolMod0DFF @ Base @ Rig0 @ M=0 @ 0.2",
              "TemplSpectrum @ POWERLAW @ ParNames @ M=0 @ q,alpha,eta_s",
              "TemplSpectrum @ POWERLAW @ ParUnits @ M=0 @ (/GeV/n/m3/Myr),-,-",
              "TemplSpectrum @ POWERLAW @ Definition @ M=0 @ FORMULA|q*beta^(eta_s)*Rig^(-alpha)",
              "TemplSpatialDist @ CST @ ParNames @ M=0 @ -", "TemplSpatialDist @ CST @ ParUnits @ M=0 @ -",
              "TemplSpatialDist @ CST @ Definition @ M=0 @ FORMULA|1",
              "UsineRun @ Calculation @ BC_ANTINUC_LE @ M=0 @ kD2NDLNEKN2_ZERO",
              "UsineRun @ Calculation @ BC_ANTINUC_HE @ M=0 @ kNOCHANGE",
              "UsineRun @ Calculation @ BC_LEPTON_LE @ M=0 @ kNOCURRENT",
              "UsineRun @ Calculation @ BC_LEPTON_HE @ M=0 @ kNOCURRENT",
              "UsineRun @ Calculation @ BC_NUC_LE @ M=0 @ kD2NDLNEKN2_ZERO",
              "UsineRun @ Calculation @ BC_NUC_HE @ M=0 @ kNOCHANGE",
              *[f"UsineRun @ Calculation @ {k} @ M=0 @ {_eps(v)}" for k, v in
                (spec.get("usine_tolerances") or DEFAULT_TOLERANCES).items()],
              "UsineRun @ Calculation @ IsUseNormList @ M=0 @ true",
              "UsineRun @ Display @ QtiesExpsEType @ M=0 @ ALL",
              "UsineRun @ Display @ ErrType @ M=0 @ kERRSTAT",
              "UsineRun @ Display @ FluxPowIndex @ M=0 @ 0",
              f"UsineRun @ Models @ Propagation @ M=1 @ {m}",
              "UsineRun @ Models @ SolarModulation @ M=1 @ SolMod0DFF"]
    lines += [f"UsineRun @ OnOff @ {k} @ M=0 @ {'true' if v else 'false'}" for k, v in spec["switches"].items()]
    if native:
        return {"usine.init.par": "\n".join(lines) + "\n"}
    # every pair with a parent at least as heavy in mass number (USINE orders 10B before 10Be by mass and needs each
    # reaction from a heavier list member filled)
    prod_rows = [(f"{p} -> {c}", spec["production_mb"].get(f"{p}->{c}", 0.0)) for p in sp for c in sp
                 if p != c and charge_and_mass(c)[1] <= charge_and_mass(p)[1]]
    inel_rows = [(s, spec["inelastic_mb"][s]) for s in sp]
    norm_rows = ["# normalisation points written by usine_translate.py: parent ratios of theory:cr-secondary-ratio "
                 "at one E_k/n, phi = 0 (not data)"]
    for element, value in spec["norm_points"].items():
        norm_rows.append(f"{element}   NORM   EKN   {e:.6e} {0.9 * e:.6e} {1.1 * e:.6e}   {value:.6e} {-1e-2 * value:.6e} "
                         f"{1e-2 * value:.6e} -0.000000e+00 0.000000e+00   none   0.000000e+00   1   "
                         "2000/01/01-000000:2000/01/02-000000 0")
    return {"usine.init.par": "\n".join(lines) + "\n",
            "xs_production.dat": _xs_table("production cross sections (mb) on H, every pair of the network",
                                           prod_rows),
            "xs_inelastic.dat": _xs_table("inelastic cross sections (mb) on H", inel_rows),
            "norm_points.dat": "\n".join(norm_rows) + "\n"}


def _ratios(spec: dict) -> list[str]:
    elements = {ELEMENTS[charge_and_mass(s)[0]] for s in spec["species"]}
    return (["B/C"] if {"B", "C"} <= elements else []) + (["10BE/9BE"] if {"10Be", "9Be"} <= set(spec["species"])
                                                          else [])


def quantities(spec: dict) -> str:
    """The quantity argument of 'usine -l': every species of the network and the element ratios it defines per
    E_k/n, and the element ratios per rigidity (USINE's own ratios, read only to check the reader), unmodulated; with
    solar modulation the E_k/n group is also written at phi."""
    names = [usine_name(s) for s in spec["species"]] + _ratios(spec)
    mod = spec.get("solar_modulation")
    phis = f"0.,{mod['phi_gv']!r}" if mod else "0."   # one group per E-type: USINE keeps one phi list per group
    return (",".join(names) + f":KEKN:{phis}"
            + (";" + ",".join(_ratios(spec)) + ":kR:0." if _ratios(spec) else ""))


def output_file(spec: dict, quantity: str, axis: str = "Ekn") -> str:
    """USINE's file name of one quantity ('10BE', 'B/C') of this run, per E_k/n ('Ekn') or rigidity ('R')."""
    return f"local_fluxes_{quantity.replace('/', '')}_{axis}_{spec['model']}_SolMod0DFF_phi0_00GV.out"


def expected_outputs(spec: dict) -> list[str]:
    return ([output_file(spec, usine_name(s)) for s in spec["species"]] + [output_file(spec, q) for q in _ratios(spec)]
            + [output_file(spec, q, "R") for q in _ratios(spec)])


def modulated_outputs(spec: dict, out_dir: Path) -> dict[str, Path]:
    """nuclide -> USINE's modulated table of the run (phi > 0), found by pattern since USINE writes phi in the file
    name with its own rounding; the reader checks the phi of the header. Empty for an unmodulated run; a nuclide with
    no table or more than one is left out (the run is then not ok)."""
    if not spec.get("solar_modulation"):
        return {}
    found = {}
    for s in spec["species"]:
        hits = [p for p in sorted(Path(out_dir).glob(f"local_fluxes_{usine_name(s)}_Ekn_{spec['model']}_SolMod0DFF_phi"
                                                     "*GV.out")) if not p.name.endswith("_phi0_00GV.out")]
        if len(hits) == 1:
            found[s] = hits[0]
    return found


HALF_LIFE_MYR = {"Myr": 1.0, "My": 1.0, "kyr": 1e-3, "ky": 1e-3, "yr": 1e-6, "y": 1e-6, "d": 1e-6 / 365.25,
                 "h": 1e-6 / (365.25 * 24)}


def _chart_beta_rows(lines: list[str]) -> list[tuple[str, float, str]]:
    """(nuclide, half-life, unit) of every BETA row of a USINE chart."""
    rows = []
    for ln in lines:
        parts = ln.split()
        if ln.lstrip().startswith("#") or len(parts) < 5 or parts[4] != "BETA" or "||" not in ln:
            continue
        fields = ln.split("||")[1].split("|")[0].split()
        rows.append((parts[3], float(fields[0]), fields[2]))
    return rows


def check_half_lives(spec: dict, data_dir: Path) -> list[str]:
    """The USINE chart's BETA half-lives of the network against NUBASE2020 (core.constants.physical); notes for the
    record. With the ILLUSTRATIVE sets (10Be only) a difference above HALF_LIFE_RTOL is refused (SpecError). With
    USINE's own inputs every BETA nucleus of the network that core knows is compared: a difference is recorded, since
    the chart is then USINE's declared input, except for 10Be (the clock of 10Be/9Be, r3 P6), which is refused; a
    nucleus core does not carry is recorded as not compared. The translator never patches the chart."""
    notes: list[str] = []
    if not spec["beta_unstable"]:
        return notes
    chart = Path(data_dir) / CHART_FILE
    lines = chart.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = {nuc: (value, unit) for nuc, value, unit in _chart_beta_rows(lines)}
    if spec["beta_unstable"] == "chart":
        z_top, a_top = spec["network_top"]
        def in_network(nuc: str) -> bool:
            try:
                return _nuclide(nuc, "chart") <= (z_top, a_top)
            except SpecError:
                return False
        wanted = [n for n in rows if in_network(n)]
    else:
        wanted = list(spec["beta_unstable"])
    for nuc in wanted:
        if nuc not in rows:
            raise SpecError(f"{nuc} not found in the USINE chart {CHART_FILE}")
        value, unit = rows[nuc]
        z, a = _nuclide(nuc, "chart")
        try:
            ref = half_life(f"{SYMBOLS[z - 1]}-{a}")
        except (KeyError, ValueError) as exc:
            notes.append(f"{nuc} half-life: USINE chart {value} {unit}, not compared ({exc})")
            continue
        if unit not in HALF_LIFE_MYR or ref.unit not in HALF_LIFE_MYR:
            raise SpecError(f"{nuc}: half-life units {unit!r} (chart) and {ref.unit!r} (NUBASE2020) not compared")
        rel = value * HALF_LIFE_MYR[unit] / (float(ref.value) * HALF_LIFE_MYR[ref.unit]) - 1.0
        if abs(rel) > HALF_LIFE_RTOL and (spec["beta_unstable"] != "chart" or nuc == "10Be"):
            raise SpecError(f"{nuc}: USINE chart half-life {value} {unit} differs from NUBASE2020 "
                            f"{ref.value} {ref.unit}; the translator does not patch the chart")
        notes.append(f"{nuc} half-life: USINE chart {value} {unit}, NUBASE2020 {ref.value} {ref.unit} "
                     f"(core.constants.physical)" + (f"; differs by {rel:+.2%}, USINE's chart value is used"
                                                     if abs(rel) > HALF_LIFE_RTOL else ""))
    return notes


class UsineDataMissing(SpecError):
    """USINE's own input files are named but HEP_USINE_DATA (--data-dir) is unset or lacks them (exit 3)."""


def usine_input_paths(spec: dict, data_dir) -> dict[str, Path]:
    """USINE's own files a run reads in place (role -> path under the inputs folder); empty with the ILLUSTRATIVE
    sets. Raises UsineDataMissing without the folder or a file: nothing is copied or replaced."""
    if spec.get("mode") != "usine-inputs":
        return {}
    named = ", ".join(f"usine:{f}" for f in spec["usine_inputs"].values())
    if data_dir is None or not str(data_dir) or not Path(data_dir).is_dir():
        raise UsineDataMissing(f"the transport names USINE's own files ({named}); they are read in place from USINE's "
                               "inputs folder, HEP_USINE_DATA (or --data-dir), which is unset or not a folder; "
                               "nothing is copied into the repository or the run")
    paths = {role: Path(data_dir) / rel for role, rel in spec["usine_inputs"].items()}
    missing = [f"usine:{spec['usine_inputs'][r]}" for r, path in paths.items() if not path.is_file()]
    if missing:
        raise UsineDataMissing(f"{missing} not found in USINE's inputs folder {data_dir}")
    return paths


def prepare(spec: dict, run_dir: Path, data_dir: Path) -> dict:
    """Write the run directory; the input files' sha256 (by name)."""
    usine_input_paths(spec, data_dir)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, text in render(spec, str(Path(data_dir).resolve()), str(run_dir.resolve())).items():
        (run_dir / name).write_text(text, encoding="utf-8")
        hashes[name] = sha256(run_dir / name)
    return hashes


def prepare_derived(spec: dict, run_dir: Path, data_dir: Path) -> dict:
    """Run-time files computed from USINE's own inputs (the modified production table); name -> sha256. They hold
    GPL-2.0 numbers, so they live only in the run directory and are never rendered into a fixture."""
    if not spec.get("production_modifiers"):
        return {}
    path = Path(run_dir) / MODIFIED_PRODUCTION_FILE
    path.write_text(modified_production_table(spec, data_dir), encoding="utf-8")
    return {MODIFIED_PRODUCTION_FILE: sha256(path)}


def tool_home(binary: Path) -> Path:
    """USINE's installation folder (the value of USINE's variable USINE): the parent of bin/usine."""
    return Path(binary).resolve().parent.parent


def run_usine(spec: dict, run_dir: Path, binary: Path, data_dir: Path, timeout: float = 3600.0) -> dict:
    """Prepare and run; {'ok', 'exit_status', 'seconds', 'inputs', 'outputs' (name -> sha256), 'command', 'notes',
    'log_tail', 'usine_inputs' (USINE's own files read in place -> sha256)}. The run is ok only if every expected
    output exists and the log has no USINE error or crash."""
    read_in_place = {f"<TOOL_HOME>/inputs/{spec['usine_inputs'][role]}": sha256(path)
                     for role, path in usine_input_paths(spec, data_dir).items()}
    notes = check_half_lives(spec, data_dir)
    run_dir = Path(run_dir).resolve()
    inputs = prepare(spec, run_dir, data_dir)
    derived = prepare_derived(spec, run_dir, data_dir)
    out = run_dir / "out"
    command = [str(Path(binary).resolve()), "-l", str(run_dir / "usine.init.par"), str(out), quantities(spec),
               "0", "1", "1", "0"]
    env = dict(os.environ, USINE=str(tool_home(binary)))
    started = time.monotonic()
    try:
        with open(run_dir / "usine.log", "w", encoding="utf-8") as log:
            code = subprocess.run(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, timeout=timeout,
                                  env=env).returncode
    except subprocess.TimeoutExpired:
        code = -1
    seconds = time.monotonic() - started
    log_text = (run_dir / "usine.log").read_text(encoding="utf-8", errors="replace")
    crashed = any(s in log_text for s in ("--- ERROR ---", "--- ABORT ---", "segmentation violation"))
    outputs = {}
    for name in expected_outputs(spec):
        if (out / name).is_file():
            outputs[f"out/{name}"] = sha256(out / name)
    modulated = modulated_outputs(spec, out)
    for path in modulated.values():
        outputs[f"out/{path.name}"] = sha256(path)
    ok = (not crashed and code != -1 and len(outputs) == len(expected_outputs(spec)) + len(modulated)
          and (not spec.get("solar_modulation") or len(modulated) == len(spec["species"])))
    return {"ok": ok, "exit_status": code, "seconds": seconds, "inputs": inputs, "outputs": outputs,
            "command": command, "notes": notes, "log_tail": "" if ok else log_text[-800:],
            "usine_inputs": read_in_place, "derived_inputs": derived}


INPUT_MANIFEST_NOTE = ("sha256 is of each file as run, with the absolute paths of the run directory and of USINE's "
                       "inputs folder written into usine.init.par; committed_form_sha256 is of the same file written "
                       "with the placeholders <TOOL_HOME>/inputs and <RUN_DIR> (the form committed under "
                       "tests/adapters/fixtures/cr_propagation/usine/inputs/), equal to sha256 for the files that hold "
                       "no path; entries with read_in_place are USINE's own files (GPL-2.0), hashed where they lie and "
                       "never copied; entries with derived_from_usine_inputs are run-time files computed from them (a "
                       "modified production table), kept in the run directory only and never committed")


def record(spec: dict, result: dict, binary: Path, environment: dict | None = None) -> dict:
    """The computational-run artifact of one USINE run (paths shortened to file names; no home path)."""
    tools = [{"name": PROGRAM, "version": PROGRAM_VERSION, "binary": "<TOOL_HOME>/bin/usine",
              "binary_sha256": sha256(binary) if Path(binary).is_file() else None}]
    if environment:
        tools += [t for t in environment.get("tools", []) if t.get("name") != PROGRAM]
    command = ["<TOOL_HOME>/bin/usine", "-l", "<RUN_DIR>/usine.init.par", "<RUN_DIR>/out"] + result["command"][4:]
    committed = {n: hashlib.sha256(t.encode("utf-8")).hexdigest()
                 for n, t in render(spec, "<TOOL_HOME>/inputs", "<RUN_DIR>").items()}
    return {
        "contract_version": CONTRACT_VERSION, "artifact_id": f"usine-run-{spec['name']}",
        "artifact_type": "computational-run",
        "objective": f"USINE run '{spec['name']}' translated from a transport block "
                     "(adapters/cr-propagation/assets/usine_translate.py)",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACT_VERSION, "profiles": {}},
        "provenance": {"producer_skill": "hep-computing", "created": _dt.date.today().isoformat(), "evidence_ids": []},
        "inputs": [], "outputs": [], "unresolved_inputs": [],
        "status": ["unvalidated"] if result["ok"] else ["failed"],
        "extension": {
            "input_manifest": [{"path": p, "sha256": h, "committed_form_sha256": committed[p]}
                               for p, h in sorted(result["inputs"].items())]
                              + [{"path": p, "sha256": h, "read_in_place": True}
                                 for p, h in sorted(result.get("usine_inputs", {}).items())]
                              + [{"path": p, "sha256": h, "derived_from_usine_inputs": True}
                                 for p, h in sorted(result.get("derived_inputs", {}).items())],
            "input_manifest_note": INPUT_MANIFEST_NOTE,
            "tools": tools,
            "commands": [" ".join(command[:4]) + " '" + command[4] + "' " + " ".join(command[5:])],
            "environment": (environment or {}).get("environment", {}),
            "seeds": {"note": "USINE's local-flux calculation is deterministic: no random numbers are drawn"},
            "tolerances": {"note": "USINE EPS_ITERCONV 1e-6, EPS_INTEGR 1e-4, EPS_NORMDATA 1e-10 (written into the "
                                   "initialisation file); outputs printed with 6 significant digits"},
            "resources": {"wall_seconds": round(result["seconds"], 2)},
            "exit_status": 0 if result["ok"] else (result["exit_status"] or 1),
            "usine_exit_status": result["exit_status"],
            "exit_status_note": "exit_status is the run's outcome as judged by usine_translate.py (0: every expected "
                                "output written, no USINE error or crash in the log); USINE V3.5 itself returns 1 on "
                                "every path (usine_exit_status)",
            "output_hashes": result["outputs"],
            "notes": result["notes"] + spec["substitutes"],
        },
    }


def load_transport(path: Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc["transport"] if isinstance(doc, dict) and isinstance(doc.get("transport"), dict) else doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog="Exit 0 ok or prepared, 1 USINE failed, 2 bad input, 3 USINE missing.")
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("translate", "run"):
        p = sub.add_parser(name)
        p.add_argument("--transport", required=True, type=Path, help="transport block or harmonized-v1 file")
        p.add_argument("--name", required=True, help="run name (letters, digits, '-', '_')")
        p.add_argument("--out", required=True, type=Path, help="run directory to write")
        p.add_argument("--ekn-range", required=True, help="LOW,HIGH in GeV/n that the outputs must cover")
        p.add_argument("--points-per-decade", type=int, default=POINTS_PER_DECADE)
        p.add_argument("--ekn-grid", help="N,LOW,HIGH: USINE's E_k/n grid given explicitly (N log-spaced nodes from "
                                          "LOW to HIGH GeV/n), replacing the derived one")
        p.add_argument("--data-dir", type=Path, default=os.environ.get("HEP_USINE_DATA"),
                       help="USINE's inputs folder (default $HEP_USINE_DATA)")
        p.add_argument("--phi", type=float, default=0.0,
                       help="force-field modulation potential in GV: USINE also writes the modulated isotope tables")
        p.add_argument("--usine-tolerance", action="append", default=[],
                       help="NAME=VALUE, one of EPS_ITERCONV, EPS_INTEGR, EPS_NORMDATA (default 1e-6, 1e-4, 1e-10)")
        p.add_argument("--production-modifiers", type=Path,
                       help="JSON list of {channel, norm, slope_le, threshold_ekn_gev} (USINE's own cross sections)")
        if name == "run":
            p.add_argument("--usine", type=Path, default=os.environ.get("HEP_USINE_BIN"),
                           help="the usine executable (default $HEP_USINE_BIN)")
            p.add_argument("--record", type=Path, help="computational-run record to write")
            p.add_argument("--environment", type=Path, help="environment manifest (environment_manifest.py record)")
            p.add_argument("--timeout", type=float, default=3600.0)
    args = ap.parse_args(argv)
    try:
        lo, hi = (float(x) for x in args.ekn_range.split(","))
        grid = None
        if args.ekn_grid:
            n_points, g_lo, g_hi = args.ekn_grid.split(",")
            grid = {"n_points": int(n_points), "ekn_min_gev": float(g_lo), "ekn_max_gev": float(g_hi)}
        mods = (json.loads(args.production_modifiers.read_text(encoding="utf-8"))
                if args.production_modifiers else None)
        spec = translate(load_transport(args.transport), args.name, (lo, hi), args.points_per_decade, grid,
                         phi_gv=args.phi, production_modifiers=mods,
                         tolerances=dict(t.split("=", 1) for t in args.usine_tolerance))
        env = json.loads(args.environment.read_text(encoding="utf-8")) if getattr(args, "environment", None) else None
    except (OSError, ValueError) as exc:  # SpecError is a ValueError
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    try:
        usine_input_paths(spec, args.data_dir)
    except UsineDataMissing as exc:
        print(json.dumps({"status": "missing-dependency", "error": str(exc)}))
        return 3
    if args.data_dir is None or not Path(args.data_dir).is_dir():
        print(json.dumps({"status": "missing-dependency",
                          "error": "USINE inputs folder not found: pass --data-dir or set HEP_USINE_DATA"}))
        return 3
    if args.command == "translate":
        try:
            inputs = prepare(spec, args.out, args.data_dir)
            inputs.update(prepare_derived(spec, args.out, args.data_dir))
            notes = check_half_lives(spec, args.data_dir)
        except (OSError, SpecError) as exc:
            print(json.dumps({"status": "error", "error": str(exc)}))
            return 2
        (args.out / "translation.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "prepared", "run_dir": str(args.out), "inputs": inputs, "notes": notes}))
        return 0
    if args.usine is None or not Path(args.usine).is_file() or not os.access(args.usine, os.X_OK):
        print(json.dumps({"status": "missing-dependency",
                          "error": "USINE executable not found: pass --usine or set HEP_USINE_BIN"}))
        return 3
    try:
        result = run_usine(spec, args.out, args.usine, args.data_dir, args.timeout)
    except (OSError, SpecError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    (Path(args.out) / "translation.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    rec = record(spec, result, args.usine, env)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok" if result["ok"] else "failed", "exit_status": result["exit_status"],
                      "run_dir": str(args.out), "wall_seconds": round(result["seconds"], 2),
                      "record": str(args.record) if args.record else None,
                      **({} if result["ok"] else {"log_tail": result["log_tail"]})}))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
