"""Study S1 of phase 5 (task card `docs/dev/simulator-calibration/simcal-tasks/phase-5.md`, "Studies to register
before their runs", conditional on reading L8 "G4-L needs its own false-alarm calibration"): the false-alarm rate of
G4-L with a correct, cross-fitted, calibrated learned ratio on the post-hoc fixture (core/calibration/data/
toy_posthoc.json), 1000 repetitions at 40,000 events, the P0 rule form, acceptance <= 16 false alarms of 1000 (the
phase-1 form of the row-2004 rule). Slurm job array tasks write raw per-repetition records; the merge applies the
registered rule (failures are reported, never retuned). Not a unit test module.

  python3 calibration_phase5_g4l.py --list                        the task table (JSON)
  python3 calibration_phase5_g4l.py --task K --out DIR            one task of the array
  python3 calibration_phase5_g4l.py --merge DIR --out FILE        merge and judge (exit 0 passed, 1 failed/incomplete)
  python3 calibration_phase5_g4l.py --local --out FILE            two repetitions at 4,000 events (`smoke`)

Seeds: repetition r draws its nominal, training, closure and resample seeds from SeedSequence([SEED0 + r, j])
(j = 0..3): no stream shared between repetitions. A repetition is a false alarm when G4-L fails; a rejected or
erroring repetition makes the array incomplete (never counted as passing). Every record is `synthetic` and
`provisional-thresholds`.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from core.calibration import evaluator as E  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import kernel_check, linear, reweight, toy  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")

FLAGS = ["synthetic", "provisional-thresholds"]
FILES = ["core/calibration/" + f for f in ("learned.py", "reweight.py", "toy.py", "kernel_check.py", "linear.py",
                                            "design.py", "data/toy_posthoc.json")] + \
    ["tests/core/calibration_phase5_g4l.py", "docs/dev/simulator-calibration/simcal-tasks/phase-5.md"]
SEED0 = 20261514
REPS = 1000
EVENTS = 40_000
BLOCK = 50                                      # repetitions per task
ALPHA = 0.01


def max_false_alarms(n: int, rate: float, pass_probability: float = 0.97) -> int:
    """The smallest count c with P(Binomial(n, rate) <= c) >= pass_probability (the phase-1 form of the row-2004 rule:
    <= 16 of 1000 at rate 0.01)."""
    return int(stats.binom.ppf(pass_probability, n, rate))


MAX_FALSE_ALARMS = max_false_alarms(REPS, ALPHA)          # 16
TASKS = [{"r0": r0, "reps": min(BLOCK, REPS - r0), "events": EVENTS} for r0 in range(0, REPS, BLOCK)]


def _seed(r: int, j: int) -> int:
    return int(np.random.SeedSequence([SEED0 + r, j]).generate_state(1)[0] % (2 ** 31 - 1)) + 1


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


def repetition(r: int, events: int) -> dict:
    """One repetition: the fixture at `events` with the seeds of r; design at the prior centre, P0's points, G4-L."""
    contract, plan = toy.posthoc_fixture()
    plan = copy.deepcopy(plan)
    plan["evaluator"]["spec"]["runs"][0]["n"] = int(events)
    plan["seeds"] = {"nominal": _seed(r, 0), "learned": _seed(r, 1), "closure": _seed(r, 2),
                     "resample": _seed(r, 3)}
    t0 = time.time()
    try:
        ev = E.make(plan, contract)
        d = linear.design(ev, contract, plan)
        pts = kernel_check.default_points(ev, contract, plan)
        g = reweight.g4l_run(ev, contract, d, pts)
    except Exception as exc:                       # recorded, never counted as passing
        return {"r": r, "status": "error", "error": repr(exc), "seconds": time.time() - t0}
    return {"r": r, "status": g["status"], "findings": [f["code"] for f in g.get("findings", [])],
            "max_ratio": max((p["max_ratio"] for p in g.get("points", [])), default=None),
            "points": [p["point"] for p in g.get("points", [])], "z": g.get("z"), "seconds": time.time() - t0}


def run_task(i: int, out_dir: Path, tasks=None) -> dict:
    kw = (tasks or TASKS)[i]
    t0 = time.time()
    rows = [repetition(r, kw["events"]) for r in range(kw["r0"], kw["r0"] + kw["reps"])]
    rec = {"task": i, "kwargs": kw, "rows": rows, "seconds": time.time() - t0, "provenance": provenance(),
           "flags": FLAGS}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


def judge(rows: list, reps: int = REPS, max_fa: int = MAX_FALSE_ALARMS) -> dict:
    """The registered rule: <= max_fa false alarms (G4-L failed) of `reps` repetitions; any missing, rejected or
    erroring repetition makes the result incomplete (not passed)."""
    seen = {row["r"]: row for row in rows}
    bad = sorted(r for r, row in seen.items() if row["status"] not in ("passed", "failed"))
    fa = sum(1 for row in seen.values() if row["status"] == "failed")
    complete = len(seen) == reps and not bad
    return {"false_alarms": fa, "repetitions": len(seen), "required": reps, "max_false_alarms": max_fa,
            "rate": fa / max(len(seen), 1), "not_judged": bad, "complete": complete,
            "passed": bool(complete and fa <= max_fa), "flags": FLAGS}


def merge(out_dir: Path, out: Path, tasks=None, reps: int = REPS, max_fa: int = MAX_FALSE_ALARMS) -> dict:
    tasks = tasks or TASKS
    recs = {}
    for i in range(len(tasks)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    rows = [row for r in recs.values() if r for row in r["rows"]]
    res = judge(rows, reps, max_fa)
    complete = res["complete"] and not missing and len(commits) == 1 and not dirty
    rep = {"study": "phase-5 S1, G4-L false alarms (post-hoc fixture)", "complete": complete,
           "missing_tasks": missing, "commits": sorted(c for c in commits if c), "dirty": dirty, "result": res,
           "passed": bool(complete and res["passed"]), "provenance": provenance(), "flags": FLAGS,
           "seconds": float(sum(r["seconds"] for r in recs.values() if r))}
    io.write_json(str(out), io.jsonable(rep))
    return rep


SMOKE = [{"r0": 900000, "reps": 2, "events": 4000}]


def local(out: Path) -> dict:
    t0 = time.time()
    d = out.parent / (out.stem + "_tasks")
    for i in range(len(SMOKE)):
        run_task(i, d, SMOKE)
    rep = merge(d, out, SMOKE, reps=sum(t["reps"] for t in SMOKE), max_fa=0)
    rep.update(label="smoke", seconds=time.time() - t0)
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
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["passed"] else 1
    if args.smoke:
        r = local(Path(args.out))
        print(json.dumps({"label": "smoke", "seconds": r["seconds"], "result": r["result"]}))
        return 0
    ap.error("one of --list, --task, --merge, --local")
    return 2


if __name__ == "__main__":
    sys.exit(main())
