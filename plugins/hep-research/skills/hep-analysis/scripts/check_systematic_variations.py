#!/usr/bin/env python3
"""Compare nominal and Up/Down systematic histograms and classify each variation's effect.

The effect of a variation is classified per histogram as `none`, `normalization`, `shape` or `mixed`
from the integral change and the change of the unit-normalized shape. An unchanged integral is NOT
evidence that the variation failed to propagate: a shape-only (migration) variation keeps the integral.
Only `none` (no bin changed beyond tolerance) asks the analyst to confirm propagation, and even then the
right check is the variation's effect on the final result (refit / sensitivity), which this script cannot see.

Inputs: a ROOT file (`--input`, needs PyROOT) or a JSON file (`--json`) of the form
{"nominal": [...], "up": [...], "down": [...]} with matching bin contents (no PyROOT needed).
Add `--format json` for a machine-readable report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_TOL = 1e-6  # relative tolerance on the integral and on the normalized shape


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check nominal/up/down histogram systematics and classify their effect.")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="ROOT file (requires PyROOT)")
    src.add_argument("--json", type=Path, help='JSON file {"nominal": [...], "up": [...], "down": [...]} of bin contents')
    parser.add_argument("--nominal", help="Nominal histogram path (ROOT input)")
    parser.add_argument("--up", help="Up-variation histogram path (ROOT input)")
    parser.add_argument("--down", help="Down-variation histogram path (ROOT input)")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow bins")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOL, help="relative tolerance (default %(default)g)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if args.input and not (args.nominal and args.up and args.down):
        parser.error("--input needs --nominal, --up and --down")
    return args


def classify_variation(nominal, varied, tol: float = DEFAULT_TOL) -> dict:
    """Classify one variation against nominal from bin contents (lists of floats).

    integral_rel_change: (sum varied - sum nominal) / sum nominal.
    shape_max_abs_change: max over bins of |varied_i / sum varied - nominal_i / sum nominal| divided by the max
    nominal fraction, i.e. the largest change of the unit-normalized shape relative to its peak.
    migration_fraction: half the L1 distance between the normalized shapes = the fraction of events that would
    have to move between bins to turn one shape into the other (0 for a pure normalization change)."""
    if len(nominal) != len(varied) or not nominal:
        raise ValueError("nominal and varied need the same, non-zero number of bins")
    n_sum, v_sum = float(sum(nominal)), float(sum(varied))
    bin_changed = any(abs(v - n) > tol * max(abs(n), abs(v), 1e-300) for n, v in zip(nominal, varied))
    if n_sum == 0.0 or v_sum == 0.0:
        return {"effect": "none" if not bin_changed else "undetermined", "integral_rel_change": None,
                "shape_max_abs_change": None, "migration_fraction": None, "bins_changed": bin_changed,
                "note": "zero integral: shape comparison undefined"}
    integral = v_sum / n_sum - 1.0
    fn = [x / n_sum for x in nominal]
    fv = [x / v_sum for x in varied]
    peak = max(abs(x) for x in fn) or 1.0
    shape = max(abs(a - b) for a, b in zip(fn, fv)) / peak
    migration = 0.5 * sum(abs(a - b) for a, b in zip(fn, fv))
    norm_changed, shape_changed = abs(integral) > tol, shape > tol
    effect = ("mixed" if norm_changed and shape_changed else "normalization" if norm_changed
              else "shape" if shape_changed else "none")
    notes = {
        "none": "no bin differs from nominal beyond tolerance: confirm the variation reached this histogram, then check "
                "its effect on the final result; a negligible effect can be genuine",
        "normalization": "integral changes, normalized shape does not: a pure normalization effect",
        "shape": "integral unchanged but the shape changes: a shape/migration effect; this is NOT a propagation failure",
        "mixed": "both the integral and the normalized shape change",
    }
    return {"effect": effect, "integral_rel_change": integral, "shape_max_abs_change": shape,
            "migration_fraction": migration, "bins_changed": bin_changed, "note": notes[effect]}


def assess(nominal, up, down, tol: float = DEFAULT_TOL) -> dict:
    out = {"up": classify_variation(nominal, up, tol), "down": classify_variation(nominal, down, tol)}
    warnings = []
    if out["up"]["effect"] == "none" and out["down"]["effect"] == "none":
        warnings.append("neither variation changes this histogram: confirm propagation, then judge by the effect on the result")
    iu, idn = out["up"]["integral_rel_change"], out["down"]["integral_rel_change"]
    if iu is not None and idn is not None and iu * idn > 0 and abs(iu) > tol and abs(idn) > tol:
        warnings.append("up and down move the integral in the same direction: one-sided or possibly swapped/mislabelled variation")
    out["warnings"] = warnings
    out["sensitivity"] = "not assessed here: evaluate the variation's effect on the fitted result (refit or impact)"
    return out


def get_hist(root_file: object, name: str) -> object:
    hist = root_file.Get(name)
    if not hist:
        raise KeyError(f"Histogram not found: {name}")
    if not hasattr(hist, "GetNbinsX"):
        raise TypeError(f"Object is not a 1D histogram-like object: {name}")
    return hist


def bin_range(hist: object, include_flow: bool) -> range:
    first_bin = 0 if include_flow else 1
    last_bin = hist.GetNbinsX() + 1 if include_flow else hist.GetNbinsX()
    return range(first_bin, last_bin + 1)


def check_compatible(nominal: object, varied: object, label: str) -> None:
    if nominal.GetNbinsX() != varied.GetNbinsX():
        raise ValueError(f"{label} bin count differs from nominal")
    for index in range(1, nominal.GetNbinsX() + 2):
        if nominal.GetXaxis().GetBinLowEdge(index) != varied.GetXaxis().GetBinLowEdge(index):
            raise ValueError(f"{label} bin edge differs from nominal at bin {index}")


def summarize_difference(nominal: object, varied: object, bins: range) -> tuple[float, float, int]:
    max_abs = 0.0
    max_rel = 0.0
    max_bin = 0
    for index in bins:
        nominal_value = float(nominal.GetBinContent(index))
        varied_value = float(varied.GetBinContent(index))
        abs_diff = abs(varied_value - nominal_value)
        rel_diff = abs_diff / abs(nominal_value) if nominal_value else (0.0 if varied_value == 0.0 else float("inf"))
        if abs_diff > max_abs:
            max_abs = abs_diff
            max_rel = rel_diff
            max_bin = index
    return max_abs, max_rel, max_bin


def contents(hist: object, bins: range) -> list[float]:
    return [float(hist.GetBinContent(index)) for index in bins]


def report(result: dict, fmt: str, header: list[str]) -> None:
    if fmt == "json":
        print(json.dumps(result, indent=1))
        return
    for line in header:
        print(line)
    for label in ("up", "down"):
        r = result[label]
        print(f"{label}: effect={r['effect']} integral_rel_change={r['integral_rel_change']} "
              f"shape_max_abs_change={r['shape_max_abs_change']} migration_fraction={r['migration_fraction']}")
        print(f"{label}: {r['note']}")
    for w in result["warnings"]:
        print(f"warning: {w}")
    print(f"sensitivity: {result['sensitivity']}")


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.json:
        doc = json.loads(args.json.read_text(encoding="utf-8"))
        result = assess(doc["nominal"], doc["up"], doc["down"], args.tolerance)
        report(result, args.format, [f"file: {args.json}"])
        return 0
    if not args.input.exists():
        raise FileNotFoundError(f"ROOT file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError as exc:
        raise SystemExit("PyROOT is required to check ROOT histogram systematics") from exc

    root_file = ROOT.TFile.Open(str(args.input), "READ")
    try:
        if not root_file or root_file.IsZombie():
            raise OSError(f"Could not open ROOT file: {args.input}")
        nominal = get_hist(root_file, args.nominal)
        up = get_hist(root_file, args.up)
        down = get_hist(root_file, args.down)

        check_compatible(nominal, up, "up")
        check_compatible(nominal, down, "down")
        bins = bin_range(nominal, args.include_flow)

        header = [f"file: {args.input}", f"nominal: {args.nominal}", f"up: {args.up}", f"down: {args.down}",
                  f"nominal integral: {nominal.Integral()}", f"up integral: {up.Integral()}", f"down integral: {down.Integral()}"]
        for label, hist in (("up", up), ("down", down)):
            max_abs, max_rel, max_bin = summarize_difference(nominal, hist, bins)
            header += [f"{label} max absolute bin difference: {max_abs}", f"{label} max relative bin difference: {max_rel}",
                       f"{label} bin with max difference: {max_bin}"]
        result = assess(contents(nominal, bins), contents(up, bins), contents(down, bins), args.tolerance)
        report(result, args.format, header)
    finally:
        if root_file:
            root_file.Close()
    return 0


if __name__ == "__main__":
    import sys as _sys
    try:
        raise SystemExit(main())
    except OSError as _exc:  # a missing or unreadable input: one line, no traceback
        print(f"check_systematic_variations.py: error: {_exc}", file=_sys.stderr)
        raise SystemExit(2)
