"""Canonical identity of the detector-simulation shared layer: canonical/1, decimal/1, run digest and run_id.

A module of detsim.py (TASK.md 9.2-9.4 under docs/dev/detector-simulation/); standard library, core and contracts only.

- canonical/1 is the repository's canonical_sha256 (contracts/recipe_semantics.py: json.dumps with sort_keys, compact
  separators and ensure_ascii=False, UTF-8, no trailing newline). canonical_bytes() returns the bytes that function
  hashes, taken from the existing serializer core.provider.hashing.canonical_json, and checks them against
  canonical_sha256 on every call: there is no second canonicalization.
- check_hash_scope(value) runs before any hashing and refuses, each by name, what would make those bytes differ from
  RFC 8785 (JCS) output or depend on the host: binary floats (float), NaN and Infinity (nan-or-infinity), integers
  outside +-(2^53 - 1) (integer-range), non-string or non-ASCII object keys (key-not-a-string, non-ascii-key), lone
  surrogates (lone-surrogate), absolute or home paths (path-reference), ${...} or $NAME references with an upper-case NAME
  (environment-reference) and any other Python type (unsupported-type). The base64 "content" of a rendered file
  (an object whose "encoding" is "base64") is exempt from the path and reference checks only.
- load_json_strict(text) parses JSON and refuses duplicate object keys and the NaN/Infinity constants while parsing
  (a parsed dict has already lost a duplicate).
- normalize_decimal(text) is decimal/1: the ASCII input grammar
  ^[+-]?(0|[1-9][0-9]*)(\\.[0-9]+)?([eE][+-]?[0-9]+)?$ (anything else is refused, never coerced), exact digit-string
  arithmetic (never Decimal.normalize, which rounds to 28 digits), output [-]d[.ddd]e<exp> or "0", matched against
  ^(0|-?[1-9](\\.[0-9]*[1-9])?e(0|-?[1-9][0-9]*))$. Both patterns are applied with re.fullmatch.
- run_digest(plan_digest, replicate) = SHA-256("detsim-run/1\\0" + the 32 raw bytes of plan_digest + uint32
  big-endian replicate); run_id is its first 32 hex characters; parse_replicate accepts 0 ... 2^32 - 1 written in
  canonical decimal (no sign, no leading zero).
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    if sys.argv[1:] in ([], ["--help"], ["-h"]):
        print((__doc__ or "detsim module").splitlines()[0] + "\nA module of detsim.py, not a command: "
              "python3 detsim.py --help")
        sys.exit(0)
    print('{"status": "rejected", "error_code": "usage", "message": "a module of detsim.py, not a command"}')
    sys.exit(2)

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import re  # noqa: E402
import struct  # noqa: E402

from contracts.recipe_semantics import canonical_sha256  # noqa: E402
from core.provider.hashing import canonical_json  # noqa: E402

CANONICAL_VERSION = "canonical/1"
DECIMAL_VERSION = "decimal/1"
INTEGER_LIMIT = 2 ** 53 - 1
REPLICATE_MAX = 2 ** 32 - 1
RUN_DIGEST_PREFIX = b"detsim-run/1\x00"
DECIMAL_INPUT = re.compile(r"^[+-]?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$", re.ASCII)
DECIMAL_OUTPUT = re.compile(r"^(0|-?[1-9](\.[0-9]*[1-9])?e(0|-?[1-9][0-9]*))$", re.ASCII)
_DECIMAL_PARTS = re.compile(r"([+-]?)(0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?", re.ASCII)
SHA256_HEX = re.compile(r"[0-9a-f]{64}", re.ASCII)
_REPLICATE = re.compile(r"0|[1-9][0-9]{0,9}", re.ASCII)
_ENVIRONMENT_REFERENCE = re.compile(r"\$(\{|\(|[A-Z_])")  # ${...}, $(...) or $NAME; canonical/1 rule: an upper-case NAME
# only, so a JSON Schema "#/$defs" or a lower-case word after "$" in free text is not refused (decision D-W3a-4)
_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")


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


def canonical_bytes(value) -> bytes:
    """The canonical/1 bytes of value (after check_hash_scope); their SHA-256 is canonical_sha256(value)."""
    require_hash_scope(value)
    raw = canonical_json(value).encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != canonical_sha256(value):
        raise RuntimeError("core.provider.hashing.canonical_json and contracts.recipe_semantics.canonical_sha256 differ")
    return raw


def digest(value) -> str:
    """canonical_sha256 of value (64 hex) after check_hash_scope: the plan_digest of a plan."""
    require_hash_scope(value)
    return canonical_sha256(value)


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


def run_digest(plan_digest: str, replicate: int) -> str:
    """SHA-256("detsim-run/1\\0" + raw plan_digest + uint32 big-endian replicate), 64 hex."""
    if not isinstance(plan_digest, str) or SHA256_HEX.fullmatch(plan_digest) is None:
        raise CanonicalError("digest-format", f"{plan_digest!r} is not 64 lowercase hex characters")
    if isinstance(replicate, bool) or not isinstance(replicate, int) or not 0 <= replicate <= REPLICATE_MAX:
        raise CanonicalError("replicate-range", f"replicate {replicate!r} is not an integer 0 ... {REPLICATE_MAX}")
    return hashlib.sha256(RUN_DIGEST_PREFIX + bytes.fromhex(plan_digest) + struct.pack(">I", replicate)).hexdigest()


def run_id(plan_digest: str, replicate: int) -> str:
    return run_digest(plan_digest, replicate)[:32]


def parse_replicate(text) -> int:
    """--replicate N: an integer 0 ... 2^32 - 1 in canonical decimal; CanonicalError('replicate-range') otherwise."""
    if not isinstance(text, str) or _REPLICATE.fullmatch(text) is None or int(text) > REPLICATE_MAX:
        raise CanonicalError("replicate-range", f"--replicate {text!r} is not an integer 0 ... {REPLICATE_MAX} "
                                                "(decimal, no sign, no leading zero)")
    return int(text)
