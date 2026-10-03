#!/usr/bin/env python3
"""Worker-side chunk runner: runs one chunk of a manifest on a batch node and writes its output once.

The campaign copies this file next to its spec, so it must stay self-contained (standard library only, no plugin
imports). It never chooses a seed or a chunk on its own: the chunk comes from the explicit --chunk/--attempt pair or
from the submission map written at submit time (--map MAP --index N, where N is the scheduler's array index), and the
seed, start and stop come from the manifest inside the spec.

  runner.py --spec SPEC --out-dir DIR (--chunk ID --attempt ATTEMPT | --map MAP --index N)

SPEC is JSON {"manifest": {...}, "cmd": "... {start} {stop} {seed} {out} {id} ...", "container_image": optional}.
The command writes a JSON result to {out}; exit 0 means success. The runner then writes
  DIR/<attempt>.json       {"chunk_id", "manifest_hash", "attempt_id", "start", "stop", "seed", "result"}
  DIR/<attempt>.meta.json  {"chunk_id", "manifest_hash", "attempt_id", "host", "start_time", "end_time", "exit_code",
                            "signal", "python", "container_image", "run_file", "runner_error"}
Both are written to a temporary file in DIR and then linked into place without overwriting: a second execution of
the same attempt (an eviction or a requeue that ran the job again) writes <attempt>.rerun-<k>.json instead, which
collection records as a duplicate and never sums. A failed command leaves only the meta file.
Exit codes: the command's exit code (128 + N when it died from signal N); 70 when the command succeeded but its result
was missing or not JSON; 2 for bad arguments or a chunk not in the manifest.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_ERROR = 70


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _place(out_dir: Path, stem: str, suffix: str, obj, run_file: str | None) -> str:
    """Write obj to a temporary file in out_dir, then hard-link it to the first free name; never overwrite."""
    fd, tmp = tempfile.mkstemp(dir=out_dir, prefix=".tmp-", suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, sort_keys=True)
    try:
        names = ([run_file] if run_file else []) + [f"{stem}{suffix}"] + [f"{stem}.rerun-{k}{suffix}" for k in range(1, 1000)]
        for name in names:
            try:
                os.link(tmp, out_dir / name)
                return name
            except FileExistsError:
                continue
        raise FileExistsError(f"no free output name for {stem}")
    finally:
        os.unlink(tmp)


def resolve(args) -> tuple[str, str]:
    if args.map is not None:
        rows = json.loads(Path(args.map).read_text(encoding="utf-8"))
        row = next((r for r in rows if r["index"] == args.index), None)
        if row is None:
            raise KeyError(f"index {args.index} not in the submission map")
        return row["chunk_id"], row["attempt_id"]
    return args.chunk, args.attempt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--chunk")
    ap.add_argument("--attempt")
    ap.add_argument("--map")
    ap.add_argument("--index", type=int)
    args = ap.parse_args(argv)
    try:
        if (args.map is None) == (args.chunk is None) or (args.chunk and not args.attempt) or (args.map and args.index is None):
            raise ValueError("give either --chunk and --attempt, or --map and --index")
        spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        manifest = spec["manifest"]
        cid, aid = resolve(args)
        chunk = next((c for c in manifest["chunks"] if c["id"] == cid), None)
        if chunk is None:
            raise KeyError(f"chunk {cid} not in the manifest")
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"chunk_id": cid, "manifest_hash": manifest["manifest_hash"], "attempt_id": aid, "host": socket.gethostname(),
            "start_time": _now(), "python": platform.python_version(),
            "container_image": spec.get("container_image") or os.environ.get("HEP_CONTAINER_IMAGE"),
            "signal": None, "runner_error": None, "run_file": None}
    with tempfile.TemporaryDirectory(prefix=".run-", dir=out_dir) as td:
        out = Path(td) / "out.json"
        cmd = [a.format(start=chunk["start"], stop=chunk["stop"], seed=chunk["seed"], out=out, id=cid) for a in shlex.split(spec["cmd"])]
        sys.stdout.flush()
        proc = subprocess.run(cmd)
        code = proc.returncode
        if code < 0:
            meta["signal"], code = -code, 128 - code
        result = None
        if code == 0:
            try:
                result = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                meta["runner_error"], code = f"result missing or not JSON: {exc}", RESULT_ERROR
    meta.update(exit_code=code, end_time=_now())
    if code == 0:
        doc = {"chunk_id": cid, "manifest_hash": manifest["manifest_hash"], "attempt_id": aid, "start": chunk["start"],
               "stop": chunk["stop"], "seed": chunk["seed"], "result": result}
        meta["run_file"] = _place(out_dir, aid, ".json", doc, None)
    _place(out_dir, aid, ".meta.json", meta, meta["run_file"] and meta["run_file"][:-5] + ".meta.json")
    return code


if __name__ == "__main__":
    sys.exit(main())
