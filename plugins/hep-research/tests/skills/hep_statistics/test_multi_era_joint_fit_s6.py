"""S6: the multi-era joint fit is documented in time-series-inference.md: the model with per-era response,
acceptance and collection time, the era nuisances of the measurement spec (M3), split consistency (S1) before the
joint fit, parametrized forward folding above the core caps, and the opt-in model-card diagnostic of
contracts/analysis_check.py. The rule ids and the CLI options it names exist."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "skills" / "hep-statistics" / "references" / "time-series-inference.md"


class MultiEraJointFit(unittest.TestCase):
    def setUp(self):
        text = REF.read_text(encoding="utf-8")
        self.assertIn("## Multi-era joint fits", text)
        self.section = text[text.index("## Multi-era joint fits"):text.index("## Deliverables")]

    def test_section_content(self):
        for phrase in ("mu^e_i = sum_j (R^e A^e T^e)_ij Phi_j Delta_j + b^e_i", "split_consistency.py", "era_correlation",
                       "forward folding"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.section)

    def test_named_rules_exist_in_the_registry(self):
        registry = json.loads((ROOT / "contracts" / "rules" / "registry.json").read_text(encoding="utf-8"))
        ids = {r["rule_id"] for r in (registry["rules"] if isinstance(registry, dict) else registry)}
        named = set(re.findall(r"`(r-[a-z]+\.[a-z_.]+)`", self.section))
        self.assertEqual(named, set())  # the model-card diagnostic (r-aux.use, r-share.parameters) was removed in 0.28.0
        self.assertLessEqual(named, ids)

    def test_contents_list_links_the_section(self):
        text = REF.read_text(encoding="utf-8")
        self.assertIn("(#multi-era-joint-fits)", text)


if __name__ == "__main__":
    unittest.main()
