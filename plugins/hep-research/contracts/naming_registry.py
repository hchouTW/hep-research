#!/usr/bin/env python3
"""Naming rule and surface registries (semantic naming spec §6.2, §6.3): check contracts/naming/rules.json and
contracts/naming/surfaces.json, and generate the kinds block of each owner section.

Rule checks beyond the schema (naming_rule_registry.json): the five states in their fixed order; a unique
(rule_id, version); known surfaces; a heuristic rule gives no violated code; no reason code in two states; a waivable
rule maps naming.waived to not_applicable, a rule with params.kinds maps naming.kind_not_covered, one with
params.sources maps naming.external_name, and every rule but semantic maps naming.no_inputs to unsupported (the codes
the engine itself gives); determinism matches the predicate (similarity heuristic, semantic review, the rest
deterministic); an active rule records the source digest of its predicate (contracts/analysis_checks/source_digest.py)
and the digest is current: changed code needs a new rule version. The key, the five states, the reason-code
convention, the digest and state_for are those of contracts/rule_registry.py; layer, suites, V cases and kind are not.

Surface checks beyond the schema (naming_surfaces.json): N1-N17 each once; owners are skills; references_to and
referenced_by mirror each other; an extractor path exists; an implemented surface's doc page holds its anchor
(<a id="naming-n<k>"></a>) and its current generated kinds block; formats compile; level floors are not below those of
the spec's surface catalogue.

Usage: python3 contracts/naming_registry.py check [--rules FILE] [--surfaces FILE]
       python3 contracts/naming_registry.py sections [--check | --write]
Exit 0 ok, 1 findings (or a stale block with sections --check), 2 unreadable registry or bad usage. Output: JSON with a
status key. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.rule_registry import STATES, state_for  # noqa: E402,F401  (state_for: the shared state mapping)
from contracts.schema import Report, validate  # noqa: E402
from contracts.skill_names import SKILLS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "contracts" / "naming" / "rules.json"
SURFACES = ROOT / "contracts" / "naming" / "surfaces.json"
DETERMINISM = {"similarity": "heuristic", "semantic": "review"}
LEVELS = ("C0", "C1", "C2", "C3", "C4")
# level floors of the spec's surface catalogue (§10): a registry may rename or add kinds, never lower these
SPEC_FLOORS = {"N1": {"local": "C0", "private": "C1", "module_public": "C2", "plugin_core_api": "C3"},
               "N2": {"output": "C2", "manifest_checksummed": "C3"}, "N3": {"object": "C2", "shape_histogram": "C3"},
               "N4": {"project_column": "C2"}, "N5": {"project_config_key": "C2", "plugin_cli_flag": "C3"},
               "N6": {"job": "C1", "log_pattern": "C3"}, "N7": {"internal_alias": "C1"}, "N8": {"selection": "C2"},
               "N9": {"variation": "C3"}, "N10": {"nuisance": "C3", "channel": "C3", "observed_data": "C4"},
               "N11": {"project_output": "C2"}, "N12": {"model_artifact": "C2"}, "N13": {"parameter": "C2"},
               "N14": {"label": "C2", "macro": "C2"}, "N15": {"bib_key": "C2"}, "N16": {"contract_term": "C3"},
               "N17": {"record_id": "C4"}}
BLOCK = "<!-- naming-kinds:{sid}: generated from contracts/naming/surfaces.json by contracts/naming_registry.py sections; do not edit -->"
BLOCK_END = "<!-- /naming-kinds:{sid} -->"


def predicate_digests() -> dict[str, str]:
    from contracts.analysis_checks.source_digest import source_digest
    from core.naming.predicates import PREDICATES
    return {name: source_digest(fn) for name, fn in PREDICATES.items()}


def check_rules(doc, surfaces_doc=None) -> Report:
    rep = validate(doc, "naming_rule_registry.json")
    if not rep.ok:
        return rep
    if tuple(doc["states"]) != STATES:
        rep.add("error", "$.states", "naming_registry.states", f"the states are {list(STATES)}, in this order")
    known = {s["surface_id"]: s for s in (surfaces_doc or {}).get("surfaces", [])}
    keys = [(r["rule_id"], r["version"]) for r in doc["rules"]]
    for k in sorted({k for k in keys if keys.count(k) > 1}):
        rep.add("error", "$.rules", "naming_registry.duplicate_rule", f"rule {k[0]} version {k[1]} is listed twice")
    digests = predicate_digests()
    for i, r in enumerate(doc["rules"]):
        where, oc, params = f"$.rules[{i}]", r["outcome_contract"], r.get("params", {})
        if known:
            for s in r["surfaces"]:
                if s not in known:
                    rep.add("error", f"{where}.surfaces", "naming_registry.unknown_surface", f"{s} is not in the surface registry")
            for k in params.get("kinds", []):
                if not any(k in known[s]["kinds"] for s in r["surfaces"] if s in known):
                    rep.add("error", f"{where}.params.kinds", "naming_registry.unknown_kind", f"no surface of the rule has kind {k}")
        if r["determinism"] == "heuristic" and oc["violated"]:
            rep.add("error", f"{where}.outcome_contract.violated", "naming_registry.heuristic_violates",
                    "a heuristic rule never gives violated (I1): only unverified")
        want = DETERMINISM.get(r["predicate"], "deterministic")
        if r["determinism"] != want:
            rep.add("error", f"{where}.determinism", "naming_registry.determinism",
                    f"predicate {r['predicate']} is {want}, the rule says {r['determinism']}")
        seen: dict[str, str] = {}
        for s in STATES:
            for code in oc[s]:
                if code in seen and seen[code] != s:
                    rep.add("error", f"{where}.outcome_contract.{s}", "naming_registry.code_ambiguous",
                            f"'{code}' gives both '{seen[code]}' and '{s}'")
                seen.setdefault(code, s)
        required = [("not_applicable", "naming.waived", r["waivable"]),
                    ("not_applicable", "naming.kind_not_covered", "kinds" in params),
                    ("not_applicable", "naming.external_name", "sources" in params),
                    ("unsupported", "naming.no_inputs", r["predicate"] != "semantic")]
        for state, code, needed in required:
            if needed and code not in oc[state]:
                rep.add("error", f"{where}.outcome_contract.{state}", "naming_registry.engine_code_missing",
                        f"the engine gives {code}; map it to {state}")
        if r["lifecycle"] == "active":
            have = r.get("source_sha256")
            if have is None:
                rep.add("error", f"{where}.source_sha256", "naming_registry.source_digest_missing",
                        f"record the digest of predicate {r['predicate']}: {digests[r['predicate']]}")
            elif have != digests[r["predicate"]]:
                rep.add("error", f"{where}.source_sha256", "naming_registry.rule_source_changed",
                        f"the code of predicate {r['predicate']} changed (now {digests[r['predicate']]}) without a new version of "
                        f"{r['rule_id']}: register the changed rule as a new version")
    return rep


def kinds_block(s: dict) -> str:
    lines = [BLOCK.format(sid=s["surface_id"]), "", "| Kind | Level floor | Format | Rename policy |", "|---|---|---|---|"]
    for k, v in s["kinds"].items():
        fmt = f"`{v['format']}`".replace("|", "\\|") if v.get("format") else "—"
        if v.get("fixed_names"):
            fmt += "; fixed: " + ", ".join(f"`{n}`" for n in v["fixed_names"])
        lines.append(f"| `{k}` | {v['level_floor']} | {fmt} | {v.get('rename_policy', s['rename_policy'])} |")
    return "\n".join(lines + ["", BLOCK_END.format(sid=s["surface_id"])])


def _block_span(text: str, sid: str):
    a, b = BLOCK.format(sid=sid), BLOCK_END.format(sid=sid)
    i = text.find(a)
    j = text.find(b, i + 1) if i >= 0 else -1
    return (i, j + len(b)) if i >= 0 and j >= 0 else None


def check_surfaces(doc, root: Path = ROOT) -> Report:
    rep = validate(doc, "naming_surfaces.json")
    if not rep.ok:
        return rep
    ids = [s["surface_id"] for s in doc["surfaces"]]
    if sorted(ids, key=lambda x: int(x[1:])) != [f"N{k}" for k in range(1, 18)]:
        rep.add("error", "$.surfaces", "naming_registry.surface_set", "the registry lists N1-N17, each once")
    reg = {s["surface_id"]: s for s in doc["surfaces"]}
    for i, s in enumerate(doc["surfaces"]):
        where, sid = f"$.surfaces[{i}]", s["surface_id"]
        if s["owner"] not in SKILLS:
            rep.add("error", f"{where}.owner", "naming_registry.owner", f"{s['owner']} is not a skill")
        for t in s["references_to"]:
            other = reg.get(t["surface"])
            if other is None or {"surface": sid, "kind": t["kind"]} not in other["referenced_by"]:
                rep.add("error", f"{where}.references_to", "naming_registry.mirror",
                        f"{sid} references {t['surface']} ({t['kind']}) but {t['surface']}.referenced_by does not list {sid}")
        for t in s["referenced_by"]:
            other = reg.get(t["surface"])
            if other is None or {"surface": sid, "kind": t["kind"]} not in other["references_to"]:
                rep.add("error", f"{where}.referenced_by", "naming_registry.mirror",
                        f"{sid} is referenced by {t['surface']} ({t['kind']}) but {t['surface']}.references_to does not list {sid}")
        for k, v in s["kinds"].items():
            if v.get("format"):
                try:
                    re.compile(v["format"])
                except re.error as exc:
                    rep.add("error", f"{where}.kinds.{k}.format", "naming_registry.bad_format", f"{exc}")
            floor = SPEC_FLOORS.get(sid, {}).get(k)
            if floor and LEVELS.index(v["level_floor"]) < LEVELS.index(floor):
                rep.add("error", f"{where}.kinds.{k}.level_floor", "naming_registry.floor_lowered",
                        f"{sid} {k} has floor {v['level_floor']}, below the catalogue's {floor}")
        if s["extractor"] is not None:
            if not (root / s["extractor"]).is_file():
                rep.add("error", f"{where}.extractor", "naming_registry.extractor_missing", f"{s['extractor']} does not exist")
            page, anchor = s["doc"].split("#", 1)
            path = root / page
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            if f'<a id="{anchor}"></a>' not in text:
                rep.add("error", f"{where}.doc", "naming_registry.anchor_missing",
                        f"{page} has no owner section anchor <a id=\"{anchor}\"></a>")
            span = _block_span(text, sid)
            if span is None or text[span[0]:span[1]] != kinds_block(s):
                rep.add("error", f"{where}.doc", "naming_registry.kinds_block_stale",
                        f"the kinds block of {sid} in {page} is missing or stale: run contracts/naming_registry.py sections --write")
    return rep


def write_sections(doc, root: Path = ROOT, write: bool = False) -> list[str]:
    """Rewrite (or, without write, list) the stale kinds blocks of implemented surfaces that have their block markers."""
    stale = []
    for s in doc["surfaces"]:
        if s["extractor"] is None:
            continue
        path = root / s["doc"].split("#", 1)[0]
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        span = _block_span(text, s["surface_id"])
        if span is None or text[span[0]:span[1]] == kinds_block(s):
            continue
        stale.append(f"{s['surface_id']}: {path.relative_to(root)}")
        if write:
            path.write_text(text[:span[0]] + kinds_block(s) + text[span[1]:], encoding="utf-8")
    return stale


def _load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check both registries")
    c.add_argument("--rules", type=Path, default=RULES)
    c.add_argument("--surfaces", type=Path, default=SURFACES)
    g = sub.add_parser("sections", help="the generated kinds blocks of the owner sections")
    mode = g.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="exit 1 when a block is stale (default)")
    mode.add_argument("--write", action="store_true", help="rewrite stale blocks")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        surfaces = _load(getattr(args, "surfaces", SURFACES))
        rules = _load(args.rules) if args.cmd == "check" else None
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    if args.cmd == "sections":
        stale = write_sections(surfaces, write=args.write)
        status = "written" if args.write else ("stale" if stale else "pass")
        print(json.dumps({"status": status, "stale": stale}, indent=1))
        return 1 if stale and not args.write else 0
    assert rules is not None  # the check command always reads the rule registry
    rep = Report()
    srep = check_surfaces(surfaces)
    rrep = check_rules(rules, surfaces if srep.ok else None)
    rep.findings = srep.findings + rrep.findings
    counts = {"surfaces": len(surfaces.get("surfaces", [])), "rules": len(rules.get("rules", [])),
              "implemented": [s["surface_id"] for s in surfaces.get("surfaces", []) if s.get("extractor")]} if rep.ok else {}
    print(json.dumps({"status": "pass" if rep.ok else "fail", "findings": [f.as_dict() for f in rep.findings],
                      "counts": counts}, indent=1))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
