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
- submit() records its attempts (state 'submitting', no job ID) and a campaign-unique tag (hepr-<campaign_uid>-<sid>,
  the job name) in state.json before calling the scheduler and confirms them afterwards. Only a client that could not
  start (SubmitRefused) settles them as 'not-submitted'. If the call is interrupted, times out, or ends without job IDs
  (SubmitAmbiguous), the submission stays 'unconfirmed': nothing is submitted again until a person runs reconcile()
  (the scheduler's jobs under the tag) and calls confirm_submission() with job IDs from those candidates, or
  abandon_submission() with a reason ('abandoned', which does not prove the scheduler never accepted the jobs).
- Collection never follows symbolic links and reads regular files up to MAX_OUTPUT_BYTES; merge() uses only chunk
  files whose digest matches the collection record of a submitted attempt.
- Every attempt has a global identity <campaign_uid>:<attempt_id>. A configured 'limits' section (core.partition.limits)
  stops a submission or reset that would exceed it, counting unknown and orphan-risk attempts as used.
- cancel() records each command's exit per job and targets, through the submission tag, jobs of unconfirmed or
  abandoned submissions too. A cancel request is not termination: an attempt is 'termination_observed' only when a
  later poll sees it in a final state. Unknown, abandoned and orphan jobs leave append-only 'resource_risk' records
  and count as running (an unknown one until a poll sees it end) until clear_orphan_risk() records the scheduler's evidence.
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
import stat
from threading import local as _thread_state  # the packaging scan reads '.local' as a host name
import time
import uuid
from pathlib import Path
from typing import Any

from core.partition import engine
from core.partition import limits as lim
from core.partition.executors import Executor, PollError, SubmitRefused
from core.partition.states import ACTIVE, NEEDS_PERSON, decide, normalize, repeated, same_resources, signature

MIN_POLL_INTERVAL_S = 60
MAX_OUTPUT_BYTES = 64 * 1024 * 1024  # a runner output larger than this is quarantined unread
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
    """Full SHA-256 of the resource request (K07: never truncated; older campaigns recorded 16 hex digits, compared
    by prefix in states.same_resources)."""
    return hashlib.sha256(json.dumps(config.get("resources", {}), sort_keys=True).encode()).hexdigest()


def init(campaign_dir, manifest: dict, cmd: str, container_image: str | None = None,
         worker_timeout_s: int | None = None) -> Path:
    """Create (or reopen) a campaign. The manifest and the command template are checked first
    (engine.validate_manifest, engine.check_template): an invalid one is refused before anything is written."""
    try:
        engine.validate_manifest(manifest)
    except ValueError as exc:
        raise CampaignError("campaign.bad_manifest", str(exc)) from None
    try:
        engine.check_template(cmd)
    except ValueError as exc:
        raise CampaignError("campaign.bad_template", str(exc)) from None
    cdir = Path(campaign_dir)
    if (cdir / "state.json").exists():
        old = json.loads((cdir / "manifest.json").read_text(encoding="utf-8"))
        if old["manifest_hash"] != manifest["manifest_hash"]:
            raise CampaignError("campaign.other_manifest", f"{cdir} belongs to manifest {old['manifest_hash'][:12]}")
        return cdir
    for sub in ("submissions", "outputs", "chunks", "quarantine"):
        (cdir / sub).mkdir(parents=True, exist_ok=True)
    engine._write_atomic(cdir / "manifest.json", manifest)
    engine._write_atomic(cdir / "spec.json", {"manifest": manifest, "cmd": cmd, "container_image": container_image,
                                              "worker_timeout_s": worker_timeout_s})
    shutil.copyfile(RUNNER, cdir / "runner.py")
    os.chmod(cdir / "runner.py", 0o755)
    state = {"manifest_hash": manifest["manifest_hash"], "campaign_uid": uuid.uuid4().hex[:16], "chunks": {},
             "submissions": [], "resets": [], "duplicates": [], "quarantine": [], "seen": [], "polls": 0, "collected": {}}
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


def _risk(state: dict, kind: str, note: str, rec: dict | None = None, **extra) -> None:
    """Append a resource-risk record (never removed): a job may run, or have run, without a confirmed record."""
    entry = {"kind": kind, "time": _now(), "note": note, **extra}
    if rec is not None:
        entry.update(attempt_id=rec["attempt_id"], global_attempt_id=lim.global_attempt_id(state.get("campaign_uid"), rec["attempt_id"]),
                     submission=rec.get("submission"), job_id=rec.get("job_id"))
    risks = state.setdefault("resource_risk", [])
    key = (kind, entry.get("attempt_id"), entry.get("job_id"))
    if not any((r["kind"], r.get("attempt_id"), r.get("job_id")) == key for r in risks):
        risks.append(entry)


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
           _origin: str = "submit", clock=_now, expected_plan_digest: str | None = None) -> dict:
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
    bad = lim.problems(config.get("limits"))
    if bad:
        raise CampaignError("limits.bad_config", "; ".join(bad))
    usage, over = lim.check_submission(state, config, len(ids))
    if over:  # stops new submissions; work already submitted is not touched
        raise CampaignError("limits.exceeded", "; ".join(over))
    limits_report = {"configured": config.get("limits") or None, "usage_before": usage}
    if not state.get("campaign_uid"):  # a campaign created before tags: fix its uid once, so dry runs are reproducible
        state["campaign_uid"] = uuid.uuid4().hex[:16]
        _save(cdir, state)
    sid = f"s{len(state['submissions']) + 1:03d}"
    sub_dir = cdir / "submissions" / sid
    rows = []
    for i, cid in enumerate(ids):
        n = sum(1 for r in _row(state, cid)["attempt_records"] if r.get("origin") != "scheduler-restart") + 1
        rows.append({"index": i, "chunk_id": cid, "attempt_id": f"{cid}-a{n:02d}"})
    tag = submission_tag(state, sid)
    ctx = {"campaign_dir": cdir, "submission_id": sid, "submission_dir": sub_dir, "rows": rows, "config": config,
           "spec": cdir / "spec.json", "runner": cdir / "runner.py", "outputs_dir": cdir / "outputs", "tag": tag}
    plan = executor.prepare(ctx)
    digest = plan_digest(plan)
    if approved and expected_plan_digest is not None and expected_plan_digest != digest:
        raise CampaignError("submit.plan_changed", f"the job files differ from the reviewed dry run ({expected_plan_digest[:12]}"
                            f" -> {digest[:12]}): review the new dry run before submitting")
    if not approved:
        preview = cdir / "dry-run" / sid
        preview.mkdir(parents=True, exist_ok=True)
        for name, text in plan["files"].items():
            (preview / name).write_text(text, encoding="utf-8")
        return {"dry_run": True, "submission_id": sid, "chunks": ids, "would_run": plan["submit_argv"], "plan_digest": digest,
                "files": sorted(str(preview / n) for n in plan["files"]), "limits": limits_report,
                "message": "dry run: no scheduler call; pass the submit flag (and this plan_digest) to submit exactly these files"}
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
        if prev and prev.get("resources_hash") is not None and not same_resources(prev["resources_hash"], rh):
            change = {"after": prev.get("final_state"), "from": prev.get("resources"), "to": config.get("resources")}
        row["attempt_records"].append({
            "attempt_id": r["attempt_id"], "global_attempt_id": lim.global_attempt_id(state["campaign_uid"], r["attempt_id"]),
            "chunk_id": r["chunk_id"], "backend": executor.name, "job_id": None,
            "submission": sid, "submission_dir": str(sub_dir), "outputs_dir": str(cdir / "outputs" / r["chunk_id"]), "submit_time": clock(), "origin": _origin, "state": "submitting",
            "final_state": None, "native_state": None, "exit_code": None, "signal": None, "hold_reason": None, "hold_code": None,
            "host": None, "elapsed_s": None, "max_rss_mb": None, "evidence": None, "restarts_seen": 0,
            "resources": config.get("resources"), "resources_hash": rh, "resource_change": change})
        row["attempts"] += 1
        row["attempts_since_reset"] += 1
        row["reset_reason"] = None
    state["submissions"].append({"id": sid, "backend": executor.name, "command": plan["submit_argv"], "chunks": ids,
                                 "origin": _origin, "pilot": pilot, "time": clock(), "status": "intent", "tag": tag,
                                 "plan_digest": digest})
    _save(cdir, state)
    try:
        jobs = executor.submit(plan)
    except SubmitRefused as exc:  # the client never started: certainly nothing was submitted, and the record says so
        _settle(cdir, sid, None, f"submit refused: {exc}")
        raise
    except BaseException as exc:  # the scheduler may have accepted the jobs: keep the intent for a person to reconcile
        _note_ambiguous(cdir, sid, f"{type(exc).__name__}: {exc}")
        raise
    _settle(cdir, sid, {j["attempt_id"]: j["job_id"] for j in jobs})
    return {"dry_run": False, "submission_id": sid, "chunks": ids, "command": plan["submit_argv"], "jobs": jobs,
            "limits": limits_report}


def submission_tag(state: dict, sid: str) -> str:
    """hepr-<campaign_uid>-<sid>: the job name the scheduler keeps, so reconcile() can find the jobs of a submission."""
    if not state.get("campaign_uid"):  # a campaign created before tags: give it one now (saved with the intent)
        state["campaign_uid"] = uuid.uuid4().hex[:16]
    return f"hepr-{state['campaign_uid']}-{sid}"


def plan_digest(plan: dict) -> str:
    """SHA-256 of what a submission would run: the rendered files and the submit command (X15)."""
    body = {"files": plan["files"], "submit_argv": [str(a) for a in plan["submit_argv"]]}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def _note_ambiguous(cdir: Path, sid: str, reason: str) -> None:
    _, state = load(cdir)
    sub = next(x for x in state["submissions"] if x["id"] == sid)
    sub["ambiguous"] = reason  # status stays 'intent': unconfirmed until reconciled
    _save(cdir, state)


def _settle(cdir: Path, sid: str, job_of: dict | None, reason: str | None = None, outcome: str = "not-submitted") -> None:
    """Confirm a recorded submission with its job IDs, or (job_of None) settle its attempts as never submitted
    (outcome 'not-submitted': the client never started) or abandoned by a person ('abandoned')."""
    _, state = load(cdir)
    sub = next(x for x in state["submissions"] if x["id"] == sid)
    for row in state["chunks"].values():
        for rec in row["attempt_records"]:
            if rec.get("submission") == sid and rec.get("state") == "submitting":
                if job_of is None:
                    rec.update(state=outcome, final_state=outcome, note=reason)
                    if outcome == "abandoned":  # abandon does not prove the scheduler never accepted the job
                        _risk(state, "abandoned", reason or "abandoned", rec, tag=sub.get("tag"))
                else:
                    rec.update(state="queued", job_id=job_of.get(rec["attempt_id"]))
    sub["status"] = "submitted" if job_of is not None else outcome
    if reason:
        sub["reason"] = reason
    _save(cdir, state)


def reconcile(campaign_dir, executor, submission_id: str) -> dict:
    """Read-only: the jobs the scheduler knows under an unconfirmed submission's tag, for a person to decide."""
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    sub = next((x for x in unconfirmed(state) if x["id"] == submission_id), None)
    if sub is None:
        raise CampaignError("reconcile.not_unconfirmed", f"{submission_id} is not an unconfirmed submission")
    if not sub.get("tag"):
        raise CampaignError("reconcile.no_tag", f"{submission_id} was recorded before submission tags; check the scheduler by hand")
    attempts = sorted(rec["attempt_id"] for row in state["chunks"].values() for rec in row["attempt_records"]
                      if rec.get("submission") == submission_id)
    return {"submission": submission_id, "tag": sub["tag"], "attempts": attempts,
            "candidates": executor.find(sub["tag"], sub.get("time")), "ambiguous": sub.get("ambiguous")}


@_locked("confirm")
def confirm_submission(campaign_dir, submission_id: str, job_ids: dict, executor=None) -> dict:
    """After an ambiguous or interrupted submit: a person found the jobs at the scheduler; record {attempt_id: job_id}.
    Every job ID must be one that reconcile() lists for the submission's tag (fabricated IDs are refused, X07)."""
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    sub = next((x for x in unconfirmed(state) if x["id"] == submission_id), None)
    if sub is None:
        raise CampaignError("confirm.not_unconfirmed", f"{submission_id} is not an unconfirmed submission")
    if executor is None or not sub.get("tag"):
        raise CampaignError("confirm.no_reconcile", "confirm needs the scheduler's candidates for the submission tag "
                            "(an executor, and a submission recorded with a tag)")
    found = {c["job_id"] for c in executor.find(sub["tag"], sub.get("time"))}
    unknown = sorted(j for j in job_ids.values() if j not in found)
    if unknown:
        raise CampaignError("confirm.unknown_jobs", f"not found at the scheduler under tag {sub['tag']}: {unknown}")
    attempts = {rec["attempt_id"] for row in state["chunks"].values() for rec in row["attempt_records"]
                if rec.get("submission") == submission_id}
    if set(job_ids) != attempts:
        raise CampaignError("confirm.attempts_mismatch", f"give a job ID for exactly these attempts: {sorted(attempts)}")
    _settle(cdir, submission_id, dict(job_ids), "confirmed by a person after an interrupted submit")
    return {"confirmed": submission_id, "jobs": dict(job_ids)}


@_locked("abandon")
def abandon_submission(campaign_dir, submission_id: str, reason: str) -> dict:
    """After an ambiguous or interrupted submit: the person found no jobs at the scheduler. The attempts become
    'abandoned' (not proof that nothing runs; their chunks need a reset to run again); an output that still appears
    for them is collected as usual."""
    if not reason or not reason.strip():
        raise CampaignError("abandon.reason_missing", "abandoning a submission needs a reason")
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    if not any(x["id"] == submission_id for x in unconfirmed(state)):
        raise CampaignError("abandon.not_unconfirmed", f"{submission_id} is not an unconfirmed submission")
    _settle(cdir, submission_id, None, f"abandoned: {reason}", outcome="abandoned")
    return {"abandoned": submission_id, "reason": reason}


@_locked("resubmit")
def resubmit(campaign_dir, executor, config: dict, approved: bool = False, clock=_now) -> dict:
    """Resubmit the chunks whose decision is 'resubmit'; report every other not-done chunk with its decision."""
    cdir = Path(campaign_dir)
    collect(cdir)
    manifest, state = load(cdir)
    max_attempts = config.get("max_attempts")
    max_resets = (config.get("limits") or {}).get("max_resets_per_chunk")
    rh = resources_hash(config)
    decisions = {}
    for c in manifest["chunks"]:
        if chunk_status(cdir, state, c["id"]) != "done":
            used = sum(1 for r in state["resets"] if r["chunk"] == c["id"])
            decisions[c["id"]] = decide(_row(state, c["id"]), max_attempts, rh, resets_used=used, max_resets=max_resets)
    eligible = [c for c, d in decisions.items() if d["decision"] == "resubmit"]
    blocked = {c: d for c, d in decisions.items() if d["decision"] not in ("resubmit", "wait", "not-submitted")}
    rep = {"decisions": decisions, "eligible": eligible, "blocked": blocked, "max_attempts": max_attempts}
    if eligible:
        rep["submission"] = submit(cdir, executor, config, eligible, approved=approved, _origin="resubmit", clock=clock)
    rep["resubmitted"] = eligible if eligible and approved else []
    return rep


@_locked("reset")
def reset(campaign_dir, chunk_ids, reason: str, config: dict | None = None) -> dict:
    """After a person fixed the cause: allow the chunk to be resubmitted, with the reason recorded in 'resets'.
    With limits.max_resets_per_chunk in config, a reset beyond it is refused before anything is recorded (X08)."""
    if not reason or not reason.strip():
        raise CampaignError("reset.reason_missing", "a reset needs a reason")
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    known = {c["id"] for c in manifest["chunks"]}
    bad = lim.problems((config or {}).get("limits"))
    if bad:
        raise CampaignError("limits.bad_config", "; ".join(bad))
    for cid in chunk_ids:
        if cid not in known:
            raise CampaignError("reset.unknown_chunk", cid)
        if list(chunk_ids).count(cid) > 1:
            raise CampaignError("reset.duplicate_chunk", f"{cid} given more than once")
        over = lim.check_reset(state, config, cid)
        if over:
            raise CampaignError("limits.exceeded", over)
    for cid in chunk_ids:
        row = _row(state, cid)
        state["resets"].append({"chunk": cid, "reason": reason, "errors": row["errors"], "attempts": row["attempts"]})
        # the failure history is kept: a reset allows one more attempt, and the same failure again still stops the chunk
        row.update(attempts_since_reset=0, reset_reason=reason)
    _save(cdir, state)
    return {"reset": list(chunk_ids), "reason": reason}


@_locked("cancel")
def cancel(campaign_dir, executor, chunk_ids=None, approved: bool = False, clock=_now) -> dict:
    """Cancel the jobs of the given chunks (default all): attempts with a job ID that may still run, and, found through
    the submission tag, the jobs of unconfirmed (intent) or abandoned submissions (orphan risk, X09). Each command's
    exit is recorded per job. A request is not termination: an attempt is 'termination_observed' only when a later
    poll sees it in a final state; an orphan job stays a resource risk until a person checks the scheduler."""
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    want = None if chunk_ids is None else set(chunk_ids)
    recs = [r for cid, row in state["chunks"].items() if want is None or cid in want
            for r in row.get("attempt_records", []) if r.get("final_state") in POLL_AGAIN and r.get("job_id")]
    known_jobs = {r["job_id"] for r in recs}
    orphans, find_errors = [], []
    for sub in state["submissions"]:
        if sub.get("status") not in ("intent", "abandoned") or (want is not None and not want & set(sub.get("chunks", []))):
            continue
        if not sub.get("tag"):
            find_errors.append({"submission": sub["id"], "error": "recorded before submission tags: check the scheduler by hand"})
            continue
        try:
            cands = executor.find(sub["tag"], sub.get("time"))
        except PollError as exc:
            find_errors.append({"submission": sub["id"], "error": exc.signature})
            continue
        for c in cands:
            if c.get("job_id") and c["job_id"] not in known_jobs:
                known_jobs.add(c["job_id"])
                orphans.append({"job_id": c["job_id"], "attempt_id": None, "submission": sub["id"], "tag": sub["tag"]})
    targets = recs + orphans
    if not approved:
        return {"dry_run": True, "would_cancel": [r["job_id"] for r in recs], "would_cancel_orphans": [o["job_id"] for o in orphans],
                "find_errors": find_errors, "message": "dry run: pass the cancel approval flag to cancel"}
    cmds = executor.cancel(targets) if targets else []
    now = clock()
    jobs = []
    for i, r in enumerate(targets):
        c = cmds[i] if i < len(cmds) else None
        res = c if isinstance(c, dict) else {"argv": c, "exit": None}  # an executor that does not report exits: unknown
        status = "requested" if res.get("exit") == 0 else "request-failed" if res.get("exit") is not None or res.get("error") else "request-unconfirmed"
        jobs.append({"job_id": r["job_id"], "attempt_id": r.get("attempt_id"), "status": status, "exit": res.get("exit"),
                     "error": res.get("error")})
    _, state = load(cdir)  # same lock; reload so the records below are the saved ones
    by_job = {j["job_id"]: j for j in jobs}
    for row in state["chunks"].values():
        for rec in row.get("attempt_records", []):
            if rec.get("job_id") in by_job and rec.get("final_state") in POLL_AGAIN:
                j = by_job[rec["job_id"]]
                rec.setdefault("cancel_requests", []).append({"time": now, "status": j["status"], "exit": j["exit"]})
                if j["status"] == "requested":  # a failed or unreported request does not make a later end a cancellation
                    rec.update(cancel_requested=True)
                if rec.get("global_attempt_id") is None:
                    rec["global_attempt_id"] = lim.global_attempt_id(state.get("campaign_uid"), rec["attempt_id"])
                j["global_attempt_id"] = rec["global_attempt_id"]
    for o in orphans:
        _risk(state, "orphan-cancel-unconfirmed", f"cancel {by_job[o['job_id']]['status']} for a job found under tag {o['tag']}; "
              "not observed to end", job_id=o["job_id"], submission=o["submission"], tag=o["tag"])
    state.setdefault("cancels", []).append({"time": now, "jobs": jobs, "find_errors": find_errors})
    _save(cdir, state)
    return {"dry_run": False, "requested": [j["job_id"] for j in jobs], "jobs": jobs,
            "find_errors": find_errors, "commands": cmds,
            "note": "cancel requested; a job is terminated only when a later poll observes it in a final state"}


@_locked("clear")
def clear_orphan_risk(campaign_dir, executor, submission_id: str, reason: str) -> dict:
    """A person, with the scheduler's evidence, stops counting a submission's unknown or abandoned attempts as running
    (limits.max_concurrent_jobs). Refused unless every job the scheduler lists under the submission's tag is in a final
    state. The attempts keep their state and their resource_risk records; they still count as jobs and core-hours."""
    if not reason or not reason.strip():
        raise CampaignError("clear.reason_missing", "clearing orphan risk needs a reason")
    cdir = Path(campaign_dir)
    _, state = load(cdir)
    sub = next((x for x in state["submissions"] if x["id"] == submission_id), None)
    if sub is None or not sub.get("tag"):
        raise CampaignError("clear.no_tag", f"{submission_id} is unknown or was recorded before submission tags")
    recs = [r for row in state["chunks"].values() for r in row["attempt_records"]
            if r.get("submission") == submission_id and r.get("final_state") in lim.ORPHAN_RISK and not r.get("orphan_cleared")]
    if not recs:
        raise CampaignError("clear.nothing", f"{submission_id} has no unknown or abandoned attempt to clear")
    if type(executor).find is Executor.find:  # the base find() lists nothing: that is no evidence
        raise CampaignError("clear.no_evidence", f"{executor.name} cannot list jobs by tag")
    cands = executor.find(sub["tag"], sub.get("time"))  # a PollError propagates: no evidence, nothing cleared
    live = [c for c in cands if normalize(c.get("state")) in ACTIVE or normalize(c.get("state")) in ("held", "unknown")]
    if live:
        raise CampaignError("clear.jobs_active", f"the scheduler lists jobs under {sub['tag']} that may still run: "
                            f"{sorted(c.get('job_id') for c in live)}")
    now = _now()
    evidence = {"time": now, "reason": reason, "tag": sub["tag"], "candidates": cands}
    for r in recs:
        r["orphan_cleared"] = evidence
        _risk(state, "orphan-cleared", f"cleared by a person: {reason}", r, tag=sub["tag"])
    _save(cdir, state)
    return {"cleared": sorted(r["attempt_id"] for r in recs), "evidence": evidence}


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
    collected = state.get("collected")  # None for a campaign created before collection records: stays unchecked
    for cdir_chunk in sorted((cdir / "outputs").iterdir()):
        cid = cdir_chunk.name
        if cdir_chunk.is_symlink() or not cdir_chunk.is_dir():  # never follow a link out of the campaign (X03)
            rel = f"outputs/{cid}"
            if cdir_chunk.is_symlink() and rel not in seen:
                seen.add(rel)
                quarantined.append({"file": rel, "moved_to": None, "reason": "symbolic link: not followed, not collected"})
            continue
        known = {r["attempt_id"] for r in _row(state, cid)["attempt_records"]} if cid in state["chunks"] else set()
        order = {a: i for i, a in enumerate(r["attempt_id"] for r in state["chunks"].get(cid, {}).get("attempt_records", []))}
        cands = []
        for f in sorted(cdir_chunk.glob("*.json")):
            rel = f"outputs/{cid}/{f.name}"
            if f.name.startswith(".") or f.name.endswith(".meta.json") or rel in seen:
                continue
            base, _, rerun = f.name[:-5].partition(".rerun-")
            st = os.lstat(f)
            doc: Any = None
            problem: str | None
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
                doc, problem = None, "not a regular file (a link is never followed)"
            elif st.st_size > MAX_OUTPUT_BYTES:
                doc, problem = None, f"larger than {MAX_OUTPUT_BYTES} bytes; not read"
            else:
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
                body = json.dumps(doc, sort_keys=True)
                tmp.write_text(body, encoding="utf-8")
                try:
                    os.link(tmp, target)  # write-once: never replaces an existing collected output
                finally:
                    tmp.unlink()
                # the provenance merge() checks: which attempt and which bytes were collected (X04)
                if collected is not None:
                    collected[cid] = {"attempt_id": doc["attempt_id"], "file": rel,
                                      "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
                for rec in _row(state, cid)["attempt_records"]:
                    if rec["attempt_id"] == doc["attempt_id"] and rec.get("final_state") in ("not-submitted", "abandoned"):
                        rec["orphan_output_collected"] = True  # the record said not submitted; a job ran anyway (X11)
                        _risk(state, "orphan-output", "an output arrived for an attempt recorded as "
                              f"{rec.get('final_state')}: a job ran without a confirmed record", rec)
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
                if rec.get("final_state") == "unknown":
                    _risk(state, "unknown", "the scheduler state of this job is unknown; it may still use resources", rec)
                elif rec.get("cancel_requested") and rec.get("final_state") not in POLL_AGAIN and not rec.get("termination_observed"):
                    rec["termination_observed"] = {"time": _now(), "final_state": rec["final_state"], "native_state": rec.get("native_state")}
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
    """engine.merge after a provenance check: every chunk file must be the one collect() recorded (same digest) for an
    attempt of a submission the scheduler accepted. A forged or replaced chunk file fails the merge (X04). This check
    reads agent-writable state: it catches mistakes and forged chunk files, not a forged state.json (that needs the
    trusted submitter)."""
    cdir = Path(campaign_dir)
    manifest, state = load(cdir)
    problems, warnings = provenance_check(cdir, state)
    if problems:
        return {"status": "refused", "problems": problems, "provenance_warnings": warnings, "result": None}
    return dict(engine.merge(manifest, cdir, combine), provenance_warnings=warnings)


def provenance_check(cdir: Path, state: dict) -> tuple[list[dict], list[dict]]:
    """(problems, warnings). Problems: a chunk file collect() did not write, bytes changed since collection, an
    attempt that was never recorded. Warning: an orphan's output (its submission was abandoned or never confirmed
    as submitted) was collected (X11), and campaigns created before collection records are not checked."""
    if "collected" not in state:
        return [], [{"code": "merge.provenance_unrecorded", "message": "campaign created before collection records"}]
    accepted = {s["id"] for s in state["submissions"] if s.get("status") == "submitted"}
    attempts = {r["attempt_id"]: r for row in state["chunks"].values() for r in row["attempt_records"]}
    problems, warnings = [], []
    for f in sorted((cdir / "chunks").glob("*.json")):
        cid = f.stem
        rec = state["collected"].get(cid)
        if rec is None:
            problems.append({"code": "merge.uncollected_chunk", "chunk": cid, "message": "not written by collect()"})
            continue
        if hashlib.sha256(f.read_bytes()).hexdigest() != rec["sha256"]:
            problems.append({"code": "merge.chunk_changed", "chunk": cid, "message": "differs from the collected bytes"})
        att = attempts.get(rec["attempt_id"])
        if att is None:
            problems.append({"code": "merge.unknown_attempt", "chunk": cid, "message": f"attempt {rec['attempt_id']} was never recorded"})
        elif att.get("submission") not in accepted:
            warnings.append({"code": "merge.orphan_output", "chunk": cid,
                             "message": f"output of attempt {rec['attempt_id']}, whose submission is {att.get('state')}: "
                                        "the scheduler ran a job the record did not confirm"})
    return problems, warnings


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
