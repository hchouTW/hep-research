"""Regression tests tying the profile's documentation to the code it describes (task Section 12)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from contracts.legacy import yaml_subset as ys  # noqa: E402

ARTIFACTS = (ROOT / "modules" / "methods" / "analysis-artifacts.md").read_text(encoding="utf-8")

# one sample per feature the module says is rejected, with the line the error must name
REJECTED = {
    "Anchors": ("a: &x 1\n", 1), "aliases": ("a: *x\n", 1), "tags": ("a: !!str 1\n", 1),
    "multiple documents": ("a: 1\n---\nb: 2\n", 2), "multi-line flow": ("a: [1,\n  2]\n", 1),
    "quoted scalars": ('a: "one\n  two"\n', 1), "tab indentation": ("a:\n\tb: 1\n", 2), "duplicate keys": ("a: 1\na: 2\n", 2),
}
ACCEPTED = {"mappings": "a:\n  b: 1\n", "lists": "a:\n- 1\n- 2\n", "comments": "a: 1  # note\n",
            "one-line": "a: [1, 2]\nb: {c: 3}\n", "block scalars": "a: |\n  x\n  y\nb: >-\n  p\n  q\n"}


class YamlDocumentationTests(unittest.TestCase):
    """Section 12: the artifact docs denied YAML parsing although a strict subset is implemented."""

    def test_docs_no_longer_deny_yaml(self):
        self.assertNotIn("no YAML parser", ARTIFACTS)
        self.assertIn("strict subset", ARTIFACTS)

    def test_every_rejected_feature_named_in_the_docs_is_rejected_with_its_line(self):
        line = next(l for l in ARTIFACTS.splitlines() if l.startswith("A YAML specification is read with a strict subset"))
        for feature, (text, lineno) in REJECTED.items():
            self.assertIn(feature, line, feature)
            with self.assertRaises(ys.YamlSubsetError, msg=feature) as cm:
                ys.loads(text)
            self.assertTrue(str(cm.exception).startswith(f"line {lineno}:"), (feature, str(cm.exception)))

    def test_every_supported_feature_named_in_the_docs_parses(self):
        for feature, text in ACCEPTED.items():
            self.assertIsInstance(ys.loads(text), dict, feature)

    def test_strings_stay_strings(self):
        self.assertEqual(ys.loads("d: 2026-10-02\ny: yes\n"), {"d": "2026-10-02", "y": "yes"})


if __name__ == "__main__":
    unittest.main()
