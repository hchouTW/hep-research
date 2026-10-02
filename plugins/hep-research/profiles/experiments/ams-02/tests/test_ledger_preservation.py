"""Negative tests for tools/check_ams_ledger_preservation.py (AC08): every kind of silent
change between the legacy ledger and the profile ledger must be reported."""
import copy
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PLUGIN / "tools"))
import check_ams_ledger_preservation as cap  # noqa: E402

OLD = [{"id": "S01", "title": "t", "access_date": "2026-09-20", "superseded_by": []},
       {"id": "S02", "title": "u", "access_date": None, "superseded_by": ["S01"]}]
IDMAP = {"S01": "ams02:S01", "S02": "ams02:S02"}


def migrated():
    return [{"id": "ams02:S01", "legacy_id": "S01", "title": "t", "verification_date": "2026-09-20", "superseded_by": [],
             "formal_status": "published"},
            {"id": "ams02:S02", "legacy_id": "S02", "title": "u", "verification_date": "unknown",
             "superseded_by": ["ams02:S01"], "formal_status": "published"}]


def diffs(new):
    out = []
    cap.compare(OLD, new, "source", IDMAP, out)
    return out


class PreservationTests(unittest.TestCase):
    def test_faithful_migration_passes(self):
        self.assertEqual(diffs(migrated()), [])

    def test_changed_field(self):
        new = migrated(); new[0]["title"] = "edited"
        self.assertTrue(any("field 'title' changed" in d for d in diffs(new)))

    def test_missing_record(self):
        self.assertTrue(any("missing" in d for d in diffs(migrated()[:1])))

    def test_reference_not_namespaced(self):
        new = migrated(); new[1]["superseded_by"] = ["S01"]
        self.assertTrue(any("superseded_by" in d for d in diffs(new)))

    def test_date_changed(self):
        new = migrated(); new[0]["verification_date"] = "2026-10-01"
        self.assertTrue(any("verification_date" in d for d in diffs(new)))

    def test_undeclared_field(self):
        new = migrated(); new[0]["value"] = 1.0
        self.assertTrue(any("undeclared new field 'value'" in d for d in diffs(new)))

    def test_id_not_matching_map(self):
        new = copy.deepcopy(migrated()); new[0]["id"] = "ams02:S99"
        self.assertTrue(any("legacy_id_map" in d for d in diffs(new)))


if __name__ == "__main__":
    unittest.main()
