#!/usr/bin/env python3
"""cr-propagation B3: USINE against the closed forms under harmonized-v1, and the cross-section reweighting check.

Criteria and tolerances: VALIDATION.md section CRPROP-B3 (fixed before any comparison). This script drives the
recorded USINE V3.5 runs through adapters/cr-propagation/assets/usine_translate.py (the specifications in specs/; the
production cross sections of a run are changed only through the translation's production table, never USINE's
files), reads them with usine_to_prediction.py (ratios of bin integrals, r3 P2, P3), and evaluates the closed forms of
profiles/theory/cr-secondary-ratio/scripts/convection_decay.py at USINE's E_k/n nodes with USINE's own parent ratio
O/C at each node (same parents).

Runs (all from the specifications in specs/; names <config>-<kind>):
  <cfg>-nom                       nominal run of each configuration (h1-2d, h1-1d, dec-2d, dec-1d, all-2d)
  <cfg>-only-<P>-<C>              only channel P->C non-zero (single-channel response; parents unchanged)
  <cfg>-<P>-<C>-p20 / -m20        full rerun with sigma(P->C) x 1.2 / x 0.8
  <cfg>-slope-<P>-<C>             full rerun with sigma(P->C) (E/E_thr)^s below E_thr (energy-dependent table)
  <cfg>-basis-<P>-<C>-k<k> / -rest  energy-basis responses: only table node k of channel P->C non-zero / nodes >= E_thr
for the norm check in h1-2d, dec-2d, all-2d and the slope check of SLOPE_CHANNELS in dec-2d and all-2d.

Usage:
  python3 b3_study.py run --out DIR [--jobs 4] [--only NAME_SUBSTRING]   # needs HEP_USINE_BIN, HEP_USINE_DATA
  python3 b3_study.py analyze --out DIR --results RESULTS.json --channels CHANNELS.json
  python3 b3_study.py compare --run-dir RUNDIR --spec SPEC.json            # B3-1 numbers of one run (offline)
Output: JSON on stdout. Exit 0 ok, 1 a USINE run failed, 2 bad input, 3 USINE missing.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parents[4]
sys.dont_write_bytecode = True
ASSETS = PLUGIN_ROOT / "adapters" / "cr-propagation" / "assets"
PROFILE_SCRIPTS = PLUGIN_ROOT / "profiles" / "theory" / "cr-secondary-ratio" / "scripts"
for p in (PLUGIN_ROOT, ASSETS, PROFILE_SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import convection_decay as cd  # noqa: E402
import predict as cf_predict  # noqa: E402
import usine_to_prediction as rd  # noqa: E402
import usine_translate as ut  # noqa: E402

SPECS = HERE / "specs"
CONFIGS = ("h1-2d", "h1-1d", "dec-2d", "dec-1d", "all-2d", "h1-2d-r40", "h1-2d-r80")
CLOSED_FORM_CONFIGS = ("h1-2d", "h1-1d", "dec-2d", "dec-1d", "h1-2d-r40", "h1-2d-r80")
BESSEL_TERMS = (100, 2000)  # 100 = the translator's N_BESSEL
NORM_CONFIGS = ("h1-2d", "dec-2d", "all-2d")
SLOPE_CONFIGS = ("dec-2d", "all-2d")
SLOPE_CHANNELS = ("12C->11B", "12C->10Be")
EPSILONS = (0.2, -0.2)
E_THR_GEV, SLOPE_S = 10.0, 0.1
TABLE_PPD = 10  # nodes per decade of the energy-dependent production tables (log grid on XS_GRID_GEV, nodes 10^(k/10))
TOL_B31, TOL_B32 = 0.02, 0.005
MAIN_FRACTION = 0.01
BC_EDGES = [2.0 * 500.0 ** (i / 16) for i in range(17)]  # 16 log-uniform rigidity bins 2-1000 GV (B1, D1)
BE_EDGES = [0.05 * 200.0 ** (i / 12) for i in range(13)]  # 12 log-uniform E_k/n bins 0.05-10 GeV/n (B1, D1)
NODE_RANGE = (0.05, 1000.0)
BORON, BERYLLIUM = ("10B", "11B"), ("7Be", "9Be", "10Be")


# ---------------------------------------------------------------- specifications and runs

def load_spec(name: str) -> dict:
    return json.loads((SPECS / f"{name}.json").read_text(encoding="utf-8"))


def translation(name: str) -> dict:
    doc = load_spec(name)
    return ut.translate(doc["transport"], f"{name}-nom", doc["ekn_range_gev"])


def check_used(spec: dict, transport: dict, init_text: str) -> list[str]:
    """Every field of the transport block reached the USINE file (the translator defaults some silently)."""
    geo, dif = transport["geometry"], transport["diffusion"]
    par = spec["transport_pars"]
    problems = []
    want = {"L": geo["L_kpc"], "h": geo["disc_halfwidth_pc"] / 1000.0}
    if geo["kind"] == "cylinder-2d":
        want["R"] = geo["radius_kpc"]
    for k, v in want.items():
        if abs(spec["geometry"][k] - v) > 1e-12 * v:
            problems.append(f"geometry {k} {spec['geometry'][k]} != {v}")
    for k, v in (("K0", dif["D0_cm2_s"] / ut.KPC2_PER_MYR_CM2_S), ("delta", dif["delta"]), ("eta_t", dif["eta"]),
                 ("R0", dif["R0_gv"]), ("Va", transport["reacceleration"]["V_A_kms"]),
                 ("Vc", transport["convection"]["V_c_kms"]), ("w", transport["reacceleration"]["w"])):
        if abs(par[k] - v) > 1e-12 * max(abs(v), 1.0):
            problems.append(f"transport {k} {par[k]} != {v}")
    if dif["breaks"] or "Rl1" in par:
        problems.append("a diffusion break reached the run (B3 uses none)")
    sw = spec["switches"]
    if sw["IsDecayBETA"] != bool(transport["decay"]["enabled"]) or sw["IsTertiaries"] or sw["IsEReacc"] != (
            transport["reacceleration"]["V_A_kms"] > 0) or sw["IsWind"] != (transport["convection"]["V_c_kms"] > 0):
        problems.append(f"switches {sw}")
    for loss, key in ut.LOSS_SWITCHES.items():
        if sw[key] != (loss in transport["losses"]):
            problems.append(f"loss {loss}: switch {key} = {sw[key]}")
    if spec["gas_cm3"] != {"HI": 1.0, "HII": 0.0, "H2": 0.0, "He": 0.0}:
        problems.append(f"gas {spec['gas_cm3']}")
    if "IsLoadGhosts @ M=0 @ false" not in init_text or "Tertiaries @ M=0 @ -" not in init_text:
        problems.append("ghost nuclei or tertiary chains not off in the USINE file")
    if (spec["source"]["spatial"] == "CST") != (geo["kind"] == "cylinder-2d"):
        problems.append("source spatial template")
    return problems


def table_nodes() -> list[float]:
    lo, hi = ut.XS_GRID_GEV
    n = round(TABLE_PPD * math.log10(hi / lo)) + 1
    return [lo * (hi / lo) ** (i / (n - 1)) for i in range(n)]


def slope_weight(e: float) -> float:
    return (e / E_THR_GEV) ** SLOPE_S if e < E_THR_GEV else 1.0


def production_table(spec: dict, tables: dict) -> str:
    """USINE production table on table_nodes(); tables: 'P->C' -> list of node values (mb); others constant."""
    nodes = table_nodes()
    sp = spec["species"]
    lines = ["# production cross sections (mb) on H, every pair of the network",
             "# ILLUSTRATIVE placeholders of theory:cr-secondary-ratio, written by b3_study.py (energy-dependent where "
             "B3 varies a channel; not data)", "#  Type  Unit     Targets", " sigma    mb      H", "",
             "# EknMIN[GeV/n]   EknMAX[GeV/n]   nEkn  (PROJECTILE GRID)",
             f"{nodes[0]:.6e}      {nodes[-1]:.6e}    {len(nodes)}", ""]
    for p in sp:
        for c in sp:
            if p == c or ut.charge_and_mass(c)[1] > ut.charge_and_mass(p)[1]:
                continue
            key = f"{p}->{c}"
            vals = tables.get(key, [spec["production_mb"].get(key, 0.0)] * len(nodes))
            lines += [f"{p} -> {c}"] + [f"{v:.9e}" for v in vals] + [""]
    return "\n".join(lines)


def run_plan() -> list[dict]:
    """Every B3 run: name, config, production_mb override, energy-dependent tables."""
    plan = []
    for cfg in CONFIGS:
        plan.append({"name": f"{cfg}-nom", "config": cfg, "kind": "nominal"})
    for cfg in NORM_CONFIGS:
        base = translation(cfg)["production_mb"]
        for chan, sigma in base.items():
            if sigma == 0:
                continue
            tag = chan.replace("->", "-")
            only = {k: (v if k == chan else 0.0) for k, v in base.items()}
            plan.append({"name": f"{cfg}-only-{tag}", "config": cfg, "kind": "single-channel", "channel": chan,
                         "production_mb": only})
            for eps in EPSILONS:
                plan.append({"name": f"{cfg}-{tag}-{'p' if eps > 0 else 'm'}{abs(round(eps * 100))}", "config": cfg,
                             "kind": "norm-rerun", "channel": chan, "epsilon": eps,
                             "production_mb": {**base, chan: sigma * (1 + eps)}})
    nodes = table_nodes()
    for cfg in SLOPE_CONFIGS:
        base = translation(cfg)["production_mb"]
        zero = {k: 0.0 for k in base}
        for chan in SLOPE_CHANNELS:
            tag, sigma = chan.replace("->", "-"), base[chan]
            plan.append({"name": f"{cfg}-slope-{tag}", "config": cfg, "kind": "slope-rerun", "channel": chan,
                         "tables": {chan: [sigma * slope_weight(e) for e in nodes]}})
            k_lo = round(TABLE_PPD * math.log10(0.0316 / ut.XS_GRID_GEV[0]))  # first node at or above USINE's grid
            for k, e in enumerate(nodes):
                if k < k_lo or e >= E_THR_GEV * (1 - 1e-9):
                    continue
                plan.append({"name": f"{cfg}-basis-{tag}-k{k}", "config": cfg, "kind": "basis", "channel": chan,
                             "node": k, "production_mb": zero,
                             "tables": {chan: [sigma if i == k else 0.0 for i in range(len(nodes))]}})
            plan.append({"name": f"{cfg}-basis-{tag}-rest", "config": cfg, "kind": "basis", "channel": chan,
                         "node": "rest", "production_mb": zero,
                         "tables": {chan: [sigma if e >= E_THR_GEV * (1 - 1e-9) else 0.0 for e in nodes]}})
    return plan


def execute(item: dict, out: Path, binary: Path, data_dir: Path) -> dict:
    doc = load_spec(item["config"])
    spec = ut.translate(doc["transport"], item["name"], doc["ekn_range_gev"])
    if "production_mb" in item:
        spec["production_mb"] = dict(item["production_mb"])
    run_dir = (out / "runs" / item["name"]).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    files = ut.render(spec, str(Path(data_dir).resolve()), str(run_dir))
    if item.get("tables"):
        files["xs_production.dat"] = production_table(spec, item["tables"])
    inputs = {}
    for fname, text in files.items():
        (run_dir / fname).write_text(text, encoding="utf-8")
        inputs[fname] = ut.sha256(run_dir / fname)
    problems = check_used(spec, doc["transport"], files["usine.init.par"])
    notes = ut.check_half_lives(spec, data_dir)
    command = [str(Path(binary).resolve()), "-l", str(run_dir / "usine.init.par"), str(run_dir / "out"),
               ut.quantities(spec), "0", "1", "1", "0"]
    env = dict(os.environ, USINE=str(ut.tool_home(binary)))
    t0 = time.monotonic()
    with open(run_dir / "usine.log", "w", encoding="utf-8") as log:
        code = subprocess.run(command, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT, env=env,
                              timeout=600).returncode
    seconds = time.monotonic() - t0
    log_text = (run_dir / "usine.log").read_text(encoding="utf-8", errors="replace")
    crashed = any(s in log_text for s in ("--- ERROR ---", "--- ABORT ---", "segmentation violation"))
    outputs = {f"out/{n}": ut.sha256(run_dir / "out" / n) for n in ut.expected_outputs(spec)
               if (run_dir / "out" / n).is_file()}
    ok = not crashed and len(outputs) == len(ut.expected_outputs(spec)) and not problems
    result = {"ok": ok, "exit_status": code, "seconds": seconds, "inputs": inputs, "outputs": outputs,
              "command": command, "notes": notes, "log_tail": "" if ok else log_text[-800:]}
    rec = ut.record(spec, result, binary)
    rec["extension"]["notes"] = rec["extension"]["notes"] + [f"B3 run kind {item['kind']}"] + problems
    (run_dir / "translation.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    (out / "records").mkdir(exist_ok=True)
    (out / "records" / f"{item['name']}.computational-run.json").write_text(json.dumps(rec, indent=1) + "\n",
                                                                           encoding="utf-8")
    return {"name": item["name"], "ok": ok, "seconds": round(seconds, 2), "problems": problems,
            "outputs": outputs, "log_tail": result["log_tail"]}


# ---------------------------------------------------------------- reading and closed form

def read_signed(path: Path, nuclide: str) -> tuple[list[float], list[float]]:
    """One USINE isotope table, keeping negative values: a response to a narrow source (energy-basis run) in an
    energy-coupled solver undershoots below zero (numerical), and superposition needs the values as written. The
    header (program, quantity, unit, phi = 0) is checked as usine_to_prediction.read_table does."""
    header, xs, ys = [], [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line[1:].strip())
        elif line.strip():
            a, b = line.split()
            xs.append(float(a))
            ys.append(float(b))
    if (len(header) < 6 or not header[0].startswith("USINE") or header[3].upper() != nuclide.upper()
            or rd.FLUX_UNIT not in header[5] or "phi0.00GV" not in header[4]):
        raise ValueError(f"{Path(path).name}: unexpected USINE header {header[:6]}")
    if any(not math.isfinite(y) for y in ys) or any(b <= a for a, b in zip(xs, xs[1:])):
        raise ValueError(f"{Path(path).name}: non-finite values or nodes not increasing")
    return xs, ys


def read(out: Path, name: str) -> dict:
    """nuclide -> (E_k/n nodes, flux) of one B3 run; a nominal or rerun table must also pass the adapter's reader."""
    run_dir = out / "runs" / name
    spec = json.loads((run_dir / "translation.json").read_text(encoding="utf-8"))
    if "-only-" in name or "-basis-" in name:
        return {s: read_signed(run_dir / "out" / rd.table_name(s, spec["model"]), s) for s in spec["species"]}
    return rd.read_run(run_dir / "out", spec["model"], spec["species"])


def closed_form_tables(tables: dict, transport: dict) -> dict:
    """Closed-form isotope fluxes on USINE's nodes: density relative to 12C (USINE's own O/C as parent ratio) times
    USINE's 12C flux; the parents are USINE's."""
    isotopic = "decay" in transport["cross_sections"]["production_set"]
    xs_rel = "models/xs-illustrative-decay.json" if isotopic else "models/xs-illustrative-A.json"
    secondaries = ([{"name": "7Be", "Z": 4, "A": 7, "stable_assumption": "fully stripped 7Be (r3 P6)"},
                    {"name": "9Be", "Z": 4, "A": 9},
                    {"name": "10Be", "Z": 4, "A": 10, "decay": {"mode": "beta-", "daughter": "10B"}},
                    {"name": "10B", "Z": 5, "A": 10}, {"name": "11B", "Z": 5, "A": 11}] if isotopic
                   else [{"name": "B", "Z": 5, "A": 11, "nuclide": "11B"}])
    if not transport["decay"]["enabled"] and isotopic:
        raise ValueError("isotopic set without decay is not a B3 configuration")
    dif, geo = transport["diffusion"], transport["geometry"]
    params = {"D0_cm2_s": dif["D0_cm2_s"], "R0_GV": dif["R0_gv"], "delta": dif["delta"], "L_kpc": geo["L_kpc"],
              "h_kpc": geo["disc_halfwidth_pc"] / 1000.0, "n_H_cm3": 1.0, "V_c_kms": transport["convection"]["V_c_kms"]}
    if dif["eta"] != 1.0 or dif["breaks"] or transport["losses"] or transport["reacceleration"]["V_A_kms"]:
        raise ValueError("the closed form has D = D0 beta (R/R0)^delta without breaks, losses or reacceleration")
    xc, yc = tables["12C"]
    _, yo = tables["16O"]
    out = {"12C": (xc, yc), "16O": (xc, yo)}
    names = [s["name"] for s in secondaries]
    vals = {n: [] for n in names}
    for e, c, o in zip(xc, yc, yo):
        cfg = {"parents": [{"name": "C", "Z": 6, "A": 12, "observed_ratio_to_reference": 1.0},
                           {"name": "O", "Z": 8, "A": 16, "observed_ratio_to_reference": o / c}],
               "secondaries": secondaries, "cross_section_set": xs_rel}
        xs = cf_predict.load_cross_sections(cfg)
        dens = cd.network_mid_plane(params, e, cfg, xs)["density"]
        for n in names:
            vals[n].append(dens[n] * c)
    for n in names:
        out["11B" if n == "B" else n] = (xc, vals[n])
    if not isotopic:
        out["10B"] = (xc, [0.0] * len(xc))
    return out


def observables(tables: dict) -> dict:
    """Ratios of bin integrals: B/C on BC_EDGES (rigidity); 10Be/9Be and Be/B on BE_EDGES (E_k/n) where present."""
    obs = {"B/C": rd.ratio_of_bin_integrals(tables, "B/C", BC_EDGES, "rigidity")}
    if "10Be" in tables:
        obs["10Be/9Be"] = rd.ratio_of_bin_integrals(tables, "10Be/9Be", BE_EDGES, "ekn")
        obs["Be/B"] = rd.ratio_of_bin_integrals(tables, "Be/B", BE_EDGES, "ekn")
    return obs


def node_ratios(tables: dict) -> dict:
    """Point ratios at USINE's nodes in the B3-1 ranges: B/C at equal rigidity (rigidities of the 11B nodes in
    2-1000 GV), 10Be/9Be at equal E_k/n (nodes in 0.05-10 GeV/n)."""
    xs = tables["12C"][0]
    rig = [rd.rigidity_from_ekn(e, 5, 11) for e in xs]
    out = {"B/C": [rd.point_ratio(tables, "B/C", r, "rigidity") for r in rig if BC_EDGES[0] <= r <= BC_EDGES[-1]
                   and rd.ekn_from_rigidity(r, 6, 12) >= xs[0]]}
    if "10Be" in tables:
        out["10Be/9Be"] = [rd.point_ratio(tables, "10Be/9Be", e, "ekn") for e in xs if BE_EDGES[0] <= e <= BE_EDGES[-1]]
    return out


def max_dev(a: list[float], b: list[float]) -> float:
    return max(abs(x / y - 1.0) for x, y in zip(a, b) if y != 0)


def compare_b31(tables: dict, transport: dict) -> dict:
    cf = closed_form_tables(tables, transport)
    o_u, o_c = observables(tables), observables(cf)
    n_u, n_c = node_ratios(tables), node_ratios(cf)
    keys = ["B/C"] + (["10Be/9Be"] if "10Be" in tables else [])
    xc, yc = tables["12C"]
    oc = [o / c for o, c in zip(tables["16O"][1], yc)]
    return {"bins": {k: {"usine": o_u[k], "closed_form": o_c[k], "ratio": [c / u for c, u in zip(o_c[k], o_u[k])],
                         "max_dev": max_dev(o_c[k], o_u[k])} for k in keys},
            "nodes_max_dev": {k: max_dev(n_c[k], n_u[k]) for k in keys},
            "usine_O_over_C": {"min": min(oc), "max": max(oc), "at_10_gev_n": rd.interpolate(xc, oc, 10.0)}}


def bessel_2d_tables(tables: dict, transport: dict, n_terms: int) -> dict:
    """Diagnostic of the 2D-1D difference: the thin-disc 2D (Fourier-Bessel) solution with free escape at r = R and
    z = +-L, sources uniform in r < R, observer at r = OBSERVER_KPC, no convection, written like the 1D closed form:
    per mode i, N_i = 2 h q_i / (D S_i coth(S_i L / 2) + 2 h n_H v sigma), S_i = sqrt(4 zeta_i^2 / R^2 + 4 Gamma / D),
    q_i = 2 / (zeta_i J1(zeta_i)) for a uniform primary source and q_i = n_H v sigma_ps N_p,i for a secondary. Parents
    as in closed_form_tables (USINE's O/C at the observer). Only stable species and 10Be (no 10B decay gain)."""
    from scipy.special import j0, j1, jn_zeros
    isotopic = "decay" in transport["cross_sections"]["production_set"]
    xs_rel = "models/xs-illustrative-decay.json" if isotopic else "models/xs-illustrative-A.json"
    xs = cf_predict.load_cross_sections({"cross_section_set": xs_rel})
    if transport["convection"]["V_c_kms"] or transport["losses"] or transport["reacceleration"]["V_A_kms"]:
        raise ValueError("the Bessel diagnostic has no convection, losses or reacceleration")
    geo, dif = transport["geometry"], transport["diffusion"]
    params = {"D0_cm2_s": dif["D0_cm2_s"], "R0_GV": dif["R0_gv"], "delta": dif["delta"]}
    big_l, radius = geo["L_kpc"] * cf_predict.KPC_CM, geo["radius_kpc"] * cf_predict.KPC_CM
    h, n_h = geo["disc_halfwidth_pc"] / 1000.0 * cf_predict.KPC_CM, 1.0
    zeta = jn_zeros(0, n_terms)
    weights = [float(j0(z * ut.OBSERVER_KPC / geo["radius_kpc"])) for z in zeta]
    q_unit = [2.0 / (z * float(j1(z))) for z in zeta]
    sec = ({"7Be": (4, 7), "9Be": (4, 9), "10Be": (4, 10), "11B": (5, 11)} if isotopic else {"B": (5, 11)})
    xc, yc = tables["12C"]
    yo = tables["16O"][1]
    out = {"12C": (xc, yc), "16O": (xc, yo)}
    vals = {n: [] for n in sec}

    def modes(e, z_a, sigma, rate):
        rig, b = cf_predict.kinematics(e, {"Z": z_a[0], "A": z_a[1]})
        diff = cf_predict.diffusion_coefficient(params, rig, b)
        vel = b * cf_predict.C_CM_S
        res = []
        for z in zeta:
            s_i = math.sqrt(4.0 * z * z / radius ** 2 + 4.0 * rate / diff)
            res.append(2.0 * h / (2.0 * diff / big_l * cd.x_coth(0.5 * s_i * big_l) + 2.0 * h * n_h * vel * sigma))
        return res, n_h * vel

    for e, c, o in zip(xc, yc, yo):
        par = {}
        for name, z_a in (("C", (6, 12)), ("O", (8, 16))):
            g, _ = modes(e, z_a, cf_predict._sigma(xs, "inelastic_mb", name), 0.0)
            par[name] = [q * gi for q, gi in zip(q_unit, g)]
        at_obs = {k: sum(w * v for w, v in zip(weights, m)) for k, m in par.items()}
        scale = {"C": 1.0 / at_obs["C"], "O": (o / c) / at_obs["O"]}  # parents at the observer as in USINE
        for name, z_a in sec.items():
            entry = {"name": name, "nuclide": "11B" if name == "B" else name}
            if name == "10Be":
                entry["decay"] = {"mode": "beta-", "daughter": "10B"}
            elif name == "7Be":
                entry["stable_assumption"] = "fully stripped 7Be (r3 P6)"
            rate = cd.decay_rate(e, dict(entry, Z=z_a[0], A=z_a[1]))
            g, nv = modes(e, z_a, cf_predict._sigma(xs, "inelastic_mb", name), rate)
            total = 0.0
            for p in ("C", "O"):
                sig = cf_predict._sigma(xs, "production_mb", f"{p}->{name}")
                total += scale[p] * sum(w * gi * nv * sig * pm for w, gi, pm in zip(weights, g, par[p]))
            vals[name].append(total * c)
    for n in sec:
        out["11B" if n == "B" else n] = (xc, vals[n])
    out.setdefault("10B", (xc, [0.0] * len(xc)))
    return out


def bessel_check(tables: dict, transport: dict, n_terms: int) -> dict:
    """USINE 2D against the Fourier-Bessel diagnostic (B/C without the 10B decay gain only for set A)."""
    bt = bessel_2d_tables(tables, transport, n_terms)
    o_u, o_b = observables(tables), observables(bt)
    keys = ["10Be/9Be"] if "10Be" in tables else ["B/C"]
    return {k: {"ratio": [b / u for b, u in zip(o_b[k], o_u[k])], "max_dev": max_dev(o_b[k], o_u[k])} for k in keys}


# ---------------------------------------------------------------- decomposition

def combine(base: dict, parts: list[tuple[float, dict]], secondaries, skip: tuple = ()) -> dict:
    """base + sum w * part, node by node (identical grids), for the secondaries only: the parents (12C, 16O) are the
    same in every run (USINE normalizes them; no channel feeds them) and stay at base; isotopes in skip stay at base."""
    out = {}
    for s, (x, y) in base.items():
        vals = list(y)
        if s in secondaries and s not in skip:
            for w, part in parts:
                px, py = part[s]
                if px != x:
                    raise ValueError(f"{s}: grids differ")
                vals = [v + w * q for v, q in zip(vals, py)]
        out[s] = (x, vals)
    return out


def deviation(pred: dict, ref: dict, secondaries) -> dict:
    o_p, o_r = observables(pred), observables(ref)
    devs = {k: max_dev(o_p[k], o_r[k]) for k in o_r}
    worst_iso = 0.0
    for s in secondaries:
        x, yr = ref[s]
        yp = pred[s][1]
        for e, a, b in zip(x, yp, yr):
            if NODE_RANGE[0] <= e <= NODE_RANGE[1] and b > 0:
                worst_iso = max(worst_iso, abs(a / b - 1.0))
    devs["isotope_nodes"] = worst_iso
    devs["max"] = max(devs.values())
    return devs


def table_weight(e: float) -> float:
    """The slope weight as USINE sees it: log-lin interpolation of slope_weight between table nodes."""
    nodes = table_nodes()
    for a, b in zip(nodes, nodes[1:]):
        if a <= e <= b:
            wa, wb = slope_weight(a), slope_weight(b)
            return wa + math.log(e / a) * (wb - wa) / math.log(b / a)
    raise ValueError(f"{e} outside the table")


def analyze(out: Path) -> tuple[dict, dict]:
    results = {"b3_1": {}, "b3_2": {}, "slope": {}, "fractions": {}}
    for cfg in CLOSED_FORM_CONFIGS:
        doc = load_spec(cfg)
        results["b3_1"][cfg] = compare_b31(read(out, f"{cfg}-nom"), doc["transport"])
        if doc["transport"]["geometry"]["kind"] == "cylinder-2d":
            results["b3_1"][cfg]["bessel_2d"] = {str(n): bessel_check(read(out, f"{cfg}-nom"), doc["transport"], n)
                                                 for n in BESSEL_TERMS}
    results["b3_1"]["usine_2d_over_1d"] = {
        k: max_dev(observables(read(out, f"{a}-nom"))[k], observables(read(out, f"{b}-nom"))[k])
        for a, b, k in (("h1-2d", "h1-1d", "B/C"), ("dec-2d", "dec-1d", "10Be/9Be"))}
    channels = []
    for cfg in NORM_CONFIGS:
        nom = read(out, f"{cfg}-nom")
        base = translation(cfg)["production_mb"]
        chans = [c for c, v in base.items() if v]
        secondaries = sorted({c.split("->")[1] for c in chans} | ({"10B"} if "10Be" in nom else set()))
        comps = {c: read(out, f"{cfg}-only-{c.replace('->', '-')}") for c in chans}
        closure = deviation(combine({s: (nom[s][0], [0.0] * len(nom[s][0])) if s in secondaries else nom[s]
                                     for s in nom}, [(1.0, comps[c]) for c in chans], secondaries), nom, secondaries)
        cres = {"closure": closure, "channels": {}}
        for c in chans:
            tag, prod = c.replace("->", "-"), c.split("->")[1]
            entry = {}
            # main-channel fraction: response over the nominal numerator of its observable, per bin
            num, edges, axis = (BORON, BC_EDGES, "rigidity") if prod in BORON else (BERYLLIUM, BE_EDGES, "ekn")
            frac = []
            for lo, hi in zip(edges, edges[1:]):
                t = sum(rd.bin_integral(nom, s, lo, hi, axis) for s in num if s in nom)
                f = sum(rd.bin_integral(comps[c], s, lo, hi, axis) for s in num if s in nom)
                frac.append(f / t)
            entry["fraction_of_numerator"] = {"observable": "B/C" if prod in BORON else "Be/B", "min": min(frac),
                                              "max": max(frac)}
            for eps in EPSILONS:
                lab = f"{'p' if eps > 0 else 'm'}{abs(round(eps * 100))}"
                rerun = read(out, f"{cfg}-{tag}-{lab}")
                entry[f"norm_{lab}"] = deviation(combine(nom, [(eps, comps[c])], secondaries), rerun, secondaries)
                if prod == "10Be":
                    entry[f"norm_{lab}_without_daughter_update"] = deviation(
                        combine(nom, [(eps, comps[c])], secondaries, skip=("10B",)), rerun, secondaries)
            entry["norm_max_dev"] = max(entry[k]["max"] for k in ("norm_p20", "norm_m20"))
            cres["channels"][c] = entry
        results["b3_2"][cfg] = cres
    for cfg in SLOPE_CONFIGS:
        nom = read(out, f"{cfg}-nom")
        base = translation(cfg)["production_mb"]
        secondaries = sorted({c.split("->")[1] for c in base} | {"10B"})
        results["slope"][cfg] = {}
        for c in SLOPE_CHANNELS:
            tag = c.replace("->", "-")
            rerun = read(out, f"{cfg}-slope-{tag}")
            comp = read(out, f"{cfg}-only-{tag}")
            post = {s: (x, [v + (table_weight(e) - 1.0) * q for e, v, q in zip(x, y, comp[s][1])])
                    if s in secondaries else (x, y) for s, (x, y) in nom.items()}
            nodes = table_nodes()
            parts = [(-1.0, comp)]
            for k, e in enumerate(nodes):
                name = f"{cfg}-basis-{tag}-k{k}"
                if (out / "runs" / name).is_dir():
                    parts.append((slope_weight(e), read(out, name)))
            parts.append((1.0, read(out, f"{cfg}-basis-{tag}-rest")))
            basis = combine(nom, parts, secondaries)
            results["slope"][cfg][c] = {"post_propagation_weight": deviation(post, rerun, secondaries),
                                        "energy_basis": deviation(basis, rerun, secondaries),
                                        "n_basis_runs": len(parts) - 1, "slope_effect": deviation(nom, rerun,
                                                                                                 secondaries)}
    # channel list (B3 step 2) and must_rerun flags (B3-3)
    for cfg in NORM_CONFIGS:
        for c, entry in results["b3_2"][cfg]["channels"].items():
            fr = entry["fraction_of_numerator"]
            main = fr["max"] >= MAIN_FRACTION
            row = {"channel": c, "config": cfg, "main": main, "fraction_of_numerator": fr,
                   "norm": {"method": "single-channel response, level by level (r3 P5)",
                            "max_dev": entry["norm_max_dev"], "tolerance": TOL_B32,
                            "must_rerun": entry["norm_max_dev"] > TOL_B32},
                   "inelastic": {"must_rerun": True, "tested": False,
                                 "reason": "inelastic cross sections are not linear (r3 P5); always rerun"}}
            sl = results["slope"].get(cfg, {}).get(c)
            if sl:
                post_ok = sl["post_propagation_weight"]["max"] <= TOL_B32
                basis_ok = sl["energy_basis"]["max"] <= TOL_B32
                row["slope"] = {"form": f"sigma (E/{E_THR_GEV:g} GeV/n)^{SLOPE_S:g} below {E_THR_GEV:g} GeV/n",
                                "post_propagation_weight_max_dev": sl["post_propagation_weight"]["max"],
                                "energy_basis_max_dev": sl["energy_basis"]["max"],
                                "n_basis_runs": sl["n_basis_runs"],
                                "method": ("post-propagation weight" if post_ok else
                                           "energy-basis responses" if basis_ok else None),
                                "must_rerun": not (post_ok or basis_ok)}
            else:
                row["slope"] = {"must_rerun": True, "tested": False,
                                "reason": "no energy-basis responses computed for this channel and configuration; an "
                                          "energy-dependent change needs them or a rerun (r3 P5)"}
            channels.append(row)
    chan_doc = {"description": "cr-propagation B3: production channels of the ILLUSTRATIVE sets in the B3 USINE "
                               "configurations, their share of the observable numerator, and whether reweighting may "
                               "replace a rerun (r3 B3 steps 2-3, P5; criteria VALIDATION.md CRPROP-B3)",
                "status": "synthetic", "labels": ["synthetic", "unvalidated"], "tolerance": TOL_B32,
                "main_fraction": MAIN_FRACTION, "channels": channels}
    return results, chan_doc


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--jobs", type=int, default=4)
    p.add_argument("--only", default="")
    p = sub.add_parser("analyze")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--results", required=True, type=Path)
    p.add_argument("--channels", required=True, type=Path)
    p = sub.add_parser("compare")
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--spec", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        if args.command == "compare":
            doc = json.loads(args.spec.read_text(encoding="utf-8"))
            run = json.loads((args.run_dir / "translation.json").read_text(encoding="utf-8"))
            tables = rd.read_run(args.run_dir / "out", run["model"], run["species"])
            print(json.dumps(compare_b31(tables, doc["transport"]), indent=1))
            return 0
        if args.command == "analyze":
            results, chans = analyze(args.out)
            args.results.write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
            args.channels.write_text(json.dumps(chans, indent=1) + "\n", encoding="utf-8")
            print(json.dumps({"status": "ok", "results": str(args.results), "channels": str(args.channels)}))
            return 0
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    binary, data_dir = os.environ.get("HEP_USINE_BIN"), os.environ.get("HEP_USINE_DATA")
    if not binary or not Path(binary).is_file() or not data_dir or not Path(data_dir).is_dir():
        print(json.dumps({"status": "missing-dependency", "error": "set HEP_USINE_BIN and HEP_USINE_DATA"}))
        return 3
    plan = [i for i in run_plan() if args.only in i["name"]]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "plan.json").write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.jobs, 4))) as pool:
        done = list(pool.map(lambda i: execute(i, args.out, Path(binary), Path(data_dir)), plan))
    (args.out / "run-index.json").write_text(json.dumps(done, indent=1) + "\n", encoding="utf-8")
    failed = [d for d in done if not d["ok"]]
    print(json.dumps({"status": "ok" if not failed else "failed", "runs": len(done),
                      "wall_seconds_sum": round(sum(d["seconds"] for d in done), 1),
                      "failed": [{k: d[k] for k in ("name", "problems", "log_tail")} for d in failed]}, indent=1))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
