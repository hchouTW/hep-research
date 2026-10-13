#!/usr/bin/env python3
"""Regenerate contract fixtures under contracts/fixtures/. All values are SYNTHETIC placeholders
chosen to exercise structure; none is a measurement, prediction, or experiment parameter.

Usage: python3 tests/contracts/make_fixtures.py   (rewrites the fixture files and cases.json)
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
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
    ext = {"estimand": "SYNTHETIC: placeholder differential cross section in cos_theta at particle level",
           "observable": observable(kind), "species_or_process": "synthetic",
           "period": {"start": "synthetic-period-1", "end": "synthetic-period-1"},
           "selections": [{"name": "two-muons", "definition": "placeholder", "conditional_denominator": "all events"}],
           "backgrounds": [{"name": "placeholder-bkg", "estimator": "sideband", "control_region": "synthetic sideband",
                            "closure": "synthetic validation region"}],
           "corrections": [{"effect_id": "trigger-eff", "category": "efficiency", "applied_in": "estimator"}],
           "systematics": [{"name": "energy-scale", "source": "calibration", "effect": "migration", "applied_via": "migration"}],
           "blinding": {"blinded": False}}
    ext.update(extra)
    return envelope("measurement-spec", ext, "hep-analysis")


def measurement_v26(mutate=None, status=None):
    """measurement-spec under the 2.6.0 rules (an estimand, factorized efficiencies, a blinding mask); `mutate` edits
    the document in place to make one defect."""
    from contracts import CONTRACTS_VERSION
    d = measurement(corrections=[{"effect_id": "trigger-eff", "category": "trigger_efficiency", "applied_in": "estimator"},
                                 {"effect_id": "selection-eff", "category": "selection_efficiency", "applied_in": "estimator"}],
                    blinding={"blinded": True, "mask": {"intervals": [{"variable": "cos_theta", "low": 0.5, "high": 1.0}]}})
    d.update(contract_version=CONTRACTS_VERSION, versions={"plugin": "0.6.17", "contracts": CONTRACTS_VERSION, "profiles": {}})
    if status:
        d["status"] = list(status)
    if mutate:
        mutate(d, d["extension"])
    return d


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


def communication_rich(**extra):
    """Traceability format (communication:traceability-v1): observed claim C1 on input A, synthetic illustration C2 on
    input B, comparison C3 on both; the envelope keeps the sticky caveats only, each claim its own provenance."""
    from contracts import CONTRACTS_VERSION
    from contracts.communication import claim_digest, evidence_fingerprint
    inputs = [{"ref": "artifacts/obs.json", "artifact_type": "statistical-result", "artifact_id": "fixture-synthetic-obs",
               "sha256": "a" * 64, "status": ["observed"]},
              {"ref": "artifacts/syn.json", "artifact_type": "prediction", "artifact_id": "fixture-synthetic-syn",
               "sha256": "b" * 64, "status": ["synthetic", "unvalidated"]}]

    def edge(eid, target, role="supports", usage="used-in-claim"):
        return {"id": eid, "target_kind": "artifact", "target": target, "locator": "extension.results (fixture)", "role": role, "usage": usage}

    def claim(cid, text, ctype, status, edges):
        return {"id": cid, "text": text, "claim_type": ctype, "scope": {"text": "synthetic fixture; no physics"},
                "status": status, "evidence": edges, "unresolved_inputs": []}
    claims = [claim("claim:C1", "The ratio is 1.02 +/- 0.05 (synthetic fixture).", "measurement", ["observed"],
                    [edge("ev:C1-a", "artifacts/obs.json")]),
              claim("claim:C2", "A synthetic illustration gives 0.98 (synthetic fixture).", "illustration", ["synthetic", "unvalidated"],
                    [edge("ev:C2-b", "artifacts/syn.json")]),
              claim("claim:C3", "The synthetic illustration is compatible with the ratio (synthetic fixture).", "comparison",
                    ["synthetic", "unvalidated"], [edge("ev:C3-a", "artifacts/obs.json"), edge("ev:C3-b", "artifacts/syn.json", "qualifies")])]
    doc = envelope("communication", {}, "research-communication", contract_version=CONTRACTS_VERSION,
                   versions={"plugin": "0.6.12", "contracts": CONTRACTS_VERSION, "profiles": {}},
                   required_capabilities=["communication:traceability-v1"], inputs=inputs)
    for c in claims:
        c["assessment"] = {"verdict": "supported", "rationale": "fixture: the value is read from the named artifact field",
                           "evidence_ids": [e["id"] for e in c["evidence"]], "assessor": {"identity": "fixture", "role": "author"},
                           "date": "2026-10-12", "claim_digest": claim_digest(c),
                           "evidence_fingerprints": {e["id"]: evidence_fingerprint(e, doc) for e in c["evidence"]}, "currency": "current"}
    doc["extension"] = {"traceability_version": "1.0.0", "scope": {"occurrences": True, "sources": False},
                        "documents": [{"id": "doc:paper", "path": "paper/main.md", "format": "markdown", "audience": "fixture", "purpose": "main text"}],
                        "claims": claims,
                        "occurrences": [{"id": "occ:1", "claim_id": "claim:C1", "document_id": "doc:paper", "locator": "section:abstract",
                                         "passage": "The ratio is 1.02 +/- 0.05.", "state": "mapped"}],
                        "sources_read": [], "evidence_ledgers": [], "limitations": ["synthetic fixture"]}
    doc["extension"].update(extra)
    return doc


SCAN = {"local_p": 1.0e-3, "local_z": 3.09, "scan": {"parameters": ["mass"], "ranges": [[100.0, 200.0]]}}


def response_v24(**extra):
    """Response under the 2.4.0 rules (controlled correction vocabulary, inline matrix, declared use); converts with
    contracts.response_adapter into core/stats/validate_response.py input."""
    from contracts import CONTRACTS_VERSION
    ext = {"truth_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
           "reco_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
           "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
           "inefficiency": "inside_matrix", "acceptance": "outside_matrix", "includes": ["migration", "efficiency"],
           "applied_separately": ["acceptance", "luminosity"], "underflow_overflow": "not_represented",
           "intended_use": "forward_folding", "matrix": [[0.7, 0.1], [0.1, 0.6]],
           "conditions": "synthetic", "provenance": SYN, **extra}
    ext = {k: x for k, x in ext.items() if x is not None}  # extra key=None removes the field
    return envelope("response", ext, "detector-response", contract_version=CONTRACTS_VERSION,
                    versions={"plugin": "0.6.14", "contracts": CONTRACTS_VERSION, "profiles": {}})


def ml_v25(**extra):
    """ml-artifact under the 2.5.0 rules: grouped splits with a passed overlap check, structured weights, a probability
    output with a calibration validated on a held-out sample, a domain-shift check on a control sample, seeds."""
    from contracts import CONTRACTS_VERSION
    ext = {"task": "classification", "labels": ["sig", "bkg"], "features": ["x", "y"],
           "splits": {"grouping_key": "run_id", "manifest": "splits/manifest.json", "test_groups_disjoint": True,
                      "overlap_check": {"tool": "check_split_integrity.py", "result": "pass", "report": "splits/report.json"}},
           "training_domain": {"x": [0.0, 1.0], "y": [-1.0, 1.0]}, "preprocessing": [],
           "weights": {"source": "generator weights (synthetic)", "negative_weight_treatment": "none-present",
                       "class_balancing": "inverse class frequency", "used_in": ["loss", "metrics"]},
           "model_hash": "sha256:" + "0" * 64, "output_semantics": "probability",
           "calibration": {"method": "temperature", "fit_sample": "val",
                           "validation": {"metric": "ece", "sample": "test", "before": 0.05, "after": 0.01}},
           "domain_shift": {"control_sample": "synthetic control region", "method": "score-shape comparison",
                            "result": {"ks_p": 0.4}, "status": "checked"},
           "environment": {"torch_version": "synthetic", "device": "cpu", "precision": "fp32", "seeds": {"torch": 1, "split": 2}},
           "downstream_validation": [{"metric": "working-point efficiency in the synthetic signal region"}], **extra}
    ext = {k: x for k, x in ext.items() if x is not None}  # extra key=None removes the field
    return envelope("ml-artifact", ext, "physics-ml", contract_version=CONTRACTS_VERSION,
                    versions={"plugin": "0.6.16", "contracts": CONTRACTS_VERSION, "profiles": {}})


def ml_v25_splits(**splits):
    return ml_v25(splits={"grouping_key": "run_id", "overlap_check": {"tool": "check_split_integrity.py", "result": "pass"},
                          **splits})


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
    "communication_traceability.json": communication_rich(),
    "response_v24.json": response_v24(),
    "ml_artifact_v25.json": ml_v25(),
    "measurement_v26.json": measurement_v26(),
}

bad = {}
d = theory(); d["extension"]["blinding"] = {"blinded": True}; bad["theory_experiment_field.json"] = (d, ["theory.experiment_field"])
d = theory(); d["bindings"]["experiments"] = [{"profile": "experiment:synthetic-collider", "version": "1.0.0"}]; bad["theory_experiment_binding.json"] = (d, ["theory.experiment_binding"])
d = measurement(); d["extension"]["corrections"].append({"effect_id": "trigger-eff", "category": "efficiency", "applied_in": "response"}); bad["measurement_duplicate_correction.json"] = (d, ["measurement.duplicate_correction"])
d = measurement(); d["extension"]["observable"]["normalization"]["kind"] = "luminosity"; bad["measurement_unknown_normalization.json"] = (d, ["vocab.unknown_term"])
d = measurement(); d["extension"]["observable"]["level"] = "instrument"; bad["measurement_unnamespaced_level.json"] = (d, ["vocab.unknown_term"])
d = copy.deepcopy(VALID["response.json"]); d["extension"]["applied_separately"] = ["efficiency"]; bad["response_double_counted.json"] = (d, ["response.double_counted"])
bad["response_trigger_efficiency_twice.json"] = (response_v24(applied_separately=["trigger_efficiency"]), ["response.double_counted"])
bad["response_matrix_missing.json"] = (response_v24(matrix=None), ["response.matrix_missing"])
bad["response_joint_counts_inefficiency_inside.json"] = (response_v24(normalization="joint_counts"), ["response.normalization_inconsistent"])
d = prediction(); d["extension"]["uncertainties"][0]["gaussian"] = True; bad["prediction_gaussian_envelope.json"] = (d, ["uncertainty.auto_gaussian"])
d = dataset(status="published", did="synthetic-collider:synthetic-pubshape-1"); d["status"] = ["unvalidated"]; bad["dataset_published_no_evidence.json"] = (d, ["dataset.values_without_provenance"])
d = dataset(did="synthetic-collider:angular-1"); d["status"] = ["unvalidated"]; bad["dataset_synthetic_unlabeled.json"] = (d, ["dataset.synthetic_unlabeled"])
d = dataset(); d["extension"]["data"]["values"] = [1.0, 2.0]; bad["dataset_binned_length.json"] = (d, ["binned.length"])
d = statres("bayesian"); del d["extension"]["priors"]; bad["statres_bayesian_no_priors.json"] = (d, ["stats.paradigm_incomplete"])
d = statres("frequentist"); d["extension"]["priors"] = [{"parameter": "mu", "form": "flat"}]; bad["statres_frequentist_with_priors.json"] = (d, ["stats.paradigm_mislabeled"])
d = prediction(); d["inputs"] = [{"ref": "x.json", "status": ["asimov"]}]; bad["status_not_propagated.json"] = (d, ["status.not_propagated"])
d = copy.deepcopy(VALID["computational_run.json"]); d["extension"]["exit_status"] = 3; bad["run_failed_unlabeled.json"] = (d, ["status.failed_unlabeled"])
d = copy.deepcopy(VALID["ml_artifact.json"]); d["extension"]["splits"] = {"grouping_key": ""}; bad["ml_no_grouping.json"] = (d, ["ml.no_grouping"])
bad["ml_blank_grouping_key.json"] = (ml_v25_splits(grouping_key="  "), ["ml.no_grouping"])
bad["ml_empty_model_hash.json"] = (ml_v25(model_hash=" "), ["ml.model_hash_missing"])
bad["ml_empty_labels_features.json"] = (ml_v25(labels=[], features=[], training_domain={}), ["ml.labels_missing", "ml.features_missing"])
bad["ml_domain_unknown_feature.json"] = (ml_v25(training_domain={"x": [0.0, 1.0], "z": [0.0, 1.0]}), ["ml.training_domain_unknown_feature"])
bad["ml_domain_inverted_range.json"] = (ml_v25(training_domain={"x": [1.0, 0.0]}), ["ml.training_domain_range"])
bad["ml_split_overlap_failed.json"] = (ml_v25_splits(overlap_check={"tool": "check_split_integrity.py", "result": "fail"}), ["ml.split_overlap"])
bad["ml_calibration_missing.json"] = (ml_v25(calibration=None), ["ml.calibration_missing"])
bad["ml_calibration_on_fit_sample.json"] = (ml_v25(calibration={"method": "temperature", "fit_sample": "val",
                                                                "validation": {"metric": "ece", "sample": "val", "after": 0.01}}),
                                            ["ml.calibration_on_fit_sample"])
d = statres_v11("bayesian", convergence={"rhat": {"mu": 1.05}}); bad["statres_bayesian_rhat_mismatch.json"] = (d, ["stats.convergence_mismatch"])
d = statres_v11("frequentist", significance={**SCAN, "global_p": 0.02, "trials_method": "look-elsewhere"}); bad["statres_trials_method_unknown.json"] = (d, ["schema.enum"])
d = theory(); del d["status"]; bad["envelope_missing_status.json"] = (d, ["schema.required"])
d = copy.deepcopy(VALID["response_parametrized.json"]); del d["extension"]["parametrization"]; bad["response_parametrized_missing.json"] = (d, ["response.parametrization_missing"])
d = measurement(ratio={"numerator": "a", "denominator": "b", "cancellations": [{"effect": "exposure", "treatment": "cancels"}]}); bad["measurement_ratio_no_correlation_model.json"] = (d, ["schema.required"])
d = copy.deepcopy(VALID["communication.json"]); d["extension"]["claims"] = [{"text": 42, "result_ref": None, "status": {"a": 1}}]; bad["communication_bad_types.json"] = (d, ["schema.type"])
d = communication_rich(); d["required_capabilities"] = []; bad["communication_traceability_without_capability.json"] = (d, ["communication.capability_missing"])
d = communication_rich(); d["extension"]["claims"][1]["status"] = ["observed"]; d["extension"]["claims"][1]["assessment"]["currency"] = "stale"; bad["communication_claim_status_upgraded.json"] = (d, ["communication.status_upgraded"])
d = communication_rich(); d["extension"]["claims"][2]["status"] = ["observed", "synthetic", "unvalidated"]; d["extension"]["claims"][2]["assessment"]["currency"] = "stale"; bad["communication_claim_status_conflict.json"] = (d, ["communication.claim_status_conflict"])


# measurement-spec rules of contracts 2.6.0 (hep-analysis audit): one invalid fixture per rule
MEAS_INVALID = {
    "estimand_missing": (lambda d, e: e.pop("estimand"), "measurement.estimand_missing"),
    "estimand_not_a_sentence": (lambda d, e: e.update(estimand="flux"), "measurement.estimand_not_a_sentence"),
    "variable_incomplete": (lambda d, e: e["observable"]["variables"][0].pop("edges"), "measurement.variable_incomplete"),
    "phase_space_missing": (lambda d, e: e["observable"].pop("phase_space"), "measurement.phase_space_missing"),
    "frame_missing": (lambda d, e: e["observable"].pop("frame"), "measurement.frame_missing"),
    "selections_empty": (lambda d, e: e.update(selections=[]), "measurement.selections_empty"),
    "denominator_blank": (lambda d, e: e["selections"][0].update(conditional_denominator=" "), "measurement.denominator_blank"),
    "unknown_not_listed": (lambda d, e: e["selections"][0].update(conditional_denominator="unknown"),
                           "measurement.unresolved_not_listed"),
    "backgrounds_empty": (lambda d, e: e.update(backgrounds=[]), "measurement.backgrounds_empty"),
    "background_estimator_missing": (lambda d, e: e["backgrounds"][0].update(estimator=""),
                                     "measurement.background_estimator_missing"),
    "background_constraint_missing": (lambda d, e: e["backgrounds"][0].pop("control_region"),
                                      "measurement.background_constraint_missing"),
    "correction_case_variant": (lambda d, e: e["corrections"].append({"effect_id": "Trigger_Eff", "category": "migration",
                                                                      "applied_in": "unfolding"}),
                                "measurement.duplicate_correction"),
    "category_repeated": (lambda d, e: e["corrections"][1].update(category="trigger_efficiency"),
                          "measurement.correction_category_repeated"),
    "bare_efficiency_with_factor": (lambda d, e: e["corrections"][1].update(category="efficiency"),
                                    "measurement.correction_category_repeated"),
    "unknown_category": (lambda d, e: e["corrections"][1].update(category="magic"),
                         "measurement.unknown_correction_category"),
    "luminosity_twice": (lambda d, e: e["corrections"].append({"effect_id": "lumi", "category": "luminosity",
                                                               "applied_in": "estimator"}),
                         "measurement.normalization_double_counted"),
    "included_and_applied": (lambda d, e: e["observable"].update(included_corrections=["trigger-eff"]),
                             "measurement.correction_in_observable_and_chain"),
    "zero_normalization": (lambda d, e: e["observable"]["normalization"].update(value=0), "measurement.zero_value"),
    "zero_correction": (lambda d, e: e["corrections"][0].update(value=0), "measurement.zero_value"),
    "shape_only_value": (lambda d, e: e["observable"].update(normalization={"kind": "shape-only", "value": 3.2}),
                         "measurement.shape_only_value"),
    "systematics_empty": (lambda d, e: e.update(systematics=[]), "measurement.systematics_empty"),
    "applied_via_blank": (lambda d, e: e["systematics"][0].update(applied_via=""), "measurement.applied_via_missing"),
    "duplicate_systematic": (lambda d, e: e["systematics"].append(dict(e["systematics"][0], name="Energy_Scale")),
                             "measurement.duplicate_systematic"),
    "blinded_no_mask": (lambda d, e: e["blinding"].pop("mask"), "measurement.blinding_mask_missing"),
    "blinded_observed": (lambda d, e: d.update(status=["observed"]), "measurement.blinded_observed"),
    "ratio_block_missing": (lambda d, e: e["observable"].update(quantity="ratio"), "measurement.ratio_block_missing"),
    "ratio_self": (lambda d, e: e.update(ratio={"numerator": "species-A", "denominator": "Species_A", "cancellations": [
        {"effect": "exposure", "treatment": "cancels", "correlation_model": "same", "verification": "by construction"}]}),
                   "measurement.ratio_self"),
    "ratio_cancellations_empty": (lambda d, e: e.update(ratio={"numerator": "a", "denominator": "b", "cancellations": []}),
                                  "measurement.ratio_cancellations_empty"),
    "period_reversed": (lambda d, e: e.update(period={"start": "2020-01-01", "end": "2019-06-30"}),
                        "measurement.period_reversed"),
    "misspelled_key": (lambda d, e: e["selections"][0].update(conditonal_denominator="all"), "measurement.misspelled_key"),
}
for _name, (_fn, _code) in MEAS_INVALID.items():
    bad[f"measurement_v26_{_name}.json"] = (measurement_v26(_fn), [_code])

# Valid (no error) but not usable as a final result: the validator reports these codes as `unresolved`.
UNRESOLVED = {"statres_scan_no_global.json": (statres_v11("frequentist", significance=dict(SCAN)), ["stats.lee_missing"])}
d = communication_rich(); d["extension"]["claims"][0]["text"] = "The ratio establishes a deviation (synthetic fixture)."; d["extension"]["claims"][0]["assessment"]["currency"] = "stale"
d["extension"]["claims"][1]["evidence"] = []; del d["extension"]["claims"][1]["assessment"]; d["extension"]["claims"][1]["unresolved_inputs"] = ["the illustration artifact is not yet written"]
UNRESOLVED["communication_traceability_pending.json"] = (d, ["communication.assessment_stale", "communication.assessment_missing"])
UNRESOLVED["ml_domain_shift_missing.json"] = (ml_v25(domain_shift=None), ["ml.domain_shift_missing"])
UNRESOLVED["measurement_v26_closure_missing.json"] = (measurement_v26(lambda d, e: e["backgrounds"][0].pop("closure")),
                                                     ["measurement.background_closure_missing"])
UNRESOLVED["measurement_v26_input_listed.json"] = (
    measurement_v26(lambda d, e: (e.update(period="not-provided"), d.update(unresolved_inputs=["period: not provided yet"]))),
    ["measurement.input_unresolved"])
UNRESOLVED["ml_split_overlap_not_run.json"] = (ml_v25_splits(overlap_check={"tool": "check_split_integrity.py", "result": "not-run"}),
                                               ["ml.split_overlap_not_run"])


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
