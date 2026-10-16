#!/usr/bin/env python3
"""Compare one histogram (TH1, TH2 or TH3) in two ROOT files bin by bin, within stated tolerances.

Usage: python3 compare_root_histograms.py --reference ref.root --candidate cand.root --hist path/in/file
           [--candidate-hist other/path] [--abs-tol A] [--rel-tol R] [--sigma-tol S] [--include-flow]
           [--backend auto|pyroot|uproot] [--status LABEL]

Checks (all must pass):
- shape: same dimension and number of bins on every axis (a mismatch is a verdict, exit 1, not a crash);
- edges: bin edges equal on every axis (relative 1e-12);
- values: every bin within |cand - ref| <= A + R * |ref| (defaults A = 0, R = 1e-9);
- sigma (only with --sigma-tol): every bin within |cand - ref| / sqrt(err_ref^2 + err_cand^2) <= S; a bin with zero
  combined error and a nonzero difference fails.
Bins are compared per (x, y, z) index in ROOT numbering (1..n; 0 and n+1 are underflow and overflow, included with
--include-flow). The worst bin by absolute difference, by relative difference and by pull is reported separately.

Output: one JSON object on stdout with "status" ("pass", "fail", "error" or "missing-dependency"), "status_label"
(--status, the inputs' artifact label, default unvalidated), "verdict", the
backend, per-check results, the worst bins and entries/integral of both histograms.
Backends: PyROOT, else uproot (auto). Exit codes: 0 within tolerance, 1 outside tolerance or shape/edge mismatch,
2 bad input (missing file, histogram not found, not a histogram, bad tolerance), 3 neither PyROOT nor uproot
importable (or the requested backend is not).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from itertools import product
from pathlib import Path

sys.dont_write_bytecode = True  # the import below leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument  # noqa: E402

EDGE_RTOL = 1e-12


class InputError(Exception):
    """Bad input: exit 2."""


class MissingDependency(Exception):
    """No usable backend: exit 3."""


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--hist", required=True, help="histogram path inside the reference (and candidate) file")
    ap.add_argument("--candidate-hist", help="histogram path in the candidate file, if different")
    ap.add_argument("--abs-tol", type=float, default=0.0)
    ap.add_argument("--rel-tol", type=float, default=1e-9)
    ap.add_argument("--sigma-tol", type=float, help="maximum |difference| / combined bin error")
    ap.add_argument("--include-flow", action="store_true", help="also compare underflow and overflow bins")
    ap.add_argument("--backend", choices=("auto", "pyroot", "uproot"), default="auto")
    add_status_argument(ap)
    return ap.parse_args(argv)


def _hist_from_pyroot(path: Path, name: str, flow: bool) -> dict:
    import ROOT  # noqa: F401 - imported by the caller's backend choice
    f = ROOT.TFile.Open(str(path), "READ")
    if not f or f.IsZombie():
        raise InputError(f"could not open ROOT file: {path}")
    try:
        h = f.Get(name)
        if not h:
            raise InputError(f"histogram not found: {name} in {path}")
        if not h.InheritsFrom("TH1"):
            raise InputError(f"{name} in {path} is a {h.ClassName()}, not a histogram")
        dim = h.GetDimension()
        axes = [h.GetXaxis(), h.GetYaxis(), h.GetZaxis()][:dim]
        nbins = [ax.GetNbins() for ax in axes]
        edges = [[ax.GetBinLowEdge(i) for i in range(1, n + 2)] for ax, n in zip(axes, nbins)]
        bins = {}
        for idx in product(*[range(0 if flow else 1, n + (2 if flow else 1)) for n in nbins]):
            full = list(idx) + [0] * (3 - dim)
            b = h.GetBin(*full)
            bins[idx] = (float(h.GetBinContent(b)), float(h.GetBinError(b)))
        return {"class": h.ClassName(), "dim": dim, "nbins": nbins, "edges": edges, "bins": bins,
                "entries": float(h.GetEntries()), "integral": float(h.Integral())}
    finally:
        f.Close()


def _hist_from_uproot(path: Path, name: str, flow: bool) -> dict:
    import uproot
    try:
        f = uproot.open(path)
    except Exception as exc:  # noqa: BLE001 - uproot raises many types for a file that is not ROOT
        raise InputError(f"could not open ROOT file: {path} ({type(exc).__name__})") from None
    with f:
        try:
            h = f[name]
        except Exception:  # noqa: BLE001 - KeyInFileError and friends
            raise InputError(f"histogram not found: {name} in {path}") from None
        cls = getattr(h, "classname", type(h).__name__)
        if not (str(cls).startswith(("TH1", "TH2", "TH3", "TProfile")) and hasattr(h, "values") and hasattr(h, "axes")):
            raise InputError(f"{name} in {path} is a {cls}, not a histogram")
        dim = len(h.axes)
        values = h.values(flow=True).tolist()
        errors = h.errors(flow=True).tolist()
        edges = [[float(x) for x in ax.edges()] for ax in h.axes]
        nbins = [len(e) - 1 for e in edges]
        bins = {}
        for idx in product(*[range(0 if flow else 1, n + (2 if flow else 1)) for n in nbins]):
            v, e = values, errors
            for i in idx:
                v, e = v[i], e[i]
            bins[idx] = (float(v), float(e))
        inner = h.values(flow=False)
        return {"class": str(cls), "dim": dim, "nbins": nbins, "edges": edges, "bins": bins,
                "entries": float(h.member("fEntries")), "integral": float(inner.sum())}


def _backend(choice: str):
    order = ("pyroot", "uproot") if choice == "auto" else (choice,)
    for name in order:
        try:
            if name == "pyroot":
                import ROOT  # noqa: F401
                return name, _hist_from_pyroot
            import uproot  # noqa: F401
            return name, _hist_from_uproot
        except (ImportError, OSError):  # a PyROOT built for another Python can fail with OSError
            continue
    want = "PyROOT or uproot" if choice == "auto" else choice
    raise MissingDependency(f"{want} is not importable; install uproot (pip install uproot) or use a Python with "
                            "PyROOT (scripts/find_python.py finds one)")


def _edges_equal(a: list, b: list) -> bool:
    return len(a) == len(b) and all(math.isclose(x, y, rel_tol=EDGE_RTOL, abs_tol=EDGE_RTOL) for x, y in zip(a, b))


def compare(ref: dict, cand: dict, abs_tol: float, rel_tol: float, sigma_tol: float | None) -> dict:
    checks: dict = {}
    shape_ok = ref["dim"] == cand["dim"] and ref["nbins"] == cand["nbins"]
    checks["shape"] = {"ok": shape_ok, "reference": {"dimension": ref["dim"], "bins": ref["nbins"]},
                       "candidate": {"dimension": cand["dim"], "bins": cand["nbins"]}}
    if not shape_ok:
        return {"checks": checks, "worst": {}}
    bad_axes = [ax for ax, (a, b) in zip("xyz", zip(ref["edges"], cand["edges"])) if not _edges_equal(a, b)]
    checks["edges"] = {"ok": not bad_axes, "axes_differing": bad_axes}
    worst: dict = {"abs": None, "rel": None, "sigma": None}
    outside_values, outside_sigma = [], []
    for idx, (rv, re_) in ref["bins"].items():
        cv, ce = cand["bins"][idx]
        diff = abs(cv - rv)
        rel = diff / abs(rv) if rv else (0.0 if diff == 0 else math.inf)
        comb = math.hypot(re_, ce)
        pull = diff / comb if comb else (0.0 if diff == 0 else math.inf)
        row = {"bin": list(idx), "reference": rv, "candidate": cv, "abs_diff": diff,
               "rel_diff": rel if math.isfinite(rel) else "inf", "pull": pull if math.isfinite(pull) else "inf"}
        for key, val in (("abs", diff), ("rel", rel), ("sigma", pull)):
            cur = worst[key]
            if cur is None or val > cur[1]:
                worst[key] = (row, val)
        if diff > abs_tol + rel_tol * abs(rv):
            outside_values.append(list(idx))
        if sigma_tol is not None and pull > sigma_tol:
            outside_sigma.append(list(idx))
    checks["values"] = {"ok": not outside_values, "abs_tol": abs_tol, "rel_tol": rel_tol,
                        "bins_outside": len(outside_values), "first_bins_outside": outside_values[:10]}
    if sigma_tol is not None:
        checks["sigma"] = {"ok": not outside_sigma, "sigma_tol": sigma_tol, "bins_outside": len(outside_sigma),
                           "first_bins_outside": outside_sigma[:10]}
    return {"checks": checks, "worst": {k: (v[0] if v else None) for k, v in worst.items()}}


def main(argv=None) -> int:
    args = parse_args(argv)
    out: dict = {"status": "error", "status_label": args.status, "histogram": args.hist}
    try:
        for name, tol in (("--abs-tol", args.abs_tol), ("--rel-tol", args.rel_tol), ("--sigma-tol", args.sigma_tol)):
            if tol is not None and not (math.isfinite(tol) and tol >= 0):
                raise InputError(f"{name} must be a finite number >= 0")
        for path in (args.reference, args.candidate):
            if not path.is_file():
                raise InputError(f"ROOT file does not exist: {path}")
        backend, load = _backend(args.backend)
        out["backend"] = backend
        ref = load(args.reference, args.hist, args.include_flow)
        cand = load(args.candidate, args.candidate_hist or args.hist, args.include_flow)
        res = compare(ref, cand, args.abs_tol, args.rel_tol, args.sigma_tol)
        ok = all(c["ok"] for c in res["checks"].values())
        out.update(status="pass" if ok else "fail", verdict="within tolerance" if ok else "outside tolerance",
                   include_flow=args.include_flow, checks=res["checks"], worst_bins=res["worst"],
                   reference={"class": ref["class"], "entries": ref["entries"], "integral": ref["integral"]},
                   candidate={"class": cand["class"], "entries": cand["entries"], "integral": cand["integral"]})
        print(json.dumps(out, indent=1))
        return 0 if ok else 1
    except InputError as exc:
        print(json.dumps(dict(out, error=str(exc))))
        return 2
    except MissingDependency as exc:
        print(json.dumps(dict(out, status="missing-dependency", error=str(exc))))
        return 3


if __name__ == "__main__":
    sys.exit(main())
