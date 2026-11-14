"""Witness W2 of the reconstruction contracts (plan Section 12, contract-map.md): linear pulse estimation and
insufficient information. The analytic solution and its tolerance are fixed here, before the first run. The artificial
model is dimensionless and is not a pulse shape; the fixed-model covariance holds under that model only. Passing proves
the stated contract behaviour, not a backend. Synthetic documents only."""
import sys
import unittest
from fractions import Fraction
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import can_recompute, matrix_rank, read_sidecar  # noqa: E402
from tests.contracts.reconstruction_fixtures import (code_list, identity_matrix, pulse_estimate, pulse_product,  # noqa: E402
                                                     truncated_pulse_estimate)

ANALYTIC_SOLUTION = [3, 2]
ANALYTIC_COVARIANCE = [[1.5, -0.5], [-0.5, 0.5]]
ABSOLUTE_TOLERANCE = 1e-12  # fixed before the first run; the reference below is exact, so this only bounds the float record
RECORD_TOLERANCE = 1e-12  # the record's comparator, relative to the size of each sum's terms


def weighted_normal_solution(design, noise_covariance, observation):
    """Exact reference for a diagonal noise covariance: x = (M^T R^-1 M)^-1 M^T R^-1 d for two parameters. It lives in the
    test because the plugin ships no solver at this stage."""
    weights = [1 / Fraction(noise_covariance[row][row]) for row in range(len(design))]
    normal = [[sum(weights[row] * design[row][i] * design[row][j] for row in range(len(design))) for j in range(2)] for i in range(2)]
    projected = [sum(weights[row] * design[row][i] * observation[row] for row in range(len(design))) for i in range(2)]
    determinant = normal[0][0] * normal[1][1] - normal[0][1] * normal[1][0]
    covariance = [[normal[1][1] / determinant, -normal[0][1] / determinant], [-normal[1][0] / determinant, normal[0][0] / determinant]]
    return [sum(covariance[i][j] * projected[j] for j in range(2)) for i in range(2)], covariance


class AnalyticSolution(unittest.TestCase):
    def assert_close(self, found, expected):
        self.assertLessEqual(abs(float(found) - expected), ABSOLUTE_TOLERANCE)

    def test_reference_reproduces_the_analytic_solution(self):
        estimate = pulse_estimate()
        solution, covariance = weighted_normal_solution(estimate["model"]["design"], estimate["model"]["noise_covariance"],
                                                        estimate["observation"])
        for found, expected in zip(solution, ANALYTIC_SOLUTION):
            self.assert_close(found, expected)
        for found_row, expected_row in zip(covariance, ANALYTIC_COVARIANCE):
            for found, expected in zip(found_row, expected_row):
                self.assert_close(found, expected)

    def test_record_holds_the_analytic_solution(self):
        estimate = pulse_estimate()
        self.assertEqual(estimate["solution"], ANALYTIC_SOLUTION)
        self.assertEqual(estimate["covariance"]["matrix"], ANALYTIC_COVARIANCE)
        self.assertEqual(estimate["comparator"]["relative_tolerance"], RECORD_TOLERANCE)
        self.assertEqual(code_list(read_sidecar(pulse_product())), [])

    def test_wrong_solution_or_covariance_is_caught(self):
        for field, wrong in (("solution", [3.5, 2]), ("covariance", {"matrix": [[1, 0], [0, 1]], "scope": "fixed-model", "includes": []})):
            estimate = pulse_estimate()
            estimate[field] = wrong
            self.assertIn("reconstruction.estimate.solution_mismatch", code_list(read_sidecar(pulse_product(estimate))), field)

    def test_a_large_declared_tolerance_buys_nothing(self):
        estimate = pulse_estimate()
        estimate.update({"solution": [100, -7], "comparator": {"relative_tolerance": 1e6}})
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["schema.maximum"])

    def test_covariance_of_the_wrong_shape_is_caught(self):
        estimate = pulse_estimate()
        estimate["covariance"]["matrix"] = [[1.5, -0.5, 99], [-0.5, 0.5]]
        self.assertIn("reconstruction.estimate.solution_mismatch", code_list(read_sidecar(pulse_product(estimate))))

    def test_noise_covariance_must_be_positive_definite(self):
        estimate = pulse_estimate()
        estimate["model"]["noise_covariance"][2][2] = 0
        self.assertIn("reconstruction.estimate.noise_not_positive_definite", code_list(read_sidecar(pulse_product(estimate))))

    def test_dimensions_must_agree(self):
        estimate = pulse_estimate()
        estimate["observation"] = [5, 2]
        self.assertIn("reconstruction.estimate.dimension_mismatch", code_list(read_sidecar(pulse_product(estimate))))


def float_fit(design, variances, observation) -> dict:
    """An honest double-precision fit: plain floats, the way a backend's record would hold them."""
    weights = [1 / variance for variance in variances]
    rows = range(len(design))
    normal = [[sum(weights[k] * design[k][i] * design[k][j] for k in rows) for j in range(2)] for i in range(2)]
    projected = [sum(weights[k] * design[k][i] * observation[k] for k in rows) for i in range(2)]
    determinant = normal[0][0] * normal[1][1] - normal[0][1] * normal[1][0]
    covariance = [[normal[1][1] / determinant, -normal[0][1] / determinant], [-normal[1][0] / determinant, normal[0][0] / determinant]]
    estimate = pulse_estimate()
    estimate["model"] = {"design": design, "shape": "fixed-template",
                         "noise_covariance": [[variances[i] if i == j else 0 for j in rows] for i in rows]}
    estimate.update({"observation": observation, "solution": [sum(covariance[i][j] * projected[j] for j in range(2)) for i in range(2)]})
    estimate["covariance"]["matrix"] = covariance
    return estimate


class ComparatorScale(unittest.TestCase):
    """RM4: the bound is relative to the size of each sum's terms, so it follows the signal, the weights and the design."""

    DESIGN = [[1.3, 0.7], [0.2, 1.1], [0.9, 0.4]]
    SCALES = {"unit signal": (1.0, [1.0, 2.0, 3.0]), "ADC scale, small variance": (1000.0, [1e-4, 2e-4, 3e-4]),
              "large signal, unit variance": (1e6, [1.0, 2.0, 3.0]), "tiny signal": (1e-6, [1e-14, 2e-14, 3e-14])}

    def honest_fit(self, signal, variances):
        return float_fit(self.DESIGN, variances, [signal * value for value in (1.000321, 0.777123, 0.512987)])

    def test_honest_float_fits_pass_at_every_scale(self):
        for name, (signal, variances) in self.SCALES.items():
            self.assertEqual(code_list(read_sidecar(pulse_product(self.honest_fit(signal, variances)))), [], name)

    def test_a_small_relative_error_fails_at_every_scale(self):
        for name, (signal, variances) in self.SCALES.items():
            estimate = self.honest_fit(signal, variances)
            estimate["solution"][0] *= 1 + 1e-9
            self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["reconstruction.estimate.solution_mismatch"], name)

    def test_a_wrong_covariance_fails_at_every_scale(self):
        for name, (signal, variances) in self.SCALES.items():
            estimate = self.honest_fit(signal, variances)
            estimate["covariance"]["matrix"][1][1] *= 1 + 1e-9
            self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["reconstruction.estimate.solution_mismatch"], name)


class DenseNoise(unittest.TestCase):
    """Re-review 2 minor 3: a dense covariance is read exactly, and in reasonable time."""

    def dense_record(self, size):
        covariance = [[0.5 ** abs(i - j) for j in range(size)] for i in range(size)]
        inverse = numpy.linalg.inv(numpy.array(covariance))
        design = numpy.array([[1.0, 1.0 + index / size] for index in range(size)])
        observation = numpy.array([float(index % 7) for index in range(size)])
        normal = design.T @ inverse @ design
        estimate = pulse_estimate()
        estimate["model"] = {"design": design.tolist(), "noise_covariance": covariance, "shape": "fixed-template"}
        estimate["observation"] = observation.tolist()
        estimate["solution"] = numpy.linalg.solve(normal, design.T @ inverse @ observation).tolist()
        estimate["covariance"]["matrix"] = numpy.linalg.inv(normal).tolist()
        estimate["comparator"]["relative_tolerance"] = 1e-10
        return estimate

    def test_an_honest_dense_fit_is_accepted_and_a_wrong_one_is_not(self):
        estimate = self.dense_record(48)
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), [])
        estimate["solution"][0] *= 1 + 1e-6
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["reconstruction.estimate.solution_mismatch"])


class InsufficientInformation(unittest.TestCase):
    def test_proportional_columns_up_to_rounding_are_rank_deficient(self):
        """M1 reaches W2: the record's comparator judges the rank of a float design."""
        estimate = truncated_pulse_estimate()
        estimate["model"] = {"design": [[0.1, 0.3], [0.2, 0.6], [0.3, 0.9]], "noise_covariance": identity_matrix(3), "shape": "fixed-template"}
        estimate["observation"] = [1, 2, 3]
        estimate["identifiability"] = {"rank": 1, "status": "rank-deficient", "unidentifiable": ["amplitude", "baseline"]}
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), [])

    def test_design_is_rank_one_after_the_first_sample_is_removed(self):
        self.assertEqual(matrix_rank(pulse_estimate()["model"]["design"]), 2)
        self.assertEqual(matrix_rank(truncated_pulse_estimate()["model"]["design"]), 1)

    def test_identifiable_component_is_delivered(self):
        self.assertEqual(code_list(read_sidecar(pulse_product(truncated_pulse_estimate()))), [])

    def test_declared_rank_must_be_the_real_one(self):
        estimate = truncated_pulse_estimate()
        estimate["identifiability"].update({"rank": 2, "status": "full", "unidentifiable": []})
        self.assertIn("reconstruction.estimate.identifiability_mismatch", code_list(read_sidecar(pulse_product(estimate))))

    def test_finite_amplitude_precision_is_refused(self):
        estimate = truncated_pulse_estimate()
        estimate["solution"], estimate["covariance"]["matrix"] = [0, 2], [[1e6, 0], [0, 0.5]]
        self.assertIn("reconstruction.estimate.spurious_precision", code_list(read_sidecar(pulse_product(estimate))))

    def test_jitter_is_refused(self):
        estimate = truncated_pulse_estimate()
        estimate["regularization"] = "jitter"
        self.assertIn("reconstruction.estimate.jitter_precision", code_list(read_sidecar(pulse_product(estimate))))

    def test_unidentifiable_parameter_must_be_named(self):
        estimate = truncated_pulse_estimate()
        estimate["identifiability"]["unidentifiable"] = []
        self.assertIn("reconstruction.estimate.identifiability_mismatch", code_list(read_sidecar(pulse_product(estimate))))

    def test_component_value_and_variance_are_checked(self):
        for field, wrong in (("value", 999), ("variance", 0)):
            estimate = truncated_pulse_estimate()
            estimate["identifiability"]["components"][0][field] = wrong
            self.assertIn("reconstruction.estimate.component_mismatch", code_list(read_sidecar(pulse_product(estimate))), field)

    def test_component_outside_the_row_space_is_refused(self):
        estimate = truncated_pulse_estimate()
        estimate["identifiability"]["components"][0]["weights"] = [1, 0]
        self.assertIn("reconstruction.estimate.component_not_identifiable", code_list(read_sidecar(pulse_product(estimate))))


class ModelDomain(unittest.TestCase):
    def test_amplitude_dependent_shape_is_out_of_domain(self):
        estimate = pulse_estimate()
        estimate["model"]["shape"] = "amplitude-dependent"
        self.assertIn("reconstruction.estimate.out_of_domain_claim", code_list(read_sidecar(pulse_product(estimate))))
        estimate.update({"status": "out-of-domain", "optimal_claim": False})
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), [])

    def test_rank_deficient_record_cannot_read_as_a_fit(self):
        """M2."""
        estimate = truncated_pulse_estimate()
        estimate.update({"status": "fit", "optimal_claim": True})
        self.assertIn("reconstruction.estimate.status_mismatch", code_list(read_sidecar(pulse_product(estimate))))

    def test_full_rank_record_states_a_fit(self):
        """M2."""
        for status in ("rank-deficient", "out-of-domain"):
            estimate = pulse_estimate()
            estimate["status"] = status
            self.assertIn("reconstruction.estimate.status_mismatch", code_list(read_sidecar(pulse_product(estimate))), status)

    def test_only_a_fit_claims_optimality(self):
        """M2."""
        estimate = truncated_pulse_estimate()
        estimate["optimal_claim"] = True
        self.assertIn("reconstruction.estimate.status_mismatch", code_list(read_sidecar(pulse_product(estimate))))

    def test_honest_diagnostic_delivers_no_solution(self):
        """M2: an out-of-domain diagnostic need not deliver a generalized least-squares solution to pass."""
        estimate = pulse_estimate()
        estimate["model"]["shape"] = "amplitude-dependent"
        estimate.update({"status": "out-of-domain", "optimal_claim": False, "solution": None})
        estimate["covariance"]["matrix"] = None
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), [])

    def test_the_linear_model_fixes_no_value_outside_its_domain(self):
        """Re-review minor 12: a record that says the model does not hold is not judged by it."""
        estimate = truncated_pulse_estimate()
        estimate["model"]["shape"] = "amplitude-dependent"
        estimate["status"] = "out-of-domain"
        estimate["identifiability"]["components"][0]["value"] = 5
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), [])

    def test_fixed_model_covariance_cannot_claim_systematic_sources(self):
        estimate = pulse_estimate()
        estimate["covariance"]["includes"] = ["template", "conditions"]
        self.assertIn("reconstruction.estimate.covariance_scope", code_list(read_sidecar(pulse_product(estimate))))


class SamplingAndRetention(unittest.TestCase):
    def test_time_origin_is_required(self):
        document = pulse_product()
        del document["sampling"]["time_origin"]
        self.assertTrue(code_list(read_sidecar(document)))

    def test_retention_decides_recomputation(self):
        document = pulse_product()
        self.assertTrue(can_recompute(document, "waveform"))
        self.assertFalse(can_recompute(document, "raw"), "removed information cannot be inferred from summaries")
        self.assertFalse(can_recompute(document, "unknown-level"))

    def test_reduced_retention_states_what_it_loses(self):
        """M8, R34."""
        document = pulse_product()
        del document["retention"]["lost_recalibrations"]
        self.assertIn("reconstruction.retention.loss_unstated", code_list(read_sidecar(document)))
        document["retention"]["lost_recalibrations"] = []
        self.assertEqual(code_list(read_sidecar(document)), [], "stating that nothing is lost is a statement")

    def test_full_retention_has_nothing_to_state(self):
        document = pulse_product()
        document["retention"].update({"raw": "reproducible", "waveform": "kept", "conditions_snapshot": "kept"})
        del document["retention"]["lost_recalibrations"]
        self.assertEqual(code_list(read_sidecar(document)), [])

    def test_block_needs_its_extension(self):
        document = pulse_product()
        document["required_extensions"] = []
        self.assertIn("reconstruction.extension.undeclared_block", code_list(read_sidecar(document)),
                      "an old reader must stop at a block that changes the meaning, so the block declares its extension")

    def test_old_reader_stops_at_the_estimate(self):
        report = read_sidecar(pulse_product(), known_extensions=frozenset())
        self.assertEqual(code_list(report), ["reconstruction.reader.unknown_required_extension"])


def quadratic_fit(step) -> dict:
    """An honest GLS fit of baseline, slope and curvature against 16 samples at this time step, solved by QR on scaled
    columns, the way a backend would; the record holds the solution and covariance in the stated units."""
    times = [index * step for index in range(16)]
    design = numpy.array([[1.0, t, t * t] for t in times])
    observation = numpy.array([2.0 + 0.5 * index - 0.03 * index * index + 0.01 * ((-1) ** index) for index in range(16)])
    norms = numpy.linalg.norm(design, axis=0)
    orthogonal, triangular = numpy.linalg.qr(design / norms)
    solution_scaled = numpy.linalg.solve(triangular, orthogonal.T @ observation)
    estimate = pulse_estimate()
    estimate.update({"parameters": ["baseline", "slope", "curvature"],
                     "model": {"design": design.tolist(), "noise_covariance": identity_matrix(16), "shape": "fixed-template"},
                     "observation": observation.tolist(), "solution": (solution_scaled / norms).tolist(),
                     "identifiability": {"rank": 3, "status": "full", "unidentifiable": []}})
    estimate["covariance"]["matrix"] = (numpy.linalg.inv(triangular.T @ triangular) / numpy.outer(norms, norms)).tolist()
    return estimate


class UnitInvariance(unittest.TestCase):
    """Re-review 3 N1: the rank of a design does not depend on the units of its parameters, so the same honest fit with time
    in nanoseconds and in seconds reads the same."""

    def test_the_same_fit_in_seconds_and_nanoseconds_reads_the_same(self):
        for unit, step in (("ns", 1.0), ("s", 1e-9)):
            self.assertEqual(code_list(read_sidecar(pulse_product(quadratic_fit(step)))), [], unit)
        self.assertEqual(matrix_rank(quadratic_fit(1e-9)["model"]["design"], 1e-9), 3)

    def test_a_small_relative_error_fails_in_both_units(self):
        for unit, step in (("ns", 1.0), ("s", 1e-9)):
            estimate = quadratic_fit(step)
            estimate["solution"][2] *= 1 + 1e-6
            self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["reconstruction.estimate.solution_mismatch"], unit)


class UncheckedComponents(unittest.TestCase):
    """Re-review 3 minors 2 and 3: where the exact numbers fix no value for a stated component, the reader says so."""

    def test_a_component_on_a_float_degenerate_design_is_reported_unchecked(self):
        """Rank 1 at the tolerance, 2 exactly: a stated value and variance cannot be compared, and the record is not clean."""
        estimate = truncated_pulse_estimate()
        estimate["model"] = {"design": [[0.1, 0.3], [0.2, 0.6], [0.3, 0.9]], "noise_covariance": identity_matrix(3), "shape": "fixed-template"}
        estimate["observation"] = [1, 2, 3]
        estimate["identifiability"] = {"rank": 1, "status": "rank-deficient", "unidentifiable": ["amplitude", "baseline"],
                                       "components": [{"weights": [1, 3], "value": 123, "variance": 1e-30}]}
        report = read_sidecar(pulse_product(estimate))
        self.assertEqual(code_list(report), [])
        self.assertEqual([finding.code for finding in report.findings], ["reconstruction.estimate.component_unchecked"])

    def test_an_honest_component_with_rounded_weights_is_not_malformed(self):
        """Weights in the row space at the tolerance and not exactly: a warning, not reader.malformed."""
        estimate = truncated_pulse_estimate()
        estimate["model"] = {"design": [[1, 3], [2, 6], [3, 9]], "noise_covariance": identity_matrix(3), "shape": "fixed-template"}
        estimate["observation"] = [2, 4, 6]
        estimate["identifiability"] = {"rank": 1, "status": "rank-deficient", "unidentifiable": ["amplitude", "baseline"],
                                       "components": [{"weights": [0.1 + 0.2, 0.9], "value": 0.6, "variance": 0.09 / 14}]}
        report = read_sidecar(pulse_product(estimate))
        self.assertEqual(code_list(report), [])
        self.assertEqual([finding.code for finding in report.findings], ["reconstruction.estimate.component_unchecked"])
        estimate["identifiability"]["components"] = [{"weights": [1, 3], "value": 2, "variance": 1 / 14}]
        self.assertEqual([finding.code for finding in read_sidecar(pulse_product(estimate)).findings], [], "exact weights are checked, and these are right")


def zero_design_estimate(parameters, named) -> dict:
    """W2's named negative in its amplitude-only form: the template has no support in the window, so the design is zero."""
    estimate = truncated_pulse_estimate()
    estimate.update({"parameters": parameters, "model": {"design": [[0] * len(parameters)] * 2, "noise_covariance": identity_matrix(2), "shape": "fixed-template"},
                     "observation": [2, 2], "identifiability": {"rank": 0, "status": "rank-deficient", "unidentifiable": named}})
    return estimate


class ZeroDesign(unittest.TestCase):
    """Re-review 4 P1, W2 and A34: on a zero design only the zero combination is determined, so every parameter is named
    unidentifiable, and a stated component is not identifiable."""

    def test_an_honest_amplitude_only_record_is_accepted(self):
        self.assertEqual(code_list(read_sidecar(pulse_product(zero_design_estimate(["amplitude"], ["amplitude"])))), [])
        self.assertEqual(code_list(read_sidecar(pulse_product(zero_design_estimate(["amplitude", "baseline"], ["amplitude", "baseline"])))), [])

    def test_a_record_that_names_nothing_is_refused(self):
        self.assertEqual(code_list(read_sidecar(pulse_product(zero_design_estimate(["amplitude"], [])))), ["reconstruction.estimate.identifiability_mismatch"])

    def test_a_component_on_a_zero_design_is_not_identifiable(self):
        estimate = zero_design_estimate(["amplitude"], ["amplitude"])
        estimate["identifiability"]["components"] = [{"weights": [1], "value": 5, "variance": 1e-30}]
        self.assertEqual(code_list(read_sidecar(pulse_product(estimate))), ["reconstruction.estimate.component_not_identifiable"])


if __name__ == "__main__":
    unittest.main()
