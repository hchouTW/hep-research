"""Shared report shape, Markdown rendering and CLI plumbing of the communication audits.

Every tool emits one report object: report_version 1.0.0, tool, scope, status (pass, fail, incomplete, input-error),
exit_code (0, 1, 3, 2), checks_run, checks_not_run (with reason and whether the check was required), findings (code,
severity, location, message, suggested_action, optional claim/source ids), notes (informational, never findings),
inputs (digests) and tool-specific sections. The outcome follows contracts.communication_project.resolve_outcome:
input-error > fail > incomplete > pass; warnings alone pass; Report.ok is never read as completeness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[4]
if str(PLUGIN) not in sys.path:
    sys.path.insert(0, str(PLUGIN))

from contracts.communication_project import output_aliases_input, resolve_context, resolve_outcome  # noqa: E402

REPORT_VERSION = "1.0.0"
STATUS_CODES = {"pass": 0, "fail": 1, "input-error": 2, "incomplete": 3}
SEVERITIES = ("error", "unresolved", "warning")


def finding(code: str, severity: str, location: str, message: str, suggested_action: str, **extra) -> dict:
    f = {"code": code, "severity": severity, "location": location, "message": message, "suggested_action": suggested_action}
    f.update({k: v for k, v in extra.items() if v is not None})
    return f


def normalize(findings, source: str, default_action: str = "see the message") -> list[dict]:
    """Findings of another checker (contracts Report dicts) in the audit shape, tagged with their source."""
    out = []
    for f in findings:
        out.append(finding(f.get("code", "unknown"), f.get("severity", "error"), f.get("path", f.get("location", "$")),
                           f.get("message", ""), f.get("suggested_action", default_action), source=source,
                           claim=f.get("claim"), source_id=f.get("source_id")))
    return out


def assemble(tool: str, scope: dict, findings: list[dict], *, checks_run, checks_not_run, notes=None, inputs=None,
             blocked: bool = False, input_error: bool = False, note: str = "", **sections) -> dict:
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings = sorted(findings, key=lambda f: order.get(f["severity"], 9))
    status, code = resolve_outcome(findings, input_error=input_error, blocked=blocked)
    rep = {"report_version": REPORT_VERSION, "tool": tool, "scope": scope, "status": status, "exit_code": code,
           "checks_run": list(checks_run), "checks_not_run": list(checks_not_run), "findings": findings,
           "notes": list(notes or []), "inputs": inputs or {},
           "counts": {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}}
    rep.update(sections)
    rep["note"] = note
    return rep


def input_error_report(tool: str, message: str, all_checks) -> dict:
    return assemble(tool, {}, [finding("input.error", "error", "-", message, "fix the invocation or the primary input")],
                    checks_run=[], checks_not_run=[{"check": c, "reason": "primary input or invocation invalid", "required": True} for c in all_checks],
                    input_error=True, note="nothing was checked")


def to_markdown(rep: dict) -> str:
    lines = [f"# {rep['tool']} report", "", f"- Status: **{rep['status']}** (exit {rep['exit_code']})",
             f"- Report version: {rep['report_version']}"]
    for key in ("traceability", "coverage"):
        if key in rep:
            lines.append(f"- {key.capitalize()}: `{json.dumps(rep[key], sort_keys=True)}`")
    if rep.get("scope"):
        lines += ["", "## Scope", "", "```json", json.dumps(rep["scope"], indent=1, sort_keys=True), "```"]
    lines += ["", "## Checks", "", f"- Run: {', '.join(rep['checks_run']) or 'none'}"]
    for c in rep["checks_not_run"]:
        lines.append(f"- Not run: {c['check']} ({c['reason']}; required: {'yes' if c.get('required') else 'no'})")
    lines += ["", "## Findings", ""]
    if not rep["findings"]:
        lines.append("None.")
    else:
        lines += ["| Severity | Code | Location | Message | Suggested action |", "|---|---|---|---|---|"]
        for f in rep["findings"]:
            cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {f['severity']} | `{f['code']}` | {cell(f['location'])} | {cell(f['message'])} | {cell(f['suggested_action'])} |")
    for key in ("claim_matrix", "draft_facts", "occurrences", "handoffs", "impacts", "reporting"):
        if rep.get(key):
            lines += ["", f"## {key.replace('_', ' ').capitalize()}", "", "```json", json.dumps(rep[key], indent=1, sort_keys=True, default=str), "```"]
    if rep.get("notes"):
        lines += ["", "## Notes", ""] + [f"- {n}" for n in rep["notes"]]
    lines += ["", f"_{rep.get('note', '')}_", ""]
    return "\n".join(lines)


def emit(rep: dict, fmt: str, out: Path | None, protected: list[Path]) -> int:
    """Print or write the report; a report path that aliases an input is refused (exit 2) before anything is written."""
    text = json.dumps(rep, indent=1, default=str) if fmt == "json" else to_markdown(rep)
    if out is not None:
        if output_aliases_input(out, protected):
            print(f"error: --out {out} names an input of this run (same file or a symlink alias); a report must not overwrite the "
                  "evidence it audits", file=sys.stderr)
            return 2
        if not out.parent.is_dir():
            print(f"error: --out directory {out.parent} does not exist", file=sys.stderr)
            return 2
        out.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")
        print(f"{rep['tool']}: {rep['status']} (exit {rep['exit_code']}); report written to {out}", file=sys.stderr)
    else:
        print(text)
    return rep["exit_code"]


def protected_paths(record_path: Path, ctx: dict | None) -> list[Path]:
    paths = [Path(record_path)]
    if ctx:
        root = Path(ctx.get("project_root", "."))
        for inp in ctx.get("inputs", {}).values():
            if inp.get("path"):
                paths.append(root / inp["path"])
        for d in ctx.get("documents", {}).values():
            if d.get("resolved_path"):
                paths.append(root / d["resolved_path"])
        for led in ctx.get("ledgers", {}).values():
            for key in ("sources_ref", "claims_ref"):
                if led.get(key) and not led.get("bound"):
                    paths.append(root / led[key])
    return paths


def base_parser(tool: str, doc: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog=tool, description=doc.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=doc.split("\n\n", 1)[1] if "\n\n" in doc else None)
    ap.add_argument("record", type=Path, nargs="?", help="communication record (JSON artifact)")
    ap.add_argument("--project-root", type=Path, required=False, help="project root: every project path resolves against it; nothing outside is opened")
    ap.add_argument("--format", choices=("json", "markdown"), default="json", help="json (default, stable) or markdown (a view of the same report)")
    ap.add_argument("--out", type=Path, help="write the report here instead of stdout (never an input path)")
    return ap


def run(tool: str, doc: str, argv, build, *, add_args=None, all_checks=(), needs_context=lambda args: True, extra_protected=None) -> int:
    """Common CLI driver: parse, read the record (exit 2 on failure), resolve the project context, call
    build(args, record, ctx) -> report, emit. Diagnostics go to stderr; JSON stdout stays parseable."""
    ap = base_parser(tool, doc)
    if add_args:
        add_args(ap)
    try:
        args = ap.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def fail(msg: str) -> int:
        print(json.dumps(input_error_report(tool, msg, all_checks), indent=1))
        print(f"error: {msg}", file=sys.stderr)
        return 2
    if args.record is None:
        return fail("a communication record is required")
    if args.project_root is None:
        return fail("--project-root is required")
    try:
        raw = args.record.read_bytes()
        record = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as exc:
        return fail(f"cannot read {args.record}: {exc}")
    if not isinstance(record, dict):
        return fail(f"{args.record} is not a JSON object")
    if not args.project_root.is_dir():
        return fail(f"--project-root {args.project_root} is not a directory")
    ctx = None
    if needs_context(args):
        ctx = resolve_context(args.record, args.project_root)
        if any(f["code"] in ("resolution.unreadable", "resolution.bad_root") for f in ctx["findings"]):
            return fail("; ".join(f["message"] for f in ctx["findings"] if f["code"] in ("resolution.unreadable", "resolution.bad_root")))
        if any(f["code"] == "resolution.outside_root" and f["path"] == "$" for f in ctx["findings"]):
            return fail(f"{args.record} lies outside --project-root {args.project_root}")
    try:
        rep = build(args, record, ctx)
    except ValueError as exc:
        return fail(str(exc))
    rep.setdefault("inputs", {})["record_sha256"] = hashlib.sha256(raw).hexdigest()
    rep["scope"].setdefault("record", str(args.record))
    protected = protected_paths(args.record, ctx) + (list(extra_protected(args, ctx)) if extra_protected else [])
    return emit(rep, args.format, args.out, protected)
