#!/usr/bin/env python3
"""Example E-3 (first part): a SYNTHETIC two-era measurement with a tracking layer added midway, from data-taking
periods to a split-consistency test and a joint fit over eras.

SYNTHETIC and ILLUSTRATIVE. The detector is the fictional toy spectrometer of
skills/hep-detector/assets/toy-spectrometer.fictional.json (protons only here); every number is invented and describes
no experiment. No profile is loaded.

Chain (each step runs the plugin's command-line tool, as a user would):
1. hep-detector D7 `toy_spectrometer.py`: seeded simulated events and 20 periods; from period 10 on (era e2) a ninth
   layer lengthens the lever arm, so the rigidity resolution improves.
2. hep-computing C1 `time_slice_reduction.py`: the run log arrives in two files that overlap by two periods; the
   reduction counts each period once.
3. hep-measurement M1 `collection_time.py`: collection time per era and rigidity bin (live time above the cutoff);
   partials from the two files merged equal one accumulation over both.
4. hep-detector D9 `build_response.py`: one response per era from the matched simulated events.
5. hep-detector D5 `mix_period_responses.py`: the stacked matrix S = [R_e1 diag(T_e1); R_e2 diag(T_e2)] for the joint
   fit, and the mixed single response (fold of the mix = sum of the per-era folds).
6. Synthetic observed counts per era: Poisson draws around S Phi_true, Phi_true a power law (rate per unit acceptance
   in each rigidity bin; acceptance 1 by construction).
7. hep-statistics S1 `split_consistency.py`: the per-era flux estimates agree; with a 5% scale offset injected into
   era e2 the test fails.
8. S6 joint fit (time-series-inference.md, "Multi-era joint fits"): Poisson maximum likelihood of Phi over both eras
   with S; seeded toys give the coverage of the +-1 sigma intervals.

Usage (from the plugin root): python3 examples/multi-era-fit/run.py [--toys 1000] [--seed 20261017] [--out DIR]
Exit 0 when every pre-declared criterion passes, 1 otherwise. Requires numpy (the tools it runs need numpy too).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

PLUGIN = Path(__file__).resolve().parents[2]
TOOLS = {
    "toy": PLUGIN / "skills" / "hep-detector" / "scripts" / "toy_spectrometer.py",
    "reduce": PLUGIN / "skills" / "hep-computing" / "assets" / "time_slice_reduction.py",
    "ctime": PLUGIN / "skills" / "hep-measurement" / "scripts" / "collection_time.py",
    "response": PLUGIN / "skills" / "hep-detector" / "scripts" / "build_response.py",
    "eras": PLUGIN / "skills" / "hep-detector" / "scripts" / "mix_period_responses.py",
    "split": PLUGIN / "skills" / "hep-statistics" / "scripts" / "split_consistency.py",
}
TOY_CONFIG = PLUGIN / "skills" / "hep-detector" / "assets" / "toy-spectrometer.fictional.json"
EDGES = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0]  # rigidity bins, GV (truth and reco)
ERAS = (("e1", 0, 10), ("e2", 10, 20))  # (id, first period, end period); periods are 1000 s long
PERIOD_S = 1000.0
INDEX = 2.7  # power-law index of the synthetic flux
K_FLUX = 40.0  # flux normalization: events / s / GV at 1 GV per unit acceptance (invented)
OFFSET = 1.05  # injected scale offset of era e2 for the S1 check
CRITERIA = {"coverage_target": 0.68, "coverage_tolerance": 0.03, "split_alpha": 0.01, "runtime_s_max": 60.0}
LABEL = "SYNTHETIC and ILLUSTRATIVE: fictional toy spectrometer; describes no experiment"


def tool(name: str, *args) -> dict:
    p = subprocess.run([sys.executable, "-B", str(TOOLS[name]), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=PLUGIN)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        raise SystemExit(f"{TOOLS[name].name} {args[:1]}: no JSON (exit {p.returncode}): {p.stderr[-800:]}")
    out["_exit"] = p.returncode
    return out


def rnd(x, digits=6):
    """Round for a byte-reproducible results file."""
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v, digits) for v in x]
    return float(f"{float(x):.{digits}g}")


def read_table(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(line for line in fh if not line.startswith("#")))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def phi_true() -> np.ndarray:
    """Rate per unit acceptance in each bin: K / (INDEX - 1) (lo^(1-INDEX) - hi^(1-INDEX))."""
    e = np.array(EDGES)
    return K_FLUX / (INDEX - 1) * (e[:-1] ** (1 - INDEX) - e[1:] ** (1 - INDEX))


def fit(S: np.ndarray, n: np.ndarray, start: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Poisson maximum likelihood of mu = S phi (phi > 0) by Newton steps in log phi; covariance from the Fisher
    information S^T diag(1/mu) S at the maximum."""
    keep = S.sum(axis=1) > 0
    S, n = S[keep], n[keep]
    theta = np.log(start)
    for _ in range(100):
        phi = np.exp(theta)
        mu = S @ phi
        grad = (S.T @ (n / mu - 1.0)) * phi
        J = S * phi
        H = J.T @ (J * (n / mu ** 2)[:, None])  # observed information in theta (dominant term)
        step = np.linalg.solve(H, grad)
        theta += step
        if np.max(np.abs(step)) < 1e-12:
            break
    phi = np.exp(theta)
    mu = S @ phi
    cov = np.linalg.inv(S.T @ (S / mu[:, None]))
    return phi, cov


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--toys", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "output")
    a = ap.parse_args(argv)
    import time
    t0 = time.perf_counter()
    out = a.out
    (out / "artifacts").mkdir(parents=True, exist_ok=True)
    work_dir = tempfile.TemporaryDirectory()
    work = Path(work_dir.name)
    checks: dict = {}

    # 1. D7: simulated events and periods, protons only, flatter spectrum to populate every bin
    cfg = json.loads(TOY_CONFIG.read_text(encoding="utf-8"))
    proton = dict(cfg["species"][0], fraction=1.0, spectrum={"kind": "power-law", "index": 1.5, "r_min_gv": 0.8,
                                                             "r_max_gv": 80.0})
    cfg.update(species=[proton], periods={"count": 20, "duration_s": PERIOD_S, "rate_hz": 12.0, "live_fraction": 0.9})
    cfg["eras"] = [{"name": "e1", "first_period": 0}, dict(cfg["eras"][1], name="e2", first_period=10)]
    (work / "toy.json").write_text(json.dumps(cfg, indent=1), encoding="utf-8")
    toy = tool("toy", "generate", work / "toy.json", "--seed", a.seed, "--events-out", work / "events.csv",
               "--periods-out", work / "periods.csv")
    assert toy["status"] == "ok", toy
    resolution = {e["name"]: {"a_per_gv": rnd(e["a_per_gv"]), "b": rnd(e["b"])} for e in toy["eras"]}

    # 2. C1: the run log in two files overlapping by two periods; an invented cutoff column (0.5 GV in even periods,
    # 1.8 GV in odd ones, so the two lowest bins collect time only in half the periods)
    periods = read_table(work / "periods.csv")
    for p in periods:
        p["cutoff_gv"] = "0.5" if int(p["period"]) % 2 == 0 else "1.8"
    fields = ["period", "era", "start_s", "duration_s", "live_fraction", "livetime_s", "cutoff_gv"]
    write_csv(work / "log_a.csv", periods[:12], fields)
    write_csv(work / "log_b.csv", periods[10:], fields)
    red = tool("reduce", "reduce", work / "log_a.csv", work / "log_b.csv", "--key", "period", "--sum", "livetime_s",
               "--status", "synthetic")
    livetime_unique = sum(float(p["livetime_s"]) for p in periods)
    checks["c1_duplicates_removed"] = red["duplicates_removed"]
    checks["c1_livetime_s"] = rnd(red["totals"]["livetime_s"])
    c1_ok = red["duplicates_removed"] == 2 and abs(red["totals"]["livetime_s"] - livetime_unique) < 1e-6

    # 3. M1: collection time per era and bin; partials merged equal one accumulation
    ct_cfg = {"key": "period", "start_column": "start_s", "duration_column": "duration_s",
              "live_fraction_column": "live_fraction", "quality_cuts": [],
              "transmission": {"cutoff_column": "cutoff_gv", "safety_factors": [1.2]},
              "x": {"variable": "rigidity", "unit": "GV", "edges": EDGES}, "time_edges": [0, 20 * PERIOD_S],
              "eras": [{"id": e, "start": lo * PERIOD_S, "end": hi * PERIOD_S} for e, lo, hi in ERAS]}
    (work / "ct.json").write_text(json.dumps(ct_cfg), encoding="utf-8")
    single = tool("ctime", "accumulate", "--config", work / "ct.json", work / "log_a.csv", work / "log_b.csv",
                  "--status", "synthetic")
    pa = tool("ctime", "accumulate", "--config", work / "ct.json", work / "log_a.csv", "--emit-partial", work / "pa.json")
    pb = tool("ctime", "accumulate", "--config", work / "ct.json", work / "log_b.csv", "--emit-partial", work / "pb.json")
    merged = tool("ctime", "merge", "--config", work / "ct.json", work / "pa.json", work / "pb.json")
    assert single["status"] == merged["status"] == pa["status"] == pb["status"] == "ok", (single, merged)
    sf = next(iter(single["collection_time_s"]["e1"]))
    T = {e: single["collection_time_s"][e][sf][0] for e, _, _ in ERAS}
    m1_ok = merged["collection_time_s"] == single["collection_time_s"]
    checks["m1_collection_time_s"] = {e: rnd(v) for e, v in T.items()}

    # 4. D9: one response per era from the simulated events
    events = read_table(work / "events.csv")
    responses = {}
    for era, _, _ in ERAS:
        rows = [{"truth": r["rigidity_true_gv"], "reco": r["rigidity_meas_gv"]} for r in events if r["era"] == era]
        write_csv(work / f"ev_{era}.csv", rows, ["truth", "reco"])
        resp = tool("response", "build", work / f"ev_{era}.csv", "--truth-col", "truth", "--reco-col", "reco",
                    "--unweighted", "--all-selected", "--truth-edges", *EDGES, "--reco-edges", *EDGES,
                    "--variable", "rigidity", "--unit", "GV", "--normalization", "conditional_on_generated",
                    "--acceptance", "inside_matrix", "--residual", "inverse", "--intended-use", "forward_folding",
                    "--artifact-id", f"multi-era-response-{era}", "--objective", "SYNTHETIC E-3 example",
                    "--created", "2026-10-17", "--status", "synthetic", "--out", out / "artifacts" / f"response_{era}.json")
        assert resp["status"] == "ok", resp
        responses[era] = out / "artifacts" / f"response_{era}.json"

    # 5. D5: stack (joint fit) and mix (one effective response)
    weights = {"source": "collection_time.py accumulate (this example), acceptance 1",
               "periods": {e: {"acceptance": 1.0, "collection_time": T[e]} for e, _, _ in ERAS}}
    (work / "w.json").write_text(json.dumps(weights), encoding="utf-8")
    per = [x for e, _, _ in ERAS for x in ("--period", f"{e}={responses[e]}")]
    st = tool("eras", "stack", *per, "--weights", work / "w.json", "--out", work / "stack.json", "--status", "synthetic")
    mx = tool("eras", "mix", *per, "--weights", work / "w.json", "--artifact-id", "multi-era-mixed",
              "--objective", "SYNTHETIC E-3 example", "--created", "2026-10-17", "--status", "synthetic",
              "--out", out / "artifacts" / "response_mixed.json")
    assert st["status"] == "ok" and mx["status"] == "ok", (st, mx)
    S = np.array(json.loads((work / "stack.json").read_text())["matrix"], dtype=float)
    nr = len(EDGES) - 1
    blocks = {e: S[i * nr:(i + 1) * nr] for i, (e, _, _) in enumerate(ERAS)}
    mixed = json.loads((out / "artifacts" / "response_mixed.json").read_text())
    R_mix = np.array(mixed["extension"]["matrix"], dtype=float)
    ph = phi_true()
    wsum = np.array(T["e1"]) + np.array(T["e2"])
    fold_gap = float(np.max(np.abs(R_mix @ (wsum * ph) - (blocks["e1"] + blocks["e2"]) @ ph)) / float(np.max(S @ ph)))
    checks["d5_mix_vs_sum_of_folds_rel"] = rnd(fold_gap, 3)

    # 6. synthetic observed counts
    rng = np.random.default_rng(a.seed)
    mu = S @ ph
    n_obs = rng.poisson(mu).astype(float)

    # 7. S1: per-era estimates agree; an injected offset in e2 is caught
    def per_era(counts):
        res = {}
        for i, (e, _, _) in enumerate(ERAS):
            phi, cov = fit(blocks[e], counts[i * nr:(i + 1) * nr], ph * 1.1)
            res[e] = (phi, cov)
        return res

    def split(counts, tag):
        est = per_era(counts)
        doc = {"splits": [{"id": e, "values": est[e][0].tolist(), "covariance": est[e][1].tolist()} for e in est],
               "cross_covariance": []}
        (work / f"split_{tag}.json").write_text(json.dumps(doc), encoding="utf-8")
        r = tool("split", "--input", work / f"split_{tag}.json", "--alpha", CRITERIA["split_alpha"],
                 "--status", "synthetic")
        return {"exit": r["_exit"], "verdict": r.get("verdict"), "chi2": rnd(r["overall"]["chi2"], 5),
                "ndf": r["overall"]["ndf"], "p": rnd(r["overall"]["p_asymptotic"], 4), "warnings": r.get("warnings", [])}

    s1_nominal = split(n_obs, "nominal")
    shifted = n_obs.copy()
    shifted[nr:] = rng.poisson(mu[nr:] * OFFSET)
    s1_offset = split(shifted, "offset")
    checks["s1_nominal"], checks["s1_offset"] = s1_nominal, s1_offset

    # 8. joint fit and its coverage
    phi_hat, cov = fit(S, n_obs, ph * 1.1)
    sig = np.sqrt(np.diag(cov))
    covered, total = 0, 0
    for _ in range(a.toys):
        n = rng.poisson(mu).astype(float)
        p_hat, c = fit(S, n, ph)
        covered += int(np.sum(np.abs(p_hat - ph) <= np.sqrt(np.diag(c))))
        total += len(ph)
    coverage = covered / total
    width = np.diff(EDGES)
    runtime = time.perf_counter() - t0

    passed = {
        "c1_period_split_across_files_counted_once": bool(c1_ok),
        "m1_partials_merged_equal_single_run": bool(m1_ok),
        "d5_fold_of_mix_equals_sum_of_era_folds": fold_gap < 1e-9,
        "s1_no_difference_is_consistent": s1_nominal["exit"] == 0,
        "s1_injected_offset_is_caught": s1_offset["exit"] == 1,
        "joint_fit_coverage_0p68_pm_0p03": abs(coverage - CRITERIA["coverage_target"]) <= CRITERIA["coverage_tolerance"],
        "runtime_below_60_s": runtime < CRITERIA["runtime_s_max"],
    }
    results = {
        "label": LABEL, "seed": a.seed, "toys": a.toys, "edges_gv": EDGES, "eras": [e for e, _, _ in ERAS],
        "toy_resolution": resolution, "checks": checks,
        "flux_true_per_gv": rnd(ph / width), "flux_joint_per_gv": rnd(phi_hat / width),
        "flux_joint_sigma_per_gv": rnd(sig / width), "joint_fit_pulls": rnd((phi_hat - ph) / sig, 4),
        "coverage_1sigma": rnd(coverage, 4), "coverage_cells": total, "criteria": CRITERIA, "pass": passed,
    }
    (out / "results.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
    lines = [f"# Multi-era fit (E-3, first part)\n\n{LABEL}.\n",
             f"Two eras of a fictional spectrometer; e2 adds a ninth layer (resolution terms {resolution}).\n",
             "| Check | Result |", "|---|---|"]
    lines += [f"| {k} | {'pass' if v else 'FAIL'} |" for k, v in passed.items()]
    lines += ["", f"Joint-fit coverage of the +-1 sigma intervals: {coverage:.4f} over {total} cells ({a.toys} toys).",
              f"S1 without a difference: chi2 {s1_nominal['chi2']} / {s1_nominal['ndf']}, p {s1_nominal['p']}; "
              f"with a {OFFSET - 1:.0%} offset in e2: chi2 {s1_offset['chi2']}, p {s1_offset['p']}.", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    work_dir.cleanup()
    print(json.dumps({"pass": passed, "coverage": coverage, "runtime_s": round(runtime, 1)}, indent=1))
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
