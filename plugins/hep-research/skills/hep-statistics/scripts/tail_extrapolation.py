#!/usr/bin/env python3
"""Extrapolation of a falling background tail from a control region into a signal region, with validation (S8).

Method: the binned control-region (CR) counts are fitted by Poisson maximum likelihood with each declared model family
  exponential   N lam exp(-lam (x - x0))                (x0 the CR edge nearer the start of the variable)
  power-law     N (gamma - 1) / x0 (x / x0)^(-gamma)     (x > 0)
  exp+power     the sum of the two (four parameters)
  plugin        bin_integral(theta, lo, hi) and START from a user file, only with --allow-plugin
integrated exactly over each bin. Parameters are fitted in log space (all positive); the covariance is the inverse
Hessian of the negative log-likelihood (numerical), and the signal-region (SR) prediction and its statistical
uncertainty follow by the delta method. Each model is validated first on a pseudo signal region cut from the CR (the
validation region VR, at the CR edge facing the SR): the model is refitted without the VR and its VR prediction is
compared with the observed VR count by a two-sided Poisson p-value with the prediction's uncertainty folded in
(Gauss-Hermite average over a Gaussian prediction, truncated at zero). A model passes when p >= validation_alpha.
The envelope runs over the models that pass: low and high are the smallest and largest central SR predictions; the
interval [min(mu - z sigma), max(mu + z sigma)] at the declared cl includes the statistical uncertainty. The envelope
is not converted into a Gaussian unless "envelope_prescription" says how ("half-range": sigma = (high - low) / 2;
"uniform": sigma = (high - low) / sqrt(12)); that choice belongs to the analysis, not to this tool.
Then hand over to core/stats: the output lists the background inputs for <plugin root>/core/stats/poisson_diagnostics.py
cls-limit and <plugin root>/core/stats/likelihood_limits.py profile-cls (the SR count stays blinded: N_OBS).

Assumptions and validity: the CR and SR follow the same smooth shape; bins are fine enough that the shape is
resolved; the VR test has power only against deviations the VR can show. A warning is printed when the far edge of
the SR lies more than max_extrapolation from the CR. A failed fit or a failed validation of the nominal model makes
the run `failed` (exit 1): its prediction is not a background estimate.

Input JSON: {"variable": TEXT, "edges": [increasing bin edges], "counts": [one count per bin],
             "control_region": [lo, hi], "validation_region": [lo, hi] (inside the CR, at the edge facing the SR),
             "signal_region": [lo, hi] (outside the CR), every boundary a bin edge,
             "models": ["exponential", "power-law", "exp+power", "plugin"], "nominal": MODEL,
             "max_extrapolation": DISTANCE, "validation_alpha": ALPHA, "cl": CL (two-sided, e.g. 0.6827),
             "envelope_prescription": "half-range" | "uniform" (optional), "plugin": PATH (with "plugin" in models)}
Output JSON: "status" (ok, failed, rejected, missing-dependency), "status_label" (--status, default unvalidated),
"inputs", "defaults_used", "models" {MODEL: {parameters, fit, signal_region {prediction, sigma_stat},
validation {observed, predicted, sigma, p_value, passed}}}, "envelope" {low, high, interval, models,
gaussian_sigma, note}, "handover", "warnings", "method_kind", "label".
Exit codes: 0 ok; 1 failed (the nominal model's fit or validation failed); 2 bad input; 3 NumPy or SciPy missing.
Run: python3 <plugin root>/skills/hep-statistics/scripts/tail_extrapolation.py --input tail.json [--allow-plugin]
Requires NumPy and SciPy (not needed for --help).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root
from core.status import add_status_argument, exit_code  # noqa: E402

LABEL = "[General method]"
FAMILIES = ("exponential", "power-law", "exp+power", "plugin")
PRESCRIPTIONS = {"half-range": 2.0, "uniform": math.sqrt(12.0)}


class InputError(ValueError):
    """A refused input (exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


# ------------------------------------------------------------------ model families (bin integrals)

def _exp_int(n, lam, x0, lo, hi):
    return n * (math.exp(-lam * (lo - x0)) - math.exp(-lam * (hi - x0)))


def _pow_int(n, g, x0, lo, hi):
    if abs(g - 1.0) < 1e-9:
        return 0.0  # the normalized form has no mass on a finite range at gamma = 1 (the fit stays away from it)
    return n * ((lo / x0) ** (1.0 - g) - (hi / x0) ** (1.0 - g))


def _family(name: str, x0: float, plugin=None):
    """(bin_integral(theta, lo, hi), number of parameters, start from the CR counts)."""
    if name == "exponential":
        return (lambda t, lo, hi: _exp_int(t[0], t[1], x0, lo, hi)), 2
    if name == "power-law":
        return (lambda t, lo, hi: _pow_int(t[0], t[1], x0, lo, hi)), 2
    if name == "exp+power":
        return (lambda t, lo, hi: _exp_int(t[0], t[1], x0, lo, hi) + _pow_int(t[2], t[3], x0, lo, hi)), 4
    return (lambda t, lo, hi: float(plugin.bin_integral(list(t), lo, hi))), len(plugin.START)


def _start(name, counts, centers, x0, plugin=None):
    import numpy as np
    total = float(sum(counts)) or 1.0
    c = np.asarray(counts, float) + 0.5
    xs = np.asarray(centers, float)
    slope = -np.polyfit(xs, np.log(c), 1)[0]
    lam = max(abs(slope), 1e-6)
    lslope = -np.polyfit(np.log(xs / x0), np.log(c), 1)[0]
    gamma = max(lslope + 1.0, 1.05)
    if name == "exponential":
        return [total, lam]
    if name == "power-law":
        return [total, gamma]
    if name == "exp+power":
        return [total / 2, lam, total / 2, gamma]
    return [float(v) for v in plugin.START]


# ------------------------------------------------------------------ input

def _region(doc, key, edges):
    r = doc.get(key)
    if not isinstance(r, list) or len(r) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in r):
        raise InputError(f"{key} must be [lo, hi]")
    lo, hi = float(r[0]), float(r[1])
    if not lo < hi or lo not in edges or hi not in edges:
        raise InputError(f"{key} boundaries must be bin edges with lo < hi")
    return lo, hi


def parse(doc: dict, base_dir: Path, allow_plugin: bool) -> dict:
    if not isinstance(doc, dict):
        raise InputError("the input must be a JSON object")
    edges, counts = doc.get("edges"), doc.get("counts")
    if not isinstance(edges, list) or len(edges) < 3 or not all(isinstance(e, (int, float)) for e in edges):
        raise InputError("edges must list at least three numbers")
    edges = [float(e) for e in edges]
    if any(b <= a for a, b in zip(edges, edges[1:])):
        raise InputError("edges must increase")
    if not isinstance(counts, list) or len(counts) != len(edges) - 1:
        raise InputError("counts must give one count per bin")
    for v in counts:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v != int(v):
            raise InputError("counts must be non-negative integers")
    cr, vr, sr = (_region(doc, k, edges) for k in ("control_region", "validation_region", "signal_region"))
    if not (cr[1] <= sr[0] or sr[1] <= cr[0]):
        raise InputError("the signal region must lie outside the control region")
    above = sr[0] >= cr[1]
    if not (cr[0] <= vr[0] and vr[1] <= cr[1]) or (vr[1] != cr[1] if above else vr[0] != cr[0]) or vr == cr:
        raise InputError("the validation region must lie inside the control region, at its edge facing the signal region")
    models = doc.get("models")
    if not isinstance(models, list) or not models or any(m not in FAMILIES for m in models) or len(set(models)) != len(models):
        raise InputError(f"models must list distinct families from {list(FAMILIES)}")
    if doc.get("nominal") not in models:
        raise InputError("nominal must be one of models")
    for key in ("max_extrapolation",):
        v = doc.get(key)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise InputError(f"{key} must be a number > 0 (no default)")
    alpha, cl = doc.get("validation_alpha"), doc.get("cl")
    for name, v in (("validation_alpha", alpha), ("cl", cl)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.0 < v < 1.0:
            raise InputError(f"{name} must lie in (0, 1) (no default)")
    presc = doc.get("envelope_prescription")
    if presc is not None and presc not in PRESCRIPTIONS:
        raise InputError(f"envelope_prescription must be one of {sorted(PRESCRIPTIONS)} or absent")
    x0 = cr[0]
    if any(m in ("power-law", "exp+power") for m in models) and min(cr[0], sr[0]) <= 0:
        raise InputError("a power law needs a positive variable")
    plugin = None
    if "plugin" in models:
        if not allow_plugin:
            raise InputError("a plugin model runs your Python file with your permissions; pass --allow-plugin")
        path = Path(str(doc.get("plugin", "")))
        path = path if path.is_absolute() else base_dir / path
        if not path.is_file():
            raise InputError(f"plugin file {path} not found")
        spec = importlib.util.spec_from_file_location("tail_extrapolation_plugin", path)
        plugin = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(plugin)  # type: ignore[union-attr]
        except Exception as exc:  # user code
            raise InputError(f"plugin {path} failed to load: {exc}") from exc
        if not callable(getattr(plugin, "bin_integral", None)) or not isinstance(getattr(plugin, "START", None), list):
            raise InputError("a plugin defines bin_integral(theta, lo, hi) and a START list")
    return {"edges": edges, "counts": [int(c) for c in counts], "cr": cr, "vr": vr, "sr": sr, "above": above,
            "models": models, "nominal": doc["nominal"], "max_extrapolation": float(doc["max_extrapolation"]),
            "alpha": float(alpha), "cl": float(cl), "prescription": presc, "x0": x0, "plugin": plugin,
            "variable": doc.get("variable")}


# ------------------------------------------------------------------ fit

def _bins(m, lo, hi):
    return [i for i, (a, b) in enumerate(zip(m["edges"], m["edges"][1:])) if a >= lo and b <= hi]


def _fit(m, name, idx):
    import numpy as np
    from scipy.optimize import minimize
    f, k = _family(name, m["x0"], m["plugin"])
    e, n = m["edges"], np.array([m["counts"][i] for i in idx], float)
    centers = [(e[i] + e[i + 1]) / 2 for i in idx]

    def nll(lt):
        t = np.exp(lt)
        try:
            mu = np.array([f(t, e[i], e[i + 1]) for i in idx], float)
        except (OverflowError, ValueError, ZeroDivisionError):
            return 1e300
        if not np.all(np.isfinite(mu)) or np.any(mu <= 0):
            return 1e300
        return float(np.sum(mu - n * np.log(mu)))
    start = np.log(np.maximum(np.asarray(_start(name, list(n), centers, m["x0"], m["plugin"]), float), 1e-12))
    best = None
    for method in ("Nelder-Mead", "BFGS"):
        res = minimize(nll, start if best is None else best.x, method=method,
                       options={"maxiter": 20000, "xatol": 1e-10, "fatol": 1e-12} if method == "Nelder-Mead" else {"gtol": 1e-8})
        if best is None or res.fun <= best.fun:
            best = res
    lt = best.x
    h = _hessian(nll, lt)
    try:
        cov = np.linalg.inv(h)
        ok = bool(np.all(np.isfinite(cov)) and np.all(np.linalg.eigvalsh((cov + cov.T) / 2) > 0) and best.fun < 1e299)
    except np.linalg.LinAlgError:
        cov, ok = None, False
    return {"f": f, "log_theta": lt, "cov": cov, "ok": ok, "nll": float(best.fun), "k": k}


def _hessian(fun, x, rel=1e-4):
    import numpy as np
    x = np.asarray(x, float)
    k = len(x)
    h = np.zeros((k, k))
    step = rel * np.maximum(np.abs(x), 1.0)
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.zeros(k), np.zeros(k)
            ei[i], ej[j] = step[i], step[j]
            v = (fun(x + ei + ej) - fun(x + ei - ej) - fun(x - ei + ej) + fun(x - ei - ej)) / (4 * step[i] * step[j])
            h[i, j] = h[j, i] = v
    return h


def _predict(fit, lo, hi):
    """Integral over [lo, hi] and its delta-method sigma."""
    import numpy as np
    lt = fit["log_theta"]

    def g(v):
        return fit["f"](np.exp(v), lo, hi)
    mu = g(lt)
    if fit["cov"] is None:
        return mu, None
    grad = np.array([(g(lt + d) - g(lt - d)) / (2 * d[i]) for i, d in
                     enumerate(np.eye(len(lt)) * 1e-6 * np.maximum(np.abs(lt), 1.0))])
    var = float(grad @ fit["cov"] @ grad)
    return float(mu), math.sqrt(max(var, 0.0))


def _pvalue(n_obs: int, mu: float, sigma: float) -> float:
    """Two-sided p-value of n_obs for a Poisson mean known to mu +- sigma (Gauss-Hermite average, truncated at 0)."""
    import numpy as np
    from scipy.stats import poisson
    nodes, weights = np.polynomial.hermite_e.hermegauss(40)
    means = np.maximum(mu + sigma * nodes, 1e-300)
    w = weights / weights.sum()
    lower = float(np.sum(w * poisson.cdf(n_obs, means)))
    upper = float(np.sum(w * poisson.sf(n_obs - 1, means)))
    return min(1.0, 2.0 * min(lower, upper))


def _validation(m, name):
    cr, vr = m["cr"], m["vr"]
    keep = [i for i in _bins(m, *cr) if i not in _bins(m, *vr)]
    fit = _fit(m, name, keep)
    n_vr = int(sum(m["counts"][i] for i in _bins(m, *vr)))
    if not fit["ok"]:
        return {"observed": n_vr, "predicted": None, "sigma": None, "p_value": None, "passed": False,
                "reason": "the fit without the validation region failed"}, fit
    mu, sig = _predict(fit, *vr)
    p = _pvalue(n_vr, mu, sig or 0.0)
    return {"observed": n_vr, "predicted": mu, "sigma": sig, "p_value": p, "passed": p >= m["alpha"]}, fit


def analyse(doc: dict, base_dir: Path | None = None, allow_plugin: bool = False) -> dict:
    from statistics import NormalDist
    m = parse(doc, base_dir or Path.cwd(), allow_plugin)
    z = NormalDist().inv_cdf(0.5 + m["cl"] / 2)
    out_models, warnings = {}, []
    for name in m["models"]:
        fit = _fit(m, name, _bins(m, *m["cr"]))
        val, _ = _validation(m, name)
        entry: dict = {"fit": {"converged": fit["ok"], "nll": fit["nll"]},
                       "parameters": [float(v) for v in __import__("numpy").exp(fit["log_theta"])],
                       "validation": val}
        if fit["ok"]:
            mu, sig = _predict(fit, *m["sr"])
            entry["signal_region"] = {"prediction": mu, "sigma_stat": sig,
                                      "interval": [mu - z * sig, mu + z * sig] if sig is not None else None}
        else:
            entry["signal_region"] = None
        out_models[name] = entry
    distance = (m["sr"][1] - m["cr"][1]) if m["above"] else (m["cr"][0] - m["sr"][0])
    if distance > m["max_extrapolation"]:
        warnings.append(f"extrapolation over {distance:g} exceeds the declared max_extrapolation {m['max_extrapolation']:g}")
    usable = [k for k, v in out_models.items() if v["signal_region"] and v["validation"]["passed"]]
    if not usable:
        warnings.append("no model passed its validation; the envelope is empty")
        env: dict = {"low": None, "high": None, "interval": None, "models": [], "gaussian_sigma": None}
    else:
        mus = [out_models[k]["signal_region"]["prediction"] for k in usable]
        ivs = [out_models[k]["signal_region"]["interval"] or [out_models[k]["signal_region"]["prediction"]] * 2 for k in usable]
        env = {"low": min(mus), "high": max(mus), "interval": [min(i[0] for i in ivs), max(i[1] for i in ivs)],
               "models": usable, "gaussian_sigma": None}
        if m["prescription"]:
            env["gaussian_sigma"] = (env["high"] - env["low"]) / PRESCRIPTIONS[m["prescription"]]
    env["cl"] = m["cl"]
    env["note"] = ("the envelope between models is not converted into a Gaussian" if not m["prescription"] else
                   f"the envelope was converted with the declared prescription '{m['prescription']}'")
    nom = out_models[m["nominal"]]
    failed = nom["signal_region"] is None or not nom["validation"]["passed"]
    handover = None
    if not failed:
        b, s = nom["signal_region"]["prediction"], nom["signal_region"]["sigma_stat"] or 0.0
        s_tot = math.hypot(s, env["gaussian_sigma"]) if env["gaussian_sigma"] is not None else None
        handover = {"b": b, "sigma_b_stat": s, "sigma_b_with_prescription": s_tot,
                    "commands": [f"python3 <plugin root>/core/stats/poisson_diagnostics.py cls-limit --n N_OBS --b {b:.6g} "
                                 f"--sigma-b {s_tot if s_tot is not None else s:.6g}",
                                 f"python3 <plugin root>/core/stats/likelihood_limits.py profile-cls --n N_OBS --b {b:.6g} "
                                 f"--sigma-b {s_tot if s_tot is not None else s:.6g} --seed S"],
                    "note": "the statistical sigma only, unless an envelope prescription is declared; the envelope "
                            "itself is a model uncertainty to state next to the limit"}
    return {"variable": m["variable"], "models": out_models, "envelope": env, "handover": handover, "warnings": warnings,
            "nominal": m["nominal"], "failed": failed, "method_kind": "binned Poisson maximum likelihood, delta method",
            "label": LABEL}


def validation_power(doc: dict, name: str) -> float:
    """Probability that `name` fails validation when the data are Poisson around the given counts (an Asimov data
    set of the true model): the model is fitted to the Asimov counts without the VR, and the rejection probability of
    the VR test is summed over the Poisson distribution of the true VR count."""
    from scipy.stats import poisson
    d = dict(doc)
    m = parse(dict(d, counts=[round(c) for c in d["counts"]]), Path.cwd(), False)
    m["counts"] = list(d["counts"])  # exact Asimov expectations for the fit
    keep = [i for i in _bins(m, *m["cr"]) if i not in _bins(m, *m["vr"])]
    fit = _fit(m, name, keep)
    mu, sig = _predict(fit, *m["vr"])
    true = sum(d["counts"][i] for i in _bins(m, *m["vr"]))
    lo, hi = int(max(0, true - 10 * math.sqrt(true) - 10)), int(true + 10 * math.sqrt(true) + 10)
    return float(sum(poisson.pmf(n, true) for n in range(lo, hi + 1) if _pvalue(n, mu, sig or 0.0) < m["alpha"]))


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="JSON input (format above)")
    ap.add_argument("--allow-plugin", action="store_true", help="run the user file named by 'plugin' (your code)")
    add_status_argument(ap)
    args = ap.parse_args(argv)
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    defaults = [k for k in ("status",) if f"--{k}" not in given]
    status, body = "ok", {}
    try:
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            status, body = "missing-dependency", {"error": "NumPy and SciPy are required: pip install numpy scipy"}
        else:
            path = Path(args.input)
            body = analyse(json.loads(path.read_text(encoding="utf-8")), path.resolve().parent, args.allow_plugin)
            if body.pop("failed"):
                status = "failed"
    except OSError as exc:
        status, body = "rejected", {"error": f"cannot read {args.input}: {exc}"}
    except (InputError, ValueError, TypeError) as exc:
        status, body = "rejected", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults, **body},
                     indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
