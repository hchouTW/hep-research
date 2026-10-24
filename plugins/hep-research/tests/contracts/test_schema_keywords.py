"""Every keyword in contracts/schemas/*.json and in the adapters' JSON Schemas (adapters/*/assets/**/*.schema.json and
adapters/*/assets/schemas/*.json) is one contracts/schema.py implements or reads as an annotation (T09; Geant4 program
A2.7). layered_sim/output.schema.json is not a JSON Schema (its top-level keys describe CSV columns) and is exempt.

A keyword the validator does not implement (uniqueItems, patternProperties, ...) would be ignored silently, so a schema
would promise a check that never runs. maxItems, maximum, exclusiveMaximum, oneOf and not are implemented since A2;
uniqueItems is not, and new schemas never use it (uniqueness, where needed, is checked in Python)."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.schema import ANNOTATION_KEYWORDS, SUPPORTED_KEYWORDS, load_schema, _resolve  # noqa: E402

from contracts.schema import validate  # noqa: E402

SCHEMAS = sorted((ROOT / "contracts" / "schemas").glob("*.json"))
NOT_JSON_SCHEMA = {"output.schema.json"}  # layered_sim's CSV column description
ADAPTER_SCHEMAS = sorted({p for pat in ("adapters/*/assets/**/*.schema.json", "adapters/*/assets/schemas/*.json")
                          for p in ROOT.glob(pat) if p.name not in NOT_JSON_SCHEMA})
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

    def test_adapter_schemas_use_only_supported_keywords(self):
        self.assertTrue(any(p.name == "spec.schema.json" for p in ADAPTER_SCHEMAS))
        allowed = SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS
        for path in ADAPTER_SCHEMAS:
            for key, where in keywords(json.loads(path.read_text(encoding="utf-8"))):
                with self.subTest(schema=str(path.relative_to(ROOT)), at=where):
                    self.assertIn(key, allowed, f"{path.name} {where}: '{key}' is not implemented by contracts/schema.py")

    def test_no_schema_uses_unique_items(self):
        for path in SCHEMAS + ADAPTER_SCHEMAS:
            self.assertNotIn("uniqueItems", {k for k, _ in keywords(json.loads(path.read_text(encoding="utf-8")))},
                             path.name)

    def test_new_keywords_behave(self):
        cases = [({"maxItems": 2}, [1, 2], True), ({"maxItems": 2}, [1, 2, 3], False),
                 ({"maximum": 1}, 1, True), ({"maximum": 1}, 1.5, False),
                 ({"exclusiveMaximum": 0}, -1e-9, True), ({"exclusiveMaximum": 0}, 0, False),
                 ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, 3, True),
                 ({"oneOf": [{"type": "number"}, {"type": "integer"}]}, 3, False),  # matches both
                 ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, 3.5, False),  # matches none
                 ({"not": {"required": ["a"]}}, {"b": 1}, True), ({"not": {"required": ["a"]}}, {"a": 1}, False)]
        for schema, value, ok in cases:
            with self.subTest(schema=schema, value=value):
                self.assertEqual(validate(value, schema).ok, ok)

    def test_layered_sim_material_forms(self):
        """spec.schema.json's oneOf/not material rule: one element (z, a_g_mole) or a mixture (components), not both."""
        spec = str(ROOT / "adapters" / "geant4" / "assets" / "layered_sim" / "spec.schema.json")
        base = json.loads((ROOT / "examples" / "geant4-thin-silicon" / "recorded" / "specs" / "sp-nominal.json")
                          .read_text(encoding="utf-8"))
        self.assertTrue(validate(base, spec).ok, validate(base, spec).errors[:3])
        both = json.loads(json.dumps(base))
        both["materials"] = [{"name": "X", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.33,
                              "components": [{"material": "G4_Si", "mass_fraction": 0.5},
                                             {"material": "G4_O", "mass_fraction": 0.5}]}]
        self.assertFalse(validate(both, spec).ok)

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
        fake = {"type": "object", "properties": {"uniqueItems": {"type": "string"}}, "uniqueItems": True}
        found = {k for k, _ in keywords(fake)}
        self.assertIn("uniqueItems", found - (SUPPORTED_KEYWORDS | ANNOTATION_KEYWORDS))
        self.assertTrue(load_schema("common.json"))


if __name__ == "__main__":
    unittest.main()
