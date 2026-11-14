"""The synthetic ZDC fixture of Part B section 15.2 (phase 3, WP-F) without Geant4: g4sim products made by a SYNTHETIC
TRANSPORT STAND-IN, never by Geant4, with g4sim's Python layers for everything after transport.

No recorded g4sim products of the ZDC example with `edep_by_dedx_class` and `edep_visible_ly_split` exist in the repository
(`examples/zdc-synthetic-ecal/output` holds only a summary.json), so the stand-in writes them: per event a list of steps
(volume, segmentation bin, deposit, dE/dx) drawn by NumPy from a seed and the event number; from the steps, at a given
Birks constant k_B and nominal light yield LY, the rows g4sim's scorers would write (g4sim section 10.3): the deposit per
dE/dx class (`edep_by_dedx_class`, independent of k_B), and per bin E^L (the visible energy of the steps with
mu_s = LY e / (1 + k_B x) > 10), E^S (the others) and n^L (`edep_visible_ly_split`), with the true step-level visible
energy. A product made at k_B' is what a full g4sim_run at k_B' writes for the same events: k_B changes no random number
of the transport in the efficiency-map path (no optical photons are tracked), so the steps are the same and only the
split moves. The Geant4 version of each item is listed in `PRODUCTION_RUNS` (not run: Slurm, the user's approval).

Everything here is `synthetic`."""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

import g4sim_simulate as simulate  # noqa: E402

LABEL = "synthetic transport stand-in (not Geant4)"
EXAMPLE = ROOT / "examples" / "zdc-synthetic-ecal" / "specs"
BIRKS0 = 0.1                 # mm/MeV, nominal k_B of the scintillating crystal (assumed)
LIGHT_YIELD0 = 200.0                  # photons per MeV, nominal light yield (assumed)
R0 = 0.5                     # RESOLUTIONSCALE r (section 15.3.1: r = 0.5)
BIRKS_PRIOR = (0.02, 0.4)
SPLIT, DEDX = "zdc_split", "zdc_classes"
VOLUMES = (1, 2)
BINS = (0, 1)
STEPS = 30                   # steps per (volume, bin)
MATERIAL = "PbWO4_scint"


def dedx_class(x: float) -> int:
    """The ionizing `edep_by_dedx_class` bin of dE/dx x (g4sim section 9.1: four classes per decade)."""
    return int(math.floor(simulate.CLASSES_PER_DECADE * math.log10(x))) + simulate.CLASS_OFFSET


def event_steps(seed: int, event: int) -> list:
    """(volume, bin, deposit MeV, dE/dx MeV/mm) of one event: per bin a fixed number of steps (so the width of the photon
    count is photon statistics, not deposit fluctuations), each x near its class's geometric centre (a small
    discretization bound). The low-dE/dx steps (class [1, 1.78)) have mu_s ~ 13 at the nominal k_B and LY and cross
    mu_s = 10 only near the upper k_B extreme; the high-dE/dx steps (class [10, 17.8)) stay below 10 in the prior."""
    r = np.random.default_rng([seed, event])
    out = []
    for v in VOLUMES:
        for b in BINS:
            out += [(v, b, float(r.uniform(0.0725, 0.0750)), float(r.uniform(1.32, 1.35))) for _ in range(STEPS - 4)]
            out += [(v, b, float(r.uniform(0.02, 0.04)), float(r.uniform(13.2, 13.5))) for _ in range(4)]
    return out


def products(seed: int, first: int, n: int, birks: float = BIRKS0, light_yield: float = LIGHT_YIELD0) -> dict:
    """cells.csv and primaries.csv rows (g4sim's bin layout, as in calibration_g4sim_eval_fixtures) of the events
    [first, first + n), with the split at (birks, light_yield), and the true step-level visible energy per (event,
    volume) (the `edep_visible` a run at `birks` scores)."""
    cells, prim, vis = [], [], {}
    for e in range(first, first + n):
        prim.append([e, 500.0, 0, 0, 0, 0, 0, 1])
        classes: dict = {}
        split: dict = {}
        for v, b, dep, x in event_steps(seed, e):
            c = dedx_class(x)
            classes[(v, c)] = classes.get((v, c), 0.0) + dep
            s = dep / (1.0 + birks * x)
            vis[(e, v)] = vis.get((e, v), 0.0) + s
            L, S, k = split.get((v, b), (0.0, 0.0, 0))
            if light_yield * s > 10.0:
                split[(v, b)] = (L + s, S, k + 1)
            else:
                split[(v, b)] = (L, S + s, k)
        for (v, c), dep in sorted(classes.items()):
            cells.append([e, DEDX, v, c, dep, 1, dep])
        for (v, b), (L, S, k) in sorted(split.items()):
            cells.append([e, SPLIT, v, 2 * b, L, k, 0.0])
            cells.append([e, SPLIT, v, 2 * b + 1, S, 1, 0.0])
    return {"cells": cells, "primaries": prim, "edep_visible": vis}


def batch(seed: int, first: int, n: int, birks: float = BIRKS0, light_yield: float = LIGHT_YIELD0, point=None, **extra) -> dict:
    """One batch for the evaluator; a batch made at a k_B other than the nominal carries `point` (a told run)."""
    p = products(seed, first, n, birks, light_yield)
    out = {"logical_run_seed": seed, "first_event": first, "events": n, "cells": p["cells"],
           "primaries": p["primaries"], "label": LABEL, **extra}
    if point is not None:
        out["point"] = dict(point)
    return out


def documents(r: float = R0, efficiencies=(0.5, 0.4)) -> dict:
    """The ZDC example's g4sim specifications with the section 15.2 extensions: an explicit Birks constant on the
    scintillating crystal, the two scorers, and a response-pipeline/1 with a scintillation stage at r."""
    request = json.loads((EXAMPLE / "request.json").read_text())
    request["scorers"] = [{"name": SPLIT, "readout": "zdc", "select": {"tags": ["crystal"]},
                           "quantity": "edep_visible_ly_split"},
                          {"name": DEDX, "readout": "zdc", "select": {"tags": ["crystal"]},
                           "quantity": "edep_by_dedx_class"}]
    run = json.loads((EXAMPLE / "run.json").read_text())
    detector = {"materials": {MATERIAL: {"ionisation": {"birks_mm_per_MeV": str(BIRKS0)}}}}

    def par(v):
        return {"value": v, "source_of_facts": "synthetic"}
    pipeline = {"schema": "response-pipeline/1", "run_seed": 1, "replica": 0, "stages": [
        {"name": "scintillation", "kind": "scintillation", "parameters": {"light_yield_per_MeV": par(LIGHT_YIELD0),
                                                                         "resolution_scale": par(r)}},
        {"name": "sensor", "kind": "sensor", "parameters": {"gain": par(1.0), "excess_noise": par(0.0),
                                                           "dark_rate_per_ns": par(0.0), "gate_ns": par(50.0)}},
        {"name": "electronics", "kind": "electronics", "parameters": {"noise_sigma": par(0.5), "threshold": par(1.0),
                                                                     "lsb": par(0.5), "bits": par(16)}}]}
    light = {"schema": "efficiency-map/1", "channels": ["a", "b"], "form": {"kind": "uniform",
                                                                           "value": list(efficiencies)}}
    return {"detector": detector, "request": request, "run": run, "pipeline": pipeline, "maps": {"light": light}}


BINDINGS = {"birks": {"document": "detector", "pointer": f"/materials/{MATERIAL}/ionisation/birks_mm_per_MeV"},
            "light_yield": {"document": "pipeline", "pointer": "/stages/0/parameters/light_yield_per_MeV/value"},
            "resolution": {"document": "pipeline", "pointer": "/stages/0/parameters/resolution_scale/value"},
            "gain": {"document": "pipeline", "pointer": "/stages/1/parameters/gain/value"}}
CONTRACT_DOCUMENT = {"detector": "detector-spec", "pipeline": "response-pipeline", "request": "simulation-request"}
OBSERVABLES = [{"name": "pe_mean", "quantity": "photoelectrons", "functional": "mean"},
               {"name": "pe_std", "quantity": "photoelectrons", "functional": "std"},
               {"name": "vis_mean", "quantity": "edep_visible", "functional": "mean"}]
PRIORS = {"birks": BIRKS_PRIOR, "light_yield": (180.0, 220.0), "resolution": (0.4, 0.9), "gain": (0.9, 1.1)}


def plan(batches: dict, nominal: str | None = None, r: float = R0, observables=None, **extra) -> dict:
    obs = [o for o in OBSERVABLES if observables is None or o["name"] in observables]
    spec = {"kind": "g4sim", "documents": documents(r), "readout": "zdc", "map": "light",
            "scorers": {"split": SPLIT, "dedx": DEDX}, "batches": batches, "nominal": nominal or next(iter(batches)),
            "observables": copy.deepcopy(obs)}
    p = {"schema": "calibration-plan/1", "kernels": {}, "evaluator": spec}
    p.update(extra)
    return p


def contract(thetas=("birks",), observables=("pe_mean", "pe_std"), exposure: int = 2000, priors=None) -> dict:
    """A calibration contract over the fixture: theta with sampling bounds (the prior) and their locked bindings, the
    observables as Gaussian blocks with log links, one exposure for the evaluator's run label `g4sim`."""
    priors = {**PRIORS, **(priors or {})}
    pars = [{"name": t, "role": "theta", "sampling_bounds": list(priors[t]),
             "physical_bounds": [0.0, 10.0 * priors[t][1]],
             "bindings": [{"document": CONTRACT_DOCUMENT[BINDINGS[t]["document"]], "pointer": BINDINGS[t]["pointer"]}]}
            for t in thetas]
    obs = [{"name": o, "role": "calibration", "block": "gaussian", "link": "log", "functional": "location"}
           for o in observables]
    return {"schema": "calibration-contract/1", "simulator": "g4sim", "parameters": pars, "observables": obs,
            "exposure": {"g4sim": exposure}, "validation": {"mode": "holdout", "N_dc": []}}


# ------------------------------------------------------------------ the Geant4 production runs (not run here)
CALORIMETER_MS_PER_EVENT = 9.2     # 40.8 billed core-hours for 2 x 8,000,000 events of the ZDC example (g4sim S3 gate 3,
#                            job 7477544; g4sim-tasks/S3.md): 500 MeV e+, edep scorer only
SCORER_FACTOR = 1.5         # an assumed margin for the two per-step scorers this fixture adds (no recorded time)


def production_runs(events: int = 20_000, seed: int = 20261201) -> list:
    """The g4sim_run productions the real fixture needs (section 15.2 synthetic ZDC; section 15.3.1 P0 (k_B);
    section 15.3.16), on the ZDC example's cards with this fixture's extensions; the run cards themselves come from the
    evaluator's ask (G4simEvaluator.ask) for the resimulated points. Cost from the recorded ZDC rate."""
    core_h = events * CALORIMETER_MS_PER_EVENT * SCORER_FACTOR / 3.6e6
    rows = [
        {"name": "nominal", "birks": BIRKS0, "events": events, "seed": seed, "first_event": 0,
         "use": "fit (the nominal MC of the rerun and the re-digitizations)"},
        {"name": "kB-low", "birks": BIRKS_PRIOR[0], "events": events, "seed": seed, "first_event": 0,
         "use": "P0 (k_B) spot check and the section 15.2 rerun-vs-resimulation item at the lower k_B extreme: the "
                "nominal run's seed and interval (the same events), detector-spec k_B written to the extreme"},
        {"name": "kB-high", "birks": BIRKS_PRIOR[1], "events": events, "seed": seed, "first_event": 0,
         "use": "as kB-low at the upper extreme"},
        {"name": "reference", "birks": BIRKS0, "events": events, "seed": seed + 1, "first_event": 0,
         "use": "P0 of the response parameters (re-digitization against g4sim_run plus response; independent events)"},
        {"name": "LY-low", "light_yield": PRIORS["light_yield"][0], "events": events, "seed": seed, "first_event": 0,
         "use": "P0 at the LY extremes (section 5.4: the E^L/E^S split at a digitization LY other than the nominal)"},
        {"name": "LY-high", "light_yield": PRIORS["light_yield"][1], "events": events, "seed": seed,
         "first_event": 0, "use": "as LY-low"},
    ]
    for r in rows:
        r["core_hours"] = round(core_h, 3)
    return rows


def production_cards(evaluator, state_path: str, nominal: dict, series: str = "simcal-p3", study: str = "zdc") -> list:
    """The run requests of the k_B spot checks from the evaluator's ask (detector-spec with k_B written at each
    extreme), re-pointed at the nominal run's logical_run_seed and interval: the paired comparison of section 15.2
    item 3 uses the same Geant4 events (k_B draws no random number in transport without optical photons)."""
    reqs = evaluator.ask([{"birks": BIRKS_PRIOR[0]}, {"birks": BIRKS_PRIOR[1]}], state_path, series=series, study=study,
                         events=int(nominal["events"]))
    for r in reqs:
        r["run"]["run"].update(logical_run_seed=int(nominal["logical_run_seed"]),
                               first_event=int(nominal["first_event"]), events=int(nominal["events"]))
        r.update(logical_run_seed=int(nominal["logical_run_seed"]), first_event=int(nominal["first_event"]),
                 paired_with="nominal")
    return reqs


def truth_events(evaluator, theta: dict, batch: str) -> dict:
    """Per-event observable values of `batch` at theta with the evaluator's methods (the truth MC of G8), and the run
    label; no event weights (k_B and the response parameters are not reweighted)."""
    import g4sim_calib_eval as E
    b = evaluator.batches[batch]
    tab = E.batch_tables(b, evaluator.scorers)
    events = np.arange(tab["first"], tab["first"] + tab["n"])
    values = {**evaluator.nominal_theta, **theta}
    kb, kb0 = evaluator._birks(values, b)
    vis = evaluator._visible(tab, events, kb)[0] if kb is not None else None
    rows = evaluator._digitize(values, tab, b, kb, kb0)
    return {"run": evaluator.run, "values": {o["name"]: evaluator._values(o, tab, events, vis, rows)
                                             for o in evaluator.observable_specs},
            "functionals": {o["name"]: o.get("functional", "mean") for o in evaluator.observable_specs}}
