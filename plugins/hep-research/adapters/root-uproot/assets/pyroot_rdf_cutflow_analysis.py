from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

ROOT: Any = None


def import_root() -> Any:
    try:
        import ROOT as root
    except ImportError as exc:
        raise SystemExit(
            "PyROOT is required. Use a Python interpreter compatible with ROOT "
            "(check `root-config --python-version`)."
        ) from exc
    return root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a PyROOT RDataFrame analysis.")
    parser.add_argument("--input", required=True, action="append", type=Path)
    parser.add_argument("--tree", default="Events")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def validate_inputs(paths: list[Path], tree_name: str) -> None:
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Input file does not exist: {path}")
        root_file = ROOT.TFile.Open(str(path), "READ")
        try:
            if not root_file or root_file.IsZombie():
                raise OSError(f"Could not open ROOT file: {path}")
            tree = root_file.Get(tree_name)
            if not tree:
                raise KeyError(f"Tree '{tree_name}' not found in {path}")
            for branch in ("nMuon", "Muon_pt", "Muon_eta", "event_weight"):
                if not tree.GetBranch(branch):
                    raise KeyError(f"Branch '{branch}' not found in {path}")
        finally:
            if root_file:
                root_file.Close()


def main() -> None:
    global ROOT
    args = parse_args()
    ROOT = import_root()
    ROOT.gROOT.SetBatch(True)
    ROOT.EnableImplicitMT()

    validate_inputs(args.input, args.tree)

    df = ROOT.RDataFrame(args.tree, [str(path) for path in args.input])
    selected = (
        df.Filter("nMuon >= 2", "at least two muons")
        .Define("leading_muon_pt", "Muon_pt[0]")
        .Define("leading_muon_eta", "Muon_eta[0]")
        .Filter("leading_muon_pt > 25.0", "leading muon pt")
        .Filter("std::abs(leading_muon_eta) < 2.4", "leading muon eta")
    )

    h_pt = selected.Histo1D(
        ("h_leading_muon_pt", "Leading muon p_{T};p_{T} [GeV];Events", 50, 0.0, 200.0),
        "leading_muon_pt",
        "event_weight",
    )
    report = selected.Report()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_file = ROOT.TFile(str(args.output), "RECREATE")
    try:
        h_pt.Write()
    finally:
        out_file.Close()

    report.Print()
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
