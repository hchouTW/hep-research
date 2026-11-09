"""core/simulation/digitize.py (g4sim S8, Section 10.5): the composition of the normative response stages that g4sim_digi reproduces. The
C++ program itself is compared with it in tests/adapters/test_g4sim_digi.py and by S8 gate 2."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import digitize, response, rng  # noqa: E402

JOB = {"schema": digitize.SCHEMA, "run_seed": 11, "replica": 0, "readout": "bar", "channels": ["left", "right"],
       "stage": {"name": "scintillation", "light_yield_per_MeV": 200.0, "resolution_scale": 0.6},
       "efficiencies": {"0": [0.1, 0.2], "1": [0.05, 0.05]},
       "timing": {"decay_ns": 2.0, "transit": {"kind": "exponential", "transit_ns": 1.0}},
       "sensor": {"name": "sensor", "gain": 1.0, "excess_noise": 0.1, "dark_rate_per_ns": 1e-3, "gate_ns": 50.0},
       "electronics": {"name": "electronics", "noise_sigma": 0.5, "threshold": 1.0, "lsb": 0.5, "bits": 10}}
ROWS = [(0, 5, 0, 0.2, 0.01, 4), (0, 5, 1, 0.0, 0.003, 0), (1, 5, 0, 0.5, 0.02, 9), (1, 9, 1, 0.05, 0.0, 1)]


class Digitize(unittest.TestCase):
    def test_rows_are_sorted_and_complete(self):
        channels, times = digitize.digitize(JOB, ROWS)
        self.assertEqual([row[:3] for row in channels], [(0, 5, 0), (0, 5, 1), (1, 5, 0), (1, 5, 1), (1, 9, 0), (1, 9, 1)])
        self.assertEqual(sum(row[3] for row in channels), len(times))  # one time per detected photon (no dark counts at this rate here)
        self.assertEqual(times, sorted(times, key=lambda row: row[:4]))

    def test_the_order_of_the_rows_does_not_matter(self):
        self.assertEqual(digitize.digitize(JOB, ROWS), digitize.digitize(JOB, list(reversed(ROWS))))

    def test_it_is_the_normative_stages(self):
        channels, _ = digitize.digitize({**JOB, "timing": None}, ROWS[:2])
        key = rng.volume_key(11, "scintillation", 0)
        expected = [0, 0]
        for bin_index, large, small, steps in ((0, 0.2, 0.01, 4), (1, 0.0, 0.003, 0)):
            stream = rng.SubStream(key, 0, 5, bin_index)
            photons = response.bin_photons(stream, 200.0, 0.6, large, small, steps)
            for at, count in enumerate(stream.multinomial(photons, JOB["efficiencies"][str(bin_index)])[:2]):
                expected[at] += count
        self.assertEqual([row[3] for row in channels], expected)

    def test_refusals(self):
        for change, code in ((lambda j: j.update(schema="x"), "schema"), (lambda j: j.update(channels=["a", "a"]), "channels"),
                             (lambda j: j["efficiencies"].update({"0": [0.7, 0.6]}), "efficiencies"),
                             (lambda j: j["timing"].update(decay_ns=0.0), "timing"), (lambda j: j["sensor"].update(name="scintillation"), "stage-name"),
                             (lambda j: j["timing"]["transit"].update(kind="gaussian"), "transit")):
            job = copy.deepcopy(JOB)
            change(job)
            with self.assertRaises(digitize.DigiError) as caught:
                digitize.digitize(job, ROWS)
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(digitize.DigiError) as caught:
            digitize.digitize(JOB, ROWS + [ROWS[0]])
        self.assertEqual(caught.exception.code, "bin-twice")
        with self.assertRaises(digitize.DigiError) as caught:
            digitize.digitize(JOB, [(0, 5, 7, 0.1, 0.0, 1)])
        self.assertEqual(caught.exception.code, "efficiencies")

    def test_keys_for_the_program(self):
        keyed = digitize.job_with_keys(JOB, blocks=3)
        self.assertEqual(keyed["keys"]["stage"], list(rng.volume_key(11, "scintillation", 0)))
        self.assertEqual(keyed["keys"]["sensor"], list(rng.channel_key(11, "bar", "sensor", 0)))
        self.assertEqual(keyed["keys"]["time_blocks"][2], list(rng.volume_key(11, "scintillation/time/2", 0)))
        self.assertEqual(len({tuple(key) for key in keyed["keys"]["time_blocks"]}), 3)


if __name__ == "__main__":
    unittest.main()
