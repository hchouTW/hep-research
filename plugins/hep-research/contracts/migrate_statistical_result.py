#!/usr/bin/env python3
"""Migrate a statistical-result written under an older contract to the current contracts version, with explicit diagnostics (audit T08, STH-T1.8).

Contracts 2.2.0 apply semantic rules to statistical-result artifacts (contracts.validate._stat_semantics) that older
artifacts were never checked against. Old artifacts stay valid under their own version; this converter is how one is
brought under the new rules. It never repairs a number: an artifact that breaks a 2.2.0 rule (a p-value above 1,
unordered expected bands, a confidence level outside (0, 1), ...) is refused with the rule's code. What it does
change, each with a diagnostic:

- contract_version and versions.contracts become the current contracts version (CONTRACTS_VERSION, 2.2.0 or later); required_capabilities gains stats:result-semantics, so a
  2.1 reader refuses the result instead of reading it under the weaker rules;
- an untyped coverage object (no check) gains "check": "not-checked", its other fields kept; the converter never
  infers toys or an exact construction from free text;
- a scan's global p-value without trials_method is kept and reported (stats.trials_method_missing stays unresolved);
  the converter never invents a trials method.

A 2.2-2.5 artifact is brought to 2.6.0 (the hardening rules of contracts.validate._stat_hardening and
_bayesian_hardening, STH-T1): only its version changes, and it is refused when it breaks a 2.6.0 error rule (a
coverage interval wider than its counts allow, a p-value of 0, z and p that disagree, a construction with a test
statistic it does not use, a malformed model_sha256, ...). Missing evidence stays unresolved and is reported; the
converter never invents a seed, a toy count or an expected band.

Usage: python3 contracts/migrate_statistical_result.py OLD.json [--out NEW.json]
Exit codes: 0 migrated (or already 2.6.0 or newer), 1 refused, 2 unreadable input or not a statistical-result.
Output: JSON report {status, diagnostics, refusals} on stdout; the migrated artifact goes to --out.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import STAT_HARDENING_FROM, STAT_SEMANTICS_FROM, _at_least, validate_artifact  # noqa: E402

CAPABILITY = "stats:result-semantics"


def migrate(doc: dict) -> tuple[dict | None, dict]:
    """Return (migrated artifact or None, report)."""
    diagnostics: list[dict] = []
    if not isinstance(doc, dict) or doc.get("artifact_type") != "statistical-result":
        return None, {"status": "refused", "diagnostics": [], "refusals": [
            {"code": "migrate.not_statistical_result", "message": "only statistical-result artifacts are migrated"}]}
    if _at_least(doc.get("contract_version"), STAT_HARDENING_FROM):
        return copy.deepcopy(doc), {"status": "unchanged", "diagnostics": [
            {"code": "migrate.already_current", "message": f"contract_version {doc.get('contract_version')} already applies the rules"}],
            "refusals": []}
    before = validate_artifact(doc)
    if not before.ok:
        return None, {"status": "refused", "diagnostics": [], "refusals": [
            {"code": "migrate.invalid_source", "message": f"{f.code}: {f.message}"} for f in before.errors]}
    new = copy.deepcopy(doc)
    old_version = new.get("contract_version")
    new["contract_version"] = CONTRACTS_VERSION
    if isinstance(new.get("versions"), dict):
        new["versions"]["contracts"] = CONTRACTS_VERSION
    caps = list(new.get("required_capabilities") or [])
    if CAPABILITY not in caps:
        caps.append(CAPABILITY)
    new["required_capabilities"] = caps
    diagnostics.append({"code": "migrate.version", "message": f"contract_version {old_version} -> {CONTRACTS_VERSION}, "
                                                              f"required capability {CAPABILITY} added"})
    ext = new.get("extension", {})
    cov = ext.get("coverage")
    if not _at_least(old_version, STAT_SEMANTICS_FROM) and isinstance(cov, dict) and cov and "check" not in cov:
        cov["check"] = "not-checked"
        diagnostics.append({"code": "migrate.coverage_untyped", "message": "untyped coverage marked check not-checked "
                                                                           "(fields kept): it is not coverage evidence"})
    after = validate_artifact(new)
    refusals = [{"code": f.code, "message": f.message} for f in after.errors]
    if refusals:
        return None, {"status": "refused", "diagnostics": diagnostics, "refusals": refusals}
    diagnostics += [{"code": f.code, "message": f"remains {f.severity}: {f.message}"} for f in after.findings
                    if f.severity == "unresolved"]
    return new, {"status": "migrated", "diagnostics": diagnostics, "refusals": []}


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 2
    try:
        doc = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "error": f"cannot read {args[0]}: {exc}"}))
        return 2
    new, report = migrate(doc)
    if report["refusals"] and report["refusals"][0]["code"] == "migrate.not_statistical_result":
        print(json.dumps(report, indent=1))
        return 2
    if new is not None and "--out" in args:
        i = args.index("--out") + 1
        if i >= len(args):
            print(json.dumps({"status": "refused", "error": "--out needs a path"}))
            return 2
        Path(args[i]).write_text(json.dumps(new, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0 if new is not None else 1


if __name__ == "__main__":
    sys.exit(main())
