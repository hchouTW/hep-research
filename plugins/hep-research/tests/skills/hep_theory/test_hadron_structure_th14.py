"""Th14 (hadron structure, phase 1): the conditional convention keys and the page format of the new references."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "skills/hep-theory/references"
NEW_KEYS = {"target_normalization", "exchanged_bosons", "electroweak_scheme", "em_coupling", "structure_function_signs",
            "heavy_quark_scheme", "factorization_scheme", "target_mass_treatment", "polarization_convention",
            "xF_definition", "rapidity_frame", "azimuth_convention", "log_accuracy"}


class ConditionalConventionKeys(unittest.TestCase):
    def test_keys_are_core_and_conditional(self):
        voc = json.loads((ROOT / "contracts/vocab/core.json").read_text())["vocabularies"]
        self.assertTrue(NEW_KEYS <= set(voc["convention_keys"]))
        self.assertEqual(set(voc["conditional_convention_keys"]), NEW_KEYS)

    def test_completeness_rule_skips_conditional_keys(self):
        import sys
        sys.path.insert(0, str(ROOT))
        from contracts.validate import _theory_spec_rules  # noqa: E402
        from contracts.vocab import Vocabulary  # noqa: E402

        class Rep:
            def __init__(self):
                self.items = []

            def add(self, severity, path, code, message):
                self.items.append((severity, code, message))

        voc = Vocabulary()
        universal = sorted(voc.core("convention_keys") - NEW_KEYS)
        ext = {"conventions": {k: "x" for k in universal}, "derivation_status": "not-derived", "checks_run": [],
               "validity_domain": {"x": "toy"}}
        rep = Rep()
        _theory_spec_rules(ext, voc, rep)
        self.assertNotIn("theory.conventions_incomplete", [c for _, c, _ in rep.items])
        ext["conventions"].pop("frame")
        rep = Rep()
        _theory_spec_rules(ext, voc, rep)
        msgs = [m for _, c, m in rep.items if c == "theory.conventions_incomplete"]
        self.assertEqual(len(msgs), 1)
        self.assertIn("'frame'", msgs[0])
        self.assertFalse(any(k in msgs[0] for k in NEW_KEYS))


class PageFormat(unittest.TestCase):
    def test_dis_page_status_and_sources(self):
        text = (REF / "dis-structure-functions.md").read_text()
        self.assertRegex(text, r"Status: guidance and one tool \(Th14\), sources read in full text on 2026-10-23")
        self.assertIn("## Sources read (full text, 2026-10-23)", text)
        self.assertIn("Not verified and therefore not used", text)
        flat = " ".join(text.split())
        self.assertIn("are not the substitution x -> xi", flat)
        self.assertIn("F_L^TMC = r^2 F_2^TMC - 2x F_1^TMC", flat)  # review I3: the TMC F_L definition differs

    def test_hub_routes_every_module(self):
        text = (REF / "hadron-structure-essentials.md").read_text()
        rows = re.findall(r"^\| ([A-H]) \|", text, flags=re.M)
        self.assertEqual(rows, list("ABCDEFGH"))
        self.assertIn("(dis-structure-functions.md)", text)
        for key in NEW_KEYS:
            self.assertIn(f"`{key}`", text)


if __name__ == "__main__":
    unittest.main()
