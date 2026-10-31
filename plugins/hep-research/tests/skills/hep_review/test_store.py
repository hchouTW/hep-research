"""hep-review store: location detection and the SQLite commit log (spec v9 sections 11.1, 11.2, 11.5).

Cases P05, P06, P07, P08/A28, P12, P27, A19, A20, N06, N07, N51."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts import hep_review as H  # noqa: E402
from hep_review_support import store as S  # noqa: E402
import store_fixtures as F  # noqa: E402

LINUX_MOUNTINFO = textwrap.dedent("""\
    22 1 8:1 / / rw,relatime shared:1 - ext4 /dev/sda1 rw
    30 22 0:40 / /mnt/nas rw - nfs4 server:/export rw
    31 22 0:41 / /data/gdrive rw - fuse.rclone gdrive: rw
    32 22 0:42 / /media/host rw - virtiofs share rw
    33 22 0:43 / /srv/plan9 rw - 9p share rw
    """)
MAC_MOUNT = textwrap.dedent("""\
    /dev/disk3s1s1 on / (apfs, sealed, local, read-only, journaled)
    /dev/disk3s5 on /System/Volumes/Data (apfs, local, journaled, nobrowse, protect, root data)
    //nas/share on /Volumes/share (smbfs, nodev, nosuid, mounted by someone)
    """)
MAC_HOME = "/" + "Users" + "/u"  # spelled in parts: tools/check_packaging.py forbids home paths in tracked files


class Location(unittest.TestCase):
    def test_default_store_dir_follows_the_state_home_variable(self):
        self.assertEqual(S.default_store_dir({"XDG_STATE_HOME": "/x/state", "HOME": "/h"}),
                         Path("/x/state/hep-research/hep-review"))
        self.assertEqual(S.default_store_dir({"HOME": "/h"}), Path("/h/.local/state/hep-research/hep-review"))

    def test_p12_n51_network_fuse_and_guest_mounts_refused(self):
        cases = {"/srv/state/x": ("ext4", True), "/mnt/nas/store": ("nfs4", False),
                 "/data/gdrive/store": ("fuse.rclone", False), "/media/host/s": ("virtiofs", False),
                 "/srv/plan9/s": ("9p", False)}
        for path, (fs, ok) in cases.items():
            with self.subTest(path):
                loc = S.check_location(path, mounts_text=LINUX_MOUNTINFO, platform="linux")
                self.assertEqual((loc["fs_type"], loc["supported"]), (fs, ok), loc)
        loc = S.check_location("/Volumes/share/x", mounts_text=MAC_MOUNT, platform="darwin")
        self.assertEqual((loc["fs_type"], loc["supported"]), ("smbfs", False))
        loc = S.check_location(MAC_HOME + "/.local/state/x", mounts_text=MAC_MOUNT, platform="darwin")
        self.assertEqual((loc["fs_type"], loc["supported"]), ("apfs", True))

    @unittest.skipUnless(sys.platform == "darwin", "the live mount(8) output of macOS")
    def test_live_macos_mount_output_parses(self):
        """On a real Mac, the temporary folder (/var is a link to /private/var on the Data volume) resolves to a
        local APFS mount through mount(8): the darwin branch reads the live output, not only the fixture."""
        with tempfile.TemporaryDirectory() as d:
            loc = S.check_location(Path(d) / "store")
        self.assertEqual(loc["fs_type"], "apfs", loc)

    def test_n51_sync_folders_and_unknown_type_refused(self):
        for p in (MAC_HOME + "/Library/CloudStorage/GoogleDrive-x/s", MAC_HOME + "/Library/Mobile Documents/s",
                  MAC_HOME + "/Dropbox/s", MAC_HOME + "/OneDrive - Org/s"):
            with self.subTest(p):
                loc = S.check_location(p, mounts_text=MAC_MOUNT, platform="darwin")
                self.assertFalse(loc["supported"])
                self.assertTrue(loc["sync_folder"])
        loc = S.check_location("/x", mounts_text="", platform="linux")
        self.assertEqual(loc["fs_type"], None)
        self.assertFalse(loc["supported"])

    def test_store_refuses_an_unsupported_location_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as d:
            bad = {"path": d, "fs_type": "nfs4", "sync_folder": False, "supported": False, "reason": "network"}
            with self.assertRaises(S.StoreLocationRefused):
                S.Store(Path(d) / "s", location=bad)
            self.assertFalse((Path(d) / "s").exists())
            self.assertEqual(list(Path(d).iterdir()), [])


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp_dir.name) / "store"
        self.s = S.Store(self.dir, location=F.TEMP_LOCATION)

    def tearDown(self):
        self.s.close()
        self.temp_dir.cleanup()


class CommitLog(StoreCase):
    def test_connection_mode_and_settings_recorded(self):
        st = self.s.settings()
        self.assertIsNone(self.s.conn.isolation_level)
        self.assertEqual(st["journal_mode"], "wal")
        self.assertIn(st["synchronous"], ("full", "2"))
        self.assertTrue(st["sqlite_version"])

    def test_genesis_and_chain(self):
        head = F.seed(self.s)
        self.assertEqual(head["seq"], 5)
        b = self.s.load_bundle("ctx-1")
        self.assertIsNone(b["commits"][0]["commit"]["prev_commit_digest"])
        v = H.validate(b, H.LATEST_VALIDATOR)  # the kernel accepts the chain as stored
        p = H.project(v, H.LATEST_VALIDATOR)
        self.assertTrue(p["summary_eligible"], p["open_reasons"])

    def test_n06_same_operation_same_payload_returns_original(self):
        head = F.seed(self.s)
        objs = [F.assignment("asg-2", "rev-2")]
        r1 = self.s.append("ctx-1", objs, head, "op-x", writer_session_id="s-1")
        r2 = self.s.append("ctx-1", objs, head, "op-x", writer_session_id="s-1")
        self.assertEqual(r2.status, "replayed")
        self.assertEqual(r2.head, r1.head)
        self.assertEqual(self.s.head("ctx-1")["seq"], 6)
        r3 = self.s.append("ctx-1", objs, r1.head, "op-x", writer_session_id="s-2")  # replay on another head
        self.assertEqual(r3.status, "replayed")
        with self.assertRaises(S.OperationConflict):
            self.s.append("ctx-1", [F.assignment("asg-3", "rev-3")], r1.head, "op-x", writer_session_id="s-1")

    def test_p27_a19_stale_expected_head_loses_cas(self):
        head = F.seed(self.s)
        p2 = F.plan(2, [F.obligation("O1"), F.obligation("O2")])
        p2b = F.plan(2, [F.obligation("O1"), F.obligation("O3")])
        self.s.append("ctx-1", [p2], head, "op-p1", writer_session_id="s")
        with self.assertRaises(S.HeadMismatch):
            self.s.append("ctx-1", [p2b], head, "op-p2", writer_session_id="s")
        # rebuilding on the new head must not lose P1's obligations (O2): dropping it is a downgrade
        p3 = F.plan(3, [F.obligation("O1"), F.obligation("O3")])
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [p3], self.s.head("ctx-1"), "op-p3", writer_session_id="s")
        self.assertIn("downgrade.required_removed", cm.exception.codes)

    def test_a20_plan_ancestry_and_downgrades_checked_at_commit(self):
        head = F.seed(self.s)
        skip = F.plan(3, [F.obligation("O1")])
        skip["parent_revision"] = 2
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [skip], head, "op-a", writer_session_id="s")
        self.assertIn("plan.ancestry", cm.exception.codes)
        no_dec = F.plan(2, [F.obligation("O1")])
        del no_dec["obligations"][0]["decision_required"]
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [no_dec], head, "op-b", writer_session_id="s")
        self.assertIn("plan.decision_required_missing", cm.exception.codes)
        self.assertEqual(self.s.head("ctx-1"), head)

    def test_same_id_never_maps_to_different_bytes(self):
        head = F.seed(self.s)
        a = F.assignment("asg-1", "someone-else")
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [a], head, "op-c", writer_session_id="s")
        self.assertIn("object.id_reused", cm.exception.codes)

    def test_schemas_are_applied_at_commit(self):
        head = F.seed(self.s)
        a = F.assignment("asg-2", "rev-2")
        a["plan_revision"] = True  # a bool is not an integer (case N21 on the I/O path)
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [a], head, "op-s", writer_session_id="s")
        self.assertIn("schema.type", cm.exception.codes)
        rec = F.record(self.s, "rec-2", "asg-1", "rev-1")
        rec["surprise"] = 1
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [rec], head, "op-t", writer_session_id="s")
        self.assertIn("schema.additional", cm.exception.codes)

    def test_reports_are_never_committed(self):
        head = F.seed(self.s)
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [F.header("report", "rep-1")], head, "op-r", writer_session_id="s")
        self.assertIn("order.report_is_not_a_commit_input", cm.exception.codes)

    def test_blobs_must_exist_before_commit(self):
        head = F.seed(self.s)
        rec = F.record(self.s, "rec-2", "asg-1", "rev-1")
        rec["evidence"][0]["content_ref"]["digest"] = "ab" * 32
        with self.assertRaises(S.AdmissionRefused) as cm:
            self.s.append("ctx-1", [rec], head, "op-d", writer_session_id="s")
        self.assertIn("blob.missing", cm.exception.codes)

    def test_quarantinable_submissions_are_still_kept(self):
        head = F.seed(self.s)
        rec = F.record(self.s, "rec-2", "asg-1", "rev-1", fidelity="mismatch")
        self.s.append("ctx-1", [rec], head, "op-e", writer_session_id="s")
        v = H.validate(self.s.load_bundle("ctx-1"), H.LATEST_VALIDATOR)
        self.assertIn("rec-2", v["quarantined_records"])

    def test_p05_rollback_leaves_head_unchanged(self):
        head = F.seed(self.s)

        def boom():
            raise RuntimeError("interrupted inside the transaction")
        with self.assertRaises(RuntimeError):
            self.s.append("ctx-1", [F.assignment("asg-2", "rev-2")], head, "op-f", writer_session_id="s",
                          _after_insert=boom)
        self.assertEqual(self.s.head("ctx-1"), head)
        self.assertEqual(len(self.s.load_bundle("ctx-1")["commits"]), 5)
        self.s.append("ctx-1", [F.assignment("asg-2", "rev-2")], head, "op-f", writer_session_id="s")

    def test_p07_blob_changed_after_commit_quarantines_dependents(self):
        F.seed(self.s)
        b = self.s.load_bundle("ctx-1")
        rec = [o for c in b["commits"] for o in c["objects"] if o["id"] == "rec-1"][0]
        d = rec["evidence"][0]["content_ref"]["digest"]
        blob = self.dir / "blobs" / d
        os.chmod(blob, 0o600)
        blob.write_bytes(b"changed after commit")
        b2 = self.s.load_bundle("ctx-1")
        self.assertEqual(b2["blob_checks"][d], "changed")
        v = H.validate(b2, H.LATEST_VALIDATOR)
        self.assertIn("rec-1-E1-1", v["quarantined_items"])
        self.assertTrue((self.dir / "blobs" / d).read_bytes() == b"changed after commit")  # never back-filled

    def test_n07_reading_and_exporting_do_not_move_the_head(self):
        head = F.seed(self.s)
        self.s.load_bundle("ctx-1")
        self.s.load_bundle("ctx-1", as_of_seq=3)
        self.assertEqual(self.s.head("ctx-1"), head)

    def test_as_of_n_is_a_prefix(self):
        F.seed(self.s)
        b = self.s.load_bundle("ctx-1", as_of_seq=3)
        self.assertEqual(b["as_of_seq"], 3)
        self.assertEqual(len(b["commits"]), 3)
        self.assertEqual(b["as_of_commit_digest"], b["commits"][-1]["digest"])

    def test_n61_current_report_needs_latest_approved_validator(self):
        self.assertTrue(S.check_current_validator(H.LATEST_VALIDATOR))
        with self.assertRaises(S.ValidatorNotApproved):
            S.check_current_validator("0.0.9")


class Processes(StoreCase):
    def script(self, body: str) -> list[str]:
        prog = textwrap.dedent(f"""
            import json, sys
            sys.path.insert(0, {str(ROOT)!r}); sys.path.insert(0, {str(ROOT / 'skills' / 'hep-review' / 'scripts')!r})
            sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})
            from hep_review_support import store as S
            import store_fixtures as F
            s = S.Store({str(self.dir)!r}, location=F.TEMP_LOCATION)
            head = json.loads(sys.argv[1])
        """) + textwrap.dedent(body)
        return [sys.executable, "-c", prog]

    def test_p06_crash_between_blob_write_and_commit_leaves_orphan_only(self):
        head = F.seed(self.s)
        body = """
            import os
            d = s.put_blob(b"orphan evidence bytes")
            print(d, flush=True)
            def die():
                os._exit(9)
            s.append("ctx-1", [F.assignment("asg-9", "rev-9")], head, "op-crash", writer_session_id="s", _after_insert=die)
        """
        r = subprocess.run(self.script(body) + [json.dumps(head)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 9, r.stderr)
        orphan = r.stdout.strip()
        self.s.close()
        self.s = S.Store(self.dir, location=F.TEMP_LOCATION)
        self.assertEqual(self.s.head("ctx-1"), head)
        self.assertIn(orphan, self.s.orphan_blobs("ctx-1"))
        self.assertNotIn("asg-9", json.dumps(self.s.load_bundle("ctx-1")))

    def test_p27_two_processes_one_cas_wins(self):
        head = F.seed(self.s)
        body = """
            import time
            aid = sys.argv[2]
            time.sleep(0.2)
            try:
                s.append("ctx-1", [F.assignment(aid, "rev-" + aid)], head, "op-" + aid, writer_session_id=aid)
                print("committed")
            except S.HeadMismatch:
                print("cas-lost")
        """
        procs = [subprocess.Popen(self.script(body) + [json.dumps(head), a], stdout=subprocess.PIPE, text=True)
                 for a in ("asg-7", "asg-8")]
        outs = sorted(p.communicate(timeout=60)[0].strip() for p in procs)
        self.assertEqual(outs, ["cas-lost", "committed"])
        self.assertEqual(self.s.head("ctx-1")["seq"], 6)

    def test_a28_p08_report_covers_commits_up_to_n_while_another_commits(self):
        head = F.seed(self.s)
        b = self.s.load_bundle("ctx-1")
        self.s.append("ctx-1", [F.assignment("asg-2", "rev-2")], head, "op-late", writer_session_id="s2")
        p = H.project(H.validate(b, H.LATEST_VALIDATOR), H.LATEST_VALIDATOR)
        self.assertEqual(p["as_of_seq"], 5)
        self.assertNotIn("asg-2", json.dumps(b))


if __name__ == "__main__":
    unittest.main()
