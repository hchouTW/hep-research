#!/usr/bin/env python3
"""Write synthetic demo inputs for the event-display templates (no real data; every output is synthetic).

Usage: python3 make_demo_data.py --out DIR [--events 5] [--seed 1]
Writes DIR/demo.root (TTree "events" with hits and sampled track points; TH1D "h_pt" with variable bins and Sumw2),
DIR/detector.obj (a schematic half cylinder in mm),
DIR/results/hit_r/<run>_<subrun>_<event>.json (an event-level result computed here, standing in for the project's
analysis) and DIR/results/hits_per_run.json (a dataset-level table). Needs numpy and uproot.
Prints JSON {"status": ...}; exit 0 ok, 2 bad input, 3 missing dependency.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--events", type=int, default=5)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    try:
        import numpy as np
        import uproot
    except ImportError as exc:
        print(json.dumps({"status": "missing-dependency", "reason": str(exc)}))
        return 3
    if a.events < 1:
        print(json.dumps({"status": "rejected", "reason": "--events must be >= 1"}))
        return 2
    out = Path(a.out)
    (out / "results" / "hit_r").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    runs, subruns, evts = [], [], []
    hx, hy, hz, tx, ty, tz, tid = [], [], [], [], [], [], []
    for i in range(a.events):
        run, subrun, event = 1 + i // 3, 0, 100 + i
        runs.append(run); subruns.append(subrun); evts.append(event)
        n = int(rng.integers(20, 60))
        r = rng.uniform(50.0, 1000.0, n)                 # mm
        phi = rng.uniform(-np.pi, np.pi, n)
        hx.append(r * np.cos(phi)); hy.append(r * np.sin(phi)); hz.append(rng.normal(0.0, 300.0, n))
        xs, ys, zs, ids = [], [], [], []
        for t in range(int(rng.integers(2, 5))):        # sampled straight-ish tracks, 8 points each
            ph, dz = rng.uniform(-np.pi, np.pi), rng.normal(0.0, 0.5)
            s = np.linspace(0.0, 1000.0, 8)
            xs += list(s * np.cos(ph)); ys += list(s * np.sin(ph)); zs += list(s * dz); ids += [t] * 8
        tx.append(np.array(xs)); ty.append(np.array(ys)); tz.append(np.array(zs)); tid.append(np.array(ids, np.int32))
        # stand-in for an event-level project result: hit-radius histogram, fixed bins, unit weights
        counts, edges = np.histogram(r, bins=np.linspace(0.0, 1000.0, 11))
        res = {"kind": "binned-1d", "name": "hit_r", "title": "Hit radius", "x_label": "r", "x_unit": "mm",
               "y_label": "hits", "edges": edges.tolist(), "contents": counts.astype(float).tolist(),
               "sumw2": counts.astype(float).tolist(), "underflow": 0.0, "overflow": 0.0,
               "labels": ["synthetic"]}
        (out / "results" / "hit_r" / f"{run}_{subrun}_{event}.json").write_text(json.dumps(res, indent=1))

    import awkward as ak
    with uproot.recreate(out / "demo.root") as f:
        f["events"] = {"run": np.array(runs, np.int32), "subrun": np.array(subruns, np.int32),
                       "event": np.array(evts, np.int64),
                       "hit": ak.zip({"x": ak.Array(hx), "y": ak.Array(hy), "z": ak.Array(hz)}),
                       "trk": ak.zip({"x": ak.Array(tx), "y": ak.Array(ty), "z": ak.Array(tz), "id": ak.Array(tid)})}
        # dataset-level TH1D with variable bins, weights and Sumw2 (written member by member)
        edges = np.array([0.0, 5.0, 10.0, 20.0, 40.0, 80.0])
        x = rng.exponential(15.0, 500); w = rng.uniform(0.5, 1.5, 500)
        sumw = np.zeros(len(edges) + 1); sumw2 = np.zeros(len(edges) + 1)
        idx = np.searchsorted(edges, x, side="right")    # 0 = underflow, len(edges) = overflow
        np.add.at(sumw, idx, w); np.add.at(sumw2, idx, w * w)
        inside = (x >= edges[0]) & (x < edges[-1])
        f["h_pt"] = uproot.writing.identify.to_TH1x(
            fName="h_pt", fTitle="Track p_{T};p_{T} [GeV];weighted tracks", data=sumw,
            fEntries=float(len(x)), fTsumw=float(w[inside].sum()), fTsumw2=float((w[inside] ** 2).sum()),
            fTsumwx=float((w * x)[inside].sum()), fTsumwx2=float((w * x * x)[inside].sum()), fSumw2=sumw2,
            fXaxis=uproot.writing.identify.to_TAxis(fName="xaxis", fTitle="p_{T} [GeV]", fNbins=len(edges) - 1,
                                                    fXmin=float(edges[0]), fXmax=float(edges[-1]), fXbins=edges))
    table = {"kind": "table", "name": "hits_per_run", "title": "Hits per run (synthetic)",
             "categories": [], "series": [{"name": "hits", "unit": "count", "values": []},
                                          {"name": "track points", "unit": "count", "values": []}],
             "labels": ["synthetic"]}
    for run in sorted(set(runs)):
        sel = [i for i, rr in enumerate(runs) if rr == run]
        table["categories"].append(f"run {run}")
        table["series"][0]["values"].append(int(sum(len(hx[i]) for i in sel)))
        table["series"][1]["values"].append(int(sum(len(tx[i]) for i in sel)))
    (out / "results" / "hits_per_run.json").write_text(json.dumps(table, indent=1))
    # a schematic detector: half cylinder shell (cut-away so the event stays visible), r = 1100 mm, |z| <= 1200 mm
    nseg, r0, z0 = 24, 1100.0, 1200.0
    lines = ["# schematic half cylinder, unit mm (synthetic)"]
    for zz in (-z0, z0):
        for j in range(nseg + 1):
            ph = np.pi * j / nseg
            lines.append(f"v {r0 * np.cos(ph):.6f} {r0 * np.sin(ph):.6f} {zz:.6f}")
    for j in range(nseg):
        a1, b1 = j + 1, j + 2
        lines.append(f"f {a1} {b1} {b1 + nseg + 1} {a1 + nseg + 1}")
    (out / "detector.obj").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": "ok", "status_label": "synthetic", "out": str(out), "events": a.events}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
