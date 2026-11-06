"""source-density/1: parameters are checked, and each density integrates to one."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import source_density as sd  # noqa: E402


def source(energy):
    return {"density": "analytic", "particle": "e+", "energy": energy, "position": {"point": {"frame": "world", "centre_mm": [0, 0, 0]}},
            "direction": {"fixed": {"frame": "world", "vector": [0, 0, 2]}}}


def integral(record, low, high, steps=200000):
    width = (high - low) / steps
    return math.fsum(sd.energy_density(record, low + (at + 0.5) * width) for at in range(steps)) * width


class Energy(unittest.TestCase):
    def test_continuous_densities_integrate_to_one(self):
        for block, low, high in (({"uniform": {"min_MeV": "1", "max_MeV": "3"}}, 1, 3), ({"log_uniform": {"min_MeV": "1", "max_MeV": "100"}}, 1, 100),
                                 ({"power_law": {"min_MeV": "1", "max_MeV": "100", "index": "2.7"}}, 1, 100), ({"power_law": {"min_MeV": "1", "max_MeV": "9", "index": "1"}}, 1, 9),
                                 ({"gaussian": {"mean_MeV": "10", "sigma_MeV": "3", "truncate_MeV": ["8", None]}}, 8, 40)):
            self.assertAlmostEqual(integral(sd.density(source(block)), low, high), 1, places=5, msg=str(block))

    def test_a_gaussian_may_be_given_a_relative_width(self):
        record = sd.density(source({"gaussian": {"mean_MeV": "492", "rel_sigma": "0.03", "truncate_MeV": ["0", None]}}))
        self.assertAlmostEqual(record["energy"]["sigma_MeV"], 14.76)

    def test_discrete_supports_report_probabilities(self):
        record = sd.density(source({"list": {"energies_MeV": ["1", "2"], "weights": ["1", "3"]}}))
        self.assertEqual(sd.energy_density(record, 2.0), 0.75)
        self.assertEqual(sd.density(source({"cycle": {"energies_MeV": ["1", "2"]}}))["energy"]["probabilities"], [0.5, 0.5])

    def test_wrong_parameters_are_refused(self):
        for block in ({"uniform": {"min_MeV": "3", "max_MeV": "1"}}, {"mono": {"energy_MeV": "0"}}, {"gaussian": {"mean_MeV": "1", "sigma_MeV": "1"}},
                      {"gaussian": {"mean_MeV": "1", "sigma_MeV": "1", "truncate_MeV": ["5", "2"]}}, {"list": {"energies_MeV": ["1"], "weights": ["1", "2"]}},
                      {"gaussian": {"mean_MeV": "1", "sigma_MeV": "-1", "truncate_MeV": ["0", None]}}):
            with self.assertRaises(sd.SourceError, msg=str(block)):
                sd.density(source(block))

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(sd.SourceError):
            sd.density(source({"landau": {}}))


class PositionAndDirection(unittest.TestCase):
    def test_a_frame_is_required(self):
        block = source({"mono": {"energy_MeV": "1"}})
        del block["position"]["point"]["frame"]
        with self.assertRaises(sd.SourceError):
            sd.density(block)

    def test_a_direction_is_normalised(self):
        self.assertEqual(sd.density(source({"mono": {"energy_MeV": "1"}}))["direction"]["vector"], [0, 0, 1])

    def test_an_external_source_has_no_density(self):
        with self.assertRaises(sd.SourceError):
            sd.density({"density": "external"})


if __name__ == "__main__":
    unittest.main()
