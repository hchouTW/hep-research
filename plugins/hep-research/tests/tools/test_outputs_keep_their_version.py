"""A release does not regenerate committed outputs: the plugin version that wrote a file is not compared, everything
else is. The negative controls show a changed result still fails."""
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._outputs import without_plugin_version

PLUGIN = Path(__file__).resolve().parents[2]
PROFILES = ("cr-secondary-ratio", "cr-secondary-antiprotons", "dis-parton-model", "drell-yan-lo", "tmd-gaussian-lo",
            "heliospheric-modulation")


def moved_float(node):
    """Multiply the first float below node by 1.01 in place; True when one was found."""
    items = node.items() if isinstance(node, dict) else enumerate(node) if isinstance(node, list) else ()
    for key, value in items:
        if isinstance(value, float) and value:
            node[key] = value * 1.01
            return True
        if moved_float(value):
            return True
    return False


class WithoutPluginVersion(unittest.TestCase):
    DOC = {"plugin_version": "1.0.0", "versions": {"plugin": "1.0.0", "contracts": "3.0.0"}, "plugin": "kept",
           "nested": [{"versions": {"plugin": "1.0.0"}, "value": 1}]}

    def test_drops_only_the_version_that_wrote_the_file(self):
        self.assertEqual(without_plugin_version(self.DOC), {"versions": {"contracts": "3.0.0"}, "plugin": "kept",
                                                            "nested": [{"versions": {}, "value": 1}]})

    def test_a_new_version_compares_equal_and_a_new_contract_does_not(self):
        other = copy.deepcopy(self.DOC)
        other["plugin_version"] = other["versions"]["plugin"] = other["nested"][0]["versions"]["plugin"] = "2.0.0"
        self.assertEqual(without_plugin_version(other), without_plugin_version(self.DOC))
        other["versions"]["contracts"] = "4.0.0"
        self.assertNotEqual(without_plugin_version(other), without_plugin_version(self.DOC))

    def test_the_input_is_not_changed(self):
        doc = copy.deepcopy(self.DOC)
        without_plugin_version(doc)
        self.assertEqual(doc, self.DOC)


class ProfileCheck(unittest.TestCase):
    """make_artifacts.py --check on a copy of each profile, so the tree under test is never written."""

    def check(self, root, profile):
        return subprocess.run([sys.executable, str(root / "profiles/theory" / profile / "scripts/make_artifacts.py"), "--check"],
                              capture_output=True, text=True, timeout=300, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})

    def test_a_stored_version_is_ignored_and_a_stored_result_is_not(self):
        for profile in PROFILES:
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as workdir:
                root = Path(workdir) / "hep-research"
                for sub in (".claude-plugin", "contracts", "core"):
                    shutil.copytree(PLUGIN / sub, root / sub, ignore=shutil.ignore_patterns("__pycache__", "fixtures"))
                shutil.copytree(PLUGIN / "profiles/theory" / profile, root / "profiles/theory" / profile,
                                ignore=shutil.ignore_patterns("__pycache__"))
                self.assertEqual(self.check(root, profile).returncode, 0)
                stored = root / "profiles/theory" / profile / "derivations/theory-spec.json"
                doc = json.loads(stored.read_text(encoding="utf-8"))
                doc["versions"]["plugin"] = "0.0.1"
                stored.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
                proc = self.check(root, profile)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                doc["versions"]["contracts"] = "0.0.1"
                stored.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
                self.assertEqual(self.check(root, profile).returncode, 1)
                doc = json.loads(stored.read_text(encoding="utf-8"))
                doc["versions"]["contracts"] = json.loads((PLUGIN / "profiles/theory" / profile / "derivations/theory-spec.json")
                                                          .read_text(encoding="utf-8"))["versions"]["contracts"]
                self.assertTrue(moved_float(doc["extension"]))
                stored.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
                self.assertEqual(self.check(root, profile).returncode, 1)


if __name__ == "__main__":
    unittest.main()
