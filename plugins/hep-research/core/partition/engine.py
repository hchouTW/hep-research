"""Manifest-based partition engine: manifest, write-once chunk outputs, bounded resubmission, complete merge.

Rules this enforces:
- The work is split once into a manifest of chunks (id, item range, seed); the manifest hash ties every output to it.
- A chunk's output is written atomically and only once; resubmission skips finished chunks, so nothing is counted twice.
- Retries happen only when the run configuration sets "max_attempts"; with no configuration a failed chunk is not
  retried. A chunk whose last two attempts failed with the same error is stopped even if attempts remain.
- State (attempts, errors) is kept on disk after any failure, so a later resubmission continues where it stopped.
- Merging checks that every manifest chunk is present exactly once, belongs to this manifest, and that the item
  ranges tile [0, n) with no gap or overlap; a missing chunk makes the merge 'incomplete', never a silent partial sum.

API: make_manifest(job_id, n_items, chunk_size, seed) -> dict; run(manifest, state_dir, worker, config=None) -> dict
(synchronous, in-process); status(manifest, state_dir); reset(state_dir, chunk_ids, reason); merge(manifest,
state_dir, combine=None). Standard library only.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


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
    return a + b


def merge(manifest: dict, state_dir, combine=None) -> dict:
    """Merge chunk outputs; combine(list_of_results) defaults to key-by-key summation."""
    combine = combine or (lambda rs: _reduce(rs))
    problems, seen, results = [], {}, []
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
    hard = [p for p in problems if p["code"] in ("merge.missing_chunks", "merge.range_mismatch", "merge.gap_or_overlap", "merge.incomplete_range")]
    merged = combine([r for _, r in sorted(results, key=lambda t: t[0])]) if results and not hard else None
    return {"status": "complete" if not hard else "incomplete", "merged": merged, "problems": problems,
            "chunks_merged": len(seen), "chunks_expected": len(wanted)}


def _reduce(results):
    out = results[0]
    for r in results[1:]:
        out = _sum(out, r)
    return out
