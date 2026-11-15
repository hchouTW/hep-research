"""Witness W5 of the reconstruction contracts (plan Section 12, contract-map.md): images, response operators and
non-unique inversion, and the contract part of A20 (retain response, background and multiple solutions, hand off the
inversion). The operator stays a typed native reference: ext_response.json does not fit it and needs no new form.
Passing proves the stated contract behaviour only. Synthetic documents only."""
import json
import random
import sys
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import response_adapter  # noqa: E402
from contracts.reconstruction import matrix_rank, read_sidecar  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402
from tests.contracts.reconstruction_fixtures import code_list, inversion_product, inversion_witness  # noqa: E402


class NonUniqueInversion(unittest.TestCase):
    def setUp(self):
        self.inversion = inversion_witness()

    def refused(self):
        return code_list(read_sidecar(inversion_product(self.inversion)))

    def test_both_solutions_and_the_null_direction_are_retained(self):
        self.assertEqual(self.refused(), [])
        self.assertEqual(matrix_rank(self.inversion["operator"]["matrix"]), 2)

    def test_a_wrong_solution_is_caught(self):
        self.inversion["solutions"][1] = [0, 0, 2]
        self.assertIn("reconstruction.inversion.solution_mismatch", self.refused())

    def test_a_wrong_null_direction_is_caught(self):
        self.inversion["null_directions"] = [[1, 1, 1]]
        self.assertIn("reconstruction.inversion.null_direction_invalid", self.refused())

    def test_ragged_null_directions_are_a_finding(self):
        """M10: the count equals the nullity, and the row has the wrong length."""
        self.inversion["null_directions"] = [[1, 1]]
        self.assertIn("reconstruction.inversion.null_direction_invalid", self.refused())
        self.inversion["operator"]["matrix"] = [[1, 0, 1, 0], [0, 1, 1, 0]]
        self.inversion["solutions"] = [[1, 1, 0, 0]]
        self.inversion["null_directions"] = [[1, 1, -1, 0], [0, 0, 0]]
        self.assertIn("reconstruction.inversion.null_direction_invalid", self.refused())

    def test_a_dropped_null_direction_is_caught(self):
        self.inversion["null_directions"] = []
        self.assertIn("reconstruction.inversion.null_space_incomplete", self.refused())

    def test_one_solution_as_the_unique_truth_is_caught(self):
        self.inversion.update({"solutions": [[1, 1, 0]], "uniqueness_claim": True})
        self.assertIn("reconstruction.inversion.unique_claim", self.refused())

    def test_a_prior_that_selects_one_solution_is_stated(self):
        self.inversion["selected_solution"] = 1
        self.assertIn("reconstruction.inversion.selection_without_prior", self.refused())
        self.inversion["prior"] = "smallest norm, declared before the fit"
        self.assertIn("reconstruction.inversion.undetermined_missing", self.refused())
        self.inversion["undetermined_components"] = [[1, 1, -1]]
        self.assertEqual(self.refused(), [])

    def test_a_selected_index_must_exist(self):
        self.inversion.update({"selected_solution": 5, "prior": "stated", "undetermined_components": [[1, 1, -1]]})
        self.assertIn("reconstruction.inversion.selection_unresolved", self.refused())

    def test_full_rank_operator_may_claim_uniqueness(self):
        self.inversion["operator"]["matrix"] = [[1, 0], [0, 1]]
        self.inversion.update({"solutions": [[1, 1]], "null_directions": [], "uniqueness_claim": True})
        self.assertEqual(self.refused(), [])


class FloatComparator(unittest.TestCase):
    """M1: Section 14.1 fixes a numerical comparison by quantities, matching rules and tolerances. Equality is relative to the
    size of each sum's terms, and rank counts singular values above the tolerance times the largest."""

    OPERATOR = [[0.1, 0.7, 0.8], [0.3, 0.2, 0.5]]
    NEAR_SINGULAR = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]  # singular values 1.68, 0.107, 7e-17

    def honest_record(self):
        first, direction = [1.3, 0.4, 0.2], [1.0, 1.0, -1.0]
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = self.OPERATOR
        inversion.update({"observed": [sum(a * b for a, b in zip(row, first)) for row in self.OPERATOR],
                          "solutions": [first, [a + 0.5 * b for a, b in zip(first, direction)]], "null_directions": [direction]})
        return inversion

    def near_singular_record(self, **fields):
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = self.NEAR_SINGULAR
        inversion.update({"observed": [0.1, 0.4, 0.7], "solutions": [[1, 0, 0]], "null_directions": [[1, -2, 1]]})
        inversion.update(fields)
        return inversion

    def test_an_honest_float_record_is_accepted(self):
        self.assertEqual(code_list(read_sidecar(inversion_product(self.honest_record()))), [])

    def test_a_small_error_in_a_solution_still_fails(self):
        inversion = self.honest_record()
        inversion["solutions"][1][0] *= 1 + 1e-9
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.solution_mismatch"])

    def test_a_small_error_in_a_null_direction_still_fails(self):
        inversion = self.honest_record()
        inversion["null_directions"] = [[1.0, 1.0 + 1e-9, -1.0]]
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.null_direction_invalid"])

    def test_the_true_null_direction_of_a_numerically_rank_two_operator_is_accepted(self):
        self.assertEqual(code_list(read_sidecar(inversion_product(self.near_singular_record()))), [])

    def test_a_unique_claim_on_a_numerically_rank_two_operator_is_refused(self):
        """W5's negative, on a one-pixel source."""
        inversion = self.near_singular_record(null_directions=[], uniqueness_claim=True)
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.null_space_incomplete", "reconstruction.inversion.unique_claim"])

    def test_a_small_real_singular_value_is_not_rounding(self):
        """The bound follows the tolerance: 1e-6 of the largest is a real direction at 1e-12."""
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = [[1, 0], [0, 1e-6]]
        inversion.update({"observed": [1, 1e-6], "solutions": [[1, 1]], "null_directions": [], "uniqueness_claim": True})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), [])

    def test_the_comparator_is_required_and_capped(self):
        inversion = inversion_witness()
        del inversion["comparator"]
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["schema.required"])
        inversion["comparator"] = {"relative_tolerance": 1.0}
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["schema.maximum"])


class OperatorMeaning(unittest.TestCase):
    def setUp(self):
        self.inversion = inversion_witness()

    def refused(self):
        return code_list(read_sidecar(inversion_product(self.inversion)))

    def test_column_normalizing_by_default_is_caught(self):
        self.inversion["operator"]["normalization"] = {"kind": "column", "basis": "default"}
        self.assertIn("reconstruction.inversion.default_normalization", self.refused())

    def test_operator_declares_quantity_and_unit_first(self):
        for field in ("input_quantity", "output_quantity", "normalization", "interpretation"):
            inversion = inversion_witness()
            del inversion["operator"][field]
            self.assertTrue(code_list(read_sidecar(inversion_product(inversion))), field)

    def test_ragged_operator_is_refused(self):
        self.inversion["operator"]["matrix"] = [[1, 0, 1], [0, 1]]
        self.assertIn("reconstruction.inversion.dimension_mismatch", self.refused())

    def test_probability_label_is_checked_against_the_columns(self):
        self.inversion["operator"]["interpretation"] = "probability"
        self.assertIn("reconstruction.inversion.not_a_probability", self.refused(), "a column of A sums to 2")

    def test_a_matrix_adapter_does_not_accept_it_as_a_response(self):
        document = json.loads((ROOT / "contracts/fixtures/artifacts/valid/response.json").read_text(encoding="utf-8"))
        extension = dict(document["extension"], normalization="unnormalized", matrix=inversion_witness()["operator"]["matrix"])
        converted = response_adapter.to_validator_input(extension, base_dir=ROOT, contract_version=document["contract_version"])
        self.assertFalse(converted["ok"], "ext_response gives no meaning to a non-probability operator, so it stays a native reference")
        self.assertIn("normalization", [error["field"] for error in converted["errors"]])

    def test_probability_readings_of_the_operator_fail_too(self):
        """Minor 6: with a matching three-bin truth axis, the probability normalizations fail in the validator."""
        document = json.loads((ROOT / "contracts/fixtures/artifacts/valid/response_v28.json").read_text(encoding="utf-8"))
        for normalization in ("joint_counts", "conditional_on_generated"):
            extension = dict(document["extension"], normalization=normalization, matrix=inversion_witness()["operator"]["matrix"])
            extension["truth_axis"] = dict(extension["truth_axis"], edges=[-1, 0, 0.5, 1])
            if normalization == "joint_counts":
                extension.update({"inefficiency": "outside_matrix", "generated_per_truth_bin": [1, 1, 2]})
            converted = response_adapter.to_validator_input(extension, base_dir=ROOT, contract_version=document["contract_version"])
            self.assertTrue(converted["ok"], (normalization, converted["errors"]))
            self.assertEqual(validate_response(converted["input"])["status"], "fail", normalization)


class ResponseImage(unittest.TestCase):
    """A20, contract part."""

    def test_response_background_and_handoff_are_required(self):
        for field in ("response_ref", "background_ref", "handoff", "native_image"):
            inversion = inversion_witness()
            del inversion[field]
            self.assertTrue(code_list(read_sidecar(inversion_product(inversion))), field)


class UnitInvariantRank(unittest.TestCase):
    """Re-review 3 N1: rank is judged on unit-norm columns, so the same operator in other parameter units reads the same.
    A truly rank-deficient operator and a numerically rank-two one stay refused when they claim uniqueness."""

    def test_a_full_rank_operator_with_a_small_unit_column_may_claim_uniqueness(self):
        """The review's case at the ceiling: the second parameter is stated in a unit 1e11 times too large for its column."""
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = [[1, 1e-11], [1, 3e-11]]
        inversion.update({"observed": [1 + 1e-11, 1 + 3e-11], "solutions": [[1, 1]], "null_directions": [], "uniqueness_claim": True,
                          "comparator": {"relative_tolerance": 1e-9}})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), [])
        self.assertEqual(matrix_rank([[1, 1e-11], [1, 3e-11]], 1e-9), matrix_rank([[1, 1], [1, 3]], 1e-9))

    def test_a_numerically_rank_two_operator_stays_rank_two_in_other_units(self):
        matrix = [[row[0] * 1e-12, row[1] * 1e-12, row[2]] for row in FloatComparator.NEAR_SINGULAR]
        self.assertEqual(matrix_rank(matrix, 1e-12), matrix_rank(FloatComparator.NEAR_SINGULAR, 1e-12))
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = matrix
        inversion.update({"observed": [0.1, 0.4, 0.7], "solutions": [[1e12, 0, 0]], "null_directions": [[1e12, -2e12, 1]]})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), [])
        inversion.update({"null_directions": [], "uniqueness_claim": True})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.null_space_incomplete", "reconstruction.inversion.unique_claim"])

    def test_a_truly_rank_deficient_operator_stays_refused(self):
        inversion = inversion_witness()
        inversion.update({"null_directions": [], "uniqueness_claim": True})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.null_space_incomplete", "reconstruction.inversion.unique_claim"])

    def test_rank_does_not_depend_on_units(self):
        """The review's designs: a quadratic in time with a 1 ns step in seconds, an order-5 polynomial in sample index, a
        template in V per electron beside a baseline in V; and the degenerate cases keep their rank."""
        quadratic = [[1.0, index * 1e-9, (index * 1e-9) ** 2] for index in range(16)]
        polynomial = [[float(index * 64) ** power for power in range(6)] for index in range(16)]
        electrons = [[1.0, 1.6e-12 * (index % 5)] for index in range(16)]
        for matrix, expected in ((quadratic, 3), (polynomial, 6), (electrons, 2), (FloatComparator.NEAR_SINGULAR, 2),
                                 ([[0.1, 0.3], [0.2, 0.6], [0.3, 0.9]], 1), ([[1, 1], [0, 1], [0, 1]], 2), ([[0, 1], [0, 1]], 1), ([[1, 0, 1], [0, 1, 1]], 2)):
            self.assertEqual(matrix_rank(matrix, 1e-9), expected, matrix)

    def test_a_tolerance_below_rounding_is_refused(self):
        """Re-review 3 minor 1: below the rounding of its own terms a tolerance would buy a rank (Section 9.5)."""
        inversion = inversion_witness()
        inversion["operator"]["matrix"] = FloatComparator.NEAR_SINGULAR
        inversion.update({"observed": [0.1, 0.4, 0.7], "solutions": [[1, 0, 0]], "null_directions": [], "uniqueness_claim": True,
                          "comparator": {"relative_tolerance": 1e-17}})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["schema.minimum"])
        inversion["comparator"] = {"relative_tolerance": 1e-15}
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.null_space_incomplete", "reconstruction.inversion.unique_claim"])


class ProbabilitySum(unittest.TestCase):
    """Re-review 3 N3: a column sum is compared with the record's comparator times the number of terms times their size."""

    def normalized(self, seed):
        generator = random.Random(seed)
        matrix = numpy.array([[generator.random() for _ in range(6)] for _ in range(6)])
        matrix = matrix / matrix.sum(axis=0)
        inversion = inversion_witness()
        inversion["operator"].update({"matrix": matrix.tolist(), "interpretation": "probability", "normalization": {"kind": "column", "basis": "declared"}})
        inversion.update({"observed": matrix.sum(axis=1).tolist(), "solutions": [[1.0] * 6], "null_directions": []})
        return inversion

    def test_honest_column_normalized_operators_pass(self):
        refused = [seed for seed in range(200) if code_list(read_sidecar(inversion_product(self.normalized(seed))))]
        self.assertEqual(refused, [])

    def test_a_sum_that_is_really_wrong_fails(self):
        inversion = self.normalized(0)
        inversion["operator"]["matrix"][0][0] += 1e-6
        self.assertIn("reconstruction.inversion.not_a_probability", code_list(read_sidecar(inversion_product(inversion))))

    def test_a_negative_entry_fails(self):
        inversion = self.normalized(0)
        inversion["operator"]["matrix"][0][0] = -1e-17
        self.assertIn("reconstruction.inversion.not_a_probability", code_list(read_sidecar(inversion_product(inversion))))

    def test_a_single_precision_operator_is_refused_at_the_ceiling(self):
        """Re-review 4 minor 3, a stated limit: an operator normalized in float32 exceeds 1 by up to about 2e-7, a true
        reading of the stored numbers; renormalizing in double precision is the way to state it."""
        matrix = numpy.random.default_rng(0).random((30, 30)).astype(numpy.float32)
        matrix = (matrix / matrix.sum(axis=0)).astype(float)
        inversion = inversion_witness()
        inversion["operator"].update({"matrix": matrix.tolist(), "interpretation": "probability", "normalization": {"kind": "column", "basis": "declared"}})
        inversion.update({"observed": matrix.sum(axis=1).tolist(), "solutions": [[1.0] * 30], "null_directions": [], "comparator": {"relative_tolerance": 1e-9}})
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), ["reconstruction.inversion.not_a_probability"])
        renormalized = matrix / matrix.sum(axis=0)
        inversion["operator"]["matrix"], inversion["observed"] = renormalized.tolist(), renormalized.sum(axis=1).tolist()
        self.assertEqual(code_list(read_sidecar(inversion_product(inversion))), [])


if __name__ == "__main__":
    unittest.main()
