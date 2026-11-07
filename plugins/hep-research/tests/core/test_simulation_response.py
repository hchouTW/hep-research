"""The response pipeline: draws independent of order and chunking, shared volume streams, and the moments of the scintillation formula (Sections 10.2, 10.3)."""
from __future__ import annotations

import math
import random
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import response, rng  # noqa: E402

STAGE = {"name": "scintillation", "kind": "scintillation", "parameters": {"light_yield_per_MeV": {"value": 100.0, "source_of_facts": "synthetic"}, "resolution_scale": {"value": 1.0, "source_of_facts": "synthetic"}}}
PIPELINE = {"schema": response.SCHEMA, "run_seed": 7, "replica": 0, "stages": [STAGE]}
MAP = {"schema": "efficiency-map/1", "channels": ["a", "b"], "form": {"kind": "uniform", "value": [0.2, 0.3]}, "source_of_facts": "synthetic"}
BINS = {0: (0.5, 0.1, 3), 1: (0.0, 0.05, 0), 2: (1.0, 0.0, 5)}


class Checks(unittest.TestCase):
    def test_a_parameter_without_a_source_is_refused(self):
        bad = {**PIPELINE, "stages": [{**STAGE, "parameters": {"x": {"value": 1}}}]}
        with self.assertRaises(response.ResponseError):
            response.check_pipeline(bad)

    def test_two_stages_with_one_name_are_refused(self):
        with self.assertRaises(response.ResponseError):
            response.check_pipeline({**PIPELINE, "stages": [STAGE, STAGE]})

    def test_keys_of_a_study_are_distinct(self):
        self.assertEqual(len(set(response.study_keys(PIPELINE, ["ecal", "hcal"]))), 3)

    def test_exhaustion_is_negligible_at_realistic_draws(self):
        self.assertLess(response.exhaustion_bound(1024), 1e-300 + 1e-200)
        self.assertEqual(response.exhaustion_bound(2 ** 15), 1.0)


class Determinism(unittest.TestCase):
    def test_the_order_of_bins_does_not_matter(self):
        shuffled = list(BINS.items())
        random.Random(3).shuffle(shuffled)
        self.assertEqual(response.scintillation_event(PIPELINE, STAGE, 4, 9, BINS, MAP), response.scintillation_event(PIPELINE, STAGE, 4, 9, dict(shuffled), MAP))

    def test_chunks_do_not_matter(self):
        whole = [response.scintillation_event(PIPELINE, STAGE, event, 9, BINS, MAP) for event in range(40)]
        parts = [response.scintillation_event(PIPELINE, STAGE, event, 9, BINS, MAP) for start in (30, 0, 10, 20) for event in range(start, start + 10)]
        self.assertEqual(sorted(map(str, whole)), sorted(map(str, parts)))

    def test_two_readouts_of_a_volume_share_the_photon_draws(self):
        first = response.scintillation_event(PIPELINE, STAGE, 4, 9, BINS, MAP)
        second = response.scintillation_event(dict(PIPELINE), dict(STAGE), 4, 9, BINS, MAP)
        self.assertEqual(first, second)

    def test_photon_times_cross_a_block_without_repeating(self):
        times = response.photon_times(PIPELINE, "scintillation", 1, 9, 0, response.PHOTON_BLOCK + 5, 10.0, 2.0)
        self.assertEqual(len(times), response.PHOTON_BLOCK + 5)
        self.assertEqual(len(set(times)), len(times))


class Formula(unittest.TestCase):
    def sample(self, scale, large, small, steps, count=40000):
        key = rng.volume_key(1, "formula", 0)
        return [response.bin_photons(rng.SubStream(key, event, 1), 100.0, scale, large, small, steps) for event in range(count)]

    def check(self, scale, large, small, steps):
        mean, variance = response.photon_moments(100.0, scale, large, small, steps)
        values = self.sample(scale, large, small, steps)
        self.assertLess(abs(statistics.fmean(values) - mean), 5 * math.sqrt(variance / len(values)))
        self.assertLess(abs(statistics.pvariance(values) / variance - 1), 0.04)

    def test_poisson_and_gaussian_regimes(self):
        self.check(1.0, 0.0, 0.05, 0)
        self.check(1.0, 1.0, 0.2, 4)
        self.check(0.5, 2.0, 0.0, 7)

    def test_the_width_subtracts_the_rounding(self):
        self.assertLess(abs(statistics.pvariance(self.sample(0.1, 0.5, 0.0, 1)) / response.photon_moments(100.0, 0.1, 0.5, 0.0, 1)[1] - 1), 0.04)

    def test_a_yield_factor_of_zero_width_is_one(self):
        self.assertEqual(response.yield_factor(PIPELINE, 1, 2, 0.0), 1.0)
        values = [response.yield_factor(PIPELINE, event, 2, 0.1) for event in range(20000)]
        self.assertAlmostEqual(statistics.fmean(values), 1.0, places=2)
        self.assertAlmostEqual(statistics.pstdev(values), 0.1, places=2)


class Stages(unittest.TestCase):
    def test_efficiency_maps(self):
        self.assertEqual(response.efficiencies(MAP, 3), [0.2, 0.3])
        linear = {**MAP, "form": {"kind": "linear", "intercept": [0.1, 0.2], "slope_per_bin": [0.01, 0.0]}}
        self.assertAlmostEqual(response.efficiencies(linear, 2)[0], 0.12)
        with self.assertRaises(response.ResponseError):
            response.efficiencies({**MAP, "form": {"kind": "uniform", "value": [0.8, 0.3]}}, 0)

    def test_charge_table_must_sum_to_one(self):
        self.assertEqual(response.share_charge(10.0, [{"offset": 0, "fraction": 0.75}, {"offset": 1, "fraction": 0.25}]), {0: 7.5, 1: 2.5})
        with self.assertRaises(response.ResponseError):
            response.share_charge(10.0, [{"offset": 0, "fraction": 0.5}])

    def test_the_handoff_is_addressed(self):
        document = response.handoff("sensor", "electronics", [{"cell": 1, "charge": 2.0}])
        self.assertEqual(response.read_handoff(document, "electronics")[0]["cell"], 1)
        with self.assertRaises(response.ResponseError):
            response.read_handoff(document, "readout")

    def test_outside_stages_are_registered(self):
        self.assertEqual(response.external_program({"name": "adc", "kind": "electronics_external"}), "fe4")
        self.assertEqual(response.external_program({"name": "strips", "kind": "readout_external"}), "simreco-strip")
        with self.assertRaises(response.ResponseError):
            response.external_program({"name": "s", "kind": "sensor"})

    def test_electronics_applies_the_threshold(self):
        stream = rng.SubStream(rng.channel_key(1, "ecal", "adc", 0), 0, 3)
        self.assertIsNone(response.electronics_response(stream, 0.0, 0.1, 5.0, 0.5, 12))
        self.assertEqual(response.electronics_response(rng.SubStream(rng.channel_key(1, "ecal", "adc", 0), 1, 3), 1e9, 0.1, 5.0, 0.5, 12), 4095)


if __name__ == "__main__":
    unittest.main()
