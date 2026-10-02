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
    parser = argparse.ArgumentParser(description="Fit a mass histogram with a RooFit signal plus background model.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--hist", required=True, help="Input TH1 path")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workspace", default="workspace")
    parser.add_argument("--observable", default="mass")
    parser.add_argument("--min", required=True, type=float, dest="x_min")
    parser.add_argument("--max", required=True, type=float, dest="x_max")
    return parser.parse_args()


def load_histogram(path: Path, hist_name: str) -> ROOT.TH1:
    if not path.exists():
        raise FileNotFoundError(f"Input ROOT file does not exist: {path}")
    root_file = ROOT.TFile.Open(str(path), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {path}")
        hist = root_file.Get(hist_name)
        if not hist:
            raise KeyError(f"Histogram not found: {hist_name}")
        if hist.GetEntries() <= 0:
            raise ValueError(f"Histogram has no entries: {hist_name}")
        detached = hist.Clone(f"{hist.GetName()}_fit_input")
        detached.SetDirectory(0)
        return detached
    finally:
        if root_file:
            root_file.Close()


def count_nonzero_bins(hist: ROOT.TH1) -> int:
    return sum(1 for index in range(1, hist.GetNbinsX() + 1) if hist.GetBinContent(index) != 0.0)


def main() -> None:
    global ROOT
    args = parse_args()
    ROOT = import_root()
    ROOT.gROOT.SetBatch(True)

    hist = load_histogram(args.input, args.hist)
    if count_nonzero_bins(hist) < 5:
        raise ValueError("Histogram has fewer than five nonzero bins; fit is likely underconstrained")

    x = ROOT.RooRealVar(args.observable, args.observable, args.x_min, args.x_max)
    data = ROOT.RooDataHist("data", "binned input data", ROOT.RooArgList(x), hist)

    mean = ROOT.RooRealVar("mean", "signal mean", 0.5 * (args.x_min + args.x_max), args.x_min, args.x_max)
    sigma = ROOT.RooRealVar("sigma", "signal width", 0.05 * (args.x_max - args.x_min), 1e-6, args.x_max - args.x_min)
    signal = ROOT.RooGaussian("signal", "Gaussian signal", x, mean, sigma)

    slope = ROOT.RooRealVar("slope", "background slope", -0.01, -10.0, 10.0)
    background = ROOT.RooExponential("background", "exponential background", x, slope)

    total_yield = max(hist.Integral(), 1.0)
    nsig = ROOT.RooRealVar("nsig", "signal yield", 0.2 * total_yield, 0.0, 10.0 * total_yield)
    nbkg = ROOT.RooRealVar("nbkg", "background yield", 0.8 * total_yield, 0.0, 10.0 * total_yield)
    model = ROOT.RooAddPdf("model", "signal plus background", ROOT.RooArgList(signal, background), ROOT.RooArgList(nsig, nbkg))

    fit_result = model.fitTo(
        data,
        ROOT.RooFit.Save(True),
        ROOT.RooFit.Extended(True),
        ROOT.RooFit.SumW2Error(True),
        ROOT.RooFit.PrintLevel(-1),
    )
    if fit_result.status() != 0 or fit_result.covQual() < 2:
        print(f"warning: fit status={fit_result.status()} covQual={fit_result.covQual()}")

    frame = x.frame(ROOT.RooFit.Title(args.hist))
    data.plotOn(frame)
    model.plotOn(frame)
    model.plotOn(frame, ROOT.RooFit.Components("background"), ROOT.RooFit.LineStyle(ROOT.kDashed))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output = ROOT.TFile(str(args.output), "RECREATE")
    try:
        workspace = ROOT.RooWorkspace(args.workspace)
        getattr(workspace, "import")(x)
        getattr(workspace, "import")(data)
        getattr(workspace, "import")(model)
        workspace.Write()
        fit_result.Write("fit_result")
        canvas = ROOT.TCanvas("fit_canvas", "fit_canvas", 900, 700)
        frame.Draw()
        canvas.Write()
    finally:
        output.Close()

    print(f"fit status: {fit_result.status()}")
    print(f"covariance quality: {fit_result.covQual()}")
    print(f"wrote: {args.output}")


if __name__ == "__main__":
    main()
