#!/usr/bin/env python3
"""Time structure of a series: change points with a toy-calibrated false-alarm rate, and lags between two series with
a look-elsewhere correction and hysteresis (S9).

changepoint: y_i = mu(t_i) + e_i with mu piecewise constant.
  segmentation  binary segmentation on the step statistic z_k (core/stats/change_point.py); the threshold is the
                (1 - alpha) quantile of max_k z_k over null toys, so P(any change | none) = alpha.
  pelt          optimal partitioning with a penalty per change (the PELT objective, solved exactly by dynamic
                programming over at most --max-changes changes): segment cost sum w (y - weighted mean)^2; the
                penalty is the (1 - alpha) quantile, over null toys, of max_K (C_0 - C_K) / K, the smallest penalty
                at which a toy would show no change.
  Null toys are N(0, C) with the declared covariance C (correlated noise), else independent N(0, sigma_i^2) and the
  output says "independence assumed": with correlated noise that underestimates the false-alarm rate.
lag: two series a(t), b(t) on the same even grid. r(l) = Pearson correlation of a_t and b_{t+l} over the overlap,
  l = -L..L (positive l: b later than a). The statistic is max_l |r(l)|; surrogates of b with randomized Fourier phases
  keep its power spectrum (autocorrelation) and break any relation to a; global p = (1 + #{surrogate max >= observed}) /
  (1 + N) includes the look-elsewhere effect over the 2L + 1 lags; local p is the same at the best lag only.
  --hysteresis-bins K: the series is split at the maximum of a into a rising and a falling branch; in K quantile bins of
  a, the mean of b on each branch and their difference (rising - falling) with standard errors, and a chi2 of the
  differences against zero.

Assumptions and validity: Gaussian noise with the stated sigma or covariance; segments are constant (a drift is not
a change point: fit a trend first); the lag test assumes stationary series on an even grid; hysteresis bins need at
least two points per branch.

Input JSON: changepoint {"times", "values", "errors" (or "covariance": [[n x n]])}; lag {"times", "a", "b"}.
Output JSON: "status" (ok, rejected, missing-dependency), "status_label", "inputs", "defaults_used", "label",
"warnings"; changepoint: "change_points" [{index, time, step}], "segments", "calibration" {method, threshold or
penalty, false_alarm_rate, toys, seed, toys_from, achieved_on_toys}; lag: "best_lag", "r_at_best", "global_p",
"local_p", "r" [{lag, r}], "look_elsewhere", "surrogates", "hysteresis" (when asked).
Exit codes: 0 ok; 2 bad input; 3 NumPy missing.
Run: python3 <plugin root>/skills/hep-statistics/scripts/time_structure.py changepoint --input series.json
         --method pelt --false-alarm 0.05 --toys 1000 --seed 1
     python3 <plugin root>/skills/hep-statistics/scripts/time_structure.py lag --input pair.json --max-lag 20
         --surrogates 1000 --seed 1 [--hysteresis-bins 5]
Requires NumPy (not needed for --help).
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

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats import change_point as cp  # noqa: E402
from core.stats.statistical_toys import chi2_sf  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
INDEPENDENCE = "independence assumed: no covariance declared, toys are independent N(0, sigma_i^2)"


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


# ------------------------------------------------------------------------------------------------ change points
def _prefix(np, y, w):
    """Prefix sums over the last axis: W, S1 = sum w y, S2 = sum w y^2 (y may be (toys, n))."""
    z = np.zeros(y.shape[:-1] + (1,))
    return (np.concatenate([[0.0], np.cumsum(w)]), np.concatenate([z, np.cumsum(w * y, axis=-1)], axis=-1),
            np.concatenate([z, np.cumsum(w * y * y, axis=-1)], axis=-1))


def _max_split(np, y, w, min_size):
    """max_k z_k for each row of y (toys, n), vectorized."""
    W, S1, _ = _prefix(np, y, w)
    n = y.shape[-1]
    k = np.arange(min_size, n - min_size + 1)
    w1, w2 = W[k], W[n] - W[k]
    m1 = S1[..., k] / w1
    m2 = (S1[..., [n]] - S1[..., k]) / w2
    return np.max(np.abs(m2 - m1) / np.sqrt(1 / w1 + 1 / w2), axis=-1)


def _cost_table(np, y, w, min_size, kmax):
    """C_K for K = 0..kmax changes (optimal partition, min segment size), for each row of y: shape (toys, kmax + 1)."""
    W, S1, S2 = _prefix(np, y, w)
    n = y.shape[-1]
    big = np.inf

    def cost(i, j):  # segment [i, j) for arrays of i (and a scalar j)
        ww = W[j] - W[i]
        s1 = S1[..., [j]] - S1[..., i]
        return (S2[..., [j]] - S2[..., i]) - s1 * s1 / ww
    rows = y.shape[0]
    D = np.full((kmax + 1, rows, n + 1), big)
    for j in range(min_size, n + 1):
        D[0][:, j] = cost(np.array([0]), j)[:, 0]
    for k in range(1, kmax + 1):
        for j in range((k + 1) * min_size, n + 1):
            i = np.arange(k * min_size, j - min_size + 1)
            D[k][:, j] = np.min(D[k - 1][:, i] + cost(i, j), axis=-1)
    return D[:, :, n].T, D


def _backtrack(np, y, w, min_size, kbest, D):
    W, S1, S2 = _prefix(np, y[None, :], w)
    n = y.shape[-1]
    cuts, j = [], n
    for k in range(kbest, 0, -1):
        i = np.arange(k * min_size, j - min_size + 1)
        ww = W[j] - W[i]
        s1 = S1[0, j] - S1[0, i]
        c = (S2[0, j] - S2[0, i]) - s1 * s1 / ww
        best = int(i[np.argmin(D[k - 1][0, i] + c)])
        cuts.append(best)
        j = best
    return sorted(cuts)


def changepoint(t, y, e, method, alpha, toys, seed, cov=None, min_size=2, max_changes=10) -> dict:
    import numpy as np
    t, y = np.asarray(t, dtype=float), np.asarray(y, dtype=float)
    n = len(y)
    warnings = []
    if cov is not None:
        C = np.asarray(cov, dtype=float)
        if C.shape != (n, n) or not np.all(np.isfinite(C)) or not np.allclose(C, C.T):
            raise InputError(f"covariance must be a symmetric finite {n} x {n} matrix")
        try:
            chol = np.linalg.cholesky(C)
        except np.linalg.LinAlgError as exc:
            raise InputError("covariance is not positive definite") from exc
        sigma = np.sqrt(np.diag(C))
        toys_from = "declared covariance"
    else:
        sigma = np.asarray(e, dtype=float)
        chol = None
        toys_from = "independent N(0, sigma_i^2)"
        warnings.append(INDEPENDENCE)
    if sigma.shape != (n,) or np.any(~np.isfinite(sigma)) or np.any(sigma <= 0):
        raise InputError("errors must be finite and > 0, one per value")
    if n < 2 * min_size:
        raise InputError("the series is too short for the minimum segment size")
    if not 0.0 < alpha < 1.0:
        raise InputError("--false-alarm must lie in (0, 1)")
    need = max(100, int(math.ceil(10.0 / alpha)))
    if toys < need:
        raise InputError(f"use at least max(100, 10 / alpha) = {need} toys")
    kmax = max(1, min(max_changes, n // min_size - 1))
    w = 1.0 / sigma ** 2
    rng = np.random.default_rng(seed)
    z = rng.normal(size=(toys, n))
    null = z @ chol.T if chol is not None else z * sigma
    q = int(math.ceil((1.0 - alpha) * toys)) - 1
    if method == "segmentation":
        stats = np.sort(_max_split(np, null, w, min_size))
        thr = float(stats[min(max(q, 0), toys - 1)])
        found = cp.binary_segmentation(y.tolist(), sigma.tolist(), thr, min_size, kmax)
        cuts = [c["index"] for c in found]
        calib = {"method": "segmentation", "threshold": thr}
        achieved = float(np.mean(stats > thr))
    elif method == "pelt":
        C0K, _ = _cost_table(np, null, w, min_size, kmax)
        ks = np.arange(1, kmax + 1)
        bstar = np.sort(np.max((C0K[:, [0]] - C0K[:, 1:]) / ks, axis=1))
        pen = float(bstar[min(max(q, 0), toys - 1)])
        CK, D = _cost_table(np, y[None, :], w, min_size, kmax)
        kbest = int(np.argmin(CK[0] + np.arange(kmax + 1) * pen))
        cuts = _backtrack(np, y, w, min_size, kbest, D) if kbest else []
        calib = {"method": "pelt", "penalty": pen, "max_changes": kmax}
        achieved = float(np.mean(bstar > pen))
    else:
        raise InputError("method must be segmentation or pelt")
    pc = cp.piecewise_constant(y.tolist(), sigma.tolist(), cuts)
    segs = pc["segments"]
    changes = [{"index": int(c), "time": float(t[c]), "step": segs[i + 1]["mean"] - segs[i]["mean"]}
               for i, c in enumerate(cuts)]
    calib.update(false_alarm_rate=alpha, toys=toys, seed=seed, toys_from=toys_from, min_size=min_size,
                 achieved_on_toys=achieved, toy_uncertainty=math.sqrt(alpha * (1 - alpha) / toys))
    return {"change_points": changes, "segments": segs, "chi2": pc["chi2"], "ndf": pc["ndf"], "calibration": calib,
            "warnings": warnings, "label": LABEL}


# ------------------------------------------------------------------------------------------------ lags
def _xcorr(np, a, b, lags):
    out = []
    n = len(a)
    for lag in lags:
        aa, bb = (a[:n - lag], b[lag:]) if lag >= 0 else (a[-lag:], b[:n + lag])
        aa, bb = aa - aa.mean(), bb - bb.mean()
        den = math.sqrt(float(aa @ aa) * float(bb @ bb))
        out.append(float(aa @ bb) / den if den > 0 else 0.0)
    return np.array(out)


def _phase_surrogate(np, rng, b):
    n = len(b)
    f = np.fft.rfft(b - b.mean())
    ph = rng.uniform(0, 2 * np.pi, len(f))
    ph[0] = 0.0
    if n % 2 == 0:
        ph[-1] = 0.0
    return np.fft.irfft(np.abs(f) * np.exp(1j * ph), n) + b.mean()


def _hysteresis(np, a, b, bins):
    k = int(np.argmax(a))
    if k < 2 or k > len(a) - 3:
        raise InputError("hysteresis needs a maximum of a inside the series (two branches)")
    edges = np.quantile(a, np.linspace(0, 1, bins + 1))
    rows, chi2, used = [], 0.0, 0
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (a >= lo) & (a <= hi)
        r, f = b[:k + 1][sel[:k + 1]], b[k + 1:][sel[k + 1:]]
        if len(r) < 2 or len(f) < 2:
            rows.append({"a_range": [float(lo), float(hi)], "difference": None, "note": "fewer than two points"})
            continue
        d = float(r.mean() - f.mean())
        err = math.sqrt(float(r.var(ddof=1)) / len(r) + float(f.var(ddof=1)) / len(f))
        rows.append({"a_range": [float(lo), float(hi)], "rising_mean": float(r.mean()), "falling_mean": float(f.mean()),
                     "difference": d, "error": err, "n_rising": int(len(r)), "n_falling": int(len(f))})
        if err > 0:
            chi2 += (d / err) ** 2
            used += 1
    return {"split_index": k, "bins": rows, "chi2": chi2, "ndf": used,
            "p_value": chi2_sf(chi2, used) if used else None,
            "definition": "difference = mean b on the rising branch - mean b on the falling branch, per bin of a"}


def lag(t, a, b, max_lag, surrogates, seed, hysteresis_bins=None) -> dict:
    import numpy as np
    t, a, b = (np.asarray(v, dtype=float) for v in (t, a, b))
    n = len(t)
    if a.shape != (n,) or b.shape != (n,) or n < 8:
        raise InputError("times, a and b must have the same length (>= 8)")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise InputError("times, a and b must be finite")
    dt = np.diff(t)
    if np.any(dt <= 0) or not np.allclose(dt, dt[0], rtol=1e-9, atol=0):
        raise InputError("lag needs an even, increasing time grid")
    if not 1 <= max_lag < n // 2:
        raise InputError("--max-lag must be between 1 and n / 2")
    if surrogates < 1:
        raise InputError("--surrogates must be >= 1")
    lags = list(range(-max_lag, max_lag + 1))
    r = _xcorr(np, a, b, lags)
    k = int(np.argmax(np.abs(r)))
    stat, at_best = float(np.abs(r).max()), float(abs(r[k]))
    rng = np.random.default_rng(seed)
    g = loc = 0
    for _ in range(surrogates):
        rs = _xcorr(np, a, _phase_surrogate(np, rng, b), lags)
        g += float(np.abs(rs).max()) >= stat
        loc += float(abs(rs[k])) >= at_best
    out = {"best_lag": lags[k], "best_lag_time": float(lags[k] * dt[0]), "r_at_best": float(r[k]),
           "global_p": (1 + g) / (1 + surrogates), "local_p": (1 + loc) / (1 + surrogates),
           "r": [{"lag": lg, "r": float(v)} for lg, v in zip(lags, r)], "surrogates": surrogates,
           "look_elsewhere": f"global p includes the {len(lags)} lags -{max_lag}..{max_lag}",
           "method": "phase-randomized surrogates of b (power spectrum kept)", "convention": "positive lag: b later",
           "warnings": [], "label": LABEL}
    if hysteresis_bins:
        out["hysteresis"] = _hysteresis(np, a, b, hysteresis_bins)
    return out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    c = sub.add_parser("changepoint", help="change points with a toy-calibrated false-alarm rate")
    c.add_argument("--input", required=True)
    c.add_argument("--method", required=True, choices=("segmentation", "pelt"))
    c.add_argument("--false-alarm", type=float, required=True, dest="false_alarm")
    c.add_argument("--toys", type=int, required=True)
    c.add_argument("--seed", type=int)
    c.add_argument("--min-segment", type=int, default=2, dest="min_segment")
    c.add_argument("--max-changes", type=int, default=10, dest="max_changes")
    lg = sub.add_parser("lag", help="cross-correlation lag with surrogates; hysteresis")
    lg.add_argument("--input", required=True)
    lg.add_argument("--max-lag", type=int, required=True, dest="max_lag")
    lg.add_argument("--surrogates", type=int, required=True)
    lg.add_argument("--seed", type=int)
    lg.add_argument("--hysteresis-bins", type=int, dest="hysteresis_bins")
    for p in (c, lg):
        add_status_argument(p)
    args = ap.parse_args(argv)
    given = {x.split("=")[0] for x in (sys.argv[1:] if argv is None else argv) if x.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status", "min-segment", "max-changes") if hasattr(args, k.replace("-", "_"))
                and f"--{k}" not in given]
    status, body = "ok", {}
    try:
        if args.seed is None:
            raise InputError("--seed is required")
        try:
            import numpy  # noqa: F401
        except ImportError:
            status, body = "missing-dependency", {"error": "NumPy is required: pip install numpy"}
        else:
            doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise InputError("the input must be a JSON object")
            if args.command == "changepoint":
                if args.min_segment < 1 or args.max_changes < 1:
                    raise InputError("--min-segment and --max-changes must be >= 1")
                if "values" not in doc or "times" not in doc or ("errors" not in doc and "covariance" not in doc):
                    raise InputError("changepoint needs times, values and errors (or covariance)")
                body = changepoint(doc["times"], doc["values"], doc.get("errors"), args.method, args.false_alarm,
                                   args.toys, args.seed, doc.get("covariance"), args.min_segment, args.max_changes)
            else:
                if args.hysteresis_bins is not None and args.hysteresis_bins < 1:
                    raise InputError("--hysteresis-bins must be >= 1")
                if any(k not in doc for k in ("times", "a", "b")):
                    raise InputError("lag needs times, a and b")
                body = lag(doc["times"], doc["a"], doc["b"], args.max_lag, args.surrogates, args.seed,
                           args.hysteresis_bins)
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, cp.ChangePointError, ValueError, TypeError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **body}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
