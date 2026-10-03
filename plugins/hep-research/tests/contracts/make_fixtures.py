#!/usr/bin/env python3
"""Regenerate contract fixtures under contracts/fixtures/. All values are SYNTHETIC placeholders
chosen to exercise structure; none is a measurement, prediction, or experiment parameter.

Usage: python3 tests/contracts/make_fixtures.py   (rewrites the fixture files and cases.json)
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "contracts" / "fixtures" / "artifacts"
SYN = "SYNTHETIC structural fixture; values are placeholders, not physics"


def envelope(atype, ext, producer, status=("synthetic", "unvalidated"), **kw):
    doc = {
        "contract_version": "1.0.0", "artifact_id": f"fixture-synthetic-{atype}", "artifact_type": atype,
        "objective": SYN, "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": "0.1.0", "contracts": "1.0.0", "profiles": {}},
        "provenance": {"producer_skill": producer, "created": "2026-10-02", "evidence_ids": []},
        "inputs": [], "outputs": [], "status": list(status), "unresolved_inputs": [], "extension": ext,
    }
    doc.update(kw)
    return doc


def observable(kind="integrated-luminosity", level="particle-fiducial", **extra):
    o = {"quantity": "differential-cross-section", "process": "synthetic e+ e- -> mu+ mu-",
         "variables": [{"name": "cos_theta", "unit": "1", "edges": [-1.0, -0.5, 0.0, 0.5, 1.0]}],
         "phase_space": {"definition": "synthetic fiducial region", "fiducial": True},
         "level": level, "frame": "center-of-mass", "normalization": {"kind": kind, "ref": "synthetic-normalization.json"},
         "bin_semantics": "bin-averaged", "unit": "pb",
         "conventions": {"energy_variable": "sqrt_s", "frame": "center-of-mass"}}
    o.update(extra)
    return o


def measurement(kind="integrated-luminosity", **extra):
    ext = {"observable": observable(kind), "species_or_process": "synthetic",
           "period": {"start": "synthetic-period-1", "end": "synthetic-period-1"},
           "selections": [{"name": "two-muons", "definition": "placeholder", "conditional_denominator": "all events"}],
           "backgrounds": [{"name": "placeholder-bkg", "estimator": "sideband"}],
           "corrections": [{"effect_id": "trigger-eff", "category": "efficiency", "applied_in": "estimator"}],
           "systematics": [{"name": "energy-scale", "source": "calibration", "effect": "migration", "applied_via": "migration"}],
           "blinding": {"blinded": False}}
    ext.update(extra)
    return envelope("measurement-spec", ext, "hep-analysis")


def theory(**extra):
    ext = {"model": {"id": "synthetic-model", "description": "structural fixture"},
           "assumptions": ["placeholder assumption"], "conventions": {"hbar_c_one": True, "metric_signature": "+---"},
           "order": "tree-level", "parameters": {"p": "placeholder"}, "scales": "not-applicable",
           "derivation_status": "not-derived", "validity_domain": {"note": "placeholder"},
           "checks_run": [], "checks_not_run": ["all (fixture)"]}
    ext.update(extra)
    return envelope("theory-spec", ext, "hep-theory", status=("unvalidated",))


def prediction(**extra):
    ext = {"observable": observable(), "parameter_point": {"p": 1}, "representation": "numerical",
           "values": {"edges": [-1.0, -0.5, 0.0, 0.5, 1.0], "values": [1.0, 1.0, 1.0, 1.0], "unit": "pb"},
           "uncertainties": [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown"}],
           "allowed_transformations": ["forward-fold"]}
    ext.update(extra)
    return envelope("prediction", ext, "hep-theory")


def dataset(status="synthetic", did="synthetic-collider:synthetic-angular-1", **extra):
    ext = {"dataset_id": did, "source_evidence_ids": [], "observable": observable(),
           "data": {"edges": [-1.0, -0.5, 0.0, 0.5, 1.0], "values": [1.0, 2.0, 3.0, 4.0], "unit": "pb",
                    "uncertainties": [{"name": "stat", "kind": "statistical", "values": [0.1, 0.1, 0.1, 0.1], "correlation": "uncorrelated"}]},
           "covariance": {"status": "absent"}, "status": status, "experiment_profile": "experiment:synthetic-collider"}
    ext.update(extra)
    return envelope("dataset-record", ext, "hep-analysis")


def statres(paradigm, **extra):
    ext = {"paradigm": paradigm, "likelihood": {"form": "poisson"}, "parameters_of_interest": ["mu"],
           "nuisances": [], "fit_status": "converged"}
    if paradigm == "frequentist":
        ext.update(test_statistic="q_mu", construction="neyman", coverage={"toys": 0, "note": "fixture"})
    if paradigm == "bayesian":
        ext.update(priors=[{"parameter": "mu", "form": "uniform[0,5]"}], sampler={"name": "placeholder"}, convergence={"rhat": "not-provided"})
    ext.update(extra)
    return envelope("statistical-result", ext, "hep-statistics", status=("asimov", "unvalidated"))


def statres_v11(paradigm, **extra):
    """A statistical-result written under contracts 1.1.0 (optional significance, expected, breakdown, GoF fields)."""
    d = statres(paradigm, **extra)
    d["contract_version"] = "1.1.0"
    d["versions"]["contracts"] = "1.1.0"
    d["artifact_id"] = "fixture-synthetic-statistical-result-v1-1"
    return d


SCAN = {"local_p": 1.0e-3, "local_z": 3.09, "scan": {"parameters": ["mass"], "ranges": [[100.0, 200.0]]}}


VALID = {
    "measurement_collider.json": measurement(),
    "measurement_exposure.json": measurement("exposure", observable=observable("exposure", level="detector", quantity="differential-flux", unit="m^-2 sr^-1 s^-1 GV^-1", variables=[{"name": "rigidity", "unit": "GV", "edges": [1, 2, 4]}])),
    "measurement_protons_on_target.json": measurement("protons-on-target", observable=observable("protons-on-target", level="detector", quantity="event-count", unit="1")),
    "measurement_target_exposure.json": measurement("target-exposure", observable=observable("target-exposure", level="detector", quantity="rate", unit="tonne^-1 yr^-1")),
    "response.json": envelope("response", {"truth_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
                                           "reco_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
                                           "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
                                           "inefficiency": "inside_matrix", "acceptance": "inside_matrix",
                                           "includes": ["efficiency", "acceptance"], "applied_separately": [],
                                           "conditions": "synthetic", "provenance": SYN}, "detector-response"),
    "response_parametrized.json": envelope("response", {"form": "parametrized", "truth_axis": "not-applicable", "reco_axis": "not-applicable",
                                                        "orientation": "rows_reco_cols_truth", "normalization": "unnormalized",
                                                        "inefficiency": "inside_matrix", "acceptance": "inside_matrix", "includes": ["efficiency"],
                                                        "parametrization": {"variables": ["pt"], "function_ref": "synthetic-eff.json", "validity_range": {"pt": [10, 1000]}},
                                                        "conditions": "synthetic", "provenance": SYN}, "detector-response"),
    "measurement_ratio.json": measurement("exposure", observable=observable("exposure", level="detector", quantity="ratio", unit="1",
                                                                            variables=[{"name": "rigidity", "unit": "GV", "edges": [1, 2, 4]}]),
                                          ratio={"numerator": "species-A", "denominator": "species-B",
                                                 "cancellations": [{"effect": "exposure", "treatment": "cancels", "correlation_model": "identical exposure per period"}]}),
    "theory_spec.json": theory(),
    "prediction.json": prediction(),
    "dataset_record.json": dataset(),
    "comparison_spec.json": envelope("comparison-spec", {"dataset_bindings": ["synthetic-collider:synthetic-angular-1"],
                                                         "prediction_bindings": ["fixture-synthetic-prediction"],
                                                         "gate_result": {"comparable": True, "mismatches": []},
                                                         "transformations": [{"kind": "forward-fold", "owner": "detector-response"}],
                                                         "correlations": [], "inference_assumptions": ["placeholder"]}, "hep-statistics"),
    "statres_frequentist.json": statres("frequentist"),
    "statres_bayesian.json": statres("bayesian"),
    "statres_scan_global.json": statres_v11(
        "frequentist", construction="toy-calibrated-profile",
        significance={**SCAN, "global_p": 0.02, "global_z": 2.05, "trials_method": "gross-vitells"},
        expected={"median": 1.2, "band_1sigma": [0.9, 1.7], "band_2sigma": [0.7, 2.4], "method": "asimov"},
        uncertainty_breakdown={"method": "group-freeze", "order": ["theory", "detector"],
                               "groups": [{"name": "theory", "value": 0.2}, {"name": "detector", "value": 0.1}],
                               "closure": {"ratio_to_total": 0.99}},
        goodness_of_fit={"statistic": "saturated-deviance", "p_value": 0.4, "calibration": "toys", "n_toys": 1000}),
    "statres_bayesian_rhat_warning.json": statres_v11("bayesian", fit_status="converged-with-warnings",
                                                      convergence={"rhat": {"mu": 1.05}, "ess_bulk": {"mu": 900}}),
    "ml_artifact.json": envelope("ml-artifact", {"task": "classification", "labels": ["sig", "bkg"], "features": ["x"],
                                                 "splits": {"grouping_key": "run_id"}, "training_domain": {"x": [0, 1]},
                                                 "preprocessing": [], "model_hash": "sha256:placeholder", "downstream_validation": []}, "physics-ml"),
    "computational_run.json": envelope("computational-run", {"input_manifest": [{"path": "in.json", "sha256": "placeholder"}],
                                                             "tools": [{"name": "python", "version": "3.11"}], "commands": ["placeholder"],
                                                             "environment": {}, "seeds": {"toys": 1}, "tolerances": {}, "exit_status": 0,
                                                             "output_hashes": {}}, "hep-computing"),
    "communication.json": envelope("communication", {"claims": [{"text": "placeholder", "result_ref": "x.json", "status": "synthetic"}],
                                                     "sources_read": [{"id": "user:S1", "level": "full-text"}],
                                                     "limitations": ["fixture"]}, "research-communication"),
}

bad = {}
d = theory(); d["extension"]["blinding"] = {"blinded": True}; bad["theory_experiment_field.json"] = (d, ["theory.experiment_field"])
d = theory(); d["bindings"]["experiments"] = [{"profile": "experiment:synthetic-collider", "version": "1.0.0"}]; bad["theory_experiment_binding.json"] = (d, ["theory.experiment_binding"])
d = measurement(); d["extension"]["corrections"].append({"effect_id": "trigger-eff", "category": "efficiency", "applied_in": "response"}); bad["measurement_duplicate_correction.json"] = (d, ["measurement.duplicate_correction"])
d = measurement(); d["extension"]["observable"]["normalization"]["kind"] = "luminosity"; bad["measurement_unknown_normalization.json"] = (d, ["vocab.unknown_term"])
d = measurement(); d["extension"]["observable"]["level"] = "instrument"; bad["measurement_unnamespaced_level.json"] = (d, ["vocab.unknown_term"])
d = copy.deepcopy(VALID["response.json"]); d["extension"]["applied_separately"] = ["efficiency"]; bad["response_double_counted.json"] = (d, ["response.double_counted"])
d = prediction(); d["extension"]["uncertainties"][0]["gaussian"] = True; bad["prediction_gaussian_envelope.json"] = (d, ["uncertainty.auto_gaussian"])
d = dataset(status="published", did="synthetic-collider:synthetic-pubshape-1"); d["status"] = ["unvalidated"]; bad["dataset_published_no_evidence.json"] = (d, ["dataset.values_without_provenance"])
d = dataset(did="synthetic-collider:angular-1"); d["status"] = ["unvalidated"]; bad["dataset_synthetic_unlabeled.json"] = (d, ["dataset.synthetic_unlabeled"])
d = dataset(); d["extension"]["data"]["values"] = [1.0, 2.0]; bad["dataset_binned_length.json"] = (d, ["binned.length"])
d = statres("bayesian"); del d["extension"]["priors"]; bad["statres_bayesian_no_priors.json"] = (d, ["stats.paradigm_incomplete"])
d = statres("frequentist"); d["extension"]["priors"] = [{"parameter": "mu", "form": "flat"}]; bad["statres_frequentist_with_priors.json"] = (d, ["stats.paradigm_mislabeled"])
d = prediction(); d["inputs"] = [{"ref": "x.json", "status": ["asimov"]}]; bad["status_not_propagated.json"] = (d, ["status.not_propagated"])
d = copy.deepcopy(VALID["computational_run.json"]); d["extension"]["exit_status"] = 3; bad["run_failed_unlabeled.json"] = (d, ["status.failed_unlabeled"])
d = copy.deepcopy(VALID["ml_artifact.json"]); d["extension"]["splits"] = {"grouping_key": ""}; bad["ml_no_grouping.json"] = (d, ["ml.no_grouping"])
d = statres_v11("bayesian", convergence={"rhat": {"mu": 1.05}}); bad["statres_bayesian_rhat_mismatch.json"] = (d, ["stats.convergence_mismatch"])
d = statres_v11("frequentist", significance={**SCAN, "global_p": 0.02, "trials_method": "look-elsewhere"}); bad["statres_trials_method_unknown.json"] = (d, ["schema.enum"])
d = theory(); del d["status"]; bad["envelope_missing_status.json"] = (d, ["schema.required"])
d = copy.deepcopy(VALID["response_parametrized.json"]); del d["extension"]["parametrization"]; bad["response_parametrized_missing.json"] = (d, ["response.parametrization_missing"])
d = measurement(ratio={"numerator": "a", "denominator": "b", "cancellations": [{"effect": "exposure", "treatment": "cancels"}]}); bad["measurement_ratio_no_correlation_model.json"] = (d, ["schema.required"])


# Valid (no error) but not usable as a final result: the validator reports these codes as `unresolved`.
UNRESOLVED = {"statres_scan_no_global.json": (statres_v11("frequentist", significance=dict(SCAN)), ["stats.lee_missing"])}


def main() -> None:
    for sub in ("valid", "invalid", "unresolved"):
        (OUT / sub).mkdir(parents=True, exist_ok=True)
        for f in (OUT / sub).glob("*.json"):
            f.unlink()
    cases = {"note": SYN, "valid": sorted(VALID), "invalid": {}}
    for name, doc in VALID.items():
        (OUT / "valid" / name).write_text(json.dumps(doc, indent=1) + "\n")
    for name, (doc, codes) in bad.items():
        (OUT / "invalid" / name).write_text(json.dumps(doc, indent=1) + "\n")
        cases["invalid"][name] = codes
    cases["unresolved"] = {}
    for name, (doc, codes) in UNRESOLVED.items():
        (OUT / "unresolved" / name).write_text(json.dumps(doc, indent=1) + "\n")
        cases["unresolved"][name] = codes
    (OUT / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(f"{len(VALID)} valid, {len(bad)} invalid, {len(UNRESOLVED)} unresolved fixtures")


if __name__ == "__main__":
    main()
