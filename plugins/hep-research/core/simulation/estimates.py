"""Estimates of declared observables from a simulation-summary/1 (Geant4 program A1.6, A1.7): the one implementation
behind hep-detector's study scripts (convergence gate, statistical target, variations, benchmarks).

An observable declaration names its estimator: mean (block means of the selected values), proportion (block
fractions count_if[threshold_index] / n), mode (the most probable value: mean of three-point block modes,
core.stats.batch_means.mpv) or quantile (histogram quantile per block). Each gives value, SE on K - 1 degrees of
freedom and the full-sample value as a diagnostic. A proportion with an empty block or a merged count below
LOW_COUNT_TOTAL has no SE: it gives the exact Clopper-Pearson intervals of the merged accumulators instead (90 % and
the one-sided 1 - alpha/m bounds are computed by the caller from k and n)."""
from __future__ import annotations

from core.simulation import summary as S
from core.stats import batch_means as M

ESTIMATORS = ("mean", "proportion", "mode", "quantile")


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
        per = [M.hist_quantile(b["hist"], lo, width, q, b["underflow"], b["overflow"]) for b in obs["blocks"]]
        if any(p["status"] != "ok" for p in per):
            return {"value": None, "status": "incomplete", "reason": next(p["reason"] for p in per if p["status"] != "ok")}
        r = M.batch_mean(p["value"] for p in per)
        out = {**r, "status": "ok", "method": f"batch means of block {q}-quantiles (linear within the bin)"}
        if tol_relative is not None and width / abs(r["value"]) >= tol_relative / 10:
            out.update(status="incomplete", reason="bin-width-too-coarse-for-the-tolerance")
        return out
    raise S.SummaryError(f"observable {name}: unknown estimator {est!r} (known: {list(ESTIMATORS)})")
