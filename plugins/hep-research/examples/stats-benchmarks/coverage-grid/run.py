#!/usr/bin/env python3
"""Coverage grid of 95% counting procedures (hep-statistics audit T14). SYNTHETIC; [General method].

What it checks, with the gate fixed in this file before any run (GATE):
- exact coverage, by summing Poisson probabilities over every count (no Monte Carlo error), of three known-background
  constructions on a grid of true signal s and background b: the classical upper limit, the CLs upper limit and the
  Feldman-Cousins interval (core/stats/poisson_diagnostics.py). Discrete constructions over-cover; that is not a
  failure. Expectations differ: the classical and FC belts cover at least 95% at every point by construction; CLs
  over-covers by design (it is not a frequentist interval, and its coverage is reported, not gated as a belt). The
  Feldman-Cousins belt is the plain construction at each b (the Neyman belt itself); the published monotone-in-b
  version only lengthens upper ends, so its coverage is at least this;
- seeded-toy coverage (20,000 toys per point by default) of the asymptotic profile-likelihood upper limit with a
  Gaussian-constrained background (q-tilde = z^2, core/stats/likelihood_limits.py), which has no exact belt: low and
  high counts, the s = 0 boundary and small and large background uncertainties. The ensemble is plug-in at the true
  point (counts and the auxiliary measurement drawn at the true s, b), failures count as not covering, and every
  toy's outcome is recorded (core/stats/toy_ensemble.py);
- a calibration of the toy machinery: toy coverage of the classical limit at one point against its exact value.

GATE: a procedure passes at a point when the one-sided lower confidence bound on its coverage is at least
0.95 - 0.01, at confidence 1 - 0.05 / (number of gated points of that procedure) (Bonferroni). For exact coverage the
bound is the value itself. Near 95%, 20,000 toys give a standard error of 0.00154. A point fails when even the upper
bound is below 0.94: the procedure is inapplicable there, and that is not repaired by changing the gate. A point
whose bounds straddle 0.94 is not established (insufficient precision), which is reported as incomplete, not as
failure or validity.

Usage (from the plugin root): python3 examples/stats-benchmarks/coverage-grid/run.py [--toys 20000] [--seed 20261012]
                              [--out DIR]
Exit codes: 0 every gated point of the exact belts passes, the toy calibration agrees and the negative control (the
limit computed ignoring sigma_b) is rejected by the gate (the asymptotic results are recorded either way); 1 otherwise;
2 bad usage. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from statistics import NormalDist

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))

from core.stats import likelihood_limits as ll  # noqa: E402
from core.stats import poisson_diagnostics as pd  # noqa: E402
from core.stats import toy_ensemble as te  # noqa: E402
from core.stats._poisson import ppf  # noqa: E402

CL = 0.95
GATE = {"nominal": CL, "max_deficit": 0.01, "gate_cl": 0.95, "rule": "one-sided lower bound >= nominal - max_deficit, Bonferroni per procedure"}
S_GRID = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0]
B_GRID = [0.0, 0.5, 2.0, 5.0]
FC_STEP = 0.01
# asymptotic profile limit: (s, b, sigma_b) covering low and high counts, the boundary and nuisance extremes
PROFILE_POINTS = [(0.0, 3.0, 0.3), (1.0, 0.5, 0.25), (2.0, 3.0, 0.3), (2.0, 3.0, 1.5), (5.0, 10.0, 0.5), (5.0, 10.0, 5.0),
                  (10.0, 50.0, 2.5), (20.0, 100.0, 5.0)]
CALIBRATION_POINT = (3.0, 1.0)


def pmf(n, mu):
    return math.exp(-mu + (n * math.log(mu) if n else 0.0) - math.lgamma(n + 1)) if mu > 0 else (1.0 if n == 0 else 0.0)


def n_max(mu):
    """Largest count summed: P(N > n_max | mu) < 1e-12 (the remainder is recorded and counted as not covering)."""
    n, cdf = 0, 0.0
    while 1.0 - cdf >= 1e-12:
        cdf += pmf(n, mu)
        n += 1
    return n


def exact_belts():
    rows = []
    for b in B_GRID:
        top = n_max(max(S_GRID) + b)
        classical = {n: pd.upper_limit(n, b, CL)["upper_limit_on_signal"] for n in range(top + 1)}
        cls = {n: pd.cls_limit(n, b, CL)["observed_upper_limit"] for n in range(top + 1)}
        fc = {}
        for n in range(top + 1):
            iv = pd.fc_interval(n, b, CL, step=FC_STEP, monotone=False)
            fc[n] = (iv["lower"], iv["upper"])
        for s in S_GRID:
            mu = s + b
            weight = {n: pmf(n, mu) for n in range(top + 1)}
            tail = 1.0 - sum(weight.values())             # probability beyond top: counted as not covering
            cov_classical = sum(w for n, w in weight.items() if classical[n] is not None and classical[n] >= s)
            cov_cls = sum(w for n, w in weight.items() if cls[n] >= s)
            cov_fc = sum(w for n, w in weight.items() if fc[n][0] - 1e-9 <= s <= fc[n][1] + 1e-9)
            rows.append({"s": s, "b": b, "classical": cov_classical, "cls": cov_cls, "feldman_cousins": cov_fc,
                         "probability_beyond_sum": max(tail, 0.0)})
    for proc in ("classical", "feldman_cousins"):
        for r in rows:
            r[f"{proc}_pass"] = r[proc] >= GATE["nominal"] - GATE["max_deficit"]
    return rows


def asymptotic_profile_limit(n, b0, sig):
    z = NormalDist().inv_cdf(CL)
    s_hat = max(n - max(b0, 0.0), 0.0)
    hi = s_hat + 20.0 * (math.sqrt(n + 1.0) + sig) + 20.0
    return ll._bisect(lambda s: ll._q1(n, b0, sig, s) - z * z, s_hat, hi)


def profile_coverage(toys, seed):
    rows = []
    for k, (s, b, sig) in enumerate(PROFILE_POINTS):
        spec = te.EnsembleSpec("plug-in", seed + k, toys)

        def generate(rng, i, s=s, b=b, sig=sig):
            return ppf(rng.random(), s + b), b + sig * rng.gauss(0.0, 1.0)

        def evaluate(data, i, sig=sig):
            n, b0 = data
            return asymptotic_profile_limit(n, b0, sig)
        t0 = time.perf_counter()
        res = te.run(spec, generate, evaluate)
        cov = te.coverage(res, lambda ul, s=s: ul >= s, CL)
        gate = te.coverage_gate(cov, GATE["max_deficit"], len(PROFILE_POINTS), GATE["gate_cl"])
        rows.append({"s": s, "b": b, "sigma_b": sig, "toys": toys, "seed": seed + k,
                     "coverage": cov["headline"]["value"], "interval_95": cov["headline"]["interval"],
                     "outcomes": cov["outcomes"], "gate": gate, "seconds": round(time.perf_counter() - t0, 1)})
    return rows


def negative_control(toys, seed):
    """A deliberately wrong procedure that the gate must reject: the asymptotic limit computed as if the background
    were known (sigma_b ignored), on data whose auxiliary measurement fluctuates with sigma_b = 5 around b = 10."""
    s, b, sig = 5.0, 10.0, 5.0
    res = te.run(te.EnsembleSpec("plug-in", seed, toys),
                 lambda rng, i: (ppf(rng.random(), s + b), b + sig * rng.gauss(0.0, 1.0)),
                 lambda d, i: asymptotic_profile_limit(d[0], max(d[1], 0.0), 0.0))
    cov = te.coverage(res, lambda ul: ul >= s, CL)
    gate = te.coverage_gate(cov, GATE["max_deficit"], 1, GATE["gate_cl"])
    return {"procedure": "asymptotic limit ignoring sigma_b", "s": s, "b": b, "sigma_b": sig, "toys": toys, "seed": seed,
            "coverage": cov["headline"]["value"], "gate": gate, "rejected": gate["verdict"] == "fail"}


def calibration(toys, seed):
    s, b = CALIBRATION_POINT
    exact = sum(pmf(n, s + b) for n in range(n_max(s + b) + 1)
                if (pd.upper_limit(n, b, CL)["upper_limit_on_signal"] or -1.0) >= s)
    res = te.run(te.EnsembleSpec("plug-in", seed, toys), lambda rng, i: ppf(rng.random(), s + b),
                 lambda n, i: pd.upper_limit(n, b, CL)["upper_limit_on_signal"] or -1.0)
    cov = te.coverage(res, lambda ul: ul >= s, CL, interval_cl=0.999)
    lo, hi = cov["headline"]["interval"]
    return {"s": s, "b": b, "exact": exact, "toy": cov["headline"]["value"], "toy_interval_999": [lo, hi],
            "agrees": lo <= exact <= hi, "toys": toys, "seed": seed}


def report(res):
    lines = ["# Coverage grid of 95% counting procedures (SYNTHETIC, [General method])", "",
             f"Gate: {GATE['rule']} (nominal {GATE['nominal']}, max deficit {GATE['max_deficit']}). Seed {res['seed']}, "
             f"{res['toys']} toys per asymptotic point.", "",
             "## Exact coverage (known background)", "",
             "| s | b | classical | CLs | Feldman-Cousins |", "|---|---|---|---|---|"]
    for r in res["exact"]:
        lines.append(f"| {r['s']:g} | {r['b']:g} | {r['classical']:.4f} | {r['cls']:.4f} | {r['feldman_cousins']:.4f} |")
    lines += ["", f"Classical and Feldman-Cousins pass at every point: {res['summary']['exact_belts_pass']}. CLs is "
              "reported, not gated as a belt: it over-covers by design.", "",
              "## Asymptotic profile limit, Gaussian-constrained background (toys)", "",
              "| s | b | sigma_b | coverage | 95% interval | lower bound (Bonferroni) | gate |", "|---|---|---|---|---|---|---|"]
    for r in res["asymptotic_profile"]:
        lines.append(f"| {r['s']:g} | {r['b']:g} | {r['sigma_b']:g} | {r['coverage']:.4f} | "
                     f"[{r['interval_95'][0]:.4f}, {r['interval_95'][1]:.4f}] | {r['gate']['lower_bound']:.4f} | "
                     f"{ {'pass': 'pass', 'fail': 'FAIL: inapplicable here', 'insufficient-precision': 'not established: more toys needed'}[r['gate']['verdict']]} |")
    c = res["calibration"]
    lines += ["", f"Toy calibration at s = {c['s']:g}, b = {c['b']:g}: exact {c['exact']:.4f}, toys {c['toy']:.4f} "
              f"(99.9% interval [{c['toy_interval_999'][0]:.4f}, {c['toy_interval_999'][1]:.4f}]): "
              f"{'agrees' if c['agrees'] else 'DISAGREES'}.", "",
              f"Negative control ({res['negative_control']['procedure']}, s = 5, b = 10, sigma_b = 5): coverage "
              f"{res['negative_control']['coverage']:.4f}, gate {res['negative_control']['gate']['verdict']}.", "",
              "A failed point marks the asymptotic limit inapplicable there (use a toy-calibrated or exact "
              "construction); passing points validate only themselves, not the space between them.", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--toys", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "output"))
    a = ap.parse_args(argv)
    if a.toys < 100:
        print(json.dumps({"status": "rejected", "error": "--toys must be at least 100"}))
        return 2
    exact = exact_belts()
    prof = profile_coverage(a.toys, a.seed)
    calib = calibration(a.toys, a.seed + 1000)
    neg = negative_control(a.toys, a.seed + 2000)
    res = {"label": "[General method] SYNTHETIC", "gate": GATE, "cl": CL, "toys": a.toys, "seed": a.seed,
           "fc_grid_step": FC_STEP, "exact": exact, "asymptotic_profile": prof, "calibration": calib, "negative_control": neg,
           "summary": {"exact_belts_pass": all(r["classical_pass"] and r["feldman_cousins_pass"] for r in exact),
                       "cls_min_coverage": min(r["cls"] for r in exact),
                       "asymptotic_points_failing": [[r["s"], r["b"], r["sigma_b"]] for r in prof if r["gate"]["verdict"] == "fail"],
                       "asymptotic_points_not_established": [[r["s"], r["b"], r["sigma_b"]] for r in prof
                                                             if r["gate"]["verdict"] == "insufficient-precision"],
                       "toy_calibration_agrees": calib["agrees"], "negative_control_rejected": neg["rejected"]}}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for r in prof:
        r.pop("seconds")  # timing is not reproducible output
    (out / "results.json").write_text(json.dumps(res, indent=1) + "\n")
    (out / "report.md").write_text(report(res))
    print(json.dumps(res["summary"], indent=1))
    return 0 if res["summary"]["exact_belts_pass"] and calib["agrees"] and neg["rejected"] else 1


if __name__ == "__main__":
    sys.exit(main())
