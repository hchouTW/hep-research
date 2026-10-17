"""M4 (gate G4): a measurement-spec may declare coupled backgrounds, `coupled_backgrounds: [{background, species,
treatment, source}]`: a background that is another species measured at the same time. review_measurement_spec.py
warns with coupled.fixed_subtraction when such a background is subtracted as a fixed amount; joint-fit and iterative
treatments do not warn; specs without the field get the same review as before. correction-chain.md and
backgrounds.md describe the coupled treatment. All specs are SYNTHETIC."""
import copy
import glob
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-measurement" / "scripts"))
from contracts.validate import validate_artifact  # noqa: E402
import review_measurement_spec as rms  # noqa: E402

SPEC = ROOT / "skills" / "hep-measurement" / "assets" / "worked-spec.cosmic-ray.synthetic.json"


def coupled_spec(treatment):
    doc = json.loads(SPEC.read_text(encoding="utf-8"))
    ext = doc["extension"]
    bkg = ext["backgrounds"][0]["name"]
    ext["coupled_backgrounds"] = [{"background": bkg, "species": "heavier nucleus (measured in the same data)",
                                   "treatment": treatment, "source": "SYNTHETIC: fragmentation above the detector"}]
    return doc


def codes(review):
    return {d["code"] for d in review["defects"]} | {w["code"] for w in review["warnings"]}


class CoupledBackgrounds(unittest.TestCase):
    def test_field_validates_without_unknown_keys(self):
        rep = validate_artifact(coupled_spec("joint-fit"))
        self.assertTrue(rep.ok, rep.as_dict())
        self.assertFalse([f for f in rep.as_dict()["findings"] if "unknown_key" in f["code"]])

    def test_unknown_treatment_and_missing_fields_refused(self):
        doc = coupled_spec("guess")
        self.assertFalse(validate_artifact(doc).ok)
        doc = coupled_spec("joint-fit")
        del doc["extension"]["coupled_backgrounds"][0]["source"]
        self.assertFalse(validate_artifact(doc).ok)

    def test_fixed_subtraction_warns(self):
        self.assertIn("coupled.fixed_subtraction", codes(rms.draft(coupled_spec("fixed-subtraction"))))
        for t in ("joint-fit", "iterative"):
            with self.subTest(treatment=t):
                self.assertNotIn("coupled.fixed_subtraction", codes(rms.draft(coupled_spec(t))))

    def test_existing_specs_unchanged(self):
        paths = sorted(glob.glob(str(ROOT / "**" / "*.json"), recursive=True))
        n = 0
        for p in paths:
            try:
                doc = json.loads(Path(p).read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not (isinstance(doc, dict) and doc.get("artifact_type") == "measurement-spec"):
                continue
            if "coupled_backgrounds" in (doc.get("extension") or {}):
                continue  # specs written to declare coupled backgrounds (example E-1) are not "existing" specs
            n += 1
            with self.subTest(spec=p):
                self.assertEqual(rms.draft(copy.deepcopy(doc)), rms.draft(copy.deepcopy(doc), coupled_checks=False))
        self.assertGreater(n, 3)

    def test_documented(self):
        corr = (ROOT / "skills" / "hep-measurement" / "references" / "correction-chain.md").read_text(encoding="utf-8")
        bkg = (ROOT / "skills" / "hep-measurement" / "references" / "backgrounds.md").read_text(encoding="utf-8")
        self.assertIn("## Coupled species", bkg)
        self.assertIn("coupled.fixed_subtraction", bkg)
        self.assertIn("Coupled species", corr)


if __name__ == "__main__":
    unittest.main()
