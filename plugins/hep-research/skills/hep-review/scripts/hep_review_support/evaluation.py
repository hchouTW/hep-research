"""Salted gold commitments, held-out status (spec v9 section 15.4) and capability claims (15.6, T08).

The commitment SHA-256(nonce || gold) proves the gold was not altered afterwards and, while the nonce is undisclosed,
does not leak it; it does not prove a reviewer never read the gold original. On a shared-filesystem host only gold and
nonces held off the host by the user count as held out.

A capability claim binds what was measured (scope, suite, trial plan, results, limitations) to a fingerprint of what
the capability depends on. It moves up only with gate evidence, one state at a time, and falls to needs-reassessment
when its fingerprint changes or a new failure type appears; retired is final.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import secrets
from pathlib import Path

from contracts import hep_review as H
from hep_review_support import coordinator as K

HELD_OUT_LOCATIONS = {"user-held-off-host"}


def commit_gold(gold: bytes) -> dict:
    """A 256-bit random nonce and the salted commitment to write to the evaluation log before the first trial."""
    nonce = secrets.token_bytes(32)
    return {"nonce": nonce, "commitment": hashlib.sha256(nonce + gold).hexdigest(), "algorithm": "sha256(nonce||gold)"}


def verify_gold(gold: bytes, nonce: bytes, commitment: str) -> bool:
    return hmac.compare_digest(hashlib.sha256(nonce + gold).hexdigest(), commitment)


def held_out_status(location_kind: str) -> dict:
    """Whether gold and nonce stored at this kind of location can count as held out from reviewers on this host."""
    if location_kind in HELD_OUT_LOCATIONS:
        return {"status": "met", "basis": "declared", "location": location_kind}
    return {"status": "unmet", "basis": "observed", "location": location_kind,
            "reason": "reviewers share this host's filesystem (host profile H1); only gold held off the host counts"}


CLAIM_STATES = ("experimental", "pilot-checked-scope", "evaluated-scope", "needs-reassessment", "retired")
UPGRADES = {"experimental": "pilot-checked-scope", "pilot-checked-scope": "evaluated-scope"}
REASSESSMENT_REASONS = ("fingerprint-changed", "new-failure-type")
READER_PROFILE = "materials.read_controlled/1"


class ClaimError(ValueError):
    pass


def fingerprint_parts(*, model_alias: str, model_pinned: bool, date: str, host: dict | None = None) -> dict:
    """What a review capability depends on (spec 15.6): host profile, packet text, validator, reader and hash profiles,
    and the model. An alias that cannot be pinned is recorded as such, with the date (never guessed)."""
    host = host or K.load_host_profile()
    return {"host_profile_digest": H.metadata_digest(host),
            "packet_template_digest": hashlib.sha256(K.PACKET.encode("utf-8")).hexdigest(),
            "validator_version": H.LATEST_VALIDATOR, "reader_profile": READER_PROFILE,
            "hash_profile": [H.METADATA_PROFILE, H.RAW_PROFILE],
            "model": {"alias": model_alias, "pinned": True if model_pinned else "unknown", "date": date}}


def fingerprint(parts: dict) -> str:
    return H.metadata_digest(parts)


def make_claim(claim_id: str, scope: dict, binding: dict, *, results: dict, limitations: list[str],
               parts: dict) -> dict:
    """A new claim is experimental; its scope and binding say exactly what was measured and how."""
    return {"id": claim_id, "state": "experimental", "scope": copy.deepcopy(scope), "binding": copy.deepcopy(binding),
            "results": copy.deepcopy(results), "limitations": list(limitations),
            "fingerprint_parts": copy.deepcopy(parts), "fingerprint": fingerprint(parts), "history": []}


def transition(claim: dict, to: str, *, evidence: dict | None = None, reason: str | None = None, at: str) -> dict:
    """The one way a claim changes state; returns a new claim with the step appended to its history."""
    state = claim["state"]
    if to not in CLAIM_STATES:
        raise ClaimError(f"unknown claim state {to!r}")
    if state == "retired":
        raise ClaimError("a retired claim never changes state")
    step: dict = {"from": state, "to": to, "at": at}
    if to in ("pilot-checked-scope", "evaluated-scope"):
        allowed_from = {k for k, v in UPGRADES.items() if v == to} | {"needs-reassessment"}
        if state not in allowed_from:
            raise ClaimError(f"{state} -> {to} skips a state")
        if not evidence or evidence.get("engineering_gate") is not True or evidence.get("graders_calibrated") is not True \
                or not evidence.get("report"):
            raise ClaimError("an upgrade needs gate evidence: engineering gate passed, graders calibrated, a report")
        step["evidence"] = copy.deepcopy(evidence)
    elif to == "needs-reassessment":
        if reason not in REASSESSMENT_REASONS:
            raise ClaimError(f"reassessment needs one of {REASSESSMENT_REASONS}")
        step["reason"] = reason
    elif to == "retired":
        if not reason:
            raise ClaimError("retiring a claim needs a reason")
        step["reason"] = reason
    else:
        raise ClaimError(f"{state} -> {to} is not a claim transition")
    out = copy.deepcopy(claim)
    out["state"] = to
    out["history"].append(step)
    return out


def reassess_if_changed(claim: dict, current_parts: dict, *, at: str) -> dict:
    """A claim whose fingerprint no longer matches what it depends on needs reassessment (spec 15.6)."""
    if claim["state"] in ("experimental", "needs-reassessment", "retired") or \
            fingerprint(current_parts) == claim["fingerprint"]:
        return claim
    return transition(claim, "needs-reassessment", reason="fingerprint-changed", at=at)


def _replayed_state(claim: dict) -> str | None:
    state = "experimental"
    for step in claim.get("history", []):
        if step.get("from") != state:
            return None
        state = step.get("to")
    return state


def check_registry(path: str | Path, *, current: bool = False) -> list[str]:
    """Problems with a claims file: an unknown state, a state its history does not reach, a fingerprint that does
    not match its parts, an upgrade without evidence; with current=True also a live claim whose fingerprint no longer
    matches the code and host profile (it must be marked needs-reassessment)."""
    problems = []
    for c in json.loads(Path(path).read_text(encoding="utf-8")).get("claims", []):
        cid = c.get("id", "?")
        if c.get("state") not in CLAIM_STATES:
            problems.append(f"{cid}: unknown state {c.get('state')!r}")
            continue
        if _replayed_state(c) != c["state"]:
            problems.append(f"{cid}: state {c['state']} is not what its history reaches")
        if c.get("fingerprint") != fingerprint(c.get("fingerprint_parts", {})):
            problems.append(f"{cid}: fingerprint does not match its parts")
        for step in c.get("history", []):
            if step.get("to") in UPGRADES.values() and not step.get("evidence", {}).get("report"):
                problems.append(f"{cid}: upgrade to {step['to']} without evidence")
        if current and c["state"] in ("pilot-checked-scope", "evaluated-scope"):
            m = c["fingerprint_parts"]["model"]
            now = fingerprint_parts(model_alias=m["alias"], model_pinned=m["pinned"] is True, date=m["date"])
            if fingerprint(now) != c["fingerprint"]:
                problems.append(f"{cid}: fingerprint changed since the claim; mark it needs-reassessment")
    return problems
