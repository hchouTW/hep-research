#!/usr/bin/env python3
"""Journey J15, live part (Geant4 program B3.2-B3.6): every Geant4 and simreco run behind J15's F4 studies, the
verification ladder and the multiple-scattering reference, written to recorded/ for the offline replay of run.py.

Needs Geant4 11.4.3 with element_sim and simroot (geant4 adapter 0.4.0) and simreco, named in a JSON file given by
HEP_GEANT4_CONFIG: {"build_record", "element_sim", "simreco"} (simroot next to element_sim). Runs go to --work
(outside the plugin); a run whose record exists is not repeated, so an interrupted campaign resumes. Event counts:
every evidence point of a study gets a trial run first and N = N_trial (SE_trial / target)^2 F_0.95(15, 15), rounded
up to a multiple of K = 16 (A1.9), fixed before the evidence run and never topped up. Seeds S = H(study_id, role,
point_id) (core/simulation/seeds.py). SYNTHETIC geometry; every record stays unvalidated except a study that passes
the qualification path (B2.8).

Usage (from the plugin root): HEP_GEANT4_CONFIG=cfg.json python3 examples/design-minimal-spectrometer/live.py
    --work DIR [--only STEP ...] [--recorded DIR]
Steps: msref, shared, ladder, tracking, cc, shower, export (default: all, in that order).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(HERE))
import run as R  # noqa: E402
from core.simulation.seeds import job_seeds, logical_run_seed  # noqa: E402
from core.stats.distributions import f_ppf  # noqa: E402
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
from geant4_benchmarks import GRADES as R_GRADE  # noqa: E402

RUN = [sys.executable, "-B", str(PLUGIN / "adapters/geant4/assets/geant4_run.py")]
CHECK = [sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/check_geant4_study.py")]
BENCH = [sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/geant4_benchmarks.py")]
PROFILE = HERE / "j15.realization.json"
K = 16
F_TWO_STAGE = f_ppf(0.95, K - 1, K - 1)
N_TRIAL = 1600
N_MIN = 4000
N_MAX = 200000  # a planned count above this is a planning error, never run (stop and look)
MP = 0.93827208943  # GeV (core constants, PDG)
ME = 0.000510998950
X0_SI = R.X0_SI_MM
DELTA_MS = 0.13  # density shift of the MS reference controls (B2 trial: at the detection limit)
TAILS_ON = {"alignment": {"on": True, "residual_sigma_y_um": 5, "residual_sigma_z_um": 10,
                          "residual_sigma_rot_urad": 20, "method": "SYNTHETIC: track-based alignment leaving 5 um"},
            "calibration-non-uniformity": {"on": True, "sigma": 0.0, "gradient_sigma": 0.01},
            # the strip resolution sqrt((p - w)^3 / 12 p) matches the declared point resolution (10.3 um bending,
            # 30.1 um non-bending with w = 8 um): the stage adds thresholds, inefficiency, noise and clustering,
            # never a finer measurement (simreco_spec.check)
            "noise-digitization": {"on": True, "pitch_y_um": 47, "pitch_z_um": 116, "sharing_um": 8, "threshold": 0.2,
                                   "efficiency": 0.99, "noise_hits_per_plane": 0.1},
            "pattern-recognition": {"on": True, "window_mm": 2.0, "chi2_per_ndof_cut": 30, "min_hits": 4}}
SEL = [{"column": "selected", "op": "==", "value": 1}]
PDG = "PDG Atomic and Nuclear Properties 2024 (https://pdg.lbl.gov/2024/AtomicNuclearProperties/), read 2026-10-24"
MATERIALS = [
    {"name": "G4_Si", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329, "radiation_length_mm": X0_SI,
     "reference_source": PDG + ", silicon_Si: density 2.329 g/cm3, A 28.0855(3), X0 9.370 cm",
     "reference_origin": "independent"},
    {"name": "G4_Pb", "z": 82, "a_g_mole": 207.2, "density_g_cm3": 11.35, "radiation_length_mm": R.X0_PB_MM,
     "reference_source": PDG + ", lead_Pb: density 11.35 g/cm3, X0 0.5612 cm", "reference_origin": "independent"},
    {"name": "G4_PLASTIC_SC_VINYLTOLUENE", "density_g_cm3": 1.032, "radiation_length_mm": R.X0_PVT_MM,
     "reference_source": PDG + ", polyvinyltoluene: density 1.032 g/cm3, X0 42.54 cm",
     "reference_origin": "independent"}]


class Campaign:
    # what a subclass may change for another design (J16 reuses this campaign for Example A): the realization
    # profile's file name in the artifacts_dir, the thickness of the multiple-scattering reference slab (the
    # design's silicon plane) and the study spec's materials
    prefix = "j15"
    profile_name = "j15.realization.json"
    slab_mm = 0.3
    materials = MATERIALS

    def __init__(self, work: Path, cfg: dict):
        self.work = work
        self.cfg = {k: str(Path(os.path.expanduser(v))) for k, v in cfg.items()}
        self.proj = work / "proj"
        self.art = self.proj / "artifacts"
        self.runs = self.art / "runs"
        self.sim_work = work / "sim"
        self.log = []

    # --- tools ---------------------------------------------------------------------------------------------------
    def go(self, cmd, *a, ok=(0,)):
        p = subprocess.run([*cmd, *map(str, a)], capture_output=True, text=True, timeout=36000)
        try:
            d = json.loads(p.stdout)
        except ValueError:
            d = {"raw": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
        if p.returncode not in ok:
            raise RuntimeError(f"{Path(str(cmd[-1])).name} {a[:2]} exit {p.returncode}: {json.dumps(d)[:3000]}")
        return p.returncode, d

    def write(self, rel: str, doc) -> Path:
        p = self.art / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
        return p

    def setup(self):
        if not (self.art / "design-spec.v1.json").is_file():
            R.write_design(self.proj)
        shutil.copy(PROFILE, self.art / self.profile_name)

    def study_id(self, sid: str) -> str:
        """The study_id of study sid, from which its runs are seeded S = H(study_id, role, point_id); a subclass may
        derive it otherwise (Geant4 program C2: a confirmation study's id from the search, core/simulation/seeds.py)."""
        return f"{self.prefix}-{sid}"

    def derived(self, sid: str) -> dict:
        out = self.art / "studies" / sid / "derived.element_sim.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        self.go(RUN, "from-geometry", "--geometry", self.art / "studies" / f"G-{sid}.geometry.json", "--profile",
                self.art / self.profile_name, "--out", out)
        return json.loads(out.read_text())

    def simulate(self, study_id, name, role, point, spec, events) -> Path:
        S = logical_run_seed(study_id, role, point)
        s = json.loads(json.dumps(spec))
        s["run"].update(events=int(events), logical_run_seed=S, seeds=list(job_seeds(S, 0)), first_event=0,
                        run_manager="mt", threads=8)
        sp = self.write(f"specs/{name}.spec.json", s)
        rec = self.runs / f"{name}.computational-run.json"
        if rec.is_file():  # a cached run: its event count was fixed when it ran (A1.9, never topped up)
            done = json.loads(rec.read_text())["extension"]["simulation"]["events"]
            if done != int(events):
                raise RuntimeError(f"{name}: the cached run has {done} events, the spec now asks {events}")
        if not rec.is_file():
            self.go(RUN, "run", "--spec", sp, "--exe", self.cfg["element_sim"], "--build-record",
                    self.cfg["build_record"], "--work", self.sim_work, "--run-id", name, "--record", rec,
                    "--evidence-role", role, "--point-id", point, "--logical-run-seed", S, "--created", R.CREATED)
        return rec

    def reco(self, run_rec: Path, reco_spec: dict, rid: str, geometry: Path | None = None) -> Path:
        sp = self.write(f"specs/{rid}.reco.json", reco_spec)
        rec = self.runs / f"{rid}.computational-run.json"
        if not rec.is_file():
            extra = ["--geometry", geometry] if geometry else []
            self.go(RUN, "reco", "--run-record", run_rec, "--reco-spec", sp, "--simreco", self.cfg["simreco"],
                    "--work-out", self.sim_work, "--reco-id", rid, "--record", rec, "--project-root", self.art,
                    "--created", R.CREATED, *extra)
        return rec

    def summary(self, rec: Path, m: int = 0) -> Path:
        aid = json.loads(rec.read_text())["artifact_id"].removeprefix("geant4-reco-")
        return self.sim_work / aid / f"summary_r{m:03d}.json"

    def dump(self, rec: Path, out: Path, ntuple="crossings") -> Path:
        if not out.is_file():
            out.parent.mkdir(parents=True, exist_ok=True)
            run_dir = self.sim_work / json.loads(rec.read_text())["artifact_id"].removeprefix("geant4-run-")
            simroot = Path(self.cfg["element_sim"]).with_name("simroot")
            with out.open("w") as fh:
                subprocess.run([str(simroot), "dump", str(run_dir / "events.root"), "--ntuple", ntuple], stdout=fh,
                               check=True, timeout=3600)
        return out

    def plan_events(self, summary: Path, decl: dict, target: float) -> int:
        """A1.9: N = N_trial (SE_trial / target)^2 F, rounded up to a multiple of K (at least N_MIN), with the
        study's declaration of the observable (its estimator: the summary does not carry it)."""
        from core.simulation import estimates as E
        doc = json.loads(summary.read_text())
        e = E.estimate(doc, decl)
        if e.get("status") != "ok" or not e.get("se") or not e.get("value"):
            raise RuntimeError(f"trial estimate of {decl['name']} unusable: {e}")
        n = math.ceil(doc["run"]["events_in_blocks"] * (e["se"] / abs(e["value"]) / target) ** 2 * F_TWO_STAGE)
        return _checked(max(N_MIN, -(-n // K) * K), decl["name"])

    # --- reco specs ------------------------------------------------------------------------------------------------
    @staticmethod
    def reco_spec(observables, events, tails=False, sigma_t=100.0, test_offset=None):
        tof = {"sigma_t_ps": sigma_t}
        if test_offset is not None:
            tof["test_layer_offset_ps"] = test_offset
        s = {"schema": "simreco.spec/1", "point_resolution_um": {"bending": 10.0, "non_bending": 30.0},
             "radiation_length_mm": {"G4_Si": X0_SI}, "tof": tof,
             "output": {"observables": observables, "blocks": {"blocks": K, "block_size": events // K}}}
        if tails:
            s["replicas"] = 20
            s["tail_sources"] = TAILS_ON
        return s

    @staticmethod
    def core_obs(width):
        return [{"name": "core", "source_column": "inv_rig_res", "estimator": "gaussian-core",
                 "bins": {"lo": -2.0, "hi": 2.0, "width": width}, "selection": SEL},
                {"name": "pull", "source_column": "rho_pull", "bins": {"lo": -10, "hi": 10, "width": 0.05},
                 "selection": SEL},
                {"name": "residual", "source_column": "inv_rig_res", "bins": {"lo": -2.0, "hi": 2.0, "width": width},
                 "selection": SEL},
                {"name": "beta", "source_column": "beta_res", "bins": {"lo": -0.5, "hi": 0.5, "width": 0.0005},
                 "selection": SEL},
                {"name": "tofdt", "source_column": "tof2_layer_resid_ps", "bins": {"lo": -2000, "hi": 2000,
                                                                                    "width": 5}, "selection": SEL}]

    @staticmethod
    def gun(spec, particle, ekin_mev):
        spec["source"].update(particle=particle, energy_MeV=ekin_mev)
        return spec

    # --- B3.2: the multiple-scattering reference (isolated 0.3 mm silicon slab), at each studied rigidity ----------
    def msref(self, rig_gv: float) -> dict:
        tag = f"msref-{rig_gv:g}gv"
        out = {}
        for name, fac in (("nominal", 1.0), ("density-plus", 1 + DELTA_MS), ("density-minus", 1 - DELTA_MS)):
            role = "nominal" if fac == 1 else "control"
            spec = {"schema": "element_sim.spec/1",
                    "world": {"material": "G4_Galactic", "half_mm": [200.0, 200.0, 200.0]},
                    "elements": [{"name": "Slab", "material": "G4_Si" if fac == 1 else "Si_ctl",
                                  "centre_mm": [0.0, 0.0, 0.0], "half_mm": [self.slab_mm / 2, 100.0, 100.0], "role": "passive"},
                                 {"name": "Plane", "material": "G4_Si", "centre_mm": [100.0, 0.0, 0.0],
                                  "half_mm": [0.0005, 150.0, 150.0], "role": "tracker-plane"}],
                    "physics": {"em_constructor": "G4EmStandardPhysics_option4", "default_cut_mm": 0.7},
                    "source": {"type": "gun", "particle": "proton", "energy_MeV": (math.hypot(rig_gv, MP) - MP) * 1000,
                               "position_mm": [-150.0, 0.0, 0.0], "direction": [1.0, 0.0, 0.0]},
                    "run": {"events": 8000, "seeds": [0, 0], "seeding": "per-event", "logical_run_seed": 0,
                            "run_manager": "mt", "threads": 8},
                    "output": {"event_file": {"level": "crossings"}}}
            if fac != 1:
                spec["materials"] = [{"name": "Si_ctl", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.33 * fac}]
            rec = self.simulate(f"{self.prefix}-{tag}", f"{tag}-{name}", role, name, spec, 8000)
            out[name] = (rec, self.dump(rec, self.work / "bench" / "msref" / f"{tag}-{name}.crossings.csv"))
        return out

    def ms_entry(self, cfg_dir: Path, rig_gv: float) -> dict:
        m = self.msref(rig_gv)
        rel = lambda p: os.path.relpath(p, cfg_dir)  # noqa: E731
        return {"benchmark": "multiple-scattering-reference", "element_spec": rel(self.art / "specs" /
                f"msref-{rig_gv:g}gv-nominal.spec.json"), "crossings": rel(m["nominal"][1]), "measuring_plane": "Plane",
                "material": "G4_Si", "particle": "proton", "momentum_MeV": rig_gv * 1000.0, "thickness_mm": self.slab_mm,
                "target_slabs": ["Slab", "Plane"], "run_record": rel(m["nominal"][0]),
                "tolerance": {"reference_accuracy_relative": 0.02, "k_sigma": 3.0,
                              "reference_source": "Lynch and Dahl, NIM B 58 (1991) 6, '2% or better' against Moliere "
                                                  "(abstract; PDG 1998 section 23.3, page read 2026-10-24)"},
                "negative_controls": [
                    {"crossings": rel(m[n][1]), "run_record": rel(m[n][0]), "injected": f"slab density x {f}",
                     "injected_relative": f - 1} for n, f in (("density-plus", 1 + DELTA_MS),
                                                             ("density-minus", 1 - DELTA_MS))]}

    # --- shared verification runs per candidate: geantino scan, charged geantinos, high-rigidity closure ----------
    def shared(self, cand: str) -> dict:
        sid = next(s for s, v in R.STUDIES.items() if v[0] == cand and v[1] == "momentum-resolution-core")
        base = self.derived(sid)
        c = cand.split("-")[1]
        geo = json.loads(json.dumps(base))
        geo["source"].update(particle="geantino", energy_MeV=1000.0)
        g = self.simulate(f"{self.prefix}-{c}-verification", f"{c}-geantino", "calibration", "geantino", geo, 2000)
        ch = json.loads(json.dumps(base))
        ch["source"].update(particle="chargedgeantino", energy_MeV=1000.0)
        q = self.simulate(f"{self.prefix}-{c}-verification", f"{c}-chargedgeantino", "calibration", "chargedgeantino", ch, 500)
        hi = json.loads(json.dumps(base))
        hi["source"].update(particle="chargedgeantino", energy_MeV=1.0e6)
        h = self.simulate(f"{self.prefix}-{c}-verification", f"{c}-closure", "calibration", "closure", hi, 8000)
        clo = self.reco(h, self.reco_spec(self.core_obs(0.002), 8000), f"{c}-closure-reco")
        return {"geantino": g, "charged": q, "closure": h, "closure_reco": clo,
                "charged_dump": self.dump(q, self.work / "bench" / c / "chargedgeantino.crossings.csv")}

    # --- B3.6: one tracking study (trial, nominal, cut scan, variations; reco tails off and on) ----------------
    def tracking(self, sid: str) -> dict:
        cand, fom, den, req = R.STUDIES[sid]
        rig = float(den["rigidity_GV"])
        study_id = self.study_id(sid)
        base = self.gun(self.derived(sid), "proton", (math.hypot(rig, MP) - MP) * 1000)
        width = 0.00025 if rig < 10 else 0.002
        obs = self.core_obs(width)
        trial = self.simulate(study_id, f"{sid}-trial", "trial", "trial", base, N_TRIAL)
        t_reco = self.reco(trial, self.reco_spec(obs, N_TRIAL), f"{sid}-trial-off")
        n = self.plan_events(self.summary(t_reco), obs[0], min(0.02, 0.1 / (4 * math.sqrt(2))))
        self.log.append({"study": sid, "trial_events": N_TRIAL, "planned_events": n})
        runs = {"nominal": self.simulate(study_id, f"{sid}-nominal", "nominal", "cut-0.7", base, n)}
        scan = json.loads(json.dumps(base))
        scan["physics"]["default_cut_mm"] = 0.35
        runs["scan"] = self.simulate(study_id, f"{sid}-scan", "scan", "cut-0.35", scan, n)
        # the multiple-scattering model variation (B3.4): single scattering where it is affordable (1 GV); at high
        # rigidity the hadronic shower in the Pb calorimeter makes single scattering of its electrons prohibitive,
        # so EM option 3 (Urban msc for protons: ConstructCharged(..., isWVI=false), G4EmStandardPhysics_option3.cc)
        # against option 4 (WentzelVI, isWVI default true) is the pair there
        msc = ("ss", ("reference list FTFP_BERT__SS: single Coulomb scattering for protons instead of WentzelVI "
                      "multiple scattering (G4EmBuilder.cc ConstructLightHadronsSS against ConstructLightHadrons, "
                      "Geant4 11.4.3)", {"reference_list": "FTFP_BERT__SS"})) if rig < 10 else (
            "emy", ("reference list FTFP_BERT_EMY: Urban multiple scattering for protons (option 3, isWVI false) "
                    "instead of WentzelVI (option 4), Geant4 11.4.3 G4EmBuilder::ConstructCharged",
                    {"reference_list": "FTFP_BERT_EMY"}))
        variations = {msc[0]: msc[1],
                      "qgsp-bic": ("reference list QGSP_BIC_EMZ: Binary cascade for nucleons below 1.5 GeV "
                                   "(G4R-BIC-RANGE)", {"reference_list": "QGSP_BIC_EMZ"})}
        if sid == "N6-TRK1":
            variations["air"] = ("world, field-region and calorimeter mothers in G4_AIR instead of vacuum", None)
        for v, (_, phys) in variations.items():
            s = json.loads(json.dumps(base))
            if phys:
                s["physics"].update(phys)
            else:
                s["world"]["material"] = "G4_AIR"
                for e in s["elements"]:
                    if e["material"] == "G4_Galactic":
                        e["material"] = "G4_AIR"
            runs[v] = self.simulate(study_id, f"{sid}-var-{v}", "variation", v, s, n)
        off = self.reco_spec(obs, n)
        on = self.reco_spec(obs, n, tails=True)
        geom = self.art / "studies" / f"G-{sid}.geometry.json"
        reco = {f"{k}-off": self.reco(r, off, f"{sid}-{k}-off", geom) for k, r in runs.items()}
        reco.update({f"{k}-on": self.reco(r, on, f"{sid}-{k}-on", geom) for k, r in runs.items() if k != "scan"})
        if sid == "N6-TRK1":  # B3.5: TOF time resolution 150 ps against the nominal 100 ps (same simulation)
            reco["nominal-off-150ps"] = self.reco(runs["nominal"], self.reco_spec(obs, n, sigma_t=150.0),
                                                  f"{sid}-nominal-off-150ps")
        return {"sid": sid, "runs": runs, "reco": reco, "events": n, "variations": variations, "obs": obs,
                "off": off, "on": on, "geom": geom}

    # --- the study record of one tracking study (B3.6), and the tails-off record of the tail-source demonstration --
    def study_spec(self, sid, kind, observable_name, particle, ek, rig, obs, conv, stat, plan, scope_extra,
                   variations, physics_note):
        sdir = self.art / "studies" / sid
        spec = {"schema": "geant4-study-spec/1", "study_id": self.study_id(sid),
                "label": "SYNTHETIC J15 F4 study (journey J15; names no experiment)",
                "geant4": {"version": "11.4.3", "documentation": [
                    {"name": "Geant4 upstream source, tag v11.4.3", "version": "11.4.3", "relied_on": True}]},
                "geometry_source": {"kind": "design", "description": f"derived by geant4_run.py from-geometry from "
                                    f"studies/G-{sid}.geometry.json and {self.profile_name}", "uses_replicas": False},
                "materials": self.materials,
                "reproducibility": {"data_paths_recorded": True, "build_record": self.cfg["build_record"]},
                "downstream_use": {"kind": "other", "note": f"F4 evaluation of {observable_name} (journey J15)"},
                "observable": {"name": observable_name, "kind": kind, "domain": "em",
                               "definition": physics_note, "unit": "1"},
                "particle": {"name": particle, "energy_MeV": ek},
                "physics": {"element_sim_spec": f"../../specs/{sid}-nominal.spec.json", "justification": [
                    {"choice": "FTFP_BERT_EMZ", "reason": "EM option 4 for multiple scattering and showers; FTFP_BERT "
                                                          "the default hadronic list",
                     "source": "geant4:source/physics_lists/lists (reference list factory)"},
                    {"choice": "production cut", "reason": "converged in this study's cut scan",
                     "source": "convergence gate of this study"}]},
                "convergence_plan": conv, "observables": obs, "blocks": {"K": K},
                "statistical_target": stat, "validation_plan": plan,
                "variation_plan": {"observable": conv["observables"][0], "model_assignment_checked": True,
                                   "variations": [{"name": v, "change": d} for v, d in variations.items()]}}
        spec["validation_plan"]["scope"] = {"particle": particle, "energy_MeV": [ek, ek], "observable": observable_name,
                                            **scope_extra}
        return self.write(f"studies/{sid}/study.json", spec), sdir

    def finish_tracking(self, t: dict, sh: dict) -> dict:
        sid = t["sid"]
        cand, fom, den, req = R.STUDIES[sid]
        rig = float(den["rigidity_GV"])
        ek = (math.hypot(rig, MP) - MP) * 1000
        c = cand.split("-")[1]
        geom = t["geom"]
        _, keys = self.go(BENCH, "scope-keys", "--element-spec", self.art / "specs" / f"{sid}-nominal.spec.json",
                          "--reco-spec", self.art / "specs" / f"{sid}-nominal-on.reco.json", "--geometry", geom,
                          "--realization", self.art / self.profile_name)
        variations = {v: d for v, (d, _) in t["variations"].items()}
        study, sdir = self.study_spec(
            sid, "tracking-resolution", "momentum-resolution-core", "proton", ek, rig, t["obs"],
            {"parameters": [{"name": "physics.default_cut_mm", "values": [0.35, 0.7]}], "observables": ["core"],
             "tolerance_relative": {"core": 0.1}},
            {"observable": "core", "relative_se": 0.02},
            {"benchmarks": [{"name": n, "grade": "verification" if n != "multiple-scattering-reference" else "reference"}
                            for n in ("material-definition", "field-propagation", "reco-closure",
                                      "multiple-scattering-reference")]},
            {"material": "G4_Si", "thickness_x0": [self.slab_mm / X0_SI] * 2, "rigidity_GV": [rig, rig], **keys["scope_keys"]},
            variations, "Gaussian core width of (1/R_reco - 1/R_true) R_true of selected tracks")
        S = lambda k: self.summary(t["reco"][k])  # noqa: E731
        self.go(CHECK, "run", "--spec", study, "--summary", f"nominal={S('nominal-off')}", "--summary",
                f"scan={S('scan-off')}", "--out", sdir / "convergence.json", ok=(0, 1, 3))
        self.go(CHECK, "variations", "--spec", study, "--nominal", S("nominal-off"),
                *[a for v in variations for a in ("--variation", f"{v}={S(v + '-off')}")],
                "--out", sdir / "variations.json", ok=(0, 1, 3))
        cfg_dir = self.work / "bench" / sid
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rel = lambda p: os.path.relpath(p, cfg_dir)  # noqa: E731
        g_run = self.sim_work / f"{c}-geantino"
        entries = [
            {"benchmark": "material-definition", "element_spec": rel(self.art / "specs" / f"{sid}-nominal.spec.json"),
             "geometry": rel(geom), "realization": rel(self.art / self.profile_name),
             "run_record": rel(sh["geantino"]), "csv": rel(g_run / "events.csv"),
             "column_map": rel(g_run / "column_map.json"), "tolerance_relative": 0.01},
            {"benchmark": "field-propagation", "element_spec": rel(self.art / "specs" / f"{c}-chargedgeantino.spec.json"),
             "reference_spec": rel(self.art / "specs" / f"{sid}-nominal.spec.json"), "crossings": rel(sh["charged_dump"])},
            {"benchmark": "reco-closure", "reco_record": rel(sh["closure_reco"]),
             "summary": rel(self.summary(sh["closure_reco"])), "pull_observable": "pull",
             "residual_observable": "residual", "rigidity_GV": 1000.0, "particle": "chargedgeantino"},
            self.ms_entry(cfg_dir, rig)]
        cfg = cfg_dir / "bench.config.json"
        cfg.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": rel(study), "benchmarks": entries},
                                  indent=1) + "\n")
        bench = sdir / "bench.results.json"
        self.go(BENCH, "run", "--config", cfg, "--out", bench, ok=(0, 1, 3))
        dens = ["--denominator", f"rigidity_GV={rig:g}", "--denominator", "species=proton"]
        self.go(RUN, "table", "--reco-record", t["reco"]["nominal-on"], "--figure-of-merit", fom, "--observable",
                "core", *dens, "--out", sdir / "table.dataset-record.json", "--id", sid, "--f4-results",
                sdir / "f4-results.json", "--geometry", geom, "--project-root", self.art, "--created", R.CREATED,
                *[a for v in variations for a in ("--variation", f"{v}={t['reco'][v + '-on']}")])
        ms = self.msref(rig)
        common = [str(r) for r in t["runs"].values()] + [str(r) for r in t["reco"].values()] + [
            str(sh[k]) for k in ("geantino", "charged", "closure", "closure_reco")] + [str(ms[k][0]) for k in ms]
        out = {"study": sdir / "study.computational-run.json"}
        self.label(study, bench, sdir, common, sdir / "f4-results.json", geom, out["study"])
        if sid == "N6-TRK1":  # the tail-source demonstration: the same simulation, every tail source off
            self.go(RUN, "table", "--reco-record", t["reco"]["nominal-off"], "--figure-of-merit", fom, "--observable",
                    "core", *dens, "--out", sdir / "table-notails.dataset-record.json", "--id", f"{sid}-notails",
                    "--f4-results", sdir / "f4-results-notails.json", "--geometry", geom, "--project-root", self.art,
                    "--created", R.CREATED,
                    *[a for v in variations for a in ("--variation", f"{v}={t['reco'][v + '-off']}")])
            out["notails"] = sdir / "study-notails.computational-run.json"
            self.label(study, bench, sdir, common, sdir / "f4-results-notails.json", geom, out["notails"])
        return out

    def label(self, study, bench, sdir, runs, results, geom, write):
        args = [a for r in dict.fromkeys(runs) for a in ("--run-record", r)]
        var = ["--variations", sdir / "variations.json"] if (sdir / "variations.json").is_file() else []
        _, doc = self.go(CHECK, "label", "--spec", study, "--benchmarks", bench, "--convergence",
                         sdir / "convergence.json", *var, *args, "--project-root", self.art, "--results", results,
                         "--geometry", geom, "--upgrade", "--write", write, "--created", R.CREATED, ok=(0, 1, 3))
        self.log.append({"label": str(write.relative_to(self.art)), "upgrade": doc.get("upgrade"),
                         "gaps": doc.get("gaps")})
        return doc


def _checked(n: int, what: str) -> int:
    if n > N_MAX:
        raise RuntimeError(f"planned {n} events for {what}: above N_MAX {N_MAX}, a planning error (not run)")
    return n


def _binomial_events(summary: Path, observable: str, target: float) -> int:
    """A1.9 for a proportion: N = N_trial (SE_trial / target)^2 F with SE_trial / p = sqrt((1 - p) / k), k >= 1."""
    doc = json.loads(summary.read_text())
    o = next(x for x in doc["observables"] if x["name"] == observable)
    n = sum(b["n"] for b in o["blocks"])
    k = max(1.0, sum(b.get("count_if", [0])[0] if isinstance(b.get("count_if"), list) else b.get("count_if", 0)
                     for b in o["blocks"]))
    rel = math.sqrt(max(1 - k / n, 0.0) / k)
    return _checked(max(N_MIN, -(-math.ceil(doc["run"]["events_in_blocks"] * (rel / target) ** 2 * F_TWO_STAGE) // K)
                        * K), observable)


def _abs_events(summary: Path, decl: dict, target_abs: float) -> int:
    """A1.9 with an absolute se target (the rear-leakage fraction, B3.3), with the study's declaration."""
    from core.simulation import estimates as E
    doc = json.loads(summary.read_text())
    se = E.estimate(doc, decl)["se"]
    return _checked(max(N_MIN, -(-math.ceil(doc["run"]["events_in_blocks"] * (se / target_abs) ** 2 * F_TWO_STAGE)
                                // K) * K), decl["name"])


class Campaign2(Campaign):
    # --- B3.6: charge confusion at 500 GV (not upgradable before D0-b) ------------------------------------------
    def cc(self, shared: dict, recorded: Path) -> None:
        sid = "N6-CC500"
        cand, fom, den, req = R.STUDIES[sid]
        rig = 500.0
        ek = (math.hypot(rig, MP) - MP) * 1000
        study_id = self.study_id(sid)
        base = self.gun(self.derived(sid), "proton", ek)
        obs = self.core_obs(0.005) + [{"name": "flip", "source_column": "charge_flip", "estimator": "proportion",
                                       "thresholds": [0.5], "bins": {"lo": 0, "hi": 2, "width": 1}, "selection": SEL}]
        trial = self.simulate(study_id, f"{sid}-trial", "trial", "trial", base, N_TRIAL)
        t_reco = self.reco(trial, self.reco_spec(obs, N_TRIAL), f"{sid}-trial-off")
        n = _binomial_events(self.summary(t_reco), "flip", 0.2)
        self.log.append({"study": sid, "trial_events": N_TRIAL, "planned_events": n})
        runs = {"nominal": self.simulate(study_id, f"{sid}-nominal", "nominal", "cut-0.7", base, n)}
        scan = json.loads(json.dumps(base))
        scan["physics"]["default_cut_mm"] = 0.35
        runs["scan"] = self.simulate(study_id, f"{sid}-scan", "scan", "cut-0.35", scan, n)
        var = json.loads(json.dumps(base))
        var["physics"]["reference_list"] = "FTFP_BERT_EMY"  # Urban msc for protons (see tracking)
        runs["emy"] = self.simulate(study_id, f"{sid}-var-emy", "variation", "emy", var, n)
        geom = self.art / "studies" / f"G-{sid}.geometry.json"
        off, on = self.reco_spec(obs, n), self.reco_spec(obs, n, tails=True)
        reco = {"nominal-off": self.reco(runs["nominal"], off, f"{sid}-nominal-off", geom),
                "scan-off": self.reco(runs["scan"], off, f"{sid}-scan-off", geom),
                "emy-off": self.reco(runs["emy"], off, f"{sid}-emy-off", geom),
                "nominal-on": self.reco(runs["nominal"], on, f"{sid}-nominal-on", geom),
                "emy-on": self.reco(runs["emy"], on, f"{sid}-emy-on", geom)}
        c = cand.split("-")[1]
        sh = shared[cand]
        _, keys = self.go(BENCH, "scope-keys", "--element-spec", self.art / "specs" / f"{sid}-nominal.spec.json",
                          "--reco-spec", self.art / "specs" / f"{sid}-nominal-on.reco.json", "--geometry", geom,
                          "--realization", self.art / self.profile_name)
        variations = {"emy": "reference list FTFP_BERT_EMY: Urban multiple scattering for protons (option 3) "
                            "instead of WentzelVI (option 4)"}
        study, sdir = self.study_spec(
            sid, "charge-confusion", "charge-confusion-rate", "proton", ek, rig, obs,
            {"parameters": [{"name": "physics.default_cut_mm", "values": [0.35, 0.7]}], "observables": ["core"],
             "tolerance_relative": {"core": 0.1}},
            {"observable": "flip", "relative_se": 0.2},
            {"benchmarks": [{"name": n, "grade": g} for n, g in (
                ("material-definition", "verification"), ("field-propagation", "verification"),
                ("reco-closure", "verification"), ("ms-tail-reference", "reference"))]},
            {"material": "G4_Si", "thickness_x0": [self.slab_mm / X0_SI] * 2, "rigidity_GV": [rig, rig], **keys["scope_keys"]},
            variations, "fraction of selected tracks whose reconstructed charge sign is opposite to the truth")
        S = lambda k: self.summary(reco[k])  # noqa: E731
        self.go(CHECK, "run", "--spec", study, "--summary", f"nominal={S('nominal-off')}", "--summary",
                f"scan={S('scan-off')}", "--out", sdir / "convergence.json", ok=(0, 1, 3))
        self.go(CHECK, "variations", "--spec", study, "--nominal", S("nominal-off"), "--variation",
                f"emy={S('emy-off')}", "--out", sdir / "variations.json", ok=(0, 1, 3))
        cfg_dir = self.work / "bench" / sid
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rel = lambda p: os.path.relpath(p, cfg_dir)  # noqa: E731
        g_run = self.sim_work / f"{c}-geantino"
        entries = [
            {"benchmark": "material-definition", "element_spec": rel(self.art / "specs" / f"{sid}-nominal.spec.json"),
             "geometry": rel(geom), "realization": rel(self.art / self.profile_name),
             "run_record": rel(sh["geantino"]), "csv": rel(g_run / "events.csv"),
             "column_map": rel(g_run / "column_map.json"), "tolerance_relative": 0.01},
            {"benchmark": "field-propagation", "element_spec": rel(self.art / "specs" / f"{c}-chargedgeantino.spec.json"),
             "reference_spec": rel(self.art / "specs" / f"{sid}-nominal.spec.json"), "crossings": rel(sh["charged_dump"])},
            {"benchmark": "reco-closure", "reco_record": rel(sh["closure_reco"]),
             "summary": rel(self.summary(sh["closure_reco"])), "pull_observable": "pull",
             "residual_observable": "residual", "rigidity_GV": 1000.0, "particle": "chargedgeantino"},
            {"benchmark": "ms-tail-reference"}]
        cfg = cfg_dir / "bench.config.json"
        cfg.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": rel(study), "benchmarks": entries},
                                  indent=1) + "\n")
        bench = sdir / "bench.results.json"
        self.go(BENCH, "run", "--config", cfg, "--out", bench, ok=(0, 1, 3))
        self.go(RUN, "table", "--reco-record", reco["nominal-on"], "--figure-of-merit", fom, "--observable", "flip",
                *[a for k, v in den.items() for a in ("--denominator", f"{k}={v}")], "--out",
                sdir / "table.dataset-record.json", "--id", sid, "--f4-results", sdir / "f4-results.json",
                "--geometry", geom, "--project-root", self.art, "--created", R.CREATED,
                "--variation", f"emy={reco['emy-on']}")
        common = [str(r) for r in runs.values()] + [str(r) for r in reco.values()] + [
            str(sh[k]) for k in ("geantino", "charged", "closure", "closure_reco")]
        self.label(study, bench, sdir, common, sdir / "f4-results.json", geom, sdir / "study.computational-run.json")

    # --- B3.6 and B3.3: shower containment of 10 GeV electrons, with the calorimeter production-cut scan --------
    def shower(self, shared: dict, recorded: Path) -> None:
        sid = "N6-CAL10"
        cand, fom, den, req = R.STUDIES[sid]
        ek = 10000.0
        study_id = self.study_id(sid)
        base = self.gun(self.derived(sid), "e-", ek)
        obs = [{"name": "containment", "source_column": "containment", "bins": {"lo": 0, "hi": 1.0001, "width": 0.0001}},
               {"name": "rear_leak", "source_column": "rear_leak_fraction", "bins": {"lo": 0, "hi": 1, "width": 0.0001},
                "tolerance_mode": "absolute", "tolerance": 0.002}]
        trial = self.simulate(study_id, f"{sid}-trial", "trial", "trial", base, N_TRIAL)
        t_reco = self.reco(trial, self.reco_spec(obs, N_TRIAL), f"{sid}-trial-reco")
        n = max(self.plan_events(self.summary(t_reco), obs[0], 0.01 / (4 * math.sqrt(2))),
                _abs_events(self.summary(t_reco), obs[1], 0.002 / (4 * math.sqrt(2))))
        nrec = self.runs / f"{sid}-nominal.computational-run.json"
        if nrec.is_file():  # the count fixed when the evidence runs were made stays (a re-reconstruction only)
            n = json.loads(nrec.read_text())["extension"]["simulation"]["events"]
        self.log.append({"study": sid, "trial_events": N_TRIAL, "planned_events": n})
        runs, reco = {}, {}
        geom = self.art / "studies" / f"G-{sid}.geometry.json"
        spec_r = self.reco_spec(obs, n)
        for cut in (0.1, 0.3, 0.7, 1.0):
            s = json.loads(json.dumps(base))
            s["physics"]["default_cut_mm"] = cut
            name = "nominal" if cut == 0.7 else f"cut-{cut:g}"
            runs[name] = self.simulate(study_id, f"{sid}-{name}", "nominal" if cut == 0.7 else "scan", f"cut-{cut:g}",
                                       s, n)
            reco[name] = self.reco(runs[name], spec_r, f"{sid}-{name}-reco", geom)
        var = json.loads(json.dumps(base))
        var["physics"]["reference_list"] = "FTFP_BERT_EMY"
        runs["emy"] = self.simulate(study_id, f"{sid}-var-emy", "variation", "emy", var, n)
        reco["emy"] = self.reco(runs["emy"], spec_r, f"{sid}-emy-reco", geom)
        variations = {"emy": "reference list FTFP_BERT_EMY: EM option 3 against option 4 (G4R-PRECISION-EM)"}
        study, sdir = self.study_spec(
            sid, "containment", "shower-containment", "e-", ek, None, obs,
            {"parameters": [{"name": "physics.default_cut_mm", "values": [0.1, 0.3, 0.7, 1.0]}],
             "observables": ["containment", "rear_leak"], "tolerance_relative": {"containment": 0.01}},
            {"observable": "containment", "relative_se": 0.01 / (4 * math.sqrt(2))},
            {"benchmarks": [{"name": "shower-containment", "grade": "sanity"}]},
            {"material": "G4_Pb"}, variations,
            "1 - (rear + front + lateral leakage of the calorimeter mother) / incident kinetic energy")
        S = lambda k: self.summary(reco[k])  # noqa: E731
        self.go(CHECK, "run", "--spec", study, *[a for k in reco if k != "emy" for a in (
            "--summary", f"{'nominal' if k == 'nominal' else 'scan'}={S(k)}")], "--out", sdir / "convergence.json",
            ok=(0, 1, 3))
        self.go(CHECK, "variations", "--spec", study, "--nominal", S("nominal"), "--variation", f"emy={S('emy')}",
                "--out", sdir / "variations.json", ok=(0, 1, 3))
        cfg_dir = self.work / "bench" / sid
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rel = lambda p: os.path.relpath(p, cfg_dir)  # noqa: E731
        n_run = self.sim_work / f"{sid}-nominal"
        entries = [{"benchmark": "shower-containment", "csv": rel(n_run / "events.csv"),
                    "column_map": rel(n_run / "column_map.json"), "particle": "e-", "energy_MeV": ek,
                    "depth_x0": 50 * (2.0 / R.X0_PB_MM + 5.0 / R.X0_PVT_MM), "critical_energy_MeV": 10.2,
                    "run_record": rel(runs["nominal"]), "target_slabs": ["Calo"]}]
        cfg = cfg_dir / "bench.config.json"
        cfg.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": rel(study), "benchmarks": entries},
                                  indent=1) + "\n")
        bench = sdir / "bench.results.json"
        self.go(BENCH, "run", "--config", cfg, "--out", bench, ok=(0, 1, 3))
        self.go(RUN, "table", "--reco-record", reco["nominal"], "--figure-of-merit", fom, "--observable",
                "containment", *[a for k, v in den.items() for a in ("--denominator", f"{k}={v}")], "--out",
                sdir / "table.dataset-record.json", "--id", sid, "--f4-results", sdir / "f4-results.json",
                "--geometry", geom, "--project-root", self.art, "--created", R.CREATED,
                "--variation", f"emy={reco['emy']}")
        common = [str(r) for r in runs.values()] + [str(r) for r in reco.values()]
        self.label(study, bench, sdir, common, sdir / "f4-results.json", geom, sdir / "study.computational-run.json")


MMU = 0.1056583755  # GeV, muon mass (PDG)
SF_REFERENCE = {"value": 0.270, "source": (
    "ionization dE/dx of 1 GeV (kinetic) muons, PDG 2024 muon tables muE_lead_Pb.txt (1.270 MeV cm2/g) and "
    "muE_polyvinyltoluene.txt (2.066 MeV cm2/g), read 2026-10-24: 0.5 cm x 1.032 x 2.066 / (that + 0.2 cm x 11.35 "
    "x 1.270) = 0.270")}


class Campaign3(Campaign2):
    def verify(self, check: str, run_rec: Path, name: str, *extra, ok=(0, 1)) -> tuple[int, dict, Path]:
        out = self.art / "checks" / f"{name}.computational-run.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        code, doc = self.go([sys.executable, "-B", str(PLUGIN / "adapters/geant4/assets/geant4_verify.py")], check,
                            "--run-record", run_rec, "--record", out, "--created", R.CREATED, *extra, ok=ok)
        return code, doc, out

    # --- B3.2: the verification ladder of J15 (cand-N6), a separate record that is always unvalidated -----------
    def ladder(self, shared: dict, recorded: Path) -> None:
        sid = "N6-TRK1"
        base = self.derived(sid)
        sh = shared["cand-N6"]
        lid = "j15-ladder"
        ldir = self.art / "studies" / "ladder"
        cfg_dir = self.work / "bench" / "ladder"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rel = lambda p: os.path.relpath(p, cfg_dir)  # noqa: E731
        items, runs, checks = [], [], []
        # implementation checks: overlaps (control: a shifted plane, refused by check-spec before any run), energy
        # balance (controls: double-counted leakage, the omitted 2 m_e of a killed e+), material budget
        nominal = self.runs / f"{sid}-nominal.computational-run.json"
        ov = json.loads(json.dumps(base))  # a dedicated run with sampled /geometry/test/run points (B1 as well)
        ov["output"] = dict(ov.get("output") or {}, overlap_test_points=10000)
        ov_run = self.simulate(lid, "ladder-overlap-test", "calibration", "overlap-test", ov, 20)
        runs.append(ov_run)
        code, doc, rec = self.verify("overlaps", ov_run, "ladder-overlaps")
        bad = json.loads(json.dumps(base))
        si2 = next(e for e in bad["elements"] if e["name"] == "Si2")
        si2["centre_mm"][0] = next(e for e in bad["elements"] if e["name"] == "Si1")["centre_mm"][0] + 0.1
        bp = self.write("specs/ladder-overlap-control.spec.json", bad)
        ccode, cdoc = self.go(RUN, "check-spec", "--spec", bp, ok=(0, 1, 2))
        items.append({"check": "overlap", "class": "implementation", "verdict": doc.get("status"),
                      "control": {"injected": "Si2 moved onto Si1", "caught": ccode != 0,
                                  "by": "geant4_run.py check-spec (refused before a run)"}})
        checks.append(rec)
        for particle in ("e-", "e+"):
            # the energy balance closes only for EM-only physics (a hadronic list moves photonuclear energy into
            # binding and neutrinos, and geant4_verify gives no verdict then): option 4 alone, as in B1
            s = self.gun(json.loads(json.dumps(base)), particle, 1000.0)
            s["physics"] = {"em_constructor": "G4EmStandardPhysics_option4",
                            "default_cut_mm": base["physics"].get("default_cut_mm", 0.7)}
            r = self.simulate(lid, f"ladder-balance-{particle}", "calibration", f"balance-{particle}", s, 400)
            runs.append(r)
            code, doc, rec = self.verify("balance", r, f"ladder-balance-{particle}", "--tolerance-mev", "0.001")
            inj = "double-count-leakage" if particle == "e-" else "omit-positron-mass"
            icode, idoc, irec = self.verify("balance", r, f"ladder-balance-{particle}-control", "--tolerance-mev",
                                            "0.001", "--inject", inj, ok=(0, 1))
            items.append({"check": f"energy balance ({particle} 1 GeV)", "class": "implementation",
                          "verdict": doc.get("status"), "worst_residual_MeV": doc.get("worst_abs_residual_MeV"),
                          "control": {"injected": inj, "caught": icode != 0}})
            checks.append(rec)  # the control record is failed by design: its outcome is in the ladder, not an input
        code, doc, rec = self.verify("budget", sh["geantino"], "ladder-budget")
        items.append({"check": "material budget (geantino path lengths)", "class": "implementation",
                      "verdict": doc.get("status"), "x_over_x0_total": doc.get("total_x_over_x0")})
        checks.append(rec)
        pb = json.loads(json.dumps(base))
        pb.setdefault("materials", []).append({"name": "Pb_ctl", "z": 82, "a_g_mole": 207.2,
                                               "density_g_cm3": 11.35 * 1.05})
        for e in pb["elements"]:
            if e["material"] == "G4_Pb":
                e["material"] = "Pb_ctl"
        pb["source"].update(particle="geantino", energy_MeV=1000.0)
        pb_run = self.simulate(lid, "ladder-geantino-pb-control", "control", "pb-density", pb, 500)
        runs.append(pb_run)
        # verification and sanity benchmarks with their controls
        def charged(fac, name):
            s = json.loads(json.dumps(base))
            s["source"].update(particle="chargedgeantino", energy_MeV=1000.0)
            for reg in s["field"]["regions"]:
                reg["b_tesla"] = [b * fac for b in reg["b_tesla"]]
            r = self.simulate(lid, f"ladder-{name}", "control", name, s, 500)
            runs.append(r)
            return r, self.dump(r, cfg_dir / f"{name}.crossings.csv")
        f_plus, f_minus = charged(1 + 1e-4, "field-plus"), charged(1 - 1e-4, "field-minus")
        nominal_spec = rel(self.art / "specs" / f"{sid}-nominal.spec.json")
        entries = [{"benchmark": "field-propagation", "element_spec": rel(self.art / "specs" / "N6-chargedgeantino.spec.json"),
                    "reference_spec": nominal_spec, "crossings": rel(sh["charged_dump"])}]
        controls = {"field-propagation": [
            {"benchmark": "field-propagation", "element_spec": rel(self.art / "specs" / f"ladder-{n}.spec.json"),
             "reference_spec": nominal_spec, "crossings": rel(d), "injected": f"Geant4-side B x {f}"}
            for n, (r, d), f in (("field-plus", f_plus, 1 + 1e-4), ("field-minus", f_minus, 1 - 1e-4))]}
        g_run = self.sim_work / "N6-geantino"
        geom = self.art / "studies" / f"G-{sid}.geometry.json"
        md = {"benchmark": "material-definition", "element_spec": nominal_spec, "geometry": rel(geom),
              "realization": rel(self.art / self.profile_name), "run_record": rel(sh["geantino"]),
              "csv": rel(g_run / "events.csv"), "column_map": rel(g_run / "column_map.json"), "tolerance_relative": 0.02}
        entries.append(md)
        pb_dir = self.sim_work / "ladder-geantino-pb-control"
        controls["material-definition"] = [dict(md, element_spec=rel(self.art / "specs" / "ladder-geantino-pb-control.spec.json"),
                                                run_record=rel(pb_run), csv=rel(pb_dir / "events.csv"),
                                                column_map=rel(pb_dir / "column_map.json"),
                                                injected="Pb density x 1.05 in the spec, 11.35 g/cm3 in the study")]
        # field-propagation-muon (sanity): mu- at 1, 10 and 100 GV; control: Geant4-side B x 1.01 at 10 GV
        mobs = self.core_obs(0.0005)
        for rig in (1.0, 10.0, 100.0):
            s = self.gun(json.loads(json.dumps(base)), "mu-", (math.hypot(rig, MMU) - MMU) * 1000)
            tr = self.simulate(lid, f"ladder-mu{rig:g}-trial", "trial", f"mu{rig:g}", s, N_TRIAL)
            trr = self.reco(tr, self.reco_spec(mobs, N_TRIAL), f"ladder-mu{rig:g}-trial-reco")
            n = _abs_events(self.summary(trr), mobs[2], 0.003 / 4)
            self.log.append({"study": f"ladder mu {rig:g} GV", "trial_events": N_TRIAL, "planned_events": n})
            r = self.simulate(lid, f"ladder-mu{rig:g}", "calibration", f"mu{rig:g}", s, n)
            rr = self.reco(r, self.reco_spec(mobs, n), f"ladder-mu{rig:g}-reco")
            runs += [tr, trr, r, rr]
            entries.append({"benchmark": "field-propagation-muon", "summary": rel(self.summary(rr)),
                            "observable": "residual", "tolerance_absolute": 0.003})
            if rig == 10.0:
                c = json.loads(json.dumps(s))
                for reg in c["field"]["regions"]:
                    reg["b_tesla"] = [b * 1.01 for b in reg["b_tesla"]]
                cr = self.simulate(lid, "ladder-mu10-field-control", "control", "mu10-field", c, n)
                # simreco reconstructs with the run's own field: the design's (nominal) field is restored by the
                # global scale 1/1.01, so the Geant4-side error shows as a curvature bias
                crr = self.reco(cr, dict(self.reco_spec(mobs, n), field_scale_global=1 / 1.01),
                                "ladder-mu10-field-control-reco")
                runs += [cr, crr]
                controls["field-propagation-muon"] = [{"benchmark": "field-propagation-muon",
                                                       "summary": rel(self.summary(crr)), "observable": "residual",
                                                       "tolerance_absolute": 0.003,
                                                       "injected": "Geant4-side B x 1.01 at 10 GV"}]
        # reco-closure (control: reconstruction B x 1.05), tof-beta and tof-layer-consistency (control: a 100 ps
        # offset on one TOF layer, the test-only reco field)
        clo_spec = json.loads((self.art / "specs" / "N6-closure-reco.reco.json").read_text())
        clo_ctl = dict(clo_spec, field_scale_global=1.05)
        clo_ctl_rec = self.reco(sh["closure"], clo_ctl, "ladder-closure-control-reco")
        runs += [clo_ctl_rec]
        closure = {"benchmark": "reco-closure", "reco_record": rel(sh["closure_reco"]),
                   "summary": rel(self.summary(sh["closure_reco"])), "pull_observable": "pull",
                   "residual_observable": "residual", "rigidity_GV": 1000.0, "particle": "chargedgeantino"}
        entries.append(closure)
        controls["reco-closure"] = [dict(closure, reco_record=rel(clo_ctl_rec), summary=rel(self.summary(clo_ctl_rec)),
                                         injected="reconstruction B x 1.05 (field_scale_global)")]
        n_off = self.runs / f"{sid}-nominal-off.computational-run.json"
        nspec = json.loads((self.art / "specs" / f"{sid}-nominal-off.reco.json").read_text())
        nspec["tof"]["test_layer_offset_ps"] = 100.0
        tof_ctl = self.reco(nominal, nspec, f"{sid}-nominal-off-tofoffset")
        runs += [tof_ctl]
        tb = {"benchmark": "tof-beta", "summary": rel(self.summary(n_off)), "observable": "beta",
              "tolerance_absolute": 0.002}
        tl = {"benchmark": "tof-layer-consistency", "summary": rel(self.summary(n_off)), "observable": "tofdt",
              "tolerance_absolute": 10.0, "sigma_t_ps": 100.0, "width_tolerance_relative": 0.1}
        entries += [tb, tl]
        controls["tof-beta"] = [dict(tb, summary=rel(self.summary(tof_ctl)), injected="+100 ps on one TOF2 layer")]
        controls["tof-layer-consistency"] = [dict(tl, summary=rel(self.summary(tof_ctl)),
                                                  injected="+100 ps on one TOF2 layer")]
        # sampling-fraction (sanity): mu- 1 GeV; control: PVT density x 1.2
        sf_obs = [{"name": "active", "source_column": "edep_CaloSc_MeV", "bins": {"lo": 0, "hi": 1000, "width": 1000}},
                  {"name": "passive", "source_column": "edep_CaloPb_MeV", "bins": {"lo": 0, "hi": 1000, "width": 1000}}]
        for name, fac in (("sf", 1.0), ("sf-pvt-control", 1.2)):
            s = self.gun(json.loads(json.dumps(base)), "mu-", 1000.0)
            s["output"] = dict(s.get("output") or {}, observables=sf_obs, blocks={"blocks": K, "block_size": 250})
            if fac != 1:
                s.setdefault("materials", []).append({  # PDG polyvinyltoluene: H 0.085, C 0.915 by mass
                    "name": "PVT_ctl", "density_g_cm3": 1.032 * fac,
                    "components": [{"material": "G4_H", "mass_fraction": 0.085},
                                   {"material": "G4_C", "mass_fraction": 0.915}]})
                for e in s["elements"]:
                    if e["role"] == "calorimeter-active":
                        e["material"] = "PVT_ctl"
            r = self.simulate(lid, f"ladder-{name}", "calibration" if fac == 1 else "control", name, s, 4000)
            runs.append(r)
            e = {"benchmark": "sampling-fraction", "summary": rel(self.sim_work / f"ladder-{name}" / "summary.json"),
                 "active_observable": "active", "passive_observable": "passive",
                 "reference_value": SF_REFERENCE["value"], "reference_source": SF_REFERENCE["source"],
                 "window_relative": 0.10}
            if fac == 1:
                entries.append(e)
            else:
                controls["sampling-fraction"] = [dict(e, injected="PVT density x 1.2")]
        # the ladder record (never upgraded) and the multiple-scattering reference record, listed separately
        def bench_run(name, ents):
            cfg = cfg_dir / f"{name}.config.json"
            cfg.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": rel(ldir / "study.json"),
                                       "benchmarks": ents}, indent=1) + "\n")
            out = cfg_dir / f"{name}.results.json"
            self.go(BENCH, "run", "--config", cfg, "--out", out, ok=(0, 1, 3))
            return json.loads(out.read_text())
        study = {"schema": "geant4-study-spec/1", "study_id": lid,
                 "label": "SYNTHETIC J15 verification ladder (journey J15): verification only, always unvalidated",
                 "geant4": {"version": "11.4.3", "documentation": [
                     {"name": "Geant4 upstream source, tag v11.4.3", "version": "11.4.3", "relied_on": True}]},
                 "geometry_source": {"kind": "design", "description": "cand-N6 through from-geometry",
                                     "uses_replicas": False},
                 "materials": MATERIALS + [{"name": "Pb_ctl", "z": 82, "a_g_mole": 207.2, "density_g_cm3": 11.35,
                                            "reference_source": "the control's claimed (independent) density",
                                            "reference_origin": "independent"}],
                 "reproducibility": {"data_paths_recorded": True, "build_record": self.cfg["build_record"]},
                 "downstream_use": {"kind": "other", "note": "verification carrier of J15 (B3.2); never F4"},
                 "observable": {"name": "verification ladder", "kind": "other", "definition": "the checks of B3.2",
                                "unit": "1"},
                 "particle": {"name": "proton", "energy_MeV": 433.0},
                 "physics": {"element_sim_spec": f"../../specs/{sid}-nominal.spec.json", "justification": [
                     {"choice": "as the F4 studies", "reason": "the ladder verifies their setup", "source": "B3.2"}]},
                 "convergence_plan": {"parameters": [], "observables": []},
                 "statistical_target": {"observable": "none", "relative_se": 1.0},
                 "validation_plan": {"benchmarks": [{"name": n, "grade": R_GRADE[n]} for n in sorted(
                     {e["benchmark"] for e in entries})],
                     "scope": {"particle": "proton", "energy_MeV": [433.0, 433.0], "material": "G4_Si",
                               "observable": "verification ladder"}},
                 "variation_plan": {"observable": "none", "model_assignment_checked": False, "variations": []}}
        sp = self.write("studies/ladder/study.json", study)
        nom = bench_run("ladder", entries)
        ctl = bench_run("ladder-controls", [{k: v for k, v in c.items() if k != "injected"}
                                            for cs in controls.values() for c in cs])
        injected = [c["injected"] for cs in controls.values() for c in cs]
        for b, inj in zip(ctl["benchmarks"], injected):
            b["injected"] = inj
            b["caught"] = b["verdict"] in ("fail", "implausible")
        doc = {"benchmarks": nom["benchmarks"], "gaps": nom["gaps"], "controls": ctl["benchmarks"],
               "implementation_checks": items,
               "note": "verification ladder (B3.2): verification and sanity benchmarks with their negative controls; "
                       "the record is never upgraded"}
        bench = self.write("studies/ladder/bench.results.json", doc)
        conv = self.write("studies/ladder/convergence.json", {"convergence": {"gate": "not-run", "parameters": []}})
        args = [a for r in dict.fromkeys(map(str, runs + [sh["geantino"], sh["charged"], sh["closure"],
                                                           sh["closure_reco"]])) for a in ("--run-record", r)]
        refs = [a for r in map(str, checks) for a in ("--reference-record", r)]
        self.go(CHECK, "label", "--spec", sp, "--benchmarks", bench, "--convergence", conv, *args, *refs,
                "--project-root", self.art, "--write", ldir / "ladder.computational-run.json", "--created", R.CREATED,
                ok=(0, 1, 3))
        self.log.append({"ladder": {"items": items, "controls": [(b["benchmark"], b.get("injected"), b["caught"])
                                                                 for b in ctl["benchmarks"]]}})
        # the multiple-scattering reference record: the reference at 1, 100 and 500 GV, listed separately
        mdir = self.art / "studies" / "msref"
        mcfg = self.work / "bench" / "msref-record"
        mcfg.mkdir(parents=True, exist_ok=True)
        ms_entries = [self.ms_entry(mcfg, r) for r in (1.0, 100.0, 500.0)]
        mstudy = dict(study, study_id="j15-msref", label="SYNTHETIC J15 multiple-scattering reference (isolated 0.3 "
                      "mm silicon slab), listed separately (B3.2)",
                      observable={"name": "multiple-scattering core width", "kind": "angle",
                                  "definition": "Gaussian fit to the central 98 % of the projected exit angle",
                                  "unit": "rad"},
                      physics={"element_sim_spec": "../../specs/msref-1gv-nominal.spec.json", "justification": [
                          {"choice": "G4EmStandardPhysics_option4", "reason": "as the F4 studies' EM physics",
                           "source": "B2.7"}]},
                      validation_plan={"benchmarks": [{"name": "multiple-scattering-reference", "grade": "reference"}],
                                       "scope": {"particle": "proton", "energy_MeV": [433.0, 433.0],
                                                 "material": "G4_Si", "observable": "multiple-scattering core width"}})
        msp = self.write("studies/msref/study.json", mstudy)
        mcf = mcfg / "msref.config.json"
        mcf.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": os.path.relpath(msp, mcfg),
                                   "benchmarks": ms_entries}, indent=1) + "\n")
        mres = mdir / "bench.results.json"
        self.go(BENCH, "run", "--config", mcf, "--out", mres, ok=(0, 1, 3))
        mruns = [a for r in (1.0, 100.0, 500.0) for k, v in self.msref(r).items() for a in ("--run-record", str(v[0]))]
        self.go(CHECK, "label", "--spec", msp, "--benchmarks", mres, "--convergence", conv, *mruns,
                "--project-root", self.art, "--write", mdir / "msref.computational-run.json", "--created", R.CREATED,
                ok=(0, 1, 3))

    # --- export: recorded/ for the offline replay (run records gzip-compressed) -----------------------------------
    def export(self, shared: dict, recorded: Path) -> None:
        if recorded.exists():
            shutil.rmtree(recorded)
        (recorded / "runs").mkdir(parents=True)
        for p in sorted(self.runs.glob("*.json")):
            with open(recorded / "runs" / (p.name + ".gz"), "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0, filename="") as fh:  # noqa: E501
                fh.write(p.read_bytes())
        for sub in ("specs", "studies", "checks"):
            src = self.art / sub
            if src.is_dir():
                shutil.copytree(src, recorded / "artifacts" / sub,
                                ignore=shutil.ignore_patterns("G-*.geometry.json", "derived.element_sim.json"))
        (recorded / "campaign-log.json").write_text(json.dumps(self.log, indent=1, default=str) + "\n")
        scrub_home(recorded)
        total = sum(p.stat().st_size for p in recorded.rglob("*") if p.is_file())
        print(json.dumps({"recorded": str(recorded), "bytes": total}))



def scrub_home(recorded: Path) -> None:
    """Write ~ for the home directory in every recorded file (gz members too) and rewrite every sha256 that cites a
    file so changed, to a fixpoint (citations form a DAG): the committed records carry no private path and still
    reference each other by the bytes they hold."""
    home = str(Path.home()).encode()
    files = sorted(p for p in recorded.rglob("*") if p.is_file())
    data = {p: gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes() for p in files}
    digest = {p: hashlib.sha256(d).hexdigest() for p, d in data.items()}
    latest: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for p in files:
            d = data[p].replace(home, b"~")
            for old, new in latest.items():
                d = d.replace(old.encode(), new.encode())
            if d != data[p]:
                h = hashlib.sha256(d).hexdigest()
                for k, v in list(latest.items()):
                    if v == digest[p]:
                        latest[k] = h
                latest[digest[p]] = h
                data[p], digest[p], changed = d, h, True
    for p in files:
        if p.suffix == ".gz":
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0, filename="") as fh:
                fh.write(data[p])
            p.write_bytes(buf.getvalue())
        else:
            p.write_bytes(data[p])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--recorded", type=Path, default=HERE / "recorded")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--studies", nargs="*", default=None, help="tracking studies to run (default all)")
    args = ap.parse_args(argv)
    cfg = json.loads(Path(os.environ["HEP_GEANT4_CONFIG"]).expanduser().read_text())
    c = Campaign3(args.work.expanduser().resolve(), cfg)
    c.setup()
    steps = args.only or ["msref", "shared", "tracking", "cc", "shower", "ladder", "export"]
    shared = {}
    if "msref" in steps:
        for rig in (1.0, 100.0, 500.0):
            c.msref(rig)
    if {"shared", "tracking", "cc", "ladder"} & set(steps):
        for cand in R.CANDIDATES:
            shared[cand] = c.shared(cand)
    if "tracking" in steps:
        for sid in args.studies or [s for s, v in R.STUDIES.items() if v[1] == "momentum-resolution-core"]:
            t = c.tracking(sid)
            out = c.finish_tracking(t, shared[R.STUDIES[sid][0]])
            print(json.dumps({"study": sid, "events": t["events"], **{k: str(v) for k, v in out.items()}}), flush=True)
    for step in ("cc", "shower", "ladder", "export"):
        if step in steps and hasattr(c, step):
            getattr(c, step)(shared, args.recorded)
    (c.work / "campaign-log.json").write_text(json.dumps(c.log, indent=1, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
