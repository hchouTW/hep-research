#!/usr/bin/env python3
"""Generate tiny synthetic ROOT fixtures for the ROOT-dependent assets and scripts.

Purpose: give the PyROOT scripts and C++/PyROOT templates a real input to run on,
so they are exercised end to end rather than only via --help or py_compile.

What it writes into OUTDIR (default: ./root_fixtures):
- events.root     TTree "Events": nMuon, Muon_pt[nMuon], Muon_eta[nMuon],
                  event_weight (includes some negative weights), pt, mass.
- histograms.root TH1D "nominal", "jes_Up", "jes_Down" (shape variations of a
                  falling spectrum) and "mass_hist" (Gaussian peak on exponential).
- histograms_candidate.root  same "nominal" with a small +2% shift, for comparisons.
- workspace.root  RooWorkspace "workspace" with observable, data, and s+b model.

Usage: PyROOT is required (e.g. Homebrew's python3.14 when ROOT is from Homebrew).
    python3 <plugin root>/tests/skills/hep_computing/make_root_fixtures.py [OUTDIR]
Seeds are fixed (TRandom3(12345)) so outputs are reproducible.
"""
from __future__ import annotations

import sys
from array import array
from pathlib import Path

import ROOT


def make_events(path: Path, rng: ROOT.TRandom3, n_events: int = 5000) -> None:
    out = ROOT.TFile(str(path), "RECREATE")
    tree = ROOT.TTree("Events", "synthetic events")
    max_mu = 4
    n_muon = array("i", [0])
    muon_pt = array("f", [0.0] * max_mu)
    muon_eta = array("f", [0.0] * max_mu)
    weight = array("f", [0.0])
    pt = array("f", [0.0])
    mass = array("f", [0.0])
    tree.Branch("nMuon", n_muon, "nMuon/I")
    tree.Branch("Muon_pt", muon_pt, "Muon_pt[nMuon]/F")
    tree.Branch("Muon_eta", muon_eta, "Muon_eta[nMuon]/F")
    tree.Branch("event_weight", weight, "event_weight/F")
    tree.Branch("pt", pt, "pt/F")
    tree.Branch("mass", mass, "mass/F")
    for _ in range(n_events):
        n_muon[0] = rng.Integer(max_mu + 1)
        pts = sorted((10.0 + rng.Exp(25.0) for _ in range(n_muon[0])), reverse=True)
        for i, value in enumerate(pts):
            muon_pt[i] = value
            muon_eta[i] = rng.Uniform(-3.0, 3.0)
        # ~5% negative weights, like NLO generators produce.
        weight[0] = -1.0 if rng.Uniform() < 0.05 else 1.0
        pt[0] = rng.Exp(20.0)
        mass[0] = rng.Gaus(91.0, 3.0) if rng.Uniform() < 0.3 else 60.0 + rng.Exp(30.0)
        tree.Fill()
    tree.Write()
    out.Close()


def make_histograms(path: Path, candidate_path: Path, rng: ROOT.TRandom3) -> None:
    out = ROOT.TFile(str(path), "RECREATE")
    nominal = ROOT.TH1D("nominal", "nominal;m [GeV];Events", 20, 0.0, 200.0)
    up = ROOT.TH1D("jes_Up", "jes_Up;m [GeV];Events", 20, 0.0, 200.0)
    down = ROOT.TH1D("jes_Down", "jes_Down;m [GeV];Events", 20, 0.0, 200.0)
    for _ in range(20000):
        x = rng.Exp(50.0)
        nominal.Fill(x)
        up.Fill(1.03 * x)
        down.Fill(0.97 * x)
    mass_hist = ROOT.TH1D("mass_hist", "mass;m [GeV];Events", 60, 60.0, 120.0)
    for _ in range(3000):
        mass_hist.Fill(rng.Gaus(91.0, 2.5))
    for _ in range(7000):
        mass_hist.Fill(60.0 + rng.Exp(40.0))
    for hist in (nominal, up, down, mass_hist):
        hist.Write()
    out.Close()

    cand = ROOT.TFile(str(candidate_path), "RECREATE")
    shifted = nominal.Clone("nominal")
    shifted.Scale(1.02)
    shifted.Write()
    cand.Close()


def make_workspace(path: Path) -> None:
    ws = ROOT.RooWorkspace("workspace")
    ws.factory("Gaussian::signal(mass[60,120], mean[91,80,100], sigma[2.5,0.5,10])")
    ws.factory("Exponential::background(mass, slope[-0.03,-1,0])")
    ws.factory("SUM::model(nsig[300,0,5000]*signal, nbkg[700,0,5000]*background)")
    model = ws.pdf("model")
    data = model.generate(ROOT.RooArgSet(ws.var("mass")), 1000)
    data.SetName("data")
    getattr(ws, "import")(data)
    ws.writeToFile(str(path))


def main() -> None:
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("root_fixtures")
    outdir.mkdir(parents=True, exist_ok=True)
    ROOT.gROOT.SetBatch(True)
    # Keep histograms owned by Python, not by the output file, so they survive Close().
    ROOT.TH1.AddDirectory(False)
    ROOT.RooRandom.randomGenerator().SetSeed(12345)
    rng = ROOT.TRandom3(12345)
    make_events(outdir / "events.root", rng)
    make_histograms(outdir / "histograms.root", outdir / "histograms_candidate.root", rng)
    make_workspace(outdir / "workspace.root")
    print(f"Wrote fixtures to {outdir}")


if __name__ == "__main__":
    main()
