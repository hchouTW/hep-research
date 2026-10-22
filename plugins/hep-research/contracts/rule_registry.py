#!/usr/bin/env python3
"""Rule and obligation registry (v6.3 D12a): check contracts/rules/registry.json, map a rule outcome to one of the
five obligation states, and compute the checks a change must run (impact closure).

The registry (schema contracts/schemas/rule_registry.json) lists rules with their layer, suites, prerequisites,
applicability, reason codes per state (outcome_contract), legacy code mapping, native_from, V cases, waivability,
owner, review status and lifecycle; the V01-V71 acceptance cases per slice part with their status; and impact groups
that map changed paths to test modules or tools/run_all_checks.py parts.

Checks beyond the schema: the five states in their fixed order; unique rule and V IDs, V IDs without gaps; a new or
changed rule has at least one reason code for each of the five states and no code in two states (an existing rule may
keep outcome_contract "pending", which evaluates as unverified); every rule names its prerequisites; a rule's V cases
exist; a V part that is passing or an expected failure names the tests that run it, and each test exists in the
checkout; every test module of the impact map exists. Registry 1.1.0 (P3, G18): every new or changed rule records the
source digest of its implementation (contracts/analysis_checks/source_digest.py), the checker implements that
(rule_id, version), and the digest is the current one: code that changed without a new version fails.

state_for(rule, code): the state a reason code gives under the rule's outcome contract; a pending contract, an unknown
code or no code at all (an adapter that produced no explicit outcome) is unverified, never satisfied.

impact(paths): the test modules and run_all_checks parts a change to these paths must run. A path no group covers, a
group marked full, or a group with a check that does not exist yet (not_available) gives the full closure
(run_all_checks.py --part all). A changed test module always runs itself.

Usage: python3 contracts/rule_registry.py check [--registry FILE]
       python3 contracts/rule_registry.py impact PATH [PATH ...] [--registry FILE]
Paths are relative to the plugin root. Exit 0 ok (impact always 0), 1 registry findings, 2 unreadable registry or bad
usage. Output: JSON with a status key. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.schema import Report, validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts" / "rules" / "registry.json"
STATES = ("satisfied", "violated", "not_applicable", "unverified", "unsupported")
RUNNING = ("passing", "expected-failure")
LEGACY_LIFECYCLES = ("legacy", "deprecated", "retired")
FULL = {"full": True, "modules": [], "parts": ["all"], "command": "python3 tools/run_all_checks.py --out <dir>"}


def _test_exists(test_id: str, root: Path) -> bool:
    """tests.pkg.module[.Class[.method]] names a file in the checkout that defines the class and method."""
    parts = test_id.split(".")
    for i in range(len(parts), 1, -1):
        f = root.joinpath(*parts[:i]).with_suffix(".py")
        if f.is_file():
            rest, text = parts[i:], f.read_text(encoding="utf-8")
            if len(rest) > 2:
                return False
            if rest and not re.search(rf"^class {re.escape(rest[0])}\b", text, re.M):
                return False
            return len(rest) < 2 or bool(re.search(rf"^\s+def {re.escape(rest[1])}\(", text, re.M))
    return False


def check(doc, root: Path = ROOT) -> Report:
    rep = validate(doc, "rule_registry.json")
    if not rep.ok:
        return rep
    if tuple(doc["states"]) != STATES:
        rep.add("error", "$.states", "registry.states", f"the states are {list(STATES)}, in this order")
    vids = [c["v_id"] for c in doc["v_cases"]]
    if doc["registry_version"] != "1.0.0":
        _check_sources(doc, rep)
    for v in sorted({v for v in vids if vids.count(v) > 1}):
        rep.add("error", "$.v_cases", "registry.duplicate_v_case", f"{v} is listed twice")
    nums = sorted({int(v[1:]) for v in vids})
    if nums and nums != list(range(1, nums[-1] + 1)):
        rep.add("error", "$.v_cases", "registry.v_case_gap", "V cases run from V01 without gaps")
    rids = [r["rule_id"] for r in doc["rules"]]
    for r in sorted({r for r in rids if rids.count(r) > 1}):
        rep.add("error", "$.rules", "registry.duplicate_rule", f"rule {r} is listed twice")
    for i, rule in enumerate(doc["rules"]):
        where = f"$.rules[{i}]"
        oc = rule["outcome_contract"]
        if rule["kind"] == "legacy":
            if rule["lifecycle"] not in LEGACY_LIFECYCLES:
                rep.add("error", f"{where}.lifecycle", "registry.legacy_lifecycle",
                        f"a legacy rule is one of {list(LEGACY_LIFECYCLES)}; register a new version as kind new or changed")
        elif oc == "pending":
            rep.add("error", f"{where}.outcome_contract", "registry.outcome_contract_incomplete",
                    f"a {rule['kind']} rule needs reason codes for all five states; 'pending' is for existing rules")
        if isinstance(oc, dict):
            for s in STATES:
                if not oc[s]:
                    rep.add("error", f"{where}.outcome_contract.{s}", "registry.outcome_contract_incomplete",
                            f"no reason code gives '{s}'")
            seen: dict[str, str] = {}
            for s in STATES:
                for code in oc[s]:
                    if code in seen and seen[code] != s:
                        rep.add("error", f"{where}.outcome_contract.{s}", "registry.outcome_code_ambiguous",
                                f"'{code}' gives both '{seen[code]}' and '{s}'")
                    seen.setdefault(code, s)
        if rule["kind"] != "legacy" and not rule["suites"]:
            rep.add("error", f"{where}.suites", "registry.suite_missing", "a new or changed rule names the suites requiring it")
        if not rule["prerequisites"]:
            rep.add("error", f"{where}.prerequisites", "registry.prerequisites_missing",
                    "name the data the rule needs: without them a missing input cannot be told from a pass")
        for v in rule["v_cases"]:
            if v not in vids:
                rep.add("error", f"{where}.v_cases", "registry.unknown_v_case", f"{v} is not in v_cases")
    for k, case in enumerate(doc["v_cases"]):
        for j, part in enumerate(case["parts"]):
            where = f"$.v_cases[{k}].parts[{j}]"
            if part["status"] in RUNNING and not part["tests"]:
                rep.add("error", f"{where}.tests", "registry.v_case_without_test",
                        f"{case['v_id']} is {part['status']} but names no test that runs it")
            for t in part["tests"]:
                if not _test_exists(t, root):
                    rep.add("error", f"{where}.tests", "registry.test_missing", f"{t} is not a test in this checkout")
    ids = [g["id"] for g in doc["impact"]]
    for g in sorted({g for g in ids if ids.count(g) > 1}):
        rep.add("error", "$.impact", "registry.duplicate_group", f"impact group {g} is listed twice")
    for i, g in enumerate(doc["impact"]):
        for c in g["checks"]:
            if c.startswith("tests.") and not _test_exists(c, root):
                rep.add("error", f"$.impact[{i}].checks", "registry.test_missing", f"{c} is not a test module in this checkout")
    return rep


def _check_sources(doc: dict, rep: Report) -> None:
    from contracts.analysis_checks.source_digest import rule_digests
    current = rule_digests()
    for i, rule in enumerate(doc["rules"]):
        if rule["kind"] == "legacy":
            continue
        where, key = f"$.rules[{i}]", (rule["rule_id"], rule["version"])
        if key not in current:
            rep.add("error", where, "registry.rule_not_implemented",
                    f"the checker does not implement {rule['rule_id']} version {rule['version']}")
        elif "source_sha256" not in rule:
            rep.add("error", f"{where}.source_sha256", "registry.source_digest_missing",
                    f"record the source digest of {rule['rule_id']} {rule['version']}: {current[key]}")
        elif rule["source_sha256"] != current[key]:
            rep.add("error", f"{where}.source_sha256", "registry.rule_source_changed",
                    f"the code of {rule['rule_id']} {rule['version']} changed (now {current[key]}) without a new version: "
                    "register the changed code as a new rule version (P3); old versions are reproduced by their release")


def state_for(rule: dict, code: str | None) -> str:
    """The obligation state a rule's reason code gives; pending contracts and unknown or absent codes are unverified."""
    oc = rule.get("outcome_contract")
    if not isinstance(oc, dict) or code is None:
        return "unverified"
    for s in STATES:
        if code in oc.get(s, []):
            return s
    return "unverified"


def _module_of(path: str) -> str | None:
    p = PurePosixPath(path)
    if p.parts and p.parts[0] == "tests" and p.suffix == ".py" and p.name.startswith("test_"):
        return ".".join(p.with_suffix("").parts)
    return None


def impact(paths, doc) -> dict:
    """{"full", "modules", "parts", "not_available", "unmatched", "groups", "command"?} for these changed paths."""
    modules: set[str] = set()
    parts: set[str] = set()
    not_available: list[str] = []
    unmatched: list[str] = []
    groups: list[str] = []
    full = False
    for raw in paths:
        path = PurePosixPath(str(raw).replace("\\", "/").removeprefix("./"))
        hit = [g for g in doc["impact"] if any(path.full_match(pat) for pat in g["patterns"])]
        own = _module_of(str(path))
        if own:
            modules.add(own)
        if not hit and not own:
            unmatched.append(str(path))
        for g in hit:
            groups.append(g["id"])
            full |= g["full"]
            not_available += [f"{g['id']}: {x}" for x in g["not_available"]]
            for c in g["checks"]:
                if c.startswith("part:"):
                    parts.add(c.removeprefix("part:"))
                else:
                    modules.add(c)
    reasons = ([f"no impact group covers {p}" for p in unmatched] + [f"not available: {x}" for x in not_available]
               + [f"group {g} always runs the full closure" for g in dict.fromkeys(groups)
                  if next(x for x in doc["impact"] if x["id"] == g)["full"]])
    out = {"full": False, "modules": sorted(modules), "parts": sorted(parts), "not_available": not_available,
           "unmatched": unmatched, "groups": list(dict.fromkeys(groups)), "reasons": reasons}
    if full or unmatched or not_available or not paths:
        out.update(FULL, modules=sorted(modules))
        if not paths:
            out["reasons"] = ["no changed path given: the change cannot be bounded"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check the registry")
    c.add_argument("--registry", type=Path, default=REGISTRY)
    m = sub.add_parser("impact", help="checks a change to these paths must run")
    m.add_argument("paths", nargs="+")
    m.add_argument("--registry", type=Path, default=REGISTRY)
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.registry.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    rep = check(doc)
    if args.cmd == "check":
        counts = {}
        if rep.ok:
            parts = [p for c in doc["v_cases"] for p in c["parts"]]
            counts = {"rules": len(doc["rules"]), "v_cases": len(doc["v_cases"]), "impact_groups": len(doc["impact"]),
                      "v_parts_by_status": {s: sum(p["status"] == s for p in parts)
                                            for s in ("not-run", "expected-failure", "required-before-enforcement", "passing")}}
        print(json.dumps({"status": "pass" if rep.ok else "fail", "findings": [f.as_dict() for f in rep.findings],
                          "counts": counts}, indent=1))
        return 0 if rep.ok else 1
    if not rep.ok:
        print(json.dumps({"status": "unreadable", "error": "the registry has findings: run 'check'", **FULL}, indent=1))
        return 2
    print(json.dumps({"status": "ok", **impact(args.paths, doc)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
