"""Canonical identity of the detector-simulation shared layer: canonical/1, decimal/1, run digest and run_id.

A module of detsim.py (TASK.md 9.2-9.4 under docs/dev/detector-simulation/); standard library, core and contracts only.
check_hash_scope, normalize_decimal and load_json_strict live in core/canonical (g4sim S1) and are described below.

- canonical/1 is the repository's canonical_sha256 (contracts/recipe_semantics.py: json.dumps with sort_keys, compact
  separators and ensure_ascii=False, UTF-8, no trailing newline). canonical_bytes() returns the bytes that function
  hashes, taken from core.canonical.canonical_json, and checks them against contracts.recipe_semantics.canonical_sha256
  on every call. That function is a separate implementation (never core.canonical's), so the check compares two.
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
import re  # noqa: E402
import struct  # noqa: E402

from contracts.recipe_semantics import canonical_sha256  # noqa: E402  (its own implementation: see canonical_bytes)
from core.canonical import (CanonicalError, canonical_json, check_hash_scope, is_normalized_decimal,  # noqa: E402, F401
                            load_json_strict, normalize_decimal, require_hash_scope)  # noqa: F401

CANONICAL_VERSION = "canonical/1"
DECIMAL_VERSION = "decimal/1"
REPLICATE_MAX = 2 ** 32 - 1
RUN_DIGEST_PREFIX = b"detsim-run/1\x00"
SHA256_HEX = re.compile(r"[0-9a-f]{64}", re.ASCII)
_REPLICATE = re.compile(r"0|[1-9][0-9]{0,9}", re.ASCII)


def canonical_bytes(value) -> bytes:
    """The canonical/1 bytes of value (after check_hash_scope); their SHA-256 is canonical_sha256(value)."""
    require_hash_scope(value)
    raw = canonical_json(value).encode("utf-8")
    if hashlib.sha256(raw).hexdigest() != canonical_sha256(value):
        raise RuntimeError("core.canonical.canonical_json and contracts.recipe_semantics.canonical_sha256 differ")
    return raw


def digest(value) -> str:
    """canonical_sha256 of value (64 hex) after check_hash_scope: the plan_digest of a plan."""
    require_hash_scope(value)
    return canonical_sha256(value)


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
