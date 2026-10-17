#!/usr/bin/env python3
"""Write a statistical-result artifact from the JSON output of a core/stats CLI, keeping its status.

The CLI's status decides the artifact's (audit T04): ok -> fit_status converged; incomplete (only toy fits failed)
-> converged-with-warnings; failed (a fit on the observed or Asimov data failed) -> fit_status failed and the
'failed' status label; rejected -> no artifact. The CLI's fit_diagnostics block is copied. A toy p-value with no
exceedance is written as a typed bound (significance.local_p_bound), never as p = 0. The model file, when given, is
hashed into likelihood.model_sha256 with likelihood.backend naming the CLI. Coverage is written only as declared
(--coverage-check, default not-checked): this script never claims coverage it did not see, and refuses a coverage
value or toy count under not-checked. A CLI output without a status is refused (exit 2) unless --assume-status names
it; the assumption is recorded in results.cli_status_assumed. A JSON input that is not an object is refused.

Paradigm (F-02): --paradigm frequentist (default) needs --construction and --test-statistic and writes the coverage
block. --paradigm bayesian reads the output of bayes_diagnostics.py diagnose as --cli-output (converged -> ok,
not-converged -> failed, incomplete -> incomplete), needs one --prior PARAM=FORM per parameter of interest and a
--sampler JSON object (name, chains, draws, and for a gradient-based sampler its warmup, divergences, e_bfmi_min,
max_treedepth_hits), writes priors, sampler and convergence (R-hat, bulk and tail ESS per parameter) and the posterior
quantiles as results.<param>_q<p>, and refuses the frequentist fields (construction, test statistic, coverage).
--paradigm likelihood-only writes construction and test statistic only when given.

Usage:
  python3 result_artifact.py --cli-output OUT.json --poi mu --construction asymptotic --test-statistic q_mu_tilde \
      --label synthetic --artifact-id my-limit --out result.json [--model MODEL.json] [--backend NAME]
      [--coverage-check not-checked|toys|exact-construction|analytic --coverage-n-toys N --coverage-value C]
      [--assume-status ok|incomplete|failed]
  python3 result_artifact.py --paradigm bayesian --cli-output DIAGNOSE.json --poi mu --prior "mu=uniform(0, 10)" \
      --sampler SAMPLER.json --label synthetic --artifact-id my-posterior --out result.json
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
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

FIT_STATUS = {"ok": "converged", "incomplete": "converged-with-warnings", "failed": "failed"}
PARADIGMS = ("frequentist", "bayesian", "likelihood-only")
DIAGNOSE_STATUS = {"converged": "ok", "not-converged": "failed", "incomplete": "incomplete"}  # bayes_diagnostics.py
LABELS = ("synthetic", "asimov", "observed", "preliminary", "unvalidated", "user-supplied")


def effective_status(cli, a: argparse.Namespace) -> str:
    """The CLI's own status; an output without one (for example from an older tool) is refused unless the caller
    states it with --assume-status, which is then recorded in results.cli_status_assumed (STH-T1.7)."""
    if not isinstance(cli, dict):
        raise ValueError(f"the CLI output must be a JSON object, got {type(cli).__name__}")
    if "status" in cli:
        if getattr(a, "paradigm", "frequentist") == "bayesian":
            return DIAGNOSE_STATUS.get(cli["status"], cli["status"])
        return cli["status"]
    if getattr(a, "assume_status", None):
        return a.assume_status
    raise ValueError("the CLI output has no 'status': a missing status is not a converged fit; rerun a core/stats CLI "
                     "that reports one, or state it with --assume-status ok|incomplete|failed (recorded in the artifact)")


def _priors(a: argparse.Namespace) -> list:
    out = []
    for item in a.prior or []:
        name, sep, form = item.partition("=")
        if not sep or not name.strip() or not form.strip():
            raise ValueError(f"--prior {item!r}: expected PARAM=FORM, for example mu=uniform(0, 10)")
        out.append({"parameter": name.strip(), "form": form.strip()})
    missing = [poi for poi in a.poi if poi not in {p["parameter"] for p in out}]
    if missing:
        raise ValueError(f"a Bayesian result needs a --prior for every parameter of interest; missing: {missing}")
    return out


def _bayesian(cli: dict, a: argparse.Namespace, ext: dict) -> None:
    """Priors, sampler and convergence of a Bayesian result from bayes_diagnostics.py diagnose output (F-02)."""
    given = [f for f, v in (("--construction", a.construction), ("--test-statistic", a.test_statistic),
                            ("--coverage-n-toys", a.coverage_n_toys), ("--coverage-value", a.coverage_value)) if v is not None]
    if given or a.coverage_check != "not-checked":
        raise ValueError(f"{given or ['--coverage-check']} belong to a frequentist result; a Bayesian result reports "
                         "calibration (for example SBC) separately, not coverage")
    params = cli.get("parameters")
    if not isinstance(params, dict):
        raise ValueError("a Bayesian --cli-output is the JSON of bayes_diagnostics.py diagnose (it has 'parameters')")
    if not a.sampler:
        raise ValueError("a Bayesian result needs --sampler SAMPLER.json (name, chains, draws, ...)")
    sampler = json.loads(Path(a.sampler).read_text(encoding="utf-8"))
    if not isinstance(sampler, dict) or not isinstance(sampler.get("name"), str):
        raise ValueError("--sampler must be a JSON object with at least a 'name'")
    chains = {p.get("chains") for p in params.values() if isinstance(p, dict)}
    if "chains" not in sampler and len(chains) == 1:
        sampler["chains"] = chains.pop()
    ext["priors"] = _priors(a)
    ext["sampler"] = sampler
    conv: dict = {k: {name: p.get(k) for name, p in params.items() if isinstance(p, dict) and k in p}
                  for k in ("rhat", "ess_bulk", "ess_tail")}
    conv["status"] = cli.get("status")
    if "method" in cli:
        conv["method"] = cli["method"]
    ext["convergence"] = conv
    ext["results"] = {f"{name}_q{q}": v["value"] for name, p in params.items() if isinstance(p, dict)
                      for q, v in (p.get("quantiles") or {}).items() if isinstance(v, dict) and isinstance(v.get("value"), (int, float))}


def build(cli: dict, a: argparse.Namespace, model_bytes: bytes | None) -> dict:
    status = effective_status(cli, a)
    if a.coverage_check == "not-checked" and (a.coverage_value is not None or a.coverage_n_toys is not None):
        raise ValueError("--coverage-check not-checked contradicts --coverage-value/--coverage-n-toys: give the check that "
                         "produced those numbers (toys), or drop them")
    if status not in FIT_STATUS:
        raise ValueError(f"CLI status {status!r} cannot become a result (rejected input or unknown status)")
    if a.paradigm == "frequentist" and (a.construction is None or a.test_statistic is None):
        raise ValueError("a frequentist result needs --construction and --test-statistic")
    if a.paradigm != "bayesian" and (a.prior or a.sampler):
        raise ValueError("--prior and --sampler belong to a Bayesian result (--paradigm bayesian)")
    labels = list(dict.fromkeys(a.label))
    if status == "failed" and "failed" not in labels:
        labels.append("failed")
    for carried in ("range_label", "label"):  # S7 and S2: a tool's own label travels with the result
        if cli.get(carried) in ("outside-validated-range", "projection") and cli[carried] not in labels:
            labels.append(cli[carried])
    ext: dict = {"paradigm": a.paradigm,
                 "likelihood": {"form": cli.get("method", "see results"), "backend": a.backend or cli.get("label", "core/stats")},
                 "parameters_of_interest": a.poi, "nuisances": cli.get("nuisances", []),
                 "fit_status": FIT_STATUS[status]}
    if a.paradigm == "bayesian":
        if not a.backend and "label" not in cli:
            ext["likelihood"]["backend"] = "user's sampler"
        ext["likelihood"]["form"] = "see the user's model"
        _bayesian(cli, a, ext)
    else:
        for key, val in (("test_statistic", a.test_statistic), ("construction", a.construction)):
            if val is not None:
                ext[key] = val
        ext["coverage"] = {"check": a.coverage_check, "method": a.coverage_method}
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
    if a.paradigm != "bayesian":
        ext["results"] = {k: v for k, v in cli.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    ext["results"]["cli_status"] = status
    if "status" not in cli:
        ext["results"]["cli_status_assumed"] = status
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
    p.add_argument("--paradigm", default="frequentist", choices=PARADIGMS)
    p.add_argument("--construction", help="frequentist (required) or likelihood-only")
    p.add_argument("--test-statistic", help="frequentist (required) or likelihood-only")
    p.add_argument("--prior", action="append", metavar="PARAM=FORM", help="bayesian: one per parameter of interest")
    p.add_argument("--sampler", metavar="SAMPLER.json", help="bayesian: JSON object with name, chains, draws, ...")
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
    p.add_argument("--assume-status", choices=tuple(FIT_STATUS),
                   help="status of a CLI output that reports none (recorded as results.cli_status_assumed)")
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
    return 0 if effective_status(cli, a) == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
