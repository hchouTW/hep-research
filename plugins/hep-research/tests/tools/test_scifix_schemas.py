"""The sci-fix ledger and advisories against their JSON schemas (docs/evidence/schemas/; sci-fix improvement plan C6):
the shipped files validate, a broken file is refused, and the schemas use only keywords contracts/schema.py
implements (anything else would be ignored silently). Cross-file rules stay in test_scifix_ledger.py and
tools/scifix_advisories.py check."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.schema import ANNOTATION_KEYWORDS, SUPPORTED_KEYWORDS, validate  # noqa: E402
from tests.contracts.test_schema_keywords import keywords  # noqa: E402

SCHEMAS = ROOT / "docs" / "evidence" / "schemas"
LEDGER_SCHEMA = json.loads((SCHEMAS / "sci-fixes.schema.json").read_text(encoding="utf-8"))
ADVISORY_SCHEMA = json.loads((SCHEMAS / "scifix-advisory.schema.json").read_text(encoding="utf-8"))
LEDGER = json.loads((ROOT / "docs" / "evidence" / "sci-fixes.json").read_text(encoding="utf-8"))
ADVISORIES = sorted((ROOT / "docs" / "evidence" / "advisories").glob("SFA-*.json"))


def errors(doc, schema):
    return [f.code + " " + f.path for f in validate(doc, schema).errors]


class SciFixSchemas(unittest.TestCase):
    def test_only_supported_keywords(self):
        allowed = SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS
        for path in sorted(SCHEMAS.glob("*.json")):
            for key, where in keywords(json.loads(path.read_text(encoding="utf-8"))):
                with self.subTest(schema=path.name, at=where):
                    self.assertIn(key, allowed)
                    self.assertNotEqual(key, "$ref", "no $ref: the validator resolves it under contracts/schemas")

    def test_shipped_files_validate(self):
        self.assertEqual(errors(LEDGER, LEDGER_SCHEMA), [])
        self.assertTrue(ADVISORIES)
        for path in ADVISORIES:
            with self.subTest(advisory=path.name):
                self.assertEqual(errors(json.loads(path.read_text(encoding="utf-8")), ADVISORY_SCHEMA), [])

    def test_broken_files_are_refused(self):
        def ledger(edit):
            doc = copy.deepcopy(LEDGER)
            edit(doc)
            return errors(doc, LEDGER_SCHEMA)
        self.assertTrue(ledger(lambda d: d["fixes"][0].pop("commits")))
        self.assertTrue(ledger(lambda d: d["fixes"][0]["commits"].update(fix="abc1234")))
        self.assertTrue(ledger(lambda d: d["fixes"][0].update(discrimination="D5")))
        self.assertTrue(ledger(lambda d: d["fixes"][0]["independence"][0].update(expected_from="memory")))
        self.assertTrue(ledger(lambda d: d["fixes"][0].update(unknown_field=1)))
        self.assertTrue(ledger(lambda d: d["fixes"][0]["parent_records"][0].update(test="tests/x.py")))
        adv = json.loads(ADVISORIES[0].read_text(encoding="utf-8"))

        def advisory(edit):
            doc = copy.deepcopy(adv)
            edit(doc)
            return errors(doc, ADVISORY_SCHEMA)
        self.assertTrue(advisory(lambda a: a.update(format="hep-research-scifix-advisory/1")))
        self.assertTrue(advisory(lambda a: a.update(published="2026-10-20")))
        self.assertTrue(advisory(lambda a: a["affected"][0]["ranges"][0]["events"].append({"fixed": "1.0"})))
        self.assertTrue(advisory(lambda a: a["applies_to"].update(extension_keys=["x"])))
        self.assertTrue(advisory(lambda a: a["affected"][0]["database_specific"].update(no_artifact=True)))


if __name__ == "__main__":
    unittest.main()
