#!/usr/bin/env python3
"""Write an ml-artifact (contracts 2.5.0) from a training run summary and validate it.

Purpose: turn what a training run recorded into the contract record that a downstream skill reads, without
retyping it, and refuse to write a record that the contract rejects: a split that leaked, a probability output
without a calibration, a calibration evaluated on its fit sample, a training domain on variables that are not
features. The artifact says what was checked; it does not make the model valid for an analysis.

What it does: copies task, labels, features, units, grouping key, training domain, preprocessing, weights, model
hash, environment and metrics from the run summary into the extension; takes the split-overlap result from
--split-report (the JSON of check_split_integrity.py --json: passed -> pass, failed -> fail, incomplete -> not-run,
with test_groups_disjoint from its group leakage when the group metadata was complete) or else from the summary's
split_check; adds the calibration, domain-shift check and downstream validations when given; lists every input
file with its sha256 and the checkpoint and score files as outputs; fills the envelope (contract and plugin
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
  --status       artifact status label, repeatable (synthetic, unvalidated, preliminary, ...; default unvalidated)
  --output-semantics probability|score|density-ratio|regression-value|generated-sample (probability and
                 density-ratio need a calibration)
Output: the artifact at --out, and a JSON summary on stdout (status written or invalid, findings).
Exit codes: 0 written (valid; it may carry warnings or unresolved findings), 1 not written because the artifact has
validation errors (listed), 2 unreadable or malformed input.
Standard library only; PyTorch is not required.
Run: python3 <plugin root>/skills/physics-ml/scripts/write_ml_artifact.py --run-summary run_summary.json \
       --calibration calibration.json --split-report split_report.json --output-semantics probability \
       --status synthetic --out ml_artifact.json
"""
from __future__ import annotations

import argparse
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


def overlap_from_report(report: dict, ref: str) -> tuple[dict, bool | None]:
    """overlap_check and test_groups_disjoint from check_split_integrity.py --json output."""
    status = report.get("status")
    if status not in SPLIT_STATUS:
        raise ValueError(f"split report status {status!r} is not passed, failed or incomplete")
    check = {"tool": "check_split_integrity.py", "result": SPLIT_STATUS[status], "report": ref}
    leak = report.get("group_leakage") or {}
    if any(any("test" in str(s) for s in splits) for splits in leak.values()):
        return check, False
    return check, (True if report.get("groups_checked") and any("test" in str(s) for s in report.get("splits", {}))
                   else None)


def build(a: argparse.Namespace) -> dict:
    summary, digest = _load(a.run_summary)
    if not isinstance(summary, dict):
        raise ValueError("the run summary must be a JSON object")
    missing = [k for k in REQUIRED if k not in summary]
    if missing:
        raise ValueError(f"the run summary lacks {', '.join(missing)}")
    inputs = [{"ref": a.run_summary, "sha256": digest}]
    splits: dict = {"grouping_key": summary["grouping_key"]}
    if summary.get("split_manifest"):
        splits["manifest"] = summary["split_manifest"]
    sc = summary.get("split_check")
    if isinstance(sc, dict) and sc.get("result"):
        splits["overlap_check"] = {k: sc[k] for k in ("tool", "result", "report") if sc.get(k) is not None}
        splits["overlap_check"].setdefault("tool", "unspecified")
    if a.split_report:
        report, h = _load(a.split_report)
        if not isinstance(report, dict):
            raise ValueError("the split report must be a JSON object (check_split_integrity.py --json)")
        splits["overlap_check"], disjoint = overlap_from_report(report, a.split_report)
        if disjoint is not None:
            splits["test_groups_disjoint"] = disjoint
        inputs.append({"ref": a.split_report, "sha256": h})
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
        ext["calibration"] = cal["calibration"]
        inputs.append({"ref": a.calibration, "sha256": h})
    if a.domain_shift:
        ds, h = _load(a.domain_shift)
        ds = ds.get("domain_shift", ds) if isinstance(ds, dict) else ds
        if not isinstance(ds, dict):
            raise ValueError("the domain-shift file must be a JSON object")
        ext["domain_shift"] = ds
        inputs.append({"ref": a.domain_shift, "sha256": h})
    ext["downstream_validation"] = []
    if a.downstream:
        dv, h = _load(a.downstream)
        if not isinstance(dv, list):
            raise ValueError("the downstream file must be a JSON list")
        ext["downstream_validation"] = dv
        inputs.append({"ref": a.downstream, "sha256": h})
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
            "provenance": {"producer_skill": "physics-ml", "created": a.created, "evidence_ids": []},
            "inputs": inputs, "outputs": outputs, "status": list(dict.fromkeys(a.status or ["unvalidated"])),
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
