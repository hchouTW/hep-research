#!/usr/bin/env python3
"""Offline literature lifecycle: import source/claim ledgers, search logs and status notices into a literature record.

Usage: python3 manage_literature.py import INPUT.json --project-root ROOT --out OUTPUT.json [--into EXISTING.json]
                                           [--today YYYY-MM-DD] [--artifact-id ID] [--format json|markdown]

The record is written as a `literature-record` artifact (contracts 2.13.0): the common envelope (producer_skill
hep-citations, status user-supplied: imported, not verified online) with the record in `extension`, so it can sit in
the project's artifacts_dir, pass `contracts/validate.py` and be handed to hep-authoring. --into accepts such an artifact
or a bare record (record_version 1.0.0) written before 2.13.0.

INPUT.json holds any of: "sources" and "claims" (arrays in the evidence-ledger format of core/evidence/ledger.py),
"search_log" (database, interface, query, filters, date, coverage_limits, export_count, discovery_route) and "notices"
(source_id, kind: correction|retraction|journal-version|supersession, affects: whole|part, scope, date, provenance,
new_source_id). The import never edits INPUT or EXISTING and never performs a lookup: it writes a new record to --out
with provenance (input path and digest, date), deduplicates only on identical stable identifiers (DOI, arXiv id, INSPIRE
record), keeps arXiv version history and flags citing claims when a version changes, applies notices as flags on
dependent claims (reassess inside the notice's scope, check outside) without deleting a citation, marks old
verification dates as recheck (never as error), flags planned claims (kind "planned") whose recheck_by date has passed, and preserves
citation keys. A summary report (report_version 1.0.0)
goes to stdout. Exit codes: 0 imported with no open item; 1 a confirmed problem (invalid ledger records, a citation-key
collision, a notice naming an unknown source); 2 invalid invocation or unreadable input; 3 open items (a version
change, a notice to assess, an incomplete search, a planned claim past or without its recheck_by date). Online verification is an explicit host-agent workflow; this tool
records it as not performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
for _p in (str(PLUGIN), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contracts import audit_report as R  # noqa: E402
from literature_lib.literature import import_literature  # noqa: E402
from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.communication_project import output_aliases_input  # noqa: E402

CHECKS = ("ledger", "identifiers", "versions", "notices", "searches", "planned-claims", "citation-keys")


def envelope(record: dict, args, root: Path) -> dict:
    """The literature-record artifact around the record: imported ledgers are user-supplied and not verified online,
    so the status says so (a communication record that cites it as an input keeps the label)."""
    plugin = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": args.artifact_id or f"literature-record-{args.out.stem}",
            "artifact_type": "literature-record",
            "objective": f"literature record imported offline from {', '.join(i.get('path') or '?' for i in record['imported'])}",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": plugin, "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-citations", "created": record["created"], "evidence_ids": []},
            "inputs": [], "outputs": [], "status": ["user-supplied"], "unresolved_inputs": [], "extension": record}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="manage_literature.py", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    sub = ap.add_subparsers(dest="command")
    imp = sub.add_parser("import", help="import ledgers, a search log and notices into a new literature record")
    imp.add_argument("input", type=Path)
    imp.add_argument("--project-root", type=Path, required=True)
    imp.add_argument("--out", type=Path, required=True, help="the new record (never an input path)")
    imp.add_argument("--into", type=Path, help="an existing record to merge into (read only; the result goes to --out)")
    imp.add_argument("--today", help="YYYY-MM-DD for reproducible runs (default: the system date)")
    imp.add_argument("--artifact-id", help="artifact_id of the record (default: literature-record-<stem of --out>)")
    imp.add_argument("--format", choices=("json", "markdown"), default="json")
    try:
        args = ap.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def fail(msg):
        print(json.dumps(R.input_error_report("manage_literature", msg, CHECKS), indent=1))
        print(f"error: {msg}", file=sys.stderr)
        return 2
    if args.command != "import":
        return fail("the only command is import")
    if not args.project_root.is_dir():
        return fail(f"--project-root {args.project_root} is not a directory")
    if args.today is not None:
        try:
            date.fromisoformat(args.today)
        except ValueError:
            return fail(f"--today {args.today!r} is not a YYYY-MM-DD date; freshness checks need a real date")
    protected = [args.input] + ([args.into] if args.into else [])
    if output_aliases_input(args.out, protected):
        return fail(f"--out {args.out} names an input of this run; the import never edits its inputs")
    try:
        raw = args.input.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        return fail(f"cannot read {args.input}: {exc}")
    if not isinstance(data, dict):
        return fail(f"{args.input} is not a JSON object")
    existing = None
    if args.into:
        try:
            existing = json.loads(args.into.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return fail(f"cannot read {args.into}: {exc}")
        if isinstance(existing, dict) and existing.get("artifact_type") == "literature-record":
            existing = existing.get("extension")
        if not isinstance(existing, dict) or existing.get("record_version") != "1.0.0":
            return fail(f"{args.into} is not a literature record (a literature-record artifact or record_version 1.0.0)")
    root = args.project_root.resolve()
    try:
        rel = str(args.input.resolve().relative_to(root))
    except ValueError:
        rel = str(args.input)
    record, rep = import_literature([{"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "data": data}], existing, today=args.today)
    rep["scope"].update(record=str(args.input), out=str(args.out), into=str(args.into) if args.into else None, project_root=str(root))
    if not args.out.parent.is_dir():
        return fail(f"--out directory {args.out.parent} does not exist")
    args.out.write_text(json.dumps(envelope(record, args, root), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manage_literature: record written to {args.out} ({rep['status']}, exit {rep['exit_code']})", file=sys.stderr)
    print(json.dumps(rep, indent=1) if args.format == "json" else R.to_markdown(rep))
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
