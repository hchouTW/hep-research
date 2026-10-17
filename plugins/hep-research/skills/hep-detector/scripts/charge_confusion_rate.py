#!/usr/bin/env python3
"""Charge-sign confusion rate per bin: template fit, control sample, or a Gaussian-core lower bound (D3).

Purpose: the probability that a particle of one charge sign is reconstructed with the other, per bin of rigidity (or
momentum), measured in a way that can be validated (see
<plugin root>/skills/hep-detector/references/charge-confusion.md).

Modes:
- template: per bin, the data histogram of a sign discriminant is fitted with right-sign and wrong-sign templates
  (and an optional background template) by the extended Poisson likelihood with the full Barlow-Beeston treatment of
  the template statistics (core/stats/template_fit.py; at most 6 templates and 60 discriminant bins). Rate
  r = Y_wrong / (Y_right + Y_wrong), its error from the fit covariance (delta method; a symmetric 68% interval);
- control: a sample of known true sign (CSV); per bin k wrong-sign of n events, the Clopper-Pearson interval
  (core/stats/tail_estimation.py), and with --mc a second sample, the data/MC scale factor r_data / r_mc with an
  approximate (delta-method) error. Weights must be integer frequency weights: non-integer weights are refused
  (hep-statistics owns weighted binomial intervals);
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
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used, warnings, bins, sign_rates.
Exit codes: 0 ok; 1 a template fit failed; 2 bad input. Standard library only.
"""
from __future__ import annotations

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


def template_rate(bin_doc: dict, names: dict) -> dict:
    """Fit one bin; names maps 'right'/'wrong' to template names."""
    try:
        tnames, data, m, mc = template_fit._load(bin_doc)
    except template_fit.ToyError as exc:
        raise InputError(str(exc)) from None
    for role in ("right", "wrong"):
        if names[role] not in tnames:
            raise InputError(f"template '{names[role]}' missing")
    # start from a positive split of the data (a start at a boundary can leave the simplex there), then the naive fit,
    # as template_fit.bb_fit does
    total = sum(data)
    start = [max(total / len(tnames), 1.0)] * len(tnames)
    y0 = template_fit._fit_yields_full(data, m, mc, "naive", start)[0]
    y, cov, _, diag = template_fit._fit_yields_full(data, m, mc, "bb", [max(v, 1.0) for v in y0])
    i, j = tnames.index(names["right"]), tnames.index(names["wrong"])
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
    return {"rate": rate, "rate_error_hessian": err, "interval_68": [lo, hi], "rate_error": (hi - lo) / 2.0,
            "interval_method": "profile likelihood in the rate, -2 Delta ln L = 1 (Barlow-Beeston), lower end at 0 "
                               "when the boundary is inside",
            "yields": {n: y[k] for k, n in enumerate(tnames)}, "fit_outcome": diag["outcome"]}


def profile_interval(data, m, mc, y, i: int, j: int) -> tuple[float, float]:
    """68% profile-likelihood interval of r = y_j / (y_i + y_j): for fixed r the total N = y_i + y_j and the other
    yields are profiled (Nelder-Mead on the Barlow-Beeston log-likelihood)."""
    others = [k for k in range(len(y)) if k not in (i, j)]

    def nll_at(r: float, start):
        def f(x):
            n = x[0]
            if n <= 0 or any(v < 0 for v in x[1:]):
                return 1e300
            yy = [0.0] * len(y)
            yy[i], yy[j] = n * (1 - r), n * r
            for k, v in zip(others, x[1:]):
                yy[k] = v
            return -template_fit._ll_bb(data, m, mc, yy)
        steps = [max(0.05 * v, 1.0) for v in start]
        x, val = template_fit._nelder_mead(f, start, steps)
        return val, x

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
    hi = 1.0 if excess(1.0) < 0 else root(r_hat, 1.0)
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


def run_template(doc: dict) -> tuple[dict, str]:
    edges = _edges(doc.get("edges", []))
    sign = doc.get("true_sign")
    other = _other(sign)
    bins = doc.get("bins")
    if not isinstance(bins, list) or len(bins) != len(edges) - 1:
        raise InputError(f"bins must list {len(edges) - 1} entries (one per pair of edges)")
    rows, status = [], "ok"
    for k, b in enumerate(bins):
        row = template_rate(b, {"right": "right", "wrong": "wrong"})
        row["bin"] = [edges[k], edges[k + 1]]
        if row["fit_outcome"] in template_fit.FAILED_OUTCOMES or row["rate_error"] is None:
            status = "failed"
        rows.append(row)
    rates = {"edges": edges, "variable": doc.get("variable"),
             "rates": [{"true": sign, "reco": other, "rate": [r["rate"] for r in rows],
                        "rate_error": [r["rate_error"] for r in rows]}]}
    return {"bins": rows, "sign_rates": rates, "method": "Barlow-Beeston template fit (core/stats/template_fit.py)"}, status


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
            result, status = run_template(doc)
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
