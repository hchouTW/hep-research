"""M5: a measurement-spec systematic may carry an optional `scaling` class (statistical-like, floor, mixed) that says
how its size falls with the control-sample size N_ctrl (sigma proportional to 1/sqrt(N_ctrl); constant; sigma^2 =
a^2 + b^2/N_ctrl). The field is optional, so specs without it stay valid, and the vocabulary is closed. Before M5
the schema had no `scaling` property, so an unknown value was not refused."""
import copy
import json
import unittest
from pathlib import Path

from contracts.validate import validate_artifact

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "skills" / "hep-measurement" / "assets" / "worked-spec.cosmic-ray.synthetic.json"


class SystematicsScaling(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(SPEC.read_text())
        self.assertTrue(self.doc["extension"]["systematics"])

    def _with(self, value):
        doc = copy.deepcopy(self.doc)
        doc["extension"]["systematics"][0]["scaling"] = value
        return validate_artifact(doc)

    def test_spec_without_scaling_still_validates(self):
        self.assertTrue(validate_artifact(self.doc).ok)

    def test_each_scaling_class_validates(self):
        for value in ("statistical-like", "floor", "mixed"):
            with self.subTest(value=value):
                rep = self._with(value)
                self.assertTrue(rep.ok, rep.as_dict())

    def test_unknown_scaling_class_is_refused(self):
        rep = self._with("sqrt-n")
        self.assertFalse(rep.ok)
        self.assertTrue([f for f in rep.as_dict()["findings"] if "scaling" in json.dumps(f)], rep.as_dict())

    def test_systematics_reference_defines_the_classes(self):
        text = (ROOT / "skills/hep-measurement/references/systematics.md").read_text()
        for value in ("`statistical-like`", "`floor`", "`mixed`", "N_ctrl"):
            self.assertIn(value, text)


if __name__ == "__main__":
    unittest.main()
