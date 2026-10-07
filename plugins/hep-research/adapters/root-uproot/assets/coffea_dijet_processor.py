#!/usr/bin/env python3
"""Starting template: a coffea processor for a jet selection, weighted yields and the leading-pair mass.

Selection (as in rdf_cutflow_analysis.cpp and uproot_awkward_analysis.py, but on jets): jets with pt > --pt-min and
|eta| < --eta-max; events with at least two such jets. Per dataset it accumulates the number of selected events, the
signed sum of generator weights and of their squares, the weighted sum of the invariant mass of the two leading
selected jets (for its weighted mean), its maximum, and a weighted histogram of that mass. Generator weights are kept
with their sign; the normalization to a cross section (genEventSumw from the Runs tree) is left to the caller.

It reads the `Events` tree with coffea's BaseSchema (plain branches: `Jet_pt`, `Jet_eta`, `Jet_phi`, `Jet_mass`,
`genWeight`), so it also runs on the synthetic NanoAOD-like files from
<plugin root>/skills/hep-computing/scripts/make_synthetic_nanoaod.py; for real NanoAOD, switch to NanoAODSchema and
`events.Jet`. Chunks run one after the other (IterativeExecutor); swap in a FuturesExecutor or DaskExecutor to scale.

Usage: coffea_dijet_processor.py FILE.root [FILE.root ...] [--dataset NAME] [--chunksize 100000]
       [--pt-min 30] [--eta-max 2.5] [--out result.json]
Prints a JSON summary. Exit 0 done, 2 bad input or a missing package. Requires coffea (tested with 2026.9.0), awkward,
numpy and uproot.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

try:
    import awkward as ak
    import numpy as np
    from coffea import processor
    from coffea.nanoevents import BaseSchema
    MISSING = None
except ImportError as _exc:  # reported by main(), so --help works without coffea
    MISSING = _exc.name
    processor = None

MJJ_BINS = np.linspace(0.0, 1200.0, 25) if MISSING is None else None


class DijetProcessor(processor.ProcessorABC if processor else object):
    def __init__(self, pt_min: float = 30.0, eta_max: float = 2.5):
        self.pt_min, self.eta_max = pt_min, eta_max

    def process(self, events):
        good = (events.Jet_pt > self.pt_min) & (abs(events.Jet_eta) < self.eta_max)
        pt, eta, phi, mass = (events[f"Jet_{v}"][good] for v in ("pt", "eta", "phi", "mass"))
        keep = ak.num(pt) >= 2
        w = ak.to_numpy(events.genWeight[keep]).astype(float)
        j1 = [ak.to_numpy(x[keep][:, 0]).astype(float) for x in (pt, eta, phi, mass)]
        j2 = [ak.to_numpy(x[keep][:, 1]).astype(float) for x in (pt, eta, phi, mass)]

        def p4(pt_, eta_, phi_, m_):
            px, py, pz = pt_ * np.cos(phi_), pt_ * np.sin(phi_), pt_ * np.sinh(eta_)
            return np.sqrt(px * px + py * py + pz * pz + m_ * m_), px, py, pz

        e1, x1, y1, z1 = p4(*j1)
        e2, x2, y2, z2 = p4(*j2)
        mjj = np.sqrt(np.maximum((e1 + e2) ** 2 - (x1 + x2) ** 2 - (y1 + y2) ** 2 - (z1 + z2) ** 2, 0.0))
        hist, _ = np.histogram(mjj, bins=MJJ_BINS, weights=w)
        name = events.metadata["dataset"]
        return {name: {"n_selected": int(ak.sum(keep)), "sumw": float(w.sum()), "sumw2": float((w * w).sum()),
                       "sumw_mjj": float((w * mjj).sum()), "mjj_max": [float(mjj.max())] if len(mjj) else [],
                       "mjj_hist": hist}}

    def postprocess(self, accumulator):
        return accumulator


def run(files: list[str], dataset: str = "synthetic", chunksize: int = 100_000, pt_min: float = 30.0,
        eta_max: float = 2.5) -> dict:
    runner = processor.Runner(executor=processor.IterativeExecutor(status=False), schema=BaseSchema, chunksize=chunksize)
    with contextlib.redirect_stdout(sys.stderr):  # coffea's progress bars stay off the JSON on stdout
        out = runner({dataset: files}, processor_instance=DijetProcessor(pt_min, eta_max), treename="Events")
    summary = {}
    for name, acc in out.items():
        sumw = acc["sumw"]
        summary[name] = {"n_selected_events": acc["n_selected"], "sumw_selected": sumw, "sumw2_selected": acc["sumw2"],
                         "mjj_weighted_mean_GeV": acc["sumw_mjj"] / sumw if sumw else None,
                         "mjj_max_GeV": max(acc["mjj_max"]) if acc["mjj_max"] else None,
                         "mjj_bins_GeV": MJJ_BINS.tolist(), "mjj_hist_sumw": acc["mjj_hist"].tolist()}
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--dataset", default="synthetic")
    ap.add_argument("--chunksize", type=int, default=100_000)
    ap.add_argument("--pt-min", type=float, default=30.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    if MISSING:
        print(f"coffea_dijet_processor.py: error: {MISSING} is not installed: pip install coffea", file=sys.stderr)
        return 2
    missing = [f for f in args.files if not Path(f).is_file()]
    if missing:
        print(f"coffea_dijet_processor.py: error: no such file: {missing[0]}", file=sys.stderr)
        return 2
    summary = run(args.files, args.dataset, args.chunksize, args.pt_min, args.eta_max)
    text = json.dumps({"label": "starting template; numbers from synthetic inputs are not results", **summary}, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
