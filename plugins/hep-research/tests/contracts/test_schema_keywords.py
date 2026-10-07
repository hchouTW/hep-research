"""Every keyword in contracts/schemas/*.json is one contracts/schema.py implements or reads as an annotation (T09).

A keyword the validator does not implement (oneOf, maxItems, uniqueItems, ...) would be ignored silently, so a schema
would promise a check that never runs."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.schema import ANNOTATION_KEYWORDS, SUPPORTED_KEYWORDS, load_schema, _resolve  # noqa: E402

SCHEMAS = sorted((ROOT / "contracts" / "schemas").glob("*.json"))
CONTAINERS = ("properties", "$defs")  # their keys are names, not keywords


def keywords(node, where="$"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, f"{where}.{k}"
            if k in CONTAINERS and isinstance(v, dict):
                for name, sub in v.items():
                    yield from keywords(sub, f"{where}.{k}.{name}")
            elif k not in ("enum", "const", "required", "examples", "default"):
                yield from keywords(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from keywords(v, f"{where}[{i}]")


class SchemaKeywordTests(unittest.TestCase):
    def test_only_supported_keywords(self):
        self.assertTrue(SCHEMAS)
        allowed = SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS
        for path in SCHEMAS:
            for key, where in keywords(json.loads(path.read_text(encoding="utf-8"))):
                with self.subTest(schema=path.name, at=where):
                    self.assertIn(key, allowed, f"{path.name} {where}: '{key}' is not implemented by contracts/schema.py")

    def test_every_supported_keyword_is_read_by_the_validator(self):
        source = (ROOT / "contracts" / "schema.py").read_text(encoding="utf-8")
        body = source.split("def validate(", 1)[1]
        for key in SUPPORTED_KEYWORDS:
            self.assertRegex(body, re.escape(f'"{key}"'), key)

    def test_every_ref_resolves(self):
        for path in SCHEMAS:
            doc = json.loads(path.read_text(encoding="utf-8"))
            for ref in self._refs(doc):
                with self.subTest(schema=path.name, ref=ref):
                    _resolve(ref, path.name)

    def _refs(self, node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref":
                    yield v
                else:
                    yield from self._refs(v)
        elif isinstance(node, list):
            for v in node:
                yield from self._refs(v)

    def test_an_unsupported_keyword_is_caught(self):
        fake = {"type": "object", "properties": {"oneOf": {"type": "string"}}, "oneOf": [{"type": "object"}]}
        found = {k for k, _ in keywords(fake)}
        self.assertIn("oneOf", found - (SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS))
        self.assertTrue(load_schema("common.json"))


if __name__ == "__main__":
    unittest.main()
