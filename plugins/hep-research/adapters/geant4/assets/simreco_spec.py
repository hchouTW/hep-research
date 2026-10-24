#!/usr/bin/env python3
"""simreco reco specs of the geant4 adapter (Geant4 program B2.1, B2.2).

Imported by geant4_run.py (subcommand reco). It checks a simreco.spec/1 against simreco/spec.schema.json and the
cross-field rules (alignment and calibration-non-uniformity need at least 20 replicas; observables name result
columns; every tracker-plane material has a radiation length), and writes the effective spec simreco reads
(simreco.effective/1): the user's spec, the tracker planes and TOF layers of the element_sim run (entry face along
+x, thickness, transverse extent, x/X0), the field regions (B along z only), the calorimeter's active-deposit columns,
the particle table (masses and charges from core/constants, PDG 2026), the logical-run seed, the replica number and
the input and output paths. Run directly it only prints this help.
Exit codes: 0 (--help). Standard library only.
"""
from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import ASSETS, JsonArgumentParser, SpecError  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core import constants as K  # noqa: E402
from core.simulation import estimates as E  # noqa: E402
from core.stats import batch_means as M  # noqa: E402
from core.stats.distributions import t_ppf  # noqa: E402

SPEC_SCHEMA = ASSETS / "simreco" / "spec.schema.json"
TAIL_SOURCES = ("alignment", "calibration-non-uniformity", "noise-digitization", "pattern-recognition")  # design.py
REPLICA_TAILS = ("alignment", "calibration-non-uniformity")
MIN_REPLICAS = 20
RESULT_COLUMNS = ("event", "replica", "pdg", "charge_true", "rig_true_GV", "n_true_planes", "fit_ok", "n_hits",
                  "n_fake_hits", "chi2", "ndof", "selected", "charge_reco", "rig_reco_GV", "inv_rig_res", "rho_sigma", "rho_pull",
                  "charge_flip", "beta_true", "beta_reco", "beta_res", "tof1_layer_dt_ps", "tof2_layer_dt_ps",
                  "tof1_layer_resid_ps", "tof2_layer_resid_ps", "e_cal_MeV", "e_over_mip", "containment", "rear_leak_fraction")


def tails_on(spec: dict) -> list[str]:
    """The tail-source stages switched on, in TAIL_SOURCES order (what simreco writes as tail_sources_simulated)."""
    t = spec.get("tail_sources") or {}
    return [n for n in TAIL_SOURCES if (t.get(n) or {}).get("on")]


def _inert_tails(spec: dict, element_spec: dict | None) -> list[str]:
    """A tail source switched on must act: it is then listed as simulated and an F4 value becomes an estimate
    (FID-03), so a stage with zero widths is refused rather than counted."""
    t = spec.get("tail_sources") or {}
    on = set(tails_on(spec))
    out = []
    a = t.get("alignment") or {}
    if "alignment" in on and not any(a.get(k, 0) > 0 for k in (
            "misalignment_sigma_y_um", "misalignment_sigma_z_um", "misalignment_sigma_rot_urad", "residual_sigma_y_um",
            "residual_sigma_z_um", "residual_sigma_rot_urad")):
        out.append("tail source alignment is on with every width zero: it would be listed as simulated and change nothing")
    if "alignment" in on and not a.get("method"):
        out.append("tail source alignment: name the alignment method its residual model stands for (method)")
    c = t.get("calibration-non-uniformity") or {}
    regions = len(((element_spec or {}).get("field") or {}).get("regions") or []) if element_spec is not None else None
    if "calibration-non-uniformity" in on and not (c.get("gradient_sigma", 0) > 0 or (
            c.get("sigma", 0) > 0 and (regions is None or regions >= 2))):
        out.append("tail source calibration-non-uniformity acts only with gradient_sigma > 0, or sigma > 0 and at least "
                   "two field regions (the common mean is removed)")
    n = t.get("noise-digitization") or {}
    if "noise-digitization" in on and not ("pitch_y_um" in n and "pitch_z_um" in n):
        out.append("tail source noise-digitization needs pitch_y_um and pitch_z_um (the strip digitization)")
    p = t.get("pattern-recognition") or {}
    if "pattern-recognition" in on and "window_mm" not in p:
        out.append("tail source pattern-recognition needs window_mm (the association window)")
    return out


def check(spec, element_spec: dict | None = None) -> list[str]:
    """Every problem of a simreco.spec/1 (and, with the element_sim spec, of the pair)."""
    if not isinstance(spec, dict):
        return ["the reco spec must be a JSON object"]
    rep = validate(spec, str(SPEC_SCHEMA))
    if not rep.ok:
        return [f"{f.path}: {f.message}" for f in rep.errors]
    problems = []
    if any(n in tails_on(spec) for n in REPLICA_TAILS) and spec.get("replicas", 1) < MIN_REPLICAS:
        problems.append(f"alignment and calibration-non-uniformity are random per replica: replicas must be at least "
                        f"{MIN_REPLICAS} (one draw is one realization, B2.2)")
    problems += _inert_tails(spec, element_spec)
    out = spec.get("output") or {}
    if ("observables" in out) != ("blocks" in out):
        problems.append("output.observables and output.blocks go together")
    if "observables" in out:
        r = validate(out["observables"], "simulation_observables.json")
        if not r.ok:
            problems.append("output.observables is not a simulation-observables/1 declaration")
        else:
            for o in out["observables"]:
                need = {o["source_column"], *(c["column"] for c in o.get("selection") or [])}
                if need - set(RESULT_COLUMNS):
                    problems.append(f"output.observables {o['name']}: {sorted(need - set(RESULT_COLUMNS))} are not "
                                    "simreco result columns")
    if element_spec is not None:
        for e in element_spec["elements"]:
            if e["role"] == "tracker-plane" and e["material"] not in spec["radiation_length_mm"]:
                problems.append(f"radiation_length_mm has no entry for {e['material']} (tracker plane {e['name']})")
            if e["role"] in ("tracker-plane", "tof-layer") and (e.get("repeat") or {}).get("count", 1) != 1:
                problems.append(f"plane {e['name']} is repeated: simreco reads one copy per plane element")
        for r in (element_spec.get("field") or {}).get("regions", []):
            if r["b_tesla"][0] != 0 or r["b_tesla"][1] != 0:
                problems.append(f"field region {r['element']}: simreco reconstructs a field along z only")
    return problems


def particle_table(source_particle: str) -> list[dict]:
    """Masses (GeV) and charges by PDG code from core/constants (PDG 2026), with antiparticles; PDG code 0 is the
    run's geantino (charged or not, mass 0)."""
    out = []
    for name in K.particle_names():
        rec = K.particle_record(name)
        mcid, charge = rec.get("mcid"), rec.get("charge")
        if not isinstance(mcid, int) or not isinstance(rec.get("mass"), dict) or charge is None:
            continue
        mass = K.particle(name, "mass", "GeV").value
        out.append({"pdg": mcid, "mass_GeV": mass, "charge": charge})
        if charge != 0:
            out.append({"pdg": -mcid, "mass_GeV": mass, "charge": -charge})
    out.append({"pdg": 0, "mass_GeV": 0.0, "charge": 1.0 if source_particle == "chargedgeantino" else 0.0})
    seen, uniq = set(), []
    for p in out:
        if p["pdg"] not in seen:
            seen.add(p["pdg"])
            uniq.append(p)
    return uniq


def effective(reco: dict, element_spec: dict, replica: int, io: dict, bending_um: float | None = None,
              tof_ps: float | None = None) -> dict:
    """The simreco.effective/1 of one replica; the design geometry's point resolution (bending) and TOF time
    resolution (mapping 1.1.0), when given, replace the reco spec's."""
    reco = json.loads(json.dumps(reco))
    if bending_um is not None:
        reco["point_resolution_um"]["bending"] = bending_um
    if tof_ps is not None:
        reco.setdefault("tof", {})["sigma_t_ps"] = tof_ps
    x0 = reco["radiation_length_mm"]
    planes = []
    for i, e in enumerate(element_spec["elements"]):
        if e["role"] not in ("tracker-plane", "tof-layer"):
            continue
        c = [e["centre_mm"][k] + e.get("shift_mm", [0.0, 0.0, 0.0])[k] for k in range(3)]
        t = 2 * e["half_mm"][0]
        planes.append({"id": i, "name": e["name"], "role": e["role"], "x_face_mm": c[0] - e["half_mm"][0],
                       "thickness_mm": t, "centre_y_mm": c[1], "centre_z_mm": c[2], "half_y_mm": e["half_mm"][1],
                       "half_z_mm": e["half_mm"][2],
                       "x_over_x0": t / x0[e["material"]] if e["role"] == "tracker-plane" else 0.0})
    els = {e["name"]: e for e in element_spec["elements"]}
    regions = []
    for r in (element_spec.get("field") or {}).get("regions", []):
        e = els[r["element"]]
        regions.append({"lo_mm": e["centre_mm"][0] - e["half_mm"][0], "hi_mm": e["centre_mm"][0] + e["half_mm"][0],
                        "bz_tesla": r["b_tesla"][2]})
    active = [f"edep_{e['name']}_MeV" for e in element_spec["elements"] if e["role"] == "calorimeter-active"]
    return {"schema": "simreco.effective/1", "reco": reco, "replica": replica,
            "logical_run_seed": element_spec["run"]["logical_run_seed"],
            "geometry": {"planes": planes, "field_regions": regions, "calorimeter_active_columns": active},
            "particles": particle_table(element_spec["source"].get("particle", "")), "io": io}


# --- F4 results (B2.3, B2.6) ---------------------------------------------------------------------------------------
# figure of merit -> the estimator its observable must use, whether it is a counting figure of merit, and the dataset
# quantity
# figure of merit -> estimator, counting, dataset quantity, the result column its observable must read, and whether the
# observable must select the fitted tracks (selected == 1: a failed fit is neither a flip nor a resolution entry)
FOM = {"momentum-resolution-core": {"estimator": "gaussian-core", "counting": False, "quantity": "resolution",
                                    "source_column": "inv_rig_res", "selected": True},
       "charge-confusion-rate": {"estimator": "proportion", "counting": True, "quantity": "fraction",
                                 "source_column": "charge_flip", "selected": True},
       "shower-containment": {"estimator": "mean", "counting": False, "quantity": "fraction",
                              "source_column": "containment", "selected": False},
       "tracking-selection-efficiency": {"estimator": "proportion", "counting": True, "quantity": "efficiency",
                                         "source_column": "selected", "selected": False}}
SELECTED = {"column": "selected", "op": "==", "value": 1}
COVERAGE = 0.90  # the F4 uncertainty object: a central interval at coverage 0.90 (CV-B2, B2.6)
Z95 = 1.6448536269514722  # one-sided 0.95 quantile of the unit normal


def replica_estimates(summaries: list[dict], decl: dict) -> list[dict]:
    return [E.estimate(s, decl) for s in summaries]


def check_denominator(den: dict, settings: dict) -> list[str]:
    """The denominator a table states against the simulated source (run settings: particle, kinetic energy): species
    equal to the particle, rigidity_GV equal to p/|q| of the gun (relative 1e-6), energy_GeV to its kinetic energy;
    a value that cannot be compared (no settings, an unknown particle) is not refused here."""
    part, ek = settings.get("particle"), settings.get("energy_MeV")
    out = []
    if "species" in den and isinstance(part, str) and den["species"] != part:
        out.append(f"denominator species {den['species']!r} is not the simulated particle {part!r}")
    if "energy_GeV" in den and isinstance(ek, (int, float)) and abs(float(den["energy_GeV"]) * 1000 / ek - 1) > 1e-6:
        out.append(f"denominator energy_GeV {den['energy_GeV']} is not the simulated kinetic energy {ek / 1000} GeV")
    if "rigidity_GV" in den and isinstance(part, str) and isinstance(ek, (int, float)):
        try:
            rec = K.particle_record(part)
            mass, charge = K.particle(part, "mass", "GeV").value, rec.get("charge")
        except (KeyError, ValueError, AttributeError):
            return out
        if charge:
            t = ek / 1000
            rig = math.sqrt(t * t + 2 * t * mass) / abs(charge)
            if abs(float(den["rigidity_GV"]) / rig - 1) > 1e-6:
                out.append(f"denominator rigidity_GV {den['rigidity_GV']} is not the simulated gun's {rig:.9g} GV")
    return out


def fom_result(fom: str, summaries: list[dict], decl: dict, denominator: dict) -> dict:
    """The F4 result of one figure of merit from the run summaries of the reconstruction replicas: value = the mean of
    the replica estimates; statistical_uncertainty = the 68.27 % t half-width of the batch means (A1; non-counting);
    s_rep = the SD of the replica estimates (alignment and field non-uniformity draws, B2.2); the uncertainty object
    (coverage 0.90, central; the five fields of a design-evaluation's uncertainty): non-counting, half-width
    sqrt((t_0.95(K-1) SE)^2 + (z_0.95 s_rep)^2), distribution non-gaussian; counting, the exact Clopper-Pearson 90 %
    interval of replica 0's counts, its distances from replica 0's proportion applied around the replica mean, with
    z_0.95 s_rep added in quadrature to each side, distribution exact (D0-c option (a): statistical (+) replica
    spread); the parts in uncertainty_components. The observable must read the figure of merit's result column (and
    select the fitted tracks where FOM says so)."""
    rule = FOM[fom]
    if decl.get("estimator", "mean") != rule["estimator"]:
        raise SpecError(f"{fom} is estimated with {rule['estimator']}; observable {decl['name']} declares "
                        f"{decl.get('estimator', 'mean')}")
    if decl.get("source_column") != rule["source_column"]:
        raise SpecError(f"{fom} reads the result column {rule['source_column']}; observable {decl['name']} reads "
                        f"{decl.get('source_column')}")
    if rule["selected"] and SELECTED not in (decl.get("selection") or []):
        raise SpecError(f"{fom}: observable {decl['name']} must select the fitted tracks ({SELECTED})")
    est = replica_estimates(summaries, decl)
    bad = next((e for e in est if e.get("status") != "ok" or e.get("value") is None), None)
    if bad:
        raise SpecError(f"observable {decl['name']} has no estimate: {bad.get('reason')}")
    values = [e["value"] for e in est]
    value = math.fsum(values) / len(values)
    s_rep = statistics.stdev(values) if len(values) > 1 else 0.0
    out = {"value": value, "estimator": {"name": rule["estimator"], "observable": decl["name"],
                                         **({"truncation_sigma": decl.get("core_truncation_sigma", 2.0)}
                                            if rule["estimator"] == "gaussian-core" else {})},
           "denominator": denominator, "replicas": len(values), "replica_spread": s_rep,
           "replica_values": values}
    if rule["counting"]:  # an exact interval always (design.py converts no counting interval)
        k, n = est[0]["k"], est[0]["n"]
        lo, hi = M.exact_proportion(k, n, COVERAGE)
        p0 = k / n if n else 0.0
        minus, plus = min(p0 - lo, value), hi - p0  # replica 0's interval shape, centred on the replica mean
        out["counts"] = {"k": k, "n": n, "interval": [lo, hi], "method": "Clopper-Pearson (replica 0)"}
        stat_desc = ("Clopper-Pearson 90 % interval of replica 0's counts, its distances from replica 0's proportion "
                     "applied around the replica mean")
    else:
        ses = [e["se"] for e in est]
        se, dof = math.fsum(ses) / len(ses), est[0]["dof"]
        out["statistical_uncertainty"] = M.t_halfwidth(se, dof)
        out["se"], out["dof"] = se, dof
        minus = plus = t_ppf(0.95, dof) * se
        stat_desc = "t_0.95(K-1) x batch-means SE over K blocks"
    out["uncertainty_components"] = {"statistical": {"minus": minus, "plus": plus, "method": stat_desc},
                                     "replica_spread": {"sd": s_rep, "half_width": Z95 * s_rep}}
    minus, plus = math.hypot(minus, Z95 * s_rep), math.hypot(plus, Z95 * s_rep)
    out["uncertainty"] = {"minus": minus, "plus": plus, "coverage": COVERAGE, "interval": "central",
                          "distribution": "exact" if rule["counting"] else "non-gaussian"}
    return out


def model_envelope(fom: str, variations: dict[str, list[dict]], decl: dict) -> dict:
    """[lo, hi] of the figure of merit over the variation table (nominal included), each end with its SE (B2.6)."""
    rows = {}
    for name, summaries in variations.items():
        r = fom_result(fom, summaries, decl, {})
        rows[name] = (r["value"], r.get("se") or (r["uncertainty"]["minus"] + r["uncertainty"]["plus"]) / (2 * Z95))
    lo = min(rows, key=lambda k: rows[k][0])
    hi = max(rows, key=lambda k: rows[k][0])
    return {"envelope": [rows[lo][0], rows[hi][0]], "ends": {"lo": {"variation": lo, "se": rows[lo][1]},
                                                             "hi": {"variation": hi, "se": rows[hi][1]}},
            "variations": {k: {"value": v[0], "se": v[1]} for k, v in rows.items()}}


if __name__ == "__main__":
    JsonArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    sys.exit(0)
