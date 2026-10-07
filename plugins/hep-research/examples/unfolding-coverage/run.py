#!/usr/bin/env python3
"""Executed unfolding example: bias and coverage of unfolded spectra, by regularization.

SYNTHETIC and ILLUSTRATIVE. The spectrum, efficiency and resolution are invented and describe no experiment; no
profile is loaded. What the example shows is the general behavior [General method]: an unregularized inversion is
unbiased and its per-bin 68% intervals cover; regularization trades variance for bias, so its intervals undercover,
more where the spectrum curves, and the model the response was built with moves the bias.

Chain: falling truth spectrum (10 bins on 0 <= x < 10) -> response with Gaussian smearing (resolution 0.8 bin
widths) and a bin-dependent efficiency (inefficiency outside the matrix, core/stats/validate_response.py convention)
-> unfolding matrices A from core.stats.unfolding_diagnostics.linear_matrix (TSVD full rank = inversion, TSVD with
6 singular values, Tikhonov at four strengths; weights from the expected reco counts of the model truth) ->
analytic bias (A R t - t) and covariance (A diag(R t) A^T) -> seeded Poisson toys: per toy the interval
x_j +- sigma_j with sigma from A diag(counts) A^T (what an analyst would quote), coverage = fraction of toys whose
interval contains t_j -> the same with a test truth of different slope (model dependence).

Pre-declared criteria (exit 1 if any fails): inversion bias below 1e-9 relative; inversion coverage within 4
binomial standard errors of 0.6827 in every bin; toy-mean bias equal to the analytic bias within 4 standard errors
for every setting; for Tikhonov, the mean sigma falls and the largest |bias|/sigma rises as the strength grows.
Coverage of the regularized settings is recorded, not required: undercoverage there is the expected result.

Usage (from the plugin root): python3 examples/unfolding-coverage/run.py [--toys 4000] [--seed 20261007] [--out DIR]
Requires numpy (D5 environment).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from core.stats.unfolding_diagnostics import linear_matrix  # noqa: E402

EDGES = np.arange(0.0, 11.0, 1.0)
CENTRES = 0.5 * (EDGES[1:] + EDGES[:-1])
RESOLUTION = 0.8
NOMINAL = 0.6827
SETTINGS = [("tsvd", 10, "inversion (TSVD, all 10 singular values)"), ("tsvd", 6, "TSVD, 6 singular values"),
            ("tikhonov", 1e-4, "Tikhonov 1e-4"), ("tikhonov", 1e-3, "Tikhonov 1e-3"),
            ("tikhonov", 1e-2, "Tikhonov 1e-2"), ("tikhonov", 1e-1, "Tikhonov 1e-1")]


def spectrum(slope, total=12000.0):
    w = np.exp(-slope * CENTRES)
    return total * w / w.sum()


def response():
    """R[i, j] = P(reco bin i | truth bin j), Gaussian smearing of the bin centre (columns >= 0, sums <= 1); events smeared outside the
    reco range and the efficiency loss are the inefficiency (columns sum to below 1)."""
    eff = 0.95 - 0.02 * np.arange(len(CENTRES))
    cdf = lambda z: 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))  # noqa: E731
    z_hi = (EDGES[1:, None] - CENTRES[None, :]) / RESOLUTION
    z_lo = (EDGES[:-1, None] - CENTRES[None, :]) / RESOLUTION
    return (cdf(z_hi) - cdf(z_lo)) * eff[None, :]


def r6(x):
    """Round to 6 significant digits so the committed output does not depend on the last floating-point bits."""
    if isinstance(x, (list, tuple, np.ndarray)):
        return [r6(v) for v in x]
    return float(f"{float(x):.6g}")


def study(a, r, truth, toys, rng):
    mu = r @ truth
    expect = a @ mu
    cov = a @ np.diag(mu) @ a.T
    sigma = np.sqrt(np.diag(cov))
    counts = rng.poisson(mu, size=(toys, len(mu))).astype(float)
    est = counts @ a.T
    sig_toy = np.sqrt(np.einsum("ji,ti,ji->tj", a, counts, a))
    covered = np.abs(est - truth) <= sig_toy
    cov_frac = covered.mean(axis=0)
    toy_bias = est.mean(axis=0) - truth
    toy_bias_se = est.std(axis=0, ddof=1) / math.sqrt(toys)
    return {"analytic_relative_bias": r6((expect - truth) / truth), "analytic_bias_over_sigma": r6((expect - truth) / sigma),
            "relative_sigma": r6(sigma / truth), "coverage_68": r6(cov_frac),
            "max_abs_bias_over_sigma": r6(np.max(np.abs(expect - truth) / sigma)), "mean_relative_sigma": r6(np.mean(sigma / truth)),
            "min_coverage_68": r6(cov_frac.min()),
            "_toy_vs_analytic_bias_in_se": float(np.max(np.abs(toy_bias - (expect - truth)) / toy_bias_se))}


def run(toys, seed):
    r = response()
    model, test = spectrum(0.35), spectrum(0.25)
    mu_w = (r @ model).tolist()
    rng = np.random.default_rng(seed)
    se = math.sqrt(NOMINAL * (1 - NOMINAL) / toys)
    rows = []
    for method, param, label in SETTINGS:
        a = np.array(linear_matrix(method, param, r.tolist(), mu_w))
        rows.append({"setting": label, "method": method, "param": param,
                     "model_truth": study(a, r, model, toys, rng), "test_truth": study(a, r, test, toys, rng)})
    inv, tik = rows[0], [x for x in rows if x["method"] == "tikhonov"]
    checks = {
        "inversion_unbiased": max(abs(v) for v in inv["model_truth"]["analytic_relative_bias"]) < 1e-9
        and max(abs(v) for v in inv["test_truth"]["analytic_relative_bias"]) < 1e-9,
        "inversion_covers": all(abs(c - NOMINAL) < 4 * se for t in ("model_truth", "test_truth") for c in inv[t]["coverage_68"]),
        "toy_bias_matches_analytic": all(x[t]["_toy_vs_analytic_bias_in_se"] < 4 for x in rows for t in ("model_truth", "test_truth")),
        "tikhonov_sigma_falls": all(b["model_truth"]["mean_relative_sigma"] < a["model_truth"]["mean_relative_sigma"] for a, b in zip(tik, tik[1:])),
        "tikhonov_bias_rises": all(b["model_truth"]["max_abs_bias_over_sigma"] > a["model_truth"]["max_abs_bias_over_sigma"] for a, b in zip(tik, tik[1:])),
    }
    for x in rows:
        for t in ("model_truth", "test_truth"):
            x[t].pop("_toy_vs_analytic_bias_in_se")
    return {"label": "SYNTHETIC [General method]", "toys": toys, "seed": seed, "nominal_coverage": NOMINAL,
            "coverage_standard_error": r6(se), "truth_edges": EDGES.tolist(), "resolution_in_bin_widths": RESOLUTION,
            "model_truth": r6(model), "test_truth": r6(test), "response": r6(r), "settings": rows,
            "criteria": checks, "passed": all(checks.values()),
            "note": ("coverage: fraction of toys whose interval x_j +- sigma_j (sigma from the toy's own counts) contains "
                     "the true bin content; the regularized settings undercover because of their bias, which is the "
                     "systematic an analysis has to assign or reduce; the response is exactly known here, so response "
                     "uncertainty adds to all of this in practice; D'Agostini iterations are not in this example (use "
                     "core/stats/unfolding_diagnostics.py closure, whose sigma comes from the toys)")}


def report(res):
    lines = ["# Unfolding bias and coverage (SYNTHETIC)", "",
             f"{res['toys']} seeded Poisson toys (seed {res['seed']}); nominal 68% coverage {NOMINAL} with binomial "
             f"standard error {res['coverage_standard_error']}. Model truth: slope 0.35; test truth: slope 0.25, "
             "unfolded with the model-truth weights.", "",
             "| Setting | mean rel. sigma | max abs(bias)/sigma (model) | min coverage (model) | max abs(bias)/sigma (test) | min coverage (test) |",
             "|---|---|---|---|---|---|"]
    for x in res["settings"]:
        m, t = x["model_truth"], x["test_truth"]
        lines.append(f"| {x['setting']} | {m['mean_relative_sigma']} | {m['max_abs_bias_over_sigma']} | {m['min_coverage_68']} | "
                     f"{t['max_abs_bias_over_sigma']} | {t['min_coverage_68']} |")
    lines += ["", "Criteria: " + ", ".join(f"{k} {'pass' if v else 'FAIL'}" for k, v in res["criteria"].items()), "",
              res["note"], ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toys", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=20261007)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    opts = ap.parse_args(argv)
    res = run(opts.toys, opts.seed)
    opts.out.mkdir(parents=True, exist_ok=True)
    (opts.out / "results.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    (opts.out / "report.md").write_text(report(res), encoding="utf-8")
    print(json.dumps({"passed": res["passed"], "criteria": res["criteria"]}))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
