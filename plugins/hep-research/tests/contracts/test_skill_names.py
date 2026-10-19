"""Skill names under contracts 3.0.0 (contracts.skill_names): the schema enum is the eight current names; a name retired
in hep-research 0.17.0 is an error, skill.unknown_name, that points to migration with 0.16.x, in an artifact and in a
profile's related_skills, with or without --strict-versions; any unknown handoff.to_skill is the same error. The retired
names are built from parts here, so the maintained tree never spells them (tools/check_retired_names.py)."""
import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import registry, skill_names, validate  # noqa: E402

RETIRED = ["-".join(parts) for parts in (("hep", "analysis"), ("detector", "response"), ("research", "communication"),
                                         ("physics", "ml"), ("hep", "communication"))]
FIXTURE = ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "response.json"
REG = ROOT / "contracts" / "fixtures" / "registry"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def errors(rep, code=skill_names.CODE):
    return {f.path: f.message for f in rep.findings if f.code == code and f.severity == "error"}


class NameTests(unittest.TestCase):
    def test_schema_enum_is_the_current_skills(self):
        enum = load(ROOT / "contracts" / "schemas" / "skill_names.json")["$defs"]["skill_name"]["enum"]
        self.assertEqual(enum, list(skill_names.SKILLS))
        self.assertEqual(validate.KNOWN_SKILLS, frozenset(skill_names.SKILLS))

    def test_hashes_are_the_retired_names(self):
        self.assertEqual(skill_names.RETIRED_SHA256, {hashlib.sha256(n.encode()).hexdigest() for n in RETIRED})
        self.assertTrue(all(skill_names.is_retired(n) for n in RETIRED))
        self.assertFalse(any(skill_names.is_retired(n) for n in skill_names.SKILLS))
        self.assertFalse(skill_names.is_retired(None))


class ArtifactTests(unittest.TestCase):
    def doc(self, producer="hep-detector", to_skill="hep-statistics"):
        doc = load(FIXTURE)
        doc["provenance"]["producer_skill"] = producer
        doc["handoff"] = {"to_skill": to_skill, "artifact_path": "x.json"}
        return doc

    def test_current_names_are_clean(self):
        rep = validate.validate_artifact(self.doc(), strict_versions=True)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings if f.severity == "error"])
        self.assertEqual(errors(rep), {})

    def test_every_retired_name_is_an_error_pointing_to_0_16(self):
        for old in RETIRED:
            for strict in (False, True):
                rep = validate.validate_artifact(self.doc(old, old), strict_versions=strict)
                self.assertFalse(rep.ok)
                msgs = errors(rep)
                self.assertEqual(set(msgs), {"$.provenance.producer_skill", "$.handoff.to_skill"}, old)
                self.assertTrue(all("hep-research 0.16.x" in m for m in msgs.values()), msgs)

    def test_unknown_to_skill_is_an_error(self):
        rep = validate.validate_artifact(self.doc(to_skill="hep-bogus"))
        self.assertIn("not a skill of this plugin", errors(rep)["$.handoff.to_skill"])

    def test_unknown_producer_is_left_to_the_schema(self):
        rep = validate.validate_artifact(self.doc(producer="hep-bogus"))
        self.assertEqual(errors(rep), {})
        self.assertIn("$.provenance.producer_skill", errors(rep, "schema.enum"))


class ProfileTests(unittest.TestCase):
    def _registry(self, names, strict=False):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "pkg"
            shutil.copytree(REG / "valid", pkg)
            pj = pkg / "profiles" / "experiments" / "a" / "profile.json"
            prof = load(pj)
            prof["related_skills"] = names
            pj.write_text(json.dumps(prof), encoding="utf-8")
            rep, _ = registry.validate_registry(pkg / "profiles" / "registry.json", strict_versions=strict)
            with contextlib.redirect_stdout(io.StringIO()):
                code = registry.main(["--registry", str(pkg / "profiles" / "registry.json")])
        return rep, code

    def test_retired_related_skill_is_an_error(self):
        rep, code = self._registry(["hep-computing", RETIRED[0]])
        self.assertIn("hep-research 0.16.x", "".join(errors(rep).values()))
        self.assertEqual(code, 1)

    def test_current_related_skills_clean(self):
        rep, code = self._registry(["hep-measurement", "hep-detector"], True)
        self.assertTrue(rep.ok and not rep.findings, [f.as_dict() for f in rep.findings])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
