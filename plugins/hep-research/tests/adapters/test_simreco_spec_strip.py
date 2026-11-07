"""The strip digitization's error in simreco_spec.py against a direct Monte Carlo of the cluster position, written here
from the sharing model and independent of the formula: linear sharing over w around each strip boundary, a strip below
the threshold fraction dropped, the charge-weighted centre of what remains."""
from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN / "adapters" / "geant4" / "assets"))

import simreco_spec as RS  # noqa: E402


def cluster(u: float, pitch: float, sharing: float, threshold: float) -> float:
    strip = math.floor(u / pitch)
    edge = (strip + 1) * pitch
    near = min(edge - u, u - strip * pitch)
    if near >= sharing / 2:
        return (strip + 0.5) * pitch
    other = strip + 1 if edge - u < u - strip * pitch else strip - 1
    share = 0.5 - near / sharing  # the part of the charge on the other strip
    charges = {strip: 1 - share, other: share}
    kept = {s: q for s, q in charges.items() if q >= threshold}
    total = sum(kept.values())
    return sum((s + 0.5) * pitch * q for s, q in kept.items()) / total


class StripError(unittest.TestCase):
    def test_the_formula_is_the_rms_of_the_cluster(self):
        rng = random.Random(11)
        for pitch, sharing, threshold in ((47.0, 8.0, 0.2), (116.0, 8.0, 0.2), (80.0, 20.0, 0.0), (50.0, 10.0, 0.3), (100.0, 40.0, 0.1)):
            with self.subTest(pitch=pitch, sharing=sharing, threshold=threshold):
                errors = [cluster(u, pitch, sharing, threshold) - u for u in (rng.uniform(0, 100 * pitch) for _ in range(200000))]
                rms = math.sqrt(sum(e * e for e in errors) / len(errors))
                self.assertAlmostEqual(RS.strip_sigma(pitch, sharing, threshold) / rms, 1.0, delta=0.005)

    def test_the_width_before_0_61_was_too_small(self):
        old = math.sqrt((47.0 - 8.0) ** 3 / (12 * 47.0))
        self.assertGreater(RS.strip_sigma(47.0, 8.0, 0.2) / old, 1.10)


if __name__ == "__main__":
    unittest.main()
