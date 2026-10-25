#!/usr/bin/env python3
"""Semantic naming check (spec §6.5, §7.9, §8, §11.2): judge naming inventories against the naming rule registry and
report each finding with its state, contract level and action.

  check --inventory INV.json [...] [--annotations A.json] [--glossary G.json] [--profile-vocab V.json]
        [--declaration D.json ...] [--project DIR] [--expect SURFACE ...] [--strict] [--all]
        [--format json|markdown|table] [--out REPORT.json]
  annotate-template --report REPORT.json --out A.json
  validate FILE                    an inventory, annotations, report or change set against its schema
  validate-change-set CS.json --inventory INV.json [...] [--project-root DIR]
  surfaces                         the 17 surfaces, owners and whether each extractor is implemented

The report has the audit_report shape (contracts/audit_report.py): status pass/fail/incomplete/input-error with exit
0/1/3/2; input error > any error (fail) > any unresolved (incomplete) > pass; warnings alone pass. Severity (§7.9): a
violated correctness rule (declared-match, reference, pairing, uniqueness, status-honesty) is an error; a violated
style rule (forbidden, pattern, vocabulary) or semantic rule is a warning in a user project, an error with --strict or
naming.strict; every unverified or unsupported result is unresolved, so a check without evidence never exits 0.
Severity never changes an action (I8). By default findings cover the names added, modified or removed and the names
whose relational judgement involves them; --all reports every name, and so does a check whose inventories carry no
change marks (made without --changed). Relational rules always see the whole inventory.

--project DIR reads the optional naming block of hep-research.project.json (strict, glossary, waivers) and refuses an
--out inside its artifacts_dir: naming working files (inventories, annotations, reports, change sets) are never
artifacts (I9). A declaration file is a JSON object {"declaration": "<name>", "sources": [{"id", "correlated",
"members": [entity_id, "<container>/<name>" or a bare name, ...]}]}, or a measurement-spec artifact, whose systematics
ledger (name, correlation_key, era_correlation, optional nuisance_names) is read as the correlation inventory
(core/naming/declarations.py; provisional, spec Q1). Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from contracts import audit_report as AR  # noqa: E402
from contracts.naming_registry import RULES, SURFACES  # noqa: E402
from contracts.rule_registry import state_for  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.naming import engine as E  # noqa: E402
from core.naming.declarations import correlation_inventory  # noqa: E402
from core.naming.model import STATES  # noqa: E402
from core.naming.vocab import Vocabulary, data_versions  # noqa: E402
from core.terminology.glossary import load_glossary  # noqa: E402

TOOL = "naming_check"
CORRECTNESS = ("declared-match", "reference", "pairing", "uniqueness", "status-honesty")
STYLE = ("forbidden", "pattern", "vocabulary")
TABLE_COLUMNS = ("Surface", "Level", "Rule", "Predicate", "State", "Current", "Proposed", "Issue", "Evidence",
                 "Confidence", "Action")
ACTION_TEXT = {"fix": "rename it and its in-scope references", "fix-with-change-set": "rename with a complete change set",
               "propose": "propose the rename: it is outside the current request",
               "propose-then-change-set-after-approval": "propose; after the user's approval, rename with a change set and hand back to the owner",
               "propose-alias": "do not rename; propose an alias or a mapping layer",
               "report-only": "report only: this surface renames only to remove a duplicate",
               "gather-evidence": "gather the missing evidence and judge again; do not claim completion",
               "report-missing": "report what is missing (extractor, inventory, declaration or input)", "none": "nothing"}
SCHEMA_OF = (("inventory_version", "naming_inventory.json"), ("annotations_version", "naming_annotations.json"),
             ("change_set_id", "naming_change_set.json"))


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canon(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _load(path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{path} is not a JSON object")
    return doc


def _schema_errors(doc, schema) -> list[str]:
    rep = validate(doc, schema)
    return [f"{f.path}: {f.message}" for f in rep.errors]


def registries():
    return _load(RULES), _load(SURFACES)


def severity(result: dict, mode: str, strict: bool) -> str | None:
    state = result["state"]
    if state in ("unverified", "unsupported"):
        return "unresolved"
    if state != "violated":
        return None
    if result["predicate"] in CORRECTNESS or mode == "gate":
        return "error"
    return "error" if strict else "warning"


def _location(e: dict | None) -> str:
    return f"{e['scope']['file']}:{e['scope']['span'][0]}" if e else "-"


def build_findings(judged: dict, surfaces: dict, mode: str, strict: bool) -> list[dict]:
    registry = {s["surface_id"]: s for s in surfaces["surfaces"]}
    by_id = judged["context"].by_id
    out = []
    for res in judged["reported"]:
        sev = severity(res, mode, strict)
        if sev is None:
            continue
        e = by_id.get(res["entity_id"])
        action, handoff = E.action_for(res, e, registry, in_request=bool(e and e["change"] != "unchanged"))
        extra = res["extra"]
        conf = extra.get("confidence")
        if conf is None and res["determinism"] == "deterministic":
            conf = "high" if res["state"] == "violated" else ("medium" if res["state"] == "unverified" else None)
        evidence = list(extra.get("evidence", [])) + [f"referenced at {loc}" for loc in extra.get("locations", [])[:5]]
        out.append(AR.finding(res["reason_code"], sev, _location(e), res["issue"] or res["reason_code"], ACTION_TEXT[action],
                              entity_id=res["entity_id"] or None, surface=res["surface"], rule_id=res["rule_id"],
                              rule_version=res["rule_version"], predicate=res["predicate"], state=res["state"],
                              reason_code=res["reason_code"], current=e["name"] if e else None,
                              proposed=extra.get("proposed"), issue=res["issue"], evidence=evidence, confidence=conf,
                              contract_level=e["contract_level"] if e else None, action=action, handoff=handoff))
        for k in ("entity_id", "current", "proposed", "confidence", "contract_level", "handoff"):
            out[-1].setdefault(k, None)
    return out


def table_rows(findings: list[dict]) -> list[dict]:
    rows = []
    for f in findings:
        rows.append({"Surface": f["surface"], "Level": f["contract_level"] or "—", "Rule": f["rule_id"],
                     "Predicate": f["predicate"], "State": f["state"], "Current": f["current"] or "—",
                     "Proposed": f["proposed"] or "—", "Issue": f["issue"] or f["code"],
                     "Evidence": "; ".join(f["evidence"]) or "—", "Confidence": f["confidence"] or "—", "Action": f["action"]})
    return rows


def render_table(rows: list[dict]) -> str:
    if not rows:
        return "No findings: every judged name satisfies its rules."
    cell = lambda v: str(v).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    head = "| " + " | ".join(TABLE_COLUMNS) + " |"
    return "\n".join([head, "|" + "---|" * len(TABLE_COLUMNS)] + [
        "| " + " | ".join(cell(r[c]) for c in TABLE_COLUMNS) + " |" for r in rows])


def run_check(inventories: list[dict], *, rules: dict, surfaces: dict, glossary=None, profile_terms=(), declarations=None,
              annotations=None, waivers=(), expect=(), strict=False, report_all=False, mode="project",
              inputs=None, scope=None, extra_notes=()) -> dict:
    vocab = Vocabulary(glossary, profile_terms)
    judged = E.judge(inventories, rules["rules"], surfaces["surfaces"], vocab=vocab, state_for=state_for,
                     declarations=declarations, annotations=annotations, waivers=waivers, expect=expect,
                     report_all=report_all, deterministic_only=(mode == "gate"))
    findings = build_findings(judged, surfaces, mode, strict)
    counts = {s: sum(1 for r in judged["reported"] if r["state"] == s) for s in STATES}
    ran = sorted({f"{r['rule_id']}@{r['rule_version']}" for r in judged["results"] if r["entity_id"]})
    rep = AR.assemble(TOOL, scope or {}, findings, checks_run=ran, checks_not_run=judged["not_run"],
                      notes=list(extra_notes) + judged["notes"], inputs=inputs or {},
                      note="names are judged from declarations, annotations and the rules only; name similarity never "
                           "decides that two names should be one (I1); a pass is software consistency, not a review",
                      naming={"counts": counts, "inputs": inputs or {}, "mode": mode, "strict": bool(strict),
                              "engine_version": E.ENGINE_VERSION, "table": table_rows(findings)})
    rep["_judged"] = judged
    return rep


def _project(dir_: Path | None):
    if dir_ is None:
        return None, {}
    from contracts.project import load_project, naming_settings
    proj = load_project(dir_)
    if not proj.report.ok:
        raise ValueError("invalid project config: " + "; ".join(f"{f.code}: {f.message}" for f in proj.report.errors))
    return proj, naming_settings(proj)


def cmd_check(args) -> int:
    def fail(msg: str) -> int:
        rep = AR.input_error_report(TOOL, msg, ["naming"])
        rep["naming"] = {"counts": {s: 0 for s in STATES}, "inputs": {}}
        print(json.dumps(rep, indent=1))
        print(f"error: {msg}", file=sys.stderr)
        return 2
    try:
        rules, surfaces = registries()
        proj, settings = _project(args.project)
        inventories, inputs = [], {"rules": _sha(RULES), "surfaces": _sha(SURFACES), "engine": E.ENGINE_VERSION,
                                   "vocabulary_data": data_versions()}
        for p in args.inventory or []:
            inv = _load(p)
            errs = _schema_errors(inv, "naming_inventory.json")
            if errs:
                return fail(f"{p}: not a naming inventory: {'; '.join(errs[:3])}")
            inventories.append(inv)
            inputs[f"inventory:{p}"] = _sha(p)
        known = {s["surface_id"] for s in surfaces["surfaces"]}
        for s in args.expect or []:
            if s not in known:
                return fail(f"--expect {s}: not a surface (N1-N17)")
        if not inventories and not args.expect:
            return fail("give at least one --inventory (or --expect a surface whose inventory is missing)")
        seen = [inv["surface"] for inv in inventories]
        if len(seen) != len(set(seen)):
            return fail("two inventories for one surface: give one complete inventory per surface")
        annotations = {}
        if args.annotations:
            doc = _load(args.annotations)
            errs = _schema_errors(doc, "naming_annotations.json")
            if errs:
                return fail(f"{args.annotations}: {'; '.join(errs[:3])}")
            annotations = {a["entity_id"]: a for a in doc["annotations"]}
            inputs["annotations"] = _sha(args.annotations)
        gpath = args.glossary or (proj.config_path.parent / settings["glossary"] if proj and settings.get("glossary") else None)
        glossary = None
        if gpath:
            glossary = load_glossary(gpath)
            inputs["glossary"] = _sha(gpath)
        profile_terms = []
        if args.profile_vocab:
            pv = _load(args.profile_vocab)
            profile_terms = list(pv.get("terms", []))
            inputs["profile_vocabulary"] = {"sha256": _sha(args.profile_vocab), "version": pv.get("vocabulary_version")}
        declarations = {}
        for p in args.declaration or []:
            d = _load(p)
            if d.get("artifact_type") == "measurement-spec":
                d = correlation_inventory(d)
            name = d.get("declaration")
            if not isinstance(name, str):
                return fail(f"{p}: a declaration names itself in 'declaration' (or is a measurement-spec artifact)")
            if name == "correlation-inventory":
                d = correlation_inventory(d)
            declarations[name] = d
            inputs[f"declaration:{name}"] = _sha(p)
        waivers = settings.get("waivers", [])
        if waivers:
            inputs["waivers"] = _canon(waivers)
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    strict = bool(args.strict or settings.get("strict"))
    if args.out is not None and proj is not None and proj.artifacts_dir and E.is_inside(args.out, proj.artifacts_dir):
        return fail(f"--out {args.out} is inside artifacts_dir: naming working files stay out of it (I9); use <project>/naming/")
    marked = any(inv.get("changed_since") for inv in inventories)
    notes = [] if marked or args.all else ["no inventory was made with --changed: every name is reported (as --all), "
                                           "since without change marks nothing would be in the reporting scope"]
    rep = run_check(inventories, rules=rules, surfaces=surfaces, glossary=glossary, profile_terms=profile_terms,
                    declarations=declarations, annotations=annotations, waivers=waivers, expect=args.expect or (),
                    strict=strict, report_all=args.all or not marked, inputs=inputs, extra_notes=notes,
                    scope={"surfaces": seen, "expect": list(args.expect or []), "all": bool(args.all)})
    rep.pop("_judged")
    if args.format == "table":
        print(render_table(rep["naming"]["table"]) if rep["naming"]["table"] or any(
            e["change"] != "unchanged" for inv in inventories for e in inv["entities"]) else "No names added, changed or deleted.")
        return rep["exit_code"]
    protected = [Path(p) for p in (args.inventory or []) + ([args.annotations] if args.annotations else [])]
    return AR.emit(rep, args.format, args.out, protected)


def cmd_annotate_template(args) -> int:
    try:
        rep = _load(args.report)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input-error", "error": str(exc)}))
        return 2
    if args.out.exists():
        print(json.dumps({"status": "input-error", "error": f"{args.out} exists: the template never overwrites a review"}))
        return 2
    want = [f for f in rep.get("findings", []) if f.get("entity_id") and f.get("state") == "unverified"
            and f.get("predicate") in ("semantic", "similarity")]
    entries: dict[str, dict] = {}
    for f in want:
        entries.setdefault(f["entity_id"], {"entity_id": f["entity_id"], "confidence": "low", "evidence": [],
                                            "referrers_read": [], "recorded_by": ""})
    doc = {"annotations_version": "1.0.0", "annotations": list(entries.values())}
    if not args.out.parent.is_dir():
        print(json.dumps({"status": "input-error", "error": f"{args.out.parent} does not exist"}))
        return 2
    args.out.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(args.out), "entries": len(entries),
                      "note": "fill semantic_verdict, proposed, evidence, referrers_read and recorded_by; confidence high "
                              "only after reading the implementation and every referrer"}, indent=1))
    return 0


def cmd_validate(args) -> int:
    try:
        doc = _load(args.file)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input-error", "error": str(exc)}))
        return 2
    schema = next((s for k, s in SCHEMA_OF if k in doc), None)
    if schema is None and doc.get("tool") == TOOL:
        schema = "naming_report.json"
    if schema is None:
        print(json.dumps({"status": "input-error", "error": f"{args.file} is no naming inventory, annotations, report or change set"}))
        return 2
    errs = _schema_errors(doc, schema)
    print(json.dumps({"status": "pass" if not errs else "fail", "schema": schema, "errors": errs}, indent=1))
    return 0 if not errs else 1


def cmd_validate_change_set(args) -> int:
    try:
        rules, surfaces = registries()
        cs = _load(args.change_set)
        errs = _schema_errors(cs, "naming_change_set.json")
        if errs:
            print(json.dumps({"status": "input-error", "error": "; ".join(errs[:3])}))
            return 2
        inventories, digests = [], []
        for p in args.inventory:
            inv = _load(p)
            if _schema_errors(inv, "naming_inventory.json"):
                print(json.dumps({"status": "input-error", "error": f"{p} is not a naming inventory"}))
                return 2
            inventories.append(inv)
            digests.append(_sha(p))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input-error", "error": str(exc)}))
        return 2
    entities = [e for inv in inventories for e in inv["entities"]]
    E.link_targets(entities)
    E.classify(entities, {inv["surface"]: inv["scope_roots"] for inv in inventories}, surfaces["surfaces"])
    out = E.validate_change_set(cs, entities, surfaces["surfaces"], args.project_root,
                                {inv["surface"] for inv in inventories}, digests)
    print(json.dumps(out, indent=1))
    return out["exit_code"]


def cmd_surfaces(args) -> int:
    _, surfaces = registries()
    rows = [{"surface": s["surface_id"], "name": s["name"], "owner": s["owner"], "implemented": s["extractor"] is not None,
             "extractor": s["extractor"], "rename_policy": s["rename_policy"], "kinds": sorted(s["kinds"])}
            for s in surfaces["surfaces"]]
    print(json.dumps({"status": "ok", "surfaces": rows,
                      "implemented": sum(r["implemented"] for r in rows), "total": len(rows)}, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="naming_check.py", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="judge inventories and write the report")
    c.add_argument("--inventory", action="append", type=Path, metavar="INV.json")
    c.add_argument("--annotations", type=Path)
    c.add_argument("--glossary", type=Path)
    c.add_argument("--profile-vocab", type=Path, help="JSON {vocabulary_version, terms: [...]} of the bound profile")
    c.add_argument("--declaration", action="append", type=Path, metavar="D.json")
    c.add_argument("--project", type=Path, help="project directory with hep-research.project.json")
    c.add_argument("--expect", action="append", metavar="SURFACE", help="a surface the work touches (unsupported without inventory)")
    c.add_argument("--strict", action="store_true", help="style and semantic violations are errors")
    c.add_argument("--all", action="store_true", help="report every name, not only changed ones and those they involve")
    c.add_argument("--format", choices=("json", "markdown", "table"), default="json")
    c.add_argument("--out", type=Path, help="write the report here (never into artifacts_dir)")
    t = sub.add_parser("annotate-template", help="an annotations template for the entities awaiting review")
    t.add_argument("--report", type=Path, required=True)
    t.add_argument("--out", type=Path, required=True)
    v = sub.add_parser("validate", help="validate a naming file against its schema")
    v.add_argument("file", type=Path)
    s = sub.add_parser("validate-change-set", help="the ordered change-set checks")
    s.add_argument("change_set", type=Path)
    s.add_argument("--inventory", action="append", type=Path, required=True)
    s.add_argument("--project-root", type=Path, default=Path("."))
    sub.add_parser("surfaces", help="list the surfaces")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    return {"check": cmd_check, "annotate-template": cmd_annotate_template, "validate": cmd_validate,
            "validate-change-set": cmd_validate_change_set, "surfaces": cmd_surfaces}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
