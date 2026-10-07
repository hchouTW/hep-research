"""Starting template: dimuon-style selection with uproot + awkward, written to a ROOT TH1D.

Reads `inputs`, `branches.required`, and `output` from a config such as
`<plugin root>/adapters/root-uproot/assets/analysis-config.example.yaml`. The selection and histogram binning are hard-coded
below to mirror `rdf_cutflow_analysis.cpp` (nMuon >= 2, leading pT > 25,
|eta| < 2.4); the config's `selection` and `histograms` blocks are descriptive only.
The output histogram keeps sum(w^2), so errors are correct with negative weights.

Usage: python3 uproot_awkward_analysis.py --config analysis-config.example.yaml
Requires: uproot, awkward, numpy, PyYAML (no ROOT installation needed).
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import awkward as ak
import numpy as np
import uproot
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an uproot plus awkward analysis.")
    parser.add_argument("--config", required=True, type=Path)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def require_branches(tree: uproot.behaviors.TTree.TTree, branches: list[str]) -> None:
    available = set(tree.keys())
    missing = [branch for branch in branches if branch not in available]
    if missing:
        raise KeyError(f"Missing required branches: {', '.join(missing)}")


def weighted_th1(
    name: str,
    title: str,
    x: np.ndarray,
    weights: np.ndarray,
    bins: int,
    x_min: float,
    x_max: float,
) -> tuple[Any, np.ndarray]:
    """Build a TH1D that keeps sum(w^2) per bin; return it and the in-range bin contents.

    Writing ``(values, edges)`` to uproot drops the per-bin variances, so ROOT
    would report sqrt(sum w) errors - wrong with negative or non-unit weights.
    """
    x = np.asarray(x, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    inner = np.linspace(x_min, x_max, bins + 1)
    edges = np.concatenate(([-np.inf], inner, [np.inf]))  # underflow, bins, overflow
    sumw, _ = np.histogram(x, bins=edges, weights=weights)
    sumw2, _ = np.histogram(x, bins=edges, weights=weights**2)
    in_range = (x >= x_min) & (x < x_max)
    th1 = uproot.writing.identify.to_TH1x(
        fName=name,
        fTitle=title,
        data=sumw,
        fEntries=float(len(x)),
        fTsumw=float(weights[in_range].sum()),
        fTsumw2=float((weights[in_range] ** 2).sum()),
        fTsumwx=float((weights[in_range] * x[in_range]).sum()),
        fTsumwx2=float((weights[in_range] * x[in_range] ** 2).sum()),
        fSumw2=sumw2,
        fXaxis=uproot.writing.identify.to_TAxis("xaxis", "", bins, x_min, x_max),
    )
    return th1, sumw[1:-1]


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    tree_name = config["inputs"]["tree"]
    input_paths = [Path(path) for path in config["inputs"]["files"]]
    required_branches = config["branches"]["required"]

    for path in input_paths:
        if not path.exists():
            raise FileNotFoundError(f"Input file does not exist: {path}")

    arrays = []
    for path in input_paths:
        with uproot.open(path) as root_file:
            if tree_name not in root_file:
                raise KeyError(f"Tree '{tree_name}' not found in {path}")
            tree = root_file[tree_name]
            require_branches(tree, required_branches)
            arrays.append(tree.arrays(required_branches, library="ak"))

    events = ak.concatenate(arrays) if len(arrays) > 1 else arrays[0]
    has_two_muons = events["nMuon"] >= 2
    selected_events = events[has_two_muons]
    mask = (
        (selected_events["Muon_pt"][:, 0] > 25.0)
        & (abs(selected_events["Muon_eta"][:, 0]) < 2.4)
    )

    selected_pt = selected_events["Muon_pt"][:, 0][mask]
    selected_weight = selected_events["event_weight"][mask]

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / config["output"]["root_file"]
    th1, values = weighted_th1(
        "h_leading_muon_pt",
        "Leading muon p_{T};p_{T} [GeV];Events",
        ak.to_numpy(selected_pt),
        ak.to_numpy(selected_weight),
        bins=50,
        x_min=0.0,
        x_max=200.0,
    )
    with uproot.recreate(output_path) as output:
        output["h_leading_muon_pt"] = th1

    print(f"processed events: {len(events)}")
    print(f"selected events: {ak.sum(mask)}")
    print(f"hist integral: {float(values.sum())}")
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()
