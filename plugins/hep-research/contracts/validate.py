#!/usr/bin/env python3
"""Validate a hep-research artifact: common envelope + typed extension + semantic rules.

Usage: python3 contracts/validate.py ARTIFACT.json [--profiles-from PROJECT_CONFIG.json] [--protected] [--strict]
                                    [--gate publication]
Exit codes: 0 valid (and, with --gate, the gate passed), 1 findings with errors (or the gate failed or is unresolved),
2 unreadable input or bad usage. Output: JSON report on stdout.
A valid artifact is self-consistent under the contract; that says nothing about physical validity, and this check is
advisory: it never authorizes a use. --protected applies the stricter version policy for protected use (a newer
minor contract version is an error, not a warning). --strict applies the statistical-result semantic rules of
contracts 2.2.0 (p-values and confidence levels in range, ordered expected bands, typed coverage and global
calibration) and the response semantic rules of contracts 2.4.0 (controlled correction vocabulary, a matrix or
matrix_ref, normalization consistent with what sits inside the matrix, one unit per variable) and the ml-artifact
rules of contracts 2.5.0 (non-blank grouping key, model hash, labels and features; training domain on the features
with lo < hi; split-overlap result; calibration where the output must be calibrated, not evaluated on its fit sample;
domain-shift check; seeds) to artifacts written under older contracts, which otherwise keep their outcome. --gate publication adds
the publication gate of a statistical-result (publication_gate): passed, unresolved or failed, with reasons; an
archived artifact may be valid and still not pass it. Passing the gate is a contract-level prerequisite for
reporting a result as validated, not evidence of scientific validity.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402
from contracts.semver import parse  # noqa: E402
from contracts.vocab import NAMESPACED, Vocabulary  # noqa: E402

EXTENSION_SCHEMAS = {
    "measurement-spec": "ext_measurement_spec.json", "response": "ext_response.json",
    "theory-spec": "ext_theory_spec.json", "prediction": "ext_prediction.json",
    "comparison-spec": "ext_comparison_spec.json", "statistical-result": "ext_statistical_result.json",
    "ml-artifact": "ext_ml_artifact.json", "computational-run": "ext_computational_run.json",
    "communication": "ext_communication.json", "dataset-record": "ext_dataset_record.json",
}
# Statuses that must survive every handoff: a consumer of such an input carries the label.
STICKY_STATUSES = ["failed", "unvalidated", "preliminary", "synthetic", "asimov", "user-supplied"]
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
    elif t == "communication":
        from contracts.communication import validate_extension  # lazy: communication imports this module's constants
        validate_extension(doc, vocab, rep)


RHAT_MAX = 1.01  # [Proposal] threshold for stats.convergence_mismatch
RESPONSE_SEMANTICS_FROM = "2.4.0"  # response semantic rules apply natively from this contract version


def _correction_classes(terms) -> set[str]:
    """Classes of response corrections: every '<x>_efficiency' (namespaced or not) counts as 'efficiency'."""
    out = set()
    for t in terms:
        bare = t.split(":", 1)[-1]
        out.add("efficiency" if bare == "efficiency" or bare.endswith("_efficiency") else bare)
    return out


def _response_semantics(ext: dict, vocab: Vocabulary, rep: Report) -> None:
    """Response rules of contracts 2.4.0 (detector-response review 2026-10-12). Native for artifacts of contract 2.4.0
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
    """ml-artifact content rules of contracts 2.5.0 (physics-ml review 2026-10-13). Native for artifacts of contract
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
        if not ext.get(key):
            rep.add("error", f"$.extension.{key}", f"ml.{key}_missing",
                    f"{key} is empty" + (": list the targets (class labels, regression targets or generated variables)"
                                         if key == "labels" else ": list the model inputs"))
    names = _feature_names(ext.get("features"))
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


STAT_SEMANTICS_FROM = "2.2.0"  # statistical-result semantic rules apply natively from this contract version
BAND_KEYS = ("band_1sigma", "band_2sigma")


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


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
        _bayesian_rules(ext, rep)
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


GRADIENT_SAMPLERS = re.compile(r"\b(nuts|hmc|hamiltonian)\b", re.I)
SAMPLER_METADATA = ("warmup", "chains", "draws", "divergences", "e_bfmi_min", "max_treedepth_hits")
IMPROPER_FORMS = re.compile(r"^\s*(flat|improper|uniform\s*\(\s*-?inf|uniform\[\s*-?inf)", re.I)
E_BFMI_MIN = 0.3  # Stan's warning threshold


def _bayesian_rules(ext: dict, rep: Report) -> None:
    """Bayesian results (audit T25): gradient-based samplers carry their warmup, chains, draws, divergences, E-BFMI and
    tree-depth saturations; divergences or a low E-BFMI under fit_status converged are errors; an improper prior is
    unresolved until the posterior's propriety is shown; SBC is calibration over the prior predictive, so it is not
    reported as frequentist coverage."""
    smp: Any = ext.get("sampler")
    conv = ext.get("fit_status") == "converged"
    if isinstance(smp, dict) and GRADIENT_SAMPLERS.search(str(smp.get("name", "")) + " " + str(smp.get("algorithm", ""))):
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
        if isinstance(pr, dict) and IMPROPER_FORMS.search(str(pr.get("form", ""))) and not pr.get("propriety"):
            rep.add("unresolved", f"$.extension.priors[{i}]", "stats.improper_prior",
                    f"prior '{pr.get('form')}' on {pr.get('parameter')} is improper: state why the posterior is proper "
                    "(priors[].propriety) or use a proper prior")
    if "coverage" in ext:
        rep.add("error", "$.extension.coverage", "stats.paradigm_mislabeled",
                "a Bayesian result reports calibration (for example SBC) under checks, not frequentist coverage")


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


def publication_gate(doc: dict, vocab: Vocabulary | None = None) -> dict:
    """Publication gate of a statistical-result (T07): status passed, unresolved or failed, with reasons.

    failed: the artifact has errors under strict validation, carries the 'failed' status, its fit failed or was not
    run, or its fit diagnostics failed. unresolved: anything not yet established: an 'unvalidated' or 'preliminary'
    label, unresolved inputs, fit_status converged-with-warnings, untyped or not-checked coverage (frequentist), a scan
    without a global p-value and its trials_method, a Bayesian result without numeric R-hat and ESS, or no model and
    backend provenance (likelihood.backend with likelihood.model_ref or model_sha256). Passing says the contract-level
    prerequisites for reporting the result as validated are present; it is not a scientific validation."""
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
            interval: Any = cov.get("interval")
            upper = interval[1] if isinstance(interval, list) and len(interval) == 2 and _is_num(interval[1]) else value
            if upper < nominal - 0.01:
                add("failed", "gate.undercoverage", f"recorded coverage {value} (upper end {upper}) is below the nominal "
                                                    f"{nominal} by more than 0.01")
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
    if not (lik.get("backend") and (lik.get("model_ref") or lik.get("model_sha256"))):
        add("unresolved", "gate.model_provenance_missing", "likelihood.backend and a model_ref or model_sha256 are required")
    levels = {r["level"] for r in reasons}
    status_out = "failed" if "failed" in levels else ("unresolved" if levels else "passed")
    return {"gate": "publication", "status": status_out, "reasons": reasons}


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


ENVELOPE_KEYS = {"contract_version", "artifact_id", "artifact_type", "objective", "bindings", "versions", "provenance",
                 "inputs", "outputs", "status", "handoff", "unresolved_inputs", "extension", "required_capabilities",
                 "data_exposure"}


def check_unknown_keys(doc: dict, rep: Report) -> None:
    """Unknown top-level keys are accepted but not propagated by any consumer: say so (P02, K03)."""
    for key in sorted(set(doc) - ENVELOPE_KEYS):
        rep.add("warning", f"$.{key}", "envelope.unknown_key",
                f"'{key}' is not an envelope field: no consumer reads or propagates it")


def validate_artifact(doc, vocab: Vocabulary | None = None, protected: bool = False, strict: bool = False) -> Report:
    vocab = vocab or Vocabulary()
    rep = validate(doc, "envelope.json", vocab)
    check_finite(doc, rep)
    if not isinstance(doc, dict):
        return rep
    check_contract_version(doc, rep, protected)
    check_unknown_keys(doc, rep)
    at = doc.get("artifact_type")
    ext_schema = EXTENSION_SCHEMAS.get(at) if isinstance(at, str) else None  # a wrong type is already a finding
    if at == "communication":
        from contracts.communication import extension_schema  # the capability selects the legacy or traceability schema
        ext_schema = extension_schema(doc)
    ext: Any = doc.get("extension")
    if ext_schema and isinstance(ext, dict):
        validate(ext, ext_schema, vocab, rep, "$.extension")
        # Semantic rules assume the value types the schema guarantees; on a type error report that alone.
        if not any(f.code in SHAPE_ERRORS for f in rep.errors):
            _rules(doc, ext, vocab, rep, strict)
            if at == "statistical-result":
                if strict or _at_least(doc.get("contract_version"), STAT_SEMANTICS_FROM):
                    validate(ext, "ext_statistical_result_v2_2.json", vocab, rep, "$.extension")
                if not any(f.code in SHAPE_ERRORS for f in rep.errors):
                    _stat_semantics(doc, ext, rep, strict)
    return rep


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"cannot read {args[0]}: {exc}"}))
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
        gate = publication_gate(doc, vocab)
    rep = validate_artifact(doc, vocab, protected="--protected" in args, strict="--strict" in args)
    rep.findings[:0] = pre.findings
    out = rep.as_dict()
    if gate is not None:
        out["gate"] = gate
    print(json.dumps(out, indent=1))
    return 0 if rep.ok and (gate is None or gate["status"] == "passed") else 1


if __name__ == "__main__":
    sys.exit(main())
