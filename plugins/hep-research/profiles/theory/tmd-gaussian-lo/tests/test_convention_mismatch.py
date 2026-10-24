"""Convention mismatches against theory:tmd-gaussian-lo are reported, not silently reconciled.

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

    def test_fragmentation_width_convention_mismatch_reported_and_sized(self):
        """Reading a Bacchetta-convention <k_T^2> as Anselmino's <p_perp^2> forgets a factor z^2 in the width."""
        other = variant(**{"tmdg:fragmentation_normalization": "D(z, k_T) with int d^2k_T D = D(z), width <k_T^2>"})
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["tmdg:fragmentation_normalization"])
        z, k2, kt2 = 0.4, 0.25, 0.20 / 0.4 ** 2
        right = predict.pt2_width(z, k2, z * z * kt2)
        wrong = predict.pt2_width(z, k2, kt2)
        self.assertGreater(wrong / right, 2.0)

    def test_sivers_sign_convention_mismatch_reported(self):
        r = compare_conventions(CONV, variant(polarization_convention="Sivers function with the Drell-Yan Wilson line"))
        self.assertFalse(r["comparable"])

    def test_azimuth_convention_mismatch_reported(self):
        r = compare_conventions(CONV, variant(azimuth_convention="phi_h measured in the lab frame"))
        self.assertFalse(r["comparable"])

    def test_ansatz_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "tmdg:gaussian_ansatz"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "tmdg:gaussian_ansatz")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(exchanged_bosons="one-photon exchange")
        mapping = [{"key": "exchanged_bosons", "action": "equivalent",
                    "justification": "test input: same content, shorter wording"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
