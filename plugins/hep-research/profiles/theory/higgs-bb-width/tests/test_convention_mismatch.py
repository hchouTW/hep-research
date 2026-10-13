"""Convention mismatches against theory:higgs-bb-width are reported, not silently reconciled.

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

    def test_pole_mass_scheme_is_a_mismatch(self):
        r = compare_conventions(CONV, variant(renormalization_scheme="on-shell (pole) b mass, MS-bar alpha_s"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["renormalization_scheme"])

    def test_mass_input_at_another_scale_is_a_mismatch(self):
        other = {**CONV, "hbb:mass_input": "mbar_b(M_H) given directly"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "hbb:mass_input")

    def test_expansion_parameter_mismatch_reported_and_sized(self):
        r = compare_conventions(CONV, variant(coupling_normalization="expansion parameter a = alpha_s / (4 pi)"))
        self.assertFalse(r["comparable"])
        s1 = predict.s_coefficients(5, -825.7)[1]
        self.assertGreater(abs(s1 - s1 / 4), 4.0)  # s_1 read as an alpha_s/(4 pi) coefficient is off by 4

    def test_massive_b_treatment_is_a_mismatch(self):
        r = compare_conventions(CONV, variant(mass_approximation="full m_b dependence (beta^3 factor)"))
        self.assertFalse(r["comparable"])

    def test_observable_definition_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "hbb:observable"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "hbb:observable")


if __name__ == "__main__":
    unittest.main()
