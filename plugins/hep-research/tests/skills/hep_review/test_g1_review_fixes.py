"""Regression tests for the independent G1 review (docs/dev/hep-review/reviews/g1-review.md: B1-B4, M1-M4, m1-m8).
Each test reproduces the reviewer's probe and asserts the specified behaviour."""
from __future__ import annotations

import copy
import json
import os
import re
import sqlite3
import subprocess
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
from hep_review_support import coordinator as K  # noqa: E402
from hep_review_support import export as X  # noqa: E402
from hep_review_support import materials as M  # noqa: E402
from hep_review_support import store as S  # noqa: E402
import store_fixtures as F  # noqa: E402

HOST = K.load_host_profile()
CLI = ROOT / "skills" / "hep-review" / "scripts" / "review.py"


def sub(aid, outcome="supported", missing=(), findings=(), **extra):
    body = {"assignment_id": aid, "answers": [{"obligation_id": "O1", "outcome": outcome, "reasoning": "r",
                                               "missing_inputs": list(missing), "findings": list(findings),
                                               "attempts": [{"method": "recompute", "observation": "completed",
                                                             "tools": ["python3"]}],
                                               "evidence": [{"requirement": "E", "summary": "s"}]}]}
    body["answers"][0].update(extra)
    return json.dumps(body).encode()


class Base(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)
        self.s = S.Store(self.d / "store", location=F.TEMP_LOCATION)
        self.session = C.start_session(self.s, "ctx-1", "coord")
        self.drops = self.d / "drops"
        for i, o in enumerate(([F.intent()], [F.manifest(self.s)], [F.plan(1, [F.obligation("O1")])]), 1):
            C.append(self.s, self.session, o, f"op-{i}")

    def tearDown(self):
        self.s.close()
        self.temp_dir.cleanup()

    def assign(self, actor="rev-1", **disp):
        d = {"via": "agent-tool", "actor": actor, "authors_declared": True, "invocation_id": f"inv-{actor}"} | disp
        a = K.make_assignment(self.s, "ctx-1", HOST, d, spec_id="spec-1", plan_revision=1)
        C.append(self.s, self.session, [a], f"op-{a['id']}")
        return a

    def submit(self, a, raw):
        p = K.drop_path(self.drops, a["id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
        return K.ingest(self.s, "ctx-1", a, self.drops)

    def violated_record(self):
        a = self.assign()
        man = [o for c in self.s.load_bundle("ctx-1")["commits"] for o in c["objects"] if o["record_kind"] == "manifest"]
        loc = {"material_id": "M1", "digest": man[0]["materials"][0]["raw_ref"]["digest"]}
        rec = self.submit(a, sub(a["id"], "violated", findings=[{"claim": "c", "element": "e", "locator": loc}]))
        C.append(self.s, self.session, [rec], "op-violated")
        return rec

    def summary(self):
        return K.report(self.s, self.session, "ctx-1")["attestation"]["output_summary"]


class B1Rollback(Base):
    def test_deleting_own_commit_and_resetting_the_head_is_broken(self):
        self.violated_record()
        self.assertFalse(self.summary())
        con = sqlite3.connect(self.d / "store" / S.DB_NAME)
        top = con.execute("SELECT seq, digest FROM commits ORDER BY seq DESC LIMIT 2").fetchall()
        con.execute("DELETE FROM commits WHERE digest=?", (top[0][1],))
        con.execute("UPDATE heads SET seq=?, commit_digest=?", (top[1][0], top[1][1]))
        con.commit()
        con.close()
        r = C.head_continuity(self.s, self.session)
        self.assertEqual(r["status"], "broken")
        self.assertIn(r["basis"]["case"], ("saved-value-not-on-chain", "head-rolled-back"))
        self.assertFalse(self.summary())


class B2ForkMigrate(Base):
    def test_fork_only_when_broken_and_never_before_own_commits(self):
        self.violated_record()
        with self.assertRaises(C.ContinuityBroken):
            C.fork(self.s, self.session, last_trusted_seq=3, operation_id="op-fork")
        other = S.Store(self.d / "store", location=F.TEMP_LOCATION)
        other.append("ctx-1", [F.assignment("asg-x", "intruder")], other.head("ctx-1"), "op-foreign",
                     writer_session_id="x")
        other.close()
        self.assertEqual(C.head_continuity(self.s, self.session)["status"], "broken")
        with self.assertRaises(ValueError):
            C.fork(self.s, self.session, last_trusted_seq=3, operation_id="op-fork-early")
        top_own = self.s.head("ctx-1")["seq"] - 1
        C.fork(self.s, self.session, last_trusted_seq=top_own, operation_id="op-fork-ok")
        out = K.report(self.s, self.session, "ctx-1")
        text = " ".join(out["attestation"]["disclosure"])
        self.assertIn("fork", text)
        self.assertIn("foreign-commits-appended", text)
        self.assertTrue(out["layer1"]["flags"]["has_supported_defects"])  # the negative record survived

    def test_migrate_must_carry_every_record(self):
        self.violated_record()

        def drop_records(objs):
            return [o for o in objs if o["record_kind"] != "record"]
        with self.assertRaises(ValueError):
            C.migrate(self.s, self.session, drop_records, "op-mig")
        C.migrate(self.s, self.session, lambda objs: objs, "op-mig-ok")
        self.assertIn("migration", " ".join(K.report(self.s, self.session, "ctx-1")["attestation"]["disclosure"]))


class B3Assignments(Base):
    def test_store_refuses_condition_bases_the_host_cannot_provide(self):
        a = F.assignment("asg-9", "rev-9")
        a["conditions"]["no-other-evaluations-seen"] = {"satisfied": True, "basis": "observed"}
        with self.assertRaises(S.AdmissionRefused) as cm:
            C.append(self.s, self.session, [a], "op-a")
        self.assertIn("assignment.basis_exceeds_host", cm.exception.codes)
        b = F.assignment("asg-9", "rev-9")
        b["dispatch"] = {"via": "same-context"}
        with self.assertRaises(S.AdmissionRefused) as cm:
            C.append(self.s, self.session, [b], "op-b")
        self.assertIn("assignment.basis_exceeds_host", cm.exception.codes)
        c = F.assignment("asg-9", "rev-9")
        c["host_profile_digest"] = "0" * 64
        with self.assertRaises(S.AdmissionRefused) as cm:
            C.append(self.s, self.session, [c], "op-c")
        self.assertIn("assignment.host_profile", cm.exception.codes)

    def test_make_assignment_needs_a_dispatch_record_for_observed_fresh_context(self):
        a = K.make_assignment(self.s, "ctx-1", HOST, {"via": "agent-tool", "actor": "r", "authors_declared": True},
                              spec_id="spec-1", plan_revision=1)
        self.assertEqual(a["conditions"]["fresh-context"]["basis"], "unknown")
        b = self.assign("r2")
        self.assertEqual(b["conditions"]["fresh-context"], {"satisfied": True, "basis": "observed"})
        self.assertEqual(b["dispatch"]["invocation_id"], "inv-r2")
        self.assertEqual(b["host_profile_digest"], H.metadata_digest(HOST))


class B4Derivation(Base):
    def test_edited_record_is_refused_at_commit(self):
        a = self.assign()
        rec = self.submit(a, sub(a["id"], "undetermined", missing=["covariance"]))
        edited = copy.deepcopy(rec)
        edited["answers"][0]["verdict"] = "supported"
        edited["answers"][0]["missing_inputs"] = []
        with self.assertRaises(S.AdmissionRefused) as cm:
            C.append(self.s, self.session, [edited], "op-edited")
        self.assertIn("record.not_derived_from_raw", cm.exception.codes)
        C.append(self.s, self.session, [rec], "op-true")

    def test_cli_ingest_commits_the_record_itself(self):
        a = self.assign()
        p = K.drop_path(self.drops, a["id"])
        p.parent.mkdir(parents=True)
        p.write_bytes(sub(a["id"]))
        state = self.d / "state.json"
        state.write_text(self.session.to_json())
        self.s.close()
        loc = S.check_location(self.d)
        if not loc["supported"]:
            self.skipTest(loc["reason"])
        r = subprocess.run([sys.executable, str(CLI), "--store", str(self.d / "store"), "ingest", "--context", "ctx-1",
                            "--state", str(state), "--assignment", a["id"], "--drop-root", str(self.drops)],
                           capture_output=True, text=True, timeout=120)
        out = json.loads(r.stdout)
        self.assertEqual(out["result"], "committed", out)
        self.s = S.Store(self.d / "store", location=F.TEMP_LOCATION)


class M1Authors(Base):
    def test_unknown_author_list_gives_unknown_non_author(self):
        snap = M.snapshot(Path(__file__).parent, ["__init__.py"], self.d / "snap")
        mat = snap["materials"][0]
        self.assertEqual(mat["authors_basis"], "unknown")
        objs = [{"record_kind": "manifest", "id": "m", "materials": [dict(mat, material_id="M1")]}]
        self.assertEqual(K.non_author_condition(objs, ["M1"], "author-a", authors_declared=True),
                         {"satisfied": None, "basis": "unknown"})


class M2Malformed(Base):
    def test_wrong_typed_fields_are_recorded_not_crashing(self):
        a = self.assign()
        for extra in ({"attempts": ["x"]}, {"missing_inputs": 3}, {"missing_inputs": "abc"},
                      {"findings": [{"claim": "c", "locator": {"material_id": ["x"]}}]}, {"evidence": "e"}):
            with self.subTest(extra):
                raw = sub(a["id"], **extra)
                rec = K.parse_submission(self.s, "ctx-1", a, raw, M.raw_ref("r", H.raw_digest(raw)), "file-transfer")
                self.assertTrue(rec["limitations"])
        body = json.loads(sub(a["id"]))
        body["suggested_obligations"] = 5
        raw = json.dumps(body).encode()
        rec = K.parse_submission(self.s, "ctx-1", a, raw, M.raw_ref("r", H.raw_digest(raw)), "file-transfer")
        self.assertEqual(rec["suggested_obligations"], [])


class M3Location(unittest.TestCase):
    def test_symlink_into_a_sync_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            sync = Path(d) / "Library" / "CloudStorage" / "Dropbox"
            sync.mkdir(parents=True)
            link = Path(d) / "store-link"
            os.symlink(sync, link)
            loc = S.check_location(link / "hep-review", mounts_text="/dev/x on / (apfs, local)\n", platform="darwin")
            self.assertFalse(loc["supported"])
            self.assertTrue(loc["sync_folder"])


class M4Docs(unittest.TestCase):
    def test_every_documented_command_exists(self):
        text = (ROOT / "skills" / "hep-review" / "references" / "workflow-and-tiers.md").read_text()
        table = text[text.index("| Command | Does |"):]
        commands = set(re.findall(r"^\| `([a-z0-9-]+)", table, re.M)) | set(re.findall(r"/ `([a-z0-9-]+)", table))
        help_text = subprocess.run([sys.executable, str(CLI), "--help"], capture_output=True, text=True,
                                   timeout=60).stdout
        for c in sorted(commands):
            with self.subTest(c):
                self.assertIn(c, help_text)
                r = subprocess.run([sys.executable, str(CLI), c, "--help"], capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0, r.stderr)
        for c in ("assign", "packets", "ingest", "report", "checkpoint"):
            self.assertIn(c, commands)


class Minors(Base):
    def test_m1_packet_form_has_locator_and_no_bare_not_applicable(self):
        text = K.packet_text({"assignment_id": "a", "obligations": [], "materials": [], "drop": "d"})
        self.assertIn('"locator"', text)
        self.assertNotIn("not-applicable", text)

    def test_m1_finding_evidence_is_kept(self):
        a = self.assign()
        raw = sub(a["id"], "violated", findings=[{"claim": "c", "element": "e", "evidence": "recomputed 0.042"}])
        rec = K.parse_submission(self.s, "ctx-1", a, raw, M.raw_ref("r", H.raw_digest(raw)), "file-transfer")
        self.assertEqual(rec["findings"][0]["evidence_text"], "recomputed 0.042")

    def test_m2_unknown_persistence_is_disclosed(self):
        out = K.report(self.s, self.session, "ctx-1")
        self.assertIn("persistence", " ".join(out["attestation"]["disclosure"]))

    def test_m3_export_headers_and_checkpoint_context_are_bound(self):
        X.export(self.s, "ctx-1", self.d / "e.json")
        doc = json.loads((self.d / "e.json").read_bytes())
        doc["context_id"] = "other"
        (self.d / "x.json").write_bytes(H.encode(doc))
        self.assertEqual(X.verify_export(self.d / "x.json")["internal_consistency"], "failed")
        cp = dict(C.parse_checkpoint(C.checkpoint_line(self.s, "ctx-1")), context_id="other")
        self.assertEqual(X.verify_export(self.d / "e.json", cp)["checkpoint"], "mismatch")

    def test_m4_new_segment_id_is_unique(self):
        self.s.conn.execute("INSERT INTO segments VALUES('ctx-1','seg-7','x',NULL)")
        self.assertEqual(C._next_segment(self.s, "ctx-1"), "seg-8")

    def test_m5_drop_root_symlink_is_refused(self):
        real = self.d / "real-drops" / "asg-1"
        real.mkdir(parents=True)
        (real / "submission.json").write_bytes(b"{}")
        os.symlink(self.d / "real-drops", self.d / "drops-link")
        with self.assertRaises(M.ReadRefused):
            M.ingest_submission(self.d / "drops-link", "asg-1/submission.json")

    def test_m6_material_supplied_after_dispatch_contaminates(self):
        a = self.assign()
        C.append(self.s, self.session, [K.supply(self.s, "ctx-1", a, source="user", reason="earlier notes",
                                                 contains_evaluation=True)], "op-supply")
        rec = self.submit(a, sub(a["id"]))
        C.append(self.s, self.session, [rec], "op-rec")
        self.assertEqual(K.report(self.s, self.session, "ctx-1")["layer1"]["achieved_tier"], "R1")

    def test_m7_confirmation_only_completes_separation(self):
        v = K.marginal_value({"gap": "g", "why": "w", "cost": "c"},
                             {"new_evidence": [], "same_source_as": None, "confirmed": ["F1"]})
        self.assertTrue(v["separation_completed"])
        self.assertFalse(v["new_independent_evidence"])

    def test_m8_authority_and_declared_digest(self):
        with self.assertRaises(ValueError):
            K.add_obligation(self.s, self.session, "ctx-1", F.obligation("O2"), reason="r", authority="anyone")
        a = self.assign()
        p = K.drop_path(self.drops, a["id"])
        p.parent.mkdir(parents=True)
        p.write_bytes(sub(a["id"]))
        rec = K.ingest(self.s, "ctx-1", a, self.drops, declared_digest="1" * 64)
        self.assertEqual((rec["submission_fidelity"], rec["declared_digest"]), ("mismatch", "1" * 64))

    def test_m8_skill_text_covers_refused_store_and_ephemeral_export(self):
        text = (ROOT / "skills" / "hep-review" / "SKILL.md").read_text()
        self.assertIn("store location is refused", text)
        self.assertIn("export before the session ends", text)


if __name__ == "__main__":
    unittest.main()
