"""LCS mapping of the independent review (spec 4.2, acceptance criterion 7): on 500 random sequences of length at most
7 over at most 3 symbols, the mapping equals brute-force enumeration under the tie-break (old positions first, then
new positions)."""
from __future__ import annotations

import itertools
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-authoring" / "scripts"))

from review_lib.units import lcs_pairs, map_units  # noqa: E402


def brute(a, b):
    for k in range(min(len(a), len(b)), -1, -1):
        cands = [(old, new) for old in itertools.combinations(range(len(a)), k)
                 for new in itertools.combinations(range(len(b)), k) if all(a[i] == b[j] for i, j in zip(old, new))]
        if cands:
            old, new = min(cands)  # old positions first, then new positions
            return list(zip(old, new))
    return []


class LcsTests(unittest.TestCase):
    def test_tie_break_example(self):
        self.assertEqual(lcs_pairs(["a"], ["a", "a"]), [(0, 0)])

    def test_matches_brute_force(self):
        r = random.Random(20261021)
        for _ in range(500):
            sym = "abc"[:r.randint(1, 3)]
            a = [r.choice(sym) for _ in range(r.randint(0, 7))]
            b = [r.choice(sym) for _ in range(r.randint(0, 7))]
            with self.subTest(a=a, b=b):
                self.assertEqual(lcs_pairs(a, b), brute(a, b))

    def test_mapping_classes(self):
        u = lambda ids, texts: [{"id": i, "text_sha256": t} for i, t in zip(ids, texts)]  # noqa: E731
        old = u(["U0001", "U0002", "U0003", "U0004"], ["h", "x", "k", "y"])
        new = u(["U0001", "U0002", "U0003", "U0004"], ["n", "h", "x2", "k"])
        m = map_units(old, new)
        self.assertEqual(m["unchanged"], [["U0001", "U0002"], ["U0003", "U0004"]])
        self.assertEqual(m["changed"], [["U0002", "U0003"]])
        self.assertEqual(m["added"], ["U0001"])
        self.assertEqual(m["removed"], ["U0004"])


if __name__ == "__main__":
    unittest.main()
