"""The sibling check at scale (g4sim S8, Section 16): the spatial hash of overlap._near_pairs must offer every pair of boxes closer than the
minimum gap, which a comparison of all pairs finds, so replacing the sweep along x changes no finding; and a regular grid costs about one
neighbourhood per box, not a plane of them."""
from __future__ import annotations

import random
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import overlap  # noqa: E402
from core.geometry.numbers import MINIMUM_GAP_MM  # noqa: E402


def box(centre: tuple, half: tuple) -> tuple:
    return (tuple(Decimal(c) - Decimal(h) for c, h in zip(centre, half)), tuple(Decimal(c) + Decimal(h) for c, h in zip(centre, half)))


def close_pairs(placed: list) -> set:
    return {(i, j) for i in range(len(placed)) for j in range(i + 1, len(placed)) if overlap._separation(placed[i][0], placed[j][0]) < MINIMUM_GAP_MM}


class NearPairs(unittest.TestCase):
    def test_every_close_pair_is_offered_on_random_layouts(self):
        rng = random.Random(8)
        for trial in range(40):
            placed = []
            for _ in range(rng.randint(2, 60)):
                centre = tuple(f"{rng.uniform(-40, 40):.4f}" for _ in range(3))
                half = tuple(f"{rng.uniform(0.01, 6):.4f}" for _ in range(3))
                placed.append((box(centre, half), {}))
            placed.sort(key=lambda item: item[0][0][0])
            offered = set(overlap._near_pairs(placed))
            self.assertLessEqual(close_pairs(placed), offered, f"trial {trial}")
            self.assertEqual(overlap._near_pairs(placed), sorted(offered))

    def test_boxes_a_gap_apart_and_touching_faces(self):
        gap = MINIMUM_GAP_MM
        placed = [(box(("0", "0", "0"), ("1", "1", "1")), {}), (box((str(Decimal(2) + gap / 2), "0", "0"), ("1", "1", "1")), {}),
                  (box(("0", "2", "0"), ("1", "1", "1")), {})]
        placed.sort(key=lambda item: item[0][0][0])
        self.assertLessEqual(close_pairs(placed), set(overlap._near_pairs(placed)))

    def test_a_regular_grid_offers_its_neighbours_only(self):
        placed = [(box((str(10 * i), str(10 * j), str(10 * k)), ("4.5", "4.5", "4.5")), {}) for i in range(12) for j in range(12) for k in range(12)]
        placed.sort(key=lambda item: item[0][0][0])
        pairs = overlap._near_pairs(placed)
        self.assertLess(len(pairs), 14 * len(placed))  # at most the 26 neighbours, each pair once
        self.assertEqual(close_pairs(placed[:200]) - set(pairs), set())


class FloatPreTest(unittest.TestCase):
    def test_a_pair_closer_than_the_gap_is_never_called_clear(self):
        rng = random.Random(9)
        gap = MINIMUM_GAP_MM
        for _ in range(4000):
            centre = Decimal(f"{rng.uniform(-3e4, 3e4):.6f}")
            half = Decimal(f"{rng.uniform(0.001, 50):.6f}")
            offset = gap * Decimal(rng.choice((-2, -1, 0, 1, 2))) + Decimal(f"{rng.uniform(-1, 1):.9f}") * gap * rng.choice((0, 1))
            a = box((str(centre), "0", "0"), (str(half), "1", "1"))
            b = box((str(centre + 2 * half + offset), "0", "0"), (str(half), "1", "1"))
            exact = overlap._separation(a, b)
            rough = [tuple(tuple(float(v) for v in corner) for corner in item) for item in (a, b)]
            slack = overlap.FLOAT_SLACK * (1.0 + max(abs(v) for item in rough for corner in item for v in corner))
            if overlap._clear_in_floats(rough[0], rough[1], slack):
                self.assertGreaterEqual(exact, gap)


if __name__ == "__main__":
    unittest.main()
