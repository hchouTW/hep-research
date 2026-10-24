#!/usr/bin/env python3
"""Implementation checks of the geant4 adapter's programs: overlaps, material budget, energy balance, mirror, field.

Purpose: verification that the application is written correctly, before any physics question. A pass here is not
validation: it says nothing about whether the physics list suits the observable (hep-detector decides that).

Checks (subcommands):
  Geometry: the placements, thicknesses and materials come from the effective config's geometry tree for runs from
  adapter 0.2.0 whose probe recorded (geometry_source "effective config"), else from the run record's spec/1.
  overlaps  construction-time checkOverlaps of every placement (layered_sim places every slab with its own
            G4PVPlacement, no replicas, because G4PVReplica does not override CheckOverlaps) plus /geometry/test/run;
            neither may report an overlap (G4Exception GeomVol1002). Both are sampled checks: a pass is not proof.
  budget    material-budget closure: sum t/X0 and sum t/lambda_I along the axis from the spec thicknesses and the
            material dump agree with the path lengths a geantino scan accumulated (plen_<slab>_mm), and the dump's
            density matches every user material of the spec. The dump is used only here, never as a reference input.
  balance   energy balance per event: residual = E_in - sum deposits (slabs and world) - sum leakage (all
            categories, an escaping e+ with 2 m_e c^2 added) - killed energy not booked - 2 m_e c^2 x killed e+
            (a killed e+ does not annihilate), with E_in = primary kinetic energy (+ 2 m_e c^2 for an e+ primary).
            Killed energy already booked as a deposit (G4UserSpecialCuts) is not subtracted again. A closure verdict
            only for an EM-only list (em_constructor) with an e-, e+ or gamma primary; otherwise the residual is
            reported without a verdict. --inject omit-positron-mass | double-count-booked applies a deliberately
            wrong accounting (negative controls: the check must fail); an injection that changes no event is
            reported incomplete (exit 3), never as a pass. element_sim runs take omit-positron-mass and
            double-count-leakage (the calorimeter leakage subtracted again on top of the escape).
  mirror    a layered_sim mirror run against the local official example (TestEm3 run 0 or TestEm5 run 0) at the
            same settings: only quantities present on both sides, z-tests with a Bonferroni threshold.
  datapaths the data-path comparison of a run record (resolved paths and content hashes against the build record).
  field     (element_sim, Geant4 program B1.7) the deterministic field check: every charged-geantino primary of the
            run (a source cycle of energies and directions) is followed analytically through the field regions of
            the run's spec, or of --reference-spec (a negative control runs Geant4 with B scaled and checks it against
            the nominal field), with core/simulation/helix.py; the first entry of the primary (track 1) into every
            tracker plane and TOF layer, read from the event file's crossings with simroot, must lie within
            --tolerance-um (default 0.5 um) of the analytic entry point in the plane (sqrt(dy^2 + dz^2) for planes
            normal to x) and, for TOF layers, within --tolerance-ps (default 1 ps) in time; a plane the analytic
            trajectory reaches without a Geant4 row, or the reverse, fails. |x - x_face| of Geant4's point is
            reported. No statistics: the geantino has no interactions.
For element_sim runs (adapter 0.3.0) the budget check reads the primary path lengths plen_<element>_mm and the balance
check's residual is E_in - sum deposits (elements and world) - escape_world_MeV (an escaping e+ with 2 m_e c^2).
Each check can write a computational-run record (--record) that lists the checked run record as an input (status
declared, sha256) and so carries its labels.
Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_verify.py overlaps --run-record RUN.json [--record OUT.json]
  python3 adapters/geant4/assets/geant4_verify.py budget --run-record GEANTINO_RUN.json [--tolerance 1e-6]
  python3 adapters/geant4/assets/geant4_verify.py balance --run-record RUN.json --tolerance-mev T [--inject KIND]
  python3 adapters/geant4/assets/geant4_verify.py mirror --run-record RUN.json --example TestEm3|TestEm5 --local-out FILE.out [--alpha 0.05]
  python3 adapters/geant4/assets/geant4_verify.py datapaths --run-record RUN.json
  python3 adapters/geant4/assets/geant4_verify.py field --run-record RUN.json [--reference-spec SPEC.json]
      [--tolerance-um 0.5] [--tolerance-ps 1.0] [--simroot SIMROOT]
The run record's work folder is found from extension.environment.work; --work overrides it.
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Exit codes: 0 the check passed (or reported without a verdict); 1 it failed; 2 bad input; 3 an injected negative
control had nothing to act on. Standard library only.
"""
from __future__ import annotations

import datetime
import gzip
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import JsonArgumentParser, SpecError, expand, record_skeleton, sha256_file, tilde, write_json  # noqa: E402
from core import constants as K  # noqa: E402
from core.simulation import helix as HELIX  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

ME_C2_MEV = K.constant("electron_mass_energy", unit="MeV").value  # CODATA 2022
EM_PRIMARIES = {"e-", "e+", "gamma"}
INJECTIONS = ("omit-positron-mass", "double-count-booked", "double-count-leakage")


def load_run(args) -> tuple[dict, Path, Path]:
    """The run record, its work folder and its run folder."""
    path = expand(str(args.run_record))
    rec = json.loads(path.read_text(encoding="utf-8"))
    sim = rec.get("extension", {}).get("simulation")
    if not sim:
        raise SpecError("not a geant4_run.py record (no extension.simulation)")
    work = expand(args.work) if args.work else expand(rec["extension"]["environment"]["work"])
    run_id = rec["artifact_id"].removeprefix("geant4-run-")
    return rec, work, work / run_id


def read_csv(path: Path) -> list[dict]:
    """Rows of a layered_sim CSV; events.csv may be replaced by a reduced events.csv.gz (geant4_run.py reduce)."""
    if not path.is_file() and path.with_name(path.name + ".gz").is_file():
        path = path.with_name(path.name + ".gz")
    raw = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if not lines or lines[0] != "# SIMULATION":
        raise SpecError(f"{tilde(path)} is not a layered_sim CSV")
    cols = lines[1].split(",")
    out = []
    for ln in lines[2:]:
        if not ln:
            continue
        row = {}
        for c, v in zip(cols, ln.split(",")):
            try:
                row[c] = float(v)
            except ValueError:
                row[c] = v
        out.append(row)
    return out


def is_element(rec: dict) -> bool:
    return rec["extension"]["simulation"].get("program", {}).get("name") == "element_sim"


def primary(sim: dict) -> str:
    return (sim.get("gun") or sim.get("source") or {}).get("particle")


def placements(rec: dict) -> tuple[list[tuple[str, float, str]], str]:
    """(slab name, thickness along x in mm, material) of every placement below the world, and the source: the
    effective config's geometry tree for runs from adapter 0.2.0 whose probe recorded (A2.6), else spec/1."""
    sim = rec["extension"]["simulation"]
    tree = ((sim.get("effective_config") or {}).get("geometry") or {}).get("tree")
    if tree:
        lvs = {lv["id"]: lv for lv in tree["logical_volumes"]}
        out = []
        for pl in tree["placements"]:
            if pl.get("mother_logical") is None:
                continue
            lv = lvs[pl["logical"]]
            par = (lv.get("solid") or {}).get("parameters") or {}
            out.append((lv["name"], 2 * float.fromhex(par["half_x_mm"]) if "half_x_mm" in par else float("nan"),
                        lv.get("material")))
        return out, "effective config"
    return [(sl["name"], sl["thickness_mm"], sl["material"]) for layer in sim["geometry"]["layers"]
            for _ in range(layer.get("repeat", 1)) for sl in layer["slabs"]], "spec/1"


def check_overlaps(rec: dict, run_dir: Path) -> tuple[str, dict]:
    log = (run_dir / "log.txt").read_text(encoding="utf-8", errors="replace")
    pls, source = placements(rec)
    expected = len(pls) + 1  # + the world
    checked = sum(1 for ln in log.splitlines() if ln.startswith("Checking overlaps for volume") and "OK!" in ln)
    reports = log.count("GeomVol1002")
    test_run = "/geometry/test/run" in log or rec["extension"]["simulation"].get("geometry") is not None
    points = (json.loads((run_dir / "spec.json").read_text(encoding="utf-8")).get("output", {})
              .get("overlap_test_points", 0))
    ok = reports == 0 and checked >= expected - 1 and points > 0
    return ("ok" if ok else "failed"), {
        "check": "overlaps", "placements_expected": expected - 1, "geometry_source": source,
        "construction_checks_ok": checked,
        "overlap_reports": reports, "geometry_test_run_points": points, "geometry_test_run_requested": bool(test_run),
        "note": "sampled checks (construction-time checkOverlaps and /geometry/test/run): a pass is not a proof"}


def check_budget(rec: dict, run_dir: Path, tol: float) -> tuple[str, dict]:
    sim = rec["extension"]["simulation"]
    if primary(sim) != "geantino":
        raise SpecError("the material-budget check needs a geantino run along the axis")
    dump = {m["name"]: m for m in json.loads((run_dir / "materials.json").read_text(encoding="utf-8"))["materials"]}
    rows = read_csv(run_dir / "events.csv")
    problems, slabs = [], []
    pls, source = placements(rec)
    for name, t, mat in pls:
        m = dump.get(mat)
        if m is None:
            problems.append(f"material {mat} missing from the dump")
            continue
        slabs.append((name, t, m))
    for user in sim.get("materials", []):
        m = dump.get(user["name"])
        if m and abs(m["density_g_cm3"] / user["density_g_cm3"] - 1) > tol:
            problems.append(f"{user['name']}: dump density {m['density_g_cm3']} != spec {user['density_g_cm3']}")
    by_name = {}
    if is_element(rec):  # mothers are traversed too: only leaf elements (no daughters) carry a thickness
        mothers = {e.get("mother") for e in sim["elements"]}
        slabs = [s for s in slabs if s[0] not in mothers]
    for name, t, m in slabs:
        e = by_name.setdefault(name, [0.0, m])
        e[0] += t
    spec_x0 = sum(t / (10 * m["radiation_length_cm"]) for t, m in by_name.values())
    spec_li = sum(t / (10 * m["nuclear_interaction_length_cm"]) for t, m in by_name.values())
    scan = {n: statistics.fmean(r[f"plen_{n}_mm"] for r in rows) for n in by_name}
    scan_x0 = sum(scan[n] / (10 * m["radiation_length_cm"]) for n, (_, m) in by_name.items())
    scan_li = sum(scan[n] / (10 * m["nuclear_interaction_length_cm"]) for n, (_, m) in by_name.items())
    for n, (t, _) in by_name.items():
        if abs(scan[n] - t) > tol * max(t, 1e-12):
            problems.append(f"slab {n}: geantino path {scan[n]} mm != spec thickness {t} mm")
    for label, a, b in (("X0", spec_x0, scan_x0), ("lambda_I", spec_li, scan_li)):
        if abs(a - b) > tol * max(abs(a), 1e-300):
            problems.append(f"sum t/{label}: spec {a} != geantino {b}")
    return ("ok" if not problems else "failed"), {
        "check": "material-budget", "geometry_source": source, "tolerance_relative": tol, "spec_x_over_X0": spec_x0,
        "scan_x_over_X0": scan_x0,
        "spec_x_over_lambda_I": spec_li, "scan_x_over_lambda_I": scan_li, "problems": problems,
        "note": "X0 and lambda_I come from the Geant4 material dump: closure of the application, never a reference"}


def residuals(rows: list[dict], particle: str, inject: str | None) -> list[float]:
    out = []
    for r in rows:
        e_in = r["primary_ekin_MeV"] + (2 * ME_C2_MEV if particle == "e+" and inject != "omit-positron-mass" else 0)
        dep = sum(v for k, v in r.items() if k.startswith("edep_") and k.endswith("_MeV") and "_copy" not in k)
        if "escape_world_MeV" in r:  # element_sim (adapter 0.3.0): no killed tracks; 2 m_e c^2 already in the escape
            res = e_in - dep - r["escape_world_MeV"]
            if inject == "double-count-leakage":  # the calorimeter's leakage counted again on top of the escape
                res -= r.get("leak_rear_MeV", 0.0) + r.get("leak_front_MeV", 0.0) + r.get("leak_lateral_MeV", 0.0)
            out.append(res)
            continue
        leak = r["leak_gamma_MeV"] + r["leak_e_MeV"] + r["leak_nu_MeV"] + r["leak_other_MeV"]
        res = e_in - dep - leak - r["killed_unbooked_MeV"]
        if inject != "omit-positron-mass":
            res -= 2 * ME_C2_MEV * r["killed_eplus"]
        if inject == "double-count-booked":
            res -= r["killed_booked_MeV"]
        out.append(res)
    return out


def check_balance(rec: dict, run_dir: Path, tol: float, inject: str | None) -> tuple[str, dict]:
    sim = rec["extension"]["simulation"]
    rows = read_csv(run_dir / "events.csv")
    if not rows:
        raise SpecError("no events")
    if inject == "double-count-booked" and is_element(rec):
        raise SpecError("--inject double-count-booked applies to layered_sim's killed tracks; element_sim kills none "
                        "(use double-count-leakage)")
    if inject == "double-count-leakage" and not is_element(rec):
        raise SpecError("--inject double-count-leakage applies to element_sim's calorimeter leakage")
    res = residuals(rows, primary(sim), inject)
    em_only = "em_constructor" in sim["physics"] and primary(sim) in EM_PRIMARIES
    worst = max(res, key=abs)
    doc = {"check": "energy-balance", "tolerance_MeV": tol, "events": len(res),
           "residual_mean_MeV": statistics.fmean(res), "residual_rms_MeV": math.sqrt(statistics.fmean(x * x for x in res)),
           "residual_max_abs_MeV": abs(worst), "events_beyond_tolerance": sum(abs(x) > tol for x in res),
           "events_with_killed_eplus": sum(1 for r in rows if r.get("killed_eplus", 0) > 0),
           "killed_booked_MeV_total": math.fsum(r.get("killed_booked_MeV", 0.0) for r in rows),
           "injected_error": inject, "closure_test": em_only,
           "formula": "E_in - deposits - leakage - killed_unbooked - 2 m_e c^2 x killed_eplus "
                      "(E_in includes 2 m_e c^2 for an e+ primary; booked killed energy is already a deposit)"}
    if inject:
        affected = sum(1 for a, b in zip(res, residuals(rows, primary(sim), None)) if abs(a - b) > 0)
        doc["events_affected_by_injection"] = affected
        if affected == 0:
            doc["note"] = ("the injected error changes no event of this run (no killed tracks, no killed e+, no e+ "
                           "primary): not a negative control here; use a run with killed tracks (min_ekin_MeV)")
            return "incomplete", doc
    if not em_only:
        doc["note"] = "not an EM-only list with an e-, e+ or gamma primary: the residual is reported without a verdict"
        return "ok", doc
    return ("ok" if doc["events_beyond_tolerance"] == 0 else "failed"), doc


MIRROR = {  # example: [(local .out quantity, function of the mirror rows -> per-event values, kind)]
    "TestEm3": [("edep_G4_Pb_MeV", lambda r: r["edep_Pb_MeV"], "mean"),
                ("edep_G4_lAr_MeV", lambda r: r["edep_lAr_MeV"], "mean"),
                ("edep_rms_G4_Pb_MeV", lambda r: r["edep_Pb_MeV"], "sd"),
                ("edep_rms_G4_lAr_MeV", lambda r: r["edep_lAr_MeV"], "sd"),
                ("tracklen_G4_Pb_mm", lambda r: r["chlen_Pb_mm"], "mean"),
                ("tracklen_G4_lAr_mm", lambda r: r["chlen_lAr_mm"], "mean"),
                ("edep_total_MeV", lambda r: r["edep_Pb_MeV"] + r["edep_lAr_MeV"], "mean")],
    "TestEm5": [("edep_MeV", lambda r: r["edep_Si_MeV"], "mean"),
                ("leak_primary_MeV", lambda r: r["exit_ekin_MeV"], "mean"),
                ("leak_secondaries_MeV", lambda r: r["leak_gamma_MeV"] + r["leak_e_MeV"] + r["leak_nu_MeV"]
                 + r["leak_other_MeV"] - r["exit_ekin_MeV"], "mean"),
                ("tracklen_charged_mm", lambda r: r["chlen_Si_mm"], "mean"),
                ("transmitted_fraction", lambda r: float(r["primary_fate"] == 1), "fraction"),
                ("reflected_fraction", lambda r: float(r["primary_fate"] == -1), "fraction")],
}


def check_mirror(rec: dict, run_dir: Path, example: str, local_out: Path, alpha: float) -> tuple[str, dict]:
    from geant4_examples import EXTRACTORS  # sibling script
    local = {r["quantity"]: r for r in EXTRACTORS[example](local_out.read_text(encoding="utf-8", errors="replace"))
             if r["run"] == 0}
    rows = read_csv(run_dir / "events.csv")
    n = len(rows)
    m = len(MIRROR[example])
    z_crit = statistics.NormalDist().inv_cdf(1 - alpha / (2 * m))
    table, bad = [], []
    for q, fn, kind in MIRROR[example]:
        if q not in local:
            raise SpecError(f"{q} not found in run 0 of {tilde(local_out)}")
        vals = [fn(r) for r in rows]
        mean, sd = statistics.fmean(vals), statistics.stdev(vals)
        ref = local[q]
        if kind == "sd":
            val, se = sd, sd / math.sqrt(2 * n)
        elif kind == "fraction":
            val = mean
            pp = (mean * n + ref["value"] * ref["n"]) / (n + ref["n"])
            se = math.sqrt(max(pp * (1 - pp), 0) * (1 / n + 1 / ref["n"]))
        else:
            val, se = mean, sd / math.sqrt(n)
        se_tot = se if kind == "fraction" else math.hypot(se, ref["se"] or 0)
        z = (val - ref["value"]) / se_tot if se_tot > 0 else 0.0
        verdict = "pass" if abs(z) <= z_crit else "fail"
        if verdict == "fail":
            bad.append(q)
        table.append({"quantity": q, "mirror": val, "se_mirror": se, "local_example": ref["value"],
                      "se_local_example": ref["se"], "z": z, "verdict": verdict})
    return ("ok" if not bad else "failed"), {
        "check": "mirror", "example": example, "local_example_output": tilde(local_out), "events_mirror": n,
        "events_local_example": next(iter(local.values()))["n"], "alpha_family": alpha, "z_crit": z_crit,
        "rows": table, "failed": bad,
        "note": "verification against the local official example at the same settings; not validation"}


PLANE_ROLES = ("tracker-plane", "tof-layer")


def _element_boxes(spec: dict, name: str) -> list[tuple[list, list]]:
    for e in spec["elements"]:
        if e["name"] == name:
            n = (e.get("repeat") or {}).get("count", 1)
            pitch = (e.get("repeat") or {}).get("pitch_mm", [0.0, 0.0, 0.0])
            shift = e.get("shift_mm", [0.0, 0.0, 0.0])
            out = []
            for k in range(n):
                c = [e["centre_mm"][i] + k * pitch[i] + shift[i] for i in range(3)]
                out.append(([c[i] - e["half_mm"][i] for i in range(3)], [c[i] + e["half_mm"][i] for i in range(3)]))
            return out
    raise SpecError(f"element {name} not in the spec")


def read_crossings(simroot: Path, root_file: Path) -> list[dict]:
    p = subprocess.run([str(simroot), "dump", str(root_file), "--ntuple", "crossings"], capture_output=True, text=True,
                       timeout=3600)
    if p.returncode != 0:
        raise SpecError(f"simroot dump failed (exit {p.returncode}): {p.stdout.strip()[:300]}")
    lines = p.stdout.splitlines()
    cols = lines[0].split(",")
    return [{c: float(v) for c, v in zip(cols, ln.split(","))} for ln in lines[1:] if ln]


def check_field(rec: dict, run_dir: Path, reference: dict | None, tol_um: float, tol_ps: float,
                simroot: Path | None) -> tuple[str, dict]:
    sim = rec["extension"]["simulation"]
    if not is_element(rec):
        raise SpecError("the field check reads an element_sim run (its event file's crossings)")
    spec = json.loads((run_dir / "spec.json").read_text(encoding="utf-8"))
    ref = reference or spec
    src = spec["source"]
    if src.get("particle") != "chargedgeantino":
        raise SpecError("the field check needs charged geantinos (mass 0, beta = 1, no interactions)")
    level = ((spec.get("output") or {}).get("event_file") or {}).get("level", "none")
    if level not in ("crossings", "hits"):
        raise SpecError("the field check needs an event file at level crossings or hits")
    ef = sim.get("event_file") or {}
    simroot = simroot or (expand(ef["simroot"]["path"]) if ef.get("simroot") else None)
    if simroot is None or not simroot.is_file():
        raise FileNotFoundError("simroot not found (--simroot)")
    boxes = []
    for r in (ref.get("field") or {}).get("regions", []):
        (lo, hi), = _element_boxes(ref, r["element"])
        boxes.append(HELIX.FieldBox(lo, hi, list(r["b_tesla"])))
    names = [e["name"] for e in spec["elements"] if e["role"] in PLANE_ROLES]
    index = {e["name"]: i for i, e in enumerate(spec["elements"])}
    roles = {e["name"]: e["role"] for e in spec["elements"]}
    rows = [r for r in read_crossings(simroot, run_dir / "events.root") if int(r["track_id"]) == 1]
    g4 = {(int(r["event_id"]), int(r["plane_id"]), int(r["copy"])): r for r in rows}
    cycle = src.get("cycle") or [{"energy_MeV": src["energy_MeV"], "direction": src.get("direction", [1.0, 0.0, 0.0])}]
    first, n = spec["run"].get("first_event", 0), spec["run"]["events"]
    table, problems, worst_um, worst_ps, worst_dx = [], [], 0.0, 0.0, 0.0
    for ev in range(first, first + n):
        c = cycle[ev % len(cycle)]
        p_gev = c["energy_MeV"] / 1000.0  # massless: p = E
        traj = HELIX.trajectory(src.get("position_mm", [0.0, 0.0, 0.0]), c["direction"], p_gev, 1.0, boxes, 1e5)
        for name in names:
            for k, (lo, hi) in enumerate(_element_boxes(spec, name)):
                a = HELIX.first_entry(traj, lo, hi)
                got = g4.get((ev, index[name], k))
                if a is None and got is None:
                    continue
                if a is None or got is None:
                    problems.append(f"event {ev} plane {name} copy {k}: "
                                    + ("Geant4 recorded an entry the analytic trajectory does not make" if a is None
                                       else "the analytic trajectory enters, Geant4 recorded no entry"))
                    continue
                x = a["position_mm"]
                face = min(range(3), key=lambda i: min(abs(x[i] - lo[i]), abs(x[i] - hi[i])))  # the entry face
                other = [i for i in range(3) if i != face]
                gp = [got["x_mm"], got["y_mm"], got["z_mm"]]
                d_um = 1e3 * math.hypot(gp[other[0]] - x[other[0]], gp[other[1]] - x[other[1]])
                dx = abs(gp[face] - x[face]) * 1e3
                dt_ps = (got["t_ns"] - a["time_ns"]) * 1e3
                worst_um, worst_dx = max(worst_um, d_um), max(worst_dx, dx)
                row = {"event": ev, "plane": name, "copy": k, "rigidity_GV": p_gev, "in_plane_um": d_um,
                       "normal_um": dx}
                if roles[name] == "tof-layer":
                    row["dt_ps"] = dt_ps
                    worst_ps = max(worst_ps, abs(dt_ps))
                    if abs(dt_ps) > tol_ps:
                        problems.append(f"event {ev} {name}: |dt| = {abs(dt_ps):.3g} ps > {tol_ps} ps")
                if d_um > tol_um:
                    problems.append(f"event {ev} {name}: in-plane distance {d_um:.3g} um > {tol_um} um")
                table.append(row)
    status = "ok" if not problems and table else "failed"
    if not table:
        problems.append("no crossing was compared")
    return status, {"check": "field-propagation", "tolerance_um": tol_um, "tolerance_ps": tol_ps,
                    "reference": "the run's own spec" if reference is None else "--reference-spec",
                    "field_regions": [{"lo": b.lo, "hi": b.hi, "b_tesla": b.b_tesla} for b in boxes],
                    "events": n, "compared": len(table), "max_in_plane_um": worst_um, "max_dt_ps": worst_ps,
                    "max_normal_um": worst_dx, "rows": table, "problems": problems[:50],
                    "note": "deterministic (no statistics): charged geantinos against the analytic helix "
                            "(core/simulation/helix.py); verification, not validation"}


def check_datapaths(rec: dict) -> tuple[str, dict]:
    sim = rec["extension"]["simulation"]
    problems = sim.get("data_path_problems", [])
    return ("ok" if not problems and sim.get("datasets") else "failed"), {
        "check": "data-paths", "datasets": sim.get("datasets", []), "problems": problems}


def write_record(args, run_rec: dict, status: str, doc: dict) -> str:
    path = expand(args.record)
    labels = list(dict.fromkeys(run_rec["status"] + (["failed"] if status == "failed" else [])))
    rec = record_skeleton(f"geant4-verify-{doc['check']}-{run_rec['artifact_id'].removeprefix('geant4-run-')}",
                          f"Implementation check '{doc['check']}' of {run_rec['artifact_id']} (verification, not "
                          "validation)", args.created or datetime.date.today().isoformat(), labels)
    run_path = expand(str(args.run_record))
    try:
        ref = str(run_path.relative_to(path.parent))
    except ValueError:
        ref = tilde(run_path)
    rec["inputs"] = [{"ref": ref, "artifact_type": "computational-run", "artifact_id": run_rec["artifact_id"],
                      "sha256": sha256_file(run_path), "status": run_rec["status"]}]
    rec["extension"] = {"input_manifest": [{"path": ref, "sha256": sha256_file(run_path)}],
                        "tools": [{"name": "geant4_verify.py", "version": sha256_file(Path(__file__))[:16]}],
                        "commands": [f"geant4_verify.py {doc['check']}"], "environment": {}, "seeds": {},
                        "tolerances": {k: v for k, v in doc.items() if k.startswith("tolerance") or k == "z_crit"},
                        "exit_status": exit_code(status), "output_hashes": {}, "verification": doc}
    write_json(path, rec)
    return tilde(path)


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    for name, help_text in (("overlaps", "construction-time and /geometry/test/run overlap reports"),
                            ("budget", "material-budget closure from a geantino run"),
                            ("balance", "per-event energy balance"),
                            ("mirror", "mirror run against the local official example"),
                            ("datapaths", "resolved data paths against the build record"),
                            ("field", "element_sim crossings of charged geantinos against the analytic helix")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--run-record", required=True)
        p.add_argument("--work")
        p.add_argument("--record", help="write a computational-run record of the check here")
        p.add_argument("--created")
        add_status_argument(p)
        if name == "budget":
            p.add_argument("--tolerance", type=float, default=1e-6, help="relative tolerance (default 1e-6)")
        if name == "balance":
            p.add_argument("--tolerance-mev", type=float, required=True, help="per-event |residual| limit, declared")
            p.add_argument("--inject", choices=INJECTIONS, help="a deliberately wrong accounting (negative control)")
        if name == "field":
            p.add_argument("--reference-spec", help="the field regions to check against (default: the run's own)")
            p.add_argument("--tolerance-um", type=float, default=0.5, help="in-plane distance limit (default 0.5)")
            p.add_argument("--tolerance-ps", type=float, default=1.0, help="TOF-layer time limit (default 1)")
            p.add_argument("--simroot", help="the simroot executable (default: the run record's)")
        if name == "mirror":
            p.add_argument("--example", required=True, choices=sorted(MIRROR))
            p.add_argument("--local-out", required=True)
            p.add_argument("--alpha", type=float, default=0.05)
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("tolerance", "alpha", "created", "tolerance_um", "tolerance_ps", "status")
                if hasattr(args, k) and f"--{k.replace('_', '-')}" not in given]
    try:
        rec, work, run_dir = load_run(args)
        if args.command == "overlaps":
            status, doc = check_overlaps(rec, run_dir)
        elif args.command == "budget":
            status, doc = check_budget(rec, run_dir, args.tolerance)
        elif args.command == "balance":
            status, doc = check_balance(rec, run_dir, args.tolerance_mev, args.inject)
        elif args.command == "field":
            ref = json.loads(expand(args.reference_spec).read_text(encoding="utf-8")) if args.reference_spec else None
            status, doc = check_field(rec, run_dir, ref, args.tolerance_um, args.tolerance_ps,
                                      expand(args.simroot) if args.simroot else None)
        elif args.command == "mirror":
            local = expand(args.local_out)
            if not local.is_file():
                raise FileNotFoundError(f"{local} not found")
            status, doc = check_mirror(rec, run_dir, args.example, local, args.alpha)
        else:
            status, doc = check_datapaths(rec)
        if args.record:
            doc["record"] = write_record(args, rec, status, doc)
    except (SpecError, FileNotFoundError, KeyError, ValueError, IsADirectoryError, OSError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1, default=str))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
