"""core/geometry foundations (g4sim S1): exact decimals, params, rotations, bitfields and the error bound.

Negative tests of Section 15.1 for this layer: a 32-bit copy-number field, a 55-bit segmentation field, one bit too few, two
levels sharing a stride, level widths totalling 65 bits, a 30 degree rotation, a placement at 1e6 mm."""
from __future__ import annotations

import sys
import unittest
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.geometry import bitfield, bound, numbers, params, rotation  # noqa: E402
from core.geometry.numbers import GeometryError  # noqa: E402


class Numbers(unittest.TestCase):
    def test_a_third_three_times_rounds_as_section_7_3_says(self):
        third = numbers.divide(D(1), D(3))
        self.assertEqual(numbers.add(numbers.add(third, third), third), D("0.9999999999999999999999999999999999"))

    def test_the_context_does_not_depend_on_the_ambient_one(self):
        import decimal
        with decimal.localcontext() as ambient:
            ambient.prec = 3
            self.assertEqual(len(str(numbers.divide(D(1), D(3)))), 36)

    def test_a_result_is_written_as_decimal_one(self):
        self.assertEqual(numbers.as_text(D("53.0")), "5.3e1")
        self.assertEqual(numbers.as_text(D("-0.0")), "0")


class Params(unittest.TestCase):
    def test_a_table_resolves_in_any_order(self):
        values = params.resolve({"pitch": "wrap + gap", "wrap": "w + 2*esr", "w": "20.0", "esr": "0.065", "gap": "0.2"})
        self.assertEqual(values["pitch"], D("20.330"))

    def test_precedence_and_unary_minus(self):
        self.assertEqual(params.evaluate("-a/2 - 0.1", {"a": D("1")}.__getitem__), D("-0.6"))
        self.assertEqual(params.evaluate("2*(1+3)", None), D(8))

    def test_an_exponent_is_part_of_a_literal(self):
        self.assertEqual(params.evaluate("1e-3 + 1", None), D("1.001"))

    def test_refusals(self):
        for table, code in (({"a": "b", "b": "a"}, "params-cycle"), ({"a": "missing"}, "params-unknown"),
                            ({"a": "1/0"}, "params-division"), ({"A": "1"}, "params-name"), ({"a": "2 ** 3"}, "params-syntax"),
                            ({"a": "__import__"}, "params-unknown"), ({"a": "(1"}, "params-syntax"), ({"a": "1 2"}, "params-syntax"),
                            ({"a": "1.2.3"}, "params-syntax"), ({"a": ""}, "params-syntax"), ({"a": "sin(1)"}, "params-unknown")):
            with self.subTest(table=table), self.assertRaises(GeometryError) as caught:
                params.resolve(table)
            self.assertEqual(caught.exception.code, code)

    def test_names_of_an_expression_are_listed(self):
        self.assertEqual(params.names_in("wrap/4 + 2*gap"), ["wrap", "gap"])


class Rotation(unittest.TestCase):
    def test_quarter_turns_are_integer_matrices(self):
        self.assertEqual(rotation.active_matrix({"axis": "z", "angle_deg": D(90)}), ((0, -1, 0), (1, 0, 0), (0, 0, 1)))
        self.assertEqual(rotation.active_matrix({"axis": "z", "angle_deg": D(-270)}),
                         rotation.active_matrix({"axis": "z", "angle_deg": D(90)}))

    def test_an_active_rotation_moves_the_point_the_right_way(self):
        matrix = rotation.active_matrix({"axis": "z", "angle_deg": D(90)})
        self.assertEqual(rotation.rotate(matrix, (D(1), D(0), D(0))), (D(0), D(1), D(0)))

    def test_passive_is_the_inverse_of_active(self):
        for angles in ((90, 0, 0), (0, 90, 0), (90, 90, 0), (90, 180, 270)):
            matrix = rotation.active_matrix({"zyx_deg": [D(a) for a in angles]})
            self.assertEqual(rotation.product(matrix, rotation.passive_matrix(matrix)), rotation.IDENTITY)

    def test_thirty_degrees_gives_decimals_and_a_right_angle_integers(self):
        self.assertFalse(rotation.is_exact(rotation.active_matrix({"axis": "z", "angle_deg": D(30)})))
        self.assertTrue(rotation.is_exact(rotation.active_matrix({"axis": "z", "angle_deg": D(90)})))


class Bitfield(unittest.TestCase):
    def test_a_layout_does_not_depend_on_key_order(self):
        self.assertEqual(bitfield.layout({"i": 3, "j": 3, "z": 6}, {"i", "j"}), bitfield.layout({"z": 6, "j": 3, "i": 3}, {"i", "j"}))

    def test_strides_follow_the_widths(self):
        self.assertEqual([f["stride"] for f in bitfield.layout({"i": 3, "j": 3, "z": 6}, {"i", "j"})], [1, 8, 64])

    def test_limits_of_section_6_2_6(self):
        bitfield.layout({"a": 31}, {"a"})
        bitfield.layout({"a": 53}, set())
        for fields, copy_fields, code in (({"a": 32}, {"a"}, "bitfield-width"), ({"a": 55}, set(), "bitfield-width"),
                                          ({"a": 53, "b": 12}, set(), "bitfield-stride"),
                                          ({"a": 0}, set(), "bitfield-width"), ({"a": True}, set(), "bitfield-width")):
            with self.subTest(fields=fields), self.assertRaises(GeometryError) as caught:
                bitfield.layout(fields, copy_fields)
            self.assertEqual(caught.exception.code, code)

    def test_one_bit_too_few_is_refused(self):
        fields = bitfield.layout({"i": 3}, {"i"})
        bitfield.check_range(fields, {"i": 8})
        with self.assertRaises(GeometryError) as caught:
            bitfield.check_range(fields, {"i": 9})
        self.assertEqual(caught.exception.code, "bitfield-range")

    def test_level_widths_totalling_65_bits_are_refused(self):
        self.assertEqual(bitfield.level_strides([3, 4, 5]), [1, 8, 128])
        with self.assertRaises(GeometryError) as caught:
            bitfield.level_strides([31, 21, 13])
        self.assertEqual(caught.exception.code, "volume-width")

    def test_a_stride_beyond_the_integer_limit_is_refused(self):
        with self.assertRaises(GeometryError) as caught:
            bitfield.level_strides([31, 22, 1])
        self.assertEqual(caught.exception.code, "volume-stride")

    def test_two_levels_sharing_a_stride_are_refused(self):
        with self.assertRaises(GeometryError):
            bitfield.check_strides([1, 8, 8])


class ErrorBound(unittest.TestCase):
    def test_the_examples_of_section_7_3(self):
        limit = Fraction(numbers.BOUND_LIMIT_MM)
        self.assertLessEqual(bound.error_bound(D(20000), [False] * 26), limit)
        self.assertGreater(bound.error_bound(D(20000), [False] * 27), limit)
        self.assertLessEqual(bound.error_bound(D(20000), [True] * 2), limit)
        self.assertGreater(bound.error_bound(D(20000), [True] * 3), limit)

    def test_a_placement_at_a_million_mm_fails_even_at_depth_zero(self):
        self.assertGreater(bound.error_bound(D(1000000), []), Fraction(numbers.BOUND_LIMIT_MM))


if __name__ == "__main__":
    unittest.main()
