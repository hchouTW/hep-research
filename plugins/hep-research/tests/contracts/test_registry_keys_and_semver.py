"""SemVer pre-release versions (contracts/semver.py) and the rule registry key (rule_id, version) with retired
versions (registry 1.2.0). (Kept from the cross-artifact check's release R2 format tests when the check was retired;
semver is shared by the project, registry and validate readers.)"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DEV = "1.1.0-dev.5"


class SemverPrerelease(unittest.TestCase):
    def test_full_versions_parse_and_order_by_semver_precedence(self):
        from contracts import semver
        self.assertEqual(semver.parse_full("1.1.0-dev.1"), (1, 1, 0, ("dev", 1)))
        self.assertTrue(semver.is_prerelease(DEV))
        self.assertFalse(semver.is_prerelease("1.1.0"))
        order = ["1.0.0", "1.1.0-0", "1.1.0-alpha", "1.1.0-dev.1", "1.1.0-dev.2", "1.1.0-dev.10", "1.1.0", "1.1.1"]
        self.assertEqual(sorted(reversed(order), key=semver.precedence), order)

    def test_release_parse_and_ranges_still_refuse_prereleases(self):
        from contracts import semver
        with self.assertRaises(ValueError):
            semver.parse(DEV)
        with self.assertRaises(ValueError):
            semver.satisfies(DEV, ">=1.0.0")

    def test_malformed_versions_are_refused(self):
        from contracts import semver
        for bad in ("1.1.0-", "01.1.0", "1.1", "1.1.0-dev..1", "1.1.0-01", "1.1.0+build"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                semver.parse_full(bad)


class RegistryKey(unittest.TestCase):
    def registry(self) -> dict:
        from contracts import rule_registry
        return json.loads(rule_registry.REGISTRY.read_text(encoding="utf-8"))

    @staticmethod
    def live(doc) -> dict:
        return next(r for r in doc["rules"] if r["kind"] != "legacy")

    def codes(self, doc) -> list[str]:
        from contracts import rule_registry
        return [f.code for f in rule_registry.check(doc).findings if f.severity == "error"]

    def test_the_shipped_registry_passes(self):
        self.assertEqual(self.codes(self.registry()), [])

    def test_registry_1_2_0_keys_rules_by_id_and_version(self):
        doc = self.registry()
        doc["registry_version"] = "1.2.0"
        old = copy.deepcopy(self.live(doc))
        old.update(version="0.9.0", lifecycle="retired")
        old.pop("source_sha256", None)
        doc["rules"].append(old)
        self.assertEqual(self.codes(doc), [])
        doc["rules"].append(copy.deepcopy(self.live(doc)))
        self.assertIn("registry.duplicate_rule", self.codes(doc))

    def test_registry_1_1_0_keeps_one_entry_per_rule(self):
        doc = self.registry()
        doc["registry_version"] = "1.1.0"
        old = copy.deepcopy(self.live(doc))
        old.update(version="0.9.0", lifecycle="retired")
        doc["rules"].append(old)
        self.assertIn("registry.duplicate_rule", self.codes(doc))

    def test_a_retired_version_needs_no_implementation_but_a_live_one_does(self):
        doc = self.registry()
        doc["registry_version"] = "1.2.0"
        ghost = copy.deepcopy(self.live(doc))
        ghost.update(version="0.9.0", lifecycle="shadow")
        ghost.pop("source_sha256", None)
        doc["rules"].append(ghost)
        self.assertIn("registry.rule_not_implemented", self.codes(doc))
        ghost["lifecycle"] = "retired"
        self.assertEqual(self.codes(doc), [])

    def test_prerelease_rule_versions_are_valid(self):
        from contracts.schema import validate
        doc = self.registry()
        self.live(doc)["version"] = DEV
        self.assertNotIn("schema.pattern", [f.code for f in validate(doc, "rule_registry.json").errors])


if __name__ == "__main__":
    unittest.main()
