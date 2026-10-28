"""hep-review head continuity, checkpoints, fork and migration segments, export / verify / import
(spec v9 sections 11.3, 11.4, 11.6).

Cases N08, N09, N32, N43, N44, N49, N52, N53, N54, N66, P13 and the export side of N60."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from hep_review_support import continuity as C  # noqa: E402
from hep_review_support import export as X  # noqa: E402
from hep_review_support import store as S  # noqa: E402
import store_fixtures as F  # noqa: E402

V = H.LATEST_VALIDATOR


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)
        self.s = S.Store(self.d / "store", location=F.TEMP_LOCATION)

    def tearDown(self):
        self.s.close()
        self.temp_dir.cleanup()

    def seeded_session(self, session="s-1"):
        st = C.start_session(self.s, "ctx-1", session)
        objs = [[F.intent()], [F.manifest(self.s)], [F.plan(1, [F.obligation("O1")])],
                [F.assignment("asg-1", "rev-1")], [F.record(self.s, "rec-1", "asg-1", "rev-1")]]
        for i, o in enumerate(objs, 1):
            C.append(self.s, st, o, f"op-{session}-{i}")
        return st

    def foreign_append(self, objs, op):
        """Someone with shell access appends a correctly chained commit with the store API (case N32)."""
        other = S.Store(self.d / "store", location=F.TEMP_LOCATION)
        other.append("ctx-1", objs, other.head("ctx-1"), op, writer_session_id="intruder")
        other.close()


class Continuity(Base):
    def test_n53_genesis_by_this_session_anchors_and_verifies(self):
        st = self.seeded_session()
        self.assertEqual(st.start, "anchored-genesis")
        self.assertEqual(C.head_continuity(self.s, st)["status"], "verified")

    def test_n49_n52_no_checkpoint_is_unverified_for_the_whole_session(self):
        self.seeded_session("s-1")
        st2 = C.start_session(self.s, "ctx-1", "s-2")
        self.assertEqual(st2.start, "unanchored-start")
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "unverified")
        C.append(self.s, st2, [F.assignment("asg-2", "rev-2")], "op-s2-1")
        r = C.head_continuity(self.s, st2)
        self.assertEqual(r["status"], "unverified")
        self.assertIn("checkpoint", r["basis"]["how_to_verify"])

    def test_n53_lost_state_is_a_new_session(self):
        self.seeded_session("s-1")
        st = C.CoordinatorState.from_json(json.dumps({"session_id": "s-1", "context_id": "ctx-1"}))
        self.assertEqual(C.head_continuity(self.s, st)["status"], "unverified")

    def test_checkpoint_round_trip_and_anchor(self):
        st = self.seeded_session("s-1")
        line = C.checkpoint_line(self.s, "ctx-1")
        cp = C.parse_checkpoint(line)
        self.assertEqual(cp["seq"], 5)
        st2 = C.start_session(self.s, "ctx-1", "s-2", checkpoint=cp)
        self.assertEqual(st2.start, "anchored-checkpoint")
        C.append(self.s, st2, [F.assignment("asg-2", "rev-2")], "op-s2-1")
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "verified")
        del st

    def test_state_file_round_trip(self):
        st = self.seeded_session()
        st2 = C.CoordinatorState.from_json(st.to_json())
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "verified")

    def test_n32_foreign_commit_breaks_continuity_and_appending_stops(self):
        st = self.seeded_session()
        self.foreign_append([F.assignment("asg-x", "intruder")], "op-foreign")
        r = C.head_continuity(self.s, st)
        self.assertEqual(r["status"], "broken")
        self.assertEqual(r["basis"]["case"], "foreign-commits-appended")
        with self.assertRaises(C.ContinuityBroken):
            C.append(self.s, st, [F.assignment("asg-2", "rev-2")], "op-after")

    def test_checkpoint_not_on_chain_is_broken(self):
        self.seeded_session()
        cp = dict(C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1")), commit_digest="0" * 64)
        st = C.start_session(self.s, "ctx-1", "s-2", checkpoint=cp)
        self.assertEqual(C.head_continuity(self.s, st)["status"], "broken")

    def test_n66_saved_value_not_on_chain_is_distinguished(self):
        st = self.seeded_session()
        st.written[-1] = "f" * 64  # a coordinator transcription error
        r = C.head_continuity(self.s, st)
        self.assertEqual((r["status"], r["basis"]["case"]), ("broken", "saved-value-not-on-chain"))

    def test_n66_fork_segment_recovers_and_keeps_old_segment(self):
        st = self.seeded_session()
        trusted = C.checkpoint_line(self.s, "ctx-1")
        self.foreign_append([F.assignment("asg-x", "intruder")], "op-foreign")
        self.assertEqual(C.head_continuity(self.s, st)["status"], "broken")
        st2 = C.start_session(self.s, "ctx-1", "s-2", checkpoint=C.parse_checkpoint(trusted))
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "broken")
        g = C.fork(self.s, st2, last_trusted_seq=5, operation_id="op-fork")
        segs = self.s.segments("ctx-1")
        self.assertEqual([x["segment_id"] for x in segs], ["seg-1", "seg-2"])
        origin = segs[1]["origin"]
        self.assertEqual(origin["forked_from"]["seq"], 5)
        self.assertEqual(len(origin["excluded_commits"]), 1)
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "verified")
        b = self.s.load_bundle("ctx-1")
        self.assertNotIn("asg-x", json.dumps(b))
        self.assertTrue(H.project(H.validate(b, V), V)["summary_eligible"])
        old = self.s.load_bundle("ctx-1", segment_id="seg-1")  # the old segment is kept as evidence
        self.assertIn("asg-x", json.dumps(old))
        del g

    def test_n44_migration_segment_leaves_old_segment_untouched(self):
        st = self.seeded_session()
        before = self.s.load_bundle("ctx-1")

        def transform(objs):
            out = []
            for o in objs:
                o = dict(o)
                if o["record_kind"] == "manifest":
                    o["limitations"] = ["rewritten by a 0.1.0 schema migration"]
                out.append(o)
            return out
        C.migrate(self.s, st, transform, "op-migrate")
        segs = self.s.segments("ctx-1")
        self.assertEqual(segs[-1]["origin"]["migrated_from"]["seq"], 5)
        self.assertEqual(self.s.load_bundle("ctx-1", segment_id="seg-1"), before)
        self.assertEqual(C.head_continuity(self.s, st)["status"], "verified")


class Export(Base):
    def test_n09_self_consistent_export_without_checkpoint(self):
        self.seeded_session()
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        r = X.verify_export(p)
        self.assertEqual(r["internal_consistency"], "ok")
        self.assertEqual(r["checkpoint"], "not-provided")
        self.assertIn("producer identity and full history are unknown", r["claim"])

    def test_n43_checkpoint_at_n_export_to_m(self):
        st = self.seeded_session()
        cp = C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1"))
        C.append(self.s, st, [F.assignment("asg-2", "rev-2")], "op-6")
        C.append(self.s, st, [F.assignment("asg-3", "rev-3")], "op-7")
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        r = X.verify_export(p, cp)
        self.assertEqual(r["checkpoint"], "matches")
        self.assertEqual(r["appended_after_checkpoint_unconfirmed"], [6, 7])

    def test_n08_p13_deleted_negative_commit_and_recomputed_chain_fail_against_checkpoint(self):
        st = self.seeded_session()
        C.append(self.s, st, [F.assignment("asg-2", "rev-2")], "op-6")
        C.append(self.s, st, [F.record(self.s, "rec-2", "asg-2", "rev-2", verdict="violated", finding=True)], "op-7")
        C.append(self.s, st, [F.assignment("asg-3", "rev-3")], "op-8")
        cp = C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1"))  # seq 8
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        doc = json.loads(p.read_bytes())
        # delete the negative commit 7 and recompute the whole chain so that it is self-consistent again
        doc["commits"] = [c for c in doc["commits"] if c["commit"]["seq"] != 7]
        prev = None
        for i, c in enumerate(doc["commits"], 1):
            c["commit"]["seq"], c["commit"]["prev_commit_digest"] = i, prev
            c["digest"] = H.metadata_digest(c["commit"])
            prev = c["digest"]
        doc["as_of_seq"], doc["as_of_commit_digest"] = len(doc["commits"]), prev
        p2 = self.d / "tampered.json"
        p2.write_bytes(H.encode(doc))
        self.assertEqual(X.verify_export(p2)["internal_consistency"], "ok")  # self-consistent after recompute
        self.assertEqual(X.verify_export(p2, cp)["checkpoint"], "mismatch")
        # without recomputing, the deletion breaks the chain itself
        raw = json.loads(p.read_bytes())
        raw["commits"] = [c for c in raw["commits"] if c["commit"]["seq"] != 7]
        p3 = self.d / "cut.json"
        p3.write_bytes(H.encode(raw))
        self.assertEqual(X.verify_export(p3)["internal_consistency"], "failed")
        with self.assertRaises(X.ImportRefused):
            X.import_export(p2, cp, self.d / "s2", location=F.TEMP_LOCATION, session_id="s-9")

    def test_tampered_blob_fails_internal_consistency(self):
        self.seeded_session()
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        doc = json.loads(p.read_bytes())
        doc["blobs"][0]["base64"] = "AAAA"
        p.write_bytes(H.encode(doc))
        r = X.verify_export(p)
        self.assertEqual(r["internal_consistency"], "failed")

    def test_partial_export_is_marked(self):
        self.seeded_session()
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p, as_of_seq=3, partial=True)
        r = X.verify_export(p)
        self.assertTrue(r["partial"])
        self.assertEqual(r["as_of_seq"], 3)

    def test_n54_export_then_import_with_checkpoint_is_verified_and_appendable(self):
        st = self.seeded_session()
        cp = C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1"))
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        s2, st2 = X.import_export(p, cp, self.d / "imported", location=F.TEMP_LOCATION, session_id="s-next")
        try:
            self.assertEqual(C.head_continuity(s2, st2)["status"], "verified")
            C.append(s2, st2, [F.assignment("asg-2", "rev-2")], "op-next-1")
            self.assertEqual(C.head_continuity(s2, st2)["status"], "verified")
        finally:
            s2.close()
        del st

    def test_n60_third_party_recomputes_layer1_byte_for_byte_from_the_export(self):
        self.seeded_session()
        original = H.encode(H.project(H.validate(self.s.load_bundle("ctx-1"), V), V))
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        s2, _ = X.import_export(p, None, self.d / "third", location=F.TEMP_LOCATION, session_id="t")
        try:
            again = H.encode(H.project(H.validate(s2.load_bundle("ctx-1"), V), V))
        finally:
            s2.close()
        self.assertEqual(original, again)
        self.assertEqual(H.encode(H.project(H.validate(X.bundle_from_export(p), V), V)), original)

    def test_import_refuses_into_a_store_that_has_the_context(self):
        self.seeded_session()
        p = self.d / "e.json"
        X.export(self.s, "ctx-1", p)
        with self.assertRaises(X.ImportRefused):
            X.import_export(p, None, self.d / "store", location=F.TEMP_LOCATION, session_id="t")


class Raw(Base):
    def test_store_file_edit_that_rewrites_history_is_detected_by_checkpoint(self):
        st = self.seeded_session()
        cp = C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1"))
        con = sqlite3.connect(self.d / "store" / S.DB_NAME)
        con.execute("UPDATE commits SET digest=? WHERE seq=5", ("e" * 64,))
        con.execute("UPDATE heads SET commit_digest=?", ("e" * 64,))
        con.commit()
        con.close()
        self.assertEqual(C.head_continuity(self.s, st)["status"], "broken")
        st2 = C.start_session(self.s, "ctx-1", "s-2", checkpoint=cp)
        self.assertEqual(C.head_continuity(self.s, st2)["status"], "broken")


if __name__ == "__main__":
    unittest.main()
