#!/usr/bin/env python3
"""Manifest-based local partition, resubmission and merge for embarrassingly parallel work (event generation,
histogram filling, toys), with bounded, explicit recovery.

Rules this enforces:
- The work is split once into a manifest of chunks (id, item range, seed); the manifest hash ties every output to it.
- A chunk's output is written atomically and only once; resubmission skips finished chunks, so nothing is counted twice.
- Retries happen only when the run configuration sets "max_attempts"; with no configuration a failed chunk is not
  retried. max_attempts counts every attempt since the chunk's last reset, over all runs: running again does not buy
  more attempts. A chunk whose last two attempts failed the same way (same exit code, timeout, missing or invalid
  output) is stopped even if attempts remain.
- State (attempts, errors) is kept on disk after any failure, so a later resubmission continues where it stopped.
- Merging reads each chunk from its own file chunks/<id>.json only and checks that it belongs to this manifest, with
  the manifest's range and seed, and that the ranges tile [0, n) with no gap or overlap; a missing chunk makes the
  merge 'incomplete', never a silent partial sum. A stray file claiming a chunk is never summed; if its result
  differs from the chunk's own file the merge is 'incomplete' (merge.conflicting_duplicate).

Python API: make_manifest(job_id, n_items, chunk_size, seed) -> dict; run(manifest, state_dir, worker, config=None)
-> dict; merge(manifest, state_dir, combine) -> dict. worker(chunk) returns a JSON-serializable result or raises.
CLI:
  plan  --job ID --items N --chunk-size K --seed S --out manifest.json
  run   --manifest manifest.json --state DIR --cmd "python3 worker.py --start {start} --stop {stop} --seed {seed} --out {out}"
        [--timeout S] [--env-passthrough NAME ...]   the worker gets PATH, HOME, locale and TMPDIR only, plus named variables
        [--config run-config.json]   (the command writes JSON to {out}; exit 0 means success)
  status --manifest manifest.json --state DIR
  merge --manifest manifest.json --state DIR   (sums numeric lists/values key by key)
  reset --manifest manifest.json --state DIR --chunks c0004 --reason "fixed input path"   (after fixing a stopped chunk)
Exit codes: 0 complete, 1 incomplete or failed chunks, 2 bad input or a state folder in use by another run, reset
or merge ({"error": ..., "code": "partition.locked"}; status takes no lock).
The engine lives in core/partition (shared with the batch-scheduler adapter); this file is its CLI.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from core.partition.engine import (PartitionError, _hash, _load_state, _reduce, _sum, _write_atomic, check_template,  # noqa: E402,F401,E501
                                   make_manifest, merge, reset, run, status, validate_manifest)
from core.partition.executors import allowed_env  # noqa: E402


class WorkerFailure(RuntimeError):
    """A failed chunk command. 'signature' is what the repeated-failure rule compares (exit code, timeout, missing or
    invalid output); the message keeps the stderr tail for people, which may hold paths or times that vary."""

    def __init__(self, signature: str, message: str):
        super().__init__(message)
        self.signature = signature


def _cmd_worker(template: str, state_dir: Path, timeout: float | None = None, passthrough=()):
    """The worker runs with an allow-listed environment (core.partition.executors.ENV_ALLOW plus passthrough names)
    and an optional timeout, the same rules as batch jobs (X16)."""
    env = allowed_env(None, passthrough)

    def worker(ch):
        with tempfile.TemporaryDirectory(dir=state_dir) as td:
            out = Path(td) / "out.json"
            cmd = [a.format(start=ch["start"], stop=ch["stop"], seed=ch["seed"], out=out, id=ch["id"]) for a in shlex.split(template)]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise WorkerFailure("timeout", f"timeout after {timeout} s") from None
            if proc.returncode != 0:
                raise WorkerFailure(f"exit={proc.returncode}", f"exit {proc.returncode}: {proc.stderr.strip()[-300:]}")
            if not out.is_file():
                raise WorkerFailure("missing-output", f"exit 0 but the command wrote no output to {out}")
            try:
                return json.loads(out.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise WorkerFailure("invalid-output", f"output is not valid JSON: {exc}") from None
    return worker


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--job", required=True)
    p.add_argument("--items", type=int, required=True)
    p.add_argument("--chunk-size", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    for name in ("run", "status", "merge", "reset"):
        s = sub.add_parser(name)
        s.add_argument("--manifest", type=Path, required=True)
        s.add_argument("--state", type=Path, required=True)
        if name == "run":
            s.add_argument("--cmd", dest="template", required=True)
            s.add_argument("--config", type=Path)
            s.add_argument("--timeout", type=float, help="seconds before a chunk's command is stopped (counts as a failure)")
            s.add_argument("--env-passthrough", nargs="*", default=[], metavar="NAME",
                           help="environment variables passed to the worker besides PATH, HOME, locale and TMPDIR")
        if name == "reset":
            s.add_argument("--chunks", nargs="+", required=True)
            s.add_argument("--reason", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "plan":
            _write_atomic(args.out, make_manifest(args.job, args.items, args.chunk_size, args.seed))
            print(json.dumps({"manifest": str(args.out)}))
            return 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.cmd == "run":
            validate_manifest(manifest)
            check_template(args.template)
            cfg = json.loads(args.config.read_text(encoding="utf-8")) if args.config else None
            args.state.mkdir(parents=True, exist_ok=True)
            res = run(manifest, args.state, _cmd_worker(args.template, args.state, args.timeout, args.env_passthrough), cfg)
            print(json.dumps(res, indent=1))
            return 0 if res["complete"] else 1
        if args.cmd == "status":
            res = status(manifest, args.state)
            print(json.dumps(res, indent=1))
            return 0 if res["complete"] else 1
        if args.cmd == "reset":
            reset(args.state, args.chunks, args.reason)
            print(json.dumps(status(manifest, args.state), indent=1))
            return 0
        res = merge(manifest, args.state)
        print(json.dumps(res, indent=1))
        return 0 if res["status"] == "complete" else 1
    except PartitionError as exc:
        print(json.dumps({"error": str(exc), "code": exc.code}))
        return 2
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
