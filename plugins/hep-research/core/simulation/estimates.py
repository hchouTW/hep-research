"""Estimates of declared observables from a simulation-summary/1 (Geant4 program A1.6, A1.7): the one implementation
behind hep-detector's study scripts (convergence gate, statistical target, variations, benchmarks).

An observable declaration names its estimator: mean (block means of the selected values), proportion (block
fractions count_if[threshold_index] / n), mode (the most probable value: mean of three-point block modes,
core.stats.batch_means.mpv), quantile (histogram quantile per block; empirical, Hyndman-Fan type 7, when the
observable keeps per-block values, Geant4 program C2.1) or gaussian-core (from contracts CV-B2, Geant4
program B2.3: the width of the iterative truncated Gaussian core per block). Each gives value, SE on K - 1 degrees of
freedom and the full-sample value as a diagnostic. A proportion with an empty block or a merged count below
LOW_COUNT_TOTAL has no SE: it gives the exact Clopper-Pearson intervals of the merged accumulators instead (90 % and
the one-sided 1 - alpha/m bounds are computed by the caller from k and n)."""
from __future__ import annotations

import math

from core.simulation import summary as S
from core.stats import batch_means as M

ESTIMATORS = ("mean", "proportion", "mode", "quantile", "gaussian-core")


def estimate(summary: dict, decl: dict, tol_relative: float | None = None, low_count_total: int = M.LOW_COUNT_TOTAL,
             interval_cl: float = 0.90) -> dict:
    """{value, se, dof, blocks, status, method, ...} of one declared observable of a summary."""
    name = decl["name"]
    obs = S.observable(summary, name)
    est = decl.get("estimator", "mean")
    merged = S.merged_accumulators(obs)
    lo, width = obs["bins"]["lo"], obs["bins"]["width"]
    if est == "mean":
        r = M.batch_mean(S.block_means(obs))
        return {**r, "status": "ok", "method": "batch means of block means",
                "full_sample": merged["sum"] / merged["n"] if merged["n"] else None, "n": merged["n"]}
    if est == "proportion":
        t = int(decl.get("threshold_index", 0))
        ks = [b["count_if"][t] for b in obs["blocks"]]
        k, n = merged["count_if"][t], merged["n"]
        if M.low_count(ks, k, low_count_total):
            lo_p, hi_p = M.exact_proportion(k, n, interval_cl)
            return {"value": k / n if n else None, "se": None, "dof": None, "blocks": len(ks), "status": "ok",
                    "method": "exact (Clopper-Pearson) on the merged counts: low count", "low_count": True,
                    "k": k, "n": n, "interval": [lo_p, hi_p], "interval_cl": interval_cl}
        r = M.batch_mean(S.block_proportions(obs, t))
        return {**r, "status": "ok", "method": "batch means of block proportions", "full_sample": k / n, "k": k,
                "n": n, "low_count": False}
    if est == "mode":
        r = M.mpv([b["hist"] for b in obs["blocks"]], lo, width, tol_relative, merged["hist"])
        return {**r, "method": r.get("estimator", "block modes")}
    if est == "quantile":
        q = decl["quantile"]
        if "values_max" in obs and not obs.get("values_omitted"):  # C2.1: empirical quantiles from the raw values
            per = [M.empirical_quantile(v, q) for v in S.block_values(obs)]
            if any(p["status"] != "ok" for p in per):
                return {"value": None, "status": "incomplete",
                        "reason": next(p["reason"] for p in per if p["status"] != "ok")}
            r = M.batch_mean(p["value"] for p in per)
            return {**r, "status": "ok", "method": f"batch means of block empirical {q}-quantiles",
                    "quantile_method": obs["quantile_method"]}
        per = [M.hist_quantile(b["hist"], lo, width, q, b["underflow"], b["overflow"]) for b in obs["blocks"]]
        if any(p["status"] != "ok" for p in per):
            return {"value": None, "status": "incomplete", "reason": next(p["reason"] for p in per if p["status"] != "ok")}
        r = M.batch_mean(p["value"] for p in per)
        out = {**r, "status": "ok", "method": f"batch means of block {q}-quantiles (linear within the bin)"}
        if tol_relative is not None and width / abs(r["value"]) >= tol_relative / 10:
            out.update(status="incomplete", reason="bin-width-too-coarse-for-the-tolerance")
        return out
    if est == "gaussian-core":
        k = float(decl.get("core_truncation_sigma", 2.0))
        per = [gaussian_core(b["hist"], lo, width, k) for b in obs["blocks"]]
        bad = next((p for p in per if p["status"] != "ok"), None)
        if bad:
            return {"value": None, "status": "incomplete", "reason": bad["reason"]}
        r = M.batch_mean(p["sigma"] for p in per)
        full = gaussian_core(merged["hist"], lo, width, k)
        return {**r, "status": "ok", "method": f"batch means of block Gaussian-core widths (iterative +-{k:g} sigma "
                f"truncation, truncation-corrected)", "truncation_sigma": k,
                "full_sample": full.get("sigma"), "full_sample_mean": full.get("mean"), "n": merged["n"]}
    raise S.SummaryError(f"observable {name}: unknown estimator {est!r} (known: {list(ESTIMATORS)})")


def block_estimates(summary: dict, decl: dict) -> dict:
    """The per-block estimates theta_b behind estimate() for the estimators mean, proportion, quantile and
    gaussian-core (Geant4 program C2.1: paired comparisons of two runs of one seed_group difference these block by
    block). {status: ok, thetas} or {status: incomplete, reason}; estimate()'s value is the mean of the thetas."""
    obs = S.observable(summary, decl["name"])
    est = decl.get("estimator", "mean")
    lo, width = obs["bins"]["lo"], obs["bins"]["width"]
    try:
        if est == "mean":
            return {"status": "ok", "thetas": S.block_means(obs)}
        if est == "proportion":
            return {"status": "ok", "thetas": S.block_proportions(obs, int(decl.get("threshold_index", 0)))}
    except S.SummaryError as exc:
        return {"status": "incomplete", "reason": str(exc)}
    if est == "quantile":
        q = decl["quantile"]
        per = ([M.empirical_quantile(v, q) for v in S.block_values(obs)]
               if "values_max" in obs and not obs.get("values_omitted") else
               [M.hist_quantile(b["hist"], lo, width, q, b["underflow"], b["overflow"]) for b in obs["blocks"]])
        bad = next((p for p in per if p["status"] != "ok"), None)
        return {"status": "incomplete", "reason": bad["reason"]} if bad else {
            "status": "ok", "thetas": [p["value"] for p in per]}
    if est == "gaussian-core":
        k = float(decl.get("core_truncation_sigma", 2.0))
        per = [gaussian_core(b["hist"], lo, width, k) for b in obs["blocks"]]
        bad = next((p for p in per if p["status"] != "ok"), None)
        return {"status": "incomplete", "reason": bad["reason"]} if bad else {
            "status": "ok", "thetas": [p["sigma"] for p in per]}
    return {"status": "incomplete", "reason": f"estimator {est!r} has no per-block estimates for pairing"}


def gaussian_core(hist, lo: float, width: float, k: float = 2.0, iterations: int = 50) -> dict:
    """The Gaussian core of a histogram (Geant4 program B2.3): start from the mean and SD of all entries, keep the bins
    whose centres lie within mean +- k sigma, take their mean and SD and divide the SD by the SD of a unit Gaussian
    truncated at +-k (0.8796 at k = 2), and repeat until the window stops moving. {mean, sigma, status}; a window with
    fewer than 10 entries or a width under 3 bins is incomplete (the bins are too coarse for the core)."""
    centres = [lo + (i + 0.5) * width for i in range(len(hist))]
    n = sum(hist)
    if n < 10:
        return {"status": "incomplete", "reason": "fewer than 10 entries in the histogram"}
    mean = sum(c * h for c, h in zip(centres, hist)) / n
    sd = math.sqrt(max(sum(h * (c - mean) ** 2 for c, h in zip(centres, hist)) / n, 0.0))
    phi = math.exp(-0.5 * k * k) / math.sqrt(2 * math.pi)
    big_phi = 0.5 * (1 + math.erf(k / math.sqrt(2)))
    shrink = math.sqrt(1 - 2 * k * phi / (2 * big_phi - 1))
    for _ in range(iterations):
        keep = [(c, h) for c, h in zip(centres, hist) if abs(c - mean) <= k * sd]
        m = sum(h for _, h in keep)
        if m < 10:
            return {"status": "incomplete", "reason": "fewer than 10 entries in the core window"}
        new_mean = sum(c * h for c, h in keep) / m
        new_sd = math.sqrt(max(sum(h * (c - new_mean) ** 2 for c, h in keep) / m, 0.0)) / shrink
        done = abs(new_mean - mean) <= 1e-9 * max(new_sd, 1e-300) and abs(new_sd - sd) <= 1e-9 * new_sd
        mean, sd = new_mean, new_sd
        if done:
            break
    if sd < 3 * width:
        return {"status": "incomplete", "reason": "core width under three bins: the bins are too coarse"}
    return {"status": "ok", "mean": mean, "sigma": sd}
