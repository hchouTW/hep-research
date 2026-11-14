"""Study S3 of phase 5 (task card `docs/dev/simulator-calibration/simcal-tasks/phase-5.md`, "S3, from V6 (d)"): the
recovery of the inferred V_model's f and ell (core/calibration/vmodel_infer.py) over synthetic draws with known truth,
run as a Slurm job array: each task writes the per-draw records of one block of one configuration; the merge
concatenates them and applies the registered rule (failures are reported, never retuned). Not a unit test module.

  python3 calibration_phase5_vmodel_s3.py --list                        the task table (JSON)
  python3 calibration_phase5_vmodel_s3.py --task K --out DIR            one task of the array
  python3 calibration_phase5_vmodel_s3.py --merge DIR --out FILE        merge and judge (exit 0 passed, 1 failed/incomplete)
  python3 calibration_phase5_vmodel_s3.py --local --out FILE            every configuration at tiny sizes (`smoke`)

A draw: link-space residual r = J theta + delta + e with delta ~ N(0, R(f, ell)) (squared-exponential kernel per
component, C = 0 between components), e ~ N(0, sigma^2 I), J = [1, z] integrated with a flat prior (theta), the prior
prior the Jeffreys measure x Half-Normal(f_scale) weight within length_bounds (vmodel_infer V3). Pull of x in log x:
(m - t) / (m - q16) if m > t, else (m - t) / (q84 - m), with m the marginal posterior median (the estimate) and q16,
q84 its 15.87 % and 84.13 % quantiles (the error toward the truth; WP-S2, A26 (2): the interval, not the rule,
replaced the Laplace sd, which misdescribed the skewed posterior in log ell).
Rule (proposed in the card, Inferred, from section 8.7 note 4's form, line 2068): per hyperparameter, |mean pull| <= 0.1
and sd within [0.9, 1.1]. A draw whose pull is undefined (the posterior mode at a bound, or a zero-width quantile
interval) is counted; any such draw makes the configuration `incomplete` (not passed) until the rule says how it counts.

Seeds: draw r of configuration j uses default_rng([SEED0 + r, j]). Records are labelled `synthetic` and
`provisional-thresholds`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from core.calibration import io  # noqa: E402
from core.calibration import vmodel_infer as VI  # noqa: E402

FLAGS = ["synthetic", "provisional-thresholds"]
FILES = ["core/calibration/vmodel_infer.py", "core/calibration/likelihood.py", "core/calibration/linear.py",
         "tests/core/calibration_phase5_vmodel_s3.py", "docs/dev/simulator-calibration/simcal-tasks/phase-5.md"]
SEED0 = 20261405
REPS = 1000
BLOCK = 100
MEAN_MAX, WIDTH_RANGE = 0.1, (0.9, 1.1)
# configurations: per component (n observables on z in [0, 1], f, ell, f_scale, length_bounds); sigma of the noise
CONFIGS = {
    "one": {"sigma": 0.01, "components": [{"n": 50, "f": 0.05, "length": 0.05, "f_scale": 0.1,
                                            "length_bounds": [0.01, 1.0]}]},
    "two": {"sigma": 0.01, "components": [{"n": 25, "f": 0.05, "length": 0.08, "f_scale": 0.1,
                                            "length_bounds": [0.01, 1.0]},
                                           {"n": 25, "f": 0.02, "length": 0.15, "f_scale": 0.05,
                                            "length_bounds": [0.02, 2.0]}]},
}


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
                                timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES if (ROOT / f).exists()}}


def problem(cfg: dict) -> tuple[dict, list[str], np.ndarray, np.ndarray]:
    """(contract, names, V, J) of a configuration; the declared f, ell are the starting values (not the truth)."""
    names, comps, zs = [], [], []
    for k, c in enumerate(cfg["components"]):
        z = np.linspace(0.0, 1.0, c["n"])
        nm = [f"c{k}_o{i}" for i in range(c["n"])]
        comps.append({"kind": "squared-exponential", "observables": nm, "f": c["f_scale"] / 2,
                      "length": math.sqrt(c["length_bounds"][0] * c["length_bounds"][1]),
                      "control": dict(zip(nm, z.tolist())),
                      "infer": {"f_scale": c["f_scale"], "length_bounds": list(c["length_bounds"])}})
        names += nm
        zs.append(z)
    contract = {"model_discrepancy": {"form": "inferred", "components": comps},
                "validation": {"mode": "holdout", "N_dc": []},
                "observables": [{"name": nm, "role": "calibration", "block": "gaussian", "link": "log"}
                                for nm in names]}
    n = len(names)
    zall = np.concatenate(zs)
    J = np.stack([np.ones(n), zall], axis=1)
    return contract, names, cfg["sigma"] ** 2 * np.eye(n), J


def truth_covariance(cfg: dict) -> np.ndarray:
    blocks = [VI.kernel_block(np.linspace(0.0, 1.0, c["n"]), c["f"], c["length"]) for c in cfg["components"]]
    n = sum(b.shape[0] for b in blocks)
    R = np.zeros((n, n))
    i = 0
    for b in blocks:
        R[i:i + len(b), i:i + len(b)] = b
        i += len(b)
    return R


def draw(name: str, r: int, cfg: dict | None = None):
    """(contract, names, residual, V, J) of draw r of configuration `name` (or of the configuration `cfg`)."""
    cfg = cfg or CONFIGS[name]
    j = sorted(CONFIGS).index(name) if name in CONFIGS else 99
    contract, names, V, J = problem(cfg)
    g = np.random.default_rng([SEED0 + r, j])
    S = truth_covariance(cfg) + V
    w, E = np.linalg.eigh(S)
    delta = (E * np.sqrt(np.clip(w, 0, None))) @ g.standard_normal(len(names))
    theta = g.normal(0.0, 1.0, J.shape[1])
    return contract, names, J @ theta + delta, V, J


def pull(q: list, truth: float) -> float | None:
    """(m - t) / (error toward t) from the log quantiles q = [2.5 %, 15.87 %, 50 %, 84.13 %, 97.5 %]."""
    m, t = q[2], math.log(truth)
    err = m - q[1] if m > t else q[3] - m
    return (m - t) / err if err > 0 else None


def pulls(rec: dict, cfg: dict) -> dict:
    out = {}
    for k, (e, c) in enumerate(zip(rec["estimates"], cfg["components"])):
        for par in ("f", "length"):
            out[f"{par}{k}"] = None if e["at_bound"] else pull(e["log_quantiles"][par], c[par])
    return out


def rep(name: str, r: int, cfg: dict | None = None) -> dict:
    cfg = cfg or CONFIGS[name]
    contract, names, res, V, J = draw(name, r, cfg)
    t0 = time.time()
    rec = VI.infer(contract, names, res, V, flat=J)
    return {"r": r, "pulls": pulls(rec, cfg), "estimates": [{k: e[k] for k in ("f", "length", "log_quantiles", "mode",
                                                                             "sd_log_f", "sd_log_length", "at_bound")}
                                                          for e in rec["estimates"]],
            "converged": rec["converged"], "seconds": time.time() - t0}


def judge(rows: list, reps: int = REPS) -> dict:
    """The registered rule on one configuration's rows."""
    keys = sorted({k for row in rows for k in row["pulls"]})
    per = {}
    undefined = 0
    for k in keys:
        x = np.array([row["pulls"][k] for row in rows if row["pulls"].get(k) is not None], float)
        undefined = max(undefined, sum(1 for row in rows if row["pulls"].get(k) is None))
        mu = float(x.mean()) if x.size else math.nan
        sd = float(x.std(ddof=1)) if x.size > 1 else math.nan
        per[k] = {"n": int(x.size), "mean": mu, "sd": sd,
                  "passed": bool(abs(mu) <= MEAN_MAX and WIDTH_RANGE[0] <= sd <= WIDTH_RANGE[1])}
    complete = len({row["r"] for row in rows}) == reps and undefined == 0
    return {"pulls": per, "draws": len(rows), "undefined": undefined, "complete": complete,
            "passed": bool(complete and per and all(v["passed"] for v in per.values())),
            "rule": f"per hyperparameter |mean pull| <= {MEAN_MAX} and sd in {list(WIDTH_RANGE)}; undefined pulls make "
                    "the configuration incomplete"}


def _tasks() -> list:
    return [(name, {"r0": i, "reps": BLOCK}) for name in sorted(CONFIGS) for i in range(0, REPS, BLOCK)]


TASKS = _tasks()


def run_block(name: str, r0: int, reps: int) -> list:
    return [rep(name, r) for r in range(r0, r0 + reps)]


def run_task(i: int, out_dir: Path) -> dict:
    name, kw = TASKS[i]
    t0 = time.time()
    rows = run_block(name, kw["r0"], kw["reps"])
    rec = {"task": i, "config": name, "kwargs": kw, "rows": rows, "seconds": time.time() - t0,
           "provenance": provenance(), "flags": FLAGS}
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
    by: dict = {}
    for r in recs.values():
        if r:
            by.setdefault(r["config"], []).extend(r["rows"])
    results = {k: judge(v) for k, v in by.items()}
    complete = not missing and len(commits) == 1 and not dirty
    rep_ = {"array": "phase-5 S3 inferred-V_model recovery", "complete": complete, "missing_tasks": missing,
            "commits": sorted(c for c in commits if c), "dirty": dirty, "results": results,
            "passed": {k: v["passed"] for k, v in results.items()}, "provenance": provenance(), "flags": FLAGS,
            "seconds": float(sum(r["seconds"] for r in recs.values() if r))}
    io.write_json(str(out), io.jsonable(rep_))
    return rep_


SMOKE_REPS = 3


def local(out: Path) -> dict:
    """Every configuration at SMOKE_REPS draws (draw indices 900000..): label `smoke`, not evidence."""
    t0 = time.time()
    results = {}
    for name in sorted(CONFIGS):
        rows = [rep(name, 900000 + r) for r in range(SMOKE_REPS)]
        results[name] = judge([dict(row, r=row["r"] - 900000) for row in rows], SMOKE_REPS)
    rep_ = {"label": "smoke", "results": results, "seconds": time.time() - t0, "flags": FLAGS}
    io.write_json(str(out), io.jsonable(rep_))
    return rep_


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", dest="smoke", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.list:
        print(json.dumps([{"task": i, "config": n, **kw} for i, (n, kw) in enumerate(TASKS)]))
        return 0
    if not args.out:
        ap.error("--out is required with --task, --merge and --local")
    if args.task is not None:
        r = run_task(args.task, Path(args.out))
        print(json.dumps({"task": r["task"], "config": r["config"], "seconds": r["seconds"]}))
        return 0
    if args.merge:
        r = merge(Path(args.merge), Path(args.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if args.smoke:
        r = local(Path(args.out))
        print(json.dumps({"label": "smoke", "seconds": r["seconds"]}))
        return 0
    ap.error("one of --list, --task, --merge, --local")
    return 2


if __name__ == "__main__":
    sys.exit(main())
