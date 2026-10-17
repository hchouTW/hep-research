#!/usr/bin/env python3
"""Check the error bookkeeping of ROOT histograms and TEfficiency objects (C7): Sum of w^2 present for weighted
histograms, stored errors consistent with the fill, negative bins, the flow fraction, and passed <= total.

Purpose: the object-level checks behind "are these error bars right?" (see
<plugin root>/skills/hep-computing/references/root-usage-patterns.md). Which interval to quote is hep-statistics'
question; measuring an efficiency is hep-detector's.
Checks per histogram (bins in ROOT numbering, flow bins included):
  sumw2-missing       error   weighted fill (fTsumw2 != fTsumw) but no Sumw2 array: ROOT then gives sqrt(content),
                              which is wrong for weights (call Sumw2() before filling, or TH1::SetDefaultSumw2()).
  sumw2-inconsistent  error   unit-weight fill (fTsumw2 == fTsumw) but Sumw2[i] != content[i] in a way no uniform
                              scale explains: errors were overwritten (SetBinError) or bins edited after filling.
  scaled              warning unit-weight fill whose Sumw2[i] = c * content[i] for one c != 1: consistent with Scale(c)
                              after filling (errors right; the stored fill statistics are not rescaled).
  negative-bins       warning bins with negative content (allowed with negative weights; a fit or a ratio may not be).
  flow-fraction       warning |under + overflow| above --max-flow-fraction of the total |content|.
  passed-above-total  error   TEfficiency (or --passed/--total): passed[i] > total[i] in some bin.
Input: a ROOT file (--object NAME, repeatable; --passed P --total T for two histograms) read with PyROOT or uproot
(--backend auto|pyroot|uproot; both optional), or a JSON file {"objects": {name: {"kind": "TH1", "values": [...],
"sumw2": [...] or null, "entries", "tsumw", "tsumw2"} | {"kind": "TEfficiency", "passed": TH1, "total": TH1}}}
with flow bins included (the canonical form both backends produce; no ROOT needed).
Usage: check_histogram_errors.py FILE [--object NAME ...] [--passed P --total T] [--backend auto|pyroot|uproot]
       [--max-flow-fraction 0.01] [--status LABEL]
Output JSON: status (ok, failed, rejected, missing-dependency), status_label, inputs, defaults_used, backend, and per
object: errors, warnings, weighted, error_definition, negative_bins, flow_fraction.
Exit codes: 0 no error (warnings allowed); 1 an error check fired; 2 bad input; 3 the requested backend is missing.
Standard library only (the backends excepted).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from array import array
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

TOL = 1e-9
INSTALL = ("install uproot (pip install uproot awkward; optional extra root-uproot) or use a Python with PyROOT "
           "(conda-forge root, LCG, Homebrew; scripts/find_python.py finds one)")


class InputError(ValueError):
    pass


class Missing(Exception):
    pass


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def check_th1(h: dict, max_flow: float) -> dict:
    vals, sw2 = [float(v) for v in h["values"]], h.get("sumw2")
    if sw2 is not None:
        sw2 = [float(v) for v in sw2]
        if len(sw2) != len(vals):
            raise InputError("values and sumw2 differ in length")
    tsumw, tsumw2 = float(h.get("tsumw") or 0.0), float(h.get("tsumw2") or 0.0)
    weighted = not _close(tsumw, tsumw2)
    errors, warnings = [], []
    if sw2 is None:
        definition = "sqrt(content) (no Sumw2)"
        if weighted:
            errors.append({"check": "sumw2-missing", "message": "weighted fill (fTsumw2 != fTsumw) without a Sumw2 array: "
                           "the errors are sqrt(content), wrong for weights; call Sumw2() before filling"})
    else:
        definition = "sqrt(sum of w^2)"
        if not weighted and tsumw > 0:
            bad = [i for i, (v, s) in enumerate(zip(vals, sw2)) if not _close(v, s)]
            if bad:
                ratios = {round(s / v, 12) for v, s in zip(vals, sw2) if v != 0}
                zero_ok = all(s == 0 for v, s in zip(vals, sw2) if v == 0)
                if len(ratios) == 1 and zero_ok:
                    c = ratios.pop()
                    warnings.append({"check": "scaled", "message": f"Sumw2 = {c:g} x content in every bin: consistent "
                                     f"with Scale({c:g}) after a unit-weight fill (errors right; fill statistics stale)"})
                else:
                    errors.append({"check": "sumw2-inconsistent", "bins": bad[:20],
                                   "message": "unit-weight fill but Sumw2 differs from the content in some bins and no "
                                              "uniform scale explains it: errors overwritten (SetBinError) or bins edited"})
    negative = [i for i, v in enumerate(vals) if v < 0]
    if negative:
        warnings.append({"check": "negative-bins", "bins": negative[:20],
                         "message": f"{len(negative)} bin(s) with negative content"})
    total = sum(abs(v) for v in vals)
    flow = abs(vals[0]) + abs(vals[-1]) if len(vals) >= 2 else 0.0
    fraction = flow / total if total > 0 else 0.0
    if fraction > max_flow:
        warnings.append({"check": "flow-fraction", "message": f"under+overflow hold {fraction:.3g} of |content| "
                         f"(threshold {max_flow:g}): widen the range or say how the flow is used"})
    return {"kind": "TH1", "weighted": weighted, "error_definition": definition, "errors": errors,
            "warnings": warnings, "negative_bins": negative, "flow_fraction": fraction, "n_bins_with_flow": len(vals)}


def check_efficiency(passed: dict, total: dict, max_flow: float) -> dict:
    p, t = check_th1(passed, max_flow), check_th1(total, max_flow)
    pv, tv = [float(v) for v in passed["values"]], [float(v) for v in total["values"]]
    if len(pv) != len(tv):
        raise InputError("passed and total have different binning")
    above = [i for i, (a, b) in enumerate(zip(pv, tv)) if a > b + TOL * max(1.0, abs(b))]
    errors = [dict(e, part="passed") for e in p["errors"]] + [dict(e, part="total") for e in t["errors"]]
    if above:
        errors.append({"check": "passed-above-total", "bins": above[:20],
                       "message": f"passed > total in {len(above)} bin(s): not an efficiency (a filling or selection bug)"})
    return {"kind": "TEfficiency", "weighted": p["weighted"] or t["weighted"],
            "error_definition": "TEfficiency interval (statistic option)", "errors": errors,
            "warnings": [dict(w, part="passed") for w in p["warnings"]] + [dict(w, part="total") for w in t["warnings"]],
            "negative_bins": sorted(set(p["negative_bins"]) | set(t["negative_bins"])),
            "flow_fraction": max(p["flow_fraction"], t["flow_fraction"]), "passed_above_total_bins": above}


# ---------------------------------------------------------------- backends (both produce the canonical form)

def _from_uproot(path: Path, names: list[str]) -> dict:
    try:
        import uproot
    except ImportError as exc:
        raise Missing(f"uproot is not installed ({exc})") from exc

    def th1(obj) -> dict:
        sw2 = obj.member("fSumw2")
        sw2 = [float(v) for v in sw2] if sw2 is not None and len(sw2) else None
        return {"kind": "TH1", "values": [float(v) for v in obj.values(flow=True).ravel()], "sumw2": sw2,
                "entries": float(obj.member("fEntries")), "tsumw": float(obj.member("fTsumw")),
                "tsumw2": float(obj.member("fTsumw2"))}
    try:
        f = uproot.open(path)
    except Exception as exc:  # uproot raises many types for a file that is not ROOT
        raise InputError(f"{path}: not readable by uproot ({exc})") from exc
    out = {}
    with f:
        for name in names:
            if name not in f:
                raise InputError(f"{name!r} not found in {path}")
            obj = f[name]
            if obj.classname.startswith("TEfficiency"):
                out[name] = {"kind": "TEfficiency", "passed": th1(obj.member("fPassedHistogram")),
                             "total": th1(obj.member("fTotalHistogram"))}
            elif obj.classname.startswith(("TH1", "TH2", "TH3")):
                out[name] = th1(obj)
            else:
                raise InputError(f"{name!r} is a {obj.classname}, not a histogram or TEfficiency")
    return out


def _from_pyroot(path: Path, names: list[str]) -> dict:
    try:
        import ROOT
    except ImportError as exc:
        raise Missing(f"PyROOT is not importable ({exc})") from exc
    ROOT.gErrorIgnoreLevel = ROOT.kError

    def th1(h) -> dict:
        stats = array("d", [0.0] * 13)  # fTsumw, fTsumw2, ... as TH1::GetStats fills them
        h.GetStats(stats)
        n = h.GetNcells()
        sw2 = [float(h.GetSumw2().At(i)) for i in range(n)] if h.GetSumw2N() > 0 else None
        return {"kind": "TH1", "values": [float(h.GetBinContent(i)) for i in range(n)], "sumw2": sw2,
                "entries": float(h.GetEntries()), "tsumw": float(stats[0]), "tsumw2": float(stats[1])}
    f = ROOT.TFile.Open(str(path))
    if not f or f.IsZombie():
        raise InputError(f"{path}: not readable by ROOT")
    out = {}
    try:
        for name in names:
            obj = f.Get(name)
            if not obj:
                raise InputError(f"{name!r} not found in {path}")
            if obj.InheritsFrom("TEfficiency"):
                out[name] = {"kind": "TEfficiency", "passed": th1(obj.GetPassedHistogram()),
                             "total": th1(obj.GetTotalHistogram())}
            elif obj.InheritsFrom("TH1"):
                out[name] = th1(obj)
            else:
                raise InputError(f"{name!r} is a {obj.ClassName()}, not a histogram or TEfficiency")
    finally:
        f.Close()
    return out


def load(args) -> tuple[str, dict]:
    path = Path(args.file)
    if not path.is_file():
        raise InputError(f"{path} not found")
    if path.suffix == ".json":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise InputError(f"{path}: not JSON ({exc})") from exc
        objs = doc.get("objects") if isinstance(doc, dict) else None
        if not isinstance(objs, dict) or not objs:
            raise InputError(f"{path}: needs a non-empty 'objects' mapping")
        return "json", objs
    names = list(args.object or []) + [n for n in (args.passed, args.total) if n]
    if not names:
        raise InputError("name the objects to check (--object, or --passed and --total)")
    order = ("pyroot", "uproot") if args.backend == "auto" else (args.backend,)
    last = None
    for backend in order:
        try:
            objs = (_from_pyroot if backend == "pyroot" else _from_uproot)(path, names)
            break
        except Missing as exc:
            last = exc
    else:
        raise Missing(str(last))
    if args.passed and args.total:
        objs[f"{args.passed}/{args.total}"] = {"kind": "TEfficiency", "passed": objs.pop(args.passed),
                                               "total": objs.pop(args.total)}
    return backend, objs


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="ROOT file, or the canonical JSON form")
    ap.add_argument("--object", action="append", help="histogram or TEfficiency name (repeatable)")
    ap.add_argument("--passed")
    ap.add_argument("--total")
    ap.add_argument("--backend", choices=("auto", "pyroot", "uproot"), default="auto")
    ap.add_argument("--max-flow-fraction", type=float, default=0.01)
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    head = {"status_label": args.status, "inputs": {k: v for k, v in vars(args).items() if k != "status"},
            "defaults_used": [k for k in ("backend", "max_flow_fraction", "status")
                              if f"--{k.replace('_', '-')}" not in given]}
    try:
        if not (math.isfinite(args.max_flow_fraction) and 0 <= args.max_flow_fraction <= 1):
            raise InputError("--max-flow-fraction must be in [0, 1]")
        if bool(args.passed) != bool(args.total):
            raise InputError("--passed and --total go together")
        backend, objs = load(args)
        report = {}
        for name, obj in objs.items():
            if not isinstance(obj, dict) or obj.get("kind") not in ("TH1", "TEfficiency"):
                raise InputError(f"{name}: kind must be TH1 or TEfficiency")
            report[name] = (check_efficiency(obj["passed"], obj["total"], args.max_flow_fraction)
                            if obj["kind"] == "TEfficiency" else check_th1(obj, args.max_flow_fraction))
    except Missing as exc:
        print(json.dumps({"status": "missing-dependency", **head, "error": str(exc), "install": INSTALL}, indent=1))
        return exit_code("missing-dependency")
    except (InputError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "rejected", **head, "error": f"{type(exc).__name__}: {exc}"}, indent=1))
        return exit_code("rejected")
    status = "failed" if any(r["errors"] for r in report.values()) else "ok"
    print(json.dumps({"status": status, **head, "backend": backend, "objects": report}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
