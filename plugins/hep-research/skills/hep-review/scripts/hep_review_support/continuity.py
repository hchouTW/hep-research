"""Head continuity, checkpoints, fork and migration segments (hep-review spec v9 sections 11.3-11.4).

The coordinator keeps the digests of the commits it wrote since its anchor outside the store (a private state file
whose path the caller chooses, never inside the store). The anchor is only a trusted checkpoint supplied by the user or
the delivery channel whose digest matches the chain, or a genesis commit written by this session. Without an anchor the
session is unverified for its whole life: appending is allowed from the head read at session start ("unanchored
start") but later appends never upgrade it. Broken stops appending; recovery is a fork segment. Digests are compared
from tool output, never retyped.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from hep_review_support.store import AppendResult, Store

HOW_TO_VERIFY = ("give the last checkpoint line of the previous session (hep-review checkpoint: context=... "
                 "segment=... seq=... digest=...) when starting the next session")


class ContinuityBroken(Exception):
    """Appending is stopped: the chain no longer matches the coordinator's anchor or written sequence."""


@dataclass
class CoordinatorState:
    session_id: str
    context_id: str
    start: str = "unanchored-start"  # anchored-checkpoint | anchored-genesis | pending-genesis | unanchored-start
    anchor: dict | None = None        # {segment_id, seq, commit_digest}
    written: list[str] = field(default_factory=list)
    expected_head: dict | None = None
    broken_reason: str | None = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=1, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> CoordinatorState:
        d = json.loads(text)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def checkpoint_line(store: Store, context_id: str) -> str:
    """The line the coordinator hands to the user after every report and before the session ends (spec 11.4)."""
    h = store.head(context_id)
    if h is None:
        raise KeyError(f"no context {context_id}")
    return (f"hep-review checkpoint: context={context_id} segment={h['segment_id']} seq={h['seq']} "
            f"digest={h['commit_digest']}")


CHECKPOINT = re.compile(r"context=(\S+)\s+segment=(\S+)\s+seq=(\d+)\s+digest=([0-9a-f]{64})")


def parse_checkpoint(text: str) -> dict:
    m = CHECKPOINT.search(text)
    if not m:
        raise ValueError("not a hep-review checkpoint line")
    return {"context_id": m.group(1), "segment_id": m.group(2), "seq": int(m.group(3)), "commit_digest": m.group(4)}


def start_session(store: Store, context_id: str, session_id: str, checkpoint: dict | None = None) -> CoordinatorState:
    head = store.head(context_id)
    st = CoordinatorState(session_id=session_id, context_id=context_id, expected_head=head)
    if checkpoint is not None:
        c = store.commit_at(context_id, checkpoint["segment_id"], checkpoint["seq"])
        anchor = {k: checkpoint[k] for k in ("segment_id", "seq", "commit_digest")}
        st.start, st.anchor = "anchored-checkpoint", anchor
        if c is None or c["digest"] != checkpoint["commit_digest"]:
            st.broken_reason = "the trusted checkpoint's digest is not on the chain at its position"
    elif head is None:
        st.start = "pending-genesis"
    return st


def append(store: Store, st: CoordinatorState, objects: list[dict], operation_id: str, **kw) -> AppendResult:
    """Append with the expected head from the coordinator's own sequence; record the written digest."""
    if head_continuity(store, st)["status"] == "broken":
        raise ContinuityBroken(st.broken_reason or "continuity is broken; fork from the last trusted head")
    res = store.append(st.context_id, objects, st.expected_head, operation_id, writer_session_id=st.session_id, **kw)
    _record(st, res)
    return res


def _record(st: CoordinatorState, res: AppendResult) -> None:
    if res.status == "committed":
        st.written.append(res.head["commit_digest"])
    st.expected_head = res.head
    if st.start == "pending-genesis" and res.head["seq"] == 1:
        st.start, st.anchor = "anchored-genesis", dict(res.head)


def head_continuity(store: Store, st: CoordinatorState) -> dict:
    """verified / unverified / broken with its basis (spec 11.3)."""
    basis = {"start": st.start, "anchor": st.anchor, "written": len(st.written), "how_to_verify": HOW_TO_VERIFY}
    if st.broken_reason:
        return {"status": "broken", "basis": basis | {"case": "anchor-mismatch", "reason": st.broken_reason}}
    if st.anchor is None:
        return {"status": "unverified", "basis": basis | {"reason": "no anchor: a session without a trusted "
                                                          "checkpoint (or with lost state) stays unverified"}}
    a = st.anchor
    c = store.commit_at(st.context_id, a["segment_id"], a["seq"])
    if c is None or c["digest"] != a["commit_digest"]:
        return {"status": "broken", "basis": basis | {"case": "anchor-mismatch",
                                                      "reason": "the anchor digest is not on the chain"}}
    head = store.head(st.context_id)
    if head is None or head["segment_id"] != a["segment_id"]:
        return {"status": "broken", "basis": basis | {"case": "foreign-segment",
                                                      "reason": "the head moved to a segment this session did not "
                                                                "open"}}
    after = []
    for seq in range(a["seq"] + 1, head["seq"] + 1):
        x = store.commit_at(st.context_id, a["segment_id"], seq)
        after.append(x["digest"] if x else None)
    foreign = [d for d in after if d not in st.written]
    if foreign:
        on_chain = set(after) | {a["commit_digest"]}
        lost = [d for d in st.written if d not in on_chain]
        case = "saved-value-not-on-chain" if lost else "foreign-commits-appended"
        return {"status": "broken", "basis": basis | {"case": case, "foreign_commits": foreign, "saved_not_on_chain":
                                                      lost}}
    return {"status": "verified", "basis": basis | {"verified_commits": len(after)}}


def _next_segment(store: Store, context_id: str) -> str:
    return f"seg-{len(store.segments(context_id)) + 1}"


def _open_segment(store: Store, st: CoordinatorState, objects: list[dict], origin: dict, operation_id: str,
                  anchor_ok: bool) -> AppendResult:
    res = store.append(st.context_id, objects, store.head(st.context_id), operation_id,
                       writer_session_id=st.session_id, _genesis_origin=origin,
                       _segment_id=_next_segment(store, st.context_id))
    st.written = [res.head["commit_digest"]]
    st.expected_head = res.head
    st.broken_reason = None
    if anchor_ok:
        st.anchor = dict(res.head)
        st.start = "anchored-" + ("fork" if "forked_from" in origin else "migration")
    else:
        st.anchor = None
        st.start = "unanchored-start"
    return res


def fork(store: Store, st: CoordinatorState, last_trusted_seq: int, operation_id: str) -> AppendResult:
    """Recovery from broken: a new segment from the last trusted head; the old segment stays as evidence. The new
    segment anchors on its genesis only when the fork point is this session's trusted anchor."""
    seg = (st.anchor or {}).get("segment_id") or store.head(st.context_id)["segment_id"]
    src = store.commit_at(st.context_id, seg, last_trusted_seq)
    if src is None:
        raise KeyError(f"seq {last_trusted_seq} is not on {seg}")
    bundle = store.load_bundle(st.context_id, last_trusted_seq, segment_id=seg)
    objects = [o for c in bundle["commits"] for o in c["objects"]]
    top = store.load_bundle(st.context_id, segment_id=seg)
    excluded = [c["digest"] for c in top["commits"] if c["commit"]["seq"] > last_trusted_seq]
    origin = {"forked_from": {"segment_id": seg, "seq": last_trusted_seq, "commit_digest": src["digest"]},
              "excluded_commits": excluded}
    trusted = st.anchor is not None and st.anchor["segment_id"] == seg and st.anchor["seq"] == last_trusted_seq \
        and st.anchor["commit_digest"] == src["digest"]
    return _open_segment(store, st, objects, origin, operation_id, trusted)


def migrate(store: Store, st: CoordinatorState, transform, operation_id: str) -> AppendResult:
    """An incompatible 0.x schema change: a new segment whose genesis records migrated_from; the old segment is never
    touched. It anchors on its genesis when the source position is verified for this session."""
    status = head_continuity(store, st)["status"]
    if status == "broken":
        raise ContinuityBroken("fork before migrating")
    head = store.head(st.context_id)
    bundle = store.load_bundle(st.context_id)
    objects = transform([o for c in bundle["commits"] for o in c["objects"]])
    origin = {"migrated_from": {"segment_id": head["segment_id"], "seq": head["seq"],
                                "commit_digest": head["commit_digest"]}}
    return _open_segment(store, st, objects, origin, operation_id, status == "verified")
