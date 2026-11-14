"""A valid phase-0 calibration contract on the toy detector, with its data releases (all synthetic), for the tests of
core/calibration and the calib_*.py scripts. Each negative test changes one thing in a deep copy."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "core" / "calibration" / "data"


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


CAL, VAL = h("release-calibration"), h("release-validation")


def toy() -> dict:
    return json.loads((FIXTURES / "toy_detector.json").read_text())


def observable(name, role, sample=None, **kw):
    o = {"name": name, "role": role, "functional": "location", "range": "positive", "link": "log",
         "block": "gaussian", "estimator": "mean", "binning": {"variable_level": "reconstructed"},
         "value_conventions": {"zero_events": "excluded", "one_event": "no-width", "zero_denominator": "excluded"}}
    if sample:
        o["sample"] = sample
    o.update(kw)
    return o


def contract() -> dict:
    t = toy()["contract"]
    params = []
    for p in t["parameters"]:
        p = dict(p, physical_bounds=[0.0, 10.0], sampling_bounds=[0.1, 5.0])
        if p["role"] == "phi":
            p["source"] = "external measurement of the material thickness (synthetic)"
        params.append(p)
    return {
        "schema": "calibration-contract/1", "series": "toy-holdout", "simulator": "toy-detector",
        "stage_graph": t["stage_graph"], "parameters": params, "references": t["references"],
        "models": {"enumerated": [{"id": "nominal"}], "absorbed": []},
        "observables": [observable("energy_mean", "calibration", "cal_sample"),
                        observable("energy_width", "calibration", "cal_sample", functional="core-width"),
                        observable("ratio_mean", "validation", "val_sample")],
        "event_samples": [{"id": "cal_sample", "normalization": "free",
                           "components": [{"id": "run1", "N_decl": 1000, "basis": "observed"}]},
                          {"id": "val_sample", "normalization": "free",
                           "components": [{"id": "run2", "N_decl": 800, "basis": "external",
                                           "basis_source": "exposure times an external rate (synthetic)"}]}],
        "estimators": {"shared_implementation": True, "uses_truth": False},
        "model_discrepancy": {"form": "fixed", "kernel": {"type": "squared-exponential", "length": 1.0}},
        "upstream": [],
        "validation": {"mode": "holdout", "N_dc": [], "N_d": [], "unused": [{"observable": "spare", "reason": "rank "
                       "condition (c)", "clause": "section 9.2"}],
                       "alternatives": [{"kind": "simulation-setting", "description": "no ENF in the gain stage"}]},
        "numerics": {"precision": "double"},
        "data": {"calibration_releases": [CAL], "validation_releases": [VAL]},
        "acceptance": {"strength": "standard"}, "intended_use": ["design-study", "systematic-variation"],
        "scope": {"beam_energy_gev": [1, 10]},
    }


def release(name, units, obs, samples, has_value=None):
    has_value = has_value or {o: True for o in obs}
    return {"schema": "calibration-data-release/1", "status": ["synthetic"], "submitter": "test fixture",
            "lineage": {"raw_units": list(units)},
            "observables": [{"name": o} for o in obs],
            "samples": samples,
            "declarations": {"representation_format": "float64", "derivation_relations": [],
                             "uncertainty_sources": {o: {"statistical": "expected", "systematic": "systematic"}
                                                     for o in obs},
                             "relative_systematic_correlation": "fully-correlated", "has_value": has_value}}


def releases() -> dict:
    cal_units = [f"evt-{i:04d}" for i in range(0, 1000)]
    val_units = [f"evt-{i:04d}" for i in range(1000, 1800)]
    return {
        CAL: release("calibration", cal_units, ["energy_mean", "energy_width"],
                     {"cal_sample": {"raw_units": cal_units, "totals": {"run1": 1000}}}),
        VAL: release("validation", val_units, ["ratio_mean", "spare"],
                     {"val_sample": {"raw_units": val_units}}),
    }


def copied():
    return copy.deepcopy(contract()), copy.deepcopy(releases())
