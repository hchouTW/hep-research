"""T-CANON (docs/dev/detector-simulation/TASK.md 16.1): canonical/1, decimal/1, the hash-scope check and the run identity.

Golden vectors of TASK.md 9.4 are hashed through every copy of canonical_sha256 in the plugin
(contracts/recipe_semantics.py, core/provider/hashing.py, contracts/release_manifest.py,
core/protected/revocation_log.py), through the shared layer (detsim_canonical.digest and canonical_bytes) and through
an independent minimal RFC 8785 (JCS) serializer written here; a few vectors also have their exact bytes written out.
normalize_decimal is checked on the spec's edge cases, against Python's exact Decimal comparison on seeded random
inputs (never Decimal.normalize, which rounds to 28 digits), and check_hash_scope / load_json_strict refuse each
violation by name. The run digest and run_id are recomputed independently (prefix, raw plan digest, uint32 big-endian
replicate). Standard library only; SYNTHETIC values.
"""
import hashlib
import random
import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
for _entry in (str(ROOT), str(ASSETS)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)

import detsim_canonical as canonical  # noqa: E402
from contracts import recipe_semantics, release_manifest  # noqa: E402
from core.protected import revocation_log  # noqa: E402
from core.provider import hashing  # noqa: E402

COPIES = {
    "contracts/recipe_semantics.py": recipe_semantics.canonical_sha256,
    "core/provider/hashing.py": hashing.canonical_sha256,
    "contracts/release_manifest.py": release_manifest.canonical_sha256,
    "core/protected/revocation_log.py": revocation_log.canonical_sha256,
    "detsim_canonical.digest": canonical.digest,
}


def canonicalization_scheme_string(text: str) -> str:
    """ECMAScript JSON.stringify string form, as RFC 8785 3.2.2.2 requires."""
    out = ['"']
    for ch in text:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch in "\b\f\n\r\t":
            out.append({"\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}[ch])
        elif code < 0x20:
            out.append("\\u%04x" % code)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canonicalization_scheme_bytes(value) -> bytes:
    """A minimal RFC 8785 serializer for the hash-scope subset (no floats): members sorted by UTF-16 code units."""
    def walk(node) -> str:
        if node is None:
            return "null"
        if node is True:
            return "true"
        if node is False:
            return "false"
        if isinstance(node, int):
            assert abs(node) <= 2 ** 53 - 1
            return str(node)
        if isinstance(node, str):
            return canonicalization_scheme_string(node)
        if isinstance(node, list):
            return "[" + ",".join(walk(x) for x in node) + "]"
        keys = sorted(node, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(canonicalization_scheme_string(k) + ":" + walk(node[k]) for k in keys) + "}"
    return walk(value).encode("utf-8")


GOLDEN = {
    "non-ascii values": {"name": "Gr\u00f6\u00dfe \u00b5m \u6f22\u5b57", "math": "\U0001d4b3", "z": 1},
    "control characters": {"ctl": "\u0000\u0001\b\t\n\f\r\u001f\"\\/\u007f\u2028"},
    "decimal quantity": {"threshold": {"value": canonical.normalize_decimal("1500"), "unit": "e"}},
    "integer limit": {"max": 2 ** 53 - 1, "min": -(2 ** 53 - 1), "zero": 0},
    "array order": {"a": [3, 1, 2]},
    "array order sorted": {"a": [1, 2, 3]},
    "empty containers": {"o": {}, "a": [], "s": ""},
    "nesting": {"b": {"d": 1, "c": [True, False, None]}, "a": [{"y": True, "x": None}], "B": "upper"},
}
EXACT_BYTES = {
    "non-ascii values": b'{"math":"\xf0\x9d\x92\xb3","name":"Gr\xc3\xb6\xc3\x9fe \xc2\xb5m \xe6\xbc\xa2\xe5\xad\x97","z":1}',
    "control characters": b'{"ctl":"\\u0000\\u0001\\b\\t\\n\\f\\r\\u001f\\"\\\\/\x7f\xe2\x80\xa8"}',
    "decimal quantity": b'{"threshold":{"unit":"e","value":"1.5e3"}}',
    "empty containers": b'{"a":[],"o":{},"s":""}',
    "nesting": b'{"B":"upper","a":[{"x":null,"y":true}],"b":{"c":[true,false,null],"d":1}}',
}


class CanonicalBytes(unittest.TestCase):
    def test_golden_vectors_hash_identically_through_every_copy_and_canonicalization_scheme_bytes(self):
        for name, value in GOLDEN.items():
            with self.subTest(vector=name):
                expected = hashlib.sha256(canonicalization_scheme_bytes(value)).hexdigest()
                for where, fn in COPIES.items():
                    self.assertEqual(fn(value), expected, where)
                self.assertEqual(canonical.canonical_bytes(value), canonicalization_scheme_bytes(value))
                self.assertEqual(canonical.check_hash_scope(value), [])

    def test_exact_bytes(self):
        for name, raw in EXACT_BYTES.items():
            with self.subTest(vector=name):
                self.assertEqual(canonical.canonical_bytes(GOLDEN[name]), raw)
                self.assertEqual(canonicalization_scheme_bytes(GOLDEN[name]), raw)

    def test_array_order_matters_and_key_order_does_not(self):
        self.assertNotEqual(canonical.digest(GOLDEN["array order"]), canonical.digest(GOLDEN["array order sorted"]))
        self.assertEqual(canonical.digest({"a": 1, "b": 2}), canonical.digest({"b": 2, "a": 1}))

    def test_decimal_spellings_give_one_digest(self):
        digests = {canonical.digest({"v": canonical.normalize_decimal(s)}) for s in ("1500", "1.5e3", "+1.50E+3",
                                                                                     "15e2", "1500.000", "0.15e4")}
        self.assertEqual(len(digests), 1)

    def test_refused_values_cannot_be_hashed(self):
        for value in ({"a": float("nan")}, {"a": 1.5}, {"\u00e9": 1}, {"a": "\ud800"}, {"a": 2 ** 53}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(canonical.CanonicalError):
                    canonical.digest(value)
                with self.assertRaises(canonical.CanonicalError):
                    canonical.canonical_bytes(value)


class NormalizeDecimal(unittest.TestCase):
    CASES = {
        "1500": "1.5e3", "1.5e3": "1.5e3", "+1.50E+3": "1.5e3", "-0": "0", "0e5": "0", "0.000": "0", "0": "0",
        "+0.0e-7": "0", "1": "1e0", "-1": "-1e0", "100e-2": "1e0", "0.001": "1e-3", "-1.20e-3": "-1.2e-3",
        "12.5": "1.25e1", "1e0": "1e0", "7E10": "7e10", "0.1000": "1e-1",
        "1234567890123456789012345678901234567890": "1.23456789012345678901234567890123456789e39",
        "9.999999999999999999999999999999999999999e-300": "9.999999999999999999999999999999999999999e-300",
        "1e99999": "1e99999",
    }
    REFUSED = ["1_000", " 1", "1 ", "\u0661\u0662", "NaN", "nan", "Infinity", "-Infinity", ".5", "1.", "01", "00.5",
               "1e", "1e+", "+", "-", "", "1.5e3\n", "0x10", "1,5", "1.5.0", "--1", "1e1.5", "\uff11"]

    def test_spec_cases(self):
        for text, expected in self.CASES.items():
            with self.subTest(text=text):
                out = canonical.normalize_decimal(text)
                self.assertEqual(out, expected)
                self.assertTrue(canonical.is_normalized_decimal(out))
                self.assertEqual(canonical.normalize_decimal(out), out)  # idempotent

    def test_forty_digit_mantissa_is_kept_exactly(self):
        text = "1234567890123456789012345678901234567891"
        out = canonical.normalize_decimal(text)
        self.assertEqual(out, "1.234567890123456789012345678901234567891e39")
        self.assertEqual(Decimal(out), Decimal(text))
        self.assertNotEqual(Decimal(out), Decimal(text).normalize())  # 28-digit context rounding loses digits

    def test_exponent_beyond_the_integer_limit_is_its_own_refusal(self):
        """The grammar accepts any exponent; decimal/1 refuses one longer than Python's int limit by name."""
        with self.assertRaises(canonical.CanonicalError) as caught:
            canonical.normalize_decimal("1e" + "9" * 5000)
        self.assertEqual(caught.exception.code, "decimal-exponent-range")

    def test_refused_spellings(self):
        for text in self.REFUSED + [1.5, 15, None, b"15"]:
            with self.subTest(text=repr(text)[:40]):
                with self.assertRaises(canonical.CanonicalError) as ctx:
                    canonical.normalize_decimal(text)
                self.assertEqual(ctx.exception.code, "decimal-grammar")

    def test_random_inputs_keep_their_exact_value(self):
        rng = random.Random(20261101)
        for _ in range(3000):
            whole = rng.choice(["0", str(rng.randint(1, 10 ** rng.randint(1, 45)))])
            fraction = "" if rng.random() < 0.3 else "." + "".join(rng.choice("0123456789")
                                                                  for _ in range(rng.randint(1, 30)))
            exponent = "" if rng.random() < 0.3 else rng.choice("eE") + rng.choice(["", "+", "-"]) + str(
                rng.randint(0, 400))
            text = rng.choice(["", "+", "-"]) + whole + fraction + exponent
            with self.subTest(text=text):
                out = canonical.normalize_decimal(text)
                self.assertTrue(canonical.is_normalized_decimal(out))
                self.assertEqual(Decimal(out), Decimal(text))
                self.assertEqual(canonical.normalize_decimal(out), out)


class HashScope(unittest.TestCase):
    def codes(self, value):
        return [i["code"] for i in canonical.check_hash_scope(value)]

    def test_each_violation_is_refused_by_name(self):
        cases = {
            "nan-or-infinity": [{"a": float("nan")}, {"a": float("inf")}, [float("-inf")]],
            "float": [{"a": 1.5}, {"a": 1.0}, [0.0]],
            "integer-range": [{"a": 2 ** 53}, {"a": -(2 ** 53)}, [10 ** 30]],
            "non-ascii-key": [{"\u00e9": 1}, {"a": {"\u6f22": 1}}],
            "key-not-a-string": [{1: "x"}],
            "lone-surrogate": [{"a": "\ud800"}, {"a": "x\udfffy"}, {"\udc00": 1}],
            "path-reference": [{"a": "/usr/bin/x"}, {"a": "~/x"}, {"a": "C:\\x"}, ["~"]],
            "environment-reference": [{"a": "$HOME/x"}, {"a": "${G4LEDATA}"}, {"a": "ENV_ROOT/$X"}],
            "unsupported-type": [{"a": (1, 2)}, {"a": b"x"}, {"a": {1, 2}}],
        }
        for code, values in cases.items():
            for value in values:
                with self.subTest(code=code, value=repr(value)):
                    self.assertIn(code, self.codes(value))

    def test_allowed_values_pass(self):
        for value in ({"a": "#/$defs/quantity"}, {"a": "ENV_ROOT/bin:ENV_ROOT/lib"}, {"a": "cost $5"},
                      {"encoding": "base64", "content": "/9j/4AAQ"}, {"a": [True, None, -(2 ** 53 - 1)]},
                      {"a": "relative/path with space"}):
            with self.subTest(value=value):
                self.assertEqual(canonical.check_hash_scope(value), [])

    def test_base64_exemption_is_only_for_file_content(self):
        self.assertIn("path-reference", self.codes({"encoding": "base64", "path": "/abs", "content": "AA=="}))
        self.assertIn("path-reference", self.codes({"content": "/9j/4AAQ"}))  # no base64 encoding declared

    def test_strict_parser(self):
        for text, code in (('{"a": 1, "a": 2}', "duplicate-key"), ('{"x": {"b": 1, "b": 1}}', "duplicate-key"),
                           ('{"a": NaN}', "nan-or-infinity"), ('[Infinity]', "nan-or-infinity"),
                           ('[-Infinity]', "nan-or-infinity"), ('{"a": 1', "json-syntax"), (b"\xff\xfe", "json-encoding")):
            with self.subTest(text=text):
                with self.assertRaises(canonical.CanonicalError) as ctx:
                    canonical.load_json_strict(text)
                self.assertEqual(ctx.exception.code, code)
        parsed = canonical.load_json_strict('{"a": "\\ud800", "b": 1.0}')
        self.assertEqual(sorted(self.codes(parsed)), ["float", "lone-surrogate"])
        self.assertEqual(canonical.load_json_strict('{"a": [1, {"b": null}]}'), {"a": [1, {"b": None}]})


class RunIdentity(unittest.TestCase):
    PLAN = "8f" * 32

    def expected(self, plan_digest, replicate):
        return hashlib.sha256(b"detsim-run/1" + bytes([0]) + bytes.fromhex(plan_digest)
                              + replicate.to_bytes(4, "big")).hexdigest()

    def test_digest_encoding(self):
        for replicate in (0, 1, 258, 2 ** 31, 2 ** 32 - 1):
            with self.subTest(replicate=replicate):
                out = canonical.run_digest(self.PLAN, replicate)
                self.assertEqual(out, self.expected(self.PLAN, replicate))
                self.assertEqual(canonical.run_id(self.PLAN, replicate), out[:32])
                self.assertEqual(len(canonical.run_id(self.PLAN, replicate)), 32)
        self.assertNotEqual(canonical.run_digest(self.PLAN, 0), canonical.run_digest(self.PLAN, 1))
        self.assertNotEqual(canonical.run_digest(self.PLAN, 0), canonical.run_digest("00" * 32, 0))
        # the raw 32 bytes, not the 64 hex characters, follow the prefix
        self.assertNotEqual(canonical.run_digest(self.PLAN, 0),
                            hashlib.sha256(b"detsim-run/1\x00" + self.PLAN.encode() + bytes(4)).hexdigest())

    def test_refused_arguments(self):
        for plan_digest, replicate, code in ((self.PLAN, -1, "replicate-range"), (self.PLAN, 2 ** 32, "replicate-range"),
                                             (self.PLAN, True, "replicate-range"), (self.PLAN, "1", "replicate-range"),
                                             (self.PLAN.upper(), 0, "digest-format"), ("8f" * 31, 0, "digest-format"),
                                             (None, 0, "digest-format")):
            with self.subTest(plan_digest=plan_digest, replicate=replicate):
                with self.assertRaises(canonical.CanonicalError) as ctx:
                    canonical.run_digest(plan_digest, replicate)
                self.assertEqual(ctx.exception.code, code)

    def test_parse_replicate(self):
        self.assertEqual(canonical.parse_replicate("0"), 0)
        self.assertEqual(canonical.parse_replicate("4294967295"), 2 ** 32 - 1)
        for text in ("4294967296", "-1", "01", "+1", " 1", "1.0", "1e3", "\u0661", "", "99999999999", None):
            with self.subTest(text=text):
                with self.assertRaises(canonical.CanonicalError):
                    canonical.parse_replicate(text)


if __name__ == "__main__":
    unittest.main()
