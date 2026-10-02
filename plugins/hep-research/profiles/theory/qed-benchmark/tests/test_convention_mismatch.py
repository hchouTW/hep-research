"""T13: convention or approximation mismatches against this profile are reported, not silently reconciled.

The variant conventions below are constructed test inputs, not sourced results.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from contracts.compat.conventions import compare_conventions  # noqa: E402

CONV = json.loads((ROOT / "conventions.json").read_text(encoding="utf-8"))
M_MU_GEV = 0.1057  # rounded muon mass, used only to size the effect in this test


def variant(**changes):
    out = dict(CONV)
    out.update(changes)
    return out


class ConventionMismatchTests(unittest.TestCase):
    def test_identical_conventions_comparable(self):
        self.assertTrue(compare_conventions(CONV, dict(CONV))["comparable"])

    def test_coupling_normalization_mismatch_reported(self):
        r = compare_conventions(CONV, variant(coupling_normalization="alpha = e^2 (Gaussian units)"))
        self.assertFalse(r["comparable"])
        self.assertEqual([m["key"] for m in r["mismatches"]], ["coupling_normalization"])

    def test_angle_definition_mismatch_reported(self):
        # theta measured from e+ instead of e- flips cos(theta); harmless for this symmetric
        # tree-level result but the gate still reports it until a mapping says so.
        other = variant(angle_definition="theta between the incoming e+ and the outgoing mu- in the c.m. frame")
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        mapping = [{"key": "angle_definition", "action": "transform", "transformation": "cos(theta) -> -cos(theta)",
                    "justification": "test input: tree-level photon exchange is symmetric in cos(theta) (A_FB = 0, derive.py check)"}]
        r = compare_conventions(CONV, other, mapping)
        self.assertTrue(r["comparable"])
        self.assertEqual(r["mappings_applied"], mapping)

    def test_mass_approximation_mismatch_reported_even_when_numerically_small(self):
        other = variant(mass_approximation="electrons massless; muon mass kept in the numerical prediction")
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        # Size of the effect at the benchmark point: sigma(beta)/sigma(1) = beta (3 - beta^2) / 2.
        sqrt_s = json.loads((ROOT / "benchmarks" / "path-c.json").read_text(encoding="utf-8"))["sqrt_s_gev"]
        beta2 = 1.0 - 4.0 * M_MU_GEV ** 2 / sqrt_s ** 2
        ratio = beta2 ** 0.5 * (3.0 - beta2) / 2.0
        self.assertLess(abs(1.0 - ratio), 1e-6)  # small, yet the gate still blocks without a recorded mapping

    def test_namespaced_key_missing_on_other_side_blocks(self):
        other = {k: v for k, v in CONV.items() if not k.startswith("qedbench:")}
        r = compare_conventions(CONV, other)
        self.assertFalse(r["comparable"])
        self.assertEqual(r["mismatches"][0]["key"], "qedbench:reference_constant")


if __name__ == "__main__":
    unittest.main()
