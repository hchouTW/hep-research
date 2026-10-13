#!/usr/bin/env python3
"""Summarize ROOT histogram statistics for HEP review (PyROOT).

Usage: python3 summarize_histogram_statistics.py --input file.root --hist h [--include-flow] [--json]
Human-readable text by default; --json prints one JSON object with a "status" key ("ok", "error" or
"missing-dependency") instead. Exit codes: 0 summarized, 2 bad input (missing or unreadable file, histogram not
found or not a histogram), 3 PyROOT not importable (scripts/find_python.py finds an interpreter that has it).
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
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--hist", required=True, help="Histogram path inside the ROOT file")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow in the reported integral")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    return parser.parse_args(argv)


def summarize(args) -> dict:
    import ROOT
    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise InputError(f"could not open ROOT file: {args.input}")
        hist = root_file.Get(args.hist)
        if not hist:
            raise InputError(f"histogram not found: {args.hist}")
        if not hist.InheritsFrom("TH1"):
            raise InputError(f"{args.hist} is a {hist.ClassName()}, not a histogram")
        first_bin = 0 if args.include_flow else 1
        last_bin = hist.GetNbinsX() + 1 if args.include_flow else hist.GetNbinsX()
        values = [(i, hist.GetBinContent(i)) for i in range(first_bin, last_bin + 1)]
        return {"file": str(args.input), "histogram": args.hist, "entries": float(hist.GetEntries()),
                "integral": float(hist.Integral(first_bin, last_bin)), "include_flow": args.include_flow,
                "mean": float(hist.GetMean()), "rms": float(hist.GetRMS()),
                "effective_entries": float(hist.GetEffectiveEntries()), "x_bins": int(hist.GetNbinsX()),
                "x_min": float(hist.GetXaxis().GetXmin()), "x_max": float(hist.GetXaxis().GetXmax()),
                "negative_bins": [i for i, v in values if v < 0.0], "empty_bins": [i for i, v in values if v == 0.0]}
    finally:
        if root_file:
            root_file.Close()


def text(s: dict) -> str:
    lines = [f"file: {s['file']}", f"histogram: {s['histogram']}", f"entries: {s['entries']}", f"integral: {s['integral']}",
             f"mean: {s['mean']}", f"rms: {s['rms']}", f"effective entries: {s['effective_entries']}",
             f"x bins: {s['x_bins']}", f"x min: {s['x_min']}", f"x max: {s['x_max']}",
             f"negative bins: {len(s['negative_bins'])}", f"empty bins: {len(s['empty_bins'])}"]
    if s["negative_bins"]:
        lines.append("negative bin indices: " + ", ".join(str(i) for i in s["negative_bins"]))
    return "\n".join(lines)


def fail(args, status: str, message: str, code: int) -> int:
    if args.json:
        print(json.dumps({"status": status, "error": message}))
    else:
        print(f"summarize_histogram_statistics.py: error: {message}", file=sys.stderr)
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
