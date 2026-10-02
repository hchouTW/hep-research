#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare one histogram in two ROOT files.")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--hist", required=True, help="Histogram path inside both ROOT files")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow bins")
    return parser.parse_args()


def open_hist(root_file: object, name: str) -> object:
    hist = root_file.Get(name)
    if not hist:
        raise KeyError(f"Histogram not found: {name}")
    if not hasattr(hist, "GetNbinsX"):
        raise TypeError(f"Object is not a 1D histogram-like object: {name}")
    hist.SetDirectory(0)
    return hist


def main() -> None:
    args = parse_args()
    for path in (args.reference, args.candidate):
        if not path.exists():
            raise FileNotFoundError(f"ROOT file does not exist: {path}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to compare ROOT histograms with this script") from exc

    ref_file = ROOT.TFile.Open(str(args.reference), "READ")
    cand_file = ROOT.TFile.Open(str(args.candidate), "READ")
    try:
        if not ref_file or ref_file.IsZombie():
            raise OSError(f"Could not open reference file: {args.reference}")
        if not cand_file or cand_file.IsZombie():
            raise OSError(f"Could not open candidate file: {args.candidate}")

        ref_hist = open_hist(ref_file, args.hist)
        cand_hist = open_hist(cand_file, args.hist)

        if ref_hist.GetNbinsX() != cand_hist.GetNbinsX():
            raise ValueError("Histogram bin counts differ")

        first_bin = 0 if args.include_flow else 1
        last_bin = ref_hist.GetNbinsX() + 1 if args.include_flow else ref_hist.GetNbinsX()

        max_abs = 0.0
        max_rel = 0.0
        max_bin = first_bin
        for index in range(first_bin, last_bin + 1):
            ref_value = float(ref_hist.GetBinContent(index))
            cand_value = float(cand_hist.GetBinContent(index))
            abs_diff = abs(cand_value - ref_value)
            rel_diff = abs_diff / abs(ref_value) if ref_value else (0.0 if cand_value == 0.0 else float("inf"))
            if abs_diff > max_abs:
                max_abs = abs_diff
                max_rel = rel_diff
                max_bin = index

        print(f"histogram: {args.hist}")
        print(f"reference entries: {ref_hist.GetEntries()}")
        print(f"candidate entries: {cand_hist.GetEntries()}")
        print(f"reference integral: {ref_hist.Integral()}")
        print(f"candidate integral: {cand_hist.Integral()}")
        print(f"max absolute bin difference: {max_abs}")
        print(f"max relative bin difference: {max_rel}")
        print(f"bin with max difference: {max_bin}")
    finally:
        if ref_file:
            ref_file.Close()
        if cand_file:
            cand_file.Close()


if __name__ == "__main__":
    main()
