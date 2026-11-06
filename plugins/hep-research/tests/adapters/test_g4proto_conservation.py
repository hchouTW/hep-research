"""The statistics of the conservation checks (Section 8.9), against values worked out by hand or stated in the plan. No Geant4 here."""
from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "adapters/geant4/tests/g4proto"
sys.path[:0] = [str(FOLDER / "reacquire"), str(FOLDER / "conservation")]
spec = importlib.util.spec_from_file_location("g4proto_conservation", FOLDER / "conservation/conservation.py")
conservation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conservation)


class Bounds(unittest.TestCase):
    def test_the_upper_bound_with_no_success_is_the_rule_of_three(self):
        self.assertAlmostEqual(conservation.upper_bound(0, 3000), 1 - 0.05 ** (1 / 3000), places=9)

    def test_the_quantile_bound_exists_from_2995_events_only(self):
        self.assertIsNone(conservation.order_index(2994))
        self.assertEqual(conservation.order_index(2995), 2995)

    def test_more_events_leave_room_below_the_maximum(self):
        self.assertLess(conservation.order_index(10000), 10000)


class PassProbability(unittest.TestCase):
    def test_a_small_trial_cannot_give_a_valid_design(self):
        """3,000 clean events bound p_max near 0.001, the level tested, so no N reaches 0.9: why the trials are larger."""
        self.assertIsNone(conservation.required_events(conservation.upper_bound(0, 3000), 0.0, 1.0, 1.0, largest=20000))

    def test_a_large_trial_gives_a_design(self):
        needed = conservation.required_events(conservation.upper_bound(0, 30000), 0.0, 1.0, 1.0)
        self.assertGreaterEqual(needed, 2995)
        self.assertGreaterEqual(conservation.pass_probability(needed, conservation.upper_bound(0, 30000), 0.0, 1.0, 1.0), 0.9)


class Fisher(unittest.TestCase):
    def test_a_small_table_worked_by_hand(self):
        """Two exceedances in two runs of two: 1 - C(2,2)/C(4,2) of having at least one in the run under test."""
        self.assertAlmostEqual(conservation.fisher_one_sided(1, 2, 1, 2), 5 / 6, places=9)

    def test_a_huge_excess_rejects(self):
        self.assertLess(conservation.fisher_one_sided(50, 100, 0, 100), 1e-10)

    def test_a_strong_control_needs_few_events(self):
        self.assertLess(conservation.required_relative_events(0.001, 0.99), 20)


class AbsoluteCheck(unittest.TestCase):
    def test_a_correct_sample_passes_and_a_shifted_one_fails(self):
        values = [math.sin(i) * 0.1 for i in range(3000)]
        self.assertTrue(conservation.absolute_passes(values, 1.0, 1.0)[0])
        self.assertFalse(conservation.absolute_passes([value + 2 for value in values], 1.0, 1.0)[0])


if __name__ == "__main__":
    unittest.main()
