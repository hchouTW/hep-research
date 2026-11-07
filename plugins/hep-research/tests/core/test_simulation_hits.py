"""Hit files: closure against the scorers, and attribution to kept particles (Sections 9.2, 9.3)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.simulation import hits  # noqa: E402

ROWS = [{"event_id": "1", "cell": "5", "edep_MeV": "1.5"}, {"event_id": "1", "cell": "5", "edep_MeV": "0.5"}, {"event_id": "2", "cell": "6", "edep_MeV": "3"}]
TWO_CELLS_ONE_DOUBLE = (2 ** 54, 2 ** 54 + 1)


class Closure(unittest.TestCase):
    def test_sums_by_cell(self):
        self.assertEqual(hits.sums_by_cell(ROWS), {(1, 5, 0): 2.0, (2, 6, 0): 3.0})

    def test_segments_and_cells_a_double_would_merge_stay_apart(self):
        self.assertEqual(float(TWO_CELLS_ONE_DOUBLE[0]), float(TWO_CELLS_ONE_DOUBLE[1]))
        rows = [{"event_id": "1", "cell": str(cell), "segment": segment, "edep_MeV": "1"} for cell in TWO_CELLS_ONE_DOUBLE for segment in ("0", "1")]
        self.assertEqual(len(hits.sums_by_cell(rows)), 4)
        self.assertFalse(hits.closure(hits.sums_by_cell(rows), hits.sums_by_cell(rows[:2]))["ok"])

    def test_equal_sums_close(self):
        self.assertTrue(hits.closure({(1, 5.0): 2.0}, {(1, 5.0): 2.0})["ok"])

    def test_a_missing_cell_or_a_difference_is_caught(self):
        self.assertFalse(hits.closure({(1, 5.0): 2.0}, {})["ok"])
        self.assertFalse(hits.closure({(1, 5.0): 2.0}, {(1, 5.0): 2.0001})["ok"])


class CellFields(unittest.TestCase):
    FIELDS = [{"name": "a", "kind": "copy", "width": 3, "stride": 1}, {"name": "b", "kind": "segmentation", "width": 61, "stride": 8}]

    def test_a_cellid_decodes_into_its_fields(self):
        self.assertEqual(hits.cell_fields(5 + 8 * 9, self.FIELDS), {"a": 5, "b": 9})

    def test_a_cellid_of_64_bits_stays_exact(self):
        self.assertEqual(hits.cell_fields(2 ** 64 - 1, self.FIELDS), {"a": 7, "b": 2 ** 61 - 1})


class Attribution(unittest.TestCase):
    def test_a_hit_on_a_track_that_was_dropped_is_reported(self):
        kept = [{"event_id": "1", "track_id": "1"}]
        self.assertEqual(hits.owners_are_kept(kept, [{"event_id": "1", "track_id": "1"}]), [])
        self.assertEqual(hits.owners_are_kept(kept, [{"event_id": "1", "track_id": "7"}]), [(1, 7)])


class Columns(unittest.TestCase):
    @staticmethod
    def hit(step, owner, track, cell):
        return {"event_id": "1", "step_index": step, "track_id": owner, "step_track_id": track, "cell": cell, "x_mm": "1", "y_mm": "2", "z_mm": "3", "px_MeV": "3", "py_MeV": "0", "pz_MeV": "4", "ekin_MeV": "9", "edep_MeV": "0.5", "time_ns": "4"}

    def test_simreco_takes_the_first_primary_hit_in_each_plane(self):
        rows = [self.hit(2, 1, 1, "5"), self.hit(1, 1, 1, "5"), self.hit(4, 1, 1, "9")]
        crossings = hits.columns_for_simreco(rows, [{"event_id": "1", "track_id": "1", "parent_id": "0", "pdg": "2212"}], {5: 0, 6: 1})
        self.assertEqual([item["plane_id"] for item in crossings], [0])
        self.assertEqual(tuple(crossings[0]), hits.CROSSING_COLUMNS)
        self.assertEqual((crossings[0]["pdg"], crossings[0]["dx"], crossings[0]["dz"]), (2212, 0.6, 0.8))

    def test_a_pruned_secondary_is_not_taken_for_its_primary(self):
        rows = [{**self.hit(1, 1, 7, "5"), "x_mm": "70"}, {**self.hit(2, 1, 1, "5"), "x_mm": "10"}]  # track 7 is pruned, so track 1 owns its hit
        crossings = hits.columns_for_simreco(rows, [{"event_id": "1", "track_id": "1", "parent_id": "0", "pdg": "2212"}], {5: 0})
        self.assertEqual([item["x_mm"] for item in crossings], [10.0])

    def test_a_plane_deposit_is_every_piece_of_the_track_in_it(self):
        rows = [{**self.hit(1, 1, 1, "5"), "edep_MeV": "0.25"}, {**self.hit(2, 1, 1, "5"), "edep_MeV": "2"}, {**self.hit(3, 1, 7, "5"), "edep_MeV": "9"}]
        crossings = hits.columns_for_simreco(rows, [{"event_id": "1", "track_id": "1", "parent_id": "0", "pdg": "2212"}], {5: 0})
        self.assertEqual([item["edep_MeV"] for item in crossings], [2.25])

    def test_every_primary_of_an_event_counts(self):
        particles = [{"event_id": "1", "track_id": track, "parent_id": "0", "pdg": "2212"} for track in ("1", "2")]
        self.assertEqual([item["track_id"] for item in hits.columns_for_simreco([self.hit(1, 2, 2, "5"), self.hit(2, 1, 1, "5")], particles, {5: 0})], [2, 1])

    def test_the_index_records_the_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "hits.root"
            path.write_bytes(b"x")
            record = hits.index("g", {"run": {"events": 3}}, path)
        self.assertEqual((record["schema"], record["events"], len(record["file_sha256"])), (hits.SCHEMA, 3, 64))


if __name__ == "__main__":
    unittest.main()
