#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize ROOT histogram statistics for HEP review.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--hist", required=True, help="Histogram path inside the ROOT file")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow in the reported integral")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input ROOT file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to summarize ROOT histograms with this script") from exc

    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {args.input}")
        hist = root_file.Get(args.hist)
        if not hist:
            raise KeyError(f"Histogram not found: {args.hist}")
        if not hasattr(hist, "GetNbinsX"):
            raise TypeError(f"Object is not a histogram-like object: {args.hist}")

        first_bin = 0 if args.include_flow else 1
        last_bin = hist.GetNbinsX() + 1 if args.include_flow else hist.GetNbinsX()
        integral = hist.Integral(first_bin, last_bin)
        negative_bins = []
        empty_bins = []
        for index in range(first_bin, last_bin + 1):
            value = hist.GetBinContent(index)
            if value < 0.0:
                negative_bins.append(index)
            if value == 0.0:
                empty_bins.append(index)

        print(f"file: {args.input}")
        print(f"histogram: {args.hist}")
        print(f"entries: {hist.GetEntries()}")
        print(f"integral: {integral}")
        print(f"mean: {hist.GetMean()}")
        print(f"rms: {hist.GetRMS()}")
        print(f"effective entries: {hist.GetEffectiveEntries()}")
        print(f"x bins: {hist.GetNbinsX()}")
        print(f"x min: {hist.GetXaxis().GetXmin()}")
        print(f"x max: {hist.GetXaxis().GetXmax()}")
        print(f"negative bins: {len(negative_bins)}")
        print(f"empty bins: {len(empty_bins)}")
        if negative_bins:
            print("negative bin indices:", ", ".join(str(index) for index in negative_bins))
    finally:
        if root_file:
            root_file.Close()


if __name__ == "__main__":
    main()
