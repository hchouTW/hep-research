#!/usr/bin/env python3
"""Validate a hep-research artifact: common envelope + typed extension + semantic rules.

Usage: python3 contracts/validate.py ARTIFACT.json [--profiles-from PROJECT_CONFIG.json]
Exit codes: 0 valid, 1 findings with errors, 2 unreadable input or bad usage. Output: JSON report on stdout.
A valid artifact is self-consistent under the contract; that says nothing about physical validity.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402
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


def _rules(doc: dict, ext: dict, vocab: Vocabulary, rep: Report) -> None:
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
    elif t == "theory-spec":
        if doc.get("bindings", {}).get("experiments"):
            rep.add("error", "$.bindings.experiments", "theory.experiment_binding",
                    "a theory spec carries no experiment binding; bind data in a comparison spec")
        check_conventions(ext.get("conventions", {}), vocab, rep, "$.extension.conventions")
        for bad in sorted(EXPERIMENT_ONLY_FIELDS & set(ext)):
            rep.add("error", f"$.extension.{bad}", "theory.experiment_field", f"experiment field '{bad}' in a theory spec")
    elif t == "prediction":
        for i, u in enumerate(ext.get("uncertainties", [])):
            if u.get("kind") in NON_GAUSSIAN_KINDS and u.get("gaussian") is True:
                rep.add("error", f"$.extension.uncertainties[{i}]", "uncertainty.auto_gaussian",
                        f"'{u['kind']}' must not be treated as Gaussian without a hep-theory prescription")
        if isinstance(ext.get("values"), dict):
            check_binned(ext["values"], rep, "$.extension.values", ext.get("observable"))
        rp = ext.get("representation")
        need = {"numerical": "values", "grid": "values", "symbolic": "expression"}.get(rp)
        if need and not ext.get(need):
            rep.add("error", f"$.extension.{need}", "prediction.payload_missing",
                    f"a {rp} prediction needs '{need}' (numbers kept elsewhere: reference them and use a metadata record)")
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
        p = ext.get("paradigm")
        need = {"frequentist": ["test_statistic", "construction", "coverage"],
                "bayesian": ["priors", "sampler", "convergence"]}.get(p, [])
        for k in need:
            if not ext.get(k):
                rep.add("error", f"$.extension.{k}", "stats.paradigm_incomplete", f"{p} result requires '{k}'")
        wrong = {"frequentist": ["priors", "sampler"], "bayesian": ["construction", "test_statistic"]}.get(p, [])
        for k in wrong:
            if k in ext:
                rep.add("error", f"$.extension.{k}", "stats.paradigm_mislabeled", f"'{k}' does not belong to a {p} result")
        if ext.get("fit_status") == "failed" and "failed" not in status:
            rep.add("error", "$.status", "status.failed_unlabeled", "failed fit must carry the 'failed' status")
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
    elif t == "communication":
        for i, c in enumerate(ext.get("claims", [])):
            cs = c.get("status")
            cs = set(cs) if isinstance(cs, list) else {cs}
            missing = sorted(set(required_statuses(doc.get("inputs", []))) - cs)
            if missing or (cs & UPGRADED and inherited & set(STICKY_STATUSES)):
                rep.add("error", f"$.extension.claims[{i}].status", "communication.status_upgraded",
                        f"a claim must keep its inputs' statuses {missing or sorted(inherited & set(STICKY_STATUSES))}; communication never upgrades status")


def validate_artifact(doc, vocab: Vocabulary | None = None) -> Report:
    vocab = vocab or Vocabulary()
    rep = validate(doc, "envelope.json", vocab)
    check_finite(doc, rep)
    if not isinstance(doc, dict):
        return rep
    ext_schema = EXTENSION_SCHEMAS.get(doc.get("artifact_type"))
    ext = doc.get("extension")
    if ext_schema and isinstance(ext, dict):
        validate(ext, ext_schema, vocab, rep, "$.extension")
        # Semantic rules assume the value types the schema guarantees; on a type error report that alone.
        if not any(f.code in SHAPE_ERRORS for f in rep.errors):
            _rules(doc, ext, vocab, rep)
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
    rep = validate_artifact(doc, vocab)
    rep.findings[:0] = pre.findings
    print(json.dumps(rep.as_dict(), indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
