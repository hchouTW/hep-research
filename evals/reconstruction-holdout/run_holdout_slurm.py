#!/usr/bin/env python3
"""Slurm runner of the T13 harness (round 8, part B): the plan's sessions as a chain of Slurm jobs on the CPU partition.

Each job runs the frozen harness, from a checked copy, on the next batch of sessions of the same plan, inside the bwrap
sandbox the settings record requires (the jobs never pass --no-sandbox): job 1 creates the plan (`run --run-root ...
--seed S --max-sessions N`), every later job continues it (`run --resume RUN_ROOT --max-sessions N`). The jobs form an
`afterok` dependency chain, so they run one after the other and the harness keeps the plan's order and interleaving
across them; a stop (exit 1) or a refusal (exit 2) ends the chain: the later jobs never start (DependencyNeverSatisfied;
`scancel` them, as the site leaves them pending). The last job also runs the harness-cause reruns.

Inside the sandbox there is no Slurm access (no munge socket is bound, and the sandbox self-test checks that it is
absent; the session environment carries no SLURM_* variable). A session's process group and any leftover processes end
with its job (the Slurm cgroup); the harness records SLURM_JOB_ID in every run record. Each job writes
job-<k>.start.json and job-<k>.end.json beside its script; `status` combines them with the submission times of the
manifest into the queue wait of every job.

Usage:
  run_holdout_slurm.py plan --out DIR --sessions-per-job N --repetitions 3 --seed S [--python PY] [--cpus 8]
                            [--mem 16G] [--time 04:00:00] [--partition edr2-al9_short_serial] [--account ams]
                            -- <the harness's run arguments: --run-root --tasks --inputs --sut --settings --repo
                               --claude-bin --login-from ...>
      writes DIR/harness/ (the harness copy, checked against the SUT record), DIR/job-<k>.sh and
      DIR/slurm-manifest.json; submits nothing.
  run_holdout_slurm.py submit [--dry-run] DIR    submit the chain (sbatch --parsable; --dependency=afterok:<previous>)
  run_holdout_slurm.py status DIR                queue wait and exit of every job, from the jobs' own records
Exit codes: 0 ok; 2 rejected input. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HARNESS = HERE / "run_holdout.py"
PARTITION, ACCOUNT = "edr2-al9_short_serial", "ams"  # the CPU partition; never --qos (site rule)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def opt(argv: list, name: str):
    return argv[argv.index(name) + 1] if name in argv else None


def job_script(k: int, out: Path, a, harness_args: list) -> str:
    run_root = opt(harness_args, "--run-root")
    rest = [x for i, x in enumerate(harness_args)
            if x != "--run-root" and (i == 0 or harness_args[i - 1] != "--run-root")]
    if k == 1:
        call = ["run", "--run-root", run_root, *rest, "--seed", str(a.seed), "--repetitions", str(a.repetitions)]
    else:
        call = ["run", "--resume", run_root, *rest]
    call += ["--max-sessions", str(a.sessions_per_job)]
    cmd = " ".join(shlex.quote(x) for x in [a.python, "-B", str(out / "harness" / "run_holdout.py"), *call])
    q = shlex.quote
    start, end, harness = q(f"{out}/job-{k:03d}.start.json"), q(f"{out}/job-{k:03d}.end.json"), q(f"{out}/harness")
    return f"""#!/bin/bash
#SBATCH --job-name=t13-holdout-{k:03d}
#SBATCH --partition={a.partition}
#SBATCH --account={a.account}
#SBATCH --cpus-per-task={a.cpus}
#SBATCH --mem={a.mem}
#SBATCH --time={a.time}
#SBATCH --output={out}/job-{k:03d}.%j.log
#SBATCH --export=NONE
# T13 holdout sessions, batch {k} of the plan (run_holdout_slurm.py). Inside the bwrap sandbox: no Slurm access; the
# session's processes end with this job (cgroup).
set -uo pipefail
echo "{{\\"job\\": \\"$SLURM_JOB_ID\\", \\"start\\": \\"$(date -u +%FT%TZ)\\", \\"node\\": \\"$(hostname)\\"}}" > {start}
cd {harness} || exit 2
sha256sum -c --quiet harness.sha256 || {{ echo "harness copy changed"; exit 2; }}
{cmd}
rc=$?
echo "{{\\"job\\": \\"$SLURM_JOB_ID\\", \\"end\\": \\"$(date -u +%FT%TZ)\\", \\"exit\\": $rc}}" > {end}
exit $rc
"""


def cmd_plan(a, harness_args: list) -> int:
    for name in ("--run-root", "--tasks", "--sut", "--settings"):
        if opt(harness_args, name) is None:
            print(f"STATUS rejected: the harness arguments need {name}", file=sys.stderr)
            return 2
    if "--no-sandbox" in harness_args or "--dry-run" in harness_args:
        print("STATUS rejected: Slurm jobs never run without the sandbox, and are no dry runs", file=sys.stderr)
        return 2
    sut = json.loads(Path(opt(harness_args, "--sut")).read_text(encoding="utf-8"))
    tasks = json.loads(Path(opt(harness_args, "--tasks")).read_text(encoding="utf-8"))["tasks"]
    out = Path(a.out).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_./+-]+", str(out)):  # #SBATCH lines cannot quote: refuse other characters
        print("STATUS rejected: --out may hold only letters, digits and _ . / + -", file=sys.stderr)
        return 2
    (out / "harness").mkdir(parents=True, exist_ok=False)
    shutil.copyfile(HARNESS, out / "harness" / "run_holdout.py")  # jobs run from a checked copy, never the live tree
    h = sha256_file(out / "harness" / "run_holdout.py")
    if h != sut.get("harness_sha256"):
        print("STATUS rejected: this harness is not the SUT record's harness_sha256", file=sys.stderr)
        return 2
    (out / "harness" / "harness.sha256").write_text(f"{h}  run_holdout.py\n", encoding="utf-8")
    sessions = len(tasks) * a.repetitions
    n_jobs = math.ceil(sessions / a.sessions_per_job)
    jobs = []
    for k in range(1, n_jobs + 1):
        script = out / f"job-{k:03d}.sh"
        script.write_text(job_script(k, out, a, harness_args), encoding="utf-8")
        jobs.append({"k": k, "script": script.name, "job_id": None, "submitted": None})
    manifest = {"schema": "t13-slurm/1", "created": now(), "harness_sha256": h, "sessions": sessions,
                "sessions_per_job": a.sessions_per_job, "seed": a.seed, "repetitions": a.repetitions,
                "partition": a.partition, "account": a.account, "cpus": a.cpus, "mem": a.mem, "time": a.time,
                "order": "one afterok chain: job k+1 starts only after job k ended with exit 0, and each job continues "
                         "the plan.json order; the harness's interleaving rule therefore holds across jobs",
                "submitted": False, "jobs": jobs}
    (out / "slurm-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"status": "planned", "jobs": n_jobs, "sessions": sessions, "out": str(out)}))
    return 0


def cmd_submit(a) -> int:
    out = Path(a.dir).resolve()
    man = json.loads((out / "slurm-manifest.json").read_text(encoding="utf-8"))
    if man.get("submitted") and not a.dry_run:
        print("STATUS rejected: this chain was submitted already", file=sys.stderr)
        return 2
    prev = None
    for job in man["jobs"]:
        cmd = ["sbatch", "--parsable"] + ([f"--dependency=afterok:{prev}"] if prev else []) + [str(out / job["script"])]
        if a.dry_run:
            print(" ".join(cmd))
            prev = f"<job-{job['k']:03d}>"
            continue
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if r.returncode != 0:
            print(f"STATUS rejected: sbatch failed for {job['script']}: {r.stderr.strip()}", file=sys.stderr)
            break
        prev = r.stdout.strip().split(";")[0]
        job.update(job_id=prev, submitted=now())
    if not a.dry_run:
        man["submitted"] = True
        (out / "slurm-manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
    return 0


def cmd_status(a) -> int:
    out = Path(a.dir).resolve()
    man = json.loads((out / "slurm-manifest.json").read_text(encoding="utf-8"))
    for job in man["jobs"]:
        start = out / f"job-{job['k']:03d}.start.json"
        end = out / f"job-{job['k']:03d}.end.json"
        job["start"] = json.loads(start.read_text())["start"] if start.exists() else None
        job["exit"] = json.loads(end.read_text())["exit"] if end.exists() else None
        if job.get("submitted") and job["start"]:
            t0 = dt.datetime.strptime(job["submitted"], "%Y-%m-%dT%H:%M:%SZ")
            t1 = dt.datetime.strptime(job["start"], "%Y-%m-%dT%H:%M:%SZ")
            job["queue_wait_s"] = int((t1 - t0).total_seconds())
    (out / "slurm-manifest.json").write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": [{k: j.get(k) for k in ("k", "job_id", "queue_wait_s", "exit")} for j in man["jobs"]]}))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    harness_args = []
    if "--" in argv:
        i = argv.index("--")
        argv, harness_args = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description="Slurm runner of the T13 harness (see the module docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--out", required=True)
    p.add_argument("--sessions-per-job", type=int, required=True)
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--python", default=sys.executable)
    p.add_argument("--cpus", type=int, default=8)
    p.add_argument("--mem", default="16G")
    p.add_argument("--time", default="04:00:00")
    p.add_argument("--partition", default=PARTITION)
    p.add_argument("--account", default=ACCOUNT)
    s = sub.add_parser("submit")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("dir")
    t = sub.add_parser("status")
    t.add_argument("dir")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        if a.sessions_per_job < 1:
            print("STATUS rejected: --sessions-per-job must be at least 1", file=sys.stderr)
            return 2
        return cmd_plan(a, harness_args)
    return cmd_submit(a) if a.cmd == "submit" else cmd_status(a)


if __name__ == "__main__":
    sys.exit(main())
