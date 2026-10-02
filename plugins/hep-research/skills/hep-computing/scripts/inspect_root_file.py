#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect keys, trees, branches, and histograms in a ROOT file.")
    parser.add_argument("--input", required=True, type=Path, help="Input ROOT file")
    parser.add_argument("--tree", help="Optional TTree name to inspect")
    parser.add_argument("--hist", help="Optional TH1/TH2 name to inspect")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to inspect ROOT files with this script") from exc

    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {args.input}")

        print(f"file: {args.input}")
        print("keys:")
        for key in root_file.GetListOfKeys():
            print(f"  {key.GetName()} [{key.GetClassName()}]")

        if args.tree:
            tree = root_file.Get(args.tree)
            if not tree:
                raise KeyError(f"Tree not found: {args.tree}")
            print(f"\ntree: {args.tree}")
            print(f"entries: {tree.GetEntries()}")
            print("branches:")
            for branch in tree.GetListOfBranches():
                # Leaf-list branches of fundamental types have an empty class name; use the leaf type.
                type_name = branch.GetClassName() or ", ".join(
                    leaf.GetTypeName() for leaf in branch.GetListOfLeaves()
                )
                print(f"  {branch.GetName()} [{type_name}]")

        if args.hist:
            hist = root_file.Get(args.hist)
            if not hist:
                raise KeyError(f"Histogram not found: {args.hist}")
            print(f"\nhistogram: {args.hist}")
            print(f"entries: {hist.GetEntries()}")
            print(f"integral: {hist.Integral()}")
            if hasattr(hist, "GetNbinsX"):
                print(f"x bins: {hist.GetNbinsX()}")
            if hasattr(hist, "GetNbinsY"):
                print(f"y bins: {hist.GetNbinsY()}")
    finally:
        if root_file:
            root_file.Close()


if __name__ == "__main__":
    main()
