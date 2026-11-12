"""Synthetic g4sim products for the phase-3 evaluator and design tests (no Geant4): a two-volume scintillating readout
with the g4sim specifications (the ZDC example's run card and request, a minimal detector-spec material), a
response-pipeline/1 with scintillation, sensor and electronics stages, an analytic efficiency map, and batches of
cells.csv rows (edep_by_dedx_class and edep_visible_ly_split, in g4sim's bin layout) and primaries.csv rows drawn by
NumPy from a seed and an event interval. Everything here is `synthetic`."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))

import g4sim_simulate as simulate  # noqa: E402

EXAMPLE = ROOT / "examples" / "zdc-synthetic-ecal" / "specs"
BIRKS0 = 0.1                                          # mm/MeV
CLASSES = (40, 44)                                 # ionizing classes x in [1, 1.78) and [10, 17.8) MeV/mm
SPLIT, DEDX = "zdc_split", "zdc_classes"
VOLUMES = (1, 2)


def source(mean="500", sigma="50", lo="300", hi="700"):
    s = json.loads((EXAMPLE / "request.json").read_text())["source"]
    s["energy"] = {"gaussian": {"mean_MeV": mean, "sigma_MeV": sigma, "truncate_MeV": [lo, hi]}}
    return s


def documents(**source_kw) -> dict:
    request = json.loads((EXAMPLE / "request.json").read_text())
    request["source"] = source(**source_kw)
    request["scorers"] = [{"name": SPLIT, "readout": "zdc", "select": {"tags": ["crystal"]},
                           "quantity": "edep_visible_ly_split"},
                          {"name": DEDX, "readout": "zdc", "select": {"tags": ["crystal"]},
                           "quantity": "edep_by_dedx_class"}]
    run = json.loads((EXAMPLE / "run.json").read_text())
    detector = {"materials": {"scint": {"ionisation": {"birks_mm_per_MeV": str(BIRKS0)}}},
                "params": {"wrapping_mm": "0.5"}}

    def par(v):
        return {"value": v, "source_of_facts": "synthetic"}
    pipeline = {"schema": "response-pipeline/1", "run_seed": 12345, "replica": 0, "stages": [
        {"name": "scintillation", "kind": "scintillation", "parameters": {"light_yield_per_MeV": par(200.0),
                                                                         "resolution_scale": par(0.6)}},
        {"name": "sensor", "kind": "sensor", "parameters": {"gain": par(1.0), "excess_noise": par(0.1),
                                                           "dark_rate_per_ns": par(1e-4), "gate_ns": par(50.0)}},
        {"name": "electronics", "kind": "electronics", "parameters": {"noise_sigma": par(0.5), "threshold": par(1.0),
                                                                     "lsb": par(0.5), "bits": par(10)}}]}
    light = {"schema": "efficiency-map/1", "channels": ["a", "b"], "form": {"kind": "uniform", "value": [0.1, 0.05]}}
    return {"detector": detector, "request": request, "run": run, "pipeline": pipeline, "maps": {"light": light}}


def batch(seed: int, first: int, n: int, mean=500.0, sigma=50.0, lo=300.0, hi=700.0, **extra) -> dict:
    """cells.csv and primaries.csv rows of one interval of synthetic events (the event numbers seed the draws, so two
    batches on different intervals are independent)."""
    cells, prim = [], []
    for e in range(first, first + n):
        r = np.random.default_rng([seed, e])
        E = r.normal(mean, sigma)
        while not lo <= E <= hi:
            E = r.normal(mean, sigma)
        prim.append([e, E, 0, 0, 0, 0, 0, 1])
        for v in VOLUMES:
            dep = E * 1e-3 * r.uniform(0.3, 0.7) * (1.0 if v == 1 else 0.5)
            frac = r.uniform(0.6, 0.9)
            rows = [(CLASSES[0], dep * frac), (CLASSES[1], dep * (1 - frac))]
            for b, x in rows:
                cells.append([e, DEDX, v, b, x, 1, x])
            vis = simulate.reweighted(rows, BIRKS0)
            for b in (0, 1):
                share = 0.5 if b == 0 else 0.5
                cells.append([e, SPLIT, v, 2 * b, 0.8 * vis * share, int(r.integers(2, 20)), 0.0])
                cells.append([e, SPLIT, v, 2 * b + 1, 0.2 * vis * share, 1, 0.0])
    return {"logical_run_seed": seed, "first_event": first, "events": n, "cells": cells, "primaries": prim, **extra}


OBSERVABLES = [{"name": "pe_mean", "quantity": "photoelectrons", "functional": "mean"},
               {"name": "pe_std", "quantity": "photoelectrons", "functional": "std"},
               {"name": "vis_mean", "quantity": "edep_visible", "functional": "mean"},
               {"name": "e_mean", "quantity": "primary_energy", "functional": "mean"}]

BINDINGS = {"light_yield": {"document": "pipeline", "pointer": "/stages/0/parameters/light_yield_per_MeV/value"},
            "gain": {"document": "pipeline", "pointer": "/stages/1/parameters/gain/value"},
            "birks": {"document": "detector", "pointer": "/materials/scint/ionisation/birks_mm_per_MeV"},
            "beam_mean": {"document": "request", "pointer": "/source/energy/gaussian/mean_MeV"},
            "wrapping": {"document": "detector", "pointer": "/params/wrapping_mm"}}


def plan(batches: dict, bindings=None, **extra) -> dict:
    docs = documents()
    spec = {"kind": "g4sim", "documents": docs, "readout": "zdc", "map": "light",
            "scorers": {"split": SPLIT, "dedx": DEDX}, "batches": batches, "nominal": next(iter(batches)),
            "observables": copy.deepcopy(OBSERVABLES)}
    p = {"schema": "calibration-plan/1", "kernels": {}, "evaluator": spec,
         "node_binding": {"parameters": copy.deepcopy(bindings if bindings is not None else BINDINGS)}}
    p.update(extra)
    return p
