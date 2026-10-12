"""Tests for core/stats/ validate_response.py. Mutation style: a valid response fixture
with one controlled defect per test, asserting the intended diagnostic code, plus
valid row- and column-normalized cases, closure summaries, and CLI exit codes.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "core" / "fixtures"
sys.path.insert(0, str(ROOT))
from core.stats import validate_response as vr  # noqa: E402

ASYM = [[0.7, 0.2, 0.0], [0.2, 0.6, 0.3], [0.1, 0.2, 0.7]]  # asymmetric, columns sum to 1


def valid():
    return json.loads((FIX / "response_valid.json").read_text(encoding="utf-8"))


def asym_doc(orientation="rows_reco_cols_truth"):
    doc = valid()
    doc["matrix"] = [list(r) for r in (ASYM if orientation == "rows_reco_cols_truth" else zip(*ASYM))]
    doc["metadata"]["orientation"] = orientation
    doc["metadata"]["underflow_overflow"] = "folded_into_edge_bins"
    del doc["underflow"], doc["overflow"], doc["closure"]
    return doc


def codes(result, kind="errors"):
    return {item["code"] for item in result[kind]}


class ValidResponseTests(unittest.TestCase):
    def test_valid_fixture_passes(self):
        result = vr.validate_response(valid())
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["physical_validity"], "not_assessed")
        self.assertEqual(result["metrics"]["numerical_rank"], 3)

    def test_column_normalized_asymmetric_passes(self):
        self.assertEqual(vr.validate_response(asym_doc())["status"], "pass")

    def test_row_normalized_orientation_passes(self):
        self.assertEqual(vr.validate_response(asym_doc("rows_truth_cols_reco"))["status"], "pass")

    def test_validation_does_not_modify_input(self):
        doc = asym_doc()
        before = copy.deepcopy(doc)
        vr.validate_response(doc)
        self.assertEqual(doc, before)


class OrientationTests(unittest.TestCase):
    def test_square_transposed_detected_by_normalization(self):
        doc = asym_doc()
        doc["metadata"]["orientation"] = "rows_truth_cols_reco"  # wrong label for the same numbers
        result = vr.validate_response(doc)
        self.assertIn("normalization.truth_sum", codes(result))
        self.assertIn("orientation.likely_transposed", codes(result))

    def test_nonsquare_shape_matches_opposite_orientation(self):
        doc = valid()
        doc["metadata"]["truth_axis"]["edges"] = [1, 2, 4]
        doc["matrix"] = [[0.5, 0.0], [0.4, 0.4], [0.1, 0.6]]
        doc["metadata"]["underflow_overflow"] = "folded_into_edge_bins"
        del doc["underflow"], doc["overflow"], doc["closure"]
        self.assertEqual(vr.validate_response(doc)["status"], "pass")
        doc["metadata"]["orientation"] = "rows_truth_cols_reco"
        self.assertIn("orientation.shape_transposed", codes(vr.validate_response(doc)))

    def test_dimension_mismatch_with_edges(self):
        doc = valid()
        doc["metadata"]["reco_axis"]["edges"] = [1, 2, 4, 8, 16]
        self.assertIn("dimensions.mismatch", codes(vr.validate_response(doc)))


class NormalizationAndBookkeepingTests(unittest.TestCase):
    def test_inefficient_matrix_labelled_conditional_fails_normalization(self):
        doc = asym_doc()
        doc["matrix"] = [[0.8 * x for x in row] for row in ASYM]
        self.assertIn("normalization.truth_sum", codes(vr.validate_response(doc)))

    def test_inefficient_matrix_labelled_includes_efficiency_passes(self):
        doc = asym_doc()
        doc["matrix"] = [[0.8 * x for x in row] for row in ASYM]
        doc["metadata"].update({"normalization": "includes_efficiency", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": False})
        result = vr.validate_response(doc)
        self.assertEqual(result["status"], "pass", result)
        for lost in result["metrics"]["inefficiency_per_truth_bin"]:
            self.assertAlmostEqual(lost, 0.2, places=9)

    def test_efficiency_counted_twice(self):
        doc = asym_doc()
        doc["matrix"] = [[0.8 * x for x in row] for row in ASYM]
        doc["metadata"].update({"normalization": "includes_efficiency", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": True})
        self.assertIn("double_counting.inefficiency", codes(vr.validate_response(doc)))

    def test_acceptance_counted_twice(self):
        doc = valid()
        doc["metadata"].update({"acceptance": "inside_matrix", "acceptance_applied_separately": True})
        self.assertIn("double_counting.acceptance", codes(vr.validate_response(doc)))

    def test_efficiency_never_applied(self):
        doc = valid()
        doc["metadata"]["efficiency_applied_separately"] = False
        self.assertIn("bookkeeping.inefficiency_not_applied", codes(vr.validate_response(doc)))

    def test_conditional_normalization_contradicts_inside_inefficiency(self):
        doc = valid()
        doc["metadata"]["inefficiency"] = "inside_matrix"
        doc["metadata"]["efficiency_applied_separately"] = False
        self.assertIn("metadata.inconsistent", codes(vr.validate_response(doc)))

    def test_includes_efficiency_with_unit_column_sums_is_flagged(self):
        doc = asym_doc()
        doc["metadata"].update({"normalization": "includes_efficiency", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": False})
        self.assertIn("double_counting.efficiency_not_visible", codes(vr.validate_response(doc), "warnings"))

    def test_includes_efficiency_with_sums_above_one_fails(self):
        doc = asym_doc()
        doc["matrix"] = [[1.2 * x for x in row] for row in ASYM]
        doc["metadata"].update({"normalization": "includes_efficiency", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": False})
        self.assertIn("normalization.exceeds_one", codes(vr.validate_response(doc)))

    def test_counts_exceeding_generated(self):
        doc = asym_doc()
        doc["matrix"] = [[100 * x for x in row] for row in ASYM]
        doc["metadata"].update({"normalization": "counts", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": False})
        doc["generated_per_truth_bin"] = [100, 50, 100]
        self.assertIn("normalization.exceeds_generated", codes(vr.validate_response(doc)))
        doc["generated_per_truth_bin"] = [100, 100, 100]
        self.assertEqual(vr.validate_response(doc)["status"], "pass")

    def test_probability_lost_outside_axes(self):
        doc = valid()
        doc["metadata"]["underflow_overflow"] = "not_represented"
        del doc["underflow"], doc["overflow"]
        result = vr.validate_response(doc)
        self.assertIn("normalization.truth_sum", codes(result))
        self.assertIn("overflow.lost_probability", codes(result))

    def test_explicit_flow_declared_without_vectors(self):
        doc = valid()
        del doc["underflow"]
        self.assertIn("overflow.vectors_missing", codes(vr.validate_response(doc), "warnings"))


class BinAndHoleTests(unittest.TestCase):
    # The next three tests used to assert errors with no declared use. Rank deficiency, fewer reco than truth
    # bins and an empty truth bin defeat unfolding but are legitimate for forward folding, so the error is now
    # tied to intended_use "unfolding" (and kept, with a warning to declare the use, when the use is absent).
    def test_empty_truth_bin(self):
        doc = asym_doc()
        for row in doc["matrix"]:
            row[1] = 0.0
        for use in ("unfolding", None):
            doc["metadata"].pop("intended_use", None)
            if use:
                doc["metadata"]["intended_use"] = use
            result = vr.validate_response(doc)
            self.assertIn("empty.truth_bin", codes(result))
        self.assertIn("metadata.intended_use_missing", codes(result, "warnings"))

    def test_empty_reco_bin(self):
        doc = asym_doc()
        doc["matrix"] = [[0.7, 0.2, 0.0], [0.0, 0.0, 0.0], [0.3, 0.8, 1.0]]
        result = vr.validate_response(doc)
        self.assertIn("empty.reco_bin", codes(result, "warnings"))

    def test_degenerate_truth_bins_are_not_identifiable(self):
        doc = asym_doc()
        doc["metadata"]["intended_use"] = "unfolding"
        doc["matrix"] = [[0.5, 0.5, 0.0], [0.5, 0.5, 0.3], [0.0, 0.0, 0.7]]
        self.assertIn("identifiability.rank_deficient", codes(vr.validate_response(doc)))
        del doc["metadata"]["intended_use"]
        result = vr.validate_response(doc)
        self.assertIn("identifiability.rank_deficient", codes(result))
        self.assertIn("metadata.intended_use_missing", codes(result, "warnings"))

    def test_fewer_reco_than_truth_bins(self):
        doc = asym_doc()
        doc["metadata"]["intended_use"] = "unfolding"
        doc["metadata"]["reco_axis"]["edges"] = [1, 4, 8]
        doc["matrix"] = [[0.9, 0.2, 0.0], [0.1, 0.8, 1.0]]
        self.assertIn("identifiability.underdetermined", codes(vr.validate_response(doc)))
        del doc["metadata"]["intended_use"]
        self.assertIn("identifiability.underdetermined", codes(vr.validate_response(doc)))

    def test_ill_conditioned_warns(self):
        doc = asym_doc()
        # truth bins 0 and 1 differ by 1e-5: identifiable in principle, hopeless in practice
        doc["matrix"] = [[0.5, 0.49999, 0.0], [0.5, 0.50001, 0.3], [0.0, 0.0, 0.7]]
        result = vr.validate_response(doc)
        self.assertNotIn("identifiability.rank_deficient", codes(result))
        self.assertIn("identifiability.ill_conditioned", codes(result, "warnings"))

    def test_negative_entries(self):
        doc = asym_doc()
        doc["matrix"][0][2] = -0.1
        doc["matrix"][2][2] = 0.8
        self.assertIn("entries.negative", codes(vr.validate_response(doc)))


class MetadataAndAxisTests(unittest.TestCase):
    def test_missing_metadata_fields(self):
        doc = valid()
        for key in ("orientation", "normalization", "underflow_overflow"):
            del doc["metadata"][key]
        result = vr.validate_response(doc)
        for key in ("orientation", "normalization", "underflow_overflow"):
            self.assertIn(f"metadata.{key}", codes(result))

    def test_no_metadata_object(self):
        self.assertIn("metadata.missing", codes(vr.validate_response({"matrix": [[1.0]]})))

    def test_axis_variable_mismatch_needs_declared_conversion(self):
        doc = valid()
        doc["metadata"]["reco_axis"].update({"variable": "total_energy", "unit": "GeV"})
        self.assertIn("axes.variable_mismatch", codes(vr.validate_response(doc)))
        doc["metadata"]["variable_conversion"] = "E from ECAL; R = E for |Z| = 1 leptons"
        self.assertNotIn("axes.variable_mismatch", codes(vr.validate_response(doc)))

    def test_axis_unit_mismatch(self):
        doc = valid()
        doc["metadata"]["reco_axis"]["unit"] = "TV"
        self.assertIn("axes.unit_mismatch", codes(vr.validate_response(doc)))

    def test_non_monotonic_edges(self):
        doc = valid()
        doc["metadata"]["truth_axis"]["edges"] = [1, 4, 2, 8]
        self.assertIn("edges.truth_axis", codes(vr.validate_response(doc)))

    def test_malformed_matrix(self):
        doc = valid()
        doc["matrix"][1] = [0.1, 0.8]
        self.assertIn("shape.ragged", codes(vr.validate_response(doc)))
        doc = valid()
        doc["matrix"][1][1] = "x"
        self.assertIn("entries.nonfinite", codes(vr.validate_response(doc)))


class ClosureTests(unittest.TestCase):
    def test_pull_summary_matches_hand_calculation(self):
        closure = vr.validate_response(valid())["metrics"]["closure"]
        self.assertEqual(closure["predicted_reco"], [89.0, 90.0, 73.0])
        self.assertEqual(closure["ndof"], 3)
        self.assertAlmostEqual(closure["chi2"], 3 ** 2 / 89 + 2 ** 2 / 90 + 2 ** 2 / 73, places=9)
        self.assertEqual(closure["sigma_source"], "Poisson sqrt(predicted)")
        self.assertIn("selected-event truth", closure["truth_interpretation"])

    def test_supplied_sigma_is_used_and_large_pull_warns(self):
        doc = valid()
        doc["closure"]["reco_sigma"] = [0.5, 0.5, 0.5]
        result = vr.validate_response(doc)
        self.assertIn("closure.large_pull", codes(result, "warnings"))
        self.assertEqual(result["metrics"]["closure"]["sigma_source"], "supplied reco_sigma")

    def test_perfect_closure_is_still_not_physical_validity(self):
        doc = valid()
        doc["closure"]["reco"] = [89, 90, 73]
        result = vr.validate_response(doc)
        self.assertAlmostEqual(result["metrics"]["closure"]["chi2"], 0.0, places=12)
        self.assertEqual(result["physical_validity"], "not_assessed")

    def test_malformed_closure(self):
        doc = valid()
        doc["closure"]["truth"] = [1, 2]
        self.assertIn("closure.malformed", codes(vr.validate_response(doc)))



def counts_doc():
    """The review's 2x2 counts response: M = [[80, 10], [20, 90]] from 100 generated events per truth bin."""
    axis = {"variable": "E", "unit": "GeV", "edges": [0, 1, 2]}
    return {"metadata": {"truth_axis": dict(axis), "reco_axis": dict(axis), "orientation": "rows_reco_cols_truth",
                         "normalization": "counts", "inefficiency": "inside_matrix", "acceptance": "outside_matrix",
                         "underflow_overflow": "not_represented", "efficiency_applied_separately": False,
                         "acceptance_applied_separately": True, "intended_use": "forward_folding"},
            "matrix": [[80, 10], [20, 90]], "generated_per_truth_bin": [100, 100],
            "closure": {"truth": [100, 100], "reco": [90, 110]}}


class CountsClosureTests(unittest.TestCase):
    def test_counts_closure_divides_by_generated(self):
        result = vr.validate_response(counts_doc())
        self.assertEqual(result["metrics"]["closure"]["predicted_reco"], [90.0, 110.0])
        self.assertNotIn("closure.large_pull", codes(result, "warnings"))

    def test_counts_and_probability_representations_fold_alike(self):
        prob = counts_doc()
        prob["metadata"]["normalization"] = "includes_efficiency"
        prob["matrix"] = [[0.8, 0.1], [0.2, 0.9]]
        del prob["generated_per_truth_bin"]
        for truth in ([100, 100], [37.5, 812.25]):
            a, b = counts_doc(), copy.deepcopy(prob)
            a["closure"]["truth"] = b["closure"]["truth"] = truth
            pa = vr.validate_response(a)["metrics"]["closure"]["predicted_reco"]
            pb = vr.validate_response(b)["metrics"]["closure"]["predicted_reco"]
            for x, y in zip(pa, pb):
                self.assertLess(abs(x - y), 1e-12)

    def test_counts_closure_without_generated_is_not_assessable(self):
        doc = counts_doc()
        del doc["generated_per_truth_bin"]
        closure = vr.validate_response(doc)["metrics"]["closure"]
        self.assertEqual(closure["status"], "not_assessable")
        self.assertIn("generated_per_truth_bin", closure["reason"])
        self.assertNotIn("predicted_reco", closure)

    def test_negative_closure_truth_is_an_error(self):
        doc = counts_doc()
        doc["closure"]["truth"] = [100, -5]
        self.assertIn("closure.negative_truth", codes(vr.validate_response(doc)))


class IntendedUseTests(unittest.TestCase):
    def folding_doc(self):
        doc = asym_doc()
        doc["metadata"]["intended_use"] = "forward_folding"
        doc["closure"] = {"truth": [100, 90, 80], "reco": [88, 90, 92]}
        return doc

    def test_rectangular_response_is_valid_for_forward_folding(self):
        doc = self.folding_doc()
        doc["metadata"].update({"normalization": "includes_efficiency", "inefficiency": "inside_matrix",
                                "efficiency_applied_separately": False})
        doc["metadata"]["truth_axis"]["edges"] = [1, 2, 4]
        doc["metadata"]["reco_axis"]["edges"] = [1, 4]
        doc["matrix"] = [[0.8, 0.7]]
        doc["closure"] = {"truth": [100, 100], "reco": [150]}
        result = vr.validate_response(doc)
        self.assertNotEqual(result["status"], "fail", result["errors"])
        self.assertTrue({"identifiability.underdetermined", "identifiability.rank_deficient"} <= codes(result, "warnings"))
        self.assertEqual(result["metrics"]["closure"]["predicted_reco"], [150.0])

    def test_zero_efficiency_truth_bin_is_valid_for_forward_folding(self):
        doc = self.folding_doc()
        for row in doc["matrix"]:
            row[1] = 0.0
        doc["closure"]["reco"] = [70, 30, 70]
        result = vr.validate_response(doc)
        self.assertNotEqual(result["status"], "fail", result["errors"])
        self.assertIn("empty.truth_bin", codes(result, "warnings"))
        self.assertIn("closure", result["metrics"])

    def test_unknown_intended_use_is_an_error(self):
        doc = self.folding_doc()
        doc["metadata"]["intended_use"] = "plotting"
        self.assertIn("metadata.intended_use", codes(vr.validate_response(doc)))

    def test_identifiability_errors_no_longer_skip_closure(self):
        doc = asym_doc()
        doc["metadata"]["intended_use"] = "unfolding"
        doc["matrix"] = [[0.5, 0.5, 0.0], [0.5, 0.5, 0.3], [0.0, 0.0, 0.7]]
        doc["closure"] = {"truth": [100, 100, 100], "reco": [100, 130, 70]}
        result = vr.validate_response(doc)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["metrics"]["closure"]["predicted_reco"], [100.0, 130.0, 70.0])

    def test_conditional_on_selected_with_acceptance_inside_is_inconsistent(self):
        doc = valid()
        doc["metadata"].update({"acceptance": "inside_matrix", "acceptance_applied_separately": False})
        self.assertIn("metadata.inconsistent", codes(vr.validate_response(doc)))

class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vr.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(str(FIX / "response_valid.json"))[0], 0)
        doc = valid()
        doc["metadata"]["efficiency_applied_separately"] = False
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(Path(fh.name).unlink)
        code, out = self.run_cli(fh.name)
        self.assertEqual((code, out["status"]), (1, "fail"))
        self.assertEqual(self.run_cli(str(FIX / "missing.json"))[0], 2)


if __name__ == "__main__":
    unittest.main()
