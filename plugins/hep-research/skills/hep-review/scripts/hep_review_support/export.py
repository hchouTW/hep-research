"""Export, verify_export and import_export (hep-review spec v9 section 11.6).

An export is one strict-JSON file in the metadata encoding: the chosen segment's commits <= N with their objects, the
segment origin, the blob inventory and the blob bytes (base64), and a partial flag. verify_export gives two separate
conclusions: internal consistency (every commit digest, the prev chain, payload digests and blob bytes recomputed) and
integrity relative to a trusted checkpoint (the digest at seq N must match; N+1..M are listed as appended after the
checkpoint, unconfirmed). Without a checkpoint only self-consistency is claimed. import_export verifies first and
rebuilds a store only if that passes; no signature PKI is claimed.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from contracts import hep_review as H
from hep_review_support import continuity as C
from hep_review_support.store import Store, _raw_refs

FORMAT = "hep-review-export/0"
MAX_EXPORT_BYTES = 512 * 1024 * 1024


class ImportRefused(Exception):
    """The export failed verification or cannot be imported here."""


def export(store: Store, context_id: str, out_path: str | Path, *, segment_id: str | None = None,
           as_of_seq: int | None = None, partial: bool = False) -> dict:
    b = store.load_bundle(context_id, as_of_seq, segment_id=segment_id)
    seg = next((s for s in store.segments(context_id) if s["segment_id"] == b["segment_id"]), {})
    digests = sorted({d for c in b["commits"] for o in c["objects"] for d in _raw_refs(o)})
    blobs, inventory = [], []  # lists: digests are not JSON key names under strict ingestion
    for d in digests:
        status = store.blob_status(d)
        inventory.append({"digest": d, "status": status})
        if status == "ok":
            blobs.append({"digest": d, "base64": base64.b64encode(store.read_blob(d)).decode("ascii")})
    doc = {"format": FORMAT, "context_id": context_id, "segment_id": b["segment_id"],
           "segment_origin": seg.get("origin"), "as_of_seq": b["as_of_seq"],
           "as_of_commit_digest": b["as_of_commit_digest"], "partial": partial or as_of_seq is not None
           and as_of_seq < (store.head(context_id) or {}).get("seq", 0),
           "commits": b["commits"], "blob_inventory": inventory, "blobs": blobs}
    raw = H.encode(doc)
    Path(out_path).write_bytes(raw)
    return {"status": "ok", "path": str(out_path), "sha256": hashlib.sha256(raw).hexdigest(),
            "commits": len(b["commits"]), "partial": doc["partial"]}


def _load(path: str | Path) -> dict:
    return H.ingest_json(Path(path).read_bytes(), max_bytes=MAX_EXPORT_BYTES, max_depth=128)


def _blob_map(doc: dict) -> dict:
    return {b["digest"]: b["base64"] for b in doc.get("blobs", [])}


def bundle_from_export(path: str | Path) -> dict:
    """The kernel bundle an export describes, for a third party's byte-for-byte recomputation of layer 1 (N60)."""
    doc = _load(path)
    checks = {}
    blobs = _blob_map(doc)
    for item in doc["blob_inventory"]:
        d = item["digest"]
        encoded = blobs.get(d)
        checks[d] = "missing" if encoded is None else ("ok" if hashlib.sha256(base64.b64decode(encoded)).hexdigest() == d
                                                    else "changed")
    return {"context_id": doc["context_id"], "segment_id": doc["segment_id"], "mode": "recorded",
            "commits": doc["commits"], "as_of_seq": doc["as_of_seq"],
            "as_of_commit_digest": doc["as_of_commit_digest"], "blob_checks": dict(sorted(checks.items()))}


def verify_export(path: str | Path, trusted_checkpoint: dict | None = None) -> dict:
    reasons: list[str] = []
    try:
        doc = _load(path)
    except (H.IngestError, OSError) as e:
        return {"status": "ok", "internal_consistency": "failed", "internal_reasons": [str(e)],
                "checkpoint": "not-checked", "appended_after_checkpoint_unconfirmed": [], "partial": None}
    if doc.get("format") != FORMAT:
        reasons.append(f"format is not {FORMAT}")
    try:
        H._check_chain(bundle_from_export(path))
    except (H.BundleError, KeyError, TypeError) as e:
        reasons.append(str(e))
    blobs = _blob_map(doc)
    for item in doc.get("blob_inventory", []):
        encoded = blobs.get(item["digest"])
        if encoded is None:
            reasons.append(f"blob {item['digest']} missing from the export")
            continue
        try:
            ok = hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest() == item["digest"]
        except ValueError:
            ok = False
        if not ok:
            reasons.append(f"blob {item['digest']} bytes do not match their digest")
    result = {"status": "ok", "internal_consistency": "failed" if reasons else "ok", "internal_reasons": reasons,
              "partial": doc.get("partial"), "as_of_seq": doc.get("as_of_seq"), "context_id": doc.get("context_id"),
              "segment_id": doc.get("segment_id"), "appended_after_checkpoint_unconfirmed": []}
    if trusted_checkpoint is None:
        result["checkpoint"] = "not-provided"
        result["claim"] = ("internal consistency only: without a trusted checkpoint the producer identity and full "
                           "history are unknown")
        return result
    commits = {c["commit"]["seq"]: c for c in doc.get("commits", [])}
    n = trusted_checkpoint["seq"]
    at = commits.get(n)
    if (trusted_checkpoint.get("segment_id") not in (None, doc.get("segment_id")) or at is None
            or at["digest"] != trusted_checkpoint["commit_digest"]):
        result["checkpoint"] = "mismatch"
    else:
        result["checkpoint"] = "matches"
        result["appended_after_checkpoint_unconfirmed"] = sorted(s for s in commits if s > n)
    return result


def import_export(path: str | Path, trusted_checkpoint: dict | None, store_dir: str | Path, *, location: dict,
                  session_id: str) -> tuple[Store, C.CoordinatorState]:
    """Verify, then rebuild a local store with the same commits and digests; anchor on the checkpoint when it matches
    (case N54). A failing export is never imported as a live store."""
    r = verify_export(path, trusted_checkpoint)
    if r["internal_consistency"] != "ok" or r["checkpoint"] == "mismatch":
        raise ImportRefused(f"verify_export: {r['internal_consistency']}, checkpoint {r['checkpoint']}: "
                            f"{r['internal_reasons']}")
    doc = _load(path)
    store = Store(store_dir, location=location)
    if store.head(doc["context_id"]) is not None:
        store.close()
        raise ImportRefused(f"the store already holds context {doc['context_id']}")
    for d, encoded in sorted(_blob_map(doc).items()):
        if store.put_blob(base64.b64decode(encoded)) != d:
            store.close()
            raise ImportRefused(f"blob {d} changed while importing")
    store.insert_verbatim(doc["context_id"], doc["segment_id"], doc["commits"], doc.get("segment_origin"))
    st = C.start_session(store, doc["context_id"], session_id, checkpoint=trusted_checkpoint)
    return store, st
