"""Evidence contract: namespacing rule and record validation (ledger tooling lives in core/evidence, M2).

Rule: every evidence ID is '<namespace>:<local>' where <namespace> is the owning profile's
evidence_namespace (or 'user' / 'private-<name>' for project-local evidence). The same local
ID in two namespaces names two different records; correlations between them need an explicit mapping.
"""
from __future__ import annotations

from contracts.schema import Report, validate
from contracts.vocab import NAMESPACED, Vocabulary

STRENGTH = {"not-verified": 0, "not-opened": 0, "metadata-only": 1, "abstract+metadata": 2, "page": 2, "full-text": 3}


def namespace_of(evidence_id: str) -> str | None:
    m = NAMESPACED.match(evidence_id)
    return m.group(1) if m else None


def validate_ledger(sources: list, claims: list, namespace: str) -> Report:
    rep, vocab = Report(), Vocabulary()
    by_id = {}
    for i, s in enumerate(sources):
        validate(s, "evidence_source.json", vocab, rep, f"sources[{i}]")
        sid = s.get("id", "")
        if namespace_of(sid) != namespace:
            rep.add("error", f"sources[{i}].id", "evidence.namespace", f"'{sid}' is not in namespace '{namespace}'")
        if sid in by_id:
            rep.add("error", f"sources[{i}].id", "evidence.duplicate_id", f"duplicate '{sid}'")
        by_id[sid] = s
    seen = set()
    for i, c in enumerate(claims):
        validate(c, "evidence_claim.json", vocab, rep, f"claims[{i}]")
        cid = c.get("id", "")
        if namespace_of(cid) != namespace:
            rep.add("error", f"claims[{i}].id", "evidence.namespace", f"'{cid}' is not in namespace '{namespace}'")
        if cid in seen:
            rep.add("error", f"claims[{i}].id", "evidence.duplicate_id", f"duplicate '{cid}'")
        seen.add(cid)
        local = [by_id[s] for s in c.get("source_ids", []) if s in by_id]
        for s in c.get("source_ids", []):
            if s not in by_id and namespace_of(s) == namespace:
                rep.add("error", f"claims[{i}].source_ids", "evidence.dangling_source", f"'{s}' not in ledger")
        if local:
            best = max(STRENGTH.get(s.get("verification_level"), 0) for s in local)
            if STRENGTH.get(c.get("verification_strength"), 0) > best:
                rep.add("error", f"claims[{i}].verification_strength", "evidence.over_strong",
                        "claim strength exceeds the best supporting source's verification level")
    return rep
