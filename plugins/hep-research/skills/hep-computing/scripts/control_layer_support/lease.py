"""Lease lock and restart recovery of the task record (reconstruction v12 stage C2; Control §5.5, CTRL-01, G5).
Standard library only. The control rules this layer serves did not pass the S0 spec review (obligation N1).

The lease serializes writers **in addition to** compare-and-set, never instead of it: every append still checks the
caller's expected head under the record's flock. A lease has an owner and an expiry:
  <task-log>.lease.json            {"owner", "pid", "host", "acquired", "expires" (epoch seconds), "lease_s"}
  <task-log>.lease-history.jsonl   append-only, canonical JSON lines, each with the SHA-256 of the previous line:
                                   acquire, renew, release, takeover (with the previous owner) and recover events
The fact kinds of Control §2 are closed and have no lock kind, so lease events are kept in this history file beside
the record, not in the record itself.
Rules: a live lease of another owner refuses every write except a human decision; under M2/M3 every write except a
human decision must hold a live lease; an expired lease is taken over only by `acquire` and only after restart
reconciliation -- while any attempt is admitted, running, cancelling or unknown, takeover is refused (reconcile, or
have a human abandon, first). Liveness is the expiry alone: a dead owner stops renewing, and its lease runs out.
Restart recovery of a torn last line: an append is acknowledged only after its single O_APPEND write and fsync, so a
last line without its newline was never acknowledged; `recover` moves that fragment to <task-log>.torn-<sha256> and
truncates it away, recording the event. Nothing else is ever removed.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path

from .derivation import canonical_bytes

UNSETTLED = ("admitted", "running", "cancelling", "unknown")


class LeaseRefused(Exception):
    """A live lease of another owner, a missing lease under M2/M3, or a takeover before reconciliation."""


def lease_path(task_log: Path) -> Path:
    return task_log.with_name(task_log.name + ".lease.json")


def history_path(task_log: Path) -> Path:
    return task_log.with_name(task_log.name + ".lease-history.jsonl")


def read_lease(task_log: Path) -> dict | None:
    path = lease_path(task_log)
    if not path.is_file():
        return None
    lease = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(lease, dict) or not isinstance(lease.get("owner"), str) or \
            not isinstance(lease.get("expires"), (int, float)):
        raise ValueError(f"malformed lease file {path}")
    return lease


def lease_state(task_log: Path, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    lease = read_lease(task_log)
    if lease is None:
        return {"held": False}
    return {"held": True, "owner": lease["owner"], "expires": lease["expires"], "live": lease["expires"] > now,
            "seconds_left": round(lease["expires"] - now, 3), "pid": lease.get("pid"), "host": lease.get("host")}


def read_history(task_log: Path) -> list[dict]:
    path = history_path(task_log)
    if not path.is_file():
        return []
    events, prev = [], None
    for index, raw in enumerate(path.read_bytes().split(b"\n")[:-1]):
        event = json.loads(raw)
        if canonical_bytes(event) != raw or event.get("prev") != prev or event.get("n") != index:
            raise ValueError(f"lease history line {index} does not verify")
        prev = hashlib.sha256(raw).hexdigest()
        events.append(event)
    return events


def _record_event(task_log: Path, event: dict):
    events = read_history(task_log)
    prev = hashlib.sha256(canonical_bytes(events[-1])).hexdigest() if events else None
    raw = canonical_bytes({**event, "n": len(events), "prev": prev,
                           "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    handle = os.open(history_path(task_log), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(handle, raw + b"\n")
        os.fsync(handle)
    finally:
        os.close(handle)


def _write_lease(task_log: Path, lease: dict):
    path = lease_path(task_log)
    scratch = path.with_name(path.name + f".{os.getpid()}.part")
    scratch.write_text(json.dumps(lease, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(scratch, path)


def check_write(task_log: Path, owner: str | None, mode: str, human: bool, now: float | None = None):
    """Called under the record's flock before an append. Raises LeaseRefused."""
    if human:
        return
    state = lease_state(task_log, now)
    if state["held"] and state["live"] and state["owner"] != owner:
        raise LeaseRefused(f"the task record is leased to {state['owner']!r} for {state['seconds_left']} s more")
    if mode in ("M2", "M3") and not (state["held"] and state["live"] and state["owner"] == owner):
        raise LeaseRefused(f"under {mode} every write holds a live lease: run `lock acquire --owner NAME` and pass "
                           f"--owner NAME")


def acquire(task_log: Path, owner: str, lease_s: float, unsettled: list[str], now: float | None = None) -> dict:
    """Acquire, renew (same owner) or take over (expired lease of another owner, only after reconciliation)."""
    if not (isinstance(lease_s, (int, float)) and 0 < lease_s <= 86400):
        raise ValueError("--lease-s must be in (0, 86400]")
    now = time.time() if now is None else now
    state = lease_state(task_log, now)
    event = "acquire"
    if state["held"] and state["owner"] != owner:
        if state["live"]:
            raise LeaseRefused(f"a live lease of {state['owner']!r} ({state['seconds_left']} s left): not taken over")
        if unsettled:
            raise LeaseRefused(f"reconcile first: attempts {unsettled} are admitted, running, cancelling or unknown; "
                               f"take their receipts (or record them lost), reconcile them or have a human abandon "
                               f"them, then take over the expired lease")
        event = "takeover"
    elif state["held"]:
        event = "renew" if state["live"] else "acquire"
    lease = {"owner": owner, "pid": os.getpid(), "host": socket.gethostname(), "acquired": now,
             "expires": now + lease_s, "lease_s": lease_s}
    _write_lease(task_log, lease)
    _record_event(task_log, {"event": event, "owner": owner, "previous_owner": state.get("owner"),
                             "expires": lease["expires"]})
    return {"event": event, **lease_state(task_log, now)}


def release(task_log: Path, owner: str) -> dict:
    state = lease_state(task_log)
    if not state["held"]:
        return {"event": "none", "held": False}
    if state["owner"] != owner:
        raise LeaseRefused(f"the lease belongs to {state['owner']!r}")
    lease_path(task_log).unlink()
    _record_event(task_log, {"event": "release", "owner": owner, "previous_owner": owner, "expires": None})
    return {"event": "release", "held": False}


def recover_torn_tail(task_log: Path) -> dict:
    """Remove a torn (never acknowledged) last line; keep it in a side file and record the event."""
    content = task_log.read_bytes()
    if not content or content.endswith(b"\n"):
        return {"recovered": False}
    cut = content.rfind(b"\n") + 1
    fragment = content[cut:]
    digest = hashlib.sha256(fragment).hexdigest()
    task_log.with_name(f"{task_log.name}.torn-{digest}").write_bytes(fragment)
    with open(task_log, "r+b") as handle:
        handle.truncate(cut)
        handle.flush()
        os.fsync(handle.fileno())
    _record_event(task_log, {"event": "recover", "owner": None, "previous_owner": None, "expires": None,
                             "torn_bytes": len(fragment), "torn_sha256": digest})
    return {"recovered": True, "torn_bytes": len(fragment), "torn_sha256": digest}
