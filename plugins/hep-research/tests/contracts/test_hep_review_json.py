"""hep-review strict JSON ingestion and the hep-review-metadata/1 encoding (hep-review spec v9 sections 10.2-10.3).

Cases P02, P26, P34, N21, N39: every row of the section 10.2 table is exercised, and the encoder is held to the gold
byte vectors in contracts/fixtures/hep_review/byte_vectors.json, which were written by hand from the rules."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import hep_review as H  # noqa: E402

VECTORS = json.loads((ROOT / "contracts" / "fixtures" / "hep_review" / "byte_vectors.json").read_text(encoding="utf-8"))


class GoldVectors(unittest.TestCase):
    def test_accepted_vectors_encode_to_the_gold_bytes(self):
        for v in VECTORS["accept"]:
            with self.subTest(v["name"]):
                value = H.ingest_json(v["input"].encode("utf-8"))
                self.assertEqual(H.encode(value), bytes.fromhex(v["expected_hex"]))

    def test_rejected_texts_carry_their_code(self):
        for v in VECTORS["reject"]:
            with self.subTest(v["name"]):
                with self.assertRaises(H.IngestError) as cm:
                    H.ingest_json(v["input"].encode("utf-8"))
                self.assertEqual(cm.exception.code, v["code"])

    def test_rejected_bytes_carry_their_code(self):
        for v in VECTORS["reject_bytes_hex"]:
            with self.subTest(v["name"]):
                with self.assertRaises(H.IngestError) as cm:
                    H.ingest_json(bytes.fromhex(v["hex"]))
                self.assertEqual(cm.exception.code, v["code"])

    def test_vectors_cover_the_section_10_3_list(self):
        names = {v["name"] for v in VECTORS["accept"]} | {v["name"] for v in VECTORS["reject"]}
        for needed in ("control_characters", "slash_quote_backslash", "chinese_and_emoji", "combining_not_normalized",
                       "safe_integer_boundaries", "minus_zero", "nested_objects_sorted_arrays_kept",
                       "duplicate_key_escaped"):
            self.assertIn(needed, names)


class Ingestion(unittest.TestCase):
    def test_size_limit_is_checked_before_decoding(self):
        with self.assertRaises(H.IngestError) as cm:
            H.ingest_json(b"[" + b"1," * 100 + b"1]", max_bytes=50)
        self.assertEqual(cm.exception.code, "json.too_large")

    def test_depth_limit_rejects_without_recursion_error(self):
        deep = b"[" * 200_000 + b"]" * 200_000
        with self.assertRaises(H.IngestError) as cm:
            H.ingest_json(deep, max_bytes=10_000_000)
        self.assertEqual(cm.exception.code, "json.too_deep")
        ok = b"[" * 10 + b"]" * 10
        self.assertEqual(H.ingest_json(ok, max_depth=10), [[[[[[[[[[]]]]]]]]]])
        with self.assertRaises(H.IngestError):
            H.ingest_json(ok, max_depth=9)

    def test_depth_scan_skips_string_contents(self):
        self.assertEqual(H.ingest_json(b'{"a":"[[[[[[[[[[[[[[["}', max_depth=2), {"a": "[[[[[[[[[[[[[[["})
        self.assertEqual(H.ingest_json(b'{"a":"\\"[[[["}', max_depth=2), {"a": '"[[[['})

    def test_never_passes_bytes_to_json_loads(self):
        # raw bytes json.loads would accept (BOM, UTF-16) are rejected here
        with self.assertRaises(H.IngestError):
            H.ingest_json('{"a":1}'.encode("utf-16"))
        with self.assertRaises(H.IngestError):
            H.ingest_json('{"a":1}'.encode("utf-32"))

    def test_str_input_is_refused(self):
        with self.assertRaises(TypeError):
            H.ingest_json('{"a":1}')  # type: ignore[arg-type]

    def test_integers_and_plain_values_accepted(self):
        self.assertEqual(H.ingest_json(b'{"n":1,"t":true,"s":"x"}'), {"n": 1, "t": True, "s": "x"})

    def test_duplicate_keys_seen_before_dict_is_built(self):
        # case P26: a dict that swallows duplicates and is then canonicalized is not strict ingestion
        swallowed = json.loads('{"id":1,"\\u0069d":2}')
        self.assertEqual(swallowed, {"id": 2})
        with self.assertRaises(H.IngestError):
            H.ingest_json(b'{"id":1,"\\u0069d":2}')

    def test_nested_duplicate_and_surrogate_found_anywhere(self):
        with self.assertRaises(H.IngestError):
            H.ingest_json(b'{"a":[{"b":1,"b":2}]}')
        with self.assertRaises(H.IngestError):
            H.ingest_json(b'{"a":[{"b":["ok","\\udfff"]}]}')


class TypeChecks(unittest.TestCase):
    def test_bool_is_not_an_integer(self):
        # case N21: an integer field equal to true is rejected, never relying on isinstance
        self.assertTrue(H.is_int(3))
        self.assertFalse(H.is_int(True))
        self.assertFalse(H.is_int(False))
        self.assertFalse(H.is_int(3.0))


class Encoder(unittest.TestCase):
    def test_encoder_refuses_values_outside_the_domain(self):
        for bad in (1.5, float("nan"), 2 ** 53, -(2 ** 53), "\ud800", {1: "x"}, {"é": 1}, (1, 2), b"x"):
            with self.subTest(repr(bad)):
                with self.assertRaises(H.EncodeError):
                    H.encode(bad)

    def test_no_bom_no_whitespace_no_trailing_newline(self):
        b = H.encode({"b": [1, 2], "a": {"c": None}})
        self.assertEqual(b, b'{"a":{"c":null},"b":[1,2]}')

    def test_digest_is_sha256_of_the_encoding(self):
        import hashlib
        v = {"x": [1, "y"]}
        self.assertEqual(H.metadata_digest(v), hashlib.sha256(H.encode(v)).hexdigest())

    def test_round_trip_is_stable(self):
        for v in VECTORS["accept"]:
            b = H.encode(H.ingest_json(v["input"].encode("utf-8")))
            self.assertEqual(H.encode(H.ingest_json(b)), b)


if __name__ == "__main__":
    unittest.main()
