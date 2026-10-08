#!/usr/bin/env python3
"""Manifest-based local partition, resubmission and merge for embarrassingly parallel work (event generation,
histogram filling, toys), with bounded, explicit recovery.

Rules this enforces:
- The work is split once into a manifest of chunks (id, item range, seed); the manifest hash ties every output to it.
- A chunk's output is written atomically and only once; resubmission skips finished chunks, so nothing is counted twice.
- Retries happen only when the run configuration sets "max_attempts"; with no configuration a failed chunk is not
  retried. A chunk whose last two attempts failed with the same error is stopped even if attempts remain.
- State (attempts, errors) is kept on disk after any failure, so a later resubmission continues where it stopped.
- Merging checks that every manifest chunk is present exactly once, belongs to this manifest, and that the item
  ranges tile [0, n) with no gap or overlap; a missing chunk makes the merge 'incomplete', never a silent partial sum.

Python API: make_manifest(job_id, n_items, chunk_size, seed) -> dict; run(manifest, state_dir, worker, config=None)
-> dict; merge(manifest, state_dir, combine) -> dict. worker(chunk) returns a JSON-serializable result or raises.
CLI:
  plan  --job ID --items N --chunk-size K --seed S --out manifest.json
  run   --manifest manifest.json --state DIR --cmd "python3 worker.py --start {start} --stop {stop} --seed {seed} --out {out}"
        [--config run-config.json]   (the command writes JSON to {out}; exit 0 means success)
  status --manifest manifest.json --state DIR
  merge --manifest manifest.json --state DIR   (sums numeric lists/values key by key)
  reset --manifest manifest.json --state DIR --chunks c0004 --reason "fixed input path"   (after fixing a stopped chunk)
Exit codes: 0 complete, 1 incomplete or failed chunks, 2 bad input.
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
from core.partition.engine import (_hash, _load_state, _reduce, _sum, _write_atomic, check_template, make_manifest, merge,  # noqa: E402,F401,E501
                                   reset, run, status, validate_manifest)


def _cmd_worker(template: str, state_dir: Path):
    def worker(ch):
        with tempfile.TemporaryDirectory(dir=state_dir) as td:
            out = Path(td) / "out.json"
            cmd = [a.format(start=ch["start"], stop=ch["stop"], seed=ch["seed"], out=out, id=ch["id"]) for a in shlex.split(template)]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"exit {proc.returncode}: {proc.stderr.strip()[-300:]}")
            return json.loads(out.read_text(encoding="utf-8"))
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
            res = run(manifest, args.state, _cmd_worker(args.template, args.state), cfg)
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
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
