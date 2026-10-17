#!/usr/bin/env python3
"""Periodicity in an unevenly sampled series with known uncertainties: weighted generalized Lomb-Scargle with a
surrogate-calibrated, band-maximum global significance (S5).

Method: the generalized Lomb-Scargle power with weights w_i = 1 / sigma_i^2 and a floating mean (Zechmeister and
Kuerster 2009) is p(f) = 1 - chi2(c + a cos 2 pi f t + b sin 2 pi f t) / chi2(c), in [0, 1]. The test statistic is the
largest power inside a declared frequency band (the band-maximum). Its null distribution comes from surrogate series
drawn under a declared noise model, with the same times and uncertainties:
  white  y* = weighted mean + N(0, sigma_i^2);
  ar1    red noise on the sample index: phi = lag-1 autocorrelation of the mean-subtracted series, a stationary AR(1)
         with the series' variance (for nearly even sampling);
  ou     red noise in time (Ornstein-Uhlenbeck): tau = -mean(dt) / ln(phi), the same stationary variance (uneven
         sampling).
global p = (1 + #{surrogates with band-maximum >= observed}) / (1 + N); the trials over frequencies inside the band
are included by construction. The search over the noise model is not: the null model is declared, not chosen after
looking.
Caps (validated range; overridable with --allow-outside-validated-range, outputs then labeled outside-validated-range):
points N <= 1e5, frequencies F <= 1e4, surrogates <= 1e4.

Assumptions and validity: Gaussian uncertainties; a red-noise null is a model estimated from the same series, so a
strong periodic signal inflates phi and makes the test conservative; the frequency grid must resolve peaks (step
<= 1 / (5 T) for a span T).

Input JSON: {"times": [...], "values": [...], "errors": [...] (> 0), "frequencies": {"min", "max", "n"} or [...],
             "band": [f_lo, f_hi] (optional; default the whole grid, reported in defaults_used)}
Output JSON: "status" (ok, rejected, missing-dependency), "status_label", "inputs", "defaults_used", "best"
{frequency, period, power}, "band", "global" {p, surrogates, statistic}, "null_model" {kind, phi | tau, variance},
"verdict" (periodicity or no-periodicity with --alpha, else null), "method_kind" (surrogate-calibrated), "label",
and the caps record when overridden.
Exit codes: 0 ok (a detection is a result); 2 bad input or a cap exceeded without the override; 3 NumPy missing.
Run: python3 <plugin root>/skills/hep-statistics/scripts/periodicity_scan.py --input series.json --null ar1
     --surrogates 1000 --seed 1 [--alpha 0.01]
Requires NumPy (not needed for --help).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.stats import _caps  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
CAPS = {"points": 100_000, "frequencies": 10_000, "surrogates": 10_000}
NULLS = ("white", "ar1", "ou")


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def gls_power(t, y, e, freqs, chunk=256):
    """Generalized Lomb-Scargle power for each frequency (vectorized in chunks of frequencies)."""
    import numpy as np
    w = 1.0 / e ** 2
    w = w / w.sum()
    ybar = float(np.sum(w * y))
    yy = float(np.sum(w * (y - ybar) ** 2))
    out = np.empty(len(freqs))
    for s in range(0, len(freqs), chunk):
        om = 2 * np.pi * np.asarray(freqs[s:s + chunk])[:, None]
        c, sn = np.cos(om * t), np.sin(om * t)
        C, S = c @ w, sn @ w
        YC = c @ (w * y) - ybar * C
        YS = sn @ (w * y) - ybar * S
        CC = (c * c) @ w - C * C
        SS = (sn * sn) @ w - S * S
        CS = (c * sn) @ w - C * S
        D = CC * SS - CS * CS
        with np.errstate(divide="ignore", invalid="ignore"):
            p = (SS * YC * YC + CC * YS * YS - 2 * CS * YC * YS) / (yy * D)
        out[s:s + chunk] = np.where(D > 1e-15, p, 0.0)
    return out


def _null(np, t, y, e, kind):
    w = 1.0 / e ** 2
    mean = float(np.sum(w * y) / np.sum(w))
    if kind == "white":
        return {"kind": "white", "mean": mean}
    r = y - mean
    var = float(np.mean(r * r))
    phi = float(np.sum(r[:-1] * r[1:]) / np.sum(r * r)) if np.sum(r * r) > 0 else 0.0
    phi = min(max(phi, -0.99), 0.99)
    if kind == "ar1":
        return {"kind": "ar1", "mean": mean, "phi": phi, "variance": var}
    dt = float(np.mean(np.diff(t)))
    tau = -dt / math.log(phi) if phi > 0 else dt * 1e-3
    return {"kind": "ou", "mean": mean, "tau": tau, "variance": var}


def _surrogate(np, rng, t, e, model):
    n = len(t)
    if model["kind"] == "white":
        return model["mean"] + rng.normal(0.0, e)
    sd = math.sqrt(max(model["variance"], 1e-300))
    x = np.empty(n)
    x[0] = rng.normal(0.0, sd)
    if model["kind"] == "ar1":
        a = model["phi"]
        innov = sd * math.sqrt(1 - a * a)
        z = rng.normal(0.0, 1.0, n)
        for i in range(1, n):
            x[i] = a * x[i - 1] + innov * z[i]
    else:
        z = rng.normal(0.0, 1.0, n)
        for i in range(1, n):
            a = math.exp(-(t[i] - t[i - 1]) / model["tau"])
            x[i] = a * x[i - 1] + sd * math.sqrt(1 - a * a) * z[i]
    return model["mean"] + x


def scan(t, y, e, freqs, band, null, surrogates, seed) -> dict:
    import numpy as np
    t, y, e, freqs = (np.asarray(v, dtype=float) for v in (t, y, e, freqs))
    lo, hi = (float(freqs.min()), float(freqs.max())) if band is None else (float(band[0]), float(band[1]))
    inband = (freqs >= lo) & (freqs <= hi)
    if not inband.any():
        raise InputError("the band contains no frequency of the grid")
    p = gls_power(t, y, e, freqs)
    k = int(np.argmax(np.where(inband, p, -1.0)))
    stat = float(p[k])
    model = _null(np, t, y, e, null)
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in _caps.timed_range(surrogates, "periodicity surrogates"):
        ys = _surrogate(np, rng, t, e, model)
        ps = gls_power(t, ys, e, freqs[inband])
        exceed += float(ps.max()) >= stat
    return {"best": {"frequency": float(freqs[k]), "period": 1.0 / float(freqs[k]) if freqs[k] > 0 else None,
                     "power": stat},
            "band": [lo, hi], "global": {"p": (1 + exceed) / (1 + surrogates), "surrogates": surrogates,
                                         "statistic": "largest generalized Lomb-Scargle power in the band"},
            "null_model": model, "method_kind": "surrogate-calibrated", "label": LABEL}


def _load(np, doc):
    try:
        t, y, e = (np.asarray(doc[k], dtype=float) for k in ("times", "values", "errors"))
    except KeyError as exc:
        raise InputError(f"missing {exc}") from exc
    if t.ndim != 1 or t.shape != y.shape or t.shape != e.shape or len(t) < 4:
        raise InputError("times, values and errors must be lists of the same length (>= 4)")
    if not (np.all(np.isfinite(t)) and np.all(np.isfinite(y)) and np.all(np.isfinite(e))) or np.any(e <= 0):
        raise InputError("times and values must be finite and errors > 0")
    if np.any(np.diff(t) <= 0):
        raise InputError("times must be strictly increasing")
    fr = doc.get("frequencies")
    if isinstance(fr, dict):
        try:
            lo, hi, n = float(fr["min"]), float(fr["max"]), int(fr["n"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InputError("frequencies needs min, max and n") from exc
        if not (0 < lo < hi and n >= 2):
            raise InputError("frequencies needs 0 < min < max and n >= 2")
        if n > CAPS["frequencies"]:
            _caps.exceed("periodicity frequencies", n, CAPS["frequencies"], InputError,
                         f"at most {CAPS['frequencies']} frequencies")
        freqs = np.linspace(lo, hi, n)
    elif isinstance(fr, list) and fr:
        freqs = np.asarray(fr, dtype=float)
        if not np.all(np.isfinite(freqs)) or np.any(freqs <= 0):
            raise InputError("frequencies must be positive")
        if len(freqs) > CAPS["frequencies"]:
            _caps.exceed("periodicity frequencies", len(freqs), CAPS["frequencies"], InputError,
                         f"at most {CAPS['frequencies']} frequencies")
    else:
        raise InputError("give frequencies as {min, max, n} or a list")
    if len(t) > CAPS["points"]:
        _caps.exceed("periodicity points", len(t), CAPS["points"], InputError, f"at most {CAPS['points']} points")
    band = doc.get("band")
    if band is not None:
        if not (isinstance(band, list) and len(band) == 2 and all(isinstance(b, (int, float)) for b in band)
                and band[0] < band[1]):
            raise InputError("band must be [f_lo, f_hi] with f_lo < f_hi")
    return t, y, e, freqs, band


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="JSON with times, values, errors, frequencies, band")
    ap.add_argument("--null", required=True, choices=NULLS, help="noise model of the surrogates (no default)")
    ap.add_argument("--surrogates", type=int, required=True, help="number of surrogate series")
    ap.add_argument("--seed", type=int, help="seed of the surrogates (required)")
    ap.add_argument("--alpha", type=float, help="test size for a verdict; without it only the p-value is reported")
    _caps.add_argument(ap)
    add_status_argument(ap)
    args = ap.parse_args(argv)
    _caps.allow_outside(args.allow_outside_validated_range)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status", "alpha") if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        if args.seed is None:
            raise InputError("--seed is required")
        if args.surrogates < 1:
            raise InputError("--surrogates must be >= 1")
        if args.alpha is not None and not (0.0 < args.alpha < 1.0):
            raise InputError("--alpha must lie in (0, 1)")
        try:
            import numpy as np
        except ImportError:
            status, body = "missing-dependency", {"error": "NumPy is required: pip install numpy"}
        else:
            doc = json.loads(Path(args.input).read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                raise InputError("the input must be a JSON object")
            if args.surrogates > CAPS["surrogates"]:
                _caps.exceed("periodicity surrogates", args.surrogates, CAPS["surrogates"], InputError,
                             f"at most {CAPS['surrogates']} surrogates")
            t, y, e, freqs, band = _load(np, doc)
            if band is None:
                defaults.append("band")
            body = scan(t, y, e, freqs, band, args.null, args.surrogates, args.seed)
            body["verdict"] = None if args.alpha is None else (
                "periodicity" if body["global"]["p"] < args.alpha else "no-periodicity")
            body.update(_caps.report())
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **body}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
