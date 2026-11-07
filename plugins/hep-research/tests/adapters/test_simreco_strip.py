"""simreco_strip, registered as `simreco-strip`: stage 5 of the response pipeline through its hand-off file (g4sim plan, Section 10.1)."""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import response, rng  # noqa: E402

ASSETS = ROOT / "adapters/geant4/assets"
COMPILER = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
REQUIRED = os.environ.get("HEP_SIMRECO_REQUIRED") == "1"
PITCH_Y_MM, PITCH_Z_MM, SHARING_MM = 0.05, 0.1, 0.01
KEY = rng.channel_key(7, "tracker", "strips", 0)


def reference_cluster(position: float, start: float, pitch: float, threshold: float) -> float:
    """simreco's linear charge sharing, written again from its description rather than from the C++."""
    ratio = (position - start) / pitch
    strip = math.floor(ratio)
    within = ratio - strip
    band = SHARING_MM / pitch
    near, far, neighbour = 1.0, 0.0, strip + 1
    if within > 1 - band / 2:
        far = (within - (1 - band / 2)) / band
        near = 1 - far
    elif within < band / 2:
        far = (band / 2 - within) / band
        near = 1 - far
        neighbour = strip - 1
    first, second = start + (strip + 0.5) * pitch, start + (neighbour + 0.5) * pitch
    keep_first, keep_second = near >= threshold, far >= threshold
    if not keep_first and not keep_second:
        return first
    total = (near if keep_first else 0) + (far if keep_second else 0)
    return ((near * first if keep_first else 0) + (far * second if keep_second else 0)) / total


@unittest.skipUnless(COMPILER or REQUIRED, "no C++ compiler: the simreco tests are optional here (required in CI job simreco)")
class SimrecoStrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not COMPILER:
            raise AssertionError("HEP_SIMRECO_REQUIRED=1 but no C++ compiler was found")
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.work = Path(cls.folder.name)
        cls.program = cls.work / "simreco_strip"
        built = subprocess.run([COMPILER, "-std=c++17", "-O2", "-ffp-contract=off", "-I", str(ASSETS / "g4sim"), "-I", str(ASSETS / "simreco"), str(ASSETS / "simreco/simreco_strip.cc"), "-o", str(cls.program)],
                               capture_output=True, text=True, timeout=300)
        if built.returncode:
            raise AssertionError(built.stderr[-2000:])

    def digitized(self, rows: list, threshold: float = 0.0, efficiency: float = 1.0, stage: str = "strips") -> tuple:
        source, target = self.work / "in.json", self.work / "out.json"
        source.write_text(json.dumps(response.handoff("sensor", "strips", rows)), encoding="utf-8")
        done = subprocess.run([str(self.program), "--handoff-in", str(source), "--handoff-out", str(target), "--stage", stage, "--next-stage", "fit", "--key0", str(KEY[0]), "--key1", str(KEY[1]),
                               "--pitch-y-um", "50", "--pitch-z-um", "100", "--sharing-um", "10", "--threshold", str(threshold), "--efficiency", str(efficiency)], capture_output=True, text=True, timeout=120)
        if done.returncode:
            return done.returncode, []
        return 0, response.read_handoff(json.loads(target.read_text(encoding="utf-8")), "fit")

    def crossings(self, count: int) -> list:
        pick = random.Random(11)
        return [{"event": at, "cell": 2 ** 40 + at % 5, "y_mm": pick.uniform(-20, 20), "z_mm": pick.uniform(-20, 20)} for at in range(count)]

    def test_matches_the_core_streams_and_the_model_bit_for_bit(self):
        rows = self.crossings(500)
        status, kept = self.digitized(rows, threshold=0.2, efficiency=0.9)
        self.assertEqual(status, 0)
        expected = []
        for row in rows:
            stream = rng.SubStream(KEY, row["event"], row["cell"])
            phase_y, phase_z, chance = stream.group()[0], stream.group()[0], stream.group()[0]
            if chance < 0.9:
                expected.append((row["event"], reference_cluster(row["y_mm"], phase_y * PITCH_Y_MM, PITCH_Y_MM, 0.2), reference_cluster(row["z_mm"], phase_z * PITCH_Z_MM, PITCH_Z_MM, 0.2)))
        self.assertGreater(len(expected), 400)
        self.assertLess(len(expected), 500)
        self.assertEqual([(row["event"], row["y_mm"], row["z_mm"]) for row in kept], expected)

    def test_a_row_does_not_depend_on_the_others(self):
        rows = self.crossings(200)
        _, whole = self.digitized(rows)
        shuffled = list(rows)
        random.Random(3).shuffle(shuffled)
        _, reordered = self.digitized(shuffled)
        self.assertEqual(sorted(whole, key=lambda row: row["event"]), sorted(reordered, key=lambda row: row["event"]))

    def test_the_scatter_is_the_resolution_it_reports(self):
        rows = self.crossings(20000)
        truth = {row["event"]: row for row in rows}
        for threshold in (0.0, 0.2):
            _, kept = self.digitized(rows, threshold=threshold)
            for axis in ("y_mm", "z_mm"):
                with self.subTest(threshold=threshold, axis=axis):
                    width = math.sqrt(statistics.fmean((row[axis] - truth[row["event"]][axis]) ** 2 for row in kept))
                    self.assertAlmostEqual(width / kept[0][f"sigma_{axis}"], 1.0, delta=0.03)

    def test_two_hits_of_one_cell_draw_apart_and_match_core(self):
        rows = [{"event": 3, "cell": 8, "sub_index": at, "y_mm": 1.0, "z_mm": 2.0} for at in range(40)]
        status, kept = self.digitized(rows, efficiency=0.5)
        self.assertEqual(status, 0)
        expected = [at for at in range(40) if self.chance(3, 8, at) < 0.5]
        self.assertEqual([row.get("sub_index", 0) for row in kept], expected)
        self.assertTrue(0 < len(expected) < 40)

    @staticmethod
    def chance(event, cell, sub_index):
        stream = rng.SubStream(KEY, event, cell, sub_index)
        stream.group(), stream.group()
        return stream.group()[0]

    def test_rows_that_would_share_their_draws_are_refused(self):
        status, _ = self.digitized([{"event": 3, "cell": 8, "y_mm": 1.0, "z_mm": 2.0}] * 2)
        self.assertEqual(status, 1)

    def test_identities_a_double_cannot_hold_are_refused(self):
        for bad in ({"cell": 2 ** 53}, {"cell": 2 ** 64 + 5}, {"cell": -1}, {"event": 5.7}, {"event": 2 ** 32}, {"sub_index": 2 ** 16}):
            with self.subTest(bad=bad):
                status, _ = self.digitized([{"event": 1, "cell": 2, "y_mm": 0.0, "z_mm": 0.0, **bad}])
                self.assertEqual(status, 1)
        status, _ = self.digitized([{"event": 1, "cell": 2 ** 53 - 1, "y_mm": 0.0, "z_mm": 0.0}])
        self.assertEqual(status, 0)

    def test_a_handoff_to_another_stage_is_refused(self):
        status, kept = self.digitized(self.crossings(3), stage="electronics")
        self.assertEqual((status, kept), (1, []))

    def test_a_row_without_a_position_is_refused(self):
        status, _ = self.digitized([{"event": 1, "cell": 2, "y_mm": 0.0}])
        self.assertEqual(status, 1)


if __name__ == "__main__":
    unittest.main()
