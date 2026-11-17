#!/usr/bin/env python3
"""Charge-sign confusion rate per bin: template fit, control sample, or a Gaussian-core lower bound (D3).

Purpose: the probability that a particle of one charge sign is reconstructed with the other, per bin of rigidity (or
momentum), measured in a way that can be validated (see
<plugin root>/skills/hep-detector/references/charge-confusion.md).

Modes:
- template: per bin, the data histogram of a sign discriminant is fitted with right-sign and wrong-sign templates
  (and an optional background template) by the extended Poisson likelihood with the full Barlow-Beeston treatment of
  the template statistics (core/stats/template_fit.py; at most 6 templates and 60 discriminant bins). Rate
  r = Y_wrong / (Y_right + Y_wrong) at the maximum of the profile likelihood in r (a scan over r, then a polishing fit),
  its 68% interval from the profile likelihood (rate_error its half-width; rate_error_hessian from the fit covariance);
- control: a sample of known true sign (CSV); per bin k wrong-sign of n events, the Clopper-Pearson interval
  (core/stats/tail_estimation.py), and with --mc a second sample of the same one true sign (else refused), the data/MC
  scale factor r_data / r_mc with an approximate (delta-method) error. Weights must be integer frequency weights:
  non-integer weights are refused (hep-statistics owns weighted binomial intervals);
- gaussian-core: Phi(-|1/R| / sigma(1/R)) at the bin edges from a Gaussian curvature core. It ignores the non-Gaussian
  tails that dominate real confusion, so it is a lower-bound reference labelled "not an estimate"; no estimate and no
  sign rates are output from it.
Output: per-bin rates and, for template and control, "sign_rates" in the format species_response.py from-rates reads:
{"edges": [...], "variable": ..., "rates": [{"true": SIGN, "reco": OTHER SIGN, "rate": [...], "rate_error": [...]}]}.
Input: template JSON {"edges": [...], "true_sign": "negative"|"positive", "variable"?: TEXT,
  "bins": [{"data": [...], "templates": {"right": [...], "wrong": [...], "background"?: [...]}, "mc_events"?: {...}}]}.
Usage:
  charge_confusion_rate.py template --input T.json [--status LABEL]
  charge_confusion_rate.py control --data CTRL.csv [--mc CTRL_MC.csv] --edges E ... --bin-column C
      --true-sign-column C --reco-sign-column C [--weight-column W] [--cl 0.6827] [--status LABEL]
  charge_confusion_rate.py gaussian-core --edges E ... --sigma-inv-r S ... [--status LABEL]
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, warnings, bins, sign_rates. Template
  status per bin: fit_outcome not-converged or infeasible gives failed and a warning naming the bin;
  converged-at-boundary or covariance-warning alone gives ok and a warning naming the bin; a rate that is not
  identified (its profile interval reaches r = 1, or a background template is compatible in shape with the right-sign
  template within the template statistics, chi2 p >= 0.01) gives failed and a warning naming the bin, and its
  sign_rates entries are null.
Exit codes: 0 ok; 1 a template bin failed (see the status rule); 2 bad input. Standard library only.
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
import csv
import json
import math
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))
from core.stats import template_fit  # noqa: E402
from core.stats.statistical_toys import chi2_sf  # noqa: E402
from core.stats.tail_estimation import clopper_pearson  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
CL68 = 0.6826894921370859
SIGNS = ("positive", "negative")


class InputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def _other(sign: str) -> str:
    if sign not in SIGNS:
        raise InputError(f"sign must be one of {SIGNS}, got {sign!r}")
    return SIGNS[1 - SIGNS.index(sign)]


def _edges(values) -> list[float]:
    e = [float(v) for v in values]
    if len(e) < 2 or any(not math.isfinite(v) for v in e) or any(b <= a for a, b in zip(e, e[1:])):
        raise InputError("edges must be at least two finite, strictly increasing numbers")
    return e


SCAN_R = [0.0] + [10.0 ** (-6 + 0.25 * t) for t in range(25)]  # rate grid: 0, then 1e-6 to 1 in quarter decades
START_AGREE = 0.5  # ln L by which another fit may beat the rate scan before the outcome is not-converged
DEGENERATE_P = 0.01  # a background shape compatible with the right-sign one at p >= this is degenerate


def _profile_at(observed, m, mc, i: int, j: int, r: float, start) -> tuple[float, list]:
    """-ln L profiled at fixed r = y_j / (y_i + y_j): the total N = y_i + y_j and the other yields by Nelder-Mead
    (restarted once from its end); returns (-ln L, yields). `start` is [N, other yields...]."""
    others = [k for k in range(len(m)) if k not in (i, j)]

    def yields(x):
        yy = [0.0] * len(m)
        yy[i], yy[j] = x[0] * (1 - r), x[0] * r
        for k, v in zip(others, x[1:]):
            yy[k] = v
        return yy

    def f(x):
        if x[0] <= 0 or any(v < 0 for v in x[1:]):
            return 1e300
        return -template_fit._ll_bb(observed, m, mc, yields(x))
    x, val = template_fit._nelder_mead(f, list(start), [max(0.05 * v, 1.0) for v in start])
    x, val = template_fit._nelder_mead(f, x, [max(0.01 * v, 1.0) for v in x])
    return val, yields(x)


def _bb_maximum(observed, m, mc, i: int, j: int):
    """Barlow-Beeston maximum found through the profile likelihood in the rate (PDG eqs. 40.9 and 40.41).

    A Nelder-Mead fit of all yields stops on a relative tolerance (1e-10 (1 + |ln L|), about 1e-3 at ln L ~ 1e7 for
    1e6 events), so one started from the naive fit, which often ends with the wrong-sign yield at 0, can stop at that
    boundary far below the maximum. Instead the profile -ln L is evaluated on the grid SCAN_R, refined by golden-section
    search between the neighbours of the best grid point, and the yields there are polished by a full fit. The deepest
    of the scan, the polished fit and the fit from the naive start is kept; if a fit beats the scan by more than
    START_AGREE, the scan missed the maximum and the outcome is not-converged.
    Returns (yields, covariance, diagnostics).
    """
    k = len(m)
    total = max(sum(observed), 1.0)
    y0 = template_fit._fit_yields_full(observed, m, mc, "naive", [max(total / k, 1.0)] * k)[0]
    y_old, _, ll_old, _ = template_fit._fit_yields_full(observed, m, mc, "bb", [max(v, 1.0) for v in y0])
    start = [max(y_old[i] + y_old[j], 1.0)] + [max(y_old[t], 1.0) for t in range(k) if t not in (i, j)]
    grid = [_profile_at(observed, m, mc, i, j, r, start) for r in SCAN_R]
    b = min(range(len(SCAN_R)), key=lambda t: grid[t][0])
    lo, hi = SCAN_R[max(b - 1, 0)], SCAN_R[min(b + 1, len(SCAN_R) - 1)]
    yb = grid[b][1]
    start = [yb[i] + yb[j]] + [yb[t] for t in range(k) if t not in (i, j)]
    g = (math.sqrt(5.0) - 1.0) / 2.0
    c, d = hi - g * (hi - lo), lo + g * (hi - lo)
    fc, fd = _profile_at(observed, m, mc, i, j, c, start), _profile_at(observed, m, mc, i, j, d, start)
    for _ in range(40):
        if fc[0] < fd[0]:
            hi, d, fd = d, c, fc
            c = hi - g * (hi - lo)
            fc = _profile_at(observed, m, mc, i, j, c, start)
        else:
            lo, c, fc = c, d, fd
            d = lo + g * (hi - lo)
            fd = _profile_at(observed, m, mc, i, j, d, start)
    nll_scan, y_scan = min([grid[b], fc, fd], key=lambda t: t[0])
    y_pol, _, ll_pol, d_pol = template_fit._fit_yields_full(observed, m, mc, "bb", [max(v, 1e-6) for v in y_scan])
    cands = [(nll_scan, y_scan), (-ll_pol, y_pol), (-ll_old, y_old)]
    nll, y = min(cands, key=lambda t: t[0])
    found = nll_scan - nll <= START_AGREE
    cov = template_fit._hessian_cov(lambda z: template_fit._ll_bb(observed, m, mc, [max(v, 1e-9) for v in z]), y)
    info = {"converged": bool(d_pol["converged"]) and found,
            "termination": "rate-scan" if found else "rate-scan-missed-maximum"}
    return y, cov, template_fit._diagnostics([info], -nll, cov, y, [])


def _degenerate_backgrounds(tnames, m, i: int, j: int) -> list[str]:
    """Background templates whose shape is compatible with the right-sign template within the template statistics:
    Pearson chi2 of the two-sample (2 x bins) homogeneity table, p >= DEGENERATE_P. With such a template the data
    cannot separate it from the right-sign yield, so the rate is not identified."""
    out = []
    for t in range(len(m)):
        if t in (i, j):
            continue
        cols = [(a, b) for a, b in zip(m[i], m[t]) if a + b > 0]
        sa, sb = sum(a for a, _ in cols), sum(b for _, b in cols)
        if len(cols) < 2 or sa <= 0 or sb <= 0:
            continue
        chi2 = sum((sb * a - sa * b) ** 2 / (a + b) for a, b in cols) / (sa * sb)
        p = chi2_sf(chi2, len(cols) - 1)
        if p >= DEGENERATE_P:
            out.append(f"the background template '{tnames[t]}' is compatible in shape with the right-sign template "
                       f"(chi2 = {chi2:.3g} for {len(cols) - 1} degrees of freedom, p = {p:.3g} >= {DEGENERATE_P})")
    return out


def template_rate(bin_doc: dict, names: dict) -> dict:
    """Fit one bin; names maps 'right'/'wrong' to template names. not_identified gives the reasons the rate is not
    identified (its profile interval reaches r = 1, or a background template is degenerate with the right-sign one)."""
    try:
        tnames, data, m, mc = template_fit._load(bin_doc)
    except template_fit.ToyError as exc:
        raise InputError(str(exc)) from None
    for role in ("right", "wrong"):
        if names[role] not in tnames:
            raise InputError(f"template '{names[role]}' missing")
    i, j = tnames.index(names["right"]), tnames.index(names["wrong"])
    y, cov, diag = _bb_maximum(data, m, mc, i, j)
    yr, yw = y[i], y[j]
    tot = yr + yw
    if tot <= 0:
        raise InputError("the fitted right- plus wrong-sign yield is zero")
    rate = yw / tot
    err = None
    if cov is not None:
        # r = yw / (yr + yw): dr/dyr = -yw/tot^2, dr/dyw = yr/tot^2
        g = {i: -yw / tot ** 2, j: yr / tot ** 2}
        var = sum(g[a] * g[b] * cov[a][b] for a in g for b in g)
        err = math.sqrt(var) if var > 0 else None
    lo, hi = profile_interval(data, m, mc, y, i, j)
    why = (["its 68% profile interval reaches r = 1"] if hi >= 1.0 else []) + _degenerate_backgrounds(tnames, m, i, j)
    return {"rate": rate, "rate_error_hessian": err, "interval_68": [lo, hi], "rate_error": (hi - lo) / 2.0,
            "interval_method": "profile likelihood in the rate, -2 Delta ln L = 1 (Barlow-Beeston), lower end at 0 "
                               "when the boundary is inside",
            "yields": {n: y[k] for k, n in enumerate(tnames)}, "fit_outcome": diag["outcome"],
            "not_identified": "; ".join(why) or None}


def profile_interval(data, m, mc, y, i: int, j: int) -> tuple[float, float]:
    """68% profile-likelihood interval of r = y_j / (y_i + y_j) about the maximum y: for fixed r the total
    N = y_i + y_j and the other yields are profiled (_profile_at)."""
    others = [k for k in range(len(y)) if k not in (i, j)]

    def nll_at(r: float, start):
        return _profile_at(data, m, mc, i, j, r, start)

    n0 = y[i] + y[j]
    start = [n0] + [y[k] for k in others]
    r_hat = y[j] / n0
    best = min(-template_fit._ll_bb(data, m, mc, y), nll_at(r_hat, start)[0])  # the deeper of the two minima

    def excess(r):
        return 2.0 * (nll_at(r, start)[0] - best) - 1.0

    def root(a, b):  # excess(a) < 0 <= excess(b)
        for _ in range(40):
            c = 0.5 * (a + b)
            if excess(c) < 0:
                a = c
            else:
                b = c
        return 0.5 * (a + b)
    lo = 0.0 if excess(0.0) < 0 else _bisect_down(excess, r_hat)
    # the upper end is tested just below r = 1: at r = 1 the right-sign yield is exactly 0 and template_fit._ll_bb
    # drops that template's terms, so ln L there is not the limit r -> 1
    top = 1.0 - 1e-12
    hi = 1.0 if excess(top) < 0 else root(r_hat, top)
    return lo, hi


def _bisect_down(excess, r_hat: float) -> float:
    """lower root of excess in [0, r_hat] (excess(0) >= 0 > excess(r_hat))."""
    a, b = 0.0, r_hat  # excess(a) >= 0, excess(b) < 0
    for _ in range(40):
        c = 0.5 * (a + b)
        if excess(c) >= 0:
            a = c
        else:
            b = c
    return 0.5 * (a + b)


def run_template(doc: dict) -> tuple[dict, str, list]:
    edges = _edges(doc.get("edges", []))
    sign = doc.get("true_sign")
    other = _other(sign)
    bins = doc.get("bins")
    if not isinstance(bins, list) or len(bins) != len(edges) - 1:
        raise InputError(f"bins must list {len(edges) - 1} entries (one per pair of edges)")
    rows, status, warnings = [], "ok", []
    for k, b in enumerate(bins):
        row = template_rate(b, {"right": "right", "wrong": "wrong"})
        row["bin"] = [edges[k], edges[k + 1]]
        outcome = row["fit_outcome"]
        if outcome in template_fit.FAILED_OUTCOMES:
            status = "failed"
            warnings.append(f"bin {k + 1}: the fit is {outcome}; its rate is not a result")
        elif outcome != "converged":  # converged-at-boundary or covariance-warning, as template_fit._overall
            warnings.append(f"bin {k + 1}: the fit is {outcome}; rate_error_hessian is unreliable there, use the "
                            "profile interval")
        if row.get("not_identified"):
            status = "failed"
            warnings.append(f"bin {k + 1}: rate not identified: {row['not_identified']}; it is not passed on in "
                            "sign_rates")
        rows.append(row)
    rates = {"edges": edges, "variable": doc.get("variable"),
             "rates": [{"true": sign, "reco": other,
                        "rate": [None if r.get("not_identified") else r["rate"] for r in rows],
                        "rate_error": [None if r.get("not_identified") else r["rate_error"] for r in rows]}]}
    return ({"bins": rows, "sign_rates": rates, "method": "Barlow-Beeston template fit (core/stats/template_fit.py)"},
            status, warnings)


def _read_counts(path: Path, args, edges) -> tuple[list[float], list[float], set]:
    n, k, signs = [0.0] * (len(edges) - 1), [0.0] * (len(edges) - 1), set()
    try:
        with Path(path).open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(line for line in fh if not line.startswith("#"))
            for i, row in enumerate(reader):
                try:
                    x = float(row[args.bin_column])
                    w = float(row[args.weight_column]) if args.weight_column else 1.0
                    t, r = row[args.true_sign_column].strip(), row[args.reco_sign_column].strip()
                except (KeyError, TypeError) as exc:
                    raise InputError(f"{path} row {i + 1}: missing column {exc}") from None
                except ValueError:
                    raise InputError(f"{path} row {i + 1}: not a number") from None
                if not (math.isfinite(x) and math.isfinite(w)) or w < 0 or w != int(w):
                    raise InputError(f"{path} row {i + 1}: weights must be non-negative integers (frequency weights); "
                                     "non-integer weights need a weighted binomial interval (hep-statistics)")
                _other(t), _other(r)
                signs.add(t)
                if not edges[0] <= x < edges[-1]:
                    continue
                b = max(i for i in range(len(edges) - 1) if edges[i] <= x)
                n[b] += w
                k[b] += w if r != t else 0.0
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from None
    return n, k, signs


def run_control(args) -> tuple[dict, str, list]:
    edges = _edges(args.edges)
    warnings = []
    n, k, signs = _read_counts(args.data, args, edges)
    if len(signs) != 1:
        raise InputError(f"a control sample has one known true sign; found {sorted(signs) or 'none'}")
    sign = signs.pop()
    mc = _read_counts(args.mc, args, edges) if args.mc else None
    if mc is not None and mc[2] != {sign}:
        # the scale factor r_data / r_mc compares one species: c+ and c- differ
        raise InputError(f"the MC control sample must have the data's one true sign ({sign}); "
                         f"found {sorted(mc[2]) or 'none'}")
    rows = []
    for b in range(len(edges) - 1):
        nb, kb = int(n[b]), int(k[b])
        row = {"bin": [edges[b], edges[b + 1]], "n": nb, "k": kb}
        if nb == 0:
            row.update(rate=None, interval_68=None)
            warnings.append(f"bin {b + 1}: no control events")
        else:
            lo, hi = clopper_pearson(kb, nb, args.cl)
            row.update(rate=kb / nb, interval_68=[lo, hi], interval_cl=args.cl)
        if mc is not None:
            nm, km = int(mc[0][b]), int(mc[1][b])
            row["mc"] = {"n": nm, "k": km, "rate": km / nm if nm else None}
            if nb and nm and km and kb:
                rd, rm = kb / nb, km / nm
                rel = math.sqrt((1 - rd) / kb + (1 - rm) / km)
                row["scale_factor"] = {"value": rd / rm, "error_approx": rd / rm * rel,
                                       "method": "delta method on two binomial rates; approximate"}
            else:
                row["scale_factor"] = None
        rows.append(row)
    rates = {"edges": edges, "variable": args.bin_column,
             "rates": [{"true": sign, "reco": _other(sign), "rate": [r["rate"] for r in rows],
                        "rate_error": [None if r["interval_68"] is None else (r["interval_68"][1] - r["interval_68"][0]) / 2
                                       for r in rows]}]}
    return {"bins": rows, "sign_rates": rates, "method": "control sample of known sign, Clopper-Pearson"}, "ok", warnings


def run_gaussian(args) -> dict:
    edges = _edges(args.edges)
    sig = [float(s) for s in args.sigma_inv_r]
    if len(sig) != len(edges) - 1 or any(not math.isfinite(s) or s <= 0 for s in sig):
        raise InputError("--sigma-inv-r needs one positive finite value per bin")
    if edges[0] <= 0:
        raise InputError("edges must be positive rigidities or momenta")
    phi = lambda z: 0.5 * math.erfc(z / math.sqrt(2.0))  # noqa: E731
    rows = [{"bin": [lo, hi], "sigma_inv_r": s, "lower_bound_at_low_edge": phi((1.0 / lo) / s),
             "lower_bound_at_high_edge": phi((1.0 / hi) / s)} for lo, hi, s in zip(edges, edges[1:], sig)]
    return {"bins": rows, "estimate": None, "label_kind": "Gaussian-core reference: a lower bound, not an estimate",
            "note": "non-Gaussian tails (scattering, mismatched hits, interactions) dominate real confusion; measure it "
                    "with the template or control mode"}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("template", help="Barlow-Beeston template fit per bin")
    p.add_argument("--input", type=Path, required=True)
    add_status_argument(p)
    p = sub.add_parser("control", help="control sample of known sign")
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--mc", type=Path)
    p.add_argument("--edges", nargs="+", required=True)
    p.add_argument("--bin-column", required=True)
    p.add_argument("--true-sign-column", required=True)
    p.add_argument("--reco-sign-column", required=True)
    p.add_argument("--weight-column")
    p.add_argument("--cl", type=float, default=CL68)
    add_status_argument(p)
    p = sub.add_parser("gaussian-core", help="Gaussian-core lower bound (not an estimate)")
    p.add_argument("--edges", nargs="+", required=True)
    p.add_argument("--sigma-inv-r", nargs="+", required=True, dest="sigma_inv_r")
    add_status_argument(p)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()}
    defaults = [k for k in ("cl", "status") if k in vars(args) and f"--{k}" not in given]
    warnings: list = []
    try:
        if args.command == "template":
            try:
                doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise InputError(f"cannot read {args.input}: {exc}") from None
            if not isinstance(doc, dict):
                raise InputError("the template input must be a JSON object")
            result, status, warnings = run_template(doc)
        elif args.command == "control":
            if not 0 < args.cl < 1:
                raise InputError("--cl must be in (0, 1)")
            result, status, warnings = run_control(args)
        else:
            result, status = run_gaussian(args), "ok"
    except (InputError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)},
                         indent=1))
        return exit_code("rejected")
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      "warnings": warnings, "label": LABEL, **result}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
