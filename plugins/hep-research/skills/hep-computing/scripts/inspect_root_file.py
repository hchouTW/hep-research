#!/usr/bin/env python3
"""Inspect keys, trees, branches and histograms in a ROOT file (PyROOT).

Usage: python3 inspect_root_file.py --input file.root [--tree Events] [--hist h] [--json]
Human-readable text by default; --json prints one JSON object with a "status" key ("ok", "error" or
"missing-dependency") instead. Exit codes: 0 inspected, 2 bad input (missing or unreadable file, tree or histogram
not found), 3 PyROOT not importable (scripts/find_python.py finds an interpreter that has it).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class InputError(Exception):
    pass


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="Input ROOT file")
    parser.add_argument("--tree", help="Optional TTree name to inspect")
    parser.add_argument("--hist", help="Optional TH1/TH2 name to inspect")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    return parser.parse_args(argv)


def inspect(args) -> dict:
    import ROOT
    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise InputError(f"could not open ROOT file: {args.input}")
        info: dict = {"file": str(args.input),
                      "keys": [{"name": k.GetName(), "class": k.GetClassName()} for k in root_file.GetListOfKeys()]}
        if args.tree:
            tree = root_file.Get(args.tree)
            if not tree or not tree.InheritsFrom("TTree"):
                raise InputError(f"tree not found: {args.tree}")
            # leaf-list branches of fundamental types have an empty class name; use the leaf type
            info["tree"] = {"name": args.tree, "entries": int(tree.GetEntries()),
                            "branches": [{"name": b.GetName(), "type": b.GetClassName() or ", ".join(
                                leaf.GetTypeName() for leaf in b.GetListOfLeaves())} for b in tree.GetListOfBranches()]}
        if args.hist:
            hist = root_file.Get(args.hist)
            if not hist or not hist.InheritsFrom("TH1"):
                raise InputError(f"histogram not found: {args.hist}")
            info["histogram"] = {"name": args.hist, "entries": float(hist.GetEntries()), "integral": float(hist.Integral()),
                                 "dimension": int(hist.GetDimension()), "x_bins": int(hist.GetNbinsX())}
            if hist.GetDimension() > 1:
                info["histogram"]["y_bins"] = int(hist.GetNbinsY())
        return info
    finally:
        if root_file:
            root_file.Close()


def text(info: dict) -> str:
    lines = [f"file: {info['file']}", "keys:"] + [f"  {k['name']} [{k['class']}]" for k in info["keys"]]
    if "tree" in info:
        t = info["tree"]
        lines += ["", f"tree: {t['name']}", f"entries: {t['entries']}", "branches:"]
        lines += [f"  {b['name']} [{b['type']}]" for b in t["branches"]]
    if "histogram" in info:
        h = info["histogram"]
        lines += ["", f"histogram: {h['name']}", f"entries: {h['entries']}", f"integral: {h['integral']}",
                  f"x bins: {h['x_bins']}"] + ([f"y bins: {h['y_bins']}"] if "y_bins" in h else [])
    return "\n".join(lines)


def fail(args, status: str, message: str, code: int) -> int:
    if args.json:
        print(json.dumps({"status": status, "error": message}))
    else:
        print(f"inspect_root_file.py: error: {message}", file=sys.stderr)
    return code


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.input.is_file():
        return fail(args, "error", f"input file does not exist: {args.input}", 2)
    try:
        import ROOT  # noqa: F401
    except (ImportError, OSError):
        return fail(args, "missing-dependency", "PyROOT is not importable in this Python; find one with "
                    "scripts/find_python.py, or read the file with uproot", 3)
    try:
        info = inspect(args)
    except (InputError, OSError) as exc:
        return fail(args, "error", str(exc), 2)
    print(json.dumps(dict(info, status="ok"), indent=1) if args.json else text(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
