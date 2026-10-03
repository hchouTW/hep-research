"""S09 static routing checks: physics-ml hands the inferential validity of ML-based results to hep-statistics, and
hep-statistics hands training to physics-ml; the hep-statistics SKILL.md links ml-assisted-inference.md; routing case
ml-neighbor-1 still expects hep-statistics. Reads files only; nothing is executed."""
import json
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
SKILLS = PLUGIN / "skills"
REF = SKILLS / "hep-statistics/references/ml-assisted-inference.md"


class MlInferenceRouting(unittest.TestCase):
    def test_reference_exists_and_is_linked_from_skill(self):
        self.assertTrue(REF.is_file())
        self.assertIn("](references/ml-assisted-inference.md)", (SKILLS / "hep-statistics/SKILL.md").read_text(encoding="utf-8"))

    def test_physics_ml_points_validity_to_hep_statistics(self):
        t = (SKILLS / "physics-ml/references/scientific-machine-learning.md").read_text(encoding="utf-8")
        self.assertRegex(t, r"statistically valid[^`]*`hep-statistics` work")
        self.assertIn("../../hep-statistics/references/ml-assisted-inference.md", t)

    def test_hep_statistics_points_training_to_physics_ml(self):
        head = REF.read_text(encoding="utf-8")[:900]
        self.assertRegex(head, r"Training[^.]*belong to `physics-ml`")
        self.assertIn("../../physics-ml/references/scientific-machine-learning.md", head)

    def test_links_resolve(self):
        for p in (REF, SKILLS / "physics-ml/references/scientific-machine-learning.md"):
            for link in re.findall(r"\]\(([^)#]+\.md)\)", p.read_text(encoding="utf-8")):
                self.assertTrue((p.parent / link).resolve().is_file(), f"{p.name}: {link}")

    def test_ml_neighbor_case_routes_to_hep_statistics(self):
        cases = {c["id"]: c for c in json.loads((PLUGIN / "tests/routing/cases.json").read_text(encoding="utf-8"))["cases"]}
        self.assertEqual(cases["ml-neighbor-1"]["expected_primary"], "hep-statistics")

    def test_no_training_code_added(self):
        self.assertFalse(any((SKILLS / "hep-statistics/scripts").glob("*train*")))


if __name__ == "__main__":
    unittest.main()
