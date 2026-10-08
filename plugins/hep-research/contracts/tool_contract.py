#!/usr/bin/env python3
"""Machine-readable tool contracts (AGENTIC-R5 T4.7, F14, F16): check a contract against its schema
(contracts/schemas/tool_contract.json), its own consistency, and the tool's command line, and check that every
operation of an enabled scope has a valid contract that covers the scope's purpose.

Usage: python3 contracts/tool_contract.py [CONTRACT ...] [--scope FILE] [--no-help-check]
  CONTRACT     contract files; none given means every file in contracts/tool_contracts/
  --scope      {"operations": ["<tool_id>:<operation_id>", ...], "purpose": "exploration"|"fixed-execution"|"validation"}:
               every listed operation needs a passing contract that declares the purpose (contract part of C15)
  --no-help-check  skip running '<entry> --help' (the comparison of declared options with the tool's usage line)

Checks: the entry is a regular file inside the plugin, not a link; every option maps to one declared input and every
input to one option; a default only on an optional input; exit codes unique within an operation; every required
capability known to this reader (contracts.KNOWN_CAPABILITIES); every caller-bound unit symbol ({X}) in an output unit
appears in an input unit; every listed operator is in a shipped operator-semantics table (contracts/semantics/tables/);
with the help check, the tool's usage line lists exactly the declared options, the required
ones outside brackets.
Output: JSON {"status": "pass"|"fail", "contracts": [...], "scope": {...} or null, "note"}. Exit 0 pass, 1 fail,
2 unreadable input. A passing contract states what the tool does; it authorizes nothing (HC-05), and checking it does
not test the tool's numbers.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import KNOWN_CAPABILITIES  # noqa: E402
from contracts.schema import Report, validate  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = PLUGIN_ROOT / "contracts" / "tool_contracts"
HELP_TIMEOUT_S = 60
NOTE = "a contract states inputs, outputs, units, failure states and purposes; it authorizes nothing (HC-05)"
UNIT_SYMBOL = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
USAGE_FLAG = re.compile(r"--[a-z0-9][a-z0-9-]*")


def usage_flags(help_text: str) -> dict[str, bool] | None:
    """{flag: required} from argparse's usage block (up to the first blank line); required options stand outside
    brackets. None when the text has no usage block."""
    lines = help_text.splitlines()
    if not lines or not lines[0].startswith("usage:"):
        return None
    block = []
    for line in lines:
        if not line.strip():
            break
        block.append(line)
    text = " ".join(block)
    flags: dict[str, bool] = {}
    depth = 0
    for i, ch in enumerate(text):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        elif ch == "-" and text.startswith("--", i) and (i == 0 or text[i - 1] in " [|"):
            m = USAGE_FLAG.match(text, i)
            if m and m.group(0) != "--help":
                flags[m.group(0)] = depth == 0
    return flags


def run_help(entry: Path) -> tuple[str | None, str]:
    try:
        p = subprocess.run([sys.executable, "-I", "-B", str(entry), "--help"], capture_output=True, text=True,
                           timeout=HELP_TIMEOUT_S, cwd=str(entry.parent))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"--help did not run: {exc}"
    if p.returncode != 0:
        return None, f"--help exited {p.returncode}"
    return p.stdout, ""


def known_operators() -> set[str]:
    """Operator ids of the shipped operator-semantics tables (contracts/semantics/tables/)."""
    from contracts.recipe_semantics import TABLE_DIR
    ids: set[str] = set()
    for p in sorted(TABLE_DIR.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        ids |= {o["operator_id"] for o in doc.get("operators", []) if isinstance(o, dict) and isinstance(o.get("operator_id"), str)}
    return ids


def check_operation(op: dict, where: str, rep: Report, help_flags: dict[str, bool] | None,
                    operators: set[str]) -> None:
    inputs = {i["name"]: i for i in op["inputs"]}
    if len(inputs) != len(op["inputs"]):
        rep.add("error", f"{where}.inputs", "tool.duplicate_input", "an input name is declared twice")
    options = op["invocation"]["options"]
    flags = [o["flag"] for o in options]
    if len(set(flags)) != len(flags):
        rep.add("error", f"{where}.invocation.options", "tool.duplicate_option", "an option is declared twice")
    mapped = [o["input"] for o in options]
    for name in sorted(set(mapped) - set(inputs)):
        rep.add("error", f"{where}.invocation.options", "tool.option_unmapped", f"option for undeclared input '{name}'")
    for name in sorted(n for n in inputs if mapped.count(n) != 1):
        rep.add("error", f"{where}.inputs.{name}", "tool.input_unreachable", "an input needs exactly one option")
    for name, i in inputs.items():
        if i["required"] and "default" in i:
            rep.add("error", f"{where}.inputs.{name}", "tool.default_on_required", "a required input has no default")
    codes = [f["exit_code"] for f in op["failure_states"]]
    if len(set(codes)) != len(codes):
        rep.add("error", f"{where}.failure_states", "tool.ambiguous_exit", "one exit code must mean one failure state")
    if any(c > 255 for c in codes):
        rep.add("error", f"{where}.failure_states", "tool.bad_exit", "exit codes are 1..255")
    for k, cap in enumerate(op["required_capabilities"]):
        if cap not in KNOWN_CAPABILITIES:
            rep.add("error", f"{where}.required_capabilities[{k}]", "tool.unknown_capability",
                    f"'{cap}' is not implemented by this reader")
    for k, name in enumerate(op.get("operators", [])):
        if name not in operators:
            rep.add("error", f"{where}.operators[{k}]", "tool.unknown_operator", f"'{name}' is in no operator-semantics table")
    bound = {s for i in op["inputs"] for s in UNIT_SYMBOL.findall(i["unit"])}
    for o in op["outputs"]:
        for sym in sorted(set(UNIT_SYMBOL.findall(o["unit"])) - bound):
            rep.add("error", f"{where}.outputs.{o['name']}", "tool.unit_unbound", f"unit symbol {{{sym}}} comes from no input")
    if help_flags is not None:
        declared = {o["flag"]: inputs.get(o["input"], {}).get("required") for o in options}
        for flag in sorted(set(help_flags) - set(declared)):
            rep.add("error", f"{where}.invocation", "tool.option_undeclared", f"the tool accepts {flag}; the contract omits it")
        for flag in sorted(set(declared) - set(help_flags)):
            rep.add("error", f"{where}.invocation", "tool.option_missing", f"the contract declares {flag}; the tool has no such option")
        for flag in sorted(set(declared) & set(help_flags)):
            if declared[flag] is not None and declared[flag] != help_flags[flag]:
                rep.add("error", f"{where}.invocation", "tool.required_mismatch",
                        f"{flag}: the contract says required={declared[flag]}, the tool says required={help_flags[flag]}")


def check(contract, root: Path = PLUGIN_ROOT, help_check: bool = True, operators: set[str] | None = None) -> dict:
    """operators: known operator ids; None reads the shipped operator-semantics tables."""
    rep = validate(contract, "tool_contract.json")
    if rep.ok:
        operators = known_operators() if operators is None else operators
        entry = root / contract["entry"]
        parts = Path(contract["entry"]).parts
        try:
            st = os.lstat(entry)
            linked = Path(root).is_symlink() or any(os.path.islink(root.joinpath(*parts[:i])) for i in range(1, len(parts)))
        except OSError:
            st, linked = None, True
        if st is None or linked or not stat.S_ISREG(st.st_mode):
            rep.add("error", "entry", "tool.entry_missing", "the entry is not a regular file in the plugin (links refused)")
            help_check = False
        ops = [o["operation_id"] for o in contract["operations"]]
        if len(set(ops)) != len(ops):
            rep.add("error", "operations", "tool.duplicate_operation", "an operation id is declared twice")
        help_flags = None
        if help_check:
            if len(contract["operations"]) != 1:
                rep.add("error", "operations", "tool.help_unchecked", "a tool with several operations needs a per-operation help check")
            else:
                text, why = run_help(entry)
                help_flags = usage_flags(text) if text is not None else None
                if help_flags is None:
                    rep.add("error", "entry", "tool.help_unchecked", why or "no argparse usage line in --help")
        for k, op in enumerate(contract["operations"]):
            check_operation(op, f"operations[{k}]", rep, help_flags, operators)
    tool = contract.get("tool_id") if isinstance(contract, dict) else None
    return {"tool_id": tool, "status": "pass" if rep.ok else "fail", "findings": [f.as_dict() for f in rep.findings]}


def check_scope(scope, results: dict[str, tuple[dict, dict]]) -> dict:
    """results: tool_id -> (contract, check result). Every scoped operation needs a passing contract with the purpose."""
    rep = Report()
    if (not isinstance(scope, dict) or not isinstance(scope.get("operations"), list) or not scope["operations"]
            or not all(isinstance(s, str) for s in scope["operations"])
            or scope.get("purpose") not in ("exploration", "fixed-execution", "validation")):
        rep.add("error", "scope", "scope.malformed", "{'operations': ['tool:operation', ...] (non-empty), 'purpose': one of "
                "exploration, fixed-execution, validation}")
        return {"status": "fail", "findings": [f.as_dict() for f in rep.findings]}
    for ref in scope["operations"]:
        tool, _, op_id = ref.partition(":")
        if tool not in results:
            rep.add("error", f"scope.{ref}", "scope.uncontracted", "no tool contract for this tool")
            continue
        contract, res = results[tool]
        op = next((o for o in contract.get("operations", []) if isinstance(o, dict) and o.get("operation_id") == op_id), None)
        if op is None:
            rep.add("error", f"scope.{ref}", "scope.uncontracted", "the contract has no such operation")
        elif res["status"] != "pass":
            rep.add("error", f"scope.{ref}", "scope.contract_failed", "the tool's contract does not pass")
        elif scope["purpose"] not in op.get("purposes", []):
            rep.add("error", f"scope.{ref}", "scope.purpose_undeclared", f"not declared for {scope['purpose']!r}")
    return {"status": "pass" if rep.ok else "fail", "findings": [f.as_dict() for f in rep.findings]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("contracts", nargs="*", type=Path)
    ap.add_argument("--scope", type=Path)
    ap.add_argument("--no-help-check", action="store_true")
    args = ap.parse_args(argv)
    paths = args.contracts or sorted(CONTRACT_DIR.glob("*.json"))
    try:
        docs = [(p, json.loads(p.read_text(encoding="utf-8"))) for p in paths]
        scope = None if args.scope is None else json.loads(args.scope.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    rows, results = [], {}
    for path, doc in docs:
        res = dict(check(doc, help_check=not args.no_help_check), file=str(path))
        rows.append(res)
        if isinstance(res["tool_id"], str):
            if res["tool_id"] in results:
                res["status"] = "fail"
                res["findings"].append({"severity": "error", "path": "tool_id", "code": "tool.duplicate_tool",
                                        "message": "two contracts name the same tool"})
            results[res["tool_id"]] = (doc, res)
    scoped = None if args.scope is None else check_scope(scope, results)
    ok = all(r["status"] == "pass" for r in rows) and (scoped is None or scoped["status"] == "pass")
    print(json.dumps({"status": "pass" if ok else "fail", "contracts": rows, "scope": scoped, "note": NOTE}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
