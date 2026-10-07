"""Seeded mutations of JSON documents for robustness tests: type swaps, nulls, lists in place of scalars, deleted
keys. Shared by tests/contracts/test_robustness.py (artifacts, gate plans) and tests/core (ledgers)."""
from __future__ import annotations

import copy
import random

REPLACEMENTS = (None, 0, -1, 1.5, float("nan"), float("inf"), "", "x", [], [None], {}, {"a": 1}, True, [1, 2], [{}])


def paths(doc, prefix=()):
    """Every path to a node below the root, depth first."""
    if isinstance(doc, dict):
        for k, v in doc.items():
            yield prefix + (k,)
            yield from paths(v, prefix + (k,))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield prefix + (i,)
            yield from paths(v, prefix + (i,))


def _parent(doc, path):
    node = doc
    for key in path[:-1]:
        node = node[key]
    return node


def single_mutations(doc):
    """Each node mutated four ways, one at a time: (description, mutated copy)."""
    for path in list(paths(doc)):
        value = _parent(doc, path)[path[-1]]
        swapped = "x" if not isinstance(value, str) else 7
        for kind, new in (("null", None), ("type-swap", swapped), ("list-wrap", [value]), ("delete", None)):
            out = copy.deepcopy(doc)
            parent = _parent(out, path)
            if kind == "delete":
                if isinstance(parent, dict):
                    del parent[path[-1]]
                else:
                    parent.pop(path[-1])
            else:
                parent[path[-1]] = copy.deepcopy(new)
            yield f"{kind} at {'.'.join(map(str, path))}", out


def random_mutation(doc, rng: random.Random, count: int = 1):
    """`count` random mutations of a copy of doc (a replacement from REPLACEMENTS, a list wrap or a deletion)."""
    doc = copy.deepcopy(doc)
    for _ in range(count):
        ps = list(paths(doc))
        if not ps:
            return copy.deepcopy(rng.choice(REPLACEMENTS))
        path = rng.choice(ps)
        parent = _parent(doc, path)
        op = rng.random()
        if op < 0.25 and isinstance(parent, dict):
            del parent[path[-1]]
        elif op < 0.35 and isinstance(parent, list):
            parent.pop(path[-1])
        elif op < 0.5:
            parent[path[-1]] = [parent[path[-1]]]
        else:
            parent[path[-1]] = copy.deepcopy(rng.choice(REPLACEMENTS))
    return doc
