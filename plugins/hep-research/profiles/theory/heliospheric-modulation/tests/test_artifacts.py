"""theory:heliospheric-modulation theory-spec: validates with contracts/validate.py, is current, keeps its labels,
and is bound to this profile with no experiment."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
SPEC = ROOT / "derivations" / "theory-spec.json"


class ArtifactTests(unittest.TestCase):
    def test_theory_spec_validates(self):
        proc = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(SPEC)],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["findings"], [])

    def test_theory_spec_is_current(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_labels_bindings_and_limits(self):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        self.assertIn("synthetic", spec["status"])
        self.assertNotIn("observed", spec["status"])
        self.assertEqual(spec["bindings"]["experiments"], [])
        ext = spec["extension"]
        self.assertEqual(ext["derivation_status"], "analytic-derivation")
        self.assertTrue(ext["degenerate_directions"])
        self.assertTrue(any("drift" in n for n in ext["neglected"]))

    def test_profile_has_no_experiment_content(self):
        prof = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(prof["depends_on"], [])
        for skill in prof["related_skills"]:
            self.assertTrue(skill.startswith("hep-"))
        text = " ".join(f.read_text(encoding="utf-8") for f in ROOT.rglob("*")
                        if f.is_file() and f.suffix in (".py", ".json", ".md") and "tests" not in f.parts)
        for word in ("profiles/experiments", "blinding\":", "experiment:"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
