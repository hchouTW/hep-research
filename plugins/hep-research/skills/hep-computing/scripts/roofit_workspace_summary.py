#!/usr/bin/env python3
"""Summarize RooFit workspace contents (PyROOT).

Usage: python3 roofit_workspace_summary.py --input file.root --workspace w [--verbose] [--json]
Human-readable text by default (--verbose adds RooFit's own Print of each object); --json prints one JSON object
with a "status" key ("ok", "error" or "missing-dependency") instead. Exit codes: 0 summarized, 2 bad input (missing
or unreadable file, workspace not found or not a RooWorkspace), 3 PyROOT not importable.
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import sys
from pathlib import Path


class InputError(Exception):
    pass


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--workspace", required=True, help="RooWorkspace name inside the ROOT file")
    parser.add_argument("--verbose", action="store_true", help="Print RooFit object details (text mode)")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    return parser.parse_args(argv)


def _items(collection) -> list:
    return [{"name": item.GetName(), "class": item.ClassName()} for item in collection] if collection.getSize() else []


def summarize(args) -> dict:
    import ROOT
    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise InputError(f"could not open ROOT file: {args.input}")
        ws = root_file.Get(args.workspace)
        if not ws:
            raise InputError(f"workspace not found: {args.workspace}")
        if not ws.InheritsFrom("RooWorkspace"):
            raise InputError(f"{args.workspace} is a {ws.ClassName()}, not a RooWorkspace")
        out = {"file": str(args.input), "workspace": args.workspace, "variables": _items(ws.allVars()),
               "pdfs": _items(ws.allPdfs()), "functions": _items(ws.allFunctions()), "categories": _items(ws.allCats())}
        out["datasets"] = []
        for name in [d.GetName() for d in ws.allData()]:
            data = ws.data(name)
            out["datasets"].append({"name": name, "class": data.ClassName(), "entries": int(data.numEntries())})
            if args.verbose and not args.json:
                data.Print()
        snaps = ws.getSnapshots()
        out["snapshots"] = [s.GetName() for s in snaps] if snaps and snaps.getSize() else []
        if args.verbose and not args.json:
            for coll in (ws.allVars(), ws.allPdfs(), ws.allFunctions(), ws.allCats()):
                for item in coll:
                    item.Print()
        return out
    finally:
        if root_file:
            root_file.Close()


def text(s: dict) -> str:
    lines = [f"file: {s['file']}", f"workspace: {s['workspace']}"]
    for title in ("variables", "pdfs", "functions", "categories"):
        lines.append(f"{title}:")
        lines += [f"  {i['name']} [{i['class']}]" for i in s[title]] or ["  none"]
    lines.append("datasets:")
    lines += [f"  {d['name']} [{d['class']}] entries={d['entries']}" for d in s["datasets"]] or ["  none"]
    lines.append("snapshots:")
    lines += [f"  {n}" for n in s["snapshots"]] or ["  none"]
    return "\n".join(lines)


def fail(args, status: str, message: str, code: int) -> int:
    if args.json:
        print(json.dumps({"status": status, "error": message}))
    else:
        print(f"roofit_workspace_summary.py: error: {message}", file=sys.stderr)
    return code


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.input.is_file():
        return fail(args, "error", f"input ROOT file does not exist: {args.input}", 2)
    try:
        import ROOT  # noqa: F401
    except (ImportError, OSError):
        return fail(args, "missing-dependency", "PyROOT is not importable in this Python; find one with "
                    "scripts/find_python.py", 3)
    try:
        summary = summarize(args)
    except (InputError, OSError) as exc:
        return fail(args, "error", str(exc), 2)
    print(json.dumps(dict(summary, status="ok"), indent=1) if args.json else text(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
