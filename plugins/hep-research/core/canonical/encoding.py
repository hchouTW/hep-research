"""canonical/1, decimal/1 and the JSON readers of hashed documents (g4sim S1; steward hep-computing, core/OWNERS.json).

- canonical_json(value) and canonical_sha256(value): the repository's canonical form, json.dumps with sort_keys, compact
  separators and ensure_ascii=False, in UTF-8 with no trailing newline.
- check_hash_scope(value) lists what would make those bytes differ from RFC 8785 (JCS) output or depend on the host.
- load_json_strict(text) parses JSON and refuses duplicate object keys and the NaN/Infinity constants.
- normalize_decimal(text) is decimal/1: exact digit-string arithmetic, never Decimal.normalize.
- load_spec_json(text, field_types) is the reading procedure of specifications: strict parsing with every literal kept,
  normalization by a type table the caller passes in, then the hash scope.

Moved here from core/provider/hashing.py and adapters/detector-simulation/assets/detsim_canonical.py unchanged. Standard
library only; this package does not import contracts, which generates the type table.
"""
from __future__ import annotations

import decimal
import hashlib
import json
import math
import re

INTEGER_LIMIT = 2 ** 53 - 1
DECIMAL_INPUT = re.compile(r"^[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$", re.ASCII)
DECIMAL_OUTPUT = re.compile(r"^(0|-?[1-9](\.[0-9]*[1-9])?e(0|-?[1-9][0-9]*))$", re.ASCII)
_DECIMAL_PARTS = re.compile(r"([+-]?)(0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?", re.ASCII)
_ENVIRONMENT_REFERENCE = re.compile(r"\$(\{|\(|[A-Z_])")  # ${...}, $(...) or $NAME; canonical/1 rule: an upper-case NAME
# only, so a JSON Schema "#/$defs" or a lower-case word after "$" in free text is not refused (decision D-W3a-4)
_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")
FIELD_TYPES = ("integer", "quantity")


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class CanonicalError(ValueError):
    """A value refused by canonical/1, decimal/1 or the identity rules; code is a stable name."""

    def __init__(self, code: str, message: str, issues: list[dict] | None = None):
        super().__init__(message)
        self.code = code
        self.issues = list(issues or [])


def _issue(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _string_issues(text: str, path: str, exempt: bool) -> list[dict]:
    issues = []
    if any(0xD800 <= ord(c) <= 0xDFFF for c in text):
        issues.append(_issue("lone-surrogate", path, "a lone surrogate cannot be encoded in UTF-8"))
    if not exempt:
        if text.startswith(("/", "~")) or _DRIVE_PATH.match(text):
            issues.append(_issue("path-reference", path, f"{text[:80]!r} is an absolute or home path; use a logical "
                                                         "root (ENV_ROOT, INPUT_ROOT, ATTEMPT_ROOT) or a relative path"))
        if _ENVIRONMENT_REFERENCE.search(text):
            issues.append(_issue("environment-reference", path, f"{text[:80]!r} holds an unresolved $NAME or ${{...}} "
                                                                "reference"))
    return issues


def check_hash_scope(value, path: str = "$") -> list[dict]:
    """Every hash-scope violation in value, each as {code, path, message}; empty when value may be hashed."""
    issues: list[dict] = []
    if value is None or isinstance(value, bool):
        return issues
    if isinstance(value, int):
        if not -INTEGER_LIMIT <= value <= INTEGER_LIMIT:
            issues.append(_issue("integer-range", path, "integers in the hash scope lie within +-(2^53 - 1); write a "
                                                        "larger value as a decimal string"))
        return issues
    if isinstance(value, float):
        code = "float" if math.isfinite(value) else "nan-or-infinity"
        issues.append(_issue(code, path, f"{value!r}: no binary floats in the hash scope; write a decimal string "
                                         "(a quantity is {\"value\": \"<decimal>\", \"unit\": \"<unit>\"})"))
        return issues
    if isinstance(value, str):
        return _string_issues(value, path, exempt=False)
    if isinstance(value, list):
        for i, item in enumerate(value):
            issues.extend(check_hash_scope(item, f"{path}[{i}]"))
        return issues
    if isinstance(value, dict):
        base64_file = value.get("encoding") == "base64"
        for key, item in value.items():
            if not isinstance(key, str):
                issues.append(_issue("key-not-a-string", path, f"object key {key!r} is not a string"))
                continue
            where = f"{path}.{key}"
            if not key.isascii():
                issues.append(_issue("non-ascii-key", where, "object keys in the hash scope are ASCII (Python sorts by "
                                                             "code point, JCS by UTF-16 unit)"))
            issues.extend(_string_issues(key, where, exempt=True))
            if base64_file and key == "content" and isinstance(item, str):
                issues.extend(_string_issues(item, where, exempt=True))
            else:
                issues.extend(check_hash_scope(item, where))
        return issues
    issues.append(_issue("unsupported-type", path, f"{type(value).__name__} is not a JSON value"))
    return issues


def require_hash_scope(value) -> None:
    issues = check_hash_scope(value)
    if issues:
        raise CanonicalError(issues[0]["code"], f"{len(issues)} hash-scope violation(s), first at {issues[0]['path']}: "
                                                f"{issues[0]['message']}", issues)



def _unique_pairs(pairs):
    out = {}
    for key, item in pairs:
        if key in out:
            raise CanonicalError("duplicate-key", f"object key {key!r} appears more than once")
        out[key] = item
    return out


def _refuse_constant(name):
    raise CanonicalError("nan-or-infinity", f"{name} is not JSON")


def load_json_strict(text):
    """Parse JSON text (str or UTF-8 bytes); refuse duplicate keys and NaN/Infinity while parsing."""
    if isinstance(text, (bytes, bytearray)):
        try:
            text = bytes(text).decode("utf-8")
        except UnicodeDecodeError as err:
            raise CanonicalError("json-encoding", f"not UTF-8: {err}") from None
    try:
        return json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_refuse_constant)
    except CanonicalError:
        raise
    except (ValueError, RecursionError) as err:
        raise CanonicalError("json-syntax", f"not JSON: {err}") from None


def normalize_decimal(text) -> str:
    """decimal/1: the normalized spelling of a decimal string, exactly; CanonicalError('decimal-grammar') otherwise."""
    if not isinstance(text, str):
        raise CanonicalError("decimal-grammar", f"{text!r} is not a string; quantities carry decimal strings")
    parts = _DECIMAL_PARTS.fullmatch(text)
    if parts is None or DECIMAL_INPUT.fullmatch(text) is None:
        raise CanonicalError("decimal-grammar", f"{text[:80]!r} is not a decimal of the form "
                                                "[+-]digits[.digits][e[+-]digits] (ASCII, no spaces or underscores)")
    sign, whole, fraction, exponent_text = parts.group(1), parts.group(2), parts.group(3) or "", parts.group(4) or "0"
    try:
        exponent = int(exponent_text) - len(fraction)
    except ValueError:  # an exponent longer than Python's int string limit (about 4300 digits)
        raise CanonicalError("decimal-exponent-range", "the exponent has more digits than decimal/1 handles "
                             "(Python's integer string limit, about 4300 digits)") from None
    digits = (whole + fraction).lstrip("0")
    if not digits:
        return "0"
    significant = digits.rstrip("0")
    exponent += len(digits) - len(significant)
    scientific = exponent + len(significant) - 1
    out = ("-" if sign == "-" else "") + significant[0] + ("." + significant[1:] if len(significant) > 1 else "")
    out += "e" + str(scientific)
    if DECIMAL_OUTPUT.fullmatch(out) is None:  # cannot happen; kept as the code side of the schema pattern
        raise RuntimeError(f"normalize_decimal produced {out!r}")
    return out


def is_normalized_decimal(text) -> bool:
    return isinstance(text, str) and DECIMAL_OUTPUT.fullmatch(text) is not None


def _pointer_segments(pointer) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise CanonicalError("field-type-table", f"{pointer!r} is not a JSON Pointer")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def _type_tree(field_types: dict) -> dict:
    """The type table as a tree of pointer segments; "*" stands for any one key or index, and a type sits under None."""
    tree: dict = {}
    for pointer, kind in field_types.items():
        if kind not in FIELD_TYPES:
            raise CanonicalError("field-type-table", f"{pointer!r}: type {kind!r} is not one of {FIELD_TYPES}")
        node = tree
        for part in _pointer_segments(pointer):
            node = node.setdefault(part, {})
        node[None] = kind
    return tree


def _descend(nodes: list[dict], key: str) -> list[dict]:
    return [child for node in nodes for child in (node.get(key), node.get("*")) if child is not None]


def _integer_field(value, path: str):
    text = str(value)
    if isinstance(value, str) and DECIMAL_INPUT.fullmatch(value) is None:
        return value  # a params expression, evaluated later
    try:
        number = decimal.Decimal(text)
        integral = number == number.to_integral_value()
    except decimal.InvalidOperation:
        raise CanonicalError("integer-range", f"{path}: {text[:80]} is beyond every integer limit") from None
    if not integral:
        raise CanonicalError("integer-field", f"{path}: {text[:80]} is not an integer")
    if abs(number) > INTEGER_LIMIT:
        raise CanonicalError("integer-range", f"{path}: integers lie within +-(2^53 - 1)")
    return int(number)


def _quantity_field(value, path: str) -> str:
    if isinstance(value, str) and DECIMAL_INPUT.fullmatch(value) is None:
        return value  # a params expression, evaluated later
    return normalize_decimal(str(value))


def _typed_value(value, kind: str, path: str):
    if isinstance(value, bool) or not isinstance(value, (int, decimal.Decimal, str)):
        raise CanonicalError("field-type", f"{path}: a {kind} field holds a number or a string, not {value!r}")
    return _integer_field(value, path) if kind == "integer" else _quantity_field(value, path)


def _normalized(value, nodes: list[dict], path: str):
    kinds = {node[None] for node in nodes if None in node}
    if len(kinds) > 1:
        raise CanonicalError("field-type-table", f"{path} matches more than one type: {sorted(kinds)}")
    if kinds:
        return _typed_value(value, kinds.pop(), path)
    if isinstance(value, dict):
        return {key: _normalized(item, _descend(nodes, key), f"{path}/{key}") for key, item in value.items()}
    if isinstance(value, list):
        return [_normalized(item, _descend(nodes, str(i)), f"{path}/{i}") for i, item in enumerate(value)]
    if isinstance(value, (int, decimal.Decimal)) and not isinstance(value, bool):
        raise CanonicalError("undeclared-number", f"{path or '/'} is a number with no declared type")
    return value


def load_spec_json(text, field_types: dict, unhashed: tuple = ()):
    """The reading procedure of a specification: every number normalized by field_types, {JSON Pointer: "integer" or
    "quantity"} with "*" for any one key or index, and the result checked against the hash scope. unhashed names top-level keys
    that never enter a hash, so the scope does not apply to them."""
    if isinstance(text, (bytes, bytearray)):
        try:
            text = bytes(text).decode("utf-8")
        except UnicodeDecodeError as err:
            raise CanonicalError("json-encoding", f"not UTF-8: {err}") from None
    tree = _type_tree(field_types)
    try:
        parsed = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_refuse_constant,
                            parse_float=decimal.Decimal)
    except CanonicalError:
        raise
    except (ValueError, RecursionError, decimal.InvalidOperation) as err:
        raise CanonicalError("json-syntax", f"not JSON: {err}") from None
    value = _normalized(parsed, [tree], "")
    require_hash_scope({key: item for key, item in value.items() if key not in unhashed} if isinstance(value, dict) else value)
    return value
