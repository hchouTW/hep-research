"""Convention mismatches against theory:drell-yan-lo are reported, not silently reconciled.

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

    def test_frame_mismatch_reported(self):
        r = compare_conventions(CONV, variant(frame="helicity frame (z along the dilepton momentum)"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["frame"])

    def test_nu_normalization_mismatch_reported_and_sized(self):
        """A distribution written with nu (not nu/2) in front of sin^2 cos 2phi doubles the quoted nu."""
        other = variant(**{"dylo:angular_distribution": "1 + lambda cos^2 + mu sin 2theta cos phi + nu sin^2 cos 2phi"})
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        nu = predict.channel_coefficients("qqbar", 1.0)["nu"]
        self.assertAlmostEqual(nu, 0.4, places=15)  # 2/(2 + 3)
        self.assertGreater(abs(nu - nu / 2), 0.1)

    def test_exchanged_boson_mismatch_reported(self):
        r = compare_conventions(CONV, variant(exchanged_bosons="photon + Z with interference"))
        self.assertFalse(r["comparable"])

    def test_rapidity_frame_mismatch_reported(self):
        r = compare_conventions(CONV, variant(rapidity_frame="lab frame, +z along the beam"))
        self.assertFalse(r["comparable"])

    def test_mixture_rule_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "dylo:channel_mixture"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "dylo:channel_mixture")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(azimuth_convention="Collins-Soper phi of the negative lepton")
        mapping = [{"key": "azimuth_convention", "action": "equivalent",
                    "justification": "test input: same convention, shorter wording"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
