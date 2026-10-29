#!/usr/bin/env python3
"""cr-propagation D3: two-level cross-code comparison of DRAGON2 and USINE (GALPROP unavailable, decisions A1.2).

Criteria and tolerances: VALIDATION.md section CRPROP-D3 (fixed before any comparison). Level 1 compares the two codes
on the same transport blocks (harmonized-v1 and D1's harmonized-v1-<item> files), each translated by its adapter
(adapters/cr-propagation/assets/usine_translate.py and dragon2_run.py). The matched level 1 (D3-3) gives USINE the
settings DRAGON2 cd588707 fixes in its code: helium target He/H = 0.11 with GALPROP's He_to_H_CS_ratio on production,
DRAGON2's own inelastic cross sections (Barashenkov-Polanski 'sighad', CROSEC option 2, evaluated by DRAGON2's own
compiled code; DRAGON2-INELASTIC below), the gas columns of DRAGON2's gas at the observer, and DRAGON2's propagated O/C
at the normalisation energy. Level 2 (D3-2) runs each code with its own default inputs at the same transport and
attributes the difference with USINE runs that swap one input at a time for DRAGON2's.

The USINE runs change the translation only after usine_translate.translate (gas densities and targets, the
cross-section tables with a helium column, the parent ratio) and never edit USINE's files: the tables derived from
DRAGON2's data (production table, inelastic values) are written into the run folder outside the repository; only
numbers computed from runs are committed (DRAGON2's data files are not; USINE is GPL-2.0).

Runs (names):
  DRAGON2   D3_harmonized_v1   harmonized-v1 (set A) translated by dragon2_run.spec_from_transport
            D3_l2_dragon2      harmonized-v1-isotopic with DRAGON2's shipped production table (Evoli 2019,
                               cumulative) and source abundances: level 2
  USINE     m-<config>         matched level 1 (D3-3) of each configuration
            l-<step>           attribution ladder of the isotopic item-off configuration (one matched setting at a time)
            u-l2-<step>        level 2: USINE defaults, then DRAGON2's inputs swapped in one at a time

Usage:
  python3 d3_study.py inelastic --build DIR --out dragon2-inelastic.json    # needs HEP_DRAGON2_BIN, HEP_DRAGON2_DATA, gfortran
  python3 d3_study.py dragon2-specs --out DIR                                # writes the DRAGON2 run specs
  python3 d3_study.py usine --out DIR [--jobs 4] [--only SUBSTRING]          # needs HEP_USINE_BIN, HEP_USINE_DATA
                                                                             # (and HEP_DRAGON2_DATA for level 2)
  python3 d3_study.py analyze --usine-out DIR --dragon2-out DIR --results d3-results.json
Output: JSON on stdout. Exit 0 ok, 1 a run failed, 2 bad input, 3 a program or data folder is missing.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import functools
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE.parent
PLUGIN_ROOT = HERE.parents[4]
sys.dont_write_bytecode = True
ASSETS = PLUGIN_ROOT / "adapters" / "cr-propagation" / "assets"
for p in (PLUGIN_ROOT, ASSETS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import dragon2_run as dr  # noqa: E402
import dragon2_to_prediction as dconv  # noqa: E402
import dragon2_translate as dt  # noqa: E402
import usine_to_prediction as rd  # noqa: E402
import usine_translate as ut  # noqa: E402

SPECS = FIX / "specs"
D1_FIX = FIX / "dragon2"
TOLERANCE = 0.05  # D3-1 and D3-3, frozen in acceptance.json and VALIDATION CRPROP-D3 before the comparison
BORON_CARBON_EDGES = [2.0 * 500.0 ** (k / 16) for k in range(17)]  # 16 log-uniform rigidity bins 2-1000 GV (B1, D1)
BERYLLIUM_EDGES = [0.05 * 200.0 ** (k / 12) for k in range(13)]  # 12 log-uniform E_k/n bins 0.05-10 GeV/n (B1, D1)
DRAGON2_NUM, DRAGON2_DEN = ["NUC_5010", "NUC_5011"], ["NUC_6012", "NUC_6013", "NUC_6014"]
DRAGON2_OXYGEN, DRAGON2_NITROGEN = ["NUC_8016", "NUC_8017", "NUC_8018"], ["NUC_7014", "NUC_7015"]
EKN_RANGE = (0.04, 2000.0)  # every D1 and B1 run of these configurations
Z_RANGE = (4, 8)  # D1's DRAGON2 network
NORM_EKN_GEV = ut.NORM_EKN_GEV

# ------------------------------------------------------------------ DRAGON2 cd588707's fixed settings

HELIUM_ABUNDANCE = 0.11  # include/constants.h He_abundance; galaxy.cc _fGasAbundances[2004]
H_KPC = 0.1  # USINE thin-disc half-thickness of every configuration (disc_halfwidth_pc 100)
OBSERVER_KPC = 8.3
GALPROP_GAS_STEP_KPC = 0.01  # include/constants.h dzzGal
KPC_CM_DRAGON2 = 3.08568e21  # include/constants.h kpc
XCO_SM96 = 1.9  # gas.cc X_CO, case SM96 (the translator's XCOmode)
TABLE_NODES_PER_DECADE = 20
XS_GRID_GEV = ut.XS_GRID_GEV
NETWORK_L2 = ("1H", "2H", "3He", "4He", "6Li", "7Li", "7Be", "9Be", "10Be", "10B", "11B", "12C", "13C", "14C", "14N",
              "15N", "16O")  # USINE's chart crcharts_Zmax30_ghost97 from 1H to 16O
INELASTIC_NUCLIDES = tuple(n for n in NETWORK_L2 if ut.charge_and_mass(n)[0] >= 3)


def table_nodes() -> list[float]:
    lo, hi = XS_GRID_GEV
    n = round(TABLE_NODES_PER_DECADE * math.log10(hi / lo)) + 1
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def helium_production_ratio(e_gev_n: float, zi: int, ai: int, zf: int, af: int) -> float:
    """DRAGON2's TGalpropXSec::He_to_H_CS_ratio (xsec.cc 2364-2410, from GALPROP; Ferrando et al. 1988): DRAGON2
    multiplies every tabulated production cross section on H by 1 + 0.11 times this ratio (xsec.cc 145)."""
    def fi(x, x1, x2, y1, y2):
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    en, d, am, z, f = [0.43, 0.73, 1.51], [2.45, 3.45, 4.40], [0.082, 0.047, 0.031], [6.0, 8.0, 26.0], [-0.76, -0.41, 1.0]
    if ai <= af:
        return 0.0
    if e_gev_n < en[1]:
        amu, delta = fi(e_gev_n, en[0], en[1], am[0], am[1]), fi(math.log(e_gev_n), math.log(en[0]), math.log(en[1]),
                                                                   d[0], d[1])
    else:
        amu, delta = fi(e_gev_n, en[1], en[2], am[1], am[2]), fi(math.log(e_gev_n), math.log(en[1]), math.log(en[2]),
                                                                   d[1], d[2])
    if e_gev_n < en[0]:
        amu, delta = am[0], d[0]
    if e_gev_n > en[2]:
        amu, delta = am[2], d[2]
    fz = fi(math.log(zi), math.log(z[0]), math.log(z[1]), f[0], f[1]) if zi < z[1] else \
        fi(math.log(zi), math.log(z[1]), math.log(z[2]), f[1], f[2])
    if zi - zf <= zi // 2:
        return math.exp(amu * abs(zi - zf - fz * delta) ** 1.43)
    x = math.exp(amu * abs(zi // 2 - fz * delta) ** 1.43)
    y = x - math.exp(amu * abs(zi // 2 - 1 - fz * delta) ** 1.43)
    b = (zi // 2) * y / x
    return x / (zi // 2) ** b * (zi - zf) ** b


def helium_inelastic_ratio(a: int) -> float:
    """DRAGON2's He_to_H_CS_totratio (include/xsec.h 465): sigma_inel(He) / sigma_inel(H) = 2.10 / A^0.055."""
    return 2.10 / a ** 0.055


def _z_grid(l_kpc: float, dz: float) -> list[float]:
    n = int(round(2 * l_kpc / dz)) + 1
    return [-l_kpc + i * dz for i in range(n)]


def bronf_ferr_density(r_kpc: float, z_kpc: float) -> dict:
    """DRAGON2 gas.cc, case BronfFerr: H2 (molecules) and HI density (cm^-3); HII is 0."""
    h2_h = 0.059 if r_kpc > 2.5 else 0.015
    h2 = (150.0 * math.exp(-((r_kpc - 0.05) / 0.2) ** 2) + 0.49 * math.exp(-((r_kpc - 5.3) / 2.2) ** 2)
          + 0.24 * math.exp(-((r_kpc - 8.1) / 1.5) ** 2)) * math.exp(-math.log(2) * (z_kpc / h2_h) ** 2)
    if r_kpc < 2.5:
        hi_h = 0.045
    elif r_kpc < 8.5:
        hi_h = 0.115
    else:
        hi_h = 0.115 * math.exp((r_kpc - 8.5) / 6.7)
    if r_kpc < 3.0:
        hi_n = 0.57 * math.exp((r_kpc - 3.0) / 0.4) + 8.0 * math.exp(-(r_kpc / 0.2) ** 2)
    elif r_kpc < 13.0:
        hi_n = 0.57
    else:
        hi_n = 0.57 * math.exp(-(r_kpc - 13.0) / 4.0)
    return {"HI": hi_n * math.exp(-math.log(2) * (z_kpc / hi_h) ** 2), "HII": 0.0, "H2": h2}


def _galprop_h2(r: float, z: float) -> float:
    rr = [0.00, 2.25, 2.75, 3.25, 3.75, 4.25, 4.75, 5.25, 5.75, 6.25, 6.75, 7.25, 7.75, 8.25, 8.75, 9.25, 9.75, 10.25]
    yy = [0.00, 1.5, 3.3, 5.8, 5.5, 8.4, 9.0, 9.6, 8.6, 9.1, 7.9, 9.2, 7.7, 5.0, 3.6, 4.8, 1.7, 0.0]
    z0 = [0.039, 0.039, 0.036, 0.000, -.008, 0.001, -.010, -.001, -.004, -.019, -.022, -.014, -.009, -.004, 0.013,
          -.004, -.020, -.020]
    zh = [0.077, 0.077, 0.080, 0.061, 0.065, 0.071, 0.072, 0.082, 0.083, 0.073, 0.063, 0.058, 0.072, 0.080, 0.066,
          0.023, 0.147, 0.147]
    if r > rr[17]:
        return 0.0
    i = 0
    while i < 17 and not (rr[i] <= r <= rr[i + 1]):
        i += 1
    f_r = yy[i] + (yy[i + 1] - yy[i]) / (rr[i + 1] - rr[i]) * (r - rr[i])
    f_z0 = z0[i] + (z0[i + 1] - z0[i]) / (rr[i + 1] - rr[i]) * (r - rr[i])
    f_zh = zh[i] + (zh[i + 1] - zh[i]) / (rr[i + 1] - rr[i]) * (r - rr[i])
    val = f_r * math.exp(-math.log(2.) * ((z - f_z0) / f_zh) ** 2) * XCO_SM96 * 1e20 / KPC_CM_DRAGON2
    return max(val, 0.0)


def _galprop_hi(r: float, z: float) -> float:
    rr = [0.0, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5,
          12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0]
    yy = [.10, .13, .14, .16, .19, .25, .30, .33, .32, .31, .30, .37, .38, .36, .32, .29, .38, .40, .25, .23, .32, .36,
          .32, .25, .16, .10, .09, .08, .06, .00]
    n_gb, n_dl = 0.33, 0.57
    a1, z1, a2, z2, b, zh = 0.395, 0.212 / 2., 0.107, 0.530 / 2., 0.064, 0.403
    i = 0
    while i < 29 and not (rr[i] <= r <= rr[i + 1]):
        i += 1
    f_r = 0.0  # beyond 16 kpc the C loop ends at i = 29 and only the extrapolation below sets f_r
    if i < 29:
        r1, y1 = (rr[i] + rr[i + 1]) / 2, yy[i]
        r2, y2 = rr[29], yy[29]
        if r < r1:
            if i > 0:
                r2, y2 = (rr[i - 1] + rr[i]) / 2, yy[i - 1]
            else:
                r2, y2 = rr[0], yy[0]
        elif i < 28:
            r2, y2 = (rr[i + 1] + rr[i + 2]) / 2, yy[i + 1]
        f_r = y1 + (y2 - y1) / (r2 - r1) * (r - r1)
    r2 = (rr[28] + rr[29]) / 2
    if r > r2:
        f_r = yy[28] * math.exp(-(r - r2) / 3)
    f_z1 = f_z2 = 0.0
    if r < 10.:
        f_z1 = a1 * math.exp(-math.log(2.) * (z / z1) ** 2) + a2 * math.exp(-math.log(2.) * (z / z2) ** 2) \
            + b * math.exp(-abs(z) / zh)
    if r > 8.:
        f_z2 = n_dl * math.exp(-(z / (0.0523 * math.exp(0.11 * r))) ** 2)
    if r <= 8.:
        f_z = f_z1
    elif r >= 10.:
        f_z = f_z2
    else:
        f_z = f_z1 + (f_z2 - f_z1) / 2. * (r - 8.)
    return f_z * f_r / n_gb


def _galprop_hii(r: float, z: float) -> float:
    return 0.025 * math.exp(-abs(z) / 1.0) * math.exp(-(r / 20.0) ** 2) \
        + 0.200 * math.exp(-abs(z) / 0.15) * math.exp(-((r - 4.0) / 2.0) ** 2)


def galprop_density(r_kpc: float, z_kpc: float, dz: float) -> dict:
    """DRAGON2 gas.cc, case Galprop: nH2_av, nHI_av, nHII_av (averages over the cell in steps dzzGal)."""
    out = {}
    for key, fn in (("H2", _galprop_h2), ("HI", _galprop_hi), ("HII", _galprop_hii)):
        total, n, zz = 0.0, 0, z_kpc - dz / 2.
        while zz <= z_kpc + dz / 2.:
            total += fn(r_kpc, zz)
            n += 1
            zz += GALPROP_GAS_STEP_KPC
        out[key] = total / n
    return out


def gas_columns(model: str, r_kpc: float, l_kpc: float, dz: float) -> dict:
    """Columns sum_l n(z_l) dz (kpc cm^-3) of HI, HII and H2 (molecules) on DRAGON2's z grid, and the hydrogen
    nucleon column HI + HII + 2 H2 (DRAGON2's total gas, galaxy.cc 521-523)."""
    col = {"HI": 0.0, "HII": 0.0, "H2": 0.0}
    for z in _z_grid(l_kpc, dz):
        dens = bronf_ferr_density(r_kpc, z) if model == "BronfFerr" else galprop_density(r_kpc, z, dz)
        for k in col:
            col[k] += dens[k] * dz
    col["nucleons"] = col["HI"] + col["HII"] + 2.0 * col["H2"]
    return col


def thin_disc_gas(model: str, l_kpc: float = 4.0, dz: float = 0.02) -> dict:
    """USINE thin-disc densities (cm^-3) with DRAGON2's columns at the observer: n = column / (2 h); He = 0.11 times
    the hydrogen nucleon density."""
    col = gas_columns(model, OBSERVER_KPC, l_kpc, dz)
    gas = {k: col[k] / (2 * H_KPC) for k in ("HI", "HII", "H2")}
    gas["He"] = HELIUM_ABUNDANCE * col["nucleons"] / (2 * H_KPC)
    return gas


# ------------------------------------------------------------------ DRAGON2's inelastic cross sections (own code)

DRIVER_SOURCE = r"""/* written by d3_study.py (cr-propagation D3): DRAGON2 cd588707's inelastic cross section of a nucleus (Z, A) on
   hydrogen, as TGalpropXSec::GetXSec(uid) computes it for SpallationXSec DRAGON2 (xsec.cc 2283-2317: nucleon_cs
   option 2, Barashenkov-Polanski sighad of crn6.f, energy clamped to 14 MeV - 1e6 MeV). Usage: inel Z A E1 E2 ...
   (GeV/n); run where data/galprop_barpol.dat is reachable. */
#include <stdio.h>
#include <stdlib.h>
extern void sigtap2_(int*);
extern double sighad_(int*, double*, double*, double*, double*, double*);
int main(int argc, char** argv) {
  int iss = -1; sigtap2_(&iss);
  int z = atoi(argv[1]), a = atoi(argv[2]);
  for (int i = 3; i < argc; ++i) {
    double ek = atof(argv[i]), em = 1000. * ek;
    if (em < 14.) em = 14.;
    if (em > 1.e6) em = 1.e6;
    int is = 2; double pa = 1., pz = 1., ta = a, tz = z;
    printf("%.9e %.9e\n", ek, sighad_(&is, &pa, &pz, &ta, &tz, &em));
  }
  return 0;
}
"""


def build_inelastic_driver(build_dir: Path, binary: Path, data_dir: Path) -> Path:
    library = Path(binary).resolve().parent.parent / "lib" / "libDRAGON.a"
    if not library.is_file():
        raise FileNotFoundError(f"{library} (DRAGON2's static library next to HEP_DRAGON2_BIN)")
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "data").mkdir(exist_ok=True)
    link = build_dir / "data" / "galprop_barpol.dat"
    if not link.exists():
        link.symlink_to(Path(data_dir).resolve() / "galprop_barpol.dat")
    (build_dir / "inel.c").write_text(DRIVER_SOURCE, encoding="utf-8")
    # One-file gfortran compile and link takes seconds; 600 s is a generous bound. subprocess.TimeoutExpired
    # propagates to the caller (raised, like check=True failures), never swallowed.
    subprocess.run(["gfortran", "-O2", "-o", "inel", "inel.c", str(library)], cwd=build_dir, check=True,
                   timeout=600)
    return build_dir / "inel"


def dragon2_inelastic(build_dir: Path, binary: Path, data_dir: Path) -> dict:
    exe = build_inelastic_driver(build_dir, binary, data_dir)
    nodes = table_nodes()
    sigma = {}
    for nuc in INELASTIC_NUCLIDES:
        z, a = ut.charge_and_mass(nuc)
        out = subprocess.run([str(exe), str(z), str(a)] + [f"{e:.9e}" for e in nodes], cwd=build_dir,
                             capture_output=True, text=True, check=True,
                             timeout=600).stdout.split()  # per-nuclide table lookup, milliseconds; raises on timeout
        sigma[nuc] = [float(v) for v in out[1::2]]
    return {"label": "DRAGON2-INELASTIC: inelastic cross sections (mb) of nuclei on hydrogen as DRAGON2 cd588707 "
                     "computes them for SpallationXSec DRAGON2 (CROSEC, nucleon_cs option 2: Barashenkov-Polanski "
                     "sighad, crn6.f, via xsec.cc TGalpropXSec::GetXSec(uid)), evaluated by DRAGON2's own compiled "
                     "code (libDRAGON.a, d3_study.py DRIVER_SOURCE) on the D3 table grid; DRAGON2 adds helium as "
                     "sigma (1 + 0.11 x 2.10 / A^0.055) (xsec.cc 2310-2317). Numbers computed from DRAGON2's code; no "
                     "DRAGON2 data file is copied",
            "program": "DRAGON2-Beta_version git cd588707fe03c76f19bda1b8092e136dcbe3fe90",
            "ekn_gev": nodes, "sigma_h_mb": sigma,
            "he_over_h": {n: helium_inelastic_ratio(ut.charge_and_mass(n)[1]) for n in INELASTIC_NUCLIDES}}


def load_inelastic() -> dict:
    return json.loads((HERE / "dragon2-inelastic.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ DRAGON2's production table on USINE's grid

def _uid(text: str) -> tuple[int, int]:
    z, a = text.split(".")
    return int(z), int(a)


def read_dragon2_production(data_dir: Path) -> dict:
    """DRAGON2's shipped production table (Parent Z.AA, Daughter Z.AA, E in MeV/n, sigma on H in mb): (zp, ap, zc,
    ac) -> (energies GeV/n, sigma)."""
    table: dict = {}
    for line in (Path(data_dir) / dr.TABLE_NAME).read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        key = _uid(parts[0]) + _uid(parts[1])
        e, s = table.setdefault(key, ([], []))
        e.append(float(parts[2]) / 1000.0)
        s.append(float(parts[3]))
    return table


def dragon2_interpolate(es: list[float], ys: list[float], e: float) -> float:
    """TSpallationNetwork::GetXSecPair (xsec.cc 1986-2040): linear in E inside the table, linear extrapolation from the
    end segment, frozen beyond 7 times the last (or below the first / 7) node, clipped at 0."""
    if e > es[-1]:
        t = (min(e, 7.0 * es[-1]) - es[-1]) / (es[-1] - es[-2])
        return max(ys[-1] + t * (ys[-1] - ys[-2]), 0.0)
    if e < es[0]:
        t = (max(e, es[0] / 7.0) - es[0]) / (es[1] - es[0])
        return max(ys[0] + t * (ys[1] - ys[0]), 0.0)
    j = 0
    while e > es[j]:
        j += 1
    if j == 0:
        return ys[0]
    return ys[j - 1] + (ys[j] - ys[j - 1]) * (e - es[j - 1]) / (es[j] - es[j - 1])


# ------------------------------------------------------------------ USINE tables with a helium column

def xs_table(title: str, nodes: list[float], rows: list[tuple[str, list[float], list[float] | None]],
             helium: bool) -> str:
    lines = [f"# {title}", "# written by d3_study.py (cr-propagation D3); not data", "#  Type  Unit     Targets",
             " sigma    mb      H,He" if helium else " sigma    mb      H", "",
             "# EknMIN[GeV/n]   EknMAX[GeV/n]   nEkn  (PROJECTILE GRID)",
             f"{nodes[0]:.6e}      {nodes[-1]:.6e}    {len(nodes)}", ""]
    for label, h_vals, he_vals in rows:
        lines.append(label)
        for i, v in enumerate(h_vals):
            lines.append(f"{v:.9e}\t{he_vals[i]:.9e}" if helium else f"{v:.9e}")
        lines.append("")
    return "\n".join(lines)


def read_usine_xs(path: Path) -> tuple[list[float], dict]:
    """A USINE cross-section file (read in place, never copied): projectile grid and label -> list of per-target
    rows."""
    lines = [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    body = [ln for ln in lines if ln and not ln.startswith("#")]
    lo, hi, n = float(body[1].split()[0]), float(body[1].split()[1]), int(body[1].split()[2])
    grid = [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]
    out, i = {}, 2
    while i < len(body):
        label = body[i]
        out[label] = [[float(x) for x in body[i + 1 + k].split()] for k in range(n)]
        i += 1 + n
    return grid, out


def _loglin(grid: list[float], vals: list[float], e: float) -> float:
    if e <= grid[0]:
        return vals[0]
    if e >= grid[-1]:
        return vals[-1]
    j = 1
    while grid[j] < e:
        j += 1
    t = math.log(e / grid[j - 1]) / math.log(grid[j] / grid[j - 1])
    return vals[j - 1] + t * (vals[j] - vals[j - 1])


# ------------------------------------------------------------------ run plan

def _load(name: str) -> dict:
    return json.loads((SPECS / f"{name}.json").read_text(encoding="utf-8"))


MATCH_ALL = {"gas": "match", "helium": True, "inelastic": "dragon2", "parent_ratio": "dragon2", "injection_eta": -1.0}
LEVEL1_CONFIGS = {  # configuration -> (transport file, DRAGON2 run of the same block, DRAGON2 gas)
    "harmonized-v1": ("harmonized-v1", "D3_harmonized_v1", "BronfFerr"),
    "isotopic": ("harmonized-v1-isotopic", "D1_isotopic", "BronfFerr"),
    "convection": ("harmonized-v1-convection", "D1_convection", "BronfFerr"),
    "decay": ("harmonized-v1-decay", "D1_decay", "BronfFerr"),
    "reacceleration": ("harmonized-v1-reacceleration", "D1_reacceleration", "BronfFerr"),
    "losses-off": ("harmonized-v1-isotopic", "D1_losses_off", "Galprop"),
    "losses": ("harmonized-v1-losses", "D1_losses", "Galprop"),
}
USINE_LEVEL1_RUNS = {  # configuration -> B1's recorded USINE run of the same block (reused, not rerun)
    "harmonized-v1": "harmonized-v1", "isotopic": "d1-isotopic", "convection": "d1-convection", "decay": "d1-decay",
    "reacceleration": "d1-reacceleration", "losses-off": "d1-isotopic", "losses": "d1-losses"}
LADDER = (  # isotopic item-off: one matched setting switched on per step (the last step is m-isotopic)
    ("l-gas", {"gas": "match", "helium": False, "inelastic": "illustrative", "parent_ratio": "profile"}),
    ("l-helium", {"gas": "match", "helium": True, "inelastic": "illustrative", "parent_ratio": "profile"}),
    ("l-inelastic", {"gas": "match", "helium": True, "inelastic": "dragon2", "parent_ratio": "profile"}),
    ("l-parent-ratio", {"gas": "match", "helium": True, "inelastic": "dragon2", "parent_ratio": "dragon2"}),
)
L2_STEPS = (  # USINE level 2: its defaults, then DRAGON2's inputs swapped in one at a time (cumulative)
    ("u-l2-usine", {}),
    ("u-l2-production", {"production": "dragon2"}),
    ("u-l2-inelastic", {"production": "dragon2", "inelastic": "dragon2"}),
    ("u-l2-gas", {"production": "dragon2", "inelastic": "dragon2", "gas": "dragon2"}),
    ("u-l2-abundances", {"production": "dragon2", "inelastic": "dragon2", "gas": "dragon2",
                         "abundances": "dragon2"}),
    ("u-l2-injection", {"production": "dragon2", "inelastic": "dragon2", "gas": "dragon2", "abundances": "dragon2",
                        "injection_eta": -1.0}),
)
USINE_DEFAULTS = {  # USINE V3.5's shipped example inputs/init.TEST.par (as B1X's b1x-init-test, numbers only)
    "production_set": "usine:XS_NUCLEI/sigProdGALPROP17_OPT12.dat",
    "inelastic_set": "usine:XS_NUCLEI/sigInelTripathi99+Coste12.dat",
    "gas": {"model": "uniform in the thin disc, n_HI = 0.867 cm^-3, n_HII = 0.033 cm^-3, n_H2 = 0 cm^-3",
            "He_to_H_number": 0.11111111111111112},
    "abundances": "data-normalised usine:crdata_crdb20170523.dat H,He:PAMELA@20;C,N,O:HEAO@10.6",
    "network_top": "O-16"}


GEOMETRY_CHECKS = ("isotopic", "losses-off", "losses")  # matched runs repeated with the gas scaled by geometry_factor


@functools.lru_cache(maxsize=None)
def geometry_factor(model: str) -> float:
    """High-energy estimate of the B/C effect of DRAGON2's gas geometry that a uniform thin disc cannot express:
    vertical extent of gas and sources times the radial gas profile (vertical_extent_estimate, radial_gas_estimate)."""
    return vertical_extent_estimate(model) * radial_gas_estimate(model)


def usine_plan() -> list[dict]:
    plan = [{"name": f"m-{cfg}", "kind": "matched", "config": cfg, "settings": dict(MATCH_ALL)}
            for cfg in LEVEL1_CONFIGS]
    plan += [{"name": n, "kind": "ladder", "config": "isotopic", "settings": dict(s)} for n, s in LADDER]
    plan += [{"name": n, "kind": "level2", "config": "isotopic", "settings": dict(s)} for n, s in L2_STEPS]
    plan += [{"name": f"a-{cfg}-geometry", "kind": "attribution", "config": cfg,
              "settings": dict(MATCH_ALL, gas_scale=geometry_factor(LEVEL1_CONFIGS[cfg][2]))} for cfg in GEOMETRY_CHECKS]
    return plan


def dragon2_observables(path: Path) -> dict:
    e, cols = dconv.read_output(path)
    out = {"B/C": dconv.ratio_of_bin_integrals(e, cols, DRAGON2_NUM, DRAGON2_DEN, BORON_CARBON_EDGES, "rigidity")}
    if "NUC_4010" in cols and any(cols["NUC_4010"]):
        out["10Be/9Be"] = dconv.ratio_of_bin_integrals(e, cols, ["NUC_4010"], ["NUC_4009"], BERYLLIUM_EDGES, "ekn")
    return out


def dragon2_element_ratio(path: Path, num: list[str], den: list[str], ekn: float) -> float:
    """Element ratio at equal E_k/n of a DRAGON2 output (columns per total kinetic energy, times A; P11)."""
    e, cols = dconv.read_output(path)
    vals = [sum(int(c[-3:]) * cols[c][i] for c in num if c in cols) / sum(int(c[-3:]) * cols[c][i] for c in den
                                                                          if c in cols) for i in range(len(e))]
    return rd.interpolate(e, vals, ekn)


def dragon2_output(run: str, dragon2_out: Path | None = None) -> Path:
    if run.startswith("D1_"):
        return D1_FIX / "outputs" / f"{run}.txt"
    return (dragon2_out / run / "output" / f"{run}.txt") if dragon2_out else HERE / "dragon2" / "outputs" / f"{run}.txt"


# ------------------------------------------------------------------ DRAGON2 specs

def dragon2_specs() -> dict:
    channels_a = {"6012->5011": 70.0, "8016->5011": 35.0}  # ILLUSTRATIVE set A on 12C, 16O and 11B (as USINE's B1)
    xs_a = json.loads((PLUGIN_ROOT / "profiles" / "theory" / "cr-secondary-ratio" / "models" / "xs-illustrative-A.json")
                      .read_text(encoding="utf-8"))
    if {"6012->5011": xs_a["production_mb"]["C->B"], "8016->5011": xs_a["production_mb"]["O->B"]} != channels_a:
        raise ValueError("set A changed in the profile")
    # DRAGON2's own sources stated (K3, escalation 12): the runs were made with them; harmonized-v1's are refused
    h1 = dt.spec_from_transport(dt.with_dragon2_sources(_load("harmonized-v1")["transport"]), "D3_harmonized_v1",
                                channels_a, z_range=Z_RANGE, ekn_range_gev=EKN_RANGE)
    h1["substitutes"].append("D3: element-level ILLUSTRATIVE set A placed on 12C -> 11B and 16O -> 11B (as USINE's "
                             "translation of the same block)")
    channels = json.loads((D1_FIX / "channels-illustrative-decay.json").read_text(encoding="utf-8"))
    l2 = dt.spec_from_transport(dt.with_dragon2_sources(_load("harmonized-v1-isotopic")["transport"]), "D3_l2_dragon2",
                                channels, z_range=Z_RANGE, ekn_range_gev=EKN_RANGE)
    del l2["production_table"]
    l2["substitutes"].append("D3 level 2: no production_table; DRAGON2's shipped production table "
                             f"{dr.TABLE_NAME} (Evoli 2019, cumulative, helium by He_to_H_CS_ratio) and the source "
                             "abundances of BaseModel_DRAGONxsec.source.param are used (DRAGON2's defaults)")
    return {"D3_harmonized_v1": h1, "D3_l2_dragon2": l2}


# ------------------------------------------------------------------ USINE runs

def _parent_ratio(cfg: str, dragon2_out: Path | None, element: str = "O") -> float:
    run = LEVEL1_CONFIGS[cfg][1]
    num = DRAGON2_OXYGEN if element == "O" else DRAGON2_NITROGEN
    return dragon2_element_ratio(dragon2_output(run, dragon2_out), num, DRAGON2_DEN, NORM_EKN_GEV)


def matched_spec(item: dict, dragon2_out: Path | None = None) -> tuple[dict, dict]:
    """Translation of a matched or ladder run and the D3 settings applied (recorded in the translation)."""
    cfg = item["config"]
    tfile, _, gas_model = LEVEL1_CONFIGS[cfg]
    s = item["settings"]
    spec = ut.translate(_load(tfile)["transport"], item["name"], EKN_RANGE)
    applied = {}
    if s["gas"] == "match":
        gas = thin_disc_gas(gas_model)
        if not s["helium"]:
            gas["He"] = 0.0
        if s.get("gas_scale"):
            gas = {k: v * s["gas_scale"] for k, v in gas.items()}
        spec["gas_cm3"] = gas
        spec["targets"] = ["H", "He"] if gas["He"] > 0 else ["H"]
        applied["gas_cm3"] = gas
        applied["gas_note"] = (f"DRAGON2 {gas_model} columns at r = {OBSERVER_KPC} kpc on its z grid (L 4 kpc, dz 0.02) "
                               f"divided by 2 h = {2 * H_KPC} kpc" + ("; He = 0.11 (HI + HII + 2 H2)" if s["helium"]
                                                                       else "; no helium")
                               + (f"; all densities x {s['gas_scale']:.6g} (geometry_factor, attribution check)"
                                  if s.get("gas_scale") else ""))
    if s["parent_ratio"] == "dragon2":
        spec["norm_points"] = dict(spec["norm_points"], O=_parent_ratio(cfg, dragon2_out))
        applied["norm_points"] = spec["norm_points"]
    if s.get("injection_eta") is not None:
        spec["source"] = dict(spec["source"], eta_s=s["injection_eta"])
        applied["source_eta_s"] = s["injection_eta"]
    applied.update(helium=s["helium"], inelastic=s["inelastic"])
    spec["d3_settings"] = applied
    spec["substitutes"] = spec["substitutes"] + [f"D3 {item['kind']} run: {json.dumps(applied, sort_keys=True)}"]
    return spec, applied


def matched_files(spec: dict, item: dict, data_dir: str, run_dir: str) -> dict:
    files = ut.render(spec, data_dir, run_dir)
    s = item["settings"]
    helium = s["helium"]
    nodes = table_nodes()
    sp = spec["species"]
    prod_rows = []
    for p in sp:
        for c in sp:
            if p == c or ut.charge_and_mass(c)[1] > ut.charge_and_mass(p)[1]:
                continue
            sig = spec["production_mb"].get(f"{p}->{c}", 0.0)
            zp, ap = ut.charge_and_mass(p)
            zc, ac = ut.charge_and_mass(c)
            he = [sig * helium_production_ratio(e, zp, ap, zc, ac) for e in nodes] if helium else None
            prod_rows.append((f"{p} -> {c}", [sig] * len(nodes), he))
    inel = load_inelastic() if s["inelastic"] == "dragon2" else None
    inel_rows = []
    for nuc in sp:
        a = ut.charge_and_mass(nuc)[1]
        if inel:
            h_vals = [_loglin(inel["ekn_gev"], inel["sigma_h_mb"][nuc], e) for e in nodes]
        else:
            h_vals = [spec["inelastic_mb"][nuc]] * len(nodes)
        inel_rows.append((nuc, h_vals, [v * helium_inelastic_ratio(a) for v in h_vals] if helium else None))
    files["xs_production.dat"] = xs_table("production cross sections (mb) on " + ("H and He" if helium else "H") +
                                          ", every pair of the network (ILLUSTRATIVE on H"
                                          + ("; He = H x DRAGON2's He_to_H_CS_ratio)" if helium else ")"),
                                          nodes, prod_rows, helium)
    files["xs_inelastic.dat"] = xs_table("inelastic cross sections (mb) on " + ("H and He" if helium else "H") + (
        " (DRAGON2-INELASTIC)" if inel else " (ILLUSTRATIVE)") + ("; He = H x 2.10 / A^0.055" if helium else ""),
        nodes, inel_rows, helium)
    return files


def level2_transport(settings: dict, dragon2_out: Path | None) -> dict:
    t = copy.deepcopy(_load("harmonized-v1-isotopic")["transport"])
    t["cross_sections"] = {"production_set": USINE_DEFAULTS["production_set"],
                           "inelastic_set": USINE_DEFAULTS["inelastic_set"],
                           "ghost_threshold": "off: ghost nuclei and tertiary chains off (IsLoadGhosts false)"}
    t["species"] = {"network_top": USINE_DEFAULTS["network_top"], "isotopic": True}
    t["sources"] = copy.deepcopy(dict(t["sources"], abundances=USINE_DEFAULTS["abundances"]))
    t["gas"] = dict(USINE_DEFAULTS["gas"])
    if settings.get("injection_eta") is not None:
        t["sources"]["injection"] = [dict(i, eta=settings["injection_eta"]) for i in t["sources"]["injection"]]
    if settings.get("gas") == "dragon2":
        g = thin_disc_gas("BronfFerr")
        t["gas"] = {"model": f"n_H = {g['HI'] + 2 * g['H2']:.10g} cm^-3 (DRAGON2 BronfFerr nucleon column at the "
                             "observer / 2 h)",
                    "He_to_H_number": HELIUM_ABUNDANCE}
    return t


def level2_files(spec: dict, settings: dict, data_dir: str, run_dir: str, dragon2_data: Path | None,
                 dragon2_out: Path | None) -> dict:
    files = ut.render(spec, data_dir, run_dir)
    init = files["usine.init.par"]
    nodes = table_nodes()
    net = list(NETWORK_L2)
    if settings.get("production") == "dragon2":
        table = read_dragon2_production(dragon2_data)
        rows = []
        for p in net:
            for c in net:
                zp, ap = ut.charge_and_mass(p)
                zc, ac = ut.charge_and_mass(c)
                if p == c or ac > ap:
                    continue
                key = (zp, ap, zc, ac)
                if key in table and zc > 2:
                    es, ys = table[key]
                    he_nodes = [y * helium_production_ratio(e, zp, ap, zc, ac) for e, y in zip(es, ys)]
                    rows.append((f"{p} -> {c}", [dragon2_interpolate(es, ys, e) for e in nodes],
                                 [dragon2_interpolate(es, he_nodes, e) for e in nodes]))
                else:
                    rows.append((f"{p} -> {c}", [0.0] * len(nodes), [0.0] * len(nodes)))
        files["xs_production.dat"] = xs_table("production cross sections (mb) on H and He: DRAGON2's shipped table "
                                              "(Evoli 2019, cumulative) on H, He = H x He_to_H_CS_ratio at the table "
                                              "nodes; channels into Z <= 2 zero (no B/C effect)", nodes, rows, True)
        init = init.replace(f"{data_dir}/{USINE_DEFAULTS['production_set'][6:]}", f"{run_dir}/xs_production.dat")
    if settings.get("inelastic") == "dragon2":
        inel = load_inelastic()
        usine_data = os.environ.get("HEP_USINE_DATA")
        if not usine_data:
            raise FileNotFoundError("HEP_USINE_DATA: USINE's inelastic file is read in place for 1H-4He")
        grid, own = read_usine_xs(Path(usine_data) / USINE_DEFAULTS["inelastic_set"][6:])
        rows = []
        for nuc in net:
            if nuc in inel["sigma_h_mb"]:
                h_vals = [_loglin(inel["ekn_gev"], inel["sigma_h_mb"][nuc], e) for e in nodes]
                rows.append((nuc, h_vals, [v * inel["he_over_h"][nuc] for v in h_vals]))
            else:
                rows.append((nuc, [_loglin(grid, [r[0] for r in own[nuc]], e) for e in nodes],
                             [_loglin(grid, [r[1] for r in own[nuc]], e) for e in nodes]))
        files["xs_inelastic.dat"] = xs_table("inelastic cross sections (mb) on H and He: DRAGON2-INELASTIC for Z >= 3 "
                                             "(He = H x 2.10 / A^0.055); 1H-4He interpolated from USINE's own file",
                                             nodes, rows, True)
        init = init.replace(f"{data_dir}/{USINE_DEFAULTS['inelastic_set'][6:]}", f"{run_dir}/xs_inelastic.dat")
    if settings.get("abundances") == "dragon2":
        run = dragon2_output("D3_l2_dragon2", dragon2_out)
        n_c = dragon2_element_ratio(run, DRAGON2_NITROGEN, DRAGON2_DEN, NORM_EKN_GEV)
        o_c = dragon2_element_ratio(run, DRAGON2_OXYGEN, DRAGON2_DEN, NORM_EKN_GEV)
        e = NORM_EKN_GEV
        rows = ["# normalisation points written by d3_study.py: DRAGON2's propagated C, N, O at one E_k/n (not data)"]
        for element, value in (("C", 1.0), ("N", n_c), ("O", o_c)):
            rows.append(f"{element}   NORM   EKN   {e:.6e} {0.9 * e:.6e} {1.1 * e:.6e}   {value:.6e} {-1e-2 * value:.6e} "
                        f"{1e-2 * value:.6e} -0.000000e+00 0.000000e+00   none   0.000000e+00   1   "
                        "2000/01/01-000000:2000/01/02-000000 0")
        files["norm_points.dat"] = "\n".join(rows) + "\n"
        old = [ln for ln in init.splitlines() if "@ CRData @ NormList @" in ln][0]
        init = init.replace(old, "Base @ CRData @ NormList @ M=0 @ H,He:PAMELA|20|kEkn;C,N,O:NORM|10|kEkn")
        fcr = [ln for ln in init.splitlines() if "@ CRData @ fCRData @" in ln][0]
        init = init.replace(fcr, fcr + f"\nBase @ CRData @ fCRData @ M=1 @ {run_dir}/norm_points.dat")
    files["usine.init.par"] = init
    return files


def item_spec_and_files(item: dict, data_dir: str, run_dir: str, dragon2_data, dragon2_out) -> tuple[dict, dict]:
    if item["kind"] == "level2":
        spec = ut.translate(level2_transport(item["settings"], dragon2_out), item["name"], EKN_RANGE)
        spec["d3_settings"] = item["settings"]
        spec["substitutes"] = spec["substitutes"] + [f"D3 level 2 run: {json.dumps(item['settings'], sort_keys=True)}"]
        return spec, level2_files(spec, item["settings"], data_dir, run_dir, dragon2_data, dragon2_out)
    spec, _ = matched_spec(item, dragon2_out)
    return spec, matched_files(spec, item, data_dir, run_dir)


def execute(item: dict, out: Path, binary: Path, data_dir: Path, dragon2_data: Path | None,
            dragon2_out: Path | None) -> dict:
    run_dir = (out / "runs" / item["name"]).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    spec, files = item_spec_and_files(item, str(Path(data_dir).resolve()), str(run_dir), dragon2_data, dragon2_out)
    inputs = {}
    for fname, text in files.items():
        (run_dir / fname).write_text(text, encoding="utf-8")
        inputs[fname] = ut.sha256(run_dir / fname)
    notes = ut.check_half_lives(spec, data_dir)
    read_in_place = {f"<TOOL_HOME>/inputs/{rel}": ut.sha256(Path(data_dir) / rel)
                     for rel in spec.get("usine_inputs", {}).values() if f"{data_dir}/{rel}" in files["usine.init.par"]
                     or str(Path(data_dir).resolve() / rel) in files["usine.init.par"]}
    command = [str(Path(binary).resolve()), "-l", str(run_dir / "usine.init.par"), str(run_dir / "out"),
               ut.quantities(spec), "0", "1", "1", "0"]
    env = dict(os.environ, USINE=str(ut.tool_home(binary)))
    t0 = time.monotonic()
    with open(run_dir / "usine.log", "w", encoding="utf-8") as log:
        code = subprocess.run(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, env=env,
                              timeout=900).returncode
    seconds = time.monotonic() - t0
    log_text = (run_dir / "usine.log").read_text(encoding="utf-8", errors="replace")
    crashed = any(s in log_text for s in ("--- ERROR ---", "--- ABORT ---", "segmentation violation"))
    outputs = {f"out/{n}": ut.sha256(run_dir / "out" / n) for n in ut.expected_outputs(spec)
               if (run_dir / "out" / n).is_file()}
    ok = not crashed and len(outputs) == len(ut.expected_outputs(spec))
    result = {"ok": ok, "exit_status": code, "seconds": seconds, "inputs": inputs, "outputs": outputs,
              "command": command, "notes": notes, "log_tail": "" if ok else log_text[-800:],
              "usine_inputs": read_in_place}
    translator_files = ut.render(spec, "<TOOL_HOME>/inputs", "<RUN_DIR>")
    rec = ut.record(spec, dict(result, inputs={k: v for k, v in inputs.items() if k in translator_files}), binary)
    committed = committed_hashes(item, dragon2_data, dragon2_out)
    manifest = rec["extension"]["input_manifest"]
    manifest[:0] = [{"path": k, "sha256": v} for k, v in sorted(inputs.items()) if k not in translator_files]
    for entry in manifest:
        if entry["path"] in committed:
            entry["committed_form_sha256"] = committed[entry["path"]]
    manifest.sort(key=lambda e: (bool(e.get("read_in_place")), e["path"]))
    rec["objective"] = (f"USINE run '{item['name']}' of cr-propagation D3 ({item['kind']}): translated from a transport "
                        "block by usine_translate.py, then the D3 settings of d3_study.py applied")
    rec["extension"]["notes"] = rec["extension"]["notes"] + [f"D3 run kind {item['kind']}, config {item['config']}"]
    (run_dir / "translation.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    (out / "records").mkdir(exist_ok=True)
    (out / "records" / f"{item['name']}.computational-run.json").write_text(json.dumps(rec, indent=1) + "\n",
                                                                           encoding="utf-8")
    return {"name": item["name"], "ok": ok, "seconds": round(seconds, 2), "outputs": len(outputs),
            "log_tail": result["log_tail"]}


def committed_hashes(item: dict, dragon2_data, dragon2_out) -> dict:
    """sha256 of each generated input with the placeholders <TOOL_HOME>/inputs and <RUN_DIR> (the form the tests
    regenerate from this script and the committed outputs)."""
    _, files = item_spec_and_files(item, "<TOOL_HOME>/inputs", "<RUN_DIR>", dragon2_data, dragon2_out)
    return {n: hashlib.sha256(t.encode("utf-8")).hexdigest() for n, t in files.items()}


# ------------------------------------------------------------------ analysis

def usine_observables(out_dir: Path, translation: dict) -> dict:
    tables = rd.read_run(out_dir, translation["model"], translation["species"])
    obs = {"B/C": rd.ratio_of_bin_integrals(tables, "B/C", BORON_CARBON_EDGES, "rigidity")}
    if "10Be" in tables:
        obs["10Be/9Be"] = rd.ratio_of_bin_integrals(tables, "10Be/9Be", BERYLLIUM_EDGES, "ekn")
    return obs


def usine_oxygen_ratio(out_dir: Path, translation: dict, ekn: float) -> float:
    tables = rd.read_run(out_dir, translation["model"], translation["species"])
    xc, yc = tables["12C"]
    _, yo = tables["16O"]
    return rd.interpolate(xc, [o / c for o, c in zip(yo, yc)], ekn)


def max_dev(a: list[float], b: list[float]) -> float:
    return max(abs(x / y - 1.0) for x, y in zip(a, b))


def compare(dragon: dict, usine: dict) -> dict:
    out = {}
    for obs in dragon:
        if obs in usine:
            ratio = [d / u for d, u in zip(dragon[obs], usine[obs])]
            out[obs] = {"dragon2": [float(x) for x in dragon[obs]], "usine": [float(x) for x in usine[obs]],
                        "dragon2_over_usine": [float(r) for r in ratio],
                        "max_abs_deviation": float(max(abs(r - 1) for r in ratio))}
    if "B/C" in out:
        out["B/C"]["passed"] = bool(out["B/C"]["max_abs_deviation"] <= TOLERANCE)
    return out


def radial_gas_estimate(model: str, l_kpc: float = 4.0, radius: float = 20.0, n_terms: int = 100) -> float:
    """High-energy (no destruction) thin-disc estimate of the B/C effect of DRAGON2's radial gas profile against a
    uniform disc with the column at the observer: Fourier-Bessel solution of pure diffusion in a cylinder (radius R,
    half-height L, N = 0 at the boundaries), uniform source in r < R (DRAGON2 OneRing, USINE CST), secondary source
    n(r) N_p(r). Returns N_s(r_obs)[n(r)] / N_s(r_obs)[n(r_obs)]."""
    from scipy import special
    zeros = special.jn_zeros(0, n_terms)
    nodes = [radius * (i + 0.5) / 2000 for i in range(2000)]
    col = [gas_columns(model, r, l_kpc, 0.02)["nucleons"] for r in nodes]
    col_obs = gas_columns(model, OBSERVER_KPC, l_kpc, 0.02)["nucleons"]

    def transfer(k):  # N_i(z = 0) per unit disc source coefficient (up to a common constant)
        s = zeros[k] / radius
        return 1.0 / (s / math.tanh(s * l_kpc))

    src = [2.0 / (zeros[k] * special.j1(zeros[k])) for k in range(n_terms)]  # Bessel coefficients of 1 on r < R
    j_obs = [special.j0(zeros[k] * OBSERVER_KPC / radius) for k in range(n_terms)]
    prim = [sum(src[k] * transfer(k) * special.j0(zeros[k] * r / radius) for k in range(n_terms)) for r in nodes]
    dr_ = radius / 2000

    def secondary(gas):
        total = 0.0
        for k in range(n_terms):
            norm = 2.0 / (radius ** 2 * special.j1(zeros[k]) ** 2)
            coeff = norm * sum(r * c * p * special.j0(zeros[k] * r / radius) * dr_ for r, c, p in zip(nodes, gas, prim))
            total += coeff * transfer(k) * j_obs[k]
        return total
    return secondary(col) / secondary([col_obs] * len(nodes))


def vertical_extent_estimate(model: str, l_kpc: float = 4.0, source_half_kpc: float = 0.2) -> float:
    """High-energy 1D estimate of the B/C effect of DRAGON2's gas layer and source box (|z| <= 0.2 kpc, sources.cc
    case Ring) against a thin disc with the same column and a thin source: slab Green's function
    G(z, z') = (L - max|.|)(L + min) / (2 L) (N = 0 at |z| = L, pure diffusion). Returns the ratio thick / thin."""
    dz = 0.002
    zs = [-l_kpc + (i + 0.5) * dz for i in range(int(round(2 * l_kpc / dz)))]

    def green(z, zp):
        lo, hi = min(z, zp), max(z, zp)
        return (l_kpc - hi) * (l_kpc + lo) / (2 * l_kpc)
    src = [1.0 if abs(z) <= source_half_kpc else 0.0 for z in zs]
    norm_s = sum(src) * dz
    prim = [sum(s * green(z, zp) for s, zp in zip(src, zs)) * dz / norm_s for z in zs]
    prim0 = sum(s * green(0.0, zp) for s, zp in zip(src, zs)) * dz / norm_s
    dens = [(lambda d: d["HI"] + d["HII"] + 2 * d["H2"])(bronf_ferr_density(OBSERVER_KPC, z) if model == "BronfFerr"
                                                          else galprop_density(OBSERVER_KPC, z, 0.02)) for z in zs]
    column = sum(dens) * dz
    thick = sum(n * p * green(0.0, z) for n, p, z in zip(dens, prim, zs)) * dz / prim0
    return thick / (column * green(0.0, 0.0))


def run_translation(item: dict, dragon2_out: Path | None = None) -> dict:
    """The translation of a planned USINE run (no file is read but the DRAGON2 outputs that fix a parent ratio)."""
    if item["kind"] == "level2":
        return ut.translate(level2_transport(item["settings"], dragon2_out), item["name"], EKN_RANGE)
    return matched_spec(item, dragon2_out)[0]


def plan_item(name: str) -> dict:
    return next(i for i in usine_plan() if i["name"] == name)


def _effect(a: list[float], b: list[float]) -> list[float]:
    return [y / x for x, y in zip(a, b)]


def _span(vals: list[float]) -> list[float]:
    return [min(vals), max(vals)]


def _bound(spec_name: str) -> float:
    """The relative error bound of the first-order reacceleration zone conversion recorded in D1's run spec."""
    import re
    subs = json.loads((D1_FIX / "specs" / f"{spec_name}.json").read_text(encoding="utf-8"))["substitutes"]
    return float(re.search(r"relative error bound ([0-9.]+)", " ".join(subs)).group(1))


def analyze(usine_dir, dragon2_out: Path | None = None) -> dict:
    """D3-1, D3-2 and D3-3 from the runs. usine_dir(name) is the folder of a USINE run's local-flux tables (the run's
    out/ folder, or d3/usine/outputs/<name> for the committed tables); dragon2_out holds the D3 DRAGON2 runs
    (None: d3/dragon2/outputs)."""
    b1 = json.loads((FIX / "usine" / "usine-results.json").read_text(encoding="utf-8"))
    plan = {i["name"]: i for i in usine_plan()}
    cache: dict = {}

    def usine_run(name):
        if name not in cache:
            tr = run_translation(plan[name], dragon2_out)
            cache[name] = (usine_observables(usine_dir(name), tr), tr)
        return cache[name]

    def d_out(run):
        return dragon2_output(run, dragon2_out)

    level1, matched = {}, {}
    for cfg, (_, d_run, _) in LEVEL1_CONFIGS.items():
        dragon = dragon2_observables(d_out(d_run))
        ref = b1["runs"][USINE_LEVEL1_RUNS[cfg]]
        level1[cfg] = dict(compare(dragon, {k: ref[k] for k in ("B/C", "10Be/9Be") if k in ref}),
                           dragon2_run=d_run, usine_run=f"B1 {USINE_LEVEL1_RUNS[cfg]} (usine/usine-results.json)")
        obs, tr = usine_run(f"m-{cfg}")
        matched[cfg] = dict(compare(dragon, obs), dragon2_run=d_run, usine_run=f"m-{cfg}",
                            O_over_C={f"{e:g} GeV/n": {"dragon2": dragon2_element_ratio(d_out(d_run), DRAGON2_OXYGEN,
                                                                                         DRAGON2_DEN, e),
                                                       "usine": usine_oxygen_ratio(usine_dir(f"m-{cfg}"), tr, e)}
                                      for e in (1.0, NORM_EKN_GEV, 100.0)},
                            settings=tr["d3_settings"])
    ladder_names = ["B1 d1-isotopic"] + [n for n, _ in LADDER] + ["m-isotopic"]
    ladder_bc = [b1["runs"]["d1-isotopic"]["B/C"]] + [usine_run(n)[0]["B/C"] for n in ladder_names[1:]]
    labels = ["gas column (BronfFerr at the observer, no helium)",
              "helium target He/H 0.11 (production x He_to_H_CS_ratio, destruction x 2.10 / A^0.055)",
              "inelastic cross sections (DRAGON2-INELASTIC on H and He)",
              "parent ratio O/C at 10 GeV/n (DRAGON2's propagated value)",
              "injection spectrum beta^-1 Rig^-gamma (USINE eta_s = -1)"]
    steps = {ladder_names[k]: {"setting": labels[k - 1], "effect": _effect(ladder_bc[k - 1], ladder_bc[k])}
             for k in range(1, len(ladder_names))}
    product = [1.0] * len(ladder_bc[0])
    for st in steps.values():
        product = [p * e for p, e in zip(product, st["effect"])]
    ladder = {"runs": ladder_names, "B/C": ladder_bc, "steps": steps,
              "level1_offset": level1["isotopic"]["B/C"]["dragon2_over_usine"],
              "product_of_steps_times_matched_residual": [p * r for p, r in zip(
                  product, matched["isotopic"]["B/C"]["dragon2_over_usine"])]}
    # level 2
    l2_names = [n for n, _ in L2_STEPS]
    l2_bc = {n: usine_run(n)[0]["B/C"] for n in l2_names}
    d_l2 = dragon2_observables(d_out("D3_l2_dragon2"))["B/C"]
    l2_labels = ["USINE defaults (sigProdGALPROP17_OPT12, sigInelTripathi99+Coste12, n_HI 0.867 + n_HII 0.033, "
                 "He/H 1/9, data-normalised abundances, injection Rig^-gamma)",
                 "production cross sections: DRAGON2's Evoli 2019 cumulative table, helium by He_to_H_CS_ratio",
                 "inelastic cross sections: DRAGON2-INELASTIC (He x 2.10 / A^0.055)",
                 "gas: DRAGON2 BronfFerr nucleon column at the observer, He/H 0.11",
                 "source abundances: DRAGON2's propagated N/C and O/C at 10 GeV/n",
                 "injection spectrum beta^-1 Rig^-gamma (as DRAGON2)"]
    level2 = {"dragon2": d_l2, "usine_defaults": l2_bc["u-l2-usine"],
              "dragon2_over_usine": [d / u for d, u in zip(d_l2, l2_bc["u-l2-usine"])],
              "steps": {n: {"setting": lab, "effect": (_effect(l2_bc[l2_names[i - 1]], l2_bc[n]) if i else None)}
                        for i, (n, lab) in enumerate(zip(l2_names, l2_labels))},
              "residual_dragon2_over_last_step": [d / u for d, u in zip(d_l2, l2_bc[l2_names[-1]])]}
    level2["residual_max_abs_deviation"] = max(abs(r - 1) for r in level2["residual_dragon2_over_last_step"])
    # estimates of what USINE cannot express
    estimates = {m: {"vertical_extent": vertical_extent_estimate(m), "radial_profile": radial_gas_estimate(m),
                     "geometry_factor": geometry_factor(m),
                     "columns_at_observer_kpc_cm3": gas_columns(m, OBSERVER_KPC, 4.0, 0.02)}
                 for m in ("BronfFerr", "Galprop")}
    geometry = {}
    for cfg in GEOMETRY_CHECKS:
        obs, tr = usine_run(f"a-{cfg}-geometry")
        dragon = dragon2_observables(d_out(LEVEL1_CONFIGS[cfg][1]))
        geometry[cfg] = dict(compare(dragon, obs), usine_run=f"a-{cfg}-geometry",
                             gas_scale=plan[f"a-{cfg}-geometry"]["settings"]["gas_scale"])
    reacc_bound = _bound("D1_reacceleration")
    u_eff = _effect(matched["isotopic"]["B/C"]["usine"], matched["reacceleration"]["B/C"]["usine"])
    d_eff = _effect(matched["isotopic"]["B/C"]["dragon2"], matched["reacceleration"]["B/C"]["dragon2"])
    reacc = {"usine_item_effect": u_eff, "dragon2_item_effect": d_eff, "relative_error_bound": reacc_bound,
             "allowed": [reacc_bound * abs(e - 1) for e in u_eff],
             "item_effect_ratio": [d / u for d, u in zip(d_eff, u_eff)]}
    reacc["within_bound"] = all(abs(r - 1) <= a + 1e-12 for r, a in zip(reacc["item_effect_ratio"], reacc["allowed"]))
    loss = {"dragon2_item_effect": _effect(matched["losses-off"]["B/C"]["dragon2"], matched["losses"]["B/C"]["dragon2"]),
            "usine_item_effect": _effect(matched["losses-off"]["B/C"]["usine"], matched["losses"]["B/C"]["usine"])}
    loss["item_effect_ratio"] = [d / u for d, u in zip(loss["dragon2_item_effect"], loss["usine_item_effect"])]
    loss["item_effect_max_abs_deviation"] = max(abs(r - 1) for r in loss["item_effect_ratio"])
    d1 = json.loads((D1_FIX / "d1-item-results.json").read_text(encoding="utf-8"))
    thick = d1["attribution"]["thick_gas_diagnostic"]["F_thick_over_thin"]
    decay = {"matched_10Be9Be_ratio": matched["decay"]["10Be/9Be"]["dragon2_over_usine"],
             "D1_thick_gas_F": thick,
             "matched_over_F": [m / f for m, f in zip(matched["decay"]["10Be/9Be"]["dragon2_over_usine"], thick)]}
    decay["matched_over_F_max_abs_deviation"] = max(abs(x - 1) for x in decay["matched_over_F"])
    # verdicts
    verdict_1 = {c: v["B/C"]["passed"] for c, v in level1.items()}
    verdict_3 = {c: v["B/C"]["passed"] for c, v in matched.items()}
    resid3 = matched["isotopic"]["B/C"]["max_abs_deviation"]
    unc = abs(1 - estimates["BronfFerr"]["geometry_factor"]) + NUMERICAL_UNCERTAINTY
    differences = level2_differences(level2, estimates, usine_run, d_out, usine_dir)
    verdict_2 = (all(d["attribution"] in ("measured", "estimated") for d in differences)
                 and level2["residual_max_abs_deviation"] <= resid3 + unc)
    return {"label": "cr-propagation D3: DRAGON2 cd588707 against USINE V3.5 (GALPROP unavailable), level 1 "
                     "(harmonized-v1 and D1's item blocks as translated; D3-1), matched level 1 (USINE given "
                     "DRAGON2's fixed settings; D3-3) and level 2 (each code's defaults, every difference attributed; "
                     "D3-2), recomputed by tests/adapters/test_cr_propagation.py D3CrossCode from the recorded runs "
                     "(d3_study.py analyze). B/C on 16 rigidity bins 2-1000 GV, 10Be/9Be on 12 E_k/n bins "
                     "0.05-10 GeV/n, ratios of bin integrals",
            "illustrative": True, "status": ["synthetic", "unvalidated"],
            "tolerance": TOLERANCE, "bc_rigidity_edges_gv": BORON_CARBON_EDGES, "be_ekn_edges_gev": BERYLLIUM_EDGES,
            "level1": level1, "matched": matched, "ladder": ladder, "level2": level2,
            "level2_differences": differences, "geometry_estimates": estimates, "geometry_checks": geometry,
            "reacceleration_check": reacc, "losses_check": loss, "decay_check": decay,
            "verdicts": {"D3-1": {"configurations": verdict_1, "passed": all(verdict_1.values())},
                         "D3-3": {"configurations": verdict_3, "passed": all(verdict_3.values())},
                         "D3-2": {"passed": verdict_2, "residual_max_abs_deviation": level2["residual_max_abs_deviation"],
                                  "allowed": resid3 + unc,
                                  "allowed_from": f"D3-3 isotopic residual {resid3:.4g} + |1 - BronfFerr geometry "
                                                  f"factor| + {NUMERICAL_UNCERTAINTY} numerical (VALIDATION CRPROP-D3)"}}}


NUMERICAL_UNCERTAINTY = 0.005  # DRAGON2 grid 0.22% (D1 convergence) and USINE Fourier-Bessel 100 terms (B3-1c 0.5%)


def level2_differences(level2: dict, estimates: dict, usine_run, d_out, usine_dir) -> list[dict]:
    """Every difference between the two codes' defaults, registered as a model-alternative with its attribution."""
    st = level2["steps"]

    def measured(step):
        return {"attribution": "measured", "evidence": f"USINE run {step} against the previous step",
                "effect_on_bc": _span(st[step]["effect"])}
    e_d, cols = dconv.read_output(d_out("D3_l2_dragon2"))
    tables = rd.read_run(usine_dir("u-l2-injection"), "Model2DKisoVc", list(ut.TABLED_ISOTOPES))
    xs = tables["12C"][0]
    f_u = [(rd.interpolate(xs, tables["13C"][1], e) + rd.interpolate(xs, tables["14C"][1], e))
           / rd.interpolate(xs, tables["12C"][1], e) for e in (1.0, 10.0, 100.0)]
    f_d = [(rd.interpolate(e_d, [13 * v for v in cols["NUC_6013"]], e) + rd.interpolate(e_d, [14 * v for v in cols["NUC_6014"]], e))
           / rd.interpolate(e_d, [12 * v for v in cols["NUC_6012"]], e) for e in (1.0, 10.0, 100.0)]
    rows = [
        dict(difference="production cross sections", dragon2="Evoli 2019 cumulative table (crxsecs_fragmentation_"
             "Evoli2019_cumulative_modified.dat), helium by GALPROP's He_to_H_CS_ratio",
             usine="sigProdGALPROP17_OPT12 (H and He columns)", **measured("u-l2-production")),
        dict(difference="inelastic cross sections", dragon2="CROSEC (Barashenkov-Polanski sighad, option 2), helium x "
             "2.10 / A^0.055", usine="sigInelTripathi99+Coste12 (H and He)", **measured("u-l2-inelastic")),
        dict(difference="gas density and helium", dragon2="BronfFerr (nucleon column 0.218 kpc cm^-3 at 8.3 kpc), "
             "He/H 0.11", usine="thin disc n_HI 0.867 + n_HII 0.033 cm^-3, He/H 1/9", **measured("u-l2-gas")),
        dict(difference="source abundances", dragon2="BaseModel_DRAGONxsec.source.param (propagated O/C 1.21 at "
             "10 GeV/n)", usine="data-normalised to HEAO (crdata_crdb20170523.dat)", **measured("u-l2-abundances")),
        dict(difference="injection spectrum convention", dragon2="rigidity power law per unit momentum (equivalent "
             "to beta^-1 Rig^-gamma per E_k/n; the C, O spectral shapes of the two codes agree within 0.6% once USINE "
             "has eta_s = -1)", usine="q Rig^-gamma per E_k/n (eta_s = 0)", **measured("u-l2-injection")),
        dict(difference="gas and source geometry", dragon2="BronfFerr radial profile, finite H2/HI layers (59/115 pc), "
             "sources uniform in |z| <= 0.2 kpc", usine="uniform thin disc (h 0.1 kpc), thin sources",
             attribution="estimated", evidence="vertical_extent_estimate x radial_gas_estimate (high-energy limit); "
             "matched run a-isotopic-geometry", effect_on_bc=[estimates["BronfFerr"]["geometry_factor"], 1.0]),
        dict(difference="source isotopic composition of C (13C, 14C in the B/C denominator)",
             dragon2=f"(13C+14C)/12C {f_d[0]:.4f}, {f_d[1]:.4f}, {f_d[2]:.4f} at 1, 10, 100 GeV/n",
             usine=f"(13C+14C)/12C {f_u[0]:.4f}, {f_u[1]:.4f}, {f_u[2]:.4f} (solar isotopic fractions)",
             attribution="estimated", evidence="B/C scales as 1 / (12C + 13C + 14C) at fixed B: effect "
             "(1 + f_USINE) / (1 + f_DRAGON2) from the propagated fractions",
             effect_on_bc=_span([(1 + u) / (1 + d) for u, d in zip(f_u, f_d)])),
        dict(difference="network edges", dragon2="Z 4-8 (17O, 18O primaries at 3e-4 of 16O; no Li)",
             usine="1H-16O (no 17O, 18O)", attribution="estimated",
             evidence="17O, 18O source abundance 3.4e-4 of 16O in BaseModel; their B production at most that fraction "
             "of O's", effect_on_bc=[0.9995, 1.0005]),
        dict(difference="numerical method", dragon2="finite differences, dz 0.02 kpc, Ekfactor 1.2 (grid convergence "
             "0.22%, VALIDATION CRPROP-D1)", usine="Fourier-Bessel 100 terms (within 0.5% of 2000, B3-1c)",
             attribution="estimated", evidence="D1 convergence study and B3-1c",
             effect_on_bc=[1 - NUMERICAL_UNCERTAINTY, 1 + NUMERICAL_UNCERTAINTY]),
    ]
    for r in rows:
        r["kind"] = "model-alternative"
    return rows


def jsonable(value):
    """Plain JSON types (numpy scalars from the readers become float, int or bool)."""
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        return value.item()
    return value


# ------------------------------------------------------------------ CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("inelastic")
    a.add_argument("--build", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    b = sub.add_parser("dragon2-specs")
    b.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("usine")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--jobs", type=int, default=4)
    c.add_argument("--only", default="")
    c.add_argument("--dragon2-out", type=Path)
    d = sub.add_parser("analyze")
    d.add_argument("--usine-out", type=Path, required=True)
    d.add_argument("--dragon2-out", type=Path)
    d.add_argument("--results", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.cmd == "inelastic":
        binary, data_dir = os.environ.get("HEP_DRAGON2_BIN"), os.environ.get("HEP_DRAGON2_DATA")
        if not binary or not data_dir:
            print(json.dumps({"status": "missing-dependency", "error": "HEP_DRAGON2_BIN and HEP_DRAGON2_DATA"}))
            return 3
        doc = dragon2_inelastic(args.build, Path(binary), Path(data_dir))
        args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok", "nuclides": len(doc["sigma_h_mb"])}))
        return 0
    if args.cmd == "dragon2-specs":
        args.out.mkdir(parents=True, exist_ok=True)
        for name, spec in dragon2_specs().items():
            (args.out / f"{name}.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"status": "ok"}))
        return 0
    if args.cmd == "usine":
        binary, data_dir = os.environ.get("HEP_USINE_BIN"), os.environ.get("HEP_USINE_DATA")
        if not binary or not data_dir:
            print(json.dumps({"status": "missing-dependency", "error": "HEP_USINE_BIN and HEP_USINE_DATA"}))
            return 3
        d2 = os.environ.get("HEP_DRAGON2_DATA")
        plan = [i for i in usine_plan() if args.only in i["name"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.jobs, 4)) as pool:
            res = list(pool.map(lambda i: execute(i, args.out, Path(binary), Path(data_dir), Path(d2) if d2 else None,
                                                  args.dragon2_out), plan))
        print(json.dumps({"status": "ok" if all(r["ok"] for r in res) else "failed", "runs": res}, indent=1))
        return 0 if all(r["ok"] for r in res) else 1
    res = analyze(lambda name: args.usine_out / "runs" / name / "out", args.dragon2_out)
    args.results.write_text(json.dumps(jsonable(res), indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
