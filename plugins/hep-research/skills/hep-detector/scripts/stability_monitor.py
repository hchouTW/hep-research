#!/usr/bin/env python3
"""Stability of a calibration or performance quantity over time: trends, change points, CUSUM, periods out of
tolerance, and proposed era boundaries (D11).

Purpose: decide from a time series (one value with its uncertainty per run, period or day) whether a detector
quantity is stable, drifts, or steps, with thresholds calibrated to a declared false-alarm rate. See "Monitoring
stability over time" in <plugin root>/skills/hep-detector/references/calibration-and-alignment.md. The statistics
are in <plugin root>/core/stats/change_point.py.

What it does:
- trends: weighted constant and linear fits with chi2 and p-value (a constant fit with a bad chi2 means the quoted
  uncertainties are too small or the quantity moves);
- change points: binary segmentation on the step statistic z_k = |m2 - m1| / sqrt(1/W1 + 1/W2), threshold calibrated
  by --toys toys (seeded) so that P(any change point | no change) = --false-alarm; segments shorter than
  --min-segment points are not split off; a piecewise-constant fit over the change points;
- CUSUM (two-sided, allowance --cusum-k in units of sigma; mu0 from the first --reference-points points), its
  threshold calibrated by toys to the same false-alarm rate: the first alarm;
- out of tolerance (only with --reference and --tolerance): points with |value - reference| > tolerance;
- proposed era boundaries: one per change point, kind "calibration", with the step and the times around it. They
  are proposals: the tool never writes them into a measurement spec.
Assumptions: independent Gaussian uncertainties as supplied (a uniform --sigma, or --error-column); points ordered by
time. If the uncertainties are underestimated the false-alarm rate is higher than declared.

Input CSV (lines starting with # skipped): --time-column, --value-column, and --error-column or --sigma; optional
--period-column (reported with the boundaries).
Output: JSON with status, status_label (--status, default unvalidated), inputs, defaults_used, warnings, trends,
calibration, change_points, piecewise, cusum, out_of_tolerance, proposed_era_boundaries, proposal_note and
"label": "[General method]". Exit codes: 0 ok; 2 invalid input or arguments (status rejected).
Run: python3 <plugin root>/skills/hep-detector/scripts/stability_monitor.py series.csv --time-column t \\
         --value-column gain --error-column gain_err --false-alarm 0.01 --toys 2000 --seed 1
Standard library only.
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats import change_point as cp  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

PROPOSAL_NOTE = ("proposed era boundaries are diagnostics for the analyst: they are never written into a spec "
                 "automatically; an accepted boundary is entered by hand with its source")


class InputError(ValueError):
    """Invalid input or arguments (status rejected, exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(exit_code("rejected"), f"{self.prog}: error: {message}\n")


def _num(text, what):
    try:
        v = float(text)
    except (TypeError, ValueError):
        raise InputError(f"{what}: {text!r} is not a number") from None
    if not math.isfinite(v):
        raise InputError(f"{what}: {text!r} is not finite")
    return v


def read_series(args):
    cols = [args.time_column, args.value_column] + [c for c in (args.error_column, args.period_column) if c]
    try:
        with open(args.series, newline="", encoding="utf-8") as fh:
            lines = [ln for ln in fh if not ln.startswith("#")]
    except OSError as exc:
        raise InputError(f"cannot read {args.series}: {exc}") from None
    reader = csv.DictReader(lines)
    missing = [c for c in cols if c not in (reader.fieldnames or [])]
    if missing:
        raise InputError(f"missing column(s) {missing}; found {reader.fieldnames}")
    t, y, s, per = [], [], [], []
    for r in reader:
        t.append(_num(r[args.time_column], args.time_column))
        y.append(_num(r[args.value_column], args.value_column))
        s.append(_num(r[args.error_column], args.error_column) if args.error_column else args.sigma)
        per.append(r[args.period_column] if args.period_column else None)
    if len(y) < 3:
        raise InputError("need at least 3 points")
    if any(b < a for a, b in zip(t, t[1:])):
        raise InputError("points must be ordered by time")
    if min(s) <= 0:
        raise InputError("uncertainties must be > 0")
    return t, y, s, per


def run(args, warnings):
    if args.false_alarm is None:
        raise InputError("--false-alarm is required (the declared false-alarm rate of the whole series)")
    if (args.error_column is None) == (args.sigma is None):
        raise InputError("give exactly one of --error-column or --sigma")
    if (args.reference is None) != (args.tolerance is None):
        raise InputError("--reference and --tolerance go together")
    if args.tolerance is not None and args.tolerance <= 0:
        raise InputError("--tolerance must be > 0")
    t, y, s, per = read_series(args)
    n = len(y)
    if 2 * args.min_segment > n:
        raise InputError("--min-segment is too large for the series")
    ref_pts = args.reference_points if args.reference_points is not None else max(args.min_segment, n // 5, 2)
    if not 1 <= ref_pts < n:
        raise InputError("--reference-points must be in [1, n)")
    try:
        trends = {m: cp.weighted_fit(t, y, s, m) for m in ("constant", "linear")}
        cal_seg = cp.calibrate_threshold(s, args.false_alarm, args.toys, args.seed, "segmentation", args.min_segment)
        cal_cus = cp.calibrate_threshold(s, args.false_alarm, args.toys, args.seed + 1, "cusum",
                                         cusum_k=args.cusum_k, reference_points=ref_pts)
        changes = cp.binary_segmentation(y, s, cal_seg["threshold"], args.min_segment)
        piecewise = cp.piecewise_constant(y, s, [c["index"] for c in changes])
        alarm = cp.cusum_first_alarm(y, s, args.cusum_k, cal_cus["threshold"], reference_points=ref_pts)
    except cp.ChangePointError as exc:
        raise InputError(str(exc)) from None
    if trends["constant"]["p_value"] is not None and trends["constant"]["p_value"] < 1e-3 and not changes:
        warnings.append("the constant fit is poor (p < 1e-3) but no step was found: a drift, or uncertainties "
                        "that are too small (then the false-alarm rate is higher than declared)")
    proposals = []
    for c in changes:
        k = c["index"]
        proposals.append({"kind": "calibration", "index": k, "first_period": _period(per[k]),
                          "last_period_before": _period(per[k - 1]), "time_before": t[k - 1], "time_after": t[k],
                          "step": c["step"], "z": c["z"]})
    out_tol = []
    if args.reference is not None:
        for i, (ti, yi, si) in enumerate(zip(t, y, s)):
            if abs(yi - args.reference) > args.tolerance:
                out_tol.append({"index": i, "period": _period(per[i]), "time": ti, "value": yi, "error": si,
                                "deviation": yi - args.reference})
    else:
        warnings.append("no --reference/--tolerance: out-of-tolerance periods not evaluated")
    return {"points": n, "trends": trends, "calibration": {"segmentation": cal_seg, "cusum": cal_cus},
            "change_points": changes, "piecewise": piecewise,
            "cusum": {"k": args.cusum_k, "reference_points": ref_pts, "threshold": cal_cus["threshold"],
                      "first_alarm_index": alarm, "first_alarm_period": _period(per[alarm]) if alarm is not None else None},
            "out_of_tolerance": out_tol, "proposed_era_boundaries": proposals, "proposal_note": PROPOSAL_NOTE}


def _period(p):
    if p is None:
        return None
    try:
        v = float(p)
        return int(v) if v.is_integer() else p
    except ValueError:
        return p


def main(argv=None):
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("series", help="CSV of the time series")
    ap.add_argument("--time-column", required=True)
    ap.add_argument("--value-column", required=True)
    ap.add_argument("--error-column", help="column of the per-point uncertainty")
    ap.add_argument("--sigma", type=float, help="one uncertainty for every point")
    ap.add_argument("--period-column", help="period or run identifier, reported with the boundaries")
    ap.add_argument("--false-alarm", type=float, help="declared false-alarm rate of the whole series (required)")
    ap.add_argument("--toys", type=int, default=2000, help="toys for the threshold calibration (default 2000)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--min-segment", type=int, default=1, help="shortest segment split off (default 1 point)")
    ap.add_argument("--cusum-k", type=float, default=0.5, help="CUSUM allowance in sigma (default 0.5)")
    ap.add_argument("--reference-points", type=int, help="points that set the CUSUM reference (default max(min-segment, n/5, 2))")
    ap.add_argument("--reference", type=float, help="reference value for the tolerance check")
    ap.add_argument("--tolerance", type=float, help="allowed |value - reference|")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {a.split("=")[0] for a in (sys.argv[1:] if argv is None else argv) if a.startswith("--")}
    defaults = [k for k in ("--status", "--toys", "--min-segment", "--cusum-k", "--reference-points") if k not in given]
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    warnings = []
    try:
        res = run(args, warnings)
        out = {"status": "ok", "status_label": args.status, "label": cp.LABEL, "inputs": inputs,
               "defaults_used": defaults, "warnings": warnings, **res}
    except InputError as exc:
        out = {"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)}
    try:
        text = json.dumps(out, indent=2, allow_nan=False)
    except ValueError:
        out = {"status": "rejected", "status_label": args.status, "error": "a result is not finite"}
        text = json.dumps(out, indent=2)
    print(text)
    return exit_code(out["status"])


if __name__ == "__main__":
    raise SystemExit(main())
