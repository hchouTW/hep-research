"""The RICH-replica fixture of Part B section 15.2 (phase 3, WP-F): the g4sim S7 reference case `ams02-rich-replica`
(synthetic; full optical tracking; FTFP_BERT_EMZ) as a calibration problem with theta on the radiator height
(`params.height_mm`) and on the refractive-index spectrum (`materials.aerogel.optical.rindex`, a theta that rescales the
whole spectrum: n(E) -> s n(E)), both resimulation. Here only the Slurm-scale configuration is built: the documents at
each design point and beta sample, and the run cards with one seed block and event interval per beta sample (common
random numbers across the design points, independent samples), as G4simEvaluator.ask does for a scalar binding. No
Geant4 run here (each array needs the user's approval). The unit tests use core/calibration/cherenkov_standin.py.

Everything here is `synthetic`."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import design_g4sim as DG  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402

CASE = ROOT / "profiles" / "reference" / "geometry-cases" / "cases" / "ams02-rich-replica"
CLAIMS = ("ams02:C70", "ams02:C205")
BINDINGS = {"height_mm": {"document": "detector", "pointer": "/params/height_mm"},
            "index_scale": {"document": "detector", "pointer": "/materials/aerogel/optical/rindex/value",
                            "form": "scale"}}
SAMPLES = [{"name": "R_p100", "particle": "proton", "kinetic_per_nucleon_GeV": 100.0, "nucleons": 1},
           {"name": "R_p2.4", "particle": "proton", "kinetic_per_nucleon_GeV": 2.4, "nucleons": 1}]
CPU_S_PER_EVENT = 25.305 / 300   # Slurm job 7523520 (S7 RICH case, 300 events of 100 GeV protons, set-up included)


def documents() -> dict:
    return {"detector": json.loads((CASE / "detector-spec.json").read_text()),
            "request": json.loads((CASE / "request.json").read_text()),
            "run": json.loads((CASE / "run.json").read_text())}


def apply(docs: dict, theta: dict, sample: dict | None = None) -> dict:
    """The documents at theta (decimal strings, as the specification writes them) and, with a sample, its beam."""
    out = DG.apply_theta(copy.deepcopy(docs), {"node_binding": {"parameters": BINDINGS}}, theta)  # scale: s n(E)
    if sample is not None:
        src = out["request"]["source"]
        src["particle"] = sample["particle"]
        src["energy"] = {"mono": {"energy_MeV": repr(1000.0 * sample["kinetic_per_nucleon_GeV"] * sample["nucleons"])}}
    return out


def ask(points: list, series: str, study: str, events: int, samples=SAMPLES, registered=()) -> list:
    """One g4sim_run request per (design point, beta sample): per sample one seed block and one event interval, shared
    by its design points (common random numbers, section 6.6); different samples are independent blocks."""
    docs = documents()
    out = []
    for b, smp in enumerate(samples):
        seed, t = DG.block_seed(series, study, "design", "surrogate", b, registered)
        first, n = DG.member_interval(0, int(events), 1)
        for i, theta in enumerate(points):
            d = apply(docs, theta, smp)
            card = d["run"]
            card["run"].update(logical_run_seed=seed, first_event=first, events=n)
            out.append({"point_id": f"{i}", "sample": smp["name"], "theta": dict(theta), "logical_run_seed": seed,
                        "seed_t": t, "first_event": first, "events": n, "run": card, "detector": d["detector"],
                        "request": d["request"], "run_sha256": canonical_sha256(card),
                        "detector_sha256": canonical_sha256(d["detector"]),
                        "request_sha256": canonical_sha256(d["request"])})
    return out


def production(n_design: int = 24, held_back: int = 8, events: int = 2000, samples=SAMPLES) -> dict:
    """The Slurm-scale production of the real evidence (P3 at the prior centre from the surrogate's or a finite-
    difference design; the section 8.7 note 6 classification needs toys on top): runs, events and CPU from the recorded
    rate of the S7 case (100 GeV protons; low-momentum protons emit fewer photons, so the rate is an upper bound)."""
    runs = (n_design + held_back) * len(samples)
    cpu_h = runs * events * CPU_S_PER_EVENT / 3600.0
    return {"runs": runs, "events_per_run": events, "samples": [s["name"] for s in samples],
            "design_points": n_design, "held_back": held_back, "cpu_hours": round(cpu_h, 2),
            "rate": "0.084 CPU s per event (job 7523520, set-up included)"}
