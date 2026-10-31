#!/usr/bin/env python3
"""Compare nominal and Up/Down systematic histograms and classify each variation's effect.

The effect of a variation is classified per histogram as `none`, `normalization`, `shape` or `mixed`
from the integral change and the change of the unit-normalized shape. An unchanged integral is NOT
evidence that the variation failed to propagate: a shape-only (migration) variation keeps the integral.
Only `none` (no bin changed beyond tolerance) asks the analyst to confirm propagation, and even then the
right check is the variation's effect on the final result (refit / sensitivity), which this script cannot see.

Inputs: a ROOT file (`--input`, needs PyROOT; bin errors give per-sample variances) or a JSON file (`--json`) of the
form {"nominal": [...], "up": [...], "down": [...]} with matching bin contents (no PyROOT needed), optionally with
per-sample variances "nominal_sumw2", "up_sumw2", "down_sumw2", or with the variance of each difference
"up_diff_sumw2", "down_diff_sumw2" (not both kinds), and "underflow"/"overflow" objects
{"nominal": x, "up": y, "down": z} that --include-flow adds as bins.

Statistical test: the effect comes from a normalization pull z = (sum varied - sum nominal) / sqrt(sum var) and a
chi2 test of the unit-normalized shapes (ndf = bins - 1), each significant at --alpha (default 0.01), where var is the
per-bin variance of the difference. A variation computed from the same events as the nominal (a scale or resolution
variation) is correlated with it, so the sum of the two samples' variances overstates var and hides real changes. The
test therefore uses: the given difference variances (up_diff_sumw2, down_diff_sumw2), or --stat-unc REL (the relative
uncertainty of the difference), or the per-sample variances (sumw2 or ROOT bin errors) only with --independent
(separately generated samples). Otherwise no statistical test is made, the output says why, and the effect comes from
the relative tolerance. The direction of a variation (which one is up)
cannot be inferred from integrals: establish it from the payloads and the generation code.
The report is JSON by default (`--format text` for a readable one) and carries `status` (--status, default
unvalidated; one of the core artifact_statuses).
Exit codes: 0 ok; 2 usage or invalid input (NaN or inf bin, malformed or incomplete JSON, missing file); 3 incomplete
(PyROOT needed for --input but not installed).
"""
from __future__ import annotations
if __name__ == "__main__":  # hep-research interpreter guard (tests/tools/test_python_compat.py)
    import sys as _sys
    from pathlib import Path as _Path
    _sys.dont_write_bytecode = True
    _root = str(_Path(__file__).resolve().parents[3])
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    try:
        from core.interpreter_guard import guard as _guard
    except ImportError:  # copied outside the plugin
        pass
    else:
        _guard()

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from core.stats.statistical_toys import chi2_sf  # noqa: E402

DEFAULT_TOL = 1e-6  # relative tolerance on the integral and on the normalized shape (no-uncertainty fallback)
DEFAULT_ALPHA = 0.01  # significance level of the normalization pull and the shape chi2
DIRECTION_NOTE = ("the direction of a variation cannot be inferred from integrals: establish which is up from the "
                  "payloads and the generation code")
STATUSES = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "observed", "user-supplied",
            "validated-in-scope", "projection", "outside-validated-range")  # contracts/vocab/core.json artifact_statuses


class InputError(ValueError):
    """Invalid or malformed input (exit 2)."""


def _reject_constant(token):
    raise InputError(f"non-finite number {token} in the input")


def _bins(doc, key):
    values = doc.get(key) if isinstance(doc, dict) else None
    if not isinstance(values, list) or not values:
        raise InputError(f"JSON input needs a non-empty list '{key}' of bin contents")
    for i, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float('inf'), float('-inf')):
            raise InputError(f"'{key}' bin {i} must be a finite number, got {v!r}")
    return [float(v) for v in values]


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", type=Path, help="ROOT file (requires PyROOT)")
    src.add_argument("--json", type=Path, help='JSON file {"nominal": [...], "up": [...], "down": [...]} of bin contents')
    parser.add_argument("--nominal", help="Nominal histogram path (ROOT input)")
    parser.add_argument("--up", help="Up-variation histogram path (ROOT input)")
    parser.add_argument("--down", help="Down-variation histogram path (ROOT input)")
    parser.add_argument("--include-flow", action="store_true", help="Include underflow and overflow bins")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOL,
                        help="relative tolerance without uncertainties (default %(default)g)")
    parser.add_argument("--stat-unc", type=float, default=None, dest="stat_unc",
                        help="relative per-bin statistical uncertainty of the difference (JSON without sumw2)")
    parser.add_argument("--independent", action="store_true",
                        help="the variations are separate samples, statistically independent of the nominal: combine "
                             "the per-sample variances (sumw2 or ROOT bin errors) for the test")
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA, help="test level (default %(default)g)")
    parser.add_argument("--format", choices=("text", "json"), default="json")
    parser.add_argument("--status", choices=STATUSES, default="unvalidated",
                        help="status label of the inputs, echoed as status (default unvalidated)")
    args = parser.parse_args(argv)
    if args.input and not (args.nominal and args.up and args.down):
        parser.error("--input needs --nominal, --up and --down")
    if not (args.tolerance == args.tolerance and 0 < args.tolerance < float('inf')):
        parser.error("--tolerance must be finite and greater than zero")
    if not (args.alpha == args.alpha and 0 < args.alpha < 1):
        parser.error("--alpha must lie in (0, 1)")
    if args.stat_unc is not None and not (args.stat_unc == args.stat_unc and 0 < args.stat_unc < float('inf')):
        parser.error("--stat-unc must be finite and greater than zero")
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
    note = notes[effect]
    if effect == "none" and bin_changed:
        note = ("some bins differ beyond tolerance, but neither the integral nor the normalized shape does: confirm "
                "propagation, then check the effect on the final result")
    return {"effect": effect, "integral_rel_change": integral, "shape_max_abs_change": shape,
            "migration_fraction": migration, "bins_changed": bin_changed, "note": note}


def stat_test(nominal, varied, variance, alpha: float = DEFAULT_ALPHA) -> dict:
    """Normalization pull and shape chi2 of `varied` against `nominal` given the per-bin variance of the difference."""
    if len(variance) != len(nominal) or any(not (math.isfinite(v) and v >= 0) for v in variance):
        raise ValueError("variances must be finite, nonnegative and one per bin")
    n_sum, v_sum, var_sum = math.fsum(nominal), math.fsum(varied), math.fsum(variance)
    if var_sum <= 0 or n_sum == 0 or v_sum == 0:
        raise ValueError("the statistical test needs positive variances and nonzero integrals")
    z = (v_sum - n_sum) / math.sqrt(var_sum)
    scale = n_sum / v_sum
    terms = [(v * scale - n) ** 2 / var for n, v, var in zip(nominal, varied, variance) if var > 0]
    ndf = max(len(terms) - 1, 1)
    chi2 = math.fsum(terms)
    p_shape = chi2_sf(chi2, ndf)
    p_norm = math.erfc(abs(z) / math.sqrt(2.0))
    norm_sig, shape_sig = p_norm < alpha, p_shape < alpha
    effect = ("mixed" if norm_sig and shape_sig else "normalization" if norm_sig
              else "shape" if shape_sig else "none")
    return {"effect": effect, "normalization_pull": z, "normalization_p_value": p_norm, "shape_chi2": chi2,
            "shape_ndf": ndf, "shape_p_value": p_shape, "alpha": alpha}


NO_TEST_CORRELATED = ("not made: per-sample variances (sumw2 or ROOT bin errors) add up to the variance of the difference "
                      "only for independent samples; a variation made from the same events is correlated with the "
                      "nominal. Give up_diff_sumw2/down_diff_sumw2 or --stat-unc, or pass --independent for separately "
                      "generated samples")


def assess(nominal, up, down, tol: float = DEFAULT_TOL, variances=None, alpha: float = DEFAULT_ALPHA,
           no_test: str | None = None) -> dict:
    """variances: None (tolerance only) or {"up": [...], "down": [...]} per-bin variances of each difference;
    no_test: the reason reported when no statistical test is made."""
    out = {"up": classify_variation(nominal, up, tol), "down": classify_variation(nominal, down, tol)}
    if variances is not None:
        for label, varied in (("up", up), ("down", down)):
            test = stat_test(nominal, varied, variances[label], alpha)
            out[label]["tolerance_effect"] = out[label]["effect"]
            out[label]["effect"] = test.pop("effect")
            out[label]["statistical_test"] = test
            if out[label]["effect"] == "none" and out[label]["bins_changed"]:
                out[label]["note"] = ("bins differ, but within their statistical uncertainty: no significant effect at "
                                      f"alpha = {alpha:g}; confirm propagation, then check the effect on the result")
    else:
        out["statistical_test"] = no_test or "not made: no per-bin uncertainties (give sumw2, ROOT bin errors or --stat-unc)"
    warnings = []
    if out["up"]["effect"] == "none" and out["down"]["effect"] == "none":
        if (out["up"]["bins_changed"] or out["down"]["bins_changed"]) and variances is not None:
            warnings.append(f"bins differ, but neither variation is significant at alpha = {alpha:g}: confirm the "
                            "variances describe the difference, then judge by the effect on the result")
        elif out["up"]["bins_changed"] or out["down"]["bins_changed"]:
            warnings.append("bins differ, but neither variation changes the integral or the normalized shape beyond "
                            "the tolerance (no statistical test made): confirm propagation, then judge by the effect on "
                            "the result")
        else:
            warnings.append("neither variation changes this histogram: confirm propagation, then judge by the effect on "
                            "the result")
    iu, idn = out["up"]["integral_rel_change"], out["down"]["integral_rel_change"]
    if iu is not None and idn is not None and iu * idn > 0 and abs(iu) > tol and abs(idn) > tol:
        warnings.append("up and down move the integral in the same direction: one-sided or possibly swapped/mislabelled variation")
    out["warnings"] = warnings
    out["sensitivity"] = "not assessed here: evaluate the variation's effect on the fitted result (refit or impact)"
    out["direction"] = DIRECTION_NOTE
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
    print(f"status: {result['status']}")
    for line in header:
        print(line)
    for label in ("up", "down"):
        r = result[label]
        print(f"{label}: effect={r['effect']} integral_rel_change={r['integral_rel_change']} "
              f"shape_max_abs_change={r['shape_max_abs_change']} migration_fraction={r['migration_fraction']}")
        print(f"{label}: {r['note']}")
    for w in result["warnings"]:
        print(f"warning: {w}")
    print(f"direction: {result['direction']}")
    print(f"sensitivity: {result['sensitivity']}")


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.json:
        try:
            doc = json.loads(args.json.read_text(encoding="utf-8"), parse_constant=_reject_constant)
        except json.JSONDecodeError as exc:
            raise InputError(f"malformed JSON in {args.json}: {exc}") from None
        nominal, up, down = (_bins(doc, k) for k in ("nominal", "up", "down"))
        sumw2 = {k: _bins(doc, f"{k}_sumw2") for k in ("nominal", "up", "down") if f"{k}_sumw2" in doc}
        diff = {k: _bins(doc, f"{k}_diff_sumw2") for k in ("up", "down") if f"{k}_diff_sumw2" in doc}
        if diff and sumw2:
            raise InputError("give per-sample sumw2 or difference variances (up_diff_sumw2, down_diff_sumw2), not both")
        if args.include_flow:
            flow = [doc.get("underflow"), doc.get("overflow")]
            if not all(isinstance(f, dict) for f in flow):
                raise InputError("--include-flow needs 'underflow' and 'overflow' objects {nominal, up, down} in the JSON")
            nominal, up, down = ([_bins({"x": [flow[0].get(k)]}, "x")[0]] + h + [_bins({"x": [flow[1].get(k)]}, "x")[0]]
                                 for k, h in (("nominal", nominal), ("up", up), ("down", down)))
            if sumw2 or diff:
                raise InputError("give flow-bin variances inside the sumw2 arrays only without --include-flow")
        variances, no_test = None, None
        if diff:
            if set(diff) != {"up", "down"}:
                raise InputError("give up_diff_sumw2 and down_diff_sumw2 together")
            variances = diff
        elif sumw2:
            if set(sumw2) != {"nominal", "up", "down"}:
                raise InputError("give nominal_sumw2, up_sumw2 and down_sumw2 together")
            if args.independent:
                variances = {k: [a + b for a, b in zip(sumw2["nominal"], sumw2[k])] for k in ("up", "down")}
            else:
                no_test = NO_TEST_CORRELATED
        elif args.stat_unc is not None:
            variances = {k: [(args.stat_unc * n) ** 2 for n in nominal] for k in ("up", "down")}
        try:
            result = assess(nominal, up, down, args.tolerance, variances, args.alpha, no_test)
        except ValueError as exc:
            raise InputError(str(exc)) from None
        report({"status": args.status, **result}, args.format, [f"file: {args.json}"])
        return 0
    if not args.input.exists():
        raise FileNotFoundError(f"ROOT file does not exist: {args.input}")

    try:
        import ROOT
    except ImportError:
        print("check_systematic_variations.py: incomplete: PyROOT is required for --input (use --json)", file=sys.stderr)
        return 3

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
        var = {lbl: [float(nominal.GetBinError(i)) ** 2 + float(h.GetBinError(i)) ** 2 for i in bins]
               for lbl, h in (("up", up), ("down", down))}
        has_errors = any(v > 0 for v in var["up"])
        result = assess(contents(nominal, bins), contents(up, bins), contents(down, bins), args.tolerance,
                        var if has_errors and args.independent else None, args.alpha,
                        NO_TEST_CORRELATED if has_errors and not args.independent else None)
        report({"status": args.status, **result}, args.format, header)
    finally:
        if root_file:
            root_file.Close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, InputError, KeyError, TypeError, ValueError) as _exc:  # bad input: one line, no traceback
        print(f"check_systematic_variations.py: error: {_exc}", file=sys.stderr)
        raise SystemExit(2)
