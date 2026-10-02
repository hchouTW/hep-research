#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check nominal/up/down ROOT histogram systematics.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--nominal", required=True, help="Nominal histogram path")
    parser.add_argument("--up", required=True, help="Up-variation histogram path")
    parser.add_argument("--down", required=True, help="Down-variation histogram path")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow bins")
    return parser.parse_args()


def get_hist(root_file: object, name: str) -> object:
    hist = root_file.Get(name)
    if not hist:
        raise KeyError(f"Histogram not found: {name}")
    if not hasattr(hist, "GetNbinsX"):
        raise TypeError(f"Object is not a 1D histogram-like object: {name}")
    return hist


def bin_range(hist: object, include_flow: bool) -> range:
    first_bin = 0 if include_flow else 1
    last_bin = hist.GetNbinsX() + 1 if include_flow else hist.GetNbinsX()
    return range(first_bin, last_bin + 1)


def check_compatible(nominal: object, varied: object, label: str) -> None:
    if nominal.GetNbinsX() != varied.GetNbinsX():
        raise ValueError(f"{label} bin count differs from nominal")
    for index in range(1, nominal.GetNbinsX() + 2):
        if nominal.GetXaxis().GetBinLowEdge(index) != varied.GetXaxis().GetBinLowEdge(index):
            raise ValueError(f"{label} bin edge differs from nominal at bin {index}")


def summarize_difference(nominal: object, varied: object, bins: range) -> tuple[float, float, int]:
    max_abs = 0.0
    max_rel = 0.0
    max_bin = 0
    for index in bins:
        nominal_value = float(nominal.GetBinContent(index))
        varied_value = float(varied.GetBinContent(index))
        abs_diff = abs(varied_value - nominal_value)
        rel_diff = abs_diff / abs(nominal_value) if nominal_value else (0.0 if varied_value == 0.0 else float("inf"))
        if abs_diff > max_abs:
            max_abs = abs_diff
            max_rel = rel_diff
            max_bin = index
    return max_abs, max_rel, max_bin


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"ROOT file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to check ROOT histogram systematics") from exc

    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {args.input}")
        nominal = get_hist(root_file, args.nominal)
        up = get_hist(root_file, args.up)
        down = get_hist(root_file, args.down)

        check_compatible(nominal, up, "up")
        check_compatible(nominal, down, "down")
        bins = bin_range(nominal, args.include_flow)

        print(f"file: {args.input}")
        print(f"nominal: {args.nominal}")
        print(f"up: {args.up}")
        print(f"down: {args.down}")
        print(f"nominal integral: {nominal.Integral()}")
        print(f"up integral: {up.Integral()}")
        print(f"down integral: {down.Integral()}")

        for label, hist in (("up", up), ("down", down)):
            max_abs, max_rel, max_bin = summarize_difference(nominal, hist, bins)
            print(f"{label} max absolute bin difference: {max_abs}")
            print(f"{label} max relative bin difference: {max_rel}")
            print(f"{label} bin with max difference: {max_bin}")
    finally:
        if root_file:
            root_file.Close()


if __name__ == "__main__":
    main()
