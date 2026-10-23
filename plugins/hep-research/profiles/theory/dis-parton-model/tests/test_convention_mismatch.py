"""Convention mismatches against theory:dis-parton-model are reported, not silently reconciled.

The variant conventions below are constructed test inputs, not sourced results.
"""
import json
import sys
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
sys.path.insert(0, str(ROOT / "scripts"))
from contracts.comparison.conventions import compare_conventions  # noqa: E402
import predict  # noqa: E402

CONV = json.loads((ROOT / "conventions.json").read_text(encoding="utf-8"))
CFG = predict.load_json(predict.DEFAULT_CONFIG)


def variant(**changes):
    out = dict(CONV)
    out.update(changes)
    return out


class ConventionMismatchTests(unittest.TestCase):
    def test_identical_conventions_comparable(self):
        self.assertTrue(compare_conventions(CONV, dict(CONV))["comparable"])

    @unittest.skipUnless(find_spec("scipy"), "scipy is required")
    def test_expansion_parameter_mismatch_reported_and_sized(self):
        r = compare_conventions(CONV, variant(coupling_normalization="expansion parameter a = alpha_s / pi"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["coupling_normalization"])
        # reading the coefficients as alpha_s/pi coefficients would change F_L by a factor 4
        # (alpha_s/pi) c^(1) = 4 (alpha_s/(4 pi)) c^(1): the same F_L code evaluated at 4 alpha_s
        a, b = predict.fl(CFG, 0.1, 0.2), predict.fl(CFG, 0.1, 0.8)
        self.assertAlmostEqual(b / a, 4.0, places=12)

    def test_momentum_density_mismatch_reported(self):
        r = compare_conventions(CONV, variant(**{"dispm:parton_densities": "momentum densities x f(x)"}))
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "dispm:parton_densities")

    def test_exchanged_boson_mismatch_reported(self):
        r = compare_conventions(CONV, variant(exchanged_bosons="photon + Z with interference"))
        self.assertFalse(r["comparable"])

    def test_heavy_quark_scheme_mismatch_reported(self):
        r = compare_conventions(CONV, variant(heavy_quark_scheme="FFNS with n_f = 3, charm massive"))
        self.assertFalse(r["comparable"])

    def test_target_mass_mismatch_reported(self):
        r = compare_conventions(CONV, variant(target_mass_treatment="target-mass corrections included"))
        self.assertFalse(r["comparable"])

    def test_observable_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if k != "dispm:observable"}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "dispm:observable")

    def test_mapping_with_justification_makes_it_comparable(self):
        other = variant(scales="mu_R = mu_F = Q")
        mapping = [{"key": "scales", "action": "equivalent",
                    "justification": "test input: same scale choice, the toy alpha_s note dropped"}]
        self.assertTrue(compare_conventions(CONV, other, mapping)["comparable"])


if __name__ == "__main__":
    unittest.main()
