#!/usr/bin/env python3
"""Regenerate contract fixtures under contracts/fixtures/. All values are SYNTHETIC placeholders
chosen to exercise structure; none is a measurement, prediction, or experiment parameter.

Usage: python3 tests/contracts/make_fixtures.py   (rewrites the fixture files and cases.json)
"""
from __future__ import annotations

import copy
import hashlib
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
    return envelope("measurement-spec", ext, "hep-measurement")


CONVENTIONS_ALL = {"unit_system": "natural units (synthetic)", "hbar_c_one": True, "metric_signature": "+---",
                   "coupling_normalization": "not-applicable", "renormalization_scheme": "not-applicable",
                   "scales": "not-applicable", "energy_variable": "sqrt_s", "frame": "center-of-mass",
                   "angle_definition": "not-applicable", "spin_treatment": "not-applicable",
                   "mass_approximation": "not-applicable"}
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
           "assumptions": ["placeholder assumption"], "conventions": dict(CONVENTIONS_ALL),
           "order": "tree-level", "parameters": {"p": "placeholder"}, "scales": "not-applicable",
           "derivation_status": "not-derived", "validity_domain": {"note": "placeholder"},
           "checks_run": [], "checks_not_run": ["all (fixture)"]}
    ext.update(extra)
    return envelope("theory-spec", ext, "hep-theory", status=("unvalidated",))


def prediction(**extra):
    ext = {"observable": observable(), "parameter_point": {"p": 1}, "representation": "numerical",
           "values": {"edges": [-1.0, -0.5, 0.0, 0.5, 1.0], "values": [1.0, 1.0, 1.0, 1.0], "unit": "pb"},
           "uncertainties": [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown", "prescription": "3-point"}],
           "allowed_transformations": ["forward-fold"]}
    ext.update(extra)
    return envelope("prediction", ext, "hep-theory")


def _v26(doc):
    """Stamp a builder's document at the contract version from which the theory rules are native (2.6.0)."""
    from contracts.validate import THEORY_SEMANTICS_FROM
    doc["contract_version"] = THEORY_SEMANTICS_FROM
    doc["versions"] = {"plugin": "0.6.17", "contracts": THEORY_SEMANTICS_FROM, "profiles": {}}
    return doc


def theory_v26(**extra):
    """theory-spec under the 2.6.0 rules: all core convention keys, a perturbative argument with its order, a check
    run with a result from check_results and its tolerance, a validity domain, what was neglected."""
    ext = {"derivation_status": "perturbative-argument", "order": "tree-level (synthetic)",
           "checks_run": [{"name": "units", "result": "pass", "tolerance": "exact"}],
           "validity_domain": {"sqrt_s": "placeholder range"}, "neglected": ["placeholder higher orders"], **extra}
    ext = {k: x for k, x in ext.items() if x is not None}  # extra key=None removes the field
    doc = theory(**ext)
    doc["extension"] = {k: x for k, x in doc["extension"].items() if x is not None}
    doc["artifact_id"] = "fixture-synthetic-theory-spec-v26"
    return _v26(doc)


def prediction_v26(**extra):
    """prediction under the 2.6.0 rules: linked to its theory spec, a scale envelope with its prescription and a
    [min, max] pair, a truncation estimate with its method."""
    ext = {"theory_spec_ref": "artifacts/theory_spec.json",
           "uncertainties": [{"name": "scale", "kind": "scale-envelope", "correlation": "unknown", "prescription": "3-point",
                              "values": [0.9, 1.1]},
                             {"name": "missing higher orders", "kind": "truncation", "correlation": "unknown",
                              "method": "last-term"}], **extra}
    doc = prediction(**ext)
    doc["extension"] = {k: x for k, x in doc["extension"].items() if x is not None}
    doc["artifact_id"] = "fixture-synthetic-prediction-v26"
    return _v26(doc)


def envelope_unc(**kw):
    u = {"name": "scale", "kind": "scale-envelope", "correlation": "unknown", "prescription": "3-point", "values": [0.9, 1.1]}
    u.update(kw)
    return [{k: x for k, x in u.items() if x is not None}]


LINKED_SPEC = [{"ref": "artifacts/theory_spec.json", "artifact_type": "theory-spec", "status": ["validated-in-scope"]}]


def dataset(status="synthetic", did="synthetic-collider:synthetic-angular-1", **extra):
    ext = {"dataset_id": did, "source_evidence_ids": [], "observable": observable(),
           "data": {"edges": [-1.0, -0.5, 0.0, 0.5, 1.0], "values": [1.0, 2.0, 3.0, 4.0], "unit": "pb",
                    "uncertainties": [{"name": "stat", "kind": "statistical", "values": [0.1, 0.1, 0.1, 0.1], "correlation": "uncorrelated"}]},
           "covariance": {"status": "absent"}, "status": status, "experiment_profile": "experiment:synthetic-collider"}
    ext.update(extra)
    return envelope("dataset-record", ext, "hep-measurement")


SIM_RUN = [{"ref": "artifacts/g4-run.computational-run.json", "artifact_type": "computational-run",
            "status": ["unvalidated"], "sha256": "0" * 64}]


def simulated(**kw):
    """3.2.0: a detector-level table derived from a recorded (here placeholder) simulation run."""
    d = dataset(status="simulated", did="synthetic-collider:synthetic-simulated-resolution-1",
                observable=observable(level="detector"), experiment_profile=None)
    d["extension"].pop("experiment_profile")
    d["inputs"] = [dict(i) for i in SIM_RUN]
    d.update(kw)
    return d


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
    doc = envelope("communication", {}, "hep-authoring", contract_version=CONTRACTS_VERSION,
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


def literature_record(**extra):
    """literature-record (contracts 2.13.0): the record manage_literature.py imports, in the envelope. One source with a
    DOI and an arXiv id read at abstract level, one claim citing it, one search; all SYNTHETIC placeholders."""
    from contracts import CONTRACTS_VERSION
    src = {"id": "fixture:S01", "title": "SYNTHETIC fixture paper", "authors": "Fixture et al.", "year": 2026, "tier": 2,
           "verification_level": "abstract+metadata", "verification_date": "2026-10-12", "formal_status": "published",
           "supersedes": [], "superseded_by": [], "verification_limitations": "fixture", "citation_key": "Fixture:2026abc",
           "identifiers": {"doi": "10.0000/fixture.1", "arxiv": "2610.00001", "arxiv_version": "v1", "inspire": None},
           "read_events": [{"level": "abstract+metadata", "date": "2026-10-12", "locators": [], "imported_from": "in.json"}],
           "versions": [{"version": "v1", "date": "2026-10-12", "imported_from": "in.json"}], "notices": [],
           "status": "as-imported", "imported_from": "in.json"}
    claim = {"id": "fixture:C01", "claim": "the fixture paper reports a placeholder value", "claim_types": ["published_result"],
             "source_ids": ["fixture:S01"], "location": "abstract", "scope": {"text": "fixture"},
             "verification_strength": "abstract+metadata", "numeric_quotation_allowed": True, "last_reviewed": "2026-10-12"}
    ext = {"record_version": "1.0.0", "created": "2026-10-19",
           "imported": [{"path": "in.json", "sha256": hashlib.sha256(b"SYNTHETIC literature input").hexdigest(), "date": "2026-10-19",
                         "counts": {"sources": 1, "claims": 1, "searches": 1, "notices": 0}}],
           "sources": {"fixture:S01": src}, "claims": {"fixture:C01": claim},
           "searches": [{"database": "INSPIRE-HEP", "query": "t fixture", "date": "2026-10-12", "export_count": 1, "imported_from": "in.json"}],
           "notices": [], "relations": [], "proposed_merges": [], "flags": [],
           "verification": {"online": "not-performed", "note": "SYNTHETIC fixture"}}
    ext.update(extra)
    return envelope("literature-record", ext, "hep-citations", status=("synthetic", "user-supplied"),
                    contract_version=CONTRACTS_VERSION,
                    versions={"plugin": "0.15.0", "contracts": CONTRACTS_VERSION, "profiles": {}})


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
    return envelope("response", ext, "hep-detector", contract_version=CONTRACTS_VERSION,
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
                       "class_balancing": "inverse class frequency", "used_in": ["loss", "metrics"],
                       "training": {"negative_weight_treatment": "none-present", "class_balancing": "inverse class frequency"},
                       "evaluation": {"treatment": "physics weights, unmodified"}},
           "model_hash": "sha256:" + "0" * 64, "output_semantics": "probability",
           "calibration": {"method": "temperature", "fit_sample": "val",
                           "validation": {"metric": "ece", "sample": "test", "before": 0.05, "after": 0.01}},
           "domain_shift": {"control_sample": "synthetic control region", "method": "score-shape comparison",
                            "result": {"ks_p": 0.4}, "status": "checked", "outcome": "no-shift"},
           "environment": {"torch_version": "synthetic", "device": "cpu", "precision": "fp32", "seeds": {"torch": 1, "split": 2}},
           "downstream_validation": [{"metric": "working-point-efficiency",
                                      "quantity_affected": "signal efficiency in the synthetic signal region",
                                      "value": 0.52, "uncertainty": 0.02, "criterion": ">= 0.5", "passed": True,
                                      "ref": "synthetic"}], **extra}
    ext = {k: x for k, x in ext.items() if x is not None}  # extra key=None removes the field
    return envelope("ml-artifact", ext, "hep-ml", contract_version=CONTRACTS_VERSION,
                    versions={"plugin": "0.6.16", "contracts": CONTRACTS_VERSION, "profiles": {}})


def ml_v25_splits(**splits):
    return ml_v25(splits={"grouping_key": "run_id", "overlap_check": {"tool": "check_split_integrity.py", "result": "pass"},
                          **splits})


def statres_v26(**extra):
    """statistical-result under the 2.6.0 hardening rules: toy-calibrated profile limit with seeds, toy coverage whose
    interval matches its counts, expected bands, z consistent with p, a well-formed model hash."""
    from contracts import CONTRACTS_VERSION
    ext = {"paradigm": "frequentist", "likelihood": {"form": "poisson (synthetic)", "backend": "core.stats.likelihood_limits",
                                                      "model_sha256": "0" * 64},
           "parameters_of_interest": ["mu"], "nuisances": [], "fit_status": "converged",
           "test_statistic": "q_mu", "construction": "toy-calibrated-profile",
           "coverage": {"check": "toys", "method": "seeded toys of the full procedure (synthetic)", "n_toys": 1000,
                        "coverage": 0.951, "interval": [0.944, 0.957], "cl": 0.95},
           "seeds": {"toys": 1, "coverage": 2},
           "expected": {"median": 1.2, "band_1sigma": [0.9, 1.7], "band_2sigma": [0.7, 2.4], "method": "toys"},
           "significance": {"local_p": 0.3, "local_z": 0.5244},
           "goodness_of_fit": {"statistic": "saturated-deviance", "p_value": 0.4, "calibration": "toys", "n_toys": 1000},
           "results": {"mu_95": 2.1, "cl": 0.95, "p0": 0.3}, **extra}
    ext = {k: x for k, x in ext.items() if x is not None}  # extra key=None removes the field
    return envelope("statistical-result", ext, "hep-statistics", contract_version=CONTRACTS_VERSION,
                    versions={"plugin": "0.6.17", "contracts": CONTRACTS_VERSION, "profiles": {}},
                    required_capabilities=["stats:result-semantics"])


def statres_v26_bayes(**extra):
    """Bayesian statistical-result under the 2.6.0 rules: a proper prior on the POI, chains recorded, ESS above floor."""
    ext = {"paradigm": "bayesian", "priors": [{"parameter": "mu", "form": "uniform(0, 10)"}],
           "sampler": {"name": "metropolis (synthetic)", "chains": 4, "draws": 4000},
           "convergence": {"rhat": 1.002, "ess_bulk": 3000, "ess_tail": 2500}, "test_statistic": None,
           "construction": None, "coverage": None, "seeds": {"chains": 7}, "expected": None, "significance": None,
           "goodness_of_fit": None, "results": {"mu_median": 1.1}, **extra}
    return statres_v26(**ext)


VALID = {
    "statres_v26.json": statres_v26(),
    "statres_v26_bayesian.json": statres_v26_bayes(),
    "measurement_collider.json": measurement(),
    "measurement_exposure.json": measurement("exposure", observable=observable("exposure", level="detector", quantity="differential-flux", unit="m^-2 sr^-1 s^-1 GV^-1", variables=[{"name": "rigidity", "unit": "GV", "edges": [1, 2, 4]}])),
    "measurement_protons_on_target.json": measurement("protons-on-target", observable=observable("protons-on-target", level="detector", quantity="event-count", unit="1")),
    "measurement_target_exposure.json": measurement("target-exposure", observable=observable("target-exposure", level="detector", quantity="rate", unit="tonne^-1 yr^-1")),
    "response.json": envelope("response", {"truth_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
                                           "reco_axis": {"name": "cos_theta", "unit": "1", "edges": [-1, 0, 1]},
                                           "orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
                                           "inefficiency": "inside_matrix", "acceptance": "inside_matrix",
                                           "includes": ["efficiency", "acceptance"], "applied_separately": [],
                                           "conditions": "synthetic", "provenance": SYN}, "hep-detector"),
    "response_parametrized.json": envelope("response", {"form": "parametrized", "truth_axis": "not-applicable", "reco_axis": "not-applicable",
                                                        "orientation": "rows_reco_cols_truth", "normalization": "unnormalized",
                                                        "inefficiency": "inside_matrix", "acceptance": "inside_matrix", "includes": ["efficiency"],
                                                        "parametrization": {"variables": ["pt"], "function_ref": "synthetic-eff.json", "validity_range": {"pt": [10, 1000]}},
                                                        "conditions": "synthetic", "provenance": SYN}, "hep-detector"),
    "measurement_ratio.json": measurement("exposure", observable=observable("exposure", level="detector", quantity="ratio", unit="1",
                                                                            variables=[{"name": "rigidity", "unit": "GV", "edges": [1, 2, 4]}]),
                                          ratio={"numerator": "species-A", "denominator": "species-B",
                                                 "cancellations": [{"effect": "exposure", "treatment": "cancels", "correlation_model": "identical exposure per period"}]}),
    "theory_spec.json": theory(),
    "prediction.json": prediction(),
    "dataset_record.json": dataset(),
    "dataset_simulated.json": simulated(),
    "comparison_spec.json": envelope("comparison-spec", {"dataset_bindings": ["synthetic-collider:synthetic-angular-1"],
                                                         "prediction_bindings": ["fixture-synthetic-prediction"],
                                                         "gate_result": {"comparable": True, "mismatches": []},
                                                         "transformations": [{"kind": "forward-fold", "owner": "hep-detector"}],
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
                                                 "preprocessing": [], "model_hash": "sha256:" + hashlib.sha256(b"SYNTHETIC fixture model").hexdigest(),
                                                 "downstream_validation": []}, "hep-ml"),
    "computational_run.json": envelope("computational-run", {"input_manifest": [{"path": "in.json", "sha256": "placeholder"}],
                                                             "tools": [{"name": "python", "version": "3.11"}], "commands": ["placeholder"],
                                                             "environment": {}, "seeds": {"toys": 1}, "tolerances": {}, "exit_status": 0,
                                                             "output_hashes": {}}, "hep-computing"),
    "communication.json": envelope("communication", {"claims": [{"text": "placeholder", "result_ref": "x.json", "status": "synthetic"}],
                                                     "sources_read": [{"id": "user:S1", "level": "full-text"}],
                                                     "limitations": ["fixture"]}, "hep-authoring"),
    "communication_traceability.json": communication_rich(),
    "literature_record.json": literature_record(),
    "response_v24.json": response_v24(),
    # contracts 2.8.0 response hardening (hep-detector audit): finite-MC statistics and correction space declared
    "response_v28.json": response_v24(intended_use="unfolding",
                                      mc_stat={"kind": "generated_counts", "events_per_truth_bin": [10000, 10000]},
                                      correction_space={"acceptance": {"space": "truth", "binned_in": "cos_theta"},
                                                        "luminosity": {"space": "global"}}),
    "ml_artifact_v25.json": ml_v25(),
    "theory_spec_v26.json": theory_v26(),
    "theory_spec_v26_asymptotic.json": theory_v26(derivation_status="asymptotic-argument", limit="m / sqrt(s) -> 0 (synthetic)"),
    "theory_spec_v26_analytic_checked.json": theory_v26(derivation_status="analytic-derivation"),
    "theory_spec_v26_inapplicable_listed.json": theory_v26(conventions={k: x for k, x in CONVENTIONS_ALL.items() if k != "frame"},
                                                          inapplicable=["frame"]),
    "theory_spec_v26_propagation.json": theory_v26(model={"id": "synthetic-diffusion-model", "description": "structural fixture",
                                                          "family": "cosmic-ray-propagation"},
                                                   degenerate_directions=["D0/L (synthetic)"]),
    "prediction_v26.json": prediction_v26(),
    "prediction_v26_validated_linked.json": _v26(dict(prediction_v26(), status=["validated-in-scope", "synthetic"],
                                                      inputs=LINKED_SPEC)),
    "prediction_v26_derivation_status.json": prediction_v26(theory_spec_ref=None, derivation_status="numerical-evidence"),
    "prediction_v26_binned_envelope.json": prediction_v26(uncertainties=envelope_unc(
        values=None, bounds={"lower": [0.9, 0.9, 0.9, 0.9], "upper": [1.1, 1.1, 1.1, 1.1]})),
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
bad["dataset_simulated_without_runs.json"] = (simulated(inputs=[]), ["dataset.simulated_without_runs"])
bad["dataset_simulated_observed.json"] = (simulated(status=["observed"]), ["dataset.simulated_observed", "dataset.simulated_unlabeled"])
d = simulated(); d["extension"]["observable"]["level"] = "unfolded"; bad["dataset_simulated_unfolded.json"] = (d, ["dataset.simulated_level"])
d = simulated(status=["validated-in-scope"]); d["inputs"][0]["status"] = []; bad["dataset_simulated_upgrade_unlinked.json"] = (d, ["dataset.simulated_upgrade_unlinked"])
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
# literature-record (contracts 2.13.0)
d = literature_record(record_version="2.0.0"); bad["literature_record_unknown_version.json"] = (d, ["schema.enum"])
d = literature_record(); d["extension"]["sources"]["fixture:S02"] = d["extension"]["sources"].pop("fixture:S01"); bad["literature_record_key_mismatch.json"] = (d, ["literature.source_key_mismatch"])
d = literature_record(); d["extension"]["claims"]["fixture:C01"]["source_ids"] = ["fixture:S99"]; bad["literature_record_unknown_source.json"] = (d, ["literature.ledger_invalid"])
d = literature_record(); del d["extension"]["verification"]; bad["literature_record_no_verification.json"] = (d, ["schema.required"])

# theory-spec and prediction rules of contracts 2.6.0 (hep-theory audit, THY-WP2.3)
bad["prediction_v26_observed.json"] = (_v26(dict(prediction_v26(), status=["observed"])), ["prediction.status_upgraded"])
bad["prediction_v26_validated_unlinked.json"] = (_v26(dict(prediction_v26(), status=["validated-in-scope", "synthetic"])),
                                                 ["prediction.status_upgraded"])
bad["prediction_v26_envelope_no_prescription.json"] = (prediction_v26(uncertainties=envelope_unc(prescription=None)),
                                                       ["prediction.envelope_prescription"])
bad["prediction_v26_envelope_inverted.json"] = (prediction_v26(uncertainties=envelope_unc(values=[1.1, 0.9])),
                                                ["prediction.envelope_prescription"])
bad["theory_v26_order_missing.json"] = (theory_v26(order=""), ["theory.order_missing"])
bad["theory_v26_limit_missing.json"] = (theory_v26(derivation_status="asymptotic-argument"), ["theory.limit_missing"])
bad["theory_v26_unchecked_formal_proof.json"] = (theory_v26(derivation_status="formal-proof", checks_run=[]),
                                                 ["theory.unchecked_strong_status"])
bad["theory_v26_check_result_vocab.json"] = (theory_v26(checks_run=[{"name": "units", "result": "looks fine"}]),
                                             ["theory.check_result_vocab"])
bad["theory_v26_validity_empty.json"] = (theory_v26(validity_domain={}), ["theory.validity_empty"])
bad["theory_v26_propagation_no_degeneracy.json"] = (theory_v26(model={"id": "synthetic-diffusion-model", "description": "structural fixture",
                                                                       "family": "cosmic-ray-propagation"}),
                                                    ["theory.degeneracy_missing"])

# Valid but reported with a warning (the rule is advisory): cases.json "warning".
WARNING = {"theory_v26_conventions_incomplete.json": (theory_v26(conventions={"hbar_c_one": True}), ["theory.conventions_incomplete"]),
           "prediction_v26_truncation_no_method.json": (prediction_v26(uncertainties=[
               {"name": "missing higher orders", "kind": "truncation", "correlation": "unknown"}]), ["prediction.truncation_method"])}


# measurement-spec rules of contracts 2.6.0 (hep-measurement audit): one invalid fixture per rule
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
# contracts 2.6.0 statistical-result hardening (STH-T1): one fixture per new error code
_COV = {"check": "toys", "method": "seeded toys (synthetic)", "n_toys": 1000, "coverage": 0.951, "cl": 0.95}
bad["statres_v26_coverage_cl_mismatch.json"] = (statres_v26(coverage={**_COV, "cl": 0.68, "coverage": 0.69}), ["stats.coverage_cl_mismatch"])
bad["statres_v26_coverage_interval_wide.json"] = (statres_v26(coverage={**_COV, "interval": [0.5, 0.99]}), ["stats.coverage_interval_inconsistent"])
bad["statres_v26_p_zero.json"] = (statres_v26(significance={"local_p": 0.0, "local_z": 8.0}), ["stats.p_zero_without_bound"])
bad["statres_v26_results_p_out_of_range.json"] = (statres_v26(results={"mu_95": 2.1, "cl": 0.95, "p0": 1.7}), ["stats.p_out_of_range"])
bad["statres_v26_z_p_inconsistent.json"] = (statres_v26(significance={"local_p": 0.5, "local_z": 5.0}), ["stats.z_p_inconsistent"])
bad["statres_v26_global_z_above_local.json"] = (statres_v26(significance={"local_p": 0.3, "local_z": 0.5244, "global_p": 0.4,
                                                                          "global_z": 0.9, "trials_method": "toys", "global_n_toys": 1000}),
                                                ["stats.global_z_above_local"])
bad["statres_v26_construction_statistic.json"] = (statres_v26(construction="feldman-cousins", test_statistic="q0"),
                                                  ["stats.construction_statistic_mismatch"])
bad["statres_v26_model_sha256_malformed.json"] = (statres_v26(likelihood={"form": "poisson (synthetic)", "backend": "core.stats",
                                                                          "model_sha256": "abc"}), ["stats.model_sha256_malformed"])


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
UNRESOLVED["prediction_v26_unlinked.json"] = (prediction_v26(theory_spec_ref=None), ["prediction.spec_unlinked"])
# contracts 2.6.0 statistical-result hardening (STH-T1): one fixture per new unresolved code
UNRESOLVED["statres_v26_coverage_toys_too_few.json"] = (statres_v26(coverage={**_COV, "n_toys": 50, "coverage": 0.96}),
                                                        ["stats.coverage_toys_too_few"])
UNRESOLVED["statres_v26_expected_missing.json"] = (statres_v26(expected={"median": 1.2, "method": "toys"}), ["stats.expected_bands_missing"])
UNRESOLVED["statres_v26_global_z_without_p.json"] = (statres_v26(significance={"local_p": 0.3, "local_z": 0.5244, "global_z": 0.1}),
                                                     ["stats.global_z_without_p"])
UNRESOLVED["statres_v26_seed_missing.json"] = (statres_v26(seeds=None), ["stats.seed_missing"])
UNRESOLVED["statres_v26_gof_toys_missing.json"] = (statres_v26(goodness_of_fit={"statistic": "saturated-deviance", "p_value": 0.4,
                                                                               "calibration": "toys"}), ["stats.gof_toys_missing"])
UNRESOLVED["statres_v26_bayes_propriety_unsupported.json"] = (
    statres_v26_bayes(priors=[{"parameter": "mu", "form": "uniform(0, inf)", "propriety": "yes"}]), ["stats.propriety_unsupported"])
UNRESOLVED["statres_v26_bayes_poi_prior_missing.json"] = (
    statres_v26_bayes(priors=[{"parameter": "bkg_norm", "form": "lognormal(0, 0.1)"}]), ["stats.poi_prior_missing"])
UNRESOLVED["statres_v26_bayes_ess_too_low.json"] = (statres_v26_bayes(convergence={"rhat": 1.0, "ess_bulk": 30, "ess_tail": 25}),
                                                    ["stats.ess_too_low"])
UNRESOLVED["statres_v26_bayes_chains_missing.json"] = (statres_v26_bayes(sampler={"name": "metropolis (synthetic)", "draws": 4000}),
                                                       ["stats.chains_missing"])


# contracts 2.8.0 ml-artifact rules (hep-ml audit, PML; CHECK-0.10.0 G-6): one committed fixture per rule family
# (structured downstream validation, output semantics and near-miss keys, task blocks, model-hash format, weights split,
# calibration outcome, domain-shift outcome, observable_source), named ml_v28_* / statres_v28_*.
def ml_v28(mutate):
    doc = ml_v25()
    mutate(doc["extension"])
    return doc


def _upd(**kw):
    return lambda e: e.update(kw)


def _sub(key, **kw):
    return lambda e: e[key].update(kw)


def _all(*fs):
    def f(e):
        for g in fs:
            g(e)
    return f


_ANOMALY = {"background_only": "score distribution on a background-only control sample (synthetic)",
            "signal_injection": "injected synthetic signal recovered at the expected rate (synthetic)"}
_REWEIGHT = {"closure": "reweighted source matches target in the input features (synthetic)",
             "prior_dependence": "weights stable under a changed source prior (synthetic)",
             "unmatched_events": "fraction of target events outside the source support (synthetic)"}
_SBI = {"coverage": {"method": "expected coverage (TARP)", "result": 0.68}, "handoff": "hep-statistics"}
_ML_DV = {"metric": "accuracy", "quantity_affected": "classifier", "value": 0.91, "criterion": ">= 0.9", "passed": True,
          "ref": "synthetic"}
_COVERAGE_DV = {"metric": "coverage", "quantity_affected": "mu 68% interval", "value": 0.40, "criterion": ">= 0.68",
                "passed": True, "ref": "synthetic"}
_NO_CAL = lambda e: e.pop("calibration")  # noqa: E731
VALID["ml_v28_unsupervised_anomaly.json"] = ml_v28(_upd(supervision="unsupervised", labels=[], anomaly_validation=_ANOMALY))
VALID["ml_v28_reweighting.json"] = ml_v28(_upd(task="reweighting", output_semantics="density-ratio",
                                               reweighting_validation=_REWEIGHT))
VALID["ml_v28_inference_sbi.json"] = ml_v28(_upd(task="inference", output_semantics="density-ratio", parameters=["theta"],
                                                 training_domain={"x": [0.0, 1.0], "y": [-1.0, 1.0], "theta": [0.0, 2.0]},
                                                 sbi_validation=_SBI))
_d = statres_v26(observable_source={"kind": "ml-score", "ml_artifact": "classifier"})
_d["inputs"] = [{"ref": "classifier", "artifact_type": "ml-artifact", "sha256": "0" * 64}]
VALID["statres_v28_observable_source_linked.json"] = _d
ML_V28_INVALID = {
    # structured downstream validation (WP1.1)
    "downstream_unstructured": (_upd(downstream_validation=["ROC AUC = 0.93 (synthetic)"]),
                                ["ml.downstream_unstructured", "ml.downstream_ml_only"]),
    "downstream_ml_only": (_upd(downstream_validation=[_ML_DV]), ["ml.downstream_ml_only"]),
    "downstream_passed_contradicts": (_upd(downstream_validation=[_COVERAGE_DV]), ["ml.downstream_passed_contradicts"]),
    # output semantics and near-miss keys (WP1.2)
    "output_semantics_misspelled": (lambda e: e.update(output_semantic=e.pop("output_semantics")), ["ml.misspelled_key"]),
    "calibration_misspelled": (lambda e: e.update(calibraton=e.pop("calibration")), ["ml.misspelled_key"]),
    "output_semantics_task_mismatch": (_all(_upd(output_semantics="regression-value"), _NO_CAL),
                                       ["ml.output_semantics_task_mismatch"]),
    # task blocks and claim checks (WP1.3)
    "surrogate_no_validation": (_all(_upd(task="surrogate", output_semantics="regression-value"), _NO_CAL),
                                ["ml.task_validation_missing"]),
    "generation_no_validation": (_all(_upd(task="generation", output_semantics="generated-sample"), _NO_CAL),
                                 ["ml.task_validation_missing"]),
    "inference_no_validation": (_upd(task="inference", output_semantics="density-ratio"), ["ml.task_validation_missing"]),
    "inference_handoff_unknown": (_upd(task="inference", output_semantics="density-ratio",
                                       sbi_validation={**_SBI, "handoff": "hep-statistic"}), ["ml.handoff_unknown"]),
    "unsupervised_no_anomaly_validation": (_upd(supervision="unsupervised", labels=[]), ["ml.task_validation_missing"]),
    "reweighting_no_validation": (_upd(task="reweighting", output_semantics="density-ratio"), ["ml.task_validation_missing"]),
    "reweighting_validation_incomplete": (_upd(task="reweighting", output_semantics="density-ratio",
                                               reweighting_validation={k: _REWEIGHT[k] for k in ("closure", "prior_dependence")}),
                                          ["ml.task_validation_incomplete"]),
    "single_label": (_upd(labels=["sig"]), ["ml.single_label"]),
    "duplicate_features": (_upd(features=["x", "y", "x"]), ["ml.duplicate_features"]),
    "label_is_feature": (_upd(labels=["sig", "x"]), ["ml.label_is_feature"]),
    "preprocessing_fit_on_all": (_upd(preprocessing=[{"step": "standardize", "features": ["x", "y"], "fit_on": "all"}]),
                                 ["ml.preprocessing_not_on_train"]),
    "multiclass_calibration_scope": (_all(_upd(labels=["a", "b", "c"]),
                                          lambda e: e["calibration"]["validation"].update(metric="brier (a vs rest)")),
                                     ["ml.multiclass_calibration_scope"]),
    # model-hash format (WP1.3)
    "model_hash_placeholder": (_upd(model_hash="sha256:placeholder"), ["ml.model_hash_malformed"]),
    "model_hash_short": (_upd(model_hash="sha256:" + "a" * 63), ["ml.model_hash_malformed"]),
    # weights split between training and evaluation (WP1.4)
    "weights_unstructured": (_upd(weights="unweighted"), ["ml.weights_unstructured"]),
    "weights_used_in_empty": (_sub("weights", used_in=[]), ["ml.weights_used_in_empty"]),
    "weights_used_in_inconsistent": (_sub("weights", used_in=["metrics"]), ["ml.weights_used_in_inconsistent"]),
    "weights_contradiction": (_sub("weights", training={"negative_weight_treatment": "abs", "class_balancing": "none"}),
                              ["ml.weights_contradiction"]),
    # calibration outcome (WP0.1, WP1.4)
    "calibration_same_sample_hash": (_sub("calibration", sample_check={"fit_sha256": "1" * 64, "eval_sha256": "1" * 64}),
                                     ["ml.calibration_on_fit_sample"]),
    "calibration_on_training_sample": (_sub("calibration", fit_sample="train"), ["ml.calibration_on_training_sample"]),
    "calibration_after_not_numeric": (lambda e: e["calibration"]["validation"].update(after="good"),
                                      ["ml.calibration_after_not_numeric"]),
    # remaining 2.8.0 claim checks: downstream items, task-block payloads, status, units, working point
    "downstream_incomplete": (_upd(downstream_validation=[{"metric": "working-point-efficiency", "value": 0.52, "ref": "synthetic"}]),
                              ["ml.downstream_incomplete"]),
    "surrogate_policy_action": (_all(_upd(task="surrogate", output_semantics="regression-value",
                                          extrapolation_policy={"action": "ignore", "consumer": "hep-theory"}), _NO_CAL),
                                ["ml.extrapolation_policy_action"]),
    "generation_two_sample_power_missing": (_all(_upd(task="generation", output_semantics="generated-sample",
                                                      generative_validation={"observables": ["x", "y"],
                                                                             "two_sample_test": {"auc": 0.5},
                                                                             "conditioning_range": "synthetic"}), _NO_CAL),
                                            ["ml.two_sample_power_missing"]),
    "units_unknown_feature": (_upd(units={"x": "GeV", "y": "1", "mass": "GeV"}), ["ml.units_unknown_feature"]),
    "threshold_from_test": (_upd(metrics={"test": {"working_point": {"threshold_from": "test"}}}), ["ml.threshold_from_test"]),
}
for _name, (_fn, _codes) in ML_V28_INVALID.items():
    bad[f"ml_v28_{_name}.json"] = (ml_v28(_fn), _codes)
_d = ml_v25()
_d["status"] = ["observed"]
bad["ml_v28_status_observed_unsupported.json"] = (_d, ["ml.status_unsupported"])
# observable_source kind ml-score names an ml-artifact input (WP0.5)
bad["statres_v28_observable_source_unlinked.json"] = (statres_v26(observable_source={"kind": "ml-score", "ml_artifact": "classifier"}),
                                                     ["stats.observable_source_unlinked"])
ML_V28_UNRESOLVED = {
    "output_semantics_missing": (_all(lambda e: e.pop("output_semantics"), _NO_CAL), ["ml.output_semantics_missing"]),
    "grouping_row_level": (_sub("splits", grouping_key="row"), ["ml.grouping_row_level"]),
    "split_check_unverified": (_sub("splits", overlap_check={"tool": "manual", "result": "pass"}), ["ml.split_check_unverified"]),
    "training_domain_unbounded": (_sub("training_domain", x=[-1e308, 1e308]), ["ml.training_domain_unbounded"]),
    "training_domain_partial": (lambda e: e["training_domain"].pop("y"), ["ml.training_domain_partial"]),
    # domain-shift outcome (WP0.6)
    "domain_shift_on_training_sample": (_sub("domain_shift", control_sample="training sample"),
                                        ["ml.domain_shift_on_training_sample"]),
    "domain_shift_uncorrected": (_sub("domain_shift", outcome="uncorrected"), ["ml.domain_shift_uncorrected"]),
    "domain_shift_outcome_missing": (lambda e: e["domain_shift"].pop("outcome"), ["ml.domain_shift_outcome_missing"]),
    "domain_shift_status_missing": (lambda e: e["domain_shift"].pop("status"), ["ml.domain_shift_status_missing"]),
    "training_domain_missing": (_upd(training_domain={}), ["ml.training_domain_missing"]),
    "calibration_not_improving": (lambda e: e["calibration"]["validation"].update(after=0.2), ["ml.calibration_not_improving"]),
}
for _name, (_fn, _codes) in ML_V28_UNRESOLVED.items():
    UNRESOLVED[f"ml_v28_{_name}.json"] = (ml_v28(_fn), _codes)
WARNING["ml_v28_framework_version_missing.json"] = (ml_v28(lambda e: e["environment"].pop("torch_version")),
                                                    ["ml.framework_version_missing"])
WARNING["ml_v28_weights_not_split.json"] = (ml_v28(lambda e: (e["weights"].pop("training"), e["weights"].pop("evaluation"))),
                                            ["ml.weights_not_split"])
WARNING["ml_v28_negative_weights_abs.json"] = (ml_v28(_sub("weights", negative_weight_treatment="abs",
                                                           training={"negative_weight_treatment": "abs",
                                                                     "class_balancing": "inverse class frequency"})),
                                               ["ml.negative_weights_abs"])
WARNING["ml_v28_environment_free_text.json"] = (ml_v28(_sub("environment", precision="high", device="my laptop")),
                                                ["ml.precision_free_text", "ml.device_free_text"])


def main() -> None:
    for sub in ("valid", "invalid", "unresolved", "warning"):
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
    cases["warning"] = {}
    for name, (doc, codes) in WARNING.items():
        (OUT / "warning" / name).write_text(json.dumps(doc, indent=1) + "\n")
        cases["warning"][name] = codes
    (OUT / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(f"{len(VALID)} valid, {len(bad)} invalid, {len(UNRESOLVED)} unresolved, {len(WARNING)} warning fixtures")


if __name__ == "__main__":
    main()
