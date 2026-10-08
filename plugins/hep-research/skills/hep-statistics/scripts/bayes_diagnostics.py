#!/usr/bin/env python3
"""Convergence diagnostics for MCMC chains, prior-sensitivity reweighting, and a demonstration sampler.

Purpose: the Bayesian invariant "state the priors, the sampler and its convergence diagnostics" needs numbers. This
script computes them for chains you supply; it is not a sampler package. Needs NumPy.

Subcommands:
  diagnose   chains from JSON {"param": [[chain 1 draws], [chain 2 draws], ...], ...} or a .npy array of shape
             (chains, draws) or (chains, draws, params). Per parameter: rank-normalized split-R-hat (the maximum of
             the bulk and the folded, tail-sensitive versions), bulk ESS, tail ESS (the smaller ESS of the 5% and 95%
             quantile indicators), and the Monte Carlo standard error of requested quantiles (Vehtari, Gelman, Simpson,
             Carpenter, Buerkner 2021, Bayesian Analysis 16, doi:10.1214/20-BA1221). Status per parameter and overall:
             converged     R-hat < --rhat-max (1.01) and bulk and tail ESS >= --min-ess-per-chain (100) x chains;
             not-converged otherwise;
             incomplete    fewer than 2 chains or fewer than 50 draws per chain: the diagnostics cannot be computed
                           reliably (4 or more chains are recommended; fewer is flagged).
  reweight   importance-reweight posterior draws to another prior: JSON {"param": "mu", "draws": [...],
             "old_prior": PRIOR, "new_prior": PRIOR, "quantiles": [0.5, 0.95]} with PRIOR one of
             {"form": "uniform", "low", "high"}, {"form": "normal", "mean", "sd"}, {"form": "lognormal", "mu", "sigma"},
             {"form": "exponential", "rate"}, {"form": "gamma", "shape", "rate"}, {"form": "halfnormal", "sd"}.
             Reports the shift of each quantile and the weight ESS (sum w)^2 / sum w^2. When the weight ESS is below
             --min-ess-fraction (10% [Proposal]) of the draws, or the new prior puts mass where the old one had none,
             the result says a rerun is required: reweighting cannot represent it.
  demo-sampler  a seeded random-walk Metropolis sampler for the counting model n ~ Pois(s + b), known b, flat prior
             on s >= 0 (the model of skills/hep-analysis/scripts/counting_reference.py). A DEMONSTRATION and test
             oracle only, not a production sampler. Prints the upper credible bound with its MCSE and the diagnostics;
             --artifact FILE writes a statistical-result (paradigm bayesian, status synthetic) with them.

Exit codes: 0 converged / ok; 1 not converged, or reweighting not representable; 2 rejected input; 3 incomplete.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

MIN_CHAINS, MIN_DRAWS, RECOMMENDED_CHAINS = 2, 50, 4


# ---------------------------------------------------------------- diagnostics (Vehtari et al. 2021)
def _normal_quantile(p):
    """Inverse standard normal CDF (Acklam's rational approximation refined by one Newton step)."""
    p = np.asarray(p, float)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    q = np.empty_like(p)
    lo, hi = p < 0.02425, p > 1 - 0.02425
    mid = ~(lo | hi)
    r = p[mid] - 0.5
    s = r * r
    q[mid] = (((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * r / \
             (((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1)
    for mask, sign, pp in ((lo, 1, p[lo]), (hi, -1, 1 - p[hi])):
        t = np.sqrt(-2 * np.log(pp))
        q[mask] = sign * (((((c[0] * t + c[1]) * t + c[2]) * t + c[3]) * t + c[4]) * t + c[5]) / \
            ((((d[0] * t + d[1]) * t + d[2]) * t + d[3]) * t + 1)
    erfc = np.vectorize(math.erfc)
    e = 0.5 * erfc(-q / math.sqrt(2)) - p
    return q - e * math.sqrt(2 * math.pi) * np.exp(q * q / 2)


def _rank_normalize(x):
    flat = x.ravel()
    order = flat.argsort(kind="mergesort")
    ranks = np.empty(flat.size)
    ranks[order] = np.arange(1, flat.size + 1)
    # average ranks over ties
    _, inv, counts = np.unique(flat, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / counts)[inv]
    return _normal_quantile((ranks - 3 / 8) / (flat.size + 1 / 4)).reshape(x.shape)


def _split(x):
    n = x.shape[1] // 2
    return np.concatenate([x[:, :n], x[:, x.shape[1] - n:]], axis=0)


def _rhat(x):
    m, n = x.shape
    w = x.var(axis=1, ddof=1).mean()
    b = n * x.mean(axis=1).var(ddof=1)
    if w <= 0:
        return math.inf if b > 0 else 1.0
    return math.sqrt(((n - 1) / n * w + b / n) / w)


def _autocov(chain):
    n = chain.size
    f = np.fft.rfft(chain - chain.mean(), n=2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n] / n
    return ac


def _ess(x):
    """ESS of chains x (m, n) with Geyer's initial monotone sequence on the multi-chain autocorrelation."""
    m, n = x.shape
    if n < 4:
        return float("nan")
    acov = np.array([_autocov(c) for c in x])
    chain_var = acov[:, 0] * n / (n - 1)
    w = chain_var.mean()
    var_plus = w * (n - 1) / n + (x.mean(axis=1).var(ddof=1) if m > 1 else 0.0)
    if var_plus <= 0:
        return float("nan")
    rho = 1 - (w - acov.mean(axis=0)) / var_plus
    rho[0] = 1.0
    t, total, prev = 0, 0.0, math.inf
    while t + 1 < n:
        pair = rho[t] + rho[t + 1]
        if pair < 0:
            break
        pair = min(pair, prev)               # monotone
        total += pair
        prev = pair
        t += 2
    tau = -1 + 2 * total
    tau = max(tau, 1 / math.log10(m * n))
    return m * n / tau


def diagnose_param(x, quantiles=(0.05, 0.5, 0.95)):
    x = np.asarray(x, float)
    m, n = x.shape
    flags = []
    if m < RECOMMENDED_CHAINS:
        flags.append(f"{m} chain(s): at least {RECOMMENDED_CHAINS} are recommended")
    if m < MIN_CHAINS or n < MIN_DRAWS:
        return {"chains": m, "draws_per_chain": n, "status": "incomplete",
                "flags": flags + [f"needs >= {MIN_CHAINS} chains and >= {MIN_DRAWS} draws per chain"]}
    if not np.all(np.isfinite(x)):
        return {"chains": m, "draws_per_chain": n, "status": "incomplete", "flags": flags + ["non-finite draws"]}
    xs = _split(x)
    z = _rank_normalize(xs)
    folded = _rank_normalize(np.abs(xs - np.median(xs)))
    rhat = max(_rhat(z), _rhat(folded))
    ess_bulk = _ess(z)
    q05, q95 = np.quantile(x, [0.05, 0.95])
    ess_tail = min(_ess(_split((x <= q05).astype(float))), _ess(_split((x >= q95).astype(float))))
    out_q = {}
    for p in quantiles:
        ind = _split((x <= np.quantile(x, p)).astype(float))
        e = _ess(ind)
        se_p = math.sqrt(p * (1 - p) / e) if e and e > 0 else float("nan")
        lo, hi = np.quantile(x, [max(p - se_p, 0.0), min(p + se_p, 1.0)])
        out_q[str(p)] = {"value": float(np.quantile(x, p)), "mcse": float((hi - lo) / 2), "ess": float(e)}
    return {"chains": m, "draws_per_chain": n, "rhat": float(rhat), "ess_bulk": float(ess_bulk),
            "ess_tail": float(ess_tail), "quantiles": out_q, "flags": flags}


def classify(res, rhat_max=1.01, min_ess_per_chain=100):
    if res.get("status") == "incomplete":
        return "incomplete"
    need = min_ess_per_chain * res["chains"]
    ok = res["rhat"] < rhat_max and res["ess_bulk"] >= need and res["ess_tail"] >= need
    if not ok:
        res["flags"].append(f"converged requires R-hat < {rhat_max} and bulk and tail ESS >= {need}")
    return "converged" if ok else "not-converged"


def diagnose(chains, quantiles, rhat_max, min_ess_per_chain):
    params = {}
    for name, x in chains.items():
        r = diagnose_param(x, quantiles)
        r["status"] = classify(r, rhat_max, min_ess_per_chain)
        params[name] = r
    statuses = {r["status"] for r in params.values()}
    overall = "incomplete" if "incomplete" in statuses else ("not-converged" if "not-converged" in statuses else "converged")
    return {"status": overall, "rhat_max": rhat_max, "min_ess_per_chain": min_ess_per_chain, "parameters": params,
            "method": "rank-normalized split-R-hat (bulk and folded), bulk and tail ESS, quantile MCSE; Vehtari et al. 2021"}


# ---------------------------------------------------------------- prior reweighting
def _log_prior(spec, x):
    f = spec.get("form")
    x = np.asarray(x, float)
    with np.errstate(divide="ignore", invalid="ignore"):
        if f == "uniform":
            lo, hi = float(spec["low"]), float(spec["high"])
            return np.where((x >= lo) & (x <= hi), -math.log(hi - lo), -np.inf)
        if f == "normal":
            mu, sd = float(spec["mean"]), float(spec["sd"])
            return -0.5 * ((x - mu) / sd) ** 2 - math.log(sd)
        if f == "halfnormal":
            sd = float(spec["sd"])
            return np.where(x >= 0, -0.5 * (x / sd) ** 2 - math.log(sd), -np.inf)
        if f == "lognormal":
            mu, s = float(spec["mu"]), float(spec["sigma"])
            return np.where(x > 0, -0.5 * ((np.log(x) - mu) / s) ** 2 - np.log(x) - math.log(s), -np.inf)
        if f == "exponential":
            r = float(spec["rate"])
            return np.where(x >= 0, math.log(r) - r * x, -np.inf)
        if f == "gamma":
            k, r = float(spec["shape"]), float(spec["rate"])
            return np.where(x > 0, (k - 1) * np.log(x) - r * x, -np.inf)
    raise ValueError(f"unknown prior form {f!r}")


def _support_exceeds(old, new):
    """True when the new prior has mass where the old prior has none (checked for the bounded forms)."""
    def bounds(s):
        f = s.get("form")
        if f == "uniform":
            return float(s["low"]), float(s["high"])
        if f == "normal":
            return -math.inf, math.inf
        return 0.0, math.inf
    (ol, oh), (nl, nh) = bounds(old), bounds(new)
    return nl < ol or nh > oh


def weighted_quantile(x, w, p):
    o = np.argsort(x)
    cw = np.cumsum(w[o])
    cw /= cw[-1]
    return float(np.interp(p, cw, x[o]))


def reweight(doc, min_ess_fraction=0.10):
    x = np.asarray(doc["draws"], float)
    if x.ndim != 1 or x.size < MIN_DRAWS or not np.all(np.isfinite(x)):
        raise ValueError(f"draws must be a finite flat list of at least {MIN_DRAWS} values")
    qs = [float(q) for q in doc.get("quantiles", [0.05, 0.5, 0.95])]
    lo_old = _log_prior(doc["old_prior"], x)
    if np.any(~np.isfinite(lo_old)):
        raise ValueError("some draws lie outside the old prior's support")
    lw = _log_prior(doc["new_prior"], x) - lo_old
    w = np.exp(lw - np.max(lw)) if np.any(np.isfinite(lw)) else np.zeros_like(x)
    ess = float(w.sum() ** 2 / np.sum(w * w)) if w.sum() > 0 else 0.0
    res = {"param": doc.get("param", "x"), "draws": int(x.size), "weight_ess": ess, "weight_ess_fraction": ess / x.size,
           "quantiles": {}}
    if w.sum() > 0:
        for p in qs:
            old_q = float(np.quantile(x, p))
            new_q = weighted_quantile(x, w, p)
            res["quantiles"][str(p)] = {"old": old_q, "new": new_q, "shift": new_q - old_q}
    problems = []
    if ess < min_ess_fraction * x.size:
        problems.append(f"weight ESS {ess:.1f} is below {min_ess_fraction:.0%} of the draws")
    if _support_exceeds(doc["old_prior"], doc["new_prior"]):
        problems.append("the new prior has support where the old prior had none")
    res["status"] = "rerun-required" if problems else "ok"
    if problems:
        res["reason"] = "; ".join(problems) + ": rerun the sampler with the new prior, do not reweight"
    return res, (1 if problems else 0)


# ---------------------------------------------------------------- demonstration sampler
def demo_sampler(n, b, chains, draws, seed, step=1.0, burn=1000):
    """Random-walk Metropolis for p(s | n) proportional to Pois(n | s + b), s >= 0. Demonstration only."""
    rng = np.random.default_rng(seed)
    out = np.empty((chains, draws))

    def logp(s):
        return -np.inf if s < 0 else (n * math.log(s + b) if n > 0 else 0.0) - (s + b)
    for c in range(chains):
        s = rng.exponential(1.0 + n)
        lp = logp(s)
        for i in range(burn + draws):
            prop = s + step * rng.normal()
            lq = logp(prop)
            if math.log(rng.random()) < lq - lp:
                s, lp = prop, lq
            if i >= burn:
                out[c, i - burn] = s
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog=__doc__.split("\n\n", 1)[1])
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("diagnose")
    d.add_argument("--input", required=True)
    d.add_argument("--quantiles", default="0.05,0.5,0.95")
    d.add_argument("--rhat-max", type=float, default=1.01)
    d.add_argument("--min-ess-per-chain", type=float, default=100)
    r = sub.add_parser("reweight")
    r.add_argument("--input", required=True)
    r.add_argument("--min-ess-fraction", type=float, default=0.10)
    s = sub.add_parser("demo-sampler")
    s.add_argument("--n", type=int, required=True)
    s.add_argument("--b", type=float, required=True)
    s.add_argument("--chains", type=int, default=4)
    s.add_argument("--draws", type=int, default=5000)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--cl", type=float, default=0.95)
    s.add_argument("--artifact")
    args = p.parse_args(argv)
    if np is None:
        print(json.dumps({"status": "rejected", "error": "NumPy is required"}))
        return 2
    try:
        if args.cmd == "diagnose":
            qs = tuple(float(v) for v in args.quantiles.split(","))
            if not all(0 < q < 1 for q in qs):
                raise ValueError("quantiles must lie in (0, 1)")
            src = Path(args.input)
            if src.suffix == ".npy":
                arr = np.load(src)
                if arr.ndim == 2:
                    chains = {"x": arr}
                elif arr.ndim == 3:
                    chains = {f"x{k}": arr[:, :, k] for k in range(arr.shape[2])}
                else:
                    raise ValueError("a .npy input must have shape (chains, draws) or (chains, draws, params)")
            else:
                raw = json.loads(src.read_text(encoding="utf-8"))
                if not isinstance(raw, dict) or not raw:
                    raise ValueError("JSON input must map parameter names to lists of chains")
                chains = {}
                for k, v in raw.items():
                    lens = {len(c) for c in v} if isinstance(v, list) and all(isinstance(c, list) for c in v) else set()
                    if len(lens) != 1:
                        raise ValueError(f"{k}: chains must be lists of equal length")
                    chains[k] = np.asarray(v, float)
            res = diagnose(chains, qs, args.rhat_max, args.min_ess_per_chain)
            code = {"converged": 0, "not-converged": 1, "incomplete": 3}[res["status"]]
        elif args.cmd == "reweight":
            if not 0 < args.min_ess_fraction < 1:
                raise ValueError("--min-ess-fraction must be in (0, 1)")
            res, code = reweight(json.loads(Path(args.input).read_text(encoding="utf-8")), args.min_ess_fraction)
        else:
            if args.n < 0 or args.b < 0 or args.chains < 1 or args.draws < 1 or not 0 < args.cl < 1:
                raise ValueError("need n >= 0, b >= 0, chains >= 1, draws >= 1, 0 < cl < 1")
            x = demo_sampler(args.n, args.b, args.chains, args.draws, args.seed)
            diag = diagnose({"s": x}, (args.cl,), 1.01, 100)
            q = diag["parameters"]["s"]
            res = {"label": "DEMONSTRATION sampler (random-walk Metropolis), a test oracle, not a production sampler",
                   "model": f"n ~ Pois(s + b), n = {args.n}, b = {args.b}, flat prior on s >= 0", "seed": args.seed,
                   "chains": args.chains, "draws_per_chain": args.draws, "upper_bound": q.get("quantiles", {}).get(str(args.cl)),
                   "cl": args.cl, "diagnostics": diag}
            code = {"converged": 0, "not-converged": 1, "incomplete": 3}[diag["status"]]
            if args.artifact:
                Path(args.artifact).write_text(json.dumps(_artifact(res, q, code), indent=1) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(res, indent=1))
    return code


def _artifact(res, q, code):
    from datetime import date
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from contracts import CONTRACTS_VERSION
    from contracts.identity import plugin_release
    plugin = json.loads((Path(__file__).resolve().parents[3] / ".claude-plugin" / "plugin.json").read_text())["version"]
    status = ["synthetic", "unvalidated"] + (["failed"] if code == 1 else [])
    return {
        "contract_version": CONTRACTS_VERSION, "artifact_id": "synthetic-demo-bayesian-counting",
        "artifact_type": "statistical-result",
        "objective": "SYNTHETIC demonstration of the Bayesian path: flat-prior upper bound for a counting model",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": plugin, "contracts": CONTRACTS_VERSION, "profiles": {}, "plugin_release": plugin_release()},
        "provenance": {"producer_skill": "hep-statistics", "created": date.today().isoformat(), "evidence_ids": []},
        "inputs": [], "outputs": [], "status": status, "unresolved_inputs": [],
        "extension": {
            "paradigm": "bayesian", "likelihood": {"form": "poisson", "model": res["model"]},
            "parameters_of_interest": ["s"], "nuisances": [],
            "priors": [{"parameter": "s", "form": "uniform[0, inf) (improper flat; posterior proper for this model)"}],
            "sampler": {"name": "random-walk Metropolis (demonstration)", "seed": res["seed"], "chains": res["chains"],
                        "draws_per_chain": res["draws_per_chain"]},
            "convergence": {"rhat": {"s": q.get("rhat")}, "ess_bulk": {"s": q.get("ess_bulk")},
                            "ess_tail": {"s": q.get("ess_tail")}, "status": res["diagnostics"]["status"]},
            "fit_status": {0: "converged", 1: "failed"}.get(code, "converged-with-warnings"),
            "results": {"upper_bound": res["upper_bound"], "cl": res["cl"]}},
    }


if __name__ == "__main__":
    sys.exit(main())
