"""Mapped efficiency maps (g4sim S7, Section 10.4): binning as the C++ grid, nominal and Dirichlet replica efficiencies, transit times,
the transverse-uniformity check, and their use by the digitization of Section 10.3."""
from __future__ import annotations

import math
import random
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import efficiency_map as em  # noqa: E402
from core.simulation import response  # noqa: E402

ALONG = {"kind": "along_axis", "axis": 2, "width_mm": ["2"]}
HALF = [50.0, 50.0, 5.0]


def mapping_run(efficiency=lambda point: (0.03, 0.01), photons=40000, seed=7):
    """A synthetic mapping run: one photon per event, two channels whose chances depend on the emission point."""
    draw = random.Random(seed)
    emitted, detected = {}, []
    for event in range(photons):
        point = [draw.uniform(-h, h) for h in HALF]
        emitted[event] = point
        first, second = efficiency(point)
        u = draw.random()
        if u < first:
            detected.append((event, "a", draw.expovariate(1 / 2.0)))
        elif u < first + second:
            detected.append((event, "b", draw.expovariate(1 / 3.0)))
    return emitted, detected


def built(segmentation=ALONG, **kwargs):
    emitted, detected = mapping_run(**kwargs)
    return em.build(template="crystal", component=1, spectrum={"energy_eV": ["2", "3"], "value": ["1", "1"]}, segmentation=segmentation,
                    half_mm=HALF, channels=["a", "b"], emitted=emitted, detected=detected,
                    hashes={"materials_sha256": "0" * 64, "surfaces_sha256": "1" * 64, "mapping_run_id": "x"})


class Binning(unittest.TestCase):
    def test_bins_follow_the_cpp_grid(self):
        self.assertEqual(em.bin_counts(ALONG, HALF), [1, 1, 5])
        self.assertEqual([em.bin_of(ALONG, HALF, [0, 0, z]) for z in (-5.0, -3.0001, -2.9999, 4.9999, 5.0, 7.0)], [0, 0, 1, 4, 4, 4])
        xyz = {"kind": "cartesian_xyz", "width_mm": ["25", "50", "10"]}
        self.assertEqual(em.bin_counts(xyz, HALF), [4, 2, 1])
        self.assertEqual(em.bin_of(xyz, HALF, [-49.0, 1.0, 0.0]), 0 + 4 * 1)

    def test_a_box_of_exactly_n_widths_has_n_bins(self):
        self.assertEqual(em.bin_counts({"kind": "along_axis", "axis": 2, "width_mm": ["10"]}, [1, 1, 15.000000000001]), [1, 1, 3])

    def test_polar_segmentation_is_refused(self):
        with self.assertRaises(em.MapError):
            em.bin_counts({"kind": "polar", "width_mm": ["1"], "phi_bins": 4}, HALF)


class Map(unittest.TestCase):
    def setUp(self):
        self.map = built()

    def test_every_emitted_photon_is_in_one_bin(self):
        rows = self.map["form"]["bins"]
        self.assertEqual(sum(row["emitted"] for row in rows), 40000)
        self.assertEqual(len(rows), 5)
        self.assertEqual(sum(sum(row["transit_counts"]) for row in rows), sum(sum(row["detected"]) for row in rows))

    def test_nominal_efficiencies_are_the_fractions(self):
        row = self.map["form"]["bins"][2]
        self.assertEqual(em.efficiencies(self.map, 2), [k / row["emitted"] for k in row["detected"]])
        self.assertAlmostEqual(em.efficiencies(self.map, 2)[0], 0.03, delta=0.006)

    def test_replicas_follow_the_dirichlet_posterior(self):
        row = self.map["form"]["bins"][1]
        alpha = [k + 0.5 for k in row["detected"]] + [row["emitted"] - sum(row["detected"]) + 0.5]
        total = math.fsum(alpha)
        draws = [em.efficiencies(self.map, 1, replica) for replica in range(1, 401)]
        for channel in range(2):
            values = [draw[channel] for draw in draws]
            mean = alpha[channel] / total
            sigma = math.sqrt(mean * (1 - mean) / (total + 1))
            self.assertAlmostEqual(statistics.fmean(values), mean, delta=4 * sigma / math.sqrt(400))
            self.assertAlmostEqual(statistics.stdev(values), sigma, delta=0.15 * sigma)
        covariance = statistics.covariance([draw[0] for draw in draws], [draw[1] for draw in draws])
        self.assertLess(covariance, 0)  # one set of photons: the channels are negatively correlated

    def test_a_replica_is_fixed_by_the_map_the_replica_and_the_bin(self):
        self.assertEqual(em.efficiencies(self.map, 3, 17), em.efficiencies(self.map, 3, 17))
        self.assertNotEqual(em.efficiencies(self.map, 3, 17), em.efficiencies(self.map, 3, 18))
        self.assertNotEqual(em.efficiencies(self.map, 3, 17), em.efficiencies(self.map, 2, 17))

    def test_a_channel_never_detected_still_varies(self):
        emitted, detected = mapping_run(efficiency=lambda point: (0.03, 0.0))
        document = em.build(template="c", component=1, spectrum={}, segmentation=ALONG, half_mm=HALF, channels=["a", "b"], emitted=emitted,
                            detected=detected, hashes={})
        self.assertEqual(em.efficiencies(document, 0)[1], 0.0)
        self.assertGreater(em.efficiencies(document, 0, 1)[1], 0.0)

    def test_transit_times_follow_the_bins_distribution(self):
        times = [em.transit_ns(self.map, 0, (i + 0.5) / 2000) for i in range(2000)]
        self.assertEqual(times, sorted(times))
        self.assertAlmostEqual(statistics.fmean(times), (0.75 * 2.0 + 0.25 * 3.0), delta=0.25)

    def test_two_detections_in_one_event_are_refused(self):
        emitted, detected = mapping_run()
        with self.assertRaises(em.MapError):
            em.build(template="c", component=1, spectrum={}, segmentation=ALONG, half_mm=HALF, channels=["a", "b"], emitted=emitted,
                     detected=detected + [detected[0]], hashes={})

    def test_fewer_than_100_replicas_are_refused(self):
        self.assertEqual(len(em.replicas(self.map)), 100)
        with self.assertRaises(em.MapError):
            em.replicas(self.map, 99)


class Uniformity(unittest.TestCase):
    def test_a_uniform_map_passes(self):
        self.assertEqual(em.transverse_uniformity(built())["status"], "passed")

    def test_a_map_that_depends_on_x_fails(self):
        result = em.transverse_uniformity(built(efficiency=lambda point: (0.02 + 0.03 * (point[0] > 0), 0.01)))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failing_bins"], [0, 1, 2, 3, 4])

    def test_too_few_photons_are_reported_not_passed(self):
        self.assertEqual(em.transverse_uniformity(built(photons=2000))["status"], "insufficient")

    def test_cartesian_maps_need_no_transverse_check(self):
        self.assertEqual(em.transverse_uniformity(built(segmentation={"kind": "cartesian_xy", "width_mm": ["50", "50"]}))["status"], "not-needed")

    def test_the_chi_square_survival_is_right(self):
        # reference values from scipy.stats.chi2.sf (SciPy is not a dependency of core)
        for statistic, dof, expected in ((13.374764951370247, 8, 0.09958921074906657), (3.84145882, 1, 0.0500000000206984), (0.5, 4, 0.9735009788392561), (40.0, 10, 1.694474393006737e-05)):
            self.assertAlmostEqual(em._chi_square_survival(statistic, dof), expected, delta=expected * 1e-10)


class Digitization(unittest.TestCase):
    PIPELINE = {"schema": "response-pipeline/1", "run_seed": 11, "replica": 0, "stages": []}

    def setUp(self):
        self.map = built()

    def test_the_response_reads_a_mapped_map_and_its_replicas(self):
        self.assertEqual(response.efficiencies(self.map, 2), em.efficiencies(self.map, 2))
        self.assertEqual(response.efficiencies(self.map, 2, 5), em.efficiencies(self.map, 2, 5))
        with self.assertRaises(response.ResponseError):
            response.efficiencies(self.map, 9)

    def test_a_map_replica_can_be_drawn_with_the_photon_streams_fixed(self):
        stage = {"name": "s", "parameters": {"light_yield_per_MeV": {"value": 500.0}, "resolution_scale": {"value": 1.0}}}
        bins = {2: (4.0, 0.5, 30)}
        nominal = response.scintillation_event(self.PIPELINE, stage, 3, 9, bins, self.map)
        self.assertEqual(response.scintillation_event(self.PIPELINE, stage, 3, 9, bins, self.map, map_replica=0), nominal)
        coupled = response.scintillation_event({**self.PIPELINE, "replica": 7}, stage, 3, 9, bins, self.map)
        held = response.scintillation_event(self.PIPELINE, stage, 3, 9, bins, self.map, map_replica=7)
        self.assertNotEqual(coupled, held)  # the coupled replica also changes the photon numbers

    def test_mapped_transit_times_replace_the_exponential(self):
        plain = response.photon_times(self.PIPELINE, "s", 1, 9, 0, 500, 10.0, 2.0)
        mapped = response.photon_times(self.PIPELINE, "s", 1, 9, 0, 500, 10.0, 2.0, map_document=self.map)
        self.assertNotEqual(plain, mapped)
        self.assertLessEqual(max(mapped) - 10.0 * 30, self.map["form"]["transit_edges_ns"][-1])

    def test_a_rise_time_adds_to_the_delay(self):
        quick = response.photon_times(self.PIPELINE, "s", 1, 9, 0, 4000, 10.0, 0.001)
        rising = response.photon_times(self.PIPELINE, "s", 1, 9, 0, 4000, 10.0, 0.001, rise_ns=3.0)
        self.assertAlmostEqual(statistics.fmean(rising) - statistics.fmean(quick), 3.0, delta=0.5)


class Checks(unittest.TestCase):
    """The Section 15.1 negatives of S7's response row: two components with different spectra sharing one map; a validation run whose
    RESOLUTIONSCALE differs from r (the latter is check-spec's, in tests/adapters/test_g4sim_run.py)."""

    SPECTRUM = {"energy_eV": ["2", "3"], "value": ["1", "1"]}

    def material(self, second=None):
        component = {"fraction": "0.5", "spectrum": self.SPECTRUM, "rise_ns": "0", "decay_ns": "2"}
        return {"scintillation": {"yield_per_MeV": "8000", "resolution_scale": "1.2", "components": [component, {**component, "spectrum": second or self.SPECTRUM}]}}

    def test_one_map_per_component_passes(self):
        first, second = built(), built(seed=8)
        second["form"]["component"] = 2
        self.assertEqual(em.component_findings(self.material(), {1: first, 2: second}), [])

    def test_two_components_with_different_spectra_sharing_one_map_are_caught(self):
        shared = built()
        other = {"energy_eV": ["2", "3"], "value": ["1", "0.2"]}
        codes = [item["code"] for item in em.component_findings(self.material(other), {1: shared, 2: shared})]
        self.assertIn("map-shared", codes)
        self.assertEqual(em.component_findings(self.material(), {1: shared, 2: shared}), [])  # the same spectrum may share

    def test_a_missing_map_a_wrong_spectrum_and_a_stale_map_are_caught(self):
        self.assertEqual([item["code"] for item in em.component_findings(self.material(), {1: built()})], ["map-missing"])
        wrong = built()
        wrong["form"]["emission_spectrum"] = {"energy_eV": ["2", "3"], "value": ["1", "0"]}
        self.assertEqual([item["code"] for item in em.component_findings({"scintillation": {"components": self.material()["scintillation"]["components"][:1]}}, {1: wrong})], ["map-spectrum"])
        self.assertEqual([item["code"] for item in em.component_findings({"scintillation": {"components": self.material()["scintillation"]["components"][:1]}}, {1: built()}, "f" * 64)], ["map-stale"])

    def test_a_validation_run_digitizes_nominally_with_one_component(self):
        stage = {"parameters": {"light_yield_per_MeV": {"value": 8000}, "resolution_scale": {"value": 1.2}}}
        single = {"scintillation": {"yield_per_MeV": "8000", "components": self.material()["scintillation"]["components"][:1]}}
        self.assertEqual(em.validation_response_findings(stage, single), [])
        stage["parameters"]["light_yield_per_MeV"]["value"] = 7000
        stage["parameters"]["yield_relative_width"] = {"value": 0.05}
        self.assertEqual([item["code"] for item in em.validation_response_findings(stage, self.material())],
                         ["validation-yield", "validation-yield-variation", "validation-components"])


if __name__ == "__main__":
    unittest.main()
