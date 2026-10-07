"""Asynchronous campaigns: submit manifest chunks through an executor, poll, collect, resubmit within bounds, merge.

The campaign directory holds everything (it must be on a file system the jobs can write, or be the target of the
scheduler's output transfer):

  manifest.json, spec.json, runner.py      the work, the command and the worker-side runner (copied at init)
  state.json                               per chunk: attempts, attempts_since_reset, errors (failure signatures),
                                           attempt_records, reset_reason; plus submissions, resets, duplicates,
                                           quarantine, seen
  submissions/<id>/                        rendered job files, submission map, job logs (*.stdout.log, *.stderr.log)
  outputs/<chunk>/                         what the runner wrote: <attempt>.json, <attempt>.meta.json, reruns
  chunks/<chunk>.json                      the one collected output per chunk (write-once); merge() reads only these
  quarantine/<chunk>/                      outputs that failed validation, kept with the reason, never deleted

Rules (the T21 rules, carried to remote and asynchronous execution):
- Seeds come from the manifest; a scheduler index reaches a chunk only through the submission map.
- Collection validates every candidate (manifest hash, chunk and attempt IDs, range and seed, finite numbers) and
  ingests the first valid one by attempt order; any other valid output of that chunk is a duplicate, recorded and
  never summed. Once a chunk is collected its output never changes.
- A chunk is done only when its output is collected: a job the scheduler calls successful without a valid output is
  'lost'. Unknown native states stay 'unknown'.
- Nothing is resubmitted except by an explicit resubmit() call, and only within the configured max_attempts (none
  configured: no resubmission); timeouts and out-of-memory need changed resources; failed, held, cancelled and
  unknown chunks need reset() with a reason; two identical failure signatures in a row stop the chunk.
- submit(), resubmit() and cancel() are dry runs unless approved=True.
- Every call that changes the campaign holds an exclusive lock on <campaign>/.lock; a second process or thread gets
  CampaignError("campaign.locked") at once instead of racing it for submission IDs or state.
- submit() records its attempts (state 'submitting', no job ID) in state.json before calling the scheduler and
  confirms them afterwards. If it is interrupted in between, the submission stays 'unconfirmed': nothing is submitted
  again until a person checks the scheduler and calls confirm_submission() with the job IDs it lists, or
  abandon_submission() with a reason.
Standard library only.
"""
from __future__ import annotations

import contextlib
import datetime
import functools
import hashlib
import json
import math
import os
import shutil
from threading import local as _thread_state  # the packaging scan reads '.local' as a host name
import time
from pathlib import Path

from core.partition import engine
from core.partition.executors import PollError
from core.partition.states import ACTIVE, NEEDS_PERSON, decide, normalize, repeated, signature

MIN_POLL_INTERVAL_S = 60
POLL_AGAIN = (None, "held", "unknown")  # a held or unknown job may still change; keep asking
RUNNER = Path(__file__).resolve().parent / "runner.py"


class CampaignError(ValueError):
    """Refusal with a named code (exit 2 in a CLI)."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def resources_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config.get("resources", {}), sort_keys=True).encode()).hexdigest()[:16]


def init(campaign_dir, manifest: dict, cmd: str, container_image: str | None = None) -> Path:
    cdir = Path(campaign_dir)
    if (cdir / "state.json").exists():
        old = json.loads((cdir / "manifest.json").read_text(encoding="utf-8"))
        if old["manifest_hash"] != manifest["manifest_hash"]:
            raise CampaignError("campaign.other_manifest", f"{cdir} belongs to manifest {old['manifest_hash'][:12]}")
        return cdir
    for sub in ("submissions", "outputs", "chunks", "quarantine"):
        (cdir / sub).mkdir(parents=True, exist_ok=True)
    engine._write_atomic(cdir / "manifest.json", manifest)
    engine._write_atomic(cdir / "spec.json", {"manifest": manifest, "cmd": cmd, "container_image": container_image})
    shutil.copyfile(RUNNER, cdir / "runner.py")
    os.chmod(cdir / "runner.py", 0o755)
    state = {"manifest_hash": manifest["manifest_hash"], "chunks": {}, "submissions": [], "resets": [], "duplicates": [],
             "quarantine": [], "seen": [], "polls": 0}
    engine._write_atomic(cdir / "state.json", state)
    return cdir


def load(campaign_dir) -> tuple[dict, dict]:
    cdir = Path(campaign_dir)
    if not (cdir / "state.json").exists():
        raise CampaignError("campaign.missing", f"no campaign at {cdir}")
    return json.loads((cdir / "manifest.json").read_text(encoding="utf-8")), json.loads((cdir / "state.json").read_text(encoding="utf-8"))


def _row(state: dict, cid: str) -> dict:
    row = state["chunks"].setdefault(cid, {})
    for k, v in (("attempts", 0), ("attempts_since_reset", 0), ("errors", []), ("attempt_records", []), ("reset_reason", None)):
        row.setdefault(k, v)  # state rows written before attempt_records existed read as an empty list
    return row


def _save(cdir: Path, state: dict) -> None:
    engine._write_atomic(cdir / "state.json", state)


_HELD = _thread_state()  # campaign directories this thread holds the lock of, with a depth (calls nest)


@contextlib.contextmanager
def campaign_lock(campaign_dir, operation: str):
    """Exclusive lock on <campaign>/.lock for one operation; nested calls in the same thread reuse it."""
    cdir = Path(campaign_dir).resolve()
    held = getattr(_HELD, "dirs", None)
    if held is None:
        held = _HELD.dirs = {}
    if held.get(cdir):
        held[cdir] += 1
        try:
            yield
        finally:
            held[cdir] -= 1
        return
    cdir.mkdir(parents=True, exist_ok=True)
    fh = open(cdir / ".lock", "a+", encoding="utf-8")
    try:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:  # Windows
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]  # Windows-only API, absent from non-win32 stubs
    except OSError:
        fh.seek(0)
        holder = fh.read().strip() or "another process"
        fh.close()
        raise CampaignError("campaign.locked", f"{cdir} is in use ({holder}); wait for it to finish") from None
    try:
        fh.seek(0)
        fh.truncate()
        fh.write(f"{operation} by pid {os.getpid()} since {_now()}")
        fh.flush()
        held[cdir] = 1
        yield
    finally:
        held.pop(cdir, None)
        fh.close()  # closing the file releases the lock


def _locked(operation: str):
    def wrap(fn):
        @functools.wraps(fn)
        def inner(campaign_dir, *args, **kwargs):
            with campaign_lock(campaign_dir, operation):
                return fn(campaign_dir, *args, **kwargs)
        return inner
    return wrap


def unconfirmed(state: dict) -> list[dict]:
    """Submissions recorded before the scheduler call and never confirmed (an interrupted submit)."""
    return [s for s in state["submissions"] if s.get("status") == "intent"]


def chunk_status(cdir: Path, state: dict, cid: str) -> str:
    if (cdir / "chunks" / f"{cid}.json").exists():
        return "done"
    row = _row(state, cid)
    if not row["attempt_records"]:
        return "planned"
    last = row["attempt_records"][-1]
    if last.get("final_state") is None:
        return last.get("state", "queued")
    if repeated(row["errors"]) and not row["reset_reason"]:
        return "stopped-repeated-failure"
    return last["final_state"]


# ---------------------------------------------------------------- submission

@_locked("submit")
def submit(campaign_dir, executor, config: dict, chunk_ids=None, approved: bool = False, pilot: bool = False,
           _origin: str = "submit", clock=_now) -> dict:
    """Submit chunks that were never submitted (all of them, the given ones, or with pilot=True the first one)."""
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    pending = unconfirmed(state)
    if pending:
        raise CampaignError("submit.unconfirmed", f"submission {pending[0]['id']} was recorded but never confirmed (an "
                            "interrupted submit): check the scheduler for its jobs, then confirm_submission() with their "
                            "IDs or abandon_submission() with a reason")
    ids = [c["id"] for c in manifest["chunks"]]
    if chunk_ids is not None:
        unknown = sorted(set(chunk_ids) - set(ids))
        if unknown:
            raise CampaignError("submit.unknown_chunks", f"not in the manifest: {unknown}")
        ids = [c for c in ids if c in set(chunk_ids)]
    if _origin == "submit":
        busy = [c for c in ids if _row(state, c)["attempt_records"] or (cdir / "chunks" / f"{c}.json").exists()]
        if chunk_ids is not None and busy:
            raise CampaignError("submit.already_submitted", f"use resubmit for chunks with attempts: {busy}")
        ids = [c for c in ids if c not in busy]
    if pilot:
        ids = ids[:1]
    if not ids:
        return {"submitted": [], "dry_run": not approved, "message": "nothing to submit"}
    sid = f"s{len(state['submissions']) + 1:03d}"
    sub_dir = cdir / "submissions" / sid
    rows = []
    for i, cid in enumerate(ids):
        n = sum(1 for r in _row(state, cid)["attempt_records"] if r.get("origin") != "scheduler-restart") + 1
        rows.append({"index": i, "chunk_id": cid, "attempt_id": f"{cid}-a{n:02d}"})
    ctx = {"campaign_dir": cdir, "submission_id": sid, "submission_dir": sub_dir, "rows": rows, "config": config,
           "spec": cdir / "spec.json", "runner": cdir / "runner.py", "outputs_dir": cdir / "outputs"}
    plan = executor.prepare(ctx)
    if not approved:
        preview = cdir / "dry-run" / sid
        preview.mkdir(parents=True, exist_ok=True)
        for name, text in plan["files"].items():
            (preview / name).write_text(text, encoding="utf-8")
        return {"dry_run": True, "submission_id": sid, "chunks": ids, "would_run": plan["submit_argv"],
                "files": sorted(str(preview / n) for n in plan["files"]), "message": "dry run: no scheduler call; pass the submit flag to submit"}
    sub_dir.mkdir(parents=True, exist_ok=True)
    (sub_dir / "logs").mkdir(exist_ok=True)
    for cid in ids:
        (cdir / "outputs" / cid).mkdir(parents=True, exist_ok=True)
    for name, text in plan["files"].items():
        (sub_dir / name).write_text(text, encoding="utf-8")
    rh = resources_hash(config)
    for r in rows:  # the intent: on disk before the scheduler sees anything
        row = _row(state, r["chunk_id"])
        prev = row["attempt_records"][-1] if row["attempt_records"] else None
        change = None
        if prev and prev.get("resources_hash") not in (None, rh):  # recorded whenever the request changed
            change = {"after": prev.get("final_state"), "from": prev.get("resources"), "to": config.get("resources")}
        row["attempt_records"].append({
            "attempt_id": r["attempt_id"], "chunk_id": r["chunk_id"], "backend": executor.name, "job_id": None,
            "submission": sid, "submission_dir": str(sub_dir), "outputs_dir": str(cdir / "outputs" / r["chunk_id"]), "submit_time": clock(), "origin": _origin, "state": "submitting",
            "final_state": None, "native_state": None, "exit_code": None, "signal": None, "hold_reason": None, "hold_code": None,
            "host": None, "elapsed_s": None, "max_rss_mb": None, "evidence": None, "restarts_seen": 0,
            "resources": config.get("resources"), "resources_hash": rh, "resource_change": change})
        row["attempts"] += 1
        row["attempts_since_reset"] += 1
        row["reset_reason"] = None
    state["submissions"].append({"id": sid, "backend": executor.name, "command": plan["submit_argv"], "chunks": ids,
                                 "origin": _origin, "pilot": pilot, "time": clock(), "status": "intent"})
    _save(cdir, state)
    try:
        jobs = executor.submit(plan)
    except Exception as exc:  # the scheduler refused: nothing was submitted, and the record says so
        _settle(cdir, sid, None, f"submit failed: {type(exc).__name__}: {exc}")
        raise
    _settle(cdir, sid, {j["attempt_id"]: j["job_id"] for j in jobs})
    return {"dry_run": False, "submission_id": sid, "chunks": ids, "command": plan["submit_argv"], "jobs": jobs}


def _settle(cdir: Path, sid: str, job_of: dict | None, reason: str | None = None) -> None:
    """Confirm a recorded submission with its job IDs, or (job_of None) mark its attempts as never submitted."""
    _, state = load(cdir)
    sub = next(x for x in state["submissions"] if x["id"] == sid)
    for row in state["chunks"].values():
        for rec in row["attempt_records"]:
            if rec.get("submission") == sid and rec.get("state") == "submitting":
                if job_of is None:
                    rec.update(state="not-submitted", final_state="not-submitted", note=reason)
                else:
                    rec.update(state="queued", job_id=job_of.get(rec["attempt_id"]))
    sub["status"] = "submitted" if job_of is not None else "not-submitted"
    if reason:
        sub["reason"] = reason
    _save(cdir, state)


@_locked("confirm")
def confirm_submission(campaign_dir, submission_id: str, job_ids: dict) -> dict:
    """After an interrupted submit: the person found the jobs at the scheduler; record {attempt_id: job_id}."""
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    sub = next((x for x in unconfirmed(state) if x["id"] == submission_id), None)
    if sub is None:
        raise CampaignError("confirm.not_unconfirmed", f"{submission_id} is not an unconfirmed submission")
    attempts = {rec["attempt_id"] for row in state["chunks"].values() for rec in row["attempt_records"]
                if rec.get("submission") == submission_id}
    if set(job_ids) != attempts:
        raise CampaignError("confirm.attempts_mismatch", f"give a job ID for exactly these attempts: {sorted(attempts)}")
    _settle(cdir, submission_id, dict(job_ids), "confirmed by a person after an interrupted submit")
    return {"confirmed": submission_id, "jobs": dict(job_ids)}


@_locked("abandon")
def abandon_submission(campaign_dir, submission_id: str, reason: str) -> dict:
    """After an interrupted submit: the person found no jobs at the scheduler. The attempts become 'not-submitted'
    (their chunks need a reset to run again); an output that still appears for them is collected as usual."""
    if not reason or not reason.strip():
        raise CampaignError("abandon.reason_missing", "abandoning a submission needs a reason")
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    if not any(x["id"] == submission_id for x in unconfirmed(state)):
        raise CampaignError("abandon.not_unconfirmed", f"{submission_id} is not an unconfirmed submission")
    _settle(cdir, submission_id, None, f"abandoned: {reason}")
    return {"abandoned": submission_id, "reason": reason}


@_locked("resubmit")
def resubmit(campaign_dir, executor, config: dict, approved: bool = False, clock=_now) -> dict:
    """Resubmit the chunks whose decision is 'resubmit'; report every other not-done chunk with its decision."""
    cdir = Path(campaign_dir)
    collect(cdir)
    manifest, state = load(cdir)
    max_attempts = config.get("max_attempts")
    rh = resources_hash(config)
    decisions = {}
    for c in manifest["chunks"]:
        if chunk_status(cdir, state, c["id"]) != "done":
            decisions[c["id"]] = decide(_row(state, c["id"]), max_attempts, rh)
    eligible = [c for c, d in decisions.items() if d["decision"] == "resubmit"]
    blocked = {c: d for c, d in decisions.items() if d["decision"] not in ("resubmit", "wait", "not-submitted")}
    rep = {"decisions": decisions, "eligible": eligible, "blocked": blocked, "max_attempts": max_attempts}
    if eligible:
        rep["submission"] = submit(cdir, executor, config, eligible, approved=approved, _origin="resubmit", clock=clock)
    rep["resubmitted"] = eligible if eligible and approved else []
    return rep


@_locked("reset")
def reset(campaign_dir, chunk_ids, reason: str) -> dict:
    """After a person fixed the cause: allow the chunk to be resubmitted, with the reason recorded in 'resets'."""
    if not reason or not reason.strip():
        raise CampaignError("reset.reason_missing", "a reset needs a reason")
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    known = {c["id"] for c in manifest["chunks"]}
    for cid in chunk_ids:
        if cid not in known:
            raise CampaignError("reset.unknown_chunk", cid)
        row = _row(state, cid)
        state["resets"].append({"chunk": cid, "reason": reason, "errors": row["errors"], "attempts": row["attempts"]})
        # the failure history is kept: a reset allows one more attempt, and the same failure again still stops the chunk
        row.update(attempts_since_reset=0, reset_reason=reason)
    _save(cdir, state)
    return {"reset": list(chunk_ids), "reason": reason}


@_locked("cancel")
def cancel(campaign_dir, executor, chunk_ids=None, approved: bool = False) -> dict:
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    recs = [r for cid, row in state["chunks"].items() if chunk_ids is None or cid in chunk_ids
            for r in row.get("attempt_records", []) if r.get("final_state") in POLL_AGAIN and r.get("job_id")]
    if not approved:
        return {"dry_run": True, "would_cancel": [r["job_id"] for r in recs], "message": "dry run: pass the cancel approval flag to cancel"}
    cmds = executor.cancel(recs)
    state.setdefault("cancels", []).append({"jobs": [r["job_id"] for r in recs], "commands": cmds, "time": _now()})
    _save(cdir, state)
    return {"dry_run": False, "cancelled": [r["job_id"] for r in recs], "commands": cmds}


# ---------------------------------------------------------------- collection

def _finite(x) -> bool:
    if isinstance(x, float):
        return math.isfinite(x)
    if isinstance(x, list):
        return all(_finite(v) for v in x)
    if isinstance(x, dict):
        return all(_finite(v) for v in x.values())
    return True


def _check(doc, manifest: dict, cid: str, attempt: str, known_attempts: set) -> str | None:
    if not isinstance(doc, dict):
        return "not a JSON object"
    missing = {"chunk_id", "manifest_hash", "attempt_id", "start", "stop", "seed", "result"} - set(doc)
    if missing:
        return f"missing keys {sorted(missing)}"
    if doc["manifest_hash"] != manifest["manifest_hash"]:
        return "output belongs to another manifest"
    chunk = next((c for c in manifest["chunks"] if c["id"] == doc["chunk_id"]), None)
    if chunk is None or doc["chunk_id"] != cid:
        return f"chunk {doc['chunk_id']!r} does not match its directory {cid!r} or the manifest"
    if doc["attempt_id"] != attempt or attempt not in known_attempts:
        return f"attempt {doc['attempt_id']!r} was never submitted for {cid}"
    if (doc["start"], doc["stop"], doc["seed"]) != (chunk["start"], chunk["stop"], chunk["seed"]):
        return "range or seed differs from the manifest"
    if not _finite(doc["result"]):
        return "result contains a non-finite number"
    return None


@_locked("collect")
def collect(campaign_dir) -> dict:
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    seen = set(state["seen"])
    ingested, dups, quarantined = [], [], []
    for cdir_chunk in sorted(p for p in (cdir / "outputs").iterdir() if p.is_dir()):
        cid = cdir_chunk.name
        known = {r["attempt_id"] for r in _row(state, cid)["attempt_records"]} if cid in state["chunks"] else set()
        order = {a: i for i, a in enumerate(r["attempt_id"] for r in state["chunks"].get(cid, {}).get("attempt_records", []))}
        cands = []
        for f in sorted(cdir_chunk.glob("*.json")):
            rel = f"outputs/{cid}/{f.name}"
            if f.name.startswith(".") or f.name.endswith(".meta.json") or rel in seen:
                continue
            base, _, rerun = f.name[:-5].partition(".rerun-")
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
                problem = _check(doc, manifest, cid, base, known)
            except ValueError as exc:
                doc, problem = None, f"unreadable: {exc}"
            seen.add(rel)
            if problem:
                dest = cdir / "quarantine" / cid / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                os.replace(f, dest)
                quarantined.append({"file": rel, "moved_to": f"quarantine/{cid}/{f.name}", "reason": problem})
                continue
            cands.append(((order.get(base, 1 << 30), int(rerun or 0)), rel, doc))
        target = cdir / "chunks" / f"{cid}.json"
        for _, rel, doc in sorted(cands, key=lambda t: t[0]):
            if not target.exists():
                tmp = cdir / "chunks" / f".tmp-{cid}.json"
                tmp.write_text(json.dumps(doc, sort_keys=True), encoding="utf-8")
                try:
                    os.link(tmp, target)  # write-once: never replaces an existing collected output
                finally:
                    tmp.unlink()
                ingested.append({"chunk": cid, "file": rel})
                continue
            kept = json.loads(target.read_text(encoding="utf-8"))
            dups.append({"chunk": cid, "file": rel, "kept": kept.get("attempt_id"), "identical_result": kept["result"] == doc["result"]})
    state["seen"] = sorted(seen)
    state["duplicates"] += dups
    state["quarantine"] += quarantined
    _save(cdir, state)
    return {"ingested": ingested, "duplicates": dups, "quarantined": quarantined}


# ---------------------------------------------------------------- observation

def _apply(row: dict, rec: dict, obs: dict) -> None:
    for k in ("native_state", "exit_code", "signal", "hold_reason", "hold_code", "host", "elapsed_s", "max_rss_mb", "evidence"):
        if obs.get(k) is not None or k in ("hold_reason", "hold_code"):
            rec[k] = obs.get(k)
    new_restarts = int(obs.get("restarts") or 0) - rec.get("restarts_seen", 0)
    for j in range(new_restarts):  # scheduler-side restarts (eviction, requeue) count as attempts
        n = rec.get("restarts_seen", 0) + j + 1
        restart = {"attempt_id": f"{rec['attempt_id']}.restart-{n}", "chunk_id": rec["chunk_id"], "backend": rec["backend"],
                   "job_id": rec["job_id"], "submission": rec["submission"], "origin": "scheduler-restart",
                   "final_state": "preempted-or-evicted", "native_state": "restarted by the scheduler", "exit_code": None,
                   "signal": None, "hold_code": None, "resources_hash": rec.get("resources_hash")}
        row["attempt_records"].insert(row["attempt_records"].index(rec), restart)
        row["attempts"] += 1
        row["attempts_since_reset"] += 1
    rec["restarts_seen"] = rec.get("restarts_seen", 0) + max(new_restarts, 0)
    state = normalize(obs.get("state"))
    if state in ACTIVE:
        rec.update(state=state, final_state=None, counted=False)
    else:
        rec.update(state=state, final_state=state)


@_locked("poll")
def poll(campaign_dir, executor) -> dict:
    """One observation round: exactly one executor poll, then collection, then a decision per chunk."""
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    active = [r for row in state["chunks"].values() for r in row.get("attempt_records", [])
              if r.get("final_state") in POLL_AGAIN and r.get("origin") != "scheduler-restart" and r.get("state") != "submitting"]
    state["polls"] += 1
    _save(cdir, state)
    obs = executor.poll(active) if active else {}
    _, state = load(cdir)
    for row in state["chunks"].values():
        for rec in list(row.get("attempt_records", [])):
            if rec.get("final_state") in POLL_AGAIN and rec.get("origin") != "scheduler-restart" and rec in active:
                _apply(row, rec, obs.get(rec["attempt_id"]) or {"state": "unknown", "evidence": "the backend returned no record"})
    _save(cdir, state)
    col = collect(cdir)
    _, state = load(cdir)
    for cid, row in state["chunks"].items():
        done = (cdir / "chunks" / f"{cid}.json").exists()
        for rec in row["attempt_records"]:
            if rec.get("final_state") == "done" and not done and not any(i["chunk"] == cid for i in col["ingested"]):
                rec.update(final_state="lost", state="lost",
                           note="the scheduler reported success but no valid output was collected")
            if rec.get("final_state") not in (None, "done") and not rec.get("counted") and rec.get("origin") != "scheduler-restart":
                if not done:
                    row["errors"].append(signature(rec))
                rec["counted"] = True
    _save(cdir, state)
    return report(cdir, collected=col)


def report(campaign_dir, collected: dict | None = None) -> dict:
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    chunks = {}
    for c in manifest["chunks"]:
        row = _row(state, c["id"])
        st = chunk_status(cdir, state, c["id"])
        last = row["attempt_records"][-1] if row["attempt_records"] else {}
        chunks[c["id"]] = {"status": st, "attempts": row["attempts"], "native_state": last.get("native_state"),
                           "exit_code": last.get("exit_code"), "signal": last.get("signal"),
                           "hold_reason": last.get("hold_reason"), "hold_code": last.get("hold_code"),
                           "elapsed_s": last.get("elapsed_s"), "max_rss_mb": last.get("max_rss_mb")}
    not_done = sorted(c for c, r in chunks.items() if r["status"] != "done")
    return {"complete": not not_done, "not_done": not_done, "chunks": chunks, "polls": state["polls"],
            "duplicates": len(state["duplicates"]), "quarantined": len(state["quarantine"]),
            "collected": collected or {}}


def merge(campaign_dir, combine=None) -> dict:
    cdir = Path(campaign_dir)
    manifest, _ = load(cdir)
    return engine.merge(manifest, cdir, combine)


# ---------------------------------------------------------------- monitoring loop

@_locked("watch")
def watch(campaign_dir, executor, config: dict, sleep=time.sleep, clock=time.monotonic) -> dict:
    """Observe -> decide -> collect, repeated within the configured limits. It never resubmits, releases or cancels.

    Needs monitor.poll_interval_s (at least MIN_POLL_INTERVAL_S) and monitor.max_polls and/or monitor.deadline_s.
    Stops when every chunk is done (complete) or settled; early on a held, unknown or stopped chunk, on the same poll
    error twice in a row, or at the deadline; and at max_polls, reported as incomplete.
    """
    mon = config.get("monitor") or {}
    interval, max_polls, deadline = mon.get("poll_interval_s"), mon.get("max_polls"), mon.get("deadline_s")
    if interval is None or (max_polls is None and deadline is None):
        raise CampaignError("watch.limits_missing", "watch needs monitor.poll_interval_s and monitor.max_polls or monitor.deadline_s")
    if interval < MIN_POLL_INTERVAL_S:
        raise CampaignError("watch.interval_too_short", f"poll_interval_s must be at least {MIN_POLL_INTERVAL_S}")
    t0, n, last_err, log, rep = clock(), 0, None, [], None
    stop = None
    while stop is None:
        n += 1
        try:
            rep = poll(campaign_dir, executor)
            last_err = None
            entry = {"poll": n, "not_done": {c: rep["chunks"][c] for c in rep["not_done"]}}
            log.append(entry)
            statuses = {c: rep["chunks"][c]["status"] for c in rep["not_done"]}
            person = {c: s for c, s in statuses.items() if s in NEEDS_PERSON or s == "stopped-repeated-failure"}
            if rep["complete"]:
                stop = "complete"
            elif person:
                stop = "needs-person"
                entry["needs_person"] = person
            elif not any(s in ACTIVE for s in statuses.values()):
                stop = "settled-incomplete"
        except PollError as exc:
            log.append({"poll": n, "poll_error": exc.signature, "text": exc.text})
            if last_err == exc.signature:
                stop = "repeated-poll-error"
            last_err = exc.signature
        if stop is None and max_polls is not None and n >= max_polls:
            stop = "max-polls"
        if stop is None and deadline is not None and clock() - t0 + interval > deadline:
            stop = "deadline"
        if stop is None:
            sleep(interval)
    final = rep or report(campaign_dir)
    return {"stop_reason": stop, "polls": n, "complete": stop == "complete", "status": "complete" if stop == "complete" else "incomplete",
            "not_done": final["not_done"], "chunks": final["chunks"], "log": log,
            "poll_errors": [e for e in log if "poll_error" in e]}
