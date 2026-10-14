#!/usr/bin/env python3
"""Worker-side chunk runner: runs one chunk of a manifest on a batch node and writes its output once.

The campaign copies this file next to its spec, so it must stay self-contained (standard library only, no plugin
imports). That copy is agent-writable: with protected data a trusted submitter must verify its full digest (and the
spec's) before a job runs it. It never chooses a seed or a chunk on its own: the chunk comes from the explicit --chunk/--attempt pair or
from the submission map written at submit time (--map MAP --index N, where N is the scheduler's array index), and the
seed, start and stop come from the manifest inside the spec.

  runner.py --spec SPEC (--out-dir DIR | --out-root ROOT) (--chunk ID --attempt ATTEMPT | --map MAP --index N)

SPEC is JSON {"manifest": {...}, "cmd": "... {start} {stop} {seed} {out} {id} ...", "container_image": optional}.
The command writes a JSON result to {out}; exit 0 means success. With --out-root, DIR is ROOT/<chunk ID>. The runner
then writes
  DIR/<attempt>.json       {"chunk_id", "manifest_hash", "attempt_id", "start", "stop", "seed", "result"}
  DIR/<attempt>.meta.json  {"chunk_id", "manifest_hash", "attempt_id", "host", "start_time", "end_time", "exit_code",
                            "signal", "python", "container_image", "run_file", "runner_error"}
Both are written to a temporary file in DIR and then linked into place without overwriting: a second execution of
the same attempt (an eviction or a requeue that ran the job again) writes <attempt>.rerun-<k>.json instead, which
collection records as a duplicate and never sums. A failed command leaves only the meta file.
Exit codes: the command's exit code (128 + N when it died from signal N); 70 when the command succeeded but its result
was missing or not JSON; 2 for bad arguments or a chunk not in the manifest, and for a command template that cannot be
filled (then the meta file records the reason, so the attempt is 'failed', never 'lost'); 3 when protected use is
refused (the meta file records it; the command does not run).
Protected mode (task P1): when the spec, the output directory or the working directory lies in a project that declares
agent_policy, the runner checks the protected inputs through the plugin's guard (core.protected.guard) when it runs
from the plugin itself; a copy of the runner cannot check them, so it refuses: protected batch execution runs through
the trusted submitter. This keeps the file self-contained: the detection below is standard library only.
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
    # timezone.utc, not the 3.11+ UTC alias: the runner executes under the batch workers' Python 3.9.
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: UP017


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


def protected_refusal(paths) -> str | None:
    """None outside protected mode; otherwise None only when the plugin's guard accepts the protected inputs."""
    on = False
    for start in [*(Path(p).absolute() for p in paths if p), Path.cwd()]:
        cur = start if start.is_dir() else start.parent
        for d in (cur, *cur.parents):
            cfg = d / "hep-research.project.json"
            if cfg.is_file():
                try:
                    on = on or "agent_policy" in json.loads(cfg.read_text(encoding="utf-8"))
                except (OSError, ValueError, TypeError):
                    pass
                break
    if not on:
        return None
    here = Path(__file__).resolve()
    if not (here.parent.name == "partition" and here.parent.parent.name == "core"):
        return ("protected mode: this copy of the runner cannot check the revocation and qualification inputs; "
                "protected batch execution runs through the trusted submitter")
    sys.path.insert(0, str(here.parents[2]))
    from core.protected.guard import ProtectedUseRefused, guard
    try:
        guard("core.partition.runner", paths=[p for p in paths if p])
    except ProtectedUseRefused as exc:
        return str(exc)
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out-dir")
    ap.add_argument("--out-root")
    ap.add_argument("--chunk")
    ap.add_argument("--attempt")
    ap.add_argument("--map")
    ap.add_argument("--index", type=int)
    args = ap.parse_args(argv)
    try:
        if (args.out_dir is None) == (args.out_root is None):
            raise ValueError("give exactly one of --out-dir and --out-root")
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
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.out_root) / cid
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {"chunk_id": cid, "manifest_hash": manifest["manifest_hash"], "attempt_id": aid, "host": socket.gethostname(),
            "start_time": _now(), "python": platform.python_version(),
            "container_image": spec.get("container_image") or os.environ.get("HEP_CONTAINER_IMAGE"),
            "signal": None, "runner_error": None, "run_file": None}
    refused = protected_refusal([args.spec, str(out_dir)])
    if refused:
        meta.update(runner_error=refused, exit_code=3, end_time=_now())
        _place(out_dir, aid, ".meta.json", meta, None)
        return 3
    with tempfile.TemporaryDirectory(prefix=".run-", dir=out_dir) as td:
        out = Path(td) / "out.json"
        result = None
        try:
            cmd = [a.format(start=chunk["start"], stop=chunk["stop"], seed=chunk["seed"], out=out, id=cid)
                   for a in shlex.split(spec["cmd"])]
        except (KeyError, IndexError, ValueError, AttributeError) as exc:
            # a literal brace in the template (a dict or f-string inside 'python -c ...') must be doubled: {{ }}
            meta["runner_error"] = (f"command template could not be filled ({type(exc).__name__}: {exc}); "
                                    "write literal braces as {{ and }}")
            cmd, code = None, 2
        if cmd is not None:
            sys.stdout.flush()
            try:
                proc = subprocess.run(cmd, timeout=spec.get("worker_timeout_s"))  # None: no limit
                code = proc.returncode
                if code < 0:
                    meta["signal"], code = -code, 128 - code
            except subprocess.TimeoutExpired:
                meta["runner_error"], code = f"worker command exceeded worker_timeout_s={spec['worker_timeout_s']}", 124
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
