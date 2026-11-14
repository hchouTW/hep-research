"""The G8-based section 8.7 calibrations of phase 2 on the linear configurations (approval A11), the G7 half of
calibration 6, and the research run on the toy detector's G8 deviation, batch C (task card `docs/dev/
simulator-calibration/simcal-tasks/phase-2.md`). Not a unit test module.

  python3 calibration_phase2_cals_c.py --task N --out DIR          one task of the array
  python3 calibration_phase2_cals_c.py --merge DIR --out FILE      merge and judge (exit 0 passed, 1 failed)
  python3 calibration_phase2_cals_c.py --smoke NAME --out FILE     the code path at tiny sizes (not evidence)

Seeds: default_rng([cal_seed(c, r), j, ...]) for calibration c (the research run uses c = 16), repetition r and
configuration j. G8 here is the engine's decision (`closure.g8`) on pseudo-data fitted one by one; the intervals of the
linear Gaussian configurations are theta-hat_i +- z sigma_tot,i (the profile interval of a linear Gaussian fit).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calibration_phase2_gates as G  # noqa: E402

from core.calibration import closure as C  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import interval as IV  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402

cal_seed = G.cal_seed
D = 3
TRUTH = np.array([0.5, -0.3, 1.0])
BOUNDS = [(-2.0, 10.0)] * D
PRIOR = [(-3.0, 3.0)] * D
N_STD, N_FULL = C.n_c(D, "standard")["N_c"], C.n_c(D, "full")["N_c"]
Z = {0.68: 1.0, 0.95: 1.96}


def _seed(*parts) -> int:
    return int(np.random.SeedSequence([int(p) for p in parts]).generate_state(1)[0])


def linear_cfg(mc_ratio: float):
    cfg = T.linear_config(n=20, d=D, seed=cal_seed(1, 0) % 2 ** 31, mc_ratio=mc_ratio, bounds=BOUNDS, prior=PRIOR)
    return cfg


def design_sigma(cfg) -> np.ndarray:
    p = T.make(cfg, TRUTH, data_seed=1, mc_seed=2)
    return F.iterate(p, T.initial_beta(p), lndet=False).sigma_tot


# ------------------------------------------------------------------ pseudo-data of one injection point
def pseudo_point(cfg, truth, n_req, base, fit_scale=1.0, shared_shift=None, inject=None, scales=None):
    """n_req converged pseudo-data at `truth`: each its own data (the analytic truth, plus a shift shared by all
    pseudo-data of the run when `shared_shift` is given: a 100-times truth MC), its own nominal MC; the fit with V_MC
    scaled by `fit_scale` (1 correct). Non-converged pseudo-data are replaced (section 7.3); `inject` = (mode, eps)
    declares pseudo-data non-converged independently of the outcome or concentrated in the covered (not covered)
    ones at 68%. Returns errors and sigma_tot per pseudo-data, X and the attempts."""
    fcfg = cfg
    if fit_scale != 1.0:
        fcfg = T.Config(**{**cfg.__dict__, "V_MC": cfg.V_MC * fit_scale})
    errs, sig, X, k, x_at = [], [], 0, 0, []
    rng = np.random.default_rng([*base, 99])
    p68 = 2 * stats.norm.cdf(1) - 1
    while len(errs) < n_req and k < 3 * n_req:
        s = k
        k += 1
        p = T.LinearProblem(cfg, mc_seed=_seed(*base, 1, s))
        b = np.r_[truth, np.zeros(p.layout.n_beta - D)]
        b[p.layout.slices()["gamma"]] = 1.0
        obs = p.simulate(b, np.random.default_rng([*base, 2, s]), nominal=False)
        if shared_shift is not None:
            obs.y_gauss = obs.y_gauss + shared_shift
        q = T.LinearProblem(fcfg, mc_seed=_seed(*base, 1, s), observed=obs)
        q.e0 = p.e0                                          # the same nominal MC sample, its V_MC as the fit states
        f = F.iterate(q, T.initial_beta(q), lndet=False)
        if not f.converged:
            X += 1
            continue
        e = f.beta[:D] - truth
        if inject is not None:
            mode, eps = inject
            cov = bool(abs(e[0]) <= f.sigma_tot[0])
            if mode == "independent":
                pd = eps
            elif mode == "covered":                          # the eps fraction taken from the covered ones only
                pd = eps / p68 if cov else 0.0
            else:                                            # from the not-covered ones only
                pd = eps / (1 - p68) if not cov else 0.0
            if rng.random() < pd:
                X += 1
                continue
        errs.append(e)
        sig.append(f.sigma_tot.copy())
        x_at.append(X)                                       # X when this pseudo-data was reached
    return {"errors": np.array(errs), "sigma": np.array(sig), "X": X, "attempts": k, "x_at": x_at}


def _decide(level, pts, sigma_design, n, scales=None):
    """closure.g8 on the first n pseudo-data of each point; `scales` = {level: z factor} scales that interval."""
    sc = {0.68: 1.0, 0.95: 1.0, **(scales or {})}
    res = {}
    for name, pt in pts.items():
        e, s = pt["errors"][:n], pt["sigma"][:n]
        res[name] = {"errors": e, "cover68": np.abs(e) <= Z[0.68] * sc[0.68] * s,
                     "cover95": np.abs(e) <= Z[0.95] * sc[0.95] * s, "nontruth_basin": np.zeros(len(e), bool),
                     "X": pt["x_at"][n - 1] if len(pt["x_at"]) >= n else pt["X"],   # the X of this level's ensemble
                     "interval_toys": {"X": 0, "n": 0}}
    return C.g8(level, [f"t{i}" for i in range(D)], sigma_design, res["interior"], res["boundary"])


def _scale_for(p1, c):
    """The interval factor whose Gaussian coverage is p1 instead of c."""
    return float(stats.norm.ppf(0.5 + p1 / 2) / stats.norm.ppf(0.5 + c / 2))


POWER = {"standard|0.68": ("standard", 0.68), "full|0.68": ("full", 0.68), "full|0.95": ("full", 0.95)}


def g8_block(cal: int, mc_ratio: float, mode: str, r0: int, reps: int) -> list:
    """One G8 replicate per repetition at full size (N_full per point); the standard-level decisions use the first
    N_std pseudo-data. mode: "null" (false alarms and the three power cases with intervals scaled to coverage p1),
    "inject|<mode>|<eps>", "shared-shift" (a 100-times truth MC shared by the run's pseudo-data), "vmc2" (V_MC
    underestimated by 2 in the fit)."""
    cfg = linear_cfg(mc_ratio)
    sd = design_sigma(cfg)
    interior, boundary = C.injection_points(PRIOR, BOUNDS, sd, TRUTH)
    rows = []
    j = int(round(mc_ratio * 1000))
    for r in range(r0, r0 + reps):
        base = (cal_seed(cal, r), j, abs(hash_mode(mode)))
        kw = {}
        if mode.startswith("inject"):
            _, m, e = mode.split("|")
            kw["inject"] = (m, float(e))
        if mode == "shared-shift":
            kw["shared_shift"] = np.random.default_rng([*base, 7]).multivariate_normal(np.zeros(20), cfg.V_MC / 100)
        if mode == "vmc2":
            kw["fit_scale"] = 0.5
        pts = {"interior": pseudo_point(cfg, interior, N_FULL, (*base, 0), **kw),
               "boundary": pseudo_point(cfg, boundary, N_FULL, (*base, 1), **kw)}
        row = {"r": r, "X": pts["interior"]["X"] + pts["boundary"]["X"],
               "attempts": pts["interior"]["attempts"] + pts["boundary"]["attempts"]}
        for level, n in (("standard", N_STD), ("full", N_FULL)):
            g = _decide(level, pts, sd, n)
            row[level] = g["status"]
            row[f"{level}_finding"] = g.get("finding")
        if mode == "null":
            for key, (level, c) in POWER.items():
                g = _decide(level, pts, sd, N_STD if level == "standard" else N_FULL,
                            {c: _scale_for(C.P1[(level, c)], c)})
                row[f"power|{key}"] = g["status"] == "failed"
            row["bias_over_sigma"] = (pts["interior"]["errors"].mean(0) / sd).tolist()
        rows.append(row)
    return rows


def hash_mode(mode: str) -> int:
    return int.from_bytes(mode.encode()[:8].ljust(8, b"\0"), "little") % (2 ** 31)


def g8_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for key, rows in rows_by.items():
        cal, ratio, mode = key.split("|", 2)
        n = len(rows)
        rec = {"calibration": int(cal), "mc_ratio": float(ratio), "mode": mode, "reps": n,
               "false_alarms_standard": int(sum(x["standard"] == "failed" for x in rows)),
               "false_alarms_full": int(sum(x["full"] == "failed" for x in rows)),
               "incomplete_or_ratio": int(sum(x["standard"] not in ("passed", "failed") or
                                              x["full"] not in ("passed", "failed") for x in rows)),
               "X_fraction": sum(x["X"] for x in rows) / max(sum(x["attempts"] for x in rows), 1)}
        judged = mode in ("null", "shared-shift") or mode.startswith("inject")
        if judged:
            lim = 62 * n / 1000
            rec["passed_false_alarms"] = bool(rec["false_alarms_standard"] <= lim and rec["false_alarms_full"] <= lim)
            passed = rec["passed_false_alarms"]
            if mode == "null":
                for k in POWER:
                    rec[f"power|{k}"] = int(sum(x[f"power|{k}"] for x in rows))
                rec["power_ok"] = all(rec[f"power|{k}"] >= 775 * n / 1000 for k in POWER)
                rec["mean_bias_over_sigma"] = np.mean([x["bias_over_sigma"] for x in rows], 0).tolist()
                passed = passed and rec["power_ok"]
            rec["passed"] = bool(passed)
            ok = ok and rec["passed"]
        else:
            rec["passed"] = None                         # detection curve: reported
            rec["detection_standard"] = rec["false_alarms_standard"] / n
            rec["detection_full"] = rec["false_alarms_full"] / n
        out[key] = rec
    return {"item": "G8 on the linear configurations (approval A11)", "configurations": out, "passed": bool(ok),
            "rule": "false alarms <= 62 of 1000 at the standard and full levels (null, injected non-convergence, the "
                    "shared truth-MC shift); power >= 775 of 1000 with intervals scaled to coverage p1 (standard 68%, "
                    "full 68% and 95%); V_MC underestimated by 2 reported"}


# ------------------------------------------------------------------ calibration 15's G8 item: multimodal intervals
def bimodal_cfg():
    cfg = T.linear_config(n=20, d=2, seed=cal_seed(15, 0) % 2 ** 31, mc_ratio=0.1, bounds=[(-1.0, 4.0), (-2.0, 10.0)],
                          prior=[(-0.5, 2.5), (-3.0, 3.0)])
    cfg.bimodal = True
    cfg.J[:, 0] = np.abs(cfg.J[:, 0]) + 0.5           # m depends on (theta_0 - 1)^2: mirror basins at 1 +- delta
    return cfg


MM_TRUTH = np.array([2.0, 0.3])
MM_TOYS = 200


def multimodal_block(point: str, r0: int, reps: int) -> list:
    """Pseudo-data of calibration 15's G8 item: the bimodal linear configuration (exactly degenerate mirror basins in
    theta_0 at 1 +- 1), each pseudo-data fitted by section 7.4 (the default starts) and covered when the
    toy-calibrated construction (200 toys) puts the truth inside, at 68% and 95% (the p-value at the truth point
    against 0.32 and 0.05); the error for the bias test is taken to the nearer of the truth and its mirror point (the
    tie between exactly degenerate basins is broken lexicographically)."""
    cfg = bimodal_cfg()
    p0 = T.make(cfg, MM_TRUTH, data_seed=1, mc_seed=2)
    sd = F.find_extremum(p0, 1, T.initial_beta(p0, MM_TRUTH)).sigma_tot
    truth = MM_TRUTH.copy()
    if point == "boundary":
        truth[1] = BOUNDS[1][0] + 0.5 * sd[1]
    rows = []
    for r in range(r0, r0 + reps):
        base = (cal_seed(15, r), 900 + (point == "boundary"))
        p = T.make(cfg, truth, data_seed=_seed(*base, 1), mc_seed=_seed(*base, 2))
        f = F.find_extremum(p, (*base, 3), T.initial_beta(p))
        row = {"r": r, "converged": bool(f.converged), "multimodal": "multimodal" in f.flags}
        if f.converged:
            mirror = np.r_[2.0 - truth[0], truth[1]]          # the exactly degenerate mirror point of the truth
            e = min((f.beta[:2] - truth, f.beta[:2] - mirror), key=lambda x: abs(x[0]))
            row["error"] = e.tolist()
            cov = []
            for i in range(2):
                iv = IV.toy_calibrated(p, f, i, [float(truth[i])], MM_TOYS, (*base, 4, i), 0.68)
                pv = iv["p"][0] if iv.get("p") else None
                cov.append(None if iv["status"] != "ok" else {"p": pv})
            row["toy_p"] = [None if c is None else c["p"] for c in cov]
            row["basin_truth"] = bool(abs(f.beta[0] - truth[0]) < abs(f.beta[0] - (2 - truth[0])))
        rows.append(row)
    return rows


def multimodal_judge(rows_by: dict) -> dict:
    pts = {}
    for name in ("interior", "boundary"):
        rows = [x for x in rows_by.get(name, []) if x["converged"] and None not in x["toy_p"]]
        pts[name] = rows
    n = min(len(pts["interior"]), len(pts["boundary"]))
    if n == 0:
        return {"item": "calibration 15 G8: toy-calibrated intervals of multimodal results", "passed": False}
    res = {}
    for name, rows in pts.items():
        rows = rows[:n]
        e = np.array([x["error"] for x in rows])
        pv = np.array([x["toy_p"] for x in rows])
        res[name] = {"errors": e, "cover68": pv > 0.32, "cover95": pv > 0.05,
                     "nontruth_basin": np.array([not x["basin_truth"] for x in rows]), "X": 0,
                     "interval_toys": {"X": 0, "n": 0}}
    cfg = bimodal_cfg()
    p0 = T.make(cfg, MM_TRUTH, data_seed=1, mc_seed=2)
    sd = F.find_extremum(p0, 1, T.initial_beta(p0, MM_TRUTH)).sigma_tot
    level = "full" if n >= N_FULL else "standard"
    g = C.decide(level, ["t0", "t1"], res["interior"], res["boundary"], sd)
    cov = {name: {"68": float(np.mean(r["cover68"], 0)[0]), "95": float(np.mean(r["cover95"], 0)[0])}
           for name, r in res.items()}
    return {"item": "calibration 15 G8: toy-calibrated intervals of multimodal results", "n_per_point": n,
            "level": level, "g8": g["status"], "fails": g.get("fails"), "coverage_theta0": cov,
            "multimodal_fraction": float(np.mean([x["multimodal"] for name in pts for x in pts[name]])),
            "nontruth_basin_fraction": float(np.mean(res["interior"]["nontruth_basin"])),
            "passed": g["status"] == "passed",
            "rule": "G8 (closure.decide at the level the pseudo-data allow) passes on the toy-calibrated intervals"}


# ------------------------------------------------------------------ calibration 6's G7 half
def g7_block(K: int, r0: int, reps: int) -> list:
    """Calibration 5 repeated with Sigma_MC = f Sigma_data, f = 0.1 (its configuration already has V_MC = 0.1 V_data,
    so Sigma_MC = 0.1 Sigma_data exactly in the linear case), calibration 6's own seeds, V_MC correct: false alarms."""
    cfg = T.linear_config(n=20, d=3, mc_ratio=0.1, seed=cal_seed(5, 0) % 2 ** 31)
    rows = []
    for r in range(r0, r0 + reps):
        p0 = T.make(cfg, [0.5, -0.3, 1.0], data_seed=_seed(cal_seed(6, r), K, 1), mc_seed=_seed(cal_seed(6, r), K, 2))
        f0 = F.iterate(p0, T.initial_beta(p0), lndet=False)
        th = [F.iterate(q, T.initial_beta(q), lndet=False).beta[:3] for q in
              (T.LinearProblem(cfg, mc_seed=_seed(cal_seed(6, r), K, 3, k), observed=p0.observed) for k in range(K))]
        rows.append({"r": r, "failed": F.g7(np.array(th), F.sigma_mc(p0, f0, cfg.V_MC))["status"] == "failed"})
    return rows


def g7_judge(rows_by: dict) -> dict:
    out = {k: {"reps": len(v), "false_alarms": int(sum(x["failed"] for x in v))} for k, v in rows_by.items()}
    for v in out.values():
        v["passed"] = v["false_alarms"] <= 34 * v["reps"] / 1000
    return {"item": "calibration 6, G7 at f = 0.1", "configurations": out,
            "passed": bool(all(v["passed"] for v in out.values())),
            "rule": "false alarms <= 2 alpha (<= 34 of 1000 refit sets) at K = 10 and 5"}


# ------------------------------------------------------------------ research: the toy detector's G8 deviation
RESEARCH = {"e100": (100, 10), "e400": (400, 10), "e2000": (2000, 10), "e8000": (8000, 10), "e400mc2": (400, 2),
            "e400mc40": (400, 40)}


def research_block(config: str, r0: int, reps: int) -> list:
    """Correct toy-detector fits (the track configuration of gate 1: theta = momentum scale and sum term a, its
    calibration observables), each repetition with fresh data at the truth, its own nominal MC (MC/exposure as named)
    and bootstrap: theta-hat - truth and sigma_tot per parameter."""
    exposure, mcr = RESEARCH[config]
    j = list(RESEARCH).index(config)
    rows = []
    for r in range(r0, r0 + reps):
        base = (cal_seed(16, r), j)
        p = TP.ToyProblem(G.track_build, G.TRACK_CAL, G.TRACK_THETA, exposure=exposure, mc_events=mcr * exposure,
                          mc_seed=(*base, 1), boot_seed=(*base, 2))
        b = np.r_[G.TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
        p.observed = p.simulate(b, np.random.default_rng([*base, 3]), nominal=False)
        f = F.iterate(p, p.initial_beta())
        row = {"r": r, "converged": bool(f.converged)}
        if f.converged:
            row.update(error=(f.beta[:2] - G.TRACK_TRUTH).tolist(), sigma_tot=f.sigma_tot.tolist())
        rows.append(row)
    return rows


def research_judge(rows_by: dict) -> dict:
    out = {}
    for key, rows in rows_by.items():
        conv = [x for x in rows if x["converged"]]
        if not conv:
            out[key] = {"reps": len(rows), "converged": 0}
            continue
        e = np.array([x["error"] for x in conv])
        s = np.array([x["sigma_tot"] for x in conv])
        z = e / s
        n = len(conv)
        out[key] = {"exposure": RESEARCH[key][0], "mc_over_exposure": RESEARCH[key][1], "reps": len(rows),
                    "converged": n, "mean_pull": z.mean(0).tolist(), "mean_pull_se": (z.std(0, ddof=1) / math.sqrt(n))
                    .tolist(), "pull_sd": z.std(0, ddof=1).tolist(), "cover68": (np.abs(z) <= 1).mean(0).tolist(),
                    "cover95": (np.abs(z) <= 1.96).mean(0).tolist(),
                    "bias_over_sigma_sd": (e.mean(0) / e.std(0, ddof=1)).tolist()}
    return {"item": "research: the toy detector's G8 deviation (correct fits against exposure and MC size)",
            "configurations": out, "passed": True, "label": "synthetic", "decision": "none (research, reported)"}


# ------------------------------------------------------------------ task table, tasks, merge
def _tasks() -> list:
    t = []
    for cal, ratio in ((1, 0.01), (6, 0.1)):
        t += [("g8", {"cal": cal, "mc_ratio": ratio, "mode": "null", "r0": 25 * i, "reps": 25}) for i in range(40)]
    for m in ("independent", "covered", "not-covered"):
        for e in (0.005, 0.01):
            t += [("g8", {"cal": 10, "mc_ratio": 0.01, "mode": f"inject|{m}|{e}", "r0": 50 * i, "reps": 50})
                  for i in range(20)]
    t += [("g8", {"cal": 12, "mc_ratio": 0.1, "mode": "shared-shift", "r0": 50 * i, "reps": 50}) for i in range(20)]
    for ratio in (0.03, 0.1):
        t += [("g8", {"cal": 12, "mc_ratio": ratio, "mode": "vmc2", "r0": 100 * i, "reps": 100}) for i in range(5)]
    for pt in ("interior", "boundary"):
        t += [("multimodal", {"point": pt, "r0": 20 * i, "reps": 20}) for i in range(26)]
    for K in (10, 5):
        t += [("g7", {"K": K, "r0": 500 * i, "reps": 500}) for i in range(2)]
    for cfg, (ex, _) in RESEARCH.items():
        per = 25 if ex >= 8000 else (50 if ex >= 2000 else 100)
        t += [("research", {"config": cfg, "r0": per * i, "reps": per}) for i in range(1000 // per)]
    return t


TASKS = _tasks()
BLOCKS = {"g8": g8_block, "multimodal": multimodal_block, "g7": g7_block, "research": research_block}
JUDGES = {"g8": g8_judge, "multimodal": multimodal_judge, "g7": g7_judge, "research": research_judge}


def _key(name, kw):
    return {"g8": lambda: f"{kw['cal']}|{kw['mc_ratio']}|{kw['mode']}", "multimodal": lambda: kw["point"],
            "g7": lambda: f"K={kw['K']}", "research": lambda: kw["config"]}[name]()


def run_task(i: int, out_dir: Path) -> dict:
    name, kw = TASKS[i]
    t0 = time.time()
    rows = BLOCKS[name](**kw)
    rec = {"task": i, "block": name, "kwargs": kw, "key": _key(name, kw), "rows": rows, "seconds": time.time() - t0,
           "provenance": G.provenance(), "label": "synthetic"}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


def merge(out_dir: Path, out: Path) -> dict:
    recs = {}
    for i in range(len(TASKS)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    by = {}
    for r in recs.values():
        if r:
            by.setdefault(r["block"], {}).setdefault(r["key"], []).extend(r["rows"])
    results = {b: JUDGES[b](v) for b, v in by.items()}
    complete = not missing and len(commits) == 1 and not dirty
    rep = {"array": "G8 calibrations on linear configurations (A11), calibration 6 G7, toy G8 research (batch C)",
           "complete": complete, "missing_tasks": missing, "commits": sorted(commits), "dirty": dirty,
           "results": results, "passed": {k: v["passed"] for k, v in results.items()}, "provenance": G.provenance(),
           "label": "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


SMOKE = {"g8": ("g8", {"cal": 1, "mc_ratio": 0.01, "mode": "null", "r0": 900000, "reps": 1}),
         "g8_inject": ("g8", {"cal": 10, "mc_ratio": 0.01, "mode": "inject|covered|0.01", "r0": 900000, "reps": 1}),
         "g8_shift": ("g8", {"cal": 12, "mc_ratio": 0.1, "mode": "shared-shift", "r0": 900000, "reps": 1}),
         "multimodal": ("multimodal", {"point": "interior", "r0": 900000, "reps": 2}),
         "g7": ("g7", {"K": 10, "r0": 900000, "reps": 5}),
         "research": ("research", {"config": "e8000", "r0": 900000, "reps": 1}),
         "research400": ("research", {"config": "e400", "r0": 900000, "reps": 2})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--smoke", choices=sorted(SMOKE))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.task is not None:
        r = run_task(a.task, Path(a.out))
        print(json.dumps({"task": r["task"], "block": r["block"], "key": r["key"], "seconds": r["seconds"]}))
        return 0
    if a.merge:
        r = merge(Path(a.merge), Path(a.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if a.smoke:
        name, kw = SMOKE[a.smoke]
        t0 = time.time()
        rows = BLOCKS[name](**kw)
        rec = {"block": name, "kwargs": kw, "rows": rows, "seconds": time.time() - t0, "label": "smoke"}
        io.write_json(a.out, io.jsonable(rec))
        print(json.dumps({"block": name, "seconds": rec["seconds"], "rows": len(rows)}))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
