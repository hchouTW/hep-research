"""AMS-02 dataset records are metadata only (task M2.4): each validates against the contracts with
this profile's vocabulary, cites ledger IDs that exist and cover it, and carries no data values."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
sys.path.insert(0, str(ROOT.parents[2]))  # plugin root
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary, declared_namespaces  # noqa: E402

PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
RECORDS = sorted((ROOT / "datasets").glob("*.json"))
SOURCES = {s["id"]: s for s in json.loads((ROOT / "evidence" / "sources.json").read_text(encoding="utf-8"))}
CLAIMS = {c["id"]: c for c in json.loads((ROOT / "evidence" / "claims.json").read_text(encoding="utf-8"))}


def profile_vocab() -> Vocabulary:
    v = Vocabulary()
    for name, terms in PROFILE["vocabulary_extensions"].items():
        assert not v.extend(name, terms, declared_namespaces(PROFILE))
    return v


class DatasetRecordTests(unittest.TestCase):
    def test_records_exist(self):
        self.assertGreaterEqual(len(RECORDS), 7)

    def test_each_record_validates_with_profile_vocabulary(self):
        v = profile_vocab()
        for f in RECORDS:
            rep = validate_artifact(json.loads(f.read_text(encoding="utf-8")), v)
            self.assertTrue(rep.ok, (f.name, [x.message for x in rep.errors]))

    def test_profile_level_needs_the_profile(self):
        doc = json.loads(RECORDS[0].read_text(encoding="utf-8"))
        self.assertFalse(validate_artifact(doc, Vocabulary()).ok)

    def test_metadata_only(self):
        for f in RECORDS:
            ext = json.loads(f.read_text(encoding="utf-8"))["extension"]
            self.assertNotIn("data", ext, f.name)
            self.assertEqual(ext["status"], "published", f.name)
            self.assertEqual(ext["covariance"]["status"], "absent", f.name)

    def test_evidence_ids_exist_and_claims_cite_the_source(self):
        for f in RECORDS:
            doc = json.loads(f.read_text(encoding="utf-8"))
            src = doc["extension"]["source_evidence_ids"]
            for sid in src:
                self.assertIn(sid, SOURCES, f.name)
            for eid in doc["provenance"]["evidence_ids"]:
                if ":C" in eid:
                    self.assertTrue(set(CLAIMS[eid]["source_ids"]) & set(src), (f.name, eid))
                else:
                    self.assertIn(eid, SOURCES, f.name)

    def test_period_matches_the_source_row(self):
        for f in RECORDS:
            ext = json.loads(f.read_text(encoding="utf-8"))["extension"]
            per = SOURCES[ext["source_evidence_ids"][0]]["data_taking_period"]
            self.assertEqual((ext["period"]["start"], ext["period"]["end"]), (per["start"], per["end"]), f.name)


if __name__ == "__main__":
    unittest.main()
