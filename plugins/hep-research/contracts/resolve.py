"""Name resolution shared by the loaders and checkers (v6.3 C13): namespace owners and the alias contract.

Namespace owners: every namespace a loaded profile declares (contracts.vocab.declared_namespaces) has exactly one
owner in the visible closure; namespace_owners returns the owners and every collision (profile.namespace_collision).
Unprefixed (base) terms belong to the owner "core".

Alias contract: an alias is a reviewed equivalence, a record
  {"owner", "vocabulary", "alias", "target", "rationale", "versions", "introduced", "retire_not_before"}
(owner: the profile id, or "core"; versions: the owner versions it applies to; retire_not_before: a version or null).
check_aliases reports, as findings {"code", "alias", "message"}: a malformed record (alias.bad_record); a vocabulary or
target that does not exist (alias.target_missing); an alias name in a namespace its owner does not own, or a base term
aliased by anyone but core (alias.cross_owner); one alias with two targets (alias.ambiguous); a cycle (alias.cycle); a
record that carries a conversion: a numeric conversion is a comparison mapping, never an alias (alias.needs_conversion).

canonical_term follows aliases to the canonical term; canonicalize_keys builds the canonical, in-memory view of a
mapping whose keys may be aliases: old and new keys merge only when their values are equal, and a conflict rejects the
view while keeping both sources (alias.key_conflict). Inputs are never modified. Standard library only.
"""
from __future__ import annotations

from contracts.vocab import NAMESPACED, Vocabulary, declared_namespaces

CORE_OWNER = "core"
ALIAS_REQUIRED = ("owner", "vocabulary", "alias", "target", "rationale", "versions", "introduced", "retire_not_before")


def namespace_owners(profiles) -> tuple[dict[str, str], list[dict]]:
    """({namespace: owner profile id}, collisions [{"namespace", "owners": [ids]}]) over loaded profile dicts."""
    seen: dict[str, list[str]] = {}
    for p in profiles:
        pid = p.get("id")
        for ns in declared_namespaces(p):
            if isinstance(ns, str) and pid not in seen.setdefault(ns, []):
                seen[ns].append(pid)
    owners = {ns: ids[0] for ns, ids in seen.items() if len(ids) == 1}
    collisions = [{"namespace": ns, "owners": ids} for ns, ids in sorted(seen.items()) if len(ids) > 1]
    return owners, collisions


def owner_of(term: str, owners: dict[str, str]) -> str | None:
    """The owner of a term: core for a base term, the namespace owner for '<ns>:<x>', None when unknown."""
    m = NAMESPACED.match(term)
    return owners.get(m.group(1)) if m else CORE_OWNER


def _well_formed(rec) -> bool:
    return (isinstance(rec, dict) and all(k in rec for k in ALIAS_REQUIRED)
            and all(isinstance(rec[k], str) and rec[k] for k in ALIAS_REQUIRED if k != "retire_not_before")
            and (rec["retire_not_before"] is None or isinstance(rec["retire_not_before"], str)))


def _f(code: str, rec, message: str) -> dict:
    return {"code": code, "alias": rec.get("alias") if isinstance(rec, dict) else None, "message": message}


def check_aliases(aliases, owners: dict[str, str], vocab: Vocabulary) -> list[dict]:
    out: list[dict] = []
    good = []
    for rec in aliases:
        if not _well_formed(rec):
            out.append(_f("alias.bad_record", rec, f"an alias record needs {list(ALIAS_REQUIRED)}"))
            continue
        if "conversion" in rec:
            out.append(_f("alias.needs_conversion", rec, "a value needing conversion is a comparison mapping, not an alias"))
        if rec["vocabulary"] not in vocab.names() or not vocab.has(rec["vocabulary"], rec["target"]):
            out.append(_f("alias.target_missing", rec, f"'{rec['target']}' is not a {rec['vocabulary']} term"))
        if owner_of(rec["alias"], owners) != rec["owner"]:
            out.append(_f("alias.cross_owner", rec, f"'{rec['alias']}' belongs to {owner_of(rec['alias'], owners)!r}, "
                                                    f"not {rec['owner']!r}: only the owner of a name may alias it"))
        good.append(rec)
    targets: dict[tuple[str, str], set[str]] = {}
    for rec in good:
        targets.setdefault((rec["vocabulary"], rec["alias"]), set()).add(rec["target"])
    for (voc, name), ts in sorted(targets.items()):
        if len(ts) > 1:
            out.append({"code": "alias.ambiguous", "alias": name, "message": f"{voc} alias '{name}' has targets {sorted(ts)}"})
    edges = {k: next(iter(ts)) for k, ts in targets.items() if len(ts) == 1}
    reported: set[frozenset] = set()
    for (voc, start) in sorted(edges):
        path, cur = [start], edges[(voc, start)]
        while (voc, cur) in edges and cur not in path:
            path.append(cur)
            cur = edges[(voc, cur)]
        if cur in path and frozenset(path) not in reported:
            reported.add(frozenset(path))
            out.append({"code": "alias.cycle", "alias": start, "message": f"{voc} alias cycle: " + " -> ".join(path + [cur])})
    return out


def canonical_term(term: str, vocabulary: str, aliases) -> str:
    """The term reached by following aliases (stops at a repeat: cycles are check_aliases findings)."""
    edges = {r["alias"]: r["target"] for r in aliases if _well_formed(r) and r["vocabulary"] == vocabulary}
    seen = {term}
    while term in edges and edges[term] not in seen:
        term = edges[term]
        seen.add(term)
    return term


def canonicalize_keys(mapping: dict, vocabulary: str, aliases) -> dict:
    """{"status": "ok"|"rejected", "view", "sources": {canonical key: [original keys]}, "findings"}; never mutates."""
    groups: dict[str, list[str]] = {}
    for key in mapping:
        groups.setdefault(canonical_term(key, vocabulary, aliases), []).append(key)
    view, findings = {}, []
    for canon, keys in groups.items():
        values = [mapping[k] for k in keys]
        if any(v != values[0] for v in values[1:]):
            findings.append({"code": "alias.key_conflict", "key": canon, "sources": {k: mapping[k] for k in sorted(keys)},
                             "message": f"{sorted(keys)} name the same key '{canon}' with different values"})
        else:
            view[canon] = values[0]
    sources = {c: sorted(ks) for c, ks in groups.items()}
    if findings:
        return {"status": "rejected", "view": None, "sources": sources, "findings": findings}
    return {"status": "ok", "view": view, "sources": sources, "findings": []}
