#!/usr/bin/env python3
"""Domain-shift report between a reference sample (for example simulation) and a target sample (data or a control
sample): per-feature distances, a classifier two-sample test, a per-period breakdown and the features that drive the
difference (ML4). Its --domain-shift-out file is the `domain_shift` input of write_ml_artifact.py.

Method (see <plugin root>/skills/hep-ml/references/robustness-and-distribution-shift.md):
  per feature  the weighted Kolmogorov-Smirnov distance D and its asymptotic p-value with the effective sizes
               n_eff = (sum w)^2 / sum w^2; the Wasserstein-1 distance (integral of |F_ref - F_tgt|); a binned chi2 on
               --bins quantile bins of the pooled sample, chi2 = sum (w_r/W_r - w_t/W_t)^2 / (s_r/W_r^2 + s_t/W_t^2)
               (s = sum of w^2 in the bin), ndf = bins - 1.
  classifier   logistic regression on the standardized features and their squares (Newton steps, ridge 1e-6),
               trained with grouped K-fold cross-validation (folds by sha256 of --group-column, so rows of one run or
               event never sit on both sides) and scored out of fold; the weighted AUC of target vs reference against
               its null spread sqrt((n_r + n_t + 1) / (12 n_r n_t)) with effective sizes; z and a one-sided p-value.
  drivers      features whose KS p-value passes a Bonferroni threshold alpha / n_features, ordered by D.
  periods      with --period-column (in the target): the KS distance of every feature per target period against the
               whole reference.
  verdict      shift_detected when the classifier p-value or any feature passes its threshold.
The block records how the check ran (status "checked") and what it found; what was done about a shift ("outcome":
no-shift, corrected, bounded-by-nuisance, uncorrected) is the analyst's declaration through --outcome, and
bounded-by-nuisance or uncorrected need --nuisance (ml-artifact 2.8.0).
Assumptions: rows are independent apart from the declared groups; a large sample makes tiny shifts significant, so
read the distances and the driver ranking, not only the p-values.
Input: CSV with a header (or .npz, loaded without pickle) for --reference and --target; numeric feature columns.
Usage:
  domain_shift_report.py --reference SIM.csv --target DATA.csv --features a,b,c --control-sample TEXT
      [--weight-column W] [--group-column G] [--period-column P] [--folds 5] [--bins 20] [--alpha 0.05] [--seed 0]
      [--domain-shift-out DS.json] [--outcome ... [--nuisance NAME]] [--status LABEL]
Output JSON: status (ok, failed, rejected, missing-dependency), status_label, inputs, defaults_used, features,
classifier_test, drivers, periods, shift_detected, domain_shift.
Exit codes: 0 no shift found; 1 a shift was found; 2 bad input; 3 numpy missing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats.statistical_toys import chi2_sf  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

OUTCOMES = ("no-shift", "corrected", "bounded-by-nuisance", "uncorrected")
INSTALL = "pip install 'numpy>=2.4,<3'"


class InputError(ValueError):
    """Bad input: exit 2."""


def kolmogorov_sf(t: float) -> float:
    """P(K > t) for the Kolmogorov distribution (asymptotic)."""
    if t < 0.2:
        return 1.0
    s = sum((-1) ** (k - 1) * math.exp(-2 * k * k * t * t) for k in range(1, 101))
    return min(1.0, max(0.0, 2 * s))


def n_eff(w):
    return float(w.sum() ** 2 / (w ** 2).sum())


def _ecdf_on(x, w, grid):
    import numpy as np
    order = np.argsort(x, kind="mergesort")
    xs, cw = x[order], np.cumsum(w[order]) / w.sum()
    idx = np.searchsorted(xs, grid, side="right")
    return np.where(idx > 0, cw[np.maximum(idx - 1, 0)], 0.0)


def ks_test(xr, wr, xt, wt) -> dict:
    import numpy as np
    grid = np.unique(np.concatenate([xr, xt]))
    d = float(np.max(np.abs(_ecdf_on(xr, wr, grid) - _ecdf_on(xt, wt, grid))))
    ne = n_eff(wr) * n_eff(wt) / (n_eff(wr) + n_eff(wt))
    sq = math.sqrt(ne)
    return {"d": d, "p": kolmogorov_sf((sq + 0.12 + 0.11 / sq) * d), "n_eff": ne}


def wasserstein(xr, wr, xt, wt) -> float:
    import numpy as np
    grid = np.unique(np.concatenate([xr, xt]))
    diff = np.abs(_ecdf_on(xr, wr, grid) - _ecdf_on(xt, wt, grid))
    return float(np.sum(diff[:-1] * np.diff(grid)))


def binned_chi2(xr, wr, xt, wt, bins: int) -> dict:
    import numpy as np
    edges = np.unique(np.quantile(np.concatenate([xr, xt]), np.linspace(0, 1, bins + 1)))
    if edges.size < 3:
        return {"chi2": 0.0, "ndf": 0, "p": 1.0, "bins": int(edges.size - 1)}
    edges[-1] = np.nextafter(edges[-1], np.inf)
    hr, _ = np.histogram(xr, edges, weights=wr)
    ht, _ = np.histogram(xt, edges, weights=wt)
    sr, _ = np.histogram(xr, edges, weights=wr ** 2)
    st, _ = np.histogram(xt, edges, weights=wt ** 2)
    Wr, Wt = wr.sum(), wt.sum()
    var = sr / Wr ** 2 + st / Wt ** 2
    keep = var > 0
    chi2 = float(np.sum((hr[keep] / Wr - ht[keep] / Wt) ** 2 / var[keep]))
    ndf = int(keep.sum() - 1)
    return {"chi2": chi2, "ndf": ndf, "p": chi2_sf(chi2, ndf) if ndf > 0 else 1.0, "bins": int(edges.size - 1)}


def _fold_of(groups, k: int):
    return [int(hashlib.sha256(str(g).encode()).hexdigest(), 16) % k for g in groups]


def _logistic(X, y, w, iters: int = 50):
    import numpy as np
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(X @ beta)))
        g = X.T @ (w * (y - p)) - 1e-6 * beta
        H = (X * (w * p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(X.shape[1])
        step = np.linalg.solve(H, g)
        beta += step
        if np.max(np.abs(step)) < 1e-10:
            break
    return beta


def weighted_auc(score, y, w) -> float:
    """P(score_target > score_reference), ties counted half, with event weights."""
    import numpy as np
    order = np.argsort(score, kind="mergesort")
    s, yy, ww = score[order], y[order], w[order]
    wt_tot, wr_tot = ww[yy == 1].sum(), ww[yy == 0].sum()
    auc, cum_r, i = 0.0, 0.0, 0
    while i < s.size:
        j = i
        while j < s.size and s[j] == s[i]:
            j += 1
        wt_blk = ww[i:j][yy[i:j] == 1].sum()
        wr_blk = ww[i:j][yy[i:j] == 0].sum()
        auc += wt_blk * (cum_r + 0.5 * wr_blk)
        cum_r += wr_blk
        i = j
    return float(auc / (wt_tot * wr_tot))


def classifier_test(Xr, wr, gr, Xt, wt, gt, folds: int) -> dict:
    import numpy as np
    X = np.vstack([Xr, Xt])
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    design = np.hstack([np.ones((Z.shape[0], 1)), Z, Z ** 2])
    y = np.concatenate([np.zeros(len(Xr)), np.ones(len(Xt))])
    w = np.concatenate([wr / wr.sum(), wt / wt.sum()]) * (len(Xr) + len(Xt)) / 2
    fold = np.array(_fold_of(list(gr) + list(gt), folds))
    score = np.zeros_like(y)
    for k in range(folds):
        test = fold == k
        if not test.any() or test.all():
            continue
        beta = _logistic(design[~test], y[~test], w[~test])
        score[test] = design[test] @ beta
    auc = weighted_auc(score, y, np.concatenate([wr, wt]))
    nr, nt = n_eff(wr), n_eff(wt)
    sigma = math.sqrt((nr + nt + 1) / (12 * nr * nt))
    z = (auc - 0.5) / sigma
    return {"method": "logistic regression on standardized features and squares, grouped K-fold, out-of-fold AUC",
            "auc": auc, "auc_sigma_null": sigma, "z": z, "p": 0.5 * math.erfc(z / math.sqrt(2)), "folds": folds}


def _load(path: Path, columns: list[str]) -> dict:
    import numpy as np
    if not path.is_file():
        raise InputError(f"{path} not found")
    if path.suffix == ".npz":
        with np.load(path, allow_pickle=False) as z:
            data = {k: z[k] for k in z.files}
    else:
        with path.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(line for line in fh if not line.startswith("#")))
        if not rows:
            raise InputError(f"{path}: no rows")
        data = {k: [r[k] for r in rows] for k in rows[0]}
    out = {}
    for c in columns:
        if c not in data:
            raise InputError(f"{path}: column {c!r} not found")
        out[c] = data[c]
    return out


def _num(values, name):
    import numpy as np
    try:
        a = np.asarray(values, dtype=float)
    except ValueError as exc:
        raise InputError(f"{name}: not numeric ({exc})") from exc
    if not np.all(np.isfinite(a)):
        raise InputError(f"{name}: non-finite values")
    return a


def analyse(args) -> dict:
    import numpy as np
    feats = [f.strip() for f in args.features.split(",") if f.strip()]
    if not feats:
        raise InputError("--features is empty")
    if args.folds < 2:
        raise InputError("--folds must be >= 2")
    if not 0 < args.alpha < 1:
        raise InputError("--alpha must be in (0, 1)")
    extra = [c for c in (args.weight_column, args.group_column) if c]
    ref = _load(args.reference, feats + extra)
    tgt = _load(args.target, feats + extra + ([args.period_column] if args.period_column else []))
    Xr = np.column_stack([_num(ref[f], f"reference {f}") for f in feats])
    Xt = np.column_stack([_num(tgt[f], f"target {f}") for f in feats])
    wr = _num(ref[args.weight_column], "reference weight") if args.weight_column else np.ones(len(Xr))
    wt = _num(tgt[args.weight_column], "target weight") if args.weight_column else np.ones(len(Xt))
    if (wr < 0).any() or (wt < 0).any():
        raise InputError("negative weights: the distances need non-negative weights (hand signed-weight samples to "
                         "hep-statistics)")
    gr = ref[args.group_column] if args.group_column else [f"r{i}" for i in range(len(Xr))]
    gt = tgt[args.group_column] if args.group_column else [f"t{i}" for i in range(len(Xt))]
    features = {}
    for i, f in enumerate(feats):
        features[f] = {"ks": ks_test(Xr[:, i], wr, Xt[:, i], wt), "wasserstein": wasserstein(Xr[:, i], wr, Xt[:, i], wt),
                       "binned_chi2": binned_chi2(Xr[:, i], wr, Xt[:, i], wt, args.bins)}
    thr = args.alpha / len(feats)
    drivers = sorted((f for f in feats if features[f]["ks"]["p"] < thr), key=lambda f: -features[f]["ks"]["d"])
    clf = classifier_test(Xr, wr, gr, Xt, wt, gt, args.folds)
    periods = {}
    if args.period_column:
        lab = np.asarray(tgt[args.period_column])
        for per in sorted(set(lab.tolist())):
            m = lab == per
            periods[str(per)] = {f: {"ks_d": (r := ks_test(Xr[:, i], wr, Xt[m, i], wt[m]))["d"], "ks_p": r["p"]}
                                 for i, f in enumerate(feats)}
    shift = bool(drivers) or clf["p"] < args.alpha
    result = {"shift_detected": shift, "classifier_auc": clf["auc"], "classifier_z": clf["z"], "drivers": drivers,
              "per_feature": {f: {"ks_d": features[f]["ks"]["d"], "ks_p": features[f]["ks"]["p"],
                                  "wasserstein": features[f]["wasserstein"]} for f in feats}}
    if periods:
        result["periods"] = periods
    block = {"control_sample": args.control_sample,
             "method": "domain_shift_report.py: weighted KS, Wasserstein-1, binned chi2 per feature; grouped K-fold "
                       f"logistic two-sample test; alpha {args.alpha}, Bonferroni over {len(feats)} features",
             "result": result, "status": "checked"}
    if args.outcome:
        block["outcome"] = args.outcome
    if args.nuisance:
        block["nuisance"] = args.nuisance
    return {"features": features, "classifier_test": clf, "drivers": drivers, "feature_threshold": thr,
            "periods": periods, "shift_detected": shift, "domain_shift": block}


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--target", type=Path, required=True)
    ap.add_argument("--features", required=True, help="comma-separated numeric columns")
    ap.add_argument("--control-sample", required=True, help="name of the target sample (data or control region)")
    ap.add_argument("--weight-column")
    ap.add_argument("--group-column", help="rows sharing a value stay in one fold (run, event or file)")
    ap.add_argument("--period-column", help="target column for the per-period breakdown")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--bins", type=int, default=20)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0, help="recorded; the method itself is deterministic")
    ap.add_argument("--domain-shift-out", type=Path)
    ap.add_argument("--outcome", choices=OUTCOMES)
    ap.add_argument("--nuisance")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("folds", "bins", "alpha", "seed", "status") if f"--{k}" not in given]
    if not args.group_column:
        defaults.append("group_column (each row its own group)")
    inputs = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items() if k != "status"}
    head = {"status_label": args.status, "inputs": inputs, "defaults_used": defaults}
    try:
        import numpy  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "missing-dependency", **head, "error": "numpy is required", "install": INSTALL}))
        return exit_code("missing-dependency")
    try:
        if args.outcome in ("bounded-by-nuisance", "uncorrected") and not args.nuisance:
            raise InputError(f"--outcome {args.outcome} needs --nuisance (the parameter that carries the shift)")
        out = analyse(args)
    except InputError as exc:
        print(json.dumps({"status": "rejected", **head, "error": str(exc)}, indent=1))
        return exit_code("rejected")
    if args.domain_shift_out:
        args.domain_shift_out.write_text(json.dumps({"domain_shift": out["domain_shift"]}, indent=1) + "\n",
                                         encoding="utf-8")
    status = "failed" if out["shift_detected"] else "ok"
    print(json.dumps({"status": status, **head, **out}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
