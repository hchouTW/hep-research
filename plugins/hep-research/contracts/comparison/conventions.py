"""Conventions comparison: the part of the gate that decides whether two conventions blocks
can meet. Unknown or namespaced keys are 'not comparable' unless a mapping is declared (T25).

A mapping is {"key": K, "action": "equivalent" | "transform" | "irrelevant", "justification": str,
              "transformation": str (for transform)}; it is recorded, never inferred.
"""
from __future__ import annotations

from contracts.vocab import Vocabulary


def compare_conventions(a: dict, b: dict, mappings: list | None = None, vocab: Vocabulary | None = None) -> dict:
    vocab = vocab or Vocabulary()
    maps = {m["key"]: m for m in (mappings or [])}
    mismatches, notes, applied = [], [], []
    for key in sorted(set(a) | set(b)):
        core = vocab.has("convention_keys", key)
        in_a, in_b = key in a, key in b
        m = maps.get(key)
        if m and m.get("justification"):
            applied.append(m)
            continue
        if in_a and in_b and a[key] == b[key]:
            continue
        if in_a and in_b:
            mismatches.append({"key": key, "a": a[key], "b": b[key], "reason": "values differ; declare a transform mapping or use a variant"})
        elif core:
            notes.append({"key": key, "reason": f"core key only on side {'a' if in_a else 'b'}; confirm it does not affect the comparison"})
        else:
            mismatches.append({"key": key, "reason": f"{'namespaced' if ':' in key else 'unknown'} key only on side {'a' if in_a else 'b'}; not comparable without a declared mapping"})
    return {"comparable": not mismatches, "mismatches": mismatches, "notes": notes, "mappings_applied": applied}
