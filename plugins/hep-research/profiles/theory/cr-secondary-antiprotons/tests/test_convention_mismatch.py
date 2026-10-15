"""Convention mismatches against theory:cr-secondary-antiprotons are reported, not silently reconciled.

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

    def test_total_energy_variable_is_a_mismatch(self):
        r = compare_conventions(CONV, variant(energy_variable="antiproton total energy E_pbar in GeV"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["energy_variable"])

    def test_antineutron_treatment_mismatch(self):
        other = variant(**{"crpb:antineutrons_hyperons": "prompt antiprotons only, no antineutrons or hyperons"})
        self.assertFalse(compare_conventions(CONV, other)["comparable"])

    def test_missing_source_term_definition_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "crpb:source_term"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "crpb:source_term")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(**{"crpb:ism": "interstellar H and He with n_He / n_H = 0.1 and carbon at 5e-4 of H"})
        mapping = [{"key": "crpb:ism", "action": "equivalent",
                    "justification": "test input: a trace of carbon is below the comparison's precision"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
