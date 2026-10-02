#!/usr/bin/env python3
"""Write a small synthetic NanoAOD-like ROOT file and print the answers to check against.

Purpose: a known-good test sample for any jagged-jet analysis code (selection, cutflow,
leading-pair mass, weighted histogram, normalization). Writing a jagged TTree with uproot
by hand is fiddly (a plain dict assignment can write an RNTuple instead of a TTree), and
models that must test their own code lose many turns on it. This script does it once,
correctly, and prints the expected numbers computed independently of any analysis code.

What it writes (all values are SYNTHETIC, never data or a physics result):
  - TTree `Events`: jagged `Jet_pt`, `Jet_eta`, `Jet_phi`, `Jet_mass` (float32, jets ordered
    by descending pt as in NanoAOD) and a scalar signed `genWeight` (+1 or -1, about 20%
    negative by default).
  - TTree `Runs` (one entry): `genEventCount`, `genEventSumw`, `genEventSumw2`, the totals
    over the FULL sample before any selection, as the NanoAOD `Runs` tree stores them.
It prints a JSON summary to stdout with the expected number of events with at least two
jets passing pt > --pt-min and |eta| < --eta-max, their signed sum of weights and sum of
squared weights, and the weighted mean and maximum of the invariant mass of the two
leading selected jets (computed from the float32 values that are stored).

Usage:
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/make_synthetic_nanoaod.py --out sample.root [--events 400] [--seed 1]
      [--pt-min 30] [--eta-max 2.5] [--neg-frac 0.2]
uproot adds one counter branch per jagged branch (`nJet_pt`, `nJet_eta`, ...) instead of NanoAOD's
single `nJet`; read the jagged `Jet_*` branches and ignore the counters.
Requires numpy, awkward and uproot (uproot >= 5; tested with 5.7). Units: pt, mass in GeV,
eta dimensionless, phi in radians. The same seed always gives the same file.
"""

import argparse
import json
import math
import sys

import numpy as np


def generate(n_events=400, seed=1, neg_frac=0.2):
    """Return per-event jet lists (float32, pt-descending) and signed weights."""
    rng = np.random.default_rng(seed)
    n_jets = rng.integers(0, 6, n_events)
    pt, eta, phi, mass = [], [], [], []
    for k in n_jets:
        pt.append(np.sort(rng.uniform(10.0, 120.0, k))[::-1].astype(np.float32))
        eta.append(rng.uniform(-3.5, 3.5, k).astype(np.float32))
        phi.append(rng.uniform(-math.pi, math.pi, k).astype(np.float32))
        mass.append(rng.uniform(2.0, 15.0, k).astype(np.float32))
    weight = np.where(rng.uniform(size=n_events) < neg_frac, -1.0, 1.0).astype(np.float32)
    return pt, eta, phi, mass, weight


def _mass_of_pair(p1, e1, f1, m1, p2, e2, f2, m2):
    px = p1 * math.cos(f1) + p2 * math.cos(f2)
    py = p1 * math.sin(f1) + p2 * math.sin(f2)
    pz = p1 * math.sinh(e1) + p2 * math.sinh(e2)
    en = math.sqrt((p1 * math.cosh(e1)) ** 2 + m1 ** 2) + math.sqrt((p2 * math.cosh(e2)) ** 2 + m2 ** 2)
    return math.sqrt(max(en * en - px * px - py * py - pz * pz, 0.0))


def expected(pt, eta, phi, mass, weight, pt_min=30.0, eta_max=2.5):
    """Pure-Python expectations (no awkward), from the float32 values that are stored."""
    n_pass, sumw, sumw2, masses, weights = 0, 0.0, 0.0, [], []
    for p, e, f, m, w in zip(pt, eta, phi, mass, weight):
        keep = [i for i in range(len(p)) if float(p[i]) > pt_min and abs(float(e[i])) < eta_max]
        if len(keep) < 2:
            continue
        keep.sort(key=lambda i: -float(p[i]))
        a, b = keep[0], keep[1]
        masses.append(_mass_of_pair(float(p[a]), float(e[a]), float(f[a]), float(m[a]),
                                    float(p[b]), float(e[b]), float(f[b]), float(m[b])))
        weights.append(float(w))
        n_pass += 1
        sumw += float(w)
        sumw2 += float(w) ** 2
    wmean = sum(m * w for m, w in zip(masses, weights)) / sumw if sumw else float("nan")
    return {"n_selected_events": n_pass, "sumw_selected": sumw, "sumw2_selected": sumw2,
            "mjj_weighted_mean_GeV": wmean, "mjj_max_GeV": max(masses) if masses else float("nan")}


def write_file(path, pt, eta, phi, mass, weight):
    import awkward as ak
    import uproot
    with uproot.recreate(path) as f:
        f.mktree("Events", {"Jet_pt": "var * float32", "Jet_eta": "var * float32",
                            "Jet_phi": "var * float32", "Jet_mass": "var * float32",
                            "genWeight": "float32"})
        f["Events"].extend({"Jet_pt": ak.Array(pt), "Jet_eta": ak.Array(eta),
                            "Jet_phi": ak.Array(phi), "Jet_mass": ak.Array(mass),
                            "genWeight": weight})
        w = weight.astype(np.float64)
        f.mktree("Runs", {"genEventCount": "int64", "genEventSumw": "float64",
                          "genEventSumw2": "float64"})
        f["Runs"].extend({"genEventCount": np.array([len(weight)], dtype=np.int64),
                          "genEventSumw": np.array([w.sum()]),
                          "genEventSumw2": np.array([(w ** 2).sum()])})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="output ROOT file")
    ap.add_argument("--events", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pt-min", type=float, default=30.0)
    ap.add_argument("--eta-max", type=float, default=2.5)
    ap.add_argument("--neg-frac", type=float, default=0.2, help="fraction of negative weights")
    args = ap.parse_args(argv)
    if args.events < 1 or not 0.0 <= args.neg_frac <= 1.0:
        ap.error("--events must be >= 1 and --neg-frac in [0, 1]")
    pt, eta, phi, mass, weight = generate(args.events, args.seed, args.neg_frac)
    write_file(args.out, pt, eta, phi, mass, weight)
    summary = {"file": args.out, "synthetic": True, "events": args.events, "seed": args.seed,
               "selection": f"jet pt > {args.pt_min} GeV, |eta| < {args.eta_max}, >= 2 jets",
               "genEventSumw_full_sample": float(weight.astype(np.float64).sum()),
               "genEventCount_full_sample": args.events}
    summary.update(expected(pt, eta, phi, mass, weight, args.pt_min, args.eta_max))
    summary["note"] = "SYNTHETIC sample: not data; do not report these numbers as results"
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
