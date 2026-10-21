#!/usr/bin/env python3
"""Validate a hep-research artifact: common envelope + typed extension + semantic rules.

Usage: python3 contracts/validate.py ARTIFACT.json|ARTIFACTS_DIR [--profiles-from PROJECT_CONFIG.json] [--protected]
           [--strict-versions] [--strict] [--gate publication]
Exit codes: 0 valid (and, with --gate, the gate passed), 1 findings with errors (or the gate failed or is unresolved),
2 unreadable input or bad usage. Output: JSON report on stdout.
A valid artifact is self-consistent under the contract; that says nothing about physical validity, and this check is
advisory: it never authorizes a use. --protected switches protected mode on (core.protected.guard: the protected
inputs of the project's authoritative agent_policy must be established, else the run is refused) and with it the
stricter version policy; --strict-versions applies only that version policy (a newer minor contract version is an
error, not a warning), without protected mode. A skill name that is not a current skill (contracts.skill_names) is
an error, except an unknown, not retired, name under an extension 'handoff' key, which is a warning
(skill.unknown_handoff; an ml-artifact under the 2.8.0 ml rules reports it as the error ml.handoff_unknown instead). --strict applies the statistical-result
semantic rules of contracts 2.2.0 (p-values and confidence levels in range, ordered expected bands, typed coverage and global
calibration) and the response semantic rules of contracts 2.4.0 (controlled correction vocabulary, a matrix or
matrix_ref, normalization consistent with what sits inside the matrix, one unit per variable) and the ml-artifact
rules of contracts 2.5.0 (non-blank grouping key, model hash, labels and features; training domain on the features
with lo < hi; split-overlap result; calibration where the output must be calibrated, not evaluated on its fit sample;
domain-shift check; seeds), the theory-spec and prediction rules of contracts 2.6.0 (conventions block, order of a
perturbative argument, limit of an asymptotic one, checks behind a formal proof or analytic derivation, check-result
vocabulary, non-empty validity domain, degenerate directions of a propagation model; no upgraded prediction status,
a linked theory spec, envelope prescription and [min, max] values, truncation method), the measurement-spec rules
of contracts 2.6.0 (an estimand sentence; complete observable with phase space and frame; conditional denominators;
backgrounds with estimator, control region or constraint, and closure; each correction once, from the controlled
categories, not repeating the normalization or the observable's included corrections; no zero standing for unknown;
systematics with applied_via and unique names; every missing marker listed in unresolved_inputs; blinded specs with a
mask and without observed status; ratio blocks; ordered periods; misspelled keys) and the statistical-result hardening
rules of contracts 2.6.0 (coverage level and interval consistent with the toy counts, at least 200 coverage toys, no
p-value of exactly 0, probability-like results in [0, 1], z consistent with p, construction and test statistic
compatible, expected bands with an observed limit, recorded seeds for toys, a well-formed model_sha256; Bayesian:
improper uniform forms, propriety with an argument and a reference, a prior on every parameter of interest, an ESS
floor of 100 per chain) and the response hardening rules of contracts 2.8.0 (declared intended_use and
underflow_overflow for a matrix, misspelled keys, placement consistent with 'includes', a probability reading, exposure
not listed with the acceptance or live time it contains, flow vectors with explicit bins, correction space, finite-MC
statistics for unfolding, variation shapes, and the numerical check of an inline matrix through
contracts.response_adapter and core/stats/validate_response.py) and the ml-artifact rules of contracts 2.8.0
(calibration sample identity, structured downstream validation, required output semantics, misspelled keys,
task-specific validation blocks, weights and calibration outcomes, domain-shift outcome) to artifacts written under
older contracts, which
otherwise keep their outcome; --strict
never raises a rule's level. Flags may come before or after ARTIFACT.json. --gate publication adds the publication
gate of a statistical-result (publication_gate): passed, unresolved or failed, with reasons (from 2.6.0 a
'synthetic' or 'asimov' result fails it); an archived artifact may be valid and still not pass it. Passing the gate
is a contract-level prerequisite for
reporting a result as validated, not evidence of scientific validity. Given a directory (an artifacts_dir), every
JSON file under it is validated and must be an artifact or a sidecar an artifact there refers to by path; another
JSON file is an error (artifacts_dir.not_artifact), another file a warning; the report lists each file
(validate_directory).
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, load_schema, validate  # noqa: E402
from contracts.semver import parse  # noqa: E402
from contracts.vocab import NAMESPACED, Vocabulary  # noqa: E402
from contracts.protected_use import guard_report  # noqa: E402
from core.protected.guard import protected_main  # noqa: E402
from contracts import KNOWN_CAPABILITIES, skill_names  # noqa: E402

EXTENSION_SCHEMAS = {
    "measurement-spec": "ext_measurement_spec.json", "response": "ext_response.json",
    "theory-spec": "ext_theory_spec.json", "prediction": "ext_prediction.json",
    "comparison-spec": "ext_comparison_spec.json", "statistical-result": "ext_statistical_result.json",
    "ml-artifact": "ext_ml_artifact.json", "computational-run": "ext_computational_run.json",
    "communication": "ext_communication.json", "dataset-record": "ext_dataset_record.json",
    "literature-record": "ext_literature_record.json",
}
# Statuses that must survive every handoff: a consumer of such an input carries the label.
STICKY_STATUSES = ["failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied"]
# Statuses under which a statistical-result is not a result on data: the publication gate fails them (contracts 2.6.0).
NOT_OBSERVED_STATUSES = ("synthetic", "asimov")
NON_GAUSSIAN_KINDS = {"scale-envelope", "model-alternative", "truncation"}
UPGRADED = {"observed", "validated-in-scope"}
SHAPE_ERRORS = {"schema.type", "schema.any_of"}
AUC_ONLY = re.compile(r"^\s*(roc[\s_-]*)?auc(\s*\(?roc\)?)?\s*$", re.I)


def required_statuses(inputs) -> list[str]:
    """Sticky statuses any consumer of these inputs must carry (failed, synthetic, asimov, ...)."""
    found = {s for i in inputs for s in i.get("status", [])}
    return [s for s in STICKY_STATUSES if s in found]
EXPERIMENT_ONLY_FIELDS = {"selections", "backgrounds", "blinding", "detector", "response", "corrections", "period"}


def check_conventions(conv: dict, vocab: Vocabulary, rep: Report, path: str) -> None:
    for key in conv:
        if not (vocab.has("convention_keys", key) or NAMESPACED.match(key)):
            rep.add("warning", f"{path}.{key}", "conventions.unknown_key",
                    f"'{key}' is neither a core convention key nor namespaced '<ns>:<key>'; "
                    "the comparison gate will report it as not comparable unless a mapping is declared")


EDGE_TOL = 1e-12


def check_finite(value, rep: Report, path: str = "$") -> None:
    """NaN and +-Infinity are not numbers a contract can carry (JSON itself has no such values)."""
    if isinstance(value, float) and not math.isfinite(value):
        rep.add("error", path, "number.non_finite", f"{value!r} is not a finite number")
    elif isinstance(value, dict):
        for k, v in value.items():
            check_finite(v, rep, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            check_finite(v, rep, f"{path}[{i}]")


def _same_edges(a, b) -> bool:
    return len(a) == len(b) and all(abs(x - y) <= EDGE_TOL * max(1.0, abs(y)) for x, y in zip(a, b))


def check_binned(b: dict, rep: Report, path: str, obs: dict | None = None) -> None:
    """Binned payload checks. With the observable: the payload's axes, shape and unit must be the observable's.
    One axis: `edges` equal the variable's edges. Several axes: `axes` lists the variable names in the observable's
    order, `values` is flattened row-major (last axis fastest) with one entry per cell, and `edges` repeats the first
    axis. A unit other than the observable's needs `unit_conversion` {from: observable unit, to, factor, justification}."""
    edges, values = b.get("edges", []), b.get("values", [])
    if any(e2 <= e1 for e1, e2 in zip(edges, edges[1:])):
        rep.add("error", f"{path}.edges", "binned.edges_not_increasing", "bin edges must be strictly increasing")
    variables = (obs or {}).get("variables") or []
    n_cells = max(len(edges) - 1, 0)
    if len(variables) > 1:
        names = [v.get("name") for v in variables]
        if "axes" not in b:
            rep.add("error", f"{path}.axes", "binned.axes_missing",
                    f"a {len(variables)}-dimensional observable needs 'axes' naming the payload's axis order {names}")
        elif b["axes"] != names:
            rep.add("error", f"{path}.axes", "binned.axes_mismatch", f"axes {b['axes']} differ from the observable's variables {names}")
        if all("edges" in v for v in variables):
            n_cells = math.prod(len(v["edges"]) - 1 for v in variables)
    if variables and "edges" in variables[0] and not _same_edges(edges, variables[0]["edges"]):
        rep.add("error", f"{path}.edges", "binned.edges_mismatch",
                f"payload edges {edges} differ from the observable's '{variables[0].get('name')}' edges {variables[0]['edges']}")
    if len(values) != n_cells:
        rep.add("error", f"{path}.values", "binned.length", f"{len(values)} values for {n_cells} bins")
    if obs is not None and "unit" in b and b["unit"] != obs.get("unit"):
        conv = b.get("unit_conversion") or {}
        f = conv.get("factor")
        traced = (conv.get("from") == obs.get("unit") and conv.get("to") == b["unit"] and conv.get("justification")
                  and isinstance(f, (int, float)) and not isinstance(f, bool) and math.isfinite(f) and f > 0)
        if not traced:
            rep.add("error", f"{path}.unit", "binned.unit_mismatch",
                    f"payload unit '{b['unit']}' differs from the observable unit '{obs.get('unit')}' without a traceable "
                    "unit_conversion {from, to, factor, justification}")
    for i, u in enumerate(b.get("uncertainties", [])):
        if "values" in u and len(u["values"]) != len(values):
            rep.add("error", f"{path}.uncertainties[{i}]", "binned.uncertainty_length",
                    f"uncertainty '{u.get('name')}' has {len(u['values'])} entries for {len(values)} bins")


def check_observable(obs: dict, vocab: Vocabulary, rep: Report, path: str) -> None:
    check_conventions(obs.get("conventions", {}), vocab, rep, f"{path}.conventions")
    for i, v in enumerate(obs.get("variables", [])):
        if "edges" in v and "points" in v:
            rep.add("error", f"{path}.variables[{i}]", "observable.edges_and_points", "give edges or points, not both")
    if obs.get("bin_semantics") in ("unknown", "not-applicable", "not-provided"):
        rep.add("unresolved", f"{path}.bin_semantics", "observable.bin_semantics_missing",
                f"bin semantics '{obs['bin_semantics']}': a comparison cannot be made until it is known")
    if obs.get("bin_semantics") == "point" and any("edges" in v for v in obs.get("variables", [])):
        rep.add("warning", path, "observable.point_with_edges",
                "point semantics with bin edges: the comparison gate needs an explicit point-to-bin mapping")
    norm = obs.get("normalization", {})
    if norm.get("kind") in ("integrated-luminosity", "exposure", "protons-on-target", "target-exposure", "live-time") \
            and "value" not in norm and "ref" not in norm:
        rep.add("unresolved", f"{path}.normalization", "normalization.value_missing",
                f"normalization kind '{norm['kind']}' has no value or ref yet")


def _rules(doc: dict, ext: dict, vocab: Vocabulary, rep: Report, strict: bool = False) -> None:
    t = doc.get("artifact_type")
    status = set(doc.get("status", []))
    inherited = {s for i in doc.get("inputs", []) for s in i.get("status", [])}
    for s in STICKY_STATUSES:
        if s in inherited and s not in status:
            rep.add("error", "$.status", "status.not_propagated", f"an input carries '{s}' but this artifact does not")
    if "observed" in status and ({"synthetic", "asimov"} & status):
        rep.add("error", "$.status", "status.conflict", "'observed' cannot be combined with 'synthetic' or 'asimov'")

    if isinstance(ext.get("observable"), dict):
        check_observable(ext["observable"], vocab, rep, "$.extension.observable")

    if t == "measurement-spec":
        ids = [c.get("effect_id") for c in ext.get("corrections", [])]
        for dup in sorted({x for x in ids if ids.count(x) > 1}):
            rep.add("error", "$.extension.corrections", "measurement.duplicate_correction", f"effect '{dup}' applied twice")
        if strict or _at_least(doc.get("contract_version"), MEASUREMENT_SEMANTICS_FROM):
            _measurement_semantics(doc, ext, vocab, rep)
    elif t == "response":
        both = set(ext.get("includes", [])) & set(ext.get("applied_separately", []))
        for x in sorted(both):
            rep.add("error", "$.extension", "response.double_counted", f"'{x}' is inside the matrix and applied separately")
        if ext.get("form") == "parametrized" and not ext.get("parametrization"):
            rep.add("error", "$.extension.parametrization", "response.parametrization_missing", "parametrized response needs a parametrization with validity range")
        if ext.get("form", "matrix") == "matrix" and not all(isinstance(ext.get(a), dict) for a in ("truth_axis", "reco_axis")):
            rep.add("error", "$.extension", "response.axes_missing", "a response matrix needs truth and reco axes")
        if ext.get("inefficiency") == "inside_matrix" and "efficiency" in ext.get("applied_separately", []):
            rep.add("error", "$.extension", "response.double_counted", "inefficiency inside the matrix and efficiency applied separately")
        if strict or _at_least(doc.get("contract_version"), RESPONSE_SEMANTICS_FROM):
            _response_semantics(ext, vocab, rep)
        if strict or _at_least(doc.get("contract_version"), RESPONSE_HARDENING_FROM):
            _response_hardening(ext, rep)
    elif t == "theory-spec":
        if doc.get("bindings", {}).get("experiments"):
            rep.add("error", "$.bindings.experiments", "theory.experiment_binding",
                    "a theory spec carries no experiment binding; bind data in a comparison spec")
        check_conventions(ext.get("conventions", {}), vocab, rep, "$.extension.conventions")
        for bad in sorted(EXPERIMENT_ONLY_FIELDS & set(ext)):
            rep.add("error", f"$.extension.{bad}", "theory.experiment_field", f"experiment field '{bad}' in a theory spec")
        if strict or _at_least(doc.get("contract_version"), THEORY_SEMANTICS_FROM):
            _theory_semantics(doc, ext, vocab, rep)
    elif t == "prediction":
        for i, u in enumerate(ext.get("uncertainties", [])):
            if u.get("kind") in NON_GAUSSIAN_KINDS and u.get("gaussian") is True:
                rep.add("error", f"$.extension.uncertainties[{i}]", "uncertainty.auto_gaussian",
                        f"'{u['kind']}' must not be treated as Gaussian without a hep-theory prescription")
        if isinstance(ext.get("values"), dict):
            check_binned(ext["values"], rep, "$.extension.values", ext.get("observable"))
        rp: Any = ext.get("representation")
        need = {"numerical": "values", "grid": "values", "symbolic": "expression"}.get(rp)
        if need and not ext.get(need):
            rep.add("error", f"$.extension.{need}", "prediction.payload_missing",
                    f"a {rp} prediction needs '{need}' (numbers kept elsewhere: reference them and use a metadata record)")
        if strict or _at_least(doc.get("contract_version"), THEORY_SEMANTICS_FROM):
            _theory_semantics(doc, ext, vocab, rep)
    elif t == "dataset-record":
        if isinstance(ext.get("data"), dict):
            check_binned(ext["data"], rep, "$.extension.data", ext.get("observable"))
            if ext.get("status") in ("published", "preliminary") and not ext.get("source_evidence_ids"):
                rep.add("error", "$.extension.source_evidence_ids", "dataset.values_without_provenance",
                        "published/preliminary values need source evidence IDs")
        if ext.get("status") == "synthetic":
            if "synthetic" not in status:
                rep.add("error", "$.status", "dataset.synthetic_unlabeled", "synthetic dataset must carry the 'synthetic' status")
            if "synthetic" not in ext.get("dataset_id", ""):
                rep.add("error", "$.extension.dataset_id", "dataset.synthetic_unlabeled", "synthetic dataset id must contain 'synthetic'")
        if ext.get("status") == "simulated":
            _simulated_dataset(doc, ext, status, rep)
        if ext.get("covariance", {}).get("status") == "present" and not ext["covariance"].get("ref"):
            rep.add("error", "$.extension.covariance", "dataset.covariance_ref", "covariance marked present needs a ref")
    elif t == "statistical-result":
        p: Any = ext.get("paradigm")
        needed = {"frequentist": ["test_statistic", "construction", "coverage"],
                "bayesian": ["priors", "sampler", "convergence"]}.get(p, [])
        for k in needed:
            if not ext.get(k):
                rep.add("error", f"$.extension.{k}", "stats.paradigm_incomplete", f"{p} result requires '{k}'")
        wrong = {"frequentist": ["priors", "sampler"], "bayesian": ["construction", "test_statistic"]}.get(p, [])
        for k in wrong:
            if k in ext:
                rep.add("error", f"$.extension.{k}", "stats.paradigm_mislabeled", f"'{k}' does not belong to a {p} result")
        if ext.get("fit_status") == "failed" and "failed" not in status:
            rep.add("error", "$.status", "status.failed_unlabeled", "failed fit must carry the 'failed' status")
        sig = ext.get("significance")
        if isinstance(sig, dict) and isinstance(sig.get("scan"), dict) and sig.get("global_p") is None:
            rep.add("unresolved", "$.extension.significance.global_p", "stats.lee_missing",
                    "a scan reports a local significance only: add the global p-value and its trials_method")
        rhat = _max_rhat(ext.get("convergence"))
        if p == "bayesian" and rhat is not None and rhat > RHAT_MAX and ext.get("fit_status") == "converged":
            # an error from contract 1.1.0 on; a 1.0.0 artifact keeps its old outcome and gets a warning
            level = "error" if _at_least(doc.get("contract_version"), "1.1.0") else "warning"
            rep.add(level, "$.extension.fit_status", "stats.convergence_mismatch",
                    f"declared R-hat {rhat:g} exceeds {RHAT_MAX} but fit_status is 'converged'; use "
                    "'converged-with-warnings' or 'failed'")
    elif t == "computational-run":
        if ext.get("exit_status", 0) != 0 and "failed" not in status:
            rep.add("error", "$.status", "status.failed_unlabeled", "non-zero exit status must carry 'failed'")
        if strict or _at_least(doc.get("contract_version"), GEANT4_UPGRADE_FROM):
            _study_upgrade(doc, ext, status, rep)
    elif t == "ml-artifact":
        if not ext.get("splits", {}).get("grouping_key"):
            rep.add("error", "$.extension.splits.grouping_key", "ml.no_grouping", "splits need a grouping key (leakage control)")
        dv = ext.get("downstream_validation", [])
        if not dv:
            rep.add("unresolved", "$.extension.downstream_validation", "ml.no_downstream_validation",
                    "no downstream validation yet: a model is not usable in an analysis until it is validated there")
        elif all(AUC_ONLY.search(str(v.get("metric", v) if isinstance(v, dict) else v)) for v in dv):
            rep.add("error", "$.extension.downstream_validation", "ml.auc_only",
                    "AUC alone is insufficient: add calibration, working-point efficiency, or data/simulation agreement in the analysis region")
        if ext.get("task") == "surrogate" and not ext.get("training_domain"):
            rep.add("error", "$.extension.training_domain", "ml.no_training_domain", "a surrogate needs its training domain to detect extrapolation")
        if strict or _at_least(doc.get("contract_version"), ML_SEMANTICS_FROM):
            _ml_semantics(ext, rep)
        if strict or _at_least(doc.get("contract_version"), ML_SEMANTICS_V2_FROM):
            _ml_semantics_v2(doc, ext, vocab, rep, native=_at_least(doc.get("contract_version"), ML_SEMANTICS_V2_FROM))
    elif t == "communication":
        from contracts.communication import validate_extension  # lazy: communication imports this module's constants
        validate_extension(doc, vocab, rep)
    elif t == "literature-record":
        _literature_semantics(ext, rep)


def _literature_semantics(ext: dict, rep: Report) -> None:
    """literature-record (contracts 2.13.0): the record's sources and claims are keyed by their own ids and still pass
    the evidence-ledger check (core.evidence.ledger) they were imported under; dates are judged at the record's
    creation date, so a record does not age into failure."""
    from core.evidence.ledger import check_ledger
    sources, claims = ext.get("sources") or {}, ext.get("claims") or {}
    for kind, table in (("source", sources), ("claim", claims)):
        for key, entry in table.items():
            if isinstance(entry, dict) and entry.get("id") != key:
                rep.add("error", f"$.extension.{kind}s.{key}", f"literature.{kind}_key_mismatch",
                        f"{kind} keyed '{key}' has id {entry.get('id')!r}; a record keys each {kind} by its own id")
    try:
        created = date.fromisoformat(str(ext.get("created")))
    except ValueError:
        created = None
    ledger = check_ledger(list(sources.values()), list(claims.values()), today=created)
    for e in ledger.get("errors", []):
        rep.add("error", f"$.extension ({e.get('where')})", "literature.ledger_invalid",
                f"{e.get('code')}: {e.get('message')} (the evidence-ledger rules of core/evidence/ledger.py)")


RHAT_MAX = 1.01  # [Proposal] threshold for stats.convergence_mismatch
GEANT4_UPGRADE_FROM = "3.1.0"  # Geant4 phase-2 rules (study record upgrade, evidence records) apply from this version


def _scope_inside(declared: dict, bench: dict) -> list[str]:
    """Where a declared scope leaves a benchmark's scope (particle, material, energy and thickness ranges)."""
    out = []
    for k in ("particle", "material"):
        if declared.get(k) is not None and bench.get(k) is not None and declared[k] != bench[k]:
            out.append(f"{k} {declared[k]!r} is not the benchmark's {bench[k]!r}")
    for k in ("energy_MeV", "thickness_mm"):
        d, b = declared.get(k), bench.get(k)
        if b is None or d is None:
            if d is not None:
                out.append(f"{k}: the benchmark states none")
            continue
        lo, hi = (d, d) if isinstance(d, (int, float)) else (d[0], d[-1])
        blo, bhi = (b, b) if isinstance(b, (int, float)) else (b[0], b[-1])
        if lo < blo * (1 - 1e-9) or hi > bhi * (1 + 1e-9):
            out.append(f"{k} {d} is outside the benchmarked {b}")
    return out


SIMULATED_LEVELS = ("detector", "particle-fiducial")


def _simulated_dataset(doc: dict, ext: dict, status: set, rep: Report) -> None:
    """3.2.0: a dataset-record with status 'simulated' is a table derived from recorded simulation runs. Its envelope
    inputs are the run records (or a study record) it was derived from, so contracts/dependencies.py checks their
    hashes and carries their labels; it is never 'observed', it keeps 'unvalidated' unless an input study record
    carries 'validated-in-scope', and its level is detector or particle-fiducial."""
    inputs = doc.get("inputs")
    linked = [i for i in inputs if isinstance(i, dict)] if isinstance(inputs, list) else []
    if not linked:
        rep.add("error", "$.inputs", "dataset.simulated_without_runs",
                "a simulated dataset needs its run records or study record as inputs")
    if "observed" in status:
        rep.add("error", "$.status", "dataset.simulated_observed", "a simulated dataset is never 'observed'")
    level = (ext.get("observable") or {}).get("level")
    if level not in SIMULATED_LEVELS:
        rep.add("error", "$.extension.observable.level", "dataset.simulated_level",
                f"a simulated dataset is at level {' or '.join(SIMULATED_LEVELS)}, not {level!r}")
    if not {"unvalidated", "validated-in-scope"} & status:
        rep.add("error", "$.status", "dataset.simulated_unlabeled",
                "a simulated dataset carries 'unvalidated', or 'validated-in-scope' from a study record it uses")
    if "validated-in-scope" in status and not any("validated-in-scope" in (i.get("status") or []) for i in linked):
        rep.add("error", "$.status", "dataset.simulated_upgrade_unlinked",
                "'validated-in-scope' needs an input study record that carries it (a status is never upgraded by hand)")


def _study_upgrade(doc: dict, ext: dict, status: set, rep: Report) -> None:
    """3.1.0 Geant4 phase 2: evidence records need their capability, and a record with Geant4 study material that
    carries validated-in-scope must show the evidence for it."""
    ev = ext.get("evidence_records")
    if ev and "core:evidence-records" not in (doc.get("required_capabilities") or []):
        rep.add("error", "$.required_capabilities", "evidence.capability_not_declared",
                "an artifact with extension.evidence_records must require core:evidence-records")
    geant4 = any(k in ext for k in ("study", "simulation", "evidence_records"))
    if "validated-in-scope" not in status or not geant4:
        return
    study = ext.get("study")
    if not isinstance(study, dict):
        rep.add("error", "$.extension.study", "geant4.upgrade_without_study",
                "validated-in-scope on a Geant4 record needs the study block of check_geant4_study.py label")
        return
    if "simulation" in ext:
        rep.add("error", "$.extension.simulation", "geant4.run_record_upgraded",
                "a Geant4 run record stays unvalidated; only a study record can be re-issued as validated-in-scope")
    if not ev:
        rep.add("error", "$.extension.evidence_records", "geant4.upgrade_without_evidence_records",
                "the run records behind the study must be referenced in extension.evidence_records")
    if (study.get("convergence") or {}).get("gate") != "pass":
        rep.add("error", "$.extension.study.convergence", "geant4.upgrade_unconverged",
                "validated-in-scope needs a passed convergence gate")
    good = [b for b in study.get("benchmarks", []) if isinstance(b, dict) and b.get("grade") == "reference"
            and b.get("verdict") == "pass" and b.get("validation_evidence") is True
            and (b.get("negative_control") or {}).get("status") == "caught"]
    if not good:
        rep.add("error", "$.extension.study.benchmarks", "geant4.upgrade_without_reference_benchmark",
                "validated-in-scope needs a passed reference benchmark whose negative control was caught")
        return
    declared = study.get("declared_scope") or {}
    misses = [_scope_inside(declared, b.get("scope") or {}) for b in good]
    if not declared or all(misses):
        detail = "; ".join(m for ms in misses for m in ms) or "no declared scope"
        rep.add("error", "$.extension.study.declared_scope", "geant4.upgrade_scope_outside",
                f"the declared scope is not inside a passed benchmark's scope: {detail}")


RESPONSE_SEMANTICS_FROM = "2.4.0"  # response semantic rules apply natively from this contract version
RESPONSE_HARDENING_FROM = "2.8.0"  # response hardening rules (hep-detector audit) apply natively from this version
IMPLIED_CORRECTIONS = {"exposure": {"acceptance", "livetime"}}  # vocab response_corrections: exposure = acceptance x live time
RESPONSE_EFFICIENCY_LIKE = {"efficiency", "acceptance", "fiducial"}  # classes whose correction_space must be stated


def _correction_classes(terms) -> set[str]:
    """Classes of response corrections: every '<x>_efficiency' (namespaced or not) counts as 'efficiency'."""
    out = set()
    for t in terms:
        bare = t.split(":", 1)[-1]
        out.add("efficiency" if bare == "efficiency" or bare.endswith("_efficiency") else bare)
    return out


def _response_semantics(ext: dict, vocab: Vocabulary, rep: Report) -> None:
    """Response rules of contracts 2.4.0 (hep-detector review 2026-10-12). Native for artifacts of contract 2.4.0
    or later; an older artifact gets them only in strict mode, so its promised outcome is unchanged."""
    includes, separate = ext.get("includes", []), ext.get("applied_separately", [])
    for field, terms in (("includes", includes), ("applied_separately", separate)):
        for t in terms:
            if not (vocab.has("response_corrections", t) or NAMESPACED.match(t)
                    or (isinstance(t, str) and re.fullmatch(r"[a-z][a-z0-9_]*_efficiency", t))):
                rep.add("error", f"$.extension.{field}", "response.unknown_correction",
                        f"'{t}' is not a response_corrections term, a '<x>_efficiency' term or a namespaced '<ns>:<term>'")
    inside = _correction_classes(includes)
    if ext.get("inefficiency") == "inside_matrix":
        inside.add("efficiency")
    if ext.get("acceptance") == "inside_matrix":
        inside.add("acceptance")
    for cls in sorted(inside & _correction_classes(separate)):
        if cls == "efficiency" and "efficiency" in separate and ext.get("inefficiency") == "inside_matrix":
            continue  # already reported by the literal check of every version
        if cls in set(includes) & set(separate):
            continue
        rep.add("error", "$.extension", "response.double_counted",
                f"'{cls}' (or a term of its class) is inside the matrix and also applied separately")
    if ext.get("form", "matrix") == "matrix" and not (isinstance(ext.get("matrix"), list) or ext.get("matrix_ref")):
        rep.add("error", "$.extension", "response.matrix_missing", "a response of form 'matrix' needs matrix or matrix_ref")
    norm = ext.get("normalization")
    if norm == "conditional_on_selected":
        for effect in ("inefficiency", "acceptance"):
            if ext.get(effect) == "inside_matrix":
                rep.add("error", f"$.extension.{effect}", "response.normalization_inconsistent",
                        f"'conditional_on_selected' puts {effect} outside the matrix, but it is declared inside")
    if norm == "joint_counts" and ext.get("inefficiency") == "inside_matrix":
        rep.add("error", "$.extension.inefficiency", "response.normalization_inconsistent",
                "'joint_counts' hold selected events only, so the inefficiency cannot be inside them; use "
                "'conditional_on_generated' or declare it outside")
    t_ax, r_ax = ext.get("truth_axis"), ext.get("reco_axis")
    if isinstance(t_ax, dict) and isinstance(r_ax, dict) and t_ax.get("name") == r_ax.get("name") \
            and t_ax.get("unit") != r_ax.get("unit"):
        rep.add("error", "$.extension.reco_axis.unit", "response.unit_mismatch",
                f"'{t_ax.get('name')}' is in {t_ax.get('unit')!r} on the truth axis and {r_ax.get('unit')!r} on the reco axis")



def _truth_bins(ext: dict) -> int | None:
    """Number of truth bins: from the truth-axis edges, else from an inline matrix and its orientation."""
    axis = ext.get("truth_axis")
    if isinstance(axis, dict) and isinstance(axis.get("edges"), list) and len(axis["edges"]) >= 2:
        return len(axis["edges"]) - 1
    m = ext.get("matrix")
    if isinstance(m, list) and m and all(isinstance(row, list) for row in m):
        return len(m[0]) if ext.get("orientation", "rows_reco_cols_truth") == "rows_reco_cols_truth" else len(m)
    return None


def _shape(m) -> tuple[int, ...] | None:
    if isinstance(m, list) and m and all(isinstance(row, list) for row in m):
        return (len(m), *sorted({len(row) for row in m}))
    return None


# Adapter conversion errors that the rules above already report under their own code.
_ADAPTER_FIELDS_REPORTED = {"underflow_overflow", "normalization", "acceptance", "inefficiency", "truth_axis", "reco_axis",
                            "intended_use", "form"}


def _response_hardening(ext: dict, rep: Report) -> None:
    """Response rules of contracts 2.8.0 (hep-detector audit 2026-10-13, DR-WP2-03, rules R1-R10). Native for
    artifacts of contract 2.8.0 or later; an older artifact gets them only in strict mode. R1 a matrix declares
    intended_use and underflow_overflow; R2 misspelled keys (error) and unknown keys (warning); R3 what 'includes'
    holds agrees with where inefficiency and acceptance sit; R4 a matrix has a probability reading and a placement of
    the acceptance; R5 'exposure' already contains acceptance and live time; R6 explicit underflow/overflow bins come
    with their vectors; R7 correction_space names terms of applied_separately, and acceptance or fiducial act in truth
    space; R8 a response for unfolding states its finite-MC statistics (unresolved otherwise); R9 variations and periods
    have the nominal shape and are not repeated; R10 an inline matrix passes core/stats/validate_response.py through
    contracts.response_adapter (a matrix_ref is not opened here: unresolved, run the adapter). 'fakes' inside the
    matrix is a warning (some analyses keep fakes as an extra truth column)."""
    x = "$.extension"
    form = ext.get("form", "matrix")
    is_matrix = form == "matrix"
    # R1
    if is_matrix:
        for key in ("intended_use", "underflow_overflow"):
            if key not in ext:
                rep.add("error", f"{x}.{key}", "response.declaration_missing",
                        f"a response matrix declares '{key}' from contracts {RESPONSE_HARDENING_FROM}")
    # R2
    known = set(load_schema("ext_response.json")["properties"]) | set(load_schema("ext_response_v2_8.json")["properties"])
    _key_checks(ext, known, x, rep, kind="response")
    includes = ext.get("includes", []) if isinstance(ext.get("includes"), list) else []
    separate = ext.get("applied_separately", []) if isinstance(ext.get("applied_separately"), list) else []
    inside_cls = _correction_classes(t for t in includes if isinstance(t, str))
    sep_bare = {t.split(":", 1)[-1] for t in separate if isinstance(t, str)}
    # R3
    if "efficiency" in inside_cls and ext.get("inefficiency") == "outside_matrix":
        rep.add("error", f"{x}.includes", "response.placement_inconsistent",
                "'includes' lists an efficiency, but the inefficiency is declared outside the matrix")
    if "acceptance" in inside_cls and ext.get("acceptance") != "inside_matrix":
        rep.add("error", f"{x}.includes", "response.placement_inconsistent",
                "'includes' lists the acceptance, but the acceptance is not declared inside the matrix")
    if ext.get("normalization") == "conditional_on_generated" and ext.get("inefficiency") == "outside_matrix":
        rep.add("error", f"{x}.inefficiency", "response.normalization_inconsistent",
                "'conditional_on_generated' puts the inefficiency inside the matrix, but it is declared outside")
    if "fakes" in inside_cls:
        rep.add("warning", f"{x}.includes", "response.fakes_inside",
                "fakes are a reco-space vector, not a migration; keep them outside unless they are an explicit extra "
                "truth column, and say so")
    # R4
    if is_matrix and ext.get("normalization") == "unnormalized":
        rep.add("error", f"{x}.normalization", "response.normalization_unusable",
                "an unnormalized matrix has no probability reading: declare conditional_on_selected, "
                "conditional_on_generated or joint_counts")
    if is_matrix and ext.get("acceptance") == "not-applicable":
        rep.add("error", f"{x}.acceptance", "response.placement_missing",
                "a response matrix places the acceptance inside or outside the matrix")
    # R5
    for term, implied in IMPLIED_CORRECTIONS.items():
        if term not in sep_bare:
            continue
        for part in sorted(sep_bare & implied):
            rep.add("error", f"{x}.applied_separately", "response.correction_overlap",
                    f"'{term}' already contains '{part}': list one or the other")
        if "acceptance" in implied and ext.get("acceptance") == "inside_matrix":
            rep.add("error", f"{x}.applied_separately", "response.double_counted",
                    f"'{term}' applied separately contains the acceptance, which is inside the matrix")
    n_truth = _truth_bins(ext)
    # R6
    if ext.get("underflow_overflow") == "explicit_bins" and isinstance(ext.get("matrix"), list):
        vectors = [ext.get(k) for k in ("underflow", "overflow")]
        if not all(isinstance(vec, list) and (n_truth is None or len(vec) == n_truth) for vec in vectors):
            rep.add("error", f"{x}.underflow", "response.flow_vectors_missing",
                    f"'explicit_bins' with an inline matrix needs 'underflow' and 'overflow' with one entry per truth "
                    f"bin ({n_truth})")
    # R7
    space = ext.get("correction_space")
    if isinstance(space, dict):
        for term, spec in space.items():
            if term not in separate:
                rep.add("error", f"{x}.correction_space.{term}", "response.correction_space_unknown_term",
                        f"'{term}' is not in applied_separately")
            elif isinstance(spec, dict) and term.split(":", 1)[-1] in ("acceptance", "fiducial") \
                    and spec.get("space") == "reco":
                rep.add("error", f"{x}.correction_space.{term}", "response.correction_space_inconsistent",
                        f"'{term}' is a truth-level phase-space correction; it cannot act in reco space")
    if isinstance(space, dict) or separate:
        stated = space if isinstance(space, dict) else {}
        for term in separate:
            if isinstance(term, str) and term not in stated and _correction_classes([term]) & RESPONSE_EFFICIENCY_LIKE:
                rep.add("warning", f"{x}.correction_space", "response.correction_space_missing",
                        f"state where '{term}' acts (truth, reco or global) in correction_space")
    # R8
    mc = ext.get("mc_stat")
    if ext.get("intended_use") == "unfolding" and is_matrix and not isinstance(mc, dict):
        rep.add("unresolved", f"{x}.mc_stat", "response.mc_stat_missing",
                "a response for unfolding states its finite-MC statistics (mc_stat): the response uncertainty cannot be "
                "propagated without it")
    if isinstance(mc, dict):
        payload = {"generated_counts": "events_per_truth_bin", "effective_counts": "events_per_truth_bin",
                   "sumw2": "sumw2", "covariance_ref": "ref"}.get(str(mc.get("kind")))
        if payload and payload not in mc:
            rep.add("error", f"{x}.mc_stat.{payload}", "response.mc_stat_payload_missing",
                    f"mc_stat kind '{mc.get('kind')}' carries '{payload}'")
        vec = mc.get("events_per_truth_bin")
        if isinstance(vec, list) and n_truth is not None and len(vec) != n_truth:
            rep.add("error", f"{x}.mc_stat.events_per_truth_bin", "response.mc_stat_payload_missing",
                    f"events_per_truth_bin has {len(vec)} entries for {n_truth} truth bins")
    # R9
    nominal = _shape(ext.get("matrix"))
    seen: set[tuple[Any, Any]] = set()
    variations: list = ext["systematic_variations"] if isinstance(ext.get("systematic_variations"), list) else []
    for i, var in enumerate(v for v in variations if isinstance(v, dict)):
        pair = (var.get("nuisance"), var.get("direction"))
        if pair in seen:
            rep.add("error", f"{x}.systematic_variations[{i}]", "response.variation_duplicate",
                    f"variation {pair} is listed twice")
        seen.add(pair)
        if nominal and _shape(var.get("matrix")) not in (None, nominal):
            rep.add("error", f"{x}.systematic_variations[{i}].matrix", "response.variation_shape",
                    f"variation {pair} has shape {_shape(var.get('matrix'))}, the nominal matrix {nominal}")
    periods: list = ext["periods"] if isinstance(ext.get("periods"), list) else []
    for i, per in enumerate(p for p in periods if isinstance(p, dict)):
        if nominal and _shape(per.get("matrix")) not in (None, nominal):
            rep.add("error", f"{x}.periods[{i}].matrix", "response.variation_shape",
                    f"period '{per.get('id')}' has shape {_shape(per.get('matrix'))}, the nominal matrix {nominal}")
    if periods and not sum(p.get("exposure_weight", 0) for p in periods
                           if isinstance(p, dict) and isinstance(p.get("exposure_weight"), (int, float))) > 0:
        rep.add("error", f"{x}.periods", "response.variation_shape", "the period exposure weights sum to zero")
    # R10
    if not is_matrix:
        return
    if isinstance(ext.get("matrix"), list):
        from contracts.response_adapter import to_validator_input
        from core.stats.validate_response import validate_response
        conv = to_validator_input(ext)
        if not conv["ok"]:
            for e in conv["errors"]:
                if e.get("field") not in _ADAPTER_FIELDS_REPORTED:
                    rep.add("error", f"{x}.{e.get('field')}", "response.not_checkable", e["message"])
            return
        result = validate_response(conv["input"])
        for level, items in (("error", result.get("errors", [])), ("warning", result.get("warnings", []))):
            for item in items:
                rep.add(level, f"{x}.matrix", f"response.numeric.{item['code']}", item["message"])
    elif ext.get("matrix_ref"):
        rep.add("unresolved", f"{x}.matrix_ref", "response.numeric_unchecked",
                "the numbers behind matrix_ref are not checked here (validate.py opens no other file): run "
                "python3 contracts/response_adapter.py <artifact> --validate")


ML_SEMANTICS_FROM = "2.5.0"  # ml-artifact content rules apply natively from this contract version
CALIBRATED_OUTPUTS = {"probability", "density-ratio"}
DOMAIN_SHIFT_TASKS = {"classification", "regression"}


def _feature_names(features) -> set[str]:
    """Feature names from a list of strings or of objects with a 'name'."""
    out = set()
    for f in features if isinstance(features, list) else []:
        name = f.get("name") if isinstance(f, dict) else f
        if isinstance(name, str):
            out.add(name)
    return out


def _blank(v) -> bool:
    return not (isinstance(v, str) and v.strip())


def _ml_semantics(ext: dict, rep: Report) -> None:
    """ml-artifact content rules of contracts 2.5.0 (hep-ml review 2026-10-13). Native for artifacts of contract
    2.5.0 or later; an older artifact gets them only in strict mode, so its promised outcome is unchanged.
    Errors: blank grouping key, empty model_hash, labels or features, training_domain keyed on a variable that is not a
    feature or with a range that is not [lo, hi] with lo < hi, a failed split-overlap check or test groups that are
    not disjoint, a missing or incomplete calibration where the output must be calibrated (output_semantics
    probability or density-ratio, task inference), a calibration evaluated on its fit sample. Unresolved: overlap check
    not run, no domain-shift check for a classifier or regressor with downstream validation. Warnings: no overlap check
    recorded, negative weights dropped, no seeds."""
    splits: Any = ext.get("splits") if isinstance(ext.get("splits"), dict) else {}
    gk = splits.get("grouping_key")
    if isinstance(gk, str) and gk and not gk.strip():
        rep.add("error", "$.extension.splits.grouping_key", "ml.no_grouping", "the grouping key is blank (leakage control)")
    if _blank(ext.get("model_hash")):
        rep.add("error", "$.extension.model_hash", "ml.model_hash_missing", "model_hash is empty: the artifact names no model")
    for key in ("labels", "features"):
        if key == "labels" and ext.get("supervision") == "unsupervised":
            continue  # anomaly detection without labels (2.8.0); its validation block is checked in _ml_semantics_v2
        if not ext.get(key):
            rep.add("error", f"$.extension.{key}", f"ml.{key}_missing",
                    f"{key} is empty" + (": list the targets (class labels, regression targets or generated variables)"
                                         if key == "labels" else ": list the model inputs"))
    names = _feature_names(ext.get("features"))
    # simulation-based inference declares its training domain on the parameters theta too (2.8.0)
    names |= {x for x in ext.get("parameters") or [] if isinstance(x, str)} if isinstance(ext.get("parameters"), list) else set()
    dom: Any = ext.get("training_domain") if isinstance(ext.get("training_domain"), dict) else {}
    for var, rng in dom.items():
        if var not in names:
            rep.add("error", f"$.extension.training_domain.{var}", "ml.training_domain_unknown_feature",
                    f"training_domain names '{var}', which is not a feature {sorted(names)}")
        if not (isinstance(rng, list) and len(rng) == 2 and all(_is_num(x) for x in rng)):
            rep.add("error", f"$.extension.training_domain.{var}", "ml.training_domain_range",
                    f"the range of '{var}' must be [lo, hi] with numbers, got {rng!r}")
        elif rng[0] >= rng[1]:
            rep.add("error", f"$.extension.training_domain.{var}", "ml.training_domain_range",
                    f"the range of '{var}' is [{rng[0]}, {rng[1]}]: lo must be below hi")
    oc: Any = splits.get("overlap_check")
    if not isinstance(oc, dict):
        rep.add("warning", "$.extension.splits.overlap_check", "ml.split_overlap_unchecked",
                "no split-overlap check is recorded: run check_split_integrity.py and record its result")
    elif oc.get("result") == "fail":
        rep.add("error", "$.extension.splits.overlap_check", "ml.split_overlap",
                "the split-overlap check failed: the test metrics measure leakage, not generalization")
    elif oc.get("result") == "not-run":
        rep.add("unresolved", "$.extension.splits.overlap_check", "ml.split_overlap_not_run",
                "the split-overlap check was not run (or ran on incomplete group metadata): leakage is not excluded")
    if splits.get("test_groups_disjoint") is False:
        rep.add("error", "$.extension.splits.test_groups_disjoint", "ml.split_overlap",
                "test groups also appear in training or validation")
    cal: Any = ext.get("calibration")
    needs_cal = ext.get("output_semantics") in CALIBRATED_OUTPUTS or ext.get("task") == "inference"
    if cal is None and needs_cal:
        why = f"output_semantics '{ext['output_semantics']}'" if ext.get("output_semantics") in CALIBRATED_OUTPUTS else "task inference"
        rep.add("error", "$.extension.calibration", "ml.calibration_missing",
                f"{why} is read as calibrated: record the calibration and its validation on a held-out sample")
    elif isinstance(cal, dict):
        val: Any = cal.get("validation") if isinstance(cal.get("validation"), dict) else None
        missing = [k for k in ("method", "fit_sample") if _blank(cal.get(k))]
        if val is None:
            missing.append("validation")
        else:
            missing += [f"validation.{k}" for k in ("metric", "sample") if _blank(val.get(k))]
            missing += ["validation.after"] if "after" not in val else []
        if missing:
            rep.add("error", "$.extension.calibration", "ml.calibration_incomplete",
                    f"calibration needs {', '.join(missing)} ({{method, fit_sample, validation: {{metric, sample, before?, after}}}})")
        if val is not None and not _blank(cal.get("fit_sample")) and cal.get("fit_sample") == val.get("sample"):
            rep.add("error", "$.extension.calibration.validation.sample", "ml.calibration_on_fit_sample",
                    f"calibration evaluated on its fit sample '{cal['fit_sample']}': validate it on a disjoint sample")
    w: Any = ext.get("weights")
    if isinstance(w, dict) and w.get("negative_weight_treatment") == "dropped":
        rep.add("warning", "$.extension.weights.negative_weight_treatment", "ml.negative_weights_dropped",
                "negative weights were dropped: the trained density is biased unless the effect is shown to be negligible")
    env: Any = ext.get("environment")
    if not (isinstance(env, dict) and isinstance(env.get("seeds"), dict) and env["seeds"]):
        rep.add("warning", "$.extension.environment.seeds", "ml.seeds_missing",
                "no seeds recorded: the training run cannot be reproduced or its seed variance estimated")
    ds: Any = ext.get("domain_shift")
    if ext.get("task") in DOMAIN_SHIFT_TASKS and ext.get("downstream_validation"):
        if not isinstance(ds, dict) or ds.get("status") == "not-checked":
            rep.add("unresolved", "$.extension.domain_shift", "ml.domain_shift_missing",
                    "no domain-shift check: a simulation-trained model must be checked on data or control samples before use")
        elif ds.get("status") == "failed":
            rep.add("unresolved", "$.extension.domain_shift", "ml.domain_shift_failed",
                    "the domain-shift check failed: correct or bound the data/simulation difference before use")


ML_SEMANTICS_V2_FROM = "2.8.0"  # ml-artifact rules of the hep-ml audit (PML) apply natively from this version


def _sample_name(value) -> str:
    """Comparison form of a sample name or path: stripped, backslashes as '/', '.' segments ('./x', 'a/./x') and
    repeated or trailing separators removed, case folded; '..' is kept (resolving it needs the file system)."""
    text = str(value).strip().replace("\\", "/")
    parts = [part for part in text.split("/") if part not in ("", ".")]
    return (("/" if text.startswith("/") else "") + "/".join(parts)).casefold()


def _ml_semantics_v2(doc: dict, ext: dict, vocab: Vocabulary, rep: Report, native: bool = True) -> None:
    """ml-artifact rules of contracts 2.8.0 (hep-ml audit, PML): the six SKILL.md invariants are checked as claims,
    not as fields present. Native for artifacts of contract 2.8.0 or later; an older artifact gets them in strict
    mode and at the gate (`native` is False there: rules that only a 2.8.0 field can satisfy are warnings)."""
    cal: Any = ext.get("calibration") if isinstance(ext.get("calibration"), dict) else None
    if cal is not None:
        val: Any = cal.get("validation") if isinstance(cal.get("validation"), dict) else {}
        sc: Any = cal.get("sample_check") if isinstance(cal.get("sample_check"), dict) else {}
        fh, eh = sc.get("fit_sha256"), sc.get("eval_sha256")
        same = None
        if sc.get("disjoint") is False:
            same = "the calibration tool recorded the fit and evaluation samples as not disjoint"
        elif isinstance(fh, str) and isinstance(eh, str) and fh and fh == eh:
            same = f"the fit and evaluation samples have the same sha256 ({fh[:12]}...)"
        elif not (_blank(cal.get("fit_sample")) or _blank(val.get("sample"))) and \
                _sample_name(cal["fit_sample"]) == _sample_name(val["sample"]):
            same = f"'{cal['fit_sample']}' and '{val['sample']}' name the same sample"
        if same and cal.get("fit_sample") != val.get("sample"):  # the exact-name case is reported by the 2.5.0 rule
            rep.add("error", "$.extension.calibration", "ml.calibration_on_fit_sample",
                    f"calibration evaluated on its fit sample: {same}; validate it on a disjoint sample")
    _ml_domain_shift_v2(ext, rep, native)
    _ml_downstream_v2(ext, vocab, rep, native)
    if ext.get("task") in SEMANTICS_REQUIRED_TASKS and "output_semantics" not in ext:
        rep.add("unresolved" if native else "warning", "$.extension.output_semantics", "ml.output_semantics_missing",
                f"a {ext.get('task')} model must say what its output means (probability, score, density-ratio, "
                "regression-value): a consumer cannot tell whether it may read it as a probability")
    _ml_task_blocks_v2(doc, ext, rep, native)
    _ml_weights_calibration_v2(ext, rep, native)
    _key_checks(ext, ML_KEYS["extension"], "$.extension", rep, kind="ml")
    for block in ("splits", "calibration", "domain_shift", "weights", "environment"):
        if isinstance(ext.get(block), dict):
            _key_checks(ext[block], ML_KEYS[block], f"$.extension.{block}", rep, kind="ml")


SEMANTICS_REQUIRED_TASKS = {"classification", "inference", "regression"}
TASK_SEMANTICS = {"classification": {"probability", "score"}, "regression": {"regression-value"},
                  "generation": {"generated-sample"}, "surrogate": {"regression-value", "score", "probability", "density-ratio"},
                  "inference": {"density-ratio", "probability", "score"}, "reweighting": {"density-ratio", "score"}}
# task -> (block, required keys); a key may be satisfied by any of the alternatives in a tuple
TASK_BLOCKS = {
    "regression": ("regression_validation", ("response_vs_truth", "response_vs_reco", "closure_alt_spectrum",
                                             "outlier_fraction")),
    "generation": ("generative_validation", ("observables", "two_sample_test", "conditioning_range")),
    "inference": ("sbi_validation", (("coverage", "sbc", "tarp"), "handoff")),
    "surrogate": ("extrapolation_policy", ("action", "consumer")),
    "reweighting": ("reweighting_validation", ("closure", "prior_dependence", "unmatched_events")),
}
KNOWN_SKILLS = frozenset(skill_names.SKILLS)
MODEL_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
UNBOUNDED = 1e30
ROW_LEVEL_KEYS = {"row", "row_id", "rowid", "row index", "index", "idx", "entry", "entry_number", "sample_index",
                  "none", "random"}
PRECISIONS = {"fp64", "fp32", "tf32", "bf16", "fp16", "mixed-bf16", "mixed-fp16", "int8"}
DEVICE_RE = re.compile(r"^(cpu|cuda(:\d+)?|mps|xpu(:\d+)?|tpu|gpu(:\d+)?|rocm(:\d+)?)$", re.I)
CALIBRATION_SCOPES = {"top-label", "classwise", "all-classes"}


BALANCING_NONE = {None, "", "none", "no", "unweighted"}


def _ml_weights_calibration_v2(ext: dict, rep: Report, native: bool) -> None:
    """Weights and calibration outcomes (PML-WP1.4: ML-K09, ML-K14, ML-C27)."""
    level = "error" if native else "warning"
    x = "$.extension"
    w: Any = ext.get("weights")
    if isinstance(w, str):
        rep.add(level, f"{x}.weights", "ml.weights_unstructured",
                f"weights {w!r} is free text: declare {{source, negative_weight_treatment, used_in, training, evaluation}}")
    elif isinstance(w, dict):
        used = w.get("used_in") if isinstance(w.get("used_in"), list) else None
        if used is not None and not used:
            rep.add("error", f"{x}.weights.used_in", "ml.weights_used_in_empty",
                    "weights.used_in is empty: say where the weights enter (loss, metrics, calibration, templates)")
        if used:
            cb = w.get("class_balancing")
            balanced = (cb not in BALANCING_NONE if isinstance(cb, str) or cb is None else bool(cb)) or \
                isinstance(w.get("training"), dict)
            if balanced and "loss" not in used:
                rep.add("error", f"{x}.weights.used_in", "ml.weights_used_in_inconsistent",
                        "training weights (class balancing or a training block) are declared but used_in has no 'loss'")
            if "calibration" in used and not isinstance(ext.get("calibration"), dict):
                rep.add("error", f"{x}.weights.used_in", "ml.weights_used_in_inconsistent",
                        "used_in names 'calibration' but the artifact records no calibration")
            if len(set(used)) != len(used):
                rep.add("error", f"{x}.weights.used_in", "ml.weights_used_in_inconsistent", "used_in lists an entry twice")
            if "loss" in used and not (isinstance(w.get("training"), dict) and isinstance(w.get("evaluation"), dict)):
                # hep-ml invariant ML-05: training and evaluation weights are recorded separately
                rep.add("warning", f"{x}.weights", "ml.weights_not_separated",
                        "weights enter the loss: record the training weights and the evaluation weights separately "
                        "(weights.training and weights.evaluation)")
        top = w.get("negative_weight_treatment")
        tr: Any = w.get("training") if isinstance(w.get("training"), dict) else {}
        if top == "none-present" and (tr.get("negative_weight_treatment") not in (None, "none-present", "signed")
                                      or (_is_num(tr.get("n_negative")) and tr["n_negative"] > 0)):
            rep.add("error", f"{x}.weights", "ml.weights_contradiction",
                    "negative_weight_treatment none-present, but the training weights treat or count negative weights")
        if "abs" in (top, tr.get("negative_weight_treatment")):
            rep.add("warning", f"{x}.weights.negative_weight_treatment", "ml.negative_weights_abs",
                    "|w| training biases the learned density where negative weights matter; show the effect is small or "
                    "use a resampling treatment")
        if native and not (isinstance(w.get("training"), dict) and isinstance(w.get("evaluation"), dict)):
            rep.add("warning", f"{x}.weights", "ml.weights_not_split",
                    "record training and evaluation weights separately (weights.training, weights.evaluation)")
    cal: Any = ext.get("calibration")
    if isinstance(cal, dict):
        val: Any = cal.get("validation") if isinstance(cal.get("validation"), dict) else {}
        if "after" in val and not _is_num(val["after"]):
            rep.add("error", f"{x}.calibration.validation.after", "ml.calibration_after_not_numeric",
                    f"calibration.validation.after must be a number, got {val['after']!r}")
        if isinstance(cal.get("fit_sample"), str) and _sample_name(cal["fit_sample"]) in TRAINING_SAMPLE_NAMES:
            rep.add("error", f"{x}.calibration.fit_sample", "ml.calibration_on_training_sample",
                    "calibration fitted on the training sample: fit it on validation (the model is overconfident there)")
        before, after = val.get("before"), val.get("after")
        if _is_num(before) and _is_num(after):
            tol = max([v for v in (val.get("after_uncertainty"), val.get("floor"), 0.0) if _is_num(v)])
            if after > before + tol:
                rep.add("unresolved", f"{x}.calibration.validation", "ml.calibration_not_improving",
                        f"{val.get('metric', 'metric')} after calibration ({after:.4g}) is worse than before ({before:.4g}) "
                        f"by more than its uncertainty or floor ({tol:.4g}): the map does not calibrate on this sample")


def _walk_keys(value, key):
    """Every value stored under `key` anywhere inside value."""
    if isinstance(value, dict):
        for k, v in value.items():
            if k == key:
                yield v
            yield from _walk_keys(v, key)
    elif isinstance(value, list):
        for v in value:
            yield from _walk_keys(v, key)


def _ml_task_blocks_v2(doc: dict, ext: dict, rep: Report, native: bool) -> None:
    """Task-specific validation and claim checks (PML-WP1.3: ML-K10, K08, K07, K12, K16)."""
    level = "error" if native else "warning"
    x = "$.extension"
    task, sem = ext.get("task"), ext.get("output_semantics")
    if task in TASK_SEMANTICS and sem is not None and sem not in TASK_SEMANTICS[task]:
        rep.add("error", f"{x}.output_semantics", "ml.output_semantics_task_mismatch",
                f"output_semantics '{sem}' does not fit task '{task}' (allowed: {sorted(TASK_SEMANTICS[task])})")
    if task in TASK_BLOCKS:
        block, keys = TASK_BLOCKS[task]
        val: Any = ext.get(block)
        if not isinstance(val, dict):
            rep.add(level, f"{x}.{block}", "ml.task_validation_missing",
                    f"a {task} model needs '{block}' ({', '.join('/'.join(k) if isinstance(k, tuple) else k for k in keys)})")
        else:
            missing = [("/".join(k) if isinstance(k, tuple) else k) for k in keys
                       if not any(a in val for a in (k if isinstance(k, tuple) else (k,)))]
            if missing:
                rep.add(level, f"{x}.{block}", "ml.task_validation_incomplete", f"'{block}' lacks {', '.join(missing)}")
            if task == "generation" and isinstance(val.get("two_sample_test"), dict) and \
                    "power" not in val["two_sample_test"]:
                rep.add(level, f"{x}.{block}.two_sample_test", "ml.two_sample_power_missing",
                        "a classifier two-sample test needs its power, measured with an injected distortion: "
                        "AUC 0.5 alone shows nothing")
            if task == "surrogate" and val.get("action") not in (None, "flag", "reject", "bounded"):
                rep.add("error", f"{x}.{block}.action", "ml.extrapolation_policy_action",
                        f"extrapolation_policy.action must be flag, reject or bounded, not {val.get('action')!r}")
    for handoff in _walk_keys(ext, "handoff"):
        if isinstance(handoff, str) and handoff not in KNOWN_SKILLS:
            rep.add("error", f"{x}", "ml.handoff_unknown",
                    f"handoff '{handoff}' is not a skill of this plugin ({sorted(KNOWN_SKILLS)})")
    if ext.get("supervision") == "unsupervised" and not isinstance(ext.get("anomaly_validation"), dict):
        rep.add(level, f"{x}.anomaly_validation", "ml.task_validation_missing",
                "an unsupervised (anomaly-detection) model needs 'anomaly_validation' (background_only, "
                "signal_injection)")
    # training domain covers every feature, with finite bounds
    feats = _feature_names(ext.get("features"))
    dom: Any = ext.get("training_domain")
    if isinstance(dom, dict) and feats:
        if not dom:
            rep.add("unresolved", f"{x}.training_domain", "ml.training_domain_missing",
                    "the training domain is empty: inputs outside it cannot be flagged at inference time")
        else:
            uncovered = sorted(feats - set(dom))
            if uncovered:
                rep.add("unresolved", f"{x}.training_domain", "ml.training_domain_partial",
                        f"the training domain does not cover {uncovered}")
            wide = sorted(k for k, r in dom.items() if isinstance(r, list) and any(_is_num(b) and abs(b) > UNBOUNDED for b in r))
            if wide:
                rep.add("unresolved", f"{x}.training_domain", "ml.training_domain_unbounded",
                        f"the training domain of {wide} is effectively unbounded (|bound| > {UNBOUNDED:g}): declare the "
                        "range the model was trained on")
    mh = ext.get("model_hash")
    if isinstance(mh, str) and mh.strip() and not MODEL_HASH_RE.match(mh):
        rep.add("error", f"{x}.model_hash", "ml.model_hash_malformed",
                f"model_hash {mh!r} is not 'sha256:' and 64 lower-case hex digits")
    # inputs and labels (K16)
    labels: list = ext["labels"] if isinstance(ext.get("labels"), list) else []
    if task == "classification" and len(labels) == 1:
        rep.add("error", f"{x}.labels", "ml.single_label", "a classifier needs at least two classes")
    raw = [f.get("name") if isinstance(f, dict) else f for f in ext.get("features") or []]
    dups = sorted({f for f in raw if isinstance(f, str) and raw.count(f) > 1})
    if dups:
        rep.add("error", f"{x}.features", "ml.duplicate_features", f"features listed twice: {dups}")
    same = sorted({str(lab) for lab in labels if isinstance(lab, str)} & feats)
    if same:
        rep.add("error", f"{x}.labels", "ml.label_is_feature", f"{same} is both a label and a feature (target leakage)")
    for i, step in enumerate(ext.get("preprocessing") or []):
        fit_on = step.get("fit_on") if isinstance(step, dict) else None
        if isinstance(fit_on, str) and _sample_name(fit_on) not in TRAINING_SAMPLE_NAMES:
            rep.add("error", f"{x}.preprocessing[{i}].fit_on", "ml.preprocessing_not_on_train",
                    f"preprocessing fitted on '{fit_on}': fit it on the training split only, or the held-out metrics "
                    "leak information from the samples they judge")
    units: Any = ext.get("units")
    if isinstance(units, dict) and feats:
        extra = sorted(set(units) - feats - {p for p in ext.get("parameters") or [] if isinstance(p, str)})
        if extra:
            rep.add("error", f"{x}.units", "ml.units_unknown_feature", f"units given for {extra}, which are not features")
    if any(isinstance(v, str) and _sample_name(v) == "test" for v in _walk_keys(ext.get("metrics"), "threshold_from")):
        rep.add("error", f"{x}.metrics", "ml.threshold_from_test",
                "a working-point threshold fixed on the test split: fix it on validation and apply it unchanged to test")
    # splits (M06, M07)
    splits: Any = ext.get("splits") if isinstance(ext.get("splits"), dict) else {}
    gk = splits.get("grouping_key")
    if isinstance(gk, str) and _sample_name(gk) in ROW_LEVEL_KEYS:
        rep.add("unresolved", f"{x}.splits.grouping_key", "ml.grouping_row_level",
                f"grouping key '{gk}' is row-level: rows of one run, event, period or seed are correlated; group by "
                "that unit, or state why rows are independent")
    oc: Any = splits.get("overlap_check")
    if isinstance(oc, dict) and oc.get("result") == "pass" and _blank(oc.get("report")):
        rep.add("unresolved", f"{x}.splits.overlap_check", "ml.split_check_unverified",
                f"a split-overlap 'pass' from '{oc.get('tool')}' with no report behind it is a claim, not a check")
    # environment (M32, M33)
    env: Any = ext.get("environment")
    if isinstance(env, dict):
        if _blank(env.get("torch_version")) and _blank(env.get("framework")):
            rep.add("warning", f"{x}.environment", "ml.framework_version_missing",
                    "no framework and version recorded (torch_version or framework)")
        prec, dev = env.get("precision"), env.get("device")
        if isinstance(prec, str) and prec.lower() not in PRECISIONS:
            rep.add("warning", f"{x}.environment.precision", "ml.precision_free_text",
                    f"precision {prec!r} is not one of {sorted(PRECISIONS)}")
        if isinstance(dev, str) and not DEVICE_RE.match(dev.strip()):
            rep.add("warning", f"{x}.environment.device", "ml.device_free_text",
                    f"device {dev!r} is not cpu, cuda[:n], mps, xpu, tpu or gpu")
    # multiclass calibration (M59)
    cal: Any = ext.get("calibration")
    if isinstance(cal, dict) and task == "classification" and len(labels) > 2 and \
            cal.get("scope") not in CALIBRATION_SCOPES:
        rep.add(level, f"{x}.calibration.scope", "ml.multiclass_calibration_scope",
                f"a {len(labels)}-class model calibrated without a scope: say whether the top label, each class or "
                "all classes were calibrated and validated (one binary metric does not cover the others)")
    # status claims (K12)
    status = set(doc.get("status") or [])
    observed_inputs = any("observed" in (i.get("status") or []) for i in doc.get("inputs") or [] if isinstance(i, dict))
    if "observed" in status and not observed_inputs:
        rep.add(level, "$.status", "ml.status_unsupported",
                "'observed' on an ml-artifact needs an input that carries 'observed' (the model was trained, "
                "calibrated or validated on data listed in inputs); a simulation-only model is not a result on data")
    if "validated-in-scope" in status:
        good = [d for d in ext.get("downstream_validation") or [] if isinstance(d, dict)
                and d.get("metric") not in PURE_ML_METRICS and d.get("passed") is True]
        if not (good and isinstance(splits.get("overlap_check"), dict) and splits["overlap_check"].get("result") == "pass"):
            rep.add(level, "$.status", "ml.status_unsupported",
                    "'validated-in-scope' needs a passed split check and at least one passed physics downstream item")

ML_KEYS = {
    "extension": {"task", "labels", "features", "splits", "training_domain", "preprocessing", "weights", "model_hash",
                  "calibration", "downstream_validation", "domain_shift", "environment", "output_semantics",
                  "source_files", "units", "metrics", "parameters", "supervision", "regression_validation",
                  "generative_validation", "sbi_validation", "extrapolation_policy", "anomaly_validation",
                  "reweighting_validation", "notes"},
    "splits": {"grouping_key", "overlap_check", "manifest", "test_groups_disjoint", "roles", "temporal"},
    "calibration": {"method", "params", "fit_sample", "validation", "sample_check", "outcome", "scope", "warnings"},
    "domain_shift": {"control_sample", "method", "result", "status", "outcome", "nuisance"},
    "weights": {"source", "negative_weight_treatment", "class_balancing", "used_in", "training", "evaluation"},
    "environment": {"torch_version", "framework", "device", "precision", "seeds"},
}


PURE_ML_METRICS = {"roc-auc", "accuracy", "loss", "calibration-ece"}
ML_ONLY_TEXT = re.compile(r"\b(auc|roc|accuracy|acc|loss|cross[ -]?entropy|log[ -]?loss|f1|precision|recall|ece|brier)\b", re.I)
BARE_TEXT = re.compile(r"^\s*(validated|valid|pass(ed)?|ok|done|yes|true|checked|good)\s*$", re.I)
DOWNSTREAM_KEYS = ("quantity_affected", "value", "criterion", "passed")
CRITERION_RE = re.compile(r"^\s*(abs\s*)?(<=|>=|<|>|==)\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$")
CRITERION_RANGE_RE = re.compile(r"^\s*(abs\s+)?in\s*\[\s*([-+]?[\d.eE+-]+)\s*,\s*([-+]?[\d.eE+-]+)\s*\]\s*$")


def _criterion_holds(value, criterion):
    """True/False when a numeric value and a criterion such as '>= 0.68', 'abs < 0.001' or 'in [0.9, 1.1]' can be
    compared, else None (the criterion is text, or the value is not a number)."""
    if not _is_num(value) or not isinstance(criterion, str):
        return None
    m = CRITERION_RE.match(criterion)
    if m:
        v, op, t = (abs(value) if m.group(1) else value), m.group(2), float(m.group(3))
        return {"<=": v <= t, ">=": v >= t, "<": v < t, ">": v > t, "==": v == t}[op]
    m = CRITERION_RANGE_RE.match(criterion)
    if m:
        try:
            lo, hi = float(m.group(2)), float(m.group(3))
        except ValueError:
            return None
        v = abs(value) if m.group(1) else value
        return lo <= v <= hi
    return None


def _ml_downstream_v2(ext: dict, vocab: Vocabulary, rep: Report, native: bool) -> None:
    """Structured downstream validation (PML-WP1.1, ML-K02): items {metric, quantity_affected, value, uncertainty?,
    criterion, passed, ref}, metric a term of ml_downstream_metrics. Errors: every item an ML metric or a bare pass
    (any contract version, under --strict), a 'passed' that contradicts a numeric value and criterion. Free-text items
    are errors from 2.8.0 and warnings for older artifacts under --strict."""
    dv: Any = ext.get("downstream_validation")
    if not isinstance(dv, list) or not dv:
        return
    p = "$.extension.downstream_validation"
    level = "error" if native else "warning"
    terms = vocab.core("ml_downstream_metrics")
    evidence = 0
    for i, item in enumerate(dv):
        metric = item.get("metric") if isinstance(item, dict) else item
        if isinstance(item, dict) and isinstance(metric, str) and metric in terms:
            if metric not in PURE_ML_METRICS:
                evidence += 1
            missing = [k for k in DOWNSTREAM_KEYS if k not in item]
            if missing:
                rep.add(level, f"{p}[{i}]", "ml.downstream_incomplete",
                        f"downstream item '{metric}' lacks {', '.join(missing)} ({{metric, quantity_affected, value, "
                        "uncertainty?, criterion, passed, ref}})")
            holds = _criterion_holds(item.get("value"), item.get("criterion"))
            if holds is not None and isinstance(item.get("passed"), bool) and holds != item["passed"]:
                rep.add("error", f"{p}[{i}]", "ml.downstream_passed_contradicts",
                        f"'{metric}' is marked passed={item['passed']}, but value {item['value']} "
                        f"{'meets' if holds else 'fails'} the criterion '{item['criterion']}'")
            continue
        text = " ".join(str(v) for v in item.values()) if isinstance(item, dict) else str(item)
        if not (ML_ONLY_TEXT.search(str(metric)) or BARE_TEXT.match(str(metric))):
            evidence += 1
        rep.add(level, f"{p}[{i}]", "ml.downstream_unstructured",
                f"downstream item {text[:60]!r} is free text: give {{metric (a term of ml_downstream_metrics), "
                "quantity_affected, value, criterion, passed, ref}")
    if not evidence:
        rep.add("error", p, "ml.downstream_ml_only",
                "every downstream item is an ML metric (AUC, accuracy, loss, ECE) or a bare pass: validate the effect "
                "on the physics result (efficiency at the working point, expected limit or uncertainty, closure, "
                "coverage, data/simulation agreement)")


TRAINING_SAMPLE_NAMES = {"train", "training", "train split", "training split", "train sample", "training sample",
                         "training set", "train set"}


def _ml_domain_shift_v2(ext: dict, rep: Report, native: bool) -> None:
    """Domain-shift record (PML-WP0.6, ML-K05): 'checked' says the check ran, outcome says what was done about it."""
    ds: Any = ext.get("domain_shift")
    if not isinstance(ds, dict):
        return
    p = "$.extension.domain_shift"
    if "status" not in ds:
        rep.add("unresolved", f"{p}.status", "ml.domain_shift_status_missing",
                "the domain-shift record has no status: say whether the check ran (checked, not-checked, failed)")
    control = ds.get("control_sample")
    if isinstance(control, str) and _sample_name(control) in TRAINING_SAMPLE_NAMES:
        rep.add("unresolved", f"{p}.control_sample", "ml.domain_shift_on_training_sample",
                f"the control sample '{control}' is the training sample: a domain-shift check compares the model's "
                "inputs or outputs on data (or a data-like control sample) with simulation")
    outcome = ds.get("outcome")
    if ds.get("status") == "checked" and outcome is None:
        rep.add("unresolved" if native else "warning", f"{p}.outcome", "ml.domain_shift_outcome_missing",
                "the check ran but its outcome is not recorded: no-shift, corrected, bounded-by-nuisance or uncorrected")
    if outcome in ("bounded-by-nuisance", "uncorrected") and not ds.get("nuisance"):
        rep.add("unresolved", f"{p}.nuisance", "ml.domain_shift_uncorrected",
                f"outcome {outcome} without a nuisance: a shift that is neither corrected nor carried by a nuisance "
                "parameter in the downstream likelihood biases the result")


THEORY_SEMANTICS_FROM = "2.6.0"  # theory-spec and prediction rules apply natively from this contract version
STRONG_STATUSES = {"formal-proof", "analytic-derivation"}


def _theory_semantics(doc: dict, ext: dict, vocab: Vocabulary, rep: Report) -> None:
    """theory-spec and prediction rules of contracts 2.6.0 (hep-theory audit 2026-10-13). Native for artifacts of
    contract 2.6.0 or later; an older artifact gets them only in strict mode, at the same level, so its promised outcome
    is unchanged.
    theory-spec: errors for a perturbative argument without an order, an asymptotic argument without a limit, a
    formal proof or analytic derivation with no check run, a check result outside check_results, an empty validity
    domain, and a cosmic-ray-propagation model without degenerate_directions; a warning for each core convention key
    that is neither given (a value or 'not-applicable') nor listed in 'inapplicable'.
    prediction: errors for 'observed', for 'validated-in-scope' without a linked theory-spec input that carries it,
    and for a scale envelope without an envelope_prescriptions term or with values that are not [min, max] (bounds
    per bin for a binned envelope); unresolved when neither theory_spec_ref nor derivation_status links the
    prediction to its derivation; a warning for a truncation without a truncation_methods term."""
    if doc.get("artifact_type") == "theory-spec":
        _theory_spec_rules(ext, vocab, rep)
    else:
        _prediction_rules(doc, ext, vocab, rep)


def _term_ok(vocab: Vocabulary, name: str, term) -> bool:
    return isinstance(term, str) and (vocab.has(name, term) or bool(NAMESPACED.match(term)))


def _theory_spec_rules(ext: dict, vocab: Vocabulary, rep: Report) -> None:
    conv: Any = ext.get("conventions") if isinstance(ext.get("conventions"), dict) else {}
    listed = set(ext.get("inapplicable") or [])
    core_keys = sorted(vocab.core("convention_keys"))
    absent = [k for k in core_keys if k not in listed and (conv.get(k) is None or (isinstance(conv.get(k), str)
                                                                                  and not conv[k].strip()))]
    if absent:
        rep.add("warning", "$.extension.conventions", "theory.conventions_incomplete",
                f"core convention keys {absent} are neither given nor marked 'not-applicable' (or listed in "
                "'inapplicable'): a conventions block travels with every derivation")
    status = ext.get("derivation_status")
    if status == "perturbative-argument" and _blank(ext.get("order")):
        rep.add("error", "$.extension.order", "theory.order_missing",
                "a perturbative argument states its order")
    if status == "asymptotic-argument" and _blank(ext.get("limit")):
        rep.add("error", "$.extension.limit", "theory.limit_missing",
                "an asymptotic argument states the limit it holds in ('limit')")
    checks = ext.get("checks_run") or []
    if status in STRONG_STATUSES and not checks:
        rep.add("error", "$.extension.checks_run", "theory.unchecked_strong_status",
                f"'{status}' with no check run: list the checks (units, limits, symmetries, ...) or lower the status")
    for i, c in enumerate(checks):
        if isinstance(c, dict) and not (isinstance(c.get("result"), str) and vocab.has("check_results", c["result"])):
            rep.add("error", f"$.extension.checks_run[{i}].result", "theory.check_result_vocab",
                    f"check result {c.get('result')!r} is not one of {sorted(vocab.core('check_results'))}")
    if ext.get("validity_domain") == {}:
        rep.add("error", "$.extension.validity_domain", "theory.validity_empty",
                "the validity domain is empty: state where the result holds")
    model: Any = ext.get("model") if isinstance(ext.get("model"), dict) else {}
    if model.get("family") == "cosmic-ray-propagation" and not any(
            not _blank(d) for d in ext.get("degenerate_directions") or []):
        rep.add("error", "$.extension.degenerate_directions", "theory.degeneracy_missing",
                "a cosmic-ray propagation model lists the parameter combinations the data cannot separate "
                "(degenerate_directions, e.g. 'D0/L')")


def _prediction_rules(doc: dict, ext: dict, vocab: Vocabulary, rep: Report) -> None:
    status = set(doc.get("status", []))
    if "observed" in status:
        rep.add("error", "$.status", "prediction.status_upgraded", "a prediction is not 'observed'")
    if "validated-in-scope" in status:
        ref = ext.get("theory_spec_ref")
        linked = [i for i in doc.get("inputs", []) if isinstance(i, dict) and i.get("artifact_type") == "theory-spec"
                  and (ref is None or ref in (i.get("ref"), i.get("artifact_id")))]
        if not any("validated-in-scope" in (i.get("status") or []) for i in linked):
            rep.add("error", "$.status", "prediction.status_upgraded",
                    "'validated-in-scope' needs a linked theory-spec input that carries it (a status is never upgraded "
                    "when a result is reused)")
    if _blank(ext.get("theory_spec_ref")) and _blank(ext.get("derivation_status")):
        rep.add("unresolved", "$.extension", "prediction.spec_unlinked",
                "no theory_spec_ref and no derivation_status: the prediction is not linked to its derivation")
    vals: Any = ext.get("values") if isinstance(ext.get("values"), dict) else {}
    n_bins = len(vals.get("values") or [])
    for i, u in enumerate(ext.get("uncertainties", [])):
        path = f"$.extension.uncertainties[{i}]"
        if u.get("kind") == "scale-envelope":
            if not _term_ok(vocab, "envelope_prescriptions", u.get("prescription")):
                rep.add("error", f"{path}.prescription", "prediction.envelope_prescription",
                        f"a scale envelope names its prescription, one of "
                        f"{sorted(vocab.core('envelope_prescriptions'))} or a namespaced '<ns>:<term>'; "
                        f"got {u.get('prescription')!r}")
            ev = u.get("values")
            if ev is not None and not (len(ev) == 2 and ev[0] <= ev[1]):
                rep.add("error", f"{path}.values", "prediction.envelope_prescription",
                        f"envelope values must be one [min, max] pair with min <= max, got {ev}; a binned envelope "
                        "uses bounds {lower, upper} with one entry per bin")
            b: Any = u.get("bounds")
            if isinstance(b, dict):
                lo, hi = b.get("lower") or [], b.get("upper") or []
                if len(lo) != len(hi) or (n_bins and len(lo) != n_bins) or any(x > y for x, y in zip(lo, hi)):
                    rep.add("error", f"{path}.bounds", "prediction.envelope_prescription",
                            f"bounds need lower <= upper bin by bin and one entry per bin ({n_bins} bins); "
                            f"got {len(lo)} lower and {len(hi)} upper")
        if u.get("kind") == "truncation" and not _term_ok(vocab, "truncation_methods", u.get("method")):
            rep.add("warning", f"{path}.method", "prediction.truncation_method",
                    f"a truncation estimate names its method, one of "
                    f"{sorted(vocab.core('truncation_methods'))}; got {u.get('method')!r}")
MEASUREMENT_SEMANTICS_FROM = "2.6.0"  # measurement-spec semantic rules apply natively from this contract version
MISSING_MARKERS = ("unknown", "not-provided")  # 'not-applicable' is a statement, not an open input
NORMALIZATION_CORRECTIONS = {"luminosity": "integrated-luminosity", "exposure": "exposure", "livetime": "live-time"}
ESTIMAND_MIN_WORDS = 5
MEASUREMENT_KEYS = {
    "extension": {"estimand", "observable", "species_or_process", "period", "selections", "backgrounds", "corrections",
                  "systematics", "blinding", "experiment_fields", "ratio", "no_backgrounds_reason", "notes", "eras",
                  "coupled_backgrounds"},
    "selections": {"name", "id", "definition", "conditional_denominator", "validation", "efficiency", "evidence_ids",
                   "notes", "status", "order", "applied_in", "variable", "value", "unit", "ref", "region"},
    "backgrounds": {"name", "id", "estimator", "control_region", "constraint", "closure", "normalization", "shape",
                    "evidence_ids", "notes", "status", "processes", "method", "ref", "uncertainty", "value", "unit",
                    "transfer_factor", "template"},
    "corrections": {"effect_id", "category", "applied_in", "value", "unit", "exact_zero", "ref", "evidence_ids",
                    "source", "notes", "uncertainty", "status", "conditional_denominator", "method", "definition",
                    "name", "factor_of"},
    "systematics": {"name", "source", "effect", "applied_via", "affected_processes", "correlation_key", "payload",
                    "validation", "magnitude", "evidence_ids", "notes", "status", "correlation_evidence",
                    "proposed_scheme", "ref", "periods", "regions", "value", "unit", "scaling", "era_correlation"},
    "eras": {"id", "start", "end", "kind", "source", "corrections", "shared_corrections", "versions", "evidence_ids",
             "notes"},
    "coupled_backgrounds": {"background", "species", "treatment", "source", "evidence_ids", "notes"},
}
# v6.3 D05a: correction keys of a measurement-spec, known only when the spec declares the capability (an older reader
# refuses such a spec through contract.unknown_capability; without it the keys stay measurement.unknown_key warnings).
# The R4 keys follow contracts/schemas/recipe.json (correction_key); application_id names a recipe step_id.
CORRECTION_KEYS_CAPABILITY = "measurement:correction-keys-v1"
CORRECTION_KEY_PATTERNS = {"target_scope": r"[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,127}", "calibration_digest": r"[0-9a-f]{64}|none",
                           "variation_id": r"[a-z0-9][a-z0-9_-]{0,63}", "stage": r"[a-z0-9][a-z0-9_-]{0,63}",
                           "application_id": r"[a-z0-9][a-z0-9_-]{0,63}"}
_ISO_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?([T ].*)?$")


def _norm_id(text) -> str:
    """Comparison form of an identifier: case, '-', '_' and spaces ignored."""
    return re.sub(r"[\s_-]+", "", str(text)).lower()


KEY_CHECK_NOUNS = {"measurement": ("measurement-spec", " (profile fields go under experiment_fields)"),
                   "ml": ("ml-artifact", " (namespaced keys '<ns>:<key>' are allowed for extra fields)"),
                   "response": ("response", " (namespaced '<ns>:<key>' fields are accepted)")}


def _key_checks(item, known: set[str], path: str, rep: Report, kind: str = "measurement") -> None:
    """Unknown keys are warnings; a near-miss of a known key is an error (the field it should fill is missing).
    `kind` names the artifact family: codes are <kind>.misspelled_key and <kind>.unknown_key."""
    import difflib
    if not isinstance(item, dict):
        return
    noun, hint = KEY_CHECK_NOUNS.get(kind, (kind, ""))
    for key in sorted(item):
        if key in known or NAMESPACED.match(key):
            continue
        near = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.85)
        if near:
            rep.add("error", f"{path}.{key}", f"{kind}.misspelled_key",
                    f"'{key}' is not a {noun} field; did you mean '{near[0]}'?")
        else:
            rep.add("warning", f"{path}.{key}", f"{kind}.unknown_key",
                    f"'{key}' is not a {noun} field: no rule or consumer reads it{hint}")


def _markers(value, path: str):
    """(path, marker) for every string equal to a missing marker inside value."""
    if isinstance(value, str) and value in MISSING_MARKERS:
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _markers(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _markers(v, f"{path}[{i}]")


def _listed(path: str, unresolved) -> bool:
    """An unresolved_inputs entry names this field: it contains the field's key (or its path)."""
    key = re.sub(r"\[\d+\]", "", path.rsplit(".", 1)[-1])
    rel = path.replace("$.extension.", "")
    entries = [str(e) for e in unresolved] if isinstance(unresolved, list) else []
    return any(rel in e or re.search(rf"(^|[^A-Za-z0-9_]){re.escape(key)}([^A-Za-z0-9_]|$)", e) for e in entries)


def _is_zero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0


# Strings that fill a required text field without stating anything (triage T11, T12). A missing marker ('unknown',
# 'not-provided') is not one of them: it goes through the unresolved_inputs rule.
PLACEHOLDER_TOKENS = frozenset({"n/a", "na", "none", "null", "tbd", "todo", "-", "--", "?", "..."})


def _placeholder(v) -> bool:
    """A non-blank string that is only a placeholder token (case and surrounding space ignored)."""
    return isinstance(v, str) and v.strip().lower() in PLACEHOLDER_TOKENS


def _mask_names_something(mask: dict) -> bool:
    """A blinding mask with a non-blank region name or an interval dict with a non-blank variable (triage T14)."""
    regions, intervals = mask.get("regions"), mask.get("intervals")
    return any(not _blank(r) for r in (regions if isinstance(regions, list) else [])) or \
        any(isinstance(iv, dict) and not _blank(iv.get("variable")) for iv in (intervals if isinstance(intervals, list) else []))


def _measurement_semantics(doc: dict, ext: dict, vocab: Vocabulary, rep: Report) -> None:
    """measurement-spec rules of contracts 2.6.0 (hep-measurement audit 2026-10-13): the SKILL.md invariants. Native for
    artifacts of contract 2.6.0 or later; an older artifact gets them only in strict mode, so its promised outcome is
    unchanged. Errors: no estimand sentence; a variable without unit and binning, no phase_space or frame; no
    selection, or a blank conditional denominator; no background without no_backgrounds_reason, a background without
    estimator or without control_region/constraint; a correction repeated (case and separators ignored), a category
    outside response_corrections / '<x>_efficiency' / '<ns>:<term>', a repeated category or a bare 'efficiency' next to
    a '<x>_efficiency', a chain item also in observable.included_corrections, a luminosity/exposure/livetime
    correction next to the normalization of the same kind; a zero normalization or correction value without
    exact_zero, a shape-only normalization with a numeric value; no systematic, a blank applied_via, a repeated
    systematic name; a missing marker not named in unresolved_inputs; a blinded spec without mask, or blinded with
    'observed' status; a ratio quantity without ratio block, a ratio of a quantity to itself, no cancellation entry; a
    period ending before it starts; a misspelled key. Unresolved: a listed missing marker, a background without
    closure. Warnings: partial selection validation, a 'cancels' entry without verification, unknown keys; a conditional
    denominator that is not a string or is a placeholder ('n/a', 'none', 'tbd', ...), a placeholder
    no_backgrounds_reason, a blinding mask that names nothing (triage 2026-10-22: warnings, so older specs keep their
    outcome)."""
    obs: Any = ext.get("observable") if isinstance(ext.get("observable"), dict) else {}
    x = "$.extension"
    est = ext.get("estimand")
    if not (isinstance(est, str) and est.strip()):
        rep.add("error", f"{x}.estimand", "measurement.estimand_missing",
                "state the estimand in one sentence: quantity, species or process, variable and range, level, frame, "
                "what is held fixed")
    elif est not in MISSING_MARKERS and len(est.split()) < ESTIMAND_MIN_WORDS:
        rep.add("error", f"{x}.estimand", "measurement.estimand_not_a_sentence",
                f"'{est}' is not an estimand sentence (quantity, species or process, variable, range, level)")
    for i, var in enumerate(obs.get("variables", []) if isinstance(obs.get("variables"), list) else []):
        if isinstance(var, dict) and not (str(var.get("unit", "")).strip() and ("edges" in var or "points" in var)):
            rep.add("error", f"{x}.observable.variables[{i}]", "measurement.variable_incomplete",
                    f"variable '{var.get('name')}' needs a unit and edges or points")
    for key in ("phase_space", "frame"):
        if key not in obs:
            rep.add("error", f"{x}.observable.{key}", f"measurement.{key}_missing",
                    f"the observable needs '{key}' (or a missing marker listed in unresolved_inputs)")
    sels: Any = ext.get("selections")
    if isinstance(sels, list) and not sels:
        rep.add("error", f"{x}.selections", "measurement.selections_empty", "a measurement needs at least one selection")
    for i, s in enumerate(sels if isinstance(sels, list) else []):
        if not isinstance(s, dict):
            continue
        den = s.get("conditional_denominator")
        if isinstance(den, str) and not den.strip():
            rep.add("error", f"{x}.selections[{i}].conditional_denominator", "measurement.denominator_blank",
                    f"selection '{s.get('name')}' needs its conditional denominator")
        elif not isinstance(den, str) or _placeholder(den):  # a warning: older specs with these values stay valid
            rep.add("warning", f"{x}.selections[{i}].conditional_denominator", "measurement.denominator_placeholder",
                    f"selection '{s.get('name')}': conditional denominator {den!r} names no sample; state what the "
                    "selection is conditional on, or write a missing marker listed in unresolved_inputs")
        val = s.get("validation")
        if isinstance(val, dict) and not all(not _blank(val.get(k)) for k in ("metric", "threshold", "action")):
            rep.add("warning", f"{x}.selections[{i}].validation", "measurement.selection_validation_partial",
                    "selection validation needs metric, threshold and action")
        _key_checks(s, MEASUREMENT_KEYS["selections"], f"{x}.selections[{i}]", rep)
    bkgs: Any = ext.get("backgrounds")
    if isinstance(bkgs, list) and not bkgs and _blank(ext.get("no_backgrounds_reason")):
        rep.add("error", f"{x}.backgrounds", "measurement.backgrounds_empty",
                "no background listed: give each background, or state why there is none in no_backgrounds_reason")
    elif isinstance(bkgs, list) and not bkgs and _placeholder(ext.get("no_backgrounds_reason")):
        rep.add("warning", f"{x}.no_backgrounds_reason", "measurement.no_backgrounds_reason_placeholder",
                f"no_backgrounds_reason {ext.get('no_backgrounds_reason')!r} states no reason: say why the "
                "measurement has no background")
    for i, b in enumerate(bkgs if isinstance(bkgs, list) else []):
        if not isinstance(b, dict):
            continue
        p = f"{x}.backgrounds[{i}]"
        if _blank(b.get("estimator")):
            rep.add("error", f"{p}.estimator", "measurement.background_estimator_missing",
                    f"background '{b.get('name')}' needs an estimator")
        if _blank(b.get("control_region")) and _blank(b.get("constraint")):
            rep.add("error", p, "measurement.background_constraint_missing",
                    f"background '{b.get('name')}' needs a control_region or a constraint")
        if _blank(b.get("closure")):
            rep.add("unresolved", f"{p}.closure", "measurement.background_closure_missing",
                    f"background '{b.get('name')}' has no closure test yet")
        _key_checks(b, MEASUREMENT_KEYS["backgrounds"], p, rep)
    corrs = [c for c in ext.get("corrections", []) if isinstance(c, dict)] if isinstance(ext.get("corrections"), list) else []
    seen: dict[str, str] = {}
    for c in corrs:
        eid = c.get("effect_id")
        if isinstance(eid, str) and _norm_id(eid) in seen and seen[_norm_id(eid)] != eid:
            rep.add("error", f"{x}.corrections", "measurement.duplicate_correction",
                    f"'{eid}' and '{seen[_norm_id(eid)]}' are the same correction (case and separators ignored)")
        elif isinstance(eid, str):
            seen.setdefault(_norm_id(eid), eid)
    cats = [str(c.get("category", "")) for c in corrs]
    for i, cat in enumerate(cats):
        if not (vocab.has("response_corrections", cat) or NAMESPACED.match(cat)
                or re.fullmatch(r"[a-z][a-z0-9_]*_efficiency", cat)):
            rep.add("error", f"{x}.corrections[{i}].category", "measurement.unknown_correction_category",
                    f"'{cat}' is not a response_corrections term, a '<x>_efficiency' term or a namespaced '<ns>:<term>'")
    normed = [_norm_id(cat) for cat in cats]
    for cat in sorted({c for c in normed if normed.count(c) > 1}):
        rep.add("error", f"{x}.corrections", "measurement.correction_category_repeated",
                f"category '{cat}' appears twice: name each factor once (trigger_efficiency, selection_efficiency, ...)")
    bare = [c.split(":", 1)[-1] for c in cats]
    if "efficiency" in bare and any(c.endswith("_efficiency") for c in bare):
        rep.add("error", f"{x}.corrections", "measurement.correction_category_repeated",
                "a bare 'efficiency' next to a '<x>_efficiency' factor counts the efficiency twice")
    included = obs.get("included_corrections") if isinstance(obs.get("included_corrections"), list) else []
    chain = {_norm_id(c.get("effect_id", "")) for c in corrs} | set(normed)
    for item in included:
        if _norm_id(item) in chain:
            rep.add("error", f"{x}.observable.included_corrections", "measurement.correction_in_observable_and_chain",
                    f"'{item}' is already inside the observable and is applied again in the chain")
    norm: Any = obs.get("normalization") if isinstance(obs.get("normalization"), dict) else {}
    for i, cat in enumerate(bare):
        if NORMALIZATION_CORRECTIONS.get(cat) == norm.get("kind"):
            rep.add("error", f"{x}.corrections[{i}]", "measurement.normalization_double_counted",
                    f"a '{cat}' correction next to a '{norm.get('kind')}' normalization applies it twice")
    if _is_zero(norm.get("value")) and norm.get("exact_zero") is not True:
        rep.add("error", f"{x}.observable.normalization.value", "measurement.zero_value",
                "a normalization value of 0 needs \"exact_zero\": true; an unknown value is 'unknown', never 0")
    if norm.get("kind") == "shape-only" and isinstance(norm.get("value"), (int, float)) and not isinstance(norm.get("value"), bool):
        rep.add("error", f"{x}.observable.normalization.value", "measurement.shape_only_value",
                "a shape-only normalization carries no absolute value")
    for i, c in enumerate(corrs):
        if _is_zero(c.get("value")) and c.get("exact_zero") is not True:
            rep.add("error", f"{x}.corrections[{i}].value", "measurement.zero_value",
                    f"correction '{c.get('effect_id')}' has value 0 without \"exact_zero\": true")
        keyed = CORRECTION_KEYS_CAPABILITY in (doc.get("required_capabilities") or [])
        _key_checks(c, MEASUREMENT_KEYS["corrections"] | (set(CORRECTION_KEY_PATTERNS) if keyed else set()),
                    f"{x}.corrections[{i}]", rep)
        if keyed:
            for key, pattern in CORRECTION_KEY_PATTERNS.items():
                if key in c and not (isinstance(c[key], str) and re.fullmatch(pattern, c[key])):
                    rep.add("error", f"{x}.corrections[{i}].{key}", "measurement.bad_correction_key",
                            f"{key} {c[key]!r} does not match {pattern} (the recipe correction-key form)")
    syst: Any = ext.get("systematics")
    if isinstance(syst, list) and not syst:
        rep.add("error", f"{x}.systematics", "measurement.systematics_empty",
                "no systematic listed: every measurement has at least one source (state its physical effect)")
    names = []
    for i, s in enumerate(syst if isinstance(syst, list) else []):
        if not isinstance(s, dict):
            continue
        if _blank(s.get("applied_via")):
            rep.add("error", f"{x}.systematics[{i}].applied_via", "measurement.applied_via_missing",
                    f"systematic '{s.get('name')}' needs applied_via (how the variation reaches the result)")
        if _norm_id(s.get("name", "")) in names:
            rep.add("error", f"{x}.systematics[{i}].name", "measurement.duplicate_systematic",
                    f"systematic '{s.get('name')}' is listed twice")
        names.append(_norm_id(s.get("name", "")))
        _key_checks(s, MEASUREMENT_KEYS["systematics"], f"{x}.systematics[{i}]", rep)
    for path, marker in _markers(ext, x):
        if _listed(path, doc.get("unresolved_inputs")):
            rep.add("unresolved", path, "measurement.input_unresolved", f"'{marker}': listed in unresolved_inputs")
        else:
            rep.add("error", path, "measurement.unresolved_not_listed",
                    f"'{marker}' is not named in unresolved_inputs: list every open input explicitly")
    bl: Any = ext.get("blinding")
    if isinstance(bl, dict) and bl.get("blinded") is True:
        mask: Any = bl.get("mask")
        if not (isinstance(mask, dict) and (mask.get("regions") or mask.get("intervals"))):
            rep.add("error", f"{x}.blinding.mask", "measurement.blinding_mask_missing",
                    "a blinded measurement needs its mask (regions or observable intervals)")
        elif not _mask_names_something(mask):
            rep.add("warning", f"{x}.blinding.mask", "measurement.blinding_mask_empty",
                    "the mask names nothing: give a non-blank region name or an interval with its variable")
        if "observed" in set(doc.get("status", [])):
            rep.add("error", "$.status", "measurement.blinded_observed",
                    "a blinded spec cannot carry 'observed' results: only an authorized person unblinds, outside the "
                    "agent session; label it preliminary or unvalidated until then")
    ratio: Any = ext.get("ratio")
    if obs.get("quantity") in ("ratio", "fraction") and not isinstance(ratio, dict):
        rep.add("error", f"{x}.ratio", "measurement.ratio_block_missing",
                f"a {obs.get('quantity')} needs the ratio block (numerator, denominator, cancellations)")
    if isinstance(ratio, dict):
        if _norm_id(ratio.get("numerator", "")) == _norm_id(ratio.get("denominator", "")):
            rep.add("error", f"{x}.ratio", "measurement.ratio_self", "numerator and denominator are the same quantity")
        canc: Any = ratio.get("cancellations")
        if isinstance(canc, list) and not canc:
            rep.add("error", f"{x}.ratio.cancellations", "measurement.ratio_cancellations_empty",
                    "list each shared effect with its treatment ('independent' for one that does not cancel)")
        for i, c in enumerate(canc if isinstance(canc, list) else []):
            if isinstance(c, dict) and c.get("treatment") == "cancels" and _blank(c.get("verification")):
                rep.add("warning", f"{x}.ratio.cancellations[{i}]", "measurement.cancellation_unverified",
                        f"'{c.get('effect')}' is assumed to cancel without a verification")
    periods: Any = ext.get("period")
    for i, per in enumerate(periods if isinstance(periods, list) else [periods]):
        if isinstance(per, dict) and all(isinstance(per.get(k), str) and _ISO_DATE.match(per[k]) for k in ("start", "end")) \
                and per["end"][:10] < per["start"][:10]:
            rep.add("error", f"{x}.period", "measurement.period_reversed",
                    f"period {i}: end {per['end']} is before start {per['start']}")
    _key_checks(ext, MEASUREMENT_KEYS["extension"], x, rep)
    for i, era in enumerate(ext.get("eras") or []):  # M3: the era rules themselves are review rules
        _key_checks(era, MEASUREMENT_KEYS["eras"], f"{x}.eras[{i}]", rep)
    for i, cb in enumerate(ext.get("coupled_backgrounds") or []):  # M4: coupled.fixed_subtraction is a review rule
        _key_checks(cb, MEASUREMENT_KEYS["coupled_backgrounds"], f"{x}.coupled_backgrounds[{i}]", rep)


STAT_SEMANTICS_FROM = "2.2.0"  # statistical-result semantic rules apply natively from this contract version
BAND_KEYS = ("band_1sigma", "band_2sigma")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _observable_source(doc: dict, ext: dict, rep: Report) -> None:
    """observable_source kind ml-score names an input of artifact_type ml-artifact (PML-WP0.5, ML-K01)."""
    src: Any = ext.get("observable_source")
    if not (isinstance(src, dict) and src.get("kind") == "ml-score"):
        return
    name = src.get("ml_artifact")
    inp = _ml_input(doc, name)
    if _blank(name) or inp is None:
        rep.add("error", "$.extension.observable_source", "stats.observable_source_unlinked",
                f"the observable is an ML score of '{name}', but no input names that ml-artifact: list it in inputs "
                "(ref, artifact_type ml-artifact, sha256) so the chain can be checked")
    elif inp.get("artifact_type") != "ml-artifact":
        rep.add("error", "$.extension.observable_source", "stats.observable_source_unlinked",
                f"the input '{name}' is declared as {inp.get('artifact_type')!r}, not an ml-artifact")


def _ml_input(doc: dict, name) -> dict | None:
    """The input whose ref or artifact_id is `name` (the ML artifact an observable_source names)."""
    for inp in doc.get("inputs") or []:
        if isinstance(inp, dict) and name is not None and name in (inp.get("ref"), inp.get("artifact_id")):
            return inp
    return None


def _stat_semantics(doc: dict, ext: dict, rep: Report, strict: bool) -> None:
    """Numerical and semantic invariants of a statistical-result (audit F04, T06, T07). They apply natively to
    artifacts of contract 2.2.0 or later; an older artifact gets them only in strict mode, so its promised outcome
    is unchanged (T08). Errors: a p-value or bound outside [0, 1], a confidence level outside (0, 1), a global
    p-value below the local one, expected bands that are not [low, high] pairs ordered -2 <= -1 <= median <= +1 <= +2.
    Unresolved (valid, not usable as a final result): untyped coverage, a scan's global p-value without its
    trials_method, toy calibration without its toy count, a failed fit diagnostic under fit_status converged."""
    if not (strict or _at_least(doc.get("contract_version"), STAT_SEMANTICS_FROM)):
        return
    sig: Any = ext.get("significance") if isinstance(ext.get("significance"), dict) else {}
    for key in ("local_p", "global_p"):
        v = sig.get(key)
        if _is_num(v) and not 0.0 <= v <= 1.0:
            rep.add("error", f"$.extension.significance.{key}", "stats.p_out_of_range", f"{key} = {v} lies outside [0, 1]")
    for key in ("local_p_bound", "global_p_bound"):
        b = sig.get(key)
        if isinstance(b, dict):
            if _is_num(b.get("value")) and not 0.0 <= b["value"] <= 1.0:
                rep.add("error", f"$.extension.significance.{key}.value", "stats.p_out_of_range", f"{key} {b['value']} lies outside [0, 1]")
            if _is_num(b.get("cl")) and not 0.0 < b["cl"] < 1.0:
                rep.add("error", f"$.extension.significance.{key}.cl", "stats.cl_out_of_range", f"{key} cl {b['cl']} lies outside (0, 1)")
            if key[:-6] in sig:
                rep.add("error", f"$.extension.significance.{key}", "stats.p_value_and_bound",
                        f"give {key[:-6]} (an estimate) or {key} (a bound), not both")
    lp: Any = sig.get("local_p", (sig.get("local_p_bound") or {}).get("value") if isinstance(sig.get("local_p_bound"), dict) else None)
    gp: Any = sig.get("global_p")
    if _is_num(lp) and _is_num(gp) and gp < lp - 1e-12 and "local_p_bound" not in sig:
        rep.add("error", "$.extension.significance.global_p", "stats.global_below_local",
                f"global p {gp} is below local p {lp}: a trials correction cannot make a result more significant")
    gof: Any = ext.get("goodness_of_fit")
    if isinstance(gof, dict) and _is_num(gof.get("p_value")) and not 0.0 <= gof["p_value"] <= 1.0:
        rep.add("error", "$.extension.goodness_of_fit.p_value", "stats.p_out_of_range", f"p_value {gof['p_value']} lies outside [0, 1]")
    cov: Any = ext.get("coverage") if isinstance(ext.get("coverage"), dict) else None
    levels: list[tuple[str, Any]] = [("$.extension.cl", ext.get("cl")), ("$.extension.coverage.cl", (cov or {}).get("cl")),
                                     ("$.extension.results.cl", ext["results"].get("cl") if isinstance(ext.get("results"), dict) else None)]
    for path, v in levels:
        if _is_num(v) and not 0.0 < v < 1.0:
            rep.add("error", path, "stats.cl_out_of_range", f"confidence level {v} lies outside (0, 1)")
    if cov is not None and _is_num(cov.get("coverage")) and not 0.0 <= cov["coverage"] <= 1.0:
        rep.add("error", "$.extension.coverage.coverage", "stats.p_out_of_range", f"coverage {cov['coverage']} lies outside [0, 1]")
    exp: Any = ext.get("expected")
    if isinstance(exp, dict):
        _check_bands(exp, rep)
    if ext.get("paradigm") == "frequentist" and cov is not None and cov and "check" not in cov:
        rep.add("unresolved", "$.extension.coverage", "stats.coverage_untyped",
                "coverage has no check: state toys (with n_toys and the result), exact-construction, analytic or "
                "not-checked; a free-text method or note alone is not coverage evidence")
    if cov is not None and cov.get("check") == "toys" and not (_is_num(cov.get("n_toys")) and cov["n_toys"] > 0):
        rep.add("unresolved", "$.extension.coverage.n_toys", "stats.coverage_without_toys", "toy coverage needs its toy count")
    if cov is not None and cov.get("check") == "toys" and not (_is_num(cov.get("coverage")) or cov.get("points")):
        rep.add("unresolved", "$.extension.coverage.coverage", "stats.coverage_value_missing",
                "toy coverage needs the measured coverage (coverage, or points with their values)")
    if cov is not None and cov.get("check") in ("analytic", "exact-construction") and not cov.get("method"):
        rep.add("unresolved", "$.extension.coverage.method", "stats.coverage_justification_missing",
                f"coverage check '{cov.get('check')}' needs its justification in method")
    if sig.get("trials_method") == "toys" and ("global_p" in sig or "global_p_bound" in sig) and not _is_num(sig.get("global_n_toys")):
        rep.add("unresolved", "$.extension.significance.global_n_toys", "stats.global_toys_missing",
                "a toy-calibrated global p-value needs its toy count (global_n_toys)")
    gb: Any = sig.get("global_p_bound")
    if isinstance(gb, dict) and gb.get("kind") == "upper" and _is_num(gb.get("value")) and _is_num(sig.get("local_p")) \
            and gb["value"] < sig["local_p"] - 1e-12:
        rep.add("error", "$.extension.significance.global_p_bound", "stats.global_below_local",
                f"global p upper bound {gb['value']} is below local p {sig['local_p']}")
    if isinstance(sig.get("scan"), dict) and ("global_p" in sig or "global_p_bound" in sig) and not sig.get("trials_method"):
        rep.add("unresolved", "$.extension.significance.trials_method", "stats.trials_method_missing",
                "a global p-value without its trials_method is not an established global significance")
    if ext.get("paradigm") == "bayesian":
        _bayesian_rules(ext, rep, strict or _at_least(doc.get("contract_version"), STAT_HARDENING_FROM))
    lik: Any = ext.get("likelihood")
    if isinstance(lik, dict) and isinstance(lik.get("model_card"), dict):
        _model_card_rules(lik["model_card"], ext.get("paradigm"), rep)
    if _at_least(doc.get("contract_version"), STAT_SEMANTICS_FROM) and \
            "stats:result-semantics" not in (doc.get("required_capabilities") or []):
        rep.add("warning", "$.required_capabilities", "stats.capability_not_declared",
                "a 2.2 statistical-result should require stats:result-semantics, so a 2.1 reader refuses it instead of "
                "reading it under the older rules")
    fd: Any = ext.get("fit_diagnostics")
    if isinstance(fd, dict) and fd.get("status") == "failed" and ext.get("fit_status") in ("converged", "converged-with-warnings"):
        rep.add("error", "$.extension.fit_status", "stats.fit_status_mismatch",
                "fit_diagnostics.status is failed but fit_status says converged")
    if strict or _at_least(doc.get("contract_version"), STAT_HARDENING_FROM):
        _stat_hardening(ext, rep)


STAT_HARDENING_FROM = "2.6.0"  # hep-statistics hardening rules (STH-T1) apply natively from this contract version
COVERAGE_MIN_TOYS = 200        # below this a toy coverage claim is unresolved (binomial sigma <= 0.035 at any level)
COVERAGE_TOLERANCE = 0.01      # undercoverage fails when the Clopper-Pearson upper end is below nominal - 0.01
COVERAGE_INTERVAL_CL = 0.6827  # the central Clopper-Pearson interval the gate computes from the toy counts
COVERAGE_INTERVAL_MAX_CL = 0.9973  # a recorded interval wider than this exact interval does not describe the counts
Z_P_TOLERANCE = 0.01           # |z - Phi^-1(1 - p)| allowed between a reported z and its p (one-sided)
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
# Probability-like results keys: exact names, and prefixes (a key that names a limit, bound or band is not one).
PROB_RESULT_KEYS = frozenset({"p0", "p_value", "pvalue", "cls", "clb", "clsb", "cl_s", "cl_b", "cl_sb"})
PROB_RESULT_PREFIXES = ("cls_", "clb_", "clsb_", "p_", "p0_")
NOT_PROB = re.compile(r"(limit|upper|lower|bound|band|_ul\b|^ul_|interval)", re.I)
# Results keys that name an observed upper limit (S95_observed, mu_95, upper_limit, limit_obs, ...).
LIMIT_KEY = re.compile(r"(limit|upper[_ ]?bound|^(s|mu|r|n|sigma|xs)_?\d{2}(_|$)|^ul(_|$)|_ul$)", re.I)
# Test-statistic families recognized in the free-text test_statistic (first match wins; unrecognized text is not
# judged), and the families each construction admits. A construction absent here admits any declared ordering.
STATISTIC_FAMILIES = (("q0", re.compile(r"\bq_?\{?0\}?(?![\d.])|discovery", re.I)),
                      ("q-tilde", re.compile(r"q[-_ ]?tilde|q̃|\\tilde\{?q|qtilde", re.I)),
                      ("q_mu", re.compile(r"\bq_?\{?mu\}?\b|q\(\s*mu\s*\)|q_?μ", re.I)),
                      ("lep", re.compile(r"\blep\b|q_lep|-2\s*ln\s*q\b", re.I)),
                      ("lr", re.compile(r"likelihood[- ]ratio|\blambda\b|\bt_?mu\b|t[-_ ]?tilde|\blr\b|ordering", re.I)),
                      ("chi2", re.compile(r"chi2|chi\^2|chi-squared?|chi squared|χ²", re.I)))
CONSTRUCTION_STATISTICS = {
    "feldman-cousins": frozenset({"lr", "chi2"}),  # the unified ordering is the two-sided likelihood ratio
    "cls": frozenset({"q_mu", "q-tilde", "lep", "lr", "chi2"}),  # a limit statistic, never the discovery q0
    "asymptotic": frozenset({"q0", "q_mu", "q-tilde", "lr", "chi2"}),
    "profile-likelihood-wilks": frozenset({"q0", "q_mu", "q-tilde", "lr", "chi2"}),
}
NO_CLS_RESULTS = frozenset({"neyman", "feldman-cousins"})  # constructions that do not produce CLs/CLb values
TOY_CONSTRUCTIONS = frozenset({"toy-calibrated-profile"})


def statistic_family(text) -> str | None:
    """Family of a free-text test statistic (q0, q-tilde, q_mu, lep, lr, chi2), or None when not recognized."""
    for name, rx in STATISTIC_FAMILIES:
        if isinstance(text, str) and rx.search(text):
            return name
    return None


def _prob_key(key: str) -> bool:
    k = key.lower()
    return (k in PROB_RESULT_KEYS or k.startswith(PROB_RESULT_PREFIXES)) and not NOT_PROB.search(k)


def _z_of_p(p: float, two_sided: bool) -> float:
    from statistics import NormalDist
    return -NormalDist().inv_cdf(p / 2.0 if two_sided else p)


def _toy_based(ext: dict) -> list[str]:
    """Parts of a statistical-result that rest on toys (each needs a recorded seed)."""
    parts = []
    if ext.get("construction") in TOY_CONSTRUCTIONS:
        parts.append(f"construction {ext['construction']}")
    cov: Any = ext.get("coverage")
    if isinstance(cov, dict) and cov.get("check") == "toys":
        parts.append("toy coverage")
    gof: Any = ext.get("goodness_of_fit")
    if isinstance(gof, dict) and gof.get("calibration") == "toys":
        parts.append("toy goodness of fit")
    sig: Any = ext.get("significance")
    if isinstance(sig, dict) and (sig.get("trials_method") == "toys" or sig.get("method") == "toys"):
        parts.append("toy-calibrated significance")
    return parts


def _stat_hardening(ext: dict, rep: Report) -> None:
    """Statistical-result rules of contracts 2.6.0 (hep-statistics hardening STH-T1.1). Native for artifacts of
    contract 2.6.0 or later; an older artifact gets them only in strict mode (and so at the publication gate), so its
    default outcome is unchanged.
    Errors: coverage.cl different from results.cl or extension.cl (stats.coverage_cl_mismatch); a recorded coverage
    interval that is not inside the 99.73% Clopper-Pearson interval of round(coverage x n_toys) of n_toys or does not
    contain the coverage (stats.coverage_interval_inconsistent); a local, global or goodness-of-fit p-value of exactly 0
    (stats.p_zero_without_bound: give the *_p_bound the toys support); a probability-like results value (keys
    PROB_RESULT_KEYS, prefixes PROB_RESULT_PREFIXES) outside [0, 1] (stats.p_out_of_range); a z that disagrees with its
    p by more than Z_P_TOLERANCE under the one-sided convention Phi^-1(1 - p) (significance.convention 'two-sided' uses
    p/2) (stats.z_p_inconsistent); global_z above local_z (stats.global_z_above_local); a recognized test statistic a
    construction does not admit (CONSTRUCTION_STATISTICS), or CLs/CLb results from a Neyman or Feldman-Cousins
    construction (stats.construction_statistic_mismatch); likelihood.model_sha256 that is not 64 hex digits
    (stats.model_sha256_malformed).
    Unresolved: toy coverage with fewer than COVERAGE_MIN_TOYS toys (stats.coverage_toys_too_few); an observed limit
    (construction cls, or a results key matching LIMIT_KEY) without expected.median and both bands
    (stats.expected_bands_missing); global_z without global_p or global_p_bound (stats.global_z_without_p); a toy-based
    construction, coverage, goodness of fit or significance without extension.seeds or coverage.seed
    (stats.seed_missing); toy goodness of fit without n_toys (stats.gof_toys_missing)."""
    results: Any = ext.get("results") if isinstance(ext.get("results"), dict) else {}
    cov: Any = ext.get("coverage") if isinstance(ext.get("coverage"), dict) else None
    if cov is not None and _is_num(cov.get("cl")):
        for path, other in (("$.extension.results.cl", results.get("cl")), ("$.extension.cl", ext.get("cl"))):
            if _is_num(other) and abs(other - cov["cl"]) > 1e-9:
                rep.add("error", "$.extension.coverage.cl", "stats.coverage_cl_mismatch",
                        f"coverage was checked at cl {cov['cl']} but {path[2:]} is {other}: the coverage claim is about another interval")
    if cov is not None and cov.get("check") == "toys":
        n, value = cov.get("n_toys"), cov.get("coverage")
        if _is_num(n) and 0 < n < COVERAGE_MIN_TOYS:
            rep.add("unresolved", "$.extension.coverage.n_toys", "stats.coverage_toys_too_few",
                    f"{n} toys cannot establish coverage: use at least {COVERAGE_MIN_TOYS} (binomial sigma <= 0.035)")
        interval: Any = cov.get("interval")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0 and _is_num(value) and 0.0 <= value <= 1.0 \
                and isinstance(interval, list) and len(interval) == 2 and all(_is_num(x) for x in interval):
            from core.stats.tail_estimation import clopper_pearson
            lo, hi = clopper_pearson(round(value * n), n, COVERAGE_INTERVAL_MAX_CL)
            if interval[0] < lo - 1e-9 or interval[1] > hi + 1e-9 or not interval[0] - 1e-12 <= value <= interval[1] + 1e-12:
                rep.add("error", "$.extension.coverage.interval", "stats.coverage_interval_inconsistent",
                        f"interval {interval} does not describe {round(value * n)} of {n} toys (exact "
                        f"{COVERAGE_INTERVAL_MAX_CL} interval [{lo:.4g}, {hi:.4g}]): a wide interval cannot hide undercoverage")
    sig: Any = ext.get("significance") if isinstance(ext.get("significance"), dict) else {}
    gof: Any = ext.get("goodness_of_fit") if isinstance(ext.get("goodness_of_fit"), dict) else {}
    for path, v in (("significance.local_p", sig.get("local_p")), ("significance.global_p", sig.get("global_p")),
                    ("goodness_of_fit.p_value", gof.get("p_value"))):
        if _is_num(v) and v == 0:
            rep.add("error", f"$.extension.{path}", "stats.p_zero_without_bound",
                    f"{path} = 0 is not an estimate: toys with no exceedance only bound it (record the bound "
                    "{kind, value, cl, convention}, for example from core/stats/tail_estimation.py)")
    for key, v in results.items():
        if not (isinstance(key, str) and _prob_key(key)):
            continue
        vals = v if isinstance(v, list) else [v]
        bad = [x for x in vals if _is_num(x) and not 0.0 <= x <= 1.0]
        if bad:
            rep.add("error", f"$.extension.results.{key}", "stats.p_out_of_range",
                    f"results.{key} = {bad[0]} is a probability outside [0, 1]")
    two_sided = sig.get("convention") == "two-sided"
    for zk, pk in (("local_z", "local_p"), ("global_z", "global_p")):
        z, p = sig.get(zk), sig.get(pk)
        if _is_num(z) and _is_num(p) and 0.0 < p < 1.0 and abs(z - _z_of_p(p, two_sided)) > Z_P_TOLERANCE:
            rep.add("error", f"$.extension.significance.{zk}", "stats.z_p_inconsistent",
                    f"{zk} = {z} but {pk} = {p} gives z = {_z_of_p(p, two_sided):.4g} "
                    f"({'two' if two_sided else 'one'}-sided): one of them is wrong")
    if _is_num(sig.get("global_z")) and _is_num(sig.get("local_z")) and sig["global_z"] > sig["local_z"] + 1e-9:
        rep.add("error", "$.extension.significance.global_z", "stats.global_z_above_local",
                f"global_z {sig['global_z']} exceeds local_z {sig['local_z']}: a trials correction cannot raise a significance")
    if "global_z" in sig and "global_p" not in sig and "global_p_bound" not in sig:
        rep.add("unresolved", "$.extension.significance.global_p", "stats.global_z_without_p",
                "global_z is reported without global_p (or its bound): the global significance is not established")
    cons, fam = ext.get("construction"), statistic_family(ext.get("test_statistic"))
    allowed = CONSTRUCTION_STATISTICS.get(cons) if isinstance(cons, str) else None
    if allowed is not None and fam is not None and fam not in allowed:
        rep.add("error", "$.extension.test_statistic", "stats.construction_statistic_mismatch",
                f"construction {cons} does not use a {fam} test statistic (admits {', '.join(sorted(allowed))})")
    if cons in NO_CLS_RESULTS:
        cls_keys = [k for k in results if isinstance(k, str) and k.lower().startswith(("cls", "clb"))]
        if cls_keys:
            rep.add("error", "$.extension.construction", "stats.construction_statistic_mismatch",
                    f"construction {cons} does not produce CLs/CLb values, but results carry {', '.join(cls_keys)}")
    if ext.get("paradigm") == "frequentist" and (cons == "cls" or any(isinstance(k, str) and LIMIT_KEY.search(k) for k in results)):
        exp: Any = ext.get("expected") if isinstance(ext.get("expected"), dict) else {}
        missing = [k for k in ("median",) + BAND_KEYS if k not in exp]
        if missing:
            rep.add("unresolved", "$.extension.expected", "stats.expected_bands_missing",
                    f"an observed limit needs its expected median and both bands for comparison (missing {', '.join(missing)})")
        if _blank(cons):
            # hep-statistics invariant STAT-02: an approximation is named (asymptotic, Wilks, exact Poisson, toys)
            rep.add("warning", "$.extension.construction", "stats.construction_missing",
                    "a frequentist limit names its construction (asymptotic, profile-likelihood-wilks, neyman, cls, "
                    "toy-calibrated-profile, ...): an approximation that is not named cannot be validated")
    toys = _toy_based(ext)
    seeds: Any = ext.get("seeds")
    if toys and not (isinstance(seeds, dict) and seeds) and not (cov is not None and "seed" in cov):
        rep.add("unresolved", "$.extension.seeds", "stats.seed_missing",
                f"{', '.join(toys)} without a recorded seed (extension.seeds or coverage.seed): the toys cannot be reproduced")
    if gof.get("calibration") == "toys" and not _is_num(gof.get("n_toys")):
        rep.add("unresolved", "$.extension.goodness_of_fit.n_toys", "stats.gof_toys_missing",
                "a toy-calibrated goodness-of-fit p-value needs its toy count (n_toys)")
    lik: Any = ext.get("likelihood") if isinstance(ext.get("likelihood"), dict) else {}
    sha = lik.get("model_sha256")
    if sha is not None and not (isinstance(sha, str) and SHA256.match(sha)):
        rep.add("error", "$.extension.likelihood.model_sha256", "stats.model_sha256_malformed",
                f"model_sha256 {sha!r} is not a SHA-256 digest (64 hexadecimal digits)")


GRADIENT_SAMPLERS = re.compile(r"\b(nuts|hmc|hamiltonian)\b", re.I)
SAMPLER_METADATA = ("warmup", "chains", "draws", "divergences", "e_bfmi_min", "max_treedepth_hits")
IMPROPER_FORMS = re.compile(r"^\s*(flat|improper|uniform\s*\(\s*-?inf|uniform\[\s*-?inf)", re.I)
E_BFMI_MIN = 0.3  # Stan's warning threshold
# contracts 2.6.0 (STH-T1.2): samplers that are gradient-based by default, an infinite bound on either side of a
# uniform form, a propriety argument with a reference, a prior on every parameter of interest, an ESS floor.
GRADIENT_SAMPLERS_2_6 = re.compile(r"\b(nuts|hmc|hamiltonian|stan|cmdstan|pystan|pymc3?|numpyro|blackjax)\b", re.I)
IMPROPER_FORMS_2_6 = re.compile(r"^\s*(flat|improper)|uniform\s*[(\[][^,\])]*\binf\b|uniform\s*[(\[][^,]*,[^\])]*\binf\b", re.I)
ESS_PER_CHAIN = 100  # bulk and tail ESS floor per chain (bayes_diagnostics.py --min-ess-per-chain), order question Q2
ESS_FLOOR_NO_CHAINS = 400  # total floor when the chain count is not recorded (four chains' worth)


def _poi_names(poi: str) -> set[str]:
    """Names a prior may use for a parameter of interest: the full string and its leading identifier
    ('S (signal events in SRB)' -> 'S')."""
    out = {poi.strip()}
    m = re.match(r"\s*([^\s(\[]+)", poi)
    if m:
        out.add(m.group(1))
    return out


def _ess_values(v) -> list[float]:
    if _is_num(v):
        return [float(v)]
    if isinstance(v, dict):
        return [float(x) for x in v.values() if _is_num(x)]
    return []


def _bayesian_hardening(ext: dict, rep: Report) -> None:
    """Bayesian rules of contracts 2.6.0 (STH-T1.2). Unresolved: an improper prior (IMPROPER_FORMS_2_6: flat,
    improper, or an infinite bound on either side of a uniform form) whose propriety is a bare 'yes'/true instead of
    {argument or derivation, ref} (stats.propriety_unsupported); a parameter of interest without a prior, matched by the
    full name or its leading identifier (stats.poi_prior_missing); a bulk or tail ESS below ESS_PER_CHAIN x
    sampler.chains, or below ESS_FLOOR_NO_CHAINS when the chain count is not recorded (stats.ess_too_low), and the
    missing chain count itself (stats.chains_missing)."""
    priors = [pr for pr in ext.get("priors", []) or [] if isinstance(pr, dict)]
    for i, pr in enumerate(priors):
        prop = pr.get("propriety")
        if not IMPROPER_FORMS_2_6.search(str(pr.get("form", ""))) or not prop:
            continue
        supported = isinstance(prop, dict) and not (_blank(prop.get("argument")) and _blank(prop.get("derivation"))) \
            and not _blank(prop.get("ref"))
        if not supported:
            rep.add("unresolved", f"$.extension.priors[{i}].propriety", "stats.propriety_unsupported",
                    f"prior '{pr.get('form')}' on {pr.get('parameter')} is improper and propriety {prop!r} is a claim, not "
                    "an argument: give {argument (or derivation), ref} showing the posterior is proper")
    names = {pr["parameter"] for pr in priors if isinstance(pr.get("parameter"), str)}
    for poi in ext.get("parameters_of_interest", []) or []:
        if isinstance(poi, str) and not (_poi_names(poi) & names):
            rep.add("unresolved", "$.extension.priors", "stats.poi_prior_missing",
                    f"parameter of interest '{poi}' has no prior (priors[].parameter must name it or its leading identifier)")
    smp: Any = ext.get("sampler") if isinstance(ext.get("sampler"), dict) else {}
    conv: Any = ext.get("convergence") if isinstance(ext.get("convergence"), dict) else {}
    chains: Any = smp.get("chains")
    has_chains = _is_num(chains) and chains >= 1
    floor = ESS_PER_CHAIN * chains if has_chains else ESS_FLOOR_NO_CHAINS
    ess_keys = [k for k in ("ess_bulk", "ess_tail", "ess") if k in conv]
    if ess_keys and not has_chains:
        rep.add("unresolved", "$.extension.sampler.chains", "stats.chains_missing",
                f"the chain count is not recorded: the ESS floor is {ESS_PER_CHAIN} per chain ({ESS_FLOOR_NO_CHAINS} total assumed)")
    for k in ess_keys:
        low = [x for x in _ess_values(conv[k]) if x < floor]
        if low:
            rep.add("unresolved", f"$.extension.convergence.{k}", "stats.ess_too_low",
                    f"{k} {min(low):g} is below the floor {floor:g} ({ESS_PER_CHAIN} per chain): the posterior summaries are not established")


def _bayesian_rules(ext: dict, rep: Report, hardening: bool = False) -> None:
    """Bayesian results (audit T25): gradient-based samplers carry their warmup, chains, draws, divergences, E-BFMI and
    tree-depth saturations; divergences or a low E-BFMI under fit_status converged are errors; an improper prior is
    unresolved until the posterior's propriety is shown; SBC is calibration over the prior predictive, so it is not
    reported as frequentist coverage. With hardening (contract 2.6.0 or strict) the sampler and improper-form patterns
    are the 2.6.0 ones and _bayesian_hardening applies."""
    smp: Any = ext.get("sampler")
    conv = ext.get("fit_status") == "converged"
    samplers = GRADIENT_SAMPLERS_2_6 if hardening else GRADIENT_SAMPLERS
    improper = IMPROPER_FORMS_2_6 if hardening else IMPROPER_FORMS
    if isinstance(smp, dict) and samplers.search(str(smp.get("name", "")) + " " + str(smp.get("algorithm", ""))):
        missing = [k for k in SAMPLER_METADATA if k not in smp]
        if missing:
            rep.add("unresolved", "$.extension.sampler", "stats.sampler_metadata_missing",
                    f"a gradient-based sampler needs {', '.join(missing)}")
        dv: Any = smp.get("divergences")
        if _is_num(dv) and dv > 0 and conv:
            rep.add("error", "$.extension.fit_status", "stats.divergences_unreported",
                    f"{dv} divergent transitions but fit_status converged: use converged-with-warnings or failed")
        eb: Any = smp.get("e_bfmi_min")
        if _is_num(eb) and eb < E_BFMI_MIN and conv:
            rep.add("error", "$.extension.fit_status", "stats.low_e_bfmi",
                    f"E-BFMI {eb} below {E_BFMI_MIN} but fit_status converged")
    for i, pr in enumerate(ext.get("priors", []) or []):
        if isinstance(pr, dict) and improper.search(str(pr.get("form", ""))) and not pr.get("propriety"):
            rep.add("unresolved", f"$.extension.priors[{i}]", "stats.improper_prior",
                    f"prior '{pr.get('form')}' on {pr.get('parameter')} is improper: state why the posterior is proper "
                    "(priors[].propriety) or use a proper prior")
    if "coverage" in ext:
        rep.add("error", "$.extension.coverage", "stats.paradigm_mislabeled",
                "a Bayesian result reports calibration (for example SBC) under checks, not frequentist coverage")
    if hardening:
        _bayesian_hardening(ext, rep)


def check_model_card(card: dict, paradigm: str | None, rep: Report, path: str = "$.extension.likelihood.model_card") -> None:
    """Semantic rules of a statistical model card (contracts/schemas/statistical_model.json), audit T15."""
    seen: dict[str, str] = {}
    for i, c in enumerate(card.get("constraints", [])):
        aux, par = c.get("aux_id"), c.get("parameter")
        if aux in seen and seen[aux] != par:
            rep.add("error", f"{path}.constraints[{i}]", "stats.duplicate_auxiliary",
                    f"auxiliary measurement '{aux}' constrains both '{seen[aux]}' and '{par}': one measurement enters the "
                    "likelihood once; share one parameter between the samples or channels it affects")
        elif aux in seen:
            rep.add("error", f"{path}.constraints[{i}]", "stats.duplicate_auxiliary",
                    f"auxiliary measurement '{aux}' appears twice for '{par}': it would be counted twice")
        seen.setdefault(aux, par)
        if paradigm == "frequentist" and c.get("kind") == "prior":
            rep.add("error", f"{path}.constraints[{i}]", "stats.prior_in_frequentist_model",
                    f"'{par}' has a prior in a frequentist model; a constraint must come from an auxiliary measurement")
    channels = {ch.get("name") for ch in card.get("channels", [])}
    params = {c.get("parameter") for c in card.get("constraints", [])}
    for i, smp in enumerate(card.get("samples", [])):
        if smp.get("channel") not in channels:
            rep.add("error", f"{path}.samples[{i}].channel", "stats.model_unknown_channel", f"channel '{smp.get('channel')}' is not defined")
        for m in smp.get("modifiers", []):
            if m.get("type") == "constrained-normalization" and m.get("parameter") not in params:
                rep.add("error", f"{path}.samples[{i}]", "stats.model_unconstrained_parameter",
                        f"constrained parameter '{m.get('parameter')}' has no constraint term")
            if m.get("type") == "poi" and m.get("parameter") != card.get("poi"):
                rep.add("error", f"{path}.samples[{i}]", "stats.model_poi_mismatch", f"'{m.get('parameter')}' is not the poi")
    roles = {ch.get("name"): ch.get("role") for ch in card.get("channels", [])}
    cr_signal = any(roles.get(s.get("channel")) == "control-region" and any(m.get("type") == "poi" for m in s.get("modifiers", []))
                    for s in card.get("samples", []))
    if card.get("signal_contamination") == "modeled" and not cr_signal:
        rep.add("error", f"{path}.signal_contamination", "stats.contamination_not_in_model",
                "signal_contamination says modeled but no control-region sample carries the poi")
    if card.get("signal_contamination") == "not-modeled":
        rep.add("unresolved", f"{path}.signal_contamination", "stats.contamination_not_modeled",
                "signal in the control regions is not modeled: show it is negligible (an injection test) or model it")


_model_card_rules = check_model_card


def _check_bands(exp: dict, rep: Report) -> None:
    bands = {}
    for key in BAND_KEYS:
        b = exp.get(key)
        if b is None:
            continue
        if not (isinstance(b, list) and len(b) == 2 and all(_is_num(v) for v in b)):
            rep.add("error", f"$.extension.expected.{key}", "stats.band_cardinality",
                    f"{key} must be a [low, high] pair, got {b!r}")
            continue
        bands[key] = b
    chain = []
    if "band_2sigma" in bands:
        chain.append(("-2sigma", bands["band_2sigma"][0]))
    if "band_1sigma" in bands:
        chain.append(("-1sigma", bands["band_1sigma"][0]))
    if _is_num(exp.get("median")):
        chain.append(("median", exp["median"]))
    if "band_1sigma" in bands:
        chain.append(("+1sigma", bands["band_1sigma"][1]))
    if "band_2sigma" in bands:
        chain.append(("+2sigma", bands["band_2sigma"][1]))
    for (n1, v1), (n2, v2) in zip(chain, chain[1:]):
        if v2 < v1:
            rep.add("error", "$.extension.expected", "stats.bands_unordered",
                    f"expected bands must satisfy -2sigma <= -1sigma <= median <= +1sigma <= +2sigma; {n1} = {v1} > {n2} = {v2}")


def publication_gate(doc: dict, vocab: Vocabulary | None = None, base_dir=None) -> dict:
    """Publication gate of a statistical-result (T07): status passed, unresolved or failed, with reasons.

    failed: the artifact has errors under strict validation, carries the 'failed' status, carries 'synthetic' or
    'asimov' (gate.not_observed_data, contracts 2.6.0: nothing makes such a result publishable as data) or 'projection'
    (gate.projection, upgrade plan S2) or 'outside-validated-range' without a valid inline extension.validation_record
    (gate.outside_validated_range, gate.validation_record_invalid, S7), its fit failed
    or was not run, its fit diagnostics failed, or toy coverage is short: the upper end of the 68.27% Clopper-Pearson
    interval of round(coverage x n_toys) of n_toys lies below the nominal level by more than 0.01 (gate.undercoverage;
    without n_toys the recorded interval or value is used). unresolved: anything not yet established: an 'unvalidated' or 'preliminary'
    label, unresolved inputs, fit_status converged-with-warnings, untyped or not-checked coverage (frequentist), a scan
    without a global p-value and its trials_method, a Bayesian result without numeric R-hat and ESS, or no model and
    backend provenance (a non-blank likelihood.backend with a non-blank model_ref or model_sha256). Passing says the contract-level
    prerequisites for reporting the result as validated are present; it is not a scientific validation.

    ML provenance (contracts 2.8.0, hep-ml audit WP0.5): every input of artifact_type ml-artifact, and the one
    extension.observable_source names (kind ml-score), is resolved relative to base_dir (the folder of the artifact;
    a ref may also be relative to up to three of its parent folders, as project-relative refs are), its sha256 is
    checked and it is validated strictly: an error there fails the gate (gate.ml_input_invalid), an unresolved
    finding leaves it unresolved (gate.ml_input_unresolved: for example a failed domain-shift check or a split check
    that was not run). Without base_dir, or when the file cannot be found, the gate is unresolved
    (gate.ml_input_unchecked)."""
    reasons: list[dict] = []

    def add(level, code, msg):
        reasons.append({"level": level, "code": code, "message": msg})
    if not isinstance(doc, dict) or doc.get("artifact_type") != "statistical-result":
        add("failed", "gate.not_statistical_result", "the publication gate applies to statistical-result artifacts")
        return {"gate": "publication", "status": "failed", "reasons": reasons}
    rep = validate_artifact(doc, vocab, strict=True)
    for f in rep.findings:
        if f.severity == "error":
            add("failed", f.code, f.message)
        elif f.severity == "unresolved":
            add("unresolved", f.code, f.message)
    ext: Any = doc.get("extension") if isinstance(doc.get("extension"), dict) else {}
    status = set(doc.get("status", []))
    if "failed" in status:
        add("failed", "gate.failed_label", "the artifact carries the 'failed' status")
    for s in NOT_OBSERVED_STATUSES:
        if s in status:
            add("failed", "gate.not_observed_data", f"the artifact carries '{s}': no further evidence makes a result on "
                                                    "synthetic or Asimov data publishable as a result on data")
    if "projection" in status:
        add("failed", "gate.projection", "the artifact carries 'projection': a projection to another exposure (S2) is "
                                         "never a result")
    if "outside-validated-range" in status:
        rec: Any = ext.get("validation_record")
        if rec is None:
            add("failed", "gate.outside_validated_range", "the artifact carries 'outside-validated-range' (a tool ran "
                "beyond its validated range, S7) and extension.validation_record is missing")
        else:
            from contracts.schema import validate as _schema_validate
            vr = _schema_validate(rec, "validation_record.json") if isinstance(rec, dict) else None
            if vr is None or any(f.severity == "error" for f in vr.findings):
                add("failed", "gate.validation_record_invalid", "extension.validation_record must be an inline "
                    "validation record (contracts/schemas/validation_record.json)")
    for s in ("unvalidated", "preliminary"):
        if s in status:
            add("unresolved", "gate.status_label", f"the artifact carries '{s}': an archival artifact, not a validated result")
    if doc.get("unresolved_inputs"):
        add("unresolved", "gate.unresolved_inputs", "unresolved inputs are listed")
    fs = ext.get("fit_status")
    if fs in ("failed", "not-run"):
        add("failed", "gate.fit_not_converged", f"fit_status is {fs}")
    elif fs == "converged-with-warnings":
        add("unresolved", "gate.fit_warnings", "fit_status is converged-with-warnings")
    fd: Any = ext.get("fit_diagnostics")
    if isinstance(fd, dict) and fd.get("status") in ("failed", "incomplete"):
        add("failed" if fd["status"] == "failed" else "unresolved", "gate.fit_diagnostics", f"fit_diagnostics.status is {fd['status']}")
    if ext.get("paradigm") == "frequentist":
        cov: Any = ext.get("coverage") if isinstance(ext.get("coverage"), dict) else {}
        if cov.get("check") in (None, "not-checked"):
            add("unresolved", "gate.coverage_not_established", "coverage is not established (check missing or not-checked)")
        nominal: Any = cov.get("cl", (ext.get("results") or {}).get("cl") if isinstance(ext.get("results"), dict) else None)
        value: Any = cov.get("coverage")
        if cov.get("check") == "toys" and _is_num(value) and _is_num(nominal):
            n: Any = cov.get("n_toys")
            if isinstance(n, int) and not isinstance(n, bool) and n > 0 and 0.0 <= value <= 1.0:
                # the exact interval from the counts, not a recorded interval (which could be widened to hide a deficit)
                from core.stats.tail_estimation import clopper_pearson
                upper = clopper_pearson(round(value * n), n, COVERAGE_INTERVAL_CL)[1]
            else:
                interval: Any = cov.get("interval")
                upper = interval[1] if isinstance(interval, list) and len(interval) == 2 and _is_num(interval[1]) else value
            if upper < nominal - COVERAGE_TOLERANCE:
                add("failed", "gate.undercoverage", f"recorded coverage {value} (upper end {upper:.4g}) is below the nominal "
                                                    f"{nominal} by more than {COVERAGE_TOLERANCE}")
        elif cov.get("check") == "toys" and not _is_num(nominal):
            add("unresolved", "gate.coverage_nominal_missing", "toy coverage needs the nominal level (coverage.cl)")
    if ext.get("paradigm") == "bayesian":
        conv: Any = ext.get("convergence") if isinstance(ext.get("convergence"), dict) else {}
        if _max_rhat(conv) is None or not any(k.startswith("ess") for k in conv):
            add("unresolved", "gate.convergence_not_established", "a Bayesian result needs numeric R-hat and ESS")
    sig: Any = ext.get("significance") if isinstance(ext.get("significance"), dict) else {}
    if isinstance(sig.get("scan"), dict) and not (("global_p" in sig or "global_p_bound" in sig) and sig.get("trials_method")):
        add("unresolved", "gate.global_not_established", "a scan needs a global p-value (or bound) with its trials_method")
    lik: Any = ext.get("likelihood") if isinstance(ext.get("likelihood"), dict) else {}
    if _blank(lik.get("backend")) or (_blank(lik.get("model_ref")) and _blank(lik.get("model_sha256"))):
        add("unresolved", "gate.model_provenance_missing", "likelihood.backend and a model_ref or model_sha256 are required")
    _gate_ml_inputs(doc, ext, vocab, base_dir, add)
    levels = {r["level"] for r in reasons}
    status_out = "failed" if "failed" in levels else ("unresolved" if levels else "passed")
    return {"gate": "publication", "status": status_out, "reasons": reasons}


def _gate_ml_inputs(doc: dict, ext: dict, vocab, base_dir, add) -> None:
    """Resolve and validate the ml-artifact inputs of a statistical result (see publication_gate)."""
    import hashlib
    src: Any = ext.get("observable_source") if isinstance(ext.get("observable_source"), dict) else {}
    wanted = []
    if src.get("kind") == "ml-score":
        inp = _ml_input(doc, src.get("ml_artifact"))
        if inp is not None and inp.get("artifact_type") == "ml-artifact":
            wanted.append(inp)
    wanted += [i for i in doc.get("inputs") or [] if isinstance(i, dict) and i.get("artifact_type") == "ml-artifact"
               and i not in wanted]
    for inp in wanted:
        ref = inp.get("ref")
        path = None
        if base_dir is not None and isinstance(ref, str) and ref and not Path(ref).is_absolute():
            base = Path(base_dir).resolve()
            for folder in (base, *list(base.parents)[:3]):
                cand = (folder / ref).resolve()
                if (cand == folder or folder in cand.parents) and cand.is_file():
                    path = cand
                    break
        if path is None:
            add("unresolved", "gate.ml_input_unchecked",
                f"the ml-artifact input {ref!r} could not be resolved here; check the chain with contracts/dependencies.py")
            continue
        data = path.read_bytes()
        sha = inp.get("sha256")
        if isinstance(sha, str) and sha != hashlib.sha256(data).hexdigest():
            add("failed", "gate.ml_input_hash_mismatch", f"the ml-artifact input {ref!r} does not match its sha256")
            continue
        try:
            mdoc = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            add("failed", "gate.ml_input_invalid", f"the ml-artifact input {ref!r} is not JSON")
            continue
        if not isinstance(mdoc, dict) or mdoc.get("artifact_type") != "ml-artifact":
            add("failed", "gate.ml_input_invalid", f"the input {ref!r} is not an ml-artifact")
            continue
        mrep = validate_artifact(mdoc, vocab, strict=True)
        errors = sorted({f.code for f in mrep.findings if f.severity == "error"})
        unresolved = sorted({f.code for f in mrep.findings if f.severity == "unresolved"})
        if errors:
            add("failed", "gate.ml_input_invalid", f"the ml-artifact {ref!r} the result rests on has errors: {', '.join(errors)}")
        elif unresolved:
            add("unresolved", "gate.ml_input_unresolved",
                f"the ml-artifact {ref!r} the result rests on is not established: {', '.join(unresolved)}")


def _max_rhat(conv):
    """Largest numeric R-hat declared in a convergence block (rhat, rhat_max: a number or a map), else None."""
    if not isinstance(conv, dict):
        return None
    vals = []
    for key in ("rhat", "rhat_max", "r_hat"):
        v = conv.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
        elif isinstance(v, dict):
            vals += [float(x) for x in v.values() if isinstance(x, (int, float)) and not isinstance(x, bool)]
    return max(vals) if vals else None


def _at_least(version, minimum) -> bool:
    try:
        return parse(str(version)) >= parse(minimum)
    except (TypeError, ValueError):
        return False


def check_contract_version(doc: dict, rep: Report, protected: bool = False) -> None:
    """Version policy (F08, K02). A newer major may carry rules this validator does not know: judging it by the older
    rules would report 'valid' for something never checked, so it is an error (fail closed). A newer minor adds only
    optional fields, so it is a warning, or an error for protected use. versions.contracts must equal
    contract_version (an error from 2.1.0 on, a warning before). Every required capability must be one this reader
    implements. Older versions keep their outcome; rules that changed branch on contract_version (see _at_least)."""
    from contracts import CONTRACTS_VERSION, KNOWN_CAPABILITIES
    cv = doc.get("contract_version")
    try:
        version = parse(str(cv))
    except (TypeError, ValueError):
        return  # the envelope schema reports a malformed version
    supported = parse(CONTRACTS_VERSION)
    if version[0] > supported[0]:
        rep.add("error", "$.contract_version", "contract.unsupported_major",
                f"contract_version {cv} is newer than this validator's contracts {CONTRACTS_VERSION}; "
                "validate it with a plugin that implements that contract")
    elif version[0] == supported[0] and version[1] > supported[1]:
        rep.add("error" if protected else "warning", "$.contract_version", "contract.newer_minor",
                f"contract_version {cv} is newer than this validator's contracts {CONTRACTS_VERSION}: fields it adds "
                "are not checked" + ("; protected use needs a reader that implements it" if protected else ""))
    declared = (doc.get("versions") or {}).get("contracts") if isinstance(doc.get("versions"), dict) else None
    if declared is not None and declared != cv:
        rep.add("error" if _at_least(cv, "2.1.0") else "warning", "$.versions.contracts", "contract.version_mismatch",
                f"versions.contracts {declared} differs from contract_version {cv}")
    caps = doc.get("required_capabilities")
    if isinstance(caps, list):
        for k, cap in enumerate(caps):
            if isinstance(cap, str) and cap not in KNOWN_CAPABILITIES:
                rep.add("error", f"$.required_capabilities[{k}]", "contract.unknown_capability",
                        f"required capability '{cap}' is not implemented by this reader (contracts {CONTRACTS_VERSION})")
    exp = doc.get("data_exposure")
    if (isinstance(exp, dict) and exp.get("basis") == "structured-record" and exp.get("record_ref")
            and "core:exposure-record" not in (caps if isinstance(caps, list) else [])):
        rep.add("warning", "$.required_capabilities", "exposure.capability_not_declared",
                "data_exposure names an exposure record; declare 'core:exposure-record' so that a reader without the "
                "record check refuses the artifact in protected use")


ENVELOPE_KEYS = {"contract_version", "artifact_id", "artifact_type", "objective", "bindings", "versions", "provenance",
                 "inputs", "outputs", "status", "handoff", "unresolved_inputs", "extension", "required_capabilities",
                 "data_exposure"}


def check_unknown_keys(doc: dict, rep: Report) -> None:
    """Unknown top-level keys are accepted but not propagated by any consumer: say so (P02, K03)."""
    for key in sorted(set(doc) - ENVELOPE_KEYS):
        rep.add("warning", f"$.{key}", "envelope.unknown_key",
                f"'{key}' is not an envelope field: no consumer reads or propagates it")


def validate_artifact(doc, vocab: Vocabulary | None = None, protected: bool = False, strict: bool = False, *,
                      context=None, strict_versions: bool = False) -> Report:
    """Schema and semantic rules of one artifact. In protected mode (the project declares agent_policy, or protected is
    true; core.protected.guard) the protected inputs are checked first, a refusal is an error finding, and the stricter
    version policy applies. strict_versions applies only that policy (a newer minor is an error), without protected
    mode. `context` reuses an established protected-use context (core.protected.guard.Context)."""
    vocab = vocab or Vocabulary()
    rep = validate(doc, "envelope.json", vocab)
    ctx = guard_report("contracts.validate.validate_artifact", rep, flag=protected, context=context)
    protected = protected or ctx is None or ctx.protected
    check_finite(doc, rep)
    if not isinstance(doc, dict):
        return rep
    check_contract_version(doc, rep, protected or strict_versions)
    skill_names.check_artifact(doc, rep)  # retired and unknown skill names (contracts 3.0.0)
    check_unknown_keys(doc, rep)
    at = doc.get("artifact_type")
    ext_schema = EXTENSION_SCHEMAS.get(at) if isinstance(at, str) else None  # a wrong type is already a finding
    if at == "communication":
        from contracts.communication import extension_schema  # the capability selects the legacy or traceability schema
        ext_schema = extension_schema(doc)
    ext: Any = doc.get("extension")
    if ext_schema and isinstance(ext, dict):
        validate(ext, ext_schema, vocab, rep, "$.extension")
        if at == "response" and (strict or _at_least(doc.get("contract_version"), RESPONSE_HARDENING_FROM)):
            validate(ext, "ext_response_v2_8.json", vocab, rep, "$.extension")
        # Semantic rules assume the value types the schema guarantees; on a type error report that alone.
        if not any(f.code in SHAPE_ERRORS for f in rep.errors):
            _rules(doc, ext, vocab, rep, strict)
            if at == "statistical-result":
                if strict or _at_least(doc.get("contract_version"), STAT_SEMANTICS_FROM):
                    validate(ext, "ext_statistical_result_v2_2.json", vocab, rep, "$.extension")
                if strict or _at_least(doc.get("contract_version"), STAT_HARDENING_FROM):
                    validate(ext, "ext_statistical_result_v2_6.json", vocab, rep, "$.extension")
                if not any(f.code in SHAPE_ERRORS for f in rep.errors):
                    _stat_semantics(doc, ext, rep, strict)
                    if strict or _at_least(doc.get("contract_version"), ML_SEMANTICS_V2_FROM):
                        _observable_source(doc, ext, rep)
    if any(f.code == "ml.handoff_unknown" for f in rep.findings):  # the ml rule already reports the unknown handoff
        rep.findings = [f for f in rep.findings if f.code != skill_names.HANDOFF_CODE]
    return rep


def _referenced_paths(doc: Any, root: Path) -> set[Path]:
    """Resolved paths of the strings in an artifact that name a file under root (absolute, or relative to root or to
    the project folder above it)."""
    out: set[Path] = set()
    stack = [doc]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)
        elif isinstance(v, str) and 0 < len(v) < 4096 and "\n" not in v:
            p = Path(v)
            for cand in ([p] if p.is_absolute() else [root / p, root.parent / p]):
                try:
                    if cand.is_file():
                        out.add(cand.resolve())
                except (OSError, ValueError):
                    pass
    return out


def validate_directory(root: Path, vocab: Vocabulary, **flags) -> dict:
    """Validate every JSON file under an artifacts_dir (suffix .json in any case): each must be a valid artifact, or a
    sidecar that an artifact in the directory refers to by path (a split report, a model file; listed under
    'sidecars'). An unreferenced JSON file without an artifact_type is an error (artifacts_dir.not_artifact: working
    files and raw tool outputs belong outside artifacts_dir); an unreferenced file of another kind is a warning
    (artifacts_dir.non_json). Hidden files are skipped."""
    top, files, docs, other = Report(), [], {}, []
    paths = sorted(f for f in root.rglob("*") if f.is_file()
                   and not any(part.startswith(".") for part in f.relative_to(root).parts))
    for f in paths:
        rel = f.relative_to(root).as_posix()
        if f.suffix.lower() != ".json":  # bad.JSON is a JSON file too, validated like bad.json
            other.append(f)
            continue
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            top.add("error", rel, "artifacts_dir.unreadable", f"cannot read: {exc}")
            continue
        if isinstance(doc, dict) and "artifact_type" in doc:
            docs[f] = doc
        else:
            other.append(f)
    referenced: set[Path] = set()
    for doc in docs.values():
        referenced |= _referenced_paths(doc, root)
    sidecars = []
    for f in other:
        rel = f.relative_to(root).as_posix()
        if f.resolve() in referenced:
            sidecars.append(rel)
        elif f.suffix.lower() == ".json":
            top.add("error", rel, "artifacts_dir.not_artifact",
                    "no artifact_type and no artifact refers to it: write it as an artifact or move this working file "
                    "out of artifacts_dir")
        else:
            top.add("warning", rel, "artifacts_dir.non_json", "not a JSON artifact and no artifact refers to it")
    for f, doc in docs.items():
        rep = validate_artifact(doc, vocab, **flags)
        files.append({"path": f.relative_to(root).as_posix(), **rep.as_dict()})
    if not paths:
        top.add("warning", ".", "artifacts_dir.empty", "no files in the directory")
    ok = top.ok and all(e["ok"] for e in files)
    return {"ok": ok, "directory": str(root), "findings": [f.as_dict() for f in top.findings], "files": files,
            "sidecars": sidecars}


@protected_main("contracts.validate", keep_flag=True, capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    takes_value = {"--profiles-from", "--gate"}
    positional = [a for k, a in enumerate(args) if not a.startswith("--") and (k == 0 or args[k - 1] not in takes_value)]
    if not positional:
        print(json.dumps({"ok": False, "error": "no artifact path given"}))
        return 2
    target = Path(positional[0])
    if target.is_dir() and "--gate" in args:
        print(json.dumps({"ok": False, "error": "--gate takes one artifact, not a directory"}))
        return 2
    doc: Any = None
    if not target.is_dir():
        try:
            doc = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(json.dumps({"ok": False, "error": f"cannot read {positional[0]}: {exc}"}))
            return 2
    vocab, pre = Vocabulary(), Report()
    if "--profiles-from" in args:
        from contracts.project import load_project
        i = args.index("--profiles-from") + 1
        if i >= len(args):
            print(json.dumps({"ok": False, "error": "--profiles-from needs a project config path"}))
            return 2
        try:
            proj = load_project(Path(args[i]))
        except (OSError, ValueError) as exc:
            print(json.dumps({"ok": False, "error": f"cannot read {args[i]}: {exc}"}))
            return 2
        vocab = Vocabulary.with_profiles(proj.profiles)
        pre.findings += proj.report.findings
        for prob in vocab.problems:
            pre.add("error", "config.profiles", "profile.vocab_namespace", prob)
    gate = None
    if "--gate" in args:
        i = args.index("--gate") + 1
        if i >= len(args) or args[i] != "publication":
            print(json.dumps({"ok": False, "error": "--gate takes 'publication'"}))
            return 2
        gate = publication_gate(doc, vocab, base_dir=Path(positional[0]).resolve().parent)
    flags = {"protected": "--protected" in args, "strict": "--strict" in args,
             "strict_versions": "--strict-versions" in args}
    if doc is None:
        out = validate_directory(target, vocab, **flags)
        out["findings"][:0] = [f.as_dict() for f in pre.findings]
        out["ok"] = out["ok"] and pre.ok
        print(json.dumps(out, indent=1))
        return 0 if out["ok"] else 1
    rep = validate_artifact(doc, vocab, **flags)
    rep.findings[:0] = pre.findings
    out = rep.as_dict()
    if gate is not None:
        out["gate"] = gate
    print(json.dumps(out, indent=1))
    return 0 if rep.ok and (gate is None or gate["status"] == "passed") else 1


if __name__ == "__main__":
    sys.exit(main())
