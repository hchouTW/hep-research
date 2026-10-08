"""Normalized job states, retry classes and failure signatures shared by every executor.

Each backend maps its native states onto NORMALIZED_STATES; a native state it does not know becomes 'unknown'
(fail closed). The retry class of a final state decides what an explicit resubmission may do with the chunk:

  retryable                 preempted-or-evicted, node-failure, lost (only after collection found no valid output)
  needs-resource-change     timeout, out-of-memory: resubmitted only when the resources differ from the failed attempt
  needs-reset               failed, held, cancelled, unknown, not-submitted: a person fixes the cause and resets with
                            a reason

Two states come from the campaign itself, never from a backend: 'submitting' (recorded before the scheduler call; seen
by a later call it means that submit was interrupted, and a person must confirm or abandon it) and 'not-submitted' (the
scheduler refused the submission, or a person abandoned it).

Nothing here resubmits anything; it only classifies. Standard library only.
"""
from __future__ import annotations

NORMALIZED_STATES = ("planned", "queued", "running", "done", "failed", "timeout", "out-of-memory", "preempted-or-evicted",
                     "node-failure", "held", "cancelled", "lost", "unknown", "submitting", "not-submitted")
ACTIVE = frozenset({"planned", "queued", "running"})
RETRY_CLASS = {
    "preempted-or-evicted": "retryable", "node-failure": "retryable", "lost": "retryable",
    "timeout": "needs-resource-change", "out-of-memory": "needs-resource-change",
    "failed": "needs-reset", "held": "needs-reset", "cancelled": "needs-reset", "unknown": "needs-reset",
    "not-submitted": "needs-reset",
}
# a chunk in one of these states stops a watch loop early: a person has to look at it
NEEDS_PERSON = frozenset({"held", "unknown", "submitting"})


def normalize(state: str | None) -> str:
    return state if state in NORMALIZED_STATES else "unknown"


def signature(rec: dict) -> str:
    """Failure signature for the 'two identical failures stop' rule: state, exit code, signal and hold code only.

    Host names, job IDs and times are left out, so a deterministic bug stops after two attempts on different nodes.
    """
    return "|".join([rec.get("final_state") or "unknown", f"exit={rec.get('exit_code')}", f"signal={rec.get('signal')}",
                     f"hold={rec.get('hold_code')}"])


def repeated(errors: list) -> bool:
    return len(errors) >= 2 and errors[-1] == errors[-2]


def same_resources(a: str | None, b: str | None) -> bool:
    """Equal resource-request hashes; a 16-hex hash recorded by an older campaign matches the full hash it begins."""
    if a is None or b is None:
        return a == b
    short, full = sorted((a, b), key=len)
    return short == full if len(short) != 16 else full.startswith(short)


def decide(chunk: dict, max_attempts: int | None, resources_hash: str | None) -> dict:
    """Decision for one chunk that has no collected output, from its last attempt record.

    Returns {"decision": ..., "reason": ...}. Decisions: 'wait' (still active), 'not-submitted', 'resubmit',
    'no-retries-configured', 'attempts-exhausted', 'needs-resource-change', 'needs-reset', 'stopped-repeated-failure'.
    """
    recs = chunk.get("attempt_records", [])
    if not recs:
        return {"decision": "not-submitted", "reason": "no attempt yet"}
    last = recs[-1]
    state = last.get("final_state")
    if state is None:
        return {"decision": "wait", "reason": f"last attempt {last['attempt_id']} is {last.get('state', 'queued')}"}
    if chunk.get("reset_reason"):
        return {"decision": "resubmit", "reason": f"reset: {chunk['reset_reason']}"}
    if repeated(chunk.get("errors", [])):
        return {"decision": "stopped-repeated-failure", "reason": f"last two attempts failed identically: {chunk['errors'][-1]}"}
    cls = RETRY_CLASS.get(state, "needs-reset")
    if cls == "needs-reset":
        return {"decision": "needs-reset", "reason": f"{state} is never retried automatically; fix the cause and reset with a reason"}
    if max_attempts is None:
        return {"decision": "no-retries-configured", "reason": "no max_attempts in the configuration"}
    if chunk.get("attempts_since_reset", 0) >= max_attempts:
        return {"decision": "attempts-exhausted", "reason": f"{chunk.get('attempts_since_reset', 0)} of {max_attempts} attempts used"}
    if cls == "needs-resource-change" and same_resources(resources_hash, last.get("resources_hash")):
        return {"decision": "needs-resource-change", "reason": f"{state}: change the resources in the configuration before resubmitting"}
    return {"decision": "resubmit", "reason": f"{state} is {cls}"}
