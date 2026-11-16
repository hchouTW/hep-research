"""Study S2 of phase 5 (task card `docs/dev/simulator-calibration/simcal-tasks/phase-5.md`, studies, from ambiguity P2):
the partial-pooling frequency report. Under equal truth in every segment of a segmented linear toy, the fraction of
replicas with tau_pool_hat = 0, the fraction whose 95% set covers 0 (section 15.3.18 as approval A25 (6) reads it),
and the coverage of the pooled theta_s, theta_bar and the common theta by +-sigma_tot of the joint fit, over 1000
repetitions. Reported, not judged (the card: unless the author makes it the test). Not a unit test module.

  python3 simcal_phase5_pooling_s2.py --list                     the task table (JSON)
  python3 simcal_phase5_pooling_s2.py --task K --out DIR         one task of the array
  python3 simcal_phase5_pooling_s2.py --merge DIR --out FILE     merge and report (exit 0 complete, 1 incomplete)
  python3 simcal_phase5_pooling_s2.py --local --out FILE         the code path at tiny size (`smoke`, not evidence)

Configuration: toys_linear.linear_config(n=8, d=2, seed=3) per segment (identical J and V), S = 4 segments, t0 pooled
(identity link), t1 common, truth (0.5, -0.3) in every segment; repetition r draws its data from seeds
[cal_seed(1, r), s] and fits with seed cal_seed(1, r), cal_seed(c, r) = 20261405 + 100000 c + r. Each repetition runs
pooling.fit_pooled (REML, the joint fit with the section 7.4 multi-start). Records are labelled `synthetic`.
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
sys.path.insert(0, str(HERE))                      # simcal_phase5_taskenv

from core.simcal import io  # noqa: E402

import simcal_phase5_taskenv as TE  # noqa: E402
from core.simcal import pooling as PL  # noqa: E402
from core.simcal import toys_linear as TL  # noqa: E402

FLAGS = ["synthetic"]
FILES = ["core/simcal/pooling.py", "core/simcal/fit.py", "core/simcal/likelihood.py",
         "core/simcal/toys_linear.py", "tests/core/simcal_phase5_pooling_s2.py"]
SEED0 = 20261405
SEGMENTS = 4
TRUTH = (0.5, -0.3)
REPS = 1000
BLOCK = 100
TASKS = [{"r0": r0, "reps": BLOCK} for r0 in range(0, REPS, BLOCK)]
Z68 = 1.0                                   # +-1 sigma_tot: nominal 68.27%


def cal_seed(c: int, r: int) -> int:
    return SEED0 + 100_000 * c + r


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}}


def config():
    return TL.linear_config(n=8, d=2, seed=3)


def repetition(r: int, segments: int = SEGMENTS) -> dict:
    segs = PL.segmented_linear(config(), [TRUTH] * segments, [cal_seed(1, r)])
    names = [f"s{i}" for i in range(segments)]
    joint = PL.Segmented(segs, names, ["t0"])
    res = PL.fit_pooled(joint, cal_seed(1, r))
    row = {"r": r, "converged": res.converged, "reason": res.reason}
    if not res.converged:
        return row
    t = res.tau.record(["t0"])["t0"]
    row.update(tau_pool_hat=t["tau_pool_hat"], covers_0=t["covers_0"], upper_95=t["upper_95"], lower=t["lower"],
               segment_sigma=t["segment_sigma"],
               theta_s=[[res.segments[n]["t0"]["value_link"], res.segments[n]["t0"]["sigma_tot_link"]] for n in names],
               theta_bar=[res.theta_bar["t0"]["value_link"], res.theta_bar["t0"]["sigma_tot_link"]],
               common=[res.common["t1"]["value"], res.common["t1"]["sigma_tot"]])
    return row


def block(r0: int, reps: int, segments: int = SEGMENTS) -> list:
    return [repetition(r, segments) for r in range(r0, r0 + reps)]


def report(rows: list) -> dict:
    """The frequency report (reported, not judged): section 15.3.18 fractions and the +-sigma_tot coverages."""
    ok = [w for w in rows if w["converged"]]
    out: dict = {"repetitions": len(rows), "converged": len(ok), "not_converged": len(rows) - len(ok)}
    if not ok:
        return out
    dec = PL.frequency_decision([w["tau_pool_hat"] for w in ok], [w["covers_0"] for w in ok])
    cov_s = [abs(v - TRUTH[0]) <= Z68 * s for w in ok for v, s in w["theta_s"]]
    cov_b = [abs(w["theta_bar"][0] - TRUTH[0]) <= Z68 * w["theta_bar"][1] for w in ok]
    cov_c = [abs(w["common"][0] - TRUTH[1]) <= Z68 * w["common"][1] for w in ok]

    def frac(x):
        p = float(np.mean(x))
        return {"fraction": p, "binomial_se": math.sqrt(max(p * (1 - p), 1e-12) / len(x)), "n": len(x)}
    out.update(zero_fraction=dec["zero_fraction"][0], cover_fraction=dec["cover_fraction"][0],
               section_15_3_18_reading=dec["status"],
               coverage_theta_s=frac(cov_s), coverage_theta_bar=frac(cov_b), coverage_common=frac(cov_c),
               nominal=0.6827, median_upper_95=float(np.median([w["upper_95"] for w in ok])))
    return out


def run_task(i: int, out_dir: Path) -> dict:
    kw = TASKS[i]
    t0 = time.time()
    rows = block(kw["r0"], kw["reps"])
    rec = {"task": i, "kwargs": kw, "rows": rows, "seconds": time.time() - t0, "provenance": provenance(),
           "flags": FLAGS}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


def merge(out_dir: Path, out: Path, tasks: list | None = None) -> dict:
    tasks = TASKS if tasks is None else tasks
    recs = {}
    for i in range(len(tasks)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    rows = [w for r in recs.values() if r for w in r["rows"]]
    complete = not missing and len(commits) == 1 and not dirty
    rep = {"study": "S2 partial-pooling frequency report (phase 5, reported, not judged)",
           "status": "reported" if complete else "incomplete", "complete": complete, "missing_tasks": missing,
           "commits": sorted(c for c in commits if c), "dirty": dirty, "report": report(rows),
           "provenance": provenance(), "flags": FLAGS, "task_environment": TE.task_environment(recs.values()),
           "seconds": float(sum(r["seconds"] for r in recs.values() if r))}
    io.write_json(str(out), io.jsonable(rep))
    return rep


def local(out: Path, reps: int = 3) -> dict:
    t0 = time.time()
    rows = block(900000, reps)
    rep = {"label": "smoke", "report": report(rows), "seconds": time.time() - t0, "flags": FLAGS}
    io.write_json(str(out), io.jsonable(rep))
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", dest="smoke", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.list:
        print(json.dumps([{"task": i, **kw} for i, kw in enumerate(TASKS)]))
        return 0
    if not args.out:
        ap.error("--out is required with --task, --merge and --local")
    if args.task is not None:
        r = run_task(args.task, Path(args.out))
        print(json.dumps({"task": r["task"], "seconds": r["seconds"]}))
        return 0
    if args.merge:
        r = merge(Path(args.merge), Path(args.out))
        print(json.dumps({"status": r["status"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] else 1
    if args.smoke:
        r = local(Path(args.out))
        print(json.dumps({"label": "smoke", "seconds": r["seconds"], "report": r["report"]}))
        return 0
    ap.error("one of --list, --task, --merge, --local")
    return 2


if __name__ == "__main__":
    sys.exit(main())
