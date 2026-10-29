"""Objects for store tests: a small review context whose raw refs point at real blobs in the store."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))

from contracts import hep_review as H  # noqa: E402
from hep_review_support import submissions as SUB  # noqa: E402
from hep_review_support.materials import raw_ref  # noqa: E402

FLOOR = [{"condition": c, "required": True} for c in ("non-author", "fresh-context", "no-other-evaluations-seen")]
# A caller-supplied location observation for test temp folders (the store accepts an explicit observation instead of
# probing; production callers probe with store.check_location).
TEMP_LOCATION = {"path": "<test temp>", "fs_type": "test-temp", "sync_folder": False, "supported": True,
                 "reason": "test temp folder supplied by the test"}


def header(kind, oid, ctx="ctx-1"):
    return {"protocol": H.PROTOCOL, "schema_version": H.SCHEMA_VERSION, "record_kind": kind, "id": oid,
            "context_id": ctx}


def obligation(oid, required=True, methods=("recompute",)):
    return {"id": oid, "origin_requirement_ids": ["REQ-1"], "question": f"Q {oid}?", "targets": ["M1"],
            "criterion": f"C {oid}.", "assumptions": [], "tolerances": [],
            "adoption_policy": {"second_method_required": False, "verification_required": False, "qualifications": []},
            "required_methods": list(methods), "evidence_requirements": ["E"], "independence_requirements": [],
            "required": required, "decision_required": True if required else False}


def intent(ctx="ctx-1"):
    return header("intent", "intent-1", ctx) | {
        "revision": 1, "target_tier": "R2", "minimum_requirements": [{"id": "REQ-1", "text": "R"}],
        "material_scope": ["M1"], "authorized_by": {"actor": "user", "basis": "declared"}}


def manifest(store, mid="manifest-1", content=b"material v1", ctx="ctx-1"):
    d = store.put_blob(content)
    return header("manifest", mid, ctx) | {"materials": [{
        "material_id": "M1", "raw_ref": raw_ref("M1", d), "view_version": "raw/1", "authors": ["author-a"],
        "authors_basis": "declared"}]}


def plan(rev, obligations, manifest_id="manifest-1", ctx="ctx-1", **extra):
    p = header("plan", f"plan-{rev}", ctx) | {
        "revision": rev, "parent_revision": rev - 1 if rev > 1 else None, "intent_id": "intent-1",
        "intent_revision": 1, "manifest_id": manifest_id, "obligations": copy.deepcopy(obligations),
        "independence_requirements": FLOOR,
        "assignment_specs": [{"id": "spec-1", "obligation_ids": [o["id"] for o in obligations], "role": "reviewer"}],
        "scope_scan": "performed-no-known-gaps", "judgments": [],
        "environment_observations": [{"executor": "exec-1", "tools": ["python3"], "environment_refs": []}]}
    p.update(extra)
    return p


HOST = json.loads((ROOT / "skills" / "hep-review" / "assets" / "host_profile.json").read_text("utf-8"))
HOST_DIGEST = H.metadata_digest(HOST)


def assignment(aid, actor, rev=1, ctx="ctx-1", role="reviewer"):
    good = {"satisfied": True, "basis": "declared"}
    return header("assignment", aid, ctx) | {
        "plan_revision": rev, "spec_id": "spec-1", "actor": actor, "role": role,
        "qualified": {"satisfied": True, "basis": "declared"},
        "conditions": {"non-author": good, "fresh-context": {"satisfied": True, "basis": "observed"},
                       "no-other-evaluations-seen": {"satisfied": True, "basis": "advisory"}},
        "restrictions": [], "dispatch": {"via": "agent-tool", "host": HOST["id"], "invocation_id": f"test-{aid}"},
        "host_profile_digest": HOST_DIGEST}


def record(store, rid, aid, actor, obligation_id="O1", verdict="supported", rev=1, ctx="ctx-1", evidence=b"ev",
           submission=None, fidelity="file-transfer", finding=False):
    """A record derived from a real raw submission, as the store requires (it re-derives it at admission)."""
    del evidence  # evidence is the submission itself
    objs = [o for c in store.load_bundle(ctx)["commits"] for o in c["objects"]]
    asg = next(o for o in objs if o["record_kind"] == "assignment" and o["id"] == aid)
    man = next(o for o in objs if o["record_kind"] == "manifest")
    loc = {"material_id": "M1", "digest": man["materials"][0]["raw_ref"]["digest"]}
    answer = {"obligation_id": obligation_id, "outcome": verdict, "reasoning": "recomputed", "missing_inputs": [],
              "attempts": [{"method": "recompute", "observation": "completed", "tools": ["python3"]}],
              "evidence": [{"requirement": "E", "summary": "recomputation"}],
              "findings": [{"claim": "defect", "element": "x", "locator": loc}] if finding else []}
    raw = submission if submission is not None else json.dumps({"assignment_id": aid, "answers": [answer]}).encode()
    digest = store.put_blob(raw)
    return SUB.parse(objs, asg, raw, raw_ref(f"raw-{rid}", digest), fidelity, executor=HOST["reviewer_executor"],
                     record_id=rid)


def seed(store, ctx="ctx-1", session="s-1"):
    """intent, manifest, plan 1 with O1, an assignment and a supported record: five commits."""
    head = None
    steps = (lambda: [intent(ctx)], lambda: [manifest(store, ctx=ctx)], lambda: [plan(1, [obligation("O1")], ctx=ctx)],
             lambda: [assignment("asg-1", "rev-1", ctx=ctx)],
             lambda: [record(store, "rec-1", "asg-1", "rev-1", ctx=ctx)])
    for i, make in enumerate(steps, 1):  # each step built after the previous commit (records derive from the store)
        res = store.append(ctx, make(), head, f"op-seed-{i}", writer_session_id=session)
        head = res.head
    return head
