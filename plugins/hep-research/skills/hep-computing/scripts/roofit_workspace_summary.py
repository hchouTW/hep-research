#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize RooFit workspace contents.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--workspace", required=True, help="RooWorkspace name inside the ROOT file")
    parser.add_argument("--verbose", action="store_true", help="Print RooFit object details")
    return parser.parse_args()


def print_collection(title: str, collection: object, verbose: bool) -> None:
    print(f"{title}:")
    if collection.getSize() == 0:
        print("  none")
        return
    for item in collection:
        print(f"  {item.GetName()} [{item.ClassName()}]")
        if verbose:
            item.Print()


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input ROOT file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to inspect RooFit workspaces with this script") from exc

    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {args.input}")
        workspace = root_file.Get(args.workspace)
        if not workspace:
            raise KeyError(f"Workspace not found: {args.workspace}")
        if not workspace.InheritsFrom("RooWorkspace"):
            raise TypeError(f"Object is not a RooWorkspace: {args.workspace}")

        print(f"file: {args.input}")
        print(f"workspace: {args.workspace}")
        print_collection("variables", workspace.allVars(), args.verbose)
        print_collection("pdfs", workspace.allPdfs(), args.verbose)
        print_collection("functions", workspace.allFunctions(), args.verbose)
        print_collection("categories", workspace.allCats(), args.verbose)

        print("datasets:")
        data_names = [name.GetName() for name in workspace.allData()]
        if not data_names:
            print("  none")
        for name in data_names:
            data = workspace.data(name)
            print(f"  {name} [{data.ClassName()}] entries={data.numEntries()}")
            if args.verbose:
                data.Print()

        print("snapshots:")
        snapshots = workspace.getSnapshots()
        if not snapshots or snapshots.getSize() == 0:
            print("  none")
        else:
            for item in snapshots:
                print(f"  {item.GetName()}")
    finally:
        if root_file:
            root_file.Close()


if __name__ == "__main__":
    main()
