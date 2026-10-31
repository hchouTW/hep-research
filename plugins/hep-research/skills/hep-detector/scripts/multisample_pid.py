#!/usr/bin/env python3
"""Combine many samples of one particle: a charge estimate from many dE/dx layers, or a log-likelihood ratio from
per-layer PDFs (D10).

Purpose: the two standard ways a detector with many samples (silicon or tracker layers, TRD layers, calorimeter
samplings) identifies a particle, with the choices stated. See "Combining many samples" in
<plugin root>/skills/hep-detector/references/particle-identification.md.

Subcommands:
- charge EVENTS.csv: per layer, the signal is corrected for the path length (signal x cos(theta) from --path-column;
  or --no-path-correction, which must be said explicitly) and inverted through a user response curve
  (--response JSON {"z2": [...], "signal": [...]}, increasing; saturation is allowed; linear interpolation, values
  outside the table are counted as out of range and left out) to a per-layer estimate of |Z|. The layers are combined
  by --method:
    truncated-mean  mean after dropping the highest --truncate-high fraction (and --truncate-low, default 0) of the
                    per-layer estimates (robust against the Landau tail);
    weighted-mean   weights 1/sigma^2 (--layer-sigma, one value or one per layer); --correlation rho (a common
                    correlation between layers) uses the generalized least-squares weights C^-1 1;
    likelihood      the |Z| that maximizes the product of per-layer Moyal densities (a Landau approximation) located
                    at the response R(Z^2) with relative width --moyal-rel-width, scanned over --z-range.
  With --true-z-column: per true Z the peak (median), mean, core width sigma68 (half the central 68.27% range) and tail
  fraction (beyond 3 sigma68 from the median), and the leakage matrix P(reco | true) between neighbouring charges
  (reco = nearest integer, a stated convention) with Clopper-Pearson central 68.27% intervals, as a species-migration
  block. --toys N --toy-z Z --toy-moyal-rel-width w --seed S predicts the core width at Z from the per-layer Moyal
  model, for comparison with the data.
- likelihood EVENTS.csv: LLR = sum over layers of log(p_sig/p_bkg) from binned per-layer PDFs (--pdfs JSON
  {"edges", "signal", "background"} for every layer, or {"layers": {name: {...}}}); empty bins get a floor of 1e-12
  of the PDF and are counted. With --label-column (1 signal, 0 background): the efficiency - mis-identification curve
  over LLR thresholds with Clopper-Pearson intervals, and the rejection 1/misid.
Correlations between layers are optional; without them the output says "independence assumed".

Input CSV: one row per particle, one column per layer (--layers a,b,c); lines starting with # are skipped.
Output: JSON with status, status_label (--status, default unvalidated), inputs, defaults_used, warnings, the results
and "label": "[General method]". Exit codes: 0 ok; 2 invalid input or arguments (status rejected).
Run: python3 <plugin root>/skills/hep-detector/scripts/multisample_pid.py charge events.csv --layers l1,l2,l3,l4 \\
         --response response.json --method truncated-mean --truncate-high 0.25 --no-path-correction --true-z-column z
Standard library only.
"""
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
import bisect
import csv
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats.tail_estimation import clopper_pearson  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
CL = 0.6827
PDF_FLOOR = 1e-12
TAIL_SIGMAS = 3.0
ND = statistics.NormalDist()


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


def read_rows(path, columns):
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            lines = [ln for ln in fh if not ln.startswith("#")]
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from None
    reader = csv.DictReader(lines)
    missing = [c for c in columns if c not in (reader.fieldnames or [])]
    if missing:
        raise InputError(f"{path}: missing column(s) {missing}; found {reader.fieldnames}")
    rows = list(reader)
    if not rows:
        raise InputError(f"{path}: no rows")
    return rows


def load_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {what} {path}: {exc}") from None


# ---------------------------------------------------------------- response curve

class Response:
    def __init__(self, doc):
        z2, sig = doc.get("z2"), doc.get("signal")
        if not isinstance(z2, list) or not isinstance(sig, list) or len(z2) != len(sig) or len(z2) < 2:
            raise InputError("response needs lists 'z2' and 'signal' of equal length >= 2")
        self.z2 = [_num(v, "response z2") for v in z2]
        self.sig = [_num(v, "response signal") for v in sig]
        if any(b <= a for a, b in zip(self.z2, self.z2[1:])) or any(b <= a for a, b in zip(self.sig, self.sig[1:])):
            raise InputError("the response curve must increase strictly in both z2 and signal (invertible)")
        if self.z2[0] < 0:
            raise InputError("response z2 must be >= 0")

    def signal(self, z2):
        i = min(max(bisect.bisect_right(self.z2, z2) - 1, 0), len(self.z2) - 2)
        f = (z2 - self.z2[i]) / (self.z2[i + 1] - self.z2[i])
        return self.sig[i] + f * (self.sig[i + 1] - self.sig[i])

    def z(self, signal):
        """|Z| for a signal, or None outside the table."""
        if signal < self.sig[0] or signal > self.sig[-1]:
            return None
        i = min(max(bisect.bisect_right(self.sig, signal) - 1, 0), len(self.sig) - 2)
        f = (signal - self.sig[i]) / (self.sig[i + 1] - self.sig[i])
        return math.sqrt(max(self.z2[i] + f * (self.z2[i + 1] - self.z2[i]), 0.0))


# ---------------------------------------------------------------- combinations

def truncated_mean(values, low, high):
    v = sorted(values)
    n = len(v)
    k_lo, k_hi = int(math.floor(low * n)), int(math.floor(high * n))
    kept = v[k_lo:n - k_hi]
    if not kept:
        raise InputError("the truncation removes every layer")
    return sum(kept) / len(kept)


def gls_weights(sigmas, rho):
    """Weights C^-1 1 / (1^T C^-1 1) for C_ij = rho s_i s_j (i != j), s_i^2 on the diagonal."""
    n = len(sigmas)
    c = [[sigmas[i] * sigmas[j] * (1.0 if i == j else rho) for j in range(n)] for i in range(n)]
    # solve C w = 1 by Gaussian elimination with partial pivoting
    a = [row[:] + [1.0] for row in c]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-300:
            raise InputError("the layer covariance is singular")
        a[col], a[piv] = a[piv], a[col]
        for r in range(n):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    w = [a[i][n] / a[i][i] for i in range(n)]
    s = sum(w)
    if s <= 0:
        raise InputError("the layer covariance is not positive definite")
    return [x / s for x in w]


def moyal_logpdf(x, loc, scale):
    lam = (x - loc) / scale
    return -0.5 * (lam + math.exp(-lam)) - math.log(scale * math.sqrt(2 * math.pi))


def moyal_sample(rng, loc, scale):
    u = rng.uniform(1e-12, 1 - 1e-12)
    return loc + scale * (-2.0 * math.log(ND.inv_cdf(1.0 - u / 2.0)))


def likelihood_z(signals, response, rel, zmin, zmax, step=0.002):
    best, best_ll = None, -math.inf
    n = int(round((zmax - zmin) / step))
    for k in range(n + 1):
        z = zmin + k * step
        mu = response.signal(z * z)
        if mu <= 0:
            continue
        ll = sum(moyal_logpdf(s, mu, rel * mu) for s in signals)
        if ll > best_ll:
            best, best_ll = z, ll
    return best


def summarize(values):
    v = sorted(values)
    med = statistics.median(v)
    lo = v[int(math.floor((1 - CL) / 2 * (len(v) - 1)))]
    hi = v[int(math.ceil((1 + CL) / 2 * (len(v) - 1)))]
    s68 = (hi - lo) / 2
    tail = sum(1 for x in v if s68 > 0 and abs(x - med) > TAIL_SIGMAS * s68) / len(v)
    return {"n": len(v), "median": med, "mean": sum(v) / len(v), "sigma68": s68, "tail_fraction": tail}


# ---------------------------------------------------------------- subcommands

def run_charge(args, warnings, defaults):
    layers = [c for c in args.layers.split(",") if c]
    if not layers:
        raise InputError("--layers names no column")
    if args.path_column is None and not args.no_path_correction:
        raise InputError("give --path-column (cos(theta) of the track) or --no-path-correction explicitly")
    if args.response is None:
        raise InputError("--response is required (the curve that turns a signal into Z^2)")
    response = Response(load_json(args.response, "response"))
    method = args.method
    if method == "truncated-mean":
        if args.truncate_high is None:
            raise InputError("truncated-mean needs --truncate-high (the fraction of highest samples dropped)")
        for name, f in (("--truncate-high", args.truncate_high), ("--truncate-low", args.truncate_low)):
            if not 0.0 <= f < 1.0:
                raise InputError(f"{name} must be in [0, 1)")
        if args.truncate_low + args.truncate_high >= 1.0:
            raise InputError("--truncate-low + --truncate-high must be < 1")
    sigmas = None
    if method == "weighted-mean":
        if not args.layer_sigma:
            raise InputError("weighted-mean needs --layer-sigma (one value or one per layer)")
        sigmas = [_num(s, "--layer-sigma") for s in args.layer_sigma.split(",")]
        if len(sigmas) == 1:
            sigmas = sigmas * len(layers)
        if len(sigmas) != len(layers) or min(sigmas) <= 0:
            raise InputError("--layer-sigma needs one positive value or one per layer")
    if args.correlation is not None:
        if method != "weighted-mean":
            raise InputError("--correlation applies to weighted-mean only")
        if not -1.0 / max(len(layers) - 1, 1) < args.correlation < 1.0:
            raise InputError("--correlation must give a positive-definite covariance")
    if method == "likelihood":
        if args.moyal_rel_width is None or args.moyal_rel_width <= 0 or not args.z_range:
            raise InputError("likelihood needs --moyal-rel-width > 0 and --z-range ZMIN ZMAX")
        if not 0 < args.z_range[0] < args.z_range[1]:
            raise InputError("--z-range needs 0 < ZMIN < ZMAX")
    weights = gls_weights(sigmas, args.correlation or 0.0) if sigmas else None
    cols = layers + ([args.path_column] if args.path_column else []) + ([args.true_z_column] if args.true_z_column else [])
    rows = read_rows(args.events, cols)
    estimates, out_of_range = [], 0
    for r in rows:
        cosine = 1.0
        if args.path_column:
            cosine = _num(r[args.path_column], args.path_column)
            if not 0 < cosine <= 1:
                raise InputError(f"{args.path_column} must be in (0, 1], got {cosine}")
        signals = [_num(r[c], c) * cosine for c in layers]
        if method == "likelihood":
            z = likelihood_z(signals, response, args.moyal_rel_width, *args.z_range)
        else:
            per = [response.z(s) for s in signals]
            if any(p is None for p in per):
                out_of_range += 1
                continue
            z = truncated_mean(per, args.truncate_low, args.truncate_high) if method == "truncated-mean" \
                else sum(w * p for w, p in zip(weights, per))
        true_z = int(round(_num(r[args.true_z_column], args.true_z_column))) if args.true_z_column else None
        estimates.append((true_z, z))
    if not estimates:
        raise InputError("no event could be estimated (every event has a signal outside the response table)")
    if out_of_range:
        warnings.append(f"{out_of_range} events had a signal outside the response table and were left out")
    corr = (f"common layer correlation rho = {args.correlation} declared (generalized least-squares weights)"
            if args.correlation is not None else "independence assumed (no layer correlations declared)")
    result = {"method": method, "layers": layers, "events_used": len(estimates), "out_of_range": out_of_range,
              "correlations": corr, "summary": summarize([z for _, z in estimates]),
              "path_correction": "signal x cos(theta) from " + args.path_column if args.path_column else "none (waived)"}
    if weights:
        result["weights"] = weights
    if args.true_z_column:
        by = {}
        for t, z in estimates:
            by.setdefault(t, []).append(z)
        result["per_true_z"] = {str(t): summarize(v) for t, v in sorted(by.items())}
        defaults.append("reco charge = nearest integer to the estimate")
        trues = sorted(by)
        prob, counts, intervals = {}, {}, {}
        for t in trues:
            n = len(by[t])
            reco = [int(math.floor(z + 0.5)) for z in by[t] if z is not None]
            row_c = {str(k): reco.count(k) for k in (t - 1, t, t + 1)}
            row_c["other"] = n - sum(row_c.values())
            counts[str(t)] = row_c
            prob[str(t)] = {k: c / n for k, c in row_c.items()}
            intervals[str(t)] = {k: list(clopper_pearson(c, n, CL)) for k, c in row_c.items()}
        result["leakage"] = {"block": "species migration P(reco | true) between neighbouring charges",
                             "true": trues, "counts": counts, "probabilities": prob, "intervals": intervals,
                             "interval": "Clopper-Pearson, central 68.27%"}
    if args.toys:
        if args.toy_z is None or args.toy_moyal_rel_width is None or args.seed is None:
            raise InputError("--toys needs --toy-z, --toy-moyal-rel-width and --seed")
        rng = random.Random(args.seed)
        mu = response.signal(args.toy_z ** 2)
        toy = []
        for _ in range(args.toys):
            sig = [moyal_sample(rng, mu, args.toy_moyal_rel_width * mu) for _ in layers]
            if method == "likelihood":
                toy.append(likelihood_z(sig, response, args.moyal_rel_width, *args.z_range))
                continue
            per = [response.z(s) for s in sig]
            if any(p is None for p in per):
                continue
            toy.append(truncated_mean(per, args.truncate_low, args.truncate_high) if method == "truncated-mean"
                       else sum(w * p for w, p in zip(weights, per)))
        result["toy_prediction"] = dict(summarize(toy), z=args.toy_z,
                                        model=f"per-layer Moyal at R(Z^2), relative width {args.toy_moyal_rel_width}",
                                        seed=args.seed)
    return result


def _pdf(doc, what):
    edges = [_num(x, f"{what} edges") for x in doc.get("edges", [])]
    if len(edges) < 2 or any(b <= a for a, b in zip(edges, edges[1:])):
        raise InputError(f"{what}: 'edges' must increase strictly")
    out = {}
    for key in ("signal", "background"):
        vals = [_num(x, f"{what} {key}") for x in doc.get(key, [])]
        if len(vals) != len(edges) - 1 or min(vals) < 0 or sum(vals) <= 0:
            raise InputError(f"{what}: '{key}' needs {len(edges) - 1} non-negative bin contents with a positive sum")
        tot = sum(vals)
        out[key] = [v / tot / (b - a) for v, a, b in zip(vals, edges, edges[1:])]
    return edges, out["signal"], out["background"]


def run_likelihood(args, warnings, defaults):
    layers = [c for c in args.layers.split(",") if c]
    doc = load_json(args.pdfs, "PDF file")
    per_layer = {}
    for c in layers:
        spec = doc.get("layers", {}).get(c, doc) if isinstance(doc.get("layers"), dict) else doc
        per_layer[c] = _pdf(spec, f"PDF of layer {c}")
    rows = read_rows(args.events, layers + ([args.label_column] if args.label_column else []))
    floored = outside = 0
    llrs = []
    for r in rows:
        llr = 0.0
        for c in layers:
            x = _num(r[c], c)
            edges, ps, pb = per_layer[c]
            i = bisect.bisect_right(edges, x) - 1
            if i < 0 or i >= len(ps):
                outside += 1
                continue
            s, b = ps[i], pb[i]
            if s <= 0 or b <= 0:
                floored += 1
            floor = PDF_FLOOR * max(max(ps), max(pb))
            llr += math.log(max(s, floor)) - math.log(max(b, floor))
        lab = int(_num(r[args.label_column], args.label_column)) if args.label_column else None
        if lab not in (None, 0, 1):
            raise InputError(f"{args.label_column} must be 0 or 1")
        llrs.append((lab, llr))
    if floored:
        warnings.append(f"{floored} layer values fell in an empty PDF bin (floor {PDF_FLOOR:g} of the PDF maximum)")
    if outside:
        warnings.append(f"{outside} layer values fell outside the PDF edges and were skipped")
    result = {"layers": layers, "events": len(llrs),
              "correlations": "independence assumed (the LLR sums per-layer terms; no layer correlations declared)",
              "llr_summary": summarize([v for _, v in llrs])}
    if args.label_column:
        sig = sorted(v for lab, v in llrs if lab == 1)
        bkg = sorted(v for lab, v in llrs if lab == 0)
        if not sig or not bkg:
            raise InputError("the curve needs both signal (1) and background (0) events")
        ns, nb = len(sig), len(bkg)
        thresholds = sorted(set(sig[int(k * (ns - 1) / (args.points - 1))] for k in range(args.points)))
        curve = []
        for t in thresholds:
            ks = ns - bisect.bisect_left(sig, t)
            kb = nb - bisect.bisect_left(bkg, t)
            curve.append({"threshold": t, "efficiency": ks / ns, "misid": kb / nb,
                          "rejection": (nb / kb) if kb else None,
                          "efficiency_interval": list(clopper_pearson(ks, ns, CL)),
                          "misid_interval": list(clopper_pearson(kb, nb, CL))})
        result["curve"] = curve
        result["interval"] = "Clopper-Pearson, central 68.27%"
        defaults.append(f"{args.points} thresholds at signal LLR quantiles")
    return result


def main(argv=None):
    parser = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ch = sub.add_parser("charge", help="charge from many dE/dx samples")
    ch.add_argument("events")
    ch.add_argument("--layers", required=True, help="comma-separated layer columns")
    ch.add_argument("--response", help="JSON {z2: [...], signal: [...]}, increasing")
    ch.add_argument("--method", required=True, choices=("truncated-mean", "weighted-mean", "likelihood"))
    ch.add_argument("--truncate-high", type=float, help="fraction of the highest samples dropped (truncated-mean)")
    ch.add_argument("--truncate-low", type=float, default=0.0, help="fraction of the lowest samples dropped")
    ch.add_argument("--layer-sigma", help="per-layer resolution in Z, one value or comma list (weighted-mean)")
    ch.add_argument("--correlation", type=float, help="common correlation between layers (weighted-mean)")
    ch.add_argument("--moyal-rel-width", type=float, help="relative Moyal width per layer (likelihood)")
    ch.add_argument("--z-range", type=float, nargs=2, help="ZMIN ZMAX scanned by the likelihood")
    ch.add_argument("--path-column", help="column of cos(theta) for the path-length correction")
    ch.add_argument("--no-path-correction", action="store_true", help="waive the path-length correction")
    ch.add_argument("--true-z-column", help="true |Z| (simulation): per-Z widths and the leakage matrix")
    ch.add_argument("--toys", type=int, help="toy events for the predicted core width")
    ch.add_argument("--toy-z", type=float)
    ch.add_argument("--toy-moyal-rel-width", type=float)
    ch.add_argument("--seed", type=int)
    lk = sub.add_parser("likelihood", help="log-likelihood ratio from per-layer PDFs")
    lk.add_argument("events")
    lk.add_argument("--layers", required=True)
    lk.add_argument("--pdfs", required=True, help="JSON with edges, signal, background (or per-layer under 'layers')")
    lk.add_argument("--label-column", help="1 signal, 0 background: efficiency - mis-identification curve")
    lk.add_argument("--points", type=int, default=200, help="number of thresholds on the curve (default 200)")
    for sp in (ch, lk):
        add_status_argument(sp)
    args = parser.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("--status", "--truncate-low", "--points") if k in
                {f"--{a.replace('_', '-')}" for a in vars(args)} and k not in given]
    warnings = []
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k != "status"}
    try:
        result = run_charge(args, warnings, defaults) if args.command == "charge" else \
            run_likelihood(args, warnings, defaults)
        out = {"status": "ok", "status_label": args.status, "label": LABEL, "inputs": inputs,
               "defaults_used": defaults, "warnings": warnings, **result}
    except InputError as exc:
        out = {"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)}
    except (OverflowError, ZeroDivisionError, ValueError) as exc:
        out = {"status": "rejected", "status_label": args.status, "inputs": inputs, "error": f"numerical range: {exc}"}
    try:
        text = json.dumps(out, indent=2, allow_nan=False)
    except ValueError:
        out = {"status": "rejected", "status_label": args.status, "error": "a result is not finite"}
        text = json.dumps(out, indent=2)
    print(text)
    return exit_code(out["status"])


if __name__ == "__main__":
    raise SystemExit(main())
