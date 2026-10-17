#!/usr/bin/env python3
"""Summarize ROOT histogram statistics for HEP review (PyROOT or uproot).

Usage: python3 summarize_histogram_statistics.py --input file.root --hist h [--include-flow] [--json]
       [--backend auto|pyroot|uproot] [--status LABEL]
Backends: PyROOT reads the histogram directly; uproot (C4) goes through the canonical reader of
check_histogram_errors.py and computes the same quantities from the stored statistics: mean = sum(w x) / sum(w),
RMS = sqrt(sum(w x^2) / sum(w) - mean^2), effective entries = sum(w)^2 / sum(w^2), the integral from the bin contents.
auto (default) tries PyROOT, then uproot. The uproot path covers 1D histograms (TH1); a TH2 or TH3 needs PyROOT.
Human-readable text by default; --json prints one JSON object with a "status" key ("ok", "error" or
"missing-dependency"), "backend" and "status_label" (--status, the input's artifact label, default unvalidated)
instead. Exit codes: 0 summarized, 2 bad input (missing or unreadable file, histogram not found or not a histogram),
3 neither backend importable (scripts/find_python.py finds an interpreter with PyROOT; pip install uproot awkward).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # the imports below leave no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling scripts
import check_histogram_errors as che  # noqa: E402
from core.status import add_status_argument  # noqa: E402


class InputError(Exception):
    pass


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--hist", required=True, help="Histogram path inside the ROOT file")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow in the reported integral")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    parser.add_argument("--backend", choices=("auto", "pyroot", "uproot"), default="auto",
                        help="reader: auto (PyROOT, then uproot), pyroot or uproot")
    add_status_argument(parser)
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


def summarize_uproot(args) -> dict:
    """The same summary from the canonical form of check_histogram_errors.py (1D histograms)."""
    try:
        h = che.read_uproot(args.input, [args.hist])[args.hist]
    except che.InputError as exc:
        raise InputError(str(exc)) from exc
    if h.get("kind") != "TH1" or "edges" not in h:
        raise InputError(f"{args.hist} is not a 1D histogram (the uproot path covers TH1; use PyROOT)")
    vals, edges = h["values"], h["edges"]
    first, last = (0, len(vals) - 1) if args.include_flow else (1, len(vals) - 2)
    sw, sw2 = h["tsumw"], h["tsumw2"]
    mean = h["tsumwx"] / sw if sw else 0.0
    rms = math.sqrt(abs(h["tsumwx2"] / sw - mean * mean)) if sw else 0.0
    return {"file": str(args.input), "histogram": args.hist, "entries": h["entries"],
            "integral": float(sum(vals[first:last + 1])), "include_flow": args.include_flow, "mean": mean, "rms": rms,
            "effective_entries": sw * sw / sw2 if sw2 else 0.0, "x_bins": len(edges) - 1, "x_min": edges[0],
            "x_max": edges[-1], "negative_bins": [i for i in range(first, last + 1) if vals[i] < 0.0],
            "empty_bins": [i for i in range(first, last + 1) if vals[i] == 0.0]}


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
    order = ("pyroot", "uproot") if args.backend == "auto" else (args.backend,)
    backend = None
    for name in order:
        try:
            if name == "pyroot":
                import ROOT  # noqa: F401
            else:
                import uproot  # noqa: F401
            backend = name
            break
        except (ImportError, OSError):
            continue
    if backend is None:
        return fail(args, "missing-dependency", "neither PyROOT nor uproot is importable in this Python (find a "
                    "PyROOT interpreter with scripts/find_python.py, or pip install uproot awkward)", 3)
    try:
        summary = summarize(args) if backend == "pyroot" else summarize_uproot(args)
    except (InputError, OSError) as exc:
        return fail(args, "error", str(exc), 2)
    summary["backend"] = backend
    print(json.dumps(dict(summary, status="ok", status_label=args.status), indent=1) if args.json else text(summary))
    return 0

if __name__ == "__main__":
    sys.exit(main())
