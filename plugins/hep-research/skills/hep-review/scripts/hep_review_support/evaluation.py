"""Salted gold commitments and held-out status (hep-review spec v9 section 15.4).

The commitment SHA-256(nonce || gold) proves the gold was not altered afterwards and, while the nonce is undisclosed,
does not leak it; it does not prove a reviewer never read the gold original. On a shared-filesystem host only gold and
nonces held off the host by the user count as held out.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

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
