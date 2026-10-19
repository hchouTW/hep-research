"""Deprecated skill-name aliases of the hep-research 0.11.0 rename (contracts 2.9.0, contracts.skill_names).

An artifact or profile written with an old name (hep-analysis, detector-response, research-communication, physics-ml)
still validates, with a deprecation warning; under the version and name policy (--strict-versions) the old name is an
error; contracts/migrate_skill_names.py rewrites provenance.producer_skill and handoff.to_skill, after which the
artifact validates cleanly. This file, contracts/skill_names.py, contracts/schemas/skill_names.json,
contracts/migrate_skill_names.py and contracts/fixtures/skill_aliases/ are the only places that keep the old names."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import migrate_skill_names, registry, skill_names, validate  # noqa: E402

OLD_NEW = {"hep-analysis": "hep-measurement", "detector-response": "hep-detector",
           "research-communication": "hep-authoring", "physics-ml": "hep-ml", "hep-communication": "hep-authoring"}
FIXTURE = ROOT / "contracts" / "fixtures" / "skill_aliases" / "response_old_skill_names.json"
REG = ROOT / "contracts" / "fixtures" / "registry"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def codes(rep, severity):
    return [f.code for f in rep.findings if f.severity == severity]


def run(main, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


class AliasDefinitionTests(unittest.TestCase):
    def test_alias_table(self):
        self.assertEqual(skill_names.DEPRECATED_SKILL_ALIASES, OLD_NEW)
        self.assertEqual(skill_names.RENAMED_IN, "0.11.0")

    def test_current_names_are_the_skill_folders(self):
        folders = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(sorted(skill_names.SKILLS), folders)
        self.assertFalse(set(OLD_NEW) & set(folders))

    def test_schema_enum_matches_module(self):
        enum = load(ROOT / "contracts" / "schemas" / "skill_names.json")["$defs"]["skill_name"]["enum"]
        self.assertEqual(enum, list(skill_names.SKILLS) + list(OLD_NEW))
        for schema, path in (("envelope.json", ("properties", "provenance", "properties", "producer_skill")),
                             ("profile.json", ("properties", "related_skills", "items"))):
            node = load(ROOT / "contracts" / "schemas" / schema)
            for key in path:
                node = node[key]
            self.assertEqual(node, {"$ref": "skill_names.json#/$defs/skill_name"}, schema)

    def test_unknown_name_still_rejected(self):
        doc = load(FIXTURE)
        doc["provenance"]["producer_skill"] = "hep-analysis-ml"
        self.assertIn("schema.enum", codes(validate.validate_artifact(doc), "error"))


class ArtifactAliasTests(unittest.TestCase):
    def test_old_names_warn(self):
        rep = validate.validate_artifact(load(FIXTURE))
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.findings])
        warned = {f.path for f in rep.findings if f.code == skill_names.CODE and f.severity == "warning"}
        self.assertEqual(warned, {"$.provenance.producer_skill", "$.handoff.to_skill"})
        self.assertIn("hep-detector", next(f.message for f in rep.findings if f.path == "$.provenance.producer_skill"))

    def test_old_names_fail_under_strict_versions(self):
        rep = validate.validate_artifact(load(FIXTURE), strict_versions=True)
        self.assertFalse(rep.ok)
        self.assertEqual(codes(rep, "error").count(skill_names.CODE), 2)
        code, text = run(validate.main, [str(FIXTURE), "--strict-versions"])
        self.assertEqual(code, 1, text)
        self.assertIn(skill_names.CODE, text)
        code, text = run(validate.main, [str(FIXTURE)])
        self.assertEqual(code, 0, text)

    def test_migration_then_clean(self):
        new, report = migrate_skill_names.migrate(load(FIXTURE))
        self.assertEqual(report["status"], "migrated")
        self.assertEqual({d["path"] for d in report["diagnostics"]}, {"$.provenance.producer_skill", "$.handoff.to_skill"})
        self.assertEqual(new["provenance"]["producer_skill"], "hep-detector")
        self.assertEqual(new["handoff"]["to_skill"], "hep-measurement")
        self.assertEqual(report["remaining"], [])
        for strict in (False, True):
            rep = validate.validate_artifact(new, strict_versions=strict)
            self.assertTrue(rep.ok and not rep.findings, [f.as_dict() for f in rep.findings])

    def test_migration_rewrites_only_the_two_fields(self):
        old = load(FIXTURE)
        new, _ = migrate_skill_names.migrate(old)
        old["provenance"]["producer_skill"] = new["provenance"]["producer_skill"]
        old["handoff"]["to_skill"] = new["handoff"]["to_skill"]
        self.assertEqual(new, old)

    def test_migration_cli(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "new.json"
            code, text = run(migrate_skill_names.main, [str(FIXTURE), "--out", str(out)])
            self.assertEqual(code, 0, text)
            self.assertEqual(json.loads(text)["status"], "migrated")
            code, text = run(validate.main, [str(out), "--strict-versions"])
            self.assertEqual(code, 0, text)
            code, text = run(migrate_skill_names.main, [str(out)])  # idempotent
            self.assertEqual((code, json.loads(text)["status"]), (0, "unchanged"))
            bad = Path(td) / "bad.json"
            bad.write_text("[1, 2]", encoding="utf-8")
            self.assertEqual(run(migrate_skill_names.main, [str(bad)])[0], 2)
            self.assertEqual(run(migrate_skill_names.main, [str(Path(td) / "missing.json")])[0], 2)
            self.assertEqual(run(migrate_skill_names.main, [str(FIXTURE), "--out"])[0], 2)
        self.assertEqual(run(migrate_skill_names.main, [])[0], 2)

    def test_extension_handoff_alias_warns_and_is_not_migrated(self):
        doc = load(FIXTURE)
        doc["extension"]["note"] = {"handoff": "physics-ml"}
        rep = validate.validate_artifact(doc)
        self.assertIn("$.extension.note.handoff",
                      {f.path for f in rep.findings if f.code == skill_names.CODE and f.severity == "warning"})
        new, report = migrate_skill_names.migrate(doc)
        self.assertEqual(new["extension"]["note"]["handoff"], "physics-ml")
        self.assertIn("$.extension.note.handoff", {r["path"] for r in report["remaining"]})

    def test_old_ml_handoff_is_not_unknown(self):
        self.assertTrue({"physics-ml", "hep-ml"} <= validate.KNOWN_SKILLS)

    def test_split_communication_name_maps_to_hep_authoring(self):
        # the split (contracts 2.13.0): an artifact produced under hep-communication migrates to hep-authoring
        doc = load(FIXTURE)
        doc["provenance"]["producer_skill"] = "hep-communication"
        doc["handoff"]["to_skill"] = "research-communication"
        rep = validate.validate_artifact(doc)
        msgs = {f.path: f.message for f in rep.findings if f.code == skill_names.CODE and f.severity == "warning"}
        self.assertIn("'hep-authoring'", msgs["$.provenance.producer_skill"])
        self.assertIn("after 0.15.0", msgs["$.provenance.producer_skill"])
        self.assertIn("0.11.0", msgs["$.handoff.to_skill"])
        new, report = migrate_skill_names.migrate(doc)
        self.assertEqual((new["provenance"]["producer_skill"], new["handoff"]["to_skill"]), ("hep-authoring", "hep-authoring"))
        self.assertTrue(validate.validate_artifact(new, strict_versions=True).ok)


class ProfileAliasTests(unittest.TestCase):
    def _registry(self, names, strict):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "pkg"
            shutil.copytree(REG / "valid", pkg)
            pj = pkg / "profiles" / "experiments" / "a" / "profile.json"
            prof = load(pj)
            prof["related_skills"] = names
            pj.write_text(json.dumps(prof), encoding="utf-8")
            rep, _ = registry.validate_registry(pkg / "profiles" / "registry.json", strict_versions=strict)
            code, text = run(registry.main, ["--registry", str(pkg / "profiles" / "registry.json")]
                             + (["--strict-versions"] if strict else []))
        return rep, code, text

    def test_old_related_skill_warns(self):
        rep, code, _ = self._registry(["hep-computing", "hep-analysis"], False)
        self.assertTrue(rep.ok)
        self.assertEqual(codes(rep, "warning"), [skill_names.PROFILE_CODE])
        self.assertEqual(code, 0)

    def test_old_related_skill_fails_under_strict_versions(self):
        rep, code, text = self._registry(["detector-response"], True)
        self.assertEqual(codes(rep, "error"), [skill_names.PROFILE_CODE])
        self.assertEqual(code, 1, text)

    def test_new_related_skills_clean(self):
        rep, code, _ = self._registry(["hep-measurement", "hep-detector"], True)
        self.assertTrue(rep.ok and not rep.findings, [f.as_dict() for f in rep.findings])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
