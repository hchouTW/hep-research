"""Convention mismatches against theory:cr-secondary-ratio are reported, not silently reconciled.

The variant conventions below are constructed test inputs, not sourced results."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from contracts.comparison.conventions import compare_conventions  # noqa: E402

CONV = json.loads((ROOT / "conventions.json").read_text(encoding="utf-8"))


def variant(**changes):
    out = dict(CONV)
    out.update(changes)
    return out


class ConventionMismatchTests(unittest.TestCase):
    def test_identical_conventions_comparable(self):
        self.assertTrue(compare_conventions(CONV, dict(CONV))["comparable"])

    def test_rigidity_energy_variable_is_a_mismatch(self):
        r = compare_conventions(CONV, variant(energy_variable="rigidity R in GV"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["energy_variable"])

    def test_bin_average_definition_mismatch(self):
        other = variant(**{"crsr:bin_average": "ratio of bin-averaged fluxes"})
        self.assertFalse(compare_conventions(CONV, other)["comparable"])

    def test_missing_observable_definition_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "crsr:observable"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "crsr:observable")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(mass_approximation="nuclear masses from a mass table")
        mapping = [{"key": "mass_approximation", "action": "equivalent",
                    "justification": "test input: per-mille mass differences are below the comparison's precision"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
