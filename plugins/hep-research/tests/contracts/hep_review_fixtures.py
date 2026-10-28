"""Bundle builder for the hep-review kernel tests (spec v9 sections 6-8). It writes records the way a coordinator
would commit them; it never computes outcomes, flags or tiers (those come only from contracts.hep_review)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import hep_review as H  # noqa: E402

FLOOR = ["non-author", "fresh-context", "no-other-evaluations-seen"]
GOOD_CONDITIONS = {"non-author": {"satisfied": True, "basis": "declared"},
                   "fresh-context": {"satisfied": True, "basis": "observed"},
                   "no-other-evaluations-seen": {"satisfied": True, "basis": "advisory"}}


def ref(logical_id: str, digest: str, profile: str = H.RAW_PROFILE, scope: str = "raw") -> dict:
    return {"logical_id": logical_id, "algorithm": "sha256", "hash_scope": scope, "profile_id": profile,
            "digest": digest}


def hexd(tag: str) -> str:
    import hashlib
    return hashlib.sha256(tag.encode()).hexdigest()


def header(kind: str, oid: str) -> dict:
    return {"protocol": H.PROTOCOL, "schema_version": H.SCHEMA_VERSION, "record_kind": kind, "id": oid,
            "context_id": "ctx-1"}


def obligation(oid: str, *, required=True, decision_required=True, targets=("M1",), requirements=("REQ-1",),
               methods=("recompute",), evidence=("E",), tolerances=(), adoption=None, **extra) -> dict:
    o = {"id": oid, "origin_requirement_ids": list(requirements), "question": f"Question of {oid}?",
         "targets": list(targets), "criterion": f"Criterion of {oid}.", "assumptions": [],
         "tolerances": list(tolerances),
         "adoption_policy": adoption or {"second_method_required": False, "verification_required": False,
                                         "qualifications": []},
         "required_methods": list(methods), "evidence_requirements": list(evidence),
         "independence_requirements": [], "required": required}
    if decision_required is not None:
        o["decision_required"] = decision_required
    o.update(extra)
    return o


class Case:
    """One review context. Objects are appended in creation order; each becomes one commit."""

    def __init__(self, requirements=("REQ-1",), target_tier="R2", mode="recorded"):
        self.mode = mode
        self.entries: list[dict] = []
        self.blob_checks: dict[str, str] = {}
        self.n = 0
        self.intent = header("intent", "intent-1") | {
            "revision": 1, "target_tier": target_tier,
            "minimum_requirements": [{"id": r, "text": f"Requirement {r}"} for r in requirements],
            "material_scope": ["M1", "M2"], "authorized_by": {"actor": "user", "basis": "declared"}}
        self.materials = {"M1": {"material_id": "M1", "raw_ref": ref("M1", hexd("M1-v1")), "view_version": "text/1",
                                 "authors": ["author-a"], "authors_basis": "declared"},
                          "M2": {"material_id": "M2", "raw_ref": ref("M2", hexd("M2-v1")), "view_version": "text/1",
                                 "authors": ["author-a"], "authors_basis": "declared"}}
        self.plans: list[dict] = []
        self.manifest_rev = 0
        self.extra_claim = None
        self.add(self.intent)
        self.new_manifest()

    # -- objects --------------------------------------------------------------------------------------------------
    def add(self, committed: dict) -> dict:
        self.entries.append({"validator_version": H.LATEST_VALIDATOR, "objects": [copy.deepcopy(committed)]})
        return committed

    def new_manifest(self, **changes) -> str:
        for mid, digest_tag in changes.items():
            self.materials[mid] = dict(self.materials[mid], raw_ref=ref(mid, hexd(digest_tag)))
        self.manifest_rev += 1
        mid = f"manifest-{self.manifest_rev}"
        self.add(header("manifest", mid) | {"materials": copy.deepcopy(list(self.materials.values()))})
        self.manifest_id = mid
        return mid

    def plan(self, obligations, *, independence=None, scope_scan="performed-no-known-gaps", obligation_map=None,
             judgments=(), env=(), assignment_specs=None, **extra) -> dict:
        rev = len(self.plans) + 1
        p = header("plan", f"plan-{rev}") | {
            "revision": rev, "parent_revision": rev - 1 if rev > 1 else None, "intent_id": "intent-1",
            "intent_revision": 1, "manifest_id": self.manifest_id, "obligations": copy.deepcopy(list(obligations)),
            "independence_requirements": [{"condition": c, "required": True} for c in FLOOR]
            if independence is None else independence,
            "assignment_specs": assignment_specs if assignment_specs is not None
            else [{"id": "spec-1", "obligation_ids": [o["id"] for o in obligations], "role": "reviewer",
                   "deadline": "P1D"}],
            "scope_scan": scope_scan, "judgments": list(judgments), "environment_observations": list(env)}
        if obligation_map is not None:
            p["obligation_map"] = obligation_map
        p.update(extra)
        self.plans.append(p)
        self.add(p)
        return p

    def assignment(self, actor: str, *, conditions=None, role="reviewer", qualified=True, **extra) -> str:
        self.n += 1
        aid = f"asg-{self.n}"
        self.add(header("assignment", aid) | {
            "plan_revision": len(self.plans), "spec_id": "spec-1", "actor": actor, "role": role,
            "qualified": {"satisfied": qualified, "basis": "declared"},
            "conditions": copy.deepcopy(conditions if conditions is not None else GOOD_CONDITIONS),
            "restrictions": [], **extra})
        return aid

    def review(self, obligation_id: str, verdict: str, *, actor=None, finding=False, tools=("python3",),
               executor="exec-1", method="recompute", evidence=True, fidelity="file-transfer", conditions=None,
               cited=(), record_type="submission", judgments=(), suspected_conflicts=(), responses=(),
               discharge=None, missing_inputs=(), observation="completed", omit_tools=False, assignment=None,
               evidence_digest=None, findings_extra=(), answer_extra=None, role="reviewer") -> dict:
        actor = actor or f"rev-{self.n + 1}"
        aid = assignment or self.assignment(actor, conditions=conditions, role=role)
        rid = f"rec-{len(self.entries) + 1}"
        k = len(self.entries) + 1
        items_attempt = {"id": f"A{k}", "obligation_id": obligation_id, "method": method, "observation": observation,
                         "executor": executor, "environment_refs": [], "depends_on": []}
        if not omit_tools:
            items_attempt["tools"] = list(tools)
        ev = []
        if evidence:
            d = evidence_digest or hexd(f"ev-{k}")
            ev.append({"id": f"E{k}", "obligation_id": obligation_id, "requirement": "E", "content_ref": ref(f"E{k}", d),
                       "depends_on": [f"A{k}"]})
            self.blob_checks.setdefault(d, "ok")
        fnd = []
        if finding:
            fnd.append({"id": f"F{k}", "obligation_id": obligation_id, "claim": "defect", "element": "x",
                        "locator": {"material_id": "M1", "digest": self.materials["M1"]["raw_ref"]["digest"]},
                        "method": method, "depends_on": [f"E{k}"] if evidence else [f"A{k}"]})
        fnd.extend(findings_extra)
        ans = {"id": f"N{k}", "obligation_id": obligation_id, "verdict": verdict,
               "finding_ids": [f["id"] for f in fnd], "attempt_ids": [f"A{k}"],
               "evidence_ids": [e["id"] for e in ev], "cited_materials": list(cited),
               "missing_inputs": list(missing_inputs), "depends_on": [e["id"] for e in ev] or [f"A{k}"]}
        if discharge is not None:
            ans["discharge"] = discharge
        if answer_extra:
            ans.update(answer_extra)
        rec = header("record", rid) | {
            "type": record_type, "plan_revision": len(self.plans), "assignment_id": aid, "actor": actor,
            "raw_submission_ref": ref(f"raw-{rid}", hexd(f"raw-{rid}")), "submission_fidelity": fidelity,
            "answers": [ans] if verdict is not None else [], "findings": fnd, "attempts": [items_attempt],
            "evidence": ev, "judgments": list(judgments), "suspected_conflicts": list(suspected_conflicts),
            "responses": list(responses), "limitations": []}
        self.add(rec)
        return rec

    def judge(self, judgments, *, actor="verifier-1", role="verifier", suspected_conflicts=()) -> dict:
        aid = self.assignment(actor, role=role)
        rid = f"rec-{len(self.entries) + 1}"
        rec = header("record", rid) | {
            "type": "verification" if role == "verifier" else "adjudication", "plan_revision": len(self.plans),
            "assignment_id": aid, "actor": actor, "raw_submission_ref": ref(f"raw-{rid}", hexd(f"raw-{rid}")),
            "submission_fidelity": "file-transfer", "answers": [], "findings": [], "attempts": [], "evidence": [],
            "judgments": list(judgments), "suspected_conflicts": list(suspected_conflicts), "responses": [],
            "limitations": []}
        self.add(rec)
        return rec

    # -- bundle ---------------------------------------------------------------------------------------------------
    def bundle(self) -> dict:
        commits = []
        prev = None
        for seq, e in enumerate(self.entries, 1):
            objs = e["objects"]
            payload = {"objects": sorted((H.object_ref(o) for o in objs), key=lambda r: r["digest"]),
                       "head_changes": {}}
            c = {"protocol": H.PROTOCOL, "context_id": "ctx-1", "segment_id": "seg-1", "seq": seq,
                 "prev_commit_digest": prev, "operation_id": f"op-{seq}", "payload_digest": H.metadata_digest(payload),
                 "validator_version": e["validator_version"], "writer_session_id": "s-1"}
            digest = H.metadata_digest(c)
            commits.append({"commit": c, "digest": digest, "objects": copy.deepcopy(objs)})
            prev = digest
        b = {"context_id": "ctx-1", "segment_id": "seg-1", "mode": self.mode, "commits": commits,
             "as_of_seq": len(commits), "as_of_commit_digest": prev, "blob_checks": dict(self.blob_checks)}
        if self.extra_claim is not None:
            b["claim_binding"] = self.extra_claim
        return b
