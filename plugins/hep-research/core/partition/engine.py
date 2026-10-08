"""Manifest-based partition engine: manifest, write-once chunk outputs, bounded resubmission, complete merge.

Rules this enforces:
- The work is split once into a manifest of chunks (id, item range, seed); the manifest hash ties every output to it.
- A chunk's output is written atomically and only once; resubmission skips finished chunks, so nothing is counted twice.
- Retries happen only when the run configuration sets "max_attempts"; with no configuration a failed chunk is not
  retried. A chunk whose last two attempts failed with the same error is stopped even if attempts remain.
- State (attempts, errors) is kept on disk after any failure, so a later resubmission continues where it stopped.
- Merging checks that every manifest chunk is present exactly once, belongs to this manifest, and that the item
  ranges tile [0, n) with no gap or overlap; a missing chunk makes the merge 'incomplete', never a silent partial sum.

API: make_manifest(job_id, n_items, chunk_size, seed) -> dict; validate_manifest(manifest); check_template(cmd); run(manifest, state_dir, worker, config=None) -> dict
(synchronous, in-process); status(manifest, state_dir); reset(state_dir, chunk_ids, reason); merge(manifest,
state_dir, combine=None). Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import string
import tempfile
from pathlib import Path
from typing import Any


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


CHUNK_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # chunk IDs name output paths: no separators, dots or spaces
JOB_ID = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
PLACEHOLDERS = ("start", "stop", "seed", "out", "id")


def validate_manifest(manifest) -> dict:
    """The manifest unchanged, or ValueError: a job ID and chunk IDs from a safe charset (a chunk ID builds output
    paths, so '../x' would write outside the campaign), integer ranges that tile [0, n_items) in order, integer seeds,
    and a manifest_hash that matches the content."""
    if not isinstance(manifest, dict):
        raise ValueError("the manifest must be a JSON object")
    body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    if manifest.get("manifest_hash") != _hash(body):
        raise ValueError("manifest_hash does not match the manifest content")
    if not isinstance(manifest.get("job_id"), str) or not JOB_ID.match(manifest["job_id"]):
        raise ValueError(f"job_id must match {JOB_ID.pattern}")
    n = manifest.get("n_items")
    chunks = manifest.get("chunks")
    if not _is_int(n) or n <= 0 or not isinstance(chunks, list) or not chunks:
        raise ValueError("the manifest needs a positive integer n_items and a non-empty chunk list")
    seen, pos = set(), 0
    for ch in chunks:
        cid = ch.get("id") if isinstance(ch, dict) else None
        if not isinstance(cid, str) or not CHUNK_ID.match(cid):
            raise ValueError(f"chunk id {cid!r} must match {CHUNK_ID.pattern}")
        if cid in seen:
            raise ValueError(f"duplicate chunk id {cid}")
        seen.add(cid)
        if not all(_is_int(ch.get(k)) for k in ("start", "stop", "seed")):
            raise ValueError(f"chunk {cid}: start, stop and seed must be integers")
        if ch["start"] != pos or ch["stop"] <= ch["start"]:
            raise ValueError(f"chunk {cid}: ranges must tile [0, n_items) in order without gaps or overlaps")
        pos = ch["stop"]
    if pos != n:
        raise ValueError(f"the chunk ranges end at {pos}, not at n_items = {n}")
    return manifest


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def check_template(cmd) -> list[str]:
    """The command template split into arguments, or ValueError. Only the fields {start} {stop} {seed} {out} {id} are
    allowed, with no conversion or format spec; {out} is required; literal braces must be doubled ({{ }}). The
    template is trial-rendered, so a template that passes cannot fail to fill in the runner."""
    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("the command template is empty")
    try:
        args = shlex.split(cmd)
    except ValueError as exc:
        raise ValueError(f"the command template cannot be split into arguments: {exc}") from None
    used = set()
    for arg in args:
        try:
            fields = list(string.Formatter().parse(arg))
        except ValueError as exc:
            raise ValueError(f"argument {arg!r}: {exc}; write literal braces as {{{{ and }}}}") from None
        for _, name, spec, conv in fields:
            if name is None:
                continue
            if name not in PLACEHOLDERS or spec or conv:
                raise ValueError(f"argument {arg!r}: only {{start}} {{stop}} {{seed}} {{out}} {{id}} are allowed, without "
                                 "conversions or format specs; write literal braces as {{ and }}")
            used.add(name)
    if "out" not in used:
        raise ValueError("the command template must write its result to {out}")
    sample = {"start": 0, "stop": 1, "seed": 0, "out": "/tmp/out.json", "id": "c0000"}
    return [a.format(**sample) for a in args]


def make_manifest(job_id: str, n_items: int, chunk_size: int, seed: int) -> dict:
    if n_items <= 0 or chunk_size <= 0:
        raise ValueError("n_items and chunk_size must be positive")
    chunks = [{"id": f"c{k:04d}", "start": s, "stop": min(s + chunk_size, n_items), "seed": seed * 100003 + k}
              for k, s in enumerate(range(0, n_items, chunk_size))]
    body = {"job_id": job_id, "n_items": n_items, "chunk_size": chunk_size, "seed": seed, "chunks": chunks}
    return dict(body, manifest_hash=_hash(body))


def _write_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, sort_keys=True)
    os.replace(tmp, path)


def _load_state(state_dir: Path) -> dict:
    p = state_dir / "state.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"chunks": {}}


def run(manifest: dict, state_dir, worker, config: dict | None = None) -> dict:
    state_dir = Path(state_dir)
    max_attempts = int((config or {}).get("max_attempts", 1))
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    state = _load_state(state_dir)
    if state.get("manifest_hash", manifest["manifest_hash"]) != manifest["manifest_hash"]:
        raise ValueError("state directory belongs to a different manifest")
    state["manifest_hash"] = manifest["manifest_hash"]
    ran, skipped = [], []
    for ch in manifest["chunks"]:
        out = state_dir / "chunks" / f"{ch['id']}.json"
        st = state["chunks"].setdefault(ch["id"], {"attempts": 0, "errors": [], "status": "pending"})
        if out.exists():
            st["status"] = "done"
            skipped.append(ch["id"])
            continue
        tries_this_run = 0
        while tries_this_run < max_attempts:
            if len(st["errors"]) >= 2 and st["errors"][-1] == st["errors"][-2]:
                st["status"] = "stopped-repeated-failure"
                break
            st["attempts"] += 1
            tries_this_run += 1
            ran.append(ch["id"])
            try:
                result = worker(ch)
            except Exception as exc:  # noqa: BLE001 - every worker failure is recorded, not hidden
                st["errors"].append(f"{type(exc).__name__}: {exc}")
                st["status"] = "failed"
                _write_atomic(state_dir / "state.json", state)
                continue
            _write_atomic(out, {"chunk_id": ch["id"], "manifest_hash": manifest["manifest_hash"], "start": ch["start"],
                                "stop": ch["stop"], "seed": ch["seed"], "result": result})
            st["status"] = "done"
            break
        if st["status"] == "failed" and len(st["errors"]) >= 2 and st["errors"][-1] == st["errors"][-2]:
            st["status"] = "stopped-repeated-failure"
        _write_atomic(state_dir / "state.json", state)
    summary = status(manifest, state_dir)
    return dict(summary, invocations=ran, skipped_done=skipped, max_attempts=max_attempts,
                retries_configured=bool(config and "max_attempts" in config))


def reset(state_dir, chunk_ids, reason: str) -> dict:
    """Clear the error history of chunks after their cause was fixed, so they can run again. Kept in 'resets'."""
    state_dir = Path(state_dir)
    state = _load_state(state_dir)
    for cid in chunk_ids:
        st = state["chunks"].get(cid)
        if st is None:
            raise ValueError(f"unknown chunk {cid}")
        state.setdefault("resets", []).append({"chunk": cid, "reason": reason, "errors": st["errors"], "attempts": st["attempts"]})
        st.update(errors=[], status="pending")
    _write_atomic(state_dir / "state.json", state)
    return state


def status(manifest: dict, state_dir) -> dict:
    state = _load_state(Path(state_dir))
    rows = {c["id"]: state["chunks"].get(c["id"], {"attempts": 0, "errors": [], "status": "pending"}) for c in manifest["chunks"]}
    for cid in rows:
        if (Path(state_dir) / "chunks" / f"{cid}.json").exists():
            rows[cid] = dict(rows[cid], status="done")
    not_done = sorted(c for c, r in rows.items() if r["status"] != "done")
    return {"complete": not not_done, "not_done": not_done, "chunks": rows}


def _sum(a, b):
    if isinstance(a, list):
        if len(a) != len(b):
            raise ValueError("chunk results have different lengths")
        return [_sum(x, y) for x, y in zip(a, b)]
    if isinstance(a, dict):
        if set(a) != set(b):
            raise ValueError("chunk results have different keys")
        return {k: _sum(a[k], b[k]) for k in a}
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError(f"the default merge adds numbers only, got {type(a).__name__} and {type(b).__name__}; "
                         "pass a combine function for other results")
    return a + b


def _nonfinite(x, path="result") -> str | None:
    """Path of the first NaN or infinity in a chunk result, else None."""
    if isinstance(x, float) and not math.isfinite(x):
        return path
    if isinstance(x, dict):
        return next((p for k, v in x.items() if (p := _nonfinite(v, f"{path}.{k}"))), None)
    if isinstance(x, list):
        return next((p for i, v in enumerate(x) if (p := _nonfinite(v, f"{path}[{i}]"))), None)
    return None


def merge(manifest: dict, state_dir, combine=None) -> dict:
    """Merge chunk outputs; combine(list_of_results) defaults to key-by-key summation."""
    combine = combine or (lambda rs: _reduce(rs))
    problems: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    results = []
    wanted = {c["id"]: c for c in manifest["chunks"]}
    for f in sorted((Path(state_dir) / "chunks").glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            problems.append({"code": "merge.unreadable", "file": f.name})
            continue
        cid = doc.get("chunk_id")
        if doc.get("manifest_hash") != manifest["manifest_hash"]:
            problems.append({"code": "merge.foreign_chunk", "file": f.name, "message": "output belongs to another manifest"})
            continue
        if cid not in wanted:
            problems.append({"code": "merge.unknown_chunk", "file": f.name})
            continue
        if cid in seen:
            problems.append({"code": "merge.duplicate_chunk", "file": f.name, "message": f"{cid} also in {seen[cid]}; not counted twice"})
            continue
        c = wanted[cid]
        if (doc["start"], doc["stop"]) != (c["start"], c["stop"]):
            problems.append({"code": "merge.range_mismatch", "file": f.name})
            continue
        bad = _nonfinite(doc["result"])
        if bad:
            problems.append({"code": "merge.non_finite", "file": f.name, "message": f"{bad} is not finite"})
            continue
        seen[cid] = f.name
        results.append((c["start"], doc["result"]))
    missing = sorted(set(wanted) - set(seen))
    if missing:
        problems.append({"code": "merge.missing_chunks", "chunks": missing})
    covered = sorted((wanted[c]["start"], wanted[c]["stop"]) for c in seen)
    pos = 0
    for a, b in covered:
        if a != pos:
            problems.append({"code": "merge.gap_or_overlap", "at": pos})
        pos = b
    if not missing and pos != manifest["n_items"]:
        problems.append({"code": "merge.incomplete_range", "covered_to": pos})
    # stray files (duplicates, other manifests, unknown ids, unreadable copies) are excluded and reported; the merge is
    # still complete when every manifest chunk was found exactly once and the ranges tile the job
    hard = [p for p in problems if p["code"] in ("merge.missing_chunks", "merge.range_mismatch", "merge.gap_or_overlap",
                                                 "merge.incomplete_range", "merge.non_finite")]
    merged = None
    if results and not hard:
        try:
            merged = combine([r for _, r in sorted(results, key=lambda t: t[0])])
        except (TypeError, ValueError) as exc:  # results the combine function cannot add: no merged value
            problems.append({"code": "merge.combine_failed", "message": str(exc)})
            hard.append(problems[-1])
        else:
            bad = _nonfinite(merged, "merged")
            if bad:
                problems.append({"code": "merge.non_finite", "message": f"{bad} is not finite after combining"})
                hard.append(problems[-1])
                merged = None
    return {"status": "complete" if not hard else "incomplete", "merged": merged, "problems": problems,
            "chunks_merged": len(seen), "chunks_expected": len(wanted)}


def _reduce(results):
    out = results[0]
    for r in results[1:]:
        out = _sum(out, r)
    return out
