"""Convention mismatches against theory:heliospheric-modulation are reported, not silently reconciled.

The variant conventions below are constructed test inputs, not sourced results.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
sys.path.insert(0, str(ROOT / "scripts"))
from contracts.comparison.conventions import compare_conventions  # noqa: E402
import predict  # noqa: E402

CONV = json.loads((ROOT / "conventions.json").read_text(encoding="utf-8"))


def variant(**changes):
    out = dict(CONV)
    out.update(changes)
    return out


class ConventionMismatchTests(unittest.TestCase):
    def test_identical_conventions_comparable(self):
        self.assertTrue(compare_conventions(CONV, dict(CONV))["comparable"])

    def test_energy_variable_mismatch_reported_and_sized(self):
        other = variant(energy_variable="kinetic energy per nucleon with shift |Z| phi (not |Z|/A)")
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["energy_variable"])
        # applying |Z| phi instead of (|Z|/A) phi per nucleon changes a helium flux at 1 GeV/n by far more than 10%
        right = predict.closed_form("Ek_per_nucleon", 1.0, 3.7273794, 2, 0.6, 1.0, 2.7, 4)
        wrong = predict.closed_form("Ek_per_nucleon", 1.0, 3.7273794, 2, 0.6 * 4, 1.0, 2.7, 4)
        self.assertGreater(abs(wrong - right) / right, 0.1)

    def test_modulation_model_mismatch_reported(self):
        r = compare_conventions(CONV, variant(**{"helmod:modulation_model": "numerical 2D model with drifts"}))
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "helmod:modulation_model")

    def test_phi_unit_mismatch_reported(self):
        r = compare_conventions(CONV, variant(unit_system="SI; phi in MV"))
        self.assertFalse(r["comparable"])

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(unit_system="natural-HEP; phi in MV")
        mapping = [{"key": "unit_system", "action": "equivalent",
                    "justification": "test input: phi converted from MV to GV before comparison"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
