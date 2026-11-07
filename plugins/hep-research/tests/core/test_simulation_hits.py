"""Hit files: closure against the scorers, and attribution to kept particles (Sections 9.2, 9.3)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import hits  # noqa: E402

ROWS = [{"event_id": "1", "cell": "5.0", "edep_MeV": "1.5"}, {"event_id": "1", "cell": "5.0", "edep_MeV": "0.5"}, {"event_id": "2", "cell": "6.0", "edep_MeV": "3"}]


class Closure(unittest.TestCase):
    def test_sums_by_cell(self):
        self.assertEqual(hits.sums_by_cell(ROWS), {(1, 5.0): 2.0, (2, 6.0): 3.0})

    def test_equal_sums_close(self):
        self.assertTrue(hits.closure({(1, 5.0): 2.0}, {(1, 5.0): 2.0})["ok"])

    def test_a_missing_cell_or_a_difference_is_caught(self):
        self.assertFalse(hits.closure({(1, 5.0): 2.0}, {})["ok"])
        self.assertFalse(hits.closure({(1, 5.0): 2.0}, {(1, 5.0): 2.0001})["ok"])


class Attribution(unittest.TestCase):
    def test_a_hit_on_a_track_that_was_dropped_is_reported(self):
        kept = [{"event_id": "1", "track_id": "1"}]
        self.assertEqual(hits.owners_are_kept(kept, [{"event_id": "1", "track_id": "1"}]), [])
        self.assertEqual(hits.owners_are_kept(kept, [{"event_id": "1", "track_id": "7"}]), [(1, 7)])


class Columns(unittest.TestCase):
    def test_simreco_takes_the_first_primary_hit_in_each_plane(self):
        def row(step, track, cell):
            return {"event_id": "1", "step_index": step, "track_id": track, "cell": cell, "x_mm": "1", "y_mm": "2", "z_mm": "3", "px_MeV": "3", "py_MeV": "0", "pz_MeV": "4", "ekin_MeV": "9", "edep_MeV": "0.5", "time_ns": "4"}
        rows = [row(2, 1, 5.0), row(1, 1, 5.0), row(3, 2, 6.0), row(4, 1, 9.0)]
        crossings = hits.columns_for_simreco(rows, [{"event_id": "1", "track_id": "1", "pdg": "2212"}], {5.0: 0, 6.0: 1})
        self.assertEqual([item["plane_id"] for item in crossings], [0])
        self.assertEqual(tuple(crossings[0]), hits.CROSSING_COLUMNS)
        self.assertEqual((crossings[0]["pdg"], crossings[0]["dx"], crossings[0]["dz"]), (2212, 0.6, 0.8))

    def test_the_index_records_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "hits.root"
            path.write_bytes(b"x")
            record = hits.index("g", {"run": {"events": 3}}, path)
        self.assertEqual((record["schema"], record["events"], len(record["file_sha256"])), (hits.SCHEMA, 3, 64))


if __name__ == "__main__":
    unittest.main()
