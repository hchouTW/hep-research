#!/usr/bin/env python3
"""Write a statistical-result artifact from the JSON output of a core/stats CLI, keeping its status.

The CLI's status decides the artifact's (audit T04): ok -> fit_status converged; incomplete (only toy fits failed)
-> converged-with-warnings; failed (a fit on the observed or Asimov data failed) -> fit_status failed and the
'failed' status label; rejected -> no artifact. The CLI's fit_diagnostics block is copied. A toy p-value with no
exceedance is written as a typed bound (significance.local_p_bound), never as p = 0. The model file, when given, is
hashed into likelihood.model_sha256 with likelihood.backend naming the CLI. Coverage is written only as declared
(--coverage-check, default not-checked): this script never claims coverage it did not see.

Usage:
  python3 result_artifact.py --cli-output OUT.json --poi mu --construction asymptotic --test-statistic q_mu_tilde \
      --label synthetic --artifact-id my-limit --out result.json [--model MODEL.json] [--backend NAME]
      [--coverage-check not-checked|toys|exact-construction|analytic --coverage-n-toys N --coverage-value C]
Exit codes: 0 written, the artifact validates and its CLI status was ok; 1 written but the CLI status was failed
or incomplete (the artifact says so), or the artifact does not validate (not written); 2 rejected input.
Standard library only.
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

FIT_STATUS = {"ok": "converged", "incomplete": "converged-with-warnings", "failed": "failed"}
LABELS = ("synthetic", "asimov", "observed", "preliminary", "unvalidated", "user-supplied")


def build(cli: dict, a: argparse.Namespace, model_bytes: bytes | None) -> dict:
    status = cli.get("status", "ok")
    if status not in FIT_STATUS:
        raise ValueError(f"CLI status {status!r} cannot become a result (rejected input or unknown status)")
    labels = list(dict.fromkeys(a.label))
    if status == "failed" and "failed" not in labels:
        labels.append("failed")
    ext: dict = {"paradigm": "frequentist",
                 "likelihood": {"form": cli.get("method", "see results"), "backend": a.backend or cli.get("label", "core/stats")},
                 "parameters_of_interest": a.poi, "nuisances": cli.get("nuisances", []),
                 "test_statistic": a.test_statistic, "construction": a.construction,
                 "fit_status": FIT_STATUS[status],
                 "coverage": {"check": a.coverage_check, "method": a.coverage_method}}
    if model_bytes is not None:
        ext["likelihood"]["model_sha256"] = hashlib.sha256(model_bytes).hexdigest()
        ext["likelihood"]["model_ref"] = a.model
    if a.coverage_n_toys is not None:
        ext["coverage"]["n_toys"] = a.coverage_n_toys
    if a.coverage_value is not None:
        ext["coverage"]["coverage"] = a.coverage_value
    if isinstance(cli.get("fit_diagnostics"), dict):
        ext["fit_diagnostics"] = cli["fit_diagnostics"]
    tail = cli.get("toy_tail")
    if "q0_observed" in cli and isinstance(tail, dict):
        if tail.get("estimate") is None and "upper_bound" in tail:
            ext["significance"] = {"local_p_bound": {"kind": "upper", "value": tail["upper_bound"]["value"],
                                                     "cl": tail["upper_bound"]["cl"], "convention": tail["convention"],
                                                     "k": tail["k"], "n": tail["n"]}}
        else:
            ext["significance"] = {"local_p": tail["estimate"]}
    ext["results"] = {k: v for k, v in cli.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    ext["results"]["cli_status"] = status
    if "cl" in cli:
        ext["results"]["cl"] = cli["cl"]
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": a.artifact_id, "artifact_type": "statistical-result",
            "objective": a.objective, "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                         "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {}},
            "provenance": {"producer_skill": "hep-statistics", "created": a.created, "evidence_ids": []},
            "inputs": [], "outputs": [], "status": labels, "unresolved_inputs": [],
            "required_capabilities": ["stats:result-semantics"], "extension": ext}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cli-output", required=True)
    p.add_argument("--poi", action="append", required=True)
    p.add_argument("--construction", required=True)
    p.add_argument("--test-statistic", required=True)
    p.add_argument("--label", action="append", required=True, choices=LABELS)
    p.add_argument("--artifact-id", required=True)
    p.add_argument("--objective", default="statistical result written from a core/stats CLI output")
    p.add_argument("--out", required=True)
    p.add_argument("--model")
    p.add_argument("--backend")
    p.add_argument("--coverage-check", default="not-checked", choices=("not-checked", "toys", "exact-construction", "analytic"))
    p.add_argument("--coverage-method", default="not studied by this run")
    p.add_argument("--coverage-n-toys", type=int)
    p.add_argument("--coverage-value", type=float)
    p.add_argument("--created", default=date.today().isoformat())
    a = p.parse_args(argv)
    try:
        cli = json.loads(Path(a.cli_output).read_text(encoding="utf-8"))
        model_bytes = Path(a.model).read_bytes() if a.model else None
        doc = build(cli, a, model_bytes)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    rep = validate_artifact(doc)
    if not rep.ok:
        print(json.dumps({"status": "invalid", "findings": rep.as_dict()["findings"]}, indent=1))
        return 1
    Path(a.out).write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "out": a.out, "fit_status": doc["extension"]["fit_status"],
                      "labels": doc["status"], "findings": rep.as_dict()["findings"]}, indent=1))
    return 0 if cli.get("status", "ok") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
