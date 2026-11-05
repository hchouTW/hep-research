"""core/canonical (g4sim S1): the canonical/1 hash, its hash scope, decimal/1 and the two JSON readers.

Equivalence with the unmodified implementations (Section 7.2, S1 gate 2) is compared on a fixed input set, and a changed
separator must break it. The specification reader follows Section 6.5."""
from __future__ import annotations

import decimal
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "adapters" / "detector-simulation" / "assets"))

import detsim_canonical  # noqa: E402
from contracts import recipe_semantics, release_manifest  # noqa: E402
from core import canonical  # noqa: E402
from core.protected import revocation_log  # noqa: E402
from core.provider import hashing  # noqa: E402

FIXED_INPUTS = [
    None, True, False, 0, -1, 2 ** 53 - 1, "", "text", "μé中", 1.5, [], {}, [1, "a", None, [2.5]],
    {"b": 1, "a": 2}, {"é": 1, "z": 2, "a": [{"y": 1, "x": 2}]}, {"nested": {"deep": {"deeper": [True, False]}}},
    {"quote": "\"", "slash": "\\", "newline": "\n"},
]
SPEC_TYPES = {"/length_mm": "quantity", "/layers/*/thickness_mm": "quantity", "/n_events": "integer"}


class Equivalence(unittest.TestCase):
    def implementations(self):
        return {"recipe_semantics": recipe_semantics.canonical_sha256, "release_manifest": release_manifest.canonical_sha256,
                "revocation_log": revocation_log.canonical_sha256, "provider": hashing.canonical_sha256}

    def test_the_implementations_agree_on_the_fixed_inputs(self):
        for name, implementation in self.implementations().items():
            for value in FIXED_INPUTS:
                with self.subTest(implementation=name, value=value):
                    self.assertEqual(canonical.canonical_sha256(value), implementation(value))

    def test_a_changed_separator_breaks_the_agreement(self):
        def spaced(value):
            return json.dumps(value, sort_keys=True, separators=(", ", ":"), ensure_ascii=False)
        digest = hashlib.sha256(spaced([1, 2]).encode("utf-8")).hexdigest()
        self.assertNotEqual(digest, canonical.canonical_sha256([1, 2]))

    def test_the_provider_functions_are_re_exports(self):
        self.assertIs(hashing.canonical_json, canonical.canonical_json)
        self.assertIs(hashing.canonical_sha256, canonical.canonical_sha256)

    def test_the_provider_point_hash_is_unchanged(self):
        self.assertEqual(hashing.point_hash(None, "p", "1.0.0", {"x": 1}),
                         "8720a296ec68530c893afa5adc31d10ea34296dfb7973a2ae62f5dae7ceeb3c8")


class DetsimCrossCheck(unittest.TestCase):
    def test_the_detsim_functions_come_from_core(self):
        for name in ("check_hash_scope", "normalize_decimal", "load_json_strict", "CanonicalError"):
            self.assertIs(getattr(detsim_canonical, name), getattr(canonical, name))

    def test_the_cross_check_compares_two_implementations(self):
        self.assertIs(detsim_canonical.canonical_sha256, recipe_semantics.canonical_sha256)
        self.assertIsNot(detsim_canonical.canonical_sha256, canonical.canonical_sha256)

    def test_a_changed_serializer_is_caught_by_the_cross_check(self):
        def spaced(value):
            return json.dumps(value, sort_keys=True, separators=(", ", ":"), ensure_ascii=False)
        with mock.patch.object(detsim_canonical, "canonical_json", spaced):
            with self.assertRaises(RuntimeError):
                detsim_canonical.canonical_bytes([1, 2])


class HashScope(unittest.TestCase):
    def test_a_decimal_that_bypasses_the_reader_is_refused(self):
        issues = canonical.check_hash_scope({"length_mm": decimal.Decimal("53.0")})
        self.assertEqual([i["code"] for i in issues], ["unsupported-type"])


class SpecReader(unittest.TestCase):
    def load(self, text, types=None):
        return canonical.load_spec_json(text, SPEC_TYPES if types is None else types)

    def test_every_form_of_a_quantity_gives_one_string_and_one_hash(self):
        forms = [self.load('{"length_mm": %s}' % form) for form in ("53", "53.0", '"53"', "5.3e1", '"53.000"')]
        self.assertEqual({doc["length_mm"] for doc in forms}, {"5.3e1"})
        self.assertEqual(len({canonical.canonical_sha256(doc) for doc in forms}), 1)

    def test_a_long_literal_keeps_every_digit(self):
        digits = "1.2345678901234567890123456789012345"
        self.assertEqual(self.load('{"length_mm": %s}' % digits)["length_mm"], digits + "e0")

    def test_an_integer_field_takes_an_integral_value(self):
        self.assertEqual(self.load('{"n_events": 6.0}')["n_events"], 6)
        self.assertEqual(self.load('{"n_events": 6}')["n_events"], 6)
        self.assertEqual(self.load('{"n_events": 6e0}')["n_events"], 6)

    def test_a_fractional_value_in_an_integer_field_is_refused(self):
        with self.assertRaises(canonical.CanonicalError) as caught:
            self.load('{"n_events": 6.5}')
        self.assertEqual(caught.exception.code, "integer-field")

    def test_an_integer_out_of_range_is_refused(self):
        with self.assertRaises(canonical.CanonicalError) as caught:
            self.load('{"n_events": 9007199254740992}')
        self.assertEqual(caught.exception.code, "integer-range")

    def test_an_exponent_beyond_every_limit_is_refused_cleanly(self):
        for text in ('{"n_events": "1e99999999999999999999"}', '{"n_events": 1e99999999999999999999}'):
            with self.subTest(text=text), self.assertRaises(canonical.CanonicalError):
                self.load(text)

    def test_a_number_with_no_declared_type_is_refused(self):
        for text in ('{"other": 1}', '{"other": 1.5}', '{"layers": [{"other": 2}]}', "[1]", "1"):
            with self.subTest(text=text), self.assertRaises(canonical.CanonicalError) as caught:
                self.load(text)
            self.assertEqual(caught.exception.code, "undeclared-number")

    def test_a_wildcard_covers_each_array_item(self):
        doc = self.load('{"layers": [{"thickness_mm": 1.50}, {"thickness_mm": 2}]}')
        self.assertEqual([item["thickness_mm"] for item in doc["layers"]], ["1.5e0", "2e0"])

    def test_a_params_expression_stays_a_string(self):
        self.assertEqual(self.load('{"length_mm": "2 * pitch_mm"}')["length_mm"], "2 * pitch_mm")

    def test_a_boolean_or_null_in_a_typed_field_is_refused(self):
        for text in ('{"n_events": true}', '{"length_mm": null}', '{"n_events": [1]}'):
            with self.subTest(text=text), self.assertRaises(canonical.CanonicalError) as caught:
                self.load(text)
            self.assertEqual(caught.exception.code, "field-type")

    def test_duplicate_keys_and_nan_are_refused_while_parsing(self):
        for text, code in (('{"a": "x", "a": "y"}', "duplicate-key"), ('{"length_mm": NaN}', "nan-or-infinity"),
                           ('{"length_mm": Infinity}', "nan-or-infinity")):
            with self.subTest(text=text), self.assertRaises(canonical.CanonicalError) as caught:
                self.load(text)
            self.assertEqual(caught.exception.code, code)

    def test_the_result_is_checked_against_the_hash_scope(self):
        with self.assertRaises(canonical.CanonicalError) as caught:
            self.load('{"path": "/opt/data/file"}')
        self.assertEqual(caught.exception.code, "path-reference")

    def test_an_unhashed_key_is_exempt_and_nothing_else_is(self):
        self.assertEqual(canonical.load_spec_json('{"legacy": {"path": "/opt/data"}}', {}, unhashed=("legacy",))["legacy"]["path"], "/opt/data")
        with self.assertRaises(canonical.CanonicalError):
            canonical.load_spec_json('{"legacy": {}, "path": "/opt/data"}', {}, unhashed=("legacy",))

    def test_a_bad_type_table_is_refused(self):
        for table in ({"/a": "float"}, {"a": "integer"}, {"/a": "integer", "/*": "quantity"}):
            with self.subTest(table=table), self.assertRaises(canonical.CanonicalError) as caught:
                self.load('{"a": 1}', table)
            self.assertEqual(caught.exception.code, "field-type-table")

    def test_an_escaped_pointer_segment_matches_its_key(self):
        self.assertEqual(self.load('{"a/b": 1}', {"/a~1b": "integer"})["a/b"], 1)


if __name__ == "__main__":
    unittest.main()
