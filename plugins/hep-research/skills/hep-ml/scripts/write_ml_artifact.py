#!/usr/bin/env python3
"""Write an ml-artifact (contracts 2.5.0) from a training run summary and validate it.

Purpose: turn what a training run recorded into the contract record that a downstream skill reads, without
retyping it, and refuse to write a record that the contract rejects: a split that leaked, a probability output
without a calibration, a calibration evaluated on its fit sample, a training domain on variables that are not
features. The artifact says what was checked; it does not make the model valid for an analysis.

What it does: copies task, labels, features, units, grouping key, training domain, preprocessing, weights, model
hash, environment and metrics from the run summary into the extension; takes the split-overlap result from
--split-report or else from the report file the summary's split_check names (the JSON of check_split_integrity.py
--json: passed -> pass, failed -> fail, incomplete -> not-run). The verdict is recomputed from the report body
(overlaps, duplicates, group leakage, temporal violations, coverage); a "passed" status the body contradicts is
refused. test_groups_disjoint comes from its group leakage when the group metadata was complete, with the test split
named by the manifest's "roles": {"test": NAME} (default "test", case-insensitive). A summary split_check with no
report behind it is recorded as not-run, never as pass; adds the calibration, domain-shift check and downstream
validations when given; lists every file it read with its sha256 in extension.source_files (tool outputs, not
artifacts, so not inputs[]) and the checkpoint and score files as outputs; fills the envelope (contract and plugin
versions, plugin_release identity, status labels). It then validates the artifact with contracts/validate.py
(validate_artifact) and writes it only when there is no error. Warnings and unresolved findings are reported and
kept: an unresolved artifact is valid but not yet usable as a final result.

Input:
  --run-summary  JSON written by train_classifier.py: {"task", "features", "units", "labels", "grouping_key",
                 "split_manifest", "split_check": {"tool", "result": pass|fail|not-run, "report"}, "training_domain":
                 {f: [lo, hi]}, "preprocessing": [...], "weights": {"source", "negative_weight_treatment",
                 "class_balancing", "used_in"}, "model_hash", "checkpoint", "environment": {"torch_version", "device",
                 "precision", "seeds"}, "metrics": {"val", "test"}, "scores": {"test": path}}
  --calibration  JSON with a top-level "calibration": {"method", "params", "fit_sample", "validation": {"metric",
                 "sample", "before", "after", "bins", "binning"}}
  --domain-shift JSON {"control_sample", "method", "result", "status"} (or wrapped in "domain_shift")
  --downstream   JSON list of downstream validations ({"metric", ...} each)
  --split-report JSON output of check_split_integrity.py --json
  --status       artifact status label, repeatable (synthetic, unvalidated, preliminary, ...); added to the run
                 summary's own "status"; with neither, the writer refuses (exit 2)
  --output-semantics probability|score|density-ratio|regression-value|generated-sample (probability and
                 density-ratio need a calibration)
Output: the artifact at --out, and a JSON summary on stdout (status written or invalid, findings).
Exit codes: 0 written (valid; it may carry warnings or unresolved findings), 1 not written because the artifact has
validation errors (listed), 2 unreadable or malformed input.
Standard library only; PyTorch is not required.
Run: python3 <plugin root>/skills/hep-ml/scripts/write_ml_artifact.py --run-summary run_summary.json \
       --calibration calibration.json --split-report split_report.json --output-semantics probability \
       --status synthetic --out ml_artifact.json
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

LABELS = ("synthetic", "asimov", "observed", "preliminary", "unvalidated", "user-supplied", "failed")
OUTPUT_SEMANTICS = ("probability", "score", "density-ratio", "regression-value", "generated-sample")
SPLIT_STATUS = {"passed": "pass", "failed": "fail", "incomplete": "not-run"}
REQUIRED = ("task", "features", "labels", "grouping_key", "training_domain", "model_hash")


def _load(path: str):
    raw = Path(path).read_bytes()
    try:
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except ValueError as exc:
        raise ValueError(f"{path} is not JSON: {exc}") from exc


LEAK_KEYS = ("duplicates_within_split", "overlaps_between_splits", "group_leakage", "temporal_violations")


def verdict_from_body(report: dict) -> str:
    """The split verdict recomputed from the report body, not from its status line: failed when any leakage is listed,
    incomplete when group or timestamp metadata is incomplete, passed otherwise."""
    if any(report.get(key) for key in LEAK_KEYS):
        return "failed"
    cov = report.get("group_coverage") if isinstance(report.get("group_coverage"), dict) else {}
    tcov = report.get("timestamp_coverage") if isinstance(report.get("timestamp_coverage"), dict) else None
    complete = report.get("groups_checked") is True and cov.get("covered") == cov.get("total")
    if tcov is not None and tcov.get("covered") != tcov.get("total"):
        complete = False
    return "passed" if complete else "incomplete"


def overlap_from_report(report: dict, ref: str, test_split: str = "test") -> tuple[dict, bool | None]:
    """overlap_check and test_groups_disjoint from check_split_integrity.py --json output.

    The verdict is the worse of the report's status and the verdict recomputed from its body; a "passed" status that
    the body contradicts is refused (ValueError). The test split is `test_split` (the manifest's roles.test, default
    "test"), compared case-insensitively."""
    status = report.get("status")
    if status not in SPLIT_STATUS:
        raise ValueError(f"split report status {status!r} is not passed, failed or incomplete")
    body = verdict_from_body(report)
    if status == "passed" and body != "passed":
        raise ValueError(f"split report {ref} says passed but its body contradicts it ({body}: "
                         f"{[k for k in LEAK_KEYS if report.get(k)] or 'incomplete group or timestamp metadata'})")
    order = ("passed", "incomplete", "failed")
    verdict = max(status, body, key=order.index)
    check = {"tool": "check_split_integrity.py", "result": SPLIT_STATUS[verdict], "report": ref}
    test = test_split.casefold()
    leak = report.get("group_leakage") or {}
    if any(any(str(s).casefold() == test for s in splits) for splits in leak.values()):
        return check, False
    names = {str(s).casefold() for s in report.get("splits", {})}
    return check, (True if report.get("groups_checked") and test in names else None)


def test_split_name(summary: dict) -> str:
    """Name of the test split: roles.test of the split manifest when it can be read, else "test"."""
    path = summary.get("split_manifest")
    with contextlib.suppress(OSError, ValueError, TypeError, AttributeError):
        roles = json.loads(Path(path).read_text(encoding="utf-8")).get("roles") or {}
        if isinstance(roles.get("test"), str) and roles["test"].strip():
            return roles["test"].strip()
    return "test"


def statuses(summary: dict, given) -> list:
    """Status labels: the run summary's own labels (train_classifier.py writes "synthetic" on its synthetic path) plus
    --status; with neither there is no basis for a label, and the writer refuses rather than default."""
    own = summary.get("status")
    own = [own] if isinstance(own, str) else list(own or [])
    bad = [x for x in own if x not in LABELS]
    if bad:
        raise ValueError(f"the run summary carries unknown status labels {bad}")
    labels = list(dict.fromkeys(own + list(given or [])))
    if not labels:
        raise ValueError("no status label: pass --status (synthetic, observed, ...) or record 'status' in the run "
                         "summary; the writer no longer defaults to 'unvalidated', which would drop 'synthetic'")
    return labels


def build(a: argparse.Namespace) -> dict:
    summary, digest = _load(a.run_summary)
    if not isinstance(summary, dict):
        raise ValueError("the run summary must be a JSON object")
    missing = [k for k in REQUIRED if k not in summary]
    if missing:
        raise ValueError(f"the run summary lacks {', '.join(missing)}")
    # tool outputs are files, not contract artifacts: they go to extension.source_files, never inputs[] (which
    # contracts/dependencies.py resolves and validates as artifacts)
    inputs: list = []
    sources = [{"ref": a.run_summary, "sha256": digest, "role": "run-summary"}]
    splits: dict = {"grouping_key": summary["grouping_key"]}
    if summary.get("split_manifest"):
        splits["manifest"] = summary["split_manifest"]
    test_split = test_split_name(summary)
    sc = summary.get("split_check")
    report_path = a.split_report
    if not report_path and isinstance(sc, dict) and sc.get("result"):
        if sc.get("report") and Path(str(sc["report"])).is_file():
            report_path = str(sc["report"])  # the report behind the summary's claim is read, not its result line
        else:
            # a pass with no report or manifest behind it is a claim, not a check
            splits["overlap_check"] = {"tool": str(sc.get("tool") or "unspecified"),
                                       "result": "fail" if sc["result"] == "fail" else "not-run"}
    if report_path:
        report, h = _load(report_path)
        if not isinstance(report, dict):
            raise ValueError("the split report must be a JSON object (check_split_integrity.py --json)")
        splits["overlap_check"], disjoint = overlap_from_report(report, report_path, test_split)
        if disjoint is not None:
            splits["test_groups_disjoint"] = disjoint
        sources.append({"ref": report_path, "sha256": h, "role": "split-report"})
    ext: dict = {"task": summary["task"], "labels": summary["labels"], "features": summary["features"],
                 "splits": splits, "training_domain": summary["training_domain"],
                 "preprocessing": summary.get("preprocessing") or [], "model_hash": summary["model_hash"]}
    for key in ("units", "weights", "environment", "metrics"):
        if summary.get(key) is not None:
            ext[key] = summary[key]
    semantics = a.output_semantics or summary.get("output_semantics")
    if semantics:
        ext["output_semantics"] = semantics
    if a.calibration:
        cal, h = _load(a.calibration)
        if not (isinstance(cal, dict) and isinstance(cal.get("calibration"), dict)):
            raise ValueError("the calibration file needs a top-level 'calibration' object")
        ext["calibration"] = dict(cal["calibration"])
        if isinstance(cal.get("sample_check"), dict):  # older calibration.py output keeps it beside the block
            ext["calibration"].setdefault("sample_check", cal["sample_check"])
        sources.append({"ref": a.calibration, "sha256": h, "role": "calibration"})
    if a.domain_shift:
        ds, h = _load(a.domain_shift)
        ds = ds.get("domain_shift", ds) if isinstance(ds, dict) else ds
        if not isinstance(ds, dict):
            raise ValueError("the domain-shift file must be a JSON object")
        ext["domain_shift"] = ds
        sources.append({"ref": a.domain_shift, "sha256": h, "role": "domain-shift"})
    ext["downstream_validation"] = []
    if a.downstream:
        dv, h = _load(a.downstream)
        if not isinstance(dv, list):
            raise ValueError("the downstream file must be a JSON list")
        ext["downstream_validation"] = dv
        sources.append({"ref": a.downstream, "sha256": h, "role": "downstream-validation"})
    ext["source_files"] = sources
    outputs = [{"ref": summary["checkpoint"], "kind": "checkpoint"}] if summary.get("checkpoint") else []
    for split, path in sorted((summary.get("scores") or {}).items()):
        if path:
            outputs.append({"ref": path, "kind": f"scores:{split}"})
    plugin_version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    model = str(summary["model_hash"]).split(":", 1)[-1][:12] or "unnamed"
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": a.artifact_id or f"ml-{summary['task']}-{model}",
            "artifact_type": "ml-artifact", "objective": a.objective, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin_version, "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(),
                         "profiles": {}},
            "provenance": {"producer_skill": "hep-ml", "created": a.created, "evidence_ids": []},
            "inputs": inputs, "outputs": outputs, "status": statuses(summary, a.status),
            "unresolved_inputs": [], "extension": ext}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("--run-summary", required=True)
    p.add_argument("--calibration")
    p.add_argument("--domain-shift")
    p.add_argument("--downstream")
    p.add_argument("--split-report")
    p.add_argument("--status", action="append", choices=LABELS)
    p.add_argument("--output-semantics", choices=OUTPUT_SEMANTICS)
    p.add_argument("--artifact-id")
    p.add_argument("--objective", default="ml-artifact written from a training run summary")
    p.add_argument("--created", default=date.today().isoformat())
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        doc = build(a)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    rep = validate_artifact(doc)
    findings = rep.as_dict()["findings"]
    if not rep.ok:
        print(json.dumps({"status": "invalid", "out": None, "findings": findings}, indent=1))
        return 1
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "out": a.out, "labels": doc["status"], "findings": findings}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
