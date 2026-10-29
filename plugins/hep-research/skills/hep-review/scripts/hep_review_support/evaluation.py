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
RANK = {"experimental": 0, "pilot-checked-scope": 1, "evaluated-scope": 2}
EVIDENCE_KINDS = {"pilot-checked-scope": ("pilot", "held-out-evaluation"), "evaluated-scope": ("held-out-evaluation",)}
REASSESSMENT_REASONS = ("fingerprint-changed", "new-failure-type")
READER_FILES = ("materials.py", "submissions.py")  # how review material and submissions are read


class ClaimError(ValueError):
    pass


def host_capabilities_digest(host: dict) -> str:
    """The host profile as far as capability goes: measured capability values and their basis, and the settings;
    notes and evidence text are left out so rewording them does not invalidate a claim."""
    return H.metadata_digest({"id": host.get("id"), "settings": host.get("settings"),
                              "capabilities": {k: {"value": v.get("value"), "basis": v.get("basis")}
                                               for k, v in sorted(host.get("capabilities", {}).items())}})


def reader_digest(sources: dict[str, bytes] | None = None) -> str:
    here = Path(__file__).resolve().parent
    sources = sources or {name: (here / name).read_bytes() for name in READER_FILES}
    return hashlib.sha256(b"".join(name.encode() + b"\0" + sources[name] for name in READER_FILES)).hexdigest()


def fingerprint_parts(*, model_alias: str, model_pinned: bool, date: str, host: dict | None = None,
                      packet: str | None = None, validator_version: str | None = None,
                      reader: str | None = None) -> dict:
    """What a review capability depends on (spec 15.6): host capabilities, packet text, validator, the code that reads
    material and submissions, hash profiles, and the model. The defaults describe the code as it is now; a claim
    measured earlier passes the values of the commit it was measured at. An alias that cannot be pinned is recorded
    as such, with the date (never guessed)."""
    return {"host_capabilities_digest": host_capabilities_digest(host or K.load_host_profile()),
            "packet_template_digest": hashlib.sha256((packet or K.PACKET).encode("utf-8")).hexdigest(),
            "validator_version": validator_version or H.LATEST_VALIDATOR, "reader_digest": reader or reader_digest(),
            "hash_profile": [H.METADATA_PROFILE, H.RAW_PROFILE],
            "model": {"alias": model_alias, "pinned": True if model_pinned else "unknown", "date": date}}


def fingerprint(parts: dict) -> str:
    return H.metadata_digest(parts)


def make_claim(claim_id: str, scope: dict, binding: dict, *, results: dict, limitations: list[str], parts: dict,
               measured_at: str) -> dict:
    """A new claim is experimental; its scope and binding say exactly what was measured and how, and its fingerprint
    describes the code and host at `measured_at` (a commit), not at the time the claim file is written."""
    return {"id": claim_id, "state": "experimental", "scope": copy.deepcopy(scope), "binding": copy.deepcopy(binding),
            "results": copy.deepcopy(results), "limitations": list(limitations), "measured_at": measured_at,
            "initial_fingerprint_parts": copy.deepcopy(parts), "fingerprint_parts": copy.deepcopy(parts),
            "fingerprint": fingerprint(parts), "history": []}


def _held_before_reassessment(claim: dict) -> tuple[str, str | None]:
    step = next(s for s in reversed(claim["history"]) if s["to"] == "needs-reassessment")
    return step["from"], step.get("reason")


def transition(claim: dict, to: str, *, evidence: dict | None = None, reason: str | None = None,
               parts: dict | None = None, at: str) -> dict:
    """The one way a claim changes state; returns a new claim with the step appended to its history.

    Upgrades need new gate evidence (engineering gate passed, graders calibrated, a report not used before by this
    claim) of a kind that fits: evaluated-scope only from a held-out evaluation, which may also lift an experimental
    claim directly. A live claim falls to needs-reassessment for a stated reason; it comes back no higher than it was,
    with new evidence and, after a fingerprint change, the new fingerprint parts."""
    state = claim["state"]
    if to not in CLAIM_STATES:
        raise ClaimError(f"unknown claim state {to!r}")
    if state == "retired":
        raise ClaimError("a retired claim never changes state")
    step: dict = {"from": state, "to": to, "at": at}
    out = copy.deepcopy(claim)
    if to in EVIDENCE_KINDS:
        ceiling, why = (_held_before_reassessment(claim) if state == "needs-reassessment" else (to, None))
        if state != "needs-reassessment" and RANK.get(state, 9) >= RANK[to]:
            raise ClaimError(f"{state} -> {to} is not an upgrade")
        if RANK[to] > RANK.get(ceiling, 0):
            raise ClaimError(f"a reassessed claim comes back no higher than {ceiling}")
        if not evidence or evidence.get("engineering_gate") is not True or evidence.get("graders_calibrated") is not True \
                or not evidence.get("report"):
            raise ClaimError("an upgrade needs gate evidence: engineering gate passed, graders calibrated, a report")
        if evidence.get("kind") not in EVIDENCE_KINDS[to]:
            raise ClaimError(f"{to} needs evidence of kind {EVIDENCE_KINDS[to]}, not {evidence.get('kind')!r}")
        used = {s.get("evidence", {}).get("report") for s in claim["history"]}
        if evidence["report"] in used:
            raise ClaimError(f"evidence {evidence['report']!r} was already used by this claim")
        if why == "fingerprint-changed":
            if parts is None:
                raise ClaimError("after a fingerprint change, coming back needs the new fingerprint parts")
            step["parts"] = copy.deepcopy(parts)
            out["fingerprint_parts"], out["fingerprint"] = copy.deepcopy(parts), fingerprint(parts)
        step["evidence"] = copy.deepcopy(evidence)
    elif to == "needs-reassessment":
        if state not in RANK or state == "experimental":
            raise ClaimError(f"only a live claim can need reassessment, not {state}")
        if reason not in REASSESSMENT_REASONS:
            raise ClaimError(f"reassessment needs one of {REASSESSMENT_REASONS}")
        step["reason"] = reason
    elif to == "retired":
        if not reason:
            raise ClaimError("retiring a claim needs a reason")
        step["reason"] = reason
    else:
        raise ClaimError(f"{state} -> {to} is not a claim transition")
    out["state"] = to
    out["history"].append(step)
    return out


def reassess_if_changed(claim: dict, current_parts: dict, *, at: str) -> dict:
    """A live claim whose fingerprint no longer matches what it depends on needs reassessment (spec 15.6)."""
    if claim["state"] not in ("pilot-checked-scope", "evaluated-scope") or \
            fingerprint(current_parts) == claim["fingerprint"]:
        return claim
    return transition(claim, "needs-reassessment", reason="fingerprint-changed", at=at)


def _replay(c: dict) -> dict:
    """Rebuild a claim from its initial parts and history through transition(); any refused step raises."""
    out = make_claim(c["id"], c["scope"], c["binding"], results=c["results"], limitations=c["limitations"],
                     parts=c["initial_fingerprint_parts"], measured_at=c["measured_at"])
    for step in c["history"]:
        out = transition(out, step["to"], evidence=step.get("evidence"), reason=step.get("reason"),
                         parts=step.get("parts"), at=step["at"])
    return out


def check_registry(path: str | Path, *, current: bool = False) -> list[str]:
    """Problems with a claims file. Every claim is replayed from its initial fingerprint parts through the state
    machine, so a skipped state, missing or reused evidence, a false gate or a fingerprint not reached by the history
    is a problem. With current=True a live claim whose code and host parts differ from the present ones (the model
    part cannot be observed here and is compared as recorded) must have been marked needs-reassessment. A claims file
    is evidence about claims, not a proof: a consistent forgery of the whole history is not detectable here."""
    problems = []
    for c in json.loads(Path(path).read_text(encoding="utf-8")).get("claims", []):
        cid = c.get("id", "?") if isinstance(c, dict) else "?"
        try:
            again = _replay(c)
            if again["state"] != c["state"] or again["fingerprint"] != c["fingerprint"] \
                    or again["fingerprint_parts"] != c["fingerprint_parts"]:
                problems.append(f"{cid}: state or fingerprint is not what its history reaches")
                continue
            if current and c["state"] in ("pilot-checked-scope", "evaluated-scope"):
                m = c["fingerprint_parts"]["model"]
                now = fingerprint_parts(model_alias=m["alias"], model_pinned=m["pinned"] is True, date=m["date"])
                if fingerprint(now) != c["fingerprint"]:
                    problems.append(f"{cid}: fingerprint changed since the claim was measured; mark it "
                                    "needs-reassessment")
        except ClaimError as e:
            problems.append(f"{cid}: history refused by the state machine: {e}")
        except (KeyError, TypeError, StopIteration) as e:
            problems.append(f"{cid}: malformed claim ({type(e).__name__}: {e})")
    return problems
