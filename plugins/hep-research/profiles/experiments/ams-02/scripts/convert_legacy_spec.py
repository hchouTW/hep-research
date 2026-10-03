#!/usr/bin/env python3
"""Convert a legacy AMS analysis specification (spec_version "1", JSON or strict YAML) into a
`measurement-spec` contract artifact (task M2.5, AC13).

Purpose: let a specification written for the legacy ams-analysis skill enter the plugin's contracts
without losing anything and without inventing anything.

What it does:
  1. Reads the spec (JSON, or the strict YAML subset of scripts/yaml_subset.py).
  2. Runs the legacy audit (scripts/audit_analysis_spec.py). Audit errors stop the conversion:
     a spec the legacy rules block must be fixed first, not converted.
  3. Maps the generic fields onto the measurement-spec extension (observable, period, selections,
     backgrounds, corrections, systematics, ratio). Legacy bare claim IDs ("C31") become
     profile-qualified evidence IDs ("ams02:C31").
  4. Keeps the AMS-only fields under `experiment_fields` with `ams02:` keys, and the complete original
     spec under `experiment_fields["ams02:legacy_spec"]`, so the conversion is lossless.
  5. Records what the legacy format cannot say (blinding, bin semantics, exposure value) and the
     audit's unresolved inputs in `unresolved_inputs`; it never fills them in.
  6. Validates the result against the contracts with this profile's vocabulary.

Usage (from the plugin root):
  python3 profiles/experiments/ams-02/scripts/convert_legacy_spec.py SPEC.json|SPEC.yaml [--out FILE]
         [--created YYYY-MM-DD] [--claims evidence/claims.json | --no-claims]
Exit codes: 0 converted; 1 refused (audit errors, unmappable target, or contract errors; all listed
on stderr as JSON); 2 input unreadable or not a legacy spec.
Standard library only. Importable: convert(spec, claims=None, created=None) -> (artifact, problems).
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import sys
from pathlib import Path

_PLUGIN_ROOT = Path(__file__).resolve().parents[4]
if str(_PLUGIN_ROOT) not in sys.path:  # make core/ and contracts/ importable when run as a script
    sys.path.insert(0, str(_PLUGIN_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_analysis_spec as legacy_audit  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary, declared_namespaces  # noqa: E402

PROFILE_DIR = Path(__file__).resolve().parents[1]
PROFILE = json.loads((PROFILE_DIR / "profile.json").read_text(encoding="utf-8"))
NS = PROFILE["evidence_namespace"]
PLUGIN_VERSION = json.loads((_PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]

QUANTITY = {"flux": "differential-flux", "ratio": "ratio", "fraction": "fraction", "limit": "limit",
            "parameter": "parameter", "efficiency": "efficiency"}  # "discovery" has no measurement-spec quantity
LEVEL = {"detector": "detector", "object": "detector", "flux": "crflux:top-of-instrument"}
FLUX_UNIT = {"GV": "m^-2 sr^-1 s^-1 GV^-1", "GeV": "m^-2 sr^-1 s^-1 GeV^-1", "GeV/c": "m^-2 sr^-1 s^-1 (GeV/c)^-1",
             "GeV/n": "m^-2 sr^-1 s^-1 (GeV/n)^-1"}
# legacy top-level sections with no generic home: kept verbatim under ams02:<name>
AMS_ONLY = ("observables", "signal", "response", "estimator", "inference", "tail_estimates", "validation",
            "parameters", "ams_claims")


def _qualify(cid: str) -> str:
    return cid if ":" in cid else f"{NS}:{cid}"


def _claim_ids(spec: dict) -> list[str]:
    ids = []
    for section in ("parameters", "ams_claims"):
        for item in spec.get(section) or []:
            for cid in (item or {}).get("claim_ids") or []:
                q = _qualify(str(cid))
                if q not in ids:
                    ids.append(q)
    return ids


def _period(ds: dict):
    p = ds.get("period")
    if isinstance(p, dict) and p.get("start") and p.get("end"):
        return {"start": p["start"], "end": p["end"]}
    if isinstance(p, list) and p and all(isinstance(x, dict) and x.get("start") and x.get("end") for x in p):
        return [{"start": x["start"], "end": x["end"]} for x in p]
    return "not-provided"


def _slug(text: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out[:60] or "spec"


def profile_vocab() -> Vocabulary:
    v = Vocabulary()
    for name, terms in PROFILE["vocabulary_extensions"].items():
        v.extend(name, terms, declared_namespaces(PROFILE))
    return v


def convert(spec: dict, claims=None, created: str | None = None) -> tuple[dict | None, list[dict]]:
    """Return (artifact, problems). artifact is None when the conversion is refused."""
    if not isinstance(spec, dict) or spec.get("spec_version") != "1":
        return None, [{"code": "input.not_legacy_spec", "message": "not a legacy AMS spec (spec_version '1' required)"}]
    report = legacy_audit.audit_spec(spec, claims)
    errors = [f for f in report["findings"] if f["severity"] == "error"]
    if errors:
        return None, [{"code": f"legacy.{f['code']}", "path": f["path"], "message": f["message"]} for f in errors]
    m = spec["measurement"]
    if m["target"] not in QUANTITY:
        return None, [{"code": "convert.unmappable_target", "path": "measurement.target",
                       "message": f"target '{m['target']}' has no measurement-spec quantity type; keep the legacy spec "
                                  "and describe the search as a statistical-result artifact instead"}]
    ratio_like = m["target"] in ("ratio", "fraction", "efficiency", "parameter")
    variable, unit = m["variable"], m["unit"]
    unresolved = ["blinding: the legacy spec format has no blinding field; declare it before any unblinded result",
                  "bin semantics: not recorded by the legacy spec (point, bin-averaged or bin-integrated)"]
    if not ratio_like:
        unresolved.append("exposure: value or reference not provided")
    audit_open = [f["message"] for f in report["findings"] if f["severity"] == "unresolved"]
    unresolved += [f"[legacy audit] {msg}" for msg in audit_open]
    unresolved += [str(x) for x in spec.get("unresolved_inputs") or [] if str(x) not in audit_open]

    conventions = {"energy_variable": variable}
    if variable == "rigidity":
        conventions[f"{NS}:rigidity_definition"] = "R = pc/(Ze) in GV; p = |Z|R/c; rigidity is not momentum"
    observable = {
        "quantity": QUANTITY[m["target"]],
        "species": [{k: v for k, v in sp.items()} for sp in m.get("species") or []],
        "variables": [{"name": variable, "unit": unit, "edges": list(m["bin_edges"])}],
        "level": LEVEL[m["level"]],
        "normalization": ({"kind": "exposure", "value": "not-applicable",
                           "convention": f"target '{m['target']}': no absolute exposure normalization of the result"}
                          if ratio_like else {"kind": "exposure", "value": "not-provided"}),
        "bin_semantics": "unknown",
        "unit": "1" if m["target"] in ("ratio", "fraction", "efficiency") else
                (FLUX_UNIT.get(unit, f"m^-2 sr^-1 s^-1 ({unit})^-1") if m["target"] in ("flux", "limit") else "not-provided"),
        "conventions": conventions,
        "validity_range": {"variable": variable, "min": m["range"][0], "max": m["range"][1], "unit": unit},
    }
    ext = {
        "observable": observable,
        "species_or_process": ", ".join(str(sp.get("name")) for sp in m.get("species") or []),
        "period": _period(spec.get("data_scope") or {}),
        "selections": copy.deepcopy(spec.get("selections") or []),
        "backgrounds": copy.deepcopy(spec.get("backgrounds") or []),
        "corrections": copy.deepcopy(spec.get("corrections") or []),
        "systematics": copy.deepcopy(spec.get("systematics") or []),
        "blinding": "not-provided",
        "experiment_fields": {f"{NS}:measurement": {k: copy.deepcopy(v) for k, v in m.items()
                                                    if k in ("title", "estimand", "level", "sample", "target")},
                              f"{NS}:data_scope": copy.deepcopy(spec.get("data_scope") or {})},
    }
    for key in AMS_ONLY:
        if key in spec:
            ext["experiment_fields"][f"{NS}:{key}"] = copy.deepcopy(spec[key])
    ext["experiment_fields"][f"{NS}:legacy_spec"] = copy.deepcopy(spec)
    if "ratio" in spec:
        ext["ratio"] = copy.deepcopy(spec["ratio"])
        for c in ext["ratio"].get("cancellations") or []:
            if c.get("correlation_model") in (None, ""):  # legacy allows none for an independent effect
                c["correlation_model"] = "not-applicable" if c.get("treatment") == "independent" else "not-provided"
    artifact = {
        "contract_version": CONTRACTS_VERSION,
        "artifact_id": f"{NS}-legacy-spec-{_slug(str(m.get('title') or m['estimand']))}",
        "artifact_type": "measurement-spec",
        "objective": str(m["estimand"]),
        "bindings": {"experiments": [{"profile": PROFILE["id"], "version": PROFILE["version"]}], "theory": []},
        "versions": {"plugin": PLUGIN_VERSION, "contracts": CONTRACTS_VERSION, "profiles": {PROFILE["id"]: PROFILE["version"]}},
        "provenance": {"producer_skill": "hep-analysis", "created": created or dt.date.today().isoformat(),
                       "evidence_ids": _claim_ids(spec),
                       "converted_from": "legacy ams-analysis spec_version 1 (agentic-ai-skills@3e995a4 format)",
                       "legacy_audit_verdict": report["verdict"]},
        "inputs": [],
        "outputs": [],
        "status": ["unvalidated"],
        "unresolved_inputs": unresolved,
        "extension": ext,
    }
    rep = validate_artifact(artifact, profile_vocab())
    if not rep.ok:
        return None, [{"code": f"contract.{f.code}", "path": f.path, "message": f.message} for f in rep.errors]
    return artifact, []


def legacy_spec_of(artifact: dict) -> dict:
    """The original spec carried by a converted artifact (lossless round trip)."""
    return artifact["extension"]["experiment_fields"][f"{NS}:legacy_spec"]


def _load(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        return legacy_audit.yaml_subset.loads(text)
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="write the artifact here instead of stdout")
    ap.add_argument("--created", default=None, help="YYYY-MM-DD for provenance.created (default: today)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--claims", type=Path, default=PROFILE_DIR / "evidence" / "claims.json", help="ledger used to resolve claim_ids")
    g.add_argument("--no-claims", action="store_true", help="skip claim-ID resolution in the legacy audit")
    args = ap.parse_args(argv)
    try:
        spec = _load(args.spec)
        claims = None if args.no_claims else json.loads(args.claims.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}), file=sys.stderr)
        return 2
    artifact, problems = convert(spec, claims, args.created)
    if artifact is None:
        code = 2 if problems and problems[0]["code"] == "input.not_legacy_spec" else 1
        print(json.dumps({"status": "refused", "problems": problems}, indent=1, ensure_ascii=False), file=sys.stderr)
        return code
    text = json.dumps(artifact, indent=1, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
