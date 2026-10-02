"""Tests for core/stats/ (ported from legacy ams-analysis tests): validate_covariance.py. Mutation style: start from the valid
fixture, introduce one controlled defect, and assert the intended diagnostic code.
Also checks that the supplied data are never modified and the CLI exit codes.
Run from the skill directory with `python3 -m unittest discover -s tests -v`."""
import contextlib
import copy
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "tests" / "core" / "fixtures"
sys.path.insert(0, str(ROOT))
from core.stats import validate_covariance as vc  # noqa: E402


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def codes(result, kind="errors"):
    return {item["code"] for item in result[kind]}


class EigenSolverTests(unittest.TestCase):
    def test_known_spectra(self):
        vals, _ = vc.jacobi_eigh([[2.0, 1.0], [1.0, 2.0]])
        self.assertAlmostEqual(vals[0], 1.0, places=12)
        self.assertAlmostEqual(vals[1], 3.0, places=12)
        vals, _ = vc.jacobi_eigh([[1, -0.9, -0.9], [-0.9, 1, -0.9], [-0.9, -0.9, 1]])
        for got, want in zip(vals, (-0.8, 1.9, 1.9)):
            self.assertAlmostEqual(got, want, places=12)

    def test_eigenvectors_reconstruct_matrix(self):
        a = [[4.0, 1.0, 0.5], [1.0, 9.0, 2.0], [0.5, 2.0, 16.0]]
        vals, vec = vc.jacobi_eigh(a)
        for i in range(3):
            for j in range(3):
                rebuilt = sum(vec[i][k] * vals[k] * vec[j][k] for k in range(3))
                self.assertAlmostEqual(rebuilt, a[i][j], places=10)


class ValidMatrixTests(unittest.TestCase):
    def test_valid_fixture_passes_with_no_findings(self):
        result = vc.validate_covariance(load("cov_valid.json"))
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["errors"] + result["warnings"], [])
        self.assertGreater(result["metrics"]["total"]["eigenvalue_min"], 0)
        self.assertFalse(result["input_modified"])

    def test_validation_does_not_modify_input(self):
        doc = load("cov_indefinite.json")
        before = copy.deepcopy(doc)
        vc.validate_covariance(doc, demo_clip=True)
        self.assertEqual(doc, before)


class DefectTests(unittest.TestCase):
    def mutate(self, edit):
        doc = load("cov_valid.json")
        edit(doc)
        return vc.validate_covariance(doc)

    def test_asymmetric(self):
        def edit(d): d["matrix"][0][1] += 0.1
        self.assertIn("symmetry", codes(self.mutate(edit)))

    def test_within_tolerance_asymmetry_is_not_an_error(self):
        def edit(d): d["matrix"][0][1] += 1e-12
        self.assertNotIn("symmetry", codes(self.mutate(edit)))

    def test_indefinite_with_all_correlations_inside_bounds(self):
        result = vc.validate_covariance(load("cov_indefinite.json"))
        self.assertEqual(result["status"], "fail")
        self.assertIn("not_psd", codes(result))
        self.assertNotIn("correlation_bound", codes(result))

    def test_negative_diagonal(self):
        def edit(d): d["matrix"][2][2] = -1.0
        self.assertIn("negative_diagonal", codes(self.mutate(edit)))

    def test_correlation_outside_physical_bounds(self):
        doc = {"labels": ["a", "b"], "kind": "relative", "units": "1", "matrix": [[1.0, 1.2], [1.2, 1.0]]}
        result = vc.validate_covariance(doc)
        self.assertIn("correlation_bound", codes(result))

    def test_zero_variance_row_with_covariance(self):
        def edit(d):
            d["matrix"][0][0] = 0.0
        self.assertIn("zero_variance_covariance", codes(self.mutate(edit)))

    def test_zero_variance_row_without_covariance_is_allowed(self):
        doc = {"labels": ["a", "b"], "kind": "absolute", "units": "u^2", "matrix": [[0.0, 0.0], [0.0, 4.0]]}
        result = vc.validate_covariance(doc)
        self.assertNotIn("zero_variance_covariance", codes(result))
        self.assertEqual(result["metrics"]["total"]["zero_variance_rows"], [0])

    def test_nearly_singular_warns_but_does_not_fail(self):
        doc = {"labels": ["a", "b"], "kind": "absolute", "units": "u^2", "matrix": [[1.0, 1.0], [1.0, 1.0 + 1e-12]]}
        result = vc.validate_covariance(doc)
        self.assertEqual(result["status"], "warn")
        self.assertIn("ill_conditioned", codes(result, "warnings"))
        self.assertGreater(result["metrics"]["total"]["condition_number"], 1e10)

    def test_roundoff_negative_eigenvalue_is_not_an_error(self):
        # rank-1 matrix built in floating point: eigenvalues 0 within round-off
        v = [0.1, 0.7, 1.3]
        doc = {"labels": ["a", "b", "c"], "kind": "absolute", "units": "u^2",
               "matrix": [[x * y for y in v] for x in v]}
        result = vc.validate_covariance(doc)
        self.assertNotIn("not_psd", codes(result))

    def test_small_negative_beyond_roundoff_but_within_stated_tolerance_warns(self):
        doc = {"labels": ["a", "b"], "kind": "absolute", "units": "u^2",
               "matrix": [[1.0, 1.0 + 1e-10], [1.0 + 1e-10, 1.0]], "tolerances": {"psd": 1e-6}}
        result = vc.validate_covariance(doc)
        self.assertIn("psd_small_negative", codes(result, "warnings"))
        self.assertNotIn("not_psd", codes(result))

    def test_non_square(self):
        def edit(d): d["matrix"][1] = [1.0, 9.0]
        self.assertIn("shape.non_square", codes(self.mutate(edit)))

    def test_malformed_entries(self):
        def edit(d): d["matrix"][1][1] = "nine"
        self.assertIn("entries.nonfinite", codes(self.mutate(edit)))

    def test_nonfinite_entry(self):
        def edit(d): d["matrix"][1][1] = float("nan")
        self.assertIn("entries.nonfinite", codes(self.mutate(edit)))

    def test_not_a_matrix(self):
        def edit(d): d["matrix"] = [1, 2, 3]
        self.assertIn("shape.malformed", codes(self.mutate(edit)))

    def test_label_dimension_and_duplicates(self):
        def short(d): d["labels"] = ["b0", "b1"]
        def dup(d): d["labels"] = ["b0", "b0", "b1"]
        self.assertIn("labels.dimension", codes(self.mutate(short)))
        self.assertIn("labels.duplicate", codes(self.mutate(dup)))

    def test_missing_metadata(self):
        def edit(d):
            del d["kind"]
            del d["units"]
        result = self.mutate(edit)
        self.assertIn("metadata.kind", codes(result))
        self.assertIn("metadata.units", codes(result, "warnings"))


class BlockTests(unittest.TestCase):
    def mutate(self, edit):
        doc = load("cov_valid.json")
        edit(doc)
        return vc.validate_covariance(doc)

    def test_blocks_that_do_not_sum_to_total(self):
        def edit(d): d["blocks"]["syst"][0][0] += 1.0
        self.assertIn("blocks.sum_mismatch", codes(self.mutate(edit)))

    def test_block_dimension_mismatch(self):
        def edit(d): d["blocks"]["stat"] = [[2.0, 0.0], [0.0, 5.0]]
        self.assertIn("blocks.dimension", codes(self.mutate(edit)))

    def test_defect_inside_one_block_is_attributed_to_it(self):
        def edit(d):
            d["blocks"]["syst"] = [[2.0, 3.0, 0.5], [3.0, 4.0, 2.0], [0.5, 2.0, 7.0]]
            d["matrix"] = [[4.0, 3.0, 0.5], [3.0, 9.0, 2.0], [0.5, 2.0, 16.0]]
        result = self.mutate(edit)
        self.assertTrue(any(c.startswith("block.syst.") for c in codes(result)), codes(result))
        self.assertEqual(codes(result) & {"blocks.sum_mismatch"}, set())

    def test_component_larger_than_total(self):
        def edit(d):
            d["blocks"]["stat"][0][0] = 5.0
            d["blocks"]["syst"][0][0] = -1.0
        self.assertIn("blocks.component_exceeds_total", codes(self.mutate(edit)))


class ClipDemoTests(unittest.TestCase):
    def test_demo_is_labelled_proposal_and_quantifies_changes(self):
        doc = load("cov_indefinite.json")
        doc["weights"] = [1.0, 0.0, 0.0]
        result = vc.validate_covariance(doc, demo_clip=True)
        demo = result["diagnostic_proposal"]
        self.assertIn("[Proposal]", demo["label"])
        self.assertEqual(demo["eigenvalues_clipped"], 1)
        self.assertGreaterEqual(min(demo["eigenvalues_after"]), 0.0)
        self.assertGreater(demo["max_relative_diagonal_change"], 0.0)
        self.assertGreater(demo["max_abs_correlation_change"], 0.0)
        self.assertIsNotNone(demo["total_uncertainty_relative_change"])
        self.assertEqual(result["status"], "fail")  # the clip does not turn the verdict into a pass

    def test_negative_total_variance_is_reported_not_hidden(self):
        result = vc.validate_covariance(load("cov_indefinite.json"), demo_clip=True)
        demo = result["diagnostic_proposal"]
        self.assertLess(demo["total_variance_before"], 0)
        self.assertIsNone(demo["total_uncertainty_before"])

    def test_no_demo_unless_requested(self):
        self.assertNotIn("diagnostic_proposal", vc.validate_covariance(load("cov_indefinite.json")))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = vc.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(str(FIX / "cov_valid.json"))[0], 0)
        code, out = self.run_cli(str(FIX / "cov_indefinite.json"))
        self.assertEqual((code, out["status"]), (1, "fail"))

    def test_unreadable_file_and_bad_json_exit_2(self):
        self.assertEqual(self.run_cli(str(FIX / "does_not_exist.json"))[0], 2)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{not json")
        self.addCleanup(Path(fh.name).unlink)
        self.assertEqual(self.run_cli(fh.name)[0], 2)

    def test_strict_turns_warnings_into_failure(self):
        doc = {"labels": ["a", "b"], "kind": "absolute", "units": "u^2", "matrix": [[1.0, 1.0], [1.0, 1.0 + 1e-12]]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        self.addCleanup(Path(fh.name).unlink)
        self.assertEqual(self.run_cli(fh.name)[0], 0)
        self.assertEqual(self.run_cli(fh.name, "--strict")[0], 1)


if __name__ == "__main__":
    unittest.main()
