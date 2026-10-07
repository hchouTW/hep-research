"""Metadata tests for experiment:eic: registry agreement, resources, budgets, scope wording, conventions."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # the eic profile folder
PLUGIN = ROOT.parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.registry import validate_registry  # noqa: E402

PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
REGISTRY = PLUGIN / "profiles" / "registry.json"
SKILLS = {"hep-analysis", "detector-response", "hep-theory", "hep-statistics", "hep-computing", "physics-ml", "research-communication"}


class IdentityTests(unittest.TestCase):
    def test_identity_and_namespace(self):
        self.assertEqual(PROFILE["id"], "experiment:eic")
        self.assertEqual(PROFILE["kind"], "experiment")
        self.assertEqual(PROFILE["evidence_namespace"], "eic")
        self.assertEqual(PROFILE["vocabulary_namespaces"], ["eic"])
        self.assertNotIn("illustrative", PROFILE)

    def test_registry_has_exactly_one_eic_entry_that_matches(self):
        entries = [e for e in json.loads(REGISTRY.read_text(encoding="utf-8"))["profiles"] if "eic" in e["id"] or "epic" in e["id"]]
        self.assertEqual(len(entries), 1, entries)
        e = entries[0]
        self.assertEqual((e["id"], e["kind"], e["version"], e["path"]), (PROFILE["id"], "experiment", PROFILE["version"], "experiments/eic"))

    def test_budgets(self):
        self.assertLessEqual(REGISTRY.stat().st_size, 2048)
        self.assertLessEqual((ROOT / "index.md").stat().st_size, 4096)

    def test_registry_validator_accepts_the_profile(self):
        rep, loaded = validate_registry()
        mine = [f for f in rep.findings if "experiment:eic" in f.path]
        self.assertEqual([f.message for f in mine], [], mine)
        self.assertIn("experiment:eic", loaded)


class ScopeTests(unittest.TestCase):
    def test_facility_and_experiment_are_both_named_and_distinguished(self):
        scope = PROFILE["scope"]
        self.assertIn("Electron-Ion Collider", scope)
        self.assertIn("ePIC", scope)
        self.assertIn("separate", scope.lower())

    def test_exclusions_cover_other_detectors_releases_and_datasets(self):
        text = " ".join(PROFILE["exclusions"]).lower()
        for word in ("detector concept", "release", "dataset", "calibration", "design target"):
            self.assertIn(word, text, word)

    def test_related_skills_are_real_and_no_skill_is_an_entry_point(self):
        self.assertTrue(set(PROFILE["related_skills"]) <= SKILLS)
        self.assertIn("never an entry point", (ROOT / "index.md").read_text(encoding="utf-8"))

    def test_capabilities_are_honest(self):
        by_name = {c["name"]: c for c in PROFILE["capabilities"]}
        self.assertEqual(by_name["facility-and-detector-context"]["status"], "documented")
        self.assertEqual(by_name["software-execution"]["status"], "unavailable")
        self.assertRegex(by_name["software-execution"]["scope"].lower(), r"\b(no|not|nothing)\b")
        for cap in PROFILE["capabilities"]:
            if cap["status"] in ("demonstrated-on-synthetic-data", "tested-in-declared-environment"):
                for t in cap["tests"]:
                    self.assertTrue((ROOT / t).exists(), (cap["name"], t))


class ConventionTests(unittest.TestCase):
    CONV = json.loads((ROOT / "conventions.json").read_text(encoding="utf-8"))

    def test_keys_are_core_or_namespaced(self):
        core = {"unit_system", "energy_variable", "frame"}
        for k in self.CONV:
            self.assertTrue(k in core or k.startswith("eic:"), k)
        self.assertEqual(sorted(k for k in self.CONV if k.startswith("eic:")), sorted(PROFILE["vocabulary_extensions"]["conventions"]))

    def test_lab_and_cm_frames_are_not_identified(self):
        frame = self.CONV["frame"].lower()
        self.assertIn("asymmetric", frame)
        self.assertIn("differ", frame)
        self.assertNotIn("lab = cm", frame)

    def test_unknown_conventions_say_so(self):
        for k in ("eic:hadron_beam_direction", "eic:polarization_sign"):
            self.assertIn("unknown", self.CONV[k].lower(), k)
            self.assertIn("not fix", self.CONV[k].lower(), k)

    def test_per_nucleon_convention_is_explicit(self):
        self.assertIn("per nucleon", self.CONV["eic:ion_energy_normalization"].lower())


if __name__ == "__main__":
    unittest.main()
