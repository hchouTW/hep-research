"""Minimal JSON-Schema-subset validator (standard library only).

Supported keywords: type, required, properties, additionalProperties (bool or schema),
enum, const, items, minItems, minLength, pattern, minimum, exclusiveMinimum, anyOf,
$ref ("#/$defs/x", "other.json", "other.json#/$defs/x"), and the custom keyword
"x-vocab": "<vocabulary name>" whose value(s) must be core terms or registered
namespaced extensions (see contracts.vocab).

Anything else in a schema is documentation and is ignored. Findings are returned,
never raised, so callers can report every problem at once.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


@dataclass
class Finding:
    severity: str          # "error" | "warning" | "unresolved"
    path: str              # JSON pointer-ish location, "$" is the root
    code: str
    message: str

    def as_dict(self) -> dict:
        return {"severity": self.severity, "path": self.path, "code": self.code, "message": self.message}


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, severity: str, path: str, code: str, message: str) -> None:
        self.findings.append(Finding(severity, path, code, message))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict:
        return {"ok": self.ok, "findings": [f.as_dict() for f in self.findings]}


# Keywords validate() implements, and keywords it reads only as annotations or as $ref targets. A schema keyword outside
# both sets would be ignored silently (for example oneOf or maxItems); tests/contracts/test_schema_keywords.py checks
# every schema under contracts/schemas/ against them.
SUPPORTED_KEYWORDS = frozenset({"$ref", "anyOf", "type", "const", "enum", "minLength", "pattern", "minimum",
                                "exclusiveMinimum", "x-vocab", "required", "properties", "additionalProperties",
                                "minItems", "items"})
ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "$comment", "$defs", "title", "description", "examples", "default"})

_cache: dict[str, dict] = {}


def load_schema(name: str) -> dict:
    if name not in _cache:
        _cache[name] = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return _cache[name]


def _type_ok(value, t) -> bool:
    if isinstance(t, list):
        return any(_type_ok(value, x) for x in t)
    if t in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[t])


def _resolve(ref: str, doc_name: str) -> tuple[dict, str]:
    file_part, _, frag = ref.partition("#")
    name = file_part or doc_name
    node = load_schema(name)
    for key in [k for k in frag.split("/") if k]:
        node = node[key]
    return node, name


def validate(value, schema: dict | str, vocab=None, report: Report | None = None,
             path: str = "$", doc_name: str | None = None) -> Report:
    """Validate `value` against `schema` (a dict, or a file name in contracts/schemas)."""
    report = report if report is not None else Report()
    if isinstance(schema, str):
        doc_name, schema = schema, load_schema(schema)
    doc_name = doc_name or ""

    if "$ref" in schema:
        target, name = _resolve(schema["$ref"], doc_name)
        validate(value, target, vocab, report, path, name)

    if "anyOf" in schema:
        trials = []
        for sub in schema["anyOf"]:
            r = validate(value, sub, vocab, Report(), path, doc_name)
            if r.ok:
                report.findings.extend(r.findings)
                break
            trials.append(r)
        else:
            first = trials[0].errors[0] if trials and trials[0].errors else None
            report.add("error", path, "schema.any_of",
                       "value matches none of the allowed forms"
                       + (f" (first form: {first.message})" if first else ""))

    t = schema.get("type")
    if t is not None and not _type_ok(value, t):
        report.add("error", path, "schema.type", f"expected {t}, got {type(value).__name__}")
        return report

    if "const" in schema and value != schema["const"]:
        report.add("error", path, "schema.const", f"must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        report.add("error", path, "schema.enum", f"{value!r} not in {schema['enum']}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            report.add("error", path, "schema.min_length", "must not be empty")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            report.add("error", path, "schema.pattern", f"{value!r} does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            report.add("error", path, "schema.minimum", f"{value} < {schema['minimum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            report.add("error", path, "schema.exclusive_minimum", f"{value} <= {schema['exclusiveMinimum']}")
    if "x-vocab" in schema and vocab is not None:
        for item in (value if isinstance(value, list) else [value]):
            if isinstance(item, str) and not vocab.has(schema["x-vocab"], item):
                report.add("error", path, "vocab.unknown_term",
                           f"'{item}' is not a core {schema['x-vocab']} term or a registered profile extension"
                           f" (core: {sorted(vocab.core(schema['x-vocab']))})")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                report.add("error", f"{path}.{key}", "schema.required", f"missing required field '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, sub in value.items():
            if key in props:
                validate(sub, props[key], vocab, report, f"{path}.{key}", doc_name)
            elif extra is False:
                report.add("error", f"{path}.{key}", "schema.additional", f"unexpected field '{key}'")
            elif isinstance(extra, dict):
                validate(sub, extra, vocab, report, f"{path}.{key}", doc_name)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            report.add("error", path, "schema.min_items", f"needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                validate(item, schema["items"], vocab, report, f"{path}[{i}]", doc_name)
    return report
