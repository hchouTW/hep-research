"""hep-review controlled reading, snapshots and drop-file ingestion (spec v9 sections 9.1-9.4, 12.4).

Cases N26, N42, N67, P31, P32, P33 and the ingest_submission side of N31/N62."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-review" / "scripts"))

from hep_review_support import materials as M  # noqa: E402


class ControlledRead(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "root"
        (self.root / "a" / "b").mkdir(parents=True)
        (self.root / "a" / "b" / "f.txt").write_bytes(b"hello")
        self.outside = Path(self.temp_dir.name) / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_bytes(b"secret")

    def tearDown(self):
        self.temp_dir.cleanup()

    def refused(self, rel, code, **kw):
        with self.assertRaises(M.ReadRefused) as cm:
            M.read_controlled(self.root, rel, **kw)
        self.assertEqual(cm.exception.code, code, cm.exception)

    def test_regular_file_is_read(self):
        r = M.read_controlled(self.root, "a/b/f.txt")
        self.assertEqual(r.content, b"hello")
        self.assertEqual(r.sha256, hashlib.sha256(b"hello").hexdigest())
        self.assertEqual(r.limitations, [])

    def test_bad_components_refused(self):
        for rel in ("", "/etc/passwd", "a/../a/b/f.txt", "./a/b/f.txt", "a//b/f.txt", "a/b/"):
            with self.subTest(rel):
                self.refused(rel, "read.bad_component")

    def test_p31_symlink_last_component_refused(self):
        os.symlink(self.outside / "secret.txt", self.root / "a" / "link.txt")
        self.refused("a/link.txt", "read.symlink")

    def test_p31_n42_symlinked_parent_component_refused(self):
        os.symlink(self.outside, self.root / "a" / "dirlink")
        self.refused("a/dirlink/secret.txt", "read.symlink")

    def test_n42_fifo_does_not_block_and_is_refused(self):
        os.mkfifo(self.root / "a" / "fifo")
        self.refused("a/fifo", "read.not_regular")

    def test_directory_is_not_a_file(self):
        self.refused("a/b", "read.not_regular")

    def test_n67_size_limit(self):
        (self.root / "big.bin").write_bytes(b"x" * 2000)
        self.refused("big.bin", "read.too_large", max_bytes=1000)

    def test_missing_file(self):
        self.refused("a/b/none.txt", "read.missing")

    def test_n42_hard_link_is_a_limitation_not_a_refusal(self):
        os.link(self.root / "a" / "b" / "f.txt", self.root / "hard.txt")
        r = M.read_controlled(self.root, "hard.txt")
        self.assertEqual(r.content, b"hello")
        self.assertTrue(any("hard link" in x for x in r.limitations))

    def test_n26_platform_without_dir_fd_cannot_claim_root_bound_reading(self):
        caps = dict(M.platform_capabilities(), supports_dir_fd_open=False)
        with self.assertRaises(M.ControlledReadUnavailable):
            M.read_controlled(self.root, "a/b/f.txt", caps=caps)
        self.assertFalse(M.controlled_read_available(caps))
        self.assertTrue(M.controlled_read_available(M.platform_capabilities()))


class Snapshots(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "src"
        self.root.mkdir()
        (self.root / "analysis.md").write_bytes(b"# analysis\n")
        (self.root / "data.json").write_bytes(b'{"x": 1}\n')
        self.snapdir = Path(self.temp_dir.name) / "snap"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_snapshot_hashes_the_saved_bytes_and_lists_gaps(self):
        os.symlink("/etc/hosts", self.root / "link.md")
        m = M.snapshot(self.root, ["analysis.md", "data.json", "link.md", "absent.md"], self.snapdir)
        ids = {x["material_id"]: x for x in m["materials"]}
        self.assertEqual(set(ids), {"analysis.md", "data.json"})
        saved = (self.snapdir / ids["data.json"]["raw_ref"]["digest"]).read_bytes()
        self.assertEqual(hashlib.sha256(saved).hexdigest(), ids["data.json"]["raw_ref"]["digest"])
        self.assertEqual({g["path"]: g["code"] for g in m["coverage_gaps"]},
                         {"link.md": "read.symlink", "absent.md": "read.missing"})
        self.assertEqual(m["capture"]["method"], "working-copy-file-by-file")
        self.assertFalse(m["capture"]["coherent_version"])

    def test_snapshot_entries_are_committable_metadata(self):
        # nanosecond times exceed 2^53-1: they are kept as decimal strings (spec 10.2), so a manifest encodes
        from contracts import hep_review as H
        m = M.snapshot(self.root, ["analysis.md"], self.snapdir)
        cap = m["materials"][0]["capture"]
        self.assertIsInstance(cap["mtime_ns"], str)
        self.assertTrue(cap["mtime_ns"].isdigit())
        H.encode(m["materials"][0])

    def test_p32_later_source_change_does_not_change_the_snapshot(self):
        m = M.snapshot(self.root, ["analysis.md"], self.snapdir)
        d = m["materials"][0]["raw_ref"]["digest"]
        (self.root / "analysis.md").write_bytes(b"# changed after capture\n")
        self.assertEqual(M.read_snapshot(self.snapdir, d), b"# analysis\n")

    def test_p32_change_during_capture_is_a_gap(self):
        def mutate(path):
            path.write_bytes(b"# changed while reading\n" * 10)
        m = M.snapshot(self.root, ["analysis.md"], self.snapdir, _between_reads=mutate, max_attempts=1)
        self.assertEqual(m["materials"], [])
        self.assertEqual(m["coverage_gaps"][0]["code"], "capture.unstable")

    def test_p33_coherent_version_required_but_only_working_copy(self):
        m = M.snapshot(self.root, ["analysis.md", "data.json"], self.snapdir, require_coherent_version=True)
        self.assertFalse(m["capture"]["coherent_version"])
        self.assertIn("capture.no_coherent_version", {g["code"] for g in m["coverage_gaps"]})

    def test_snapshot_read_verifies_the_digest(self):
        m = M.snapshot(self.root, ["analysis.md"], self.snapdir)
        d = m["materials"][0]["raw_ref"]["digest"]
        (self.snapdir / d).write_bytes(b"tampered")
        with self.assertRaises(M.ReadRefused) as cm:
            M.read_snapshot(self.snapdir, d)
        self.assertEqual(cm.exception.code, "snapshot.digest_mismatch")


class Submissions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.drops = Path(self.temp_dir.name) / "drops"
        (self.drops / "asg-1").mkdir(parents=True)
        self.body = b'{"assignment_id": "asg-1", "answers": []}'
        (self.drops / "asg-1" / "submission.json").write_bytes(self.body)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_transfer_without_digest(self):
        s = M.ingest_submission(self.drops, "asg-1/submission.json")
        self.assertEqual(s["submission_fidelity"], "file-transfer")
        self.assertEqual(s["raw"], self.body)
        self.assertEqual(s["raw_ref"]["digest"], hashlib.sha256(self.body).hexdigest())

    def test_digest_bound_and_mismatch(self):
        good = hashlib.sha256(self.body).hexdigest()
        self.assertEqual(M.ingest_submission(self.drops, "asg-1/submission.json", declared_digest=good)
                         ["submission_fidelity"], "digest-bound")
        bad = M.ingest_submission(self.drops, "asg-1/submission.json", declared_digest="0" * 64)
        self.assertEqual(bad["submission_fidelity"], "mismatch")
        self.assertEqual(bad["raw"], self.body)  # both copies kept: the bytes and the declared digest
        self.assertEqual(bad["declared_digest"], "0" * 64)

    def test_n67_drop_path_replaced_by_symlink_or_fifo_or_oversize(self):
        outside = Path(self.temp_dir.name) / "outside.json"
        outside.write_bytes(b"{}")
        (self.drops / "asg-2").mkdir()
        os.symlink(outside, self.drops / "asg-2" / "submission.json")
        with self.assertRaises(M.ReadRefused):
            M.ingest_submission(self.drops, "asg-2/submission.json")
        (self.drops / "asg-3").mkdir()
        os.mkfifo(self.drops / "asg-3" / "submission.json")
        with self.assertRaises(M.ReadRefused):
            M.ingest_submission(self.drops, "asg-3/submission.json")
        with self.assertRaises(M.ReadRefused):
            M.ingest_submission(self.drops, "asg-1/submission.json", max_bytes=10)
        os.symlink(self.drops / "asg-1", self.drops / "asg-4")
        with self.assertRaises(M.ReadRefused):
            M.ingest_submission(self.drops, "asg-4/submission.json")

    def test_n31_transcribed_is_explicit(self):
        s = M.transcribed_submission("text the coordinator typed")
        self.assertEqual(s["submission_fidelity"], "transcribed")


if __name__ == "__main__":
    unittest.main()
