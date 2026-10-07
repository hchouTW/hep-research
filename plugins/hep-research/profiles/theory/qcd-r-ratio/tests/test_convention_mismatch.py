"""Convention mismatches against theory:qcd-r-ratio are reported, not silently reconciled (T4.4 negative tests).

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
CFG = json.loads((ROOT / "benchmarks" / "r-ratio-15gev.json").read_text(encoding="utf-8"))


def variant(**changes):
    out = dict(CONV)
    out.update(changes)
    return out


class ConventionMismatchTests(unittest.TestCase):
    def test_identical_conventions_comparable(self):
        self.assertTrue(compare_conventions(CONV, dict(CONV))["comparable"])

    def test_expansion_parameter_mismatch_reported_and_sized(self):
        other = variant(coupling_normalization="expansion parameter a = alpha_s / (4 pi)")
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["coupling_normalization"])
        # reading c_2 as an alpha_s/(4 pi) coefficient changes the NNLO term by a factor 1/4
        c2 = predict.c_coefficients(5, 1 / 33)[1]
        self.assertGreater(abs(c2 - c2 / 4), 1.0)

    def test_scheme_mismatch_reported(self):
        r = compare_conventions(CONV, variant(renormalization_scheme="MOM scheme with n_f = 5"))
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "renormalization_scheme")

    def test_scale_choice_mismatch_reported_even_when_numerically_small(self):
        other = variant(scales="renormalization scale mu = 2Q; no envelope")
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        p = predict.predict(CFG)["orders"][4]
        shift = abs(p["scale_envelope"]["three_point"]["2.0"] - p["R_central_mu_eq_Q"])
        self.assertLess(shift, 0.01)  # small at N3LO, yet the gate still blocks without a recorded mapping

    def test_nf_and_mass_treatment_mismatch_reported(self):
        r = compare_conventions(CONV, variant(mass_approximation="b quark massive, n_f = 4 light flavours"))
        self.assertFalse(r["comparable"])

    def test_observable_definition_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "qcdr:observable"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "qcdr:observable")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(scales="renormalization scale mu = Q only")
        mapping = [{"key": "scales", "action": "equivalent",
                    "justification": "test input: only the central value at mu = Q is compared"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
