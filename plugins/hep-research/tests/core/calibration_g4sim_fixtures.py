"""A g4sim calibration contract and its documents (all synthetic), for the phase-3 tests of the model identity (Part B
section 5.1) and the g4sim binding (section 11.4). The documents are g4sim's real formats: the synthetic ZDC example
specifications (detector-spec/1, simulation-request/1, g4sim-run/1) and a response-pipeline/1, alignment-overlay/1,
condition-snapshot/1 and a mapped efficiency-map/1 built here and checked by g4sim's own readers in the tests."""
from __future__ import annotations

import json
import random
from pathlib import Path

import calibration_fixtures as F

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "examples" / "zdc-synthetic-ecal" / "specs"
RUN_SCHEMA = ROOT / "adapters" / "geant4" / "assets" / "g4sim_run.schema.json"
SHA = "ab" * 32


def detector_text(birks="0.126", thickness="0.065", **extra) -> bytes:
    """The ZDC example detector-spec/1 with a Birks constant on FR4 (so that k_B can be bound) as text."""
    spec = json.loads((SPECS / "detector.json").read_text())
    spec["materials"]["FR4"]["ionisation"] = {"birks_mm_per_MeV": birks}
    spec["templates"]["crystal"]["modifiers"][0]["shell"]["thickness_mm"] = thickness
    spec.update(extra)
    return json.dumps(spec, indent=1).encode()


def request_text(energy="500") -> bytes:
    req = json.loads((SPECS / "request.json").read_text())
    req["source"]["energy"]["mono"]["energy_MeV"] = energy
    return json.dumps(req).encode()


def run_card(**physics) -> dict:
    card = json.loads((SPECS / "run.json").read_text())
    card["kill_policy"] = {"min_kinetic_energy_MeV": 0.01}
    card["physics"].update(physics)
    return card


def pipeline(light_yield=200.0, gain=1.0, run_seed=11, replica=0) -> dict:
    def par(v):
        return {"value": v, "source_of_facts": "synthetic"}
    return {"schema": "response-pipeline/1", "run_seed": run_seed, "replica": replica, "stages": [
        {"name": "scintillation", "kind": "scintillation", "readout": "ecal",
         "parameters": {"light_yield_per_MeV": par(light_yield), "resolution_scale": par(0.6)}},
        {"name": "collection", "kind": "efficiency_map", "readout": "ecal", "parameters": {}},
        {"name": "sensor", "kind": "sensor", "readout": "ecal",
         "parameters": {"gain": par(gain), "excess_noise": par(0.1), "dark_rate_per_ns": par(0.001),
                        "gate_ns": par(50.0)}},
        {"name": "electronics", "kind": "electronics", "readout": "ecal",
         "parameters": {"noise_sigma": par(0.5), "threshold": par(1.0), "lsb": par(0.5), "bits": par(10)}}]}


def overlay(dx="0.05", description="survey 1") -> dict:
    return {"schema": "alignment-overlay/1", "description": description, "source_of_facts": {"/shifts": "synthetic"},
            "shifts": [{"mother": "world", "template": "crystal_shell", "copy_number": 0, "delta_mm": [dx, "0", "0"]}]}


def snapshot(gain_factor=1.02, threshold=2.0, dead=False, description="conditions v1") -> dict:
    return {"schema": "condition-snapshot/1", "readout": "ecal", "version": "v1", "description": description,
            "source_of_facts": {"/iovs": "synthetic"}, "time_unit": "ns", "defaults": {"gain_factor": 1.0},
            "iovs": [{"start_ns": 0, "end_ns": 1000000000, "rows": [
                {"cell": {"volume": 0, "channel": 0}, "gain_factor": gain_factor, "threshold": threshold,
                 "dead": dead}]}]}


EVENT_TIME = {"kind": "linear", "start_ns": 0, "step_ns": 1000}
BUILD = {"build_hash": SHA, "geant4_version": "11.2.1", "datasets": {"G4EMLOW": "8.5", "G4ENSDFSTATE": "2.3"}}


def efficiency_map(seed=7, photons=4000) -> dict:
    from core.simulation import efficiency_map as em
    draw = random.Random(seed)
    half = [10.0, 10.0, 26.5]
    emitted, detected = {}, []
    for event in range(photons):
        emitted[event] = [draw.uniform(-h, h) for h in half]
        u = draw.random()
        if u < 0.03:
            detected.append((event, "left", draw.expovariate(0.5)))
        elif u < 0.05:
            detected.append((event, "right", draw.expovariate(0.4)))
    return em.build(template="crystal", component=1, spectrum={"energy_eV": ["2", "3"], "value": ["1", "1"]},
                    segmentation={"kind": "along_axis", "axis": 2, "width_mm": ["13.25"]}, half_mm=half,
                    channels=["left", "right"], emitted=emitted, detected=detected,
                    hashes={"materials_sha256": "0" * 64, "surfaces_sha256": "1" * 64, "mapping_run_id": "x"})


def documents(**over) -> dict:
    """The documents of model "nominal", as model_identity.identity reads them."""
    docs = {"detector_spec": detector_text(), "alignment_overlay": overlay(), "simulation_request": request_text(),
            "run_card": run_card(), "response_pipeline": pipeline(), "efficiency_map": efficiency_map(),
            "condition_snapshot": snapshot(), "event_time_rule": dict(EVENT_TIME), "build_environment": dict(BUILD)}
    docs.update(over)
    return {k: v for k, v in docs.items() if v is not None}


def tables() -> dict:
    from contracts.geometry import field_types
    from contracts.schema import load_schema
    from core.calibration import model_identity as mi
    out = {"detector-spec": field_types(), "run-card": mi.type_table(json.loads(RUN_SCHEMA.read_text()))}
    for kind, name in (("alignment-overlay", "alignment_overlay"), ("simulation-request", "simulation_request"),
                       ("response-pipeline", "response_pipeline"), ("condition-snapshot", "condition_snapshot")):
        out[kind] = mi.type_table(load_schema(f"{name}.json"))
    return out


NODES = [("source", "density", "0"), ("transport", "black-box", "1"), ("quanta", "density", "2"),
         ("collection", "density", "3"), ("pde", "density", "4a"), ("sensor", "density", "4b"),
         ("electronics", "density", "5e"), ("readout", "deterministic", "5r"), ("reco", "deterministic", "6-7")]


def index():
    return {"mechanism": "noise-threshold", "channel_set": "ecal channel 0", "conditioning": "piecewise-independent"}


def parameter(name, role, node, document, pointer, **kw):
    p = {"name": name, "role": role, "nodes": [node], "physical_bounds": [0.0, 10.0], "sampling_bounds": [0.1, 5.0],
         "bindings": [{"document": document, "pointer": pointer}]}
    if role == "phi":
        p["source"] = "synthetic external measurement"
    p.update(kw)
    return p


def contract(identity=None) -> dict:
    c = F.contract()
    c["simulator"] = "g4sim"
    c["source"] = {"density": "analytic"}
    nodes = [{"id": n, "kernel": k, "kind": "stage"} for n, k, _ in NODES]
    nodes[1]["samplable"] = True
    nodes.append({"id": "module", "kernel": "deterministic", "kind": "observation"})
    edges = [{"from": a[0], "to": b[0]} for a, b in zip(NODES, NODES[1:])] + [{"from": "reco", "to": "module"}]
    c["stage_graph"] = {"nodes": nodes, "edges": edges}
    c["references"] = [{"id": "known_beam", "type": "known-input", "edge": {"into": "source"},
                        "observation": "module"}]
    c["parameters"] = [
        parameter("beam_energy", "theta", "source", "simulation-request", "/source/energy/mono/energy_MeV"),
        parameter("wrap_thickness", "phi", "transport", "detector-spec",
                  "/templates/crystal/modifiers/0/shell/thickness_mm"),
        parameter("birks", "theta", "transport", "detector-spec", "/materials/FR4/ionisation/birks_mm_per_MeV"),
        parameter("light_yield", "theta", "quanta", "response-pipeline", "/stages/0/parameters/light_yield_per_MeV/value"),
        parameter("gain", "theta", "sensor", "response-pipeline", "/stages/2/parameters/gain/value"),
        parameter("threshold_0", "theta", "electronics", "condition-snapshot", "/iovs/0/rows/0/threshold",
                  index=index()),
        parameter("cut", "theta", "transport", "run-card", "/physics/cuts_mm/default"),
        parameter("reco_offset", "theta", "reco", "reconstruction", "/planes/0/offset_mm"),
    ]
    c["models"] = {"enumerated": [{"id": "nominal", "physics_list": "FTFP_BERT_EMZ"}], "absorbed": []}
    if identity is not None:
        c["models"]["enumerated"][0]["identity"] = identity
    return c


def plan() -> dict:
    base = {"recording": "column", "stored": ["edep_by_dedx_class", "edep_visible_ly_split", "hits",
                                             "simreco_columns"]}
    nb = {n: dict(base, table1=t) for n, _, t in NODES}
    nb["source"]["support_declared"] = True
    nb["quanta"]["stage"] = "scintillation"
    nb["sensor"]["distribution"] = "poisson"
    return {"schema": "calibration-plan/1", "kernels": {}, "node_binding": {"nodes": nb, "pde_split": False},
            "design_points": [{"theta": {}}]}

